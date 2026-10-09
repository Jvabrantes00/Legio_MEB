from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils import timezone
from rest_framework import status

from core.models import (
    CorrespondenciaCadastralInscricao,
    DadosDeclaradosInscricao,
    InscricaoEncontro,
    Pessoa,
)
from core.roles import SiaRole
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_encontro


class ResolucaoCadastralApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.encontro = make_encontro()
        self.inscricao = self.criar_inscricao()
        self.base_url = f'/api/resolucoes-inscricoes/{self.inscricao.pk}/'

    def autenticar(self, role=None, indice='principal'):
        usuario = get_user_model().objects.create_user(
            username=f'usuario-{indice}',
            password='senha-exclusiva-de-teste',
        )
        if role is not None:
            grupo, _ = Group.objects.get_or_create(name=role.value)
            usuario.groups.add(grupo)
        self.client.force_authenticate(usuario)
        return usuario

    def criar_inscricao(self, **overrides):
        inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            origem=InscricaoEncontro.Origem.PUBLICA,
        )
        dados = {
            'inscricao': inscricao,
            'nome_completo': 'Pessoa API Declarada',
            'data_nascimento': date(2000, 1, 1),
            'cpf': '52998224725',
            'email': 'declarada-api@example.test',
            'telefone_whatsapp': '61999990000',
            'cep': '70000-000',
            'logradouro': 'Rua API',
            'numero': '10',
            'bairro': 'Bairro API',
            'cidade': 'Brasília',
            'uf': 'DF',
            'como_conheceu': DadosDeclaradosInscricao.ComoConheceu.INDICACAO,
            'snapshot_atual': {'segredo': 'nao-expor'},
        }
        dados.update(overrides)
        DadosDeclaradosInscricao.objects.create(**dados)
        return inscricao

    def criar_candidata(self, **overrides):
        dados = {
            'nome': 'Pessoa API Candidata',
            'data_nascimento': date(1999, 1, 1),
            'cpf': '52998224725',
            'email': 'candidata-api@example.test',
        }
        dados.update(overrides)
        return Pessoa.objects.create(**dados)

    def test_fichas_diretoria_suporte_e_superuser_acessam(self):
        for indice, role in enumerate((
            SiaRole.FICHAS,
            SiaRole.DIRETORIA,
            SiaRole.SUPORTE,
        )):
            with self.subTest(role=role):
                self.autenticar(role, indice)
                response = self.client.get(self.base_url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)

        superuser = get_user_model().objects.create_superuser(
            username='superuser-resolucao',
            email='superuser@example.test',
            password='senha-exclusiva-de-teste',
        )
        self.client.force_authenticate(superuser)
        self.assertEqual(
            self.client.get(self.base_url).status_code,
            status.HTTP_200_OK,
        )

    def test_sem_autenticacao_ou_papel_recebe_default_deny(self):
        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get(self.base_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.autenticar(indice='sem-papel')
        self.assertEqual(
            self.client.get(self.base_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_outro_papel_permanece_negado(self):
        self.autenticar(SiaRole.COMUNICACAO, 'comunicacao')

        response = self.client.post(
            f'{self.base_url}gerar-sugestoes/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_geracao_e_consulta_minimizam_resposta(self):
        self.autenticar(SiaRole.FICHAS, 'fichas')
        self.criar_candidata()

        response = self.client.post(
            f'{self.base_url}gerar-sugestoes/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        self.assertEqual(len(payload['correspondencias']), 1)
        self.assertNotIn('snapshot_atual', payload)
        self.assertNotIn('dados_cuidado', payload)
        self.assertNotIn('cpf', payload['dados_declarados'])
        candidata = payload['correspondencias'][0]['pessoa_candidata']
        self.assertTrue(candidata['cpf_coincidente'])
        self.assertNotIn('cpf', candidata)

    def test_aceite_rejeicao_criacao_e_aplicacao_usam_commands(self):
        self.autenticar(SiaRole.FICHAS, 'commands')
        candidata = self.criar_candidata()
        correspondencia = CorrespondenciaCadastralInscricao.objects.create(
            inscricao=self.inscricao,
            pessoa_candidata=candidata,
            origem_sinal='cpf_exato',
        )
        aceite = self.client.post(
            f'{self.base_url}correspondencias/{correspondencia.pk}/aceitar/',
            {},
            format='json',
        )
        self.assertEqual(aceite.status_code, status.HTTP_200_OK)
        self.assertEqual(aceite.json()['pessoa_id'], candidata.pk)

        aplicacao = self.client.post(
            f'{self.base_url}aplicar-campos/',
            {'campos': ['nome']},
            format='json',
        )
        self.assertEqual(aplicacao.status_code, status.HTTP_200_OK)
        candidata.refresh_from_db()
        self.assertEqual(candidata.nome, 'Pessoa API Declarada')

        outra = self.criar_inscricao(
            cpf='11144477735',
            email='outra-api@example.test',
        )
        outra_url = f'/api/resolucoes-inscricoes/{outra.pk}/'
        nova = self.client.post(
            f'{outra_url}criar-pessoa/',
            {'campos': ['nome', 'email']},
            format='json',
        )
        self.assertEqual(nova.status_code, status.HTTP_201_CREATED)

        terceira = self.criar_inscricao(
            cpf='93541134780',
            email='terceira-api@example.test',
        )
        terceira_candidata = self.criar_candidata(
            cpf='93541134780',
            email='terceira-candidata@example.test',
        )
        rejeitada = CorrespondenciaCadastralInscricao.objects.create(
            inscricao=terceira,
            pessoa_candidata=terceira_candidata,
            origem_sinal='cpf_exato',
        )
        rejeicao = self.client.post(
            f'/api/resolucoes-inscricoes/{terceira.pk}/correspondencias/'
            f'{rejeitada.pk}/rejeitar/',
            {},
            format='json',
        )
        self.assertEqual(rejeicao.status_code, status.HTTP_200_OK)

    def test_correspondencia_de_outra_inscricao_retorna_404(self):
        self.autenticar(SiaRole.FICHAS, 'nested')
        outra = self.criar_inscricao(email='outra-nested@example.test')
        candidata = self.criar_candidata()
        correspondencia = CorrespondenciaCadastralInscricao.objects.create(
            inscricao=outra,
            pessoa_candidata=candidata,
            origem_sinal='cpf_exato',
        )

        response = self.client.post(
            f'{self.base_url}correspondencias/{correspondencia.pk}/aceitar/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_payload_arbitrario_e_transicao_invalida_retornam_400(self):
        self.autenticar(SiaRole.FICHAS, 'invalidos')
        arbitrario = self.client.post(
            f'{self.base_url}aplicar-campos/',
            {'campos': ['nome'], 'pessoa_id': 999},
            format='json',
        )
        self.assertEqual(arbitrario.status_code, status.HTTP_400_BAD_REQUEST)

        candidata = self.criar_candidata()
        correspondencia = CorrespondenciaCadastralInscricao.objects.create(
            inscricao=self.inscricao,
            pessoa_candidata=candidata,
            origem_sinal='cpf_exato',
            status=CorrespondenciaCadastralInscricao.Status.REJEITADA,
            decidida_por=self.user,
            decidida_em=timezone.now(),
        )
        invalida = self.client.post(
            f'{self.base_url}correspondencias/{correspondencia.pk}/aceitar/',
            {},
            format='json',
        )
        self.assertEqual(invalida.status_code, status.HTTP_400_BAD_REQUEST)

    def test_base_nao_oferece_crud_generico(self):
        self.autenticar(SiaRole.FICHAS, 'sem-crud')

        self.assertEqual(
            self.client.patch(
                self.base_url,
                {'pessoa_id': 999},
                format='json',
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(self.base_url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
