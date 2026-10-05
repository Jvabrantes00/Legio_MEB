from datetime import date, time
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    LogSistema,
    Pessoa,
    PresencaPreparatoria,
    ReuniaoPreparatoriaEncontro,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoUsuarioPessoa,
)
from core.permissions import pode_registrar_presenca_preparatoria
from core.roles import SiaRole
from core.services import reunioes_preparatorias as reuniao_services
from core.tests.factories import make_alpinista, make_encontro


class EncounterContextualAuthorizationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.client.raise_request_exception = False
        self.encontro = make_encontro(
            tipo=Encontro.Tipo.ESCALADA,
            status=Encontro.Status.EM_PREPARACAO,
        )
        self.template_coordenacao = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='coordenacao-geral',
            nome='Coordenação Geral',
        )
        self.template_role_autorizada = TemplateRoleEquipe.objects.create(
            template_equipe=self.template_coordenacao,
            codigo='adulto-geral',
            nome='Adulto Geral',
            concede_registro_presenca=True,
        )
        self.template_role_comum = TemplateRoleEquipe.objects.create(
            template_equipe=self.template_coordenacao,
            codigo='integrante',
            nome='Integrante',
            concede_registro_presenca=False,
        )
        self.equipe_coordenacao = self._criar_equipe(
            self.encontro,
            self.template_coordenacao,
        )
        self.role_autorizada = self._criar_role(
            self.equipe_coordenacao,
            self.template_role_autorizada,
        )
        self.role_comum = self._criar_role(
            self.equipe_coordenacao,
            self.template_role_comum,
        )

        template_outra = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='vigilia',
            nome='Vigília',
        )
        template_role_outra = TemplateRoleEquipe.objects.create(
            template_equipe=template_outra,
            codigo='coordenador',
            nome='Coordenador',
            concede_registro_presenca=False,
        )
        equipe_outra = self._criar_equipe(self.encontro, template_outra)
        self.role_outra_equipe = self._criar_role(
            equipe_outra,
            template_role_outra,
        )

        self.trabalho_alvo = self._criar_trabalho(
            'Pessoa cuja presença será registrada',
            self.encontro,
            self.role_comum,
        )
        self.reuniao = self._criar_reuniao(self.encontro, ordem=1)

    def _criar_equipe(self, encontro, template):
        return EquipeEncontro.objects.create(
            encontro=encontro,
            template_origem=template,
            codigo=template.codigo,
            nome=template.nome,
        )

    def _criar_role(self, equipe, template_role):
        return RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo=template_role.codigo,
            nome=template_role.nome,
            concede_registro_presenca=(
                template_role.concede_registro_presenca
            ),
        )

    def _criar_trabalho(self, nome, encontro, role):
        pessoa = Pessoa.objects.create(nome=nome)
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        return TrabalhoEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            convite=convite,
            role_equipe=role,
            status=TrabalhoEncontro.Status.ALOCADO,
        )

    def _criar_reuniao(self, encontro, ordem):
        return ReuniaoPreparatoriaEncontro.objects.create(
            encontro=encontro,
            ordem=ordem,
            data=date(2030, 3, ordem),
            horario=time(19, 30),
            local=f'Local {ordem}',
        )

    def _criar_usuario_contextual(
        self,
        username,
        *,
        encontro=None,
        role=None,
        ativo=True,
    ):
        encontro = encontro or self.encontro
        role = role or self.role_autorizada
        trabalho = self._criar_trabalho(
            f'Pessoa de {username}',
            encontro,
            role,
        )
        usuario = User.objects.create_user(
            username=username,
            password='senha-de-teste',
            is_active=ativo,
        )
        VinculoUsuarioPessoa.objects.create(
            usuario=usuario,
            pessoa=trabalho.pessoa,
        )
        return usuario, trabalho

    def _criar_usuario_com_role(self, username, role):
        usuario = User.objects.create_user(
            username=username,
            password='senha-de-teste',
        )
        grupo, _ = Group.objects.get_or_create(name=role.value)
        usuario.groups.add(grupo)
        return usuario

    def _payload(self, reuniao=None):
        return {
            'reuniao_id': (reuniao or self.reuniao).pk,
            'trabalho_id': self.trabalho_alvo.pk,
            'status': PresencaPreparatoria.Status.PRESENTE,
            'justificativa': '',
        }

    def _registrar(self, usuario, *, reuniao=None):
        self.client.force_authenticate(user=usuario)
        return self.client.post(
            reverse('presenca-preparatoria-list'),
            self._payload(reuniao),
            format='json',
        )

    def test_fichas_diretoria_e_suporte_preservam_acesso_administrativo(self):
        for ordem, role in enumerate(
            (SiaRole.FICHAS, SiaRole.DIRETORIA, SiaRole.SUPORTE),
            start=2,
        ):
            with self.subTest(role=role.value):
                usuario = self._criar_usuario_com_role(
                    f'administrador-{ordem}',
                    role,
                )
                reuniao = self._criar_reuniao(self.encontro, ordem)

                response = self._registrar(usuario, reuniao=reuniao)

                self.assertEqual(response.status_code, status.HTTP_201_CREATED)
                self.assertTrue(
                    PresencaPreparatoria.objects.filter(
                        reuniao=reuniao,
                        registrada_por=usuario,
                    ).exists()
                )

    def test_coordenacao_apropriada_registra_e_audita_usando_service(self):
        usuario, _ = self._criar_usuario_contextual('coordenacao-apropriada')

        with patch(
            'core.serializers.reuniao_services.registrar_presenca_preparatoria',
            wraps=reuniao_services.registrar_presenca_preparatoria,
        ) as service:
            response = self._registrar(usuario)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(
            set(response.data),
            {
                'id',
                'reuniao_id',
                'trabalho_id',
                'status',
                'justificativa',
                'registrada_por_id',
                'criado_em',
                'atualizado_em',
            },
        )
        service.assert_called_once()
        presenca = PresencaPreparatoria.objects.get()
        self.assertEqual(presenca.registrada_por, usuario)
        self.assertTrue(pode_registrar_presenca_preparatoria(usuario, self.encontro))
        self.assertTrue(
            LogSistema.objects.filter(
                usuario=usuario,
                modulo='PresencaPreparatoria',
                acao='CREATE',
            ).exists()
        )

    def test_correcao_autorizada_reutiliza_service_e_preserva_auditoria(self):
        usuario, _ = self._criar_usuario_contextual('coordenacao-corrige')
        response = self._registrar(usuario)
        presenca = PresencaPreparatoria.objects.get(pk=response.data['id'])

        with patch(
            'core.views.corrigir_presenca_preparatoria',
            wraps=reuniao_services.corrigir_presenca_preparatoria,
        ) as service:
            response = self.client.patch(
                reverse('presenca-preparatoria-corrigir', args=[presenca.pk]),
                {
                    'status': (
                        PresencaPreparatoria.Status.AUSENTE_JUSTIFICADO
                    ),
                    'justificativa': 'Justificativa aceita',
                },
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        service.assert_called_once()
        presenca.refresh_from_db()
        self.assertEqual(
            presenca.status,
            PresencaPreparatoria.Status.AUSENTE_JUSTIFICADO,
        )
        self.assertEqual(presenca.registrada_por, usuario)
        self.assertTrue(
            LogSistema.objects.filter(
                usuario=usuario,
                modulo='PresencaPreparatoria',
                acao='UPDATE',
            ).exists()
        )

    def test_coordenador_de_outra_equipe_e_integrante_comum_sao_negados(self):
        casos = (
            ('outra-equipe', self.role_outra_equipe),
            ('integrante-comum', self.role_comum),
        )
        for username, role in casos:
            with self.subTest(username=username):
                usuario, _ = self._criar_usuario_contextual(
                    username,
                    role=role,
                )

                response = self._registrar(usuario)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(PresencaPreparatoria.objects.exists())

    def test_coordenacao_de_outro_encontro_e_negada(self):
        outro_encontro = make_encontro(
            tipo=Encontro.Tipo.ESCALADA,
            status=Encontro.Status.EM_PREPARACAO,
        )
        equipe = self._criar_equipe(
            outro_encontro,
            self.template_coordenacao,
        )
        role = self._criar_role(equipe, self.template_role_autorizada)
        usuario, _ = self._criar_usuario_contextual(
            'coordenacao-outro-encontro',
            encontro=outro_encontro,
            role=role,
        )

        response = self._registrar(usuario)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(PresencaPreparatoria.objects.exists())

    def test_usuario_sem_vinculo_explicito_e_negado_sem_inferencia(self):
        usuario = User.objects.create_user(
            username=self.trabalho_alvo.pessoa.nome,
            email=self.trabalho_alvo.pessoa.email or 'igual@example.test',
            password='senha-de-teste',
        )

        response = self._registrar(usuario)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(PresencaPreparatoria.objects.exists())
        self.assertFalse(VinculoUsuarioPessoa.objects.filter(usuario=usuario).exists())

    def test_usuario_inativo_e_negado(self):
        usuario, _ = self._criar_usuario_contextual(
            'coordenacao-inativa',
            ativo=False,
        )

        response = self._registrar(usuario)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(PresencaPreparatoria.objects.exists())

    def test_finalizado_e_cancelado_encerram_somente_acesso_contextual(self):
        usuario, _ = self._criar_usuario_contextual('coordenacao-lifecycle')
        for encontro_status in (
            Encontro.Status.FINALIZADO,
            Encontro.Status.CANCELADO,
        ):
            with self.subTest(status=encontro_status):
                self.encontro.status = encontro_status
                self.encontro.save(update_fields=['status'])

                response = self._registrar(usuario)

                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(PresencaPreparatoria.objects.exists())

        suporte = self._criar_usuario_com_role('suporte-finalizado', SiaRole.SUPORTE)
        response = self._registrar(suporte)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_estado_operacional_valido_e_trabalho_alocado_sao_exigidos(self):
        usuario, trabalho = self._criar_usuario_contextual('coordenacao-valida')
        self.assertTrue(pode_registrar_presenca_preparatoria(usuario, self.encontro))

        trabalho.status = TrabalhoEncontro.Status.RETIRADO
        trabalho.save(update_fields=['status'])

        response = self._registrar(usuario)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertFalse(PresencaPreparatoria.objects.exists())

    def test_tentativa_nao_autorizada_nao_altera_presenca(self):
        autorizado, _ = self._criar_usuario_contextual('coordenacao-original')
        response = self._registrar(autorizado)
        presenca = PresencaPreparatoria.objects.get(pk=response.data['id'])
        sem_vinculo = User.objects.create_user(
            username='sem-vinculo-correcao',
            password='senha-de-teste',
        )
        self.client.force_authenticate(user=sem_vinculo)

        response = self.client.patch(
            reverse('presenca-preparatoria-corrigir', args=[presenca.pk]),
            {
                'status': PresencaPreparatoria.Status.AUSENTE_SEM_JUSTIFICATIVA,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        presenca.refresh_from_db()
        self.assertEqual(presenca.status, PresencaPreparatoria.Status.PRESENTE)
        self.assertEqual(presenca.registrada_por, autorizado)
        self.assertEqual(
            LogSistema.objects.filter(
                modulo='PresencaPreparatoria',
                acao='UPDATE',
            ).count(),
            0,
        )

    def test_capability_nao_concede_acesso_global_ou_a_saude(self):
        usuario, _ = self._criar_usuario_contextual('coordenacao-escopo')
        alpinista = make_alpinista()
        self.client.force_authenticate(user=usuario)

        detalhe = self.client.get(reverse('alpinista-detail', args=[alpinista.pk]))
        criar_encontro = self.client.post(
            reverse('encontro-list'),
            {'encontro': 'Não autorizado'},
            format='json',
        )

        self.assertEqual(detalhe.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(criar_encontro.status_code, status.HTTP_403_FORBIDDEN)

    def test_fluxo_nao_cria_nem_remove_user_automaticamente(self):
        usuario, _ = self._criar_usuario_contextual('coordenacao-preservada')
        total_usuarios = User.objects.count()

        response = self._registrar(usuario)
        self.encontro.status = Encontro.Status.FINALIZADO
        self.encontro.save(update_fields=['status'])

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(pode_registrar_presenca_preparatoria(usuario, self.encontro))
        self.assertEqual(User.objects.count(), total_usuarios)
        self.assertTrue(User.objects.filter(pk=usuario.pk).exists())

    def test_falha_de_auditoria_reverte_registro_de_presenca(self):
        usuario, _ = self._criar_usuario_contextual('coordenacao-rollback')
        self.client.force_authenticate(user=usuario)

        with patch(
            'core.views.LogSistema.objects.create',
            side_effect=RuntimeError('falha de auditoria'),
        ):
            response = self.client.post(
                reverse('presenca-preparatoria-list'),
                self._payload(),
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
        self.assertFalse(PresencaPreparatoria.objects.exists())


class UserPersonLinkFoundationTests(TestCase):
    def test_vinculo_e_explicito_unico_e_protegido(self):
        usuario = User.objects.create_user(username='usuario-vinculado')
        pessoa = Pessoa.objects.create(nome='Pessoa vinculada')
        vinculo = VinculoUsuarioPessoa.objects.create(
            usuario=usuario,
            pessoa=pessoa,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoUsuarioPessoa.objects.create(
                usuario=usuario,
                pessoa=Pessoa.objects.create(nome='Outra Pessoa'),
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoUsuarioPessoa.objects.create(
                usuario=User.objects.create_user(username='outro-usuario'),
                pessoa=pessoa,
            )
        for protegido in (usuario, pessoa):
            with self.subTest(protegido=protegido):
                with self.assertRaises(ProtectedError):
                    protegido.delete()
        self.assertTrue(VinculoUsuarioPessoa.objects.filter(pk=vinculo.pk).exists())


class UserPersonLinkMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0031_expand_reunioes_presencas_preparatorias')
    migrate_to = ('core', '0032_vinculousuariopessoa')

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        UsuarioAntigo = old_apps.get_model('auth', 'User')
        PessoaAntiga = old_apps.get_model('core', 'Pessoa')
        self.usuario_id = UsuarioAntigo.objects.create(
            username='usuario-preservado-d3e',
        ).pk
        self.pessoa_id = PessoaAntiga.objects.create(
            nome='Pessoa preservada D.3E',
        ).pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_forward_preserva_dados_e_cria_vinculo_vazio(self):
        Usuario = self.apps.get_model('auth', 'User')
        PessoaNova = self.apps.get_model('core', 'Pessoa')
        Vinculo = self.apps.get_model('core', 'VinculoUsuarioPessoa')

        self.assertTrue(Usuario.objects.filter(pk=self.usuario_id).exists())
        self.assertTrue(PessoaNova.objects.filter(pk=self.pessoa_id).exists())
        self.assertEqual(Vinculo.objects.count(), 0)
        self.assertIn(
            'core_vinculousuariopessoa',
            connection.introspection.table_names(),
        )

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()
