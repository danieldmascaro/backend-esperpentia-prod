from django import forms
from django.contrib import admin
from django.db import models
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import Autor, Editorial, Genero, Libro, Obra


def build_unique_slug(model, seed, instance_pk=None):
    base_slug = slugify(seed) or "item"
    slug = base_slug
    counter = 2
    queryset = model.objects.all()
    if instance_pk:
        queryset = queryset.exclude(pk=instance_pk)
    while queryset.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


class OptionalSlugModelForm(forms.ModelForm):
    slug_source_field = ""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["slug"].required = False

    def clean_slug(self):
        slug = self.cleaned_data.get("slug")
        if slug:
            return slugify(slug)
        source = self.cleaned_data.get(self.slug_source_field)
        return build_unique_slug(self._meta.model, source, getattr(self.instance, "pk", None))


class AutorAdminForm(OptionalSlugModelForm):
    slug_source_field = "nombre"

    class Meta:
        model = Autor
        fields = "__all__"


class GeneroAdminForm(OptionalSlugModelForm):
    slug_source_field = "nombre"

    class Meta:
        model = Genero
        fields = "__all__"


class EditorialAdminForm(OptionalSlugModelForm):
    slug_source_field = "nombre"

    class Meta:
        model = Editorial
        fields = "__all__"


class ObraAdminForm(OptionalSlugModelForm):
    slug_source_field = "titulo"

    class Meta:
        model = Obra
        fields = "__all__"


class LibroAdminForm(OptionalSlugModelForm):
    slug_source_field = "obra"

    class Meta:
        model = Libro
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Placeholder para el autocomplete nativo de admin (select2).
        self.fields["obra"].widget.attrs["data-placeholder"] = "Escribe para buscar una obra..."
        self.fields["editorial"].widget.attrs["data-placeholder"] = "Escribe para buscar una editorial..."


class FriendlyAdminMixin:
    save_on_top = True
    list_per_page = 25
    formfield_overrides = {
        models.CharField: {"widget": forms.TextInput(attrs={"style": "width: min(600px, 100%);"})},
        models.TextField: {"widget": forms.Textarea(attrs={"rows": 3})},
    }


@admin.register(Autor)
class AutorAdmin(FriendlyAdminMixin, admin.ModelAdmin):
    form = AutorAdminForm
    list_display = ("nombre", "nacionalidad", "fecha_nacimiento", "slug", "creado_en")
    search_fields = ("nombre", "slug", "nacionalidad")
    readonly_fields = ("creado_en", "actualizado_en")
    fieldsets = (
        (
            _("Datos del autor"),
            {"fields": ("nombre", "slug", "imagen", "fecha_nacimiento", "nacionalidad", "biografia")},
        ),
        (_("Fechas"), {"fields": ("creado_en", "actualizado_en"), "classes": ("collapse",)}),
    )


@admin.register(Genero)
class GeneroAdmin(FriendlyAdminMixin, admin.ModelAdmin):
    form = GeneroAdminForm
    list_display = ("nombre", "slug", "creado_en")
    search_fields = ("nombre", "slug")
    readonly_fields = ("creado_en", "actualizado_en")
    fieldsets = (
        (_("Datos del genero"), {"fields": ("nombre", "slug", "descripcion")}),
        (_("Fechas"), {"fields": ("creado_en", "actualizado_en"), "classes": ("collapse",)}),
    )


@admin.register(Editorial)
class EditorialAdmin(FriendlyAdminMixin, admin.ModelAdmin):
    form = EditorialAdminForm
    list_display = ("nombre", "slug", "sitio_web", "creado_en")
    search_fields = ("nombre", "slug")
    readonly_fields = ("creado_en", "actualizado_en")
    fieldsets = (
        (_("Datos de la editorial"), {"fields": ("nombre", "slug", "imagen", "descripcion", "sitio_web")}),
        (_("Fechas"), {"fields": ("creado_en", "actualizado_en"), "classes": ("collapse",)}),
    )


@admin.register(Obra)
class ObraAdmin(FriendlyAdminMixin, admin.ModelAdmin):
    form = ObraAdminForm
    list_display = ("titulo", "autor", "genero", "fecha_publicacion", "creado_en")
    search_fields = ("titulo", "slug", "autor__nombre", "genero__nombre")
    list_filter = ("genero", "autor")
    list_select_related = ("autor", "genero")
    autocomplete_fields = ("autor", "genero")
    readonly_fields = ("creado_en", "actualizado_en")
    fieldsets = (
        (
            _("Ficha de la obra"),
            {
                "fields": (
                    "titulo",
                    "slug",
                    "autor",
                    "genero",
                    "fecha_publicacion",
                    "descripcion_corta",
                    "descripcion",
                )
            },
        ),
        (_("Fechas"), {"fields": ("creado_en", "actualizado_en"), "classes": ("collapse",)}),
    )


@admin.register(Libro)
class LibroAdmin(FriendlyAdminMixin, admin.ModelAdmin):
    form = LibroAdminForm
    list_display = (
        "portada_preview_small",
        "nombre",
        "autor_nombre",
        "editorial",
        "genero_nombre",
        "tipo_tapa",
        "precio",
        "stock",
        "activo",
    )
    search_fields = ("nombre", "obra__titulo", "obra__autor__nombre", "editorial__nombre", "sku", "isbn")
    list_filter = ("tipo_tapa", "activo", "destacado", "editorial", "obra__genero")
    list_select_related = ("obra__autor", "obra__genero", "editorial")
    autocomplete_fields = ("obra", "editorial")
    exclude = ("nombre",)
    readonly_fields = ("portada_preview", "creado_en", "actualizado_en")
    actions = ("marcar_activos", "marcar_inactivos", "marcar_destacados")

    class Media:
        css = {"all": ("productos/admin.css",)}

    def get_form(self, request, obj=None, change=False, **kwargs):
        form = super().get_form(request, obj=obj, change=change, **kwargs)
        placeholders = {
            "obra": "Escribe para buscar una obra...",
            "editorial": "Escribe para buscar una editorial...",
        }
        for field_name, placeholder in placeholders.items():
            if field_name in form.base_fields:
                widget = form.base_fields[field_name].widget
                widget.attrs["data-placeholder"] = placeholder
                widget.attrs["style"] = "width: 100%;"
        return form

    fieldsets = (
        (
            _("Libro"),
            {
                "description": _("Completa este formulario una sola vez para crear el libro."),
                "fields": (
                    "obra",
                    "editorial",
                    "slug",
                    "sku",
                    "descripcion_corta",
                    "descripcion",
                    "imagen",
                    "portada_preview",
                    "tipo_tapa",
                    "cantidad_paginas",
                    "isbn",
                    "idioma",
                    "anio_publicacion",
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
                    "creado_en",
                    "actualizado_en",
                ),
            },
        ),
    )

    @admin.display(description="Portada")
    def portada_preview_small(self, obj):
        if not obj.imagen:
            return "Sin imagen"
        return format_html('<img src="{}" style="height:40px;border-radius:4px;" />', obj.imagen.url)

    @admin.display(description="Vista previa")
    def portada_preview(self, obj):
        if not obj or not obj.imagen:
            return "Todavia no hay portada."
        return format_html('<img src="{}" style="max-height:240px;border-radius:8px;" />', obj.imagen.url)

    @admin.action(description="Marcar como activos")
    def marcar_activos(self, request, queryset):
        queryset.update(activo=True)

    @admin.action(description="Marcar como inactivos")
    def marcar_inactivos(self, request, queryset):
        queryset.update(activo=False)

    @admin.action(description="Marcar como destacados")
    def marcar_destacados(self, request, queryset):
        queryset.update(destacado=True)

    @admin.display(ordering="obra__autor__nombre", description="Autor")
    def autor_nombre(self, obj):
        return obj.obra.autor.nombre

    @admin.display(ordering="obra__genero__nombre", description="Genero")
    def genero_nombre(self, obj):
        return obj.obra.genero.nombre

admin.site.site_title = "Esperpentia Admin"
admin.site.site_header = "Esperpentia Admin"
admin.site.index_title = "Esperpentia Admin"
