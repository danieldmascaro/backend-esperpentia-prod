from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.conf import settings
from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from inventory.services import assert_stock_available, consume_reserved_stock, reserve_stock
from orders.services import create_order_from_sale
from productos.models import Libro
from ventas.services import create_sale_from_cart
from .models import (
    Cart,
    CartDiscount,
    CartItem,
    CartOperationLog,
    CartTaxLine,
    DiscountCoupon,
    DiscountType,
    default_cart_expiry,
)

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


def _get_active_cart_for_update(cart_id):
    try:
        return Cart.objects.select_for_update().get(pk=cart_id, status=Cart.Status.ACTIVE)
    except Cart.DoesNotExist as exc:
        raise CheckoutError("El carrito no existe o ya no esta activo.") from exc


def _calculate_discount_amount(
    *,
    subtotal,
    discount_type,
    value,
    metadata,
    max_discount_amount=None,
):
    amount = Decimal("0")
    if value < 0:
        raise CheckoutError("El valor del descuento no puede ser negativo.")

    if discount_type == DiscountType.PERCENT:
        if value > 100:
            raise CheckoutError("El descuento porcentual no puede ser mayor a 100.")
        amount = quantize(subtotal * (value / Decimal("100")))
    elif discount_type in {DiscountType.FIXED, DiscountType.COUPON}:
        amount = quantize(value)
    elif discount_type == DiscountType.QTY_PROMO:
        min_qty = int(metadata.get("min_qty", 0))
        amount_per_bundle = Decimal(str(metadata.get("amount_off", "0")))
        current_qty = int(metadata.get("current_qty", 0))
        if min_qty > 0 and current_qty >= min_qty:
            bundles = current_qty // min_qty
            amount = quantize(amount_per_bundle * bundles)

    if max_discount_amount is not None:
        amount = min(amount, quantize(max_discount_amount))

    amount = min(amount, subtotal)
    return max(amount, Decimal("0"))


def _get_book_snapshot(book: Libro) -> dict:
    """
    Crea un snapshot compacto del libro.
    Requiere que book ya tenga select_related("obra__autor", "obra__genero", "editorial").
    """
    return {
        "libro_id": book.id,
        "isbn": book.isbn,
        "idioma": book.idioma,
        "tipo_tapa": book.tipo_tapa,
        "obra": {
            "id": book.obra_id,
            "titulo": book.obra.titulo,
            "autor": book.obra.autor.nombre,
            "genero": book.obra.genero.nombre,
        },
        "editorial": book.editorial.nombre,
    }


def calculate_cart_totals(cart: Cart) -> Cart:
    """
    Calcula los totales del carrito en una sola query.
    Optimizado para evitar N+1 queries.
    """
    from django.db.models import Sum as DjangoSum
    
    # Si los items/discounts están precargados, usarlos; si no, hacer la query
    if hasattr(cart, '_prefetched_objects_cache') and 'items' in cart._prefetched_objects_cache:
        items_subtotal = sum(item.subtotal for item in cart.items.all()) or Decimal("0")
    else:
        items_subtotal = cart.items.aggregate(total=DjangoSum("subtotal"))["total"] or Decimal("0")
    
    if hasattr(cart, '_prefetched_objects_cache') and 'discounts' in cart._prefetched_objects_cache:
        discount_amount = sum(d.amount for d in cart.discounts.all()) or Decimal("0")
    else:
        discount_amount = cart.discounts.aggregate(total=DjangoSum("amount"))["total"] or Decimal("0")

    taxable_base = max(items_subtotal - discount_amount, Decimal("0"))
    apply_tax = getattr(settings, "CHECKOUT_APPLY_TAX", True)
    tax_rate = Decimal(str(getattr(settings, "CHECKOUT_TAX_RATE", "0.19")))
    tax_amount = quantize(taxable_base * tax_rate) if apply_tax else Decimal("0")

    quantized_subtotal = quantize(items_subtotal)
    quantized_discount = quantize(discount_amount)
    quantized_total = quantize(quantized_subtotal - quantized_discount + tax_amount)

    # Determinar si necesitamos actualizar totales
    totals_changed = (
        cart.subtotal_amount != quantized_subtotal
        or cart.discount_amount != quantized_discount
        or cart.tax_amount != tax_amount
        or cart.total_amount != quantized_total
    )

    # Manejar tax_lines más eficientemente
    line_changed = False
    if apply_tax:
        desired_line = {
            "rate": tax_rate,
            "taxable_base": quantize(taxable_base),
            "amount": tax_amount,
        }
        tax_line, created = cart.tax_lines.get_or_create(
            name="IVA",
            defaults=desired_line
        )
        if not created:
            # Solo actualizar si hay cambios
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

    # Guardar cart si hay cambios
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
    cart = _get_active_cart_for_update(cart_id)
    try:
        book = Libro.objects.select_related("obra__autor", "obra__genero", "editorial").get(pk=book_id, activo=True)
    except Libro.DoesNotExist as exc:
        raise CheckoutError("El libro no existe o no esta activo.") from exc
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
    cart = _get_active_cart_for_update(cart_id)
    try:
        item = CartItem.objects.select_related("book").get(pk=item_id, cart=cart)
    except CartItem.DoesNotExist as exc:
        raise CheckoutError("El item del carrito no existe.") from exc
    assert_stock_available(item.book, quantity)
    item.quantity = quantity
    item.subtotal = quantize(item.unit_price_snapshot * quantity)
    item.save(update_fields=["quantity", "subtotal", "updated_at"])
    return calculate_cart_totals(cart)


@transaction.atomic
def remove_cart_item(cart_id, item_id) -> Cart:
    cart = _get_active_cart_for_update(cart_id)
    item = CartItem.objects.filter(pk=item_id, cart=cart).first()
    if item:
        item.delete()
    return calculate_cart_totals(cart)


@transaction.atomic
def apply_discount(cart_id, code) -> Cart:
    cart = _get_active_cart_for_update(cart_id)
    normalized_code = (code or "").strip().upper()
    if not normalized_code:
        raise CheckoutError("Debes proporcionar un codigo de cupon valido.")

    now = timezone.now()
    coupon = (
        DiscountCoupon.objects.select_for_update()
        .filter(code=normalized_code, active=True)
        .first()
    )
    if not coupon:
        raise CheckoutError("El cupon no existe o esta inactivo.")
    if coupon.valid_from and coupon.valid_from > now:
        raise CheckoutError("El cupon aun no esta vigente.")
    if coupon.valid_until and coupon.valid_until < now:
        raise CheckoutError("El cupon ya expiro.")
    if coupon.usage_limit is not None and coupon.times_used >= coupon.usage_limit:
        raise CheckoutError("El cupon alcanzo su limite de uso.")
    if cart.discounts.filter(coupon_id=coupon.id).exists():
        raise CheckoutError("Este cupon ya fue aplicado en el carrito.")

    subtotal = cart.items.aggregate(total=Sum("subtotal"))["total"] or Decimal("0")
    subtotal = quantize(subtotal)
    if subtotal <= 0:
        raise CheckoutError("No se puede aplicar cupon a un carrito vacio.")
    if subtotal < coupon.min_subtotal_amount:
        raise CheckoutError("El cupon requiere un subtotal minimo mayor.")

    coupon_metadata = dict(coupon.metadata or {})
    coupon_metadata["current_qty"] = cart.items.aggregate(total=Sum("quantity"))["total"] or 0
    amount = _calculate_discount_amount(
        subtotal=subtotal,
        discount_type=coupon.type,
        value=Decimal(coupon.value),
        metadata=coupon_metadata,
        max_discount_amount=coupon.max_discount_amount,
    )
    if amount <= 0:
        raise CheckoutError("El cupon no aplica a las condiciones actuales del carrito.")

    CartDiscount.objects.create(
        cart=cart,
        coupon=coupon,
        code=coupon.code,
        type=coupon.type,
        value=quantize(Decimal(coupon.value)),
        amount=amount,
        metadata=coupon_metadata,
        description=f"Coupon {coupon.code}",
    )
    DiscountCoupon.objects.filter(pk=coupon.pk).update(
        times_used=F("times_used") + 1,
        updated_at=timezone.now(),
    )
    return calculate_cart_totals(cart)


@transaction.atomic
def convert_cart_to_order(cart_id, contact_data=None):
    """
    Convierte un carrito a una orden.
    Optimizado para ejecutar con el mínimo de queries.
    """
    cart = Cart.objects.select_for_update().prefetch_related(
        'items',
        'discounts', 
        'tax_lines'
    ).filter(pk=cart_id, status=Cart.Status.ACTIVE).first()
    if not cart:
        raise CheckoutError("El carrito no existe o ya no esta activo.")

    items = list(cart.items.select_related("book"))
    if not items:
        raise CheckoutError("No se puede convertir un carrito vacio.")
    
    # Calcular totales si no están actualizados
    calculate_cart_totals(cart)
    
    # Procesar items ya precargados sin hacer queries adicionales
    for item in items:
        reserve_stock(item.book, item.quantity)
        consume_reserved_stock(item.book, item.quantity)

    sale = create_sale_from_cart(cart, contact_data=contact_data)
    order = create_order_from_sale(sale)
    
    # Actualizar estado del carrito
    cart.status = Cart.Status.CONVERTED
    cart.converted_at = timezone.now()
    cart.version += 1
    cart.save(update_fields=["status", "converted_at", "version", "updated_at"])
    
    return cart, order


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


def cleanup_expired_operation_logs():
    """
    Limpia los registros de operaciones expiradas.
    Llamar regularmente mediante Celery o un management command.
    """
    deleted_count, _ = CartOperationLog.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
    return deleted_count
