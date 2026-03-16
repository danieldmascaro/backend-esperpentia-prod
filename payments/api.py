from django.conf import settings
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from orders.models import Order

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


class PaymentCreateIntentAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_user"

    def post(self, request):
        serializer = CreatePaymentIntentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order_id = serializer.validated_data["order_id"]
        provider = serializer.validated_data.get("provider", "mockpay")

        order = Order.objects.filter(id=order_id).first()
        if not order:
            return Response({"detail": "Order no encontrada."}, status=status.HTTP_404_NOT_FOUND)

        if not request.user.is_staff and order.user_id != request.user.id:
            return Response({"detail": "No autorizado para pagar esta orden."}, status=status.HTTP_403_FORBIDDEN)

        try:
            payload = create_payment_intent(order, provider=provider)
        except PaymentIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(payload, status=status.HTTP_201_CREATED)


class PaymentWebhookAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_webhook_public"

    def post(self, request):
        secret = getattr(settings, "PAYMENTS_WEBHOOK_SECRET", "")
        if not secret:
            return Response({"detail": "Webhook no configurado."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        if secret:
            provided = request.headers.get("X-Webhook-Secret", "")
            if provided != secret:
                return Response({"detail": "Webhook unauthorized."}, status=status.HTTP_403_FORBIDDEN)

        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payment = process_webhook(
            provider_reference=serializer.validated_data["provider_reference"],
            status=serializer.validated_data["status"],
        )
        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)


class WebpayCommitAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_commit_public"

    def post(self, request):
        serializer = WebpayCommitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token_ws"]
        try:
            payment, webpay_response = commit_webpay_transaction(token)
        except PaymentIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "payment": PaymentSerializer(payment).data,
                "webpay": webpay_response,
            },
            status=status.HTTP_200_OK,
        )


class WebpayStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [*api_settings.DEFAULT_THROTTLE_CLASSES, ScopedRateThrottle]
    throttle_scope = "payments_user"

    def get(self, request):
        token = request.query_params.get("token_ws")
        if not token:
            return Response({"detail": "token_ws es requerido."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            response = webpay_transaction_status(token)
        except PaymentIntegrationError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(response, status=status.HTTP_200_OK)


class WebpayRefundAPIView(APIView):
    permission_classes = [IsAuthenticated]
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
