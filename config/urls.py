"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from usuarios.auth_views import CsrfCookieView, CookieLogoutView, CookieTokenObtainPairView, CookieTokenRefreshView
from usuarios.views import activate_user_from_link

urlpatterns = [
    path('admin/', admin.site.urls),
    path('activate/<uid>/<token>', activate_user_from_link, name='users-activate-link'),
    path('activate/<uid>/<token>/', activate_user_from_link, name='users-activate-link-slash'),
    path('auth/csrf/', CsrfCookieView.as_view(), name='auth-csrf'),
    path('auth/jwt/create/', CookieTokenObtainPairView.as_view(), name='jwt-create'),
    path('auth/jwt/refresh/', CookieTokenRefreshView.as_view(), name='jwt-refresh'),
    path('auth/jwt/logout/', CookieLogoutView.as_view(), name='jwt-logout'),
    path('auth/', include('djoser.urls')),
    path('auth/', include('djoser.urls.jwt')),
    path('users/', include('usuarios.urls')),
    path('productos/', include('productos.urls')),
    path('catalog/', include('productos.urls')),
    path('checkout/', include('checkout.urls')),
    path('inventory/', include('inventory.urls')),
    path('orders/', include('orders.urls')),
    path('shipping/', include('shipping.urls')),
    path('payments/', include('payments.urls')),
    path('ventas/', include('ventas.urls')),
    path('blog/', include('blog.urls')),
]

if not settings.IS_PRODUCTION:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += [
        path("media/<path:path>", serve, {"document_root": settings.MEDIA_ROOT}),
    ]
