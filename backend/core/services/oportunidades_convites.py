import re
from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from hashlib import sha256
from secrets import compare_digest

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from core.models import (
    CampanhaConvitesEncontro,
    ConviteEncontro,
    Encontro,
    OportunidadeConviteEncontro,
    RodadaConvitesEncontro,
)
from core.services.auditoria_encontros import (
    registrar_evento_auditoria_encontro,
)
from core.services.elegibilidade_encontristas import (
    ResultadoElegibilidadeEncontrista,
    avaliar_elegibilidade_encontrista,
)
from core.services.participacoes import (
    bloquear_configuracao_capacidade,
    ocupacao_confirmada_participacao,
)


TOKEN_PATTERN = re.compile(r'^[A-Za-z0-9_-]{43}$')
RESULTADOS_ELEGIVEIS = frozenset({
    ResultadoElegibilidadeEncontrista.ELEGIVEL,
    ResultadoElegibilidadeEncontrista.ELEGIVEL_COM_AVISO,
})
MENSAGEM_NAO_VALIDADO = (
    'Não foi possível validar este convite. Confira os dados ou procure '
    'a equipe de Fichas.'
)


class ConvitePublicoNaoValidado(Exception):
    pass


class DecisaoConvitePublico(str, Enum):
    CONFIRMAR = 'confirmar'
    RECUSAR = 'recusar'


class EstadoConvitePublico(str, Enum):
    PENDENTE = 'pendente'
    CONFIRMADO = 'confirmado'
    RECUSADO = 'recusado'
    EXPIRADO = 'expirado'
    SUSPENSO = 'suspenso'
    INDISPONIVEL = 'indisponivel'


MENSAGENS_ESTADO = {
    EstadoConvitePublico.PENDENTE: (
        'Confirme ou recuse este convite dentro do prazo informado.'
    ),
    EstadoConvitePublico.CONFIRMADO: 'Sua confirmação foi registrada.',
    EstadoConvitePublico.RECUSADO: (
        'Sua resposta de recusa foi registrada.'
    ),
    EstadoConvitePublico.EXPIRADO: 'O prazo deste convite terminou.',
    EstadoConvitePublico.SUSPENSO: (
        'Este convite está em análise pela equipe de Fichas.'
    ),
    EstadoConvitePublico.INDISPONIVEL: (
        'Esta oportunidade não está mais disponível.'
    ),
}


@dataclass(frozen=True)
class ResultadoConvitePublico:
    estado: EstadoConvitePublico
    titulo_encontro: str
    datas_encontro: tuple[date, ...]
    prazo_resposta: datetime

    @property
    def pode_responder(self):
        return self.estado == EstadoConvitePublico.PENDENTE

    def as_dict(self):
        return {
            'estado': self.estado.value,
            'titulo_encontro': self.titulo_encontro,
            'datas_encontro': [item.isoformat() for item in self.datas_encontro],
            'prazo_resposta': self.prazo_resposta.isoformat(),
            'finalidade': ConviteEncontro.Finalidade.PARTICIPAR,
            'pode_responder': self.pode_responder,
            'mensagem': MENSAGENS_ESTADO[self.estado],
        }


CAMPOS_AUDITORIA = frozenset({
    'origem',
    'oportunidade_id',
    'oportunidade_status',
    'convite_id',
    'convite_status',
    'motivo',
})


def _momento(valor=None):
    valor = valor or timezone.now()
    if not isinstance(valor, datetime) or timezone.is_naive(valor):
        raise ValidationError('Momento da resposta pública inválido.')
    return valor


def _digest_apresentado(token):
    texto = token if isinstance(token, str) else ''
    texto_limitado = texto[:128]
    digest = sha256(texto_limitado.encode()).hexdigest()
    formato_valido = bool(TOKEN_PATTERN.fullmatch(texto))
    return digest, formato_valido


def _nascimento_confere(oportunidade, data_nascimento):
    nascimento = oportunidade.convite.pessoa.data_nascimento
    if nascimento is None or not isinstance(data_nascimento, date):
        return False
    return compare_digest(
        nascimento.isoformat(),
        data_nascimento.isoformat(),
    )


def _queryset_oportunidade():
    return OportunidadeConviteEncontro.objects.select_related(
        'convite__pessoa',
        'convite__encontro',
        'rodada__campanha__iniciada_por',
    )


def _autenticar_oportunidade(*, token, data_nascimento):
    digest, formato_valido = _digest_apresentado(token)
    oportunidade = _queryset_oportunidade().filter(
        token_digest=digest,
        convite__finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
    ).first()
    if (
        not formato_valido
        or oportunidade is None
        or not _nascimento_confere(oportunidade, data_nascimento)
    ):
        raise ConvitePublicoNaoValidado(MENSAGEM_NAO_VALIDADO)
    return oportunidade


def _datas_publicas(encontro):
    return tuple(
        encontro.calendarios.filter(
            vigente=True,
            oficializado_em__isnull=False,
        )
        .values_list('dias__data', flat=True)
        .order_by('dias__data')
    )


def _estado_publico(oportunidade):
    if oportunidade.status == OportunidadeConviteEncontro.Status.CONSUMIDA:
        if oportunidade.convite.status == ConviteEncontro.Status.CONFIRMADO:
            return EstadoConvitePublico.CONFIRMADO
        if oportunidade.convite.status == ConviteEncontro.Status.RECUSADO:
            return EstadoConvitePublico.RECUSADO
        return EstadoConvitePublico.INDISPONIVEL
    if oportunidade.status == OportunidadeConviteEncontro.Status.EXPIRADA:
        return EstadoConvitePublico.EXPIRADO
    if oportunidade.status == OportunidadeConviteEncontro.Status.SUSPENSA:
        return EstadoConvitePublico.SUSPENSO
    if oportunidade.status == OportunidadeConviteEncontro.Status.INVALIDADA:
        return EstadoConvitePublico.INDISPONIVEL
    campanha = oportunidade.rodada.campanha
    if (
        campanha.status != CampanhaConvitesEncontro.Status.ATIVA
        or oportunidade.rodada.status != RodadaConvitesEncontro.Status.ABERTA
    ):
        return EstadoConvitePublico.INDISPONIVEL
    return EstadoConvitePublico.PENDENTE


def _resultado(oportunidade):
    encontro = oportunidade.convite.encontro
    return ResultadoConvitePublico(
        estado=_estado_publico(oportunidade),
        titulo_encontro=encontro.encontro,
        datas_encontro=_datas_publicas(encontro),
        prazo_resposta=oportunidade.expira_em,
    )


def _auditar(
    oportunidade,
    *,
    fato,
    anterior,
    novo,
    motivo='',
    ator=None,
    origem='publica',
):
    if motivo:
        novo['motivo'] = motivo
    return registrar_evento_auditoria_encontro(
        encontro=oportunidade.convite.encontro,
        ator=ator,
        fato=fato,
        entidade='oportunidade_convite',
        objeto_id=oportunidade.pk,
        valor_anterior=anterior,
        valor_novo=novo,
        campos_permitidos=CAMPOS_AUDITORIA,
        justificativa='',
        origem=origem,
    )


def _expirar_se_necessario(oportunidade, *, momento):
    if (
        oportunidade.status == OportunidadeConviteEncontro.Status.PENDENTE
        and (
            momento >= oportunidade.expira_em
            or momento >= oportunidade.rodada.campanha.prazo_confirmacao
        )
    ):
        oportunidade.status = OportunidadeConviteEncontro.Status.EXPIRADA
        oportunidade.save(update_fields=['status', 'atualizada_em'])


def _suspender_se_inelegivel(
    oportunidade,
    *,
    ator=None,
    origem='publica',
):
    if oportunidade.status != OportunidadeConviteEncontro.Status.PENDENTE:
        return False
    avaliacao = avaliar_elegibilidade_encontrista(
        pessoa=oportunidade.convite.pessoa,
        encontro=oportunidade.convite.encontro,
    )
    if avaliacao.resultado in RESULTADOS_ELEGIVEIS:
        return False
    oportunidade.status = OportunidadeConviteEncontro.Status.SUSPENSA
    oportunidade.save(update_fields=['status', 'atualizada_em'])
    _auditar(
        oportunidade,
        ator=ator,
        origem=origem,
        fato='oportunidade_convite.suspensa_inelegibilidade',
        anterior={
            'oportunidade_id': oportunidade.pk,
            'oportunidade_status': OportunidadeConviteEncontro.Status.PENDENTE,
        },
        novo={
            'oportunidade_id': oportunidade.pk,
            'oportunidade_status': oportunidade.status,
        },
        motivo='inelegibilidade_revalidada',
    )
    return True


@transaction.atomic
def consultar_convite_publico(*, token, data_nascimento, momento=None):
    instante = _momento(momento)
    autenticada = _autenticar_oportunidade(
        token=token,
        data_nascimento=data_nascimento,
    )
    oportunidade = (
        _queryset_oportunidade()
        .select_for_update(of=('self',))
        .get(pk=autenticada.pk)
    )
    _expirar_se_necessario(oportunidade, momento=instante)
    if oportunidade.status == OportunidadeConviteEncontro.Status.PENDENTE:
        _suspender_se_inelegivel(oportunidade)
    return _resultado(oportunidade)


def _invalidar(oportunidade, *, fato, motivo):
    if oportunidade.status != OportunidadeConviteEncontro.Status.PENDENTE:
        return
    oportunidade.status = OportunidadeConviteEncontro.Status.INVALIDADA
    oportunidade.save(update_fields=['status', 'atualizada_em'])
    _auditar(
        oportunidade,
        fato=fato,
        anterior={
            'oportunidade_id': oportunidade.pk,
            'oportunidade_status': OportunidadeConviteEncontro.Status.PENDENTE,
        },
        novo={
            'oportunidade_id': oportunidade.pk,
            'oportunidade_status': oportunidade.status,
        },
        motivo=motivo,
    )


def _invalidar_por_lotacao(oportunidade):
    _invalidar(
        oportunidade,
        fato='oportunidade_convite.invalidada_lotacao',
        motivo='capacidade_preenchida',
    )


def _bloquear_para_resposta(autenticada):
    encontro = Encontro.objects.select_for_update(of=('self',)).get(
        pk=autenticada.convite.encontro_id,
    )
    configuracao = bloquear_configuracao_capacidade(
        encontro,
        obrigatoria=True,
    )
    oportunidade = (
        _queryset_oportunidade()
        .select_for_update(of=('self',))
        .get(pk=autenticada.pk)
    )
    convite = ConviteEncontro.objects.select_for_update(of=('self',)).get(
        pk=oportunidade.convite_id,
    )
    oportunidade.convite = convite
    return configuracao, oportunidade, convite


@transaction.atomic
def responder_convite_publico(
    *,
    token,
    data_nascimento,
    decisao,
    momento=None,
):
    try:
        decisao = DecisaoConvitePublico(decisao)
    except (TypeError, ValueError) as error:
        raise ValidationError('Decisão pública inválida.') from error
    instante = _momento(momento)
    autenticada = _autenticar_oportunidade(
        token=token,
        data_nascimento=data_nascimento,
    )
    configuracao, oportunidade, convite = _bloquear_para_resposta(autenticada)
    if not _nascimento_confere(oportunidade, data_nascimento):
        raise ConvitePublicoNaoValidado(MENSAGEM_NAO_VALIDADO)

    _expirar_se_necessario(oportunidade, momento=instante)
    if oportunidade.status == OportunidadeConviteEncontro.Status.CONSUMIDA:
        return _resultado(oportunidade)
    if oportunidade.status != OportunidadeConviteEncontro.Status.PENDENTE:
        return _resultado(oportunidade)
    if (
        oportunidade.rodada.campanha.status
        != CampanhaConvitesEncontro.Status.ATIVA
        or oportunidade.rodada.status != RodadaConvitesEncontro.Status.ABERTA
    ):
        return _resultado(oportunidade)

    if decisao == DecisaoConvitePublico.CONFIRMAR:
        if _suspender_se_inelegivel(oportunidade):
            return _resultado(oportunidade)
        confirmados = ocupacao_confirmada_participacao(
            convite=convite,
            configuracao=configuracao,
        )
        if confirmados >= configuracao.capacidade:
            _invalidar_por_lotacao(oportunidade)
            return _resultado(oportunidade)
        status_convite = ConviteEncontro.Status.CONFIRMADO
        fato = 'oportunidade_convite.confirmada_publicamente'
    else:
        status_convite = ConviteEncontro.Status.RECUSADO
        fato = 'oportunidade_convite.recusada_publicamente'

    if convite.status != ConviteEncontro.Status.CONVIDADO:
        _invalidar(
            oportunidade,
            fato='oportunidade_convite.invalidada_estado_convite',
            motivo='convite_nao_respondivel',
        )
        return _resultado(oportunidade)

    status_anterior_convite = convite.status
    convite.status = status_convite
    convite.save(update_fields=['status', 'atualizado_em'])
    oportunidade.status = OportunidadeConviteEncontro.Status.CONSUMIDA
    oportunidade.consumida_em = instante
    oportunidade.save(update_fields=[
        'status',
        'consumida_em',
        'atualizada_em',
    ])
    _auditar(
        oportunidade,
        fato=fato,
        anterior={
            'oportunidade_id': oportunidade.pk,
            'oportunidade_status': OportunidadeConviteEncontro.Status.PENDENTE,
            'convite_id': convite.pk,
            'convite_status': status_anterior_convite,
        },
        novo={
            'oportunidade_id': oportunidade.pk,
            'oportunidade_status': oportunidade.status,
            'convite_id': convite.pk,
            'convite_status': convite.status,
        },
    )

    if decisao == DecisaoConvitePublico.CONFIRMAR:
        confirmados += 1
        if confirmados == configuracao.capacidade:
            concorrentes = list(
                _queryset_oportunidade()
                .select_for_update(of=('self',))
                .filter(
                    rodada=oportunidade.rodada,
                    status=OportunidadeConviteEncontro.Status.PENDENTE,
                )
                .exclude(pk=oportunidade.pk)
                .order_by('pk')
            )
            for concorrente in concorrentes:
                _invalidar_por_lotacao(concorrente)
    return _resultado(oportunidade)


@transaction.atomic
def reconciliar_oportunidades_apos_reprogramacao(*, encontro, ator=None):
    if not isinstance(encontro, Encontro) or encontro.pk is None:
        raise ValidationError('Encontro deve estar persistido.')
    oportunidades = list(
        _queryset_oportunidade()
        .select_for_update(of=('self',))
        .filter(
            convite__encontro=encontro,
            status=OportunidadeConviteEncontro.Status.PENDENTE,
        )
        .order_by('pk')
    )
    suspensas = []
    for oportunidade in oportunidades:
        if _suspender_se_inelegivel(
            oportunidade,
            ator=ator,
            origem='interna',
        ):
            suspensas.append(oportunidade)
    return tuple(suspensas)
