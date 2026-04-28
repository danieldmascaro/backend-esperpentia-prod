from django.db import migrations


def _repair_legacy_ventaitem_schema(apps, schema_editor):
    table_name = "ventas_ventaitem"

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
            """,
            [table_name],
        )
        existing_columns = {row[0] for row in cursor.fetchall()}

        add_columns_sql = {
            "autor_nombre": "ALTER TABLE ventas_ventaitem ADD COLUMN autor_nombre varchar(255) NOT NULL DEFAULT ''",
            "editorial_nombre": "ALTER TABLE ventas_ventaitem ADD COLUMN editorial_nombre varchar(255) NOT NULL DEFAULT ''",
            "genero_nombre": "ALTER TABLE ventas_ventaitem ADD COLUMN genero_nombre varchar(120) NOT NULL DEFAULT ''",
        }

        for column_name, sql in add_columns_sql.items():
            if column_name not in existing_columns:
                cursor.execute(sql)

        if "variante_nombre" in existing_columns:
            cursor.execute("ALTER TABLE ventas_ventaitem DROP COLUMN variante_nombre")

        if "product_variant_id" in existing_columns:
            cursor.execute("ALTER TABLE ventas_ventaitem DROP COLUMN product_variant_id")


def _noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("ventas", "0004_alter_venta_user_alter_ventaitem_libro"),
    ]

    operations = [
        migrations.RunPython(_repair_legacy_ventaitem_schema, _noop_reverse),
    ]
