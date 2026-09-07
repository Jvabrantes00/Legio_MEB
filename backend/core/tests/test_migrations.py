from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class NormalizeAlpinistaStatusMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0016_alter_alpinista_status')
    migrate_to = ('core', '0017_normalize_alpinista_status')

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Alpinista = old_apps.get_model('core', 'Alpinista')

        statuses = (
            'Pendente',
            'ATIVO',
            'cOnFiRmAdO',
            'Inativo',
            'ativo',
            'valor_desconhecido',
        )
        for index, status in enumerate(statuses, start=1):
            Alpinista.objects.create(
                cpf=f'000.000.100-{index:02d}',
                nome=f'Alpinista legado {index}',
                email=f'legado{index}@example.test',
                telefone=f'610001{index:04d}',
                status=status,
            )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_normaliza_somente_variacoes_de_status_conhecidos(self):
        Alpinista = self.apps.get_model('core', 'Alpinista')

        statuses = list(
            Alpinista.objects.order_by('id').values_list('status', flat=True)
        )

        self.assertEqual(
            statuses,
            [
                'pendente',
                'ativo',
                'confirmado',
                'inativo',
                'ativo',
                'valor_desconhecido',
            ],
        )
