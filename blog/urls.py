from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import BlogPostImageViewSet, BlogPostViewSet

router = DefaultRouter()
router.register(r"posts", BlogPostViewSet, basename="blog-posts")
router.register(r"post-images", BlogPostImageViewSet, basename="blog-post-images")

urlpatterns = [
    path("", include(router.urls)),
]

