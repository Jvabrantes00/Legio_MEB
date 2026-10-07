from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from core.models import AvaliacaoEncontro, Encontro


def _bloquear_encontro(encontro):
    if encontro is None or encontro.pk is None:
        raise ValidationError('Encontro deve estar persistido.')
    try:
        return Encontro.objects.select_for_update().get(pk=encontro.pk)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error


@transaction.atomic
def criar_avaliacao_encontro(*, encontro, data):
    encontro_bloqueado = _bloquear_encontro(encontro)
    try:
        with transaction.atomic():
            return AvaliacaoEncontro.objects.create(
                encontro=encontro_bloqueado,
                data=data,
            )
    except IntegrityError as error:
        raise ValidationError(
            'O Encontro já possui uma avaliação de agenda.'
        ) from error


@transaction.atomic
def editar_avaliacao_encontro(avaliacao, *, data):
    encontro_bloqueado = _bloquear_encontro(avaliacao.encontro)
    try:
        avaliacao_bloqueada = (
            AvaliacaoEncontro.objects
            .select_for_update()
            .get(pk=avaliacao.pk, encontro=encontro_bloqueado)
        )
    except AvaliacaoEncontro.DoesNotExist as error:
        raise ValidationError('Avaliação do Encontro não encontrada.') from error
    avaliacao_bloqueada.data = data
    avaliacao_bloqueada.save(update_fields=['data', 'atualizado_em'])
    return avaliacao_bloqueada


@transaction.atomic
def remover_avaliacao_encontro(avaliacao):
    encontro_bloqueado = _bloquear_encontro(avaliacao.encontro)
    try:
        avaliacao_bloqueada = (
            AvaliacaoEncontro.objects
            .select_for_update()
            .get(pk=avaliacao.pk, encontro=encontro_bloqueado)
        )
    except AvaliacaoEncontro.DoesNotExist as error:
        raise ValidationError('Avaliação do Encontro não encontrada.') from error
    avaliacao_bloqueada.delete()
