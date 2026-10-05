from unittest.mock import patch

from django.contrib.auth import get_user_model
from rest_framework import status

from core.models import (
    ConviteEncontro,
    Encontro,
    Frequencia,
    LogSistema,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.services import participacoes as participacao_services
from core.services import trabalhos as trabalho_services
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_alpinista, make_encontro


class EncounterWorkCommandApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='apoio',
            nome='Apoio',
            capacidade_minima_recomendada=1,
            capacidade_maxima_recomendada=5,
        )
        TemplateRoleEquipe.objects.create(
            template_equipe=self.template,
            codigo='integrante',
            nome='Integrante',
        )

    def _preparar_role(self):
        response = self.client.post(
            f'/api/encontros/{self.encontro.pk}/preparar-equipes/',
            {},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return self.encontro.equipes.get().roles.get()

    def _criar_convite(self, pessoa, *, role=None):
        payload = {
            'pessoa_id': pessoa.pk,
            'encontro_id': self.encontro.pk,
            'finalidade': ConviteEncontro.Finalidade.TRABALHAR,
            'confirmar_avisos': True,
        }
        if role is not None:
            payload['role_trabalho_proposta_id'] = role.pk
        response = self.client.post(
            '/api/convites-encontros/',
            payload,
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        convite = ConviteEncontro.objects.get(pk=response.json()['id'])
        participacao_services.responder_convite(
            convite,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        return convite

    def _iniciar(self, pessoa, *, role=None):
        convite = self._criar_convite(pessoa, role=role)
        response = self.client.post(
            '/api/trabalhos-encontros/',
            {
                'convite_id': convite.pk,
                'confirmar_avisos': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return TrabalhoEncontro.objects.get(pk=response.json()['id'])

    def test_aviso_exige_confirmacao_e_preserva_avaliacao_estruturada(self):
        pessoa = Pessoa.objects.create(nome='Pessoa com aviso')
        payload = {
            'pessoa_id': pessoa.pk,
            'encontro_id': self.encontro.pk,
            'finalidade': ConviteEncontro.Finalidade.TRABALHAR,
        }

        bloqueado = self.client.post(
            '/api/convites-encontros/',
            payload,
            format='json',
        )
        aceito = self.client.post(
            '/api/convites-encontros/',
            {**payload, 'confirmar_avisos': True},
            format='json',
        )

        self.assertEqual(bloqueado.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            bloqueado.json()['avaliacao']['resultado'],
            'AVISO',
        )
        self.assertTrue(bloqueado.json()['avaliacao']['motivos'])
        self.assertEqual(aceito.status_code, status.HTTP_201_CREATED)
        self.assertEqual(aceito.json()['avaliacao']['resultado'], 'AVISO')
        self.assertTrue(
            LogSistema.objects.filter(
                modulo='ConviteEncontro',
                descricao__contains='PERFIL_ALPINISTA_AUSENTE',
            ).exists()
        )

    def test_api_preserva_resultados_elegivel_e_bloqueio(self):
        pessoa_elegivel = Pessoa.objects.create(nome='Pessoa elegível')
        PerfilAlpinista.objects.create(pessoa=pessoa_elegivel)
        make_alpinista(pessoa=pessoa_elegivel, status='ativo')
        ParticipacaoEncontro.objects.create(
            pessoa=pessoa_elegivel,
            encontro=make_encontro(tipo=Encontro.Tipo.ESPPA),
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=Encontro.Tipo.ESPPA,
        )
        elegivel = self.client.post(
            '/api/convites-encontros/',
            {
                'pessoa_id': pessoa_elegivel.pk,
                'encontro_id': self.encontro.pk,
                'finalidade': ConviteEncontro.Finalidade.TRABALHAR,
            },
            format='json',
        )

        pessoa_bloqueada = Pessoa.objects.create(nome='Pessoa bloqueada')
        PerfilAlpinista.objects.create(pessoa=pessoa_bloqueada)
        make_alpinista(pessoa=pessoa_bloqueada, status='ativo')
        ParticipacaoEncontro.objects.create(
            pessoa=pessoa_bloqueada,
            encontro=make_encontro(tipo=Encontro.Tipo.ESCALADA),
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )
        bloqueio = self.client.post(
            '/api/convites-encontros/',
            {
                'pessoa_id': pessoa_bloqueada.pk,
                'encontro_id': self.encontro.pk,
                'finalidade': ConviteEncontro.Finalidade.TRABALHAR,
                'confirmar_avisos': True,
            },
            format='json',
        )

        self.assertEqual(elegivel.status_code, status.HTTP_201_CREATED)
        self.assertEqual(elegivel.json()['avaliacao']['resultado'], 'ELEGIVEL')
        self.assertEqual(bloqueio.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(bloqueio.json()['avaliacao']['resultado'], 'BLOQUEIO')
        self.assertIn(
            'AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA',
            [
                motivo['codigo']
                for motivo in bloqueio.json()['avaliacao']['motivos']
            ],
        )

    def test_preparacao_consulta_e_writes_delegam_aos_services(self):
        with patch(
            'core.views.trabalho_services.preparar_equipes_encontro',
            wraps=trabalho_services.preparar_equipes_encontro,
        ) as preparar:
            role = self._preparar_role()

        pessoa = Pessoa.objects.create(nome='Pessoa alocada pela API')
        with patch(
            'core.serializers.trabalho_services.criar_convite_trabalho',
            wraps=trabalho_services.criar_convite_trabalho,
        ) as convidar:
            trabalho = self._iniciar(pessoa)

        with patch(
            'core.views.trabalho_services.alocar_trabalho',
            wraps=trabalho_services.alocar_trabalho,
        ) as alocar:
            alocacao = self.client.post(
                f'/api/trabalhos-encontros/{trabalho.pk}/alocar/',
                {
                    'role_equipe_id': role.pk,
                    'confirmar_avisos': True,
                },
                format='json',
            )

        with patch(
            'core.views.trabalho_services.registrar_resultado_trabalho',
            wraps=trabalho_services.registrar_resultado_trabalho,
        ) as resultado:
            final = self.client.post(
                f'/api/trabalhos-encontros/{trabalho.pk}/resultado/',
                {'status': TrabalhoEncontro.Status.TRABALHOU},
                format='json',
            )

        equipes = self.client.get(
            f'/api/equipes-encontros/?encontro={self.encontro.pk}'
        )
        trabalhos = self.client.get(
            f'/api/trabalhos-encontros/?encontro={self.encontro.pk}'
        )

        self.assertEqual(alocacao.status_code, status.HTTP_200_OK)
        self.assertEqual(final.status_code, status.HTTP_200_OK)
        self.assertEqual(final.json()['status'], TrabalhoEncontro.Status.TRABALHOU)
        self.assertEqual(equipes.status_code, status.HTTP_200_OK)
        self.assertEqual(equipes.json()[0]['capacidade']['resultado'], 'AVISO')
        self.assertEqual(equipes.json()[0]['roles'][0]['trabalhos'][0]['id'], trabalho.pk)
        self.assertEqual(trabalhos.status_code, status.HTTP_200_OK)
        self.assertEqual(len(trabalhos.json()), 1)
        preparar.assert_called_once()
        convidar.assert_called_once()
        alocar.assert_called_once()
        resultado.assert_called_once()
        self.assertFalse(Frequencia.objects.exists())

    def test_realocacao_desalocacao_retirada_e_substituicao_usam_comandos(self):
        role_a = self._preparar_role()
        template_b = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='vigilia',
            nome='Vigília',
        )
        template_role_b = TemplateRoleEquipe.objects.create(
            template_equipe=template_b,
            codigo='integrante',
            nome='Integrante',
        )
        # O snapshot é imutável após materialização; este segundo snapshot é
        # explícito no fixture para exercitar realocação sem reabrir templates.
        equipe_b = self.encontro.equipes.create(
            template_origem=template_b,
            codigo=template_b.codigo,
            nome=template_b.nome,
        )
        role_b = equipe_b.roles.create(
            template_origem=template_role_b,
            codigo=template_role_b.codigo,
            nome=template_role_b.nome,
        )
        anterior = self._iniciar(
            Pessoa.objects.create(nome='Pessoa anterior'),
            role=role_a,
        )
        novo = self._iniciar(Pessoa.objects.create(nome='Pessoa substituta'))

        realocado = self.client.post(
            f'/api/trabalhos-encontros/{anterior.pk}/realocar/',
            {'role_equipe_id': role_b.pk, 'confirmar_avisos': True},
            format='json',
        )
        substituido = self.client.post(
            f'/api/trabalhos-encontros/{anterior.pk}/substituir/',
            {
                'trabalho_novo_id': novo.pk,
                'role_equipe_id': role_b.pk,
                'confirmar_avisos': True,
            },
            format='json',
        )
        desalocado = self.client.post(
            f'/api/trabalhos-encontros/{novo.pk}/desalocar/',
            {},
            format='json',
        )
        retirado = self.client.post(
            f'/api/trabalhos-encontros/{novo.pk}/retirar/',
            {},
            format='json',
        )

        self.assertEqual(realocado.status_code, status.HTTP_200_OK)
        self.assertEqual(substituido.status_code, status.HTTP_200_OK)
        self.assertEqual(
            substituido.json()['anterior']['status'],
            TrabalhoEncontro.Status.RETIRADO,
        )
        self.assertEqual(desalocado.status_code, status.HTTP_200_OK)
        self.assertEqual(retirado.status_code, status.HTTP_200_OK)
        self.assertEqual(retirado.json()['status'], TrabalhoEncontro.Status.RETIRADO)
        self.assertFalse(hasattr(TrabalhoEncontro, 'substituido_por'))

    def test_listagens_exigem_escopo_e_crud_generico_permanece_fechado(self):
        self.assertEqual(
            self.client.get('/api/equipes-encontros/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.get('/api/trabalhos-encontros/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        trabalho = self._iniciar(Pessoa.objects.create(nome='Pessoa protegida'))
        detail = f'/api/trabalhos-encontros/{trabalho.pk}/'
        self.assertEqual(
            self.client.patch(detail, {'status': 'trabalhou'}).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(detail).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_default_deny_nas_novas_rotas(self):
        usuario = get_user_model().objects.create_user(
            username='sem-role-trabalho',
            password='senha-de-teste',
        )
        self.client.force_authenticate(user=usuario)

        for method, url in (
            ('get', f'/api/equipes-encontros/?encontro={self.encontro.pk}'),
            ('get', f'/api/trabalhos-encontros/?encontro={self.encontro.pk}'),
            ('post', f'/api/encontros/{self.encontro.pk}/preparar-equipes/'),
        ):
            with self.subTest(url=url):
                response = getattr(self.client, method)(url, {}, format='json')
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_legado_nao_cria_trabalho_canonico(self):
        pessoa = Pessoa.objects.create(nome='Pessoa sem inferência')
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        self.assertFalse(TrabalhoEncontro.objects.filter(convite=convite).exists())
        self.assertFalse(Frequencia.objects.exists())
