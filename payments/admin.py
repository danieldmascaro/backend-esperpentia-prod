from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "provider", "status", "amount", "currency", "created_at")
    list_filter = ("status", "provider", "currency", "created_at")
    search_fields = ("id", "provider_reference", "order__id")
