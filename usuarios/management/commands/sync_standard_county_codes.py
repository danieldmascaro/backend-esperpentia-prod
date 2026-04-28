from django.core.management.base import BaseCommand
from django.db import transaction

from usuarios.geography import (
    COUNTY_CODE_ALIASES,
    LEGACY_SHIPPING_COUNTY_CODES_URL,
    fetch_text,
    normalize_geography_name,
    parse_legacy_shipping_codes,
)
from usuarios.models import Comuna


EXTRA_COUNTY_ALIASES = {
    "SANTIAGO CENTRO": "SANTIAGO",
    "TILTIL": "TIL TIL",
    "MARCHIHUE": "MARCHIGUE",
    "PLACILLA SEXTA REGION": "PLACILLA",
}


def build_name_candidates(name):
    normalized = normalize_geography_name(name)
    candidates = [normalized]

    alias = COUNTY_CODE_ALIASES.get(normalized)
    if alias:
        candidates.append(normalize_geography_name(alias))

    extra_alias = EXTRA_COUNTY_ALIASES.get(normalized)
    if extra_alias:
        candidates.append(normalize_geography_name(extra_alias))

    if normalized.endswith(" SEXTA REGION"):
        candidates.append(normalized.replace(" SEXTA REGION", ""))

    unique = []
    for candidate in candidates:
        if candidate and candidate not in unique:
            unique.append(candidate)
    return unique


class Command(BaseCommand):
    help = "Sincroniza county_code con códigos estándar de cobertura cuando exista mapeo."

    @transaction.atomic
    def handle(self, *args, **options):
        shipping_codes = parse_legacy_shipping_codes(fetch_text(LEGACY_SHIPPING_COUNTY_CODES_URL))
        all_comunas = list(Comuna.objects.select_related("region").order_by("region__nombre", "nombre"))

        updated = 0
        already_ok = 0
        unresolved = []
        conflicts = []

        for comuna in all_comunas:
            target_code = None
            for candidate in build_name_candidates(comuna.nombre):
                shipping_code = shipping_codes.get(candidate)
                if shipping_code:
                    target_code = shipping_code
                    break

            if not target_code:
                unresolved.append((comuna.region.nombre, comuna.nombre, comuna.county_code))
                continue

            if comuna.county_code == target_code:
                already_ok += 1
                continue

            code_in_use = Comuna.objects.filter(county_code=target_code).exclude(pk=comuna.pk).first()
            if code_in_use:
                conflicts.append(
                    (
                        comuna.region.nombre,
                        comuna.nombre,
                        comuna.county_code,
                        target_code,
                        code_in_use.region.nombre,
                        code_in_use.nombre,
                    )
                )
                continue

            comuna.county_code = target_code
            comuna.save(update_fields=["county_code"])
            updated += 1

        self.stdout.write(self.style.SUCCESS("Sincronización de county_code finalizada."))
        self.stdout.write(f"- Comunas totales: {len(all_comunas)}")
        self.stdout.write(f"- Actualizadas: {updated}")
        self.stdout.write(f"- Ya estándar: {already_ok}")
        self.stdout.write(f"- Sin mapeo estándar: {len(unresolved)}")
        self.stdout.write(f"- En conflicto por código duplicado: {len(conflicts)}")

        if conflicts:
            self.stdout.write("\nConflictos (muestra):")
            for item in conflicts[:20]:
                self.stdout.write(
                    f"- {item[0]} / {item[1]} ({item[2]}) quiere {item[3]}, ya usado por {item[4]} / {item[5]}"
                )

        if unresolved:
            self.stdout.write("\nSin mapeo estándar (muestra):")
            for item in unresolved[:20]:
                self.stdout.write(f"- {item[0]} / {item[1]} (actual: {item[2]})")

