from celery import shared_task
from django.utils import timezone

from core.models import CampanhaConvitesEncontro
from core.services.campanhas_convites import (
    processar_prazo_automaticamente,
)
from core.services.entregas_convites import (
    processar_outbox_entrega_convite,
    reconciliar_outboxes_entrega_convite,
)
from core.services.reposicao_campanha import (
    processar_sinal_reposicao_campanha,
    reconciliar_sinais_reposicao,
)


@shared_task(name='core.processar_outbox_convite', ignore_result=True)
def processar_outbox_convite(outbox_id):
    processar_outbox_entrega_convite(outbox_id=outbox_id)


@shared_task(name='core.reconciliar_outboxes_convites', ignore_result=True)
def reconciliar_outboxes_convites():
    reconciliar_outboxes_entrega_convite()


@shared_task(name='core.processar_prazo_campanha', ignore_result=True)
def processar_prazo_campanha(campanha_id):
    try:
        campanha = CampanhaConvitesEncontro.objects.get(pk=campanha_id)
    except CampanhaConvitesEncontro.DoesNotExist:
        return
    processar_prazo_automaticamente(campanha=campanha)


@shared_task(name='core.processar_prazos_campanhas', ignore_result=True)
def processar_prazos_campanhas():
    ids = tuple(
        CampanhaConvitesEncontro.objects
        .filter(
            status=CampanhaConvitesEncontro.Status.ATIVA,
            prazo_confirmacao__lte=timezone.now(),
        )
        .order_by('pk')
        .values_list('pk', flat=True)
    )
    for campanha_id in ids:
        processar_prazo_campanha.delay(campanha_id)


@shared_task(name='core.processar_sinal_reposicao', ignore_result=True)
def processar_sinal_reposicao(sinal_id):
    processar_sinal_reposicao_campanha(sinal_id=sinal_id)


@shared_task(name='core.processar_sinais_reposicao', ignore_result=True)
def processar_sinais_reposicao():
    reconciliar_sinais_reposicao()
