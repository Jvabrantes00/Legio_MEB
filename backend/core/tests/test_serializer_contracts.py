from datetime import date

from django.utils import timezone
from rest_framework import status

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Pessoa,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoEncontroLegado as ParticipacaoEncontro,
)
from core.serializers import (
    EquipeEncontroSerializer,
    AlpinistaCompletoSerializer,
    HistoricoFormativoSerializer,
    PalestranteSessaoSerializer,
    SessaoFormativaSerializer,
    TrabalhoEncontroCommandSerializer,
    EncontroSerializer,
    EventoSerializer,
    FuncaoEncontroSerializer,
    PresencaPreparatoriaCommandSerializer,
)
from core.tests.base import AuthenticatedAPITestCase
from core.tests.factories import make_alpinista, make_encontro, make_funcao


class RemainingSerializerAllowlistTests(AuthenticatedAPITestCase):
    def test_serializers_restantes_possuem_allowlists_explicitas(self):
        contracts = (
            (
                EncontroSerializer,
                (
                    'id',
                    'status_encontro',
                    'encontro',
                    'tipo',
                    'data_referencia',
                    'data_exato',
                    'local',
                    'status',
                    'criado_em',
                    'participantes',
                ),
            ),
            (
                EventoSerializer,
                (
                    'id',
                    'status_evento',
                    'total_participantes',
                    'nome',
                    'data_evento',
                    'local',
                ),
            ),
            (
                FuncaoEncontroSerializer,
                ('id', 'nome', 'tipo', 'descricao_faq', 'ordem', 'eh_violeiro'),
            ),
            (
                PresencaPreparatoriaCommandSerializer,
                (
                    'id',
                    'reuniao_id',
                    'trabalho_id',
                    'status',
                    'justificativa',
                    'registrada_por_id',
                    'criado_em',
                    'atualizado_em',
                ),
            ),
            (
                TrabalhoEncontroCommandSerializer,
                (
                    'id',
                    'pessoa_id',
                    'encontro_id',
                    'convite_id',
                    'role_equipe_id',
                    'status',
                    'resultado_registrado_em',
                    'confirmar_avisos',
                    'avaliacao',
                    'criado_em',
                    'atualizado_em',
                ),
            ),
            (
                EquipeEncontroSerializer,
                (
                    'id',
                    'encontro_id',
                    'codigo',
                    'nome',
                    'ordem',
                    'capacidade_minima_recomendada',
                    'capacidade_maxima_recomendada',
                    'capacidade',
                    'composicao',
                    'roles',
                ),
            ),
            (
                PalestranteSessaoSerializer,
                (
                    'id',
                    'perfil_alpinista_id',
                    'nome_alpinista',
                    'nome_externo',
                    'status',
                    'ministrou_em',
                    'criado_em',
                    'atualizado_em',
                ),
            ),
            (
                SessaoFormativaSerializer,
                (
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
                ),
            ),
            (
                HistoricoFormativoSerializer,
                (
                    'palestrante_id',
                    'palestrante_nome',
                    'encontro_id',
                    'nome_encontro',
                    'tipo_encontro',
                    'data_encontro',
                    'tema_codigo',
                    'titulo',
                    'tipo_conteudo',
                    'ministrou_em',
                ),
            ),
        )

        for serializer_class, expected_fields in contracts:
            with self.subTest(serializer=serializer_class.__name__):
                self.assertNotEqual(serializer_class.Meta.fields, '__all__')
                self.assertEqual(serializer_class.Meta.fields, expected_fields)
                self.assertEqual(tuple(serializer_class().fields), expected_fields)


class AlpinistaCompletoContractTests(AuthenticatedAPITestCase):
    expected_fields = {
        'id',
        'cpf',
        'nome',
        'dataNascimento',
        'endereco',
        'email',
        'telefone',
        'nomePai',
        'telefonePai',
        'nomeMae',
        'telefoneMae',
        'restricaoSaude',
        'medicacao',
        'conheciaEscalada',
        'grupo',
        'status',
        'foto',
        'batizado',
        'primeira_comunhao',
        'crismado',
        'eh_violeiro',
        'canta',
        'is_neurodivergente',
        'tipo_neurodivergente',
        'idade_atual',
        'encontros_realizados',
        'historico_equipes',
        'historico_eventos',
    }

    def test_perfil_completo_tem_allowlist_explicita_e_contrato_preservado(self):
        alpinista = make_alpinista(
            cpf='52998224725',
            dataNascimento=date(2000, 1, 1),
            endereco='Endereço reservado',
            restricaoSaude='Dado reservado',
            medicacao='Dado reservado',
            is_neurodivergente=True,
            tipo_neurodivergente='Dado reservado',
        )

        response = self.client.get(f'/api/alpinistas/{alpinista.pk}/')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(set(response.json()), self.expected_fields)
        self.assertNotEqual(AlpinistaCompletoSerializer.Meta.fields, '__all__')
        self.assertEqual(
            set(AlpinistaCompletoSerializer.Meta.fields),
            self.expected_fields,
        )

    def test_campos_calculados_e_id_sao_somente_leitura(self):
        self.assertTrue(
            {
                'id',
                'idade_atual',
                'encontros_realizados',
                'historico_equipes',
                'historico_eventos',
            }.issubset(AlpinistaCompletoSerializer.Meta.read_only_fields)
        )


class ParticipacaoEncontroContractTests(AuthenticatedAPITestCase):
    def test_alpinista_aninhado_expoe_somente_id_e_nome(self):
        alpinista = make_alpinista(
            cpf='52998224725',
            endereco='Endereço que não deve aparecer',
            restricaoSaude='Saúde que não deve aparecer',
            medicacao='Medicação que não deve aparecer',
            tipo_neurodivergente='Dado que não deve aparecer',
        )
        participacao = ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=make_encontro(),
            funcao=make_funcao(),
        )

        response = self.client.get(
            f'/api/participacoes-encontros/{participacao.pk}/'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json()['alpinista'],
            {'id': alpinista.pk, 'nome': alpinista.nome},
        )
        self.assertEqual(set(response.json()['alpinista']), {'id', 'nome'})


class HistoricoEquipeContractTests(AuthenticatedAPITestCase):
    def test_historico_preserva_formato_e_conta_somente_trabalho_realizado(self):
        pessoa = Pessoa.objects.create(nome='Pessoa com histórico canônico')
        alpinista = make_alpinista(pessoa=pessoa)
        encontro = make_encontro(encontro='Escalada canônica')
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='dirigentes',
            nome='Dirigentes',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='coordenador',
            nome='Coordenador',
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
        TrabalhoEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            convite=convite,
            role_equipe=role,
            status=TrabalhoEncontro.Status.TRABALHOU,
            resultado_registrado_em=timezone.now(),
        )
        ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=make_encontro(encontro='Escala legada'),
            funcao=make_funcao(nome='Legado não comprovado', tipo='equipe'),
            cor_grupo='azul',
        )

        payload = AlpinistaCompletoSerializer(alpinista).data

        self.assertEqual(payload['historico_equipes'], [{
            'nome_encontro': 'Escalada canônica',
            'equipe': 'Dirigentes',
            'tipo_encontro': Encontro.Tipo.ESCALADA,
            'data': '01/01/2030',
            'cor_grupo': None,
        }])
