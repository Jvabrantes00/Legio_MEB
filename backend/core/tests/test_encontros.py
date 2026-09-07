from rest_framework import status

from core.models import Encontro
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_encontro


class ExclusaoEncontroRegressionTests(AuthenticatedAPITestCase):
    def test_exclusao_de_encontro_deve_retornar_204(self):
        # Arrange
        encontro = make_encontro()

        # Act
        response = self.client.delete(f'/api/encontros/{encontro.pk}/')

        # Assert: hoje falha porque perform_destroy acessa instance.nome.
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Encontro.objects.filter(pk=encontro.pk).exists())
