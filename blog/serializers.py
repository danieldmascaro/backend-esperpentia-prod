from rest_framework import serializers

from .models import BlogPost, BlogPostImage


class BlogPostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPostImage
        fields = ("id", "post", "imagen", "alt_text", "orden", "creado_en")
        read_only_fields = ("id", "creado_en")


class BlogPostNestedImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlogPostImage
        fields = ("id", "imagen", "alt_text", "orden", "creado_en")
        read_only_fields = ("id", "creado_en")


class BlogPostSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField(read_only=True)
    imagenes = BlogPostNestedImageSerializer(many=True, read_only=True)
    imagenes_data = BlogPostNestedImageSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = BlogPost
        fields = (
            "id",
            "titulo",
            "slug",
            "resumen",
            "contenido",
            "imagen_principal",
            "status",
            "publicado_en",
            "autor_nombre",
            "imagenes",
            "imagenes_data",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("id", "autor_nombre", "creado_en", "actualizado_en")

    def get_autor_nombre(self, obj):
        if not obj.autor_id:
            return ""

        nombre = getattr(obj.autor, "nombre", "") or ""
        apellido = getattr(obj.autor, "apellido", "") or ""
        full_name = f"{nombre} {apellido}".strip()
        return full_name or nombre or "Autor"

    def create(self, validated_data):
        imagenes_data = validated_data.pop("imagenes_data", [])
        post = super().create(validated_data)
        if imagenes_data:
            BlogPostImage.objects.bulk_create(
                [BlogPostImage(post=post, **image_data) for image_data in imagenes_data]
            )
        return post

    def update(self, instance, validated_data):
        imagenes_data = validated_data.pop("imagenes_data", None)
        post = super().update(instance, validated_data)
        if imagenes_data is not None:
            post.imagenes.all().delete()
            if imagenes_data:
                BlogPostImage.objects.bulk_create(
                    [BlogPostImage(post=post, **image_data) for image_data in imagenes_data]
                )
        return post
