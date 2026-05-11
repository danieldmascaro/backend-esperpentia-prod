from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def db_health(request):
    result = {
        "ok": False,
        "env": "production" if settings.IS_PRODUCTION else "development",
        "engine": settings.DATABASES["default"].get("ENGINE"),
        "name": settings.DATABASES["default"].get("NAME"),
        "host": settings.DATABASES["default"].get("HOST"),
        "port": settings.DATABASES["default"].get("PORT"),
    }
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            one = cursor.fetchone()
        result["ok"] = bool(one and one[0] == 1)
        return JsonResponse(result, status=200)
    except Exception as exc:
        result["error"] = str(exc)
        return JsonResponse(result, status=500)

