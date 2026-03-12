from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import Venta
from .serializers import VentaSerializer
from .services import (
    get_sales_by_book,
    get_sales_by_date,
    get_sales_summary,
    parse_date_filters,
)


class VentaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Venta.objects.prefetch_related("items").all()
    serializer_class = VentaSerializer
    permission_classes = [IsAdminUser]
    filterset_fields = ("status", "currency")
    ordering_fields = ("sold_at", "total_amount", "total_quantity", "created_at")
    ordering = ("-sold_at",)

    def _extract_dates(self):
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        try:
            return parse_date_filters(date_from, date_to)
        except ValueError as exc:
            raise ValidationError({"detail": f"Formato de fecha invalido: {exc}"})

    @action(detail=False, methods=["get"], url_path="stats/summary")
    def stats_summary(self, request):
        date_from, date_to = self._extract_dates()
        data = get_sales_summary(date_from=date_from, date_to=date_to)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="stats/by-date")
    def stats_by_date(self, request):
        date_from, date_to = self._extract_dates()
        group_by = request.query_params.get("group_by", "day")
        if group_by not in {"day", "month"}:
            group_by = "day"
        data = get_sales_by_date(date_from=date_from, date_to=date_to, group_by=group_by)
        return Response(data)

    @action(detail=False, methods=["get"], url_path="stats/by-book")
    def stats_by_book(self, request):
        date_from, date_to = self._extract_dates()
        try:
            limit = int(request.query_params.get("limit", 20))
        except ValueError:
            raise ValidationError({"detail": "limit debe ser un entero."})
        data = get_sales_by_book(date_from=date_from, date_to=date_to, limit=limit)
        return Response(data)
