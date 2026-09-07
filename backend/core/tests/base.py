from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase, APITransactionTestCase


class AuthenticatedTestMixin:
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username='usuario_teste',
            password='senha-exclusiva-de-teste',
        )
        self.client.force_authenticate(user=self.user)
        self.client.raise_request_exception = False


class AuthenticatedAPITestCase(AuthenticatedTestMixin, APITestCase):
    pass


class AuthenticatedAPITransactionTestCase(
    AuthenticatedTestMixin,
    APITransactionTestCase,
):
    pass
