from datetime import date, time

from django.contrib.auth.models import AnonymousUser, Group, User
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    InscricaoEncontro,
    Pessoa,
    PreEncontro,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoUsuarioPessoa,
)
from core.permissions import (
    pode_aprovar_encaminhamento_encontrista,
    pode_encerrar_preselecao_encontrista,
    pode_preselecionar_encontrista,
)
from core.roles import SiaRole
from core.services.preselecoes_encontristas import (
    encerrar_preselecao_encontrista,
    preselecionar_encontrista,
)
from core.tests.factories import make_encontro


class PreSelecaoEncontristaAuthorizationTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 1, 1),
            horario=time(14),
            local='Local do Pré-Encontro',
        )
        self.inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )

    def _usuario(self, username, *roles):
        usuario = User.objects.create_user(username=username)
        for role in roles:
            grupo, _ = Group.objects.get_or_create(name=role.value)
            usuario.groups.add(grupo)
        return usuario

    def _coordenador_contextual(self):
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=self.encontro.tipo,
            codigo='coordenacao-geral-autorizacao-preselecao',
            nome='Coordenação Geral',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
            concede_registro_presenca=False,
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=template,
            codigo='coordenacao-geral',
            nome='Coordenação Geral',
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo='integrante',
            nome='Integrante',
            concede_registro_presenca=False,
        )
        pessoa = Pessoa.objects.create(nome='Coordenação contextual')
        convite = ConviteEncontro.objects.create(
            encontro=self.encontro,
            pessoa=pessoa,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        TrabalhoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=pessoa,
            convite=convite,
            role_equipe=role,
            status=TrabalhoEncontro.Status.ALOCADO,
        )
        usuario = self._usuario('coordenacao-contextual')
        VinculoUsuarioPessoa.objects.create(usuario=usuario, pessoa=pessoa)
        return usuario

    def test_suporte_diretoria_e_fichas_sao_autorizados(self):
        for role in (SiaRole.SUPORTE, SiaRole.DIRETORIA, SiaRole.FICHAS):
            with self.subTest(role=role):
                usuario = self._usuario(f'usuario-{role.name.lower()}', role)
                self.assertTrue(
                    pode_preselecionar_encontrista(usuario, self.encontro)
                )
                self.assertTrue(
                    pode_encerrar_preselecao_encontrista(
                        usuario,
                        self.encontro,
                    )
                )

    def test_superuser_e_bypass_tecnico(self):
        usuario = User.objects.create_superuser(
            username='superuser-preselecao',
            password='senha-de-teste',
        )

        self.assertTrue(
            pode_preselecionar_encontrista(usuario, self.encontro)
        )
        self.assertTrue(
            pode_encerrar_preselecao_encontrista(usuario, self.encontro)
        )

    def test_comunicacao_sem_papel_e_anonimo_sao_negados(self):
        usuarios = (
            self._usuario('comunicacao-isolada', SiaRole.COMUNICACAO),
            self._usuario('sem-papel'),
            AnonymousUser(),
        )

        for usuario in usuarios:
            with self.subTest(usuario=str(usuario)):
                self.assertFalse(
                    pode_preselecionar_encontrista(usuario, self.encontro)
                )
                self.assertFalse(
                    pode_encerrar_preselecao_encontrista(
                        usuario,
                        self.encontro,
                    )
                )

    def test_coordenacao_geral_apenas_contextual_e_negada(self):
        usuario = self._coordenador_contextual()

        self.assertFalse(
            pode_preselecionar_encontrista(usuario, self.encontro)
        )
        self.assertFalse(
            pode_encerrar_preselecao_encontrista(usuario, self.encontro)
        )

    def test_multiplos_papeis_preservam_uniao_de_permissoes(self):
        permitido = self._usuario(
            'fichas-com-comunicacao',
            SiaRole.COMUNICACAO,
            SiaRole.FICHAS,
        )
        negado = self._usuario(
            'comunicacao-com-formacao',
            SiaRole.COMUNICACAO,
            SiaRole.FORMACAO,
        )

        self.assertTrue(
            pode_preselecionar_encontrista(permitido, self.encontro)
        )
        self.assertFalse(
            pode_preselecionar_encontrista(negado, self.encontro)
        )

    def test_aprovacao_de_encaminhamento_para_fichas_e_suporte(self):
        fichas = self._usuario('fichas-aprova', SiaRole.FICHAS)
        misto = self._usuario(
            'fichas-comunicacao-aprova',
            SiaRole.FICHAS,
            SiaRole.COMUNICACAO,
        )
        negados = (
            self._usuario('diretoria-nao-aprova', SiaRole.DIRETORIA),
            self._usuario('comunicacao-nao-aprova', SiaRole.COMUNICACAO),
            self._usuario('sem-papel-nao-aprova'),
            self._coordenador_contextual(),
            AnonymousUser(),
        )

        self.assertTrue(
            pode_aprovar_encaminhamento_encontrista(fichas, self.encontro)
        )
        self.assertTrue(pode_aprovar_encaminhamento_encontrista(
            self._usuario('suporte-aprova', SiaRole.SUPORTE), self.encontro,
        ))
        self.assertTrue(
            pode_aprovar_encaminhamento_encontrista(misto, self.encontro)
        )
        for usuario in negados:
            with self.subTest(usuario=str(usuario)):
                self.assertFalse(
                    pode_aprovar_encaminhamento_encontrista(
                        usuario,
                        self.encontro,
                    )
                )

        fichas.is_active = False
        fichas.save(update_fields=['is_active'])
        self.assertFalse(
            pode_aprovar_encaminhamento_encontrista(fichas, self.encontro)
        )

    def test_superuser_pode_aprovar_encaminhamento(self):
        usuario = User.objects.create_superuser(
            username='superuser-aprova-encaminhamento',
            password='senha-de-teste',
        )

        self.assertTrue(
            pode_aprovar_encaminhamento_encontrista(usuario, self.encontro)
        )

    def test_policy_exige_encontro_persistido(self):
        usuario = self._usuario('fichas-sem-escopo', SiaRole.FICHAS)

        self.assertFalse(pode_preselecionar_encontrista(usuario, None))
        self.assertFalse(
            pode_preselecionar_encontrista(usuario, Encontro())
        )

    def test_policy_respeita_lifecycle_encerrado(self):
        usuario = self._usuario('fichas-lifecycle', SiaRole.FICHAS)
        self.encontro.status = Encontro.Status.FINALIZADO

        self.assertFalse(
            pode_preselecionar_encontrista(usuario, self.encontro)
        )
        self.assertFalse(
            pode_encerrar_preselecao_encontrista(usuario, self.encontro)
        )

    def test_service_aplica_autorizacao_de_criacao_e_encerramento(self):
        fichas = self._usuario('fichas-service', SiaRole.FICHAS)
        negado = self._usuario('comunicacao-service', SiaRole.COMUNICACAO)
        preselecao = preselecionar_encontrista(
            usuario=fichas,
            encontro=self.encontro,
            origem_tipo='inscricao',
            inscricao=self.inscricao,
        )

        with self.assertRaises(PermissionDenied):
            preselecionar_encontrista(
                usuario=negado,
                encontro=self.encontro,
                origem_tipo='inscricao',
                inscricao=self.inscricao,
            )
        with self.assertRaises(PermissionDenied):
            encerrar_preselecao_encontrista(
                usuario=negado,
                encontro=self.encontro,
                preselecao=preselecao,
            )
