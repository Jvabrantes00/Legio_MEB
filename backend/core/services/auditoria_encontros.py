import json
import re
from collections.abc import Mapping

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from core.models import Encontro, EventoAuditoriaEncontro
from core.permissions import pode_consultar_auditoria_encontro


_IDENTIFICADOR_RE = re.compile(r'^[a-z][a-z0-9_.-]{0,99}$')
_OBJETO_ID_RE = re.compile(r'^[A-Za-z0-9:_-]{1,100}$')
ORIGEM_INTERNA = 'interna'
ORIGEM_PUBLICA = 'publica'
ORIGENS_EVENTO = frozenset({ORIGEM_INTERNA, ORIGEM_PUBLICA})
_CAMPOS_SENSIVEIS = frozenset({
    'alergia',
    'alergias',
    'cep',
    'cpf',
    'email',
    'endereco',
    'logradouro',
    'medicacao',
    'medicacoes',
    'medicamento',
    'medicamentos',
    'neurodivergencia',
    'password',
    'restricao',
    'restricoes',
    'saude',
    'senha',
    'telefone',
    'token',
    'whatsapp',
})


def _pk(instance, nome):
    if instance is None or instance.pk is None:
        raise ValidationError(f'{nome} deve estar persistido.')
    return instance.pk


def _identificador(valor, nome):
    if not isinstance(valor, str) or not _IDENTIFICADOR_RE.fullmatch(valor):
        raise ValidationError(
            f'{nome} deve ser um identificador técnico válido.'
        )
    return valor


def _objeto_id(valor):
    valor_normalizado = str(valor)
    if not _OBJETO_ID_RE.fullmatch(valor_normalizado):
        raise ValidationError('Objeto deve possuir identificador técnico válido.')
    return valor_normalizado


def _nome_canonico_campo(campo):
    return campo.lower().replace('-', '_').replace('.', '_')


def _normalizar_diferenca(nome, valor, campos_permitidos):
    if not isinstance(valor, Mapping):
        raise ValidationError(f'{nome} deve ser informado por campos.')

    chaves = set(valor)
    if not all(isinstance(campo, str) for campo in chaves):
        raise ValidationError(f'{nome} possui campo inválido.')

    desconhecidos = chaves - campos_permitidos
    if desconhecidos:
        raise ValidationError(
            f'{nome} possui campos fora da allowlist: '
            f'{", ".join(sorted(desconhecidos))}.'
        )

    sensiveis = {
        campo
        for campo in chaves
        if _nome_canonico_campo(campo) in _CAMPOS_SENSIVEIS
    }
    if sensiveis:
        raise ValidationError(
            f'{nome} não pode duplicar campos sensíveis: '
            f'{", ".join(sorted(sensiveis))}.'
        )

    try:
        json.dumps(valor, cls=DjangoJSONEncoder)
    except (TypeError, ValueError) as error:
        raise ValidationError(
            f'{nome} deve conter valores serializáveis.'
        ) from error
    return dict(valor)


@transaction.atomic
def registrar_evento_auditoria_encontro(
    *,
    encontro,
    ator,
    fato,
    entidade,
    objeto_id,
    valor_anterior,
    valor_novo,
    campos_permitidos,
    justificativa='',
    origem=ORIGEM_INTERNA,
):
    encontro_id = _pk(encontro, 'Encontro')

    if origem not in ORIGENS_EVENTO:
        raise ValidationError('Origem do evento de auditoria inválida.')
    if origem == ORIGEM_PUBLICA and ator is not None:
        raise ValidationError('Evento público não pode possuir ator interno.')
    if origem == ORIGEM_INTERNA and ator is None:
        raise ValidationError('Evento interno exige ator ativo.')

    try:
        encontro_persistido = Encontro.objects.get(pk=encontro_id)
    except Encontro.DoesNotExist as error:
        raise ValidationError('Encontro não encontrado.') from error

    ator_persistido = None
    if origem == ORIGEM_INTERNA:
        ator_id = _pk(ator, 'Ator')
        user_model = get_user_model()
        try:
            ator_persistido = user_model.objects.get(pk=ator_id, is_active=True)
        except user_model.DoesNotExist as error:
            raise ValidationError('Ator ativo não encontrado.') from error

    if not isinstance(campos_permitidos, (set, frozenset, tuple, list)):
        raise ValidationError('A allowlist de campos deve ser explícita.')
    campos_permitidos = frozenset(campos_permitidos)
    if not all(isinstance(campo, str) for campo in campos_permitidos):
        raise ValidationError('A allowlist possui campo inválido.')
    if origem == ORIGEM_PUBLICA and 'origem' not in campos_permitidos:
        raise ValidationError(
            'Evento público exige origem na allowlist de auditoria.'
        )

    anterior = _normalizar_diferenca(
        'Valor anterior',
        valor_anterior,
        campos_permitidos,
    )
    novo = _normalizar_diferenca(
        'Valor novo',
        valor_novo,
        campos_permitidos,
    )
    if origem == ORIGEM_PUBLICA:
        if anterior.get('origem', ORIGEM_PUBLICA) != ORIGEM_PUBLICA:
            raise ValidationError('Origem pública conflitante no valor anterior.')
        if novo.get('origem', ORIGEM_PUBLICA) != ORIGEM_PUBLICA:
            raise ValidationError('Origem pública conflitante no valor novo.')
        anterior['origem'] = ORIGEM_PUBLICA
        novo['origem'] = ORIGEM_PUBLICA
    if not isinstance(justificativa, str):
        raise ValidationError('Justificativa deve ser textual.')

    return EventoAuditoriaEncontro.objects.create(
        encontro=encontro_persistido,
        ator=ator_persistido,
        fato=_identificador(fato, 'Fato'),
        entidade=_identificador(entidade, 'Entidade'),
        objeto_id=_objeto_id(objeto_id),
        valor_anterior=anterior,
        valor_novo=novo,
        justificativa=justificativa,
    )


def consultar_eventos_auditoria_encontro(*, usuario, encontro):
    encontro_id = _pk(encontro, 'Encontro')
    if not pode_consultar_auditoria_encontro(usuario):
        raise PermissionDenied(
            'Seu usuário não pode consultar a auditoria de Encontros.'
        )
    return (
        EventoAuditoriaEncontro.objects
        .filter(encontro_id=encontro_id)
        .select_related('ator', 'encontro')
        .order_by('-criado_em', '-id')
    )
