from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Alpinista, ParticipacaoEncontro
from core.serializers import AlpinistaSerializer
from core.tests.factories import make_alpinista, make_encontro, make_funcao


class HistoricoAlpinistaRegressionTests(TestCase):
    def test_historico_de_encontro_recupera_cor_grupo(self):
        # Arrange
        alpinista = make_alpinista()
        encontro = make_encontro()
        funcao = make_funcao(nome='Encontrista', tipo='encontrista')
        ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            funcao=funcao,
            cor_grupo='azul',
        )

        # Act
        payload = AlpinistaSerializer(alpinista).data

        # Assert: hoje o serializer procura o nome antigo corGrupo.
        self.assertEqual(payload['encontros_realizados'][0]['cor_grupo'], 'azul')


class StatusAlpinistaRegressionTests(TestCase):
    def test_status_padrao_deve_usar_valor_canonico_pendente(self):
        # Arrange / Act
        alpinista = Alpinista.objects.create(
            cpf='000.000.099-00',
            nome='Status padrão',
            email='status-padrao@example.test',
            telefone='6199999999',
        )

        # Assert: documenta a diferença atual entre Pendente e pendente.
        self.assertEqual(alpinista.status, 'pendente')

    def test_nova_participacao_deve_usar_valor_canonico_ativo(self):
        # Arrange
        alpinista = make_alpinista(status='pendente')
        encontro = make_encontro()
        funcao = make_funcao(nome='Equipe', tipo='equipe')

        # Act
        ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            funcao=funcao,
        )
        alpinista.refresh_from_db()

        # Assert: hoje o signal grava Ativo em vez de ativo.
        self.assertEqual(alpinista.status, 'ativo')


class CPFRegressionTests(TestCase):
    def test_cadastros_sem_cpf_colidem_no_default_unico(self):
        # Arrange
        Alpinista.objects.create(
            nome='Sem CPF 1',
            email='sem-cpf-1@example.test',
            telefone='6100000001',
        )

        # Act / Assert: o segundo cadastro recebe o mesmo default "False".
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Alpinista.objects.create(
                    nome='Sem CPF 2',
                    email='sem-cpf-2@example.test',
                    telefone='6100000002',
                )
