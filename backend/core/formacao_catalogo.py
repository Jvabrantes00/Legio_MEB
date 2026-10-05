from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping


class TipoConteudoFormativo(StrEnum):
    PALESTRA = 'palestra'
    BATE_PAPO = 'bate_papo'


class BlocoFormativo(StrEnum):
    PRE_ESCALADA = 'PRE_ESCALADA'
    PRE_AVC = 'PRE_AVC'
    SEXTA = 'SEXTA'
    SABADO = 'SABADO'
    DOMINGO = 'DOMINGO'


TIPO_CONTEUDO_FORMATIVO_CHOICES = (
    (TipoConteudoFormativo.PALESTRA.value, 'Palestra'),
    (TipoConteudoFormativo.BATE_PAPO.value, 'Bate-papo'),
)


@dataclass(frozen=True, slots=True)
class TemaFormativo:
    codigo: str
    tipo_conteudo: TipoConteudoFormativo
    titulo: str
    ordem: int
    bloco: BlocoFormativo
    tipos_encontro: frozenset[str]


TIPOS_PALESTRA = frozenset({'Escalada', 'Esppa'})
TIPOS_BATE_PAPO = frozenset({'AVC'})


TEMAS_FORMATIVOS: Mapping[str, TemaFormativo] = MappingProxyType({
    'PALESTRA_SER_PESSOA': TemaFormativo(
        codigo='PALESTRA_SER_PESSOA',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Ser Pessoa',
        ordem=1,
        bloco=BlocoFormativo.PRE_ESCALADA,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'PALESTRA_VALORES_CONTRAVALORES': TemaFormativo(
        codigo='PALESTRA_VALORES_CONTRAVALORES',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Valores e Contravalores',
        ordem=2,
        bloco=BlocoFormativo.PRE_ESCALADA,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'PALESTRA_AMOR_DE_DEUS': TemaFormativo(
        codigo='PALESTRA_AMOR_DE_DEUS',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Amor de Deus',
        ordem=3,
        bloco=BlocoFormativo.PRE_ESCALADA,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'PALESTRA_JESUS_CRISTO': TemaFormativo(
        codigo='PALESTRA_JESUS_CRISTO',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Jesus Cristo',
        ordem=4,
        bloco=BlocoFormativo.SABADO,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'PALESTRA_AMOR_DE_MARIA': TemaFormativo(
        codigo='PALESTRA_AMOR_DE_MARIA',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Amor de Maria',
        ordem=5,
        bloco=BlocoFormativo.SABADO,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'PALESTRA_PERDAO': TemaFormativo(
        codigo='PALESTRA_PERDAO',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Perdão',
        ordem=6,
        bloco=BlocoFormativo.SABADO,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'PALESTRA_AMOR_SEXUALIDADE': TemaFormativo(
        codigo='PALESTRA_AMOR_SEXUALIDADE',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Amor e Sexualidade',
        ordem=7,
        bloco=BlocoFormativo.DOMINGO,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'PALESTRA_FAMILIA': TemaFormativo(
        codigo='PALESTRA_FAMILIA',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Família',
        ordem=8,
        bloco=BlocoFormativo.DOMINGO,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'PALESTRA_ESTRUTURA_MOVIMENTO': TemaFormativo(
        codigo='PALESTRA_ESTRUTURA_MOVIMENTO',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Estrutura do Movimento',
        ordem=9,
        bloco=BlocoFormativo.DOMINGO,
        tipos_encontro=TIPOS_PALESTRA,
    ),
    'BATE_PAPO_JESUS_DEUS_HOMEM': TemaFormativo(
        codigo='BATE_PAPO_JESUS_DEUS_HOMEM',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='Jesus, Deus e Homem',
        ordem=1,
        bloco=BlocoFormativo.PRE_AVC,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_DEPOIMENTO_SANTO_1': TemaFormativo(
        codigo='BATE_PAPO_DEPOIMENTO_SANTO_1',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='1º Depoimento de um santo',
        ordem=2,
        bloco=BlocoFormativo.PRE_AVC,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_DEPOIMENTO_SANTO_2': TemaFormativo(
        codigo='BATE_PAPO_DEPOIMENTO_SANTO_2',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='2º Depoimento de um santo',
        ordem=3,
        bloco=BlocoFormativo.PRE_AVC,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_DEPOIMENTO_SANTO_3': TemaFormativo(
        codigo='BATE_PAPO_DEPOIMENTO_SANTO_3',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='3º Depoimento de um santo',
        ordem=4,
        bloco=BlocoFormativo.PRE_AVC,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_ALIANCAS_DEUS_HOMEM': TemaFormativo(
        codigo='BATE_PAPO_ALIANCAS_DEUS_HOMEM',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='As alianças de Deus com o homem',
        ordem=5,
        bloco=BlocoFormativo.SEXTA,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_SER_PROFETA': TemaFormativo(
        codigo='BATE_PAPO_SER_PROFETA',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='Ser profeta',
        ordem=6,
        bloco=BlocoFormativo.SEXTA,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_NECESSIDADES_SER_HUMANO': TemaFormativo(
        codigo='BATE_PAPO_NECESSIDADES_SER_HUMANO',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='As necessidades do ser humano',
        ordem=7,
        bloco=BlocoFormativo.SABADO,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_IMPORTANCIA_SACRAMENTOS_PROFETA': TemaFormativo(
        codigo='BATE_PAPO_IMPORTANCIA_SACRAMENTOS_PROFETA',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='A importância dos sacramentos para o profeta',
        ordem=8,
        bloco=BlocoFormativo.SABADO,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_CAMPANHA_FRATERNIDADE': TemaFormativo(
        codigo='BATE_PAPO_CAMPANHA_FRATERNIDADE',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='Campanha da Fraternidade',
        ordem=9,
        bloco=BlocoFormativo.DOMINGO,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_BIOGRAFIA_SANTO': TemaFormativo(
        codigo='BATE_PAPO_BIOGRAFIA_SANTO',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='Biografia de um santo (5 pessoas)',
        ordem=10,
        bloco=BlocoFormativo.DOMINGO,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
    'BATE_PAPO_PROFETA_IGREJA': TemaFormativo(
        codigo='BATE_PAPO_PROFETA_IGREJA',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='Profeta e a igreja',
        ordem=11,
        bloco=BlocoFormativo.DOMINGO,
        tipos_encontro=TIPOS_BATE_PAPO,
    ),
})
