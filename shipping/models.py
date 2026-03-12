from django.conf import settings
from django.db import models


class ShippingMethod(models.Model):
    name = models.CharField(max_length=120)
    price = models.DecimalField(max_digits=12, decimal_places=0)
    region = models.CharField(max_length=120)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)


class CustomerAddress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="addresses", on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=120)
    region = models.CharField(max_length=120)
    country = models.CharField(max_length=120)
    postal_code = models.CharField(max_length=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)
