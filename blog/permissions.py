from rest_framework.permissions import SAFE_METHODS, BasePermission


class BlogPostPermission(BasePermission):
    """
    - Lectura publica.
    - Creacion solo por usuarios staff.
    - Edicion/eliminacion solo por autor o admin (superuser).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if request.method == "POST":
            return bool(user and user.is_authenticated and user.is_staff)

        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        return bool(user.is_superuser or obj.autor_id == user.id)


class BlogPostImagePermission(BasePermission):
    """
    - Lectura publica.
    - Creacion solo staff.
    - Edicion/eliminacion solo por autor del post o admin (superuser).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if request.method == "POST":
            return bool(user and user.is_authenticated and user.is_staff)

        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if not user or not user.is_authenticated:
            return False

        return bool(user.is_superuser or obj.post.autor_id == user.id)

