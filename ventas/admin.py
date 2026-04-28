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
        "despachado",
        "status",
        "contact_first_name",
        "contact_last_name",
        "contact_email",
        "contact_phone",
        "currency",
        "total_amount",
        "items_count",
        "total_quantity",
        "sold_at",
    )
    list_editable = ("despachado",)
    search_fields = (
        "id",
        "cart_id",
        "user__email",
        "guest_token",
        "contact_first_name",
        "contact_last_name",
        "contact_email",
        "contact_phone",
        "shipping_address",
    )
    list_filter = ("despachado", "status", "currency", "sold_at")
    actions = ("marcar_como_despachado", "marcar_como_no_despachado")
    readonly_fields = ("id", "cart_id", "guest_token", "sold_at", "created_at", "updated_at")
    fieldsets = (
        (
            "Estado de despacho",
            {"fields": ("despachado", "status", "sold_at")},
        ),
        (
            "Contacto",
            {
                "fields": (
                    "contact_first_name",
                    "contact_last_name",
                    "contact_email",
                    "contact_phone",
                )
            },
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
            "Detalle venta",
            {
                "fields": (
                    "id",
                    "cart_id",
                    "user",
                    "guest_token",
                    "currency",
                    "subtotal_amount",
                    "discount_amount",
                    "tax_amount",
                    "total_amount",
                    "items_count",
                    "total_quantity",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
    inlines = [VentaItemInline]

    @admin.action(description="Marcar seleccionadas como despachadas")
    def marcar_como_despachado(self, request, queryset):
        queryset.update(despachado=True)

    @admin.action(description="Marcar seleccionadas como no despachadas")
    def marcar_como_no_despachado(self, request, queryset):
        queryset.update(despachado=False)
