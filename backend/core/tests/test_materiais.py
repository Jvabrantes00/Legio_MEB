from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import EntregaMaterial, LogSistema, Material
from core.roles import SiaRole
from core.tests.factories import make_alpinista, make_encontro


class MateriaisAuthorizationAndDomainTests(APITestCase):
    material_url = '/api/materiais/'
    entrega_url = '/api/entregas-materiais/'
    summary_profile_fields = {
        'id',
        'nome',
        'foto',
        'idade',
        'grupo',
        'whatsapp',
        'batizado',
        'primeira_comunhao',
        'crismado',
        'musica',
    }

    def make_user(self, username, *roles, is_superuser=False):
        user = get_user_model().objects.create_user(
            username=username,
            password='senha-exclusiva-de-teste',
            is_superuser=is_superuser,
            is_staff=is_superuser,
        )
        for role in roles:
            group, _ = Group.objects.get_or_create(name=role.value)
            user.groups.add(group)
        return user

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def make_material(self, **overrides):
        values = {'nome': 'Camiseta', 'quantidade_disponivel': 10}
        values.update(overrides)
        return Material.objects.create(**values)

    def test_secretaria_ve_resumo_sem_editar_alpinista_ou_outros_dominios(self):
        alpinista = make_alpinista(
            cpf='52998224725',
            endereco='Endereço privado',
            restricaoSaude='Saúde privada',
            is_neurodivergente=True,
        )
        encontro = make_encontro()
        self.authenticate(self.make_user('secretaria-resumo', SiaRole.SECRETARIA))
        detail_url = f'/api/alpinistas/{alpinista.pk}/'

        response = self.client.get(detail_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.json()), self.summary_profile_fields)
        self.assertNotIn(alpinista.cpf, str(response.json()))
        self.assertEqual(
            self.client.patch(detail_url, {'nome': 'Indevido'}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        bloqueadas = (
            self.client.patch(
                f'/api/alpinistas/{alpinista.pk}/musica/',
                {'canta': True},
                format='json',
            ),
            self.client.patch(
                f'/api/alpinistas/{alpinista.pk}/foto/',
                {},
                format='multipart',
            ),
            self.client.get('/api/encontros/'),
            self.client.get('/api/eventos/'),
            self.client.get('/api/logs/'),
            self.client.get(
                f'/api/alpinistas/{alpinista.pk}/historico-violeiro/'
            ),
            self.client.get(
                f'/api/alpinistas/{alpinista.pk}/historico-palestras/'
            ),
            self.client.get(f'/api/encontros/{encontro.pk}/fotos/'),
        )
        for blocked_response in bloqueadas:
            self.assertEqual(
                blocked_response.status_code,
                status.HTTP_403_FORBIDDEN,
            )

    def test_secretaria_cria_lista_altera_e_exclui_material_sem_historico(self):
        self.authenticate(self.make_user('secretaria-material', SiaRole.SECRETARIA))

        create_response = self.client.post(
            self.material_url,
            {'nome': 'Crachá', 'quantidade_disponivel': 20},
            format='json',
        )
        material_id = create_response.json()['id']
        detail_url = f'{self.material_url}{material_id}/'

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.client.get(self.material_url).status_code, status.HTTP_200_OK)
        self.assertEqual(
            self.client.patch(
                detail_url,
                {'quantidade_disponivel': 15},
                format='json',
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(Material.objects.get(pk=material_id).quantidade_disponivel, 15)
        self.assertEqual(
            LogSistema.objects.filter(modulo='Material').count(),
            2,
        )
        self.assertEqual(
            self.client.delete(detail_url).status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(Material.objects.filter(pk=material_id).exists())

    def test_quantidade_negativa_de_material_e_rejeitada(self):
        material = self.make_material()
        self.authenticate(self.make_user('secretaria-negativa', SiaRole.SECRETARIA))

        response = self.client.patch(
            f'{self.material_url}{material.pk}/',
            {'quantidade_disponivel': -1},
            format='json',
        )
        material.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(material.quantidade_disponivel, 10)
        self.assertFalse(LogSistema.objects.filter(modulo='Material').exists())

    def test_entrega_zero_ou_acima_do_estoque_nao_altera_saldo(self):
        material = self.make_material(quantidade_disponivel=2)
        alpinista = make_alpinista()
        self.authenticate(self.make_user('secretaria-entrega-invalida', SiaRole.SECRETARIA))

        zero = self.client.post(
            self.entrega_url,
            {
                'material_id': material.pk,
                'alpinista_id': alpinista.pk,
                'quantidade': 0,
            },
            format='json',
        )
        excesso = self.client.post(
            self.entrega_url,
            {
                'material_id': material.pk,
                'alpinista_id': alpinista.pk,
                'quantidade': 3,
            },
            format='json',
        )
        material.refresh_from_db()

        self.assertEqual(zero.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(excesso.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(material.quantidade_disponivel, 2)
        self.assertFalse(EntregaMaterial.objects.exists())
        self.assertFalse(LogSistema.objects.filter(modulo='EntregaMaterial').exists())

    def test_duas_entregas_reduzem_estoque_e_preservam_historico_separado(self):
        material = self.make_material(quantidade_disponivel=10)
        primeiro = make_alpinista()
        segundo = make_alpinista()
        self.authenticate(self.make_user('secretaria-historico', SiaRole.SECRETARIA))

        for alpinista, quantidade in ((primeiro, 2), (segundo, 3)):
            response = self.client.post(
                self.entrega_url,
                {
                    'material_id': material.pk,
                    'alpinista_id': alpinista.pk,
                    'quantidade': quantidade,
                },
                format='json',
            )
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        material.refresh_from_db()
        historico = self.client.get(self.entrega_url)
        itens = historico.json()['results']

        self.assertEqual(material.quantidade_disponivel, 5)
        self.assertEqual(EntregaMaterial.objects.count(), 2)
        self.assertEqual({item['quantidade'] for item in itens}, {2, 3})
        self.assertEqual(
            {item['alpinista_id'] for item in itens},
            {primeiro.pk, segundo.pk},
        )
        for item in itens:
            self.assertEqual(
                set(item),
                {
                    'id',
                    'material_id',
                    'material_nome',
                    'alpinista_id',
                    'alpinista_nome',
                    'quantidade',
                    'entregue_em',
                },
            )
            self.assertEqual(item['material_id'], material.pk)
            self.assertEqual(item['material_nome'], material.nome)
        self.assertEqual(
            LogSistema.objects.filter(modulo='EntregaMaterial').count(),
            2,
        )

    def test_serializer_da_entrega_nao_expoe_ficha_completa(self):
        material = self.make_material()
        alpinista = make_alpinista(
            cpf='52998224725',
            endereco='Endereço privado',
            restricaoSaude='Saúde privada',
            medicacao='Medicamento privado',
        )
        entrega = EntregaMaterial.objects.create(
            material=material,
            alpinista=alpinista,
            quantidade=1,
        )
        self.authenticate(self.make_user('secretaria-privacidade', SiaRole.SECRETARIA))

        response = self.client.get(f'{self.entrega_url}{entrega.pk}/')
        payload = response.json()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(payload['alpinista_id'], alpinista.pk)
        self.assertEqual(payload['alpinista_nome'], alpinista.nome)
        self.assertNotIn(alpinista.cpf, str(payload))
        self.assertNotIn('privado', str(payload).lower())

    def test_entrega_historica_nao_pode_ser_editada_ou_excluida(self):
        material = self.make_material()
        entrega = EntregaMaterial.objects.create(
            material=material,
            alpinista=make_alpinista(),
            quantidade=1,
        )
        self.authenticate(self.make_user('secretaria-imutavel', SiaRole.SECRETARIA))
        url = f'{self.entrega_url}{entrega.pk}/'

        self.assertEqual(
            self.client.patch(url, {'quantidade': 2}, format='json').status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(url).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertTrue(EntregaMaterial.objects.filter(pk=entrega.pk).exists())

    def test_material_com_historico_nao_pode_ser_excluido(self):
        material = self.make_material()
        EntregaMaterial.objects.create(
            material=material,
            alpinista=make_alpinista(),
            quantidade=1,
        )
        self.authenticate(self.make_user('secretaria-protect', SiaRole.SECRETARIA))

        response = self.client.delete(f'{self.material_url}{material.pk}/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(Material.objects.filter(pk=material.pk).exists())
        self.assertTrue(EntregaMaterial.objects.filter(material=material).exists())

    def test_falha_depois_da_reducao_do_saldo_desfaz_toda_a_entrega(self):
        material = self.make_material(quantidade_disponivel=4)
        alpinista = make_alpinista()
        self.authenticate(self.make_user('secretaria-rollback', SiaRole.SECRETARIA))

        with patch(
            'core.views.LogSistema.objects.create',
            side_effect=RuntimeError('falha simulada no log'),
        ):
            with self.assertRaises(RuntimeError):
                self.client.post(
                    self.entrega_url,
                    {
                        'material_id': material.pk,
                        'alpinista_id': alpinista.pk,
                        'quantidade': 2,
                    },
                    format='json',
                )

        material.refresh_from_db()
        self.assertEqual(material.quantidade_disponivel, 4)
        self.assertFalse(EntregaMaterial.objects.exists())

    def test_matriz_de_autorizacao_de_materiais(self):
        material = self.make_material()
        permitidos = (
            SiaRole.SUPORTE,
            SiaRole.DIRETORIA,
            SiaRole.SECRETARIA,
        )
        bloqueados = (
            SiaRole.FICHAS,
            SiaRole.MME,
            SiaRole.FORMACAO,
            SiaRole.EVENTOS,
            SiaRole.COMUNICACAO,
            SiaRole.ACAO_SOCIAL,
            SiaRole.LITURGIA,
        )

        for index, role in enumerate(permitidos):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'material-permitido-{index}', role))
                self.assertEqual(
                    self.client.get(self.material_url).status_code,
                    status.HTTP_200_OK,
                )
                self.assertEqual(
                    self.client.post(
                        self.material_url,
                        {
                            'nome': f'Material permitido {index}',
                            'quantidade_disponivel': 1,
                        },
                        format='json',
                    ).status_code,
                    status.HTTP_201_CREATED,
                )
                self.assertEqual(
                    self.client.get(self.entrega_url).status_code,
                    status.HTTP_200_OK,
                )

        for index, role in enumerate(bloqueados):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'material-negado-{index}', role))
                self.assertEqual(
                    self.client.get(self.material_url).status_code,
                    status.HTTP_403_FORBIDDEN,
                )
                self.assertEqual(
                    self.client.get(self.entrega_url).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get(self.material_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.assertEqual(
            self.client.get(self.entrega_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
        self.authenticate(self.make_user('material-sem-papel'))
        self.assertEqual(
            self.client.get(self.material_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(self.entrega_url).status_code,
            status.HTTP_403_FORBIDDEN,
        )
