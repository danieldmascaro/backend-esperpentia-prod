from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


def default_cart_expiry():
    return timezone.now() + timedelta(days=7)


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        CONVERTED = "converted", "Converted"
        EXPIRED = "expired", "Expired"
        ABANDONED = "abandoned", "Abandoned"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="carts",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    guest_token = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    currency = models.CharField(max_length=3, default="CLP")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE, db_index=True)
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    expires_at = models.DateTimeField(default=default_cart_expiry, db_index=True)
    converted_at = models.DateTimeField(null=True, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status="active"),
                name="unique_active_cart_per_user",
            ),
            models.UniqueConstraint(
                fields=["guest_token"],
                condition=Q(status="active"),
                name="unique_active_cart_per_guest_token",
            ),
        ]

    def __str__(self):
        owner = self.user.email if self.user else self.guest_token
        return f"Cart<{self.id}>:{owner}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name="items", on_delete=models.CASCADE)
    book = models.ForeignKey("productos.Libro", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    unit_price_snapshot = models.DecimalField(max_digits=12, decimal_places=0)
    subtotal = models.DecimalField(max_digits=12, decimal_places=0)
    metadata_snapshot = models.JSONField(default=dict, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("cart", "book")
        ordering = ("id",)

    def __str__(self):
        return f"{self.cart_id}:{self.book_id} x {self.quantity}"


class CartDiscount(models.Model):
    class Type(models.TextChoices):
        COUPON = "coupon", "Coupon"
        PERCENT = "percent", "Percent"
        FIXED = "fixed", "Fixed"
        QTY_PROMO = "qty_promo", "Quantity promo"

    cart = models.ForeignKey(Cart, related_name="discounts", on_delete=models.CASCADE)
    code = models.CharField(max_length=64, blank=True)
    type = models.CharField(max_length=20, choices=Type.choices)
    value = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    amount = models.DecimalField(max_digits=12, decimal_places=0, default=Decimal("0"))
    description = models.CharField(max_length=255, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)


class CartTaxLine(models.Model):
    cart = models.ForeignKey(Cart, related_name="tax_lines", on_delete=models.CASCADE)
    name = models.CharField(max_length=120)
    rate = models.DecimalField(max_digits=6, decimal_places=4)
    taxable_base = models.DecimalField(max_digits=12, decimal_places=0)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("name",)
        unique_together = ("cart", "name")


class CartOperationLog(models.Model):
    cart = models.ForeignKey(Cart, related_name="operation_logs", on_delete=models.CASCADE)
    operation = models.CharField(max_length=64)
    idempotency_key = models.CharField(max_length=128)
    response_payload = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(default=default_cart_expiry)

    class Meta:
        ordering = ("-created_at",)
        unique_together = ("cart", "operation", "idempotency_key")
