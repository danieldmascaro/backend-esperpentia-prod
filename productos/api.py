from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.viewsets import ModelViewSet

from .filters import LibroFilter
from .models import Autor, Editorial, Genero, Libro, Obra
from .serializers import (
    AutorSerializer,
    EditorialSerializer,
    GeneroSerializer,
    LibroSerializer,
    ObraSerializer,
)


class PublicReadAdminWriteViewSet(ModelViewSet):
    permission_classes = [AllowAny]

    def get_permissions(self):
        if self.request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            return [IsAdminUser()]
        return [AllowAny()]


class AutorViewSet(PublicReadAdminWriteViewSet):
    queryset = Autor.objects.all()
    serializer_class = AutorSerializer
    search_fields = ("nombre", "slug")
    ordering_fields = ("nombre", "creado_en")
    ordering = ("nombre",)


class GeneroViewSet(PublicReadAdminWriteViewSet):
    queryset = Genero.objects.all()
    serializer_class = GeneroSerializer
    search_fields = ("nombre", "slug")
    ordering_fields = ("nombre", "creado_en")
    ordering = ("nombre",)


class EditorialViewSet(PublicReadAdminWriteViewSet):
    queryset = Editorial.objects.all()
    serializer_class = EditorialSerializer
    search_fields = ("nombre", "slug")
    ordering_fields = ("nombre", "creado_en")
    ordering = ("nombre",)


class ObraViewSet(PublicReadAdminWriteViewSet):
    queryset = Obra.objects.select_related("autor", "genero").all()
    serializer_class = ObraSerializer
    filterset_fields = ("autor", "genero")
    search_fields = ("titulo", "slug", "autor__nombre", "genero__nombre")
    ordering_fields = ("titulo", "creado_en")
    ordering = ("titulo",)


class LibroViewSet(PublicReadAdminWriteViewSet):
    queryset = Libro.objects.select_related("obra__autor", "obra__genero", "editorial").all()
    serializer_class = LibroSerializer
    filterset_class = LibroFilter
    search_fields = (
        "nombre",
        "obra__titulo",
        "obra__autor__nombre",
        "editorial__nombre",
        "obra__genero__nombre",
        "sku",
        "slug",
        "isbn",
    )
    ordering_fields = ("creado_en", "precio", "stock", "nombre", "anio_publicacion")
    ordering = ("-creado_en",)
