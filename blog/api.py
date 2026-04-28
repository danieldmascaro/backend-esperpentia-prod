from django.utils import timezone
from rest_framework.settings import api_settings
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.viewsets import ModelViewSet

from .models import BlogPost, BlogPostImage
from .permissions import BlogPostImagePermission, BlogPostPermission
from .serializers import BlogPostImageSerializer, BlogPostSerializer


class BlogPostViewSet(ModelViewSet):
    serializer_class = BlogPostSerializer
    permission_classes = [BlogPostPermission]
    search_fields = ("titulo", "resumen", "contenido", "autor__nombre", "autor__apellido")
    filterset_fields = ("status", "autor")
    ordering_fields = ("publicado_en", "creado_en", "titulo")
    ordering = ("-publicado_en", "-creado_en")

    def get_queryset(self):
        base_qs = BlogPost.objects.select_related("autor").prefetch_related("imagenes")
        user = self.request.user
        if user and user.is_authenticated and user.is_staff:
            return base_qs
        return base_qs.filter(
            status=BlogPost.Status.PUBLISHED,
            publicado_en__isnull=False,
            publicado_en__lte=timezone.now(),
        )

    def get_throttles(self):
        throttle_classes = list(api_settings.DEFAULT_THROTTLE_CLASSES)
        if self.request.method in {"GET", "HEAD", "OPTIONS"}:
            self.throttle_scope = "catalog_public"
            throttle_classes.append(ScopedRateThrottle)
        return [throttle() for throttle in throttle_classes]

    def perform_create(self, serializer):
        serializer.save(autor=self.request.user)


class BlogPostImageViewSet(ModelViewSet):
    serializer_class = BlogPostImageSerializer
    permission_classes = [BlogPostImagePermission]
    filterset_fields = ("post",)
    ordering_fields = ("orden", "creado_en")
    ordering = ("orden", "id")

    def get_queryset(self):
        base_qs = BlogPostImage.objects.select_related("post", "post__autor")
        user = self.request.user
        if user and user.is_authenticated and user.is_staff:
            return base_qs
        return base_qs.filter(
            post__status=BlogPost.Status.PUBLISHED,
            post__publicado_en__isnull=False,
            post__publicado_en__lte=timezone.now(),
        )

    def get_throttles(self):
        throttle_classes = list(api_settings.DEFAULT_THROTTLE_CLASSES)
        if self.request.method in {"GET", "HEAD", "OPTIONS"}:
            self.throttle_scope = "catalog_public"
            throttle_classes.append(ScopedRateThrottle)
        return [throttle() for throttle in throttle_classes]
