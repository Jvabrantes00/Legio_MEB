from dataclasses import FrozenInstanceError
from datetime import date

from django.apps import apps
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from core.formacao_catalogo import (
    TEMAS_FORMATIVOS,
    TemaFormativo,
    TipoConteudoFormativo,
)
from core.models import (
    Encontro,
    Frequencia,
    Palestra,
    PalestranteSessao,
    PerfilAlpinista,
    Pessoa,
    SessaoFormativa,
    TrabalhoEncontro,
)
from core.tests.factories import make_alpinista, make_encontro


class EncounterFormationFoundationTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.pessoa = Pessoa.objects.create(nome='Palestrante interno')
        self.perfil = PerfilAlpinista.objects.create(pessoa=self.pessoa)
        self.sessao = SessaoFormativa.objects.create(
            encontro=self.encontro,
            tema_codigo='codigo-estrutural',
            tipo_conteudo=TipoConteudoFormativo.PALESTRA,
            titulo_snapshot='Título histórico',
        )

    def test_registry_nasce_vazio_e_imutavel(self):
        self.assertEqual(dict(TEMAS_FORMATIVOS), {})

        with self.assertRaises(TypeError):
            TEMAS_FORMATIVOS['tema'] = TemaFormativo(
                codigo='tema',
                tipo_conteudo=TipoConteudoFormativo.PALESTRA,
                titulo='Tema',
                tipos_encontro=frozenset({Encontro.Tipo.ESCALADA}),
            )

    def test_definicao_de_tema_e_imutavel(self):
        tema = TemaFormativo(
            codigo='tema',
            tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
            titulo='Tema',
            tipos_encontro=frozenset({Encontro.Tipo.AVC}),
        )

        with self.assertRaises(FrozenInstanceError):
            tema.titulo = 'Título alterado'

    def test_cria_sessao_sem_choices_derivadas_do_registry(self):
        campo_tema = SessaoFormativa._meta.get_field('tema_codigo')

        self.assertIsNone(campo_tema.choices)
        self.assertEqual(self.sessao.tema_codigo, 'codigo-estrutural')
        self.assertEqual(self.sessao.titulo_snapshot, 'Título histórico')
        self.assertEqual(
            self.sessao.status,
            SessaoFormativa.Status.PLANEJADA,
        )

    def test_sessao_realizada_exige_timestamp_coerente(self):
        realizada = SessaoFormativa.objects.create(
            encontro=self.encontro,
            tema_codigo='tema-realizado',
            tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
            titulo_snapshot='Bate-papo realizado',
            status=SessaoFormativa.Status.REALIZADA,
            realizada_em=timezone.now(),
        )
        self.assertEqual(realizada.status, SessaoFormativa.Status.REALIZADA)

        casos_invalidos = (
            {
                'tema_codigo': 'status-invalido',
                'status': 'status_invalido',
            },
            {
                'tema_codigo': 'tipo-invalido',
                'tipo_conteudo': 'tipo_invalido',
            },
            {
                'tema_codigo': 'realizada-sem-data',
                'status': SessaoFormativa.Status.REALIZADA,
            },
            {
                'tema_codigo': 'planejada-com-data',
                'realizada_em': timezone.now(),
            },
        )
        for valores in casos_invalidos:
            with self.subTest(valores=valores):
                parametros = {
                    'encontro': self.encontro,
                    'tipo_conteudo': TipoConteudoFormativo.PALESTRA,
                    'titulo_snapshot': 'Sessão inválida',
                    **valores,
                }
                with self.assertRaises(IntegrityError), transaction.atomic():
                    SessaoFormativa.objects.create(**parametros)

    def test_sessao_aceita_multiplos_palestrantes_internos_e_externos(self):
        interno = PalestranteSessao.objects.create(
            sessao_formativa=self.sessao,
            perfil_alpinista=self.perfil,
        )
        externo_a = PalestranteSessao.objects.create(
            sessao_formativa=self.sessao,
            nome_externo='Convidado externo A',
        )
        externo_b = PalestranteSessao.objects.create(
            sessao_formativa=self.sessao,
            nome_externo='Convidado externo B',
        )

        self.assertEqual(self.sessao.palestrantes.count(), 3)
        self.assertEqual(interno.perfil_alpinista, self.perfil)
        self.assertEqual(externo_a.nome_externo, 'Convidado externo A')
        self.assertEqual(externo_b.nome_externo, 'Convidado externo B')

    def test_constraint_xor_rejeita_ambos_ou_nenhum(self):
        casos_invalidos = (
            {},
            {
                'perfil_alpinista': self.perfil,
                'nome_externo': 'Origem duplicada',
            },
        )
        for valores in casos_invalidos:
            with self.subTest(valores=valores):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    PalestranteSessao.objects.create(
                        sessao_formativa=self.sessao,
                        **valores,
                    )

    def test_perfil_interno_nao_se_repete_na_mesma_sessao(self):
        PalestranteSessao.objects.create(
            sessao_formativa=self.sessao,
            perfil_alpinista=self.perfil,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            PalestranteSessao.objects.create(
                sessao_formativa=self.sessao,
                perfil_alpinista=self.perfil,
            )

    def test_status_ministrou_exige_timestamp_coerente(self):
        palestrante = PalestranteSessao.objects.create(
            sessao_formativa=self.sessao,
            perfil_alpinista=self.perfil,
            status=PalestranteSessao.Status.MINISTROU,
            ministrou_em=timezone.now(),
        )
        self.assertEqual(
            palestrante.status,
            PalestranteSessao.Status.MINISTROU,
        )

        casos_invalidos = (
            {
                'nome_externo': 'Status inválido',
                'status': 'status_invalido',
            },
            {
                'nome_externo': 'Sem timestamp',
                'status': PalestranteSessao.Status.MINISTROU,
            },
            {
                'nome_externo': 'Previsto com timestamp',
                'ministrou_em': timezone.now(),
            },
        )
        for valores in casos_invalidos:
            with self.subTest(valores=valores):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    PalestranteSessao.objects.create(
                        sessao_formativa=self.sessao,
                        **valores,
                    )

    def test_fks_historicas_usam_protect(self):
        palestrante = PalestranteSessao.objects.create(
            sessao_formativa=self.sessao,
            perfil_alpinista=self.perfil,
        )

        for protected_object in (self.encontro, self.perfil, self.sessao):
            with self.subTest(protected_object=protected_object):
                with self.assertRaises(ProtectedError):
                    protected_object.delete()

        self.assertTrue(
            PalestranteSessao.objects.filter(pk=palestrante.pk).exists()
        )

    def test_estrutura_legada_e_demais_dominios_permanecem_independentes(self):
        alpinista = make_alpinista()
        palestra = Palestra.objects.create(
            alpinista=alpinista,
            encontro=self.encontro,
            titulo='Palestra legada preservada',
        )
        PalestranteSessao.objects.create(
            sessao_formativa=self.sessao,
            perfil_alpinista=self.perfil,
        )

        self.assertEqual(palestra.titulo, 'Palestra legada preservada')
        self.assertFalse(TrabalhoEncontro.objects.exists())
        self.assertFalse(Frequencia.objects.exists())
        with self.assertRaises(LookupError):
            apps.get_model('core', 'HistoricoFormativo')


class EncounterFormationMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0032_vinculousuariopessoa')
    migrate_to = ('core', '0033_expand_sessoes_formativas')

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        AlpinistaAntigo = old_apps.get_model('core', 'Alpinista')
        EncontroAntigo = old_apps.get_model('core', 'Encontro')
        PalestraAntiga = old_apps.get_model('core', 'Palestra')

        alpinista = AlpinistaAntigo.objects.create(
            nome='Alpinista legado preservado',
            email='formacao-legada@example.test',
            telefone='61999992222',
        )
        encontro = EncontroAntigo.objects.create(
            encontro='Escalada preservada',
            tipo='Escalada',
            data_referencia=date(2030, 1, 1),
            data_exato='1 de janeiro de 2030',
        )
        self.palestra_id = PalestraAntiga.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            titulo='Palestra legada preservada',
        ).pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_forward_preserva_palestra_e_cria_estrutura_nova_vazia(self):
        PalestraNova = self.apps.get_model('core', 'Palestra')
        Sessao = self.apps.get_model('core', 'SessaoFormativa')
        Palestrante = self.apps.get_model('core', 'PalestranteSessao')

        palestra = PalestraNova.objects.get(pk=self.palestra_id)
        self.assertEqual(palestra.titulo, 'Palestra legada preservada')
        self.assertEqual(Sessao.objects.count(), 0)
        self.assertEqual(Palestrante.objects.count(), 0)

        tabelas = connection.introspection.table_names()
        self.assertIn('core_palestra', tabelas)
        self.assertIn('core_sessaoformativa', tabelas)
        self.assertIn('core_palestrantesessao', tabelas)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()
