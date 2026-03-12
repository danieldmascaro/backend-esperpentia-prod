from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Comuna, Region, Usuario


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre")
    search_fields = ("nombre",)


@admin.register(Comuna)
class ComunaAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "region")
    list_filter = ("region",)
    search_fields = ("nombre", "region__nombre")


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    model = Usuario
    list_display = ("email", "nombre", "apellido", "region", "comuna", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "region")
    ordering = ("email",)
    search_fields = ("email", "nombre", "apellido", "region__nombre", "comuna__nombre")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Informacion personal", {"fields": ("nombre", "apellido", "direccion_entrega", "region", "comuna")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "nombre", "apellido", "direccion_entrega", "region", "comuna", "password1", "password2"),
            },
        ),
    )
