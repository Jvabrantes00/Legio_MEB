from datetime import date, datetime

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from rest_framework.exceptions import PermissionDenied

from core.models import (
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    Encontro,
)
from core.permissions import (
    pode_consultar_configuracao_encontristas,
    pode_gerir_configuracao_encontristas,
)
from core.services.auditoria_encontros import (
    registrar_evento_auditoria_encontro,
)
from core.services.reposicao_campanha import (
    registrar_transicao_lotado_para_disponivel,
)


_NAO_INFORMADO = object()
_CAMPOS_CONFIGURACAO = frozenset({
    'capacidade',
    'idade_minima',
    'idade_maxima',
    'inscricoes_abrem_em',
    'inscricoes_encerram_em',
})


def _exigir_gestao(usuario):
    if not pode_gerir_configuracao_encontristas(usuario):
        raise PermissionDenied(
            'Seu usuário não pode alterar a configuração de encontristas.'
        )


def _encontro_persistido(encontro, *, bloquear=False):
    if encontro is None or encontro.pk is None:
        raise ValidationError('Encontro deve estar persistido.')
    queryset = Encontro.objects
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(pk=encontro.pk)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error


def _snapshot(configuracao, campos=_CAMPOS_CONFIGURACAO):
    return {
        campo: _valor_auditavel(getattr(configuracao, campo))
        for campo in campos
    }


def _valor_auditavel(valor):
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return valor


def _ocupacao_confirmada(encontro):
    return ConviteEncontro.objects.filter(
        encontro=encontro,
        finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        status=ConviteEncontro.Status.CONFIRMADO,
    ).count()


def _validar_capacidade_disponivel(encontro, capacidade):
    ocupacao = _ocupacao_confirmada(encontro)
    if capacidade < ocupacao:
        raise ValidationError({
            'capacidade': [
                'A capacidade não pode ser menor que a ocupação confirmada '
                f'atual ({ocupacao}).'
            ],
        })


def _validar_model(configuracao):
    configuracao.full_clean()


def consultar_configuracao_encontristas(*, usuario, encontro):
    if not pode_consultar_configuracao_encontristas(usuario):
        raise PermissionDenied(
            'Seu usuário não pode consultar a configuração de encontristas.'
        )
    encontro_persistido = _encontro_persistido(encontro)
    return (
        ConfiguracaoEncontristasEncontro.objects
        .filter(encontro=encontro_persistido)
        .select_related('encontro')
        .first()
    )


@transaction.atomic
def criar_configuracao_encontristas(
    *,
    usuario,
    encontro,
    capacidade,
    idade_minima,
    idade_maxima,
    inscricoes_abrem_em,
    inscricoes_encerram_em,
    justificativa='',
):
    _exigir_gestao(usuario)
    encontro_bloqueado = _encontro_persistido(encontro, bloquear=True)
    if ConfiguracaoEncontristasEncontro.objects.filter(
        encontro=encontro_bloqueado,
    ).exists():
        raise ValidationError(
            'O Encontro já possui configuração de encontristas.'
        )

    configuracao = ConfiguracaoEncontristasEncontro(
        encontro=encontro_bloqueado,
        capacidade=capacidade,
        idade_minima=idade_minima,
        idade_maxima=idade_maxima,
        inscricoes_abrem_em=inscricoes_abrem_em,
        inscricoes_encerram_em=inscricoes_encerram_em,
    )
    _validar_model(configuracao)
    _validar_capacidade_disponivel(encontro_bloqueado, capacidade)
    try:
        with transaction.atomic():
            configuracao.save()
    except IntegrityError as error:
        raise ValidationError(
            'Não foi possível criar a configuração de encontristas.'
        ) from error

    registrar_evento_auditoria_encontro(
        encontro=encontro_bloqueado,
        ator=usuario,
        fato='configuracao_encontristas.criada',
        entidade='configuracao_encontristas',
        objeto_id=configuracao.pk,
        valor_anterior={},
        valor_novo=_snapshot(configuracao),
        campos_permitidos=_CAMPOS_CONFIGURACAO,
        justificativa=justificativa,
    )
    return configuracao


@transaction.atomic
def alterar_configuracao_encontristas(
    *,
    usuario,
    configuracao,
    capacidade=_NAO_INFORMADO,
    idade_minima=_NAO_INFORMADO,
    idade_maxima=_NAO_INFORMADO,
    inscricoes_abrem_em=_NAO_INFORMADO,
    inscricoes_encerram_em=_NAO_INFORMADO,
    justificativa='',
):
    _exigir_gestao(usuario)
    if configuracao is None or configuracao.pk is None:
        raise ValidationError('Configuração deve estar persistida.')
    try:
        configuracao_bloqueada = (
            ConfiguracaoEncontristasEncontro.objects
            .select_for_update()
            .select_related('encontro')
            .get(pk=configuracao.pk)
        )
    except ConfiguracaoEncontristasEncontro.DoesNotExist as error:
        raise ValidationError('Configuração não encontrada.') from error

    valores = {
        'capacidade': capacidade,
        'idade_minima': idade_minima,
        'idade_maxima': idade_maxima,
        'inscricoes_abrem_em': inscricoes_abrem_em,
        'inscricoes_encerram_em': inscricoes_encerram_em,
    }
    informados = {
        campo: valor
        for campo, valor in valores.items()
        if valor is not _NAO_INFORMADO
    }
    if not informados:
        raise ValidationError('Informe ao menos um campo para alterar.')

    anteriores = _snapshot(configuracao_bloqueada, informados)
    capacidade_anterior = configuracao_bloqueada.capacidade
    ocupacao_anterior = _ocupacao_confirmada(
        configuracao_bloqueada.encontro
    )
    for campo, valor in informados.items():
        setattr(configuracao_bloqueada, campo, valor)
    novos = _snapshot(configuracao_bloqueada, informados)
    alterados = {
        campo
        for campo in informados
        if anteriores[campo] != novos[campo]
    }
    if not alterados:
        return configuracao_bloqueada

    _validar_model(configuracao_bloqueada)
    if 'capacidade' in alterados:
        _validar_capacidade_disponivel(
            configuracao_bloqueada.encontro,
            configuracao_bloqueada.capacidade,
        )
    configuracao_bloqueada.save(update_fields=sorted(alterados))

    if 'capacidade' in alterados:
        registrar_transicao_lotado_para_disponivel(
            encontro=configuracao_bloqueada.encontro,
            ocupacao_antes=ocupacao_anterior,
            capacidade_antes=capacidade_anterior,
            ocupacao_depois=ocupacao_anterior,
            capacidade_depois=configuracao_bloqueada.capacidade,
            motivo='capacidade_aumentada',
        )

    registrar_evento_auditoria_encontro(
        encontro=configuracao_bloqueada.encontro,
        ator=usuario,
        fato='configuracao_encontristas.alterada',
        entidade='configuracao_encontristas',
        objeto_id=configuracao_bloqueada.pk,
        valor_anterior={campo: anteriores[campo] for campo in alterados},
        valor_novo={campo: novos[campo] for campo in alterados},
        campos_permitidos=_CAMPOS_CONFIGURACAO,
        justificativa=justificativa,
    )
    return configuracao_bloqueada
