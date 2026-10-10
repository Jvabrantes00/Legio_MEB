from django.db import IntegrityError, transaction
from django.utils import timezone

from core.models import (
    CampanhaConvitesEncontro,
    ConfiguracaoEncontristasEncontro,
    Encontro,
    SinalReposicaoCampanha,
)


def _publicar_sinal_apos_commit(sinal_id):
    try:
        from core.tasks import processar_sinal_reposicao

        processar_sinal_reposicao.delay(sinal_id)
    except Exception:
        return False
    return True


@transaction.atomic
def registrar_transicao_lotado_para_disponivel(
    *,
    encontro,
    ocupacao_antes,
    capacidade_antes,
    ocupacao_depois,
    capacidade_depois,
    motivo,
):
    if not (
        ocupacao_antes == capacidade_antes
        and ocupacao_depois < capacidade_depois
    ):
        return None
    campanha = (
        CampanhaConvitesEncontro.objects
        .select_for_update()
        .filter(
            encontro=encontro,
            status=CampanhaConvitesEncontro.Status.ATIVA,
        )
        .first()
    )
    if campanha is None:
        return None
    existente = (
        SinalReposicaoCampanha.objects
        .filter(
            campanha=campanha,
            status=SinalReposicaoCampanha.Status.PENDENTE,
        )
        .first()
    )
    if existente is not None:
        return existente
    try:
        with transaction.atomic():
            sinal = SinalReposicaoCampanha.objects.create(
                campanha=campanha,
                motivo=motivo,
            )
    except IntegrityError:
        return SinalReposicaoCampanha.objects.get(
            campanha=campanha,
            status=SinalReposicaoCampanha.Status.PENDENTE,
        )
    transaction.on_commit(
        lambda sinal_id=sinal.pk: _publicar_sinal_apos_commit(sinal_id)
    )
    return sinal


@transaction.atomic
def processar_sinal_reposicao_campanha(*, sinal_id, momento=None):
    referencia = (
        SinalReposicaoCampanha.objects
        .filter(pk=sinal_id)
        .values('campanha_id', 'campanha__encontro_id')
        .first()
    )
    if referencia is None:
        return None

    encontro_id = referencia['campanha__encontro_id']
    Encontro.objects.select_for_update(of=('self',)).get(pk=encontro_id)
    ConfiguracaoEncontristasEncontro.objects.select_for_update(
        of=('self',)
    ).get(encontro_id=encontro_id)
    campanha = (
        CampanhaConvitesEncontro.objects
        .select_related('encontro')
        .select_for_update(of=('self',))
        .get(pk=referencia['campanha_id'])
    )
    try:
        sinal = (
            SinalReposicaoCampanha.objects
            .select_for_update(of=('self',))
            .get(pk=sinal_id)
        )
    except SinalReposicaoCampanha.DoesNotExist:
        return None
    sinal.campanha = campanha
    if sinal.status == SinalReposicaoCampanha.Status.PROCESSADO:
        return sinal

    from core.services.campanhas_convites import (
        abrir_reposicao_nova_vaga_automaticamente,
    )

    abrir_reposicao_nova_vaga_automaticamente(
        campanha=sinal.campanha,
        momento=momento,
    )
    sinal.status = SinalReposicaoCampanha.Status.PROCESSADO
    sinal.processado_em = momento or timezone.now()
    sinal.save(update_fields=[
        'status',
        'processado_em',
        'atualizada_em',
    ])
    return sinal


def reconciliar_sinais_reposicao():
    ids = tuple(
        SinalReposicaoCampanha.objects
        .filter(status=SinalReposicaoCampanha.Status.PENDENTE)
        .order_by('pk')
        .values_list('pk', flat=True)
    )
    for sinal_id in ids:
        _publicar_sinal_apos_commit(sinal_id)
    return ids
