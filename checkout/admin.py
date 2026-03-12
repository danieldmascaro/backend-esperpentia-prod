from django.contrib import admin

from .models import Cart, CartDiscount, CartItem, CartOperationLog, CartTaxLine


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


class CartDiscountInline(admin.TabularInline):
    model = CartDiscount
    extra = 0


class CartTaxLineInline(admin.TabularInline):
    model = CartTaxLine
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "guest_token",
        "status",
        "currency",
        "subtotal_amount",
        "discount_amount",
        "tax_amount",
        "total_amount",
        "expires_at",
    )
    search_fields = ("id", "guest_token", "user__email")
    list_filter = ("status", "currency")
    inlines = [CartItemInline, CartDiscountInline, CartTaxLineInline]


@admin.register(CartOperationLog)
class CartOperationLogAdmin(admin.ModelAdmin):
    list_display = ("cart", "operation", "idempotency_key", "created_at", "expires_at")
    search_fields = ("cart__id", "operation", "idempotency_key")
