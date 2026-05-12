from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.settings import api_settings
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.db.models import Prefetch
import logging
from uuid import uuid4

from inventory.services import InventoryError
from .models import Cart, CartItem
from .serializers import (
    AddCartItemSerializer,
    ApplyDiscountSerializer,
    CartSerializer,
    ConvertCartSerializer,
    ResolveCartSerializer,
    UpdateCartItemSerializer,
)
from .services import (
    CheckoutError,
    add_item_to_cart,
    apply_discount,
    calculate_cart_totals,
    convert_cart_to_order,
    get_idempotent_payload,
    get_current_cart,
    get_or_create_cart,
    remove_cart_item,
    store_idempotent_payload,
    update_cart_item,
)

logger = logging.getLogger(__name__)


class CartViewSet(viewsets.GenericViewSet):
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Optimizar queryset con prefetches y select_related."""
        return Cart.objects.prefetch_related(
            Prefetch('items', queryset=CartItem.objects.select_related('book')),
            'discounts',
            'tax_lines'
        )

    def get_throttles(self):
        throttle_classes = list(api_settings.DEFAULT_THROTTLE_CLASSES)
        if self.action == "current":
            self.throttle_scope = "checkout_read"
            throttle_classes.append(ScopedRateThrottle)
        elif self.action in {"resolve", "add_item", "update_item", "remove_item", "apply_discount", "recalculate", "convert"}:
            self.throttle_scope = "checkout_write"
            throttle_classes.append(ScopedRateThrottle)
        return [throttle() for throttle in throttle_classes]

    def _get_guest_token(self, request):
        body_token = None
        if request.method != "GET":
            body_token = request.data.get("guest_token")
        return (
            request.headers.get("X-Guest-Token")
            or request.query_params.get("guest_token")
            or body_token
        )

    def _get_idempotency_key(self, request):
        value = request.headers.get("Idempotency-Key")
        if value and len(value) > 128:
            raise ValidationError({"detail": "Idempotency-Key excede el maximo de 128 caracteres."})
        return value

    def _assert_cart_access(self, request, cart):
        if request.user.is_authenticated and cart.user_id == request.user.id:
            return
        guest_token = self._get_guest_token(request)
        if guest_token and cart.guest_token == guest_token:
            return
        raise PermissionDenied("No tienes acceso a este carrito.")

    @action(detail=False, methods=["post"], url_path="resolve")
    def resolve(self, request):
        serializer = ResolveCartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = get_or_create_cart(
            user=request.user if request.user.is_authenticated else None,
            guest_token=data.get("guest_token"),
            currency=data.get("currency", "CLP"),
        )
        calculate_cart_totals(cart)
        payload = CartSerializer(cart).data
        return Response(payload)

    @action(detail=False, methods=["get"], url_path="current")
    def current(self, request):
        cart = get_current_cart(
            user=request.user if request.user.is_authenticated else None,
            guest_token=self._get_guest_token(request),
        )
        if not cart:
            return Response({"detail": "No existe un carrito activo."}, status=status.HTTP_404_NOT_FOUND)
        calculate_cart_totals(cart)
        return Response(CartSerializer(cart).data)

    @action(detail=True, methods=["post"], url_path="add-item")
    def add_item(self, request, pk=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = self._get_idempotency_key(request)
        cached = get_idempotent_payload(cart, "add_item", idempotency_key)
        if cached:
            return Response(cached)

        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            cart = add_item_to_cart(cart.id, data["book_id"], data["quantity"])
        except (CheckoutError, InventoryError) as exc:
            raise ValidationError({"detail": str(exc)})
        payload = CartSerializer(cart).data
        store_idempotent_payload(cart, "add_item", idempotency_key, payload)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path=r"items/(?P<item_id>[^/.]+)")
    def update_item(self, request, pk=None, item_id=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = self._get_idempotency_key(request)
        cached = get_idempotent_payload(cart, "update_item", idempotency_key)
        if cached:
            return Response(cached)

        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cart = update_cart_item(cart.id, item_id, serializer.validated_data["quantity"])
        except (CheckoutError, InventoryError) as exc:
            raise ValidationError({"detail": str(exc)})
        payload = CartSerializer(cart).data
        store_idempotent_payload(cart, "update_item", idempotency_key, payload)
        return Response(payload)

    @update_item.mapping.delete
    def remove_item(self, request, pk=None, item_id=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = self._get_idempotency_key(request)
        cached = get_idempotent_payload(cart, "remove_item", idempotency_key)
        if cached:
            return Response(cached)

        try:
            cart = remove_cart_item(cart.id, item_id)
        except CheckoutError as exc:
            raise ValidationError({"detail": str(exc)})
        payload = CartSerializer(cart).data
        store_idempotent_payload(cart, "remove_item", idempotency_key, payload)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="apply-discount")
    def apply_discount(self, request, pk=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = self._get_idempotency_key(request)
        cached = get_idempotent_payload(cart, "apply_discount", idempotency_key)
        if cached:
            return Response(cached)

        serializer = ApplyDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            cart = apply_discount(cart.id, code=data["code"])
        except CheckoutError as exc:
            raise ValidationError({"detail": str(exc)})
        payload = CartSerializer(cart).data
        store_idempotent_payload(cart, "apply_discount", idempotency_key, payload)
        return Response(payload)

    @action(detail=True, methods=["post"], url_path="recalculate")
    def recalculate(self, request, pk=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        cart = calculate_cart_totals(cart)
        return Response(CartSerializer(cart).data)

    @action(detail=True, methods=["post"], url_path="convert")
    def convert(self, request, pk=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = self._get_idempotency_key(request)
        cached = get_idempotent_payload(cart, "convert", idempotency_key)
        if cached:
            return Response(cached)

        convert_serializer = ConvertCartSerializer(data=request.data or {})
        convert_serializer.is_valid(raise_exception=True)
        try:
            cart, order = convert_cart_to_order(cart.id, contact_data=convert_serializer.validated_data)
        except (CheckoutError, InventoryError) as exc:
            raise ValidationError({"detail": str(exc)})
        except Exception as exc:
            error_id = uuid4().hex[:12]
            logger.exception("Error inesperado al convertir carrito. error_id=%s", error_id)
            raise ValidationError({"detail": f"Error interno en checkout convert. ref={error_id}: {exc}"})
        payload = {
            "cart": CartSerializer(cart).data,
            "order_id": str(order.id),
            "sale_id": str(order.sale_id) if order.sale_id else None,
            "order_status": order.status,
        }
        store_idempotent_payload(cart, "convert", idempotency_key, payload)
        return Response(payload, status=status.HTTP_200_OK)
