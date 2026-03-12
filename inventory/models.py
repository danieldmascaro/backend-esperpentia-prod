from django.db import models


class InventoryItem(models.Model):
    book = models.OneToOneField(
        "productos.Libro",
        related_name="inventory_item",
        on_delete=models.CASCADE,
        primary_key=True,
    )
    stock = models.PositiveIntegerField(default=0)
    reserved_stock = models.PositiveIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("book",)

    @property
    def available_stock(self):
        available = self.stock - self.reserved_stock
        return available if available > 0 else 0
