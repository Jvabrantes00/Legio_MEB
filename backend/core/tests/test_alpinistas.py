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
    valid_cpf = '52998224725'
    formatted_valid_cpf = '529.982.247-25'

    def payload(self, index, **extra):
        return {
            'nome': f'Alpinista CPF {index}',
            'email': f'cpf-{index}@example.test',
            'telefone': f'610000{index:04d}',
            **extra,
        }

    def test_permite_dois_alpinistas_sem_cpf(self):
        first = AlpinistaSerializer(data=self.payload(1))
        second = AlpinistaSerializer(data=self.payload(2))

        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)
        first_alpinista = first.save()
        second_alpinista = second.save()

        self.assertIsNone(first_alpinista.cpf)
        self.assertIsNone(second_alpinista.cpf)

    def test_constraint_impede_dois_alpinistas_com_o_mesmo_cpf(self):
        Alpinista.objects.create(cpf=self.valid_cpf, **self.payload(1))

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Alpinista.objects.create(cpf=self.valid_cpf, **self.payload(2))

    def test_cpf_formatado_e_nao_formatado_sao_o_mesmo_valor(self):
        first = AlpinistaSerializer(data=self.payload(1, cpf=self.valid_cpf))
        self.assertTrue(first.is_valid(), first.errors)
        first.save()

        second = AlpinistaSerializer(
            data=self.payload(2, cpf=self.formatted_valid_cpf)
        )

        self.assertFalse(second.is_valid())
        self.assertIn('cpf', second.errors)

    def test_rejeita_cpf_invalido(self):
        serializer = AlpinistaSerializer(
            data=self.payload(1, cpf='111.111.111-11')
        )

        self.assertFalse(serializer.is_valid())
        self.assertIn('cpf', serializer.errors)

    def test_persiste_cpf_sem_pontuacao(self):
        serializer = AlpinistaSerializer(
            data=self.payload(1, cpf=self.formatted_valid_cpf)
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)
        alpinista = serializer.save()
        alpinista.refresh_from_db()

        self.assertEqual(alpinista.cpf, self.valid_cpf)
