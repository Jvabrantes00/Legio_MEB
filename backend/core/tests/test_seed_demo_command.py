import inspect
import os
from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from core.management.commands.seed_demo import (
    DEMO_ACCOUNTS,
    DEMO_ENCOUNTERS,
    DEMO_GROUP_NAMES,
    DEMO_PERSON_NAMES,
    DEMO_REGISTRATION_CLOSE_DAYS_BEFORE,
    DEMO_REGISTRATION_OPEN_DAYS_BEFORE,
    DEMO_REGISTRATION_SPECS,
    _configure_encounter_registrations,
    _delete_demo_dataset,
)
from core.models import (
    Alpinista,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Grupo,
    ItemPropostaVioleiros,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
    PropostaVioleiros,
    ReuniaoPreparatoriaEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.permissions import pode_registrar_presenca_preparatoria
from core.roles import SiaRole
from core.serializers import AlpinistaCompletoSerializer
from core.services.encontro_workspace import projetar_capabilities


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
        configurations = ConfiguracaoEncontristasEncontro.objects.filter(
            encontro__in=encounters,
        ).select_related('encontro')
        self.assertEqual(configurations.count(), len(DEMO_ENCOUNTERS))
        for configuration in configurations:
            spec = DEMO_REGISTRATION_SPECS[configuration.encontro.tipo]
            self.assertEqual(configuration.capacidade, spec['capacidade'])
            self.assertEqual(
                configuration.idade_minima,
                spec['idade_minima'],
            )
            self.assertEqual(
                configuration.idade_maxima,
                spec['idade_maxima'],
            )
            self.assertIsNotNone(configuration.public_id)
            configuration.full_clean()
            first_day = (
                configuration.encontro.calendarios
                .get(vigente=True)
                .dias
                .order_by('ordem', 'data')
                .values_list('data', flat=True)
                .first()
            )
            opening_local = timezone.localtime(
                configuration.inscricoes_abrem_em,
            )
            closing_local = timezone.localtime(
                configuration.inscricoes_encerram_em,
            )
            self.assertEqual(
                opening_local.date(),
                first_day - timedelta(
                    days=DEMO_REGISTRATION_OPEN_DAYS_BEFORE,
                ),
            )
            self.assertEqual(opening_local.hour, 8)
            self.assertEqual(
                closing_local.date(),
                first_day - timedelta(
                    days=DEMO_REGISTRATION_CLOSE_DAYS_BEFORE,
                ),
            )
            self.assertEqual(closing_local.hour, 23)
            self.assertEqual(closing_local.minute, 59)
            self.assertLess(
                configuration.inscricoes_abrem_em,
                configuration.inscricoes_encerram_em,
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

    def test_contextual_coordination_and_team_snapshots(self):
        self.run_seed()
        encounters = list(Encontro.objects.filter(
            encontro__in=[title for title, _ in DEMO_ENCOUNTERS],
        ))
        communication = User.objects.get(username='demo.comunicacao')
        no_role = User.objects.get(username='demo.sem_papel')
        secretary = User.objects.get(username='demo.secretaria')
        vale = next(e for e in encounters if 'Vale Verde' in e.encontro)
        for encounter in encounters:
            with self.subTest(encounter=encounter.encontro):
                self.assertEqual(
                    projetar_capabilities(usuario=communication, encontro=encounter)['acessar_equipes'],
                    encounter.pk == vale.pk,
                )
                self.assertFalse(projetar_capabilities(
                    usuario=no_role, encontro=encounter,
                )['acessar_equipes'])
                self.assertEqual(EquipeEncontro.objects.filter(
                    encontro=encounter, codigo='coordenacao-geral',
                ).count(), 1)
        self.assertEqual(len(encounters), 4)
        self.assertTrue(projetar_capabilities(
            usuario=secretary, encontro=vale,
        )['acessar_equipes'])
        work = TrabalhoEncontro.objects.get(pessoa=communication.vinculo_pessoa.pessoa)
        self.assertEqual(work.encontro, vale)
        self.assertEqual(work.status, TrabalhoEncontro.Status.ALOCADO)
        self.assertEqual(work.role_equipe.codigo, 'demo-apoio-coordenacao')
        self.assertEqual(work.role_equipe.quantidade_estrutural, 4)
        self.assertFalse(TrabalhoEncontro.objects.filter(
            pessoa=no_role.vinculo_pessoa.pessoa,
        ).exists())

    def _assert_real_conflict(self, encounter_type):
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=encounter_type, codigo='coordenacao-geral',
            nome='Coordenação real', ordem=7,
        )
        TemplateRoleEquipe.objects.create(
            template_equipe=template, codigo='papel-real', nome='Papel real',
            quantidade_estrutural=3,
        )
        before = TemplateEquipeEncontro.objects.filter(pk=template.pk).values().get()
        roles_before = list(template.roles.values())
        with self.assertRaisesMessage(CommandError, str(encounter_type)):
            self.run_seed()
        self.assertEqual(TemplateEquipeEncontro.objects.filter(pk=template.pk).values().get(), before)
        self.assertEqual(list(template.roles.values()), roles_before)
        self.assertFalse(Pessoa.objects.filter(nome__in=DEMO_PERSON_NAMES).exists())
        self.assertFalse(Encontro.objects.filter(
            encontro__in=[title for title, _ in DEMO_ENCOUNTERS],
        ).exists())
        self.assertFalse(User.objects.filter(
            username__in=[username for username, _ in DEMO_ACCOUNTS],
        ).exists())
        self.assertFalse(TemplateEquipeEncontro.objects.filter(nome__startswith='[DEMO]').exists())

    def test_real_escalada_template_conflict_fails_closed(self):
        self._assert_real_conflict(Encontro.Tipo.ESCALADA)

    def test_real_esppa_template_conflict_fails_closed(self):
        self._assert_real_conflict(Encontro.Tipo.ESPPA)

    def test_conflict_rolls_back_existing_demo_deletion(self):
        self.run_seed()
        template = TemplateEquipeEncontro.objects.get(
            tipo_encontro=Encontro.Tipo.ESPPA, codigo='coordenacao-geral',
        )
        template.nome = 'Coordenação real'
        template.save(update_fields=['nome'])
        before_people = list(Pessoa.objects.filter(nome__in=DEMO_PERSON_NAMES).order_by('pk').values())
        before_encounters = list(Encontro.objects.filter(
            encontro__in=[title for title, _ in DEMO_ENCOUNTERS],
        ).order_by('pk').values())
        before_users = list(User.objects.filter(
            username__in=[username for username, _ in DEMO_ACCOUNTS],
        ).order_by('pk').values())
        before_templates = list(TemplateEquipeEncontro.objects.order_by('pk').values())
        before_roles = list(TemplateRoleEquipe.objects.order_by('pk').values())
        with self.assertRaisesMessage(CommandError, 'template real conflitante'):
            self.run_seed()
        self.assertEqual(list(Pessoa.objects.filter(nome__in=DEMO_PERSON_NAMES).order_by('pk').values()), before_people)
        self.assertEqual(list(Encontro.objects.filter(
            encontro__in=[title for title, _ in DEMO_ENCOUNTERS],
        ).order_by('pk').values()), before_encounters)
        self.assertEqual(list(User.objects.filter(
            username__in=[username for username, _ in DEMO_ACCOUNTS],
        ).order_by('pk').values()), before_users)
        self.assertEqual(list(TemplateEquipeEncontro.objects.order_by('pk').values()), before_templates)
        self.assertEqual(list(TemplateRoleEquipe.objects.order_by('pk').values()), before_roles)

    def test_reset_removes_only_demo_legacy_template(self):
        legacy = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA, codigo='demo-coordenacao-geral',
            nome='[DEMO] Coordenação Geral',
        )
        TemplateRoleEquipe.objects.create(
            template_equipe=legacy, codigo='demo-apoio-coordenacao', nome='Apoio',
        )
        real = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESPPA, codigo='demo-coordenacao-geral',
            nome='Coordenação real legada',
        )
        TemplateRoleEquipe.objects.create(
            template_equipe=real, codigo='papel-real', nome='Papel real',
        )
        before = TemplateEquipeEncontro.objects.filter(pk=real.pk).values().get()
        roles_before = list(real.roles.values())
        self.run_seed()
        self.run_reset()
        self.assertFalse(TemplateEquipeEncontro.objects.filter(pk=legacy.pk).exists())
        self.assertEqual(TemplateEquipeEncontro.objects.filter(pk=real.pk).values().get(), before)
        self.assertEqual(list(real.roles.values()), roles_before)

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
            ConfiguracaoEncontristasEncontro.objects.filter(
                encontro__encontro__in=[
                    title for title, _ in DEMO_ENCOUNTERS
                ],
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
                ConfiguracaoEncontristasEncontro.objects.filter(
                    encontro__encontro__in=[
                        title for title, _ in DEMO_ENCOUNTERS
                    ],
                ).count(),
            ),
            first_counts,
        )

    def test_registration_configuration_reconciliation_is_idempotent(self):
        self.run_seed()
        encounters = {
            key: Encontro.objects.get(encontro=title)
            for key, (title, _) in zip(
                ('serra', 'vale', 'horizonte', 'caminho'),
                DEMO_ENCOUNTERS,
                strict=True,
            )
        }
        recorder = User.objects.get(username='demo.fichas')
        configuration = ConfiguracaoEncontristasEncontro.objects.get(
            encontro=encounters['serra'],
        )
        original_pk = configuration.pk
        original_public_id = configuration.public_id
        configuration.capacidade = 99
        configuration.save(update_fields=['capacidade'])

        _configure_encounter_registrations(encounters, recorder)
        _configure_encounter_registrations(encounters, recorder)

        configuration.refresh_from_db()
        self.assertEqual(configuration.pk, original_pk)
        self.assertEqual(configuration.public_id, original_public_id)
        self.assertEqual(
            configuration.capacidade,
            DEMO_REGISTRATION_SPECS[Encontro.Tipo.ESCALADA]['capacidade'],
        )
        self.assertEqual(
            ConfiguracaoEncontristasEncontro.objects.filter(
                encontro__in=encounters.values(),
            ).count(),
            len(DEMO_ENCOUNTERS),
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
