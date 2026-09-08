from rest_framework import status

from core.models import LogSistema
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import (
    make_alpinista,
    make_encontro,
    make_evento,
    make_funcao,
)


class CrudAuditLogTests(AuthenticatedAPITestCase):
    def assert_crud_logs(self, module, object_id, sensitive_values=()):
        logs = LogSistema.objects.filter(modulo=module).order_by('id')

        self.assertEqual(
            list(logs.values_list('acao', flat=True)),
            ['CREATE', 'UPDATE', 'DELETE'],
        )
        for log in logs:
            self.assertIn(f'ID {object_id}', log.descricao)
            for value in sensitive_values:
                self.assertNotIn(value, log.descricao)

    def test_crud_funcao_encontro_gera_logs_com_id(self):
        created = self.client.post(
            '/api/funcoes/',
            {'nome': 'Função confidencial', 'tipo': 'equipe'},
            format='json',
        )
        object_id = created.json()['id']
        updated = self.client.patch(
            f'/api/funcoes/{object_id}/',
            {'ordem': 10},
            format='json',
        )
        deleted = self.client.delete(f'/api/funcoes/{object_id}/')

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assert_crud_logs(
            'FuncaoEncontro', object_id, ('Função confidencial',)
        )

    def test_crud_participacao_encontro_gera_logs_com_id(self):
        alpinista = make_alpinista(nome='Pessoa confidencial')
        encontro = make_encontro(encontro='Encontro confidencial')
        funcao = make_funcao(nome='Equipe confidencial')
        created = self.client.post(
            '/api/participacoes-encontros/',
            {
                'alpinista_id': alpinista.pk,
                'encontro_id': encontro.pk,
                'funcao_id': funcao.pk,
            },
            format='json',
        )
        object_id = created.json()['id']
        updated = self.client.patch(
            f'/api/participacoes-encontros/{object_id}/',
            {'cor_grupo': 'Azul'},
            format='json',
        )
        deleted = self.client.delete(
            f'/api/participacoes-encontros/{object_id}/'
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assert_crud_logs(
            'ParticipacaoEncontro',
            object_id,
            (alpinista.nome, encontro.encontro, funcao.nome),
        )

    def test_crud_participacao_evento_gera_logs_com_id(self):
        alpinista = make_alpinista(nome='Pessoa confidencial')
        evento = make_evento(nome='Evento confidencial')
        created = self.client.post(
            '/api/participacoes-eventos/',
            {'alpinista': alpinista.pk, 'evento': evento.pk},
            format='json',
        )
        object_id = created.json()['id']
        updated = self.client.patch(
            f'/api/participacoes-eventos/{object_id}/',
            {'evento': evento.pk},
            format='json',
        )
        deleted = self.client.delete(
            f'/api/participacoes-eventos/{object_id}/'
        )

        self.assertEqual(created.status_code, status.HTTP_201_CREATED)
        self.assertEqual(updated.status_code, status.HTTP_200_OK)
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)
        self.assert_crud_logs(
            'ParticipacaoEvento', object_id, (alpinista.nome, evento.nome)
        )

    def test_crud_alpinista_nao_registra_nome_nos_logs(self):
        created = self.client.post(
            '/api/alpinistas/',
            {
                'nome': 'Nome pessoal reservado',
                'email': 'auditado@example.test',
                'telefone': '61999999999',
            },
            format='json',
        )
        object_id = created.json()['id']
        self.client.patch(
            f'/api/alpinistas/{object_id}/',
            {'grupo': 'Grupo reservado'},
            format='json',
        )
        self.client.delete(f'/api/alpinistas/{object_id}/')

        self.assert_crud_logs(
            'Alpinista', object_id, ('Nome pessoal reservado',)
        )


class BatchActionAuditLogTests(AuthenticatedAPITestCase):
    def test_efetivacao_e_remocao_em_lote_geram_logs_sem_nomes(self):
        alpinista = make_alpinista(nome='Nome pessoal reservado')
        encontro = make_encontro(encontro='Encontro reservado')
        url_base = f'/api/encontros/{encontro.pk}'

        efetivacao = self.client.post(
            f'{url_base}/efetivar-encontristas/',
            {'alpinistas_ids': [alpinista.pk]},
            format='json',
        )
        remocao = self.client.post(
            f'{url_base}/remover-encontristas/',
            {'alpinistas_ids': [alpinista.pk]},
            format='json',
        )
        logs = LogSistema.objects.filter(
            modulo='ParticipacaoEncontro',
            descricao__contains='em lote',
        ).order_by('id')

        self.assertEqual(efetivacao.status_code, status.HTTP_200_OK)
        self.assertEqual(remocao.status_code, status.HTTP_200_OK)
        self.assertEqual(
            list(logs.values_list('acao', flat=True)),
            ['CREATE', 'DELETE'],
        )
        for log in logs:
            self.assertIn(f'Encontro ID {encontro.pk}', log.descricao)
            self.assertIn(str(alpinista.pk), log.descricao)
            self.assertNotIn(alpinista.nome, log.descricao)
            self.assertNotIn(encontro.encontro, log.descricao)
