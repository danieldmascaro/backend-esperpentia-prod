from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from .models import Comuna, Region, Usuario
from .serializers import ComunaSerializer, RegionSerializer, SuperUsuarioSerializer, UsuarioSerializer


class RegionViewSet(ReadOnlyModelViewSet):
    serializer_class = RegionSerializer
    permission_classes = [AllowAny]
    queryset = Region.objects.all().order_by("nombre")


class ComunaViewSet(ReadOnlyModelViewSet):
    serializer_class = ComunaSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Comuna.objects.select_related("region").order_by("nombre")
        region_id = self.request.query_params.get("region_id")
        if region_id:
            queryset = queryset.filter(region_id=region_id)
        return queryset


class UsuarioViewSet(ModelViewSet):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        # Each authenticated user can only access their own profile in this viewset.
        return (
            Usuario.objects.select_related("region", "comuna", "comuna__region")
            .filter(id=self.request.user.id, is_superuser=False)
            .order_by("id")
        )

    def get_object(self):
        requested_pk = str(self.kwargs.get(self.lookup_field, ""))
        current_user_pk = str(self.request.user.pk)
        if requested_pk and requested_pk != current_user_pk:
            raise AuthenticationFailed("Unauthorized.")
        return super().get_object()


class SuperUsuarioViewSet(ModelViewSet):
    serializer_class = SuperUsuarioSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Usuario.objects.select_related("region", "comuna", "comuna__region").filter(is_superuser=True).order_by("id")
