from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import (
    ConviteEncontro,
    DiaEncontro,
    Encontro,
    Inscricao,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
)


STATUS_RESPOSTA_CONVITE = {
    ConviteEncontro.Status.CONFIRMADO,
    ConviteEncontro.Status.RECUSADO,
    ConviteEncontro.Status.SEM_RESPOSTA,
}


def _pk(instance, nome):
    if instance is None or instance.pk is None:
        raise ValidationError(f'{nome} deve estar persistido.')
    return instance.pk


def _bloquear_pessoa(pessoa):
    pessoa_id = _pk(pessoa, 'Pessoa')
    try:
        return Pessoa.objects.select_for_update().get(pk=pessoa_id)
    except Pessoa.DoesNotExist as error:
        raise ValidationError('Pessoa não encontrada.') from error


def _bloquear_encontro(encontro):
    encontro_id = _pk(encontro, 'Encontro')
    try:
        return Encontro.objects.select_for_update().get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error


def _bloquear_convite(convite):
    convite_id = _pk(convite, 'Convite')
    try:
        return (
            ConviteEncontro.objects
            .select_for_update()
            .get(pk=convite_id)
        )
    except ConviteEncontro.DoesNotExist as error:
        raise ValidationError('Convite não encontrado.') from error


def _bloquear_inscricao(inscricao):
    inscricao_id = _pk(inscricao, 'Inscrição')
    try:
        return Inscricao.objects.select_for_update().get(pk=inscricao_id)
    except Inscricao.DoesNotExist as error:
        raise ValidationError('Inscrição não encontrada.') from error


def _ano_encontro(encontro):
    data_oficial = (
        DiaEncontro.objects
        .filter(
            calendario__encontro=encontro,
            calendario__vigente=True,
            calendario__oficializado_em__isnull=False,
        )
        .order_by('data', 'pk')
        .values_list('data', flat=True)
        .first()
    )
    return (data_oficial or encontro.data_referencia).year


def _conclusao_escalada(pessoa):
    return (
        ParticipacaoEncontro.objects
        .filter(
            pessoa=pessoa,
            tipo_encontro=Encontro.Tipo.ESCALADA,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
        )
        .select_related('encontro')
        .first()
    )


def _validar_elegibilidade(pessoa, encontro):
    if encontro.tipo not in {
        Encontro.Tipo.AVC,
        Encontro.Tipo.ACAMPAMENTO,
    }:
        return

    conclusao_escalada = _conclusao_escalada(pessoa)
    if conclusao_escalada is None:
        raise ValidationError(
            f'{encontro.get_tipo_display()} exige conclusão anterior de Escalada.'
        )

    if (
        encontro.tipo == Encontro.Tipo.AVC
        and _ano_encontro(encontro)
        < _ano_encontro(conclusao_escalada.encontro) + 2
    ):
        raise ValidationError(
            'AVC só é elegível a partir do ano da Escalada mais dois.'
        )


def _validar_inscricao_do_convite(inscricao, pessoa, encontro, finalidade):
    if inscricao is None:
        return
    if finalidade != ConviteEncontro.Finalidade.PARTICIPAR:
        raise ValidationError(
            'Somente convite para participar pode referenciar inscrição.'
        )
    if inscricao.pessoa_id != pessoa.pk:
        raise ValidationError('Convite e inscrição devem pertencer à mesma Pessoa.')
    if inscricao.status != Inscricao.Status.PENDENTE:
        raise ValidationError('O convite exige uma inscrição pendente.')
    if inscricao.tipo != encontro.tipo:
        raise ValidationError(
            'O tipo da inscrição deve coincidir com o tipo do Encontro.'
        )


def _validar_convite_da_participacao(convite, pessoa, encontro):
    if convite is None:
        return
    if convite.pessoa_id != pessoa.pk or convite.encontro_id != encontro.pk:
        raise ValidationError(
            'Convite, Pessoa e Encontro devem representar o mesmo vínculo.'
        )
    if convite.finalidade != ConviteEncontro.Finalidade.PARTICIPAR:
        raise ValidationError(
            'Resultado de participação não pode usar convite para trabalhar.'
        )


def _traduzir_integridade(mensagem, error):
    raise ValidationError(mensagem) from error


@transaction.atomic
def criar_inscricao(*, pessoa, tipo):
    if tipo not in Inscricao.Tipo.values:
        raise ValidationError('Inscrição permitida somente para Escalada e ESPPA.')

    pessoa_bloqueada = _bloquear_pessoa(pessoa)
    if ParticipacaoEncontro.objects.filter(
        pessoa=pessoa_bloqueada,
        tipo_encontro=tipo,
        resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
    ).exists():
        raise ValidationError('A Pessoa já concluiu este tipo de Encontro.')
    if Inscricao.objects.filter(
        pessoa=pessoa_bloqueada,
        tipo=tipo,
        status=Inscricao.Status.PENDENTE,
    ).exists():
        raise ValidationError(
            'Já existe inscrição pendente para esta Pessoa e tipo.'
        )

    try:
        with transaction.atomic():
            return Inscricao.objects.create(
                pessoa=pessoa_bloqueada,
                tipo=tipo,
            )
    except IntegrityError as error:
        _traduzir_integridade(
            'Já existe inscrição pendente para esta Pessoa e tipo.',
            error,
        )


@transaction.atomic
def criar_convite(
    *,
    pessoa,
    encontro,
    finalidade,
    inscricao=None,
):
    if finalidade not in ConviteEncontro.Finalidade.values:
        raise ValidationError('Finalidade de convite inválida.')

    pessoa_bloqueada = _bloquear_pessoa(pessoa)
    encontro_bloqueado = _bloquear_encontro(encontro)
    convite_existente = (
        ConviteEncontro.objects
        .select_for_update()
        .filter(
            pessoa=pessoa_bloqueada,
            encontro=encontro_bloqueado,
            finalidade=finalidade,
        )
        .first()
    )
    inscricao_bloqueada = (
        _bloquear_inscricao(inscricao) if inscricao is not None else None
    )
    _validar_inscricao_do_convite(
        inscricao_bloqueada,
        pessoa_bloqueada,
        encontro_bloqueado,
        finalidade,
    )

    if finalidade == ConviteEncontro.Finalidade.PARTICIPAR:
        _validar_elegibilidade(pessoa_bloqueada, encontro_bloqueado)

    if convite_existente is not None:
        if convite_existente.inscricao_id == (
            inscricao_bloqueada.pk if inscricao_bloqueada else None
        ):
            return convite_existente
        raise ValidationError(
            'Já existe convite com outra inscrição para esta finalidade.'
        )

    try:
        with transaction.atomic():
            return ConviteEncontro.objects.create(
                pessoa=pessoa_bloqueada,
                encontro=encontro_bloqueado,
                finalidade=finalidade,
                inscricao=inscricao_bloqueada,
            )
    except IntegrityError as error:
        _traduzir_integridade(
            'Já existe convite para esta Pessoa, Encontro e finalidade.',
            error,
        )


@transaction.atomic
def responder_convite(convite, *, status):
    if status not in STATUS_RESPOSTA_CONVITE:
        raise ValidationError('Status de resposta do convite inválido.')

    _bloquear_pessoa(convite.pessoa)
    _bloquear_encontro(convite.encontro)
    convite_bloqueado = _bloquear_convite(convite)
    if convite_bloqueado.inscricao_id is not None:
        _bloquear_inscricao(convite_bloqueado.inscricao)

    if convite_bloqueado.status == status:
        return convite_bloqueado
    if convite_bloqueado.status != ConviteEncontro.Status.CONVIDADO:
        raise ValidationError('O convite já possui uma resposta definitiva.')

    convite_bloqueado.status = status
    convite_bloqueado.save(update_fields=['status', 'atualizado_em'])
    return convite_bloqueado


def _inscricao_da_conclusao(pessoa, encontro, convite):
    if convite is not None and convite.inscricao_id is not None:
        return _bloquear_inscricao(convite.inscricao)
    if encontro.tipo not in Inscricao.Tipo.values:
        return None
    return (
        Inscricao.objects
        .select_for_update()
        .filter(
            pessoa=pessoa,
            tipo=encontro.tipo,
            status=Inscricao.Status.PENDENTE,
        )
        .first()
    )


def _aplicar_conclusao(pessoa, encontro, convite, *, momento):
    if encontro.tipo in {Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA}:
        PerfilAlpinista.objects.get_or_create(pessoa=pessoa)
        inscricao = _inscricao_da_conclusao(pessoa, encontro, convite)
        if inscricao is not None and inscricao.status == Inscricao.Status.PENDENTE:
            inscricao.status = Inscricao.Status.CUMPRIDA
            inscricao.cumprida_em = momento
            inscricao.save(
                update_fields=['status', 'cumprida_em', 'atualizada_em']
            )


@transaction.atomic
def registrar_resultado_participacao(
    *,
    pessoa,
    encontro,
    resultado,
    convite=None,
    momento=None,
):
    if resultado not in ParticipacaoEncontro.Resultado.values:
        raise ValidationError('Resultado de participação inválido.')

    pessoa_bloqueada = _bloquear_pessoa(pessoa)
    encontro_bloqueado = _bloquear_encontro(encontro)
    convite_bloqueado = None
    if convite is not None:
        convite_bloqueado = _bloquear_convite(convite)
        if convite_bloqueado.inscricao_id is not None:
            _bloquear_inscricao(convite_bloqueado.inscricao)
    _validar_convite_da_participacao(
        convite_bloqueado,
        pessoa_bloqueada,
        encontro_bloqueado,
    )
    _validar_elegibilidade(pessoa_bloqueada, encontro_bloqueado)

    participacao = (
        ParticipacaoEncontro.objects
        .select_for_update()
        .filter(
            pessoa=pessoa_bloqueada,
            encontro=encontro_bloqueado,
        )
        .first()
    )
    if participacao is not None:
        if convite_bloqueado is not None and participacao.convite_id not in {
            None,
            convite_bloqueado.pk,
        }:
            raise ValidationError('A participação já está ligada a outro convite.')
        if participacao.resultado == resultado:
            return participacao
        if not (
            participacao.resultado
            in {
                ParticipacaoEncontro.Resultado.FALTOU,
                ParticipacaoEncontro.Resultado.DESISTIU,
            }
            and resultado == ParticipacaoEncontro.Resultado.CONCLUIU
        ):
            raise ValidationError('A participação já possui outro resultado.')

    if resultado == ParticipacaoEncontro.Resultado.CONCLUIU:
        conclusao_existente = ParticipacaoEncontro.objects.filter(
            pessoa=pessoa_bloqueada,
            tipo_encontro=encontro_bloqueado.tipo,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
        )
        if participacao is not None:
            conclusao_existente = conclusao_existente.exclude(pk=participacao.pk)
        if conclusao_existente.exists():
            raise ValidationError('A Pessoa já concluiu este tipo de Encontro.')

    instante = momento or timezone.now()
    try:
        with transaction.atomic():
            if participacao is None:
                participacao = ParticipacaoEncontro.objects.create(
                    pessoa=pessoa_bloqueada,
                    encontro=encontro_bloqueado,
                    convite=convite_bloqueado,
                    resultado=resultado,
                    tipo_encontro=encontro_bloqueado.tipo,
                )
            else:
                participacao.resultado = resultado
                update_fields = ['resultado', 'atualizada_em']
                if participacao.convite_id is None and convite_bloqueado is not None:
                    participacao.convite = convite_bloqueado
                    update_fields.append('convite')
                participacao.save(update_fields=update_fields)

            if resultado == ParticipacaoEncontro.Resultado.CONCLUIU:
                _aplicar_conclusao(
                    pessoa_bloqueada,
                    encontro_bloqueado,
                    convite_bloqueado,
                    momento=instante,
                )
            return participacao
    except IntegrityError as error:
        _traduzir_integridade(
            'Resultado duplicado ou conclusão já registrada.',
            error,
        )
