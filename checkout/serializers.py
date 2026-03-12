from rest_framework import serializers

from .models import Cart, CartDiscount, CartItem, CartTaxLine


class CartItemSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(source="book.id", read_only=True)

    class Meta:
        model = CartItem
        fields = (
            "id",
            "book_id",
            "quantity",
            "unit_price_snapshot",
            "subtotal",
            "metadata_snapshot",
        )


class CartDiscountSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartDiscount
        fields = ("id", "code", "type", "value", "amount", "description", "metadata")


class CartTaxLineSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartTaxLine
        fields = ("id", "name", "rate", "taxable_base", "amount")


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    discounts = CartDiscountSerializer(many=True, read_only=True)
    tax_lines = CartTaxLineSerializer(many=True, read_only=True)

    class Meta:
        model = Cart
        fields = (
            "id",
            "guest_token",
            "status",
            "currency",
            "subtotal_amount",
            "discount_amount",
            "tax_amount",
            "total_amount",
            "expires_at",
            "items",
            "discounts",
            "tax_lines",
            "version",
            "created_at",
            "updated_at",
        )


class ResolveCartSerializer(serializers.Serializer):
    guest_token = serializers.CharField(required=False, allow_blank=False, max_length=64)
    currency = serializers.CharField(required=False, default="CLP", max_length=3)


class AddCartItemSerializer(serializers.Serializer):
    book_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class UpdateCartItemSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class ApplyDiscountSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=CartDiscount.Type.choices)
    value = serializers.DecimalField(max_digits=12, decimal_places=0, required=False, default="0")
    code = serializers.CharField(required=False, allow_blank=True, max_length=64)
    metadata = serializers.DictField(required=False, default=dict)
