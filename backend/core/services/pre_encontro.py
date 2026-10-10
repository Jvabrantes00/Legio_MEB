from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    AtendimentoPreEncontro,
    ConferenciaCuidadoPreEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DadosCuidadoInscricao,
    DecisaoVagaPreEncontro,
    Encontro,
    FotoTemporariaPreEncontro,
    InscricaoEncontro,
    PagamentoPreEncontro,
    Pessoa,
    PreEncontro,
)
from core.permissions import (
    pode_aumentar_capacidade_pre_encontro,
    pode_conferir_cuidados_pre_encontro,
    pode_consultar_cuidados_pre_encontro,
    pode_consultar_operacao_pre_encontro,
    pode_operar_checkin_pre_encontro,
    pode_operar_foto_pre_encontro,
    pode_registrar_pagamento_pre_encontro,
    pode_regularizar_pre_encontro,
    pode_resolver_vaga_pre_encontro,
)
from core.services.auditoria_encontros import (
    registrar_evento_auditoria_encontro,
)
from core.services.configuracao_encontristas import (
    alterar_configuracao_encontristas,
)
from core.validators import normalize_cpf


class SituacaoAptidaoPreEncontro(StrEnum):
    APTO = 'apto'
    NAO_APTO = 'nao_apto'
    AGUARDANDO_DECISAO_DIRETORIA = 'aguardando_decisao_diretoria'


@dataclass(frozen=True)
class AptidaoPreEncontro:
    situacao: SituacaoAptidaoPreEncontro
    motivo: str

    @property
    def apto(self):
        return self.situacao == SituacaoAptidaoPreEncontro.APTO


@dataclass(frozen=True)
class CapabilitiesContextoPreEncontro:
    consultar_operacao: bool
    registrar_checkin: bool
    aumentar_capacidade: bool

    def as_dict(self):
        return {
            'consultar_operacao': self.consultar_operacao,
            'registrar_checkin': self.registrar_checkin,
            'aumentar_capacidade': self.aumentar_capacidade,
        }


@dataclass(frozen=True)
class CapabilitiesAtendimentoPreEncontro:
    regularizar: bool
    registrar_pagamento: bool
    consultar_cuidados: bool
    conferir_cuidados: bool
    visualizar_foto: bool
    alterar_foto: bool
    decidir_vaga: bool

    def as_dict(self):
        return {
            'regularizar': self.regularizar,
            'registrar_pagamento': self.registrar_pagamento,
            'consultar_cuidados': self.consultar_cuidados,
            'conferir_cuidados': self.conferir_cuidados,
            'visualizar_foto': self.visualizar_foto,
            'alterar_foto': self.alterar_foto,
            'decidir_vaga': self.decidir_vaga,
        }


_STATUS_ENCERRADOS = {
    Encontro.Status.CANCELADO,
    Encontro.Status.FINALIZADO,
}


def _lifecycle_permite_operacao(encontro, *, depende_data=False):
    if encontro.status in _STATUS_ENCERRADOS:
        return False
    return not (depende_data and encontro.status == Encontro.Status.ADIADO)


def projetar_capabilities_contexto_pre_encontro(*, usuario, encontro):
    mutavel = _lifecycle_permite_operacao(encontro)
    permite_operacao_datada = _lifecycle_permite_operacao(
        encontro,
        depende_data=True,
    )
    return CapabilitiesContextoPreEncontro(
        consultar_operacao=pode_consultar_operacao_pre_encontro(
            usuario,
            encontro,
        ),
        registrar_checkin=(
            permite_operacao_datada
            and pode_operar_checkin_pre_encontro(usuario, encontro)
        ),
        aumentar_capacidade=(
            mutavel
            and pode_aumentar_capacidade_pre_encontro(usuario, encontro)
        ),
    )


def projetar_capabilities_atendimento_pre_encontro(
    *,
    usuario,
    atendimento,
):
    encontro = atendimento.pre_encontro.encontro
    mutavel = _lifecycle_permite_operacao(encontro)
    permite_operacao_datada = _lifecycle_permite_operacao(
        encontro,
        depende_data=True,
    )
    possui_cuidado = bool(
        atendimento.inscricao_id
        and hasattr(atendimento.inscricao, 'dados_cuidado')
    )
    possui_foto = hasattr(atendimento, 'foto_privada')
    try:
        decisao_pendente = (
            atendimento.decisao_vaga.status
            == DecisaoVagaPreEncontro.Status.AGUARDANDO_DECISAO_DIRETORIA
        )
    except DecisaoVagaPreEncontro.DoesNotExist:
        decisao_pendente = False
    return CapabilitiesAtendimentoPreEncontro(
        regularizar=(
            mutavel
            and (atendimento.pessoa_id is None or atendimento.inscricao_id is None)
            and pode_regularizar_pre_encontro(usuario, encontro)
        ),
        registrar_pagamento=(
            mutavel
            and pode_registrar_pagamento_pre_encontro(usuario, encontro)
        ),
        consultar_cuidados=(
            possui_cuidado
            and pode_consultar_cuidados_pre_encontro(usuario, encontro)
        ),
        conferir_cuidados=(
            mutavel
            and possui_cuidado
            and pode_conferir_cuidados_pre_encontro(usuario, encontro)
        ),
        visualizar_foto=(
            possui_foto
            and pode_operar_foto_pre_encontro(usuario, encontro)
        ),
        alterar_foto=(
            mutavel
            and pode_operar_foto_pre_encontro(usuario, encontro)
        ),
        decidir_vaga=(
            permite_operacao_datada
            and decisao_pendente
            and pode_resolver_vaga_pre_encontro(usuario, encontro)
        ),
    )


def _erro(campo, mensagem):
    raise ValidationError({campo: [mensagem]})


def _pk(instancia, nome):
    if instancia is None or instancia.pk is None:
        raise ValidationError(f'{nome} deve estar persistido.')
    return instancia.pk


def _exigir_permissao(permitido, mensagem):
    if not permitido:
        raise PermissionDenied(mensagem)


def _bloquear_encontro(encontro):
    encontro_id = _pk(encontro, 'Encontro')
    try:
        return (
            Encontro.objects
            .select_for_update(of=('self',))
            .get(pk=encontro_id)
        )
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error


def _bloquear_configuracao(encontro, *, obrigatoria=False):
    configuracao = (
        ConfiguracaoEncontristasEncontro.objects
        .select_for_update(of=('self',))
        .filter(encontro=encontro)
        .first()
    )
    if configuracao is None and obrigatoria:
        _erro('capacidade', 'Configuração de encontristas ausente.')
    return configuracao


def _bloquear_pre_encontro(pre_encontro, encontro):
    pre_encontro_id = _pk(pre_encontro, 'Pré-Encontro')
    try:
        pre_bloqueado = (
            PreEncontro.objects
            .select_for_update(of=('self',))
            .get(pk=pre_encontro_id)
        )
    except PreEncontro.DoesNotExist as error:
        raise ValidationError('Pré-Encontro não encontrado.') from error
    if pre_bloqueado.encontro_id != encontro.pk:
        _erro('pre_encontro', 'Pré-Encontro pertence a outro Encontro.')
    return pre_bloqueado


def _bloquear_atendimento(atendimento, encontro):
    atendimento_id = _pk(atendimento, 'Atendimento')
    try:
        atendimento_bloqueado = (
            AtendimentoPreEncontro.objects
            .select_for_update(of=('self',))
            .select_related('pre_encontro')
            .get(pk=atendimento_id)
        )
    except AtendimentoPreEncontro.DoesNotExist as error:
        raise ValidationError('Atendimento não encontrado.') from error
    if atendimento_bloqueado.pre_encontro.encontro_id != encontro.pk:
        _erro('atendimento', 'Atendimento pertence a outro Encontro.')
    return atendimento_bloqueado


def _encontro_do_pre(pre_encontro):
    pre_encontro_id = _pk(pre_encontro, 'Pré-Encontro')
    try:
        return Encontro.objects.get(pre_encontro__pk=pre_encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Pré-Encontro não encontrado.') from error


def _encontro_do_atendimento(atendimento):
    atendimento_id = _pk(atendimento, 'Atendimento')
    try:
        return Encontro.objects.get(
            pre_encontro__atendimentos__pk=atendimento_id,
        )
    except Encontro.DoesNotExist as error:
        raise ValidationError('Atendimento não encontrado.') from error


def _exigir_lifecycle(encontro, *, depende_data=False):
    if encontro.status in _STATUS_ENCERRADOS:
        _erro('encontro', 'O Encontro não aceita novas operações do Pré.')
    if not _lifecycle_permite_operacao(encontro, depende_data=depende_data):
        _erro(
            'encontro',
            'O Encontro adiado precisa ser reprogramado antes desta operação.',
        )


def _validar_inscricao_encontro(inscricao, encontro):
    if inscricao is None:
        return None
    inscricao_id = _pk(inscricao, 'Inscrição')
    try:
        inscricao_bloqueada = (
            InscricaoEncontro.objects
            .select_for_update(of=('self',))
            .get(pk=inscricao_id)
        )
    except InscricaoEncontro.DoesNotExist as error:
        raise ValidationError('Inscrição não encontrada.') from error
    if inscricao_bloqueada.encontro_id != encontro.pk:
        _erro('inscricao', 'Inscrição pertence a outro Encontro.')
    return inscricao_bloqueada


def _bloquear_pessoa(pessoa):
    if pessoa is None:
        return None
    pessoa_id = _pk(pessoa, 'Pessoa')
    try:
        return Pessoa.objects.select_for_update().get(pk=pessoa_id)
    except Pessoa.DoesNotExist as error:
        raise ValidationError('Pessoa não encontrada.') from error


def _pessoa_id_atendimento(atendimento):
    if atendimento.pessoa_id is not None:
        return atendimento.pessoa_id
    if atendimento.inscricao_id is not None:
        return atendimento.inscricao.pessoa_id
    return None


def _identidade_regularizada(atendimento):
    if atendimento.pessoa_id is not None:
        return True
    return bool(
        atendimento.inscricao_id is not None
        and atendimento.inscricao.status == InscricaoEncontro.Status.ENVIADA
        and atendimento.inscricao.encontro_id
        == atendimento.pre_encontro.encontro_id
    )


def _pessoas_confirmadas(encontro):
    return set(
        ConviteEncontro.objects.filter(
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        ).values_list('pessoa_id', flat=True)
    )


def _atendimentos_do_pre_bloqueados(encontro):
    return list(
        AtendimentoPreEncontro.objects
        .select_for_update(of=('self',))
        .filter(pre_encontro__encontro=encontro)
        .select_related('pre_encontro', 'inscricao', 'pessoa', 'decisao_vaga')
        .order_by('pk')
    )


def _candidatos_nao_confirmados(atendimentos, confirmados):
    candidatos = []
    for atendimento in atendimentos:
        if not _identidade_regularizada(atendimento):
            continue
        pessoa_id = _pessoa_id_atendimento(atendimento)
        if pessoa_id is not None and pessoa_id in confirmados:
            continue
        candidatos.append(atendimento)
    return candidatos


def _decisao(atendimento):
    try:
        return atendimento.decisao_vaga
    except DecisaoVagaPreEncontro.DoesNotExist:
        return None


def _recalcular_disputa_bloqueada(encontro, configuracao):
    if configuracao is None or encontro.status == Encontro.Status.ADIADO:
        return
    atendimentos = _atendimentos_do_pre_bloqueados(encontro)
    confirmados = _pessoas_confirmadas(encontro)
    candidatos = _candidatos_nao_confirmados(atendimentos, confirmados)
    aprovados = [
        atendimento
        for atendimento in candidatos
        if (
            _decisao(atendimento) is not None
            and _decisao(atendimento).status
            == DecisaoVagaPreEncontro.Status.APROVADO
        )
    ]
    indefinidos = [
        atendimento
        for atendimento in candidatos
        if (
            _decisao(atendimento) is None
            or _decisao(atendimento).status
            == DecisaoVagaPreEncontro.Status.AGUARDANDO_DECISAO_DIRETORIA
        )
    ]
    vagas_restantes = max(
        configuracao.capacidade - len(confirmados) - len(aprovados),
        0,
    )
    if len(indefinidos) <= vagas_restantes:
        DecisaoVagaPreEncontro.objects.filter(
            atendimento__in=indefinidos,
            status=(
                DecisaoVagaPreEncontro.Status.AGUARDANDO_DECISAO_DIRETORIA
            ),
        ).delete()
        return
    for atendimento in indefinidos:
        DecisaoVagaPreEncontro.objects.get_or_create(
            atendimento=atendimento,
            defaults={
                'status': (
                    DecisaoVagaPreEncontro.Status
                    .AGUARDANDO_DECISAO_DIRETORIA
                ),
            },
        )


def _auditar(
    *,
    encontro,
    usuario,
    fato,
    entidade,
    objeto_id,
    anterior,
    novo,
    campos,
    justificativa='',
):
    registrar_evento_auditoria_encontro(
        encontro=encontro,
        ator=usuario,
        fato=fato,
        entidade=entidade,
        objeto_id=objeto_id,
        valor_anterior=anterior,
        valor_novo=novo,
        campos_permitidos=campos,
        justificativa=justificativa,
    )


@transaction.atomic
def registrar_checkin_pre_encontro(
    *,
    usuario,
    pre_encontro,
    inscricao=None,
    pessoa=None,
    nome_informado='',
    data_nascimento_informada=None,
    cpf_informado=None,
    telefone_informado='',
    observacoes='',
    momento=None,
):
    encontro = _encontro_do_pre(pre_encontro)
    _exigir_permissao(
        pode_operar_checkin_pre_encontro(usuario, encontro),
        'Seu usuário não pode registrar check-in neste Pré-Encontro.',
    )
    encontro = _bloquear_encontro(encontro)
    _exigir_lifecycle(encontro, depende_data=True)
    configuracao = _bloquear_configuracao(encontro)
    pre_encontro = _bloquear_pre_encontro(pre_encontro, encontro)
    inscricao = _validar_inscricao_encontro(inscricao, encontro)
    pessoa = _bloquear_pessoa(pessoa)
    if (
        inscricao is not None
        and inscricao.pessoa_id is not None
        and pessoa is not None
        and inscricao.pessoa_id != pessoa.pk
    ):
        _erro('pessoa', 'Pessoa diverge da Pessoa resolvida na inscrição.')
    cpf_informado = normalize_cpf(cpf_informado)

    existentes = set()
    if inscricao is not None:
        existentes.update(
            AtendimentoPreEncontro.objects.filter(
                pre_encontro=pre_encontro,
                inscricao=inscricao,
            ).values_list('pk', flat=True)
        )
    if pessoa is not None:
        existentes.update(
            AtendimentoPreEncontro.objects.filter(
                pre_encontro=pre_encontro,
                pessoa=pessoa,
            ).values_list('pk', flat=True)
        )
    pessoa_efetiva_id = (
        pessoa.pk
        if pessoa is not None
        else inscricao.pessoa_id if inscricao is not None else None
    )
    if pessoa_efetiva_id is not None:
        existentes.update(
            AtendimentoPreEncontro.objects.filter(
                Q(pessoa_id=pessoa_efetiva_id)
                | Q(inscricao__pessoa_id=pessoa_efetiva_id),
                pre_encontro=pre_encontro,
            ).values_list('pk', flat=True)
        )
    if cpf_informado:
        existentes.update(
            AtendimentoPreEncontro.objects.filter(
                pre_encontro=pre_encontro,
                cpf_informado=cpf_informado,
            ).values_list('pk', flat=True)
        )
    if len(existentes) > 1:
        _erro('atendimento', 'Os identificadores apontam atendimentos distintos.')
    if existentes:
        atendimento = (
            AtendimentoPreEncontro.objects
            .select_for_update(of=('self',))
            .get(pk=existentes.pop())
        )
        _recalcular_disputa_bloqueada(encontro, configuracao)
        return atendimento

    atendimento = AtendimentoPreEncontro(
        pre_encontro=pre_encontro,
        inscricao=inscricao,
        pessoa=pessoa,
        nome_informado=nome_informado,
        data_nascimento_informada=data_nascimento_informada,
        cpf_informado=cpf_informado,
        telefone_informado=telefone_informado,
        registrado_por=usuario,
        registrado_em=momento or timezone.now(),
        observacoes=observacoes,
    )
    atendimento.full_clean()
    try:
        atendimento.save()
    except IntegrityError as error:
        raise ValidationError(
            'Não foi possível registrar o check-in sem duplicidade.',
        ) from error
    _auditar(
        encontro=encontro,
        usuario=usuario,
        fato='pre_encontro.checkin_registrado',
        entidade='atendimento_pre_encontro',
        objeto_id=atendimento.pk,
        anterior={},
        novo={
            'inscricao_vinculada': inscricao is not None,
            'pessoa_vinculada': pessoa is not None,
            'origem_avulsa': inscricao is None and pessoa is None,
        },
        campos={
            'inscricao_vinculada',
            'pessoa_vinculada',
            'origem_avulsa',
        },
    )
    _recalcular_disputa_bloqueada(encontro, configuracao)
    return atendimento


@transaction.atomic
def regularizar_atendimento_pre_encontro(
    *,
    usuario,
    atendimento,
    pessoa=None,
    inscricao=None,
):
    encontro = _encontro_do_atendimento(atendimento)
    _exigir_permissao(
        pode_regularizar_pre_encontro(usuario, encontro),
        'Seu usuário não pode regularizar este atendimento.',
    )
    encontro = _bloquear_encontro(encontro)
    _exigir_lifecycle(encontro)
    configuracao = _bloquear_configuracao(encontro)
    atendimento = _bloquear_atendimento(atendimento, encontro)
    pessoa = _bloquear_pessoa(pessoa) if pessoa is not None else atendimento.pessoa
    inscricao = (
        _validar_inscricao_encontro(inscricao, encontro)
        if inscricao is not None
        else atendimento.inscricao
    )
    if pessoa is None and inscricao is None:
        _erro('atendimento', 'Informe Pessoa ou inscrição para regularizar.')
    if (
        pessoa is not None
        and inscricao is not None
        and inscricao.pessoa_id is not None
        and inscricao.pessoa_id != pessoa.pk
    ):
        _erro('pessoa', 'Pessoa diverge da Pessoa resolvida na inscrição.')
    pessoa_efetiva_id = (
        pessoa.pk
        if pessoa is not None
        else inscricao.pessoa_id if inscricao is not None else None
    )
    if pessoa_efetiva_id is not None and (
        AtendimentoPreEncontro.objects
        .filter(
            Q(pessoa_id=pessoa_efetiva_id)
            | Q(inscricao__pessoa_id=pessoa_efetiva_id),
            pre_encontro=atendimento.pre_encontro,
        )
        .exclude(pk=atendimento.pk)
        .exists()
    ):
        _erro('pessoa', 'Pessoa já possui atendimento neste Pré-Encontro.')
    anterior = {
        'pessoa_id': atendimento.pessoa_id,
        'inscricao_id': atendimento.inscricao_id,
    }
    atendimento.pessoa = pessoa
    atendimento.inscricao = inscricao
    novo = {
        'pessoa_id': atendimento.pessoa_id,
        'inscricao_id': atendimento.inscricao_id,
    }
    if novo == anterior:
        return atendimento
    atendimento.full_clean()
    try:
        atendimento.save(
            update_fields=['pessoa', 'inscricao', 'atualizado_em'],
        )
    except IntegrityError as error:
        raise ValidationError(
            'A regularização conflita com outro atendimento.',
        ) from error
    _auditar(
        encontro=encontro,
        usuario=usuario,
        fato='pre_encontro.atendimento_regularizado',
        entidade='atendimento_pre_encontro',
        objeto_id=atendimento.pk,
        anterior=anterior,
        novo=novo,
        campos={'pessoa_id', 'inscricao_id'},
    )
    _recalcular_disputa_bloqueada(encontro, configuracao)
    return atendimento


@transaction.atomic
def registrar_pagamento_pre_encontro(
    *,
    usuario,
    atendimento,
    status,
    valor=None,
    forma='',
    pago_em=None,
    observacao='',
):
    encontro = _encontro_do_atendimento(atendimento)
    _exigir_permissao(
        pode_registrar_pagamento_pre_encontro(usuario, encontro),
        'Seu usuário não pode registrar pagamento neste Pré-Encontro.',
    )
    encontro = _bloquear_encontro(encontro)
    _exigir_lifecycle(encontro)
    atendimento = _bloquear_atendimento(atendimento, encontro)
    pagamento = (
        PagamentoPreEncontro.objects
        .select_for_update(of=('self',))
        .filter(atendimento=atendimento)
        .first()
    )
    anterior = {}
    if pagamento is None:
        pagamento = PagamentoPreEncontro(atendimento=atendimento)
        observacao_anterior = ''
    else:
        observacao_anterior = pagamento.observacao
        anterior = {
            'status': pagamento.status,
            'forma': pagamento.forma,
            'valor_informado': pagamento.valor is not None,
            'pago_em_informado': pagamento.pago_em is not None,
        }
    pagamento.status = status
    pagamento.valor = valor
    pagamento.forma = forma
    pagamento.pago_em = pago_em
    pagamento.observacao = observacao
    novo = {
        'status': pagamento.status,
        'forma': pagamento.forma,
        'valor_informado': pagamento.valor is not None,
        'pago_em_informado': pagamento.pago_em is not None,
    }
    if pagamento.pk and novo == anterior and observacao_anterior == observacao:
        return pagamento
    pagamento.full_clean()
    try:
        pagamento.save()
    except IntegrityError as error:
        raise ValidationError('Pagamento duplicado para o atendimento.') from error
    _auditar(
        encontro=encontro,
        usuario=usuario,
        fato='pre_encontro.pagamento_registrado',
        entidade='pagamento_pre_encontro',
        objeto_id=pagamento.pk,
        anterior=anterior,
        novo=novo,
        campos={'status', 'forma', 'valor_informado', 'pago_em_informado'},
    )
    return pagamento


@transaction.atomic
def conferir_cuidados_pre_encontro(
    *,
    usuario,
    atendimento,
    dados_cuidado,
    momento=None,
):
    encontro = _encontro_do_atendimento(atendimento)
    _exigir_permissao(
        pode_conferir_cuidados_pre_encontro(usuario, encontro),
        'Seu usuário não pode conferir cuidados neste Pré-Encontro.',
    )
    encontro = _bloquear_encontro(encontro)
    _exigir_lifecycle(encontro)
    atendimento = _bloquear_atendimento(atendimento, encontro)
    dados_id = _pk(dados_cuidado, 'Dados de cuidado')
    try:
        dados_cuidado = (
            DadosCuidadoInscricao.objects
            .select_for_update(of=('self',))
            .get(pk=dados_id)
        )
    except DadosCuidadoInscricao.DoesNotExist as error:
        raise ValidationError('Dados de cuidado não encontrados.') from error
    if atendimento.inscricao_id != dados_cuidado.inscricao_id:
        _erro(
            'dados_cuidado',
            'Dados de cuidado pertencem a outra inscrição.',
        )
    conferencia = (
        ConferenciaCuidadoPreEncontro.objects
        .select_for_update(of=('self',))
        .filter(atendimento=atendimento)
        .first()
    )
    anterior = {}
    if conferencia is None:
        conferencia = ConferenciaCuidadoPreEncontro(
            atendimento=atendimento,
        )
    else:
        anterior = {
            'conferido_por_id': conferencia.conferido_por_id,
            'conferido_em': conferencia.conferido_em.isoformat(),
            'dados_cuidado_atualizado_em': (
                conferencia.dados_cuidado_atualizado_em.isoformat()
            ),
        }
    conferencia.dados_cuidado = dados_cuidado
    conferencia.conferido_por = usuario
    conferencia.conferido_em = momento or timezone.now()
    conferencia.dados_cuidado_atualizado_em = dados_cuidado.atualizado_em
    conferencia.full_clean()
    try:
        conferencia.save()
    except IntegrityError as error:
        raise ValidationError(
            'Conferência duplicada para o atendimento.',
        ) from error
    novo = {
        'conferido_por_id': conferencia.conferido_por_id,
        'conferido_em': conferencia.conferido_em.isoformat(),
        'dados_cuidado_atualizado_em': (
            conferencia.dados_cuidado_atualizado_em.isoformat()
        ),
    }
    _auditar(
        encontro=encontro,
        usuario=usuario,
        fato='pre_encontro.cuidados_conferidos',
        entidade='conferencia_cuidado_pre_encontro',
        objeto_id=conferencia.pk,
        anterior=anterior,
        novo=novo,
        campos={
            'conferido_por_id',
            'conferido_em',
            'dados_cuidado_atualizado_em',
        },
    )
    return conferencia


def avaliar_aptidao_pre_encontro(atendimento):
    atendimento_id = _pk(atendimento, 'Atendimento')
    try:
        atendimento = (
            AtendimentoPreEncontro.objects
            .select_related(
                'pre_encontro',
                'pre_encontro__encontro',
                'inscricao',
                'pessoa',
                'decisao_vaga',
            )
            .get(pk=atendimento_id)
        )
    except AtendimentoPreEncontro.DoesNotExist as error:
        raise ValidationError('Atendimento não encontrado.') from error
    encontro = atendimento.pre_encontro.encontro
    if not _identidade_regularizada(atendimento):
        return AptidaoPreEncontro(
            SituacaoAptidaoPreEncontro.NAO_APTO,
            'identidade_nao_regularizada',
        )
    decisao = _decisao(atendimento)
    if decisao is not None:
        if decisao.status == DecisaoVagaPreEncontro.Status.NAO_APROVADO:
            return AptidaoPreEncontro(
                SituacaoAptidaoPreEncontro.NAO_APTO,
                'vaga_nao_aprovada',
            )
        if (
            decisao.status
            == DecisaoVagaPreEncontro.Status.AGUARDANDO_DECISAO_DIRETORIA
        ):
            return AptidaoPreEncontro(
                SituacaoAptidaoPreEncontro.AGUARDANDO_DECISAO_DIRETORIA,
                'disputa_de_vaga',
            )
        if decisao.status == DecisaoVagaPreEncontro.Status.APROVADO:
            return AptidaoPreEncontro(
                SituacaoAptidaoPreEncontro.APTO,
                'vaga_aprovada_pela_diretoria',
            )
    pessoa_id = _pessoa_id_atendimento(atendimento)
    if pessoa_id in _pessoas_confirmadas(encontro):
        return AptidaoPreEncontro(
            SituacaoAptidaoPreEncontro.APTO,
            'vaga_confirmada',
        )
    configuracao = ConfiguracaoEncontristasEncontro.objects.filter(
        encontro=encontro,
    ).first()
    if configuracao is None:
        return AptidaoPreEncontro(
            SituacaoAptidaoPreEncontro.NAO_APTO,
            'capacidade_nao_configurada',
        )
    confirmados = _pessoas_confirmadas(encontro)
    atendimentos = list(
        AtendimentoPreEncontro.objects
        .filter(pre_encontro__encontro=encontro)
        .select_related('pre_encontro', 'inscricao', 'pessoa', 'decisao_vaga')
    )
    candidatos = _candidatos_nao_confirmados(atendimentos, confirmados)
    aprovados = sum(
        1
        for candidato in candidatos
        if (
            _decisao(candidato) is not None
            and _decisao(candidato).status
            == DecisaoVagaPreEncontro.Status.APROVADO
        )
    )
    indefinidos = sum(
        1 for candidato in candidatos if _decisao(candidato) is None
    )
    if len(confirmados) + aprovados + indefinidos <= configuracao.capacidade:
        return AptidaoPreEncontro(
            SituacaoAptidaoPreEncontro.APTO,
            'capacidade_ordinaria',
        )
    return AptidaoPreEncontro(
        SituacaoAptidaoPreEncontro.AGUARDANDO_DECISAO_DIRETORIA,
        'disputa_de_vaga',
    )


@transaction.atomic
def resolver_vaga_pre_encontro(
    *,
    usuario,
    atendimento,
    status,
    justificativa='',
    momento=None,
):
    if status not in {
        DecisaoVagaPreEncontro.Status.APROVADO,
        DecisaoVagaPreEncontro.Status.NAO_APROVADO,
    }:
        _erro('status', 'Resultado de decisão de vaga inválido.')
    encontro = _encontro_do_atendimento(atendimento)
    _exigir_permissao(
        pode_resolver_vaga_pre_encontro(usuario, encontro),
        'Somente a Diretoria pode resolver a disputa de vaga.',
    )
    encontro = _bloquear_encontro(encontro)
    _exigir_lifecycle(encontro, depende_data=True)
    configuracao = _bloquear_configuracao(encontro, obrigatoria=True)
    atendimento = _bloquear_atendimento(atendimento, encontro)
    decisao = (
        DecisaoVagaPreEncontro.objects
        .select_for_update(of=('self',))
        .filter(atendimento=atendimento)
        .first()
    )
    if decisao is None:
        _erro('decisao', 'Atendimento não possui disputa de vaga pendente.')
    if decisao.status == status:
        return decisao
    if (
        decisao.status
        != DecisaoVagaPreEncontro.Status.AGUARDANDO_DECISAO_DIRETORIA
    ):
        _erro('decisao', 'A disputa já possui decisão definitiva.')
    if status == DecisaoVagaPreEncontro.Status.APROVADO:
        confirmados = len(_pessoas_confirmadas(encontro))
        aprovados = DecisaoVagaPreEncontro.objects.filter(
            atendimento__pre_encontro__encontro=encontro,
            status=DecisaoVagaPreEncontro.Status.APROVADO,
        ).count()
        if confirmados + aprovados >= configuracao.capacidade:
            _erro('capacidade', 'Não existe vaga disponível para aprovação.')
    anterior = {'status': decisao.status}
    decisao.status = status
    decisao.decidida_por = usuario
    decisao.decidida_em = momento or timezone.now()
    decisao.justificativa = justificativa
    decisao.full_clean()
    decisao.save(
        update_fields=[
            'status',
            'decidida_por',
            'decidida_em',
            'justificativa',
            'atualizado_em',
        ],
    )
    _auditar(
        encontro=encontro,
        usuario=usuario,
        fato='pre_encontro.vaga_resolvida',
        entidade='decisao_vaga_pre_encontro',
        objeto_id=decisao.pk,
        anterior=anterior,
        novo={'status': decisao.status},
        campos={'status'},
        justificativa=justificativa,
    )
    _recalcular_disputa_bloqueada(encontro, configuracao)
    return decisao


@transaction.atomic
def aumentar_capacidade_pre_encontro(
    *,
    usuario,
    configuracao,
    capacidade,
    justificativa='',
):
    configuracao_id = _pk(configuracao, 'Configuração')
    try:
        referencia = ConfiguracaoEncontristasEncontro.objects.get(
            pk=configuracao_id,
        )
    except ConfiguracaoEncontristasEncontro.DoesNotExist as error:
        raise ValidationError('Configuração não encontrada.') from error
    encontro = referencia.encontro
    _exigir_permissao(
        pode_aumentar_capacidade_pre_encontro(usuario, encontro),
        'Seu usuário não pode aumentar a capacidade do Pré-Encontro.',
    )
    encontro = _bloquear_encontro(encontro)
    _exigir_lifecycle(encontro)
    configuracao_bloqueada = _bloquear_configuracao(
        encontro,
        obrigatoria=True,
    )
    if capacidade <= configuracao_bloqueada.capacidade:
        _erro('capacidade', 'Informe uma capacidade maior que a atual.')
    configuracao_atualizada = alterar_configuracao_encontristas(
        usuario=usuario,
        configuracao=configuracao_bloqueada,
        capacidade=capacidade,
        justificativa=justificativa,
    )
    _recalcular_disputa_bloqueada(encontro, configuracao_atualizada)
    return configuracao_atualizada


@transaction.atomic
def registrar_foto_pre_encontro(*, usuario, atendimento, arquivo):
    encontro = _encontro_do_atendimento(atendimento)
    _exigir_permissao(
        pode_operar_foto_pre_encontro(usuario, encontro),
        'Seu usuário não pode operar a foto deste Pré-Encontro.',
    )
    encontro = _bloquear_encontro(encontro)
    _exigir_lifecycle(encontro)
    atendimento = _bloquear_atendimento(atendimento, encontro)
    foto = (
        FotoTemporariaPreEncontro.objects
        .select_for_update(of=('self',))
        .filter(atendimento=atendimento)
        .first()
    )
    nome_anterior = foto.arquivo.name if foto is not None else ''
    storage_anterior = foto.arquivo.storage if foto is not None else None
    if foto is None:
        foto = FotoTemporariaPreEncontro(atendimento=atendimento)

    arquivo.seek(0)
    conteudo = arquivo.read()
    arquivo.seek(0)
    foto.arquivo = arquivo
    foto.nome_original = arquivo.name[:255]
    foto.content_type = getattr(arquivo, 'content_type', '')[:100]
    foto.tamanho = arquivo.size
    foto.sha256 = sha256(conteudo).hexdigest()
    foto.full_clean()
    foto.save()

    if nome_anterior and nome_anterior != foto.arquivo.name:
        transaction.on_commit(
            lambda: storage_anterior.delete(nome_anterior),
        )
    _auditar(
        encontro=encontro,
        usuario=usuario,
        fato='pre_encontro.foto_registrada',
        entidade='foto_temporaria_pre_encontro',
        objeto_id=foto.pk,
        anterior={'foto_existente': bool(nome_anterior)},
        novo={'foto_existente': True},
        campos={'foto_existente'},
    )
    return foto
