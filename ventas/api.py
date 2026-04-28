from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

from .models import Venta
from .serializers import VentaDispatchUpdateSerializer, VentaSerializer
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
    filterset_fields = ("status", "currency", "despachado")
    ordering_fields = ("sold_at", "total_amount", "total_quantity", "created_at")
    ordering = ("-sold_at",)

    def _extract_dates(self):
        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")
        try:
            return parse_date_filters(date_from, date_to)
        except ValueError as exc:
            raise ValidationError({"detail": f"Formato de fecha invalido: {exc}"})

    def _extract_status(self):
        status_value = self.request.query_params.get("status", Venta.Status.COMPLETED)
        valid_statuses = {choice for choice, _ in Venta.Status.choices}
        if status_value not in valid_statuses:
            raise ValidationError({"detail": "status invalido."})
        return status_value

    def _extract_currency(self):
        currency = self.request.query_params.get("currency")
        if not currency:
            return None
        if len(currency) != 3:
            raise ValidationError({"detail": "currency debe tener 3 caracteres."})
        return currency.upper()

    @action(detail=False, methods=["get"], url_path="stats/summary")
    def stats_summary(self, request):
        date_from, date_to = self._extract_dates()
        data = get_sales_summary(
            date_from=date_from,
            date_to=date_to,
            status_value=self._extract_status(),
            currency=self._extract_currency(),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="stats/by-date")
    def stats_by_date(self, request):
        date_from, date_to = self._extract_dates()
        group_by = request.query_params.get("group_by", "day")
        if group_by not in {"day", "month"}:
            raise ValidationError({"detail": "group_by debe ser 'day' o 'month'."})
        data = get_sales_by_date(
            date_from=date_from,
            date_to=date_to,
            group_by=group_by,
            status_value=self._extract_status(),
            currency=self._extract_currency(),
        )
        return Response(data)

    @action(detail=False, methods=["get"], url_path="stats/by-book")
    def stats_by_book(self, request):
        date_from, date_to = self._extract_dates()
        try:
            limit = int(request.query_params.get("limit", 20))
        except ValueError:
            raise ValidationError({"detail": "limit debe ser un entero."})
        if limit <= 0 or limit > 100:
            raise ValidationError({"detail": "limit debe estar entre 1 y 100."})
        data = get_sales_by_book(
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            status_value=self._extract_status(),
            currency=self._extract_currency(),
        )
        return Response(data)

    @action(detail=True, methods=["patch"], url_path="dispatch-status")
    def dispatch_status(self, request, pk=None):
        venta = self.get_object()
        serializer = VentaDispatchUpdateSerializer(instance=venta, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(VentaSerializer(venta).data)
