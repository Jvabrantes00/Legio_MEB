from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from core.models import (ConviteEncontro, Encontro, LogSistema, ParticipacaoEncontro,
                         PerfilAlpinista, Pessoa, TemplateEquipeEncontro, TemplateRoleEquipe)
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_alpinista, make_encontro_canonico


class GE2AApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.encontro = make_encontro_canonico(tipo=Encontro.Tipo.ESCALADA)
        template = TemplateEquipeEncontro.objects.create(tipo_encontro=Encontro.Tipo.ESCALADA, codigo='apoio', nome='Apoio')
        TemplateRoleEquipe.objects.create(template_equipe=template, codigo='membro', nome='Membro')
        response = self.client.post(f'/api/encontros/{self.encontro.pk}/preparar-equipes/', {}, format='json')
        self.assertEqual(response.status_code, 200)
        self.role = self.encontro.equipes.get().roles.get()

    def test_aviso_bloqueio_idempotencia_e_auditoria(self):
        pessoa = Pessoa.objects.create(nome='Pessoa aviso')
        payload = {'pessoa_id': pessoa.pk, 'encontro_id': self.encontro.pk, 'finalidade': 'trabalhar', 'role_trabalho_proposta_id': self.role.pk}
        antes = ConviteEncontro.objects.count()
        logs_antes = LogSistema.objects.filter(modulo='ConviteEncontro').count()
        resposta = self.client.post('/api/convites-encontros/', payload, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json()['avaliacao']['resultado'], 'AVISO')
        self.assertEqual(ConviteEncontro.objects.count(), antes)
        self.assertEqual(LogSistema.objects.filter(modulo='ConviteEncontro').count(), logs_antes)
        criado = self.client.post('/api/convites-encontros/', {**payload, 'confirmar_avisos': True}, format='json')
        self.assertEqual(criado.status_code, 201)
        self.assertEqual(criado.json()['role_trabalho_proposta_id'], self.role.pk)
        convite = ConviteEncontro.objects.get(pk=criado.json()['id'])
        estado = (convite.pk, convite.status, convite.role_trabalho_proposta_id, convite.criado_em)
        logs = LogSistema.objects.filter(modulo='ConviteEncontro').count()
        self.assertEqual(logs, 1)
        repetido = self.client.post('/api/convites-encontros/', {**payload, 'confirmar_avisos': True}, format='json')
        self.assertEqual(repetido.status_code, 400, repetido.data)
        self.assertIn('non_field_errors', repetido.json())
        convite.refresh_from_db()
        self.assertEqual((convite.pk, convite.status, convite.role_trabalho_proposta_id, convite.criado_em), estado)
        self.assertEqual(ConviteEncontro.objects.filter(pessoa=pessoa, encontro=self.encontro, finalidade='trabalhar').count(), 1)
        self.assertEqual(ConviteEncontro.objects.count(), antes + 1)
        self.assertEqual(LogSistema.objects.filter(modulo='ConviteEncontro').count(), logs)
        bloqueada = Pessoa.objects.create(nome='Pessoa bloqueada')
        PerfilAlpinista.objects.create(pessoa=bloqueada)
        make_alpinista(pessoa=bloqueada, status='ativo')
        anterior = make_encontro_canonico(tipo=Encontro.Tipo.ESCALADA)
        ParticipacaoEncontro.objects.create(pessoa=bloqueada, encontro=anterior, resultado=ParticipacaoEncontro.Resultado.CONCLUIU, tipo_encontro=Encontro.Tipo.ESCALADA)
        resposta = self.client.post('/api/convites-encontros/', {**payload, 'pessoa_id': bloqueada.pk, 'confirmar_avisos': True}, format='json')
        self.assertEqual(resposta.status_code, 400)
        self.assertEqual(resposta.json()['avaliacao']['resultado'], 'BLOQUEIO')
        self.assertEqual(ConviteEncontro.objects.count(), antes + 1)
        self.assertEqual(LogSistema.objects.filter(modulo='ConviteEncontro').count(), logs)

    def test_lista_e_seletor_privados_e_filtrados(self):
        pessoa = Pessoa.objects.create(nome='Nome Selecionado')
        make_alpinista(pessoa=pessoa, nome='Nome Selecionado')
        make_alpinista(nome='Sem Pessoa', pessoa=None)
        convite = ConviteEncontro.objects.create(pessoa=pessoa, encontro=self.encontro, finalidade='trabalhar')
        ConviteEncontro.objects.create(pessoa=Pessoa.objects.create(nome='Participar'), encontro=self.encontro, finalidade='participar')
        ConviteEncontro.objects.create(pessoa=pessoa, encontro=make_encontro_canonico(), finalidade='trabalhar')
        url = '/api/convites-encontros/'
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.get(url, {'encontro': ''}).status_code, 405)
        self.assertEqual(self.client.get(url, {'encontro': 'abc'}).status_code, 400)
        self.assertEqual(self.client.get(url, {'encontro': self.encontro.pk, 'finalidade': 'participar'}).status_code, 400)
        dados = self.client.get(url, {'encontro': self.encontro.pk, 'finalidade': 'trabalhar'}).json()
        self.assertEqual([r['id'] for r in dados['results']], [convite.pk])
        self.assertEqual(set(dados['results'][0]), {'id', 'pessoa_id', 'pessoa_nome', 'encontro_id', 'finalidade', 'status', 'role_trabalho_proposta_id', 'trabalho_id', 'trabalho_status', 'criado_em'})
        seletor = self.client.get('/api/alpinistas/seletor-trabalho/', {'search': 'Nome Selecionado', 'page': 1, 'ordering': 'nome'}).json()
        self.assertEqual(seletor['count'], 1)
        self.assertEqual(set(seletor['results'][0]), {'id', 'pessoa_id', 'nome', 'grupo'})
        self.assertEqual(seletor['results'][0]['pessoa_id'], pessoa.pk)
        self.assertEqual(set(seletor), {'count', 'next', 'previous', 'results'})
        for index in range(30):
            linked = Pessoa.objects.create(nome=f'Pagina {index:02d}')
            make_alpinista(pessoa=linked, nome=linked.nome)
        primeira = self.client.get('/api/alpinistas/seletor-trabalho/', {'search': 'Pagina', 'page': 1, 'ordering': 'nome'}).json()
        self.assertEqual(primeira['count'], 30)
        self.assertIsNotNone(primeira['next'])
        self.assertIsNone(primeira['previous'])
        segunda = self.client.get('/api/alpinistas/seletor-trabalho/', {'search': 'Pagina', 'page': 2, 'ordering': 'nome'}).json()
        self.assertIsNotNone(segunda['previous'])
        self.assertFalse({item['id'] for item in primeira['results']} & {item['id'] for item in segunda['results']})

    def test_matriz_perfis(self):
        user_model = get_user_model()
        for role, ativo, esperado in [('Suporte', True, 200), ('Diretoria', True, 200), ('Fichas', True, 200), ('Suporte', False, 403), ('MME', True, 403), (None, True, 403)]:
            user = user_model.objects.create_user(username=f'{role}-{ativo}', is_active=ativo)
            if role: user.groups.add(Group.objects.get_or_create(name=role)[0])
            self.client.force_authenticate(user=user)
            for path, params in [('/api/convites-encontros/', {'encontro': self.encontro.pk}), ('/api/alpinistas/seletor-trabalho/', {})]:
                with self.subTest(role=role, ativo=ativo, path=path):
                    self.assertEqual(self.client.get(path, params).status_code, esperado)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get('/api/alpinistas/seletor-trabalho/').status_code, 401)
        self.assertEqual(self.client.get('/api/convites-encontros/', {'encontro': self.encontro.pk}).status_code, 401)
