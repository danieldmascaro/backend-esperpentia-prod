from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from productos.models import Autor, Editorial, Genero, Libro, Obra


class InventorySecurityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin = user_model.objects.create_superuser(
            email="admin.inventory@test.com",
            nombre="Admin",
            apellido="Inventory",
            telefono="+56925000001",
            password="AdminPass123!",
        )
        cls.user = user_model.objects.create_user(
            email="user.inventory@test.com",
            nombre="User",
            apellido="Inventory",
            telefono="+56925000002",
            password="UserPass123!",
        )

        author = Autor.objects.create(nombre="Autor Inventario", slug="autor-inventario")
        genre = Genero.objects.create(nombre="Genero Inventario", slug="genero-inventario")
        publisher = Editorial.objects.create(nombre="Editorial Inventario", slug="editorial-inventario")
        work = Obra.objects.create(
            titulo="Obra Inventario",
            slug="obra-inventario",
            autor=author,
            genero=genre,
        )
        cls.book = Libro.objects.create(
            obra=work,
            editorial=publisher,
            slug="libro-inventario",
            sku="INV-001",
            descripcion="",
            descripcion_corta="",
            precio=Decimal("12990"),
            stock=10,
            tipo_tapa=Libro.TipoTapa.BLANDA,
            cantidad_paginas=100,
            isbn="9780000000099",
            idioma="es",
            activo=True,
        )

    def test_inventory_endpoints_require_admin(self):
        response = self.client.get("/inventory/")
        self.assertIn(response.status_code, {status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN})

        self.client.force_authenticate(user=self.user)
        response = self.client.get("/inventory/")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=self.admin)
        response = self.client.get("/inventory/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.get(f"/inventory/{self.book.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
