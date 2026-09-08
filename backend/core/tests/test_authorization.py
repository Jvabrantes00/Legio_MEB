from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import LogSistema
from core.roles import SiaRole, user_has_any_role, user_has_role
from core.tests.factories import make_alpinista


class AuthorizationFoundationTests(APITestCase):
    protected_url = '/api/alpinistas/'
    summary_profile_fields = {
        'id',
        'nome',
        'foto',
        'idade',
        'grupo',
        'whatsapp',
        'batizado',
        'primeira_comunhao',
        'crismado',
    }

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

    def make_sensitive_alpinista(self, **overrides):
        values = {
            'cpf': '52998224725',
            'dataNascimento': timezone.localdate() - timedelta(days=365 * 20),
            'endereco': 'Endereço confidencial',
            'nomePai': 'Responsável pai',
            'telefonePai': '6100000001',
            'nomeMae': 'Responsável mãe',
            'telefoneMae': '6100000002',
            'restricaoSaude': 'Informação de saúde',
            'medicacao': 'Medicação confidencial',
            'grupo': 'Grupo Azul',
            'batizado': True,
            'primeira_comunhao': True,
            'crismado': False,
            'is_neurodivergente': True,
            'tipo_neurodivergente': 'Informação confidencial',
        }
        values.update(overrides)
        return make_alpinista(**values)

    def assert_role_receives_complete_profile(self, role, username):
        alpinista = self.make_sensitive_alpinista()
        self.authenticate(self.make_user(username, role))

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            {
                'cpf',
                'endereco',
                'dataNascimento',
                'restricaoSaude',
                'medicacao',
                'is_neurodivergente',
                'tipo_neurodivergente',
                'encontros_realizados',
                'historico_equipes',
                'historico_eventos',
            }.issubset(response.json().keys())
        )

    def get_first_list_item(self, response):
        payload = response.json()
        return payload['results'][0]

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

    def test_mme_recebe_leitura_mas_nao_acesso_administrativo(self):
        self.authenticate(self.make_user('mme', SiaRole.MME))

        self.assertEqual(
            self.client.get(self.protected_url).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get('/api/dashboard-stats/').status_code,
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

    def test_suporte_recebe_perfil_completo(self):
        self.assert_role_receives_complete_profile(SiaRole.SUPORTE, 'suporte-completo')

    def test_diretoria_recebe_perfil_completo(self):
        self.assert_role_receives_complete_profile(
            SiaRole.DIRETORIA,
            'diretoria-completo',
        )

    def test_fichas_recebe_perfil_completo(self):
        self.assert_role_receives_complete_profile(SiaRole.FICHAS, 'fichas-completo')

    def test_mme_lista_somente_campos_resumidos(self):
        self.make_sensitive_alpinista()
        self.authenticate(self.make_user('mme-resumo', SiaRole.MME))

        response = self.client.get('/api/alpinistas/')
        item = self.get_first_list_item(response)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(item),
            self.summary_profile_fields,
        )

    def test_formacao_consulta_detalhe_sem_campos_sensiveis(self):
        alpinista = self.make_sensitive_alpinista()
        self.authenticate(self.make_user('formacao-resumo', SiaRole.FORMACAO))

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(payload),
            self.summary_profile_fields,
        )
        self.assertTrue(
            {
                'cpf',
                'endereco',
                'email',
                'dataNascimento',
                'restricaoSaude',
                'medicacao',
                'is_neurodivergente',
                'tipo_neurodivergente',
                'encontros_realizados',
                'historico_equipes',
                'historico_eventos',
            }.isdisjoint(payload)
        )

    def test_todos_os_papeis_resumidos_podem_consultar_alpinista(self):
        alpinista = self.make_sensitive_alpinista()
        roles = (
            SiaRole.MME,
            SiaRole.FORMACAO,
            SiaRole.SECRETARIA,
            SiaRole.ACAO_SOCIAL,
            SiaRole.LITURGIA,
            SiaRole.EVENTOS,
            SiaRole.COMUNICACAO,
        )

        for index, role in enumerate(roles):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'resumido-{index}', role))
                response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(
                    set(response.json()),
                    self.summary_profile_fields,
                )

    def test_perfil_resumido_expoe_foto_existente(self):
        alpinista = self.make_sensitive_alpinista(foto='fotos/perfil.jpg')
        self.authenticate(self.make_user('mme-foto', SiaRole.MME))

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.json()['foto'].endswith('/media/fotos/perfil.jpg'))

    def test_perfil_resumido_retorna_foto_nula_quando_ausente(self):
        alpinista = self.make_sensitive_alpinista(foto=None)
        self.authenticate(self.make_user('mme-sem-foto', SiaRole.MME))

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.json()['foto'])

    def test_perfil_resumido_expoe_situacao_sacramental(self):
        alpinista = self.make_sensitive_alpinista(
            batizado=True,
            primeira_comunhao=False,
            crismado=None,
        )
        self.authenticate(self.make_user('mme-sacramentos', SiaRole.MME))

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIs(payload['batizado'], True)
        self.assertIs(payload['primeira_comunhao'], False)
        self.assertIsNone(payload['crismado'])

    def test_fichas_continua_podendo_editar_alpinista(self):
        alpinista = self.make_sensitive_alpinista()
        self.authenticate(self.make_user('fichas-update', SiaRole.FICHAS))

        response = self.client.patch(
            f'/api/alpinistas/{alpinista.pk}/',
            {'nome': 'Nome atualizado'},
            format='json',
        )
        alpinista.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(alpinista.nome, 'Nome atualizado')

    def test_papel_resumido_nao_pode_criar_alpinista(self):
        self.authenticate(self.make_user('mme-post', SiaRole.MME))

        response = self.client.post(
            '/api/alpinistas/',
            {'nome': 'Criação indevida'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_papel_resumido_nao_pode_editar_alpinista(self):
        alpinista = self.make_sensitive_alpinista()
        self.authenticate(self.make_user('mme-update', SiaRole.MME))

        patch_response = self.client.patch(
            f'/api/alpinistas/{alpinista.pk}/',
            {'nome': 'Alteração indevida'},
            format='json',
        )
        put_response = self.client.put(
            f'/api/alpinistas/{alpinista.pk}/',
            {'nome': 'Alteração indevida'},
            format='json',
        )

        self.assertEqual(patch_response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(put_response.status_code, status.HTTP_403_FORBIDDEN)

    def test_papel_resumido_nao_pode_excluir_alpinista(self):
        alpinista = self.make_sensitive_alpinista()
        self.authenticate(self.make_user('mme-delete', SiaRole.MME))

        response = self.client.delete(f'/api/alpinistas/{alpinista.pk}/')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_menor_recebe_responsaveis_no_perfil_resumido(self):
        birth_date = timezone.localdate() - timedelta(days=365 * 10)
        alpinista = self.make_sensitive_alpinista(dataNascimento=birth_date)
        self.authenticate(self.make_user('mme-menor', SiaRole.MME))

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')
        payload = response.json()

        expected_age = timezone.localdate().year - birth_date.year - (
            (timezone.localdate().month, timezone.localdate().day)
            < (birth_date.month, birth_date.day)
        )
        self.assertEqual(payload['idade'], expected_age)
        self.assertEqual(
            payload['responsaveis'],
            [
                {'nome': 'Responsável pai', 'telefone': '6100000001'},
                {'nome': 'Responsável mãe', 'telefone': '6100000002'},
            ],
        )

    def test_maior_nao_recebe_responsaveis_no_perfil_resumido(self):
        alpinista = self.make_sensitive_alpinista()
        self.authenticate(self.make_user('mme-maior', SiaRole.MME))

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')

        self.assertNotIn('responsaveis', response.json())
