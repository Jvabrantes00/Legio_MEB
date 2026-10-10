from django.conf import settings
from django.utils import timezone

from .contracts import (
    CanalEntregaConvite,
    CategoriaFalhaEntrega,
    PayloadEntregaConvite,
    ProviderEntregaConvite,
    ResultadoEntregaConvite,
)
from .validation import payload_basico_valido


MODOS_SUPORTADOS = frozenset({'sucesso', 'falha', 'timeout'})


class AdaptadorWhatsAppMock:
    canal = CanalEntregaConvite.WHATSAPP
    provider = ProviderEntregaConvite.WHATSAPP_MOCK

    def __init__(self, modo=None):
        self.modo = modo or settings.SIA_WHATSAPP_MOCK_MODE

    def entregar(self, payload: PayloadEntregaConvite):
        instante = timezone.now()
        if self.modo not in MODOS_SUPORTADOS:
            return ResultadoEntregaConvite(
                sucesso=False,
                provider=self.provider,
                processado_em=instante,
                categoria_falha=CategoriaFalhaEntrega.CONFIGURACAO,
                codigo_erro='whatsapp_mock_configuracao_invalida',
            )
        if not payload_basico_valido(payload):
            return ResultadoEntregaConvite(
                sucesso=False,
                provider=self.provider,
                processado_em=instante,
                categoria_falha=CategoriaFalhaEntrega.PAYLOAD,
                codigo_erro='whatsapp_mock_payload_invalido',
            )
        if self.modo == 'timeout':
            return ResultadoEntregaConvite(
                sucesso=False,
                provider=self.provider,
                processado_em=instante,
                categoria_falha=CategoriaFalhaEntrega.TEMPORARIA,
                codigo_erro='whatsapp_mock_timeout',
            )
        if self.modo == 'falha':
            return ResultadoEntregaConvite(
                sucesso=False,
                provider=self.provider,
                processado_em=instante,
                categoria_falha=CategoriaFalhaEntrega.PERMANENTE,
                codigo_erro='whatsapp_mock_falha',
            )
        return ResultadoEntregaConvite(
            sucesso=True,
            provider=self.provider,
            processado_em=instante,
        )
