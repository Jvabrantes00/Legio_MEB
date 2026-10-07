import base64
import calendar
import hashlib
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML
from weasyprint.urls import URLFetcher

from core.models import PublicacaoCalendarioInstitucional

from . import calendario_institucional as calendario_services


ESCOPO_PUBLICO = 'PUBLICO'
ESCOPO_INTERNO = 'INTERNO'
PERIODO_MES = 'MES'
PERIODO_ANO = 'ANO'
LAYOUT_MENSAL = 'MENSAL'
LAYOUT_ANUAL_RESUMIDO = 'ANUAL_RESUMIDO'
SNAPSHOT_SCHEMA_VERSION = 2

LOGO_OFICIAL_PATH = Path(
    settings.BASE_DIR,
    'core',
    'static',
    'core',
    'branding',
    'logo-escalada.svg',
)

_MESES = (
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
)
_MESES_SLUG = (
    'janeiro', 'fevereiro', 'marco', 'abril', 'maio', 'junho',
    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro',
)
_DIAS_SEMANA = ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom')


class ExportacaoCalendarioError(Exception):
    pass


class LogoOficialIndisponivel(ExportacaoCalendarioError):
    pass


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
    layout: str
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
            'layout': self.layout,
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
                'renderer': 'WEASYPRINT_70',
            },
        }


def validar_modalidade(periodo, layout, mes):
    validas = {
        (PERIODO_MES, LAYOUT_MENSAL),
        (PERIODO_ANO, LAYOUT_MENSAL),
        (PERIODO_ANO, LAYOUT_ANUAL_RESUMIDO),
    }
    if (periodo, layout) not in validas:
        raise ValueError('Combinação de período e layout inválida.')
    if periodo == PERIODO_MES and (mes is None or not 1 <= mes <= 12):
        raise ValueError('O período MES exige mês entre 1 e 12.')
    if periodo == PERIODO_ANO and mes is not None:
        raise ValueError('O período ANO não aceita mês.')


def _intervalo(periodo, layout, ano, mes):
    validar_modalidade(periodo, layout, mes)
    if periodo == PERIODO_MES:
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        return date(ano, mes, 1), date(ano, mes, ultimo_dia)
    return date(ano, 1, 1), date(ano, 12, 31)


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
    layout,
    ano,
    mes,
    itens,
    gerado_em=None,
):
    if escopo not in {ESCOPO_PUBLICO, ESCOPO_INTERNO}:
        raise ValueError('Escopo de exportação inválido.')
    inicio, fim = _intervalo(periodo, layout, ano, mes)
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
        layout=layout,
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


def capturar_snapshot(
    *,
    escopo,
    periodo,
    layout,
    ano,
    mes=None,
    gerado_em=None,
):
    inicio, fim = _intervalo(periodo, layout, ano, mes)
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
        layout=layout,
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
        'titulo_periodo': f'{_MESES[mes - 1]} {snapshot.ano}',
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


def carregar_logo_oficial(*, obrigatoria=False):
    if not LOGO_OFICIAL_PATH.is_file():
        if obrigatoria:
            raise LogoOficialIndisponivel(
                f'Asset oficial da logo ausente em {LOGO_OFICIAL_PATH}.'
            )
        return None
    conteudo = LOGO_OFICIAL_PATH.read_bytes()
    if b'<svg' not in conteudo[:500].lower():
        raise LogoOficialIndisponivel(
            f'O asset oficial em {LOGO_OFICIAL_PATH} não é um SVG válido.'
        )
    codificado = base64.b64encode(conteudo).decode('ascii')
    return f'data:image/svg+xml;base64,{codificado}'


def contexto_pdf(
    snapshot,
    *,
    preview,
    publicado_em=None,
    logo_data_uri=None,
):
    meses = (
        [_mes_template(snapshot, snapshot.mes)]
        if snapshot.periodo == PERIODO_MES
        else [_mes_template(snapshot, mes) for mes in range(1, 13)]
    )
    return {
        'snapshot': snapshot,
        'titulo_periodo': (
            f'{_MESES[snapshot.mes - 1]} {snapshot.ano}'
            if snapshot.periodo == PERIODO_MES
            else str(snapshot.ano)
        ),
        'dias_semana': _DIAS_SEMANA,
        'meses': meses,
        'interno': snapshot.escopo == ESCOPO_INTERNO,
        'preview': preview,
        'publicado_em': publicado_em,
        'logo_data_uri': logo_data_uri,
    }


def _html_pdf(snapshot, *, preview, publicado_em, logo_data_uri):
    return render_to_string(
        'core/calendario_institucional_pdf.html',
        contexto_pdf(
            snapshot,
            preview=preview,
            publicado_em=publicado_em,
            logo_data_uri=logo_data_uri,
        ),
    )


def renderizar_html(
    snapshot,
    *,
    preview=True,
    publicado_em=None,
    logo_obrigatoria=False,
):
    logo_data_uri = carregar_logo_oficial(obrigatoria=logo_obrigatoria)
    return _html_pdf(
        snapshot,
        preview=preview,
        publicado_em=publicado_em,
        logo_data_uri=logo_data_uri,
    )


class _LogoFetcher(URLFetcher):
    def __init__(self, logo_data_uri):
        super().__init__(
            allowed_protocols={'data'},
            allow_redirects=False,
            fail_on_errors=True,
        )
        self.logo_data_uri = logo_data_uri

    def __call__(self, url):
        if self.logo_data_uri and url == self.logo_data_uri:
            return super().__call__(url)
        raise ValueError(f'Recurso externo não permitido no PDF: {url}')


def renderizar_documento(
    snapshot,
    *,
    preview=True,
    publicado_em=None,
    logo_obrigatoria=False,
):
    logo_data_uri = carregar_logo_oficial(obrigatoria=logo_obrigatoria)
    html = _html_pdf(
        snapshot,
        preview=preview,
        publicado_em=publicado_em,
        logo_data_uri=logo_data_uri,
    )
    return HTML(
        string=html,
        url_fetcher=_LogoFetcher(logo_data_uri),
    ).render()


def renderizar_pdf(
    snapshot,
    *,
    preview=True,
    publicado_em=None,
    logo_obrigatoria=False,
):
    return renderizar_documento(
        snapshot,
        preview=preview,
        publicado_em=publicado_em,
        logo_obrigatoria=logo_obrigatoria,
    ).write_pdf()


def sha256_pdf(conteudo):
    return hashlib.sha256(conteudo).hexdigest()


def nome_arquivo(snapshot):
    prefixo = f'calendario-{snapshot.escopo.lower()}'
    if snapshot.periodo == PERIODO_MES:
        return f'{prefixo}-{_MESES_SLUG[snapshot.mes - 1]}-{snapshot.ano}.pdf'
    if snapshot.layout == LAYOUT_MENSAL:
        return f'{prefixo}-{snapshot.ano}-mensal.pdf'
    return f'{prefixo}-{snapshot.ano}-resumido.pdf'


def nome_arquivo_publicacao(publicacao):
    prefixo = f'calendario-{publicacao.escopo.lower()}'
    if publicacao.periodo == PublicacaoCalendarioInstitucional.Periodo.MES:
        return (
            f'{prefixo}-{_MESES_SLUG[publicacao.mes - 1]}-'
            f'{publicacao.ano}.pdf'
        )
    if publicacao.layout == PublicacaoCalendarioInstitucional.Layout.MENSAL:
        return f'{prefixo}-{publicacao.ano}-mensal.pdf'
    return f'{prefixo}-{publicacao.ano}-resumido.pdf'


def _periodo_model(periodo):
    return {
        PERIODO_MES: PublicacaoCalendarioInstitucional.Periodo.MES,
        PERIODO_ANO: PublicacaoCalendarioInstitucional.Periodo.ANO,
    }[periodo]


def _layout_model(layout):
    return {
        LAYOUT_MENSAL: PublicacaoCalendarioInstitucional.Layout.MENSAL,
        LAYOUT_ANUAL_RESUMIDO: (
            PublicacaoCalendarioInstitucional.Layout.ANUAL_RESUMIDO
        ),
    }[layout]


def publicar_calendario(
    *,
    escopo,
    periodo,
    layout,
    ano,
    mes,
    autor,
):
    publicado_em = timezone.now()
    snapshot = capturar_snapshot(
        escopo=escopo,
        periodo=periodo,
        layout=layout,
        ano=ano,
        mes=mes,
        gerado_em=publicado_em,
    )
    conteudo = renderizar_pdf(
        snapshot,
        preview=False,
        publicado_em=publicado_em,
        logo_obrigatoria=True,
    )
    publicacao = PublicacaoCalendarioInstitucional(
        escopo=escopo,
        periodo=_periodo_model(periodo),
        layout=_layout_model(layout),
        ano=ano,
        mes=mes,
        publicado_em=publicado_em,
        publicado_por=autor,
        snapshot_schema_version=SNAPSHOT_SCHEMA_VERSION,
        snapshot=snapshot.as_dict(),
        sha256=sha256_pdf(conteudo),
    )
    arquivo_salvo = None
    try:
        with transaction.atomic():
            publicacao.arquivo_pdf.save(
                nome_arquivo(snapshot),
                ContentFile(conteudo),
                save=False,
            )
            arquivo_salvo = publicacao.arquivo_pdf.name
            publicacao.save(force_insert=True)
    except Exception:
        if arquivo_salvo:
            publicacao.arquivo_pdf.storage.delete(arquivo_salvo)
        raise
    return publicacao
