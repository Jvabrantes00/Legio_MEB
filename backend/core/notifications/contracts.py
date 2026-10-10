from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable


class CanalEntregaConvite(StrEnum):
    EMAIL = 'email'
    WHATSAPP = 'whatsapp'


class ProviderEntregaConvite(StrEnum):
    SMTP = 'smtp'
    WHATSAPP_MOCK = 'whatsapp_mock'


class CategoriaFalhaEntrega(StrEnum):
    CONFIGURACAO = 'configuracao'
    PAYLOAD = 'payload'
    TEMPORARIA = 'temporaria'
    PERMANENTE = 'permanente'


@dataclass(frozen=True, slots=True)
class PayloadEntregaConvite:
    destinatario: str = field(repr=False)
    nome_encontro: str
    prazo_resposta: datetime
    link_convite: str = field(repr=False)


@dataclass(frozen=True, slots=True)
class ResultadoEntregaConvite:
    sucesso: bool
    provider: ProviderEntregaConvite
    processado_em: datetime
    categoria_falha: CategoriaFalhaEntrega | None = None
    codigo_erro: str = ''

    def __post_init__(self):
        falha_informada = self.categoria_falha is not None and bool(
            self.codigo_erro
        )
        if self.sucesso and (
            self.categoria_falha is not None or self.codigo_erro
        ):
            raise ValueError('Resultado de sucesso não aceita dados de falha.')
        if not self.sucesso and not falha_informada:
            raise ValueError('Resultado de falha exige categoria e código.')


@runtime_checkable
class AdaptadorEntregaConvite(Protocol):
    canal: CanalEntregaConvite
    provider: ProviderEntregaConvite

    def entregar(
        self,
        payload: PayloadEntregaConvite,
    ) -> ResultadoEntregaConvite:
        ...
