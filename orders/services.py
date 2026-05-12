from django.db import transaction

from .models import Order


class OrderTransitionError(Exception):
    pass


ALLOWED_ORDER_TRANSITIONS = {
    Order.Status.PENDING: {
        Order.Status.PENDING,
        Order.Status.PAID,
        Order.Status.PROCESSING,
        Order.Status.CANCELLED,
    },
    Order.Status.PAID: {
        Order.Status.PAID,
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
        Order.Status.CANCELLED,
    },
    Order.Status.PROCESSING: {
        Order.Status.PROCESSING,
        Order.Status.SHIPPED,
        Order.Status.CANCELLED,
    },
    Order.Status.SHIPPED: {
        Order.Status.SHIPPED,
        Order.Status.DELIVERED,
    },
    Order.Status.DELIVERED: {
        Order.Status.DELIVERED,
    },
    Order.Status.CANCELLED: {
        Order.Status.CANCELLED,
    },
}


def assert_valid_order_transition(current_status, next_status):
    allowed = ALLOWED_ORDER_TRANSITIONS.get(current_status, {current_status})
    if next_status not in allowed:
        raise OrderTransitionError(f"Transicion de estado invalida: {current_status} -> {next_status}.")


@transaction.atomic
def create_order_from_sale(sale):
    order, created = Order.objects.get_or_create(
        sale=sale,
        defaults={
            "user": sale.user,
            "status": Order.Status.PENDING,
            "currency": sale.currency,
            "subtotal_amount": sale.subtotal_amount,
            "discount_amount": sale.discount_amount,
            "tax_amount": sale.tax_amount,
            "total_amount": sale.total_amount,
        },
    )
    return order


@transaction.atomic
def create_order_from_cart(cart, contact_data=None):
    order, created = Order.objects.get_or_create(
        cart=cart,
        defaults={
            "user": cart.user,
            "status": Order.Status.PENDING,
            "currency": cart.currency,
            "subtotal_amount": cart.subtotal_amount,
            "discount_amount": cart.discount_amount,
            "tax_amount": cart.tax_amount,
            "total_amount": cart.total_amount,
            "checkout_contact_payload": dict(contact_data or {}),
        },
    )
    if not created and contact_data:
        payload = dict(contact_data)
        if order.checkout_contact_payload != payload:
            order.checkout_contact_payload = payload
            order.save(update_fields=["checkout_contact_payload", "updated_at"])
    return order
