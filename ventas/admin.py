from django.contrib import admin

from .models import Venta, VentaItem


class VentaItemInline(admin.TabularInline):
    model = VentaItem
    extra = 0
    readonly_fields = (
        "libro",
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


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "status",
        "currency",
        "total_amount",
        "items_count",
        "total_quantity",
        "sold_at",
    )
    search_fields = ("id", "cart_id", "user__email", "guest_token")
    list_filter = ("status", "currency", "sold_at")
    inlines = [VentaItemInline]
