from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from productos.models import Autor, Editorial, Genero, Libro, Obra
from ventas.models import Venta, VentaItem


class VentaRetentionTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email="ventas.user@test.com",
            nombre="Ventas",
            apellido="User",
            telefono="+56921000001",
            password="UserPass123!",
        )
        author = Autor.objects.create(nombre="Autor Venta", slug="autor-venta")
        genre = Genero.objects.create(nombre="Genero Venta", slug="genero-venta")
        publisher = Editorial.objects.create(nombre="Editorial Venta", slug="editorial-venta")
        work = Obra.objects.create(
            titulo="Obra Venta",
            slug="obra-venta",
            autor=author,
            genero=genre,
        )
        self.book = Libro.objects.create(
            obra=work,
            editorial=publisher,
            slug="libro-venta",
            sku="VEN-001",
            descripcion="",
            descripcion_corta="",
            precio=Decimal("12000"),
            stock=5,
            tipo_tapa=Libro.TipoTapa.BLANDA,
            cantidad_paginas=90,
            isbn="9780000000009",
            idioma="es",
            activo=True,
        )

    def test_deleting_book_keeps_sale_item_snapshot(self):
        venta = Venta.objects.create(
            cart_id=uuid4(),
            user=self.user,
            status=Venta.Status.COMPLETED,
            currency="CLP",
            subtotal_amount=Decimal("12000"),
            discount_amount=Decimal("0"),
            tax_amount=Decimal("2280"),
            total_amount=Decimal("14280"),
            items_count=1,
            total_quantity=1,
            sold_at=timezone.now(),
        )
        item = VentaItem.objects.create(
            venta=venta,
            libro=self.book,
            libro_nombre=self.book.nombre,
            autor_nombre=self.book.obra.autor.nombre,
            editorial_nombre=self.book.editorial.nombre,
            genero_nombre=self.book.obra.genero.nombre,
            isbn=self.book.isbn,
            idioma=self.book.idioma,
            unit_price=Decimal("12000"),
            quantity=1,
            subtotal=Decimal("12000"),
            sold_at=timezone.now(),
        )

        self.book.delete()
        item.refresh_from_db()
        self.assertIsNone(item.libro)
        self.assertEqual(item.libro_nombre, "Obra Venta")

    def test_sale_defaults_to_not_dispatched(self):
        venta = Venta.objects.create(
            cart_id=uuid4(),
            user=self.user,
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
        self.assertFalse(venta.despachado)
