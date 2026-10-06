from dataclasses import dataclass
from enum import Enum

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import (
    Encontro,
    ItemPropostaVioleiros,
    PerfilAlpinista,
    Pessoa,
    PropostaVioleiros,
    TrabalhoEncontro,
)
from core.services.elegibilidade_trabalho import avaliar_elegibilidade_trabalho


CODIGO_EQUIPE_VIOLEIROS = 'violeiros'
TOTAL_POSICOES = 5


class SituacaoItemProposta(str, Enum):
    DISPONIVEL = 'DISPONIVEL'
    APROVEITADO_VIOLEIROS = 'APROVEITADO_VIOLEIROS'
    INDISPONIVEL_OUTRA_EQUIPE = 'INDISPONIVEL_OUTRA_EQUIPE'
    INDISPONIVEL_MME = 'INDISPONIVEL_MME'
    HISTORICO = 'HISTORICO'


@dataclass(frozen=True)
class ResultadoItemProposta:
    item: ItemPropostaVioleiros
    situacao: SituacaoItemProposta
    avaliacao_elegibilidade: object | None = None
    trabalho: TrabalhoEncontro | None = None

    @property
    def disponivel(self):
        return self.situacao == SituacaoItemProposta.DISPONIVEL


@dataclass(frozen=True)
class ResumoPropostaVioleiros:
    proposta: PropostaVioleiros
    itens: tuple[ResultadoItemProposta, ...]
    total_posicoes: int = TOTAL_POSICOES

    @property
    def total_disponivel(self):
        return sum(resultado.disponivel for resultado in self.itens)

    @property
    def vagas_disponiveis(self):
        return self.total_posicoes - self.total_disponivel

    @property
    def completa(self):
        return self.total_disponivel == self.total_posicoes

    @property
    def precisa_completar(self):
        return not self.completa


def _pk(instancia, nome):
    if instancia is None or instancia.pk is None:
        raise ValidationError(f'{nome} deve estar persistido.')
    return instancia.pk


def _bloquear_encontro(encontro):
    encontro_id = _pk(encontro, 'Encontro')
    try:
        return Encontro.objects.select_for_update().get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error


def _encontro_id_da_proposta(proposta_id):
    try:
        return PropostaVioleiros.objects.values_list(
            'encontro_id',
            flat=True,
        ).get(pk=proposta_id)
    except PropostaVioleiros.DoesNotExist as error:
        raise ValidationError('Proposta de Violeiros não encontrada.') from error


def _bloquear_proposta(proposta, encontro):
    proposta_id = _pk(proposta, 'Proposta de Violeiros')
    try:
        return (
            PropostaVioleiros.objects
            .select_for_update()
            .select_related('encontro')
            .get(pk=proposta_id, encontro=encontro)
        )
    except PropostaVioleiros.DoesNotExist as error:
        raise ValidationError('Proposta de Violeiros não encontrada.') from error


def _bloquear_contexto_proposta(proposta):
    proposta_id = _pk(proposta, 'Proposta de Violeiros')
    encontro_id = _encontro_id_da_proposta(proposta_id)
    try:
        encontro = Encontro.objects.select_for_update().get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error
    return _bloquear_proposta(proposta, encontro), encontro


def _bloquear_perfil_e_pessoa(perfil):
    perfil_id = _pk(perfil, 'PerfilAlpinista')
    try:
        pessoa_id = PerfilAlpinista.objects.values_list(
            'pessoa_id',
            flat=True,
        ).get(pk=perfil_id)
    except PerfilAlpinista.DoesNotExist as error:
        raise ValidationError('PerfilAlpinista não encontrado.') from error
    try:
        pessoa = Pessoa.objects.select_for_update().get(pk=pessoa_id)
        perfil_bloqueado = (
            PerfilAlpinista.objects
            .select_for_update()
            .select_related('pessoa')
            .get(pk=perfil_id, pessoa=pessoa)
        )
    except (Pessoa.DoesNotExist, PerfilAlpinista.DoesNotExist) as error:
        raise ValidationError('PerfilAlpinista não encontrado.') from error
    return perfil_bloqueado, pessoa


def _validar_aberta(proposta):
    if proposta.status != PropostaVioleiros.Status.ABERTA:
        raise ValidationError('A proposta de Violeiros está encerrada.')


def _validar_slot(papel_sugerido, posicao):
    valido = (
        papel_sugerido
        == ItemPropostaVioleiros.PapelSugerido.COORDENADOR
        and posicao == 1
    ) or (
        papel_sugerido
        == ItemPropostaVioleiros.PapelSugerido.INTEGRANTE
        and posicao in range(1, 5)
    )
    if not valido:
        raise ValidationError('Papel e posição não formam um slot válido.')


def _trabalho_oficial(pessoa, encontro, *, bloquear=False):
    trabalhos = (
        TrabalhoEncontro.objects
        .select_related('role_equipe__equipe_encontro')
        .filter(
            pessoa=pessoa,
            encontro=encontro,
            role_equipe__isnull=False,
            status__in=(
                TrabalhoEncontro.Status.ALOCADO,
                TrabalhoEncontro.Status.TRABALHOU,
                TrabalhoEncontro.Status.FALTOU,
            ),
        )
    )
    if bloquear:
        trabalhos = trabalhos.select_for_update(of=('self',))
    return trabalhos.first()


def _avaliar_candidato(perfil, encontro, *, bloquear_trabalho=False):
    trabalho = _trabalho_oficial(
        perfil.pessoa,
        encontro,
        bloquear=bloquear_trabalho,
    )
    if trabalho is not None:
        equipe_codigo = trabalho.role_equipe.equipe_encontro.codigo
        situacao = (
            SituacaoItemProposta.APROVEITADO_VIOLEIROS
            if equipe_codigo == CODIGO_EQUIPE_VIOLEIROS
            else SituacaoItemProposta.INDISPONIVEL_OUTRA_EQUIPE
        )
        return situacao, None, trabalho

    avaliacao = avaliar_elegibilidade_trabalho(perfil.pessoa, encontro)
    if not (perfil.violeiro and perfil.disponivel_mme):
        return SituacaoItemProposta.INDISPONIVEL_MME, avaliacao, None
    if avaliacao.bloqueios:
        return SituacaoItemProposta.INDISPONIVEL_MME, avaliacao, None
    return SituacaoItemProposta.DISPONIVEL, avaliacao, None


def _validar_candidato_disponivel(perfil, encontro):
    situacao, avaliacao, _ = _avaliar_candidato(
        perfil,
        encontro,
        bloquear_trabalho=True,
    )
    if situacao != SituacaoItemProposta.DISPONIVEL:
        raise ValidationError(
            'O candidato não está disponível para esta proposta de Violeiros.'
        )
    return avaliacao


def _criar_item(
    *,
    proposta,
    perfil,
    papel_sugerido,
    posicao,
    avaliacao,
):
    try:
        with transaction.atomic():
            item = ItemPropostaVioleiros.objects.create(
                proposta=proposta,
                perfil_alpinista=perfil,
                papel_sugerido=papel_sugerido,
                posicao=posicao,
            )
    except IntegrityError as error:
        raise ValidationError(
            'O slot ou o candidato já possui uma ocupação vigente.'
        ) from error
    item.avaliacao_elegibilidade = avaliacao
    return item


@transaction.atomic
def criar_proposta_violeiros(*, encontro, nome=''):
    encontro_bloqueado = _bloquear_encontro(encontro)
    return PropostaVioleiros.objects.create(
        encontro=encontro_bloqueado,
        nome=nome,
    )


@transaction.atomic
def editar_proposta_violeiros(proposta, *, nome):
    proposta_bloqueada, _ = _bloquear_contexto_proposta(proposta)
    _validar_aberta(proposta_bloqueada)
    if proposta_bloqueada.nome == nome:
        return proposta_bloqueada
    proposta_bloqueada.nome = nome
    proposta_bloqueada.save(update_fields=['nome', 'atualizada_em'])
    return proposta_bloqueada


@transaction.atomic
def preencher_posicao_proposta(
    proposta,
    *,
    perfil_alpinista,
    papel_sugerido,
    posicao,
):
    _validar_slot(papel_sugerido, posicao)
    perfil_bloqueado, _ = _bloquear_perfil_e_pessoa(perfil_alpinista)
    proposta_id = _pk(proposta, 'Proposta de Violeiros')
    encontro_id = _encontro_id_da_proposta(proposta_id)
    try:
        encontro_bloqueado = (
            Encontro.objects.select_for_update().get(pk=encontro_id)
        )
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error
    proposta_bloqueada = _bloquear_proposta(proposta, encontro_bloqueado)
    _validar_aberta(proposta_bloqueada)

    itens_vigentes = list(
        ItemPropostaVioleiros.objects
        .select_for_update()
        .filter(proposta=proposta_bloqueada, vigente=True)
        .order_by('pk')
    )
    if any(
        item.perfil_alpinista_id == perfil_bloqueado.pk
        for item in itens_vigentes
    ):
        raise ValidationError('O candidato já está vigente nesta proposta.')
    if any(
        item.papel_sugerido == papel_sugerido and item.posicao == posicao
        for item in itens_vigentes
    ):
        raise ValidationError('O slot já possui uma ocupação vigente.')

    avaliacao = _validar_candidato_disponivel(
        perfil_bloqueado,
        encontro_bloqueado,
    )
    return _criar_item(
        proposta=proposta_bloqueada,
        perfil=perfil_bloqueado,
        papel_sugerido=papel_sugerido,
        posicao=posicao,
        avaliacao=avaliacao,
    )


@transaction.atomic
def substituir_ocupacao_proposta(
    item_atual,
    *,
    perfil_alpinista,
    momento=None,
):
    item_id = _pk(item_atual, 'Item da proposta')
    try:
        item_contexto = ItemPropostaVioleiros.objects.values(
            'proposta_id',
            'papel_sugerido',
            'posicao',
        ).get(pk=item_id)
    except ItemPropostaVioleiros.DoesNotExist as error:
        raise ValidationError('Item da proposta não encontrado.') from error
    papel_sugerido = item_contexto['papel_sugerido']
    posicao = item_contexto['posicao']
    _validar_slot(papel_sugerido, posicao)
    perfil_bloqueado, _ = _bloquear_perfil_e_pessoa(perfil_alpinista)
    proposta_id = item_contexto['proposta_id']
    encontro_id = _encontro_id_da_proposta(proposta_id)
    try:
        encontro_bloqueado = (
            Encontro.objects.select_for_update().get(pk=encontro_id)
        )
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error
    proposta_bloqueada = _bloquear_proposta(
        PropostaVioleiros(pk=proposta_id),
        encontro_bloqueado,
    )
    _validar_aberta(proposta_bloqueada)

    itens_vigentes = list(
        ItemPropostaVioleiros.objects
        .select_for_update()
        .filter(proposta=proposta_bloqueada, vigente=True)
        .order_by('pk')
    )
    if any(
        item.perfil_alpinista_id == perfil_bloqueado.pk
        for item in itens_vigentes
    ):
        raise ValidationError('O candidato já está vigente nesta proposta.')
    item_anterior = next(
        (item for item in itens_vigentes if item.pk == item_id),
        None,
    )
    if item_anterior is None:
        raise ValidationError('A ocupação informada não está mais vigente.')

    avaliacao = _validar_candidato_disponivel(
        perfil_bloqueado,
        encontro_bloqueado,
    )
    item_anterior.vigente = False
    item_anterior.retirado_em = momento or timezone.now()
    item_anterior.save(
        update_fields=['vigente', 'retirado_em', 'atualizado_em']
    )
    item_novo = _criar_item(
        proposta=proposta_bloqueada,
        perfil=perfil_bloqueado,
        papel_sugerido=papel_sugerido,
        posicao=posicao,
        avaliacao=avaliacao,
    )
    return item_anterior, item_novo


@transaction.atomic
def retirar_item_proposta(item, *, momento=None):
    item_id = _pk(item, 'Item da proposta')
    try:
        proposta_id = ItemPropostaVioleiros.objects.values_list(
            'proposta_id',
            flat=True,
        ).get(pk=item_id)
    except ItemPropostaVioleiros.DoesNotExist as error:
        raise ValidationError('Item da proposta não encontrado.') from error
    encontro_id = _encontro_id_da_proposta(proposta_id)
    try:
        encontro = Encontro.objects.select_for_update().get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error
    proposta = _bloquear_proposta(
        PropostaVioleiros(pk=proposta_id),
        encontro,
    )
    _validar_aberta(proposta)
    try:
        item_bloqueado = (
            ItemPropostaVioleiros.objects
            .select_for_update()
            .get(pk=item_id, proposta=proposta)
        )
    except ItemPropostaVioleiros.DoesNotExist as error:
        raise ValidationError('Item da proposta não encontrado.') from error
    if not item_bloqueado.vigente:
        return item_bloqueado
    item_bloqueado.vigente = False
    item_bloqueado.retirado_em = momento or timezone.now()
    item_bloqueado.save(
        update_fields=['vigente', 'retirado_em', 'atualizado_em']
    )
    return item_bloqueado


@transaction.atomic
def encerrar_proposta_violeiros(proposta, *, momento=None):
    proposta_bloqueada, _ = _bloquear_contexto_proposta(proposta)
    if proposta_bloqueada.status == PropostaVioleiros.Status.ENCERRADA:
        return proposta_bloqueada
    proposta_bloqueada.status = PropostaVioleiros.Status.ENCERRADA
    proposta_bloqueada.encerrada_em = momento or timezone.now()
    proposta_bloqueada.save(
        update_fields=['status', 'encerrada_em', 'atualizada_em']
    )
    return proposta_bloqueada


def obter_situacao_item_proposta(item):
    if not isinstance(item, ItemPropostaVioleiros) or item.pk is None:
        raise ValueError('Item da proposta deve estar persistido.')
    item_atual = (
        ItemPropostaVioleiros.objects
        .select_related(
            'perfil_alpinista__pessoa',
            'proposta__encontro',
        )
        .get(pk=item.pk)
    )
    return _resultado_item_proposta(item_atual)


def obter_candidato_para_aproveitamento(item):
    resultado = obter_situacao_item_proposta(item)
    if resultado.situacao != SituacaoItemProposta.DISPONIVEL:
        raise ValidationError(
            'Somente candidato disponível pode ser aproveitado pela escala.'
        )
    return resultado.item.perfil_alpinista.pessoa


def _resultado_item_proposta(item):
    if not item.vigente:
        return ResultadoItemProposta(
            item=item,
            situacao=SituacaoItemProposta.HISTORICO,
        )
    situacao, avaliacao, trabalho = _avaliar_candidato(
        item.perfil_alpinista,
        item.proposta.encontro,
    )
    return ResultadoItemProposta(
        item=item,
        situacao=situacao,
        avaliacao_elegibilidade=avaliacao,
        trabalho=trabalho,
    )


def resumir_proposta_violeiros(proposta):
    proposta_id = _pk(proposta, 'Proposta de Violeiros')
    try:
        proposta_atual = (
            PropostaVioleiros.objects
            .select_related('encontro')
            .get(pk=proposta_id)
        )
    except PropostaVioleiros.DoesNotExist as error:
        raise ValidationError('Proposta de Violeiros não encontrada.') from error
    itens = list(
        ItemPropostaVioleiros.objects
        .select_related('perfil_alpinista__pessoa', 'proposta__encontro')
        .filter(proposta=proposta_atual)
        .order_by('-vigente', 'papel_sugerido', 'posicao', 'pk')
    )
    resultados = tuple(_resultado_item_proposta(item) for item in itens)
    return ResumoPropostaVioleiros(
        proposta=proposta_atual,
        itens=resultados,
    )
