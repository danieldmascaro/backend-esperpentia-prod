import argparse
import json
import mimetypes
import os
import shutil
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.core import serializers  # noqa: E402
from django.utils import timezone  # noqa: E402

from checkout.models import CartItem  # noqa: E402
from inventory.models import InventoryItem  # noqa: E402
from productos.models import Autor, Editorial, Genero, Libro, Obra  # noqa: E402
from ventas.models import VentaItem  # noqa: E402


DEFAULT_BACKEND_URL = "https://backend-esperpentia-prod.onrender.com"
BACKUP_MODELS = (Autor, Genero, Editorial, Obra, Libro, CartItem, InventoryItem, VentaItem)


def encode_value(value):
    if isinstance(value, Decimal):
        return str(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def image_path(image_field):
    if not image_field or not image_field.name:
        return None
    name = image_field.name
    if name.startswith(("http://", "https://")):
        return None
    path = Path(settings.MEDIA_ROOT) / name
    return path if path.exists() else None


def relative_media_name(path):
    if not path:
        return None
    try:
        return path.relative_to(settings.MEDIA_ROOT).as_posix()
    except ValueError:
        return path.name


def collect_snapshot():
    authors = []
    for author in Autor.objects.order_by("id"):
        local_image = image_path(author.imagen)
        authors.append(
            {
                "old_id": author.id,
                "nombre": author.nombre,
                "slug": author.slug,
                "imagen": relative_media_name(local_image),
                "fecha_nacimiento": encode_value(author.fecha_nacimiento) or "",
                "nacionalidad": author.nacionalidad or "",
                "biografia": author.biografia or "",
            }
        )

    genres = []
    for genre in Genero.objects.order_by("id"):
        genres.append(
            {
                "old_id": genre.id,
                "nombre": genre.nombre,
                "slug": genre.slug,
                "descripcion": genre.descripcion or "",
            }
        )

    publishers = []
    for publisher in Editorial.objects.order_by("id"):
        local_image = image_path(publisher.imagen)
        publishers.append(
            {
                "old_id": publisher.id,
                "nombre": publisher.nombre,
                "slug": publisher.slug,
                "imagen": relative_media_name(local_image),
                "descripcion": publisher.descripcion or "",
                "sitio_web": publisher.sitio_web or "",
            }
        )

    works = []
    for work in Obra.objects.select_related("autor", "genero").order_by("id"):
        works.append(
            {
                "old_id": work.id,
                "titulo": work.titulo,
                "slug": work.slug,
                "descripcion": work.descripcion or "",
                "descripcion_corta": work.descripcion_corta or "",
                "fecha_publicacion": encode_value(work.fecha_publicacion) or "",
                "autor_old_id": work.autor_id,
                "genero_old_id": work.genero_id,
            }
        )

    books = []
    for book in Libro.objects.select_related("obra", "editorial").order_by("id"):
        local_image = image_path(book.imagen)
        books.append(
            {
                "old_id": book.id,
                "slug": book.slug,
                "sku": book.sku,
                "imagen": relative_media_name(local_image),
                "descripcion": book.descripcion or "",
                "descripcion_corta": book.descripcion_corta or "",
                "precio": encode_value(book.precio),
                "precio_referencia": encode_value(book.precio_referencia) if book.precio_referencia is not None else "",
                "moneda": book.moneda,
                "stock": book.stock,
                "gestionar_stock": book.gestionar_stock,
                "peso_kg": encode_value(book.peso_kg) if book.peso_kg is not None else "",
                "alto_cm": encode_value(book.alto_cm) if book.alto_cm is not None else "",
                "ancho_cm": encode_value(book.ancho_cm) if book.ancho_cm is not None else "",
                "largo_cm": encode_value(book.largo_cm) if book.largo_cm is not None else "",
                "activo": book.activo,
                "destacado": book.destacado,
                "obra_old_id": book.obra_id,
                "editorial_old_id": book.editorial_id,
                "tipo_tapa": book.tipo_tapa,
                "cantidad_paginas": book.cantidad_paginas,
                "isbn": book.isbn or "",
                "idioma": book.idioma or "es",
                "anio_publicacion": book.anio_publicacion or "",
            }
        )

    return {
        "created_at": timezone.now().isoformat(),
        "counts": {
            "authors": len(authors),
            "genres": len(genres),
            "publishers": len(publishers),
            "works": len(works),
            "books": len(books),
            "cart_items": CartItem.objects.count(),
            "inventory_items": InventoryItem.objects.count(),
            "venta_items": VentaItem.objects.count(),
        },
        "authors": authors,
        "genres": genres,
        "publishers": publishers,
        "works": works,
        "books": books,
    }


def write_backup(snapshot, backup_dir):
    backup_dir.mkdir(parents=True, exist_ok=True)
    media_dir = backup_dir / "media"
    media_dir.mkdir(parents=True, exist_ok=True)

    (backup_dir / "catalog_snapshot.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    objects = []
    for model in BACKUP_MODELS:
        objects.extend(model.objects.all())
    (backup_dir / "django_dump.json").write_text(
        serializers.serialize("json", objects, indent=2),
        encoding="utf-8",
    )

    copied = []
    for group in ("authors", "publishers", "books"):
        for item in snapshot[group]:
            media_name = item.get("imagen")
            if not media_name:
                continue
            source = Path(settings.MEDIA_ROOT) / media_name
            if not source.exists():
                continue
            target = media_dir / media_name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(media_name)

    (backup_dir / "summary.json").write_text(
        json.dumps({"counts": snapshot["counts"], "media_files_copied": copied}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def require_success(response, action):
    if response.status_code >= 400:
        raise RuntimeError(f"{action} failed: HTTP {response.status_code} {response.text[:500]}")
    return response


def fetch_all(session, base_url, endpoint):
    url = f"{base_url}{endpoint}"
    rows = []
    while url:
        response = require_success(session.get(url, timeout=60), f"GET {url}")
        payload = response.json()
        if isinstance(payload, list):
            rows.extend(payload)
            break
        rows.extend(payload.get("results", []))
        url = payload.get("next")
    return rows


def create_temp_admin(password):
    User = get_user_model()
    email = f"catalog-loader-{uuid.uuid4().hex[:12]}@esperpentia.local"
    user = User.objects.create_superuser(
        email=email,
        nombre="Catalog",
        apellido="Loader",
        telefono="+000000000",
        password=password,
    )
    return user


def login_admin(session, base_url, email, password):
    csrf_response = require_success(session.get(f"{base_url}/auth/csrf/", timeout=60), "GET csrf")
    csrf_token = csrf_response.json()["csrfToken"]
    response = require_success(
        session.post(
            f"{base_url}/auth/jwt/create/",
            json={"email": email, "password": password},
            headers={
                "Origin": base_url,
                "Referer": f"{base_url}/auth/csrf/",
                "X-CSRFToken": csrf_token,
            },
            timeout=60,
        ),
        "POST jwt create",
    )
    return response.json()["access"]


def auth_headers(access_token):
    return {"Authorization": f"Bearer {access_token}"}


def delete_endpoint_rows(session, base_url, access_token, endpoint, label):
    rows = fetch_all(session, base_url, endpoint)
    for row in rows:
        response = session.delete(
            f"{base_url}{endpoint}{row['id']}/",
            headers=auth_headers(access_token),
            timeout=60,
        )
        if response.status_code not in (200, 202, 204, 404):
            raise RuntimeError(f"DELETE {label} {row['id']} failed: HTTP {response.status_code} {response.text[:500]}")
    return len(rows)


def post_json(session, base_url, access_token, endpoint, payload, label):
    response = require_success(
        session.post(
            f"{base_url}{endpoint}",
            json=payload,
            headers=auth_headers(access_token),
            timeout=60,
        ),
        f"POST {label}",
    )
    return response.json()


def post_form(session, base_url, access_token, endpoint, payload, image_media_name, label):
    files = None
    opened_file = None
    try:
        if image_media_name:
            path = Path(settings.MEDIA_ROOT) / image_media_name
            if path.exists():
                content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
                opened_file = path.open("rb")
                files = {"imagen": (path.name, opened_file, content_type)}

        response = require_success(
            session.post(
                f"{base_url}{endpoint}",
                data=payload,
                files=files,
                headers=auth_headers(access_token),
                timeout=120,
            ),
            f"POST {label}",
        )
        return response.json()
    finally:
        if opened_file:
            opened_file.close()


def bool_form(value):
    return "true" if value else "false"


def drop_empty(payload, keys):
    for key in keys:
        if payload.get(key) in ("", None):
            payload.pop(key, None)
    return payload


def reload_catalog(snapshot, base_url, access_token):
    session = requests.Session()

    deleted = {
        "books": delete_endpoint_rows(session, base_url, access_token, "/catalog/books/", "book"),
        "works": delete_endpoint_rows(session, base_url, access_token, "/catalog/works/", "work"),
        "authors": delete_endpoint_rows(session, base_url, access_token, "/catalog/authors/", "author"),
        "genres": delete_endpoint_rows(session, base_url, access_token, "/catalog/genres/", "genre"),
        "publishers": delete_endpoint_rows(session, base_url, access_token, "/catalog/publishers/", "publisher"),
    }

    author_ids = {}
    for item in snapshot["authors"]:
        payload = {
            "nombre": item["nombre"],
            "slug": item["slug"],
            "fecha_nacimiento": item["fecha_nacimiento"],
            "nacionalidad": item["nacionalidad"],
            "biografia": item["biografia"],
        }
        drop_empty(payload, ("fecha_nacimiento",))
        created = post_form(session, base_url, access_token, "/catalog/authors/", payload, item["imagen"], "author")
        author_ids[item["old_id"]] = created["id"]

    genre_ids = {}
    for item in snapshot["genres"]:
        created = post_json(
            session,
            base_url,
            access_token,
            "/catalog/genres/",
            {"nombre": item["nombre"], "slug": item["slug"], "descripcion": item["descripcion"]},
            "genre",
        )
        genre_ids[item["old_id"]] = created["id"]

    publisher_ids = {}
    for item in snapshot["publishers"]:
        payload = {
            "nombre": item["nombre"],
            "slug": item["slug"],
            "descripcion": item["descripcion"],
            "sitio_web": item["sitio_web"],
        }
        created = post_form(session, base_url, access_token, "/catalog/publishers/", payload, item["imagen"], "publisher")
        publisher_ids[item["old_id"]] = created["id"]

    work_ids = {}
    for item in snapshot["works"]:
        payload = {
            "titulo": item["titulo"],
            "slug": item["slug"],
            "descripcion": item["descripcion"],
            "descripcion_corta": item["descripcion_corta"],
            "fecha_publicacion": item["fecha_publicacion"],
            "autor_id": author_ids[item["autor_old_id"]],
            "genero_id": genre_ids[item["genero_old_id"]],
        }
        drop_empty(payload, ("fecha_publicacion",))
        created = post_json(session, base_url, access_token, "/catalog/works/", payload, "work")
        work_ids[item["old_id"]] = created["id"]

    created_books = []
    for item in snapshot["books"]:
        payload = {
            "slug": item["slug"],
            "sku": item["sku"],
            "descripcion": item["descripcion"],
            "descripcion_corta": item["descripcion_corta"],
            "precio": item["precio"],
            "precio_referencia": item["precio_referencia"],
            "moneda": item["moneda"],
            "stock": str(item["stock"]),
            "gestionar_stock": bool_form(item["gestionar_stock"]),
            "peso_kg": item["peso_kg"],
            "alto_cm": item["alto_cm"],
            "ancho_cm": item["ancho_cm"],
            "largo_cm": item["largo_cm"],
            "activo": bool_form(item["activo"]),
            "destacado": bool_form(item["destacado"]),
            "obra_id": str(work_ids[item["obra_old_id"]]),
            "editorial_id": str(publisher_ids[item["editorial_old_id"]]),
            "tipo_tapa": item["tipo_tapa"],
            "cantidad_paginas": str(item["cantidad_paginas"]),
            "isbn": item["isbn"],
            "idioma": item["idioma"],
            "anio_publicacion": str(item["anio_publicacion"]),
        }
        drop_empty(
            payload,
            (
                "precio_referencia",
                "peso_kg",
                "alto_cm",
                "ancho_cm",
                "largo_cm",
                "anio_publicacion",
            ),
        )
        created = post_form(session, base_url, access_token, "/catalog/books/", payload, item["imagen"], "book")
        created_books.append(created)

    return deleted, created_books


def validate_catalog(base_url):
    session = requests.Session()
    books = fetch_all(session, base_url, "/catalog/books/")
    image_checks = []
    for book in books:
        image_url = book.get("imagen")
        if not image_url:
            image_checks.append({"id": book["id"], "nombre": book["nombre"], "status": None})
            continue
        try:
            response = session.get(image_url, timeout=60, stream=True)
            response.close()
            status_code = response.status_code
        except requests.RequestException:
            status_code = "error"
        image_checks.append({"id": book["id"], "nombre": book["nombre"], "status": status_code, "url": image_url})
    return books, image_checks


def main():
    parser = argparse.ArgumentParser(description="Backup and reload the Render catalog through the production API.")
    parser.add_argument("--backend-url", default=DEFAULT_BACKEND_URL)
    parser.add_argument("--backup-dir", default="")
    parser.add_argument("--backup-only", action="store_true")
    parser.add_argument("--from-backup-dir", default="")
    args = parser.parse_args()

    base_url = args.backend_url.rstrip("/")
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(args.backup_dir) if args.backup_dir else Path(settings.BASE_DIR) / "backups" / f"catalog_render_{timestamp}"

    if args.from_backup_dir:
        backup_dir = Path(args.from_backup_dir)
        snapshot = json.loads((backup_dir / "catalog_snapshot.json").read_text(encoding="utf-8"))
        print(f"Using backup from {backup_dir}")
    else:
        snapshot = collect_snapshot()
        write_backup(snapshot, backup_dir)
        print(f"Backup written to {backup_dir}")

    print(json.dumps(snapshot["counts"], ensure_ascii=False, indent=2))

    if args.backup_only:
        return 0

    password = uuid.uuid4().hex + uuid.uuid4().hex
    temp_admin = create_temp_admin(password)
    try:
        login_session = requests.Session()
        access_token = login_admin(login_session, base_url, temp_admin.email, password)
        deleted, created_books = reload_catalog(snapshot, base_url, access_token)
        books, image_checks = validate_catalog(base_url)

        validation_path = backup_dir / "post_reload_validation.json"
        validation_path.write_text(
            json.dumps(
                {
                    "deleted": deleted,
                    "created_books": len(created_books),
                    "published_books": len(books),
                    "image_checks": image_checks,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        failed_images = [item for item in image_checks if item["status"] != 200]
        print(json.dumps({"deleted": deleted, "created_books": len(created_books), "published_books": len(books)}, indent=2))
        if failed_images:
            print(f"WARNING: {len(failed_images)} image URLs did not return HTTP 200. See {validation_path}", file=sys.stderr)
            return 2
        print(f"Validation written to {validation_path}")
        return 0
    finally:
        temp_admin.delete()


if __name__ == "__main__":
    raise SystemExit(main())
