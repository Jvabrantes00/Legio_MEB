from datetime import timedelta
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from core.models import (
    EntregaConviteEncontro,
    OutboxEntregaConvite,
)
from core.notifications import (
    CategoriaFalhaEntrega,
    PayloadEntregaConvite,
    ProviderEntregaConvite,
    ResultadoEntregaConvite,
    resolver_adaptador_entrega_convite,
)


MAXIMO_TENTATIVAS = 3
BACKOFF_MINUTOS = {1: 1, 2: 5}


class ConfiguracaoOutboxInvalida(ValidationError):
    pass


def _fernet():
    chave = settings.SIA_INVITATION_OUTBOX_KEY
    if not chave:
        raise ConfiguracaoOutboxInvalida(
            'A chave criptográfica da outbox não foi configurada.'
        )
    try:
        return Fernet(chave.encode())
    except (TypeError, ValueError) as error:
        raise ConfiguracaoOutboxInvalida(
            'A chave criptográfica da outbox é inválida.'
        ) from error


def criptografar_token_convite(token):
    if not isinstance(token, str) or not token:
        raise ValidationError('Token transitório de convite inválido.')
    return _fernet().encrypt(token.encode()).decode()


def descriptografar_token_convite(ciphertext):
    if not isinstance(ciphertext, str) or not ciphertext:
        raise ValidationError('Segredo criptografado da outbox está ausente.')
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except InvalidToken as error:
        raise ValidationError(
            'Segredo criptografado da outbox não pôde ser validado.'
        ) from error


def _publicar_outbox_apos_commit(outbox_id, *, eta=None):
    try:
        from core.tasks import processar_outbox_convite

        if eta is None:
            processar_outbox_convite.delay(outbox_id)
        else:
            processar_outbox_convite.apply_async(args=[outbox_id], eta=eta)
    except Exception:
        # O PostgreSQL já contém o trabalho durável. O reconciliador periódico
        # recupera publicações perdidas sem expor payload ou segredo em log.
        return False
    return True


def criar_outbox_entrega_convite(*, oportunidade, token, canais):
    canais_normalizados = tuple(sorted({canal.lower() for canal in canais}))
    canais_validos = {
        EntregaConviteEncontro.Canal.EMAIL,
        EntregaConviteEncontro.Canal.WHATSAPP,
    }
    if not canais_normalizados:
        return None
    if not set(canais_normalizados) <= canais_validos:
        raise ValidationError('Canal de entrega de convite inválido.')

    ciphertext = criptografar_token_convite(token)
    try:
        outbox = OutboxEntregaConvite.objects.create(
            oportunidade=oportunidade,
            segredo_criptografado=ciphertext,
        )
        EntregaConviteEncontro.objects.bulk_create([
            EntregaConviteEncontro(
                oportunidade=oportunidade,
                canal=canal,
            )
            for canal in canais_normalizados
        ])
    except IntegrityError as error:
        raise ValidationError(
            'Não foi possível preparar a entrega do convite.'
        ) from error

    transaction.on_commit(
        lambda outbox_id=outbox.pk: _publicar_outbox_apos_commit(outbox_id)
    )
    return outbox


def _base_publica_convite():
    base = settings.SIA_PUBLIC_INVITATION_BASE_URL
    partes = urlsplit(base)
    if (
        partes.scheme not in {'http', 'https'}
        or not partes.netloc
        or partes.username is not None
        or partes.password is not None
    ):
        raise ImproperlyConfigured(
            'A URL pública de convites não foi configurada corretamente.'
        )
    return base


def _destinatario(entrega, pessoa):
    if entrega.canal == EntregaConviteEncontro.Canal.EMAIL:
        return pessoa.email or ''
    return (
        pessoa.telefones
        .filter(whatsapp=True)
        .exclude(numero='')
        .order_by('pk')
        .values_list('numero', flat=True)
        .first()
        or ''
    )


def _resultado_payload_invalido(provider):
    return ResultadoEntregaConvite(
        sucesso=False,
        provider=provider,
        processado_em=timezone.now(),
        categoria_falha=CategoriaFalhaEntrega.PAYLOAD,
        codigo_erro='destinatario_indisponivel',
    )


def _registrar_resultado(entrega, resultado, *, momento):
    entrega.tentativas += 1
    if entrega.primeira_tentativa_em is None:
        entrega.primeira_tentativa_em = momento
    entrega.ultima_tentativa_em = momento
    entrega.proxima_tentativa_em = None
    entrega.codigo_erro = ''
    entrega.erro_tecnico = ''

    if resultado.sucesso:
        entrega.status = EntregaConviteEncontro.Status.ENTREGUE
        entrega.entregue_em = momento
    else:
        entrega.codigo_erro = resultado.codigo_erro
        entrega.erro_tecnico = (
            f'categoria:{resultado.categoria_falha.value}'
        )
        retry = (
            resultado.categoria_falha == CategoriaFalhaEntrega.TEMPORARIA
            and entrega.tentativas < MAXIMO_TENTATIVAS
        )
        if retry:
            entrega.status = EntregaConviteEncontro.Status.PENDENTE
            entrega.proxima_tentativa_em = momento + timedelta(
                minutes=BACKOFF_MINUTOS[entrega.tentativas]
            )
        else:
            entrega.status = EntregaConviteEncontro.Status.FALHOU

    entrega.save(update_fields=[
        'status',
        'tentativas',
        'primeira_tentativa_em',
        'ultima_tentativa_em',
        'entregue_em',
        'proxima_tentativa_em',
        'codigo_erro',
        'erro_tecnico',
        'atualizada_em',
    ])


@transaction.atomic
def processar_outbox_entrega_convite(
    *,
    outbox_id,
    momento=None,
    resolver_adapter=resolver_adaptador_entrega_convite,
):
    instante = momento or timezone.now()
    try:
        outbox = (
            OutboxEntregaConvite.objects
            .select_for_update()
            .select_related(
                'oportunidade__convite__pessoa',
                'oportunidade__convite__encontro',
            )
            .get(pk=outbox_id)
        )
    except OutboxEntregaConvite.DoesNotExist:
        return None
    if outbox.status == OutboxEntregaConvite.Status.CONCLUIDA:
        return outbox
    if (
        outbox.proxima_tentativa_em is not None
        and outbox.proxima_tentativa_em > instante
    ):
        return outbox

    entregas = list(
        EntregaConviteEncontro.objects
        .select_for_update()
        .filter(oportunidade=outbox.oportunidade)
        .order_by('pk')
    )
    pendentes = [
        entrega
        for entrega in entregas
        if entrega.status == EntregaConviteEncontro.Status.PENDENTE
        and (
            entrega.proxima_tentativa_em is None
            or entrega.proxima_tentativa_em <= instante
        )
    ]
    if pendentes:
        token = descriptografar_token_convite(
            outbox.segredo_criptografado
        )
        link = f'{_base_publica_convite()}/{token}'
        pessoa = outbox.oportunidade.convite.pessoa
        for entrega in pendentes:
            try:
                adapter = resolver_adapter(entrega.canal)
                destinatario = _destinatario(entrega, pessoa)
                if destinatario:
                    resultado = adapter.entregar(PayloadEntregaConvite(
                        destinatario=destinatario,
                        nome_encontro=(
                            outbox.oportunidade.convite.encontro.encontro
                        ),
                        prazo_resposta=outbox.oportunidade.expira_em,
                        link_convite=link,
                    ))
                else:
                    resultado = _resultado_payload_invalido(adapter.provider)
            except ImproperlyConfigured:
                provider = (
                    ProviderEntregaConvite.SMTP
                    if entrega.canal == EntregaConviteEncontro.Canal.EMAIL
                    else ProviderEntregaConvite.WHATSAPP_MOCK
                )
                resultado = ResultadoEntregaConvite(
                    sucesso=False,
                    provider=provider,
                    processado_em=instante,
                    categoria_falha=CategoriaFalhaEntrega.CONFIGURACAO,
                    codigo_erro='adapter_nao_configurado',
                )
            _registrar_resultado(entrega, resultado, momento=instante)

    terminais = {
        EntregaConviteEncontro.Status.ENTREGUE,
        EntregaConviteEncontro.Status.FALHOU,
    }
    if entregas and all(entrega.status in terminais for entrega in entregas):
        outbox.status = OutboxEntregaConvite.Status.CONCLUIDA
        outbox.segredo_criptografado = None
        outbox.segredo_destruido_em = instante
        outbox.proxima_tentativa_em = None
        outbox.save(update_fields=[
            'status',
            'segredo_criptografado',
            'segredo_destruido_em',
            'proxima_tentativa_em',
            'atualizada_em',
        ])
        return outbox

    proximas = [
        entrega.proxima_tentativa_em
        for entrega in entregas
        if entrega.status == EntregaConviteEncontro.Status.PENDENTE
        and entrega.proxima_tentativa_em is not None
    ]
    outbox.proxima_tentativa_em = min(proximas) if proximas else instante
    outbox.save(update_fields=['proxima_tentativa_em', 'atualizada_em'])
    if proximas:
        transaction.on_commit(
            lambda outbox_id=outbox.pk, eta=min(proximas): (
                _publicar_outbox_apos_commit(outbox_id, eta=eta)
            )
        )
    return outbox


def reconciliar_outboxes_entrega_convite(*, momento=None):
    instante = momento or timezone.now()
    ids = tuple(
        OutboxEntregaConvite.objects
        .filter(status=OutboxEntregaConvite.Status.PENDENTE)
        .filter(
            models.Q(proxima_tentativa_em__isnull=True)
            | models.Q(proxima_tentativa_em__lte=instante)
        )
        .order_by('pk')
        .values_list('pk', flat=True)
    )
    for outbox_id in ids:
        _publicar_outbox_apos_commit(outbox_id)
    return ids
