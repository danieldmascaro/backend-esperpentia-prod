from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    sale_id = serializers.UUIDField(source="sale.id", read_only=True)

    class Meta:
        model = Order
        fields = (
            "id",
            "sale_id",
            "status",
            "currency",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "created_at",
            "updated_at",
        )


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
