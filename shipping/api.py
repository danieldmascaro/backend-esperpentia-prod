from rest_framework import mixins, status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import CustomerAddress, ShippingMethod
from .serializers import CustomerAddressSerializer, ShippingMethodSerializer
from .chilexpress import ChilexpressApiError, quote_chilexpress_rate, search_chilexpress_streets


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


@api_view(["POST"])
@permission_classes([AllowAny])
def search_streets_view(request):
    """Search for streets in a specific county using Chilexpress API."""
    try:
        county_name = request.data.get("countyName", "").strip()
        street_name = request.data.get("streetName", "").strip()
        limit = request.data.get("limit", 6)

        if not county_name or not street_name:
            return Response(
                {"error": "countyName y streetName son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = search_chilexpress_streets(
            county_name=county_name,
            street_name=street_name,
            limit=int(limit) if limit else 6,
            points_of_interest_enabled=request.data.get("pointsOfInterestEnabled", False),
            street_name_enabled=request.data.get("streetNameEnabled", True),
            road_type=request.data.get("roadType", 0),
        )

        return Response(
            {
                "streets": result.get("streets", []),
                "statusDescription": result.get("status_description"),
            }
        )
    except ChilexpressApiError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as exc:
        return Response(
            {"error": f"Error inesperado: {str(exc)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(["POST"])
@permission_classes([AllowAny])
def quote_rate_view(request):
    """Quote courier rates using Chilexpress API."""
    try:
        origin_county_code = request.data.get("originCountyCode", "").strip().upper()
        destination_county_code = request.data.get("destinationCountyCode", "").strip().upper()
        package = request.data.get("package")
        product_type = request.data.get("productType")
        content_type = request.data.get("contentType")
        declared_worth = request.data.get("declaredWorth")
        delivery_time = request.data.get("deliveryTime")

        if not origin_county_code or not destination_county_code:
            return Response(
                {"error": "originCountyCode y destinationCountyCode son requeridos"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(package, dict):
            return Response(
                {"error": "package es requerido y debe ser un objeto"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = quote_chilexpress_rate(
            origin_county_code=origin_county_code,
            destination_county_code=destination_county_code,
            package=package,
            product_type=product_type,
            content_type=content_type,
            declared_worth=declared_worth,
            delivery_time=delivery_time,
        )

        return Response(
            {
                "options": result.get("options", []),
                "statusDescription": result.get("status_description"),
            }
        )
    except ChilexpressApiError as exc:
        return Response(
            {"error": str(exc)},
            status=status.HTTP_502_BAD_GATEWAY,
        )
    except Exception as exc:
        return Response(
            {"error": f"Error inesperado: {str(exc)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
