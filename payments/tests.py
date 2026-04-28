from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order
from payments.models import Payment
from payments.services import PaymentIntegrationError
from ventas.models import Venta


@override_settings(PAYMENTS_WEBHOOK_SECRET="test-webhook-secret")
class PaymentsSecurityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser(
            email="admin.payments@test.com",
            nombre="Admin",
            apellido="Payments",
            telefono="+56922000001",
            password="AdminPass123!",
        )
        cls.customer = user_model.objects.create_user(
            email="customer.payments@test.com",
            nombre="Customer",
            apellido="Payments",
            telefono="+56922000002",
            password="UserPass123!",
        )
        cls.other_user = user_model.objects.create_user(
            email="other.payments@test.com",
            nombre="Other",
            apellido="Payments",
            telefono="+56922000003",
            password="UserPass123!",
        )

        sale = Venta.objects.create(
            cart_id=uuid4(),
            user=cls.customer,
            status=Venta.Status.COMPLETED,
            currency="CLP",
            subtotal_amount=Decimal("10000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("1900"),
            total_amount=Decimal("11900"),
            items_count=1,
            total_quantity=1,
            sold_at=timezone.now(),
        )
        cls.order = Order.objects.create(
            sale=sale,
            user=cls.customer,
            status=Order.Status.PENDING,
            currency="CLP",
            subtotal_amount=sale.subtotal_amount,
            discount_amount=sale.discount_amount,
            tax_amount=sale.tax_amount,
            total_amount=sale.total_amount,
        )
        cls.payment = Payment.objects.create(
            order=cls.order,
            provider="webpay",
            status=Payment.Status.PENDING,
            amount=cls.order.total_amount,
            currency=cls.order.currency,
            provider_reference="token-secure-test",
        )

    def test_webpay_status_is_restricted_to_owner_or_admin(self):
        with patch("payments.api.webpay_transaction_status") as mocked_status:
            mocked_status.return_value = {"status": "AUTHORIZED", "response_code": 0}

            self.client.force_authenticate(user=self.other_user)
            response = self.client.get("/payments/webpay/status/?token_ws=token-secure-test")
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.client.force_authenticate(user=self.customer)
            response = self.client.get("/payments/webpay/status/?token_ws=token-secure-test")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_webpay_refund_requires_admin(self):
        with patch("payments.api.webpay_refund") as mocked_refund:
            mocked_refund.return_value = (self.payment, {"type": "NULLIFIED", "balance": 0})

            self.client.force_authenticate(user=self.customer)
            response = self.client.post(
                "/payments/webpay/refund/",
                {"token_ws": "token-secure-test", "amount": "11900"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

            self.client.force_authenticate(user=self.admin)
            response = self.client.post(
                "/payments/webpay/refund/",
                {"token_ws": "token-secure-test", "amount": "11900"},
                format="json",
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_webhook_rejects_invalid_payment_transition(self):
        self.payment.status = Payment.Status.REFUNDED
        self.payment.save(update_fields=["status", "updated_at"])

        response = self.client.post(
            "/payments/webhook/",
            {"provider_reference": "token-secure-test", "status": "paid"},
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class GuestPaymentIntentTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.guest_token = "guest-token-payments-test"
        cls.sale = Venta.objects.create(
            cart_id=uuid4(),
            user=None,
            guest_token=cls.guest_token,
            status=Venta.Status.COMPLETED,
            currency="CLP",
            subtotal_amount=Decimal("5000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("950"),
            total_amount=Decimal("5950"),
            items_count=1,
            total_quantity=1,
            sold_at=timezone.now(),
        )
        cls.order = Order.objects.create(
            sale=cls.sale,
            user=None,
            status=Order.Status.PENDING,
            currency="CLP",
            subtotal_amount=cls.sale.subtotal_amount,
            discount_amount=cls.sale.discount_amount,
            tax_amount=cls.sale.tax_amount,
            total_amount=cls.sale.total_amount,
        )

    def test_guest_can_create_payment_intent_with_valid_guest_token(self):
        with patch("payments.api.create_payment_intent") as mocked_create_intent:
            mocked_create_intent.return_value = {
                "payment_id": str(uuid4()),
                "provider": "webpay",
                "provider_reference": "token123",
                "token": "token123",
                "redirect_url": "https://webpay3gint.transbank.cl/webpayserver/initTransaction?token_ws=token123",
                "amount": "5950",
                "currency": "CLP",
                "status": "pending",
            }

            response = self.client.post(
                "/payments/create-intent/",
                {"order_id": str(self.order.id), "provider": "webpay"},
                format="json",
                HTTP_X_GUEST_TOKEN=self.guest_token,
            )

            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            mocked_create_intent.assert_called_once()

    def test_guest_cannot_create_payment_intent_with_invalid_guest_token(self):
        response = self.client.post(
            "/payments/create-intent/",
            {"order_id": str(self.order.id), "provider": "webpay"},
            format="json",
            HTTP_X_GUEST_TOKEN="guest-token-incorrecto",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class WebpayReturnTests(APITestCase):
    def test_return_without_token_redirects_as_failed(self):
        response = self.client.get("/payments/webpay/return/")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("outcome=failed", response["Location"])
        self.assertIn("reason=missing_token_ws", response["Location"])

    def test_return_unexpected_exception_redirects_without_500(self):
        with patch("payments.api.commit_webpay_transaction", side_effect=Exception("boom")):
            response = self.client.get("/payments/webpay/return/?token_ws=tok123")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("outcome=failed", response["Location"])
        self.assertIn("reason=unexpected_error", response["Location"])
        self.assertIn("error_id=", response["Location"])

    def test_return_payment_integration_error_exposes_reason_code(self):
        with patch(
            "payments.api.commit_webpay_transaction",
            side_effect=PaymentIntegrationError("No existe un pago Webpay asociado al token."),
        ):
            response = self.client.get("/payments/webpay/return/?token_ws=tok123")
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("reason=payment_integration_error", response["Location"])
        self.assertIn("detail=", response["Location"])


class WebpayCommitApiTests(APITestCase):
    def test_commit_unexpected_exception_returns_controlled_error(self):
        with patch("payments.api.commit_webpay_transaction", side_effect=Exception("boom")):
            response = self.client.post(
                "/payments/webpay/commit/",
                {"token_ws": "tok123"},
                format="json",
            )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Error interno al confirmar transaccion Webpay.", response.data.get("detail", ""))
        self.assertIn("ref=", response.data.get("detail", ""))
