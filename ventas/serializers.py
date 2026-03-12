from rest_framework import serializers

from .models import Venta, VentaItem


class VentaItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = VentaItem
        fields = (
            "id",
            "libro_id",
            "libro_nombre",
            "autor_nombre",
            "editorial_nombre",
            "genero_nombre",
            "isbn",
            "idioma",
            "unit_price",
            "quantity",
            "subtotal",
            "sold_at",
        )


class VentaSerializer(serializers.ModelSerializer):
    items = VentaItemSerializer(many=True, read_only=True)

    class Meta:
        model = Venta
        fields = (
            "id",
            "cart_id",
            "user_id",
            "guest_token",
            "status",
            "currency",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "items_count",
            "total_quantity",
            "sold_at",
            "items",
        )
