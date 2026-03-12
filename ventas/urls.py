from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import VentaViewSet

router = DefaultRouter()
router.register(r"", VentaViewSet, basename="ventas")

urlpatterns = [
    path("", include(router.urls)),
]
