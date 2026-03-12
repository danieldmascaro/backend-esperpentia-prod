from django.db import transaction
from django.db.models import Sum

from .models import InventoryItem


class InventoryError(Exception):
    pass


def get_or_create_inventory_item(book):
    inventory_item, _ = InventoryItem.objects.get_or_create(
        book=book,
        defaults={"stock": book.stock, "reserved_stock": 0},
    )
    return inventory_item


@transaction.atomic
def reserve_stock(book, quantity):
    inventory_item = get_or_create_inventory_item(book)
    inventory_item = InventoryItem.objects.select_for_update().get(book=inventory_item.book)
    available = inventory_item.stock - inventory_item.reserved_stock
    if quantity > available:
        raise InventoryError("Stock insuficiente para el libro seleccionado.")
    inventory_item.reserved_stock += quantity
    inventory_item.save(update_fields=["reserved_stock", "updated_at"])
    return inventory_item


@transaction.atomic
def release_stock(book, quantity):
    inventory_item = get_or_create_inventory_item(book)
    inventory_item = InventoryItem.objects.select_for_update().get(book=inventory_item.book)
    inventory_item.reserved_stock = max(inventory_item.reserved_stock - quantity, 0)
    inventory_item.save(update_fields=["reserved_stock", "updated_at"])
    return inventory_item


@transaction.atomic
def consume_reserved_stock(book, quantity):
    inventory_item = get_or_create_inventory_item(book)
    inventory_item = InventoryItem.objects.select_for_update().get(book=inventory_item.book)
    if quantity > inventory_item.reserved_stock:
        raise InventoryError("No existe stock reservado suficiente para confirmar la venta.")
    if quantity > inventory_item.stock:
        raise InventoryError("Stock total insuficiente para confirmar la venta.")
    inventory_item.reserved_stock -= quantity
    inventory_item.stock -= quantity
    inventory_item.save(update_fields=["reserved_stock", "stock", "updated_at"])
    return inventory_item


def get_inventory_queryset():
    return InventoryItem.objects.select_related("book", "book__obra__autor", "book__obra__genero", "book__editorial")


def inventory_monitoring_snapshot():
    qs = get_inventory_queryset()
    totals = qs.aggregate(total_stock=Sum("stock"), total_reserved=Sum("reserved_stock"))
    low_stock = []
    for row in qs:
        if row.available_stock <= 5:
            low_stock.append(
                {
                    "book_id": row.book_id,
                    "book": row.book.nombre,
                    "author": row.book.obra.autor.nombre,
                    "editorial": row.book.editorial.nombre,
                    "stock": row.stock,
                    "reserved_stock": row.reserved_stock,
                    "available_stock": row.available_stock,
                }
            )
    return {
        "total_stock": totals["total_stock"] or 0,
        "total_reserved_stock": totals["total_reserved"] or 0,
        "low_stock_books": low_stock,
    }
