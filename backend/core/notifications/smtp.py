import smtplib
from dataclasses import dataclass, field
from socket import timeout as SocketTimeout

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone

from .contracts import (
    CanalEntregaConvite,
    CategoriaFalhaEntrega,
    PayloadEntregaConvite,
    ProviderEntregaConvite,
    ResultadoEntregaConvite,
)
from .validation import payload_basico_valido


@dataclass(frozen=True, slots=True)
class ConfiguracaoSMTP:
    host: str
    port: int
    username: str
    password: str = field(repr=False)
    from_email: str
    use_tls: bool
    use_ssl: bool
    timeout: float

    @classmethod
    def from_settings(cls):
        return cls(
            host=settings.SIA_SMTP_HOST,
            port=settings.SIA_SMTP_PORT,
            username=settings.SIA_SMTP_USERNAME,
            password=settings.SIA_SMTP_PASSWORD,
            from_email=settings.SIA_SMTP_FROM_EMAIL,
            use_tls=settings.SIA_SMTP_USE_TLS,
            use_ssl=settings.SIA_SMTP_USE_SSL,
            timeout=settings.SIA_SMTP_TIMEOUT,
        )

    def valida(self):
        basico_valido = bool(
            self.host.strip()
            and 0 < self.port <= 65535
            and self.from_email.strip()
            and self.timeout > 0
            and not (self.use_tls and self.use_ssl)
        )
        if not basico_valido:
            return False
        try:
            validate_email(self.from_email)
        except ValidationError:
            return False
        return True


class AdaptadorSMTPConvite:
    canal = CanalEntregaConvite.EMAIL
    provider = ProviderEntregaConvite.SMTP

    def __init__(self, configuracao=None):
        self.configuracao = configuracao or ConfiguracaoSMTP.from_settings()

    def _resultado_falha(self, categoria, codigo):
        return ResultadoEntregaConvite(
            sucesso=False,
            provider=self.provider,
            processado_em=timezone.now(),
            categoria_falha=categoria,
            codigo_erro=codigo,
        )

    def _payload_valido(self, payload):
        if not payload_basico_valido(payload):
            return False
        try:
            validate_email(payload.destinatario)
        except ValidationError:
            return False
        return True

    def _mensagem(self, payload, *, connection):
        prazo = timezone.localtime(payload.prazo_resposta).strftime(
            '%d/%m/%Y às %H:%M'
        )
        corpo = (
            'Movimento Escalada de Brasília\n\n'
            f'Você recebeu um convite para {payload.nome_encontro}.\n'
            'Acesse o link abaixo para responder ao convite até '
            f'{prazo}:\n\n{payload.link_convite}\n\n'
            'A confirmação registra apenas sua resposta ao convite; ela não '
            'representa presença ou participação concluída.'
        )
        return EmailMultiAlternatives(
            subject=f'Convite — {payload.nome_encontro}',
            body=corpo,
            from_email=self.configuracao.from_email,
            to=[payload.destinatario],
            connection=connection,
        )

    def entregar(self, payload: PayloadEntregaConvite):
        if not self.configuracao.valida():
            return self._resultado_falha(
                CategoriaFalhaEntrega.CONFIGURACAO,
                'smtp_configuracao_invalida',
            )
        if not self._payload_valido(payload):
            return self._resultado_falha(
                CategoriaFalhaEntrega.PAYLOAD,
                'smtp_payload_invalido',
            )

        try:
            connection = get_connection(
                backend='django.core.mail.backends.smtp.EmailBackend',
                host=self.configuracao.host,
                port=self.configuracao.port,
                username=self.configuracao.username or None,
                password=self.configuracao.password or None,
                use_tls=self.configuracao.use_tls,
                use_ssl=self.configuracao.use_ssl,
                timeout=self.configuracao.timeout,
                fail_silently=False,
            )
            enviados = self._mensagem(
                payload,
                connection=connection,
            ).send(fail_silently=False)
        except (TimeoutError, SocketTimeout):
            return self._resultado_falha(
                CategoriaFalhaEntrega.TEMPORARIA,
                'smtp_timeout',
            )
        except smtplib.SMTPAuthenticationError:
            return self._resultado_falha(
                CategoriaFalhaEntrega.PERMANENTE,
                'smtp_autenticacao',
            )
        except (smtplib.SMTPConnectError, ConnectionError, OSError):
            return self._resultado_falha(
                CategoriaFalhaEntrega.TEMPORARIA,
                'smtp_conexao',
            )
        except Exception:
            return self._resultado_falha(
                CategoriaFalhaEntrega.PERMANENTE,
                'smtp_falha',
            )

        if enviados != 1:
            return self._resultado_falha(
                CategoriaFalhaEntrega.TEMPORARIA,
                'smtp_nao_entregue',
            )
        return ResultadoEntregaConvite(
            sucesso=True,
            provider=self.provider,
            processado_em=timezone.now(),
        )
