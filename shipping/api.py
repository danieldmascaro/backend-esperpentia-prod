from rest_framework import mixins, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated

from .models import CustomerAddress, ShippingMethod
from .serializers import CustomerAddressSerializer, ShippingMethodSerializer


class ShippingMethodViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ShippingMethodSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        return ShippingMethod.objects.filter(active=True)


class CustomerAddressViewSet(mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    serializer_class = CustomerAddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomerAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
