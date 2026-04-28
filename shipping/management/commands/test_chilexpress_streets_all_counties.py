from django.core.management.base import BaseCommand, CommandError

from shipping.chilexpress import ChilexpressApiError, search_chilexpress_streets
from usuarios.geography import COUNTY_CODE_ALIASES, normalize_geography_name
from usuarios.models import Comuna


class Command(BaseCommand):
    help = "Prueba la API de calles de Chilexpress contra todas las comunas registradas."

    def add_arguments(self, parser):
        parser.add_argument(
            "--street-name",
            default="SAN",
            help="Texto a buscar para calles (minimo 3 caracteres).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=1,
            help="Limite de resultados por comuna.",
        )
        parser.add_argument(
            "--fail-on-error",
            action="store_true",
            help="Falla el comando si alguna comuna devuelve error.",
        )

    def _county_name_candidates(self, comuna_name):
        raw = (comuna_name or "").strip()
        normalized = normalize_geography_name(raw)

        candidates = []

        def add_candidate(value):
            candidate = (value or "").strip()
            if candidate and candidate not in candidates:
                candidates.append(candidate)

        add_candidate(raw.upper())
        add_candidate(normalized)

        alias_target = COUNTY_CODE_ALIASES.get(normalized)
        if alias_target:
            add_candidate(alias_target)

        for alias_source, alias_value in COUNTY_CODE_ALIASES.items():
            if alias_value == normalized:
                add_candidate(alias_source)

        # Refuerzo explícito para variantes comunes en Chilexpress.
        if normalized == "SANTIAGO":
            add_candidate("SANTIAGO CENTRO")
        if normalized == "SANTIAGO CENTRO":
            add_candidate("SANTIAGO")

        return candidates

    def handle(self, *args, **options):
        street_name = (options["street_name"] or "").strip()
        if len(street_name) < 3:
            raise CommandError("--street-name debe tener al menos 3 caracteres.")

        limit = max(1, int(options["limit"]))
        fail_on_error = bool(options["fail_on_error"])

        comunas = list(
            Comuna.objects.select_related("region").order_by("region__nombre", "nombre")
        )
        if not comunas:
            self.stdout.write(self.style.WARNING("No hay comunas registradas para probar."))
            return

        ok_count = 0
        with_matches_count = 0
        error_count = 0

        self.stdout.write(
            f"Iniciando prueba de calles Chilexpress para {len(comunas)} comunas con streetName='{street_name.upper()}'."
        )

        for index, comuna in enumerate(comunas, start=1):
            county_candidates = self._county_name_candidates(comuna.nombre)
            resolved_county_name = None
            last_error = None
            result = None

            for county_name in county_candidates:
                try:
                    result = search_chilexpress_streets(
                        county_name=county_name,
                        street_name=street_name.upper(),
                        limit=limit,
                    )
                    resolved_county_name = county_name
                    break
                except ChilexpressApiError as exc:
                    last_error = exc

            if result is None:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"[{index}/{len(comunas)}] {comuna.region.nombre} / {comuna.nombre}: ERROR - {last_error}"
                    )
                )
                continue

            streets = result.get("streets") or []
            has_matches = len(streets) > 0
            if has_matches:
                with_matches_count += 1
            ok_count += 1

            status_label = "OK con resultados" if has_matches else "OK sin resultados"
            renamed_label = ""
            if resolved_county_name and resolved_county_name != comuna.nombre.upper():
                renamed_label = f" (usando '{resolved_county_name}')"
            self.stdout.write(
                f"[{index}/{len(comunas)}] {comuna.region.nombre} / {comuna.nombre}: {status_label}{renamed_label}"
            )

        self.stdout.write("")
        self.stdout.write("Resumen:")
        self.stdout.write(f"- Comunas probadas: {len(comunas)}")
        self.stdout.write(f"- Respuesta OK: {ok_count}")
        self.stdout.write(f"- OK con al menos una calle: {with_matches_count}")
        self.stdout.write(f"- Errores: {error_count}")

        if fail_on_error and error_count > 0:
            raise CommandError(f"Se detectaron {error_count} errores consultando Chilexpress.")
