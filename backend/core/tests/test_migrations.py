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
        cpfs = ('False', '', 'NULL', 'None', '52998224725', '11144477735')
        for index, (status, cpf) in enumerate(zip(statuses, cpfs), start=1):
            Alpinista.objects.create(
                cpf=cpf,
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

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()


class NormalizeAlpinistaCPFMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0017_normalize_alpinista_status')
    migrate_to = ('core', '0018_alter_alpinista_cpf')

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Alpinista = old_apps.get_model('core', 'Alpinista')

        cpfs = ('False', '', 'NULL', '529.982.247-25')
        for index, cpf in enumerate(cpfs, start=1):
            Alpinista.objects.create(
                cpf=cpf,
                nome=f'Alpinista CPF legado {index}',
                email=f'cpf-legado-{index}@example.test',
                telefone=f'610002{index:04d}',
            )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_normaliza_ausencias_e_cpf_valido(self):
        Alpinista = self.apps.get_model('core', 'Alpinista')

        cpfs = list(Alpinista.objects.order_by('id').values_list('cpf', flat=True))

        self.assertEqual(cpfs, [None, None, None, '52998224725'])

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()


class RejectUnknownAlpinistaCPFMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0017_normalize_alpinista_status')
    migrate_to = ('core', '0018_alter_alpinista_cpf')

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Alpinista = old_apps.get_model('core', 'Alpinista')
        self.alpinista_id = Alpinista.objects.create(
            cpf='valor-invalido',
            nome='Alpinista CPF desconhecido',
            email='cpf-desconhecido@example.test',
            telefone='6100030001',
        ).id

    def test_interrompe_migration_sem_alterar_valor_desconhecido(self):
        executor = MigrationExecutor(connection)

        with self.assertRaises(RuntimeError):
            executor.migrate([self.migrate_to])

        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Alpinista = old_apps.get_model('core', 'Alpinista')
        self.assertEqual(Alpinista.objects.get(pk=self.alpinista_id).cpf, 'valor-invalido')

    def tearDown(self):
        executor = MigrationExecutor(connection)
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        old_apps.get_model('core', 'Alpinista').objects.all().delete()
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()
