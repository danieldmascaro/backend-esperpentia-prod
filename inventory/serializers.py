from rest_framework import serializers

from .models import InventoryItem


class InventoryItemSerializer(serializers.ModelSerializer):
    book_id = serializers.IntegerField(source="book.id", read_only=True)
    book_title = serializers.CharField(source="book.nombre", read_only=True)
    author_name = serializers.CharField(source="book.obra.autor.nombre", read_only=True)
    editorial_name = serializers.CharField(source="book.editorial.nombre", read_only=True)
    genre_name = serializers.CharField(source="book.obra.genero.nombre", read_only=True)
    available_stock = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = (
            "book_id",
            "book_title",
            "author_name",
            "editorial_name",
            "genre_name",
            "stock",
            "reserved_stock",
            "available_stock",
            "updated_at",
        )

    def get_available_stock(self, obj):
        return obj.available_stock


class InventoryUpdateSerializer(serializers.Serializer):
    stock = serializers.IntegerField(min_value=0, required=False)
    reserved_stock = serializers.IntegerField(min_value=0, required=False)
