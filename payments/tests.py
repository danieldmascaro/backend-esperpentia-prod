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
from payments.services import PaymentIntegrationError, commit_webpay_transaction, create_payment_intent
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


class WebpayPaymentIntentServiceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sale = Venta.objects.create(
            cart_id=uuid4(),
            user=None,
            status=Venta.Status.COMPLETED,
            currency="CLP",
            subtotal_amount=Decimal("10000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("10000"),
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

    @override_settings(WEBPAY_RETURN_URL="https://backend.example.com/payments/webpay/commit/")
    def test_webpay_intent_uses_configured_return_url(self):
        configured_return_url = "https://backend.example.com/payments/webpay/commit/"

        with patch("payments.services._build_webpay_transaction") as mocked_builder:
            mocked_tx = mocked_builder.return_value
            mocked_tx.create.return_value = {
                "token": "token-env-return-url",
                "url": "https://webpay.example.com/initTransaction",
            }

            payload = create_payment_intent(self.order, provider="webpay")

        mocked_tx.create.assert_called_once()
        self.assertEqual(mocked_tx.create.call_args.kwargs["return_url"], configured_return_url)
        self.assertEqual(payload["provider_reference"], "token-env-return-url")

    @override_settings(WEBPAY_RETURN_URL="")
    def test_webpay_intent_requires_return_url_setting(self):
        with patch("payments.services._build_webpay_transaction") as mocked_builder:
            with self.assertRaisesMessage(PaymentIntegrationError, "WEBPAY_RETURN_URL"):
                create_payment_intent(self.order, provider="webpay")

        mocked_builder.assert_not_called()

    @override_settings(WEBPAY_RETURN_URL="/payments/webpay/return/")
    def test_webpay_intent_rejects_relative_return_url(self):
        with self.assertRaisesMessage(PaymentIntegrationError, "URL absoluta http(s)"):
            create_payment_intent(self.order, provider="webpay")

    def test_commit_accepts_string_zero_response_code(self):
        payment = Payment.objects.create(
            order=self.order,
            provider="webpay",
            status=Payment.Status.PENDING,
            amount=self.order.total_amount,
            currency=self.order.currency,
            provider_reference="token-string-zero",
        )

        with patch("payments.services._build_webpay_transaction") as mocked_builder:
            mocked_tx = mocked_builder.return_value
            mocked_tx.commit.return_value = {"status": "AUTHORIZED", "response_code": "0"}

            updated_payment, webpay_response = commit_webpay_transaction("token-string-zero")

        payment.refresh_from_db()
        self.assertEqual(updated_payment.status, Payment.Status.PAID)
        self.assertEqual(payment.status, Payment.Status.PAID)
        self.assertEqual(webpay_response["response_code"], "0")

    def test_commit_is_idempotent_when_payment_is_already_paid(self):
        Payment.objects.create(
            order=self.order,
            provider="webpay",
            status=Payment.Status.PAID,
            amount=self.order.total_amount,
            currency=self.order.currency,
            provider_reference="token-already-paid",
        )

        with patch("payments.services._build_webpay_transaction") as mocked_builder:
            _, webpay_response = commit_webpay_transaction("token-already-paid")

        mocked_builder.assert_not_called()
        self.assertTrue(webpay_response["already_committed"])


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


@override_settings(WEBPAY_FRONTEND_RESULT_URL="https://frontend.example.com/checkout/resultado")
class WebpayCommitBrowserReturnTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sale = Venta.objects.create(
            cart_id=uuid4(),
            user=None,
            status=Venta.Status.COMPLETED,
            currency="CLP",
            subtotal_amount=Decimal("12000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("0"),
            total_amount=Decimal("12000"),
            items_count=1,
            total_quantity=1,
            sold_at=timezone.now(),
        )
        cls.order = Order.objects.create(
            sale=cls.sale,
            user=None,
            status=Order.Status.PAID,
            currency="CLP",
            subtotal_amount=cls.sale.subtotal_amount,
            discount_amount=cls.sale.discount_amount,
            tax_amount=cls.sale.tax_amount,
            total_amount=cls.sale.total_amount,
        )
        cls.payment = Payment.objects.create(
            order=cls.order,
            provider="webpay",
            status=Payment.Status.PAID,
            amount=cls.order.total_amount,
            currency=cls.order.currency,
            provider_reference="token-browser-return",
        )

    def test_commit_get_redirects_to_frontend_after_commit(self):
        with patch(
            "payments.api.commit_webpay_transaction",
            return_value=(self.payment, {"status": "AUTHORIZED", "response_code": 0}),
        ) as mocked_commit:
            response = self.client.get("/payments/webpay/commit/?token_ws=token-browser-return")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertTrue(response["Location"].startswith("https://frontend.example.com/checkout/resultado?"))
        self.assertIn("outcome=paid", response["Location"])
        mocked_commit.assert_called_once_with("token-browser-return")

    def test_commit_form_post_redirects_to_frontend_after_commit(self):
        with patch(
            "payments.api.commit_webpay_transaction",
            return_value=(self.payment, {"status": "AUTHORIZED", "response_code": 0}),
        ):
            response = self.client.post(
                "/payments/webpay/commit/",
                {"token_ws": "token-browser-return"},
            )

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("outcome=paid", response["Location"])

    def test_commit_browser_return_handles_aborted_payment(self):
        response = self.client.get("/payments/webpay/commit/?TBK_TOKEN=token-browser-return")

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn("outcome=aborted", response["Location"])
        self.assertIn("reason=payment_aborted_by_user", response["Location"])


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
