from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models


class Venta(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        REFUNDED = "refunded", "Refunded"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    cart_id = models.UUIDField(unique=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="ventas",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    guest_token = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED, db_index=True)
    despachado = models.BooleanField(default=False, db_index=True)
    contact_first_name = models.CharField(max_length=120, blank=True, default="")
    contact_last_name = models.CharField(max_length=120, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=32, blank=True, default="")
    shipping_address = models.CharField(max_length=255, blank=True, default="")
    shipping_city = models.CharField(max_length=120, blank=True, default="")
    shipping_region = models.CharField(max_length=120, blank=True, default="")
    shipping_postal_code = models.CharField(max_length=32, blank=True, default="")
    shipping_country = models.CharField(max_length=80, blank=True, default="Chile")
    currency = models.CharField(max_length=3, default="CLP")
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    items_count = models.PositiveIntegerField(default=0)
    total_quantity = models.PositiveIntegerField(default=0)
    sold_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-sold_at",)

    def __str__(self):
        return f"Venta<{self.id}> total={self.total_amount}"


class VentaItem(models.Model):
    venta = models.ForeignKey(Venta, related_name="items", on_delete=models.CASCADE)
    libro = models.ForeignKey("productos.Libro", on_delete=models.SET_NULL, null=True, blank=True)
    libro_nombre = models.CharField(max_length=255)
    autor_nombre = models.CharField(max_length=255, blank=True)
    editorial_nombre = models.CharField(max_length=255, blank=True)
    genero_nombre = models.CharField(max_length=120, blank=True)
    isbn = models.CharField(max_length=20, blank=True)
    idioma = models.CharField(max_length=60, blank=True)
    unit_price = models.DecimalField(max_digits=12, decimal_places=0)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=12, decimal_places=0)
    sold_at = models.DateTimeField(db_index=True)
    metadata_snapshot = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ("id",)


class VentaDespacho(Venta):
    class Meta:
        proxy = True
        verbose_name = "Despacho"
        verbose_name_plural = "Despachos"
