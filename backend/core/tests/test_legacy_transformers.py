from django.test import SimpleTestCase

from core.legacy.issues import IssueCode
from core.legacy.transformers import (
    transform_alpinista,
    transform_avc_group,
    transform_encounter_team,
    transform_encontro,
    transform_event,
    transform_event_team,
    transform_group,
    transform_user,
)


class LegacyTransformerTests(SimpleTestCase):
    def issue_codes(self, result):
        return {issue.code for issue in result.issues}

    def test_alpinista_cria_dto_canonico_e_preserva_deferred(self):
        result = transform_alpinista({
            'CD_REGISTRO': '10',
            'NO_ALPINISTA': '  João da Silva  ',
            'DT_NASCIMENTO': '2000-05-20',
            'TX_APELIDO': ' João ',
            'TX_ENDERECO': ' Rua Um ',
            'CD_CEP': '70000-000',
            'IN_BAIRRO': 'Centro',
            'NO_CIDADE': 'Brasília',
            'SG_UF': 'df',
            'CD_DDD': '61',
            'NR_TELEFONE': '98888-7777',
            'NR_TELEFONE1': ' (61) 98888-7777 ',
            'CD_EMAIL': ' JOAO@EXAMPLE.COM ',
            'NR_CPF': '529.982.247-25',
            'IN_VIOLEIRO': 'S',
            'URL_FOTO': 'fotos/joao.jpg',
            'NO_ESCALADA': 12,
            'CD_GRUPO': '7',
            'AMIGO_BANCO': 'dado financeiro preservado',
            'CAMPO_SEM_SEMANTICA': 'valor bruto preservado',
        })

        self.assertTrue(result.is_valid)
        self.assertEqual(result.value.legacy_id, 10)
        self.assertEqual(result.value.name, 'João da Silva')
        self.assertEqual(result.value.email, 'joao@example.com')
        self.assertEqual(result.value.phones, ('61988887777',))
        self.assertEqual(result.value.cpf, '52998224725')
        self.assertIs(result.value.is_violeiro, True)
        self.assertEqual(result.value.deferred['NO_ESCALADA'], 12)
        self.assertEqual(result.value.deferred['CD_GRUPO'], '7')
        self.assertIn('AMIGO_BANCO', result.value.deferred)
        self.assertEqual(
            result.value.legacy_metadata['CAMPO_SEM_SEMANTICA'],
            'valor bruto preservado',
        )

    def test_dois_telefones_diferentes_nao_sao_escolhidos_silenciosamente(self):
        result = transform_alpinista({
            'CD_REGISTRO': 11,
            'NO_ALPINISTA': 'Pessoa',
            'CD_DDD': '61',
            'NR_TELEFONE': '98888-7777',
            'NR_TELEFONE1': '97777-6666',
        })

        self.assertEqual(result.value.phones, ('61988887777', '61977776666'))
        self.assertIn(IssueCode.PHONE_CONFLICT, self.issue_codes(result))
        self.assertFalse(result.is_valid)

    def test_cpf_invalido_e_nome_ausente_geram_issues_seguras(self):
        invalid_cpf = '111.111.111-11'
        result = transform_alpinista({
            'CD_REGISTRO': 12,
            'NO_ALPINISTA': ' ',
            'NR_CPF': invalid_cpf,
        })

        self.assertIn(IssueCode.INVALID_CPF, self.issue_codes(result))
        self.assertIn(IssueCode.MISSING_REQUIRED_NAME, self.issue_codes(result))
        self.assertNotIn(invalid_cpf, ' '.join(i.description for i in result.issues))

    def test_encontro_com_tipo_desconhecido_falha_sem_inventar_status(self):
        result = transform_encontro({
            'CD_ENCONTRO': 20,
            'DT_ENCONTRO': '2010-01-02',
            'NO_ENCONTRO': 'Escalada histórica',
            'IN_TIPO_ENCONTRO': 'E',
            'DT_ENCONTRO_COMPLETA': '1 e 2 de janeiro',
        })

        self.assertIn(IssueCode.UNKNOWN_ENCOUNTER_TYPE, self.issue_codes(result))
        self.assertIsNone(result.value.encounter_type)
        self.assertIsNone(result.value.deferred['status'])

    def test_funcao_desconhecida_falha_sem_get_or_create(self):
        result = transform_encounter_team({
            'CD_EQUIPE': 30,
            'CD_ENCONTRO': 20,
            'CD_REGISTRO': 10,
            'NR_ORDEM': '2.0',
            'NM_FUNCAO': 'Descrição ainda não perfilada',
        })

        self.assertIn(IssueCode.UNKNOWN_FUNCTION, self.issue_codes(result))
        self.assertIsNone(result.value.canonical_function)

    def test_grupo_preserva_pessoas_sem_resolver_por_nome(self):
        result = transform_group({
            'CD_GRUPO': 40,
            'DT_CRIACAO': '2015-03-04',
            'NO_GRUPO': 'Grupo Esperança',
            'NO_PADRINHO': 10,
            'NO_MADRINHA': 'Nome possivelmente ambíguo',
            'NO_COORDENADOR1': 'Outra pessoa',
            'IN_ATIVO': 'S',
        })

        self.assertTrue(result.is_valid)
        self.assertEqual(result.value.unresolved_people['NO_PADRINHO'], 10)
        self.assertEqual(
            result.value.unresolved_people['NO_MADRINHA'],
            'Nome possivelmente ambíguo',
        )

    def test_grupo_avc_permanece_contrato_separado(self):
        result = transform_avc_group({
            'CD_GRUPO_AVC': 50,
            'NO_GRUPO_AVC': 'Grupo AVC',
            'DS_GRUPO_AVC': 'Descrição',
        })

        self.assertEqual(result.value.legacy_id, 50)
        self.assertEqual(result.value.name, 'Grupo AVC')

    def test_evento_e_equipe_de_evento_permanecem_conceitos_distintos(self):
        event = transform_event({
            'CD_EVENTO': 60,
            'DT_EVENTO': '2020-01-01',
            'NO_EVENTO': 'Evento legado',
            'IN_TIPO_EVENTO': 'X',
            'NO_TIPO_EVENTO': 'Tipo ainda desconhecido',
        })
        team = transform_event_team({
            'CD_EVENTO_EQUIPE': 61,
            'CD_EVENTO': 60,
            'CD_REGISTRO': 10,
            'NM_FUNCAO': 'Função desconhecida',
        })

        self.assertEqual(event.value.legacy_id, 60)
        self.assertEqual(team.value.event_legacy_id, 60)
        self.assertIn(IssueCode.UNKNOWN_FUNCTION, self.issue_codes(team))
        self.assertNotEqual(type(event.value), type(team.value))

    def test_usuario_descarta_credencial_e_exige_mapping_de_tipo(self):
        historical_secret = 'valor-historico-nao-reutilizavel'
        result = transform_user({
            'usu_nome': 'Operador legado',
            'usu_login': 'operador',
            'usu_senha': historical_secret,
            'usu_tipo': 'tipo ainda desconhecido',
            'grupo': 'grupo legado',
        })

        self.assertIn(IssueCode.UNKNOWN_USER_TYPE, self.issue_codes(result))
        self.assertIn(IssueCode.LEGACY_SECRET_IGNORED, self.issue_codes(result))
        self.assertNotIn('usu_senha', result.value.legacy_metadata)
        self.assertNotIn(
            historical_secret,
            ' '.join(issue.description for issue in result.issues),
        )
