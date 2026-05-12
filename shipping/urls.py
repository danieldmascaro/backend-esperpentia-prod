from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import CustomerAddressViewSet, ShippingMethodViewSet, quote_rate_view, search_streets_view

router = DefaultRouter()
router.register(r"methods", ShippingMethodViewSet, basename="shipping-methods")
router.register(r"address", CustomerAddressViewSet, basename="shipping-address")

urlpatterns = [
    path("", include(router.urls)),
    path("streets/search/", search_streets_view, name="search-streets"),
    path("rates/quote/", quote_rate_view, name="quote-rates"),
]
