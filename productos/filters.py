import django_filters

from .models import Libro


class LibroFilter(django_filters.FilterSet):
    titulo = django_filters.CharFilter(field_name="obra__titulo", lookup_expr="icontains")
    autor = django_filters.CharFilter(field_name="obra__autor__nombre", lookup_expr="icontains")
    editorial = django_filters.CharFilter(field_name="editorial__nombre", lookup_expr="icontains")
    genero = django_filters.CharFilter(field_name="obra__genero__nombre", lookup_expr="icontains")

    class Meta:
        model = Libro
        fields = ("activo", "destacado", "moneda", "tipo_tapa", "titulo", "autor", "editorial", "genero")
