from django.db import connection
from django.test.utils import CaptureQueriesContext

from core.models import ConviteEncontro, Encontro, LogSistema, Pessoa, TemplateEquipeEncontro, TemplateRoleEquipe, TrabalhoEncontro
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_encontro_canonico


class RespostasTrabalhoTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.encontro = make_encontro_canonico()

    def convite(self, finalidade='trabalhar', status='convidado', encontro=None):
        return ConviteEncontro.objects.create(pessoa=Pessoa.objects.create(nome='Pessoa'), encontro=encontro or self.encontro, finalidade=finalidade, status=status)

    def test_resposta_restringe_finalidade_e_preserva_auditoria(self):
        convite = self.convite('participar')
        logs = LogSistema.objects.count()
        for pk in (convite.pk, 99999999):
            response = self.client.post(f'/api/convites-encontros/{pk}/responder-trabalho/', {'status': 'confirmado'}, format='json')
            self.assertEqual(response.status_code, 404)
        convite.refresh_from_db()
        self.assertEqual(convite.status, 'convidado')
        self.assertEqual(LogSistema.objects.count(), logs)
        trabalho = self.convite()
        response = self.client.post(f'/api/convites-encontros/{trabalho.pk}/responder-trabalho/', {'status': 'confirmado'}, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(TrabalhoEncontro.objects.filter(convite=trabalho).exists())

    def test_listagem_filtra_isola_e_evitar_n_mais_um(self):
        convites = [self.convite(status=status) for status in ConviteEncontro.Status.values]
        self.convite('participar')
        self.convite(encontro=make_encontro_canonico())
        trabalho = TrabalhoEncontro.objects.create(pessoa=convites[1].pessoa, encontro=self.encontro, convite=convites[1])
        url = '/api/convites-encontros/'
        with CaptureQueriesContext(connection) as queries:
            response = self.client.get(url, {'encontro': self.encontro.pk})
        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(queries), 3)
        rows = {item['id']: item for item in response.json()['results']}
        self.assertEqual(set(rows), {item.pk for item in convites})
        self.assertEqual(rows[convites[0].pk]['trabalho_id'], None)
        self.assertEqual(rows[convites[0].pk]['trabalho_status'], None)
        self.assertEqual(rows[convites[1].pk]['trabalho_id'], trabalho.pk)
        self.assertEqual(rows[convites[1].pk]['trabalho_status'], trabalho.status)
        self.assertEqual(set(rows[convites[0].pk]), {'id', 'pessoa_id', 'pessoa_nome', 'encontro_id', 'finalidade', 'status', 'role_trabalho_proposta_id', 'trabalho_id', 'trabalho_status', 'criado_em'})
        for convite in convites:
            result = self.client.get(url, {'encontro': self.encontro.pk, 'status': convite.status}).json()
            self.assertEqual([item['id'] for item in result['results']], [convite.pk])
        self.assertEqual(self.client.get(url, {'encontro': self.encontro.pk, 'status': 'invalido'}).status_code, 400)

    def test_respostas_definitivas_e_nao_autenticado(self):
        for status in ('confirmado', 'recusado', 'sem_resposta'):
            convite = self.convite()
            url = f'/api/convites-encontros/{convite.pk}/responder-trabalho/'
            self.assertEqual(self.client.post(url, {'status': status}, format='json').status_code, 200)
            self.assertEqual(self.client.post(url, {'status': status}, format='json').status_code, 200)
            self.assertEqual(self.client.post(url, {'status': 'convidado'}, format='json').status_code, 400)
            convite.refresh_from_db()
            self.assertEqual(convite.status, status)
        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.post(url, {'status': 'confirmado'}, format='json').status_code, 401)

    def test_funcao_lotada_preserva_convite_confirmado(self):
        template = TemplateEquipeEncontro.objects.create(tipo_encontro=self.encontro.tipo, codigo='apoio', nome='Apoio')
        TemplateRoleEquipe.objects.create(template_equipe=template, codigo='membro', nome='Membro', quantidade_estrutural=1)
        self.assertEqual(self.client.post(f'/api/encontros/{self.encontro.pk}/preparar-equipes/', {}, format='json').status_code, 200)
        role = self.encontro.equipes.get().roles.get()
        ocupante = self.convite(status='confirmado')
        TrabalhoEncontro.objects.create(pessoa=ocupante.pessoa, encontro=self.encontro, convite=ocupante, role_equipe=role, status='alocado')
        convite = self.convite(status='confirmado')
        convite.role_trabalho_proposta = role
        convite.save(update_fields=['role_trabalho_proposta'])
        response = self.client.post('/api/trabalhos-encontros/', {'convite_id': convite.pk, 'confirmar_avisos': True}, format='json')
        self.assertEqual(response.status_code, 400)
        convite.refresh_from_db()
        self.assertEqual((convite.status, convite.role_trabalho_proposta_id), ('confirmado', role.pk))
        self.assertFalse(TrabalhoEncontro.objects.filter(convite=convite).exists())
