from calendar import monthrange
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.models import (
    ConfiguracaoGrupo,
    CoordenacaoGrupo,
    Frequencia,
    Grupo,
    PerfilAlpinista,
    VinculoGrupo,
)


def adicionar_meses_calendario(data_base, meses):
    indice_mes = data_base.month - 1 + meses
    ano = data_base.year + indice_mes // 12
    mes = indice_mes % 12 + 1
    dia = min(data_base.day, monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def _validar_periodo(inicio, fim):
    if fim is not None and fim < inicio:
        raise ValidationError('A data final não pode ser anterior à inicial.')


def _ha_sobreposicao(queryset, inicio, fim, *, campo_inicio, campo_fim):
    limite_final = fim or date.max
    filtros = {
        f'{campo_inicio}__lte': limite_final,
    }
    return (
        queryset
        .filter(**filtros)
        .filter(
            Q(**{f'{campo_fim}__isnull': True})
            | Q(**{f'{campo_fim}__gte': inicio})
        )
        .exists()
    )


@transaction.atomic
def criar_configuracao_grupo(
    *,
    grupo,
    vigente_desde,
    vigente_ate=None,
    ativo=True,
    paroquia=None,
    local_reuniao='',
    dia_semana='',
    horario=None,
):
    _validar_periodo(vigente_desde, vigente_ate)
    grupo_bloqueado = Grupo.objects.select_for_update().get(pk=grupo.pk)
    configuracoes = ConfiguracaoGrupo.objects.filter(grupo=grupo_bloqueado)
    if _ha_sobreposicao(
        configuracoes,
        vigente_desde,
        vigente_ate,
        campo_inicio='vigente_desde',
        campo_fim='vigente_ate',
    ):
        raise ValidationError(
            'A configuração se sobrepõe a outro período do Grupo.'
        )

    return ConfiguracaoGrupo.objects.create(
        grupo=grupo_bloqueado,
        vigente_desde=vigente_desde,
        vigente_ate=vigente_ate,
        ativo=ativo,
        paroquia=paroquia,
        local_reuniao=local_reuniao,
        dia_semana=dia_semana,
        horario=horario,
    )


@transaction.atomic
def criar_vinculo_grupo(
    *,
    perfil_alpinista,
    grupo,
    inicio,
    fim=None,
):
    _validar_periodo(inicio, fim)
    perfil_bloqueado = (
        PerfilAlpinista.objects
        .select_for_update()
        .get(pk=perfil_alpinista.pk)
    )

    if fim is None:
        vinculos_atuais = VinculoGrupo.objects.filter(
            perfil_alpinista=perfil_bloqueado,
            fim__isnull=True,
        )
        if vinculos_atuais.filter(grupo=grupo).exists():
            raise ValidationError(
                'Já existe vínculo atual deste Perfil com o Grupo.'
            )
        if vinculos_atuais.count() >= 2:
            raise ValidationError(
                'Um PerfilAlpinista pode ter no máximo dois Grupos atuais.'
            )

    return VinculoGrupo.objects.create(
        perfil_alpinista=perfil_bloqueado,
        grupo=grupo,
        inicio=inicio,
        fim=fim,
    )


@transaction.atomic
def criar_coordenacao_grupo(
    *,
    perfil_alpinista,
    grupo,
    tipo,
    inicio,
    fim=None,
):
    _validar_periodo(inicio, fim)
    if tipo not in CoordenacaoGrupo.Tipo.values:
        raise ValidationError('Tipo de coordenação inválido.')

    perfil_bloqueado = (
        PerfilAlpinista.objects
        .select_for_update()
        .get(pk=perfil_alpinista.pk)
    )
    coordenacoes = CoordenacaoGrupo.objects.filter(
        perfil_alpinista=perfil_bloqueado
    )
    if _ha_sobreposicao(
        coordenacoes,
        inicio,
        fim,
        campo_inicio='inicio',
        campo_fim='fim',
    ):
        raise ValidationError(
            'A coordenação se sobrepõe a outro mandato da pessoa.'
        )

    return CoordenacaoGrupo.objects.create(
        perfil_alpinista=perfil_bloqueado,
        grupo=grupo,
        tipo=tipo,
        inicio=inicio,
        fim=fim,
    )


def possui_acesso_transicao(perfil_alpinista, *, data_referencia=None):
    referencia = data_referencia or timezone.localdate()
    coordenacoes = (
        CoordenacaoGrupo.objects
        .filter(
            perfil_alpinista=perfil_alpinista,
            inicio__lte=referencia,
        )
        .only('fim')
    )
    for coordenacao in coordenacoes:
        if coordenacao.fim is None:
            return True
        if referencia <= adicionar_meses_calendario(coordenacao.fim, 1):
            return True
    return False


@transaction.atomic
def registrar_frequencia(
    *,
    perfil_alpinista,
    data,
    registrada_por,
    grupo=None,
    data_atual=None,
):
    hoje = data_atual or timezone.localdate()
    if data > hoje:
        raise ValidationError('Não é permitido registrar frequência futura.')

    perfil_bloqueado = (
        PerfilAlpinista.objects
        .select_for_update()
        .get(pk=perfil_alpinista.pk)
    )
    if Frequencia.objects.filter(
        perfil_alpinista=perfil_bloqueado,
        data=data,
    ).exists():
        raise ValidationError(
            'Já existe frequência para este PerfilAlpinista na data.'
        )

    return Frequencia.objects.create(
        perfil_alpinista=perfil_bloqueado,
        data=data,
        grupo=grupo,
        registrada_por=registrada_por,
    )


def perfil_alpinista_ativo(perfil_alpinista, *, data_referencia=None):
    referencia = data_referencia or timezone.localdate()
    ultima_frequencia = (
        Frequencia.objects
        .filter(perfil_alpinista=perfil_alpinista)
        .order_by('-data')
        .values_list('data', flat=True)
        .first()
    )
    if ultima_frequencia is None:
        return True

    limite = adicionar_meses_calendario(ultima_frequencia, 6)
    return referencia <= limite
