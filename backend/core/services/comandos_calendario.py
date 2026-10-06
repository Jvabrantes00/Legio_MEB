from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction

from core.models import Encontro
from core.services import encontros as encontro_services


def _datas_dos_dias(dias):
    datas = sorted(item['data'] for item in dias)
    if not datas or not all(isinstance(data_dia, date) for data_dia in datas):
        raise ValidationError('O calendário deve possuir ao menos um dia.')
    return datas


def _representacao_legada(datas):
    representacao = ', '.join(data_dia.isoformat() for data_dia in datas)
    if len(representacao) <= 150:
        return representacao
    return (
        f'{len(datas)} dias; primeiro: {datas[0].isoformat()}; '
        f'último: {datas[-1].isoformat()}'
    )


def _sincronizar_datas_legadas(encontro, dias):
    datas = _datas_dos_dias(dias)
    encontro.data_referencia = datas[0]
    encontro.data_exato = _representacao_legada(datas)
    encontro.save(update_fields=['data_referencia', 'data_exato'])


@transaction.atomic
def criar_encontro(*, titulo, tipo, local, dias):
    datas = _datas_dos_dias(dias)
    return encontro_services.criar_encontro_com_agenda(
        encontro=titulo,
        tipo=tipo,
        data_referencia=datas[0],
        data_exato=_representacao_legada(datas),
        local=local,
        dias=dias,
    )


@transaction.atomic
def editar_dados_basicos(encontro, *, titulo=None, local=None):
    return encontro_services.editar_dados_basicos(
        encontro,
        titulo=titulo,
        local=local,
    )


@transaction.atomic
def editar_planejamento(encontro, *, dias):
    calendario = encontro_services.editar_planejamento(encontro, dias=dias)
    _sincronizar_datas_legadas(calendario.encontro, dias)
    return calendario


@transaction.atomic
def oficializar_agenda(encontro):
    return encontro_services.oficializar_agenda(encontro)


@transaction.atomic
def reprogramar_agenda(encontro, *, dias):
    calendario = encontro_services.reprogramar_agenda(encontro, dias=dias)
    _sincronizar_datas_legadas(calendario.encontro, dias)
    return calendario


@transaction.atomic
def adiar_encontro(encontro):
    return encontro_services.adiar_encontro(encontro)


@transaction.atomic
def iniciar_novo_planejamento(encontro, *, dias):
    calendario = encontro_services.iniciar_novo_planejamento(
        encontro,
        dias=dias,
    )
    _sincronizar_datas_legadas(calendario.encontro, dias)
    return calendario


@transaction.atomic
def cancelar_encontro(encontro):
    return encontro_services.cancelar_encontro(encontro)
