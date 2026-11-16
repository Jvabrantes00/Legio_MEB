"""Matriz 16.7/16.12: legado, reversão de schema e triggers."""
from datetime import timedelta
from hashlib import sha256
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone

from core.models import (
    CampanhaConvitesEncontro, ConviteEncontro, EntregaConviteEncontro,
    OportunidadeConviteEncontro, OutboxEntregaConvite, Pessoa,
    RodadaConvitesEncontro,
)
from core.tests.factories import make_encontro


class _MigrationScenario:
    def migrate(self, name):
        executor = MigrationExecutor(connection)
        executor.migrate([('core', name)])
        return executor.loader.project_state([('core', name)]).apps

    def restore_leaf(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())

    def trigger_names(self):
        if connection.vendor != 'postgresql':
            return set()
        with connection.cursor() as cursor:
            cursor.execute("SELECT tgname FROM pg_trigger WHERE tgname LIKE 'sia_conv_%' AND NOT tgisinternal")
            return {row[0] for row in cursor.fetchall()}

    def function_names(self):
        if connection.vendor != 'postgresql':
            return set()
        with connection.cursor() as cursor:
            cursor.execute("SELECT proname FROM pg_proc WHERE pronamespace = current_schema()::regnamespace AND proname LIKE 'sia_conv_%'")
            return {row[0] for row in cursor.fetchall()}

    def test_reversao_e_preservacao_de_entrega_e_outbox(self):
        # Executado exclusivamente no banco temporário criado pelo runner de teste.
        now = timezone.now()
        user = get_user_model().objects.create_user(username='migracao_b1')
        encontro = make_encontro()
        pessoa = Pessoa.objects.create(nome='Legado')
        convite = ConviteEncontro.objects.create(pessoa=pessoa, encontro=encontro, finalidade='participar')
        campanha = CampanhaConvitesEncontro.objects.create(encontro=encontro, iniciada_por=user, iniciada_em=now, prazo_confirmacao=now + timedelta(days=7))
        rodada = RodadaConvitesEncontro.objects.create(campanha=campanha, sequencia=1, tipo='inicial', aberta_em=now)
        oportunidade = OportunidadeConviteEncontro.objects.create(rodada=rodada, convite=convite, token_digest=sha256(b'migracao').hexdigest(), expira_em=now + timedelta(days=2))
        entrega = EntregaConviteEncontro.objects.create(oportunidade=oportunidade, canal='email')
        outbox = OutboxEntregaConvite.objects.create(oportunidade=oportunidade, segredo_criptografado='registro-de-teste')
        self.addCleanup(self.restore_leaf)

        apps_50 = self.migrate('0050_preselecaoencontrista')
        OldEntrega = apps_50.get_model('core', 'EntregaConviteEncontro')
        OldOutbox = apps_50.get_model('core', 'OutboxEntregaConvite')
        before_entrega = OldEntrega.objects.filter(pk=entrega.pk).values().get()
        before_outbox = OldOutbox.objects.filter(pk=outbox.pk).values().get()
        self.assertFalse(self.trigger_names())
        self.assertFalse(self.function_names())
        self.assertNotIn('core_tentativaentregaconvite', connection.introspection.table_names())

        apps_51 = self.migrate('0051_entrega_reconciliacao')
        self.assertIn('core_tentativaentregaconvite', connection.introspection.table_names())
        self.assertFalse(self.trigger_names())
        NewEntrega = apps_51.get_model('core', 'EntregaConviteEncontro')
        after_entrega = NewEntrega.objects.filter(pk=entrega.pk).values().get()
        self.assertIsNone(after_entrega.pop('protocolo'))
        self.assertEqual(after_entrega, before_entrega)
        self.assertEqual(apps_51.get_model('core', 'OutboxEntregaConvite').objects.filter(pk=outbox.pk).values().get(), before_outbox)

        self.migrate('0052_entrega_integridade')
        if connection.vendor == 'postgresql':
            self.assertEqual(len(self.trigger_names()), 6)
            self.assertEqual(len(self.function_names()), 5)
        self.migrate('0051_entrega_reconciliacao')
        self.assertFalse(self.trigger_names())
        self.assertFalse(self.function_names())
        self.migrate('0050_preselecaoencontrista')
        self.assertNotIn('core_tentativaentregaconvite', connection.introspection.table_names())
        self.restore_leaf()


@skipUnless(connection.vendor == 'sqlite', 'Requer SQLite isolado')
class MigracaoEntregaSQLiteTests(_MigrationScenario, TransactionTestCase):
    pass


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL descartável')
class MigracaoEntregaPostgresTests(_MigrationScenario, TransactionTestCase):
    pass
