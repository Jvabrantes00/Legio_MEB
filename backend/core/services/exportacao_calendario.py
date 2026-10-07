import calendar
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime

from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from . import calendario_institucional as calendario_services


ESCOPO_PUBLICO = 'PUBLICO'
ESCOPO_INTERNO = 'INTERNO'
PERIODO_MENSAL = 'MENSAL'
PERIODO_ANUAL = 'ANUAL'
MODELO_ANUAL_A = 'A'
MODELO_ANUAL_B = 'B'
SNAPSHOT_SCHEMA_VERSION = 1

_MESES = (
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
)
_DIAS_SEMANA = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom')


@dataclass(frozen=True)
class ItemExportacaoCalendario:
    id: str
    origem: str
    origem_id: int | None
    data: date
    encontro_id: int
    encontro_titulo: str
    encontro_tipo: str
    encontro_status: str
    rotulo: str | None
    complemento: str | None
    categoria: str
    provisorio: bool
    publicavel_externamente: bool
    conflito: bool

    def as_dict(self):
        return {
            'id': self.id,
            'origem': self.origem,
            'origem_id': self.origem_id,
            'data': self.data.isoformat(),
            'encontro_id': self.encontro_id,
            'encontro_titulo': self.encontro_titulo,
            'encontro_tipo': self.encontro_tipo,
            'encontro_status': self.encontro_status,
            'rotulo': self.rotulo,
            'complemento': self.complemento,
            'categoria': self.categoria,
            'provisorio': self.provisorio,
            'publicavel_externamente': self.publicavel_externamente,
            'conflito': self.conflito,
        }


@dataclass(frozen=True)
class SnapshotCalendario:
    schema_version: int
    escopo: str
    periodo: str
    ano: int
    mes: int | None
    gerado_em: datetime
    inicio: date
    fim: date
    itens: tuple[ItemExportacaoCalendario, ...]

    def as_dict(self):
        return {
            'schema_version': self.schema_version,
            'escopo': self.escopo,
            'periodo': self.periodo,
            'ano': self.ano,
            'mes': self.mes,
            'gerado_em': self.gerado_em.isoformat(),
            'inicio': self.inicio.isoformat(),
            'fim': self.fim.isoformat(),
            'dias': sorted({item.data.isoformat() for item in self.itens}),
            'itens': [item.as_dict() for item in self.itens],
            'metadados': {
                'fonte': 'CALENDARIO_INSTITUCIONAL',
                'legenda_provisoriedade': '* Data ainda sujeita a confirmação.',
            },
        }


def _intervalo(periodo, ano, mes):
    if periodo == PERIODO_MENSAL:
        if mes is None or not 1 <= mes <= 12:
            raise ValueError('O período mensal exige mês entre 1 e 12.')
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        return date(ano, mes, 1), date(ano, mes, ultimo_dia)
    if periodo == PERIODO_ANUAL:
        if mes is not None:
            raise ValueError('O período anual não aceita mês.')
        return date(ano, 1, 1), date(ano, 12, 31)
    raise ValueError('Período de exportação inválido.')


def _titulo_preparatoria(titulo):
    return re.sub(r'^(\d+)ª Reunião$', r'\1ª Preparatória', titulo)


def _item_exportacao(item_calendario, item_agenda):
    if item_agenda.origem == calendario_services.TIPO_DIA_ENCONTRO:
        rotulo = item_agenda.titulo if item_agenda.subtitulo else None
        complemento = None
    else:
        rotulo = _titulo_preparatoria(item_agenda.titulo)
        complemento = item_agenda.subtitulo
    return ItemExportacaoCalendario(
        id=item_agenda.id,
        origem=item_agenda.origem,
        origem_id=item_agenda.origem_id,
        data=item_agenda.data,
        encontro_id=item_calendario.encontro_id,
        encontro_titulo=item_calendario.titulo,
        encontro_tipo=item_calendario.tipo,
        encontro_status=item_calendario.status,
        rotulo=rotulo,
        complemento=complemento,
        categoria=item_calendario.categoria,
        provisorio=(
            item_agenda.confirmacao
            == calendario_services.CONFIRMACAO_PROVISORIA
        ),
        publicavel_externamente=item_agenda.publicavel_externamente,
        conflito=item_agenda.conflito is not None,
    )


def montar_snapshot(
    *,
    escopo,
    periodo,
    ano,
    mes,
    itens,
    gerado_em=None,
):
    if escopo not in {ESCOPO_PUBLICO, ESCOPO_INTERNO}:
        raise ValueError('Escopo de exportação inválido.')
    inicio, fim = _intervalo(periodo, ano, mes)
    itens_filtrados = (
        item
        for item in itens
        if inicio <= item.data <= fim
        and (escopo == ESCOPO_INTERNO or item.publicavel_externamente)
    )
    return SnapshotCalendario(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        escopo=escopo,
        periodo=periodo,
        ano=ano,
        mes=mes,
        gerado_em=gerado_em or timezone.now(),
        inicio=inicio,
        fim=fim,
        itens=tuple(sorted(
            itens_filtrados,
            key=lambda item: (
                item.data,
                item.encontro_titulo.casefold(),
                item.origem,
                item.id,
            ),
        )),
    )


def capturar_snapshot(*, escopo, periodo, ano, mes=None, gerado_em=None):
    inicio, fim = _intervalo(periodo, ano, mes)
    consulta = calendario_services.consultar_calendario_institucional(
        inicio,
        fim,
    )
    itens = (
        _item_exportacao(item_calendario, item_agenda)
        for item_calendario in consulta.itens
        for item_agenda in item_calendario.agenda
    )
    return montar_snapshot(
        escopo=escopo,
        periodo=periodo,
        ano=ano,
        mes=mes,
        itens=itens,
        gerado_em=gerado_em,
    )


def _item_template(item):
    return {
        'titulo': f'{item.encontro_titulo}{" *" if item.provisorio else ""}',
        'rotulo': item.rotulo,
        'complemento': item.complemento,
        'conflito': item.conflito,
    }


def _mes_template(snapshot, mes):
    itens_por_dia = defaultdict(list)
    for item in snapshot.itens:
        if item.data.month == mes:
            itens_por_dia[item.data].append(_item_template(item))
    semanas = calendar.Calendar(firstweekday=0).monthdatescalendar(
        snapshot.ano,
        mes,
    )
    while len(semanas) < 6:
        proximo_inicio = semanas[-1][-1]
        semanas.append([
            date.fromordinal(proximo_inicio.toordinal() + deslocamento)
            for deslocamento in range(1, 8)
        ])
    return {
        'numero': mes,
        'nome': _MESES[mes - 1],
        'semanas': [
            [
                {
                    'data': data_dia,
                    'numero_dia': data_dia.day,
                    'mes_atual': data_dia.month == mes,
                    'itens': itens_por_dia.get(data_dia, ()),
                }
                for data_dia in semana
            ]
            for semana in semanas
        ],
        'agenda': [
            {
                'data': data_item,
                'dia': data_item.day,
                'itens': itens_por_dia[data_item],
            }
            for data_item in sorted(itens_por_dia)
        ],
        'quantidade': sum(len(itens) for itens in itens_por_dia.values()),
    }


def contexto_pdf(snapshot, *, modelo_anual=None):
    if snapshot.periodo == PERIODO_ANUAL and modelo_anual not in {
        MODELO_ANUAL_A,
        MODELO_ANUAL_B,
    }:
        raise ValueError('O PDF anual exige o Modelo A ou B.')
    meses = (
        [_mes_template(snapshot, snapshot.mes)]
        if snapshot.periodo == PERIODO_MENSAL
        else [_mes_template(snapshot, mes) for mes in range(1, 13)]
    )
    return {
        'snapshot': snapshot,
        'titulo_periodo': (
            f'{_MESES[snapshot.mes - 1]} {snapshot.ano}'
            if snapshot.periodo == PERIODO_MENSAL
            else str(snapshot.ano)
        ),
        'dias_semana': _DIAS_SEMANA,
        'meses': meses,
        'modelo_anual': modelo_anual,
        'interno': snapshot.escopo == ESCOPO_INTERNO,
        'logo_disponivel': False,
    }


def renderizar_html(snapshot, *, modelo_anual=None):
    return render_to_string(
        'core/calendario_institucional_pdf.html',
        contexto_pdf(snapshot, modelo_anual=modelo_anual),
    )


def _bloquear_recurso_externo(url, *args, **kwargs):
    del args, kwargs
    raise ValueError(f'Recurso externo não permitido no PDF: {url}')


def renderizar_documento(snapshot, *, modelo_anual=None):
    return HTML(
        string=renderizar_html(snapshot, modelo_anual=modelo_anual),
        url_fetcher=_bloquear_recurso_externo,
    ).render()


def renderizar_pdf(snapshot, *, modelo_anual=None):
    return renderizar_documento(
        snapshot,
        modelo_anual=modelo_anual,
    ).write_pdf()


def sha256_pdf(conteudo):
    return hashlib.sha256(conteudo).hexdigest()
