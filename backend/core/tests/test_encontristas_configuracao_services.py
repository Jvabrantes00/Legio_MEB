from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    EventoAuditoriaEncontro,
    Pessoa,
)
from core.roles import SiaRole
from core.services.configuracao_encontristas import (
    alterar_configuracao_encontristas,
    consultar_configuracao_encontristas,
    criar_configuracao_encontristas,
)
from core.tests.factories import make_encontro


class ConfiguracaoEncontristasServiceTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro()
        self.abertura = timezone.make_aware(datetime(2030, 1, 1, 8, 0))
        self.encerramento = self.abertura + timedelta(days=30)
        self.diretoria = self._usuario_com_papel(
            'diretoria_configuracao',
            SiaRole.DIRETORIA,
        )
        self.suporte = self._usuario_com_papel(
            'suporte_configuracao',
            SiaRole.SUPORTE,
        )
        self.fichas = self._usuario_com_papel(
            'fichas_configuracao',
            SiaRole.FICHAS,
        )
        self.sem_papel = get_user_model().objects.create_user(
            username='sem_papel_configuracao',
        )

    def _usuario_com_papel(self, username, papel):
        usuario = get_user_model().objects.create_user(username=username)
        grupo, _ = Group.objects.get_or_create(name=papel.value)
        usuario.groups.add(grupo)
        return usuario

    def _dados(self, **overrides):
        valores = {
            'capacidade': 80,
            'idade_minima': 18,
            'idade_maxima': 25,
            'inscricoes_abrem_em': self.abertura,
            'inscricoes_encerram_em': self.encerramento,
        }
        valores.update(overrides)
        return valores

    def _criar_diretamente(self, **overrides):
        return ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            **self._dados(**overrides),
        )

    def test_diretoria_e_suporte_podem_criar_configuracao(self):
        for usuario in (self.diretoria, self.suporte):
            with self.subTest(usuario=usuario.username):
                encontro = make_encontro()
                configuracao = criar_configuracao_encontristas(
                    usuario=usuario,
                    encontro=encontro,
                    **self._dados(),
                )

                self.assertEqual(configuracao.encontro, encontro)
                self.assertEqual(configuracao.capacidade, 80)

    def test_diretoria_e_suporte_podem_alterar_configuracao(self):
        for usuario in (self.diretoria, self.suporte):
            with self.subTest(usuario=usuario.username):
                encontro = make_encontro()
                configuracao = ConfiguracaoEncontristasEncontro.objects.create(
                    encontro=encontro,
                    **self._dados(),
                )

                alterada = alterar_configuracao_encontristas(
                    usuario=usuario,
                    configuracao=configuracao,
                    capacidade=90,
                )

                self.assertEqual(alterada.capacidade, 90)

    def test_fichas_consulta_mas_nao_altera_configuracao(self):
        configuracao = self._criar_diretamente()

        consultada = consultar_configuracao_encontristas(
            usuario=self.fichas,
            encontro=self.encontro,
        )

        self.assertEqual(consultada, configuracao)
        with self.assertRaises(PermissionDenied):
            alterar_configuracao_encontristas(
                usuario=self.fichas,
                configuracao=configuracao,
                capacidade=90,
            )

    def test_default_deny_impede_consulta_e_alteracao(self):
        configuracao = self._criar_diretamente()

        with self.assertRaises(PermissionDenied):
            consultar_configuracao_encontristas(
                usuario=self.sem_papel,
                encontro=self.encontro,
            )
        with self.assertRaises(PermissionDenied):
            alterar_configuracao_encontristas(
                usuario=self.sem_papel,
                configuracao=configuracao,
                capacidade=90,
            )

    def test_service_rejeita_invariantes_invalidas(self):
        casos = (
            {'capacidade': 0},
            {'idade_minima': 26, 'idade_maxima': 25},
            {'inscricoes_encerram_em': self.abertura},
        )

        for indice, valores in enumerate(casos):
            with self.subTest(valores=valores):
                encontro = make_encontro(encontro=f'Escalada inválida {indice}')
                with self.assertRaises(ValidationError):
                    criar_configuracao_encontristas(
                        usuario=self.diretoria,
                        encontro=encontro,
                        **self._dados(**valores),
                    )

        self.assertFalse(
            ConfiguracaoEncontristasEncontro.objects.filter(
                encontro__encontro__startswith='Escalada inválida',
            ).exists()
        )

    def test_reducao_nao_pode_ficar_abaixo_da_ocupacao_confirmada(self):
        configuracao = self._criar_diretamente(capacidade=2)
        for numero in range(2):
            ConviteEncontro.objects.create(
                pessoa=Pessoa.objects.create(nome=f'Pessoa confirmada {numero}'),
                encontro=self.encontro,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
                status=ConviteEncontro.Status.CONFIRMADO,
            )

        with self.assertRaisesMessage(
            ValidationError,
            'ocupação confirmada atual (2)',
        ):
            alterar_configuracao_encontristas(
                usuario=self.diretoria,
                configuracao=configuracao,
                capacidade=1,
            )

        configuracao.refresh_from_db()
        self.assertEqual(configuracao.capacidade, 2)

    def test_aumento_de_capacidade_e_permitido_e_auditado(self):
        configuracao = self._criar_diretamente(capacidade=2)

        alterada = alterar_configuracao_encontristas(
            usuario=self.suporte,
            configuracao=configuracao,
            capacidade=3,
        )

        evento = EventoAuditoriaEncontro.objects.get(
            fato='configuracao_encontristas.alterada',
        )
        self.assertEqual(alterada.capacidade, 3)
        self.assertEqual(evento.encontro, self.encontro)
        self.assertEqual(evento.ator, self.suporte)
        self.assertEqual(evento.valor_anterior, {'capacidade': 2})
        self.assertEqual(evento.valor_novo, {'capacidade': 3})
        self.assertIsNotNone(evento.criado_em)
        self.assertEqual(evento.justificativa, '')

    def test_criacao_registra_auditoria_sem_dados_pessoais(self):
        configuracao = criar_configuracao_encontristas(
            usuario=self.diretoria,
            encontro=self.encontro,
            **self._dados(),
        )

        evento = EventoAuditoriaEncontro.objects.get(
            fato='configuracao_encontristas.criada',
        )
        self.assertEqual(evento.objeto_id, str(configuracao.pk))
        self.assertEqual(evento.valor_anterior, {})
        self.assertEqual(set(evento.valor_novo), {
            'capacidade',
            'idade_minima',
            'idade_maxima',
            'inscricoes_abrem_em',
            'inscricoes_encerram_em',
        })

    def test_falha_na_auditoria_reverte_alteracao(self):
        configuracao = self._criar_diretamente(capacidade=80)

        with patch(
            'core.services.configuracao_encontristas.'
            'registrar_evento_auditoria_encontro',
            side_effect=RuntimeError('Falha controlada na auditoria.'),
        ):
            with self.assertRaises(RuntimeError):
                alterar_configuracao_encontristas(
                    usuario=self.diretoria,
                    configuracao=configuracao,
                    capacidade=90,
                )

        configuracao.refresh_from_db()
        self.assertEqual(configuracao.capacidade, 80)

