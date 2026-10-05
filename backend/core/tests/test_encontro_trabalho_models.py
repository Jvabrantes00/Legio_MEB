from datetime import date

from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Frequencia,
    FuncaoEncontro,
    Pessoa,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoEncontroLegado,
)
from core.tests.factories import make_alpinista, make_encontro, make_funcao


class EncounterWorkFoundationTests(TestCase):
    def setUp(self):
        self.pessoa = Pessoa.objects.create(nome='Pessoa trabalhadora')
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.template_equipe = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='coordenacao-geral',
            nome='Coordenação Geral',
            ordem=1,
            capacidade_minima_recomendada=6,
            capacidade_maxima_recomendada=6,
        )
        self.template_role = TemplateRoleEquipe.objects.create(
            template_equipe=self.template_equipe,
            codigo='adulto-geral',
            nome='Adulto Geral',
            ordem=1,
            quantidade_estrutural=2,
            concede_registro_presenca=True,
        )
        self.equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=self.template_equipe,
            codigo=self.template_equipe.codigo,
            nome=self.template_equipe.nome,
            ordem=self.template_equipe.ordem,
            capacidade_minima_recomendada=(
                self.template_equipe.capacidade_minima_recomendada
            ),
            capacidade_maxima_recomendada=(
                self.template_equipe.capacidade_maxima_recomendada
            ),
        )
        self.role = RoleEquipeEncontro.objects.create(
            equipe_encontro=self.equipe,
            template_origem=self.template_role,
            codigo=self.template_role.codigo,
            nome=self.template_role.nome,
            ordem=self.template_role.ordem,
            quantidade_estrutural=self.template_role.quantidade_estrutural,
            concede_registro_presenca=(
                self.template_role.concede_registro_presenca
            ),
        )

    def _criar_convite(self, *, pessoa=None, encontro=None, finalidade=None):
        return ConviteEncontro.objects.create(
            pessoa=pessoa or self.pessoa,
            encontro=encontro or self.encontro,
            finalidade=finalidade or ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

    def test_cria_template_e_roles_estruturais(self):
        self.assertEqual(
            self.template_equipe.tipo_encontro,
            Encontro.Tipo.ESCALADA,
        )
        self.assertEqual(self.template_equipe.roles.get(), self.template_role)
        self.assertEqual(self.template_role.quantidade_estrutural, 2)
        self.assertTrue(self.template_role.concede_registro_presenca)

    def test_snapshot_permanece_independente_apos_alterar_template(self):
        self.template_equipe.nome = 'Nome futuro do template'
        self.template_equipe.capacidade_maxima_recomendada = 8
        self.template_equipe.save(
            update_fields=['nome', 'capacidade_maxima_recomendada']
        )
        self.template_role.nome = 'Role futura'
        self.template_role.quantidade_estrutural = 3
        self.template_role.save(
            update_fields=['nome', 'quantidade_estrutural']
        )

        self.equipe.refresh_from_db()
        self.role.refresh_from_db()
        self.assertEqual(self.equipe.nome, 'Coordenação Geral')
        self.assertEqual(self.equipe.capacidade_maxima_recomendada, 6)
        self.assertEqual(self.role.nome, 'Adulto Geral')
        self.assertEqual(self.role.quantidade_estrutural, 2)

    def test_convite_trabalho_pode_existir_sem_role_proposta(self):
        convite = self._criar_convite()

        self.assertIsNone(convite.role_trabalho_proposta)
        self.assertFalse(TrabalhoEncontro.objects.exists())

    def test_role_proposta_so_pode_ser_usada_em_convite_trabalho(self):
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            role_trabalho_proposta=self.role,
        )
        self.assertEqual(convite.role_trabalho_proposta, self.role)

        outra_pessoa = Pessoa.objects.create(nome='Pessoa participante')
        with self.assertRaises(IntegrityError), transaction.atomic():
            ConviteEncontro.objects.create(
                pessoa=outra_pessoa,
                encontro=self.encontro,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
                role_trabalho_proposta=self.role,
            )

    def test_trabalho_pode_aguardar_alocacao_sem_role(self):
        trabalho = TrabalhoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            convite=self._criar_convite(),
        )

        self.assertEqual(
            trabalho.status,
            TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO,
        )
        self.assertIsNone(trabalho.role_equipe)
        self.assertIs(
            TrabalhoEncontro._meta.get_field('role_equipe').remote_field.model,
            RoleEquipeEncontro,
        )
        self.assertFalse(hasattr(trabalho, 'substituido_por'))
        self.assertFalse(Frequencia.objects.exists())

    def test_trabalho_alocado_referencia_role_do_snapshot(self):
        trabalho = TrabalhoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            convite=self._criar_convite(),
            role_equipe=self.role,
            status=TrabalhoEncontro.Status.ALOCADO,
        )

        self.assertEqual(trabalho.role_equipe, self.role)
        self.assertEqual(trabalho.role_equipe.equipe_encontro, self.equipe)
        self.assertEqual(
            set(TrabalhoEncontro.Status.values),
            {
                'aguardando_alocacao',
                'alocado',
                'trabalhou',
                'faltou',
                'retirado',
            },
        )

    def test_trabalho_e_unico_por_pessoa_e_encontro(self):
        TrabalhoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            convite=self._criar_convite(),
        )
        outro_convite = self._criar_convite(
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            TrabalhoEncontro.objects.create(
                pessoa=self.pessoa,
                encontro=self.encontro,
                convite=outro_convite,
            )

    def test_constraints_de_template_e_snapshot_rejeitam_incoerencias(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            TemplateEquipeEncontro.objects.create(
                tipo_encontro='tipo-invalido',
                codigo='tipo-invalido',
                nome='Tipo inválido',
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            TemplateEquipeEncontro.objects.create(
                tipo_encontro=Encontro.Tipo.ESCALADA,
                codigo=self.template_equipe.codigo,
                nome='Duplicada',
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            TemplateEquipeEncontro.objects.create(
                tipo_encontro=Encontro.Tipo.AVC,
                codigo='capacidade-invalida',
                nome='Capacidade inválida',
                capacidade_minima_recomendada=5,
                capacidade_maxima_recomendada=4,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            TemplateRoleEquipe.objects.create(
                template_equipe=self.template_equipe,
                codigo='quantidade-invalida',
                nome='Quantidade inválida',
                quantidade_estrutural=0,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            EquipeEncontro.objects.create(
                encontro=self.encontro,
                template_origem=self.template_equipe,
                codigo='snapshot-invalido',
                nome='Snapshot inválido',
                capacidade_minima_recomendada=10,
                capacidade_maxima_recomendada=5,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            RoleEquipeEncontro.objects.create(
                equipe_encontro=self.equipe,
                template_origem=self.template_role,
                codigo='role-invalida',
                nome='Role inválida',
                quantidade_estrutural=0,
            )

    def test_constraints_de_status_exigem_alocacao_e_resultado_coerentes(self):
        casos_invalidos = (
            {
                'status': 'status_invalido',
            },
            {
                'status': TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO,
                'role_equipe': self.role,
            },
            {
                'status': TrabalhoEncontro.Status.ALOCADO,
            },
            {
                'status': TrabalhoEncontro.Status.TRABALHOU,
                'role_equipe': self.role,
            },
            {
                'status': TrabalhoEncontro.Status.ALOCADO,
                'role_equipe': self.role,
                'resultado_registrado_em': timezone.now(),
            },
        )

        for indice, valores in enumerate(casos_invalidos):
            with self.subTest(valores=valores):
                pessoa = Pessoa.objects.create(nome=f'Pessoa inválida {indice}')
                convite = self._criar_convite(pessoa=pessoa)
                with self.assertRaises(IntegrityError), transaction.atomic():
                    TrabalhoEncontro.objects.create(
                        pessoa=pessoa,
                        encontro=self.encontro,
                        convite=convite,
                        **valores,
                    )

        pessoa_valida = Pessoa.objects.create(nome='Pessoa trabalhou')
        trabalho = TrabalhoEncontro.objects.create(
            pessoa=pessoa_valida,
            encontro=self.encontro,
            convite=self._criar_convite(pessoa=pessoa_valida),
            role_equipe=self.role,
            status=TrabalhoEncontro.Status.TRABALHOU,
            resultado_registrado_em=timezone.now(),
        )
        self.assertEqual(trabalho.status, TrabalhoEncontro.Status.TRABALHOU)

    def test_fks_historicas_usam_protect(self):
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
            role_trabalho_proposta=self.role,
        )
        TrabalhoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            convite=convite,
            role_equipe=self.role,
            status=TrabalhoEncontro.Status.ALOCADO,
        )

        for protected_object in (
            self.template_equipe,
            self.template_role,
            self.equipe,
            self.role,
            convite,
            self.pessoa,
            self.encontro,
        ):
            with self.subTest(protected_object=protected_object):
                with self.assertRaises(ProtectedError):
                    protected_object.delete()

    def test_estrutura_legada_permanece_independente(self):
        alpinista = make_alpinista()
        funcao = make_funcao(nome='Equipe legada', tipo='equipe')
        vinculo = VinculoEncontroLegado.objects.create(
            alpinista=alpinista,
            encontro=self.encontro,
            funcao=funcao,
            coordenador=True,
        )

        self.assertEqual(
            VinculoEncontroLegado._meta.db_table,
            'core_participacaoencontro',
        )
        self.assertEqual(vinculo.funcao, funcao)
        self.assertIsInstance(funcao, FuncaoEncontro)
        self.assertFalse(TrabalhoEncontro.objects.exists())


class EncounterWorkMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0029_expand_inscricao_convite_participacao')
    migrate_to = ('core', '0030_expand_equipes_trabalho_encontro')

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        PessoaAntiga = old_apps.get_model('core', 'Pessoa')
        AlpinistaAntigo = old_apps.get_model('core', 'Alpinista')
        EncontroAntigo = old_apps.get_model('core', 'Encontro')
        FuncaoAntiga = old_apps.get_model('core', 'FuncaoEncontro')
        VinculoAntigo = old_apps.get_model('core', 'VinculoEncontroLegado')
        ConviteAntigo = old_apps.get_model('core', 'ConviteEncontro')

        pessoa = PessoaAntiga.objects.create(nome='Pessoa preservada')
        alpinista = AlpinistaAntigo.objects.create(
            nome='Alpinista legado preservado',
            email='trabalho-legado@example.test',
            telefone='61999991111',
            pessoa=pessoa,
        )
        encontro = EncontroAntigo.objects.create(
            encontro='Escalada preservada',
            tipo='Escalada',
            data_referencia=date(2030, 1, 1),
            data_exato='1 de janeiro de 2030',
        )
        funcao = FuncaoAntiga.objects.create(
            nome='Equipe legada',
            tipo='equipe',
        )
        self.vinculo_id = VinculoAntigo.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            funcao=funcao,
        ).pk
        self.convite_id = ConviteAntigo.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            finalidade='trabalhar',
        ).pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_forward_preserva_legado_e_cria_estrutura_nova_vazia(self):
        VinculoLegado = self.apps.get_model('core', 'VinculoEncontroLegado')
        ConviteNovo = self.apps.get_model('core', 'ConviteEncontro')
        TemplateEquipe = self.apps.get_model('core', 'TemplateEquipeEncontro')
        TemplateRole = self.apps.get_model('core', 'TemplateRoleEquipe')
        Equipe = self.apps.get_model('core', 'EquipeEncontro')
        Role = self.apps.get_model('core', 'RoleEquipeEncontro')
        Trabalho = self.apps.get_model('core', 'TrabalhoEncontro')

        self.assertTrue(VinculoLegado.objects.filter(pk=self.vinculo_id).exists())
        self.assertIsNone(
            ConviteNovo.objects.get(pk=self.convite_id).role_trabalho_proposta_id
        )
        for model in (TemplateEquipe, TemplateRole, Equipe, Role, Trabalho):
            with self.subTest(model=model.__name__):
                self.assertEqual(model.objects.count(), 0)

        tabelas = connection.introspection.table_names()
        self.assertIn('core_participacaoencontro', tabelas)
        self.assertIn('core_templateequipeencontro', tabelas)
        self.assertIn('core_trabalhoencontro', tabelas)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()
