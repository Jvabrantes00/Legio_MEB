from datetime import date
from importlib import import_module
from pathlib import Path
from tempfile import TemporaryDirectory

from django.db import connection, models
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings


class BackfillPessoaMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0024_material_entregamaterial')
    migrate_schema = ('core', '0025_expand_pessoa')
    migrate_to = ('core', '0026_backfill_pessoa')

    def setUp(self):
        super().setUp()
        self.media_directory = TemporaryDirectory()
        self.media_override = override_settings(
            MEDIA_ROOT=self.media_directory.name
        )
        self.media_override.enable()

        original_photo = (
            Path(self.media_directory.name) / 'fotos' / 'original.jpg'
        )
        original_photo.parent.mkdir(parents=True)
        original_photo.write_bytes(b'foto-existente')

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Alpinista = old_apps.get_model('core', 'Alpinista')

        self.complete_id = Alpinista.objects.create(
            id=41,
            nome='Cadastro legado completo',
            dataNascimento=date(1990, 5, 17),
            endereco='Endereço monolítico sem parsing',
            email='pessoa@example.test',
            telefone='61999990001',
            nomePai='Responsável pai',
            telefonePai='61999990002',
            nomeMae='Responsável mãe',
            telefoneMae='61999990003',
            restricaoSaude='Texto genérico não classificável',
            medicacao='Medicação preservada literalmente',
            conheciaEscalada='Campo sem equivalência',
            grupo='Grupo legado',
            status='ativo',
            foto='fotos/original.jpg',
            batizado=True,
            primeira_comunhao=False,
            crismado=None,
            eh_violeiro=True,
            canta=True,
            is_neurodivergente=True,
            tipo_neurodivergente='Texto preservado literalmente',
            cpf='52998224725',
        ).pk
        self.minimal_id = Alpinista.objects.create(
            id=80,
            nome='Cadastro legado mínimo',
            email='pessoa-minima@example.test',
            telefone='61999990004',
            status='pendente',
        ).pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_backfill_preserva_identidade_campos_diretos_e_auxiliares(self):
        Alpinista = self.apps.get_model('core', 'Alpinista')
        DadosSaudePessoa = self.apps.get_model('core', 'DadosSaudePessoa')
        Pessoa = self.apps.get_model('core', 'Pessoa')
        ResponsavelPessoa = self.apps.get_model('core', 'ResponsavelPessoa')
        TelefonePessoa = self.apps.get_model('core', 'TelefonePessoa')

        pessoa = Pessoa.objects.get(pk=self.complete_id)
        alpinista = Alpinista.objects.get(pk=self.complete_id)

        self.assertEqual(Pessoa.objects.count(), 2)
        self.assertEqual(alpinista.pessoa_id, pessoa.pk)
        self.assertEqual(pessoa.pk, alpinista.pk)
        self.assertEqual(pessoa.nome, alpinista.nome)
        self.assertEqual(pessoa.data_nascimento, alpinista.dataNascimento)
        self.assertEqual(pessoa.cpf, '52998224725')
        self.assertEqual(pessoa.email, 'pessoa@example.test')
        self.assertEqual(pessoa.foto.name, 'fotos/original.jpg')
        self.assertIs(pessoa.batismo, True)
        self.assertIs(pessoa.primeira_comunhao, False)
        self.assertIsNone(pessoa.crisma)

        self.assertEqual(
            list(
                TelefonePessoa.objects.filter(pessoa_id=pessoa.pk)
                .values_list('numero', 'whatsapp')
            ),
            [('61999990001', False)],
        )
        self.assertEqual(
            set(
                ResponsavelPessoa.objects.filter(pessoa_id=pessoa.pk)
                .values_list('parentesco', 'nome', 'telefone', 'principal')
            ),
            {
                ('pai', 'Responsável pai', '61999990002', False),
                ('mãe', 'Responsável mãe', '61999990003', False),
            },
        )
        dados_saude = DadosSaudePessoa.objects.get(pessoa_id=pessoa.pk)
        self.assertEqual(
            dados_saude.medicamentos,
            'Medicação preservada literalmente',
        )
        self.assertEqual(
            dados_saude.neurodivergencia,
            'Texto preservado literalmente',
        )

    def test_nao_inventa_dados_nem_perfil_e_nao_duplica_arquivo(self):
        Alpinista = self.apps.get_model('core', 'Alpinista')
        EnderecoPessoa = self.apps.get_model('core', 'EnderecoPessoa')
        PerfilAlpinista = self.apps.get_model('core', 'PerfilAlpinista')
        Pessoa = self.apps.get_model('core', 'Pessoa')
        RegiaoAdministrativa = self.apps.get_model(
            'core',
            'RegiaoAdministrativa',
        )

        pessoa = Pessoa.objects.get(pk=self.complete_id)
        alpinista = Alpinista.objects.get(pk=self.complete_id)

        self.assertEqual(Pessoa.objects.get(pk=self.minimal_id).apelido, '')
        self.assertIsNone(pessoa.estado_civil)
        self.assertEqual(EnderecoPessoa.objects.count(), 0)
        self.assertEqual(RegiaoAdministrativa.objects.count(), 0)
        self.assertEqual(PerfilAlpinista.objects.count(), 0)

        self.assertEqual(
            alpinista.endereco,
            'Endereço monolítico sem parsing',
        )
        self.assertEqual(
            alpinista.restricaoSaude,
            'Texto genérico não classificável',
        )
        self.assertEqual(alpinista.status, 'ativo')
        self.assertEqual(alpinista.grupo, 'Grupo legado')
        self.assertTrue(alpinista.eh_violeiro)
        self.assertTrue(alpinista.canta)

        files = sorted(
            path.relative_to(self.media_directory.name).as_posix()
            for path in Path(self.media_directory.name).rglob('*')
            if path.is_file()
        )
        self.assertEqual(files, ['fotos/original.jpg'])

    def test_sequence_avanca_depois_dos_ids_explicitos(self):
        Pessoa = self.apps.get_model('core', 'Pessoa')

        nova_pessoa = Pessoa.objects.create(nome='Pessoa posterior')

        self.assertGreater(nova_pessoa.pk, max(self.complete_id, self.minimal_id))

    def test_reexecucao_controlada_e_idempotente(self):
        models = (
            'Pessoa',
            'TelefonePessoa',
            'ResponsavelPessoa',
            'DadosSaudePessoa',
            'PerfilAlpinista',
        )
        before = {
            model: self.apps.get_model('core', model).objects.count()
            for model in models
        }
        migration = import_module('core.migrations.0026_backfill_pessoa')

        with connection.schema_editor() as schema_editor:
            migration.backfill_pessoas(self.apps, schema_editor)

        after = {
            model: self.apps.get_model('core', model).objects.count()
            for model in models
        }
        self.assertEqual(after, before)

    def test_reverse_remove_somente_pessoas_do_backfill_e_permite_forward(self):
        Pessoa = self.apps.get_model('core', 'Pessoa')
        TelefonePessoa = self.apps.get_model('core', 'TelefonePessoa')
        pessoa_independente = Pessoa.objects.create(nome='Pessoa independente')
        TelefonePessoa.objects.create(
            pessoa=pessoa_independente,
            numero='61999999999',
        )
        pessoa_independente_id = pessoa_independente.pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_schema])
        schema_apps = executor.loader.project_state([self.migrate_schema]).apps
        Alpinista = schema_apps.get_model('core', 'Alpinista')
        Pessoa = schema_apps.get_model('core', 'Pessoa')
        TelefonePessoa = schema_apps.get_model('core', 'TelefonePessoa')

        self.assertFalse(Pessoa.objects.filter(pk=self.complete_id).exists())
        self.assertFalse(Pessoa.objects.filter(pk=self.minimal_id).exists())
        self.assertTrue(Pessoa.objects.filter(pk=pessoa_independente_id).exists())
        self.assertTrue(
            TelefonePessoa.objects.filter(
                pessoa_id=pessoa_independente_id,
                numero='61999999999',
            ).exists()
        )
        self.assertFalse(
            Alpinista.objects.exclude(pessoa_id=None).exists()
        )

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        forward_apps = executor.loader.project_state([self.migrate_to]).apps
        Pessoa = forward_apps.get_model('core', 'Pessoa')
        PerfilAlpinista = forward_apps.get_model('core', 'PerfilAlpinista')

        self.assertEqual(Pessoa.objects.count(), 3)
        self.assertTrue(Pessoa.objects.filter(pk=self.complete_id).exists())
        self.assertTrue(Pessoa.objects.filter(pk=self.minimal_id).exists())
        self.assertTrue(Pessoa.objects.filter(pk=pessoa_independente_id).exists())
        self.assertEqual(PerfilAlpinista.objects.count(), 0)

    def test_rollback_e_forward_completos_das_duas_migrations(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        Alpinista = old_apps.get_model('core', 'Alpinista')

        self.assertEqual(Alpinista.objects.count(), 2)
        with self.assertRaises(LookupError):
            old_apps.get_model('core', 'Pessoa')

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        forward_apps = executor.loader.project_state([self.migrate_to]).apps
        Alpinista = forward_apps.get_model('core', 'Alpinista')
        Pessoa = forward_apps.get_model('core', 'Pessoa')
        PerfilAlpinista = forward_apps.get_model('core', 'PerfilAlpinista')

        self.assertEqual(Pessoa.objects.count(), 2)
        self.assertFalse(
            Alpinista.objects.exclude(pessoa_id=models.F('id')).exists()
        )
        self.assertEqual(PerfilAlpinista.objects.count(), 0)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        self.media_override.disable()
        self.media_directory.cleanup()
        super().tearDown()
