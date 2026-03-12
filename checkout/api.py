from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from inventory.services import InventoryError
from .models import Cart
from .serializers import (
    AddCartItemSerializer,
    ApplyDiscountSerializer,
    CartSerializer,
    ResolveCartSerializer,
    UpdateCartItemSerializer,
)
from .services import (
    add_item_to_cart,
    apply_discount,
    calculate_cart_totals,
    convert_cart_to_order,
    get_idempotent_payload,
    get_or_create_cart,
    remove_cart_item,
    store_idempotent_payload,
    update_cart_item,
)


class CartViewSet(viewsets.GenericViewSet):
    queryset = Cart.objects.prefetch_related("items", "discounts", "tax_lines")
    serializer_class = CartSerializer
    permission_classes = [AllowAny]

    def _get_guest_token(self, request):
        return (
            request.headers.get("X-Guest-Token")
            or request.query_params.get("guest_token")
            or request.data.get("guest_token")
        )

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
        cart = get_or_create_cart(
            user=request.user if request.user.is_authenticated else None,
            guest_token=self._get_guest_token(request),
        )
        calculate_cart_totals(cart)
        return Response(CartSerializer(cart).data)

    @action(detail=True, methods=["post"], url_path="add-item")
    def add_item(self, request, pk=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = request.headers.get("Idempotency-Key")
        cached = get_idempotent_payload(cart, "add_item", idempotency_key)
        if cached:
            return Response(cached)

        serializer = AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            cart = add_item_to_cart(cart.id, data["book_id"], data["quantity"])
        except InventoryError as exc:
            raise ValidationError({"detail": str(exc)})
        payload = CartSerializer(cart).data
        store_idempotent_payload(cart, "add_item", idempotency_key, payload)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["patch"], url_path=r"items/(?P<item_id>[^/.]+)")
    def update_item(self, request, pk=None, item_id=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = request.headers.get("Idempotency-Key")
        cached = get_idempotent_payload(cart, "update_item", idempotency_key)
        if cached:
            return Response(cached)

        serializer = UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            cart = update_cart_item(cart.id, item_id, serializer.validated_data["quantity"])
        except InventoryError as exc:
            raise ValidationError({"detail": str(exc)})
        payload = CartSerializer(cart).data
        store_idempotent_payload(cart, "update_item", idempotency_key, payload)
        return Response(payload)

    @update_item.mapping.delete
    def remove_item(self, request, pk=None, item_id=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = request.headers.get("Idempotency-Key")
        cached = get_idempotent_payload(cart, "remove_item", idempotency_key)
        if cached:
            return Response(cached)

        cart = remove_cart_item(cart.id, item_id)
        payload = CartSerializer(cart).data
        store_idempotent_payload(cart, "remove_item", idempotency_key, payload)
        return Response(payload, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="apply-discount")
    def apply_discount(self, request, pk=None):
        cart = self.get_object()
        self._assert_cart_access(request, cart)
        idempotency_key = request.headers.get("Idempotency-Key")
        cached = get_idempotent_payload(cart, "apply_discount", idempotency_key)
        if cached:
            return Response(cached)

        serializer = ApplyDiscountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        cart = apply_discount(
            cart.id,
            discount_type=data["type"],
            value=data.get("value", "0"),
            code=data.get("code", ""),
            metadata=data.get("metadata", {}),
        )
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
        try:
            cart = convert_cart_to_order(cart.id)
        except InventoryError as exc:
            raise ValidationError({"detail": str(exc)})
        return Response(CartSerializer(cart).data, status=status.HTTP_200_OK)
