from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.db.models.deletion import ProtectedError

from core.models import (
    AvaliacaoEncontro,
    CalendarioEncontro,
    Encontro,
    ReuniaoPreparatoriaEncontro,
)
from core.services import avaliacoes_encontro as avaliacao_services
from core.services import encontros as encontro_services
from core.services import oportunidades_convites as oportunidade_services
from core.services import reunioes_preparatorias as reuniao_services


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
def criar_encontro(
    *,
    titulo,
    tipo,
    local,
    dias,
    reunioes=(),
    avaliacao=None,
    pre_encontro_data=None,
):
    datas = _datas_dos_dias(dias)
    encontro = encontro_services.criar_encontro_com_agenda(
        encontro=titulo,
        tipo=tipo,
        data_referencia=datas[0],
        data_exato=_representacao_legada(datas),
        local=local,
        dias=dias,
        pre_encontro_data=pre_encontro_data,
    )
    for reuniao in reunioes:
        reuniao_services.criar_reuniao_preparatoria(
            encontro=encontro,
            **reuniao,
        )
    if avaliacao is not None:
        avaliacao_services.criar_avaliacao_encontro(
            encontro=encontro,
            **avaliacao,
        )
    return encontro


@transaction.atomic
def editar_dados_basicos(encontro, *, titulo=None, local=None):
    return encontro_services.editar_dados_basicos(
        encontro,
        titulo=titulo,
        local=local,
    )


@transaction.atomic
def editar_planejamento(
    encontro,
    *,
    dias,
    pre_encontro_data=encontro_services.PRE_ENCONTRO_DATA_NAO_INFORMADA,
):
    calendario = encontro_services.editar_planejamento(
        encontro,
        dias=dias,
        pre_encontro_data=pre_encontro_data,
    )
    _sincronizar_datas_legadas(calendario.encontro, dias)
    return calendario


@transaction.atomic
def editar_rotulo_dia(encontro, *, dia_id, rotulo):
    return encontro_services.editar_rotulo_dia(
        encontro,
        dia_id=dia_id,
        rotulo=rotulo,
    )


def _planejamento_foi_alterado(encontro, *, dias, pre_encontro_data):
    calendario = (
        CalendarioEncontro.objects
        .select_for_update()
        .filter(encontro=encontro, vigente=True)
        .first()
    )
    if calendario is None:
        return True
    atuais = list(
        calendario.dias.order_by('ordem', 'id').values(
            'ordem',
            'data',
            'rotulo',
        )
    )
    recebidos = sorted(
        (
            {
                'ordem': item['ordem'],
                'data': item['data'],
                'rotulo': item.get('rotulo') or '',
            }
            for item in dias
        ),
        key=lambda item: item['ordem'],
    )
    return (
        atuais != recebidos
        or calendario.pre_encontro_data != pre_encontro_data
    )


def _sincronizar_reunioes(encontro, reunioes):
    existentes = {
        reuniao.pk: reuniao
        for reuniao in (
            ReuniaoPreparatoriaEncontro.objects
            .select_for_update()
            .filter(encontro=encontro)
            .order_by('ordem', 'pk')
        )
    }
    ids_recebidos = {
        item['id'] for item in reunioes if 'id' in item
    }
    desconhecidos = ids_recebidos - set(existentes)
    if desconhecidos:
        raise ValidationError(
            'Uma preparatória não pertence ao Encontro informado.'
        )

    try:
        for reuniao_id in set(existentes) - ids_recebidos:
            existentes[reuniao_id].delete()
    except ProtectedError as error:
        raise ValidationError(
            'Preparatória com presença registrada não pode ser removida.'
        ) from error

    mantidas = [
        reuniao for reuniao_id, reuniao in existentes.items()
        if reuniao_id in ids_recebidos
    ]
    if mantidas:
        maior_ordem = max(
            [reuniao.ordem for reuniao in mantidas]
            + [item['ordem'] for item in reunioes]
        )
        deslocamento = maior_ordem + len(mantidas) + 1
        ReuniaoPreparatoriaEncontro.objects.filter(
            pk__in=[reuniao.pk for reuniao in mantidas]
        ).update(ordem=F('ordem') + deslocamento)

    for item in reunioes:
        dados = dict(item)
        reuniao_id = dados.pop('id', None)
        if reuniao_id is None:
            reuniao_services.criar_reuniao_preparatoria(
                encontro=encontro,
                **dados,
            )
            continue

        reuniao = existentes[reuniao_id]
        valores = {
            'ordem': dados['ordem'],
            'data': dados['data'],
            'horario': dados.get('horario', reuniao.horario),
            'local': dados.get('local', reuniao.local),
            'complemento': dados.get(
                'complemento',
                reuniao.complemento,
            ),
        }
        reuniao_services.editar_reuniao_preparatoria(
            reuniao,
            **valores,
        )


def _sincronizar_avaliacao(encontro, avaliacao):
    existente = (
        AvaliacaoEncontro.objects
        .select_for_update()
        .filter(encontro=encontro)
        .first()
    )
    if avaliacao is None:
        if existente is not None:
            avaliacao_services.remover_avaliacao_encontro(existente)
        return
    if existente is None:
        avaliacao_services.criar_avaliacao_encontro(
            encontro=encontro,
            **avaliacao,
        )
    elif existente.data != avaliacao['data']:
        avaliacao_services.editar_avaliacao_encontro(
            existente,
            **avaliacao,
        )


@transaction.atomic
def salvar_edicao(
    encontro,
    *,
    titulo,
    dias,
    pre_encontro_data,
    reunioes,
    avaliacao,
    local=None,
    ator=None,
):
    try:
        encontro_bloqueado = (
            Encontro.objects.select_for_update().get(pk=encontro.pk)
        )
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error

    dados_basicos = {}
    if encontro_bloqueado.encontro != titulo:
        dados_basicos['titulo'] = titulo
    if local is not None and encontro_bloqueado.local != local:
        dados_basicos['local'] = local
    if dados_basicos:
        encontro_bloqueado = editar_dados_basicos(
            encontro_bloqueado,
            **dados_basicos,
        )

    if _planejamento_foi_alterado(
        encontro_bloqueado,
        dias=dias,
        pre_encontro_data=pre_encontro_data,
    ):
        if encontro_bloqueado.status == Encontro.Status.EM_AGENDAMENTO:
            editar_planejamento(
                encontro_bloqueado,
                dias=dias,
                pre_encontro_data=pre_encontro_data,
            )
        elif encontro_bloqueado.status in {
            Encontro.Status.AGENDADO,
            Encontro.Status.ADIADO,
        }:
            reprogramar_agenda(
                encontro_bloqueado,
                dias=dias,
                pre_encontro_data=pre_encontro_data,
                ator=ator,
            )
        else:
            raise ValidationError(
                'O estado atual não permite alterar a agenda temporal.'
            )

    _sincronizar_reunioes(encontro_bloqueado, reunioes)
    _sincronizar_avaliacao(encontro_bloqueado, avaliacao)
    return encontro_bloqueado


@transaction.atomic
def oficializar_agenda(encontro):
    return encontro_services.oficializar_agenda(encontro)


@transaction.atomic
def reprogramar_agenda(
    encontro,
    *,
    dias,
    pre_encontro_data=encontro_services.PRE_ENCONTRO_DATA_NAO_INFORMADA,
    ator=None,
):
    calendario = encontro_services.reprogramar_agenda(
        encontro,
        dias=dias,
        pre_encontro_data=pre_encontro_data,
    )
    _sincronizar_datas_legadas(calendario.encontro, dias)
    oportunidade_services.reconciliar_oportunidades_apos_reprogramacao(
        encontro=calendario.encontro,
        ator=ator,
    )
    return calendario


@transaction.atomic
def adiar_encontro(encontro):
    return encontro_services.adiar_encontro(encontro)


@transaction.atomic
def iniciar_novo_planejamento(
    encontro,
    *,
    dias,
    pre_encontro_data=encontro_services.PRE_ENCONTRO_DATA_NAO_INFORMADA,
):
    calendario = encontro_services.iniciar_novo_planejamento(
        encontro,
        dias=dias,
        pre_encontro_data=pre_encontro_data,
    )
    _sincronizar_datas_legadas(calendario.encontro, dias)
    return calendario


@transaction.atomic
def cancelar_encontro(encontro):
    return encontro_services.cancelar_encontro(encontro)
