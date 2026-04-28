from django.db import migrations, models


def backfill_user_phone_numbers(apps, schema_editor):
    Usuario = apps.get_model("usuarios", "Usuario")
    users_without_phone = Usuario.objects.filter(telefono__isnull=True) | Usuario.objects.filter(telefono="")

    for user in users_without_phone.iterator():
        user.telefono = f"+5690000{user.id:04d}"
        user.save(update_fields=["telefono"])


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0004_comuna_county_code"),
    ]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="telefono",
            field=models.CharField(default="", max_length=32),
            preserve_default=False,
        ),
        migrations.RunPython(backfill_user_phone_numbers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="usuario",
            name="telefono",
            field=models.CharField(max_length=32),
        ),
    ]
