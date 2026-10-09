from datetime import datetime, timedelta
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from core.models import (
    ConfiguracaoEncontristasEncontro,
    Inscricao,
    VinculoEncontroLegado,
)
from core.tests.factories import make_encontro


class ConfiguracaoEncontristasEncontroTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro()
        self.abertura = timezone.make_aware(datetime(2030, 1, 1, 8, 0))
        self.encerramento = self.abertura + timedelta(days=30)

    def criar_configuracao(self, **overrides):
        valores = {
            'encontro': self.encontro,
            'capacidade': 80,
            'idade_minima': 15,
            'idade_maxima': 17,
            'inscricoes_abrem_em': self.abertura,
            'inscricoes_encerram_em': self.encerramento,
        }
        valores.update(overrides)
        return ConfiguracaoEncontristasEncontro.objects.create(**valores)

    def test_configuracao_persiste_para_um_encontro(self):
        configuracao = self.criar_configuracao()

        self.assertEqual(configuracao.encontro, self.encontro)
        self.assertEqual(configuracao.capacidade, 80)
        self.assertEqual(configuracao.idade_minima, 15)
        self.assertEqual(configuracao.idade_maxima, 17)
        self.assertEqual(configuracao.inscricoes_abrem_em, self.abertura)
        self.assertEqual(
            configuracao.inscricoes_encerram_em,
            self.encerramento,
        )

    def test_public_id_e_uuid_automatico_distinto_unico_e_nao_editavel(self):
        primeira = self.criar_configuracao()
        segunda = self.criar_configuracao(
            encontro=make_encontro(),
        )
        campo = ConfiguracaoEncontristasEncontro._meta.get_field('public_id')

        self.assertIsInstance(primeira.public_id, UUID)
        self.assertIsInstance(segunda.public_id, UUID)
        self.assertNotEqual(primeira.public_id, segunda.public_id)
        self.assertTrue(campo.unique)
        self.assertFalse(campo.editable)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_configuracao(
                encontro=make_encontro(),
                public_id=primeira.public_id,
            )

    def test_permite_uma_configuracao_por_encontro(self):
        self.criar_configuracao()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_configuracao()

    def test_capacidade_deve_ser_positiva(self):
        for capacidade in (0, -1):
            with self.subTest(capacidade=capacidade):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.criar_configuracao(capacidade=capacidade)

    def test_idades_devem_ser_nao_negativas_e_coerentes(self):
        casos_invalidos = (
            {'idade_minima': -1},
            {'idade_maxima': -1},
            {'idade_minima': 18, 'idade_maxima': 17},
        )

        for idades in casos_invalidos:
            with self.subTest(idades=idades):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.criar_configuracao(**idades)

    def test_permite_idades_iguais(self):
        configuracao = self.criar_configuracao(
            idade_minima=16,
            idade_maxima=16,
        )

        self.assertEqual(configuracao.idade_minima, configuracao.idade_maxima)

    def test_abertura_deve_anteceder_encerramento(self):
        for encerramento in (self.abertura, self.abertura - timedelta(days=1)):
            with self.subTest(encerramento=encerramento):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.criar_configuracao(
                        inscricoes_encerram_em=encerramento,
                    )

    def test_encontro_referenciado_e_protegido(self):
        self.criar_configuracao()

        with self.assertRaises(ProtectedError):
            self.encontro.delete()

    def test_criacao_nao_altera_encontro_nem_estrutura_legada(self):
        encontro_antes = {
            'encontro': self.encontro.encontro,
            'tipo': self.encontro.tipo,
            'data_referencia': self.encontro.data_referencia,
            'data_exato': self.encontro.data_exato,
            'local': self.encontro.local,
            'status': self.encontro.status,
        }

        self.criar_configuracao()
        self.encontro.refresh_from_db()

        encontro_depois = {
            campo: getattr(self.encontro, campo)
            for campo in encontro_antes
        }
        self.assertEqual(encontro_depois, encontro_antes)
        self.assertFalse(VinculoEncontroLegado.objects.exists())
        self.assertFalse(Inscricao.objects.exists())
