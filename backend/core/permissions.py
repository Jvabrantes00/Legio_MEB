from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .roles import (
    FICHAS_MANAGEMENT_ROLES,
    RECOGNIZED_ROLES,
    SiaRole,
    user_has_any_role,
)


class AlpinistaQueryPolicy:
    """Allow query capabilities explicitly according to the user's SIA roles."""

    BASE_QUERY_PARAMS = frozenset({'page', 'search', 'ordering', 'format'})
    KNOWN_FILTERS = frozenset({
        'status',
        'eh_violeiro',
        'canta',
        'palestrou',
    })
    SUMMARY_SEARCH_FIELDS = ('nome', 'telefone', 'grupo')
    ADMIN_SEARCH_FIELDS = ('nome', 'email', 'telefone', 'grupo')
    SUMMARY_ORDERING_FIELDS = ('nome', 'grupo')
    ADMIN_ORDERING_FIELDS = ('nome', 'dataNascimento', 'status')
    KNOWN_ORDERING_FIELDS = frozenset(
        SUMMARY_ORDERING_FIELDS + ADMIN_ORDERING_FIELDS
    )

    @classmethod
    def has_full_access(cls, user):
        return user.is_superuser or user_has_any_role(
            user,
            *FICHAS_MANAGEMENT_ROLES,
        )

    @classmethod
    def allowed_filters(cls, user):
        if cls.has_full_access(user):
            return cls.KNOWN_FILTERS

        allowed = set()
        if user_has_any_role(user, SiaRole.MME):
            allowed.update({'eh_violeiro', 'canta'})
        if user_has_any_role(user, SiaRole.FORMACAO):
            allowed.add('palestrou')
        return frozenset(allowed)

    @classmethod
    def search_fields(cls, user):
        if cls.has_full_access(user):
            return cls.ADMIN_SEARCH_FIELDS
        return cls.SUMMARY_SEARCH_FIELDS

    @classmethod
    def ordering_fields(cls, user):
        if cls.has_full_access(user):
            return cls.ADMIN_ORDERING_FIELDS
        return cls.SUMMARY_ORDERING_FIELDS

    @classmethod
    def validate(cls, user, query_params):
        supplied = set(query_params)
        supported = cls.BASE_QUERY_PARAMS | cls.KNOWN_FILTERS
        unknown = supplied - supported
        if unknown:
            raise ValidationError({
                'parametros': [
                    f"Parâmetros desconhecidos: {', '.join(sorted(unknown))}."
                ]
            })

        forbidden_filters = (
            supplied & cls.KNOWN_FILTERS
        ) - cls.allowed_filters(user)
        if forbidden_filters:
            raise PermissionDenied(
                'Seu papel não pode utilizar os filtros solicitados.'
            )

        ordering = query_params.get('ordering')
        if not ordering:
            return

        requested_fields = {
            item.removeprefix('-')
            for item in ordering.split(',')
            if item
        }
        allowed_ordering = set(cls.ordering_fields(user))
        forbidden_ordering = requested_fields - allowed_ordering
        if not forbidden_ordering:
            return
        if forbidden_ordering <= cls.KNOWN_ORDERING_FIELDS:
            raise PermissionDenied(
                'Seu papel não pode utilizar os campos de ordenação solicitados.'
            )
        raise ValidationError({
            'ordering': ['Um ou mais campos de ordenação são desconhecidos.']
        })


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

        action_roles = getattr(view, 'action_roles', {})
        action = getattr(view, 'action', None)
        if action in action_roles:
            allowed_roles = action_roles[action]
        elif request.method in SAFE_METHODS:
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


class IsSiaSuperuser(BasePermission):
    """Reserve technical endpoints for Django superusers."""

    message = 'Este endpoint é reservado à administração técnica.'

    def has_permission(self, request, view):
        user = request.user
        return bool(
            getattr(user, 'is_authenticated', False)
            and user.is_superuser
        )


def require_sia_roles(*roles):
    """Build a DRF permission configured for any one of the supplied roles."""

    class RequiredSiaRole(HasAnySiaRole):
        allowed_roles = roles

    return RequiredSiaRole
