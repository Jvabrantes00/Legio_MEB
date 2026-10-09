from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from secrets import token_urlsafe

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    CampanhaConvitesEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    Encontro,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    ParticipacaoEncontro,
    RodadaConvitesEncontro,
)
from core.permissions import (
    pode_consultar_campanha_convites,
    pode_gerir_campanha_convites,
)
from core.services.auditoria_encontros import (
    registrar_evento_auditoria_encontro,
)
from core.services.elegibilidade_encontristas import (
    ResultadoElegibilidadeEncontrista,
    avaliar_elegibilidade_encontrista,
)
from core.services.participacoes import responder_convite


class ErroCampanhaConvites(ValidationError):
    pass


@dataclass(frozen=True)
class CandidatoCampanha:
    inscricao: InscricaoEncontro
    convite: ConviteEncontro
    elegibilidade: ResultadoElegibilidadeEncontrista
    canais: tuple[str, ...]

    @property
    def sem_canal(self):
        return not self.canais

    def as_dict(self):
        return {
            'inscricao_id': self.inscricao.pk,
            'pessoa_id': self.inscricao.pessoa_id,
            'convite_id': self.convite.pk,
            'elegibilidade': self.elegibilidade.value,
            'canais_disponiveis': list(self.canais),
            'sem_canal': self.sem_canal,
        }


@dataclass(frozen=True)
class ProjecaoCandidatosCampanha:
    capacidade: int
    confirmados: int
    lista_espera_ativa: bool
    candidatos: tuple[CandidatoCampanha, ...]

    def as_dict(self):
        return {
            'capacidade': self.capacidade,
            'confirmados': self.confirmados,
            'lista_espera_ativa': self.lista_espera_ativa,
            'sem_prioridade': True,
            'ordenacao_representa_prioridade': False,
            'candidatos': [item.as_dict() for item in self.candidatos],
        }


@dataclass(frozen=True)
class ResultadoAberturaRodada:
    rodada: RodadaConvitesEncontro
    oportunidades: tuple[OportunidadeConviteEncontro, ...]
    criada: bool = True


_RESULTADOS_ELEGIVEIS = frozenset({
    ResultadoElegibilidadeEncontrista.ELEGIVEL,
    ResultadoElegibilidadeEncontrista.ELEGIVEL_COM_AVISO,
})
_STATUS_AUTOMATICOS_CONVITE = frozenset({
    ConviteEncontro.Status.CONVIDADO,
    ConviteEncontro.Status.SEM_RESPOSTA,
})
_CAMPOS_AUDITORIA = frozenset({
    'campanha_id',
    'status',
    'prazo_confirmacao',
    'rodada_id',
    'tipo_rodada',
    'sequencia',
    'oportunidades_criadas',
    'oportunidade_id',
    'convite_id',
    'convite_status',
    'oportunidade_status',
    'confirmados',
    'capacidade',
})


def _erro(campo, mensagem):
    raise ErroCampanhaConvites({campo: [mensagem]})


def _exigir_gestao(usuario):
    if not pode_gerir_campanha_convites(usuario):
        raise PermissionDenied(
            'Seu usuário não pode gerir campanhas de convites.'
        )


def _exigir_consulta(usuario):
    if not pode_consultar_campanha_convites(usuario):
        raise PermissionDenied(
            'Seu usuário não pode consultar campanhas de convites.'
        )


def _momento(valor=None):
    valor = valor or timezone.now()
    if not isinstance(valor, datetime) or timezone.is_naive(valor):
        _erro('momento', 'Informe data e hora com fuso horário.')
    return valor


def _prazo_futuro(valor, *, momento):
    if not isinstance(valor, datetime) or timezone.is_naive(valor):
        _erro('prazo_confirmacao', 'Informe prazo com fuso horário.')
    if valor <= momento:
        _erro('prazo_confirmacao', 'O prazo deve ser posterior ao início.')
    return valor


def _encontro_bloqueado(encontro):
    if encontro is None or encontro.pk is None:
        _erro('encontro', 'Encontro deve estar persistido.')
    try:
        return Encontro.objects.select_for_update().get(pk=encontro.pk)
    except Encontro.DoesNotExist:
        _erro('encontro', 'Encontro não encontrado.')


def _configuracao(encontro, *, bloquear=False):
    queryset = ConfiguracaoEncontristasEncontro.objects
    if bloquear:
        queryset = queryset.select_for_update()
    try:
        return queryset.get(encontro=encontro)
    except ConfiguracaoEncontristasEncontro.DoesNotExist:
        _erro(
            'configuracao',
            'Configure os encontristas antes de operar a campanha.',
        )


def _campanha_bloqueada(campanha):
    if campanha is None or campanha.pk is None:
        _erro('campanha', 'Campanha deve estar persistida.')
    try:
        return (
            CampanhaConvitesEncontro.objects
            .select_for_update()
            .select_related('encontro')
            .get(pk=campanha.pk)
        )
    except CampanhaConvitesEncontro.DoesNotExist:
        _erro('campanha', 'Campanha não encontrada.')


def _ocupacao_confirmada(encontro):
    return ConviteEncontro.objects.filter(
        encontro=encontro,
        finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        status=ConviteEncontro.Status.CONFIRMADO,
    ).count()


def _canais_da_pessoa(pessoa):
    canais = []
    if pessoa.email:
        canais.append('EMAIL')
    if any(
        telefone.whatsapp and telefone.numero
        for telefone in pessoa.telefones.all()
    ):
        canais.append('WHATSAPP')
    return tuple(canais)


def _candidatos(
    *,
    encontro,
    convites_recusados_permitidos=frozenset(),
    bloquear=False,
):
    inscricoes = list(
        InscricaoEncontro.objects
        .filter(
            encontro=encontro,
            status=InscricaoEncontro.Status.ENVIADA,
            pessoa__isnull=False,
        )
        .select_related('pessoa')
        .prefetch_related('pessoa__telefones')
        .order_by('pessoa_id')
    )
    if not inscricoes:
        return ()

    convites_queryset = ConviteEncontro.objects.filter(
        encontro=encontro,
        finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        pessoa_id__in=[item.pessoa_id for item in inscricoes],
    )
    if bloquear:
        convites_queryset = convites_queryset.select_for_update()
    convites = {
        convite.pessoa_id: convite
        for convite in convites_queryset.order_by('pessoa_id')
    }
    pessoas_com_participacao = set(
        ParticipacaoEncontro.objects.filter(
            encontro=encontro,
            pessoa_id__in=[item.pessoa_id for item in inscricoes],
        ).values_list('pessoa_id', flat=True)
    )
    candidatos = []
    for inscricao in inscricoes:
        convite = convites.get(inscricao.pessoa_id)
        if convite is None or inscricao.pessoa_id in pessoas_com_participacao:
            continue
        status_permitido = convite.status in _STATUS_AUTOMATICOS_CONVITE
        if (
            convite.status == ConviteEncontro.Status.RECUSADO
            and convite.pk in convites_recusados_permitidos
        ):
            status_permitido = True
        if not status_permitido:
            continue
        avaliacao = avaliar_elegibilidade_encontrista(
            pessoa=inscricao.pessoa,
            encontro=encontro,
        )
        if avaliacao.resultado not in _RESULTADOS_ELEGIVEIS:
            continue
        candidatos.append(CandidatoCampanha(
            inscricao=inscricao,
            convite=convite,
            elegibilidade=avaliacao.resultado,
            canais=_canais_da_pessoa(inscricao.pessoa),
        ))
    return tuple(candidatos)


def _auditar(
    *,
    campanha,
    usuario,
    fato,
    entidade,
    objeto_id,
    anterior,
    novo,
    justificativa='',
):
    return registrar_evento_auditoria_encontro(
        encontro=campanha.encontro,
        ator=usuario,
        fato=fato,
        entidade=entidade,
        objeto_id=objeto_id,
        valor_anterior=anterior,
        valor_novo=novo,
        campos_permitidos=_CAMPOS_AUDITORIA,
        justificativa=justificativa,
    )


def _digest_novo():
    segredo = token_urlsafe(32)
    return sha256(segredo.encode()).hexdigest()


def _encerrar_rodadas_abertas(
    *,
    campanha,
    momento,
    status_oportunidade,
    marcar_sem_resposta=False,
):
    rodadas = list(
        RodadaConvitesEncontro.objects
        .select_for_update()
        .filter(campanha=campanha, status=RodadaConvitesEncontro.Status.ABERTA)
    )
    if not rodadas:
        return
    oportunidades = OportunidadeConviteEncontro.objects.select_for_update().filter(
        rodada__in=rodadas,
        status=OportunidadeConviteEncontro.Status.PENDENTE,
    )
    convite_ids = list(oportunidades.values_list('convite_id', flat=True))
    oportunidades.update(
        status=status_oportunidade,
        atualizada_em=momento,
    )
    if marcar_sem_resposta and convite_ids:
        ConviteEncontro.objects.filter(
            pk__in=convite_ids,
            status=ConviteEncontro.Status.CONVIDADO,
        ).update(
            status=ConviteEncontro.Status.SEM_RESPOSTA,
            atualizado_em=momento,
        )
    RodadaConvitesEncontro.objects.filter(pk__in=[item.pk for item in rodadas]).update(
        status=RodadaConvitesEncontro.Status.ENCERRADA,
        encerrada_em=momento,
        atualizada_em=momento,
    )


def _abrir_rodada(
    *,
    campanha,
    tipo,
    momento,
    convites_recusados_permitidos=frozenset(),
    convites_restritos=frozenset(),
    encerrar_anteriores=True,
):
    if encerrar_anteriores:
        _encerrar_rodadas_abertas(
            campanha=campanha,
            momento=momento,
            status_oportunidade=(
                OportunidadeConviteEncontro.Status.INVALIDADA
            ),
        )
    ultima_sequencia = (
        RodadaConvitesEncontro.objects
        .select_for_update()
        .filter(campanha=campanha)
        .aggregate(maxima=Max('sequencia'))['maxima']
        or 0
    )
    rodada = RodadaConvitesEncontro.objects.create(
        campanha=campanha,
        sequencia=ultima_sequencia + 1,
        tipo=tipo,
        aberta_em=momento,
    )
    configuracao = _configuracao(campanha.encontro)
    candidatos = ()
    if _ocupacao_confirmada(campanha.encontro) < configuracao.capacidade:
        candidatos = _candidatos(
            encontro=campanha.encontro,
            convites_recusados_permitidos=convites_recusados_permitidos,
            bloquear=True,
        )
        if convites_restritos:
            candidatos = tuple(
                candidato
                for candidato in candidatos
                if candidato.convite.pk in convites_restritos
            )
    oportunidades = []
    for candidato in candidatos:
        convite = candidato.convite
        if convite.status != ConviteEncontro.Status.CONVIDADO:
            convite.status = ConviteEncontro.Status.CONVIDADO
            convite.save(update_fields=['status', 'atualizado_em'])
        oportunidades.append(OportunidadeConviteEncontro.objects.create(
            rodada=rodada,
            convite=convite,
            token_digest=_digest_novo(),
            expira_em=campanha.prazo_confirmacao,
        ))
    return ResultadoAberturaRodada(
        rodada=rodada,
        oportunidades=tuple(oportunidades),
    )


def consultar_campanha(*, usuario, encontro):
    _exigir_consulta(usuario)
    if encontro is None or encontro.pk is None:
        _erro('encontro', 'Encontro deve estar persistido.')
    return (
        CampanhaConvitesEncontro.objects
        .filter(encontro=encontro)
        .select_related('encontro', 'iniciada_por')
        .prefetch_related('rodadas__oportunidades')
        .first()
    )


def projetar_candidatos(*, usuario, encontro):
    _exigir_consulta(usuario)
    configuracao = _configuracao(encontro)
    confirmados = _ocupacao_confirmada(encontro)
    candidatos = _candidatos(encontro=encontro)
    return ProjecaoCandidatosCampanha(
        capacidade=configuracao.capacidade,
        confirmados=confirmados,
        lista_espera_ativa=confirmados == configuracao.capacidade,
        candidatos=candidatos,
    )


def projetar_lista_espera(*, usuario, encontro):
    projecao = projetar_candidatos(usuario=usuario, encontro=encontro)
    if not projecao.lista_espera_ativa:
        return ProjecaoCandidatosCampanha(
            capacidade=projecao.capacidade,
            confirmados=projecao.confirmados,
            lista_espera_ativa=False,
            candidatos=(),
        )
    return projecao


@transaction.atomic
def iniciar_campanha(
    *,
    usuario,
    encontro,
    prazo_confirmacao,
    justificativa='',
    momento=None,
):
    _exigir_gestao(usuario)
    instante = _momento(momento)
    prazo = _prazo_futuro(prazo_confirmacao, momento=instante)
    encontro = _encontro_bloqueado(encontro)
    _configuracao(encontro, bloquear=True)
    if CampanhaConvitesEncontro.objects.select_for_update().filter(
        encontro=encontro,
    ).exists():
        _erro('campanha', 'O Encontro já possui campanha de convites.')
    try:
        campanha = CampanhaConvitesEncontro.objects.create(
            encontro=encontro,
            iniciada_por=usuario,
            iniciada_em=instante,
            prazo_confirmacao=prazo,
        )
        abertura = _abrir_rodada(
            campanha=campanha,
            tipo=RodadaConvitesEncontro.Tipo.INICIAL,
            momento=instante,
            encerrar_anteriores=False,
        )
    except IntegrityError:
        _erro('campanha', 'Não foi possível iniciar outra campanha.')
    _auditar(
        campanha=campanha,
        usuario=usuario,
        fato='campanha_convites.iniciada',
        entidade='campanha_convites',
        objeto_id=campanha.pk,
        anterior={},
        novo={
            'campanha_id': campanha.pk,
            'status': campanha.status,
            'prazo_confirmacao': prazo.isoformat(),
            'rodada_id': abertura.rodada.pk,
            'tipo_rodada': abertura.rodada.tipo,
            'sequencia': abertura.rodada.sequencia,
            'oportunidades_criadas': len(abertura.oportunidades),
        },
        justificativa=justificativa,
    )
    return campanha


@transaction.atomic
def processar_prazo(*, usuario, campanha, momento=None):
    _exigir_gestao(usuario)
    instante = _momento(momento)
    campanha = _campanha_bloqueada(campanha)
    _configuracao(campanha.encontro, bloquear=True)
    if campanha.status in {
        CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO,
        CampanhaConvitesEncontro.Status.ENCERRADA,
    }:
        return campanha
    if instante < campanha.prazo_confirmacao:
        return campanha

    anterior = campanha.status
    _encerrar_rodadas_abertas(
        campanha=campanha,
        momento=instante,
        status_oportunidade=OportunidadeConviteEncontro.Status.EXPIRADA,
        marcar_sem_resposta=True,
    )
    campanha.status = CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO
    campanha.save(update_fields=['status', 'atualizada_em'])
    _auditar(
        campanha=campanha,
        usuario=usuario,
        fato='campanha_convites.prazo_processado',
        entidade='campanha_convites',
        objeto_id=campanha.pk,
        anterior={'status': anterior},
        novo={'status': campanha.status},
    )
    return campanha


@transaction.atomic
def encerrar_campanha(
    *,
    usuario,
    campanha,
    justificativa='',
    momento=None,
):
    _exigir_gestao(usuario)
    instante = _momento(momento)
    campanha = _campanha_bloqueada(campanha)
    _configuracao(campanha.encontro, bloquear=True)
    if campanha.status == CampanhaConvitesEncontro.Status.ENCERRADA:
        return campanha
    if campanha.status != CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO:
        _erro(
            'status',
            'A campanha precisa aguardar decisão antes do encerramento.',
        )
    anterior = campanha.status
    _encerrar_rodadas_abertas(
        campanha=campanha,
        momento=instante,
        status_oportunidade=OportunidadeConviteEncontro.Status.INVALIDADA,
        marcar_sem_resposta=True,
    )
    campanha.status = CampanhaConvitesEncontro.Status.ENCERRADA
    campanha.encerrada_em = instante
    campanha.save(update_fields=['status', 'encerrada_em', 'atualizada_em'])
    _auditar(
        campanha=campanha,
        usuario=usuario,
        fato='campanha_convites.encerrada',
        entidade='campanha_convites',
        objeto_id=campanha.pk,
        anterior={'status': anterior},
        novo={'status': campanha.status},
        justificativa=justificativa,
    )
    return campanha


@transaction.atomic
def prorrogar_campanha(
    *,
    usuario,
    campanha,
    novo_prazo,
    justificativa='',
    momento=None,
):
    _exigir_gestao(usuario)
    instante = _momento(momento)
    prazo = _prazo_futuro(novo_prazo, momento=instante)
    campanha = _campanha_bloqueada(campanha)
    _configuracao(campanha.encontro, bloquear=True)
    if campanha.status != CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO:
        _erro('status', 'Somente campanha aguardando decisão pode ser prorrogada.')
    prazo_anterior = campanha.prazo_confirmacao
    campanha.status = CampanhaConvitesEncontro.Status.ATIVA
    campanha.prazo_confirmacao = prazo
    campanha.encerrada_em = None
    campanha.save(update_fields=[
        'status',
        'prazo_confirmacao',
        'encerrada_em',
        'atualizada_em',
    ])
    abertura = _abrir_rodada(
        campanha=campanha,
        tipo=RodadaConvitesEncontro.Tipo.PRORROGACAO,
        momento=instante,
    )
    _auditar(
        campanha=campanha,
        usuario=usuario,
        fato='campanha_convites.prorrogada',
        entidade='campanha_convites',
        objeto_id=campanha.pk,
        anterior={
            'status': CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO,
            'prazo_confirmacao': prazo_anterior.isoformat(),
        },
        novo={
            'status': campanha.status,
            'prazo_confirmacao': prazo.isoformat(),
            'rodada_id': abertura.rodada.pk,
            'tipo_rodada': abertura.rodada.tipo,
            'sequencia': abertura.rodada.sequencia,
            'oportunidades_criadas': len(abertura.oportunidades),
        },
        justificativa=justificativa,
    )
    return campanha


@transaction.atomic
def registrar_recusa(
    *,
    usuario,
    oportunidade,
    justificativa='',
    momento=None,
):
    _exigir_gestao(usuario)
    instante = _momento(momento)
    if oportunidade is None or oportunidade.pk is None:
        _erro('oportunidade', 'Oportunidade deve estar persistida.')
    try:
        oportunidade = (
            OportunidadeConviteEncontro.objects
            .select_for_update()
            .select_related('rodada__campanha__encontro', 'convite')
            .get(pk=oportunidade.pk)
        )
    except OportunidadeConviteEncontro.DoesNotExist:
        _erro('oportunidade', 'Oportunidade não encontrada.')
    campanha = _campanha_bloqueada(oportunidade.rodada.campanha)
    _configuracao(campanha.encontro, bloquear=True)
    convite = oportunidade.convite
    if (
        oportunidade.status == OportunidadeConviteEncontro.Status.CONSUMIDA
        and convite.status == ConviteEncontro.Status.RECUSADO
    ):
        return oportunidade
    if campanha.status != CampanhaConvitesEncontro.Status.ATIVA:
        _erro('campanha', 'A campanha não aceita respostas neste estado.')
    if instante > campanha.prazo_confirmacao or instante > oportunidade.expira_em:
        _erro('prazo', 'A oportunidade não aceita mais resposta.')
    if oportunidade.status != OportunidadeConviteEncontro.Status.PENDENTE:
        _erro('oportunidade', 'A oportunidade não está pendente.')

    responder_convite(
        convite,
        status=ConviteEncontro.Status.RECUSADO,
    )
    oportunidade.status = OportunidadeConviteEncontro.Status.CONSUMIDA
    oportunidade.consumida_em = instante
    oportunidade.save(update_fields=['status', 'consumida_em', 'atualizada_em'])
    _auditar(
        campanha=campanha,
        usuario=usuario,
        fato='campanha_convites.recusa_registrada',
        entidade='oportunidade_convite',
        objeto_id=oportunidade.pk,
        anterior={
            'oportunidade_status': OportunidadeConviteEncontro.Status.PENDENTE,
            'convite_status': ConviteEncontro.Status.CONVIDADO,
        },
        novo={
            'oportunidade_id': oportunidade.pk,
            'convite_id': convite.pk,
            'oportunidade_status': oportunidade.status,
            'convite_status': ConviteEncontro.Status.RECUSADO,
        },
        justificativa=justificativa,
    )
    return oportunidade


@transaction.atomic
def reabrir_recusa(
    *,
    usuario,
    campanha,
    convite,
    justificativa,
    momento=None,
):
    _exigir_gestao(usuario)
    justificativa = justificativa.strip() if isinstance(justificativa, str) else ''
    if not justificativa:
        _erro('justificativa', 'Informe a justificativa da reabertura.')
    instante = _momento(momento)
    campanha = _campanha_bloqueada(campanha)
    _configuracao(campanha.encontro, bloquear=True)
    if campanha.status != CampanhaConvitesEncontro.Status.ATIVA:
        _erro('status', 'A campanha precisa estar ativa para reabrir recusa.')
    if instante >= campanha.prazo_confirmacao:
        _erro('prazo', 'O prazo da campanha terminou.')
    try:
        convite = (
            ConviteEncontro.objects
            .select_for_update()
            .get(
                pk=convite.pk,
                encontro=campanha.encontro,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            )
        )
    except (AttributeError, ConviteEncontro.DoesNotExist):
        _erro('convite', 'Convite de participação não encontrado.')
    if convite.status != ConviteEncontro.Status.RECUSADO:
        _erro('convite', 'Somente convite recusado pode ser reaberto.')

    abertura = _abrir_rodada(
        campanha=campanha,
        tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
        momento=instante,
        convites_recusados_permitidos=frozenset({convite.pk}),
        convites_restritos=frozenset({convite.pk}),
        encerrar_anteriores=False,
    )
    oportunidade = next(
        (item for item in abertura.oportunidades if item.convite_id == convite.pk),
        None,
    )
    if oportunidade is None:
        _erro(
            'convite',
            'A Pessoa não está resolvida e elegível para nova oportunidade.',
        )
    _auditar(
        campanha=campanha,
        usuario=usuario,
        fato='campanha_convites.recusa_reaberta',
        entidade='convite_encontro',
        objeto_id=convite.pk,
        anterior={'convite_status': ConviteEncontro.Status.RECUSADO},
        novo={
            'convite_id': convite.pk,
            'convite_status': ConviteEncontro.Status.CONVIDADO,
            'rodada_id': abertura.rodada.pk,
            'tipo_rodada': abertura.rodada.tipo,
            'sequencia': abertura.rodada.sequencia,
            'oportunidade_id': oportunidade.pk,
            'oportunidades_criadas': len(abertura.oportunidades),
        },
        justificativa=justificativa,
    )
    return abertura


@transaction.atomic
def abrir_reposicao_nova_vaga(
    *,
    usuario,
    campanha,
    justificativa='',
    momento=None,
):
    _exigir_gestao(usuario)
    instante = _momento(momento)
    campanha = _campanha_bloqueada(campanha)
    configuracao = _configuracao(campanha.encontro, bloquear=True)
    if campanha.status != CampanhaConvitesEncontro.Status.ATIVA:
        _erro('status', 'A campanha precisa estar ativa para repor vaga.')
    if instante >= campanha.prazo_confirmacao:
        _erro('prazo', 'O prazo da campanha terminou.')
    confirmados = _ocupacao_confirmada(campanha.encontro)
    if confirmados >= configuracao.capacidade:
        _erro('capacidade', 'Não existe vaga disponível para reposição.')

    rodada_existente = (
        RodadaConvitesEncontro.objects
        .select_for_update()
        .filter(
            campanha=campanha,
            tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
            status=RodadaConvitesEncontro.Status.ABERTA,
        )
        .order_by('-sequencia')
        .first()
    )
    if rodada_existente is not None:
        return ResultadoAberturaRodada(
            rodada=rodada_existente,
            oportunidades=tuple(rodada_existente.oportunidades.all()),
            criada=False,
        )

    abertura = _abrir_rodada(
        campanha=campanha,
        tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
        momento=instante,
    )
    if not abertura.oportunidades:
        _erro('candidatos', 'Não existem candidatos elegíveis para reposição.')
    _auditar(
        campanha=campanha,
        usuario=usuario,
        fato='campanha_convites.reposicao_aberta',
        entidade='rodada_convites',
        objeto_id=abertura.rodada.pk,
        anterior={
            'confirmados': confirmados,
            'capacidade': configuracao.capacidade,
        },
        novo={
            'rodada_id': abertura.rodada.pk,
            'tipo_rodada': abertura.rodada.tipo,
            'sequencia': abertura.rodada.sequencia,
            'oportunidades_criadas': len(abertura.oportunidades),
            'confirmados': confirmados,
            'capacidade': configuracao.capacidade,
        },
        justificativa=justificativa,
    )
    return abertura
