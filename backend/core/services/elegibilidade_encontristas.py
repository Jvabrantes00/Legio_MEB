from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum

from django.core.exceptions import ValidationError
from django.db.models import Max, Min
from django.utils import timezone

from core.models import (
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    Encontro,
    ParticipacaoEncontro,
    Pessoa,
)


class ResultadoElegibilidadeEncontrista(str, Enum):
    ELEGIVEL = 'ELEGIVEL'
    ELEGIVEL_COM_AVISO = 'ELEGIVEL_COM_AVISO'
    INELEGIVEL = 'INELEGIVEL'
    NAO_AVALIAVEL = 'NAO_AVALIAVEL'


class CodigoElegibilidadeEncontrista(str, Enum):
    CONCLUSAO_ANTERIOR_MESMO_TIPO = 'CONCLUSAO_ANTERIOR_MESMO_TIPO'
    CONFIGURACAO_AUSENTE = 'CONFIGURACAO_AUSENTE'
    CALENDARIO_OFICIAL_AUSENTE = 'CALENDARIO_OFICIAL_AUSENTE'
    DATA_NASCIMENTO_AUSENTE = 'DATA_NASCIMENTO_AUSENTE'
    IDADE_MINIMA_NAO_ATINGIDA = 'IDADE_MINIMA_NAO_ATINGIDA'
    IDADE_MAXIMA_EXCEDIDA = 'IDADE_MAXIMA_EXCEDIDA'
    IDADE_MINIMA_FUTURA = 'IDADE_MINIMA_FUTURA'


@dataclass(frozen=True)
class DetalheElegibilidadeEncontrista:
    codigo: CodigoElegibilidadeEncontrista
    mensagem: str

    def as_dict(self):
        return {
            'codigo': self.codigo.value,
            'mensagem': self.mensagem,
        }


@dataclass(frozen=True)
class ConfiguracaoElegibilidadeUtilizada:
    id: int
    capacidade: int
    idade_minima: int
    idade_maxima: int
    inscricoes_abrem_em: datetime
    inscricoes_encerram_em: datetime

    def as_dict(self):
        return {
            'id': self.id,
            'capacidade': self.capacidade,
            'idade_minima': self.idade_minima,
            'idade_maxima': self.idade_maxima,
            'inscricoes_abrem_em': self.inscricoes_abrem_em,
            'inscricoes_encerram_em': self.inscricoes_encerram_em,
        }


@dataclass(frozen=True)
class AvaliacaoElegibilidadeEncontrista:
    resultado: ResultadoElegibilidadeEncontrista
    motivos: tuple[DetalheElegibilidadeEncontrista, ...] = ()
    avisos: tuple[DetalheElegibilidadeEncontrista, ...] = ()
    idade_na_avaliacao: int | None = None
    idade_no_primeiro_dia: int | None = None
    idade_no_ultimo_dia: int | None = None
    primeiro_dia: date | None = None
    ultimo_dia: date | None = None
    configuracao: ConfiguracaoElegibilidadeUtilizada | None = None

    def as_dict(self):
        return {
            'resultado': self.resultado.value,
            'motivos': [motivo.as_dict() for motivo in self.motivos],
            'avisos': [aviso.as_dict() for aviso in self.avisos],
            'idade_na_avaliacao': self.idade_na_avaliacao,
            'idade_no_primeiro_dia': self.idade_no_primeiro_dia,
            'idade_no_ultimo_dia': self.idade_no_ultimo_dia,
            'primeiro_dia': self.primeiro_dia,
            'ultimo_dia': self.ultimo_dia,
            'configuracao': (
                self.configuracao.as_dict() if self.configuracao else None
            ),
        }


def _detalhe(codigo, mensagem):
    return DetalheElegibilidadeEncontrista(
        codigo=codigo,
        mensagem=mensagem,
    )


def _idade_em(data_nascimento, referencia):
    return referencia.year - data_nascimento.year - (
        (referencia.month, referencia.day)
        < (data_nascimento.month, data_nascimento.day)
    )


def _datas_oficiais(encontro):
    calendario = (
        CalendarioEncontro.objects
        .filter(
            encontro=encontro,
            vigente=True,
            oficializado_em__isnull=False,
        )
        .first()
    )
    if calendario is None:
        return None, None
    limites = calendario.dias.aggregate(
        primeiro_dia=Min('data'),
        ultimo_dia=Max('data'),
    )
    return limites['primeiro_dia'], limites['ultimo_dia']


def _configuracao_utilizada(configuracao):
    if configuracao is None:
        return None
    return ConfiguracaoElegibilidadeUtilizada(
        id=configuracao.pk,
        capacidade=configuracao.capacidade,
        idade_minima=configuracao.idade_minima,
        idade_maxima=configuracao.idade_maxima,
        inscricoes_abrem_em=configuracao.inscricoes_abrem_em,
        inscricoes_encerram_em=configuracao.inscricoes_encerram_em,
    )


def _concluiu_mesmo_tipo(pessoa, encontro):
    if encontro.tipo not in {
        Encontro.Tipo.ESCALADA,
        Encontro.Tipo.ESPPA,
    }:
        return False
    return ParticipacaoEncontro.objects.filter(
        pessoa=pessoa,
        tipo_encontro=encontro.tipo,
        resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
    ).exists()


def avaliar_elegibilidade_encontrista(
    *,
    pessoa,
    encontro,
    data_avaliacao=None,
):
    if not isinstance(pessoa, Pessoa) or pessoa.pk is None:
        raise ValidationError('Pessoa deve estar persistida.')
    if not isinstance(encontro, Encontro) or encontro.pk is None:
        raise ValidationError('Encontro deve estar persistido.')
    data_avaliacao = data_avaliacao or timezone.localdate()
    if not isinstance(data_avaliacao, date):
        raise ValidationError('Data de avaliação inválida.')

    if _concluiu_mesmo_tipo(pessoa, encontro):
        return AvaliacaoElegibilidadeEncontrista(
            resultado=ResultadoElegibilidadeEncontrista.INELEGIVEL,
            motivos=(
                _detalhe(
                    CodigoElegibilidadeEncontrista.CONCLUSAO_ANTERIOR_MESMO_TIPO,
                    'A Pessoa já concluiu este tipo de Encontro.',
                ),
            ),
        )

    configuracao = (
        ConfiguracaoEncontristasEncontro.objects
        .filter(encontro=encontro)
        .first()
    )
    primeiro_dia, ultimo_dia = _datas_oficiais(encontro)
    motivos_nao_avaliaveis = []
    if configuracao is None:
        motivos_nao_avaliaveis.append(_detalhe(
            CodigoElegibilidadeEncontrista.CONFIGURACAO_AUSENTE,
            'O Encontro não possui configuração de encontristas.',
        ))
    if primeiro_dia is None or ultimo_dia is None:
        motivos_nao_avaliaveis.append(_detalhe(
            CodigoElegibilidadeEncontrista.CALENDARIO_OFICIAL_AUSENTE,
            'O Encontro não possui calendário oficial vigente com dias.',
        ))
    if pessoa.data_nascimento is None:
        motivos_nao_avaliaveis.append(_detalhe(
            CodigoElegibilidadeEncontrista.DATA_NASCIMENTO_AUSENTE,
            'A Pessoa não possui data de nascimento para avaliação etária.',
        ))
    if motivos_nao_avaliaveis:
        return AvaliacaoElegibilidadeEncontrista(
            resultado=ResultadoElegibilidadeEncontrista.NAO_AVALIAVEL,
            motivos=tuple(motivos_nao_avaliaveis),
            primeiro_dia=primeiro_dia,
            ultimo_dia=ultimo_dia,
            configuracao=_configuracao_utilizada(configuracao),
        )

    idade_na_avaliacao = _idade_em(
        pessoa.data_nascimento,
        data_avaliacao,
    )
    idade_no_primeiro_dia = _idade_em(
        pessoa.data_nascimento,
        primeiro_dia,
    )
    idade_no_ultimo_dia = _idade_em(
        pessoa.data_nascimento,
        ultimo_dia,
    )
    contexto = {
        'idade_na_avaliacao': idade_na_avaliacao,
        'idade_no_primeiro_dia': idade_no_primeiro_dia,
        'idade_no_ultimo_dia': idade_no_ultimo_dia,
        'primeiro_dia': primeiro_dia,
        'ultimo_dia': ultimo_dia,
        'configuracao': _configuracao_utilizada(configuracao),
    }

    motivos = []
    if idade_no_ultimo_dia < configuracao.idade_minima:
        motivos.append(_detalhe(
            CodigoElegibilidadeEncontrista.IDADE_MINIMA_NAO_ATINGIDA,
            'A idade mínima não será atingida até o último dia oficial.',
        ))
    if idade_no_primeiro_dia > configuracao.idade_maxima:
        motivos.append(_detalhe(
            CodigoElegibilidadeEncontrista.IDADE_MAXIMA_EXCEDIDA,
            'A idade máxima já estará excedida no primeiro dia oficial.',
        ))
    if motivos:
        return AvaliacaoElegibilidadeEncontrista(
            resultado=ResultadoElegibilidadeEncontrista.INELEGIVEL,
            motivos=tuple(motivos),
            **contexto,
        )

    avisos = []
    if idade_na_avaliacao < configuracao.idade_minima:
        avisos.append(_detalhe(
            CodigoElegibilidadeEncontrista.IDADE_MINIMA_FUTURA,
            'A idade mínima será atingida até o último dia oficial.',
        ))
    return AvaliacaoElegibilidadeEncontrista(
        resultado=(
            ResultadoElegibilidadeEncontrista.ELEGIVEL_COM_AVISO
            if avisos
            else ResultadoElegibilidadeEncontrista.ELEGIVEL
        ),
        avisos=tuple(avisos),
        **contexto,
    )
