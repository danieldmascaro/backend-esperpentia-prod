from django.contrib import admin

from .models import CustomerAddress, ShippingMethod


@admin.register(ShippingMethod)
class ShippingMethodAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "region", "active")
    list_filter = ("active", "region")
    search_fields = ("name", "region")


@admin.register(CustomerAddress)
class CustomerAddressAdmin(admin.ModelAdmin):
    list_display = ("user", "address", "city", "region", "country", "postal_code")
    search_fields = ("user__email", "address", "city", "region", "country", "postal_code")
