from dataclasses import dataclass
from datetime import date, datetime, time

from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML

from core.models import (
    AtendimentoPreEncontro,
    ConferenciaCuidadoPreEncontro,
    DadosCuidadoInscricao,
    PagamentoPreEncontro,
)

from . import pre_encontro as pre_encontro_services


ORIGENS = {
    'inscricao': 'Inscrição',
    'pessoa': 'Pessoa existente',
    'avulso': 'Avulso',
}
APTIDOES = {
    pre_encontro_services.SituacaoAptidaoPreEncontro.APTO: 'Apto',
    pre_encontro_services.SituacaoAptidaoPreEncontro.NAO_APTO: 'Não apto',
    pre_encontro_services.SituacaoAptidaoPreEncontro.AGUARDANDO_DECISAO_DIRETORIA: (
        'Aguardando decisão da Diretoria'
    ),
}


@dataclass(frozen=True)
class CabecalhoPreEncontro:
    encontro: str
    data: date
    horario: time
    local: str
    gerado_em: datetime


@dataclass(frozen=True)
class LinhaOperacionalPreEncontro:
    nome: str
    telefone: str
    origem: str
    presenca: str
    pagamento: str
    vaga: str
    aptidao: str


@dataclass(frozen=True)
class ProjecaoOperacionalPreEncontro:
    cabecalho: CabecalhoPreEncontro
    linhas: tuple[LinhaOperacionalPreEncontro, ...]
    quantidade_linhas_extras: int = 10


@dataclass(frozen=True)
class CampoCuidadoPreEncontro:
    rotulo: str
    valor: str


@dataclass(frozen=True)
class LinhaCuidadoPreEncontro:
    nome: str
    campos: tuple[CampoCuidadoPreEncontro, ...]
    conferencia: str


@dataclass(frozen=True)
class ProjecaoCuidadosPreEncontro:
    cabecalho: CabecalhoPreEncontro
    linhas: tuple[LinhaCuidadoPreEncontro, ...]


def _queryset_atendimentos(pre_encontro):
    return (
        AtendimentoPreEncontro.objects
        .filter(pre_encontro=pre_encontro)
        .select_related(
            'pessoa',
            'inscricao',
            'inscricao__pessoa',
            'inscricao__dados_declarados',
            'inscricao__dados_cuidado',
            'pagamento',
            'decisao_vaga',
            'conferencia_cuidado',
            'conferencia_cuidado__dados_cuidado',
        )
        .prefetch_related('pessoa__telefones', 'inscricao__pessoa__telefones')
    )


def _cabecalho(pre_encontro, *, momento=None):
    return CabecalhoPreEncontro(
        encontro=pre_encontro.encontro.encontro,
        data=pre_encontro.data,
        horario=pre_encontro.horario,
        local=pre_encontro.local,
        gerado_em=momento or timezone.now(),
    )


def nome_canonico_atendimento(atendimento):
    if atendimento.pessoa_id:
        return atendimento.pessoa.nome
    if atendimento.inscricao_id:
        try:
            return atendimento.inscricao.dados_declarados.nome_completo
        except AttributeError:
            if atendimento.inscricao.pessoa_id:
                return atendimento.inscricao.pessoa.nome
    return atendimento.nome_informado


def _origem(atendimento):
    if atendimento.inscricao_id:
        return ORIGENS['inscricao']
    if atendimento.pessoa_id:
        return ORIGENS['pessoa']
    return ORIGENS['avulso']


def _telefone_pessoa(pessoa):
    if pessoa is None:
        return ''
    telefones = list(pessoa.telefones.all())
    return next(
        (telefone.numero for telefone in telefones if telefone.whatsapp),
        telefones[0].numero if telefones else '',
    )


def telefone_canonico_atendimento(atendimento):
    if atendimento.inscricao_id:
        try:
            telefone = atendimento.inscricao.dados_declarados.telefone_whatsapp
        except AttributeError:
            telefone = ''
        if telefone:
            return telefone
    pessoa = atendimento.pessoa
    if pessoa is None and atendimento.inscricao_id:
        pessoa = atendimento.inscricao.pessoa
    return _telefone_pessoa(pessoa) or atendimento.telefone_informado


def _pagamento(atendimento):
    try:
        return atendimento.pagamento.get_status_display()
    except PagamentoPreEncontro.DoesNotExist:
        return PagamentoPreEncontro.Status.PENDENTE.label


def _vaga(atendimento):
    try:
        return atendimento.decisao_vaga.get_status_display()
    except AttributeError:
        return 'Sem decisão específica'


def projetar_operacional(pre_encontro, *, momento=None):
    linhas = []
    for atendimento in _queryset_atendimentos(pre_encontro):
        aptidao = pre_encontro_services.avaliar_aptidao_pre_encontro(
            atendimento,
        )
        linhas.append(LinhaOperacionalPreEncontro(
            nome=nome_canonico_atendimento(atendimento),
            telefone=telefone_canonico_atendimento(atendimento),
            origem=_origem(atendimento),
            presenca='Presente',
            pagamento=_pagamento(atendimento),
            vaga=_vaga(atendimento),
            aptidao=APTIDOES[aptidao.situacao],
        ))
    linhas.sort(key=lambda item: (item.nome.casefold(), item.telefone))
    return ProjecaoOperacionalPreEncontro(
        cabecalho=_cabecalho(pre_encontro, momento=momento),
        linhas=tuple(linhas),
    )


_CAMPOS_TEXTO_CUIDADO = (
    ('alergias', 'Alergias'),
    ('restricoes_intolerancias', 'Restrições e intolerâncias'),
    ('medicamentos', 'Medicamentos'),
    ('horarios_medicamentos', 'Horários dos medicamentos'),
    ('observacoes_medicamentos', 'Observações dos medicamentos'),
    ('neurodivergencia_condicao', 'Neurodivergência/condição informada'),
    ('necessidades_apoio', 'Necessidades de apoio'),
    ('sensibilidades_desconfortos', 'Sensibilidades e desconfortos'),
    ('o_que_ajuda', 'O que ajuda'),
    ('outras_informacoes', 'Outras informações'),
    ('observacoes', 'Observações'),
)


def _cuidado_relevante(dados):
    respostas_positivas = (
        dados.possui_alergias == DadosCuidadoInscricao.RespostaBinaria.SIM
        or dados.possui_restricoes_intolerancias
        == DadosCuidadoInscricao.RespostaBinaria.SIM
        or dados.usa_medicamentos == DadosCuidadoInscricao.RespostaBinaria.SIM
        or dados.neurodivergencia_apoio
        in (
            DadosCuidadoInscricao.RespostaApoio.SIM,
            DadosCuidadoInscricao.RespostaApoio.PREFERE_NAO_INFORMAR,
        )
    )
    return respostas_positivas or any(
        str(getattr(dados, campo, '')).strip()
        for campo, _ in _CAMPOS_TEXTO_CUIDADO
    )


def _campos_cuidado(dados):
    campos = []
    for campo, rotulo in (
        ('possui_alergias', 'Possui alergias'),
        ('possui_restricoes_intolerancias', 'Possui restrições/intolerâncias'),
        ('usa_medicamentos', 'Usa medicamentos'),
        ('neurodivergencia_apoio', 'Neurodivergência/apoio'),
    ):
        valor = getattr(dados, campo)
        if valor:
            campos.append(CampoCuidadoPreEncontro(
                rotulo=rotulo,
                valor=getattr(dados, f'get_{campo}_display')(),
            ))
    campos.extend(
        CampoCuidadoPreEncontro(rotulo=rotulo, valor=valor.strip())
        for campo, rotulo in _CAMPOS_TEXTO_CUIDADO
        if (valor := str(getattr(dados, campo, '')).strip())
    )
    return tuple(campos)


def _estado_conferencia(atendimento, dados):
    try:
        conferencia = atendimento.conferencia_cuidado
    except ConferenciaCuidadoPreEncontro.DoesNotExist:
        return 'Não conferido'
    if (
        conferencia.dados_cuidado_id == dados.pk
        and conferencia.dados_cuidado_atualizado_em == dados.atualizado_em
    ):
        return 'Conferido'
    return 'Atualizado após conferência'


def projetar_cuidados(pre_encontro, *, momento=None):
    linhas = []
    for atendimento in _queryset_atendimentos(pre_encontro):
        if not atendimento.inscricao_id:
            continue
        try:
            dados = atendimento.inscricao.dados_cuidado
        except DadosCuidadoInscricao.DoesNotExist:
            continue
        if not _cuidado_relevante(dados):
            continue
        linhas.append(LinhaCuidadoPreEncontro(
            nome=nome_canonico_atendimento(atendimento),
            campos=_campos_cuidado(dados),
            conferencia=_estado_conferencia(atendimento, dados),
        ))
    linhas.sort(key=lambda item: item.nome.casefold())
    return ProjecaoCuidadosPreEncontro(
        cabecalho=_cabecalho(pre_encontro, momento=momento),
        linhas=tuple(linhas),
    )


def renderizar_html_operacional(projecao):
    return render_to_string(
        'core/pre_encontro_operacional_pdf.html',
        {'projecao': projecao, 'linhas_extras': range(10)},
    )


def renderizar_html_cuidados(projecao):
    return render_to_string(
        'core/pre_encontro_cuidados_pdf.html',
        {'projecao': projecao},
    )


def renderizar_pdf_operacional(projecao):
    return HTML(string=renderizar_html_operacional(projecao)).write_pdf()


def renderizar_pdf_cuidados(projecao):
    return HTML(string=renderizar_html_cuidados(projecao)).write_pdf()


def gerar_pdf_operacional_pre_encontro(pre_encontro):
    return renderizar_pdf_operacional(projetar_operacional(pre_encontro))


def gerar_pdf_cuidados_pre_encontro(pre_encontro):
    return renderizar_pdf_cuidados(projetar_cuidados(pre_encontro))
