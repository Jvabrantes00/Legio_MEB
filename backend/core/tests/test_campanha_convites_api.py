from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from core.models import (
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DiaEncontro,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    Pessoa,
)
from core.roles import SiaRole
from core.services import campanhas_convites as services
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_encontro


class CampanhaConvitesApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.user.groups.clear()
        fichas, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.user.groups.add(fichas)
        self.encontro = make_encontro(data_referencia=date(2030, 6, 1))
        self.agora = timezone.now()
        ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=2,
            idade_minima=18,
            idade_maxima=30,
            inscricoes_abrem_em=self.agora - timedelta(days=30),
            inscricoes_encerram_em=self.agora - timedelta(days=1),
        )
        calendario = CalendarioEncontro.objects.create(
            encontro=self.encontro,
            versao=1,
            vigente=True,
            oficializado_em=self.agora,
        )
        DiaEncontro.objects.create(
            calendario=calendario,
            ordem=1,
            data=date(2030, 6, 1),
        )
        self.pessoa = Pessoa.objects.create(
            nome='Pessoa API campanha',
            data_nascimento=date(2010, 1, 1),
            email='campanha-api@example.test',
        )
        InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=self.pessoa,
            origem=InscricaoEncontro.Origem.PUBLICA,
        )
        self.convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )
        self.detail_url = reverse(
            'campanha-convites-encontro-detail',
            kwargs={'pk': self.encontro.pk},
        )
        self.iniciar_url = reverse(
            'campanha-convites-encontro-iniciar',
            kwargs={'pk': self.encontro.pk},
        )

    def autenticar(self, role=None, indice='usuario'):
        usuario = get_user_model().objects.create_user(
            username=f'campanha-{indice}',
            password='senha-exclusiva-de-teste',
        )
        if role is not None:
            grupo, _ = Group.objects.get_or_create(name=role.value)
            usuario.groups.add(grupo)
        self.client.force_authenticate(usuario)
        return usuario

    def iniciar(self):
        return services.iniciar_campanha(
            usuario=self.user,
            encontro=self.encontro,
            prazo_confirmacao=self.agora + timedelta(days=10),
            momento=self.agora,
        )

    def test_autenticacao_e_default_deny(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get(self.detail_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.autenticar(indice='sem-papel')
        self.assertEqual(
            self.client.get(self.detail_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.autenticar(SiaRole.COMUNICACAO, 'comunicacao')
        self.assertEqual(
            self.client.post(
                self.iniciar_url,
                {'prazo_confirmacao': (timezone.now() + timedelta(days=1)).isoformat()},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_fichas_diretoria_suporte_e_superuser_consultam(self):
        campanha = self.iniciar()
        self.assertIsNotNone(campanha.pk)
        projecao_url = reverse(
            'campanha-convites-encontro-projecao',
            kwargs={'pk': self.encontro.pk},
        )
        for indice, role in enumerate((
            SiaRole.FICHAS,
            SiaRole.DIRETORIA,
            SiaRole.SUPORTE,
        )):
            with self.subTest(role=role):
                self.autenticar(role, indice)
                self.assertEqual(
                    self.client.get(self.detail_url).status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    self.client.get(projecao_url).status_code,
                    status.HTTP_200_OK,
                )
        superuser = get_user_model().objects.create_superuser(
            username='superuser-campanha',
            email='superuser-campanha@example.test',
            password='senha-exclusiva-de-teste',
        )
        self.client.force_authenticate(superuser)
        self.assertEqual(
            self.client.get(self.detail_url).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(projecao_url).status_code,
            status.HTTP_200_OK,
        )

    def test_diretoria_e_suporte_nao_executam_mutacoes(self):
        mutacoes = (
            self.iniciar_url,
            reverse(
                'campanha-convites-encontro-processar-prazo',
                kwargs={'pk': self.encontro.pk},
            ),
            reverse(
                'campanha-convites-encontro-prorrogar',
                kwargs={'pk': self.encontro.pk},
            ),
            reverse(
                'campanha-convites-encontro-encerrar',
                kwargs={'pk': self.encontro.pk},
            ),
            reverse(
                'campanha-convites-encontro-recusar',
                kwargs={'pk': self.encontro.pk, 'oportunidade_id': 999},
            ),
            reverse(
                'campanha-convites-encontro-reabrir-recusa',
                kwargs={'pk': self.encontro.pk},
            ),
            reverse(
                'campanha-convites-encontro-nova-vaga',
                kwargs={'pk': self.encontro.pk},
            ),
        )
        for role in (SiaRole.DIRETORIA, SiaRole.SUPORTE):
            self.autenticar(role, f'somente-leitura-{role.value}')
            for url in mutacoes:
                with self.subTest(role=role, url=url):
                    self.assertEqual(
                        self.client.post(url, {}, format='json').status_code,
                        status.HTTP_403_FORBIDDEN,
                    )

    def test_superuser_mantem_bypass_tecnico_para_mutacao(self):
        superuser = get_user_model().objects.create_superuser(
            username='superuser-campanha-mutacao',
            email='superuser-campanha-mutacao@example.test',
            password='senha-exclusiva-de-teste',
        )
        self.client.force_authenticate(superuser)

        resposta = self.client.post(
            self.iniciar_url,
            {
                'prazo_confirmacao': (
                    timezone.now() + timedelta(days=3)
                ).isoformat(),
            },
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)

    def test_inicia_uma_vez_e_resposta_nao_expoe_segredo(self):
        prazo = timezone.now() + timedelta(days=3)

        resposta = self.client.post(
            self.iniciar_url,
            {'prazo_confirmacao': prazo.isoformat()},
            format='json',
        )
        duplicada = self.client.post(
            self.iniciar_url,
            {'prazo_confirmacao': prazo.isoformat()},
            format='json',
        )

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicada.status_code, status.HTTP_400_BAD_REQUEST)
        conteudo = str(resposta.json()).lower()
        self.assertNotIn('token', conteudo)
        self.assertNotIn('digest', conteudo)
        self.assertNotIn(self.pessoa.email, conteudo)

    def test_processa_prazo_prorroga_e_consulta_nova_rodada(self):
        self.iniciar()
        instante_decisao = self.agora + timedelta(days=11)
        with patch(
            'core.services.campanhas_convites.timezone.now',
            return_value=instante_decisao,
        ):
            processada = self.client.post(
                reverse(
                    'campanha-convites-encontro-processar-prazo',
                    kwargs={'pk': self.encontro.pk},
                ),
                {},
                format='json',
            )
            resposta = self.client.post(
                reverse(
                    'campanha-convites-encontro-prorrogar',
                    kwargs={'pk': self.encontro.pk},
                ),
                {
                    'novo_prazo': (
                        instante_decisao + timedelta(days=20)
                    ).isoformat(),
                    'justificativa': 'Decisão operacional de Fichas.',
                },
                format='json',
            )

        self.assertEqual(processada.status_code, status.HTTP_200_OK)
        self.assertEqual(processada.json()['status'], 'aguardando_decisao')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.json()['status'], 'ativa')
        self.assertEqual(resposta.json()['rodadas'][-1]['tipo'], 'prorrogacao')
        self.assertEqual(resposta.json()['rodadas'][-1]['sequencia'], 2)
        self.assertNotIn('token', str(resposta.json()).lower())

    def test_encerramento_explicito(self):
        campanha = self.iniciar()
        instante_decisao = self.agora + timedelta(days=11)
        services.processar_prazo(
            usuario=self.user,
            campanha=campanha,
            momento=instante_decisao,
        )

        with patch(
            'core.services.campanhas_convites.timezone.now',
            return_value=instante_decisao + timedelta(minutes=1),
        ):
            resposta = self.client.post(
                reverse(
                    'campanha-convites-encontro-encerrar',
                    kwargs={'pk': self.encontro.pk},
                ),
                {'justificativa': 'Encerrar com confirmados existentes.'},
                format='json',
            )

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.json()['status'], 'encerrada')

    def test_recusa_e_reabertura_manual_exigem_justificativa(self):
        self.iniciar()
        oportunidade = OportunidadeConviteEncontro.objects.get()
        recusada = self.client.post(
            reverse(
                'campanha-convites-encontro-recusar',
                kwargs={
                    'pk': self.encontro.pk,
                    'oportunidade_id': oportunidade.pk,
                },
            ),
            {'justificativa': 'Recusa informada a Fichas.'},
            format='json',
        )
        url = reverse(
            'campanha-convites-encontro-reabrir-recusa',
            kwargs={'pk': self.encontro.pk},
        )

        invalida = self.client.post(
            url,
            {'convite_id': self.convite.pk, 'justificativa': ''},
            format='json',
        )
        valida = self.client.post(
            url,
            {
                'convite_id': self.convite.pk,
                'justificativa': 'Contato confirmado manualmente.',
            },
            format='json',
        )

        self.assertEqual(recusada.status_code, status.HTTP_200_OK)
        self.assertEqual(invalida.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(valida.status_code, status.HTTP_200_OK)
        self.assertEqual(valida.json()['rodadas'][-1]['tipo'], 'reposicao')
        self.assertNotEqual(
            valida.json()['rodadas'][-1]['oportunidades'][0]['id'],
            oportunidade.pk,
        )

    def test_projecao_minima_mostra_sem_canal_sem_ranking(self):
        self.pessoa.email = None
        self.pessoa.save(update_fields=['email'])
        configuracao = self.encontro.configuracao_encontristas
        configuracao.capacidade = 1
        configuracao.save(update_fields=['capacidade'])
        pessoa_confirmada = Pessoa.objects.create(
            nome='Pessoa confirmada API',
            data_nascimento=date(2010, 1, 1),
        )
        ConviteEncontro.objects.create(
            pessoa=pessoa_confirmada,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        resposta = self.client.get(reverse(
            'campanha-convites-encontro-projecao',
            kwargs={'pk': self.encontro.pk},
        ))
        payload = resposta.json()

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(payload['lista_espera_ativa'])
        self.assertTrue(payload['sem_prioridade'])
        self.assertTrue(payload['candidatos'][0]['sem_canal'])
        self.assertNotIn('posicao', payload['candidatos'][0])
        conteudo = str(payload).lower()
        self.assertNotIn('email', conteudo)
        self.assertNotIn('telefone', conteudo)
        self.assertNotIn('token', conteudo)
