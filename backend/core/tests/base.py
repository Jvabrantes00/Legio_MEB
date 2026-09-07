from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework.test import APITestCase, APITransactionTestCase

from core.roles import SiaRole


class AuthenticatedTestMixin:
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_user(
            username='usuario_teste',
            password='senha-exclusiva-de-teste',
        )
        support, _ = Group.objects.get_or_create(name=SiaRole.SUPORTE.value)
        self.user.groups.add(support)
        self.client.force_authenticate(user=self.user)
        self.client.raise_request_exception = False


class AuthenticatedAPITestCase(AuthenticatedTestMixin, APITestCase):
    pass


class AuthenticatedAPITransactionTestCase(
    AuthenticatedTestMixin,
    APITransactionTestCase,
):
    pass
