from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Frequencia,
    LogSistema,
    Palestra,
    PalestranteSessao,
    PerfilAlpinista,
    Pessoa,
    RoleEquipeEncontro,
    SessaoFormativa,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.roles import SiaRole
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_alpinista, make_encontro


class EncounterFormationApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)

    def _authenticate_role(self, role, *, username):
        user = get_user_model().objects.create_user(
            username=username,
            password='senha-exclusiva-de-teste',
        )
        group, _ = Group.objects.get_or_create(name=role.value)
        user.groups.add(group)
        self.client.force_authenticate(user=user)
        return user

    def _criar_sessao(
        self,
        *,
        encontro=None,
        tema_codigo='PALESTRA_SER_PESSOA',
    ):
        response = self.client.post(
            '/api/sessoes-formativas/',
            {
                'encontro_id': (encontro or self.encontro).pk,
                'tema_codigo': tema_codigo,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response, SessaoFormativa.objects.get(pk=response.json()['id'])

    def _adicionar_interno(self, sessao, perfil):
        response = self.client.post(
            f'/api/sessoes-formativas/{sessao.pk}/adicionar-palestrante/',
            {'perfil_alpinista_id': perfil.pk},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return PalestranteSessao.objects.get(pk=response.json()['id'])

    def _adicionar_externo(self, sessao, nome='Pessoa externa'):
        return self.client.post(
            f'/api/sessoes-formativas/{sessao.pk}/adicionar-palestrante/',
            {'nome_externo': nome},
            format='json',
        )

    def _trabalho_avc(self, *, pessoa, encontro):
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.AVC,
            codigo=f'equipe-avc-{encontro.pk}',
            nome='Equipe AVC',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=encontro,
            template_origem=template,
            codigo=template.codigo,
            nome=template.nome,
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo=template_role.codigo,
            nome=template_role.nome,
        )
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

    def test_catalogo_por_tipo_e_estruturado(self):
        esppa = make_encontro(tipo=Encontro.Tipo.ESPPA)
        avc = make_encontro(tipo=Encontro.Tipo.AVC)
        acampamento = make_encontro(tipo=Encontro.Tipo.ACAMPAMENTO)

        escalada_response = self.client.get(
            f'/api/catalogo-formacao/?encontro={self.encontro.pk}'
        )
        esppa_response = self.client.get(
            f'/api/catalogo-formacao/?encontro={esppa.pk}'
        )
        avc_response = self.client.get(
            f'/api/catalogo-formacao/?encontro={avc.pk}'
        )
        acampamento_response = self.client.get(
            f'/api/catalogo-formacao/?encontro={acampamento.pk}'
        )

        self.assertEqual(escalada_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(escalada_response.json()), 9)
        self.assertEqual(escalada_response.json(), esppa_response.json())
        self.assertEqual(len(avc_response.json()), 11)
        self.assertEqual(acampamento_response.json(), [])
        self.assertEqual(
            set(escalada_response.json()[0]),
            {'tema_codigo', 'titulo', 'tipo', 'ordem', 'bloco'},
        )
        self.assertTrue(all(
            item['tipo'] == 'palestra'
            for item in escalada_response.json()
        ))
        self.assertTrue(all(
            item['tipo'] == 'bate_papo'
            for item in avc_response.json()
        ))

    def test_catalogo_e_lista_exigem_escopo_de_encontro(self):
        self.assertEqual(
            self.client.get('/api/catalogo-formacao/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.client.get('/api/sessoes-formativas/').status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_cria_lista_e_recupera_sessao_com_allowlist(self):
        response, sessao = self._criar_sessao()

        self.assertEqual(
            set(response.json()),
            {
                'id',
                'encontro_id',
                'tema_codigo',
                'titulo_snapshot',
                'tipo_conteudo',
                'status',
                'realizada_em',
                'palestrantes',
                'criado_em',
                'atualizado_em',
            },
        )
        self.assertEqual(response.json()['titulo_snapshot'], 'Ser Pessoa')
        listagem = self.client.get(
            f'/api/sessoes-formativas/?encontro={self.encontro.pk}'
        )
        detalhe = self.client.get(f'/api/sessoes-formativas/{sessao.pk}/')
        self.assertEqual(listagem.status_code, status.HTTP_200_OK)
        self.assertEqual([item['id'] for item in listagem.json()], [sessao.pk])
        self.assertEqual(detalhe.status_code, status.HTTP_200_OK)
        self.assertTrue(
            LogSistema.objects.filter(
                modulo='SessaoFormativa',
                descricao__contains=f'ID {sessao.pk}',
            ).exists()
        )

    def test_gestao_e_permitida_para_formacao_diretoria_suporte_e_superuser(self):
        casos = (
            SiaRole.FORMACAO,
            SiaRole.DIRETORIA,
            SiaRole.SUPORTE,
        )
        for indice, role in enumerate(casos):
            with self.subTest(role=role.value):
                self._authenticate_role(role, username=f'gestao-formacao-{indice}')
                encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
                response = self.client.post(
                    '/api/sessoes-formativas/',
                    {
                        'encontro_id': encontro.pk,
                        'tema_codigo': 'PALESTRA_SER_PESSOA',
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        superuser = get_user_model().objects.create_superuser(
            username='superuser-formacao',
            password='senha-exclusiva-de-teste',
        )
        self.client.force_authenticate(user=superuser)
        encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        response = self.client.post(
            '/api/sessoes-formativas/',
            {
                'encontro_id': encontro.pk,
                'tema_codigo': 'PALESTRA_SER_PESSOA',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fichas_consulta_sem_gestao_e_outro_papel_permanece_negado(self):
        _, sessao = self._criar_sessao()
        self._authenticate_role(SiaRole.FICHAS, username='fichas-formacao')

        leitura = self.client.get(
            f'/api/sessoes-formativas/?encontro={self.encontro.pk}'
        )
        escrita = self.client.post(
            '/api/sessoes-formativas/',
            {
                'encontro_id': self.encontro.pk,
                'tema_codigo': 'PALESTRA_AMOR_DE_DEUS',
            },
            format='json',
        )
        cancelamento = self.client.post(
            f'/api/sessoes-formativas/{sessao.pk}/cancelar/',
            {},
            format='json',
        )
        self.assertEqual(leitura.status_code, status.HTTP_200_OK)
        self.assertEqual(escrita.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(cancelamento.status_code, status.HTTP_403_FORBIDDEN)

        self._authenticate_role(SiaRole.MME, username='mme-formacao')
        self.assertEqual(
            self.client.get(
                f'/api/sessoes-formativas/?encontro={self.encontro.pk}'
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.get(
                f'/api/catalogo-formacao/?encontro={self.encontro.pk}'
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_edita_e_cancela_sessao_por_commands(self):
        _, sessao = self._criar_sessao()

        alterada = self.client.patch(
            f'/api/sessoes-formativas/{sessao.pk}/alterar-tema/',
            {'tema_codigo': 'PALESTRA_AMOR_DE_DEUS'},
            format='json',
        )
        cancelada = self.client.post(
            f'/api/sessoes-formativas/{sessao.pk}/cancelar/',
            {},
            format='json',
        )

        self.assertEqual(alterada.status_code, status.HTTP_200_OK)
        self.assertEqual(alterada.json()['titulo_snapshot'], 'Amor de Deus')
        self.assertEqual(cancelada.status_code, status.HTTP_200_OK)
        self.assertEqual(
            cancelada.json()['status'],
            SessaoFormativa.Status.CANCELADA,
        )
        self.assertEqual(
            self.client.patch(
                f'/api/sessoes-formativas/{sessao.pk}/',
                {},
                format='json',
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_gerencia_multiplos_palestrantes_e_remove_no_escopo_da_sessao(self):
        _, sessao = self._criar_sessao()
        perfil = PerfilAlpinista.objects.create(
            pessoa=Pessoa.objects.create(nome='Alpinista da sessão'),
        )
        interno = self._adicionar_interno(sessao, perfil)
        externo_response = self._adicionar_externo(sessao)
        self.assertEqual(externo_response.status_code, status.HTTP_201_CREATED)
        externo_id = externo_response.json()['id']

        listagem = self.client.get(
            f'/api/sessoes-formativas/{sessao.pk}/palestrantes/'
        )
        self.assertEqual(listagem.status_code, status.HTTP_200_OK)
        self.assertEqual(
            {item['id'] for item in listagem.json()},
            {interno.pk, externo_id},
        )

        outra_sessao = self._criar_sessao(
            tema_codigo='PALESTRA_AMOR_DE_DEUS'
        )[1]
        nested_mismatch = self.client.post(
            f'/api/sessoes-formativas/{outra_sessao.pk}/remover-palestrante/',
            {'palestrante_id': externo_id},
            format='json',
        )
        removido = self.client.post(
            f'/api/sessoes-formativas/{sessao.pk}/remover-palestrante/',
            {'palestrante_id': externo_id},
            format='json',
        )
        self.assertEqual(nested_mismatch.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(removido.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            PalestranteSessao.objects.filter(pk=externo_id).exists()
        )

    def test_externo_em_escalada_e_esppa_nao_cria_entidades_colaterais(self):
        pessoas_antes = Pessoa.objects.count()
        perfis_antes = PerfilAlpinista.objects.count()
        for tipo in (Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA):
            with self.subTest(tipo=tipo):
                encontro = make_encontro(tipo=tipo)
                _, sessao = self._criar_sessao(encontro=encontro)
                response = self._adicionar_externo(
                    sessao,
                    nome=f'Externo {tipo}',
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(Pessoa.objects.count(), pessoas_antes)
        self.assertEqual(PerfilAlpinista.objects.count(), perfis_antes)
        self.assertFalse(TrabalhoEncontro.objects.exists())
        self.assertFalse(Frequencia.objects.exists())

    def test_avc_delega_bloqueios_e_aceita_trabalhador_valido(self):
        avc = make_encontro(tipo=Encontro.Tipo.AVC)
        _, sessao = self._criar_sessao(
            encontro=avc,
            tema_codigo='BATE_PAPO_JESUS_DEUS_HOMEM',
        )
        pessoa = Pessoa.objects.create(nome='Palestrante do AVC')
        perfil = PerfilAlpinista.objects.create(pessoa=pessoa)

        externo = self._adicionar_externo(sessao, nome='Externo no AVC')
        sem_trabalho = self.client.post(
            f'/api/sessoes-formativas/{sessao.pk}/adicionar-palestrante/',
            {'perfil_alpinista_id': perfil.pk},
            format='json',
        )
        self.assertEqual(externo.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(sem_trabalho.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(sessao.palestrantes.exists())

        trabalho = self._trabalho_avc(pessoa=pessoa, encontro=avc)
        valido = self.client.post(
            f'/api/sessoes-formativas/{sessao.pk}/adicionar-palestrante/',
            {'perfil_alpinista_id': perfil.pk},
            format='json',
        )
        self.assertEqual(valido.status_code, status.HTTP_201_CREATED)
        trabalho.refresh_from_db()
        self.assertEqual(trabalho.status, TrabalhoEncontro.Status.ALOCADO)

    def test_realizacao_e_historico_canonico_excluem_nao_atuacao_e_externo(self):
        pessoa = Pessoa.objects.create(nome='Palestrante efetivo')
        perfil = PerfilAlpinista.objects.create(pessoa=pessoa)
        alpinista = make_alpinista(pessoa=pessoa)
        outra_pessoa = Pessoa.objects.create(nome='Palestrante previsto')
        outro_perfil = PerfilAlpinista.objects.create(pessoa=outra_pessoa)
        outro_alpinista = make_alpinista(pessoa=outra_pessoa)
        _, sessao = self._criar_sessao()
        efetivo = self._adicionar_interno(sessao, perfil)
        nao_ministrou = self._adicionar_interno(sessao, outro_perfil)
        externo = self._adicionar_externo(sessao, nome='Externo efetivo').json()

        realizada = self.client.post(
            f'/api/sessoes-formativas/{sessao.pk}/realizar/',
            {
                'resultados': [
                    {
                        'palestrante_id': efetivo.pk,
                        'status': PalestranteSessao.Status.MINISTROU,
                    },
                    {
                        'palestrante_id': nao_ministrou.pk,
                        'status': PalestranteSessao.Status.NAO_MINISTROU,
                    },
                    {
                        'palestrante_id': externo['id'],
                        'status': PalestranteSessao.Status.MINISTROU,
                    },
                ],
            },
            format='json',
        )
        historico = self.client.get(
            f'/api/alpinistas/{alpinista.pk}/historico-formativo/'
        )
        historico_vazio = self.client.get(
            f'/api/alpinistas/{outro_alpinista.pk}/historico-formativo/'
        )

        self.assertEqual(realizada.status_code, status.HTTP_200_OK)
        self.assertEqual(
            realizada.json()['status'],
            SessaoFormativa.Status.REALIZADA,
        )
        self.assertEqual(historico.status_code, status.HTTP_200_OK)
        self.assertEqual(len(historico.json()), 1)
        self.assertEqual(historico.json()[0]['palestrante_id'], perfil.pk)
        self.assertEqual(historico.json()[0]['titulo'], 'Ser Pessoa')
        self.assertEqual(historico_vazio.json(), [])
        self.assertFalse(Frequencia.objects.exists())

    def test_legado_permanece_legivel_e_novos_writes_nao_fazem_dual_write(self):
        alpinista = make_alpinista()
        palestra = Palestra.objects.create(
            alpinista=alpinista,
            encontro=self.encontro,
            titulo='Palestra legada',
        )

        legado = self.client.get(
            f'/api/alpinistas/{alpinista.pk}/historico-palestras/'
        )
        _, sessao = self._criar_sessao()

        self.assertEqual(legado.status_code, status.HTTP_200_OK)
        self.assertEqual(legado.json()[0]['titulo'], 'Palestra legada')
        self.assertTrue(Palestra.objects.filter(pk=palestra.pk).exists())
        self.assertEqual(Palestra.objects.count(), 1)
        self.assertEqual(sessao.tema_codigo, 'PALESTRA_SER_PESSOA')

    def test_formacao_nao_recebe_permissoes_de_outros_dominios(self):
        self._authenticate_role(SiaRole.FORMACAO, username='formacao-isolada-api')
        self.assertEqual(
            self.client.post('/api/trabalhos-encontros/', {}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post('/api/alpinistas/', {}, format='json').status_code,
            status.HTTP_403_FORBIDDEN,
        )
