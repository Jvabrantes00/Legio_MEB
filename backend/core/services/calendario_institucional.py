from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date

from core.models import (
    AvaliacaoEncontro,
    CalendarioEncontro,
    DiaEncontro,
    Encontro,
    ReuniaoPreparatoriaEncontro,
)


CATEGORIA_ENCONTRO = 'ENCONTRO'
ORIGEM_CANONICA = 'CANONICA'
ORIGEM_LEGADO = 'LEGADO'
CONFIRMACAO_PROVISORIA = 'PROVISORIA'
CONFIRMACAO_OFICIAL = 'OFICIAL'
CONFIRMACAO_INDETERMINADA = 'INDETERMINADA'
TIPO_DIA_ENCONTRO = 'DIA_ENCONTRO'
TIPO_REUNIAO_PREPARATORIA = 'REUNIAO_PREPARATORIA'
TIPO_AVALIACAO = 'AVALIACAO'
MAXIMO_DIAS_INTERVALO = 366

_ORDEM_TIPO_AGENDA = {
    TIPO_DIA_ENCONTRO: 0,
    TIPO_REUNIAO_PREPARATORIA: 1,
    TIPO_AVALIACAO: 2,
}


@dataclass(frozen=True)
class ConflitoCalendarioDTO:
    data: date
    encontro_ids: tuple[int, ...]
    quantidade: int


@dataclass(frozen=True)
class DiaCalendarioDTO:
    id: int | None
    data: date
    ordem: int
    rotulo: str
    conflito: ConflitoCalendarioDTO | None = None


@dataclass(frozen=True)
class ItemAgendaEncontroDTO:
    id: str
    origem_id: int | None
    origem: str
    data: date
    titulo: str
    subtitulo: str | None
    confirmacao: str | None
    publicavel_externamente: bool
    encontro_id: int
    conflito: ConflitoCalendarioDTO | None = None


@dataclass(frozen=True)
class ItemCalendarioEncontroDTO:
    categoria: str
    encontro_id: int
    titulo: str
    tipo: str
    status: str
    calendario_id: int | None
    calendario_versao: int | None
    origem_agenda: str
    confirmacao: str
    dias: tuple[DiaCalendarioDTO, ...]
    agenda: tuple[ItemAgendaEncontroDTO, ...]


@dataclass(frozen=True)
class AgendaEncontroDTO:
    encontro_id: int
    itens: tuple[ItemAgendaEncontroDTO, ...]


@dataclass(frozen=True)
class PeriodoCalendarioDTO:
    inicio: date
    fim: date


@dataclass(frozen=True)
class ConsultaCalendarioInstitucionalDTO:
    periodo: PeriodoCalendarioDTO
    itens: tuple[ItemCalendarioEncontroDTO, ...]
    conflitos: tuple[ConflitoCalendarioDTO, ...]


def _validar_periodo(inicio, fim):
    if inicio > fim:
        raise ValueError('A data inicial não pode ser posterior à data final.')
    if (fim - inicio).days >= MAXIMO_DIAS_INTERVALO:
        raise ValueError(
            'O intervalo não pode ultrapassar um ano civil completo.'
        )


def _confirmacao(calendario):
    if calendario is None:
        return CONFIRMACAO_INDETERMINADA
    return (
        CONFIRMACAO_OFICIAL
        if calendario.oficializado_em is not None
        else CONFIRMACAO_PROVISORIA
    )


def _item_dia(dia, encontro, confirmacao):
    return ItemAgendaEncontroDTO(
        id=f'{TIPO_DIA_ENCONTRO}:{dia.pk}',
        origem_id=dia.pk,
        origem=TIPO_DIA_ENCONTRO,
        data=dia.data,
        titulo=dia.rotulo or encontro.encontro,
        subtitulo=encontro.encontro if dia.rotulo else None,
        confirmacao=confirmacao,
        publicavel_externamente=True,
        encontro_id=encontro.pk,
    )


def _item_reuniao(reuniao):
    return ItemAgendaEncontroDTO(
        id=f'{TIPO_REUNIAO_PREPARATORIA}:{reuniao.pk}',
        origem_id=reuniao.pk,
        origem=TIPO_REUNIAO_PREPARATORIA,
        data=reuniao.data,
        titulo=f'{reuniao.ordem}ª Reunião',
        subtitulo=reuniao.complemento or None,
        confirmacao=None,
        publicavel_externamente=False,
        encontro_id=reuniao.encontro_id,
    )


def _item_avaliacao(avaliacao):
    return ItemAgendaEncontroDTO(
        id=f'{TIPO_AVALIACAO}:{avaliacao.pk}',
        origem_id=avaliacao.pk,
        origem=TIPO_AVALIACAO,
        data=avaliacao.data,
        titulo='Avaliação',
        subtitulo=None,
        confirmacao=None,
        publicavel_externamente=False,
        encontro_id=avaliacao.encontro_id,
    )


def _chave_agenda(item):
    return (
        item.data,
        _ORDEM_TIPO_AGENDA[item.origem],
        item.titulo.casefold(),
        item.origem_id or 0,
    )


def _novo_item_encontro(encontro, *, calendario=None):
    return ItemCalendarioEncontroDTO(
        categoria=CATEGORIA_ENCONTRO,
        encontro_id=encontro.pk,
        titulo=encontro.encontro,
        tipo=encontro.tipo,
        status=encontro.status,
        calendario_id=calendario.pk if calendario else None,
        calendario_versao=calendario.versao if calendario else None,
        origem_agenda=ORIGEM_CANONICA,
        confirmacao=_confirmacao(calendario),
        dias=(),
        agenda=(),
    )


def _adicionar_agenda(agrupados, encontro, item_agenda, *, dia=None):
    item = agrupados.get(encontro.pk) or _novo_item_encontro(encontro)
    agrupados[encontro.pk] = replace(
        item,
        dias=(*item.dias, dia) if dia is not None else item.dias,
        agenda=(*item.agenda, item_agenda),
    )


def _itens_canonicos(inicio, fim):
    agrupados = {}
    dias = (
        DiaEncontro.objects.filter(
            data__gte=inicio,
            data__lte=fim,
            calendario__vigente=True,
        )
        .select_related('calendario__encontro')
        .order_by('data', 'ordem', 'calendario__encontro_id', 'id')
    )
    for dia in dias:
        calendario = dia.calendario
        encontro = calendario.encontro
        confirmacao = _confirmacao(calendario)
        if encontro.pk not in agrupados:
            agrupados[encontro.pk] = _novo_item_encontro(
                encontro,
                calendario=calendario,
            )
        _adicionar_agenda(
            agrupados,
            encontro,
            _item_dia(dia, encontro, confirmacao),
            dia=DiaCalendarioDTO(
                id=dia.pk,
                data=dia.data,
                ordem=dia.ordem,
                rotulo=dia.rotulo,
            ),
        )

    reunioes = (
        ReuniaoPreparatoriaEncontro.objects.filter(
            data__gte=inicio,
            data__lte=fim,
        )
        .select_related('encontro')
        .order_by('data', 'ordem', 'encontro_id', 'id')
    )
    for reuniao in reunioes:
        _adicionar_agenda(
            agrupados,
            reuniao.encontro,
            _item_reuniao(reuniao),
        )

    avaliacoes = (
        AvaliacaoEncontro.objects.filter(
            data__gte=inicio,
            data__lte=fim,
        )
        .select_related('encontro')
        .order_by('data', 'encontro_id', 'id')
    )
    for avaliacao in avaliacoes:
        _adicionar_agenda(
            agrupados,
            avaliacao.encontro,
            _item_avaliacao(avaliacao),
        )

    sem_calendario_no_periodo = {
        encontro_id
        for encontro_id, item in agrupados.items()
        if item.calendario_id is None
    }
    if sem_calendario_no_periodo:
        calendarios_por_encontro = defaultdict(list)
        for calendario in CalendarioEncontro.objects.filter(
            encontro_id__in=sem_calendario_no_periodo,
        ):
            calendarios_por_encontro[calendario.encontro_id].append(calendario)
        for encontro_id in sem_calendario_no_periodo:
            calendarios = calendarios_por_encontro[encontro_id]
            calendario = next(
                (item for item in calendarios if item.vigente),
                None,
            )
            item = agrupados[encontro_id]
            if calendario is None:
                if not calendarios:
                    agrupados[encontro_id] = replace(
                        item,
                        origem_agenda=ORIGEM_LEGADO,
                    )
                continue
            agrupados[encontro_id] = replace(
                item,
                calendario_id=calendario.pk,
                calendario_versao=calendario.versao,
                confirmacao=_confirmacao(calendario),
            )

    return [
        replace(item, agenda=tuple(sorted(item.agenda, key=_chave_agenda)))
        for item in agrupados.values()
    ]


def _itens_legados(inicio, fim):
    encontros = (
        Encontro.objects.filter(
            calendarios__isnull=True,
            data_referencia__gte=inicio,
            data_referencia__lte=fim,
        )
        .order_by('data_referencia', 'encontro', 'id')
    )
    itens = []
    for encontro in encontros:
        agenda = ItemAgendaEncontroDTO(
            id=f'{TIPO_DIA_ENCONTRO}:LEGADO:{encontro.pk}',
            origem_id=None,
            origem=TIPO_DIA_ENCONTRO,
            data=encontro.data_referencia,
            titulo=encontro.encontro,
            subtitulo=None,
            confirmacao=CONFIRMACAO_INDETERMINADA,
            publicavel_externamente=True,
            encontro_id=encontro.pk,
        )
        itens.append(ItemCalendarioEncontroDTO(
            categoria=CATEGORIA_ENCONTRO,
            encontro_id=encontro.pk,
            titulo=encontro.encontro,
            tipo=encontro.tipo,
            status=encontro.status,
            calendario_id=None,
            calendario_versao=None,
            origem_agenda=ORIGEM_LEGADO,
            confirmacao=CONFIRMACAO_INDETERMINADA,
            dias=(DiaCalendarioDTO(
                id=None,
                data=encontro.data_referencia,
                ordem=1,
                rotulo='',
            ),),
            agenda=(agenda,),
        ))
    return itens


def _detectar_conflitos(itens):
    encontros_por_data = defaultdict(set)
    for item in itens:
        for compromisso in item.agenda:
            encontros_por_data[compromisso.data].add(item.encontro_id)
    return tuple(
        ConflitoCalendarioDTO(
            data=data_item,
            encontro_ids=tuple(sorted(encontro_ids)),
            quantidade=len(encontro_ids),
        )
        for data_item, encontro_ids in sorted(encontros_por_data.items())
        if len(encontro_ids) > 1
    )


def detectar_conflitos_para_encontro(encontro_id, datas):
    """Return advisory overlaps across every dated Encounter agenda source."""
    datas = tuple(sorted(set(datas)))
    if not datas:
        return ()

    encontros_por_data = defaultdict(set)
    fontes = (
        DiaEncontro.objects.filter(
            data__in=datas,
            calendario__vigente=True,
        ).exclude(calendario__encontro_id=encontro_id).values_list(
            'data', 'calendario__encontro_id'
        ),
        ReuniaoPreparatoriaEncontro.objects.filter(
            data__in=datas,
        ).exclude(encontro_id=encontro_id).values_list('data', 'encontro_id'),
        AvaliacaoEncontro.objects.filter(data__in=datas).exclude(
            encontro_id=encontro_id
        ).values_list('data', 'encontro_id'),
        Encontro.objects.filter(
            calendarios__isnull=True,
            data_referencia__in=datas,
        ).exclude(pk=encontro_id).values_list('data_referencia', 'pk'),
    )
    for fonte in fontes:
        for data_item, outro_id in fonte:
            encontros_por_data[data_item].add(outro_id)

    return tuple(
        ConflitoCalendarioDTO(
            data=data_item,
            encontro_ids=tuple(sorted({encontro_id, *outros_ids})),
            quantidade=len(outros_ids) + 1,
        )
        for data_item, outros_ids in sorted(encontros_por_data.items())
        if outros_ids
    )


def _anotar_conflitos(itens, conflitos):
    conflitos_por_data = {conflito.data: conflito for conflito in conflitos}
    return tuple(
        replace(
            item,
            dias=tuple(
                replace(dia, conflito=conflitos_por_data.get(dia.data))
                for dia in item.dias
            ),
            agenda=tuple(
                replace(
                    compromisso,
                    conflito=conflitos_por_data.get(compromisso.data),
                )
                for compromisso in item.agenda
            ),
        )
        for item in itens
    )


def consultar_agenda_encontro(encontro):
    calendario = (
        CalendarioEncontro.objects
        .filter(encontro=encontro, vigente=True)
        .first()
    )
    itens = []
    if calendario is not None:
        confirmacao = _confirmacao(calendario)
        itens.extend(
            _item_dia(dia, encontro, confirmacao)
            for dia in calendario.dias.order_by('ordem', 'id')
        )
    elif not encontro.calendarios.exists():
        itens.append(ItemAgendaEncontroDTO(
            id=f'{TIPO_DIA_ENCONTRO}:LEGADO:{encontro.pk}',
            origem_id=None,
            origem=TIPO_DIA_ENCONTRO,
            data=encontro.data_referencia,
            titulo=encontro.encontro,
            subtitulo=None,
            confirmacao=CONFIRMACAO_INDETERMINADA,
            publicavel_externamente=True,
            encontro_id=encontro.pk,
        ))
    itens.extend(
        _item_reuniao(reuniao)
        for reuniao in encontro.reunioes_preparatorias.order_by('ordem', 'id')
    )
    try:
        avaliacao = encontro.avaliacao_agenda
    except AvaliacaoEncontro.DoesNotExist:
        avaliacao = None
    if avaliacao is not None:
        itens.append(_item_avaliacao(avaliacao))
    return AgendaEncontroDTO(
        encontro_id=encontro.pk,
        itens=tuple(sorted(itens, key=_chave_agenda)),
    )


def consultar_calendario_institucional(inicio, fim):
    """Project dated Encounter agenda sources for an inclusive date range."""
    _validar_periodo(inicio, fim)
    itens = _itens_canonicos(inicio, fim)
    por_encontro = {item.encontro_id: item for item in itens}
    for legado in _itens_legados(inicio, fim):
        atual = por_encontro.get(legado.encontro_id)
        if atual is None:
            itens.append(legado)
            por_encontro[legado.encontro_id] = legado
            continue
        combinado = replace(
            atual,
            origem_agenda=ORIGEM_LEGADO,
            confirmacao=CONFIRMACAO_INDETERMINADA,
            dias=(*atual.dias, *legado.dias),
            agenda=tuple(sorted(
                (*atual.agenda, *legado.agenda),
                key=_chave_agenda,
            )),
        )
        itens[itens.index(atual)] = combinado
        por_encontro[legado.encontro_id] = combinado
    itens.sort(
        key=lambda item: (
            item.agenda[0].data,
            _ORDEM_TIPO_AGENDA[item.agenda[0].origem],
            item.titulo.casefold(),
            item.encontro_id,
        )
    )
    conflitos = _detectar_conflitos(itens)
    return ConsultaCalendarioInstitucionalDTO(
        periodo=PeriodoCalendarioDTO(inicio=inicio, fim=fim),
        itens=_anotar_conflitos(itens, conflitos),
        conflitos=conflitos,
    )
