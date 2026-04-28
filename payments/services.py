from uuid import uuid4
import logging

from django.conf import settings
from django.db import transaction

from orders.models import Order
from transbank.common.integration_type import IntegrationType
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.options import WebpayOptions
from transbank.webpay.webpay_plus.transaction import Transaction
from ventas.services import sync_sale_status_from_payment

from .models import Payment

logger = logging.getLogger(__name__)


class PaymentIntegrationError(Exception):
    pass


ALLOWED_PAYMENT_TRANSITIONS = {
    Payment.Status.PENDING: {
        Payment.Status.PENDING,
        Payment.Status.AUTHORIZED,
        Payment.Status.PAID,
        Payment.Status.FAILED,
    },
    Payment.Status.AUTHORIZED: {
        Payment.Status.AUTHORIZED,
        Payment.Status.PAID,
        Payment.Status.FAILED,
        Payment.Status.REFUNDED,
    },
    Payment.Status.PAID: {
        Payment.Status.PAID,
        Payment.Status.REFUNDED,
    },
    Payment.Status.FAILED: {Payment.Status.FAILED},
    Payment.Status.REFUNDED: {Payment.Status.REFUNDED},
}


def _ensure_valid_payment_transition(payment, next_status):
    allowed = ALLOWED_PAYMENT_TRANSITIONS.get(payment.status, {payment.status})
    if next_status not in allowed:
        raise PaymentIntegrationError(
            f"Transicion de estado de pago invalida: {payment.status} -> {next_status}."
        )


def _get_webpay_options():
    commerce_code = str(
        getattr(settings, "WEBPAY_COMMERCE_CODE", str(IntegrationCommerceCodes.WEBPAY_PLUS))
    ).strip()
    api_key = str(getattr(settings, "WEBPAY_API_KEY", IntegrationApiKeys.WEBPAY)).strip()
    configured_environment = str(getattr(settings, "WEBPAY_ENVIRONMENT", "")).strip().upper()

    if configured_environment in {"LIVE", "TEST", "MOCK"}:
        integration_type = IntegrationType[configured_environment]
    else:
        is_default_integration_credentials = (
            commerce_code == str(IntegrationCommerceCodes.WEBPAY_PLUS)
            and api_key == IntegrationApiKeys.WEBPAY
        )
        integration_type = IntegrationType.TEST if is_default_integration_credentials else IntegrationType.LIVE

    return WebpayOptions(commerce_code, api_key, integration_type), integration_type


def _build_webpay_transaction():
    options, _ = _get_webpay_options()
    return Transaction(options)


def _sync_order_status_from_payment(order, payment_status):
    next_status = order.status
    if payment_status == Payment.Status.PAID:
        next_status = Order.Status.PAID
    elif payment_status == Payment.Status.FAILED:
        next_status = Order.Status.CANCELLED
    elif payment_status == Payment.Status.REFUNDED:
        next_status = Order.Status.CANCELLED
    elif payment_status == Payment.Status.AUTHORIZED:
        next_status = Order.Status.PROCESSING
    if order.status != next_status:
        order.status = next_status
        order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def create_payment_intent(order, provider="mockpay"):
    if provider == "webpay":
        tx = _build_webpay_transaction()
        _, integration_type = _get_webpay_options()
        buy_order = f"ORD{order.id.hex[:22]}"
        session_id = f"SES{order.id.hex[:22]}"
        amount = int(order.total_amount)
        return_url = getattr(settings, "WEBPAY_RETURN_URL", "http://localhost:8000/payments/webpay/commit/")

        try:
            response = tx.create(buy_order=buy_order, session_id=session_id, amount=amount, return_url=return_url)
        except Exception as exc:
            raise PaymentIntegrationError(f"Error creando transaccion Webpay: {exc}")

        token = response.get("token")
        url = response.get("url")
        if not token or not url:
            raise PaymentIntegrationError("Respuesta invalida de Webpay al crear transaccion.")

        payment = Payment.objects.create(
            order=order,
            provider="webpay",
            status=Payment.Status.PENDING,
            amount=order.total_amount,
            currency=order.currency,
            provider_reference=token,
        )
        return {
            "payment_id": str(payment.id),
            "provider": "webpay",
            "provider_reference": token,
            "token": token,
            "redirect_url": f"{url}?token_ws={token}",
            "webpay_url": url,
            "amount": str(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "sandbox": integration_type != IntegrationType.LIVE,
        }

    provider_reference = f"{provider}_{uuid4().hex[:20]}"
    payment = Payment.objects.create(
        order=order,
        provider=provider,
        status=Payment.Status.PENDING,
        amount=order.total_amount,
        currency=order.currency,
        provider_reference=provider_reference,
    )
    return {
        "payment_id": str(payment.id),
        "provider": provider,
        "provider_reference": provider_reference,
        "client_secret": f"mock_secret_{provider_reference}",
        "amount": str(payment.amount),
        "currency": payment.currency,
        "status": payment.status,
    }


@transaction.atomic
def commit_webpay_transaction(token):
    tx = _build_webpay_transaction()
    try:
        response = tx.commit(token=token)
    except Exception as exc:
        raise PaymentIntegrationError(f"Error al confirmar transaccion Webpay: {exc}")

    payment = Payment.objects.select_for_update().select_related("order").filter(provider="webpay", provider_reference=token).first()
    if not payment:
        raise PaymentIntegrationError("No existe un pago Webpay asociado al token.")

    response_code = response.get("response_code")
    status_code = str(response.get("status", "")).upper()
    is_success = response_code == 0 and status_code == "AUTHORIZED"
    next_status = Payment.Status.PAID if is_success else Payment.Status.FAILED
    _ensure_valid_payment_transition(payment, next_status)
    payment.status = next_status
    payment.save(update_fields=["status", "updated_at"])

    try:
        _sync_order_status_from_payment(payment.order, payment.status)
        sync_sale_status_from_payment(payment)
    except Exception as exc:
        logger.exception("Error sincronizando estado de orden/venta para token Webpay %s", token)
        raise PaymentIntegrationError(
            f"Error sincronizando estado interno tras commit Webpay: {exc}"
        )
    return payment, response


def webpay_transaction_status(token):
    tx = _build_webpay_transaction()
    try:
        return tx.status(token=token)
    except Exception as exc:
        raise PaymentIntegrationError(f"Error consultando estado Webpay: {exc}")


@transaction.atomic
def webpay_refund(token, amount):
    tx = _build_webpay_transaction()
    try:
        response = tx.refund(token=token, amount=float(amount))
    except Exception as exc:
        raise PaymentIntegrationError(f"Error al reversar/reembolsar en Webpay: {exc}")

    payment = Payment.objects.select_for_update().select_related("order").filter(provider="webpay", provider_reference=token).first()
    if not payment:
        raise PaymentIntegrationError("No existe un pago Webpay asociado al token.")

    _ensure_valid_payment_transition(payment, Payment.Status.REFUNDED)
    payment.status = Payment.Status.REFUNDED
    payment.save(update_fields=["status", "updated_at"])
    _sync_order_status_from_payment(payment.order, payment.status)
    sync_sale_status_from_payment(payment)
    return payment, response


@transaction.atomic
def process_webhook(provider_reference, status):
    payment = (
        Payment.objects.select_for_update()
        .select_related("order")
        .filter(provider_reference=provider_reference)
        .first()
    )
    if not payment:
        raise PaymentIntegrationError("No existe un pago asociado al provider_reference recibido.")
    _ensure_valid_payment_transition(payment, status)
    payment.status = status
    payment.save(update_fields=["status", "updated_at"])

    _sync_order_status_from_payment(payment.order, status)
    sync_sale_status_from_payment(payment)

    return payment
