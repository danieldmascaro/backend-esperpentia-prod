from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from .throttles import AuthCsrfThrottle, AuthLoginThrottle, AuthLogoutThrottle, AuthRefreshThrottle


def set_refresh_cookie(response, refresh_token):
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
    )


def clear_refresh_cookie(response):
    response.delete_cookie(
        settings.AUTH_REFRESH_COOKIE_NAME,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
    )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfCookieView(APIView):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = (AuthCsrfThrottle,)

    def get(self, request, *args, **kwargs):
        return Response({"csrfToken": get_token(request)}, status=status.HTTP_200_OK)


@method_decorator(csrf_protect, name="dispatch")
class CookieTokenObtainPairView(APIView):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = (AuthLoginThrottle,)

    def post(self, request, *args, **kwargs):
        serializer = TokenObtainPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        response = Response(
            {"access": serializer.validated_data["access"]},
            status=status.HTTP_200_OK,
        )
        set_refresh_cookie(response, serializer.validated_data["refresh"])
        return response


@method_decorator(csrf_protect, name="dispatch")
class CookieTokenRefreshView(APIView):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = (AuthRefreshThrottle,)

    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)
        if not refresh:
            return Response({"detail": "Refresh token ausente."}, status=status.HTTP_401_UNAUTHORIZED)
        serializer = TokenRefreshSerializer(data={"refresh": refresh})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_401_UNAUTHORIZED)

        response = Response(
            {"access": serializer.validated_data["access"]},
            status=status.HTTP_200_OK,
        )

        if settings.SIMPLE_JWT.get("ROTATE_REFRESH_TOKENS") and serializer.validated_data.get("refresh"):
            set_refresh_cookie(response, serializer.validated_data["refresh"])

        return response


@method_decorator(csrf_protect, name="dispatch")
class CookieLogoutView(APIView):
    authentication_classes = ()
    permission_classes = ()
    throttle_classes = (AuthLogoutThrottle,)

    def post(self, request, *args, **kwargs):
        refresh = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE_NAME)

        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass

        response = Response(status=status.HTTP_204_NO_CONTENT)
        clear_refresh_cookie(response)
        return response
