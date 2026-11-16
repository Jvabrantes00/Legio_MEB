from django.db import transaction
from rest_framework.exceptions import APIException

from core.models import (
    Encontro, EquipeEncontro, EventoAuditoriaEncontro, FuncaoEncontro,
    LogSistema, TrabalhoEncontro, VinculoEncontroLegado,
)


class ConflitoModeloEquipes(APIException):
    status_code = 409
    default_detail = 'Operação incompatível com o modelo de equipes do Encontro.'
    default_code = 'conflito_modelo_equipes'


def exigir_canonico(encontro):
    if encontro.modelo_equipes != Encontro.ModeloEquipes.CANONICO:
        raise ConflitoModeloEquipes()


def prontidao(encontro):
    vinculos = VinculoEncontroLegado.objects.filter(encontro=encontro)
    equipes = vinculos.filter(funcao__tipo='equipe').count()
    indefinidos = vinculos.exclude(funcao__tipo__in=('equipe', 'encontrista')).count()
    motivos = []
    if encontro.modelo_equipes != Encontro.ModeloEquipes.LEGADO:
        motivos.append('modelo_ja_canonico')
    if encontro.status in (Encontro.Status.FINALIZADO, Encontro.Status.CANCELADO):
        motivos.append('encontro_encerrado')
    if equipes:
        motivos.append('vinculos_legados_equipe')
    if indefinidos:
        motivos.append('vinculos_tipo_indefinido')
    return {
        'elegivel': not motivos,
        'motivos': motivos,
        'contagens': {
            'vinculos_legados_equipe': equipes,
            'vinculos_tipo_indefinido': indefinidos,
            'equipes_canonicas': EquipeEncontro.objects.filter(encontro=encontro).count(),
            'trabalhos_canonicos': TrabalhoEncontro.objects.filter(encontro=encontro).count(),
        },
    }


@transaction.atomic
def ativar(encontro, *, ator, justificativa):
    list(FuncaoEncontro.objects.select_for_update().order_by('pk'))
    encontro = Encontro.objects.select_for_update().get(pk=encontro.pk)
    resultado = prontidao(encontro)
    if not resultado['elegivel']:
        raise ConflitoModeloEquipes(resultado)
    encontro.modelo_equipes = Encontro.ModeloEquipes.CANONICO
    encontro.save(update_fields=['modelo_equipes'])
    EventoAuditoriaEncontro.objects.create(
        encontro=encontro, ator=ator, fato='modelo_equipes.ativado',
        entidade='Encontro', objeto_id=str(encontro.pk),
        valor_anterior={'modelo_equipes': 'LEGADO'},
        valor_novo={'modelo_equipes': 'CANONICO'}, justificativa=justificativa,
    )
    LogSistema.objects.create(
        usuario=ator, acao='UPDATE', modulo='Encontro',
        descricao=f'Modelo canônico de equipes ativado no Encontro {encontro.pk}.',
    )
    return encontro
