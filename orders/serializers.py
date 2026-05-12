from rest_framework import serializers

from .models import Order


class OrderSerializer(serializers.ModelSerializer):
    sale_id = serializers.SerializerMethodField()

    def get_sale_id(self, obj):
        return str(obj.sale_id) if obj.sale_id else None

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
