from datetime import date

from rest_framework import status

from core.models import ParticipacaoEncontro
from core.serializers import AlpinistaCompletoSerializer
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_alpinista, make_encontro, make_funcao


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
