from datetime import date, time
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Frequencia,
    Pessoa,
    PresencaPreparatoria,
    ReuniaoPreparatoriaEncontro,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.services.reunioes_preparatorias import (
    anotar_revisao_permanencia,
    corrigir_presenca_preparatoria,
    criar_reuniao_preparatoria,
    editar_reuniao_preparatoria,
    registrar_presenca_preparatoria,
    trabalho_requer_revisao,
)
from core.tests.factories import make_encontro


class EncounterPreparationTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.usuario = User.objects.create_user(
            username='registrador-presenca',
            password='senha-de-teste',
        )
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='coordenacao-geral',
            nome='Coordenação Geral',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=template,
            codigo=template.codigo,
            nome=template.nome,
        )
        self.role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo=template_role.codigo,
            nome=template_role.nome,
        )
        self.trabalho = self._criar_trabalho('Pessoa trabalhadora')

    def _criar_trabalho(self, nome, *, encontro=None):
        encontro = encontro or self.encontro
        pessoa = Pessoa.objects.create(nome=nome)
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        valores = {
            'pessoa': pessoa,
            'encontro': encontro,
            'convite': convite,
        }
        if encontro == self.encontro:
            valores.update(
                role_equipe=self.role,
                status=TrabalhoEncontro.Status.ALOCADO,
            )
        return TrabalhoEncontro.objects.create(**valores)

    def _criar_reuniao(self, ordem=1, *, encontro=None):
        return criar_reuniao_preparatoria(
            encontro=encontro or self.encontro,
            ordem=ordem,
            data=date(2030, 2, max(ordem, 1)),
            horario=time(19, 30),
            local=f'Local {ordem}',
            observacoes=f'Observação {ordem}',
        )

    def _registrar(
        self,
        reuniao,
        status=PresencaPreparatoria.Status.PRESENTE,
        *,
        trabalho=None,
        justificativa='',
    ):
        return registrar_presenca_preparatoria(
            reuniao=reuniao,
            trabalho=trabalho or self.trabalho,
            status=status,
            justificativa=justificativa,
            registrada_por=self.usuario,
        )

    def test_cria_multiplas_reunioes_ordenadas_e_edita(self):
        segunda = self._criar_reuniao(2)
        primeira = self._criar_reuniao(1)

        self.assertEqual(
            list(
                self.encontro.reunioes_preparatorias.values_list(
                    'ordem', flat=True
                )
            ),
            [1, 2],
        )

        editada = editar_reuniao_preparatoria(
            segunda,
            ordem=3,
            local='Novo local',
            observacoes='',
        )
        self.assertEqual(editada.ordem, 3)
        self.assertEqual(editada.local, 'Novo local')
        self.assertEqual(editada.observacoes, '')
        self.assertEqual(primeira.ordem, 1)

    def test_edicao_de_agenda_preserva_presenca_existente(self):
        reuniao = self._criar_reuniao()
        presenca = self._registrar(reuniao)

        editar_reuniao_preparatoria(
            reuniao,
            complemento='Missa de Entrega',
        )

        presenca.refresh_from_db()
        reuniao.refresh_from_db()
        self.assertEqual(presenca.reuniao_id, reuniao.pk)
        self.assertEqual(reuniao.complemento, 'Missa de Entrega')

    def test_mesma_ordem_em_encontros_diferentes_e_permitida(self):
        outro_encontro = make_encontro(tipo=Encontro.Tipo.AVC)

        primeira = self._criar_reuniao(1)
        outra = self._criar_reuniao(1, encontro=outro_encontro)

        self.assertEqual(primeira.ordem, outra.ordem)
        self.assertNotEqual(primeira.encontro_id, outra.encontro_id)

    def test_ordem_deve_ser_positiva_e_unica_no_encontro(self):
        self._criar_reuniao(1)

        with self.assertRaisesMessage(ValidationError, 'Já existe reunião'):
            self._criar_reuniao(1)
        with self.assertRaisesMessage(ValidationError, 'deve ser positiva'):
            self._criar_reuniao(0)

        with self.assertRaises(IntegrityError), transaction.atomic():
            ReuniaoPreparatoriaEncontro.objects.create(
                encontro=self.encontro,
                ordem=0,
                data=date(2030, 2, 1),
                horario=time(19),
                local='Inválido',
            )

    def test_conflito_ao_editar_ordem_preserva_reuniao_original(self):
        primeira = self._criar_reuniao(1)
        segunda = self._criar_reuniao(2)

        with self.assertRaisesMessage(ValidationError, 'Já existe reunião'):
            editar_reuniao_preparatoria(segunda, ordem=primeira.ordem)

        segunda.refresh_from_db()
        self.assertEqual(segunda.ordem, 2)

    def test_registra_todos_os_estados_e_justificativa_opcional(self):
        casos = (
            (PresencaPreparatoria.Status.PRESENTE, ''),
            (
                PresencaPreparatoria.Status.AUSENTE_JUSTIFICADO,
                'Compromisso profissional',
            ),
            (PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA, ''),
        )

        for ordem, (status, justificativa) in enumerate(casos, start=1):
            with self.subTest(status=status):
                presenca = self._registrar(
                    self._criar_reuniao(ordem),
                    status,
                    justificativa=justificativa,
                )
                self.assertEqual(presenca.status, status)
                self.assertEqual(presenca.justificativa, justificativa)
                self.assertEqual(presenca.registrada_por, self.usuario)

    def test_presenca_e_unica_e_registro_identico_e_idempotente(self):
        reuniao = self._criar_reuniao()
        primeira = self._registrar(reuniao)
        repetida = self._registrar(reuniao)

        self.assertEqual(repetida.pk, primeira.pk)
        self.assertEqual(PresencaPreparatoria.objects.count(), 1)

        with self.assertRaisesMessage(ValidationError, 'use a operação de correção'):
            self._registrar(
                reuniao,
                PresencaPreparatoria.Status.AUSENTE_JUSTIFICADO,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            PresencaPreparatoria.objects.create(
                reuniao=reuniao,
                trabalho=self.trabalho,
                status=PresencaPreparatoria.Status.PRESENTE,
                registrada_por=self.usuario,
            )

    def test_status_invalido_e_rejeitado_pelo_service_e_banco(self):
        reuniao = self._criar_reuniao()
        with self.assertRaisesMessage(ValidationError, 'Status de presença inválido'):
            self._registrar(reuniao, 'invalido')

        with self.assertRaises(IntegrityError), transaction.atomic():
            PresencaPreparatoria.objects.create(
                reuniao=reuniao,
                trabalho=self.trabalho,
                status='invalido',
                registrada_por=self.usuario,
            )

    def test_rejeita_trabalho_de_outro_encontro(self):
        outro_encontro = make_encontro(tipo=Encontro.Tipo.AVC)
        outro_trabalho = self._criar_trabalho(
            'Pessoa de outro Encontro',
            encontro=outro_encontro,
        )

        with self.assertRaisesMessage(ValidationError, 'mesmo Encontro'):
            self._registrar(
                self._criar_reuniao(),
                trabalho=outro_trabalho,
            )

        self.assertFalse(PresencaPreparatoria.objects.exists())

    def test_correcao_recalcula_revisao_pelo_conjunto_atual(self):
        primeira = self._registrar(
            self._criar_reuniao(1),
            PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA,
        )
        segunda = self._registrar(
            self._criar_reuniao(2),
            PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA,
        )
        self.assertTrue(trabalho_requer_revisao(self.trabalho))
        self.assertTrue(
            anotar_revisao_permanencia().get(pk=self.trabalho.pk).requer_revisao
        )

        corrigir_presenca_preparatoria(
            primeira,
            status=PresencaPreparatoria.Status.AUSENTE_JUSTIFICADO,
            justificativa='Justificativa aceita',
            registrada_por=self.usuario,
        )
        self.assertTrue(trabalho_requer_revisao(self.trabalho))

        corrigida = corrigir_presenca_preparatoria(
            segunda,
            status=PresencaPreparatoria.Status.PRESENTE,
            registrada_por=self.usuario,
        )
        repetida = corrigir_presenca_preparatoria(
            corrigida,
            status=PresencaPreparatoria.Status.PRESENTE,
            registrada_por=self.usuario,
        )
        self.assertEqual(repetida.pk, corrigida.pk)
        self.assertFalse(trabalho_requer_revisao(self.trabalho))

    def test_ausencia_nao_retira_trabalhador_nem_cria_frequencia(self):
        role_original = self.trabalho.role_equipe
        self._registrar(
            self._criar_reuniao(),
            PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA,
        )

        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, TrabalhoEncontro.Status.ALOCADO)
        self.assertEqual(self.trabalho.role_equipe, role_original)
        self.assertTrue(trabalho_requer_revisao(self.trabalho))
        self.assertFalse(Frequencia.objects.exists())

    def test_correcao_faz_rollback_em_erro_de_persistencia(self):
        presenca = self._registrar(
            self._criar_reuniao(),
            PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA,
        )

        with patch.object(
            PresencaPreparatoria,
            'save',
            side_effect=RuntimeError('falha intermediária'),
        ):
            with self.assertRaisesMessage(RuntimeError, 'falha intermediária'):
                corrigir_presenca_preparatoria(
                    presenca,
                    status=PresencaPreparatoria.Status.PRESENTE,
                    registrada_por=self.usuario,
                )

        presenca.refresh_from_db()
        self.assertEqual(
            presenca.status,
            PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA,
        )
        self.assertTrue(trabalho_requer_revisao(self.trabalho))

    def test_fks_historicas_usam_protect(self):
        reuniao = self._criar_reuniao()
        presenca = self._registrar(reuniao)

        for protegido in (reuniao, self.trabalho, self.usuario):
            with self.subTest(protegido=protegido):
                with self.assertRaises(ProtectedError):
                    protegido.delete()
        self.assertTrue(PresencaPreparatoria.objects.filter(pk=presenca.pk).exists())


class EncounterPreparationMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0030_expand_equipes_trabalho_encontro')
    migrate_to = (
        'core',
        '0031_expand_reunioes_presencas_preparatorias',
    )

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps

        PessoaAntiga = old_apps.get_model('core', 'Pessoa')
        EncontroAntigo = old_apps.get_model('core', 'Encontro')
        ConviteAntigo = old_apps.get_model('core', 'ConviteEncontro')
        TrabalhoAntigo = old_apps.get_model('core', 'TrabalhoEncontro')

        pessoa = PessoaAntiga.objects.create(nome='Pessoa preservada D.3D')
        encontro = EncontroAntigo.objects.create(
            encontro='Encontro preservado D.3D',
            tipo='Escalada',
            data_referencia=date(2030, 1, 1),
            data_exato='1 de janeiro de 2030',
        )
        convite = ConviteAntigo.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            finalidade='trabalhar',
            status='confirmado',
        )
        self.trabalho_id = TrabalhoAntigo.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            convite=convite,
        ).pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_forward_preserva_trabalho_e_cria_tabelas_novas_vazias(self):
        Trabalho = self.apps.get_model('core', 'TrabalhoEncontro')
        Reuniao = self.apps.get_model('core', 'ReuniaoPreparatoriaEncontro')
        Presenca = self.apps.get_model('core', 'PresencaPreparatoria')

        self.assertTrue(Trabalho.objects.filter(pk=self.trabalho_id).exists())
        self.assertEqual(Reuniao.objects.count(), 0)
        self.assertEqual(Presenca.objects.count(), 0)

        tabelas = connection.introspection.table_names()
        self.assertIn('core_reuniaopreparatoriaencontro', tabelas)
        self.assertIn('core_presencapreparatoria', tabelas)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()
