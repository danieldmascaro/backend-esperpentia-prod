import itertools
import json
import re
import unicodedata
import urllib.request


OFFICIAL_CHILE_GEOJSON_URL = "https://gist.githubusercontent.com/rhacs/ed3be80022a0d0f94cdfd24c47b4cc0b/raw/chile.json"
LEGACY_SHIPPING_COUNTY_CODES_URL = "https://gist.githubusercontent.com/baamenabar/fcfaf53e8f585e9d2e62/raw"
OFFICIAL_REGION_NAME_OVERRIDES = {
    "03": "Región de Atacama",
}
OFFICIAL_REGION_SUPPLEMENTS = {
    "Region Metropolitana de Santiago": (
        "Alhue",
        "Buin",
        "Calera de Tango",
        "Cerrillos",
        "Cerro Navia",
        "Colina",
        "Conchali",
        "Curacavi",
        "El Bosque",
        "El Monte",
        "Estacion Central",
        "Huechuraba",
        "Independencia",
        "Isla de Maipo",
        "La Cisterna",
        "La Florida",
        "La Granja",
        "La Pintana",
        "La Reina",
        "Lampa",
        "Las Condes",
        "Lo Barnechea",
        "Lo Espejo",
        "Lo Prado",
        "Macul",
        "Maipu",
        "Maria Pinto",
        "Melipilla",
        "Nunoa",
        "Padre Hurtado",
        "Paine",
        "Pedro Aguirre Cerda",
        "Penaflor",
        "Penalolen",
        "Pirque",
        "Providencia",
        "Pudahuel",
        "Puente Alto",
        "Quilicura",
        "Quinta Normal",
        "Recoleta",
        "Renca",
        "San Bernardo",
        "San Joaquin",
        "San Jose de Maipo",
        "San Miguel",
        "San Pedro",
        "San Ramon",
        "Santiago",
        "Talagante",
        "Tiltil",
        "Vitacura",
    ),
}

COUNTY_CODE_ALIASES = {
    "AYSEN": "PUERTO AYSEN",
    "CABO DE HORNOS": "PUERTO WILLIAMS",
    "ISLA DE PASCUA": "RAPA NUI",
    "LA CALERA": "CALERA",
    "SAN FRANCISCO DE MOSTAZAL": "MOSTAZAL",
    "SAN JOSE DE LA MARIQUINA": "MARIQUINA",
    "SAN VICENTE DE TAGUA TAGUA": "SAN VICENTE",
    "SANTIAGO": "SANTIAGO CENTRO",
    "TIL TIL": "TIL TIL",
}
COUNTY_CODE_STOPWORDS = {"DE", "DEL", "EL", "LA", "LAS", "LOS", "SAN", "SANTA"}
LEGACY_REGION_REDIRECTS = {
    "ATACAMA": "REGION DE ATACAMA",
    "AYSEN DEL GENERAL CARLOS IBANEZ DEL CAMPO": "REGION DE AYSEN",
    "BIOBIO": "REGION DEL BIO BIO",
    "LIBERTADOR GENERAL BERNARDO O HIGGINS": "REGION DEL LIBERTADOR BERNARDO O HIGGINS",
    "MAGALLANES Y DE LA ANTARTICA CHILENA": "REGION DE MAGALLANES Y LA ANTARTICA CHILENA",
    "REGION METROPOLITANA": "REGION METROPOLITANA DE SANTIAGO",
}


def normalize_geography_name(value):
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.upper().replace("'", " ")
    normalized = re.sub(r"[^A-Z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def parse_legacy_shipping_codes(raw_text):
    return {
        normalize_geography_name(name): code
        for name, code in re.findall(r"^\|([^;]+);([A-Z0-9]+)\s*$", raw_text, re.MULTILINE)
    }


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def fetch_text(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="ignore")


def iter_official_regions_and_comunas(geojson):
    emitted = set()

    for region in geojson["regiones"]:
        region_name = OFFICIAL_REGION_NAME_OVERRIDES.get(region["codigo"], region["nombre_largo"])
        for provincia in region["provincias"]:
            for comuna in provincia["comunas"]:
                key = (
                    normalize_geography_name(region_name),
                    normalize_geography_name(comuna["nombre"]),
                )
                if key in emitted:
                    continue
                emitted.add(key)
                yield region_name, comuna["nombre"]

    for region_name, comunas in OFFICIAL_REGION_SUPPLEMENTS.items():
        for comuna_name in comunas:
            key = (
                normalize_geography_name(region_name),
                normalize_geography_name(comuna_name),
            )
            if key in emitted:
                continue
            emitted.add(key)
            yield region_name, comuna_name


def normalize_region_key(value):
    normalized = normalize_geography_name(value)
    for prefix in ("REGION DE ", "REGION DEL ", "REGION "):
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return normalized


def _county_code_candidates(name):
    normalized = normalize_geography_name(name)
    words = [word for word in normalized.split() if word]
    significant = [word for word in words if word not in COUNTY_CODE_STOPWORDS] or words
    joined = "".join(significant)
    consonants = "".join(char for char in joined if char not in "AEIOU")

    candidates = []
    if len(significant) >= 2:
        candidates.append((significant[0][0] + significant[1][:3])[:4])
        candidates.append((significant[0][:2] + significant[1][:2])[:4])
        initials = significant[0][0] + "".join(word[0] for word in significant[1:])
        candidates.append((initials + joined)[:4])

    candidates.extend(
        [
            joined[:4],
            consonants[:4],
            (joined[:2] + consonants)[:4],
            (consonants + joined)[:4],
        ]
    )
    return [re.sub(r"[^A-Z0-9]", "", candidate)[:4] for candidate in candidates if len(candidate) >= 4]


def generate_unique_county_code(name, used_codes):
    for candidate in _county_code_candidates(name):
        if candidate not in used_codes:
            return candidate

    normalized = normalize_geography_name(name)
    significant = normalized.replace(" ", "")
    consonants = "".join(char for char in significant if char not in "AEIOU")
    pool = f"{consonants}{significant}XXXX"

    for indexes in itertools.permutations(range(len(pool)), 4):
        candidate = "".join(pool[index] for index in indexes)
        if candidate not in used_codes:
            return candidate

    raise ValueError(f"No se pudo generar county_code unico para '{name}'.")


def resolve_county_code(name, shipping_codes, used_codes):
    normalized = normalize_geography_name(name)
    shipping_candidates = [normalized]

    alias = COUNTY_CODE_ALIASES.get(normalized)
    if alias:
        shipping_candidates.append(normalize_geography_name(alias))

    for shipping_name in shipping_candidates:
        shipping_code = shipping_codes.get(shipping_name)
        if shipping_code and shipping_code not in used_codes:
            return shipping_code

    return generate_unique_county_code(name, used_codes)


