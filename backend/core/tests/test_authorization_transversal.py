from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import Material
from core.roles import SiaRole
from core.tests.factories import make_alpinista, make_encontro, make_evento


class FinalAuthorizationMatrixTests(APITestCase):
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

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_acao_social_e_liturgia_ficam_restritas_ao_perfil_resumido(self):
        alpinista = make_alpinista(
            nome='Pessoa pesquisável',
            telefone='61988887777',
            grupo='Grupo Visível',
        )
        encontro = make_encontro()

        for index, role in enumerate((SiaRole.ACAO_SOCIAL, SiaRole.LITURGIA)):
            with self.subTest(role=role.value):
                user = self.make_user(f'papel-restrito-{index}', role)
                self.authenticate(user)

                for url in (
                    '/api/alpinistas/',
                    f'/api/alpinistas/{alpinista.pk}/',
                    '/api/alpinistas/?search=Pessoa pesquisável',
                    '/api/alpinistas/?ordering=grupo',
                ):
                    self.assertEqual(
                        self.client.get(url).status_code,
                        status.HTTP_200_OK,
                    )

                blocked_requests = (
                    self.client.patch(
                        f'/api/alpinistas/{alpinista.pk}/',
                        {'nome': 'Alteração indevida'},
                        format='json',
                    ),
                    self.client.patch(
                        f'/api/alpinistas/{alpinista.pk}/foto/',
                        {},
                        format='json',
                    ),
                    self.client.patch(
                        f'/api/alpinistas/{alpinista.pk}/musica/',
                        {'canta': True},
                        format='json',
                    ),
                    self.client.get(
                        f'/api/alpinistas/{alpinista.pk}/historico-violeiro/'
                    ),
                    self.client.get(
                        f'/api/alpinistas/{alpinista.pk}/historico-palestras/'
                    ),
                    self.client.get('/api/encontros/'),
                    self.client.get(f'/api/encontros/{encontro.pk}/fotos/'),
                    self.client.get('/api/funcoes/'),
                    self.client.get('/api/participacoes-encontros/'),
                    self.client.get('/api/eventos/'),
                    self.client.get('/api/participacoes-eventos/'),
                    self.client.get('/api/materiais/'),
                    self.client.get('/api/entregas-materiais/'),
                    self.client.get('/api/dashboard-stats/'),
                    self.client.get('/api/logs/'),
                    self.client.get('/api/'),
                    self.client.get('/api/alpinistas/?status=ativo'),
                )
                for response in blocked_requests:
                    self.assertEqual(
                        response.status_code,
                        status.HTTP_403_FORBIDDEN,
                    )

                admin_client = Client()
                admin_client.force_login(user)
                admin_response = admin_client.get('/admin/')
                self.assertEqual(
                    admin_response.status_code,
                    status.HTTP_302_FOUND,
                )
                self.assertIn('/admin/login/', admin_response.url)

    def test_superuser_mantem_bypass_transversal_sem_ampliar_metodos(self):
        alpinista = make_alpinista()
        encontro = make_encontro()
        evento = make_evento()
        material = Material.objects.create(
            nome='Material do teste transversal',
            quantidade_disponivel=2,
        )
        self.authenticate(self.make_user('superuser-transversal', is_superuser=True))

        expected_responses = (
            (self.client.get('/api/alpinistas/'), status.HTTP_200_OK),
            (
                self.client.patch(
                    f'/api/alpinistas/{alpinista.pk}/',
                    {'grupo': 'Grupo atualizado'},
                    format='json',
                ),
                status.HTTP_200_OK,
            ),
            (
                self.client.patch(
                    f'/api/alpinistas/{alpinista.pk}/musica/',
                    {'canta': True},
                    format='json',
                ),
                status.HTTP_200_OK,
            ),
            (
                self.client.patch(
                    f'/api/alpinistas/{alpinista.pk}/foto/',
                    {},
                    format='json',
                ),
                status.HTTP_400_BAD_REQUEST,
            ),
            (
                self.client.get(
                    f'/api/alpinistas/{alpinista.pk}/foto-arquivo/'
                ),
                status.HTTP_404_NOT_FOUND,
            ),
            (
                self.client.get(
                    f'/api/alpinistas/{alpinista.pk}/historico-violeiro/'
                ),
                status.HTTP_200_OK,
            ),
            (
                self.client.get(
                    f'/api/alpinistas/{alpinista.pk}/historico-palestras/'
                ),
                status.HTTP_200_OK,
            ),
            (self.client.get('/api/encontros/'), status.HTTP_200_OK),
            (
                self.client.get(f'/api/encontros/{encontro.pk}/fotos/'),
                status.HTTP_200_OK,
            ),
            (self.client.get('/api/funcoes/'), status.HTTP_200_OK),
            (
                self.client.get('/api/participacoes-encontros/'),
                status.HTTP_200_OK,
            ),
            (self.client.get('/api/eventos/'), status.HTTP_200_OK),
            (
                self.client.patch(
                    f'/api/eventos/{evento.pk}/',
                    {'local': 'Local atualizado'},
                    format='json',
                ),
                status.HTTP_200_OK,
            ),
            (
                self.client.get('/api/participacoes-eventos/'),
                status.HTTP_200_OK,
            ),
            (self.client.get('/api/materiais/'), status.HTTP_200_OK),
            (
                self.client.patch(
                    f'/api/materiais/{material.pk}/',
                    {'quantidade_disponivel': 3},
                    format='json',
                ),
                status.HTTP_200_OK,
            ),
            (
                self.client.get('/api/entregas-materiais/'),
                status.HTTP_200_OK,
            ),
            (self.client.get('/api/dashboard-stats/'), status.HTTP_200_OK),
            (self.client.get('/api/logs/'), status.HTTP_200_OK),
            (
                self.client.post('/api/logs/', {}, format='json'),
                status.HTTP_405_METHOD_NOT_ALLOWED,
            ),
            (self.client.get('/api/'), status.HTTP_200_OK),
        )

        for response, expected_status in expected_responses:
            self.assertEqual(response.status_code, expected_status)
