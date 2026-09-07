from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import LogSistema
from core.roles import SiaRole, user_has_any_role, user_has_role


class AuthorizationFoundationTests(APITestCase):
    protected_url = '/api/alpinistas/'

    def make_user(self, username, *roles, is_superuser=False):
        user = get_user_model().objects.create_user(
            username=username,
            password='senha-exclusiva-de-teste',
            is_superuser=is_superuser,
            is_staff=is_superuser,
        )
        for role in roles:
            group, _ = Group.objects.get_or_create(name=role.value)
            user.groups.add(group)
        return user

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_usuario_anonimo_recebe_401(self):
        response = self.client.get(self.protected_url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_usuario_autenticado_sem_papel_recebe_403(self):
        self.authenticate(self.make_user('sem-papel'))

        response = self.client.get(self.protected_url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_superuser_possui_bypass(self):
        self.authenticate(self.make_user('superuser', is_superuser=True))

        response = self.client.get(self.protected_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_suporte_possui_acesso_administrativo(self):
        self.authenticate(self.make_user('suporte', SiaRole.SUPORTE))

        urls = (
            '/api/alpinistas/',
            '/api/encontros/',
            '/api/eventos/',
            '/api/funcoes/',
            '/api/participacoes-encontros/',
            '/api/participacoes-eventos/',
            '/api/dashboard-stats/',
            '/api/logs/',
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_200_OK,
                )

    def test_usuario_pode_possuir_dois_papeis(self):
        user = self.make_user('dois-papeis', SiaRole.MME, SiaRole.SUPORTE)
        self.authenticate(user)

        self.assertTrue(user_has_role(user, SiaRole.MME))
        self.assertTrue(user_has_role(user, SiaRole.SUPORTE))
        self.assertTrue(
            user_has_any_role(user, SiaRole.DIRETORIA, SiaRole.SUPORTE)
        )
        self.assertEqual(
            self.client.get(self.protected_url).status_code,
            status.HTTP_200_OK,
        )

    def test_mme_nao_recebe_acesso_administrativo(self):
        self.authenticate(self.make_user('mme', SiaRole.MME))

        for url in (self.protected_url, '/api/dashboard-stats/'):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_fichas_acessa_fluxos_provisorios_de_pessoas_e_encontros(self):
        self.authenticate(self.make_user('fichas', SiaRole.FICHAS))

        urls = (
            '/api/alpinistas/',
            '/api/encontros/',
            '/api/funcoes/',
            '/api/participacoes-encontros/',
            '/api/dashboard-stats/',
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_200_OK,
                )

    def test_fichas_nao_recebe_acesso_amplo_a_eventos_ou_logs(self):
        self.authenticate(self.make_user('fichas-limitado', SiaRole.FICHAS))

        for url in ('/api/eventos/', '/api/participacoes-eventos/', '/api/logs/'):
            with self.subTest(url=url):
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_logs_sao_somente_leitura_para_papel_autorizado(self):
        user = self.make_user('diretoria', SiaRole.DIRETORIA)
        self.authenticate(user)
        log = LogSistema.objects.create(
            usuario=user,
            acao='LOGIN',
            modulo='Autorização',
            descricao='Log criado pelo servidor para teste.',
        )

        self.assertEqual(
            self.client.get('/api/logs/').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post('/api/logs/', {}, format='json').status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.patch(
                f'/api/logs/{log.pk}/',
                {'descricao': 'alteração indevida'},
                format='json',
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(f'/api/logs/{log.pk}/').status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
