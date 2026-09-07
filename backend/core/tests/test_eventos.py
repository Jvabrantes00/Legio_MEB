from datetime import date

from rest_framework import status

from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_evento


class EventoRegressionTests(AuthenticatedAPITestCase):
    def test_listagem_serializa_data_evento_atual(self):
        # Arrange
        evento = make_evento(data_evento=date(2030, 5, 20))

        # Act
        response = self.client.get('/api/eventos/')

        # Assert: hoje a serialização ainda tenta acessar dataEvento.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()['results'][0]
        self.assertEqual(payload['id'], evento.pk)
        self.assertEqual(payload['data_evento'], '2030-05-20')
