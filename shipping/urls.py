from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import CustomerAddressViewSet, ShippingMethodViewSet

router = DefaultRouter()
router.register(r"methods", ShippingMethodViewSet, basename="shipping-methods")
router.register(r"address", CustomerAddressViewSet, basename="shipping-address")

urlpatterns = [
    path("", include(router.urls)),
]
