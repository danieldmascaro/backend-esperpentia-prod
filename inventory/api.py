from django.shortcuts import get_object_or_404
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from config.pagination import StandardResultsSetPagination
from productos.models import Libro

from .models import InventoryItem
from .serializers import InventoryItemSerializer, InventoryUpdateSerializer
from .services import get_inventory_queryset, get_or_create_inventory_item, inventory_monitoring_snapshot


class InventoryViewSet(viewsets.GenericViewSet):
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        return [IsAdminUser()]

    def list(self, request):
        queryset = get_inventory_queryset()
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = InventoryItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = InventoryItemSerializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        book = get_object_or_404(Libro, pk=pk)
        item = get_or_create_inventory_item(book)
        item = InventoryItem.objects.select_related("book", "book__obra__autor", "book__obra__genero", "book__editorial").get(
            book=item.book
        )
        serializer = InventoryItemSerializer(item)
        return Response(serializer.data)

    def partial_update(self, request, pk=None):
        book = get_object_or_404(Libro, pk=pk)
        item = get_or_create_inventory_item(book)
        serializer = InventoryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            item = InventoryItem.objects.select_for_update().get(book=item.book)
            if "stock" in data:
                item.stock = data["stock"]
            if "reserved_stock" in data:
                item.reserved_stock = data["reserved_stock"]
            item.save(update_fields=["stock", "reserved_stock", "updated_at"])

        response_serializer = InventoryItemSerializer(item)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], url_path="admin/monitor")
    def monitoring(self, request):
        return Response(inventory_monitoring_snapshot())
