import inspect
import os
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from core.management.commands.seed_demo import (
    DEMO_ACCOUNTS,
    DEMO_ENCOUNTERS,
    DEMO_GROUP_NAMES,
    DEMO_PERSON_NAMES,
    _delete_demo_dataset,
)
from core.models import (
    Alpinista,
    ConviteEncontro,
    Encontro,
    Grupo,
    ItemPropostaVioleiros,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
    PropostaVioleiros,
    ReuniaoPreparatoriaEncontro,
    TemplateEquipeEncontro,
    TrabalhoEncontro,
)
from core.permissions import pode_registrar_presenca_preparatoria
from core.roles import SiaRole
from core.serializers import AlpinistaCompletoSerializer


DEMO_ENV = {'SIA_ENVIRONMENT': 'development'}
DEMO_PASSWORD = 'test-only-demo-password'


@override_settings(DEBUG=True)
class SeedDemoCommandTests(TestCase):
    def run_seed(self):
        output = StringIO()
        with patch.dict(os.environ, DEMO_ENV, clear=False):
            call_command('seed_demo', password=DEMO_PASSWORD, stdout=output)
        return output.getvalue()

    def run_reset(self):
        output = StringIO()
        with patch.dict(os.environ, DEMO_ENV, clear=False):
            call_command('seed_demo', reset=True, stdout=output)
        return output.getvalue()

    def test_command_is_fail_closed_outside_development(self):
        with override_settings(DEBUG=False), patch.dict(
            os.environ,
            DEMO_ENV,
            clear=False,
        ):
            with self.assertRaisesMessage(CommandError, 'bloqueado'):
                call_command('seed_demo', password=DEMO_PASSWORD)

        with patch.dict(
            os.environ,
            {'SIA_ENVIRONMENT': 'production'},
            clear=False,
        ):
            with self.assertRaisesMessage(CommandError, 'bloqueado'):
                call_command('seed_demo', password=DEMO_PASSWORD)

    def test_password_is_required(self):
        environment = {**os.environ, **DEMO_ENV}
        environment.pop('SIA_DEMO_PASSWORD', None)
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesMessage(CommandError, 'SIA_DEMO_PASSWORD'):
                call_command('seed_demo')

    def test_seed_creates_accounts_roles_dataset_and_summary(self):
        output = self.run_seed()

        usernames = [username for username, _ in DEMO_ACCOUNTS]
        self.assertEqual(
            set(User.objects.filter(username__in=usernames).values_list(
                'username',
                flat=True,
            )),
            set(usernames),
        )
        for username, role in DEMO_ACCOUNTS:
            user = User.objects.get(username=username)
            if role is not None:
                self.assertEqual(
                    list(user.groups.values_list('name', flat=True)),
                    [role.value],
                )

        no_role = User.objects.get(username='demo.sem_papel')
        self.assertFalse(no_role.groups.exists())
        self.assertFalse(no_role.is_superuser)
        no_role_person = no_role.vinculo_pessoa.pessoa
        vale = Encontro.objects.get(
            encontro='[DEMO] Escalada Vale Verde 2027'
        )
        self.assertFalse(
            TrabalhoEncontro.objects.filter(
                pessoa=no_role_person,
            ).exists()
        )
        self.assertFalse(
            pode_registrar_presenca_preparatoria(no_role, vale)
        )
        superuser = User.objects.get(username='demo.superuser')
        self.assertTrue(superuser.is_superuser)
        self.assertFalse(superuser.groups.exists())

        demo_people = Pessoa.objects.filter(nome__in=DEMO_PERSON_NAMES)
        self.assertEqual(demo_people.count(), 40)
        self.assertEqual(
            PerfilAlpinista.objects.filter(pessoa__in=demo_people).count(),
            32,
        )
        self.assertFalse(demo_people.exclude(cpf__isnull=True).exists())
        self.assertFalse(
            demo_people.exclude(email__endswith='@example.invalid').exists()
        )
        self.assertEqual(Grupo.objects.filter(nome__in=DEMO_GROUP_NAMES).count(), 4)

        encounters = Encontro.objects.filter(
            encontro__in=[title for title, _ in DEMO_ENCOUNTERS]
        )
        self.assertEqual(encounters.count(), 4)
        self.assertEqual(encounters.filter(tipo=Encontro.Tipo.ESCALADA).count(), 2)
        self.assertEqual(encounters.filter(tipo=Encontro.Tipo.ESPPA).count(), 2)
        expected_statuses = {
            '[DEMO] Escalada Serra Azul 2027': Encontro.Status.EM_AGENDAMENTO,
            '[DEMO] Escalada Vale Verde 2027': Encontro.Status.EM_PREPARACAO,
            '[DEMO] ESPPA Horizonte 2027': Encontro.Status.AGENDADO,
            '[DEMO] ESPPA Caminho 2026': Encontro.Status.FINALIZADO,
        }
        self.assertEqual(
            dict(encounters.values_list('encontro', 'status')),
            expected_statuses,
        )

        confirmed_without_participation = ConviteEncontro.objects.filter(
            encontro__encontro='[DEMO] ESPPA Horizonte 2027',
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        ).first()
        self.assertIsNotNone(confirmed_without_participation)
        self.assertFalse(
            ParticipacaoEncontro.objects.filter(
                convite=confirmed_without_participation
            ).exists()
        )
        self.assertTrue(
            TrabalhoEncontro.objects.filter(
                encontro__encontro='[DEMO] ESPPA Caminho 2026',
                status=TrabalhoEncontro.Status.TRABALHOU,
            ).exists()
        )
        missed_work = TrabalhoEncontro.objects.get(
            encontro__encontro='[DEMO] ESPPA Caminho 2026',
            status=TrabalhoEncontro.Status.FALTOU,
        )
        legacy_alpinist = Alpinista.objects.get(pessoa=missed_work.pessoa)
        self.assertEqual(
            AlpinistaCompletoSerializer().get_historico_equipes(
                legacy_alpinist
            ),
            [],
        )
        self.assertEqual(
            ReuniaoPreparatoriaEncontro.objects.filter(
                encontro__encontro='[DEMO] Escalada Vale Verde 2027'
            ).count(),
            3,
        )
        proposal = PropostaVioleiros.objects.get(
            encontro__encontro='[DEMO] Escalada Vale Verde 2027'
        )
        self.assertEqual(
            ItemPropostaVioleiros.objects.filter(
                proposta=proposal,
                vigente=True,
            ).count(),
            5,
        )
        self.assertIn('Dataset demo criado com sucesso.', output)
        self.assertIn('Pessoas: 40', output)
        self.assertIn('Contas demo: 12', output)
        self.assertNotIn(DEMO_PASSWORD, output)

    def test_second_execution_replaces_dataset_without_duplication(self):
        self.run_seed()
        first_counts = (
            Pessoa.objects.filter(nome__in=DEMO_PERSON_NAMES).count(),
            Encontro.objects.filter(
                encontro__in=[title for title, _ in DEMO_ENCOUNTERS]
            ).count(),
            User.objects.filter(
                username__in=[username for username, _ in DEMO_ACCOUNTS]
            ).count(),
        )

        self.run_seed()

        self.assertEqual(
            (
                Pessoa.objects.filter(nome__in=DEMO_PERSON_NAMES).count(),
                Encontro.objects.filter(
                    encontro__in=[title for title, _ in DEMO_ENCOUNTERS]
                ).count(),
                User.objects.filter(
                    username__in=[username for username, _ in DEMO_ACCOUNTS]
                ).count(),
            ),
            first_counts,
        )

    def test_reset_removes_only_allowlisted_demo_roots(self):
        real_person = Pessoa.objects.create(
            nome='Registro real preservado',
            email='real@example.org',
        )
        real_encounter = Encontro.objects.create(
            encontro='Encontro real preservado',
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia='2028-01-01',
            data_exato='1 de janeiro de 2028',
        )
        real_template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='violeiros',
            nome='Violeiros real preservado',
        )
        self.run_seed()

        output = self.run_reset()

        self.assertFalse(Pessoa.objects.filter(nome__in=DEMO_PERSON_NAMES).exists())
        self.assertFalse(
            Encontro.objects.filter(
                encontro__in=[title for title, _ in DEMO_ENCOUNTERS]
            ).exists()
        )
        self.assertFalse(
            User.objects.filter(
                username__in=[username for username, _ in DEMO_ACCOUNTS]
            ).exists()
        )
        self.assertTrue(Pessoa.objects.filter(pk=real_person.pk).exists())
        self.assertTrue(Encontro.objects.filter(pk=real_encounter.pk).exists())
        self.assertTrue(
            TemplateEquipeEncontro.objects.filter(pk=real_template.pk).exists()
        )
        self.assertIn('Dataset demo removido.', output)

    def test_reset_implementation_does_not_use_global_delete(self):
        source = inspect.getsource(_delete_demo_dataset)
        self.assertNotIn('.objects.all().delete()', source)

    def test_environment_password_can_be_used_without_cli_value(self):
        output = StringIO()
        with patch.dict(
            os.environ,
            {**DEMO_ENV, 'SIA_DEMO_PASSWORD': DEMO_PASSWORD},
            clear=False,
        ):
            call_command('seed_demo', stdout=output)

        self.assertTrue(User.objects.get(username='demo.suporte').check_password(
            DEMO_PASSWORD
        ))
        self.assertEqual(
            User.objects.get(username='demo.suporte').groups.get().name,
            SiaRole.SUPORTE.value,
        )
