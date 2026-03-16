from django.db import migrations, models
import re
import unicodedata
import itertools


def _normalize(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.upper().replace("'", " ")
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _generate(name, used_codes):
    normalized = _normalize(name)
    words = [word for word in normalized.split() if word]
    significant = [word for word in words if word not in {"DE", "DEL", "EL", "LA", "LAS", "LOS", "SAN", "SANTA"}] or words
    joined = "".join(significant)
    consonants = "".join(char for char in joined if char not in "AEIOU")
    candidates = [joined[:4], consonants[:4], (joined[:2] + consonants)[:4], (consonants + joined)[:4]]

    for candidate in candidates:
        candidate = re.sub(r"[^A-Z0-9]", "", candidate)[:4]
        if len(candidate) == 4 and candidate not in used_codes:
            return candidate

    pool = f"{consonants}{joined}XXXX"
    for indexes in itertools.permutations(range(len(pool)), 4):
        candidate = "".join(pool[index] for index in indexes)
        if candidate not in used_codes:
            return candidate

    raise ValueError(f"No se pudo generar county_code unico para '{name}'.")


def populate_county_codes(apps, schema_editor):
    Comuna = apps.get_model("usuarios", "Comuna")
    used_codes = set()
    for comuna in Comuna.objects.order_by("id"):
        code = _generate(comuna.nombre, used_codes)
        comuna.county_code = code
        comuna.save(update_fields=["county_code"])
        used_codes.add(code)


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0003_alter_usuario_comuna_alter_usuario_region"),
    ]

    operations = [
        migrations.AddField(
            model_name="comuna",
            name="county_code",
            field=models.CharField(blank=True, editable=False, max_length=4, null=True),
        ),
        migrations.RunPython(populate_county_codes, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="comuna",
            name="county_code",
            field=models.CharField(editable=False, max_length=4, unique=True),
        ),
    ]
