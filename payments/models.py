import uuid

from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        AUTHORIZED = "authorized", "Authorized"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey("orders.Order", related_name="payments", on_delete=models.PROTECT)
    provider = models.CharField(max_length=60, default="mockpay")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    amount = models.DecimalField(max_digits=12, decimal_places=0)
    currency = models.CharField(max_length=3, default="CLP")
    provider_reference = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
