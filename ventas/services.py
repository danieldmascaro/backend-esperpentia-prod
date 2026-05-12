from datetime import datetime, time
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Count, Sum
from django.db.models.functions import TruncDay, TruncMonth
from django.utils import timezone

from .models import Venta, VentaItem

CLP_UNIT = Decimal("1")


def quantize(value: Decimal) -> Decimal:
    return value.quantize(CLP_UNIT, rounding=ROUND_HALF_UP)


def _parse_date(date_str, end_of_day=False):
    if not date_str:
        return None
    parsed = datetime.fromisoformat(date_str).date()
    base_time = time.max if end_of_day else time.min
    dt = datetime.combine(parsed, base_time)
    return timezone.make_aware(dt, timezone.get_current_timezone())


def _sales_queryset(date_from=None, date_to=None, status_value=Venta.Status.COMPLETED, currency=None):
    qs = Venta.objects.all()
    if status_value:
        qs = qs.filter(status=status_value)
    if currency:
        qs = qs.filter(currency=currency)
    if date_from:
        qs = qs.filter(sold_at__gte=date_from)
    if date_to:
        qs = qs.filter(sold_at__lte=date_to)
    return qs


def sync_sale_status(venta, status):
    if venta.status == status:
        return venta
    venta.status = status
    venta.save(update_fields=["status", "updated_at"])
    return venta


def sync_sale_status_from_order(order):
    if not getattr(order, "sale_id", None):
        return None

    if order.status == "cancelled":
        return sync_sale_status(order.sale, Venta.Status.CANCELLED)

    return sync_sale_status(order.sale, Venta.Status.COMPLETED)


def sync_sale_status_from_payment(payment):
    sale = getattr(payment.order, "sale", None)
    if sale is None:
        return None
    if payment.status == "refunded":
        return sync_sale_status(sale, Venta.Status.REFUNDED)
    if payment.status == "failed":
        return sync_sale_status(sale, Venta.Status.CANCELLED)
    return sync_sale_status(sale, Venta.Status.COMPLETED)


def _normalize_contact_payload(cart, contact_data):
    payload = dict(contact_data or {})
    user = cart.user

    first_name = (payload.get("contact_first_name") or "").strip()
    last_name = (payload.get("contact_last_name") or "").strip()
    email = (payload.get("contact_email") or "").strip()
    phone = (payload.get("contact_phone") or "").strip()

    if user:
        if not first_name:
            first_name = (getattr(user, "nombre", "") or "").strip()
        if not last_name:
            last_name = (getattr(user, "apellido", "") or "").strip()
        if not email:
            email = (getattr(user, "email", "") or "").strip()

    return {
        "contact_first_name": first_name,
        "contact_last_name": last_name,
        "contact_email": email,
        "contact_phone": phone,
        "shipping_address": (payload.get("shipping_address") or "").strip(),
        "shipping_city": (payload.get("shipping_city") or "").strip(),
        "shipping_region": (payload.get("shipping_region") or "").strip(),
        "shipping_postal_code": (payload.get("shipping_postal_code") or "").strip(),
        "shipping_country": (payload.get("shipping_country") or "Chile").strip(),
    }


def create_sale_from_cart(cart, contact_data=None):
    existing = Venta.objects.filter(cart_id=cart.id).first()
    if existing:
        return existing

    sold_at = timezone.now()
    items = list(cart.items.select_related("book", "book__obra__autor", "book__obra__genero", "book__editorial").all())
    items_count = len(items)
    total_quantity = sum(item.quantity for item in items)

    with transaction.atomic():
        contact_payload = _normalize_contact_payload(cart, contact_data)
        venta = Venta.objects.create(
            cart_id=cart.id,
            user=cart.user,
            guest_token=cart.guest_token,
            despachado=False,
            **contact_payload,
            currency=cart.currency,
            subtotal_amount=cart.subtotal_amount,
            discount_amount=cart.discount_amount,
            tax_amount=cart.tax_amount,
            total_amount=cart.total_amount,
            items_count=items_count,
            total_quantity=total_quantity,
            sold_at=sold_at,
        )

        venta_items = []
        for item in items:
            libro = item.book
            sale_item = VentaItem(
                venta=venta,
                libro=libro,
                libro_nombre=libro.nombre,
                autor_nombre=libro.obra.autor.nombre,
                editorial_nombre=libro.editorial.nombre,
                genero_nombre=libro.obra.genero.nombre,
                isbn=libro.isbn,
                idioma=libro.idioma,
                unit_price=item.unit_price_snapshot,
                quantity=item.quantity,
                subtotal=item.subtotal,
                sold_at=sold_at,
                metadata_snapshot=item.metadata_snapshot,
            )
            venta_items.append(sale_item)

        VentaItem.objects.bulk_create(venta_items)
        return venta


def get_sales_summary(date_from=None, date_to=None, status_value=Venta.Status.COMPLETED, currency=None):
    qs = _sales_queryset(date_from=date_from, date_to=date_to, status_value=status_value, currency=currency)
    aggregated = qs.aggregate(
        orders_count=Count("id"),
        total_subtotal=Sum("subtotal_amount"),
        total_discount=Sum("discount_amount"),
        total_tax=Sum("tax_amount"),
        total_amount=Sum("total_amount"),
        total_items=Sum("items_count"),
        total_quantity=Sum("total_quantity"),
    )

    orders_count = aggregated["orders_count"] or 0
    total_amount = aggregated["total_amount"] or Decimal("0")
    avg_order_value = quantize(total_amount / orders_count) if orders_count else Decimal("0")

    return {
        "orders_count": orders_count,
        "total_subtotal": aggregated["total_subtotal"] or Decimal("0"),
        "total_discount": aggregated["total_discount"] or Decimal("0"),
        "total_tax": aggregated["total_tax"] or Decimal("0"),
        "total_amount": total_amount,
        "total_items": aggregated["total_items"] or 0,
        "total_quantity": aggregated["total_quantity"] or 0,
        "average_order_value": avg_order_value,
    }


def get_sales_by_date(date_from=None, date_to=None, group_by="day", status_value=Venta.Status.COMPLETED, currency=None):
    qs = _sales_queryset(date_from=date_from, date_to=date_to, status_value=status_value, currency=currency)
    trunc = TruncMonth("sold_at") if group_by == "month" else TruncDay("sold_at")
    rows = (
        qs.annotate(period=trunc)
        .values("period")
        .annotate(
            orders_count=Count("id"),
            total_amount=Sum("total_amount"),
            total_quantity=Sum("total_quantity"),
        )
        .order_by("period")
    )
    return list(rows)


def get_sales_by_book(date_from=None, date_to=None, limit=20, status_value=Venta.Status.COMPLETED, currency=None):
    qs = VentaItem.objects.all()
    if status_value:
        qs = qs.filter(venta__status=status_value)
    if currency:
        qs = qs.filter(venta__currency=currency)
    if date_from:
        qs = qs.filter(sold_at__gte=date_from)
    if date_to:
        qs = qs.filter(sold_at__lte=date_to)

    rows = (
        qs.values("libro_id", "libro_nombre")
        .annotate(
            total_quantity=Sum("quantity"),
            gross_sales=Sum("subtotal"),
            lines=Count("id"),
            authors_count=Count("autor_nombre", distinct=True),
        )
        .order_by("-gross_sales", "-total_quantity")[:limit]
    )
    return list(rows)


def parse_date_filters(date_from_str=None, date_to_str=None):
    date_from = _parse_date(date_from_str, end_of_day=False)
    date_to = _parse_date(date_to_str, end_of_day=True)
    if date_from and date_to and date_from > date_to:
        raise ValueError("date_from no puede ser mayor que date_to.")
    return date_from, date_to
