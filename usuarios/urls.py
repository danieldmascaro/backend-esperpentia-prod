from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import ComunaViewSet, RegionViewSet, SuperUsuarioViewSet, UsuarioViewSet

router = DefaultRouter()
router.register(r"regiones", RegionViewSet, basename="regiones")
router.register(r"comunas", ComunaViewSet, basename="comunas")
router.register(r"usuarios", UsuarioViewSet, basename="usuarios")
router.register(r"superusuarios", SuperUsuarioViewSet, basename="superusuarios")

urlpatterns = [
    path("", include(router.urls)),
]
