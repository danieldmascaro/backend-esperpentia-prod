from django.db import migrations
from django.utils.text import slugify


def _table_exists(connection, table_name):
    return table_name in connection.introspection.table_names()


def _column_exists(connection, table_name, column_name):
    with connection.cursor() as cursor:
        description = connection.introspection.get_table_description(cursor, table_name)
    return any(col.name == column_name for col in description)


def _unique_slug(model, seed):
    base_slug = slugify(seed) or "item"
    slug = base_slug
    counter = 2
    while model.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def repair_catalog_schema(apps, schema_editor):
    connection = schema_editor.connection
    Autor = apps.get_model("productos", "Autor")
    Genero = apps.get_model("productos", "Genero")
    Editorial = apps.get_model("productos", "Editorial")
    Obra = apps.get_model("productos", "Obra")
    Libro = apps.get_model("productos", "Libro")

    for model in (Autor, Genero, Editorial, Obra):
        if not _table_exists(connection, model._meta.db_table):
            schema_editor.create_model(model)

    libro_table = Libro._meta.db_table
    if not _table_exists(connection, libro_table):
        schema_editor.create_model(Libro)
        return

    if not _column_exists(connection, libro_table, "obra_id"):
        schema_editor.execute(f"ALTER TABLE {libro_table} ADD COLUMN obra_id bigint")
    if not _column_exists(connection, libro_table, "editorial_id"):
        schema_editor.execute(f"ALTER TABLE {libro_table} ADD COLUMN editorial_id bigint")
    if not _column_exists(connection, libro_table, "isbn"):
        schema_editor.execute(f"ALTER TABLE {libro_table} ADD COLUMN isbn varchar(20) NOT NULL DEFAULT ''")
    if not _column_exists(connection, libro_table, "idioma"):
        schema_editor.execute(f"ALTER TABLE {libro_table} ADD COLUMN idioma varchar(60) NOT NULL DEFAULT 'es'")
    if not _column_exists(connection, libro_table, "anio_publicacion"):
        schema_editor.execute(f"ALTER TABLE {libro_table} ADD COLUMN anio_publicacion integer")

    has_legacy_author = _column_exists(connection, libro_table, "autor")
    has_legacy_editorial = _column_exists(connection, libro_table, "editorial")

    if has_legacy_author or has_legacy_editorial:
        genero_default, _ = Genero.objects.get_or_create(
            nombre="Sin genero",
            defaults={
                "slug": _unique_slug(Genero, "sin-genero"),
                "descripcion": "Genero asignado automaticamente durante reparacion de esquema.",
            },
        )
        if not genero_default.slug:
            genero_default.slug = _unique_slug(Genero, genero_default.nombre)
            genero_default.save(update_fields=["slug"])

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, nombre,
                    {("autor" if has_legacy_author else "''")} AS autor_legacy,
                    {("editorial" if has_legacy_editorial else "''")} AS editorial_legacy
                FROM {libro_table}
                """
            )
            rows = cursor.fetchall()

        fallback_autor, _ = Autor.objects.get_or_create(
            nombre="Autor desconocido",
            defaults={"slug": _unique_slug(Autor, "autor-desconocido"), "biografia": ""},
        )
        fallback_editorial, _ = Editorial.objects.get_or_create(
            nombre="Editorial desconocida",
            defaults={"slug": _unique_slug(Editorial, "editorial-desconocida"), "descripcion": "", "sitio_web": ""},
        )

        for book_id, book_name, author_name, editorial_name in rows:
            author_name = (author_name or "").strip() or fallback_autor.nombre
            editorial_name = (editorial_name or "").strip() or fallback_editorial.nombre
            title = (book_name or "").strip() or f"Libro-{book_id}"

            autor_obj, _ = Autor.objects.get_or_create(
                nombre=author_name,
                defaults={"slug": _unique_slug(Autor, author_name), "biografia": ""},
            )
            editorial_obj, _ = Editorial.objects.get_or_create(
                nombre=editorial_name,
                defaults={"slug": _unique_slug(Editorial, editorial_name), "descripcion": "", "sitio_web": ""},
            )
            obra_obj, _ = Obra.objects.get_or_create(
                titulo=title,
                autor=autor_obj,
                defaults={
                    "slug": _unique_slug(Obra, f"{title}-{autor_obj.id}"),
                    "genero": genero_default,
                    "descripcion": "",
                    "descripcion_corta": "",
                },
            )
            with connection.cursor() as cursor:
                cursor.execute(
                    f"UPDATE {libro_table} SET obra_id = %s, editorial_id = %s WHERE id = %s",
                    [obra_obj.id, editorial_obj.id, book_id],
                )

    # Asegura datos para columnas FK nuevas incluso si no habia columnas legacy.
    genero_default, _ = Genero.objects.get_or_create(
        nombre="Sin genero",
        defaults={"slug": _unique_slug(Genero, "sin-genero"), "descripcion": ""},
    )
    fallback_autor, _ = Autor.objects.get_or_create(
        nombre="Autor desconocido",
        defaults={"slug": _unique_slug(Autor, "autor-desconocido"), "biografia": ""},
    )
    fallback_editorial, _ = Editorial.objects.get_or_create(
        nombre="Editorial desconocida",
        defaults={"slug": _unique_slug(Editorial, "editorial-desconocida"), "descripcion": "", "sitio_web": ""},
    )
    fallback_obra, _ = Obra.objects.get_or_create(
        titulo="Obra desconocida",
        autor=fallback_autor,
        defaults={
            "slug": _unique_slug(Obra, "obra-desconocida"),
            "genero": genero_default,
            "descripcion": "",
            "descripcion_corta": "",
        },
    )

    with connection.cursor() as cursor:
        cursor.execute(
            f"UPDATE {libro_table} SET obra_id = %s WHERE obra_id IS NULL",
            [fallback_obra.id],
        )
        cursor.execute(
            f"UPDATE {libro_table} SET editorial_id = %s WHERE editorial_id IS NULL",
            [fallback_editorial.id],
        )

    if connection.vendor == "postgresql":
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {libro_table} ALTER COLUMN obra_id SET NOT NULL")
            cursor.execute(f"ALTER TABLE {libro_table} ALTER COLUMN editorial_id SET NOT NULL")
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'productos_libro_obra_id_fkey'
                    ) THEN
                        ALTER TABLE productos_libro
                        ADD CONSTRAINT productos_libro_obra_id_fkey
                        FOREIGN KEY (obra_id) REFERENCES productos_obra(id)
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END $$;
                """
            )
            cursor.execute(
                """
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'productos_libro_editorial_id_fkey'
                    ) THEN
                        ALTER TABLE productos_libro
                        ADD CONSTRAINT productos_libro_editorial_id_fkey
                        FOREIGN KEY (editorial_id) REFERENCES productos_editorial(id)
                        DEFERRABLE INITIALLY DEFERRED;
                    END IF;
                END $$;
                """
            )


class Migration(migrations.Migration):
    dependencies = [
        ("productos", "0005_alter_libro_editorial_alter_libro_obra_and_more"),
    ]

    operations = [
        migrations.RunPython(repair_catalog_schema, migrations.RunPython.noop),
    ]
