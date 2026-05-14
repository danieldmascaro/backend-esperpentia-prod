import hmac
import logging
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.http import HttpResponseRedirect
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from orders.models import Order
from .models import Payment

from .serializers import (
    CreatePaymentIntentSerializer,
    PaymentSerializer,
    PaymentWebhookSerializer,
    WebpayCommitSerializer,
    WebpayRefundSerializer,
)
from .services import (
    PaymentIntegrationError,
    commit_webpay_transaction,
    create_payment_intent,
    process_webhook,
    webpay_refund,
    webpay_transaction_status,
)

logger = logging.getLogger(__name__)


class PaymentCreateIntentAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_user"

    def _get_guest_token(self, request):
        body_token = request.data.get("guest_token") if request.method != "GET" else None
        return (
            request.headers.get("X-Guest-Token")
            or request.query_params.get("guest_token")
            or body_token
        )

    def post(self, request):
        try:
            serializer = CreatePaymentIntentSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            order_id = serializer.validated_data["order_id"]
            provider = serializer.validated_data.get("provider", "webpay")

            order = Order.objects.select_related("sale").filter(id=order_id).first()
            if not order:
                return Response({"detail": "Order no encontrada."}, status=status.HTTP_404_NOT_FOUND)

            if request.user.is_authenticated:
                if not request.user.is_staff and order.user_id != request.user.id:
                    return Response({"detail": "No autorizado para pagar esta orden."}, status=status.HTTP_403_FORBIDDEN)
            else:
                guest_token = self._get_guest_token(request)
                if order.user_id:
                    return Response({"detail": "No autorizado para pagar esta orden."}, status=status.HTTP_403_FORBIDDEN)
                sale_guest_token = getattr(order.sale, "guest_token", None)
                if not guest_token or not sale_guest_token or guest_token != sale_guest_token:
                    return Response({"detail": "No autorizado para pagar esta orden."}, status=status.HTTP_403_FORBIDDEN)

            payload = create_payment_intent(order, provider=provider)
        except PaymentIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            error_id = uuid4().hex[:12]
            logger.exception("Error inesperado al crear intent de pago. error_id=%s", error_id)
            return Response(
                {"detail": f"Error interno creando el intento de pago. ref={error_id}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(payload, status=status.HTTP_201_CREATED)


class PaymentWebhookAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_webhook_public"

    def post(self, request):
        secret = getattr(settings, "PAYMENTS_WEBHOOK_SECRET", "")
        if not secret:
            return Response({"detail": "Webhook no configurado."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        provided = request.headers.get("X-Webhook-Secret", "")
        if not hmac.compare_digest(provided, secret):
            return Response({"detail": "Webhook unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            payment = process_webhook(
                provider_reference=serializer.validated_data["provider_reference"],
                status=serializer.validated_data["status"],
            )
        except PaymentIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)


class WebpayCommitAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_commit_public"

    @staticmethod
    def _is_json_request(request):
        return "application/json" in (request.content_type or "").lower()

    def _handle_api_commit(self, request):
        try:
            serializer = WebpayCommitSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            token = serializer.validated_data["token_ws"]
            payment, webpay_response = commit_webpay_transaction(token)
        except PaymentIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            error_id = uuid4().hex[:12]
            logger.exception("Error inesperado en commit Webpay. error_id=%s", error_id)
            return Response(
                {"detail": f"Error interno al confirmar transaccion Webpay. ref={error_id}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "webpay": webpay_response,
            },
            status=status.HTTP_200_OK,
        )

    def get(self, request):
        return WebpayReturnAPIView()._handle_return(request)

    def post(self, request):
        if not self._is_json_request(request):
            return WebpayReturnAPIView()._handle_return(request)

        return self._handle_api_commit(request)


class WebpayReturnAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_commit_public"

    @staticmethod
    def _frontend_result_base_url():
        default_url = "http://localhost:5173/checkout/resultado"
        return getattr(settings, "WEBPAY_FRONTEND_RESULT_URL", default_url)

    @classmethod
    def _build_redirect_url(cls, **params):
        base_url = cls._frontend_result_base_url()
        serialized_params = {key: value for key, value in params.items() if value is not None}
        if not serialized_params:
            return base_url
        separator = "&" if "?" in base_url else "?"
        return f"{base_url}{separator}{urlencode(serialized_params)}"

    @staticmethod
    def _extract_param(request, key):
        query_value = request.query_params.get(key)
        if query_value:
            return query_value
        try:
            data_value = request.data.get(key)
            if data_value:
                return data_value
        except Exception:
            logger.exception("No se pudo leer '%s' desde request.data en retorno Webpay.", key)
        return None

    @staticmethod
    def _build_purchase_summary(payment):
        order = payment.order
        sale = getattr(order, "sale", None)
        if sale is None:
            return {}

        items = list(sale.items.all())
        item_names = [item.libro_nombre for item in items if item.libro_nombre]
        books_preview = " | ".join(item_names[:3]) if item_names else None
        if books_preview and len(item_names) > 3:
            books_preview = f"{books_preview} | +{len(item_names) - 3} mas"

        return {
            "total_amount": str(order.total_amount),
            "currency": order.currency,
            "purchased_at": sale.sold_at.isoformat() if sale.sold_at else None,
            "books": books_preview,
            "items_count": str(sale.items_count),
            "total_quantity": str(sale.total_quantity),
        }

    def _handle_return(self, request):
        try:
            token = self._extract_param(request, "token_ws")
            tbk_token = self._extract_param(request, "TBK_TOKEN")

            if tbk_token and not token:
                return HttpResponseRedirect(
                    self._build_redirect_url(
                        outcome="aborted",
                        reason="payment_aborted_by_user",
                    )
                )

            if not token:
                return HttpResponseRedirect(
                    self._build_redirect_url(
                        outcome="failed",
                        reason="missing_token_ws",
                    )
                )

            try:
                payment, _ = commit_webpay_transaction(token)
            except PaymentIntegrationError as exc:
                return HttpResponseRedirect(
                    self._build_redirect_url(
                        outcome="failed",
                        reason="payment_integration_error",
                        detail=str(exc),
                    )
                )

            payment = (
                Payment.objects.select_related("order__sale")
                .prefetch_related("order__sale__items")
                .filter(id=payment.id)
                .first()
                or payment
            )

            outcome = "paid" if payment.status == Payment.Status.PAID else "failed"
            purchase_summary = self._build_purchase_summary(payment) if outcome == "paid" else {}
            return HttpResponseRedirect(
                self._build_redirect_url(
                    outcome=outcome,
                    payment_id=str(payment.id),
                    order_id=str(payment.order_id),
                    token_ws=token,
                    **purchase_summary,
                )
            )
        except Exception:
            error_id = uuid4().hex[:12]
            logger.exception("Error inesperado en retorno Webpay. error_id=%s", error_id)
            return HttpResponseRedirect(
                self._build_redirect_url(
                    outcome="failed",
                    reason="unexpected_error",
                    error_id=error_id,
                )
            )

    def get(self, request):
        return self._handle_return(request)

    def post(self, request):
        return self._handle_return(request)


class WebpayStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_user"

    def get(self, request):
        token = request.query_params.get("token_ws")
        if not token:
            return Response({"detail": "token_ws es requerido."}, status=status.HTTP_400_BAD_REQUEST)
        payment = Payment.objects.select_related("order").filter(provider="webpay", provider_reference=token).first()
        if not payment:
            return Response({"detail": "Pago no encontrado para token_ws."}, status=status.HTTP_404_NOT_FOUND)
        if not request.user.is_staff and payment.order.user_id != request.user.id:
            return Response({"detail": "No autorizado para consultar este pago."}, status=status.HTTP_403_FORBIDDEN)
        try:
            response = webpay_transaction_status(token)
        except PaymentIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_200_OK)


class WebpayRefundAPIView(APIView):
    permission_classes = [IsAdminUser]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_user"

    def post(self, request):
        serializer = WebpayRefundSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token_ws"]
        amount = serializer.validated_data["amount"]
        try:
            payment, webpay_response = webpay_refund(token, amount)
        except PaymentIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "webpay": webpay_response,
            },
            status=status.HTTP_200_OK,
        )
