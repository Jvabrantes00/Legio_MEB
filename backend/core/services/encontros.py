from collections.abc import Mapping
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.models import CalendarioEncontro, DiaEncontro, Encontro


TRANSICOES_STATUS = {
    Encontro.Status.EM_AGENDAMENTO: {
        Encontro.Status.AGENDADO,
        Encontro.Status.CANCELADO,
    },
    Encontro.Status.AGENDADO: {
        Encontro.Status.EM_PREPARACAO,
        Encontro.Status.ADIADO,
        Encontro.Status.CANCELADO,
    },
    Encontro.Status.EM_PREPARACAO: {
        Encontro.Status.EM_ANDAMENTO,
        Encontro.Status.ADIADO,
        Encontro.Status.CANCELADO,
    },
    Encontro.Status.EM_ANDAMENTO: {
        Encontro.Status.FINALIZADO,
        Encontro.Status.CANCELADO,
    },
    Encontro.Status.ADIADO: {
        Encontro.Status.EM_AGENDAMENTO,
        Encontro.Status.AGENDADO,
        Encontro.Status.CANCELADO,
    },
    Encontro.Status.FINALIZADO: set(),
    Encontro.Status.CANCELADO: set(),
}


def _normalizar_dias(dias):
    if dias is None:
        raise ValidationError('O calendário deve possuir ao menos um dia.')

    dias_normalizados = []
    ordens = set()
    datas = set()

    for item in dias:
        if not isinstance(item, Mapping):
            raise ValidationError('Cada dia deve ser informado por campos.')

        ordem = item.get('ordem')
        data_dia = item.get('data')
        descricao = item.get('descricao') or ''

        if not isinstance(descricao, str):
            raise ValidationError('A descrição de cada dia deve ser textual.')
        if not isinstance(ordem, int) or isinstance(ordem, bool) or ordem <= 0:
            raise ValidationError('A ordem de cada dia deve ser positiva.')
        if not isinstance(data_dia, date):
            raise ValidationError('A data de cada dia deve ser uma data válida.')
        if len(descricao) > 255:
            raise ValidationError(
                'A descrição de um dia não pode exceder 255 caracteres.'
            )
        if ordem in ordens:
            raise ValidationError('A ordem dos dias não pode se repetir.')
        if data_dia in datas:
            raise ValidationError(
                'Uma data não pode se repetir no mesmo calendário.'
            )

        ordens.add(ordem)
        datas.add(data_dia)
        dias_normalizados.append({
            'ordem': ordem,
            'data': data_dia,
            'descricao': descricao,
        })

    if not dias_normalizados:
        raise ValidationError('O calendário deve possuir ao menos um dia.')

    return sorted(dias_normalizados, key=lambda item: item['ordem'])


def _criar_dias(calendario, dias):
    return DiaEncontro.objects.bulk_create([
        DiaEncontro(calendario=calendario, **dia)
        for dia in dias
    ])


def _bloquear_encontro(encontro):
    return Encontro.objects.select_for_update().get(pk=encontro.pk)


def _obter_calendario_vigente(encontro):
    calendario = (
        CalendarioEncontro.objects
        .select_for_update()
        .filter(encontro=encontro, vigente=True)
        .first()
    )
    if calendario is None:
        raise ValidationError('O Encontro não possui calendário vigente.')
    return calendario


def _proxima_versao(encontro):
    maior_versao = (
        CalendarioEncontro.objects
        .filter(encontro=encontro)
        .aggregate(maior=Max('versao'))['maior']
    )
    return (maior_versao or 0) + 1


def _aplicar_transicao(encontro, novo_status):
    permitidos = TRANSICOES_STATUS.get(encontro.status, set())
    if novo_status not in permitidos:
        raise ValidationError(
            f'Transição de {encontro.status} para {novo_status} não permitida.'
        )
    encontro.status = novo_status
    encontro.save(update_fields=['status'])


def _exigir_agenda_oficial_vigente(encontro):
    calendario = _obter_calendario_vigente(encontro)
    if calendario.oficializado_em is None:
        raise ValidationError('O calendário vigente ainda não foi oficializado.')
    return calendario


@transaction.atomic
def editar_dados_basicos(encontro, *, titulo=None, local=None):
    encontro_bloqueado = _bloquear_encontro(encontro)
    campos_alterados = []
    if titulo is not None:
        encontro_bloqueado.encontro = titulo
        campos_alterados.append('encontro')
    if local is not None:
        encontro_bloqueado.local = local
        campos_alterados.append('local')
    if not campos_alterados:
        raise ValidationError('Informe ao menos um dado básico para alterar.')
    encontro_bloqueado.save(update_fields=campos_alterados)
    return encontro_bloqueado


@transaction.atomic
def criar_encontro_com_agenda(
    *,
    encontro,
    tipo,
    data_referencia,
    data_exato,
    local,
    dias,
):
    dias_normalizados = _normalizar_dias(dias)
    if tipo not in Encontro.Tipo.values:
        raise ValidationError('Tipo de Encontro inválido.')

    novo_encontro = Encontro.objects.create(
        encontro=encontro,
        tipo=tipo,
        data_referencia=data_referencia,
        data_exato=data_exato,
        local=local,
        status=Encontro.Status.EM_AGENDAMENTO,
    )
    calendario = CalendarioEncontro.objects.create(
        encontro=novo_encontro,
        versao=1,
        vigente=True,
    )
    _criar_dias(calendario, dias_normalizados)
    return novo_encontro


@transaction.atomic
def editar_planejamento(encontro, *, dias):
    dias_normalizados = _normalizar_dias(dias)
    encontro_bloqueado = _bloquear_encontro(encontro)
    if encontro_bloqueado.status != Encontro.Status.EM_AGENDAMENTO:
        raise ValidationError(
            'Somente Encontro em agendamento pode editar o planejamento.'
        )

    calendario = _obter_calendario_vigente(encontro_bloqueado)
    if calendario.oficializado_em is not None:
        raise ValidationError(
            'Uma agenda oficial não pode ser editada no próprio calendário.'
        )

    calendario.dias.all().delete()
    _criar_dias(calendario, dias_normalizados)
    return calendario


@transaction.atomic
def oficializar_agenda(encontro, *, momento=None):
    encontro_bloqueado = _bloquear_encontro(encontro)
    if encontro_bloqueado.status != Encontro.Status.EM_AGENDAMENTO:
        raise ValidationError(
            'Somente Encontro em agendamento pode oficializar sua agenda.'
        )

    calendario = _obter_calendario_vigente(encontro_bloqueado)
    if calendario.oficializado_em is not None:
        raise ValidationError('A agenda vigente já foi oficializada.')
    if not calendario.dias.exists():
        raise ValidationError('A agenda não pode ser oficializada sem dias.')

    calendario.oficializado_em = momento or timezone.now()
    calendario.save(update_fields=['oficializado_em'])
    _aplicar_transicao(encontro_bloqueado, Encontro.Status.AGENDADO)
    return calendario


@transaction.atomic
def reprogramar_agenda(encontro, *, dias, momento=None):
    dias_normalizados = _normalizar_dias(dias)
    encontro_bloqueado = _bloquear_encontro(encontro)
    if encontro_bloqueado.status not in {
        Encontro.Status.AGENDADO,
        Encontro.Status.ADIADO,
    }:
        raise ValidationError(
            'A reprogramação exige Encontro agendado ou adiado.'
        )

    instante = momento or timezone.now()
    calendario_anterior = None
    if encontro_bloqueado.status == Encontro.Status.AGENDADO:
        calendario_anterior = _exigir_agenda_oficial_vigente(
            encontro_bloqueado
        )
        calendario_anterior.vigente = False
        calendario_anterior.substituido_em = instante
        calendario_anterior.save(
            update_fields=['vigente', 'substituido_em']
        )
    elif CalendarioEncontro.objects.filter(
        encontro=encontro_bloqueado,
        vigente=True,
    ).exists():
        raise ValidationError(
            'Encontro adiado não pode possuir calendário vigente.'
        )

    novo_calendario = CalendarioEncontro.objects.create(
        encontro=encontro_bloqueado,
        versao=_proxima_versao(encontro_bloqueado),
        vigente=True,
        oficializado_em=instante,
    )
    _criar_dias(novo_calendario, dias_normalizados)

    if encontro_bloqueado.status == Encontro.Status.ADIADO:
        _aplicar_transicao(encontro_bloqueado, Encontro.Status.AGENDADO)
    return novo_calendario


@transaction.atomic
def adiar_encontro(encontro, *, momento=None):
    encontro_bloqueado = _bloquear_encontro(encontro)
    if encontro_bloqueado.status not in {
        Encontro.Status.AGENDADO,
        Encontro.Status.EM_PREPARACAO,
    }:
        raise ValidationError(
            'Somente Encontro agendado ou em preparação pode ser adiado.'
        )

    calendario = _exigir_agenda_oficial_vigente(encontro_bloqueado)
    calendario.vigente = False
    calendario.substituido_em = momento or timezone.now()
    calendario.save(update_fields=['vigente', 'substituido_em'])
    _aplicar_transicao(encontro_bloqueado, Encontro.Status.ADIADO)
    return calendario


@transaction.atomic
def iniciar_novo_planejamento(encontro, *, dias):
    dias_normalizados = _normalizar_dias(dias)
    encontro_bloqueado = _bloquear_encontro(encontro)
    if encontro_bloqueado.status != Encontro.Status.ADIADO:
        raise ValidationError(
            'Somente Encontro adiado pode iniciar novo planejamento.'
        )
    if CalendarioEncontro.objects.filter(
        encontro=encontro_bloqueado,
        vigente=True,
    ).exists():
        raise ValidationError(
            'Encontro adiado não pode possuir calendário vigente.'
        )

    calendario = CalendarioEncontro.objects.create(
        encontro=encontro_bloqueado,
        versao=_proxima_versao(encontro_bloqueado),
        vigente=True,
    )
    _criar_dias(calendario, dias_normalizados)
    _aplicar_transicao(
        encontro_bloqueado,
        Encontro.Status.EM_AGENDAMENTO,
    )
    return calendario


@transaction.atomic
def iniciar_preparacao(encontro):
    encontro_bloqueado = _bloquear_encontro(encontro)
    _exigir_agenda_oficial_vigente(encontro_bloqueado)
    _aplicar_transicao(
        encontro_bloqueado,
        Encontro.Status.EM_PREPARACAO,
    )
    return encontro_bloqueado


@transaction.atomic
def iniciar_encontro(encontro):
    encontro_bloqueado = _bloquear_encontro(encontro)
    _exigir_agenda_oficial_vigente(encontro_bloqueado)
    _aplicar_transicao(
        encontro_bloqueado,
        Encontro.Status.EM_ANDAMENTO,
    )
    return encontro_bloqueado


@transaction.atomic
def finalizar_encontro(encontro):
    encontro_bloqueado = _bloquear_encontro(encontro)
    _aplicar_transicao(encontro_bloqueado, Encontro.Status.FINALIZADO)
    return encontro_bloqueado


@transaction.atomic
def cancelar_encontro(encontro):
    encontro_bloqueado = _bloquear_encontro(encontro)
    _aplicar_transicao(encontro_bloqueado, Encontro.Status.CANCELADO)
    return encontro_bloqueado
