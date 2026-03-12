from django.contrib import admin

from .models import InventoryItem


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("book", "stock", "reserved_stock", "updated_at")
    search_fields = ("book__nombre", "book__obra__autor__nombre", "book__editorial__nombre", "book__sku")
