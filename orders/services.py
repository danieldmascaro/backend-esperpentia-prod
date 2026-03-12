from django.db import transaction

from .models import Order


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
