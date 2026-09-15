from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import SimpleTestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.backends import TokenBackend
from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from core.roles import SiaRole


class SimpleJWTConfigurationTests(SimpleTestCase):
    def test_contrato_simplejwt_e_explicito(self):
        jwt_settings = settings.SIMPLE_JWT

        self.assertIn(
            'rest_framework_simplejwt.token_blacklist',
            settings.INSTALLED_APPS,
        )
        self.assertEqual(jwt_settings['ACCESS_TOKEN_LIFETIME'], timedelta(minutes=15))
        self.assertEqual(jwt_settings['REFRESH_TOKEN_LIFETIME'], timedelta(days=7))
        self.assertIs(jwt_settings['ROTATE_REFRESH_TOKENS'], True)
        self.assertIs(jwt_settings['BLACKLIST_AFTER_ROTATION'], True)
        self.assertIs(jwt_settings['UPDATE_LAST_LOGIN'], False)
        self.assertEqual(jwt_settings['ALGORITHM'], 'HS256')
        self.assertEqual(jwt_settings['SIGNING_KEY'], settings.JWT_SIGNING_KEY)
        self.assertNotEqual(settings.JWT_SIGNING_KEY, settings.SECRET_KEY)
        self.assertEqual(jwt_settings['AUTH_HEADER_TYPES'], ('Bearer',))
        self.assertEqual(jwt_settings['USER_ID_FIELD'], 'id')
        self.assertEqual(jwt_settings['USER_ID_CLAIM'], 'user_id')
        self.assertEqual(jwt_settings['TOKEN_TYPE_CLAIM'], 'token_type')
        self.assertEqual(
            jwt_settings['AUTH_TOKEN_CLASSES'],
            ('rest_framework_simplejwt.tokens.AccessToken',),
        )


class JWTTestHelpers:
    token_url = '/api/token/'
    refresh_url = '/api/token/refresh/'
    blacklist_url = '/api/token/blacklist/'
    protected_url = '/api/alpinistas/'
    password = 'senha-exclusiva-de-teste'

    def make_user(self, username='usuario-jwt', *roles, **overrides):
        user = get_user_model().objects.create_user(
            username=username,
            password=self.password,
            **overrides,
        )
        for role in roles:
            group, _ = Group.objects.get_or_create(name=role.value)
            user.groups.add(group)
        return user

    def obtain_pair(self, user):
        response = self.client.post(
            self.token_url,
            {'username': user.username, 'password': self.password},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return response.json()

    def authorize(self, token):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

    def expired_access_for(self, user):
        token = AccessToken.for_user(user)
        token.set_exp(
            from_time=timezone.now() - timedelta(minutes=2),
            lifetime=timedelta(minutes=1),
        )
        return str(token)

    def expired_refresh_for(self, user):
        token = RefreshToken.for_user(user)
        token.set_exp(
            from_time=timezone.now() - timedelta(minutes=2),
            lifetime=timedelta(minutes=1),
        )
        return str(token)

    def token_with_wrong_signature(self, token):
        backend = TokenBackend(
            algorithm='HS256',
            signing_key='different-test-key-that-is-not-configured',
        )
        return backend.encode(dict(token.payload))

    def assert_unauthorized_get(self, token):
        self.authorize(token)
        self.assertEqual(
            self.client.get(self.protected_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


class JWTAuthenticationContractTests(JWTTestHelpers, APITestCase):
    def test_login_valido_emite_access_e_refresh_sem_dados_sensiveis(self):
        user = self.make_user()

        response = self.client.post(
            self.token_url,
            {'username': user.username, 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.json()), {'access', 'refresh'})
        self.assertNotIn('password', response.json())
        self.assertNotIn('password_hash', response.json())
        user.refresh_from_db()
        self.assertIsNone(user.last_login)

    def test_login_invalido_nao_permite_enumerar_conta(self):
        user = self.make_user()

        wrong_password = self.client.post(
            self.token_url,
            {'username': user.username, 'password': 'senha-incorreta'},
            format='json',
        )
        missing_user = self.client.post(
            self.token_url,
            {'username': 'usuario-inexistente', 'password': 'senha-incorreta'},
            format='json',
        )

        self.assertEqual(wrong_password.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(missing_user.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(wrong_password.json(), missing_user.json())

    def test_usuario_inativo_nao_recebe_tokens(self):
        user = self.make_user(is_active=False)

        response = self.client.post(
            self.token_url,
            {'username': user.username, 'password': self.password},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.json())
        self.assertNotIn('refresh', response.json())

    def test_claims_e_lifetimes_do_par_emitido(self):
        user = self.make_user()
        pair = self.obtain_pair(user)
        access = AccessToken(pair['access'])
        refresh = RefreshToken(pair['refresh'])

        self.assertEqual(access['token_type'], 'access')
        self.assertEqual(access['user_id'], str(user.pk))
        self.assertIn('exp', access)
        self.assertIn('iat', access)
        self.assertAlmostEqual(
            access['exp'] - access['iat'],
            settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
            delta=2,
        )
        self.assertEqual(refresh['token_type'], 'refresh')
        self.assertEqual(refresh['user_id'], str(user.pk))
        self.assertIn('exp', refresh)
        self.assertIn('iat', refresh)
        self.assertAlmostEqual(
            refresh['exp'] - refresh['iat'],
            settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds(),
            delta=2,
        )

    def test_access_valido_autentica_endpoint_protegido(self):
        user = self.make_user('suporte-jwt', SiaRole.SUPORTE)
        pair = self.obtain_pair(user)
        self.authorize(pair['access'])

        self.assertEqual(
            self.client.get(self.protected_url).status_code,
            status.HTTP_200_OK,
        )

    def test_access_rejeita_token_malformado_refresh_expirado_e_assinatura_incorreta(self):
        user = self.make_user('suporte-access-invalido', SiaRole.SUPORTE)
        pair = self.obtain_pair(user)

        invalid_tokens = {
            'malformed': 'token-malformado',
            'refresh': pair['refresh'],
            'expired': self.expired_access_for(user),
            'wrong-signature': self.token_with_wrong_signature(
                AccessToken.for_user(user)
            ),
        }
        for token_kind, token in invalid_tokens.items():
            with self.subTest(token_kind=token_kind):
                self.assert_unauthorized_get(token)

    def test_access_emitido_deixa_de_autenticar_usuario_inativo(self):
        user = self.make_user('usuario-depois-inativo', SiaRole.SUPORTE)
        access = self.obtain_pair(user)['access']
        user.is_active = False
        user.save(update_fields=['is_active'])

        self.assert_unauthorized_get(access)

    def test_access_emitido_deixa_de_autenticar_usuario_removido(self):
        user = self.make_user('usuario-removido', SiaRole.SUPORTE)
        access = self.obtain_pair(user)['access']
        user.delete()

        self.assert_unauthorized_get(access)

    def test_refresh_rotaciona_o_par_e_invalida_o_refresh_anterior(self):
        user = self.make_user()
        refresh = self.obtain_pair(user)['refresh']
        old_jti = RefreshToken(refresh)['jti']

        first = self.client.post(self.refresh_url, {'refresh': refresh}, format='json')
        replay = self.client.post(self.refresh_url, {'refresh': refresh}, format='json')

        self.assertEqual(first.status_code, status.HTTP_200_OK)
        self.assertEqual(set(first.json()), {'access', 'refresh'})
        self.assertEqual(AccessToken(first.json()['access'])['user_id'], str(user.pk))
        self.assertEqual(RefreshToken(first.json()['refresh'])['user_id'], str(user.pk))
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=old_jti).exists()
        )
        self.assertEqual(replay.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rotacionado_novo_permanece_utilizavel(self):
        user = self.make_user('refresh-novo-valido')
        original = self.obtain_pair(user)['refresh']
        rotated = self.client.post(
            self.refresh_url,
            {'refresh': original},
            format='json',
        ).json()['refresh']

        response = self.client.post(
            self.refresh_url,
            {'refresh': rotated},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.json()), {'access', 'refresh'})

    def test_blacklist_app_registra_tokens_emitidos(self):
        user = self.make_user('outstanding-token')
        refresh = self.obtain_pair(user)['refresh']
        jti = RefreshToken(refresh)['jti']

        outstanding = OutstandingToken.objects.get(jti=jti)

        self.assertEqual(outstanding.user, user)
        self.assertFalse(
            BlacklistedToken.objects.filter(token=outstanding).exists()
        )

    def test_refresh_valido_pode_ser_revogado_e_nao_pode_ser_reutilizado(self):
        user = self.make_user('refresh-revogado')
        refresh = self.obtain_pair(user)['refresh']

        revoked = self.client.post(
            self.blacklist_url,
            {'refresh': refresh},
            format='json',
        )
        replay = self.client.post(
            self.refresh_url,
            {'refresh': refresh},
            format='json',
        )

        self.assertEqual(revoked.status_code, status.HTTP_200_OK)
        self.assertEqual(replay.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blacklist_rejeita_token_invalido_e_access_token(self):
        user = self.make_user('blacklist-invalida')
        access = self.obtain_pair(user)['access']

        for token_kind, token in {
            'malformed': 'token-invalido',
            'access': access,
        }.items():
            with self.subTest(token_kind=token_kind):
                response = self.client.post(
                    self.blacklist_url,
                    {'refresh': token},
                    format='json',
                )
                self.assertEqual(
                    response.status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_refresh_emitido_deixa_de_funcionar_para_usuario_inativo(self):
        user = self.make_user('refresh-usuario-inativo')
        refresh = self.obtain_pair(user)['refresh']
        user.is_active = False
        user.save(update_fields=['is_active'])

        response = self.client.post(
            self.refresh_url,
            {'refresh': refresh},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_emitido_deixa_de_funcionar_para_usuario_removido(self):
        user = self.make_user('refresh-usuario-removido')
        refresh = self.obtain_pair(user)['refresh']
        user.delete()

        response = self.client.post(
            self.refresh_url,
            {'refresh': refresh},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_rejeita_access_malformado_expirado_e_assinatura_incorreta(self):
        user = self.make_user()
        pair = self.obtain_pair(user)
        invalid_refreshes = {
            'access': pair['access'],
            'malformed': 'refresh-malformado',
            'expired': self.expired_refresh_for(user),
            'wrong-signature': self.token_with_wrong_signature(
                RefreshToken.for_user(user)
            ),
        }

        for token_kind, token in invalid_refreshes.items():
            with self.subTest(token_kind=token_kind):
                response = self.client.post(
                    self.refresh_url,
                    {'refresh': token},
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class CurrentUserEndpointTests(JWTTestHelpers, APITestCase):
    me_url = '/api/auth/me/'

    def authenticated_me(self, user):
        self.authorize(self.obtain_pair(user)['access'])
        return self.client.get(self.me_url)

    def test_me_retorna_identidade_e_papel_reconhecido(self):
        user = self.make_user('usuario-me', SiaRole.SUPORTE)

        response = self.authenticated_me(user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {
                'id': user.pk,
                'username': user.username,
                'roles': [SiaRole.SUPORTE.value],
                'superuser': False,
            },
        )

    def test_me_retorna_multiplos_papeis_em_ordem_canonica_e_ignora_desconhecido(self):
        user = self.make_user(
            'usuario-multiplos-papeis',
            SiaRole.COMUNICACAO,
            SiaRole.FICHAS,
        )
        user.groups.add(Group.objects.create(name='Grupo fora do SIA'))

        response = self.authenticated_me(user)

        self.assertEqual(
            response.json()['roles'],
            [SiaRole.FICHAS.value, SiaRole.COMUNICACAO.value],
        )

    def test_me_permite_identificar_token_valido_sem_papel(self):
        user = self.make_user('usuario-sem-papel-me')

        response = self.authenticated_me(user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['roles'], [])
        self.assertIs(response.json()['superuser'], False)

    def test_me_sinaliza_superuser_sem_inventar_papel_suporte(self):
        user = self.make_user(
            'superuser-me',
            is_superuser=True,
            is_staff=True,
        )

        response = self.authenticated_me(user)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['roles'], [])
        self.assertIs(response.json()['superuser'], True)

    def test_me_rejeita_anonimo_refresh_e_access_invalido(self):
        self.assertEqual(
            self.client.get(self.me_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        user = self.make_user('usuario-me-invalido')
        refresh = self.obtain_pair(user)['refresh']
        invalid_tokens = {
            'refresh': refresh,
            'malformed': 'access-malformado',
        }
        for token_kind, token in invalid_tokens.items():
            with self.subTest(token_kind=token_kind):
                self.authorize(token)
                self.assertEqual(
                    self.client.get(self.me_url).status_code,
                    status.HTTP_401_UNAUTHORIZED,
                )

    def test_me_e_somente_leitura(self):
        user = self.make_user('usuario-me-readonly')
        self.authorize(self.obtain_pair(user)['access'])

        for method in ('post', 'put', 'patch', 'delete'):
            with self.subTest(method=method):
                response = getattr(self.client, method)(self.me_url, {}, format='json')
                self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_me_nao_muda_default_deny_dos_recursos_de_negocio(self):
        user = self.make_user('usuario-sem-papel-negocio')
        access = self.obtain_pair(user)['access']
        self.authorize(access)

        self.assertEqual(self.client.get(self.me_url).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.get(self.protected_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
