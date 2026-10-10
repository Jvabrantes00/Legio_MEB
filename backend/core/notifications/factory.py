from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .contracts import CanalEntregaConvite
from .smtp import AdaptadorSMTPConvite
from .whatsapp_mock import AdaptadorWhatsAppMock


def resolver_adaptador_entrega_convite(canal):
    try:
        canal = CanalEntregaConvite(canal)
    except (TypeError, ValueError) as error:
        raise ImproperlyConfigured(
            'Canal de entrega de convite não suportado.'
        ) from error

    if canal == CanalEntregaConvite.EMAIL:
        if settings.SIA_INVITATION_EMAIL_BACKEND != 'smtp':
            raise ImproperlyConfigured(
                'Adapter de e-mail de convites não configurado.'
            )
        return AdaptadorSMTPConvite()

    if settings.SIA_WHATSAPP_BACKEND != 'mock':
        raise ImproperlyConfigured(
            'Adapter de WhatsApp de convites não configurado.'
        )
    return AdaptadorWhatsAppMock()
