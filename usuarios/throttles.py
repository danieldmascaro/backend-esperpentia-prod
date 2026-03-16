from rest_framework.throttling import ScopedRateThrottle


class AuthCsrfThrottle(ScopedRateThrottle):
    scope = "auth_csrf"


class AuthLoginThrottle(ScopedRateThrottle):
    scope = "auth_login"


class AuthRefreshThrottle(ScopedRateThrottle):
    scope = "auth_refresh"


class AuthLogoutThrottle(ScopedRateThrottle):
    scope = "auth_logout"
