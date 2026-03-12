from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import AutorViewSet, EditorialViewSet, GeneroViewSet, LibroViewSet, ObraViewSet

router = DefaultRouter()
router.register(r"autores", AutorViewSet, basename="autores")
router.register(r"authors", AutorViewSet, basename="authors")
router.register(r"generos", GeneroViewSet, basename="generos")
router.register(r"genres", GeneroViewSet, basename="genres")
router.register(r"editoriales", EditorialViewSet, basename="editoriales")
router.register(r"publishers", EditorialViewSet, basename="publishers")
router.register(r"obras", ObraViewSet, basename="obras")
router.register(r"works", ObraViewSet, basename="works")
router.register(r"libros", LibroViewSet, basename="libros")
router.register(r"books", LibroViewSet, basename="books")

urlpatterns = [
    path("", include(router.urls)),
]
