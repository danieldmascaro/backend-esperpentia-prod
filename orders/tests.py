from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order
from ventas.models import Venta


class OrderTransitionsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser(
            email="admin.orders@test.com",
            nombre="Admin",
            apellido="Orders",
            telefono="+56924000001",
            password="AdminPass123!",
        )

        cls.customer = user_model.objects.create_user(
            email="customer.orders@test.com",
            nombre="Customer",
            apellido="Orders",
            telefono="+56924000002",
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
            status=Order.Status.SHIPPED,
            currency="CLP",
            subtotal_amount=sale.subtotal_amount,
            discount_amount=sale.discount_amount,
            tax_amount=sale.tax_amount,
            total_amount=sale.total_amount,
        )

    def test_admin_cannot_apply_invalid_order_transition(self):
        self.client.force_authenticate(user=self.admin)
        response = self.client.patch(
            f"/orders/{self.order.id}/admin/status/",
            {"status": Order.Status.PROCESSING},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_deletion_does_not_remove_historic_order_or_sale(self):
        self.customer.delete()
        self.order.refresh_from_db()
        self.order.sale.refresh_from_db()
        self.assertIsNone(self.order.user)
        self.assertIsNone(self.order.sale.user)
