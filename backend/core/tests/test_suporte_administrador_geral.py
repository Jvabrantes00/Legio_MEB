from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase
from rest_framework.test import APIClient, APIRequestFactory
from rest_framework_simplejwt.tokens import RefreshToken

from core.permissions import (
    HasAnySiaRole,
    pode_aprovar_encaminhamento_encontrista,
    pode_associar_foto_pessoa_pre_encontro,
    pode_configurar_pre_encontro,
    pode_consultar_cuidados_pre_encontro,
    pode_gerir_campanha_convites,
    pode_resolver_vaga_pre_encontro,
)
from core.roles import SiaRole, eh_administrador_geral
from core.tests.factories import make_alpinista, make_encontro
from core.views import (
    AlpinistaViewSet, CampanhaConvitesEncontroViewSet, EncontroViewSet,
    PropostaVioleirosViewSet, SessaoFormativaCommandViewSet,
)


class SuporteAdministradorGeralTests(TestCase):
    def setUp(self):
        self.suporte = User.objects.create_user('suporte-geral')
        self.suporte.groups.add(Group.objects.get(name=SiaRole.SUPORTE.value))
        self.diretoria = User.objects.create_user('diretoria-geral')
        self.diretoria.groups.add(Group.objects.get(name=SiaRole.DIRETORIA.value))
        self.fichas = User.objects.create_user('fichas-geral')
        self.fichas.groups.add(Group.objects.get(name=SiaRole.FICHAS.value))
        self.sem_papel = User.objects.create_user('sem-papel-geral')
        self.root = User.objects.create_superuser('root-geral')
        self.encontro = make_encontro()

    def test_predicado_exige_usuario_ativo_e_nao_promove_outros_papeis(self):
        for usuario in (self.suporte, self.root):
            self.assertTrue(eh_administrador_geral(usuario))
            usuario.is_active = False
            self.assertFalse(eh_administrador_geral(usuario))
        for usuario in (self.diretoria, self.fichas, self.sem_papel, AnonymousUser()):
            self.assertFalse(eh_administrador_geral(usuario))

    def test_policies_especificas_e_matriz_de_perfis(self):
        policies = (
            (lambda user: pode_gerir_campanha_convites(user), True, False),
            (lambda user: pode_aprovar_encaminhamento_encontrista(user, self.encontro), True, False),
            (lambda user: pode_configurar_pre_encontro(user, self.encontro), True, True),
            (lambda user: pode_resolver_vaga_pre_encontro(user, self.encontro), False, True),
            (lambda user: pode_associar_foto_pessoa_pre_encontro(user, self.encontro), True, False),
            (lambda user: pode_consultar_cuidados_pre_encontro(user, self.encontro), True, False),
        )
        for policy, fichas, diretoria in policies:
            with self.subTest(policy=policy):
                self.assertTrue(policy(self.suporte))
                self.assertTrue(policy(self.root))
                self.assertEqual(policy(self.fichas), fichas)
                self.assertEqual(policy(self.diretoria), diretoria)
                self.assertFalse(policy(self.sem_papel))
                self.suporte.is_active = False
                self.assertFalse(policy(self.suporte))
                self.suporte.is_active = True

    def test_has_any_role_nos_cinco_viewsets_e_default_deny(self):
        permission = HasAnySiaRole()
        for view_class in (AlpinistaViewSet, EncontroViewSet,
                           CampanhaConvitesEncontroViewSet,
                           PropostaVioleirosViewSet, SessaoFormativaCommandViewSet):
            for method, action in (('get', 'list'), ('post', 'create')):
                with self.subTest(view=view_class.__name__, action=action):
                    request = getattr(APIRequestFactory(), method)('/')
                    view = view_class()
                    view.action = action
                    request.user = self.suporte
                    self.assertTrue(permission.has_permission(request, view))
                    request.user = self.sem_papel
                    self.assertFalse(permission.has_permission(request, view))
                    self.suporte.is_active = False
                    request.user = self.suporte
                    self.assertFalse(permission.has_permission(request, view))
                    self.suporte.is_active = True

    def test_raiz_tecnica_e_grupos_nao_sao_acessiveis(self):
        grupos_antes = list(self.suporte.groups.values_list('pk', flat=True))
        api = APIClient()
        self.assertEqual(api.get('/api/').status_code, 401)
        token = RefreshToken.for_user(self.suporte).access_token
        api.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(api.get('/api/alpinistas/').status_code, 200)
        self.assertEqual(api.get('/api/').status_code, 403)
        self.client.force_login(self.suporte)
        self.assertEqual(self.client.get('/admin/').status_code, 302)
        self.assertEqual(self.client.post('/admin/auth/group/add/', {}).status_code, 302)
        self.assertEqual(list(self.suporte.groups.values_list('pk', flat=True)), grupos_antes)
        self.assertFalse(self.suporte.is_superuser)

    def test_http_recursos_transversais_e_perfis_inativos(self):
        api = APIClient()
        alpinista = make_alpinista()
        urls = (
            f'/api/alpinistas/{alpinista.pk}/',
            f'/api/encontros/{self.encontro.pk}/',
            f'/api/encontros/{self.encontro.pk}/workspace/equipes/',
            f'/api/propostas-violeiros/?encontro={self.encontro.pk}',
            f'/api/sessoes-formativas/?encontro={self.encontro.pk}',
            '/api/calendario-institucional/?inicio=2030-01-01&fim=2030-01-31',
            '/api/calendario-institucional/publicacoes/?escopo=INTERNO',
        )
        api.force_authenticate(self.suporte)
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(api.get(url).status_code, 200)
        self.assertEqual(api.patch(f'/api/alpinistas/{alpinista.pk}/',
                                   {'grupo': 'Atualizado'}, format='json').status_code, 200)
        self.assertEqual(api.patch(f'/api/encontros/{self.encontro.pk}/',
                                   {'local': 'Atualizado'}, format='json').status_code, 200)
        self.assertEqual(api.post(f'/api/campanhas-convites-encontros/{self.encontro.pk}/iniciar/',
                                  {}, format='json').status_code, 400)
        self.assertEqual(api.post('/api/propostas-violeiros/', {}, format='json').status_code, 400)
        self.assertEqual(api.post('/api/sessoes-formativas/', {}, format='json').status_code, 400)
        for usuario in (self.suporte, self.diretoria, self.fichas, self.root):
            usuario.is_active = False
            api.force_authenticate(usuario)
            for url in (urls[0], urls[1], urls[3], urls[4]):
                with self.subTest(usuario=usuario.username, url=url):
                    self.assertEqual(api.get(url).status_code, 403)
            usuario.is_active = True
        api.force_authenticate(self.fichas)
        self.assertEqual(api.post('/api/propostas-violeiros/', {}, format='json').status_code, 403)
        self.assertEqual(api.post('/api/sessoes-formativas/', {}, format='json').status_code, 403)
        api.force_authenticate(self.diretoria)
        self.assertEqual(api.post(f'/api/campanhas-convites-encontros/{self.encontro.pk}/iniciar/',
                                  {}, format='json').status_code, 403)
