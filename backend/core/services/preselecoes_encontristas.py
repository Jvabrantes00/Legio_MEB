from dataclasses import dataclass

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    AtendimentoPreEncontro,
    CampanhaConvitesEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    Encontro,
    InscricaoEncontro,
    ParticipacaoEncontro,
    Pessoa,
    PreSelecaoEncontrista,
)
from core.permissions import (
    pode_aprovar_encaminhamento_encontrista,
    pode_encerrar_preselecao_encontrista,
    pode_preselecionar_encontrista,
)
from core.services.auditoria_encontros import (
    registrar_evento_auditoria_encontro,
)
from core.services.elegibilidade_encontristas import (
    ResultadoElegibilidadeEncontrista,
    avaliar_elegibilidade_encontrista,
)
from core.services.participacoes import criar_convite


class ErroPreSelecaoEncontrista(ValidationError):
    pass


_ESTADOS_ABERTOS = (
    PreSelecaoEncontrista.Estado.PRESELECIONADA,
    PreSelecaoEncontrista.Estado.ENCAMINHADA,
)
_STATUS_ENCONTRO_ENCERRADOS = (
    Encontro.Status.CANCELADO,
    Encontro.Status.FINALIZADO,
)
_CAMPOS_AUDITORIA_CRIACAO = frozenset({
    'estado',
    'origem_tipo',
    'pessoa_resolvida',
})
_CAMPOS_AUDITORIA_ENCERRAMENTO = frozenset({'estado'})
_CAMPOS_AUDITORIA_ENCAMINHAMENTO = frozenset({
    'estado',
    'origem_tipo',
    'pessoa_resolvida',
    'convite_id',
    'convite_status',
    'convite_criado',
})


@dataclass(frozen=True)
class ResultadoEncaminhamentoEncontrista:
    preselecao: PreSelecaoEncontrista
    convite: ConviteEncontro
    convite_criado: bool
    confirmacao_preexistente: bool


def _erro(campo, mensagem):
    raise ErroPreSelecaoEncontrista({campo: [mensagem]})


def _pk(objeto, nome):
    if objeto is None or objeto.pk is None:
        _erro(nome, f'{nome.capitalize()} deve estar persistido.')
    return objeto.pk


def _encontro_bloqueado(encontro):
    encontro_id = _pk(encontro, 'encontro')
    try:
        return Encontro.objects.select_for_update().get(pk=encontro_id)
    except Encontro.DoesNotExist:
        _erro('encontro', 'Encontro não encontrado.')


def _exigir_lifecycle(encontro):
    if encontro.status in _STATUS_ENCONTRO_ENCERRADOS:
        _erro(
            'encontro',
            'O Encontro não aceita operações de pré-seleção.',
        )


def _exigir_permissao_preselecionar(usuario, encontro):
    if not pode_preselecionar_encontrista(usuario, encontro):
        raise PermissionDenied(
            'Seu usuário não pode pré-selecionar encontristas.'
        )


def _exigir_permissao_encerrar(usuario, encontro):
    if not pode_encerrar_preselecao_encontrista(usuario, encontro):
        raise PermissionDenied(
            'Seu usuário não pode encerrar pré-seleções de encontristas.'
        )


def _exigir_permissao_encaminhar(usuario, encontro):
    if not pode_aprovar_encaminhamento_encontrista(usuario, encontro):
        raise PermissionDenied(
            'Seu usuário não pode aprovar encaminhamentos de encontristas.'
        )


def _campanha_bloqueada(encontro):
    return (
        CampanhaConvitesEncontro.objects
        .select_for_update(of=('self',))
        .filter(encontro=encontro)
        .first()
    )


def _configuracao_bloqueada(encontro, *, obrigatoria=True):
    configuracao = (
        ConfiguracaoEncontristasEncontro.objects
        .select_for_update(of=('self',))
        .filter(encontro=encontro)
        .first()
    )
    if configuracao is None and obrigatoria:
        _erro(
            'configuracao',
            'O Encontro não possui configuração de encontristas.',
        )
    return configuracao


def _preselecao_bloqueada(preselecao, encontro):
    preselecao_id = _pk(preselecao, 'preselecao')
    try:
        bloqueada = (
            PreSelecaoEncontrista.objects
            .select_for_update(of=('self',))
            .get(pk=preselecao_id)
        )
    except PreSelecaoEncontrista.DoesNotExist:
        _erro('preselecao', 'Pré-seleção não encontrada.')
    if bloqueada.encontro_id != encontro.pk:
        _erro('preselecao', 'Pré-seleção não encontrada.')
    return bloqueada


def _pessoa_bloqueada(pessoa):
    if pessoa is None:
        _erro('identidade', 'A origem não possui Pessoa canônica resolvida.')
    try:
        return Pessoa.objects.select_for_update().get(pk=pessoa.pk)
    except (AttributeError, Pessoa.DoesNotExist):
        _erro('identidade', 'A Pessoa canônica não foi encontrada.')


def _inscricao_bloqueada(inscricao, encontro):
    inscricao_id = _pk(inscricao, 'inscricao')
    try:
        inscricao = (
            InscricaoEncontro.objects
            .select_for_update(of=('self',))
            .select_related('pessoa')
            .get(pk=inscricao_id)
        )
    except InscricaoEncontro.DoesNotExist:
        _erro('origem', 'Origem canônica não encontrada.')
    if inscricao.encontro_id != encontro.pk:
        _erro('origem', 'Origem canônica não pertence ao Encontro informado.')
    return inscricao


def _atendimento_bloqueado(atendimento, encontro):
    atendimento_id = _pk(atendimento, 'atendimento')
    try:
        atendimento = (
            AtendimentoPreEncontro.objects
            .select_for_update(of=('self',))
            .select_related('pre_encontro', 'pessoa', 'inscricao')
            .get(pk=atendimento_id)
        )
    except AtendimentoPreEncontro.DoesNotExist:
        _erro('origem', 'Origem canônica não encontrada.')
    if atendimento.pre_encontro.encontro_id != encontro.pk:
        _erro('origem', 'Origem canônica não pertence ao Encontro informado.')
    return atendimento


def _eh_atendimento_avulso(atendimento):
    return bool(
        atendimento.inscricao_id is None
        and atendimento.nome_informado
        and atendimento.data_nascimento_informada is not None
        and atendimento.telefone_informado
    )


def _resolver_origem(
    *,
    encontro,
    origem_tipo,
    inscricao,
    atendimento,
):
    if origem_tipo == PreSelecaoEncontrista.OrigemTipo.INSCRICAO:
        if atendimento is not None:
            _erro('origem', 'Informe somente a inscrição canônica.')
        inscricao = _inscricao_bloqueada(inscricao, encontro)
        return {
            'inscricao_origem': inscricao,
            'atendimento_origem': None,
            'pessoa_resolvida': inscricao.pessoa,
        }

    if origem_tipo not in (
        PreSelecaoEncontrista.OrigemTipo.PESSOA,
        PreSelecaoEncontrista.OrigemTipo.AVULSO,
    ):
        _erro('origem_tipo', 'Tipo de origem inválido.')
    if inscricao is not None:
        _erro('origem', 'Informe somente o atendimento canônico.')

    atendimento = _atendimento_bloqueado(atendimento, encontro)
    if atendimento.inscricao_id is not None:
        _erro(
            'origem',
            'Atendimento vinculado a inscrição deve usar a origem INSCRICAO.',
        )

    if origem_tipo == PreSelecaoEncontrista.OrigemTipo.PESSOA:
        if atendimento.pessoa_id is None:
            _erro('origem', 'O atendimento não possui Pessoa canônica resolvida.')
    elif not _eh_atendimento_avulso(atendimento):
        _erro('origem', 'O atendimento não possui origem avulsa verificável.')

    return {
        'inscricao_origem': None,
        'atendimento_origem': atendimento,
        'pessoa_resolvida': atendimento.pessoa,
    }


def _preselecoes_abertas(encontro):
    return PreSelecaoEncontrista.objects.select_for_update().filter(
        encontro=encontro,
        estado__in=_ESTADOS_ABERTOS,
    )


def _preselecao_exata(queryset, *, inscricao, atendimento):
    if inscricao is not None:
        return queryset.filter(inscricao_origem=inscricao).first()
    return queryset.filter(atendimento_origem=atendimento).first()


def _validar_identidade_existente(existente, pessoa_resolvida):
    if (
        existente is not None
        and existente.pessoa_resolvida_id is not None
        and pessoa_resolvida is not None
        and existente.pessoa_resolvida_id != pessoa_resolvida.pk
    ):
        _erro(
            'identidade',
            'A origem possui identidade conflitante com a pré-seleção aberta.',
        )


def _conflito_de_pessoa(queryset, *, pessoa_resolvida, excluir=None):
    if pessoa_resolvida is None:
        return False
    conflitos = queryset.filter(pessoa_resolvida=pessoa_resolvida)
    if excluir is not None:
        conflitos = conflitos.exclude(pk=excluir.pk)
    return conflitos.exists()


def _auditar_criacao(preselecao, usuario):
    registrar_evento_auditoria_encontro(
        encontro=preselecao.encontro,
        ator=usuario,
        fato='encontrista.preselecionado',
        entidade='preselecao_encontrista',
        objeto_id=preselecao.pk,
        valor_anterior={},
        valor_novo={
            'estado': preselecao.estado,
            'origem_tipo': preselecao.origem_tipo,
            'pessoa_resolvida': preselecao.pessoa_resolvida_id is not None,
        },
        campos_permitidos=_CAMPOS_AUDITORIA_CRIACAO,
    )


def _auditar_encerramento(preselecao, usuario, estado_anterior):
    registrar_evento_auditoria_encontro(
        encontro=preselecao.encontro,
        ator=usuario,
        fato='encontrista.preselecao_encerrada',
        entidade='preselecao_encontrista',
        objeto_id=preselecao.pk,
        valor_anterior={'estado': estado_anterior},
        valor_novo={'estado': preselecao.estado},
        campos_permitidos=_CAMPOS_AUDITORIA_ENCERRAMENTO,
    )


def _auditar_encaminhamento(preselecao, convite, usuario, *, convite_criado):
    registrar_evento_auditoria_encontro(
        encontro=preselecao.encontro,
        ator=usuario,
        fato='encontrista.encaminhamento_aprovado',
        entidade='preselecao_encontrista',
        objeto_id=preselecao.pk,
        valor_anterior={'estado': PreSelecaoEncontrista.Estado.PRESELECIONADA},
        valor_novo={
            'estado': preselecao.estado,
            'origem_tipo': preselecao.origem_tipo,
            'pessoa_resolvida': preselecao.pessoa_resolvida_id is not None,
            'convite_id': convite.pk,
            'convite_status': convite.status,
            'convite_criado': convite_criado,
        },
        campos_permitidos=_CAMPOS_AUDITORIA_ENCAMINHAMENTO,
    )


def _resolver_origem_preselecao(preselecao, encontro):
    if preselecao.origem_tipo == PreSelecaoEncontrista.OrigemTipo.INSCRICAO:
        inscricao = _inscricao_bloqueada(preselecao.inscricao_origem, encontro)
        if inscricao.status != InscricaoEncontro.Status.ENVIADA:
            _erro('origem', 'A inscrição de origem não está enviada.')
        pessoa = inscricao.pessoa
    else:
        atendimento = _atendimento_bloqueado(
            preselecao.atendimento_origem,
            encontro,
        )
        if atendimento.inscricao_id is not None:
            _erro('origem', 'A origem do atendimento tornou-se incompatível.')
        if (
            preselecao.origem_tipo == PreSelecaoEncontrista.OrigemTipo.AVULSO
            and not _eh_atendimento_avulso(atendimento)
        ):
            _erro('origem', 'A origem avulsa não é mais verificável.')
        pessoa = atendimento.pessoa

    if pessoa is None:
        _erro('identidade', 'A origem não possui Pessoa canônica resolvida.')
    if (
        preselecao.pessoa_resolvida_id is not None
        and preselecao.pessoa_resolvida_id != pessoa.pk
    ):
        _erro('identidade', 'A origem diverge da Pessoa resolvida na pré-seleção.')
    return pessoa


def _convite_bloqueado(pessoa, encontro):
    return (
        ConviteEncontro.objects
        .select_for_update(of=('self',))
        .filter(
            pessoa=pessoa,
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )
        .first()
    )


def _resultado_encaminhado_idempotente(preselecao, pessoa, encontro):
    convite = _convite_bloqueado(pessoa, encontro)
    if convite is None:
        _erro(
            'integridade',
            'A pré-seleção encaminhada não possui convite lógico correspondente.',
        )
    return ResultadoEncaminhamentoEncontrista(
        preselecao=preselecao,
        convite=convite,
        convite_criado=False,
        confirmacao_preexistente=(
            convite.status == ConviteEncontro.Status.CONFIRMADO
        ),
    )


def _exigir_campanha_compativel(campanha):
    if campanha is None:
        return
    if campanha.status == CampanhaConvitesEncontro.Status.ENCERRADA:
        _erro('campanha', 'A campanha de convites está encerrada.')
    if campanha.status != CampanhaConvitesEncontro.Status.ATIVA:
        _erro(
            'campanha',
            'A campanha não permite novos encaminhamentos neste estado.',
        )


def _exigir_elegibilidade(pessoa, encontro, momento):
    data_avaliacao = (
        timezone.localdate(momento)
        if momento is not None
        else timezone.localdate()
    )
    avaliacao = avaliar_elegibilidade_encontrista(
        pessoa=pessoa,
        encontro=encontro,
        data_avaliacao=data_avaliacao,
    )
    if avaliacao.resultado not in {
        ResultadoElegibilidadeEncontrista.ELEGIVEL,
        ResultadoElegibilidadeEncontrista.ELEGIVEL_COM_AVISO,
    }:
        _erro('elegibilidade', 'A Pessoa não está elegível para encaminhamento.')


@transaction.atomic
def aprovar_encaminhamento_preselecao(
    *,
    usuario,
    encontro,
    preselecao,
    momento=None,
):
    _exigir_permissao_encaminhar(usuario, encontro)
    encontro = _encontro_bloqueado(encontro)
    _exigir_lifecycle(encontro)

    # A configuração é opcional somente até o estado da pré-seleção ser
    # conhecido: isso preserva a repetição histórica de um encaminhamento já
    # efetivado sem inverter a ordem canônica Configuração → Campanha.
    configuracao = _configuracao_bloqueada(encontro, obrigatoria=False)
    campanha = _campanha_bloqueada(encontro)
    preselecao = _preselecao_bloqueada(preselecao, encontro)

    if preselecao.estado == PreSelecaoEncontrista.Estado.ENCAMINHADA:
        pessoa = _pessoa_bloqueada(preselecao.pessoa_resolvida)
        return _resultado_encaminhado_idempotente(preselecao, pessoa, encontro)
    if preselecao.estado == PreSelecaoEncontrista.Estado.ENCERRADA:
        _erro('estado', 'Pré-seleção encerrada não pode ser encaminhada.')
    if preselecao.estado != PreSelecaoEncontrista.Estado.PRESELECIONADA:
        _erro('estado', 'Estado de pré-seleção inválido para encaminhamento.')

    _exigir_campanha_compativel(campanha)
    if configuracao is None:
        _erro(
            'configuracao',
            'O Encontro não possui configuração de encontristas.',
        )
    pessoa_origem = _resolver_origem_preselecao(preselecao, encontro)
    pessoa = _pessoa_bloqueada(pessoa_origem)
    if _conflito_de_pessoa(
        _preselecoes_abertas(encontro),
        pessoa_resolvida=pessoa,
        excluir=preselecao,
    ):
        _erro('identidade', 'A Pessoa possui outra pré-seleção aberta.')
    if ParticipacaoEncontro.objects.filter(
        pessoa=pessoa,
        encontro=encontro,
    ).exists():
        _erro('participacao', 'A Pessoa já possui participação neste Encontro.')
    _exigir_elegibilidade(pessoa, encontro, momento)

    convite = _convite_bloqueado(pessoa, encontro)
    convite_criado = convite is None
    if convite is None:
        convite = criar_convite(
            pessoa=pessoa,
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )
    elif convite.status == ConviteEncontro.Status.RECUSADO:
        _erro('convite', 'Convite recusado exige reabertura explícita.')

    if preselecao.pessoa_resolvida_id is None:
        preselecao.pessoa_resolvida = pessoa
    instante = momento or timezone.now()
    preselecao.estado = PreSelecaoEncontrista.Estado.ENCAMINHADA
    preselecao.encaminhada_por = usuario
    preselecao.encaminhada_em = instante
    preselecao.save(update_fields=[
        'pessoa_resolvida',
        'estado',
        'encaminhada_por',
        'encaminhada_em',
        'atualizada_em',
    ])
    _auditar_encaminhamento(
        preselecao,
        convite,
        usuario,
        convite_criado=convite_criado,
    )
    return ResultadoEncaminhamentoEncontrista(
        preselecao=preselecao,
        convite=convite,
        convite_criado=convite_criado,
        confirmacao_preexistente=(
            convite.status == ConviteEncontro.Status.CONFIRMADO
        ),
    )


@transaction.atomic
def preselecionar_encontrista(
    *,
    usuario,
    encontro,
    origem_tipo,
    inscricao=None,
    atendimento=None,
    momento=None,
):
    _exigir_permissao_preselecionar(usuario, encontro)
    encontro = _encontro_bloqueado(encontro)
    _exigir_lifecycle(encontro)
    origem = _resolver_origem(
        encontro=encontro,
        origem_tipo=origem_tipo,
        inscricao=inscricao,
        atendimento=atendimento,
    )
    abertas = _preselecoes_abertas(encontro)
    existente = _preselecao_exata(
        abertas,
        inscricao=origem['inscricao_origem'],
        atendimento=origem['atendimento_origem'],
    )
    _validar_identidade_existente(existente, origem['pessoa_resolvida'])
    if _conflito_de_pessoa(
        abertas,
        pessoa_resolvida=origem['pessoa_resolvida'],
        excluir=existente,
    ):
        _erro(
            'identidade',
            'A Pessoa já possui outra pré-seleção aberta neste Encontro.',
        )
    if existente is not None:
        if existente.origem_tipo != origem_tipo:
            _erro('origem', 'A origem já possui pré-seleção aberta incompatível.')
        return existente

    preselecao = PreSelecaoEncontrista(
        encontro=encontro,
        origem_tipo=origem_tipo,
        registrada_por=usuario,
        registrada_em=momento or timezone.now(),
        **origem,
    )
    try:
        with transaction.atomic():
            preselecao.save(force_insert=True)
    except IntegrityError:
        concorrente = _preselecao_exata(
            _preselecoes_abertas(encontro),
            inscricao=origem['inscricao_origem'],
            atendimento=origem['atendimento_origem'],
        )
        _validar_identidade_existente(concorrente, origem['pessoa_resolvida'])
        if concorrente is not None and concorrente.origem_tipo == origem_tipo:
            return concorrente
        if _conflito_de_pessoa(
            _preselecoes_abertas(encontro),
            pessoa_resolvida=origem['pessoa_resolvida'],
        ):
            _erro(
                'identidade',
                'A Pessoa já possui outra pré-seleção aberta neste Encontro.',
            )
        _erro('integridade', 'Não foi possível registrar a pré-seleção.')

    _auditar_criacao(preselecao, usuario)
    return preselecao


@transaction.atomic
def encerrar_preselecao_encontrista(
    *,
    usuario,
    encontro,
    preselecao,
    momento=None,
):
    _exigir_permissao_encerrar(usuario, encontro)
    encontro = _encontro_bloqueado(encontro)
    preselecao_id = _pk(preselecao, 'preselecao')
    try:
        preselecao = (
            PreSelecaoEncontrista.objects
            .select_for_update()
            .select_related('encontro')
            .get(pk=preselecao_id)
        )
    except PreSelecaoEncontrista.DoesNotExist:
        _erro('preselecao', 'Pré-seleção não encontrada.')
    if preselecao.encontro_id != encontro.pk:
        _erro('preselecao', 'Pré-seleção não encontrada.')
    if preselecao.estado == PreSelecaoEncontrista.Estado.ENCERRADA:
        return preselecao

    _exigir_lifecycle(encontro)
    if preselecao.estado != PreSelecaoEncontrista.Estado.PRESELECIONADA:
        _erro(
            'estado',
            'Somente uma pré-seleção ainda não encaminhada pode ser encerrada.',
        )

    estado_anterior = preselecao.estado
    preselecao.estado = PreSelecaoEncontrista.Estado.ENCERRADA
    preselecao.encerrada_por = usuario
    preselecao.encerrada_em = momento or timezone.now()
    preselecao.save(update_fields=[
        'estado',
        'encerrada_por',
        'encerrada_em',
        'atualizada_em',
    ])
    _auditar_encerramento(preselecao, usuario, estado_anterior)
    return preselecao
