from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from core.models import (
    ConviteEncontro,
    Encontro,
    Frequencia,
    Inscricao,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
    VinculoEncontroLegado,
)
from core.tests.factories import make_encontro


class EncounterParticipationFoundationTests(TestCase):
    def setUp(self):
        self.pessoa = Pessoa.objects.create(nome='Pessoa candidata')
        self.outra_pessoa = Pessoa.objects.create(nome='Outra pessoa')
        self.escalada = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.outra_escalada = make_encontro(tipo=Encontro.Tipo.ESCALADA)

    def test_models_expoem_choices_e_relacoes_aprovadas(self):
        inscricao = Inscricao.objects.create(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            inscricao=inscricao,
        )
        participacao = ParticipacaoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            convite=convite,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )

        self.assertEqual(inscricao.status, Inscricao.Status.PENDENTE)
        self.assertEqual(convite.status, ConviteEncontro.Status.CONVIDADO)
        self.assertEqual(participacao.pessoa, self.pessoa)
        self.assertIs(
            ParticipacaoEncontro._meta.get_field('pessoa').remote_field.model,
            Pessoa,
        )
        self.assertEqual(
            set(ParticipacaoEncontro.Resultado.values),
            {'concluiu', 'faltou', 'desistiu'},
        )

    def test_inscricao_impede_duas_pendencias_da_mesma_pessoa_e_tipo(self):
        Inscricao.objects.create(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Inscricao.objects.create(
                pessoa=self.pessoa,
                tipo=Inscricao.Tipo.ESCALADA,
            )

        Inscricao.objects.create(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESPPA,
        )

    def test_inscricao_cumprida_libera_nova_pendencia_e_exige_timestamp(self):
        Inscricao.objects.create(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
            status=Inscricao.Status.CUMPRIDA,
            cumprida_em=timezone.now(),
        )
        nova = Inscricao.objects.create(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )

        self.assertEqual(nova.status, Inscricao.Status.PENDENTE)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Inscricao.objects.create(
                pessoa=self.outra_pessoa,
                tipo=Inscricao.Tipo.ESCALADA,
                status=Inscricao.Status.CUMPRIDA,
            )

    def test_checks_rejeitam_choices_invalidas(self):
        invalid_creations = (
            lambda: Inscricao.objects.create(
                pessoa=self.pessoa,
                tipo='AVC',
            ),
            lambda: ConviteEncontro.objects.create(
                pessoa=self.pessoa,
                encontro=self.escalada,
                finalidade='outra',
            ),
            lambda: ParticipacaoEncontro.objects.create(
                pessoa=self.pessoa,
                encontro=self.escalada,
                resultado='confirmado',
                tipo_encontro=Encontro.Tipo.ESCALADA,
            ),
        )

        for create_invalid in invalid_creations:
            with self.subTest(create_invalid=create_invalid):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    create_invalid()

    def test_convite_e_unico_por_pessoa_encontro_e_finalidade(self):
        ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ConviteEncontro.objects.create(
                pessoa=self.pessoa,
                encontro=self.escalada,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            )

        ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
        )

    def test_convite_para_trabalhar_nao_aceita_inscricao(self):
        inscricao = Inscricao.objects.create(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ConviteEncontro.objects.create(
                pessoa=self.pessoa,
                encontro=self.escalada,
                finalidade=ConviteEncontro.Finalidade.TRABALHAR,
                inscricao=inscricao,
            )

    def test_participacao_e_unica_por_pessoa_e_encontro(self):
        ParticipacaoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ParticipacaoEncontro.objects.create(
                pessoa=self.pessoa,
                encontro=self.escalada,
                resultado=ParticipacaoEncontro.Resultado.DESISTIU,
                tipo_encontro=Encontro.Tipo.ESCALADA,
            )

    def test_conclusao_e_unica_por_pessoa_e_tipo(self):
        ParticipacaoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ParticipacaoEncontro.objects.create(
                pessoa=self.pessoa,
                encontro=self.outra_escalada,
                resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
                tipo_encontro=Encontro.Tipo.ESCALADA,
            )

        ParticipacaoEncontro.objects.create(
            pessoa=self.outra_pessoa,
            encontro=self.outra_escalada,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )

    def test_resultados_nao_concluidos_podem_repetir_tipo_em_edicoes_distintas(self):
        ParticipacaoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )
        ParticipacaoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.outra_escalada,
            resultado=ParticipacaoEncontro.Resultado.DESISTIU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )

        self.assertEqual(
            ParticipacaoEncontro.objects.filter(pessoa=self.pessoa).count(),
            2,
        )

    def test_confirmacao_e_resultado_nao_criam_perfil_ou_frequencia(self):
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        self.assertFalse(ParticipacaoEncontro.objects.exists())
        self.assertFalse(PerfilAlpinista.objects.exists())

        ParticipacaoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            convite=convite,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )

        self.assertFalse(PerfilAlpinista.objects.exists())
        self.assertFalse(Frequencia.objects.exists())

    def test_fks_historicas_usam_protect(self):
        inscricao = Inscricao.objects.create(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            inscricao=inscricao,
        )
        ParticipacaoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            convite=convite,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )

        for protected_object in (
            self.pessoa,
            self.escalada,
            inscricao,
            convite,
        ):
            with self.subTest(protected_object=protected_object):
                with self.assertRaises(ProtectedError):
                    protected_object.delete()

    def test_vinculo_legado_mantem_tabela_fisica(self):
        self.assertEqual(
            VinculoEncontroLegado._meta.db_table,
            'core_participacaoencontro',
        )
        self.assertEqual(
            ParticipacaoEncontro._meta.db_table,
            'core_participacaoencontro_resultado',
        )


class EncounterParticipationMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0028_nucleo_encontros')
    migrate_to = ('core', '0029_expand_inscricao_convite_participacao')

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        Alpinista = old_apps.get_model('core', 'Alpinista')
        EncontroAntigo = old_apps.get_model('core', 'Encontro')
        FuncaoEncontro = old_apps.get_model('core', 'FuncaoEncontro')
        ParticipacaoAntiga = old_apps.get_model('core', 'ParticipacaoEncontro')

        alpinista = Alpinista.objects.create(
            nome='Vínculo preservado',
            email='vinculo-preservado@example.test',
            telefone='61999990000',
        )
        encontro = EncontroAntigo.objects.create(
            encontro='Escalada legada',
            tipo='Escalada',
            data_referencia=date(2027, 1, 1),
            data_exato='1 de janeiro de 2027',
        )
        funcao = FuncaoEncontro.objects.create(
            nome='Encontrista',
            tipo='encontrista',
        )
        self.vinculo_id = ParticipacaoAntiga.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            funcao=funcao,
        ).pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_forward_preserva_tabela_e_dados_e_cria_tabelas_vazias(self):
        VinculoLegado = self.apps.get_model('core', 'VinculoEncontroLegado')
        InscricaoNova = self.apps.get_model('core', 'Inscricao')
        ConviteNovo = self.apps.get_model('core', 'ConviteEncontro')
        ParticipacaoNova = self.apps.get_model('core', 'ParticipacaoEncontro')

        self.assertEqual(
            VinculoLegado._meta.db_table,
            'core_participacaoencontro',
        )
        self.assertTrue(VinculoLegado.objects.filter(pk=self.vinculo_id).exists())
        self.assertEqual(InscricaoNova.objects.count(), 0)
        self.assertEqual(ConviteNovo.objects.count(), 0)
        self.assertEqual(ParticipacaoNova.objects.count(), 0)
        self.assertIn(
            'core_participacaoencontro',
            connection.introspection.table_names(),
        )
        self.assertIn(
            'core_participacaoencontro_resultado',
            connection.introspection.table_names(),
        )

    def test_reverse_restaura_estado_legado_sem_perder_dados(self):
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        ParticipacaoAntiga = old_apps.get_model('core', 'ParticipacaoEncontro')

        self.assertTrue(
            ParticipacaoAntiga.objects.filter(pk=self.vinculo_id).exists()
        )
        self.assertNotIn(
            'core_participacaoencontro_resultado',
            connection.introspection.table_names(),
        )

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()
