from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    ConviteEncontro, EquipeEncontro, Pessoa, RoleEquipeEncontro,
    TemplateEquipeEncontro, TemplateRoleEquipe, TrabalhoEncontro,
    VinculoUsuarioPessoa,
)
from core.roles import SiaRole
from core.serializers import EquipeEncontroSerializer
from core.tests.factories import make_encontro


class WorkspaceEquipesApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.encontro = make_encontro()
        self.url = f'/api/encontros/{self.encontro.pk}/workspace/equipes/'
        self.gestor = User.objects.create_user('gestor')
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.gestor.groups.add(grupo)
        self.outro = User.objects.create_user('outro')

    def equipe(self):
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=self.encontro.tipo, codigo='cg', nome='Coordenação',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template, codigo='integrante', nome='Integrante',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro, template_origem=template,
            codigo='coordenacao-geral', nome='Coordenação',
            capacidade_minima_recomendada=5,
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe, template_origem=template_role,
            codigo='integrante', nome='Integrante', quantidade_estrutural=5,
        )
        return equipe, role

    def trabalho(self, nome, status, role):
        pessoa = Pessoa.objects.create(nome=nome)
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa, encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        return TrabalhoEncontro.objects.create(
            pessoa=pessoa, encontro=self.encontro, convite=convite,
            role_equipe=role, status=status,
            resultado_registrado_em=(
                timezone.now() if status in (
                    TrabalhoEncontro.Status.TRABALHOU,
                    TrabalhoEncontro.Status.FALTOU,
                ) else None
            ),
        )

    def test_autenticacao_permissao_e_encontro_inexistente(self):
        self.assertEqual(self.client.get(self.url).status_code, 401)
        self.client.force_authenticate(self.outro)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.force_authenticate(self.gestor)
        self.assertEqual(self.client.get('/api/encontros/999999/workspace/equipes/').status_code, 404)

    def test_lista_vazia_e_somente_leitura(self):
        self.client.force_authenticate(self.gestor)
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data, [])
        self.assertEqual(self.client.post(self.url, {}, format='json').status_code, 405)
        self.assertFalse(EquipeEncontro.objects.exists())

    def test_gestor_recebe_serializer_completo_em_lista(self):
        equipe, role = self.equipe()
        retirado = self.trabalho('Pessoa retirada', TrabalhoEncontro.Status.RETIRADO, role)
        self.client.force_authenticate(self.gestor)
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertIsInstance(resposta.data, list)
        self.assertEqual(resposta.data, EquipeEncontroSerializer([equipe], many=True).data)
        self.assertEqual(resposta.data[0]['roles'][0]['trabalhos'][0]['id'], retirado.pk)

    def test_coordenacao_ve_apenas_estados_permitidos_sem_vazamento_indireto(self):
        equipe, role = self.equipe()
        coordenador = self.trabalho('Coordenador', TrabalhoEncontro.Status.ALOCADO, role)
        self.trabalho('Trabalhou', TrabalhoEncontro.Status.TRABALHOU, role)
        self.trabalho('Faltou', TrabalhoEncontro.Status.FALTOU, role)
        usuario = User.objects.create_user('coordenador')
        VinculoUsuarioPessoa.objects.create(usuario=usuario, pessoa=coordenador.pessoa)
        self.client.force_authenticate(usuario)
        antes = self.client.get(self.url)
        self.assertEqual(antes.status_code, 200)
        aguardando = self.trabalho('Oculto aguardando', TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO, None)
        retirado = self.trabalho('Oculto retirado', TrabalhoEncontro.Status.RETIRADO, role)
        depois = self.client.get(self.url)
        self.assertEqual(depois.data, antes.data)
        trabalhos = depois.data[0]['roles'][0]['trabalhos']
        self.assertEqual({item['status'] for item in trabalhos}, {'alocado', 'trabalhou', 'faltou'})
        self.assertNotIn(aguardando.pk, [item['id'] for item in trabalhos])
        self.assertNotIn(retirado.pk, [item['id'] for item in trabalhos])
        outro = make_encontro()
        self.assertEqual(self.client.get(f'/api/encontros/{outro.pk}/workspace/equipes/').status_code, 403)
