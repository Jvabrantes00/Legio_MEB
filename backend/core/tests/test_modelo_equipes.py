from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from rest_framework.test import APIClient

from core.models import Encontro, EventoAuditoriaEncontro, VinculoEncontroLegado
from core.tests.factories import make_alpinista, make_encontro, make_funcao


class ModeloEquipesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('admin-modelo', 'admin@example.test', 'senha')
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.encontro = make_encontro()
        self.url = f'/api/encontros/{self.encontro.pk}/modelo-equipes/'

    def test_ativacao_e_auditoria(self):
        self.assertEqual(self.client.get(self.url).data['elegivel'], True)
        resposta = self.client.post(self.url, {'confirmacao': True, 'justificativa': 'Teste'}, format='json')
        self.assertEqual(resposta.status_code, 200)
        self.encontro.refresh_from_db()
        self.assertEqual(self.encontro.modelo_equipes, 'CANONICO')
        self.assertEqual(EventoAuditoriaEncontro.objects.count(), 1)
        self.assertEqual(self.client.post(self.url, {'confirmacao': True, 'justificativa': 'Teste'}, format='json').status_code, 409)

    def test_legado_impede_preparacao_e_vinculo_impede_ativacao(self):
        self.assertEqual(self.client.post(f'/api/encontros/{self.encontro.pk}/preparar-equipes/').status_code, 409)
        VinculoEncontroLegado.objects.create(alpinista=make_alpinista(), encontro=self.encontro, funcao=make_funcao())
        self.assertFalse(self.client.get(self.url).data['elegivel'])
        self.assertEqual(self.client.post(self.url, {'confirmacao': True, 'justificativa': 'Teste'}, format='json').status_code, 409)

    def test_confirmacao_e_justificativa_obrigatorias(self):
        for payload in ({}, {'confirmacao': False, 'justificativa': 'Teste'},
                        {'confirmacao': True, 'justificativa': '   '}):
            self.assertEqual(self.client.post(self.url, payload, format='json').status_code, 400)
        self.encontro.refresh_from_db()
        self.assertEqual(self.encontro.modelo_equipes, 'LEGADO')

    def test_canonico_preserva_encontrista_e_bloqueia_equipe(self):
        self.assertEqual(self.client.post(self.url, {'confirmacao': True, 'justificativa': 'Teste'}, format='json').status_code, 200)
        pessoa = make_alpinista()
        encontrista = make_funcao(tipo='encontrista')
        equipe = make_funcao(tipo='equipe')
        url = '/api/participacoes-encontros/'
        dados = {'alpinista_id': pessoa.pk, 'encontro_id': self.encontro.pk, 'funcao_id': encontrista.pk}
        criado = self.client.post(url, dados, format='json')
        self.assertEqual(criado.status_code, 201)
        vinculo_url = f"{url}{criado.data['id']}/"
        self.assertEqual(self.client.patch(vinculo_url, {'funcao_id': equipe.pk}, format='json').status_code, 409)
        self.assertEqual(self.client.patch(f'/api/funcoes/{encontrista.pk}/', {'tipo': 'equipe'}, format='json').status_code, 409)
        self.assertEqual(self.client.delete(vinculo_url).status_code, 204)

    def test_finalizado_e_cancelado_nao_podem_ser_ativados(self):
        for estado in (Encontro.Status.FINALIZADO, Encontro.Status.CANCELADO):
            Encontro.objects.filter(pk=self.encontro.pk).update(status=estado)
            self.assertEqual(self.client.post(self.url, {'confirmacao': True, 'justificativa': 'Teste'}, format='json').status_code, 409)


@skipUnless(connection.vendor == 'postgresql', 'exige PostgreSQL')
class ModeloEquipesConcorrenciaTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser('admin-modelo', 'admin@example.test', 'senha')
        self.encontro = make_encontro()
        self.url = f'/api/encontros/{self.encontro.pk}/modelo-equipes/'

    def concorrer(self, primeiro, segundo):
        barreira = Barrier(2)
        def executar(operacao):
            close_old_connections()
            try:
                client = APIClient()
                client.force_authenticate(user=get_user_model().objects.get(pk=self.user.pk))
                barreira.wait(timeout=10)
                return operacao(client).status_code
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros = [executor.submit(executar, op) for op in (primeiro, segundo)]
            return [f.result(timeout=30) for f in futuros]

    def ativar(self, client):
        return client.post(self.url, {'confirmacao': True, 'justificativa': 'Teste'}, format='json')

    def test_ativacao_contra_escrita_legada(self):
        pessoa, funcao = make_alpinista(), make_funcao()
        resultados = self.concorrer(self.ativar, lambda c: c.post('/api/participacoes-encontros/', {'alpinista_id': pessoa.pk, 'encontro_id': self.encontro.pk, 'funcao_id': funcao.pk}, format='json'))
        self.assertIn(resultados, ([200, 409], [409, 201]))

    def test_ativacao_contra_patch_tipo(self):
        funcao = make_funcao(tipo='encontrista')
        VinculoEncontroLegado.objects.create(alpinista=make_alpinista(), encontro=self.encontro, funcao=funcao)
        resultados = self.concorrer(self.ativar, lambda c: c.patch(f'/api/funcoes/{funcao.pk}/', {'tipo': 'equipe'}, format='json'))
        self.assertIn(resultados, ([200, 409], [409, 200]))

    def test_ativacao_contra_operacao_canonica(self):
        resultados = self.concorrer(self.ativar, lambda c: c.post(f'/api/encontros/{self.encontro.pk}/preparar-equipes/'))
        self.assertEqual(resultados[0], 200)
        self.assertIn(resultados[1], (200, 409))

    def test_duas_ativacoes(self):
        self.assertEqual(sorted(self.concorrer(self.ativar, self.ativar)), [200, 409])
        self.assertEqual(EventoAuditoriaEncontro.objects.count(), 1)
