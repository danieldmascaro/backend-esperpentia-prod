from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from .models import DiscountCoupon
from orders.models import Order
from productos.models import Autor, Editorial, Genero, Libro, Obra
from ventas.models import Venta


class CheckoutApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.author = Autor.objects.create(nombre="Autor Test", slug="autor-test")
        self.genre = Genero.objects.create(nombre="Genero Test", slug="genero-test")
        self.publisher = Editorial.objects.create(nombre="Editorial Test", slug="editorial-test")
        self.work = Obra.objects.create(
            titulo="Libro Test",
            slug="libro-test",
            autor=self.author,
            genero=self.genre,
        )
        self.book = Libro.objects.create(
            obra=self.work,
            editorial=self.publisher,
            slug="libro-test-edicion",
            sku="SKU-TEST-001",
            descripcion="",
            descripcion_corta="",
            precio=12990,
            stock=10,
            tipo_tapa=Libro.TipoTapa.BLANDA,
            cantidad_paginas=120,
            isbn="9780000000001",
            idioma="es",
            activo=True,
        )

    def test_current_cart_does_not_increment_version_when_nothing_changes(self):
        guest_token = "guest-version-check"
        response = self.client.post(
            "/checkout/carts/resolve/",
            {"guest_token": guest_token, "currency": "CLP"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        initial_version = response.data["version"]

        response = self.client.get("/checkout/carts/current/", HTTP_X_GUEST_TOKEN=guest_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], initial_version)

        response = self.client.get("/checkout/carts/current/", HTTP_X_GUEST_TOKEN=guest_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["version"], initial_version)

    def test_convert_cart_is_idempotent_with_same_key(self):
        guest_token = "guest-convert-check"
        resolve_response = self.client.post(
            "/checkout/carts/resolve/",
            {"guest_token": guest_token, "currency": "CLP"},
            format="json",
        )
        self.assertEqual(resolve_response.status_code, status.HTTP_200_OK)
        cart_id = resolve_response.data["id"]

        add_response = self.client.post(
            f"/checkout/carts/{cart_id}/add-item/",
            {"book_id": self.book.id, "quantity": 1},
            format="json",
            HTTP_X_GUEST_TOKEN=guest_token,
        )
        self.assertEqual(add_response.status_code, status.HTTP_200_OK)

        first_response = self.client.post(
            f"/checkout/carts/{cart_id}/convert/",
            format="json",
            HTTP_X_GUEST_TOKEN=guest_token,
            HTTP_IDEMPOTENCY_KEY="convert-test-key",
        )
        self.assertEqual(first_response.status_code, status.HTTP_200_OK)

        second_response = self.client.post(
            f"/checkout/carts/{cart_id}/convert/",
            format="json",
            HTTP_X_GUEST_TOKEN=guest_token,
            HTTP_IDEMPOTENCY_KEY="convert-test-key",
        )
        self.assertEqual(second_response.status_code, status.HTTP_200_OK)
        self.assertEqual(second_response.data, first_response.data)
        self.assertEqual(Venta.objects.filter(cart_id=cart_id).count(), 1)
        self.assertEqual(Order.objects.filter(sale__cart_id=cart_id).count(), 1)

    def test_apply_discount_requires_backend_coupon(self):
        guest_token = "guest-discount-check"
        resolve_response = self.client.post(
            "/checkout/carts/resolve/",
            {"guest_token": guest_token, "currency": "CLP"},
            format="json",
        )
        self.assertEqual(resolve_response.status_code, status.HTTP_200_OK)
        cart_id = resolve_response.data["id"]

        add_response = self.client.post(
            f"/checkout/carts/{cart_id}/add-item/",
            {"book_id": self.book.id, "quantity": 2},
            format="json",
            HTTP_X_GUEST_TOKEN=guest_token,
        )
        self.assertEqual(add_response.status_code, status.HTTP_200_OK)

        invalid_coupon_response = self.client.post(
            f"/checkout/carts/{cart_id}/apply-discount/",
            {"code": "INEXISTENTE"},
            format="json",
            HTTP_X_GUEST_TOKEN=guest_token,
        )
        self.assertEqual(invalid_coupon_response.status_code, status.HTTP_400_BAD_REQUEST)

        DiscountCoupon.objects.create(code="PROMO10", type="percent", value=10, active=True)
        valid_coupon_response = self.client.post(
            f"/checkout/carts/{cart_id}/apply-discount/",
            {"code": "PROMO10"},
            format="json",
            HTTP_X_GUEST_TOKEN=guest_token,
        )
        self.assertEqual(valid_coupon_response.status_code, status.HTTP_200_OK)
        self.assertEqual(valid_coupon_response.data["discount_amount"], "2598")
