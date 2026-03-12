from uuid import uuid4

from django.conf import settings
from django.db import transaction

from orders.models import Order
from transbank.common.integration_api_keys import IntegrationApiKeys
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.webpay.webpay_plus.transaction import Transaction

from .models import Payment


class PaymentIntegrationError(Exception):
    pass


def _build_webpay_transaction():
    commerce_code = getattr(settings, "WEBPAY_COMMERCE_CODE", str(IntegrationCommerceCodes.WEBPAY_PLUS))
    api_key = getattr(settings, "WEBPAY_API_KEY", IntegrationApiKeys.WEBPAY)
    return Transaction.build_for_integration(commerce_code, api_key)


def _sync_order_status_from_payment(order, payment_status):
    if payment_status == Payment.Status.PAID:
        order.status = Order.Status.PAID
    elif payment_status == Payment.Status.FAILED:
        order.status = Order.Status.CANCELLED
    elif payment_status == Payment.Status.REFUNDED:
        order.status = Order.Status.CANCELLED
    elif payment_status == Payment.Status.AUTHORIZED:
        order.status = Order.Status.PROCESSING
    order.save(update_fields=["status", "updated_at"])


@transaction.atomic
def create_payment_intent(order, provider="mockpay"):
    if provider == "webpay":
        tx = _build_webpay_transaction()
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
            "sandbox": True,
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
    payment.status = Payment.Status.PAID if is_success else Payment.Status.FAILED
    payment.save(update_fields=["status", "updated_at"])

    _sync_order_status_from_payment(payment.order, payment.status)
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

    payment.status = Payment.Status.REFUNDED
    payment.save(update_fields=["status", "updated_at"])
    _sync_order_status_from_payment(payment.order, payment.status)
    return payment, response


@transaction.atomic
def process_webhook(provider_reference, status):
    payment = Payment.objects.select_for_update().select_related("order").get(provider_reference=provider_reference)
    payment.status = status
    payment.save(update_fields=["status", "updated_at"])

    _sync_order_status_from_payment(payment.order, status)

    return payment
