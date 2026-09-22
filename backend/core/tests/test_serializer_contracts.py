from datetime import date

from rest_framework import status

from core.models import ParticipacaoEncontro
from core.serializers import (
    AlpinistaCompletoSerializer,
    EncontroSerializer,
    EventoSerializer,
    FuncaoEncontroSerializer,
)
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_alpinista, make_encontro, make_funcao


class RemainingSerializerAllowlistTests(AuthenticatedAPITestCase):
    def test_serializers_restantes_possuem_allowlists_explicitas(self):
        contracts = (
            (
                EncontroSerializer,
                (
                    'id',
                    'status_encontro',
                    'encontro',
                    'tipo',
                    'data_referencia',
                    'data_exato',
                    'local',
                    'status',
                    'criado_em',
                    'participantes',
                ),
            ),
            (
                EventoSerializer,
                (
                    'id',
                    'status_evento',
                    'total_participantes',
                    'nome',
                    'data_evento',
                    'local',
                ),
            ),
            (
                FuncaoEncontroSerializer,
                ('id', 'nome', 'tipo', 'descricao_faq', 'ordem', 'eh_violeiro'),
            ),
        )

        for serializer_class, expected_fields in contracts:
            with self.subTest(serializer=serializer_class.__name__):
                self.assertNotEqual(serializer_class.Meta.fields, '__all__')
                self.assertEqual(serializer_class.Meta.fields, expected_fields)
                self.assertEqual(tuple(serializer_class().fields), expected_fields)


class AlpinistaCompletoContractTests(AuthenticatedAPITestCase):
    expected_fields = {
        'id',
        'cpf',
        'nome',
        'dataNascimento',
        'endereco',
        'email',
        'telefone',
        'nomePai',
        'telefonePai',
        'nomeMae',
        'telefoneMae',
        'restricaoSaude',
        'medicacao',
        'conheciaEscalada',
        'grupo',
        'status',
        'foto',
        'batizado',
        'primeira_comunhao',
        'crismado',
        'eh_violeiro',
        'canta',
        'is_neurodivergente',
        'tipo_neurodivergente',
        'idade_atual',
        'encontros_realizados',
        'historico_equipes',
        'historico_eventos',
    }

    def test_perfil_completo_tem_allowlist_explicita_e_contrato_preservado(self):
        alpinista = make_alpinista(
            cpf='52998224725',
            dataNascimento=date(2000, 1, 1),
            endereco='Endereço reservado',
            restricaoSaude='Dado reservado',
            medicacao='Dado reservado',
            is_neurodivergente=True,
            tipo_neurodivergente='Dado reservado',
        )

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.json()), self.expected_fields)
        self.assertNotEqual(AlpinistaCompletoSerializer.Meta.fields, '__all__')
        self.assertEqual(
            set(AlpinistaCompletoSerializer.Meta.fields),
            self.expected_fields,
        )

    def test_campos_calculados_e_id_sao_somente_leitura(self):
        self.assertTrue(
            {
                'id',
                'idade_atual',
                'encontros_realizados',
                'historico_equipes',
                'historico_eventos',
            }.issubset(AlpinistaCompletoSerializer.Meta.read_only_fields)
        )


class ParticipacaoEncontroContractTests(AuthenticatedAPITestCase):
    def test_alpinista_aninhado_expoe_somente_id_e_nome(self):
        alpinista = make_alpinista(
            cpf='52998224725',
            endereco='Endereço que não deve aparecer',
            restricaoSaude='Saúde que não deve aparecer',
            medicacao='Medicação que não deve aparecer',
            tipo_neurodivergente='Dado que não deve aparecer',
        )
        participacao = ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=make_encontro(),
            funcao=make_funcao(),
        )

        response = self.client.get(
            f'/api/participacoes-encontros/{participacao.pk}/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['alpinista'],
            {'id': alpinista.pk, 'nome': alpinista.nome},
        )
        self.assertEqual(set(response.json()['alpinista']), {'id', 'nome'})


class HistoricoEquipeContractTests(AuthenticatedAPITestCase):
    def test_coordenador_dos_dirigentes_preserva_cor_sem_diferenciar_case(self):
        for nome_funcao in (
            'Coordenador dos Dirigentes',
            'COORDENADOR DOS DIRIGENTES',
        ):
            with self.subTest(nome_funcao=nome_funcao):
                alpinista = make_alpinista()
                ParticipacaoEncontro.objects.create(
                    alpinista=alpinista,
                    encontro=make_encontro(),
                    funcao=make_funcao(nome=nome_funcao, tipo='equipe'),
                    cor_grupo='azul',
                )

                payload = AlpinistaCompletoSerializer(alpinista).data

                self.assertEqual(
                    payload['historico_equipes'][0]['cor_grupo'],
                    'azul',
                )
