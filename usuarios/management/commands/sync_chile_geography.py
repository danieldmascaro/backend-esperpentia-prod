from django.core.management.base import BaseCommand
from django.db import transaction

from usuarios.geography import (
    LEGACY_SHIPPING_COUNTY_CODES_URL,
    LEGACY_REGION_REDIRECTS,
    OFFICIAL_CHILE_GEOJSON_URL,
    fetch_json,
    fetch_text,
    iter_official_regions_and_comunas,
    normalize_geography_name,
    normalize_region_key,
    parse_legacy_shipping_codes,
    resolve_county_code,
)
from usuarios.models import Comuna, Region


class Command(BaseCommand):
    help = "Carga o actualiza las regiones y comunas oficiales de Chile con county_code interno."

    @transaction.atomic
    def handle(self, *args, **options):
        geojson = fetch_json(OFFICIAL_CHILE_GEOJSON_URL)
        shipping_codes = parse_legacy_shipping_codes(fetch_text(LEGACY_SHIPPING_COUNTY_CODES_URL))

        region_cache = {normalize_region_key(region.nombre): region for region in Region.objects.all()}
        comuna_cache = {}
        for comuna in Comuna.objects.select_related("region").all():
            comuna_cache.setdefault(comuna.region_id, {})
            comuna_cache[comuna.region_id][normalize_geography_name(comuna.nombre)] = comuna
        used_codes = set(
            Comuna.objects.exclude(county_code__isnull=True)
            .exclude(county_code="")
            .values_list("county_code", flat=True)
        )
        expected_region_comunas = {}

        created_regions = 0
        created_comunas = 0
        updated_comunas = 0

        for region_name, comuna_name in iter_official_regions_and_comunas(geojson):
            expected_region_comunas.setdefault(normalize_geography_name(region_name), set()).add(
                normalize_geography_name(comuna_name)
            )
            region_key = normalize_region_key(region_name)
            region = region_cache.get(region_key)
            if region is None:
                region = Region.objects.create(nombre=region_name)
                region_cache[region_key] = region
                comuna_cache[region.id] = {}
                created_regions += 1
            elif region.nombre != region_name:
                region.nombre = region_name
                region.save(update_fields=["nombre"])

            region_comunas = comuna_cache.setdefault(region.id, {})
            normalized_comuna_name = normalize_geography_name(comuna_name)
            comuna = region_comunas.get(normalized_comuna_name)
            current_code = comuna.county_code if comuna else None
            reserved_codes = used_codes - ({current_code} if current_code else set())
            code_to_use = resolve_county_code(comuna_name, shipping_codes, reserved_codes)

            if comuna is None:
                comuna = Comuna.objects.filter(county_code=code_to_use).select_related("region").first()
                if comuna is not None:
                    previous_cache = comuna_cache.setdefault(comuna.region_id, {})
                    previous_cache.pop(normalize_geography_name(comuna.nombre), None)
                    comuna.region = region
                    comuna.nombre = comuna_name
                    comuna.save(update_fields=["region", "nombre"])
                    region_comunas[normalized_comuna_name] = comuna
                    current_code = comuna.county_code

            if comuna is None:
                comuna = Comuna.objects.create(region=region, nombre=comuna_name, county_code=code_to_use)
                region_comunas[normalized_comuna_name] = comuna
                created_comunas += 1
            else:
                changed = False
                if comuna.nombre != comuna_name:
                    region_comunas.pop(normalize_geography_name(comuna.nombre), None)
                    comuna.nombre = comuna_name
                    region_comunas[normalized_comuna_name] = comuna
                    changed = True
                if comuna.county_code != code_to_use:
                    comuna.county_code = code_to_use
                    changed = True
                if changed:
                    comuna.save(update_fields=["nombre", "county_code"])
                    updated_comunas += 1

            if current_code:
                used_codes.discard(current_code)
            used_codes.add(code_to_use)

        self._merge_legacy_regions(comuna_cache)
        self._prune_out_of_region_duplicates(expected_region_comunas)

        self.stdout.write(
            self.style.SUCCESS(
                f"Regiones creadas: {created_regions}. Comunas creadas: {created_comunas}. Comunas actualizadas: {updated_comunas}."
            )
        )

    def _merge_legacy_regions(self, comuna_cache):
        regions = list(Region.objects.all())
        for legacy_name, official_name in LEGACY_REGION_REDIRECTS.items():
            legacy_region = next(
                (region for region in regions if normalize_geography_name(region.nombre) == legacy_name),
                None,
            )
            official_region = next(
                (region for region in regions if normalize_geography_name(region.nombre) == official_name),
                None,
            )

            if legacy_region is None or official_region is None or legacy_region.id == official_region.id:
                continue

            official_comunas = comuna_cache.setdefault(official_region.id, {})

            for usuario in legacy_region.usuarios.select_related("comuna").all():
                usuario.region = official_region
                if usuario.comuna:
                    target_comuna = official_comunas.get(normalize_geography_name(usuario.comuna.nombre))
                    if target_comuna is not None:
                        usuario.comuna = target_comuna
                usuario.save(update_fields=["region", "comuna"])

            for legacy_comuna in list(legacy_region.comunas.all()):
                normalized_name = normalize_geography_name(legacy_comuna.nombre)
                target_comuna = official_comunas.get(normalized_name)
                if target_comuna is not None:
                    legacy_comuna.usuarios.update(comuna=target_comuna)
                    legacy_comuna.delete()
                    continue

                legacy_comuna.region = official_region
                legacy_comuna.save(update_fields=["region"])
                official_comunas[normalized_name] = legacy_comuna

            legacy_region.delete()

    def _prune_out_of_region_duplicates(self, expected_region_comunas):
        regions = list(Region.objects.all())
        regions_by_name = {normalize_geography_name(region.nombre): region for region in regions}
        target_regions_by_comuna = {}

        for region_name, comuna_names in expected_region_comunas.items():
            region = regions_by_name.get(region_name)
            if region is None:
                continue
            for comuna_name in comuna_names:
                target_regions_by_comuna.setdefault(comuna_name, []).append(region)

        for region in regions:
            expected_comunas = expected_region_comunas.get(normalize_geography_name(region.nombre))
            if expected_comunas is None:
                continue

            for comuna in list(region.comunas.all()):
                normalized_name = normalize_geography_name(comuna.nombre)
                if normalized_name in expected_comunas:
                    continue

                target_regions = target_regions_by_comuna.get(normalized_name, [])
                if len(target_regions) != 1:
                    continue

                target_region = target_regions[0]
                if target_region.id == region.id:
                    continue

                target_comuna = target_region.comunas.filter(nombre=comuna.nombre).first()
                if target_comuna is None:
                    comuna.region = target_region
                    comuna.save(update_fields=["region"])
                    continue

                comuna.usuarios.update(comuna=target_comuna)
                comuna.delete()
