from rest_framework import serializers

from .models import Autor, Editorial, Genero, Libro, Obra


class AutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Autor
        fields = (
            "id",
            "nombre",
            "slug",
            "imagen",
            "fecha_nacimiento",
            "nacionalidad",
            "biografia",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("creado_en", "actualizado_en")


class GeneroSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genero
        fields = ("id", "nombre", "slug", "descripcion", "creado_en", "actualizado_en")
        read_only_fields = ("creado_en", "actualizado_en")


class EditorialSerializer(serializers.ModelSerializer):
    class Meta:
        model = Editorial
        fields = (
            "id",
            "nombre",
            "slug",
            "imagen",
            "descripcion",
            "sitio_web",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("creado_en", "actualizado_en")


class ObraSerializer(serializers.ModelSerializer):
    autor = AutorSerializer(read_only=True)
    genero = GeneroSerializer(read_only=True)
    autor_id = serializers.PrimaryKeyRelatedField(queryset=Autor.objects.all(), source="autor", write_only=True)
    genero_id = serializers.PrimaryKeyRelatedField(queryset=Genero.objects.all(), source="genero", write_only=True)

    class Meta:
        model = Obra
        fields = (
            "id",
            "titulo",
            "slug",
            "descripcion",
            "descripcion_corta",
            "fecha_publicacion",
            "autor",
            "autor_id",
            "genero",
            "genero_id",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("creado_en", "actualizado_en")


class LibroSerializer(serializers.ModelSerializer):
    obra = ObraSerializer(read_only=True)
    obra_id = serializers.PrimaryKeyRelatedField(queryset=Obra.objects.all(), source="obra", write_only=True)
    editorial = EditorialSerializer(read_only=True)
    editorial_id = serializers.PrimaryKeyRelatedField(
        queryset=Editorial.objects.all(),
        source="editorial",
        write_only=True,
    )
    autor = AutorSerializer(source="obra.autor", read_only=True)
    genero = GeneroSerializer(source="obra.genero", read_only=True)

    class Meta:
        model = Libro
        fields = (
            "id",
            "nombre",
            "slug",
            "sku",
            "imagen",
            "descripcion",
            "descripcion_corta",
            "precio",
            "precio_referencia",
            "moneda",
            "stock",
            "gestionar_stock",
            "peso_kg",
            "alto_cm",
            "ancho_cm",
            "largo_cm",
            "activo",
            "destacado",
            "obra",
            "obra_id",
            "autor",
            "genero",
            "editorial",
            "editorial_id",
            "tipo_tapa",
            "cantidad_paginas",
            "isbn",
            "idioma",
            "anio_publicacion",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("creado_en", "actualizado_en", "nombre")
