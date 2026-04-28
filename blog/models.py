from django.conf import settings
from django.db import models
from django.utils import timezone


class BlogPostQuerySet(models.QuerySet):
    def published(self):
        return self.filter(
            status=BlogPost.Status.PUBLISHED,
            publicado_en__isnull=False,
            publicado_en__lte=timezone.now(),
        )


class BlogPost(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Borrador"
        PUBLISHED = "PUBLISHED", "Publicado"

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="blog_posts",
    )
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    resumen = models.CharField(max_length=320, blank=True)
    contenido = models.TextField()
    imagen_principal = models.ImageField(upload_to="blog/posts/%Y/%m/", blank=True, null=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT, db_index=True)
    publicado_en = models.DateTimeField(blank=True, null=True, db_index=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    objects = BlogPostQuerySet.as_manager()

    class Meta:
        ordering = ("-publicado_en", "-creado_en")
        indexes = [
            models.Index(fields=["status", "publicado_en"]),
            models.Index(fields=["slug"]),
        ]

    def __str__(self):
        return self.titulo

    def save(self, *args, **kwargs):
        if self.status == self.Status.PUBLISHED and not self.publicado_en:
            self.publicado_en = timezone.now()
        if self.status == self.Status.DRAFT:
            self.publicado_en = None
        super().save(*args, **kwargs)


class BlogPostImage(models.Model):
    post = models.ForeignKey(BlogPost, on_delete=models.CASCADE, related_name="imagenes")
    imagen = models.ImageField(upload_to="blog/posts/gallery/%Y/%m/")
    alt_text = models.CharField(max_length=180, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("orden", "id")
        indexes = [
            models.Index(fields=["post", "orden"]),
        ]

    def __str__(self):
        return f"Imagen {self.id} - {self.post.titulo}"

