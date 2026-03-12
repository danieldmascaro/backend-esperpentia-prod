from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from djoser.conf import settings as djoser_settings
from djoser.signals import user_registered

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
    permission_classes = [AllowAny]

    def get_queryset(self):
        return Usuario.objects.select_related("region", "comuna", "comuna__region").filter(is_superuser=False).order_by("id")

    def perform_create(self, serializer):
        should_send_activation = djoser_settings.SEND_ACTIVATION_EMAIL
        user = serializer.save(is_active=not should_send_activation)

        context = {"user": user}
        if should_send_activation:
            djoser_settings.EMAIL.activation(self.request, context).send([user.email])
        elif djoser_settings.SEND_CONFIRMATION_EMAIL:
            djoser_settings.EMAIL.confirmation(self.request, context).send([user.email])

        user_registered.send(sender=self.__class__, user=user, request=self.request)


class SuperUsuarioViewSet(ModelViewSet):
    serializer_class = SuperUsuarioSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Usuario.objects.select_related("region", "comuna", "comuna__region").filter(is_superuser=True).order_by("id")
