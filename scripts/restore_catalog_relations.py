import argparse
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from checkout.models import Cart, CartItem  # noqa: E402
from inventory.models import InventoryItem  # noqa: E402
from productos.models import Libro  # noqa: E402
from ventas.models import VentaItem  # noqa: E402


def load_backup(backup_dir):
    backup_dir = Path(backup_dir)
    snapshot = json.loads((backup_dir / "catalog_snapshot.json").read_text(encoding="utf-8"))
    dump = json.loads((backup_dir / "django_dump.json").read_text(encoding="utf-8"))
    return snapshot, dump


def build_old_book_to_new_book(snapshot):
    old_book_to_sku = {book["old_id"]: book["sku"] for book in snapshot["books"]}
    new_by_sku = {book.sku: book for book in Libro.objects.all()}
    return {
        old_id: new_by_sku[sku]
        for old_id, sku in old_book_to_sku.items()
        if sku in new_by_sku
    }


def restore_inventory(dump, old_book_to_new_book):
    restored = 0
    for row in dump:
        if row["model"] != "inventory.inventoryitem":
            continue
        old_book_id = row["pk"]
        book = old_book_to_new_book.get(old_book_id)
        if not book:
            continue
        fields = row["fields"]
        InventoryItem.objects.update_or_create(
            book=book,
            defaults={
                "stock": fields["stock"],
                "reserved_stock": fields["reserved_stock"],
            },
        )
        restored += 1
    return restored


def restore_cart_items(dump, old_book_to_new_book):
    restored = 0
    for row in dump:
        if row["model"] != "checkout.cartitem":
            continue
        fields = row["fields"]
        cart_id = fields["cart"]
        old_book_id = fields["book"]
        book = old_book_to_new_book.get(old_book_id)
        if not book or not Cart.objects.filter(pk=cart_id).exists():
            continue
        CartItem.objects.update_or_create(
            cart_id=cart_id,
            book=book,
            defaults={
                "quantity": fields["quantity"],
                "unit_price_snapshot": fields["unit_price_snapshot"],
                "subtotal": fields["subtotal"],
                "metadata_snapshot": fields.get("metadata_snapshot") or {},
            },
        )
        restored += 1
    return restored


def restore_venta_item_links(dump, old_book_to_new_book):
    restored = 0
    for row in dump:
        if row["model"] != "ventas.ventaitem":
            continue
        old_book_id = row["fields"].get("libro")
        book = old_book_to_new_book.get(old_book_id)
        if not book:
            continue
        updated = VentaItem.objects.filter(pk=row["pk"]).update(libro=book)
        restored += updated
    return restored


def main():
    parser = argparse.ArgumentParser(description="Restore catalog relations after a catalog reload.")
    parser.add_argument("backup_dir")
    args = parser.parse_args()

    snapshot, dump = load_backup(args.backup_dir)
    old_book_to_new_book = build_old_book_to_new_book(snapshot)

    with transaction.atomic():
        result = {
            "mapped_books": len(old_book_to_new_book),
            "inventory_items": restore_inventory(dump, old_book_to_new_book),
            "cart_items": restore_cart_items(dump, old_book_to_new_book),
            "venta_item_links": restore_venta_item_links(dump, old_book_to_new_book),
        }

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
