from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from checkout.models import DiscountCoupon
from orders.models import Order
from payments.models import Payment
from productos.models import Autor, Editorial, Genero, Libro, Obra
from shipping.models import ShippingMethod
from usuarios.models import Comuna, Region
from ventas.models import Venta


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    PAYMENTS_WEBHOOK_SECRET="test-webhook-secret",
    DJOSER={
        "LOGIN_FIELD": "email",
        "SEND_ACTIVATION_EMAIL": False,
        "SEND_CONFIRMATION_EMAIL": False,
        "USER_CREATE_PASSWORD_RETYPE": True,
        "SET_PASSWORD_RETYPE": True,
        "PASSWORD_RESET_CONFIRM_URL": "password/reset/confirm/{uid}/{token}",
        "ACTIVATION_URL": "activate/{uid}/{token}",
    },
)
class BackendEndpointsV2Tests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.password = "Passw0rd-Endpoint"
        cls.region_metropolitana = Region.objects.create(nombre="Region Metropolitana")
        cls.region_valparaiso = Region.objects.create(nombre="Region de Valparaiso")
        cls.comuna_santiago = Comuna.objects.create(nombre="Santiago", region=cls.region_metropolitana)
        cls.comuna_providencia = Comuna.objects.create(nombre="Providencia", region=cls.region_metropolitana)
        cls.comuna_valparaiso = Comuna.objects.create(nombre="Valparaiso", region=cls.region_valparaiso)
        cls.admin = user_model.objects.create_superuser(
            email="admin@test.com",
            nombre="Admin",
            apellido="Root",
            telefono="+56911110001",
            password=cls.password,
            region=cls.region_metropolitana,
            comuna=cls.comuna_santiago,
        )
        cls.customer = user_model.objects.create_user(
            email="cliente@test.com",
            nombre="Cliente",
            apellido="Principal",
            telefono="+56911110002",
            password=cls.password,
            direccion_entrega="Av. Demo 123",
            region=cls.region_metropolitana,
            comuna=cls.comuna_providencia,
        )
        cls.secondary_customer = user_model.objects.create_user(
            email="cliente2@test.com",
            nombre="Cliente2",
            apellido="Secundario",
            telefono="+56911110003",
            password=cls.password,
            direccion_entrega="Calle 456",
            region=cls.region_valparaiso,
            comuna=cls.comuna_valparaiso,
        )

        cls.genero_novela = Genero.objects.create(nombre="Novela", slug="novela", descripcion="Narrativa")
        cls.genero_poesia = Genero.objects.create(nombre="Poesia", slug="poesia", descripcion="Verso")
        cls.editorial_alpha = Editorial.objects.create(
            nombre="Editorial Alpha",
            slug="editorial-alpha",
            descripcion="Sello Alpha",
            sitio_web="https://alpha.example.com",
        )
        cls.editorial_beta = Editorial.objects.create(
            nombre="Editorial Beta",
            slug="editorial-beta",
            descripcion="Sello Beta",
            sitio_web="https://beta.example.com",
        )
        cls.autor_cervantes = Autor.objects.create(
            nombre="Miguel de Cervantes",
            slug="miguel-de-cervantes",
            biografia="Autor canonico",
        )
        cls.autor_mistral = Autor.objects.create(
            nombre="Gabriela Mistral",
            slug="gabriela-mistral",
            biografia="Poeta chilena",
        )
        cls.obra_quijote = Obra.objects.create(
            titulo="Don Quijote",
            slug="don-quijote",
            descripcion="Novela clasica",
            descripcion_corta="Clasico",
            autor=cls.autor_cervantes,
            genero=cls.genero_novela,
        )
        cls.obra_desolacion = Obra.objects.create(
            titulo="Desolacion",
            slug="desolacion",
            descripcion="Poesia chilena",
            descripcion_corta="Poesia",
            autor=cls.autor_mistral,
            genero=cls.genero_poesia,
        )
        cls.book = Libro.objects.create(
            slug="don-quijote-edicion-alpha",
            sku="LIB-001",
            descripcion="Libro de prueba principal",
            descripcion_corta="Quijote",
            precio=Decimal("12990"),
            precio_referencia=Decimal("14990"),
            moneda="CLP",
            stock=25,
            gestionar_stock=True,
            activo=True,
            destacado=True,
            obra=cls.obra_quijote,
            editorial=cls.editorial_alpha,
            tipo_tapa="DURA",
            cantidad_paginas=860,
            isbn="9780000000001",
            idioma="es",
            anio_publicacion=2024,
        )
        cls.secondary_book = Libro.objects.create(
            slug="desolacion-edicion-beta",
            sku="LIB-002",
            descripcion="Libro de prueba secundario",
            descripcion_corta="Desolacion",
            precio=Decimal("9990"),
            precio_referencia=Decimal("11990"),
            moneda="CLP",
            stock=18,
            gestionar_stock=True,
            activo=True,
            destacado=False,
            obra=cls.obra_desolacion,
            editorial=cls.editorial_beta,
            tipo_tapa="BLANDA",
            cantidad_paginas=240,
            isbn="9780000000002",
            idioma="es",
            anio_publicacion=2023,
        )

        ShippingMethod.objects.create(name="Estandar", price=2990, region="RM", active=True)
        ShippingMethod.objects.create(name="Express", price=4990, region="RM", active=True)
        DiscountCoupon.objects.create(
            code="PROMO10",
            type="percent",
            value=Decimal("10"),
            active=True,
        )

    def _login(self, email, password):
        csrf_token = self._get_csrf_token()
        response = self.client.post(
            "/auth/jwt/create/",
            {"email": email, "password": password},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.data["access"]

    def _get_csrf_token(self, client=None):
        client = client or self.client
        response = client.get("/auth/csrf/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("csrftoken", response.cookies)
        self.assertTrue(response.data["csrfToken"])
        return response.data["csrfToken"]

    def _auth(self, user):
        return {"HTTP_AUTHORIZATION": f"Bearer {self._login(user.email, self.password)}"}

    def _count(self, payload):
        if isinstance(payload, dict) and "count" in payload:
            return payload["count"]
        return len(payload)

    def _results(self, payload):
        if isinstance(payload, dict) and "results" in payload:
            return payload["results"]
        return payload

    def _create_catalog_graph(self, admin_auth, suffix):
        response = self.client.post(
            "/productos/autores/",
            {"nombre": f"Autor {suffix}", "slug": f"autor-{suffix}", "biografia": f"Bio {suffix}"},
            format="json",
            **admin_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        author_id = response.data["id"]

        response = self.client.post(
            "/productos/generos/",
            {"nombre": f"Genero {suffix}", "slug": f"genero-{suffix}", "descripcion": f"Desc {suffix}"},
            format="json",
            **admin_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        genre_id = response.data["id"]

        response = self.client.post(
            "/productos/editoriales/",
            {
                "nombre": f"Editorial {suffix}",
                "slug": f"editorial-{suffix}",
                "descripcion": f"Editorial {suffix}",
                "sitio_web": f"https://{suffix}.example.com",
            },
            format="json",
            **admin_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        publisher_id = response.data["id"]

        response = self.client.post(
            "/productos/obras/",
            {
                "titulo": f"Obra {suffix}",
                "slug": f"obra-{suffix}",
                "descripcion": f"Obra {suffix}",
                "descripcion_corta": f"Corta {suffix}",
                "autor_id": author_id,
                "genero_id": genre_id,
            },
            format="json",
            **admin_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        work_id = response.data["id"]

        response = self.client.post(
            "/productos/libros/",
            {
                "slug": f"libro-{suffix}",
                "sku": f"LIB-{suffix.upper()}",
                "descripcion": f"Libro {suffix}",
                "descripcion_corta": f"Corto {suffix}",
                "precio": "15500",
                "precio_referencia": "17500",
                "moneda": "CLP",
                "stock": 20,
                "gestionar_stock": True,
                "activo": True,
                "destacado": False,
                "obra_id": work_id,
                "editorial_id": publisher_id,
                "tipo_tapa": "DURA",
                "cantidad_paginas": 320,
                "isbn": f"9781234567{suffix[-3:]}",
                "idioma": "es",
                "anio_publicacion": 2025,
            },
            format="json",
            **admin_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return {
            "author_id": author_id,
            "genre_id": genre_id,
            "publisher_id": publisher_id,
            "work_id": work_id,
            "book_id": response.data["id"],
        }

    def _create_order_for_user(self, user):
        auth = self._auth(user)
        guest_token = f"guest-{user.id}"

        response = self.client.post(
            "/checkout/carts/resolve/",
            {"guest_token": guest_token, "currency": "CLP"},
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_id = response.data["id"]

        response = self.client.post(
            f"/checkout/carts/{cart_id}/add-item/",
            {"book_id": self.book.id, "quantity": 1},
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(f"/checkout/carts/{cart_id}/convert/", format="json", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        order = Order.objects.filter(user=user).order_by("-created_at").first()
        self.assertIsNotNone(order)
        return order

    def test_auth_and_user_endpoints(self):
        self.assertEqual(self.comuna_santiago.county_code, "SANT")
        self.assertEqual(self.comuna_providencia.county_code, "PROV")

        register_payload = {
            "email": "nuevo.auth@test.com",
            "nombre": "Nuevo",
            "apellido": "Usuario",
            "telefono": "+56911110004",
            "direccion_entrega": "Dir test",
            "region_id": self.region_metropolitana.id,
            "comuna_id": self.comuna_santiago.id,
            "password": self.password,
            "re_password": self.password,
        }
        response = self.client.post("/auth/users/", register_payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        csrf_token = self._get_csrf_token()
        response = self.client.post(
            "/auth/jwt/create/",
            {"email": register_payload["email"], "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        access = response.data["access"]
        self.assertNotIn("refresh", response.data)
        self.assertIn("refresh_token", response.cookies)
        refresh_cookie = response.cookies["refresh_token"].value

        response = self.client.post("/auth/jwt/refresh/", format="json", HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)

        response = self.client.post("/auth/jwt/logout/", format="json", HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        self.client.cookies["refresh_token"] = refresh_cookie
        csrf_token = self._get_csrf_token()
        response = self.client.post("/auth/jwt/refresh/", format="json", HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.post("/auth/jwt/verify/", {"token": access}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        auth = {"HTTP_AUTHORIZATION": f"Bearer {access}"}
        response = self.client.get("/auth/users/me/", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        if response.data.get("region") is not None:
            self.assertEqual(response.data["region"]["id"], self.region_metropolitana.id)
        if response.data.get("comuna") is not None:
            self.assertEqual(response.data["comuna"]["id"], self.comuna_santiago.id)

        response = self.client.patch(
            "/auth/users/me/",
            {
                "nombre": "Nuevo2",
                "direccion_entrega": "Dir nueva",
                "region_id": self.region_valparaiso.id,
                "comuna_id": self.comuna_valparaiso.id,
            },
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["region"]["id"], self.region_valparaiso.id)
        self.assertEqual(response.data["comuna"]["id"], self.comuna_valparaiso.id)

        response = self.client.get("/users/regiones/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._count(response.data), 2)

        response = self.client.get(f"/users/comunas/?region_id={self.region_metropolitana.id}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._count(response.data), 2)

        response = self.client.post(
            "/auth/users/set_password/",
            {
                "current_password": self.password,
                "new_password": "Passw0rd-Endpoint-2",
                "re_new_password": "Passw0rd-Endpoint-2",
            },
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        response = self.client.get("/users/usuarios/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.get("/users/usuarios/", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._count(response.data), 1)
        listed_user = self._results(response.data)[0]
        self.assertEqual(str(listed_user["email"]), register_payload["email"])

        user_id = get_user_model().objects.get(email=register_payload["email"]).id

        response = self.client.get(f"/users/usuarios/{user_id}/", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["region"]["id"], self.region_valparaiso.id)
        self.assertEqual(response.data["comuna"]["id"], self.comuna_valparaiso.id)

        response = self.client.patch(
            f"/users/usuarios/{user_id}/",
            {"nombre": "Ana Final"},
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["nombre"], "Ana Final")

        response = self.client.get(f"/users/usuarios/{self.customer.id}/", **auth)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        response = self.client.get("/users/superusuarios/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        admin_auth = self._auth(self.admin)
        response = self.client.get("/users/superusuarios/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_cookie_auth_endpoints_require_csrf(self):
        strict_client = APIClient(enforce_csrf_checks=True)

        response = strict_client.post(
            "/auth/jwt/create/",
            {"email": self.customer.email, "password": self.password},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        csrf_token = self._get_csrf_token(strict_client)
        response = strict_client.post(
            "/auth/jwt/create/",
            {"email": self.customer.email, "password": self.password},
            format="json",
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = strict_client.post("/auth/jwt/refresh/", format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = strict_client.post("/auth/jwt/refresh/", format="json", HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_product_endpoints_create_related_objects_and_filters(self):
        response = self.client.get("/productos/autores/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(self._count(response.data), 2)

        response = self.client.get("/productos/generos/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(self._count(response.data), 2)

        response = self.client.get("/productos/editoriales/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(self._count(response.data), 2)

        response = self.client.get("/productos/obras/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(self._count(response.data), 2)

        response = self.client.get("/productos/libros/?titulo=Don%20Quijote&autor=Cervantes&editorial=Alpha&genero=Novela")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._count(response.data), 1)

        response = self.client.get("/catalog/books/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self._count(response.data), 2)
        self.assertEqual(len(self._results(response.data)), 2)

        response = self.client.get("/catalog/works/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(self._count(response.data), 2)

        response = self.client.get(f"/productos/libros/{self.book.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["obra"]["titulo"], "Don Quijote")

        admin_auth = self._auth(self.admin)
        created = self._create_catalog_graph(admin_auth, "nuevo")

        response = self.client.patch(
            f"/productos/libros/{created['book_id']}/",
            {"stock": 30, "destacado": True},
            format="json",
            **admin_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(f"/productos/libros/{created['book_id']}/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_checkout_inventory_orders_shipping_payments_and_sales_endpoints(self):
        auth = self._auth(self.customer)
        guest_token = "guest-checkout-flow"

        response = self.client.post(
            "/checkout/carts/resolve/",
            {"guest_token": guest_token, "currency": "CLP"},
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        cart_id = response.data["id"]

        response = self.client.get("/checkout/carts/current/", HTTP_X_GUEST_TOKEN=guest_token, **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/checkout/carts/current/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.post(
            f"/checkout/carts/{cart_id}/add-item/",
            {"book_id": self.book.id, "quantity": 2},
            format="json",
            HTTP_IDEMPOTENCY_KEY="add-book-1",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"][0]["book_id"], self.book.id)
        item_id = response.data["items"][0]["id"]

        response = self.client.patch(
            f"/checkout/carts/{cart_id}/items/{item_id}/",
            {"quantity": 3},
            format="json",
            HTTP_IDEMPOTENCY_KEY="upd-book-1",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            f"/checkout/carts/{cart_id}/apply-discount/",
            {"code": "PROMO10"},
            format="json",
            HTTP_IDEMPOTENCY_KEY="discount-1",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(f"/checkout/carts/{cart_id}/recalculate/", format="json", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.delete(
            f"/checkout/carts/{cart_id}/items/{item_id}/",
            HTTP_IDEMPOTENCY_KEY="delete-1",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            f"/checkout/carts/{cart_id}/add-item/",
            {"book_id": self.secondary_book.id, "quantity": 1},
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(f"/checkout/carts/{cart_id}/convert/", format="json", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        order = Order.objects.filter(user=self.customer).order_by("-created_at").first()
        self.assertIsNotNone(order)
        admin_auth = self._auth(self.admin)

        response = self.client.get("/inventory/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f"/inventory/{self.book.id}/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(
            f"/inventory/{self.book.id}/",
            {"stock": 35, "reserved_stock": 0},
            format="json",
            **admin_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/inventory/admin/monitor/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/orders/me/", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f"/orders/{order.id}/", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/orders/admin/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(
            f"/orders/{order.id}/admin/status/",
            {"status": "processing"},
            format="json",
            **admin_auth,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/shipping/methods/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            "/shipping/address/",
            {
                "address": "Av Test 123",
                "city": "Santiago",
                "region": "RM",
                "country": "Chile",
                "postal_code": "8320000",
            },
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.get("/shipping/address/", **auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.post(
            "/payments/create-intent/",
            {"order_id": str(order.id), "provider": "mockpay"},
            format="json",
            **auth,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        provider_reference = response.data["provider_reference"]

        response = self.client.post(
            "/payments/webhook/",
            {"provider_reference": provider_reference, "status": "paid"},
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        order.sale.refresh_from_db()
        self.assertEqual(order.sale.status, Venta.Status.COMPLETED)

        response = self.client.post(
            "/payments/webhook/",
            {"provider_reference": provider_reference, "status": "refunded"},
            format="json",
            HTTP_X_WEBHOOK_SECRET="test-webhook-secret",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        order.sale.refresh_from_db()
        self.assertEqual(order.sale.status, Venta.Status.REFUNDED)

        webpay_payment = Payment.objects.create(
            order=order,
            provider="webpay",
            status=Payment.Status.PENDING,
            amount=order.total_amount,
            currency=order.currency,
            provider_reference="token-test-webpay",
        )

        with patch("payments.api.commit_webpay_transaction") as mocked_commit:
            mocked_commit.return_value = (webpay_payment, {"status": "AUTHORIZED", "response_code": 0})
            response = self.client.post("/payments/webpay/commit/", {"token_ws": "token-test-webpay"}, format="json")
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with patch("payments.api.webpay_transaction_status") as mocked_status:
            mocked_status.return_value = {"status": "AUTHORIZED", "response_code": 0}
            response = self.client.get("/payments/webpay/status/?token_ws=token-test-webpay", **auth)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        with patch("payments.api.webpay_refund") as mocked_refund:
            mocked_refund.return_value = (webpay_payment, {"type": "NULLIFIED", "balance": 0})
            response = self.client.post(
                "/payments/webpay/refund/",
                {"token_ws": "token-test-webpay", "amount": str(order.total_amount)},
                format="json",
                **admin_auth,
            )
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/ventas/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        venta_id = self._results(response.data)[0]["id"]

        response = self.client.get(f"/ventas/{venta_id}/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get("/ventas/stats/summary/", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["orders_count"], 0)

        response = self.client.get("/ventas/stats/by-date/?group_by=day", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        response = self.client.get("/ventas/stats/by-book/?limit=10", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

        response = self.client.get("/ventas/stats/summary/?status=refunded", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["orders_count"], 1)

        response = self.client.get("/ventas/stats/by-date/?group_by=year", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = self.client.get("/ventas/stats/by-book/?limit=0", **admin_auth)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
