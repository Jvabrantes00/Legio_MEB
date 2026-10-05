from dataclasses import dataclass
from enum import Enum

from django.core.exceptions import ValidationError

from core.models import (
    Alpinista,
    Encontro,
    EquipeEncontro,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
    RoleEquipeEncontro,
    TrabalhoEncontro,
)


class ResultadoElegibilidade(str, Enum):
    ELEGIVEL = 'ELEGIVEL'
    AVISO = 'AVISO'
    BLOQUEIO = 'BLOQUEIO'


class CodigoElegibilidade(str, Enum):
    PERFIL_ALPINISTA_AUSENTE = 'PERFIL_ALPINISTA_AUSENTE'
    ALPINISTA_INATIVO = 'ALPINISTA_INATIVO'
    ATIVIDADE_NAO_DETERMINADA = 'ATIVIDADE_NAO_DETERMINADA'
    AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA = (
        'AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA'
    )
    CAMINHO_FORMATIVO_NAO_DETERMINADO = (
        'CAMINHO_FORMATIVO_NAO_DETERMINADO'
    )
    REVISAO_MANUAL_TRABALHO_AVC = 'REVISAO_MANUAL_TRABALHO_AVC'
    REVISAO_MANUAL_TRABALHO_ACAMPAMENTO = (
        'REVISAO_MANUAL_TRABALHO_ACAMPAMENTO'
    )
    CAPACIDADE_MINIMA_NAO_ATINGIDA = 'CAPACIDADE_MINIMA_NAO_ATINGIDA'
    CAPACIDADE_MAXIMA_EXCEDIDA = 'CAPACIDADE_MAXIMA_EXCEDIDA'
    COMPOSICAO_ESTRUTURAL_INCOMPLETA = (
        'COMPOSICAO_ESTRUTURAL_INCOMPLETA'
    )
    QUANTIDADE_ESTRUTURAL_EXCEDIDA = (
        'QUANTIDADE_ESTRUTURAL_EXCEDIDA'
    )


@dataclass(frozen=True)
class MotivoElegibilidade:
    codigo: CodigoElegibilidade
    categoria: ResultadoElegibilidade
    mensagem: str
    contexto: dict | None = None

    def as_dict(self):
        resultado = {
            'codigo': self.codigo.value,
            'categoria': self.categoria.value,
            'mensagem': self.mensagem,
        }
        if self.contexto:
            resultado['contexto'] = dict(self.contexto)
        return resultado


@dataclass(frozen=True)
class AvaliacaoElegibilidade:
    resultado: ResultadoElegibilidade
    motivos: tuple[MotivoElegibilidade, ...] = ()

    @property
    def avisos(self):
        return tuple(
            motivo
            for motivo in self.motivos
            if motivo.categoria == ResultadoElegibilidade.AVISO
        )

    @property
    def bloqueios(self):
        return tuple(
            motivo
            for motivo in self.motivos
            if motivo.categoria == ResultadoElegibilidade.BLOQUEIO
        )

    @property
    def codigos(self):
        return tuple(motivo.codigo.value for motivo in self.motivos)

    def as_dict(self):
        return {
            'resultado': self.resultado.value,
            'motivos': [motivo.as_dict() for motivo in self.motivos],
        }


class AvaliacaoTrabalhoError(ValidationError):
    def __init__(self, avaliacao, mensagem):
        self.avaliacao = avaliacao
        super().__init__({
            'elegibilidade': [
                f'{motivo.codigo.value}: {motivo.mensagem}'
                for motivo in avaliacao.motivos
            ],
            'comando': [mensagem],
        })


class BloqueioElegibilidadeTrabalho(AvaliacaoTrabalhoError):
    pass


class AvisosElegibilidadePendentes(AvaliacaoTrabalhoError):
    pass


def _avaliacao(*motivos):
    motivos = tuple(motivo for motivo in motivos if motivo is not None)
    if any(
        motivo.categoria == ResultadoElegibilidade.BLOQUEIO
        for motivo in motivos
    ):
        resultado = ResultadoElegibilidade.BLOQUEIO
    elif motivos:
        resultado = ResultadoElegibilidade.AVISO
    else:
        resultado = ResultadoElegibilidade.ELEGIVEL
    return AvaliacaoElegibilidade(resultado=resultado, motivos=motivos)


def combinar_avaliacoes(*avaliacoes):
    return _avaliacao(*(
        motivo
        for avaliacao in avaliacoes
        for motivo in avaliacao.motivos
    ))


def _aviso(codigo, mensagem, contexto=None):
    return MotivoElegibilidade(
        codigo=codigo,
        categoria=ResultadoElegibilidade.AVISO,
        mensagem=mensagem,
        contexto=contexto,
    )


def _bloqueio(codigo, mensagem, contexto=None):
    return MotivoElegibilidade(
        codigo=codigo,
        categoria=ResultadoElegibilidade.BLOQUEIO,
        mensagem=mensagem,
        contexto=contexto,
    )


def _tipos_concluidos(pessoa):
    return set(
        ParticipacaoEncontro.objects.filter(
            pessoa=pessoa,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
        ).values_list('tipo_encontro', flat=True)
    )


def _avaliar_perfil_e_atividade(pessoa):
    motivos = []
    if not PerfilAlpinista.objects.filter(pessoa=pessoa).exists():
        motivos.append(_aviso(
            CodigoElegibilidade.PERFIL_ALPINISTA_AUSENTE,
            'A Pessoa não possui PerfilAlpinista canônico.',
        ))

    status_legado = (
        Alpinista.objects
        .filter(pessoa=pessoa)
        .values_list('status', flat=True)
        .first()
    )
    if status_legado == Alpinista.Status.INATIVO:
        motivos.append(_aviso(
            CodigoElegibilidade.ALPINISTA_INATIVO,
            'O Alpinista está inativo e exige revisão humana.',
        ))
    elif status_legado != Alpinista.Status.ATIVO:
        motivos.append(_aviso(
            CodigoElegibilidade.ATIVIDADE_NAO_DETERMINADA,
            'Não há evidência canônica suficiente do estado de atividade.',
        ))
    return motivos


def avaliar_elegibilidade_trabalho(pessoa, encontro):
    if not isinstance(pessoa, Pessoa) or pessoa.pk is None:
        raise ValueError('Pessoa deve estar persistida.')
    if not isinstance(encontro, Encontro) or encontro.pk is None:
        raise ValueError('Encontro deve estar persistido.')

    motivos = _avaliar_perfil_e_atividade(pessoa)
    conclusoes = _tipos_concluidos(pessoa)
    concluiu_escalada = Encontro.Tipo.ESCALADA in conclusoes
    concluiu_esppa = Encontro.Tipo.ESPPA in conclusoes
    concluiu_avc = Encontro.Tipo.AVC in conclusoes

    if encontro.tipo == Encontro.Tipo.ESCALADA:
        if concluiu_esppa:
            pass
        elif concluiu_escalada and not concluiu_avc:
            motivos.append(_bloqueio(
                CodigoElegibilidade.AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA,
                'O caminho da Escalada exige conclusão de AVC.',
            ))
        elif not concluiu_escalada:
            motivos.append(_aviso(
                CodigoElegibilidade.CAMINHO_FORMATIVO_NAO_DETERMINADO,
                'O caminho formativo para trabalhar exige revisão humana.',
            ))
    elif encontro.tipo == Encontro.Tipo.ESPPA:
        if concluiu_esppa:
            pass
        elif concluiu_escalada and concluiu_avc:
            pass
        elif concluiu_escalada:
            motivos.append(_bloqueio(
                CodigoElegibilidade.AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA,
                'Escalada sem AVC concluído não habilita trabalho em ESPPA.',
            ))
        else:
            motivos.append(_aviso(
                CodigoElegibilidade.CAMINHO_FORMATIVO_NAO_DETERMINADO,
                'O caminho formativo para trabalhar exige revisão humana.',
            ))
    elif encontro.tipo == Encontro.Tipo.AVC:
        motivos.append(_aviso(
            CodigoElegibilidade.REVISAO_MANUAL_TRABALHO_AVC,
            'A elegibilidade para trabalhar em AVC exige revisão humana.',
        ))
    elif encontro.tipo == Encontro.Tipo.ACAMPAMENTO:
        motivos.append(_aviso(
            CodigoElegibilidade.REVISAO_MANUAL_TRABALHO_ACAMPAMENTO,
            'A elegibilidade para Acampamento exige revisão humana.',
        ))

    return _avaliacao(*motivos)


def _ocupacao_equipe(equipe, excluir_trabalho=None):
    trabalhos = TrabalhoEncontro.objects.filter(
        role_equipe__equipe_encontro=equipe,
        status=TrabalhoEncontro.Status.ALOCADO,
    )
    if excluir_trabalho is not None and excluir_trabalho.pk is not None:
        trabalhos = trabalhos.exclude(pk=excluir_trabalho.pk)
    return trabalhos.count()


def avaliar_capacidade_equipe(
    equipe,
    *,
    ocupacao_adicional=0,
    excluir_trabalho=None,
):
    if not isinstance(equipe, EquipeEncontro) or equipe.pk is None:
        raise ValueError('Equipe deve estar persistida.')
    ocupacao = (
        _ocupacao_equipe(equipe, excluir_trabalho)
        + ocupacao_adicional
    )
    contexto = {'equipe_id': equipe.pk, 'ocupacao': ocupacao}
    motivos = []
    minimo = equipe.capacidade_minima_recomendada
    maximo = equipe.capacidade_maxima_recomendada
    if minimo is not None and ocupacao < minimo:
        motivos.append(_aviso(
            CodigoElegibilidade.CAPACIDADE_MINIMA_NAO_ATINGIDA,
            'A equipe está abaixo da capacidade mínima recomendada.',
            {**contexto, 'referencia': minimo},
        ))
    if maximo is not None and ocupacao > maximo:
        motivos.append(_aviso(
            CodigoElegibilidade.CAPACIDADE_MAXIMA_EXCEDIDA,
            'A equipe está acima da capacidade máxima recomendada.',
            {**contexto, 'referencia': maximo},
        ))
    return _avaliacao(*motivos)


def avaliar_composicao_estrutural(equipe):
    if not isinstance(equipe, EquipeEncontro) or equipe.pk is None:
        raise ValueError('Equipe deve estar persistida.')
    motivos = []
    for role in equipe.roles.exclude(quantidade_estrutural__isnull=True):
        ocupacao = role.trabalhos.filter(
            status=TrabalhoEncontro.Status.ALOCADO,
        ).count()
        contexto = {
            'equipe_id': equipe.pk,
            'role_id': role.pk,
            'ocupacao': ocupacao,
            'quantidade_estrutural': role.quantidade_estrutural,
        }
        if ocupacao < role.quantidade_estrutural:
            motivos.append(_aviso(
                CodigoElegibilidade.COMPOSICAO_ESTRUTURAL_INCOMPLETA,
                'A composição estrutural da role está incompleta.',
                contexto,
            ))
        elif ocupacao > role.quantidade_estrutural:
            motivos.append(_bloqueio(
                CodigoElegibilidade.QUANTIDADE_ESTRUTURAL_EXCEDIDA,
                'A quantidade estrutural da role foi excedida.',
                contexto,
            ))
    return _avaliacao(*motivos)


def avaliar_alocacao_trabalho(pessoa, encontro, role, trabalho=None):
    if not isinstance(role, RoleEquipeEncontro) or role.pk is None:
        raise ValueError('Role deve estar persistida.')
    ocupantes = role.trabalhos.filter(
        status=TrabalhoEncontro.Status.ALOCADO,
    )
    if trabalho is not None and trabalho.pk is not None:
        ocupantes = ocupantes.exclude(pk=trabalho.pk)
    ocupacao_role = ocupantes.count() + 1
    avaliacao_role = _avaliacao()
    if (
        role.quantidade_estrutural is not None
        and ocupacao_role > role.quantidade_estrutural
    ):
        avaliacao_role = _avaliacao(_bloqueio(
            CodigoElegibilidade.QUANTIDADE_ESTRUTURAL_EXCEDIDA,
            'A quantidade estrutural da role seria excedida.',
            {
                'equipe_id': role.equipe_encontro_id,
                'role_id': role.pk,
                'ocupacao': ocupacao_role,
                'quantidade_estrutural': role.quantidade_estrutural,
            },
        ))
    return combinar_avaliacoes(
        avaliar_elegibilidade_trabalho(pessoa, encontro),
        avaliar_capacidade_equipe(
            role.equipe_encontro,
            ocupacao_adicional=1,
            excluir_trabalho=trabalho,
        ),
        avaliacao_role,
    )
