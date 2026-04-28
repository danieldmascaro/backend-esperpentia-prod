from django.contrib import admin

from despachos.models import Despacho
from ventas.models import VentaItem


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


@admin.register(Despacho)
class DespachoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "despachado",
        "contact_first_name",
        "contact_last_name",
        "contact_email",
        "contact_phone",
        "shipping_address",
        "shipping_city",
        "shipping_region",
        "shipping_postal_code",
        "sold_at",
    )
    list_editable = ("despachado",)
    list_filter = ("despachado", "sold_at", "status")
    search_fields = (
        "id",
        "contact_first_name",
        "contact_last_name",
        "contact_email",
        "contact_phone",
        "shipping_address",
        "shipping_city",
        "shipping_region",
        "shipping_postal_code",
        "user__email",
    )
    actions = ("marcar_como_despachado", "marcar_como_no_despachado")
    readonly_fields = (
        "id",
        "cart_id",
        "user",
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
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("Estado de despacho", {"fields": ("despachado", "status", "sold_at")}),
        (
            "Contacto",
            {"fields": ("contact_first_name", "contact_last_name", "contact_email", "contact_phone")},
        ),
        (
            "Direccion de entrega",
            {
                "fields": (
                    "shipping_address",
                    "shipping_city",
                    "shipping_region",
                    "shipping_postal_code",
                    "shipping_country",
                )
            },
        ),
        (
            "Totales",
            {"fields": ("currency", "subtotal_amount", "discount_amount", "tax_amount", "total_amount")},
        ),
        (
            "Trazabilidad",
            {"fields": ("id", "cart_id", "user", "guest_token", "items_count", "total_quantity", "created_at", "updated_at")},
        ),
    )
    inlines = [VentaItemInline]

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("despachado", "-sold_at")

    @admin.action(description="Marcar seleccionadas como despachadas")
    def marcar_como_despachado(self, request, queryset):
        queryset.update(despachado=True)

    @admin.action(description="Marcar seleccionadas como no despachadas")
    def marcar_como_no_despachado(self, request, queryset):
        queryset.update(despachado=False)

