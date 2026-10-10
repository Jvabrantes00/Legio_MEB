from datetime import datetime
from urllib.parse import urlsplit

from django.utils import timezone

from .contracts import PayloadEntregaConvite


def payload_basico_valido(payload):
    if not isinstance(payload, PayloadEntregaConvite):
        return False
    if not payload.destinatario.strip() or not payload.nome_encontro.strip():
        return False
    if '\r' in payload.nome_encontro or '\n' in payload.nome_encontro:
        return False
    if (
        not isinstance(payload.prazo_resposta, datetime)
        or timezone.is_naive(payload.prazo_resposta)
    ):
        return False
    link = urlsplit(payload.link_convite)
    return (
        link.scheme in {'http', 'https'}
        and bool(link.netloc)
        and link.username is None
        and link.password is None
    )
