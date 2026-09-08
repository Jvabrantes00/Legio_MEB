from rest_framework.permissions import BasePermission, SAFE_METHODS

from .roles import RECOGNIZED_ROLES, user_has_any_role


class HasAnySiaRole(BasePermission):
    """Allow superusers or users with one of the configured SIA roles."""

    allowed_roles = ()
    message = 'Seu usuário não possui um papel autorizado para esta operação.'

    def has_permission(self, request, view):
        user = request.user
        if not getattr(user, 'is_authenticated', False):
            return False
        if user.is_superuser:
            return True

        if request.method in SAFE_METHODS:
            allowed_roles = getattr(
                view,
                'read_roles',
                getattr(view, 'allowed_roles', self.allowed_roles),
            )
        else:
            allowed_roles = getattr(
                view,
                'write_roles',
                getattr(view, 'allowed_roles', self.allowed_roles),
            )
        return user_has_any_role(user, *allowed_roles)

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class HasRecognizedSiaRole(HasAnySiaRole):
    allowed_roles = RECOGNIZED_ROLES


def require_sia_roles(*roles):
    """Build a DRF permission configured for any one of the supplied roles."""

    class RequiredSiaRole(HasAnySiaRole):
        allowed_roles = roles

    return RequiredSiaRole
