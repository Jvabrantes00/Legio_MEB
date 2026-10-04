from datetime import date
from unittest.mock import patch

from rest_framework import status

from core.models import (
    ConviteEncontro,
    Encontro,
    Frequencia,
    Inscricao,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
)
from core.services import participacoes as participacao_services
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_encontro


class EncounterParticipationCommandApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.pessoa = Pessoa.objects.create(nome='Pessoa candidata')
        self.escalada = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.esppa = make_encontro(tipo=Encontro.Tipo.ESPPA)

    def test_criacao_de_inscricao_delega_ao_service(self):
        with patch(
            'core.serializers.participacao_services.criar_inscricao',
            wraps=participacao_services.criar_inscricao,
        ) as service:
            response = self.client.post(
                '/api/inscricoes-encontros/',
                {
                    'pessoa_id': self.pessoa.pk,
                    'tipo': Inscricao.Tipo.ESCALADA,
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        service.assert_called_once()
        self.assertEqual(response.json()['status'], Inscricao.Status.PENDENTE)

    def test_convite_e_resposta_delegam_aos_services_sem_criar_participacao(self):
        inscricao = participacao_services.criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )
        with patch(
            'core.serializers.participacao_services.criar_convite',
            wraps=participacao_services.criar_convite,
        ) as criar, patch(
            'core.serializers.participacao_services.responder_convite',
            wraps=participacao_services.responder_convite,
        ) as responder:
            criacao = self.client.post(
                '/api/convites-encontros/',
                {
                    'pessoa_id': self.pessoa.pk,
                    'encontro_id': self.escalada.pk,
                    'finalidade': ConviteEncontro.Finalidade.PARTICIPAR,
                    'inscricao_id': inscricao.pk,
                },
                format='json',
            )
            resposta = self.client.post(
                f"/api/convites-encontros/{criacao.json()['id']}/responder/",
                {'status': ConviteEncontro.Status.CONFIRMADO},
                format='json',
            )

        self.assertEqual(criacao.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.json()['status'], ConviteEncontro.Status.CONFIRMADO)
        criar.assert_called_once()
        responder.assert_called_once()
        self.assertFalse(ParticipacaoEncontro.objects.exists())
        self.assertFalse(PerfilAlpinista.objects.exists())
        self.assertFalse(Frequencia.objects.exists())

    def test_conclusao_de_escalada_e_esppa_passa_pelo_service_e_cria_perfil(self):
        casos = (
            (self.pessoa, self.escalada),
            (Pessoa.objects.create(nome='Pessoa ESPPA'), self.esppa),
        )

        with patch(
            'core.serializers.participacao_services.registrar_resultado_participacao',
            wraps=participacao_services.registrar_resultado_participacao,
        ) as service:
            for pessoa, encontro in casos:
                with self.subTest(tipo=encontro.tipo):
                    response = self.client.post(
                        '/api/resultados-participacoes-encontros/',
                        {
                            'pessoa_id': pessoa.pk,
                            'encontro_id': encontro.pk,
                            'resultado': ParticipacaoEncontro.Resultado.CONCLUIU,
                        },
                        format='json',
                    )
                    self.assertEqual(
                        response.status_code,
                        status.HTTP_201_CREATED,
                    )
                    self.assertTrue(
                        PerfilAlpinista.objects.filter(pessoa=pessoa).exists()
                    )

        self.assertEqual(service.call_count, 2)
        self.assertFalse(Frequencia.objects.exists())

    def test_falta_e_desistencia_nao_criam_perfil_ou_frequencia(self):
        for resultado in (
            ParticipacaoEncontro.Resultado.FALTOU,
            ParticipacaoEncontro.Resultado.DESISTIU,
        ):
            with self.subTest(resultado=resultado):
                pessoa = Pessoa.objects.create(nome=f'Pessoa {resultado}')
                encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)

                response = self.client.post(
                    '/api/resultados-participacoes-encontros/',
                    {
                        'pessoa_id': pessoa.pk,
                        'encontro_id': encontro.pk,
                        'resultado': resultado,
                    },
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertFalse(
                    PerfilAlpinista.objects.filter(pessoa=pessoa).exists()
                )

        self.assertFalse(Frequencia.objects.exists())

    def test_avc_e_acampamento_nao_criam_perfil_ou_frequencia(self):
        for tipo in (Encontro.Tipo.AVC, Encontro.Tipo.ACAMPAMENTO):
            with self.subTest(tipo=tipo):
                pessoa = Pessoa.objects.create(nome=f'Pessoa {tipo}')
                escalada = make_encontro(
                    tipo=Encontro.Tipo.ESCALADA,
                    data_referencia=date(2027, 1, 1),
                )
                ParticipacaoEncontro.objects.create(
                    pessoa=pessoa,
                    encontro=escalada,
                    resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
                    tipo_encontro=Encontro.Tipo.ESCALADA,
                )
                encontro = make_encontro(
                    tipo=tipo,
                    data_referencia=date(2030, 1, 1),
                )

                response = self.client.post(
                    '/api/resultados-participacoes-encontros/',
                    {
                        'pessoa_id': pessoa.pk,
                        'encontro_id': encontro.pk,
                        'resultado': ParticipacaoEncontro.Resultado.CONCLUIU,
                    },
                    format='json',
                )

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertFalse(
                    PerfilAlpinista.objects.filter(pessoa=pessoa).exists()
                )

        self.assertFalse(Frequencia.objects.exists())

    def test_erros_de_dominio_sao_expostos_como_400(self):
        primeira = self.client.post(
            '/api/inscricoes-encontros/',
            {
                'pessoa_id': self.pessoa.pk,
                'tipo': Inscricao.Tipo.ESCALADA,
            },
            format='json',
        )
        duplicada = self.client.post(
            '/api/inscricoes-encontros/',
            {
                'pessoa_id': self.pessoa.pk,
                'tipo': Inscricao.Tipo.ESCALADA,
            },
            format='json',
        )

        self.assertEqual(primeira.status_code, status.HTTP_201_CREATED)
        self.assertEqual(duplicada.status_code, status.HTTP_400_BAD_REQUEST)

    def test_endpoints_de_comando_nao_expoem_listagem_generica(self):
        for url in (
            '/api/inscricoes-encontros/',
            '/api/convites-encontros/',
            '/api/resultados-participacoes-encontros/',
        ):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
