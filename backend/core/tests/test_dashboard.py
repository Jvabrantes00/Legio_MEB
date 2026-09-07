from datetime import date, timedelta

from django.contrib.auth.models import Group
from rest_framework import status

from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_alpinista, make_encontro


class DashboardRegressionTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        diretoria, _ = Group.objects.get_or_create(name='Diretoria')
        self.user.groups.add(diretoria)

    def test_contagens_usam_status_canonicos(self):
        # Arrange
        make_alpinista(status='ativo')
        make_alpinista(status='pendente')
        make_alpinista(status='inativo')

        # Act
        response = self.client.get('/api/dashboard-stats/')

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['visaoGeral'],
            {'ativos': 1, 'pendentes': 1, 'inativos': 1},
        )

    def test_dashboard_retorna_proximo_encontro(self):
        # Arrange
        encontro = make_encontro(data_referencia=date.today() + timedelta(days=10))

        # Act
        response = self.client.get('/api/dashboard-stats/')

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['proximosEncontros'][0],
            {
                'nome': encontro.encontro,
                'data': str(encontro.data_referencia),
            },
        )

    def test_dashboard_sem_encontro_futuro_retorna_lista_vazia(self):
        make_encontro(data_referencia=date.today() - timedelta(days=1))

        response = self.client.get('/api/dashboard-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['proximosEncontros'], [])

    def test_dashboard_ordena_varios_encontros_do_mais_proximo(self):
        mais_distante = make_encontro(
            data_referencia=date.today() + timedelta(days=20)
        )
        mais_proximo = make_encontro(
            data_referencia=date.today() + timedelta(days=5)
        )
        intermediario = make_encontro(
            data_referencia=date.today() + timedelta(days=10)
        )

        response = self.client.get('/api/dashboard-stats/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['nome'] for item in response.json()['proximosEncontros']],
            [
                mais_proximo.encontro,
                intermediario.encontro,
                mais_distante.encontro,
            ],
        )
