from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models

from .geography import generate_unique_county_code


class Region(models.Model):
    nombre = models.CharField(max_length=150, unique=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Comuna(models.Model):
    nombre = models.CharField(max_length=150)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="comunas")
    county_code = models.CharField(max_length=4, unique=True, editable=False)

    class Meta:
        ordering = ["nombre"]
        constraints = [
            models.UniqueConstraint(fields=["region", "nombre"], name="unique_comuna_por_region"),
        ]

    def __str__(self):
        return f"{self.nombre}, {self.region.nombre}"

    def save(self, *args, **kwargs):
        if not self.county_code:
            used_codes = set(
                Comuna.objects.exclude(pk=self.pk)
                .exclude(county_code__isnull=True)
                .values_list("county_code", flat=True)
            )
            self.county_code = generate_unique_county_code(self.nombre, used_codes)
        super().save(*args, **kwargs)


class UsuarioManager(BaseUserManager):
    def create_user(self, email, nombre, apellido, password=None, **extra_fields):
        if not email:
            raise ValueError("El email es obligatorio.")

        email = self.normalize_email(email)
        user = self.model(email=email, nombre=nombre, apellido=apellido, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, nombre, apellido, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser debe tener is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser debe tener is_superuser=True.")

        return self.create_user(email, nombre, apellido, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    nombre = models.CharField(max_length=150)
    apellido = models.CharField(max_length=150)
    telefono = models.CharField(max_length=32)
    direccion_entrega = models.CharField(max_length=255, blank=True, null=True)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name="usuarios", blank=True, null=True)
    comuna = models.ForeignKey(Comuna, on_delete=models.CASCADE, related_name="usuarios", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre", "apellido", "telefono"]

    def __str__(self):
        return f"{self.nombre} {self.apellido} <{self.email}>"
