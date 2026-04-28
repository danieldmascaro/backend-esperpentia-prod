from django.db import models


class ProductoBase(models.Model):
    class Moneda(models.TextChoices):
        CLP = "CLP", "Peso chileno"
        USD = "USD", "Dolar"

    nombre = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    sku = models.CharField(max_length=64, unique=True)
    imagen = models.ImageField(upload_to="libros/%Y/%m/", blank=True, null=True)
    descripcion = models.TextField(blank=True)
    descripcion_corta = models.CharField(max_length=300, blank=True)
    precio = models.DecimalField(max_digits=12, decimal_places=0)
    precio_referencia = models.DecimalField(max_digits=12, decimal_places=0, blank=True, null=True)
    moneda = models.CharField(max_length=3, choices=Moneda.choices, default=Moneda.CLP)
    stock = models.PositiveIntegerField(default=0)
    gestionar_stock = models.BooleanField(default=True)
    peso_kg = models.DecimalField(max_digits=8, decimal_places=3, blank=True, null=True)
    alto_cm = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    ancho_cm = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    largo_cm = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    activo = models.BooleanField(default=True)
    destacado = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ("-creado_en",)

    def __str__(self):
        return self.nombre


class Autor(models.Model):
    nombre = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=280, unique=True)
    imagen = models.ImageField(upload_to="autores/%Y/%m/", blank=True, null=True)
    fecha_nacimiento = models.DateField(blank=True, null=True)
    nacionalidad = models.CharField(max_length=120, blank=True)
    biografia = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class Genero(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    slug = models.SlugField(max_length=140, unique=True)
    descripcion = models.TextField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class Editorial(models.Model):
    nombre = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=280, unique=True)
    imagen = models.ImageField(upload_to="editoriales/%Y/%m/", blank=True, null=True)
    descripcion = models.TextField(blank=True)
    sitio_web = models.URLField(blank=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("nombre",)

    def __str__(self):
        return self.nombre


class Obra(models.Model):
    titulo = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True)
    autor = models.ForeignKey(Autor, related_name="obras", on_delete=models.CASCADE)
    genero = models.ForeignKey(Genero, related_name="obras", on_delete=models.CASCADE)
    descripcion = models.TextField(blank=True)
    descripcion_corta = models.CharField(max_length=300, blank=True)
    fecha_publicacion = models.DateField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("titulo",)
        unique_together = ("titulo", "autor")

    def __str__(self):
        return self.titulo


class Libro(ProductoBase):
    class TipoTapa(models.TextChoices):
        DURA = "DURA", "Tapa dura"
        BLANDA = "BLANDA", "Tapa blanda"

    obra = models.ForeignKey(Obra, related_name="libros", on_delete=models.CASCADE)
    editorial = models.ForeignKey(Editorial, related_name="libros", on_delete=models.CASCADE)
    tipo_tapa = models.CharField(max_length=10, choices=TipoTapa.choices)
    cantidad_paginas = models.PositiveIntegerField()
    isbn = models.CharField(max_length=20, blank=True)
    idioma = models.CharField(max_length=60, default="es")
    anio_publicacion = models.PositiveIntegerField(blank=True, null=True)

    class Meta(ProductoBase.Meta):
        ordering = ("-creado_en",)

    def save(self, *args, **kwargs):
        if self.obra_id:
            self.nombre = self.obra.titulo
        super().save(*args, **kwargs)

    @property
    def autor(self):
        return self.obra.autor

    @property
    def genero(self):
        return self.obra.genero
