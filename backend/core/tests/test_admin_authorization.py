from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from core.roles import SiaRole


class DjangoAdminAuthorizationTests(TestCase):
    password = 'senha-exclusiva-de-teste'

    def make_user(self, username, **overrides):
        return get_user_model().objects.create_user(
            username=username,
            password=self.password,
            **overrides,
        )

    def assert_admin_blocked(self, user, path='/admin/'):
        self.client.force_login(user)
        response = self.client.get(path)

        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertIn('/admin/login/', response.url)
        self.client.logout()

    def test_superuser_acessa_admin_tecnico(self):
        superuser = self.make_user(
            'superuser-admin',
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_login(superuser)

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_staff_sem_ser_superuser_nao_acessa_admin(self):
        self.assert_admin_blocked(self.make_user('staff', is_staff=True))

    def test_staff_com_permissao_de_model_nao_acessa_admin(self):
        staff = self.make_user('staff-permissao', is_staff=True)
        staff.user_permissions.add(
            Permission.objects.get(codename='view_alpinista')
        )

        self.assert_admin_blocked(staff, '/admin/core/alpinista/')

    def test_suporte_nao_acessa_admin_mas_continua_acessando_api(self):
        suporte = self.make_user('suporte-admin')
        suporte.groups.add(Group.objects.get(name=SiaRole.SUPORTE.value))

        self.assert_admin_blocked(suporte)

        api_client = APIClient()
        api_client.force_authenticate(user=suporte)
        self.assertEqual(
            api_client.get('/api/alpinistas/').status_code,
            status.HTTP_200_OK,
        )


class ApiRootAuthorizationTests(TestCase):
    def make_user(self, username, role=None, is_superuser=False):
        user = get_user_model().objects.create_user(
            username=username,
            password='senha-exclusiva-de-teste',
            is_superuser=is_superuser,
            is_staff=is_superuser,
        )
        if role is not None:
            user.groups.add(Group.objects.get(name=role.value))
        return user

    def test_raiz_api_exige_autenticacao(self):
        self.assertEqual(
            APIClient().get('/api/').status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_raiz_api_bloqueia_papel_normal(self):
        client = APIClient()
        client.force_authenticate(
            user=self.make_user('suporte-root', SiaRole.SUPORTE)
        )

        self.assertEqual(
            client.get('/api/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_raiz_api_permite_superuser(self):
        client = APIClient()
        client.force_authenticate(
            user=self.make_user('superuser-root', is_superuser=True)
        )

        self.assertEqual(
            client.get('/api/').status_code,
            status.HTTP_200_OK,
        )
