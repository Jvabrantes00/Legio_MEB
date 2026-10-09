from datetime import date

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from core.models import (
    Alpinista,
    CorrespondenciaCadastralInscricao,
    DadosCuidadoInscricao,
    DadosDeclaradosInscricao,
    DadosEsppaInscricao,
    Inscricao,
    InscricaoEncontro,
    PerfilAlpinista,
    Pessoa,
    ResponsavelDeclaradoInscricao,
    VinculoConjugal,
)
from core.tests.factories import make_encontro


class InscricaoEncontroModelTests(TestCase):
    cpf_compartilhado = '52998224725'

    def setUp(self):
        self.encontro = make_encontro()

    def criar_inscricao(self, **overrides):
        valores = {
            'encontro': self.encontro,
            'origem': InscricaoEncontro.Origem.PUBLICA,
        }
        valores.update(overrides)
        return InscricaoEncontro.objects.create(**valores)

    def criar_dados(self, inscricao, **overrides):
        valores = {
            'inscricao': inscricao,
            'nome_completo': 'Pessoa declarada',
            'data_nascimento': date(2010, 1, 1),
            'cpf': self.cpf_compartilhado,
            'email': 'declarado@example.test',
            'telefone_whatsapp': '',
            'cep': '70000-000',
            'logradouro': 'Rua declarada',
            'numero': '10',
            'bairro': 'Bairro declarado',
            'cidade': 'Brasília',
            'uf': 'DF',
            'como_conheceu': DadosDeclaradosInscricao.ComoConheceu.INDICACAO,
        }
        valores.update(overrides)
        return DadosDeclaradosInscricao.objects.create(**valores)

    def test_cria_sem_pessoa_sem_efeitos_canonicos(self):
        inscricao = self.criar_inscricao()

        self.assertIsNone(inscricao.pessoa_id)
        self.assertEqual(inscricao.status, InscricaoEncontro.Status.ENVIADA)
        self.assertFalse(Pessoa.objects.exists())
        self.assertFalse(PerfilAlpinista.objects.exists())
        self.assertFalse(Alpinista.objects.exists())

    def test_cria_com_pessoa_e_preserva_relacao_opcional(self):
        pessoa = Pessoa.objects.create(nome='Pessoa resolvida')

        inscricao = self.criar_inscricao(pessoa=pessoa)

        self.assertEqual(inscricao.pessoa, pessoa)
        self.assertEqual(list(pessoa.inscricoes_por_encontro.all()), [inscricao])

    def test_unicidade_pessoa_encontro_inclui_inscricao_cancelada(self):
        pessoa = Pessoa.objects.create(nome='Pessoa única')
        self.criar_inscricao(pessoa=pessoa)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_inscricao(
                pessoa=pessoa,
                status=InscricaoEncontro.Status.CANCELADA,
                cancelada_em=timezone.now(),
            )

    def test_multiplas_nao_resolvidas_e_cpf_declarado_repetido_sao_permitidos(self):
        primeira = self.criar_inscricao()
        segunda = self.criar_inscricao()

        dados_primeira = self.criar_dados(primeira)
        dados_segunda = self.criar_dados(
            segunda,
            email='outra@example.test',
        )

        self.assertNotEqual(primeira.pk, segunda.pk)
        self.assertEqual(dados_primeira.cpf, dados_segunda.cpf)

    def test_status_cancelado_e_origens_sao_representaveis(self):
        cancelada_em = timezone.now()
        publica = self.criar_inscricao(
            status=InscricaoEncontro.Status.CANCELADA,
            cancelada_em=cancelada_em,
        )
        administrativa = self.criar_inscricao(
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )

        self.assertEqual(publica.cancelada_em, cancelada_em)
        self.assertEqual(administrativa.origem, 'administrativa')

    def test_cancelamento_exige_timestamp(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_inscricao(status=InscricaoEncontro.Status.CANCELADA)

    def test_encontro_e_pessoa_resolvida_sao_protegidos(self):
        pessoa = Pessoa.objects.create(nome='Pessoa protegida')
        self.criar_inscricao(pessoa=pessoa)

        with self.assertRaises(ProtectedError):
            self.encontro.delete()
        with self.assertRaises(ProtectedError):
            pessoa.delete()

    def test_componentes_sao_modulares_e_one_to_one(self):
        inscricao = self.criar_inscricao()
        dados = self.criar_dados(inscricao)
        responsavel = ResponsavelDeclaradoInscricao.objects.create(
            inscricao=inscricao,
            nome_completo='Responsável declarado',
            cpf='11144477735',
            parentesco='Mãe',
            telefone_whatsapp='61999990000',
        )
        cuidado = DadosCuidadoInscricao.objects.create(
            inscricao=inscricao,
            possui_alergias=DadosCuidadoInscricao.RespostaBinaria.NAO,
            possui_restricoes_intolerancias=(
                DadosCuidadoInscricao.RespostaBinaria.NAO
            ),
            usa_medicamentos=DadosCuidadoInscricao.RespostaBinaria.NAO,
            neurodivergencia_apoio=(
                DadosCuidadoInscricao.RespostaApoio.PREFERE_NAO_INFORMAR
            ),
        )
        esppa = DadosEsppaInscricao.objects.create(
            inscricao=inscricao,
            estado_civil=DadosEsppaInscricao.EstadoCivil.CASADO,
            nome_conjuge='Cônjuge declarado',
            telefone_conjuge='61988880000',
        )

        self.assertEqual(inscricao.dados_declarados, dados)
        self.assertEqual(inscricao.responsavel_declarado, responsavel)
        self.assertEqual(inscricao.dados_cuidado, cuidado)
        self.assertEqual(inscricao.dados_esppa, esppa)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_dados(inscricao, email='duplicado@example.test')

    def test_responsavel_tem_cpf_repetivel_e_nao_cria_pessoa(self):
        inscricoes = (self.criar_inscricao(), self.criar_inscricao())

        for indice, inscricao in enumerate(inscricoes):
            ResponsavelDeclaradoInscricao.objects.create(
                inscricao=inscricao,
                nome_completo=f'Responsável {indice}',
                cpf=self.cpf_compartilhado,
                parentesco='Pai',
                telefone_whatsapp=f'6199999000{indice}',
            )

        self.assertEqual(ResponsavelDeclaradoInscricao.objects.count(), 2)
        self.assertFalse(Pessoa.objects.exists())

    def test_contato_exige_email_ou_telefone(self):
        inscricao = self.criar_inscricao()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_dados(inscricao, email='', telefone_whatsapp='')

    def test_sacramentos_preservam_quatro_estados_declarativos(self):
        estados = (
            DadosDeclaradosInscricao.Sacramento.SIM,
            DadosDeclaradosInscricao.Sacramento.NAO,
            DadosDeclaradosInscricao.Sacramento.NAO_SEI,
            DadosDeclaradosInscricao.Sacramento.NAO_INFORMADO,
        )

        for estado in estados:
            with self.subTest(estado=estado):
                dados = self.criar_dados(
                    self.criar_inscricao(),
                    email=f'{estado}@example.test',
                    batismo=estado,
                    primeira_comunhao=estado,
                    crisma=estado,
                )
                self.assertEqual(dados.batismo, estado)

    def test_snapshot_atual_e_schema_positivo_sao_suportados(self):
        inscricao = self.criar_inscricao()
        snapshot = {'schema': 1, 'origem': 'submissao_atual'}

        dados = self.criar_dados(
            inscricao,
            snapshot_schema_version=1,
            snapshot_atual=snapshot,
        )

        self.assertEqual(dados.snapshot_atual, snapshot)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_dados(
                self.criar_inscricao(),
                email='schema-invalido@example.test',
                snapshot_schema_version=0,
            )

    def test_cuidado_e_separado_e_nao_possui_resultado_de_elegibilidade(self):
        cuidado = DadosCuidadoInscricao.objects.create(
            inscricao=self.criar_inscricao(),
            possui_alergias=DadosCuidadoInscricao.RespostaBinaria.SIM,
            alergias='Informação restrita',
            neurodivergencia_apoio=(
                DadosCuidadoInscricao.RespostaApoio.PREFERE_NAO_INFORMAR
            ),
        )

        campos = {campo.name for campo in cuidado._meta.get_fields()}
        self.assertNotIn('elegibilidade', campos)
        self.assertNotIn('resultado', campos)

    def test_esppa_e_opcional_e_nao_cria_vinculo_canonico(self):
        escalada = self.criar_inscricao()
        self.assertFalse(hasattr(escalada, 'dados_esppa'))

        esppa = DadosEsppaInscricao.objects.create(
            inscricao=self.criar_inscricao(),
            estado_civil=DadosEsppaInscricao.EstadoCivil.SOLTEIRO,
            nome_referencia='Referência declarada',
            relacao_referencia=DadosEsppaInscricao.RelacaoReferencia.AMIGO,
            telefone_referencia='61977770000',
        )

        self.assertIsNotNone(esppa.pk)
        self.assertFalse(VinculoConjugal.objects.exists())
        self.assertFalse(Pessoa.objects.exists())

    def test_correspondencia_e_estrutura_sem_autoassociacao(self):
        inscricao = self.criar_inscricao()
        candidata = Pessoa.objects.create(nome='Pessoa candidata')

        correspondencia = CorrespondenciaCadastralInscricao.objects.create(
            inscricao=inscricao,
            pessoa_candidata=candidata,
            origem_sinal='cpf',
        )

        inscricao.refresh_from_db()
        self.assertEqual(
            correspondencia.status,
            CorrespondenciaCadastralInscricao.Status.SUGERIDA,
        )
        self.assertIsNone(inscricao.pessoa_id)

    def test_apenas_uma_correspondencia_aceita_por_inscricao(self):
        inscricao = self.criar_inscricao()
        decisor = get_user_model().objects.create_user(username='decisor')
        instante = timezone.now()
        for indice in range(2):
            candidata = Pessoa.objects.create(nome=f'Candidata {indice}')
            if indice == 0:
                CorrespondenciaCadastralInscricao.objects.create(
                    inscricao=inscricao,
                    pessoa_candidata=candidata,
                    origem_sinal='manual',
                    status=CorrespondenciaCadastralInscricao.Status.ACEITA,
                    decidida_por=decisor,
                    decidida_em=instante,
                )
            else:
                with self.assertRaises(IntegrityError), transaction.atomic():
                    CorrespondenciaCadastralInscricao.objects.create(
                        inscricao=inscricao,
                        pessoa_candidata=candidata,
                        origem_sinal='manual',
                        status=(
                            CorrespondenciaCadastralInscricao.Status.ACEITA
                        ),
                        decidida_por=decisor,
                        decidida_em=instante,
                    )

    def test_representacoes_nao_expoem_pii(self):
        inscricao = self.criar_inscricao()
        dados = self.criar_dados(
            inscricao,
            email='segredo@example.test',
            telefone_whatsapp='61999999999',
        )
        responsavel = ResponsavelDeclaradoInscricao.objects.create(
            inscricao=inscricao,
            nome_completo='Nome responsável sigiloso',
            cpf='11144477735',
            parentesco='Mãe',
            telefone_whatsapp='61888888888',
        )
        cuidado = DadosCuidadoInscricao.objects.create(
            inscricao=inscricao,
            medicamentos='Medicamento sigiloso',
        )

        representacoes = ' '.join(map(str, (
            inscricao,
            dados,
            responsavel,
            cuidado,
        )))
        for sensivel in (
            self.cpf_compartilhado,
            'segredo@example.test',
            '61999999999',
            '11144477735',
            '61888888888',
            'Medicamento sigiloso',
        ):
            self.assertNotIn(sensivel, representacoes)

    def test_model_legado_permanece_separado(self):
        campos_legados = {campo.name for campo in Inscricao._meta.get_fields()}

        self.assertNotIn('encontro', campos_legados)
        self.assertNotEqual(
            Inscricao._meta.db_table,
            InscricaoEncontro._meta.db_table,
        )
