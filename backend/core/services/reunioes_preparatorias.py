from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Exists, OuterRef

from core.models import (
    Encontro,
    PresencaPreparatoria,
    ReuniaoPreparatoriaEncontro,
    TrabalhoEncontro,
)
from core.services.trabalhos import _bloquear_contexto_trabalho


NAO_INFORMADO = object()


def _pk(instance, nome):
    if instance is None or instance.pk is None:
        raise ValidationError(f'{nome} deve estar persistido.')
    return instance.pk


def _bloquear_encontro(encontro):
    encontro_id = _pk(encontro, 'Encontro')
    try:
        return Encontro.objects.select_for_update().get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error


def _bloquear_reuniao(reuniao):
    reuniao_id = _pk(reuniao, 'Reunião preparatória')
    try:
        return (
            ReuniaoPreparatoriaEncontro.objects
            .select_for_update()
            .get(pk=reuniao_id)
        )
    except ReuniaoPreparatoriaEncontro.DoesNotExist as error:
        raise ValidationError('Reunião preparatória não encontrada.') from error


def _obter_usuario(usuario):
    usuario_id = _pk(usuario, 'Usuário registrador')
    try:
        return User.objects.get(pk=usuario_id)
    except User.DoesNotExist as error:
        raise ValidationError('Usuário registrador não encontrado.') from error


def _validar_ordem(ordem):
    if not isinstance(ordem, int) or isinstance(ordem, bool) or ordem <= 0:
        raise ValidationError('A ordem da reunião deve ser positiva.')


def _validar_status_presenca(status):
    if status not in PresencaPreparatoria.Status.values:
        raise ValidationError('Status de presença inválido.')


def _validar_contexto(reuniao, trabalho):
    if reuniao.encontro_id != trabalho.encontro_id:
        raise ValidationError(
            'A reunião e o trabalho devem pertencer ao mesmo Encontro.'
        )


@transaction.atomic
def criar_reuniao_preparatoria(
    *,
    encontro,
    ordem,
    data,
    horario,
    local,
    observacoes='',
):
    encontro_bloqueado = _bloquear_encontro(encontro)
    _validar_ordem(ordem)

    try:
        with transaction.atomic():
            return ReuniaoPreparatoriaEncontro.objects.create(
                encontro=encontro_bloqueado,
                ordem=ordem,
                data=data,
                horario=horario,
                local=local,
                observacoes=observacoes,
            )
    except IntegrityError as error:
        raise ValidationError(
            'Já existe reunião com esta ordem neste Encontro.'
        ) from error


@transaction.atomic
def editar_reuniao_preparatoria(
    reuniao,
    *,
    ordem=NAO_INFORMADO,
    data=NAO_INFORMADO,
    horario=NAO_INFORMADO,
    local=NAO_INFORMADO,
    observacoes=NAO_INFORMADO,
):
    encontro_bloqueado = _bloquear_encontro(reuniao.encontro)
    reuniao_bloqueada = _bloquear_reuniao(reuniao)
    if reuniao_bloqueada.encontro_id != encontro_bloqueado.pk:
        raise ValidationError('A reunião não pertence ao Encontro informado.')

    campos = {
        'ordem': ordem,
        'data': data,
        'horario': horario,
        'local': local,
        'observacoes': observacoes,
    }
    if ordem is not NAO_INFORMADO:
        _validar_ordem(ordem)

    alterados = []
    for campo, valor in campos.items():
        if valor is NAO_INFORMADO:
            continue
        setattr(reuniao_bloqueada, campo, valor)
        alterados.append(campo)
    if not alterados:
        return reuniao_bloqueada

    try:
        with transaction.atomic():
            reuniao_bloqueada.save(
                update_fields=[*alterados, 'atualizado_em']
            )
    except IntegrityError as error:
        raise ValidationError(
            'Já existe reunião com esta ordem neste Encontro.'
        ) from error
    return reuniao_bloqueada


@transaction.atomic
def registrar_presenca_preparatoria(
    *,
    reuniao,
    trabalho,
    status,
    registrada_por,
    justificativa='',
):
    trabalho_bloqueado, _, _, _ = _bloquear_contexto_trabalho(trabalho)
    reuniao_bloqueada = _bloquear_reuniao(reuniao)
    usuario = _obter_usuario(registrada_por)
    _validar_contexto(reuniao_bloqueada, trabalho_bloqueado)
    _validar_status_presenca(status)

    existente = (
        PresencaPreparatoria.objects
        .select_for_update()
        .filter(
            reuniao=reuniao_bloqueada,
            trabalho=trabalho_bloqueado,
        )
        .first()
    )
    if existente is not None:
        if (
            existente.status == status
            and existente.justificativa == justificativa
            and existente.registrada_por_id == usuario.pk
        ):
            return existente
        raise ValidationError(
            'A presença já foi registrada; use a operação de correção.'
        )

    try:
        with transaction.atomic():
            return PresencaPreparatoria.objects.create(
                reuniao=reuniao_bloqueada,
                trabalho=trabalho_bloqueado,
                status=status,
                justificativa=justificativa,
                registrada_por=usuario,
            )
    except IntegrityError as error:
        raise ValidationError(
            'A presença já foi registrada para este trabalho e reunião.'
        ) from error


@transaction.atomic
def corrigir_presenca_preparatoria(
    presenca,
    *,
    status,
    registrada_por,
    justificativa='',
):
    presenca_id = _pk(presenca, 'Presença preparatória')
    trabalho_bloqueado, _, _, _ = _bloquear_contexto_trabalho(
        presenca.trabalho
    )
    reuniao_bloqueada = _bloquear_reuniao(presenca.reuniao)
    usuario = _obter_usuario(registrada_por)
    _validar_contexto(reuniao_bloqueada, trabalho_bloqueado)
    _validar_status_presenca(status)

    try:
        presenca_bloqueada = (
            PresencaPreparatoria.objects
            .select_for_update()
            .get(pk=presenca_id)
        )
    except PresencaPreparatoria.DoesNotExist as error:
        raise ValidationError('Presença preparatória não encontrada.') from error
    if (
        presenca_bloqueada.reuniao_id != reuniao_bloqueada.pk
        or presenca_bloqueada.trabalho_id != trabalho_bloqueado.pk
    ):
        raise ValidationError('O vínculo da presença preparatória é incoerente.')

    if (
        presenca_bloqueada.status == status
        and presenca_bloqueada.justificativa == justificativa
        and presenca_bloqueada.registrada_por_id == usuario.pk
    ):
        return presenca_bloqueada

    presenca_bloqueada.status = status
    presenca_bloqueada.justificativa = justificativa
    presenca_bloqueada.registrada_por = usuario
    presenca_bloqueada.save(
        update_fields=[
            'status',
            'justificativa',
            'registrada_por',
            'atualizado_em',
        ]
    )
    return presenca_bloqueada


def anotar_revisao_permanencia(queryset=None):
    queryset = queryset if queryset is not None else TrabalhoEncontro.objects.all()
    ausencias = PresencaPreparatoria.objects.filter(
        trabalho_id=OuterRef('pk'),
        status=PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA,
    )
    return queryset.annotate(requer_revisao=Exists(ausencias))


def trabalho_requer_revisao(trabalho):
    trabalho_id = _pk(trabalho, 'Trabalho')
    try:
        return (
            anotar_revisao_permanencia(
                TrabalhoEncontro.objects.filter(pk=trabalho_id)
            )
            .values_list('requer_revisao', flat=True)
            .get()
        )
    except TrabalhoEncontro.DoesNotExist as error:
        raise ValidationError('Trabalho não encontrado.') from error
