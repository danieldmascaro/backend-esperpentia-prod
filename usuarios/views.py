from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.http import JsonResponse
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.http import require_GET


@require_GET
def activate_user_from_link(request, uid, token):
    try:
        user_id = urlsafe_base64_decode(uid).decode()
        user = get_user_model().objects.get(pk=user_id)
    except Exception:
        return JsonResponse({"detail": "Enlace de activacion invalido."}, status=400)

    if not default_token_generator.check_token(user, token):
        return JsonResponse({"detail": "Token de activacion invalido o expirado."}, status=400)

    if not user.is_active:
        user.is_active = True
        user.save(update_fields=["is_active"])

    return JsonResponse({"detail": "Cuenta activada correctamente."}, status=200)
