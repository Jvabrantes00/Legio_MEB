from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import Pessoa, TelefonePessoa, VinculoConjugal


class PessoaDomainConstraintTests(TestCase):
    def test_telefone_e_unico_somente_dentro_da_mesma_pessoa(self):
        pessoa_a = Pessoa.objects.create(nome='Pessoa A')
        pessoa_b = Pessoa.objects.create(nome='Pessoa B')
        TelefonePessoa.objects.create(
            pessoa=pessoa_a,
            numero='61999990000',
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            TelefonePessoa.objects.create(
                pessoa=pessoa_a,
                numero='61999990000',
            )

        TelefonePessoa.objects.create(
            pessoa=pessoa_b,
            numero='61999990000',
        )

    def test_vinculo_conjugal_exige_ordem_canonica_e_unicidade(self):
        pessoa_a = Pessoa.objects.create(nome='Pessoa A')
        pessoa_b = Pessoa.objects.create(nome='Pessoa B')
        VinculoConjugal.objects.create(
            pessoa_a=pessoa_a,
            pessoa_b=pessoa_b,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoConjugal.objects.create(
                pessoa_a=pessoa_a,
                pessoa_b=pessoa_b,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoConjugal.objects.create(
                pessoa_a=pessoa_b,
                pessoa_b=pessoa_a,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoConjugal.objects.create(
                pessoa_a=pessoa_a,
                pessoa_b=pessoa_a,
            )
