from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import status

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Frequencia,
    ItemPropostaVioleiros,
    LogSistema,
    PerfilAlpinista,
    Pessoa,
    PropostaVioleiros,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoEncontroLegado,
)
from core.roles import SiaRole
from core.serializers import (
    AproveitamentoPropostaVioleirosCommandSerializer,
    CriacaoPropostaVioleirosCommandSerializer,
    EdicaoPropostaVioleirosCommandSerializer,
    ItemPropostaVioleirosCommandSerializer,
    ItemPropostaVioleirosSerializer,
    PreenchimentoPropostaVioleirosCommandSerializer,
    PropostaVioleirosSerializer,
    SubstituicaoPropostaVioleirosCommandSerializer,
)
from core.tests.base import AuthenticatedAPITestCase


class PropostaVioleirosApiTests(AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.encontro = Encontro.objects.create(
            encontro='Escalada API MME',
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia=date(2027, 4, 10),
            data_exato='10 de abril de 2027',
        )
        self._equipes = {}

    def autenticar(self, role, indice='principal'):
        user = get_user_model().objects.create_user(
            username=f'{role.value}-{indice}',
            password='senha-exclusiva-de-teste',
        )
        group, _ = Group.objects.get_or_create(name=role.value)
        user.groups.add(group)
        self.client.force_authenticate(user=user)
        return user

    def criar_perfil(
        self,
        indice,
        *,
        violeiro=True,
        canta=False,
        disponivel_mme=True,
    ):
        return PerfilAlpinista.objects.create(
            pessoa=Pessoa.objects.create(nome=f'Candidato API {indice}'),
            violeiro=violeiro,
            canta=canta,
            disponivel_mme=disponivel_mme,
        )

    def criar_proposta(self, *, nome='Proposta API'):
        response = self.client.post(
            '/api/propostas-violeiros/',
            {'encontro_id': self.encontro.pk, 'nome': nome},
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return PropostaVioleiros.objects.get(pk=response.json()['id'])

    def preencher(
        self,
        proposta,
        perfil,
        *,
        papel='integrante',
        posicao=1,
    ):
        response = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/preencher-posicao/',
            {
                'perfil_alpinista_id': perfil.pk,
                'papel_sugerido': papel,
                'posicao': posicao,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return ItemPropostaVioleiros.objects.filter(
            proposta=proposta,
            perfil_alpinista=perfil,
            vigente=True,
        ).get()

    def preencher_cinco(self, proposta, inicio=1):
        itens = [self.preencher(
            proposta,
            self.criar_perfil(inicio),
            papel='coordenador',
            posicao=1,
        )]
        for posicao in range(1, 5):
            itens.append(self.preencher(
                proposta,
                self.criar_perfil(inicio + posicao),
                posicao=posicao,
            ))
        return itens

    def criar_role(self, codigo):
        if codigo in self._equipes:
            return self._equipes[codigo]
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=self.encontro.tipo,
            codigo=codigo,
            nome=codigo.title(),
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=template,
            codigo=codigo,
            nome=codigo.title(),
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo='integrante',
            nome='Integrante',
        )
        self._equipes[codigo] = role
        return role

    def alocar(self, perfil, codigo):
        convite = ConviteEncontro.objects.create(
            pessoa=perfil.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        return TrabalhoEncontro.objects.create(
            pessoa=perfil.pessoa,
            encontro=self.encontro,
            convite=convite,
            role_equipe=self.criar_role(codigo),
            status=TrabalhoEncontro.Status.ALOCADO,
        )

    def test_mme_diretoria_e_suporte_criam_proposta(self):
        for indice, role in enumerate((
            SiaRole.MME,
            SiaRole.DIRETORIA,
            SiaRole.SUPORTE,
        )):
            with self.subTest(role=role):
                self.autenticar(role, indice)
                response = self.client.post(
                    '/api/propostas-violeiros/',
                    {
                        'encontro_id': self.encontro.pk,
                        'nome': f'Proposta {role.value}',
                    },
                    format='json',
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_fichas_nao_cria_nem_edita_slots(self):
        proposta = self.criar_proposta()
        perfil = self.criar_perfil(1)
        self.autenticar(SiaRole.FICHAS)

        criar = self.client.post(
            '/api/propostas-violeiros/',
            {'encontro_id': self.encontro.pk},
            format='json',
        )
        preencher = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/preencher-posicao/',
            {
                'perfil_alpinista_id': perfil.pk,
                'papel_sugerido': 'integrante',
                'posicao': 1,
            },
            format='json',
        )

        self.assertEqual(criar.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(preencher.status_code, status.HTTP_403_FORBIDDEN)

    def test_outro_papel_permanece_default_deny(self):
        proposta = self.criar_proposta()
        self.autenticar(SiaRole.FORMACAO)

        lista = self.client.get(
            f'/api/propostas-violeiros/?encontro={self.encontro.pk}'
        )
        detalhe = self.client.get(
            f'/api/propostas-violeiros/{proposta.pk}/'
        )

        self.assertEqual(lista.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(detalhe.status_code, status.HTTP_403_FORBIDDEN)

    def test_leitura_e_permitida_para_mme_fichas_diretoria_e_suporte(self):
        proposta = self.criar_proposta()
        for indice, role in enumerate((
            SiaRole.MME,
            SiaRole.FICHAS,
            SiaRole.DIRETORIA,
            SiaRole.SUPORTE,
        )):
            with self.subTest(role=role):
                self.autenticar(role, indice)
                response = self.client.get(
                    f'/api/propostas-violeiros/{proposta.pk}/'
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_usuario_nao_autenticado_recebe_401(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(
            f'/api/propostas-violeiros/?encontro={self.encontro.pk}'
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_lista_exige_escopo_de_encontro(self):
        response = self.client.get('/api/propostas-violeiros/')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('encontro', response.json())

    def test_preenchimento_substituicao_retirada_e_auditoria(self):
        proposta = self.criar_proposta()
        anterior = self.preencher(proposta, self.criar_perfil(1))

        substituicao = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/substituir-posicao/',
            {
                'item_id': anterior.pk,
                'perfil_alpinista_id': self.criar_perfil(2).pk,
            },
            format='json',
        )
        self.assertEqual(substituicao.status_code, status.HTTP_200_OK)
        novo = proposta.itens.get(vigente=True)
        retirada = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/retirar-item/',
            {'item_id': novo.pk},
            format='json',
        )

        self.assertEqual(retirada.status_code, status.HTTP_200_OK)
        self.assertEqual(proposta.itens.count(), 2)
        self.assertFalse(proposta.itens.filter(vigente=True).exists())
        descricoes = list(
            LogSistema.objects
            .filter(modulo='PropostaVioleiros')
            .values_list('descricao', flat=True)
        )
        self.assertTrue(any('substituído' in item for item in descricoes))
        self.assertTrue(any('retirado' in item for item in descricoes))

    def test_criacao_edicao_e_encerramento_sao_auditados(self):
        proposta = self.criar_proposta()
        edicao = self.client.patch(
            f'/api/propostas-violeiros/{proposta.pk}/editar-nome/',
            {'nome': 'Nome atualizado'},
            format='json',
        )
        encerramento = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/encerrar/',
            {},
            format='json',
        )

        self.assertEqual(edicao.status_code, status.HTTP_200_OK)
        self.assertEqual(edicao.json()['nome'], 'Nome atualizado')
        self.assertEqual(encerramento.status_code, status.HTTP_200_OK)
        descricoes = list(
            LogSistema.objects
            .filter(modulo='PropostaVioleiros')
            .values_list('descricao', flat=True)
        )
        self.assertTrue(any('criada' in item for item in descricoes))
        self.assertTrue(any('nome alterado' in item for item in descricoes))
        self.assertTrue(any('encerrada' in item for item in descricoes))

    def test_encerramento_bloqueia_edicao_e_nao_oferece_reabertura(self):
        proposta = self.criar_proposta()
        encerramento = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/encerrar/',
            {},
            format='json',
        )
        edicao = self.client.patch(
            f'/api/propostas-violeiros/{proposta.pk}/editar-nome/',
            {'nome': 'Não permitido'},
            format='json',
        )
        reabertura = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/reabrir/',
            {},
            format='json',
        )

        self.assertEqual(encerramento.status_code, status.HTTP_200_OK)
        self.assertEqual(edicao.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            encerramento.json()['status'],
            PropostaVioleiros.Status.ENCERRADA,
        )
        self.assertEqual(reabertura.status_code, status.HTTP_404_NOT_FOUND)

    def test_resumo_completo_e_incompleto(self):
        proposta = self.criar_proposta()
        itens = self.preencher_cinco(proposta)
        completo = self.client.get(
            f'/api/propostas-violeiros/{proposta.pk}/resumo/'
        )
        self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/retirar-item/',
            {'item_id': itens[-1].pk},
            format='json',
        )
        incompleto = self.client.get(
            f'/api/propostas-violeiros/{proposta.pk}/resumo/'
        )

        self.assertEqual(completo.json()['total_disponivel'], 5)
        self.assertTrue(completo.json()['completa'])
        self.assertEqual(incompleto.json()['total_disponivel'], 4)
        self.assertEqual(incompleto.json()['vagas_disponiveis'], 1)
        self.assertTrue(incompleto.json()['precisa_completar'])

    def test_filtro_lista_somente_abertas_que_precisam_completar(self):
        incompleta = self.criar_proposta(nome='Incompleta')
        completa = self.criar_proposta(nome='Completa')
        encerrada = self.criar_proposta(nome='Encerrada')
        self.preencher_cinco(completa, inicio=10)
        self.client.post(
            f'/api/propostas-violeiros/{encerrada.pk}/encerrar/',
            {},
            format='json',
        )

        response = self.client.get(
            '/api/propostas-violeiros/'
            f'?encontro={self.encontro.pk}&precisa_completar=true'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['id'] for item in response.json()],
            [incompleta.pk],
        )

    def test_api_expoe_todas_as_situacoes_derivadas_e_historico(self):
        proposta = self.criar_proposta()
        historico = self.preencher(proposta, self.criar_perfil(1), posicao=1)
        aproveitado_perfil = self.criar_perfil(2)
        aproveitado = self.preencher(proposta, aproveitado_perfil, posicao=2)
        outra_perfil = self.criar_perfil(3)
        outra = self.preencher(proposta, outra_perfil, posicao=3)
        indisponivel = self.preencher(
            proposta,
            self.criar_perfil(4),
            posicao=4,
        )
        indisponivel.perfil_alpinista.disponivel_mme = False
        indisponivel.perfil_alpinista.save(update_fields=['disponivel_mme'])
        disponivel = self.preencher(
            proposta,
            self.criar_perfil(5),
            papel='coordenador',
            posicao=1,
        )
        self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/retirar-item/',
            {'item_id': historico.pk},
            format='json',
        )
        self.alocar(aproveitado_perfil, 'violeiros')
        self.alocar(outra_perfil, 'apoio')

        response = self.client.get(
            f'/api/propostas-violeiros/{proposta.pk}/resumo/'
        )
        situacoes = {
            item['id']: item['situacao'] for item in response.json()['itens']
        }

        self.assertEqual(situacoes[historico.pk], 'HISTORICO')
        self.assertEqual(situacoes[disponivel.pk], 'DISPONIVEL')
        self.assertEqual(
            situacoes[aproveitado.pk],
            'APROVEITADO_VIOLEIROS',
        )
        self.assertEqual(situacoes[outra.pk], 'INDISPONIVEL_OUTRA_EQUIPE')
        self.assertEqual(situacoes[indisponivel.pk], 'INDISPONIVEL_MME')

    def test_disponibilidade_reflete_em_multiplas_propostas_sem_dual_write(self):
        perfil = self.criar_perfil(1)
        proposta_a = self.criar_proposta(nome='A')
        proposta_b = self.criar_proposta(nome='B')
        item_a = self.preencher(proposta_a, perfil)
        item_b = self.preencher(proposta_b, perfil)
        self.alocar(perfil, 'apoio')

        respostas = (
            self.client.get(
                f'/api/propostas-violeiros/{proposta_a.pk}/resumo/'
            ).json(),
            self.client.get(
                f'/api/propostas-violeiros/{proposta_b.pk}/resumo/'
            ).json(),
        )

        self.assertTrue(all(
            resposta['itens'][0]['situacao']
            == 'INDISPONIVEL_OUTRA_EQUIPE'
            for resposta in respostas
        ))
        item_a.refresh_from_db()
        item_b.refresh_from_db()
        self.assertTrue(item_a.vigente)
        self.assertTrue(item_b.vigente)

    def test_fichas_aproveita_candidato_criando_somente_convite_de_trabalho(self):
        proposta = self.criar_proposta()
        item = self.preencher(
            proposta,
            self.criar_perfil(1),
            papel='coordenador',
        )
        role_oficial = self.criar_role('violeiros')
        self.autenticar(SiaRole.FICHAS)

        response = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/aproveitar-candidato/',
            {
                'item_id': item.pk,
                'role_equipe_id': role_oficial.pk,
                'confirmar_avisos': True,
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        convite = ConviteEncontro.objects.get(pk=response.json()['id'])
        self.assertEqual(convite.finalidade, ConviteEncontro.Finalidade.TRABALHAR)
        self.assertEqual(convite.status, ConviteEncontro.Status.CONVIDADO)
        self.assertEqual(convite.role_trabalho_proposta, role_oficial)
        self.assertEqual(item.papel_sugerido, 'coordenador')
        self.assertEqual(role_oficial.codigo, 'integrante')
        self.assertFalse(TrabalhoEncontro.objects.exists())

    def test_diretoria_pode_aproveitar_candidatos_de_propostas_distintas(self):
        proposta_a = self.criar_proposta(nome='A')
        proposta_b = self.criar_proposta(nome='B')
        itens = (
            self.preencher(proposta_a, self.criar_perfil(1)),
            self.preencher(proposta_b, self.criar_perfil(2)),
        )
        self.autenticar(SiaRole.DIRETORIA)

        responses = [
            self.client.post(
                f'/api/propostas-violeiros/{proposta.pk}/aproveitar-candidato/',
                {'item_id': item.pk, 'confirmar_avisos': True},
                format='json',
            )
            for proposta, item in zip((proposta_a, proposta_b), itens)
        ]

        self.assertTrue(all(
            response.status_code == status.HTTP_200_OK
            for response in responses
        ))
        self.assertEqual(ConviteEncontro.objects.count(), 2)
        self.assertFalse(TrabalhoEncontro.objects.exists())

    def test_mme_nao_pode_executar_aproveitamento_oficial(self):
        proposta = self.criar_proposta()
        item = self.preencher(proposta, self.criar_perfil(1))
        self.autenticar(SiaRole.MME)

        response = self.client.post(
            f'/api/propostas-violeiros/{proposta.pk}/aproveitar-candidato/',
            {'item_id': item.pk, 'confirmar_avisos': True},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_proposta_nao_cria_trabalho_frequencia_ou_historico_permanente(self):
        proposta = self.criar_proposta()
        self.preencher(proposta, self.criar_perfil(1))

        self.assertFalse(ConviteEncontro.objects.exists())
        self.assertFalse(TrabalhoEncontro.objects.exists())
        self.assertFalse(Frequencia.objects.exists())
        self.assertFalse(VinculoEncontroLegado.objects.exists())

    def test_metodos_nao_expostos_retornam_405(self):
        proposta = self.criar_proposta()

        self.assertEqual(
            self.client.put(
                f'/api/propostas-violeiros/{proposta.pk}/',
                {'nome': 'Inválida'},
                format='json',
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        self.assertEqual(
            self.client.delete(
                f'/api/propostas-violeiros/{proposta.pk}/'
            ).status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_item_de_outra_proposta_retorna_404(self):
        proposta_a = self.criar_proposta(nome='A')
        proposta_b = self.criar_proposta(nome='B')
        item = self.preencher(proposta_a, self.criar_perfil(1))

        response = self.client.post(
            f'/api/propostas-violeiros/{proposta_b.pk}/retirar-item/',
            {'item_id': item.pk},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class PropostaVioleirosSerializerContractTests(AuthenticatedAPITestCase):
    def test_serializers_possuem_allowlists_explicitas(self):
        contracts = (
            (
                PropostaVioleirosSerializer,
                (
                    'id',
                    'encontro_id',
                    'nome',
                    'status',
                    'encerrada_em',
                    'total_posicoes',
                    'total_disponivel',
                    'vagas_disponiveis',
                    'completa',
                    'precisa_completar',
                    'itens',
                    'criada_em',
                    'atualizada_em',
                ),
            ),
            (
                ItemPropostaVioleirosSerializer,
                (
                    'id',
                    'perfil_alpinista_id',
                    'pessoa_id',
                    'pessoa_nome',
                    'musica',
                    'papel_sugerido',
                    'posicao',
                    'vigente',
                    'retirado_em',
                    'situacao',
                    'disponivel',
                    'avaliacao',
                    'criado_em',
                ),
            ),
            (
                CriacaoPropostaVioleirosCommandSerializer,
                ('encontro_id', 'nome'),
            ),
            (
                EdicaoPropostaVioleirosCommandSerializer,
                ('nome',),
            ),
            (
                PreenchimentoPropostaVioleirosCommandSerializer,
                ('perfil_alpinista_id', 'papel_sugerido', 'posicao'),
            ),
            (
                ItemPropostaVioleirosCommandSerializer,
                ('item_id',),
            ),
            (
                SubstituicaoPropostaVioleirosCommandSerializer,
                ('item_id', 'perfil_alpinista_id'),
            ),
            (
                AproveitamentoPropostaVioleirosCommandSerializer,
                ('item_id', 'role_equipe_id', 'confirmar_avisos'),
            ),
        )

        for serializer_class, expected in contracts:
            with self.subTest(serializer=serializer_class.__name__):
                self.assertEqual(
                    tuple(serializer_class().fields),
                    expected,
                )

    def test_command_serializer_rejeita_campos_extras(self):
        serializer = EdicaoPropostaVioleirosCommandSerializer(data={
            'nome': 'Proposta',
            'campo_indevido': True,
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('campos_extras', serializer.errors)
