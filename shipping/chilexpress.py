import json
import os
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request


CHILEXPRESS_API_BASE_URL = os.getenv(
    "CHILEXPRESS_API_BASE_URL",
    "http://testservices.wschilexpress.com",
).rstrip("/")
CHILEXPRESS_COVERAGE_API_KEY = os.getenv(
    "CHILEXPRESS_API_COBERTURA_KEY",
    os.getenv("VITE_CHILEXPRESS_API_COBERTURA_KEY", ""),
)
CHILEXPRESS_RATES_API_KEY = os.getenv(
    "CHILEXPRESS_API_COTIZADOR_KEY",
    os.getenv("VITE_CHILEXPRESS_API_COTIZADOR_KEY", ""),
)


class ChilexpressApiError(Exception):
    pass


def _load_response_body(raw_body):
    if not raw_body:
        return {}
    try:
        return json.loads(raw_body)
    except json.JSONDecodeError:
        return {}


def search_chilexpress_streets(
    *,
    county_name,
    street_name,
    limit=6,
    points_of_interest_enabled=False,
    street_name_enabled=True,
    road_type=0,
):
    api_key = CHILEXPRESS_COVERAGE_API_KEY.strip()
    if not api_key:
        raise ChilexpressApiError(
            "Falta configurar CHILEXPRESS_API_COBERTURA_KEY para consultar calles en Chilexpress."
        )

    path = "/georeference/api/v1.0/streets/search"
    query_string = urllib_parse.urlencode({"limit": int(limit)})
    url = f"{CHILEXPRESS_API_BASE_URL}{path}?{query_string}"
    payload = json.dumps(
        {
            "countyName": county_name,
            "streetName": street_name,
            "pointsOfInterestEnabled": points_of_interest_enabled,
            "streetNameEnabled": street_name_enabled,
            "roadType": road_type,
        }
    ).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": api_key,
        },
    )

    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = _load_response_body(body)
            return {
                "status_code": response.status,
                "status_description": data.get("statusDescription"),
                "streets": data.get("streets") or [],
                "raw": data,
            }
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        data = _load_response_body(body)
        description = data.get("statusDescription") or f"HTTP {exc.code}"
        raise ChilexpressApiError(description) from exc
    except urllib_error.URLError as exc:
        raise ChilexpressApiError(f"No se pudo conectar con Chilexpress: {exc.reason}") from exc
    except Exception as exc:
        raise ChilexpressApiError(f"Error inesperado conectando con Chilexpress: {type(exc).__name__} - {str(exc)}") from exc


def quote_chilexpress_rate(
    *,
    origin_county_code,
    destination_county_code,
    package,
    product_type,
    content_type,
    declared_worth,
    delivery_time,
):
    api_key = CHILEXPRESS_RATES_API_KEY.strip()
    if not api_key:
        raise ChilexpressApiError(
            "Falta configurar CHILEXPRESS_API_COTIZADOR_KEY para cotizar en Chilexpress."
        )

    path = "/rating/api/v1.0/rates/courier"
    url = f"{CHILEXPRESS_API_BASE_URL}{path}"
    payload = json.dumps(
        {
            "originCountyCode": origin_county_code,
            "destinationCountyCode": destination_county_code,
            "package": package,
            "productType": product_type,
            "contentType": content_type,
            "declaredWorth": declared_worth,
            "deliveryTime": delivery_time,
        }
    ).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=payload,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Ocp-Apim-Subscription-Key": api_key,
        },
    )

    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            data = _load_response_body(body)
            return {
                "status_code": response.status,
                "status_description": data.get("statusDescription"),
                "options": (data.get("data") or {}).get("courierServiceOptions") or [],
                "raw": data,
            }
    except urllib_error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        data = _load_response_body(body)
        description = data.get("statusDescription") or f"HTTP {exc.code}"
        raise ChilexpressApiError(description) from exc
    except urllib_error.URLError as exc:
        raise ChilexpressApiError(f"No se pudo conectar con Chilexpress: {exc.reason}") from exc
    except Exception as exc:
        raise ChilexpressApiError(f"Error inesperado conectando con Chilexpress: {type(exc).__name__} - {str(exc)}") from exc
