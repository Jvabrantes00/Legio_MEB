import smtplib
from dataclasses import fields
from datetime import datetime
from socket import create_connection
from unittest.mock import patch

from django.core.exceptions import ImproperlyConfigured
from django.test import SimpleTestCase, override_settings
from django.utils import timezone

from core.notifications import (
    AdaptadorEntregaConvite,
    CanalEntregaConvite,
    CategoriaFalhaEntrega,
    PayloadEntregaConvite,
    ProviderEntregaConvite,
    ResultadoEntregaConvite,
    resolver_adaptador_entrega_convite,
)
from core.notifications.smtp import AdaptadorSMTPConvite, ConfiguracaoSMTP
from core.notifications.whatsapp_mock import AdaptadorWhatsAppMock


SEGREDO = 'SECRET_INVITATION_TOKEN_DO_NOT_LOG'


class ConexaoEmailFake:
    def __init__(self, *, retorno=1, erro=None):
        self.retorno = retorno
        self.erro = erro
        self.mensagens = []

    def send_messages(self, mensagens):
        self.mensagens.extend(mensagens)
        if self.erro is not None:
            raise self.erro
        return self.retorno


def configuracao_smtp(**overrides):
    valores = {
        'host': 'smtp.example.test',
        'port': 2525,
        'username': 'usuario-tecnico',
        'password': 'senha-smtp-secreta',
        'from_email': 'convites@example.test',
        'use_tls': True,
        'use_ssl': False,
        'timeout': 7.5,
    }
    valores.update(overrides)
    return ConfiguracaoSMTP(**valores)


def payload_convite(**overrides):
    valores = {
        'destinatario': 'destinatario@example.test',
        'nome_encontro': 'Escalada 2030',
        'prazo_resposta': timezone.make_aware(datetime(2030, 5, 20, 18, 0)),
        'link_convite': f'https://app.example.test/convites/{SEGREDO}',
    }
    valores.update(overrides)
    return PayloadEntregaConvite(**valores)


class AdaptadorSMTPConviteTests(SimpleTestCase):
    def test_payload_possui_somente_campos_minimos_e_oculta_segredos_no_repr(self):
        payload = payload_convite()

        self.assertEqual(
            {campo.name for campo in fields(PayloadEntregaConvite)},
            {
                'destinatario',
                'nome_encontro',
                'prazo_resposta',
                'link_convite',
            },
        )
        self.assertNotIn(SEGREDO, repr(payload))
        self.assertNotIn(payload.destinatario, repr(payload))

    @patch('core.notifications.smtp.get_connection')
    def test_sucesso_smtp_usa_remetente_timeout_e_conteudo_neutro(self, get_connection):
        conexao = ConexaoEmailFake()
        get_connection.return_value = conexao
        adapter = AdaptadorSMTPConvite(configuracao_smtp())

        resultado = adapter.entregar(payload_convite())

        self.assertTrue(resultado.sucesso)
        self.assertEqual(resultado.provider, ProviderEntregaConvite.SMTP)
        self.assertIsNone(resultado.categoria_falha)
        get_connection.assert_called_once_with(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host='smtp.example.test',
            port=2525,
            username='usuario-tecnico',
            password='senha-smtp-secreta',
            use_tls=True,
            use_ssl=False,
            timeout=7.5,
            fail_silently=False,
        )
        mensagem = conexao.mensagens[0]
        self.assertEqual(mensagem.from_email, 'convites@example.test')
        self.assertIn('Movimento Escalada de Brasília', mensagem.body)
        self.assertIn('Escalada 2030', mensagem.body)
        self.assertIn(SEGREDO, mensagem.body)
        self.assertIn('não representa presença', mensagem.body)
        self.assertNotIn('CPF', mensagem.body)
        self.assertNotIn('nascimento', mensagem.body)

    @patch('core.notifications.smtp.get_connection')
    def test_falha_smtp_e_sanitizada(self, get_connection):
        get_connection.return_value = ConexaoEmailFake(
            erro=RuntimeError(
                f'falha para destinatario@example.test com {SEGREDO}'
            )
        )

        with self.assertNoLogs(level='WARNING'):
            resultado = AdaptadorSMTPConvite(
                configuracao_smtp()
            ).entregar(payload_convite())

        self.assertFalse(resultado.sucesso)
        self.assertEqual(
            resultado.categoria_falha,
            CategoriaFalhaEntrega.PERMANENTE,
        )
        self.assertEqual(resultado.codigo_erro, 'smtp_falha')
        self.assertNotIn(SEGREDO, repr(resultado))
        self.assertNotIn('destinatario@example.test', repr(resultado))
        self.assertNotIn('senha-smtp-secreta', repr(resultado))

    @patch('core.notifications.smtp.get_connection')
    def test_timeout_smtp_e_falha_temporaria(self, get_connection):
        get_connection.return_value = ConexaoEmailFake(erro=TimeoutError())

        resultado = AdaptadorSMTPConvite(
            configuracao_smtp()
        ).entregar(payload_convite())

        self.assertFalse(resultado.sucesso)
        self.assertEqual(
            resultado.categoria_falha,
            CategoriaFalhaEntrega.TEMPORARIA,
        )
        self.assertEqual(resultado.codigo_erro, 'smtp_timeout')

    @patch('core.notifications.smtp.get_connection')
    def test_autenticacao_nao_expoe_credencial(self, get_connection):
        get_connection.return_value = ConexaoEmailFake(
            erro=smtplib.SMTPAuthenticationError(
                535,
                b'senha-smtp-secreta recusada',
            )
        )

        configuracao = configuracao_smtp()
        resultado = AdaptadorSMTPConvite(configuracao).entregar(
            payload_convite()
        )

        self.assertEqual(resultado.codigo_erro, 'smtp_autenticacao')
        self.assertNotIn('senha-smtp-secreta', repr(resultado))
        self.assertNotIn('senha-smtp-secreta', repr(configuracao))

    @patch('core.notifications.smtp.get_connection')
    def test_configuracao_ausente_falha_sem_tentar_rede(self, get_connection):
        resultado = AdaptadorSMTPConvite(
            configuracao_smtp(host='')
        ).entregar(payload_convite())

        self.assertFalse(resultado.sucesso)
        self.assertEqual(
            resultado.categoria_falha,
            CategoriaFalhaEntrega.CONFIGURACAO,
        )
        self.assertEqual(resultado.codigo_erro, 'smtp_configuracao_invalida')
        get_connection.assert_not_called()

    @patch('core.notifications.smtp.get_connection')
    def test_payload_invalido_nao_abre_conexao(self, get_connection):
        resultado = AdaptadorSMTPConvite(
            configuracao_smtp()
        ).entregar(payload_convite(destinatario='email-invalido'))

        self.assertEqual(resultado.codigo_erro, 'smtp_payload_invalido')
        get_connection.assert_not_called()


class AdaptadorWhatsAppMockTests(SimpleTestCase):
    def test_sucesso_falha_e_timeout_sao_deterministicos(self):
        casos = (
            ('sucesso', True, None, ''),
            (
                'falha',
                False,
                CategoriaFalhaEntrega.PERMANENTE,
                'whatsapp_mock_falha',
            ),
            (
                'timeout',
                False,
                CategoriaFalhaEntrega.TEMPORARIA,
                'whatsapp_mock_timeout',
            ),
        )
        for modo, sucesso, categoria, codigo in casos:
            with self.subTest(modo=modo):
                resultado = AdaptadorWhatsAppMock(modo=modo).entregar(
                    payload_convite(destinatario='+5561999999999')
                )
                self.assertEqual(resultado.sucesso, sucesso)
                self.assertEqual(resultado.categoria_falha, categoria)
                self.assertEqual(resultado.codigo_erro, codigo)

    def test_mock_nao_abre_conexao_externa(self):
        with patch(
            'socket.create_connection',
            wraps=create_connection,
        ) as conexao:
            resultado = AdaptadorWhatsAppMock(modo='sucesso').entregar(
                payload_convite(destinatario='+5561999999999')
            )

        self.assertTrue(resultado.sucesso)
        conexao.assert_not_called()

    def test_modo_invalido_falha_sem_fingir_sucesso(self):
        resultado = AdaptadorWhatsAppMock(modo='desconhecido').entregar(
            payload_convite(destinatario='+5561999999999')
        )

        self.assertFalse(resultado.sucesso)
        self.assertEqual(
            resultado.categoria_falha,
            CategoriaFalhaEntrega.CONFIGURACAO,
        )


class ContratoEntregaConviteTests(SimpleTestCase):
    @override_settings(
        SIA_INVITATION_EMAIL_BACKEND='smtp',
        SIA_SMTP_HOST='smtp.example.test',
        SIA_SMTP_FROM_EMAIL='convites@example.test',
        SIA_WHATSAPP_BACKEND='mock',
        SIA_WHATSAPP_MOCK_MODE='sucesso',
    )
    def test_factory_resolve_adapters_pela_interface(self):
        email = resolver_adaptador_entrega_convite(
            CanalEntregaConvite.EMAIL
        )
        whatsapp = resolver_adaptador_entrega_convite(
            CanalEntregaConvite.WHATSAPP
        )

        self.assertIsInstance(email, AdaptadorEntregaConvite)
        self.assertIsInstance(whatsapp, AdaptadorEntregaConvite)
        self.assertEqual(email.canal, CanalEntregaConvite.EMAIL)
        self.assertEqual(whatsapp.canal, CanalEntregaConvite.WHATSAPP)

    @override_settings(SIA_INVITATION_EMAIL_BACKEND='desconhecido')
    def test_factory_nao_faz_fallback_silencioso(self):
        with self.assertRaisesMessage(
            ImproperlyConfigured,
            'Adapter de e-mail de convites não configurado.',
        ):
            resolver_adaptador_entrega_convite(CanalEntregaConvite.EMAIL)

    def test_resultado_e_tipado_e_substituivel(self):
        class AdaptadorFake:
            canal = CanalEntregaConvite.EMAIL
            provider = ProviderEntregaConvite.SMTP

            def entregar(self, payload):
                return ResultadoEntregaConvite(
                    sucesso=True,
                    provider=self.provider,
                    processado_em=timezone.now(),
                )

        adapter: AdaptadorEntregaConvite = AdaptadorFake()
        resultado = adapter.entregar(payload_convite())

        self.assertIsInstance(resultado, ResultadoEntregaConvite)
        self.assertTrue(resultado.sucesso)
