from rest_framework import serializers

from .models import CustomerAddress, ShippingMethod


class ShippingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingMethod
        fields = ("id", "name", "price", "region", "active")


class CustomerAddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAddress
        fields = (
            "id",
            "address",
            "city",
            "region",
            "country",
            "postal_code",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("created_at", "updated_at")
