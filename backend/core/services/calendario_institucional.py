from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date

from core.models import DiaEncontro, Encontro


CATEGORIA_ENCONTRO = 'ENCONTRO'
ORIGEM_CANONICA = 'CANONICA'
ORIGEM_LEGADO = 'LEGADO'
CONFIRMACAO_PROVISORIA = 'PROVISORIA'
CONFIRMACAO_OFICIAL = 'OFICIAL'
CONFIRMACAO_INDETERMINADA = 'INDETERMINADA'
MAXIMO_DIAS_INTERVALO = 366


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


def _itens_canonicos(inicio, fim):
    dias = (
        DiaEncontro.objects.filter(
            data__gte=inicio,
            data__lte=fim,
            calendario__vigente=True,
        )
        .select_related('calendario__encontro')
        .order_by(
            'data',
            'ordem',
            'calendario__encontro__encontro',
            'calendario__encontro_id',
            'id',
        )
    )
    agrupados = {}
    for dia in dias:
        calendario = dia.calendario
        encontro = calendario.encontro
        item = agrupados.get(encontro.pk)
        dia_dto = DiaCalendarioDTO(
            id=dia.pk,
            data=dia.data,
            ordem=dia.ordem,
        )
        if item is None:
            agrupados[encontro.pk] = ItemCalendarioEncontroDTO(
                categoria=CATEGORIA_ENCONTRO,
                encontro_id=encontro.pk,
                titulo=encontro.encontro,
                tipo=encontro.tipo,
                status=encontro.status,
                calendario_id=calendario.pk,
                calendario_versao=calendario.versao,
                origem_agenda=ORIGEM_CANONICA,
                confirmacao=(
                    CONFIRMACAO_OFICIAL
                    if calendario.oficializado_em is not None
                    else CONFIRMACAO_PROVISORIA
                ),
                dias=(dia_dto,),
            )
        else:
            agrupados[encontro.pk] = replace(
                item,
                dias=(*item.dias, dia_dto),
            )
    return list(agrupados.values())


def _itens_legados(inicio, fim):
    encontros = (
        Encontro.objects.filter(
            calendarios__isnull=True,
            data_referencia__gte=inicio,
            data_referencia__lte=fim,
        )
        .order_by('data_referencia', 'encontro', 'id')
    )
    return [
        ItemCalendarioEncontroDTO(
            categoria=CATEGORIA_ENCONTRO,
            encontro_id=encontro.pk,
            titulo=encontro.encontro,
            tipo=encontro.tipo,
            status=encontro.status,
            calendario_id=None,
            calendario_versao=None,
            origem_agenda=ORIGEM_LEGADO,
            confirmacao=CONFIRMACAO_INDETERMINADA,
            dias=(
                DiaCalendarioDTO(
                    id=None,
                    data=encontro.data_referencia,
                    ordem=1,
                ),
            ),
        )
        for encontro in encontros
    ]


def _detectar_conflitos(itens):
    encontros_por_data = defaultdict(set)
    for item in itens:
        for dia in item.dias:
            encontros_por_data[dia.data].add(item.encontro_id)

    return tuple(
        ConflitoCalendarioDTO(
            data=data,
            encontro_ids=tuple(sorted(encontro_ids)),
            quantidade=len(encontro_ids),
        )
        for data, encontro_ids in sorted(encontros_por_data.items())
        if len(encontro_ids) > 1
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
        )
        for item in itens
    )


def consultar_calendario_institucional(inicio, fim):
    """Project current Encounter schedules for an inclusive date range."""
    _validar_periodo(inicio, fim)
    itens = [*_itens_canonicos(inicio, fim), *_itens_legados(inicio, fim)]
    itens.sort(
        key=lambda item: (
            item.dias[0].data,
            item.dias[0].ordem,
            item.titulo.casefold(),
            item.encontro_id,
            item.dias[0].id or 0,
        )
    )
    conflitos = _detectar_conflitos(itens)
    return ConsultaCalendarioInstitucionalDTO(
        periodo=PeriodoCalendarioDTO(inicio=inicio, fim=fim),
        itens=_anotar_conflitos(itens, conflitos),
        conflitos=conflitos,
    )
