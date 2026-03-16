from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from inventory.services import assert_stock_available, consume_reserved_stock, reserve_stock
from orders.services import create_order_from_sale
from productos.models import Libro
from ventas.services import create_sale_from_cart
from .models import Cart, CartDiscount, CartItem, CartOperationLog, CartTaxLine, default_cart_expiry

CLP_UNIT = Decimal("1")


class CheckoutError(Exception):
    pass


def quantize(value: Decimal) -> Decimal:
    return value.quantize(CLP_UNIT, rounding=ROUND_HALF_UP)


def get_or_create_cart(user=None, guest_token=None, currency="CLP") -> Cart:
    if user and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(
            user=user,
            status=Cart.Status.ACTIVE,
            defaults={"currency": currency, "guest_token": guest_token},
        )
        return cart

    if not guest_token:
        guest_token = uuid4().hex

    cart, _ = Cart.objects.get_or_create(
        guest_token=guest_token,
        status=Cart.Status.ACTIVE,
        defaults={"currency": currency},
    )
    return cart


def get_current_cart(user=None, guest_token=None):
    if user and user.is_authenticated:
        return Cart.objects.filter(user=user, status=Cart.Status.ACTIVE).first()
    if not guest_token:
        return None
    return Cart.objects.filter(guest_token=guest_token, status=Cart.Status.ACTIVE).first()


def _get_book_unit_price(book: Libro) -> Decimal:
    return quantize(book.precio)


def _get_book_snapshot(book: Libro) -> dict:
    return {
        "libro_id": book.id,
        "obra_id": book.obra_id,
        "obra": book.obra.titulo,
        "autor": book.obra.autor.nombre,
        "genero": book.obra.genero.nombre,
        "editorial": book.editorial.nombre,
        "isbn": book.isbn,
        "idioma": book.idioma,
        "tipo_tapa": book.tipo_tapa,
    }


def calculate_cart_totals(cart: Cart) -> Cart:
    items_subtotal = cart.items.aggregate(total=Sum("subtotal"))["total"] or Decimal("0")
    discount_amount = cart.discounts.aggregate(total=Sum("amount"))["total"] or Decimal("0")
    taxable_base = max(items_subtotal - discount_amount, Decimal("0"))

    apply_tax = getattr(settings, "CHECKOUT_APPLY_TAX", True)
    tax_rate = Decimal(str(getattr(settings, "CHECKOUT_TAX_RATE", "0.19")))
    tax_amount = quantize(taxable_base * tax_rate) if apply_tax else Decimal("0")

    line_changed = False
    quantized_subtotal = quantize(items_subtotal)
    quantized_discount = quantize(discount_amount)
    quantized_total = quantize(quantized_subtotal - quantized_discount + tax_amount)

    if apply_tax:
        tax_line = cart.tax_lines.filter(name="IVA").first()
        desired_line = {
            "rate": tax_rate,
            "taxable_base": quantize(taxable_base),
            "amount": tax_amount,
        }
        if not tax_line:
            CartTaxLine.objects.create(cart=cart, name="IVA", **desired_line)
            line_changed = True
        else:
            dirty_fields = [
                field_name for field_name, expected_value in desired_line.items()
                if getattr(tax_line, field_name) != expected_value
            ]
            if dirty_fields:
                for field_name, expected_value in desired_line.items():
                    setattr(tax_line, field_name, expected_value)
                tax_line.save(update_fields=[*dirty_fields, "updated_at"])
                line_changed = True
    else:
        deleted, _ = cart.tax_lines.all().delete()
        line_changed = deleted > 0

    totals_changed = any([
        cart.subtotal_amount != quantized_subtotal,
        cart.discount_amount != quantized_discount,
        cart.tax_amount != tax_amount,
        cart.total_amount != quantized_total,
    ])

    if totals_changed or line_changed:
        cart.subtotal_amount = quantized_subtotal
        cart.discount_amount = quantized_discount
        cart.tax_amount = tax_amount
        cart.total_amount = quantized_total
        cart.version += 1
        cart.save(
            update_fields=[
                "subtotal_amount",
                "discount_amount",
                "tax_amount",
                "total_amount",
                "version",
                "updated_at",
            ]
        )
    return cart


@transaction.atomic
def add_item_to_cart(cart_id, book_id, quantity) -> Cart:
    cart = Cart.objects.select_for_update().get(pk=cart_id, status=Cart.Status.ACTIVE)
    book = Libro.objects.select_related("obra__autor", "obra__genero", "editorial").get(pk=book_id, activo=True)
    unit_price = _get_book_unit_price(book)

    existing_item = CartItem.objects.filter(cart=cart, book=book).only("id", "quantity", "unit_price_snapshot").first()
    next_quantity = quantity if not existing_item else existing_item.quantity + quantity
    assert_stock_available(book, next_quantity)

    item, created = CartItem.objects.get_or_create(
        cart=cart,
        book=book,
        defaults={
            "quantity": quantity,
            "unit_price_snapshot": unit_price,
            "subtotal": quantize(unit_price * quantity),
            "metadata_snapshot": _get_book_snapshot(book),
        },
    )
    if not created:
        item.quantity += quantity
        item.subtotal = quantize(item.unit_price_snapshot * item.quantity)
        item.save(update_fields=["quantity", "subtotal", "updated_at"])

    return calculate_cart_totals(cart)


@transaction.atomic
def update_cart_item(cart_id, item_id, quantity) -> Cart:
    cart = Cart.objects.select_for_update().get(pk=cart_id, status=Cart.Status.ACTIVE)
    item = CartItem.objects.select_related("book").get(pk=item_id, cart=cart)
    assert_stock_available(item.book, quantity)
    item.quantity = quantity
    item.subtotal = quantize(item.unit_price_snapshot * quantity)
    item.save(update_fields=["quantity", "subtotal", "updated_at"])
    return calculate_cart_totals(cart)


@transaction.atomic
def remove_cart_item(cart_id, item_id) -> Cart:
    cart = Cart.objects.select_for_update().get(pk=cart_id, status=Cart.Status.ACTIVE)
    item = CartItem.objects.filter(pk=item_id, cart=cart).first()
    if item:
        item.delete()
    return calculate_cart_totals(cart)


@transaction.atomic
def apply_discount(cart_id, discount_type, value=Decimal("0"), code="", metadata=None) -> Cart:
    cart = Cart.objects.select_for_update().get(pk=cart_id, status=Cart.Status.ACTIVE)
    metadata = metadata or {}
    subtotal = cart.items.aggregate(total=Sum("subtotal"))["total"] or Decimal("0")
    subtotal = quantize(subtotal)

    amount = Decimal("0")
    value = Decimal(value)
    if value < 0:
        raise CheckoutError("El valor del descuento no puede ser negativo.")
    if discount_type == CartDiscount.Type.PERCENT:
        if value > 100:
            raise CheckoutError("El descuento porcentual no puede ser mayor a 100.")
        amount = quantize(subtotal * (value / Decimal("100")))
    elif discount_type == CartDiscount.Type.FIXED:
        amount = min(quantize(value), subtotal)
    elif discount_type == CartDiscount.Type.QTY_PROMO:
        min_qty = int(metadata.get("min_qty", 0))
        amount_per_bundle = Decimal(str(metadata.get("amount_off", "0")))
        current_qty = cart.items.aggregate(total=Sum("quantity"))["total"] or 0
        if min_qty > 0 and current_qty >= min_qty:
            bundles = current_qty // min_qty
            amount = quantize(amount_per_bundle * bundles)
            amount = min(amount, subtotal)
    elif discount_type == CartDiscount.Type.COUPON:
        amount = min(quantize(value), subtotal)

    CartDiscount.objects.create(
        cart=cart,
        code=code,
        type=discount_type,
        value=quantize(value),
        amount=amount,
        metadata=metadata,
        description=f"Discount {discount_type}",
    )
    return calculate_cart_totals(cart)


@transaction.atomic
def convert_cart_to_order(cart_id):
    cart = Cart.objects.select_for_update().prefetch_related("items", "discounts", "tax_lines").get(
        pk=cart_id, status=Cart.Status.ACTIVE
    )
    if not cart.items.exists():
        raise CheckoutError("No se puede convertir un carrito vacio.")
    calculate_cart_totals(cart)
    for item in cart.items.select_related("book"):
        reserve_stock(item.book, item.quantity)
        consume_reserved_stock(item.book, item.quantity)

    sale = create_sale_from_cart(cart)
    create_order_from_sale(sale)
    cart.status = Cart.Status.CONVERTED
    cart.converted_at = timezone.now()
    cart.version += 1
    cart.save(update_fields=["status", "converted_at", "version", "updated_at"])
    return cart


def get_idempotent_payload(cart, operation, idempotency_key):
    if not idempotency_key:
        return None
    log = CartOperationLog.objects.filter(
        cart=cart,
        operation=operation,
        idempotency_key=idempotency_key,
        expires_at__gt=timezone.now(),
    ).first()
    return log.response_payload if log else None


def store_idempotent_payload(cart, operation, idempotency_key, payload):
    if not idempotency_key:
        return
    CartOperationLog.objects.update_or_create(
        cart=cart,
        operation=operation,
        idempotency_key=idempotency_key,
        defaults={
            "response_payload": payload,
            "expires_at": default_cart_expiry(),
        },
    )
