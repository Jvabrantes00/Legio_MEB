from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class TipoConteudoFormativo(StrEnum):
    PALESTRA = 'palestra'
    BATE_PAPO = 'bate_papo'


TIPO_CONTEUDO_FORMATIVO_CHOICES = (
    (TipoConteudoFormativo.PALESTRA.value, 'Palestra'),
    (TipoConteudoFormativo.BATE_PAPO.value, 'Bate-papo'),
)


@dataclass(frozen=True, slots=True)
class TemaFormativo:
    codigo: str
    tipo_conteudo: TipoConteudoFormativo
    titulo: str
    tipos_encontro: frozenset[str]


# O catálogo permanece vazio até que os temas reais sejam fornecidos. Novas
# entradas serão mudanças de código, não dados ou choices persistidos no model.
TEMAS_FORMATIVOS: Mapping[str, TemaFormativo] = MappingProxyType({})
