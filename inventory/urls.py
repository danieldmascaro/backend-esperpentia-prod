from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import InventoryViewSet

router = DefaultRouter()
router.register(r"", InventoryViewSet, basename="inventory")

urlpatterns = [
    path("", include(router.urls)),
]
