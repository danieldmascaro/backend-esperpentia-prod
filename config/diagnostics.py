from django.conf import settings
from django.db import connection
from django.http import JsonResponse


def db_health(request):
    result = {
        "ok": False,
        "env": "production" if settings.IS_PRODUCTION else "development",
        "public_https": settings.IS_PUBLIC_HTTPS_DEPLOYMENT,
        "csrf_cookie_secure": settings.CSRF_COOKIE_SECURE,
        "csrf_cookie_samesite": settings.CSRF_COOKIE_SAMESITE,
        "auth_refresh_cookie_secure": settings.AUTH_REFRESH_COOKIE_SECURE,
        "auth_refresh_cookie_samesite": settings.AUTH_REFRESH_COOKIE_SAMESITE,
        "auth_refresh_cookie_path": settings.AUTH_REFRESH_COOKIE_PATH,
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
