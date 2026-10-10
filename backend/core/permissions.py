from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .models import (
    Encontro,
    PresencaPreparatoria,
    ReuniaoPreparatoriaEncontro,
    TrabalhoEncontro,
    VinculoUsuarioPessoa,
)
from .roles import (
    FICHAS_MANAGEMENT_ROLES,
    FULL_ADMIN_ROLES,
    SiaRole,
    user_has_any_role,
)


def pode_consultar_auditoria_encontro(user):
    if not (
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', False)
    ):
        return False
    return bool(
        user.is_superuser
        or user_has_any_role(user, *FULL_ADMIN_ROLES)
    )


def pode_gerir_configuracao_encontristas(user):
    if not (
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', False)
    ):
        return False
    return bool(
        user.is_superuser
        or user_has_any_role(user, *FULL_ADMIN_ROLES)
    )


def pode_consultar_configuracao_encontristas(user):
    if not (
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', False)
    ):
        return False
    return bool(
        user.is_superuser
        or user_has_any_role(user, *FICHAS_MANAGEMENT_ROLES)
    )


def pode_resolver_cadastro_inscricao(user):
    if not (
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', False)
    ):
        return False
    return bool(
        user.is_superuser
        or user_has_any_role(user, *FICHAS_MANAGEMENT_ROLES)
    )


def pode_gerir_campanha_convites(user):
    if not (
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', False)
    ):
        return False
    return bool(
        user.is_superuser
        or user_has_any_role(user, SiaRole.FICHAS)
    )


def pode_consultar_campanha_convites(user):
    if not (
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', False)
    ):
        return False
    return bool(
        user.is_superuser
        or user_has_any_role(user, *FICHAS_MANAGEMENT_ROLES)
    )


def _usuario_ativo(user):
    return bool(
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', False)
    )


def pertence_coordenacao_geral_encontro(user, encontro):
    if not (
        _usuario_ativo(user)
        and encontro is not None
        and encontro.pk is not None
    ):
        return False
    try:
        pessoa_id = user.vinculo_pessoa.pessoa_id
    except VinculoUsuarioPessoa.DoesNotExist:
        return False
    return TrabalhoEncontro.objects.filter(
        pessoa_id=pessoa_id,
        encontro=encontro,
        status=TrabalhoEncontro.Status.ALOCADO,
        role_equipe__equipe_encontro__encontro=encontro,
        role_equipe__equipe_encontro__codigo='coordenacao-geral',
    ).exists()


def pode_operar_checkin_pre_encontro(user, encontro):
    del encontro
    return bool(
        _usuario_ativo(user)
        and (
            user.is_superuser
            or user_has_any_role(user, *FICHAS_MANAGEMENT_ROLES)
        )
    )


def pode_regularizar_pre_encontro(user, encontro):
    del encontro
    return pode_resolver_cadastro_inscricao(user)


def pode_registrar_pagamento_pre_encontro(user, encontro):
    return bool(
        _usuario_ativo(user)
        and (
            user.is_superuser
            or user_has_any_role(user, *FICHAS_MANAGEMENT_ROLES)
            or pertence_coordenacao_geral_encontro(user, encontro)
        )
    )


def pode_conferir_cuidados_pre_encontro(user, encontro):
    return bool(
        _usuario_ativo(user)
        and (
            user.is_superuser
            or user_has_any_role(user, *FICHAS_MANAGEMENT_ROLES)
            or pertence_coordenacao_geral_encontro(user, encontro)
        )
    )


def pode_resolver_vaga_pre_encontro(user, encontro):
    del encontro
    return bool(
        _usuario_ativo(user)
        and (
            user.is_superuser
            or user_has_any_role(user, SiaRole.DIRETORIA)
        )
    )


def pode_aumentar_capacidade_pre_encontro(user, encontro):
    del encontro
    return pode_gerir_configuracao_encontristas(user)


def pode_registrar_presenca_preparatoria(user, encontro):
    if not (
        getattr(user, 'is_authenticated', False)
        and getattr(user, 'is_active', False)
        and encontro is not None
        and encontro.pk is not None
    ):
        return False
    if user.is_superuser or user_has_any_role(
        user,
        *FICHAS_MANAGEMENT_ROLES,
    ):
        return True
    if encontro.status in {
        Encontro.Status.FINALIZADO,
        Encontro.Status.CANCELADO,
    }:
        return False

    try:
        pessoa_id = user.vinculo_pessoa.pessoa_id
    except VinculoUsuarioPessoa.DoesNotExist:
        return False

    return TrabalhoEncontro.objects.filter(
        pessoa_id=pessoa_id,
        encontro=encontro,
        status=TrabalhoEncontro.Status.ALOCADO,
        role_equipe__concede_registro_presenca=True,
        role_equipe__equipe_encontro__encontro=encontro,
        role_equipe__template_origem__template_equipe=F(
            'role_equipe__equipe_encontro__template_origem'
        ),
    ).exists()


class CanRegisterPreparatoryAttendance(BasePermission):
    message = (
        'Seu usuário não pode registrar presença preparatória neste Encontro.'
    )

    def has_permission(self, request, view):
        user = request.user
        if not (
            getattr(user, 'is_authenticated', False)
            and getattr(user, 'is_active', False)
        ):
            return False
        if user.is_superuser or user_has_any_role(
            user,
            *FICHAS_MANAGEMENT_ROLES,
        ):
            return True
        return VinculoUsuarioPessoa.objects.filter(usuario=user).exists()

    def has_object_permission(self, request, view, obj):
        if isinstance(obj, PresencaPreparatoria):
            encontro = obj.reuniao.encontro
        elif isinstance(obj, ReuniaoPreparatoriaEncontro):
            encontro = obj.encontro
        else:
            return False
        return pode_registrar_presenca_preparatoria(request.user, encontro)


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
