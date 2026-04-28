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
    code = serializers.CharField(required=True, allow_blank=False, max_length=64)


class ConvertCartSerializer(serializers.Serializer):
    contact_first_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    contact_last_name = serializers.CharField(required=False, allow_blank=True, max_length=120)
    contact_email = serializers.EmailField(required=False, allow_blank=True, max_length=254)
    contact_phone = serializers.CharField(required=False, allow_blank=True, max_length=32)
    shipping_address = serializers.CharField(required=False, allow_blank=True, max_length=255)
    shipping_city = serializers.CharField(required=False, allow_blank=True, max_length=120)
    shipping_region = serializers.CharField(required=False, allow_blank=True, max_length=120)
    shipping_postal_code = serializers.CharField(required=False, allow_blank=True, max_length=32)
    shipping_country = serializers.CharField(required=False, allow_blank=True, max_length=80)
