from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    Alpinista,
    FuncaoEncontro,
    LogSistema,
    Palestra,
    ParticipacaoEncontro,
    ParticipacaoEvento,
)
from core.roles import SiaRole, user_has_any_role, user_has_role
from core.tests.factories import (
    make_alpinista,
    make_encontro,
    make_evento,
    make_funcao,
)


class SiaAuthorizationTestCase(APITestCase):
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


class AuthorizationFoundationTests(SiaAuthorizationTestCase):
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
        'musica',
    }

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

    def test_fichas_acessa_fluxos_de_pessoas_e_encontros(self):
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


class AdministrativeRoleMatrixTests(SiaAuthorizationTestCase):
    non_administrative_roles = (
        SiaRole.MME,
        SiaRole.FORMACAO,
        SiaRole.SECRETARIA,
        SiaRole.ACAO_SOCIAL,
        SiaRole.LITURGIA,
        SiaRole.EVENTOS,
        SiaRole.COMUNICACAO,
    )

    def assert_crud_allowed(self, base_url, create_payload, update_payload):
        self.assertEqual(self.client.get(base_url).status_code, status.HTTP_200_OK)

        create_response = self.client.post(base_url, create_payload, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        detail_url = f"{base_url}{create_response.json()['id']}/"

        self.assertEqual(
            self.client.get(detail_url).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.put(detail_url, create_payload, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.patch(detail_url, update_payload, format='json').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )

    def assert_people_and_encounter_crud(self, suffix):
        self.assert_crud_allowed(
            '/api/alpinistas/',
            {
                'nome': f'Alpinista administrativo {suffix}',
                'email': f'administrativo-{suffix}@example.test',
                'telefone': '61999990000',
            },
            {'nome': f'Alpinista atualizado {suffix}'},
        )
        self.assert_crud_allowed(
            '/api/encontros/',
            {
                'encontro': f'Encontro administrativo {suffix}',
                'tipo': 'Escalada',
                'data_referencia': '2031-01-01',
                'data_exato': '1 de janeiro de 2031',
                'local': 'Local administrativo',
                'status': 'agendado',
            },
            {'local': 'Local atualizado'},
        )
        self.assert_crud_allowed(
            '/api/funcoes/',
            {
                'nome': f'Equipe administrativa {suffix}',
                'tipo': 'equipe',
                'descricao_faq': 'Descrição para teste',
                'ordem': 10,
            },
            {'ordem': 11},
        )

        alpinista = make_alpinista()
        encontro = make_encontro()
        funcao = make_funcao()
        self.assert_crud_allowed(
            '/api/participacoes-encontros/',
            {
                'alpinista_id': alpinista.pk,
                'encontro_id': encontro.pk,
                'funcao_id': funcao.pk,
                'cor_grupo': 'Azul',
            },
            {'cor_grupo': 'Verde'},
        )

    def assert_event_crud(self, suffix):
        self.assert_crud_allowed(
            '/api/eventos/',
            {
                'nome': f'Evento administrativo {suffix}',
                'data_evento': '2031-02-01',
                'local': 'Local do evento',
            },
            {'local': 'Local atualizado'},
        )

        alpinista = make_alpinista()
        evento = make_evento()
        self.assert_crud_allowed(
            '/api/participacoes-eventos/',
            {'alpinista': alpinista.pk, 'evento': evento.pk},
            {'evento': evento.pk},
        )

    def test_suporte_e_diretoria_possuem_crud_administrativo_amplo(self):
        for index, role in enumerate((SiaRole.SUPORTE, SiaRole.DIRETORIA)):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'admin-{index}', role))
                self.assert_people_and_encounter_crud(f'admin-{index}')
                self.assert_event_crud(f'admin-{index}')
                self.assertEqual(
                    self.client.get('/api/dashboard-stats/').status_code,
                    status.HTTP_200_OK,
                )

    def test_suporte_e_diretoria_leem_logs_mas_nao_os_modificam(self):
        for index, role in enumerate((SiaRole.SUPORTE, SiaRole.DIRETORIA)):
            with self.subTest(role=role.value):
                user = self.make_user(f'logs-admin-{index}', role)
                self.authenticate(user)
                log = LogSistema.objects.create(
                    usuario=user,
                    acao='LOGIN',
                    modulo='Autorização',
                    descricao='Log criado pelo servidor.',
                )

                self.assertEqual(
                    self.client.get('/api/logs/').status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    self.client.get(f'/api/logs/{log.pk}/').status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    self.client.post('/api/logs/', {}, format='json').status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
                self.assertEqual(
                    self.client.put(
                        f'/api/logs/{log.pk}/',
                        {},
                        format='json',
                    ).status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
                self.assertEqual(
                    self.client.patch(
                        f'/api/logs/{log.pk}/',
                        {},
                        format='json',
                    ).status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )
                self.assertEqual(
                    self.client.delete(f'/api/logs/{log.pk}/').status_code,
                    status.HTTP_405_METHOD_NOT_ALLOWED,
                )

    def test_fichas_possui_crud_de_pessoas_e_encontros_e_dashboard(self):
        self.authenticate(self.make_user('fichas-matriz', SiaRole.FICHAS))

        self.assert_people_and_encounter_crud('fichas')
        self.assertEqual(
            self.client.get('/api/dashboard-stats/').status_code,
            status.HTTP_200_OK,
        )

    def assert_all_methods_forbidden(self, base_url, detail_url):
        requests = (
            self.client.get(base_url),
            self.client.post(base_url, {}, format='json'),
            self.client.get(detail_url),
            self.client.put(detail_url, {}, format='json'),
            self.client.patch(detail_url, {}, format='json'),
            self.client.delete(detail_url),
        )
        for response in requests:
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_fichas_nao_acessa_eventos_participacoes_de_evento_ou_logs(self):
        user = self.make_user('fichas-bloqueado', SiaRole.FICHAS)
        evento = make_evento()
        participacao = ParticipacaoEvento.objects.create(
            alpinista=make_alpinista(),
            evento=evento,
        )
        log = LogSistema.objects.create(
            usuario=user,
            acao='LOGIN',
            modulo='Autorização',
            descricao='Log protegido.',
        )
        self.authenticate(user)

        self.assert_all_methods_forbidden(
            '/api/eventos/',
            f'/api/eventos/{evento.pk}/',
        )
        self.assert_all_methods_forbidden(
            '/api/participacoes-eventos/',
            f'/api/participacoes-eventos/{participacao.pk}/',
        )
        self.assert_all_methods_forbidden(
            '/api/logs/',
            f'/api/logs/{log.pk}/',
        )

    def test_actions_de_encontro_sao_permitidas_aos_papeis_administrativos(self):
        roles = (SiaRole.SUPORTE, SiaRole.DIRETORIA, SiaRole.FICHAS)
        for index, role in enumerate(roles):
            with self.subTest(role=role.value):
                encontro = make_encontro()
                alpinista = make_alpinista()
                self.authenticate(self.make_user(f'action-admin-{index}', role))
                payload = {'alpinistas_ids': [alpinista.pk]}

                self.assertEqual(
                    self.client.post(
                        f'/api/encontros/{encontro.pk}/efetivar-encontristas/',
                        payload,
                        format='json',
                    ).status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    self.client.post(
                        f'/api/encontros/{encontro.pk}/remover-encontristas/',
                        payload,
                        format='json',
                    ).status_code,
                    status.HTTP_200_OK,
                )

    def test_papeis_nao_administrativos_nao_contornam_actions_diretas(self):
        encontro = make_encontro()
        alpinista = make_alpinista()
        payload = {'alpinistas_ids': [alpinista.pk]}
        action_urls = (
            f'/api/encontros/{encontro.pk}/efetivar-encontristas/',
            f'/api/encontros/{encontro.pk}/remover-encontristas/',
        )

        for index, role in enumerate(self.non_administrative_roles):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'action-negada-{index}', role))
                for url in action_urls:
                    self.assertEqual(
                        self.client.post(url, payload, format='json').status_code,
                        status.HTTP_403_FORBIDDEN,
                    )

    def test_papeis_nao_administrativos_nao_recebem_novos_acessos(self):
        restricted_urls = (
            '/api/encontros/',
            '/api/funcoes/',
            '/api/participacoes-encontros/',
            '/api/eventos/',
            '/api/participacoes-eventos/',
            '/api/dashboard-stats/',
            '/api/logs/',
        )
        for index, role in enumerate(self.non_administrative_roles):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'nao-admin-{index}', role))
                for url in restricted_urls:
                    self.assertEqual(
                        self.client.get(url).status_code,
                        status.HTTP_403_FORBIDDEN,
                    )


class MMEMusicaAuthorizationTests(SiaAuthorizationTestCase):
    def test_mme_altera_e_desmarca_musica_com_log_de_auditoria(self):
        alpinista = make_alpinista()
        user = self.make_user('mme-violeiro', SiaRole.MME)
        self.authenticate(user)
        url = f'/api/alpinistas/{alpinista.pk}/musica/'

        marcar = self.client.patch(
            url,
            {'violeiro': True, 'canta': True},
            format='json',
        )
        alpinista.refresh_from_db()

        self.assertEqual(marcar.status_code, status.HTTP_200_OK)
        self.assertIs(alpinista.eh_violeiro, True)
        self.assertIs(alpinista.canta, True)
        self.assertEqual(
            marcar.json(),
            {
                'id': alpinista.pk,
                'musica': {'violeiro': True, 'canta': True},
            },
        )
        log = LogSistema.objects.get(usuario=user, modulo='Alpinista')
        self.assertIn(str(alpinista.pk), log.descricao)
        self.assertIn('eh_violeiro: False -> True', log.descricao)
        self.assertIn('canta: False -> True', log.descricao)
        self.assertNotIn(alpinista.nome, log.descricao)
        self.assertNotIn(alpinista.cpf or 'cpf-ausente', log.descricao)

        desmarcar = self.client.patch(
            url,
            {'violeiro': False, 'canta': False},
            format='json',
        )
        alpinista.refresh_from_db()

        self.assertEqual(desmarcar.status_code, status.HTTP_200_OK)
        self.assertIs(alpinista.eh_violeiro, False)
        self.assertIs(alpinista.canta, False)
        self.assertEqual(
            LogSistema.objects.filter(usuario=user, modulo='Alpinista').count(),
            2,
        )

    def test_mme_altera_somente_canta_sem_mudar_indicacao_de_violeiro(self):
        alpinista = make_alpinista(eh_violeiro=True, canta=False)
        self.authenticate(self.make_user('mme-somente-canta', SiaRole.MME))

        marcar = self.client.patch(
            f'/api/alpinistas/{alpinista.pk}/musica/',
            {'canta': True},
            format='json',
        )
        alpinista.refresh_from_db()

        self.assertEqual(marcar.status_code, status.HTTP_200_OK)
        self.assertIs(alpinista.eh_violeiro, True)
        self.assertIs(alpinista.canta, True)

        desmarcar = self.client.patch(
            f'/api/alpinistas/{alpinista.pk}/musica/',
            {'canta': False},
            format='json',
        )
        alpinista.refresh_from_db()

        self.assertEqual(desmarcar.status_code, status.HTTP_200_OK)
        self.assertIs(alpinista.eh_violeiro, True)
        self.assertIs(alpinista.canta, False)

    def test_action_rejeita_campos_extras_sem_alterar_a_ficha(self):
        alpinista = make_alpinista(cpf='52998224725')
        nome_original = alpinista.nome
        cpf_original = alpinista.cpf
        self.authenticate(self.make_user('mme-payload-estrito', SiaRole.MME))

        response = self.client.patch(
            f'/api/alpinistas/{alpinista.pk}/musica/',
            {
                'violeiro': True,
                'canta': True,
                'nome': 'Nome alterado indevidamente',
                'cpf': '11144477735',
            },
            format='json',
        )
        alpinista.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('campos_extras', response.json())
        self.assertIs(alpinista.eh_violeiro, False)
        self.assertIs(alpinista.canta, False)
        self.assertEqual(alpinista.nome, nome_original)
        self.assertEqual(alpinista.cpf, cpf_original)
        self.assertFalse(LogSistema.objects.exists())

    def test_papeis_autorizados_podem_alterar_caracteristicas_musicais(self):
        roles = (
            SiaRole.SUPORTE,
            SiaRole.DIRETORIA,
            SiaRole.FICHAS,
            SiaRole.MME,
        )
        for index, role in enumerate(roles):
            with self.subTest(role=role.value):
                alpinista = make_alpinista()
                self.authenticate(self.make_user(f'violeiro-permitido-{index}', role))

                response = self.client.patch(
                    f'/api/alpinistas/{alpinista.pk}/musica/',
                    {'violeiro': True, 'canta': True},
                    format='json',
                )
                alpinista.refresh_from_db()

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIs(alpinista.eh_violeiro, True)
                self.assertIs(alpinista.canta, True)

    def test_formacao_e_comunicacao_nao_podem_alterar_indicacao(self):
        for index, role in enumerate((SiaRole.FORMACAO, SiaRole.COMUNICACAO)):
            with self.subTest(role=role.value):
                alpinista = make_alpinista()
                self.authenticate(self.make_user(f'violeiro-negado-{index}', role))

                response = self.client.patch(
                    f'/api/alpinistas/{alpinista.pk}/musica/',
                    {'violeiro': True, 'canta': True},
                    format='json',
                )
                alpinista.refresh_from_db()

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
                self.assertIs(alpinista.eh_violeiro, False)
                self.assertIs(alpinista.canta, False)

    def test_mme_consulta_somente_historico_marcado_como_violeiro(self):
        alpinista = make_alpinista(
            cpf='52998224725',
            restricaoSaude='Dado privado',
            medicacao='Dado privado',
            is_neurodivergente=True,
        )
        funcao_violeiro = make_funcao(
            nome='Violeiro',
            tipo='equipe',
            eh_violeiro=True,
        )
        outra_funcao = make_funcao(
            nome='Violeiro',
            tipo='equipe',
            eh_violeiro=False,
        )
        encontro_violeiro = make_encontro(
            encontro='Escalada com música',
            tipo='Escalada',
            data_referencia=date(2031, 5, 10),
        )
        outro_encontro = make_encontro(
            encontro='Escalada em outra equipe',
            data_referencia=date(2031, 6, 10),
        )
        ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=encontro_violeiro,
            funcao=funcao_violeiro,
        )
        ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=outro_encontro,
            funcao=outra_funcao,
        )
        self.authenticate(self.make_user('mme-historico', SiaRole.MME))

        response = self.client.get(
            f'/api/alpinistas/{alpinista.pk}/historico-violeiro/'
        )
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(payload), 1)
        self.assertEqual(
            set(payload[0]),
            {
                'encontro_id',
                'nome_encontro',
                'tipo_encontro',
                'data_encontro',
                'funcao',
            },
        )
        self.assertEqual(payload[0]['encontro_id'], encontro_violeiro.pk)
        self.assertEqual(payload[0]['nome_encontro'], 'Escalada com música')
        self.assertEqual(payload[0]['data_encontro'], '2031-05-10')
        self.assertNotEqual(payload[0]['encontro_id'], outro_encontro.pk)
        self.assertNotIn(alpinista.cpf, str(payload))
        self.assertNotIn('Dado privado', str(payload))

    def test_historico_restrito_por_papel_e_autenticacao(self):
        alpinista = make_alpinista()
        url = f'/api/alpinistas/{alpinista.pk}/historico-violeiro/'

        self.assertEqual(
            self.client.get(url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.authenticate(self.make_user('historico-sem-papel'))
        self.assertEqual(
            self.client.get(url).status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.authenticate(self.make_user('historico-formacao', SiaRole.FORMACAO))
        self.assertEqual(
            self.client.get(url).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_perfil_resumido_agrupa_caracteristicas_musicais(self):
        alpinista = make_alpinista(eh_violeiro=True, canta=True)
        self.authenticate(self.make_user('mme-perfil-musical', SiaRole.MME))

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload['musica'], {'violeiro': True, 'canta': True})
        self.assertNotIn('eh_violeiro', payload)
        self.assertNotIn('canta', payload)

    def test_filtro_retorna_somente_alpinistas_indicados(self):
        indicado = make_alpinista(eh_violeiro=True)
        make_alpinista(eh_violeiro=False)
        self.authenticate(self.make_user('mme-filtro', SiaRole.MME))

        response = self.client.get('/api/alpinistas/?eh_violeiro=true')
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in payload['results']], [indicado.pk])
        self.assertTrue(payload['results'][0]['musica']['violeiro'])

    def test_filtros_de_canto_e_violeiro_funcionam_em_conjunto(self):
        ambos = make_alpinista(eh_violeiro=True, canta=True)
        make_alpinista(eh_violeiro=True, canta=False)
        somente_cantor = make_alpinista(eh_violeiro=False, canta=True)
        self.authenticate(self.make_user('mme-filtro-musical', SiaRole.MME))

        resposta_canto = self.client.get('/api/alpinistas/?canta=true')
        resposta_combinada = self.client.get(
            '/api/alpinistas/?eh_violeiro=true&canta=true'
        )
        somente_canto = resposta_canto.json()
        combinados = resposta_combinada.json()

        self.assertEqual(resposta_canto.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta_combinada.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item['id'] for item in somente_canto['results']},
            {ambos.pk, somente_cantor.pk},
        )
        self.assertEqual(
            [item['id'] for item in combinados['results']],
            [ambos.pk],
        )

    def test_nao_existe_classificacao_ou_historico_independente_de_canto(self):
        self.assertFalse(hasattr(FuncaoEncontro, 'eh_canto'))
        alpinista = make_alpinista(canta=True)
        self.authenticate(self.make_user('mme-sem-historico-canto', SiaRole.MME))

        response = self.client.get(
            f'/api/alpinistas/{alpinista.pk}/historico-canto/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class FormacaoPalestraAuthorizationTests(SiaAuthorizationTestCase):
    summary_profile_fields = AuthorizationFoundationTests.summary_profile_fields

    def test_formacao_le_perfil_resumido_sem_receber_escrita(self):
        alpinista = make_alpinista()
        self.authenticate(self.make_user('formacao-isolada', SiaRole.FORMACAO))
        detail_url = f'/api/alpinistas/{alpinista.pk}/'

        detail_response = self.client.get(detail_url)

        self.assertEqual(detail_response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(detail_response.json()), self.summary_profile_fields)
        self.assertEqual(
            self.client.patch(
                detail_url,
                {'nome': 'Alteração indevida'},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post('/api/alpinistas/', {}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.patch(
                f'/api/alpinistas/{alpinista.pk}/musica/',
                {'canta': True},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(
                f'/api/alpinistas/{alpinista.pk}/historico-violeiro/'
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_historico_retorna_duas_palestras_e_exclui_trabalho_em_equipe(self):
        alpinista = make_alpinista(
            cpf='52998224725',
            restricaoSaude='Dado privado',
            medicacao='Dado privado',
            is_neurodivergente=True,
        )
        encontro = make_encontro(
            encontro='Escalada da Formação',
            tipo='Escalada',
            data_referencia=date(2032, 3, 20),
        )
        Palestra.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            titulo='Família e comunidade',
        )
        Palestra.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            titulo='Serviço e espiritualidade',
        )
        ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            funcao=make_funcao(nome='Cozinha', tipo='equipe'),
        )
        self.authenticate(self.make_user('formacao-historico', SiaRole.FORMACAO))

        response = self.client.get(
            f'/api/alpinistas/{alpinista.pk}/historico-palestras/'
        )
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(payload), 2)
        self.assertEqual(
            {item['titulo'] for item in payload},
            {'Família e comunidade', 'Serviço e espiritualidade'},
        )
        for item in payload:
            self.assertEqual(
                set(item),
                {
                    'encontro_id',
                    'nome_encontro',
                    'tipo_encontro',
                    'data_encontro',
                    'titulo',
                },
            )
            self.assertEqual(item['encontro_id'], encontro.pk)
            self.assertEqual(item['nome_encontro'], 'Escalada da Formação')
            self.assertEqual(item['tipo_encontro'], 'Escalada')
            self.assertEqual(item['data_encontro'], '2032-03-20')
        self.assertNotIn('Cozinha', str(payload))
        self.assertNotIn(alpinista.cpf, str(payload))
        self.assertNotIn('Dado privado', str(payload))

    def test_papeis_autorizados_consultam_historico_de_palestras(self):
        roles = (
            SiaRole.SUPORTE,
            SiaRole.DIRETORIA,
            SiaRole.FICHAS,
            SiaRole.FORMACAO,
        )
        alpinista = make_alpinista()
        encontro = make_encontro()
        Palestra.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            titulo='Palestra autorizada',
        )
        url = f'/api/alpinistas/{alpinista.pk}/historico-palestras/'

        for index, role in enumerate(roles):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'palestra-permitida-{index}', role))
                response = self.client.get(url)

                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response.json()[0]['titulo'], 'Palestra autorizada')

    def test_papeis_nao_autorizados_nao_consultam_historico_de_palestras(self):
        roles = (
            SiaRole.MME,
            SiaRole.SECRETARIA,
            SiaRole.ACAO_SOCIAL,
            SiaRole.LITURGIA,
            SiaRole.EVENTOS,
            SiaRole.COMUNICACAO,
        )
        alpinista = make_alpinista()
        url = f'/api/alpinistas/{alpinista.pk}/historico-palestras/'

        for index, role in enumerate(roles):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'palestra-negada-{index}', role))
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

    def test_historico_de_palestras_exige_autenticacao_e_papel(self):
        alpinista = make_alpinista()
        url = f'/api/alpinistas/{alpinista.pk}/historico-palestras/'

        self.assertEqual(
            self.client.get(url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.authenticate(self.make_user('palestra-sem-papel'))
        self.assertEqual(
            self.client.get(url).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_filtro_palestrou_e_derivado_do_historico(self):
        palestrante = make_alpinista()
        nao_palestrante = make_alpinista()
        Palestra.objects.create(
            alpinista=palestrante,
            encontro=make_encontro(),
            titulo='Palestra registrada',
        )
        self.authenticate(self.make_user('formacao-filtro', SiaRole.FORMACAO))

        response = self.client.get('/api/alpinistas/?palestrou=true')
        ids = [item['id'] for item in response.json()['results']]

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ids, [palestrante.pk])
        self.assertNotIn(nao_palestrante.pk, ids)
        self.assertFalse(hasattr(Alpinista, 'eh_palestrante'))
