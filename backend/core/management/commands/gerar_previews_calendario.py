from datetime import UTC, date, datetime
from pathlib import Path

from django.core.management.base import BaseCommand

from core.services.exportacao_calendario import (
    ESCOPO_INTERNO,
    ESCOPO_PUBLICO,
    MODELO_ANUAL_A,
    MODELO_ANUAL_B,
    PERIODO_ANUAL,
    PERIODO_MENSAL,
    ItemExportacaoCalendario,
    montar_snapshot,
    renderizar_pdf,
)


def _item(
    identificador,
    data_item,
    encontro_id,
    encontro,
    rotulo,
    *,
    origem='DIA_ENCONTRO',
    complemento=None,
    provisorio=False,
    publicavel=True,
):
    return ItemExportacaoCalendario(
        id=identificador,
        origem=origem,
        origem_id=encontro_id,
        data=data_item,
        encontro_id=encontro_id,
        encontro_titulo=encontro,
        encontro_tipo='Escalada',
        encontro_status='em_agendamento' if provisorio else 'agendado',
        rotulo=rotulo,
        complemento=complemento,
        categoria='ENCONTRO',
        provisorio=provisorio,
        publicavel_externamente=publicavel,
        conflito=False,
    )


def dataset_controlado():
    return (
        _item('DIA:1', date(2027, 3, 7), 1, 'Escalada 2027', 'Pré-Escalada', provisorio=True),
        _item('DIA:2', date(2027, 3, 21), 1, 'Escalada 2027', 'Sexta-feira', provisorio=True),
        _item('DIA:3', date(2027, 3, 22), 1, 'Escalada 2027', 'Sábado', provisorio=True),
        _item('DIA:4', date(2027, 3, 23), 1, 'Escalada 2027', 'Domingo', provisorio=True),
        _item('DIA:5', date(2027, 3, 21), 2, 'AVC Nossa Senhora da Esperança e da Juventude', 'Encontro principal'),
        _item('DIA:6', date(2027, 3, 21), 3, 'ESPPA Regional', 'Formação comunitária com rótulo mais longo'),
        _item('REUNIAO:1', date(2027, 3, 3), 1, 'Escalada 2027', '1ª Preparatória', origem='REUNIAO_PREPARATORIA', publicavel=False),
        _item('REUNIAO:2', date(2027, 3, 10), 1, 'Escalada 2027', '2ª Preparatória', origem='REUNIAO_PREPARATORIA', publicavel=False),
        _item('REUNIAO:3', date(2027, 3, 17), 1, 'Escalada 2027', '3ª Preparatória', origem='REUNIAO_PREPARATORIA', complemento='Missa de Entrega', publicavel=False),
        _item('AVALIACAO:1', date(2027, 3, 30), 1, 'Escalada 2027', 'Avaliação', origem='AVALIACAO', publicavel=False),
        _item('DIA:7', date(2027, 6, 12), 4, 'Acampamento de Inverno', 'Primeiro dia'),
        _item('DIA:8', date(2027, 9, 18), 5, 'Escalada da Primavera', 'Sábado'),
        _item('DIA:9', date(2027, 11, 6), 6, 'AVC Jovem', 'Dia do Encontro', provisorio=True),
    )


class Command(BaseCommand):
    help = 'Gera previews controlados e não publicados do Calendário.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            default='/tmp/sia_calendar_pdf_previews',
        )

    def handle(self, *args, **options):
        output_dir = Path(options['output_dir']).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        gerado_em = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
        itens = dataset_controlado()
        mensal_publico = montar_snapshot(
            escopo=ESCOPO_PUBLICO,
            periodo=PERIODO_MENSAL,
            ano=2027,
            mes=3,
            itens=itens,
            gerado_em=gerado_em,
        )
        mensal_interno = montar_snapshot(
            escopo=ESCOPO_INTERNO,
            periodo=PERIODO_MENSAL,
            ano=2027,
            mes=3,
            itens=itens,
            gerado_em=gerado_em,
        )
        anual_publico = montar_snapshot(
            escopo=ESCOPO_PUBLICO,
            periodo=PERIODO_ANUAL,
            ano=2027,
            mes=None,
            itens=itens,
            gerado_em=gerado_em,
        )
        anual_interno = montar_snapshot(
            escopo=ESCOPO_INTERNO,
            periodo=PERIODO_ANUAL,
            ano=2027,
            mes=None,
            itens=itens,
            gerado_em=gerado_em,
        )
        artefatos = (
            ('mensal-publico.pdf', mensal_publico, None),
            ('mensal-interno.pdf', mensal_interno, None),
            ('anual-publico-modelo-a.pdf', anual_publico, MODELO_ANUAL_A),
            ('anual-publico-modelo-b.pdf', anual_publico, MODELO_ANUAL_B),
            ('anual-interno-modelo-a.pdf', anual_interno, MODELO_ANUAL_A),
            ('anual-interno-modelo-b.pdf', anual_interno, MODELO_ANUAL_B),
        )
        for nome, snapshot, modelo in artefatos:
            destino = output_dir / nome
            destino.write_bytes(renderizar_pdf(snapshot, modelo_anual=modelo))
            self.stdout.write(str(destino))
