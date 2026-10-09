from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    DadosCuidadoInscricao,
    DadosDeclaradosInscricao,
    DiaEncontro,
    Encontro,
    InscricaoEncontro,
    Pessoa,
)
from core.tests.factories import make_encontro
from core.throttles import (
    PublicRegistrationReadThrottle,
    PublicRegistrationSubmitThrottle,
)


class InscricaoEncontroPublicaAPITests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.agora = timezone.now()
        self.encontro = make_encontro(
            encontro='Escalada pública',
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia=(self.agora + timedelta(days=180)).date(),
        )
        self.configuracao = self._configurar(self.encontro)
        self._oficializar_calendario(self.encontro)
        self.url = reverse(
            'inscricao-encontro-publica',
            kwargs={'public_id': self.configuracao.public_id},
        )

    def tearDown(self):
        cache.clear()

    def _configurar(self, encontro, **overrides):
        valores = {
            'encontro': encontro,
            'capacidade': 40,
            'idade_minima': 15,
            'idade_maxima': 29,
            'inscricoes_abrem_em': self.agora - timedelta(days=1),
            'inscricoes_encerram_em': self.agora + timedelta(days=1),
        }
        valores.update(overrides)
        return ConfiguracaoEncontristasEncontro.objects.create(**valores)

    def _oficializar_calendario(self, encontro):
        calendario = CalendarioEncontro.objects.create(
            encontro=encontro,
            versao=1,
            vigente=True,
            oficializado_em=self.agora,
        )
        DiaEncontro.objects.create(
            calendario=calendario,
            ordem=1,
            data=(self.agora + timedelta(days=180)).date(),
        )

    def _payload(self, **dados_overrides):
        dados = {
            'nome_completo': 'Pessoa Pública Sensível',
            'apelido': 'Pessoa',
            'data_nascimento': date(2000, 1, 15).isoformat(),
            'cpf': '529.982.247-25',
            'email': 'pessoa.publica@example.test',
            'telefone_whatsapp': '',
            'cep': '70000-000',
            'logradouro': 'Rua Declarada',
            'numero': '10',
            'complemento': '',
            'bairro': 'Bairro',
            'cidade': 'Brasília',
            'uf': 'DF',
            'como_conheceu': (
                DadosDeclaradosInscricao.ComoConheceu.INDICACAO
            ),
            'como_conheceu_outro': '',
            'batismo': DadosDeclaradosInscricao.Sacramento.SIM,
            'primeira_comunhao': DadosDeclaradosInscricao.Sacramento.NAO,
            'crisma': DadosDeclaradosInscricao.Sacramento.NAO_SEI,
        }
        dados.update(dados_overrides)
        return {
            'dados_declarados': dados,
            'dados_cuidado': {
                'possui_alergias': (
                    DadosCuidadoInscricao.RespostaBinaria.NAO
                ),
                'alergias': '',
                'possui_restricoes_intolerancias': (
                    DadosCuidadoInscricao.RespostaBinaria.NAO
                ),
                'restricoes_intolerancias': '',
                'usa_medicamentos': (
                    DadosCuidadoInscricao.RespostaBinaria.NAO
                ),
                'medicamentos': '',
                'horarios_medicamentos': '',
                'observacoes_medicamentos': '',
                'neurodivergencia_apoio': (
                    DadosCuidadoInscricao.RespostaApoio.NAO
                ),
                'neurodivergencia_condicao': '',
                'necessidades_apoio': '',
                'sensibilidades_desconfortos': '',
                'o_que_ajuda': '',
                'outras_informacoes': '',
                'observacoes': '',
            },
        }

    def test_leitura_publica_retorna_somente_tipo_titulo_e_janela(self):
        resposta = self.client.get(self.url)

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(resposta.json()),
            {
                'titulo',
                'tipo',
                'inscricoes_abrem_em',
                'inscricoes_encerram_em',
                'inscricoes_abertas',
            },
        )
        self.assertEqual(resposta.json()['titulo'], 'Escalada pública')
        self.assertEqual(resposta.json()['tipo'], Encontro.Tipo.ESCALADA)
        self.assertTrue(resposta.json()['inscricoes_abertas'])
        self.assertNotIn('id', resposta.json())
        self.assertNotIn('capacidade', resposta.json())
        self.assertNotIn('local', resposta.json())

    def test_janela_fechada_e_informada_e_impede_submissao(self):
        self.configuracao.inscricoes_abrem_em = self.agora - timedelta(days=2)
        self.configuracao.inscricoes_encerram_em = self.agora - timedelta(days=1)
        self.configuracao.save(
            update_fields=['inscricoes_abrem_em', 'inscricoes_encerram_em'],
        )

        leitura = self.client.get(self.url)
        submissao = self.client.post(self.url, self._payload(), format='json')

        self.assertEqual(leitura.status_code, status.HTTP_200_OK)
        self.assertFalse(leitura.json()['inscricoes_abertas'])
        self.assertEqual(submissao.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(submissao.json()), {'janela'})
        self.assertFalse(InscricaoEncontro.objects.exists())

    def test_submissao_retorna_confirmacao_minima_sem_id_ou_pii(self):
        resposta = self.client.post(self.url, self._payload(), format='json')

        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            resposta.json(),
            {'mensagem': 'Inscrição enviada com sucesso.'},
        )
        conteudo = resposta.content.decode()
        self.assertNotIn('Pessoa Pública Sensível', conteudo)
        self.assertNotIn('529.982.247-25', conteudo)
        self.assertNotIn('pessoa.publica@example.test', conteudo)
        self.assertNotIn('identificador', conteudo)
        self.assertEqual(InscricaoEncontro.objects.count(), 1)
        self.assertEqual(
            InscricaoEncontro.objects.get().origem,
            InscricaoEncontro.Origem.PUBLICA,
        )
        self.assertFalse(Pessoa.objects.exists())

    def test_esppa_aceita_dados_especificos_pelo_mesmo_contrato_publico(self):
        self.encontro.tipo = Encontro.Tipo.ESPPA
        self.encontro.save(update_fields=['tipo'])
        payload = self._payload()
        payload['dados_esppa'] = {
            'estado_civil': 'solteiro',
            'nome_referencia': 'Pessoa de referência',
            'relacao_referencia': 'amigo',
            'telefone_referencia': '61988880000',
        }

        leitura = self.client.get(self.url)
        resposta = self.client.post(self.url, payload, format='json')

        self.assertEqual(leitura.status_code, status.HTTP_200_OK)
        self.assertEqual(leitura.json()['tipo'], Encontro.Tipo.ESPPA)
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            hasattr(InscricaoEncontro.objects.get(), 'dados_esppa'),
        )

    def test_payload_invalido_e_campos_extras_nao_persistem(self):
        payload = self._payload()
        payload['pessoa_id'] = 123

        resposta = self.client.post(self.url, payload, format='json')

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(set(resposta.json()), {'campos_extras'})
        self.assertFalse(InscricaoEncontro.objects.exists())

    def test_pk_inteiro_nao_e_aceito_na_rota_publica(self):
        url_antiga = (
            f'/api/public/encontros/{self.encontro.pk}/inscricao/'
        )

        self.assertEqual(
            self.client.get(url_antiga).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.post(
                url_antiga,
                self._payload(),
                format='json',
            ).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_404_publico_e_uniforme_sem_revelar_a_causa(self):
        avc = self._configurar(
            make_encontro(tipo=Encontro.Tipo.AVC),
        )
        acampamento = self._configurar(
            make_encontro(tipo=Encontro.Tipo.ACAMPAMENTO),
        )
        configuracao_removida = self._configurar(
            make_encontro(tipo=Encontro.Tipo.ESCALADA),
        )
        public_id_removido = configuracao_removida.public_id
        configuracao_removida.delete()

        casos = {
            'uuid_inexistente': uuid4(),
            'avc': avc.public_id,
            'acampamento': acampamento.public_id,
            'configuracao_indisponivel': public_id_removido,
        }
        resposta_esperada = {'detail': 'Recurso público não encontrado.'}

        for causa, public_id in casos.items():
            url = reverse(
                'inscricao-encontro-publica',
                kwargs={'public_id': public_id},
            )
            with self.subTest(causa=causa, metodo='GET'):
                resposta = self.client.get(url)
                self.assertEqual(
                    resposta.status_code,
                    status.HTTP_404_NOT_FOUND,
                )
                self.assertEqual(resposta.json(), resposta_esperada)
            with self.subTest(causa=causa, metodo='POST'):
                resposta = self.client.post(
                    url,
                    self._payload(),
                    format='json',
                )
                self.assertEqual(
                    resposta.status_code,
                    status.HTTP_404_NOT_FOUND,
                )
                self.assertEqual(resposta.json(), resposta_esperada)

    def test_endpoints_internos_continuam_default_deny(self):
        urls = [
            reverse('resolucao-inscricao-detail', kwargs={'pk': 999}),
            reverse('inscricao-encontro-list'),
        ]

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_throttles_de_leitura_e_submissao_sao_dedicados(self):
        rates = {
            'public_registration_read': '1/minute',
            'public_registration_submit': '1/minute',
        }
        with (
            patch.object(
                PublicRegistrationReadThrottle,
                'THROTTLE_RATES',
                rates,
            ),
            patch.object(
                PublicRegistrationSubmitThrottle,
                'THROTTLE_RATES',
                rates,
            ),
        ):
            leitura = self.client.get(self.url)
            primeira = self.client.post(
                self.url,
                self._payload(),
                format='json',
            )
            segunda = self.client.post(
                self.url,
                self._payload(),
                format='json',
            )

        self.assertEqual(leitura.status_code, status.HTTP_200_OK)
        self.assertEqual(primeira.status_code, status.HTTP_201_CREATED)
        self.assertEqual(segunda.status_code, status.HTTP_429_TOO_MANY_REQUESTS)
        self.assertEqual(InscricaoEncontro.objects.count(), 1)

    def test_log_de_rejeicao_nao_contem_pii_ou_payload(self):
        payload = self._payload(
            email='',
            telefone_whatsapp='',
        )

        with self.assertLogs('core.public_registration', level='INFO') as logs:
            resposta = self.client.post(self.url, payload, format='json')

        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        conteudo_logs = '\n'.join(logs.output)
        self.assertIn('Public encounter registration rejected.', conteudo_logs)
        self.assertNotIn('Pessoa Pública Sensível', conteudo_logs)
        self.assertNotIn('529.982.247-25', conteudo_logs)
        self.assertNotIn('pessoa.publica@example.test', conteudo_logs)
        self.assertNotIn('Rua Declarada', conteudo_logs)
        self.assertFalse(InscricaoEncontro.objects.exists())
