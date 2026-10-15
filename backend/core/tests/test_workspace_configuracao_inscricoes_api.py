from datetime import datetime, timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from core.models import (
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    Encontro,
    Pessoa,
)
from core.permissions import pode_resolver_vaga_pre_encontro
from core.roles import SiaRole
from core.tests.factories import make_encontro


class ConfiguracaoInscricoesWorkspaceApiTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.abertura = timezone.make_aware(datetime(2030, 1, 1, 8))
        self.encerramento = self.abertura + timedelta(days=30)
        self.diretoria = self._usuario('config-diretoria', SiaRole.DIRETORIA)
        self.fichas = self._usuario('config-fichas', SiaRole.FICHAS)
        self.suporte = self._usuario('config-suporte', SiaRole.SUPORTE)
        self.comunicacao = self._usuario(
            'config-comunicacao',
            SiaRole.COMUNICACAO,
        )
        self.superuser = User.objects.create_superuser(
            'config-root',
            email='root@example.test',
            password='senha',
        )

    def _usuario(self, username, role):
        usuario = User.objects.create_user(username)
        grupo, _ = Group.objects.get_or_create(name=role.value)
        usuario.groups.add(grupo)
        return usuario

    def _url(self, encontro=None):
        encontro = encontro or self.encontro
        return (
            f'/api/encontros/{encontro.pk}/workspace/'
            'inscricoes/configuracao/'
        )

    def _dados(self, **overrides):
        dados = {
            'capacidade': 30,
            'idade_minima': 15,
            'idade_maxima': 18,
            'inscricoes_abrem_em': self.abertura.isoformat(),
            'inscricoes_encerram_em': self.encerramento.isoformat(),
        }
        dados.update(overrides)
        return dados

    def _configuracao(self, encontro=None, **overrides):
        dados = self._dados(**overrides)
        dados['inscricoes_abrem_em'] = datetime.fromisoformat(
            dados['inscricoes_abrem_em'],
        )
        dados['inscricoes_encerram_em'] = datetime.fromisoformat(
            dados['inscricoes_encerram_em'],
        )
        return ConfiguracaoEncontristasEncontro.objects.create(
            encontro=encontro or self.encontro,
            **dados,
        )

    def _auth(self, usuario):
        self.client.force_authenticate(usuario)

    def test_get_representa_ausencia_explicitamente(self):
        self._auth(self.fichas)
        resposta = self.client.get(self._url())
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data, {
            'configurado': False,
            'capacidade': None,
            'idade_minima': None,
            'idade_maxima': None,
            'inscricoes_abrem_em': None,
            'inscricoes_encerram_em': None,
            'public_id': None,
            'status_janela': None,
        })

    def test_post_cria_com_public_id_automatico_e_post_duplicado_falha(self):
        self._auth(self.fichas)
        resposta = self.client.post(self._url(), self._dados(), format='json')
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertTrue(resposta.data['configurado'])
        self.assertIsNotNone(resposta.data['public_id'])
        self.assertEqual(
            ConfiguracaoEncontristasEncontro.objects.filter(
                encontro=self.encontro,
            ).count(),
            1,
        )
        duplicada = self.client.post(self._url(), self._dados(), format='json')
        self.assertEqual(duplicada.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            ConfiguracaoEncontristasEncontro.objects.filter(
                encontro=self.encontro,
            ).count(),
            1,
        )

    def test_public_id_e_somente_leitura_em_post_e_patch(self):
        self._auth(self.diretoria)
        payload = self._dados(public_id='11111111-1111-1111-1111-111111111111')
        self.assertEqual(
            self.client.post(self._url(), payload, format='json').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        configuracao = self._configuracao()
        anterior = configuracao.public_id
        resposta = self.client.patch(
            self._url(),
            {'public_id': '22222222-2222-2222-2222-222222222222'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        configuracao.refresh_from_db()
        self.assertEqual(configuracao.public_id, anterior)

    def test_patch_atualiza_todos_os_campos_em_uma_operacao(self):
        configuracao = self._configuracao()
        public_id = configuracao.public_id
        self._auth(self.fichas)
        novos = self._dados(
            capacidade=40,
            idade_minima=16,
            idade_maxima=20,
            inscricoes_abrem_em=(self.abertura + timedelta(days=1)).isoformat(),
            inscricoes_encerram_em=(self.encerramento + timedelta(days=1)).isoformat(),
        )
        resposta = self.client.patch(self._url(), novos, format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        configuracao.refresh_from_db()
        self.assertEqual(configuracao.capacidade, 40)
        self.assertEqual(configuracao.idade_minima, 16)
        self.assertEqual(configuracao.idade_maxima, 20)
        self.assertEqual(configuracao.public_id, public_id)

    def test_invariantes_e_ocupacao_continuam_no_backend(self):
        self._auth(self.diretoria)
        for payload in (
            self._dados(idade_minima=19, idade_maxima=18),
            self._dados(
                inscricoes_encerram_em=self.abertura.isoformat(),
            ),
        ):
            with self.subTest(payload=payload):
                encontro = make_encontro()
                resposta = self.client.post(
                    self._url(encontro),
                    payload,
                    format='json',
                )
                self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)

        configuracao = self._configuracao(capacidade=2)
        for indice in range(2):
            ConviteEncontro.objects.create(
                pessoa=Pessoa.objects.create(nome=f'Confirmada {indice}'),
                encontro=self.encontro,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
                status=ConviteEncontro.Status.CONFIRMADO,
            )
        resposta = self.client.patch(
            self._url(),
            {'capacidade': 1},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        configuracao.refresh_from_db()
        self.assertEqual(configuracao.capacidade, 2)

    def test_diretoria_fichas_suporte_e_superuser_podem_configurar(self):
        for indice, usuario in enumerate((
            self.diretoria,
            self.fichas,
            self.suporte,
            self.superuser,
        )):
            with self.subTest(usuario=usuario.username):
                encontro = make_encontro(encontro=f'Configuração {indice}')
                self._auth(usuario)
                resposta = self.client.post(
                    self._url(encontro),
                    self._dados(),
                    format='json',
                )
                self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)

    def test_outro_papel_permanece_default_deny(self):
        self._auth(self.comunicacao)
        self.assertEqual(
            self.client.get(self._url()).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                self._url(),
                self._dados(),
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_nested_ausente_retorna_404(self):
        self._auth(self.diretoria)
        url_inexistente = (
            '/api/encontros/999999/workspace/inscricoes/configuracao/'
        )
        self.assertEqual(
            self.client.get(url_inexistente).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.patch(self._url(), self._dados(), format='json').status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_status_da_janela_e_derivado_no_backend(self):
        configuracao = self._configuracao()
        self._auth(self.fichas)
        casos = (
            (self.abertura - timedelta(seconds=1), 'ainda_nao_abriu'),
            (self.abertura, 'abertas'),
            (self.encerramento + timedelta(seconds=1), 'encerradas'),
        )
        for momento, esperado in casos:
            with self.subTest(esperado=esperado), patch(
                'core.services.configuracao_encontristas.timezone.now',
                return_value=momento,
            ):
                resposta = self.client.get(self._url())
                self.assertEqual(resposta.data['status_janela'], esperado)
                self.assertEqual(
                    resposta.data['public_id'],
                    str(configuracao.public_id),
                )

    def test_summary_alerta_ausencia_e_reflete_configuracao(self):
        self._auth(self.fichas)
        summary_url = f'/api/encontros/{self.encontro.pk}/workspace/'
        sem_configuracao = self.client.get(summary_url)
        self.assertIsNone(sem_configuracao.data['pre_encontro']['capacidade'])
        self.assertIn(
            {
                'codigo': 'INSCRICOES_NAO_CONFIGURADAS',
                'mensagem': 'Inscrições ainda não configuradas.',
            },
            sem_configuracao.data['alertas'],
        )
        self._configuracao()
        com_configuracao = self.client.get(summary_url)
        self.assertEqual(com_configuracao.data['pre_encontro']['capacidade'], 30)
        self.assertNotIn(
            'INSCRICOES_NAO_CONFIGURADAS',
            {alerta['codigo'] for alerta in com_configuracao.data['alertas']},
        )

    def test_fichas_nao_recebe_permissao_exclusiva_de_diretoria(self):
        self.assertFalse(
            pode_resolver_vaga_pre_encontro(self.fichas, self.encontro),
        )
