from django.contrib import admin

from .models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "sale", "user", "status", "total_amount", "created_at")
    list_filter = ("status", "currency", "created_at")
    search_fields = ("id", "sale__id", "user__email")
