from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from core.models import (
    ConviteEncontro, EquipeEncontro, LogSistema, Pessoa, RoleEquipeEncontro,
    TemplateEquipeEncontro, TemplateRoleEquipe, TrabalhoEncontro,
    VinculoUsuarioPessoa,
)
from core.permissions import pertence_coordenacao_geral_encontro
from core.roles import SiaRole
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_encontro_canonico


class WorkActionPermissionsTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.encontro = make_encontro_canonico()
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=self.encontro.tipo, codigo='cg', nome='Coordenação',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template, codigo='membro', nome='Membro',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro, template_origem=template,
            codigo='coordenacao-geral', nome='Coordenação',
        )
        self.a = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe, template_origem=template_role,
            codigo='a', nome='A', quantidade_estrutural=20,
        )
        self.b = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe, template_origem=template_role,
            codigo='b', nome='B', quantidade_estrutural=20,
        )

    def trabalho(self, nome, role=None):
        pessoa = Pessoa.objects.create(nome=nome)
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa, encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        return TrabalhoEncontro.objects.create(
            pessoa=pessoa, encontro=self.encontro, convite=convite,
            role_equipe=role, status=(TrabalhoEncontro.Status.ALOCADO if role else TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO),
        )

    def usuario(self, nome, role=None):
        user = get_user_model().objects.create_user(username=nome)
        if role:
            group, _ = Group.objects.get_or_create(name=role.value)
            user.groups.add(group)
        return user

    def post(self, trabalho, action):
        body = {} if action == 'desalocar' else {'role_equipe_id': self.b.pk, 'confirmar_avisos': True}
        return self.client.post(f'/api/trabalhos-encontros/{trabalho.pk}/{action}/', body, format='json')

    def test_gestores_podem_executar_cada_acao(self):
        for role in (SiaRole.FICHAS, SiaRole.DIRETORIA, SiaRole.SUPORTE):
            user = self.usuario(role.value, role)
            for action in ('alocar', 'realocar', 'desalocar'):
                with self.subTest(role=role, action=action):
                    trabalho = self.trabalho(f'{role.value}-{action}', None if action == 'alocar' else self.a)
                    self.client.force_authenticate(user)
                    response = self.post(trabalho, action)
                    self.assertEqual(response.status_code, 200, response.data)
                    trabalho.refresh_from_db()
                    self.assertEqual(trabalho.role_equipe_id, None if action == 'desalocar' else self.b.pk)
                    self.assertEqual(trabalho.status, TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO if action == 'desalocar' else TrabalhoEncontro.Status.ALOCADO)

    def test_negados_nao_alteram_trabalho_ocupacao_ou_auditoria(self):
        coord = self.trabalho('Coordenador', self.a)
        coord_user = self.usuario('coordenador')
        VinculoUsuarioPessoa.objects.create(usuario=coord_user, pessoa=coord.pessoa)
        self.assertTrue(pertence_coordenacao_geral_encontro(coord_user, self.encontro))
        users = [coord_user, self.usuario('sem-role'), None]
        users += [self.usuario(f'negado-{role.name}', role) for role in SiaRole if role not in (SiaRole.FICHAS, SiaRole.DIRETORIA, SiaRole.SUPORTE)]
        for user in users:
            for action in ('alocar', 'realocar', 'desalocar'):
                with self.subTest(user=str(user), action=action):
                    trabalho = self.trabalho(f'alvo-{len(users)}-{user}-{action}', None if action == 'alocar' else self.a)
                    before = (trabalho.status, trabalho.role_equipe_id)
                    occupancy = list(TrabalhoEncontro.objects.filter(role_equipe__in=[self.a, self.b], status=TrabalhoEncontro.Status.ALOCADO).order_by('pk').values_list('pk', 'role_equipe_id'))
                    logs = LogSistema.objects.filter(modulo='TrabalhoEncontro').count()
                    self.client.force_authenticate(user)
                    response = self.post(trabalho, action)
                    self.assertEqual(response.status_code, 401 if user is None else 403)
                    trabalho.refresh_from_db()
                    self.assertEqual((trabalho.status, trabalho.role_equipe_id), before)
                    self.assertEqual(list(TrabalhoEncontro.objects.filter(role_equipe__in=[self.a, self.b], status=TrabalhoEncontro.Status.ALOCADO).order_by('pk').values_list('pk', 'role_equipe_id')), occupancy)
                    self.assertEqual(LogSistema.objects.filter(modulo='TrabalhoEncontro').count(), logs)
