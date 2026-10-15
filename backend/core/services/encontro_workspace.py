from collections import Counter
from dataclasses import dataclass
from enum import StrEnum

from django.db.models import Count, Sum
from django.utils import timezone

from core.models import (
    AtendimentoPreEncontro,
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    EquipeEncontro,
    InscricaoEncontro,
    RoleEquipeEncontro,
    SessaoFormativa,
    TrabalhoEncontro,
)
from core.permissions import (
    pode_acessar_agenda_workspace,
    pode_acessar_equipes_workspace,
    pode_acessar_formacao_workspace,
    pode_consultar_contato_workspace,
    pode_consultar_configuracao_encontristas,
    pode_consultar_encontristas_workspace,
    pode_consultar_operacao_pre_encontro,
    pode_consultar_resumo_workspace_encontro,
    pode_gerir_configuracao_encontristas,
)
from core.services import pre_encontro as pre_encontro_services
from core.services.exportacao_pre_encontro import (
    nome_canonico_atendimento,
    telefone_canonico_atendimento,
)


class OrigemCandidatoWorkspace(StrEnum):
    INSCRICAO = 'INSCRICAO'
    PESSOA = 'PESSOA'
    AVULSO = 'AVULSO'


ORIGEM_LABELS = {
    OrigemCandidatoWorkspace.INSCRICAO: 'Inscrição',
    OrigemCandidatoWorkspace.PESSOA: 'Pessoa existente',
    OrigemCandidatoWorkspace.AVULSO: 'Avulso',
}


class SituacaoCandidatoWorkspace(StrEnum):
    INSCRITO = 'INSCRITO'
    CANCELADO = 'CANCELADO'
    AGUARDANDO_DECISAO = 'AGUARDANDO_DECISAO'
    APTO = 'APTO'
    NAO_APTO = 'NAO_APTO'
    CONFIRMADO = 'CONFIRMADO'


SITUACAO_LABELS = {
    SituacaoCandidatoWorkspace.INSCRITO: 'Inscrito',
    SituacaoCandidatoWorkspace.CANCELADO: 'Cancelado',
    SituacaoCandidatoWorkspace.AGUARDANDO_DECISAO: 'Aguardando decisão',
    SituacaoCandidatoWorkspace.APTO: 'Apto',
    SituacaoCandidatoWorkspace.NAO_APTO: 'Não apto',
    SituacaoCandidatoWorkspace.CONFIRMADO: 'Confirmado',
}


@dataclass(frozen=True)
class CandidatoWorkspace:
    inscricao: InscricaoEncontro | None
    atendimento: AtendimentoPreEncontro | None
    aptidao: pre_encontro_services.AptidaoPreEncontro | None
    confirmado: bool


def projetar_capabilities(*, usuario, encontro):
    return {
        'consultar_resumo': pode_consultar_resumo_workspace_encontro(
            usuario, encontro,
        ),
        'consultar_encontristas': pode_consultar_encontristas_workspace(
            usuario, encontro,
        ),
        'consultar_contato': pode_consultar_contato_workspace(
            usuario, encontro,
        ),
        'acessar_pre_encontro': pode_consultar_operacao_pre_encontro(
            usuario, encontro,
        ),
        'acessar_equipes': pode_acessar_equipes_workspace(usuario, encontro),
        'acessar_formacao': pode_acessar_formacao_workspace(usuario, encontro),
        'acessar_agenda': pode_acessar_agenda_workspace(usuario, encontro),
        'consultar_inscricoes': pode_consultar_configuracao_encontristas(
            usuario,
        ),
        'configurar_inscricoes': pode_gerir_configuracao_encontristas(
            usuario,
        ),
    }


def _queryset_inscricoes(
    encontro,
    *,
    incluir_contato,
    incluir_identificacao,
):
    queryset = (
        InscricaoEncontro.objects
        .filter(encontro=encontro)
        .order_by('enviada_em', 'pk')
    )
    if incluir_identificacao:
        queryset = queryset.select_related('pessoa', 'dados_declarados')
    if incluir_contato:
        queryset = queryset.prefetch_related('pessoa__telefones')
    return queryset


def _queryset_atendimentos(
    encontro,
    *,
    incluir_contato,
    incluir_identificacao,
):
    queryset = (
        AtendimentoPreEncontro.objects
        .filter(pre_encontro__encontro=encontro)
        .select_related(
            'pre_encontro',
            'pre_encontro__encontro',
            'inscricao',
            'decisao_vaga',
        )
        .order_by('registrado_em', 'pk')
    )
    if incluir_identificacao:
        queryset = queryset.select_related(
            'inscricao__pessoa',
            'inscricao__dados_declarados',
            'pessoa',
        )
    if incluir_contato:
        queryset = queryset.prefetch_related(
            'pessoa__telefones',
            'inscricao__pessoa__telefones',
        )
    return queryset


def _pessoa_id(candidato):
    if candidato.atendimento is not None:
        return (
            candidato.atendimento.pessoa_id
            or (
                candidato.atendimento.inscricao.pessoa_id
                if candidato.atendimento.inscricao_id else None
            )
        )
    return candidato.inscricao.pessoa_id


def _carregar_candidatos(
    encontro,
    *,
    incluir_contato=False,
    incluir_identificacao=True,
):
    inscricoes = list(_queryset_inscricoes(
        encontro,
        incluir_contato=incluir_contato,
        incluir_identificacao=incluir_identificacao,
    ))
    atendimentos = list(_queryset_atendimentos(
        encontro,
        incluir_contato=incluir_contato,
        incluir_identificacao=incluir_identificacao,
    ))
    aptidoes = pre_encontro_services.avaliar_aptidoes_pre_encontro(atendimentos)
    confirmados = set(
        ConviteEncontro.objects.filter(
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        ).values_list('pessoa_id', flat=True)
    )
    atendimento_por_inscricao = {
        item.inscricao_id: item
        for item in atendimentos
        if item.inscricao_id is not None
    }
    candidatos = []
    for inscricao in inscricoes:
        atendimento = atendimento_por_inscricao.get(inscricao.pk)
        pessoa_id = (
            atendimento.pessoa_id if atendimento is not None else None
        ) or inscricao.pessoa_id
        candidatos.append(CandidatoWorkspace(
            inscricao=inscricao,
            atendimento=atendimento,
            aptidao=aptidoes.get(atendimento.pk) if atendimento else None,
            confirmado=bool(pessoa_id and pessoa_id in confirmados),
        ))
    candidatos.extend(
        CandidatoWorkspace(
            inscricao=None,
            atendimento=atendimento,
            aptidao=aptidoes[atendimento.pk],
            confirmado=bool(
                _pessoa_id(CandidatoWorkspace(None, atendimento, None, False))
                in confirmados
            ),
        )
        for atendimento in atendimentos
        if atendimento.inscricao_id is None
    )
    return candidatos


def situacao_candidato(candidato):
    if (
        candidato.inscricao is not None
        and candidato.inscricao.status == InscricaoEncontro.Status.CANCELADA
    ):
        return SituacaoCandidatoWorkspace.CANCELADO
    if candidato.confirmado:
        return SituacaoCandidatoWorkspace.CONFIRMADO
    if candidato.atendimento is None:
        return SituacaoCandidatoWorkspace.INSCRITO
    if (
        candidato.aptidao.situacao
        == pre_encontro_services.SituacaoAptidaoPreEncontro.APTO
    ):
        return SituacaoCandidatoWorkspace.APTO
    if (
        candidato.aptidao.situacao
        == pre_encontro_services.SituacaoAptidaoPreEncontro.AGUARDANDO_DECISAO_DIRETORIA
    ):
        return SituacaoCandidatoWorkspace.AGUARDANDO_DECISAO
    return SituacaoCandidatoWorkspace.NAO_APTO


def _origem(candidato):
    if candidato.inscricao is not None:
        return OrigemCandidatoWorkspace.INSCRICAO
    if candidato.atendimento.pessoa_id is not None:
        return OrigemCandidatoWorkspace.PESSOA
    return OrigemCandidatoWorkspace.AVULSO


def _nome(candidato):
    if candidato.atendimento is not None:
        return nome_canonico_atendimento(candidato.atendimento)
    try:
        return candidato.inscricao.dados_declarados.nome_completo
    except AttributeError:
        return candidato.inscricao.pessoa.nome if candidato.inscricao.pessoa else ''


def _telefone(candidato):
    if candidato.atendimento is not None:
        return telefone_canonico_atendimento(candidato.atendimento)
    try:
        declarado = candidato.inscricao.dados_declarados.telefone_whatsapp
    except AttributeError:
        declarado = ''
    if declarado:
        return declarado
    pessoa = candidato.inscricao.pessoa
    if pessoa is None:
        return ''
    telefones = list(pessoa.telefones.all())
    return next(
        (item.numero for item in telefones if item.whatsapp),
        telefones[0].numero if telefones else '',
    )


def serializar_candidato(candidato, *, incluir_contato=False):
    origem = _origem(candidato)
    situacao = situacao_candidato(candidato)
    aptidao = candidato.aptidao.situacao.value if candidato.aptidao else None
    dados = {
        'ref': {
            'origem_tipo': origem.value,
            'origem_id': str(
                candidato.inscricao.identificador
                if candidato.inscricao is not None
                else candidato.atendimento.pk
            ),
        },
        'nome': _nome(candidato),
        'origem': {'codigo': origem.value, 'label': ORIGEM_LABELS[origem]},
        'situacao': {
            'codigo': situacao.value,
            'label': SITUACAO_LABELS[situacao],
        },
        'presenca_pre': candidato.atendimento is not None,
        'aptidao': aptidao,
        'pessoa_id': _pessoa_id(candidato),
    }
    if incluir_contato:
        dados['telefone'] = _telefone(candidato)
    return dados


def listar_encontristas(
    *,
    encontro,
    incluir_contato=False,
    search='',
    situacao='',
    origem='',
):
    candidatos = _carregar_candidatos(
        encontro,
        incluir_contato=incluir_contato,
    )
    if situacao:
        candidatos = [
            item for item in candidatos
            if situacao_candidato(item).value == situacao
        ]
    if origem:
        candidatos = [item for item in candidatos if _origem(item).value == origem]
    termo = search.strip().casefold()
    if termo:
        candidatos = [
            item for item in candidatos
            if termo in _nome(item).casefold()
            or (incluir_contato and termo in _telefone(item).casefold())
        ]
    candidatos.sort(key=lambda item: (
        _nome(item).casefold(),
        str(item.inscricao.pk if item.inscricao else item.atendimento.pk),
    ))
    return candidatos


def _resumo_agenda(encontro):
    calendario = (
        CalendarioEncontro.objects
        .filter(encontro=encontro, vigente=True)
        .prefetch_related('dias')
        .first()
    )
    datas = (
        [dia.data for dia in calendario.dias.all()]
        if calendario is not None else []
    )
    itens = list(datas)
    if calendario is not None and calendario.pre_encontro_data:
        itens.append(calendario.pre_encontro_data)
    itens.extend(encontro.reunioes_preparatorias.values_list('data', flat=True))
    try:
        itens.append(encontro.avaliacao_agenda.data)
    except AttributeError:
        pass
    itens.sort()
    hoje = timezone.localdate()
    proximo = next((item for item in itens if item >= hoje), None)
    return {
        'configurada': calendario is not None,
        'oficializada': bool(
            calendario is not None and calendario.oficializado_em is not None
        ),
        'quantidade_itens': len(itens),
        'proximo_item': proximo,
        'datas_principais': datas,
        'pre_encontro_data': (
            calendario.pre_encontro_data if calendario is not None else None
        ),
    }


def _resumo_equipes(encontro):
    equipes = EquipeEncontro.objects.filter(encontro=encontro).count()
    agregados = RoleEquipeEncontro.objects.filter(
        equipe_encontro__encontro=encontro,
    ).aggregate(
        funcoes=Count('id'),
        vagas=Sum('quantidade_estrutural'),
    )
    preenchidas = TrabalhoEncontro.objects.filter(
        encontro=encontro,
        role_equipe__isnull=False,
    ).exclude(status=TrabalhoEncontro.Status.RETIRADO).count()
    return {
        'quantidade_equipes': equipes,
        'quantidade_funcoes': agregados['funcoes'] or 0,
        'vagas_estruturais': agregados['vagas'],
        'vagas_preenchidas': preenchidas,
    }


def _resumo_formacao(encontro):
    por_status = dict(
        SessaoFormativa.objects.filter(encontro=encontro)
        .values_list('status')
        .annotate(total=Count('id'))
    )
    return {
        'total_sessoes': sum(por_status.values()),
        'planejadas': por_status.get(SessaoFormativa.Status.PLANEJADA, 0),
        'realizadas': por_status.get(SessaoFormativa.Status.REALIZADA, 0),
        'canceladas': por_status.get(SessaoFormativa.Status.CANCELADA, 0),
    }


def projetar_resumo(*, encontro):
    candidatos = _carregar_candidatos(
        encontro,
        incluir_identificacao=False,
    )
    contagens = Counter(situacao_candidato(item).value for item in candidatos)
    configuracao = ConfiguracaoEncontristasEncontro.objects.filter(
        encontro=encontro,
    ).first()
    pre = getattr(encontro, 'pre_encontro', None)
    agenda = _resumo_agenda(encontro)
    aguardando = contagens[SituacaoCandidatoWorkspace.AGUARDANDO_DECISAO.value]
    alertas = []
    if pre is None:
        alertas.append({'codigo': 'PRE_NAO_CONFIGURADO', 'mensagem': 'Pré-Encontro ainda não configurado.'})
    if configuracao is None:
        alertas.append({
            'codigo': 'INSCRICOES_NAO_CONFIGURADAS',
            'mensagem': 'Inscrições ainda não configuradas.',
        })
    if agenda['pre_encontro_data'] is None:
        alertas.append({'codigo': 'DATA_PRE_AUSENTE', 'mensagem': 'Data do Pré-Encontro ausente no Calendário.'})
    if aguardando:
        alertas.append({'codigo': 'CANDIDATOS_AGUARDANDO_DECISAO', 'mensagem': f'{aguardando} candidato(s) aguardando decisão.'})
    capacidade = configuracao.capacidade if configuracao else None
    aptos = contagens[SituacaoCandidatoWorkspace.APTO.value] + contagens[SituacaoCandidatoWorkspace.CONFIRMADO.value]
    if capacidade is not None and aptos > capacidade:
        alertas.append({'codigo': 'CAPACIDADE_EXCEDIDA', 'mensagem': 'Quantidade apta/confirmada excede a capacidade.'})
    return {
        'encontro': {
            'id': encontro.pk,
            'nome': encontro.encontro,
            'tipo': encontro.tipo,
            'local': encontro.local,
        },
        'lifecycle': encontro.status,
        'agenda': agenda,
        'encontristas': {
            'inscricoes_recebidas': InscricaoEncontro.objects.filter(encontro=encontro).count(),
            'total_funil': len(candidatos),
            'por_situacao': {
                item.value: contagens[item.value]
                for item in SituacaoCandidatoWorkspace
            },
        },
        'pre_encontro': {
            'configurado': pre is not None,
            'data': agenda['pre_encontro_data'],
            'capacidade': capacidade,
            'quantidade_checkins': sum(item.atendimento is not None for item in candidatos),
            'quantidade_aptos': aptos,
            'quantidade_aguardando_decisao': aguardando,
        },
        'equipes': _resumo_equipes(encontro),
        'formacao': _resumo_formacao(encontro),
        'alertas': alertas,
    }
