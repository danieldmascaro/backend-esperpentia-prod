from django.contrib import admin

from .models import BlogPost, BlogPostImage


class BlogPostImageInline(admin.TabularInline):
    model = BlogPostImage
    extra = 1


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ("titulo", "autor", "status", "publicado_en", "creado_en")
    list_filter = ("status", "creado_en", "publicado_en")
    search_fields = ("titulo", "slug", "autor__nombre", "autor__apellido", "autor__email")
    prepopulated_fields = {"slug": ("titulo",)}
    inlines = [BlogPostImageInline]


@admin.register(BlogPostImage)
class BlogPostImageAdmin(admin.ModelAdmin):
    list_display = ("id", "post", "orden", "creado_en")
    list_filter = ("creado_en",)
    search_fields = ("post__titulo", "post__slug")

