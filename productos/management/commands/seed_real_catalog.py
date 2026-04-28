import json
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from productos.models import Autor, Editorial, Genero, Libro, Obra

BOOK_POOL = [
    {
        "title": "1984",
        "author": "George Orwell",
        "genre": "Distopia",
        "publisher": "Signet Classics",
        "isbn": "9780451524935",
        "pages": 328,
        "year": 1950,
        "description": "Una novela clasica sobre vigilancia estatal y control totalitario.",
    },
    {
        "title": "Animal Farm",
        "author": "George Orwell",
        "genre": "Satira politica",
        "publisher": "Signet Classics",
        "isbn": "9780451526342",
        "pages": 112,
        "year": 1954,
        "description": "Fabula politica sobre poder, propaganda y corrupcion.",
    },
    {
        "title": "Pride and Prejudice",
        "author": "Jane Austen",
        "genre": "Novela romantica",
        "publisher": "Penguin Classics",
        "isbn": "9780141439518",
        "pages": 480,
        "year": 2002,
        "description": "Una de las novelas mas influyentes de la literatura inglesa.",
    },
    {
        "title": "Jane Eyre",
        "author": "Charlotte Bronte",
        "genre": "Clasico",
        "publisher": "Penguin Classics",
        "isbn": "9780142437209",
        "pages": 624,
        "year": 2006,
        "description": "Historia de independencia, amor y formacion personal.",
    },
    {
        "title": "Wuthering Heights",
        "author": "Emily Bronte",
        "genre": "Clasico",
        "publisher": "Penguin Classics",
        "isbn": "9780141439556",
        "pages": 416,
        "year": 2003,
        "description": "Relato oscuro e intenso sobre pasion y venganza.",
    },
    {
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "genre": "Clasico",
        "publisher": "Scribner",
        "isbn": "9780743273565",
        "pages": 180,
        "year": 2004,
        "description": "Retrato de la sociedad norteamericana de los anos 20.",
    },
    {
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "genre": "Drama",
        "publisher": "Harper Perennial",
        "isbn": "9780061120084",
        "pages": 336,
        "year": 2006,
        "description": "Novela sobre justicia, racismo y crecimiento moral.",
    },
    {
        "title": "The Catcher in the Rye",
        "author": "J. D. Salinger",
        "genre": "Coming of age",
        "publisher": "Little, Brown and Company",
        "isbn": "9780316769488",
        "pages": 277,
        "year": 1991,
        "description": "Clasico moderno narrado por un adolescente inconforme.",
    },
    {
        "title": "Fahrenheit 451",
        "author": "Ray Bradbury",
        "genre": "Ciencia ficcion",
        "publisher": "Simon & Schuster",
        "isbn": "9781451673319",
        "pages": 256,
        "year": 2012,
        "description": "Distopia sobre censura y destruccion del pensamiento critico.",
    },
    {
        "title": "Brave New World",
        "author": "Aldous Huxley",
        "genre": "Distopia",
        "publisher": "Harper Perennial",
        "isbn": "9780060850524",
        "pages": 288,
        "year": 2006,
        "description": "Mundo futurista dominado por tecnologia y condicionamiento social.",
    },
    {
        "title": "Dune",
        "author": "Frank Herbert",
        "genre": "Ciencia ficcion",
        "publisher": "Ace",
        "isbn": "9780441172719",
        "pages": 896,
        "year": 1990,
        "description": "Epic fantasy sci-fi sobre politica, ecologia y destino.",
    },
    {
        "title": "The Hobbit",
        "author": "J. R. R. Tolkien",
        "genre": "Fantasia",
        "publisher": "Mariner Books",
        "isbn": "9780547928227",
        "pages": 300,
        "year": 2012,
        "description": "Aventura fantastica que precede a El Senor de los Anillos.",
    },
    {
        "title": "The Fellowship of the Ring",
        "author": "J. R. R. Tolkien",
        "genre": "Fantasia",
        "publisher": "Mariner Books",
        "isbn": "9780547928210",
        "pages": 432,
        "year": 2012,
        "description": "Primera parte de la trilogia El Senor de los Anillos.",
    },
    {
        "title": "The Two Towers",
        "author": "J. R. R. Tolkien",
        "genre": "Fantasia",
        "publisher": "Mariner Books",
        "isbn": "9780547928203",
        "pages": 352,
        "year": 2012,
        "description": "Segunda parte de la trilogia El Senor de los Anillos.",
    },
    {
        "title": "The Return of the King",
        "author": "J. R. R. Tolkien",
        "genre": "Fantasia",
        "publisher": "Mariner Books",
        "isbn": "9780547928197",
        "pages": 432,
        "year": 2012,
        "description": "Cierre epico de la trilogia El Senor de los Anillos.",
    },
    {
        "title": "Harry Potter and the Sorcerer's Stone",
        "author": "J. K. Rowling",
        "genre": "Fantasia juvenil",
        "publisher": "Scholastic",
        "isbn": "9780590353427",
        "pages": 320,
        "year": 1998,
        "description": "Inicio de la saga de magia mas popular de las ultimas decadas.",
    },
    {
        "title": "Harry Potter and the Chamber of Secrets",
        "author": "J. K. Rowling",
        "genre": "Fantasia juvenil",
        "publisher": "Scholastic",
        "isbn": "9780439064873",
        "pages": 352,
        "year": 1999,
        "description": "Segunda entrega de la saga de Harry Potter.",
    },
    {
        "title": "Harry Potter and the Prisoner of Azkaban",
        "author": "J. K. Rowling",
        "genre": "Fantasia juvenil",
        "publisher": "Scholastic",
        "isbn": "9780439136365",
        "pages": 448,
        "year": 1999,
        "description": "Tercera novela de la saga de Harry Potter.",
    },
    {
        "title": "A Game of Thrones",
        "author": "George R. R. Martin",
        "genre": "Fantasia epica",
        "publisher": "Bantam",
        "isbn": "9780553593716",
        "pages": 864,
        "year": 2005,
        "description": "Primera novela de Cancion de Hielo y Fuego.",
    },
    {
        "title": "The Name of the Wind",
        "author": "Patrick Rothfuss",
        "genre": "Fantasia",
        "publisher": "DAW",
        "isbn": "9780756404741",
        "pages": 672,
        "year": 2008,
        "description": "Primera parte de Cronica del Asesino de Reyes.",
    },
]


class Command(BaseCommand):
    help = "Reemplaza el catálogo completo por un pool de ~20 libros reales con portadas reales."

    def _fetch_image_bytes(self, url):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0", "Accept": "image/*"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            content_type = response.headers.get("Content-Type", "")
            if "image" not in content_type:
                return None
            return response.read()

    def _resolve_cover_image(self, book_data):
        isbn = book_data["isbn"]
        isbn_url = f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false"
        try:
            image = self._fetch_image_bytes(isbn_url)
            if image:
                return image
        except Exception:
            pass

        query = urllib.parse.urlencode(
            {
                "title": book_data["title"],
                "author": book_data["author"],
                "limit": 5,
            }
        )
        search_url = f"https://openlibrary.org/search.json?{query}"

        try:
            request = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            docs = payload.get("docs", [])
        except Exception:
            return None

        for doc in docs:
            cover_id = doc.get("cover_i")
            if not cover_id:
                continue
            cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg?default=false"
            try:
                image = self._fetch_image_bytes(cover_url)
                if image:
                    return image
            except Exception:
                continue

        return None

    @transaction.atomic
    def handle(self, *args, **options):
        media_books_path = Path(settings.MEDIA_ROOT) / "libros"
        if media_books_path.exists():
            shutil.rmtree(media_books_path)

        self.stdout.write("Borrando catálogo actual...")
        Libro.objects.all().delete()
        Obra.objects.all().delete()
        Autor.objects.all().delete()
        Genero.objects.all().delete()
        Editorial.objects.all().delete()

        self.stdout.write("Creando nuevo pool de libros reales...")

        for index, entry in enumerate(BOOK_POOL, start=1):
            author, _ = Autor.objects.get_or_create(
                nombre=entry["author"],
                defaults={
                    "slug": slugify(entry["author"]),
                    "biografia": f"Autor/a real de la obra '{entry['title']}'.",
                },
            )

            genre, _ = Genero.objects.get_or_create(
                nombre=entry["genre"],
                defaults={
                    "slug": slugify(entry["genre"]),
                    "descripcion": f"genero literario: {entry['genre']}",
                },
            )

            publisher, _ = Editorial.objects.get_or_create(
                nombre=entry["publisher"],
                defaults={
                    "slug": slugify(entry["publisher"]),
                    "descripcion": f"Editorial real para '{entry['title']}'.",
                },
            )

            obra_slug = slugify(f"{entry['title']}-{entry['author']}")
            obra, _ = Obra.objects.get_or_create(
                titulo=entry["title"],
                autor=author,
                defaults={
                    "slug": obra_slug,
                    "genero": genre,
                    "descripcion": entry["description"],
                    "descripcion_corta": entry["description"][:280],
                },
            )

            libro = Libro.objects.create(
                obra=obra,
                editorial=publisher,
                slug=slugify(f"{entry['title']}-{entry['isbn'][-6:]}"),
                sku=f"REAL-{index:04d}",
                descripcion=entry["description"],
                descripcion_corta=entry["description"][:280],
                precio=14990 + (index * 500),
                moneda="CLP",
                stock=30,
                Gestiónar_stock=True,
                peso_kg=0.45,
                alto_cm=23,
                ancho_cm=15,
                largo_cm=3,
                activo=True,
                destacado=index <= 6,
                tipo_tapa=Libro.TipoTapa.BLANDA,
                cantidad_paginas=entry["pages"],
                isbn=entry["isbn"],
                idioma="en",
                año_publicación=entry["year"],
            )

            image_bytes = self._resolve_cover_image(entry)
            if image_bytes:
                filename = f"seed/{slugify(entry['author'])}-{slugify(entry['title'])}.jpg"
                libro.imagen.save(filename, ContentFile(image_bytes), save=True)

        self.stdout.write(self.style.SUCCESS(f"catálogo real cargado: {len(BOOK_POOL)} libros."))




