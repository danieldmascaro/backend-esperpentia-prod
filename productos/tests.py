from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Autor, Editorial, Genero, Libro, Obra


class ProductosAdminCreationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_user = user_model.objects.create_superuser(
            email="admin-productos@test.com",
            nombre="Admin",
            apellido="Productos",
            password="AdminPass123!",
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_admin_can_create_author_genre_work_and_book(self):
        response = self.client.post(
            reverse("admin:productos_autor_add"),
            {"nombre": "Autor Admin", "slug": "", "biografia": "Bio admin", "_save": "Guardar"},
        )
        self.assertEqual(response.status_code, 302)
        autor = Autor.objects.get(nombre="Autor Admin")
        self.assertTrue(autor.slug.startswith("autor-admin"))

        response = self.client.post(
            reverse("admin:productos_genero_add"),
            {"nombre": "Genero Admin", "slug": "", "descripcion": "Genero admin", "_save": "Guardar"},
        )
        self.assertEqual(response.status_code, 302)
        genero = Genero.objects.get(nombre="Genero Admin")
        self.assertTrue(genero.slug.startswith("genero-admin"))

        response = self.client.post(
            reverse("admin:productos_editorial_add"),
            {
                "nombre": "Editorial Admin",
                "slug": "",
                "descripcion": "Editorial admin",
                "sitio_web": "https://editorial-admin.example.com",
                "_save": "Guardar",
            },
        )
        self.assertEqual(response.status_code, 302)
        editorial = Editorial.objects.get(nombre="Editorial Admin")
        self.assertTrue(editorial.slug.startswith("editorial-admin"))

        response = self.client.post(
            reverse("admin:productos_obra_add"),
            {
                "titulo": "Obra Admin",
                "slug": "",
                "autor": autor.id,
                "genero": genero.id,
                "descripcion_corta": "Obra corta",
                "descripcion": "Descripcion completa",
                "_save": "Guardar",
            },
        )
        self.assertEqual(response.status_code, 302)
        obra = Obra.objects.get(titulo="Obra Admin")
        self.assertTrue(obra.slug.startswith("obra-admin"))

        response = self.client.post(
            reverse("admin:productos_libro_add"),
            {
                "obra": obra.id,
                "editorial": editorial.id,
                "slug": "",
                "sku": "ADM-BOOK-001",
                "descripcion_corta": "Libro corto",
                "descripcion": "Libro completo",
                "tipo_tapa": Libro.TipoTapa.DURA,
                "cantidad_paginas": 210,
                "isbn": "9781111111111",
                "idioma": "es",
                "anio_publicacion": 2025,
                "precio": "12990",
                "precio_referencia": "13990",
                "moneda": "CLP",
                "stock": 20,
                "gestionar_stock": "on",
                "activo": "on",
                "_save": "Guardar",
            },
        )
        self.assertEqual(response.status_code, 302)
        libro = Libro.objects.get(sku="ADM-BOOK-001")
        self.assertEqual(libro.nombre, "Obra Admin")
        self.assertTrue(libro.slug.startswith("obra-admin"))
