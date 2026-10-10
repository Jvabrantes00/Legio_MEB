from datetime import timedelta
from unittest.mock import patch

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import ConviteEncontro, OportunidadeConviteEncontro
from core.services import oportunidades_convites as services
from core.tests.test_oportunidade_convite_services import (
    OportunidadeConviteFixtureMixin,
)
from core.throttles import PublicInvitationThrottle


class ConvitePublicoAPITests(OportunidadeConviteFixtureMixin, TestCase):
    def setUp(self):
        cache.clear()
        self.preparar_dominio()
        self.pessoa, self.convite = self.criar_candidato('Pessoa Pública')
        _, emissoes = self.iniciar_campanha()
        self.emissao = emissoes[self.convite.pk]
        self.oportunidade = self.emissao.oportunidade
        self.client = APIClient()
        self.url = reverse('convite-encontro-publico')

    def tearDown(self):
        cache.clear()

    def payload(self, **overrides):
        dados = {
            'token': self.emissao.token,
            'data_nascimento': self.pessoa.data_nascimento.isoformat(),
            'acao': 'validar',
        }
        dados.update(overrides)
        return dados

    def test_superficie_publica_e_allow_any_com_resposta_minima(self):
        resposta = self.client.post(self.url, self.payload(), format='json')
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(resposta.json()),
            {
                'estado',
                'titulo_encontro',
                'datas_encontro',
                'prazo_resposta',
                'finalidade',
                'pode_responder',
                'mensagem',
            },
        )
        conteudo = resposta.content.decode().lower()
        for segredo in (
            self.emissao.token,
            self.oportunidade.token_digest,
            self.pessoa.nome,
            self.pessoa.email,
            self.pessoa.data_nascimento.isoformat(),
        ):
            self.assertNotIn(str(segredo).lower(), conteudo)
        self.assertNotIn('pessoa_id', conteudo)
        self.assertNotIn('convite_id', conteudo)
        self.assertNotIn('encontro_id', conteudo)

    def test_token_e_nascimento_invalidos_tem_mesma_resposta(self):
        respostas = (
            self.client.post(
                self.url,
                self.payload(token='A' * 43),
                format='json',
            ),
            self.client.post(
                self.url,
                self.payload(data_nascimento='2001-01-01'),
                format='json',
            ),
            self.client.post(
                self.url,
                self.payload(token='malformado'),
                format='json',
            ),
        )
        for resposta in respostas:
            self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)
            self.assertEqual(
                resposta.json(),
                {'detail': services.MENSAGEM_NAO_VALIDADO},
            )

    def test_confirmar_recusar_e_replay_preservam_primeira_decisao(self):
        confirmacao = self.client.post(
            self.url,
            self.payload(acao='confirmar'),
            format='json',
        )
        replay = self.client.post(
            self.url,
            self.payload(acao='recusar'),
            format='json',
        )
        self.assertEqual(confirmacao.json()['estado'], 'confirmado')
        self.assertEqual(replay.json()['estado'], 'confirmado')

    def test_recusa_publica_e_somente_leitura(self):
        resposta = self.client.post(
            self.url,
            self.payload(acao='recusar'),
            format='json',
        )
        consulta = self.client.post(self.url, self.payload(), format='json')
        self.convite.refresh_from_db()
        self.assertEqual(resposta.json()['estado'], 'recusado')
        self.assertFalse(consulta.json()['pode_responder'])
        self.assertEqual(self.convite.status, ConviteEncontro.Status.RECUSADO)

    def test_expirado_suspenso_e_invalidado_sao_somente_leitura(self):
        for estado, publico in (
            (OportunidadeConviteEncontro.Status.EXPIRADA, 'expirado'),
            (OportunidadeConviteEncontro.Status.SUSPENSA, 'suspenso'),
            (OportunidadeConviteEncontro.Status.INVALIDADA, 'indisponivel'),
        ):
            with self.subTest(estado=estado):
                self.oportunidade.status = estado
                self.oportunidade.save(update_fields=['status'])
                resposta = self.client.post(
                    self.url,
                    self.payload(acao='confirmar'),
                    format='json',
                )
                self.assertEqual(resposta.status_code, status.HTTP_200_OK)
                self.assertEqual(resposta.json()['estado'], publico)
                self.assertFalse(resposta.json()['pode_responder'])
                self.oportunidade.status = (
                    OportunidadeConviteEncontro.Status.PENDENTE
                )
                self.oportunidade.save(update_fields=['status'])

    def test_capacidade_cheia_retorna_indisponivel_sem_recusa(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        outra_pessoa, outro_convite = self.criar_candidato('Já Confirmada')
        outro_convite.status = ConviteEncontro.Status.CONFIRMADO
        outro_convite.save(update_fields=['status'])
        resposta = self.client.post(
            self.url,
            self.payload(acao='confirmar'),
            format='json',
        )
        self.convite.refresh_from_db()
        self.assertEqual(resposta.json()['estado'], 'indisponivel')
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)
        self.assertIsNotNone(outra_pessoa.pk)

    def test_throttle_protege_validacao_e_decisoes(self):
        original = PublicInvitationThrottle.get_rate
        PublicInvitationThrottle.get_rate = lambda _self: '1/minute'
        try:
            primeira = self.client.post(self.url, self.payload(), format='json')
            segunda = self.client.post(
                self.url,
                self.payload(acao='confirmar'),
                format='json',
            )
        finally:
            PublicInvitationThrottle.get_rate = original
        self.assertEqual(primeira.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_429_TOO_MANY_REQUESTS)

    def test_acesso_apos_prazo_reconcilia_expiracao(self):
        self.oportunidade.expira_em = (
            self.oportunidade.criada_em + timedelta(seconds=1)
        )
        self.oportunidade.save(update_fields=['expira_em'])
        with patch.object(
            services.timezone,
            'now',
            return_value=self.oportunidade.expira_em + timedelta(seconds=1),
        ):
            resposta = self.client.post(
                self.url,
                self.payload(),
                format='json',
            )
        self.assertEqual(resposta.json()['estado'], 'expirado')
