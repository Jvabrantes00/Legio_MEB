from datetime import date, datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from core.models import (
    Alpinista,
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    CorrespondenciaCadastralInscricao,
    DadosCuidadoInscricao,
    DadosDeclaradosInscricao,
    DadosEsppaInscricao,
    DiaEncontro,
    Inscricao,
    InscricaoEncontro,
    PerfilAlpinista,
    Pessoa,
    ResponsavelDeclaradoInscricao,
    VinculoConjugal,
)
from core.services import inscricoes_encontro as services
from core.services.inscricoes_encontro import (
    ErroFichaInscricao,
    atualizar_ficha_inscricao,
    cancelar_inscricao_encontro,
    reativar_inscricao_encontro,
    submeter_inscricao_encontro,
)
from core.tests.factories import make_encontro


class InscricaoEncontroServiceTests(TestCase):
    def setUp(self):
        self.momento = datetime(
            2030,
            1,
            15,
            12,
            tzinfo=datetime_timezone.utc,
        )
        self.encontro = make_encontro(
            tipo='Escalada',
            data_referencia=self.momento.date(),
        )
        self.criar_configuracao(self.encontro)
        self.primeiro_dia = date(2030, 6, 1)
        self.ultimo_dia = date(2030, 6, 3)
        self.criar_calendario_oficial(
            self.encontro,
            self.primeiro_dia,
            self.ultimo_dia,
        )

    def criar_configuracao(self, encontro, **overrides):
        valores = {
            'encontro': encontro,
            'capacidade': 40,
            'idade_minima': 15,
            'idade_maxima': 29,
            'inscricoes_abrem_em': self.momento - timedelta(days=10),
            'inscricoes_encerram_em': self.momento + timedelta(days=10),
        }
        valores.update(overrides)
        return ConfiguracaoEncontristasEncontro.objects.create(**valores)

    def criar_calendario_oficial(
        self,
        encontro,
        primeiro_dia,
        ultimo_dia=None,
        *,
        oficializado=True,
    ):
        calendario = CalendarioEncontro.objects.create(
            encontro=encontro,
            versao=1,
            vigente=True,
            oficializado_em=self.momento if oficializado else None,
        )
        DiaEncontro.objects.create(
            calendario=calendario,
            ordem=1,
            data=primeiro_dia,
        )
        if ultimo_dia is not None:
            DiaEncontro.objects.create(
                calendario=calendario,
                ordem=2,
                data=ultimo_dia,
            )
        return calendario

    def dados_declarados(self, **overrides):
        valores = {
            'nome_completo': '  Pessoa Declarada  ',
            'apelido': ' Pessoa ',
            'data_nascimento': self.momento.date().replace(year=2000),
            'cpf': '529.982.247-25',
            'email': ' PESSOA@EXAMPLE.TEST ',
            'telefone_whatsapp': '',
            'cep': '70000-000',
            'logradouro': ' Rua Declarada ',
            'numero': '10',
            'complemento': '',
            'bairro': 'Bairro',
            'cidade': 'Brasília',
            'uf': 'df',
            'como_conheceu': DadosDeclaradosInscricao.ComoConheceu.INDICACAO,
            'como_conheceu_outro': '',
            'batismo': DadosDeclaradosInscricao.Sacramento.SIM,
            'primeira_comunhao': DadosDeclaradosInscricao.Sacramento.NAO,
            'crisma': DadosDeclaradosInscricao.Sacramento.NAO_SEI,
        }
        valores.update(overrides)
        return valores

    def dados_cuidado(self, **overrides):
        valores = {
            'possui_alergias': DadosCuidadoInscricao.RespostaBinaria.NAO,
            'alergias': '',
            'possui_restricoes_intolerancias': (
                DadosCuidadoInscricao.RespostaBinaria.NAO
            ),
            'restricoes_intolerancias': '',
            'usa_medicamentos': DadosCuidadoInscricao.RespostaBinaria.NAO,
            'medicamentos': '',
            'horarios_medicamentos': '',
            'observacoes_medicamentos': '',
            'neurodivergencia_apoio': DadosCuidadoInscricao.RespostaApoio.NAO,
            'neurodivergencia_condicao': '',
            'necessidades_apoio': '',
            'sensibilidades_desconfortos': '',
            'o_que_ajuda': '',
            'outras_informacoes': '',
            'observacoes': '',
        }
        valores.update(overrides)
        return valores

    def responsavel(self, **overrides):
        valores = {
            'nome_completo': 'Responsável Declarado',
            'cpf': '111.444.777-35',
            'parentesco': 'Mãe',
            'telefone_whatsapp': '61999990000',
            'email': '',
        }
        valores.update(overrides)
        return valores

    def dados_esppa(self, **overrides):
        valores = {
            'estado_civil': DadosEsppaInscricao.EstadoCivil.SOLTEIRO,
            'nome_conjuge': '',
            'telefone_conjuge': '',
            'nome_referencia': 'Pessoa de Referência',
            'relacao_referencia': DadosEsppaInscricao.RelacaoReferencia.AMIGO,
            'telefone_referencia': '61988880000',
        }
        valores.update(overrides)
        return valores

    def submeter(self, **overrides):
        valores = {
            'encontro': self.encontro,
            'origem': InscricaoEncontro.Origem.PUBLICA,
            'dados_declarados': self.dados_declarados(),
            'dados_cuidado': self.dados_cuidado(),
            'momento': self.momento,
        }
        valores.update(overrides)
        return submeter_inscricao_encontro(**valores)

    def test_submissao_completa_e_atomica_constroi_snapshot_normalizado(self):
        inscricao = self.submeter(snapshot_schema_version=2)

        dados = inscricao.dados_declarados
        self.assertEqual(dados.nome_completo, 'Pessoa Declarada')
        self.assertEqual(dados.cpf, '52998224725')
        self.assertEqual(dados.email, 'pessoa@example.test')
        self.assertEqual(dados.uf, 'DF')
        self.assertEqual(dados.snapshot_schema_version, 2)
        self.assertEqual(
            dados.snapshot_atual['participante']['data_nascimento'],
            '2000-01-15',
        )
        self.assertEqual(
            dados.snapshot_atual['participante']['nome_completo'],
            dados.nome_completo,
        )
        self.assertEqual(dados.snapshot_atual['schema_version'], 2)
        self.assertTrue(hasattr(inscricao, 'dados_cuidado'))
        self.assertFalse(hasattr(inscricao, 'responsavel_declarado'))
        self.assertFalse(hasattr(inscricao, 'dados_esppa'))

    def test_falha_de_componente_reverte_toda_submissao(self):
        original = services._criar_componente

        def criar_e_falhar(model, inscricao, valores):
            resultado = original(model, inscricao, valores)
            if model is DadosCuidadoInscricao:
                raise RuntimeError('falha controlada')
            return resultado

        with patch.object(
            services,
            '_criar_componente',
            side_effect=criar_e_falhar,
        ), self.assertRaisesRegex(RuntimeError, 'falha controlada'):
            self.submeter()

        self.assertFalse(InscricaoEncontro.objects.exists())
        self.assertFalse(DadosDeclaradosInscricao.objects.exists())
        self.assertFalse(DadosCuidadoInscricao.objects.exists())

    def test_submissao_nao_cria_pessoa_perfil_correspondencia_ou_legado(self):
        self.submeter()

        self.assertFalse(Pessoa.objects.exists())
        self.assertFalse(PerfilAlpinista.objects.exists())
        self.assertFalse(Alpinista.objects.exists())
        self.assertFalse(CorrespondenciaCadastralInscricao.objects.exists())
        self.assertFalse(Inscricao.objects.exists())

    def test_contato_aceita_somente_email_ou_somente_telefone(self):
        por_email = self.submeter(
            dados_declarados=self.dados_declarados(
                telefone_whatsapp='',
            ),
        )
        por_telefone = self.submeter(
            dados_declarados=self.dados_declarados(
                cpf=None,
                email='',
                telefone_whatsapp='61999990000',
            ),
        )

        self.assertEqual(
            por_email.dados_declarados.email,
            'pessoa@example.test',
        )
        self.assertEqual(
            por_telefone.dados_declarados.telefone_whatsapp,
            '61999990000',
        )

    def test_contato_ausente_e_rejeitado_antes_do_banco(self):
        with self.assertRaises(ErroFichaInscricao) as contexto:
            self.submeter(
                dados_declarados=self.dados_declarados(
                    email='',
                    telefone_whatsapp='',
                ),
            )

        self.assertIn('contato', contexto.exception.message_dict)
        self.assertFalse(InscricaoEncontro.objects.exists())

    def test_publica_exige_configuracao_e_janela_aberta(self):
        encontro_sem_configuracao = make_encontro()
        with self.assertRaises(ErroFichaInscricao) as ausente:
            self.submeter(encontro=encontro_sem_configuracao)
        self.assertIn('janela', ausente.exception.message_dict)

        with self.assertRaises(ErroFichaInscricao) as fechada:
            self.submeter(momento=self.momento + timedelta(days=11))
        self.assertIn('janela', fechada.exception.message_dict)

    def test_administrativa_nao_inventa_dependencia_da_janela(self):
        encontro_sem_configuracao = make_encontro()
        self.criar_calendario_oficial(
            encontro_sem_configuracao,
            self.primeiro_dia,
        )

        inscricao = self.submeter(
            encontro=encontro_sem_configuracao,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )

        self.assertEqual(
            inscricao.origem,
            InscricaoEncontro.Origem.ADMINISTRATIVA,
        )

    def test_17_anos_no_primeiro_dia_exige_responsavel_completo(self):
        menor = self.dados_declarados(
            data_nascimento=date(2012, 7, 1),
            cpf=None,
        )
        with self.assertRaises(ErroFichaInscricao) as ausente:
            self.submeter(dados_declarados=menor)
        self.assertIn('responsavel', ausente.exception.message_dict)

        with self.assertRaises(ErroFichaInscricao) as incompleto:
            self.submeter(
                dados_declarados=menor,
                responsavel=self.responsavel(telefone_whatsapp=''),
            )
        self.assertIn('telefone_whatsapp', incompleto.exception.message_dict)

        inscricao = self.submeter(
            dados_declarados=menor,
            responsavel=self.responsavel(),
        )
        self.assertEqual(
            inscricao.responsavel_declarado.cpf,
            '11144477735',
        )
        self.assertIsNone(inscricao.pessoa_id)

    def test_17_no_primeiro_dia_e_18_durante_encontro_continua_menor(self):
        participante = self.dados_declarados(
            data_nascimento=date(2012, 6, 2),
            cpf=None,
        )

        with self.assertRaises(ErroFichaInscricao) as contexto:
            self.submeter(dados_declarados=participante)

        self.assertIn('responsavel', contexto.exception.message_dict)

    def test_18_anos_no_primeiro_dia_nao_exige_responsavel(self):
        inscricao = self.submeter(
            dados_declarados=self.dados_declarados(
                data_nascimento=date(2012, 6, 1),
            ),
        )

        self.assertFalse(hasattr(inscricao, 'responsavel_declarado'))

    def test_adulto_pode_informar_contato_sem_cpf(self):
        inscricao = self.submeter(
            responsavel=self.responsavel(cpf=None),
        )

        contato = inscricao.responsavel_declarado
        self.assertIsNone(contato.cpf)
        self.assertEqual(contato.parentesco, 'Mãe')
        self.assertEqual(
            inscricao.dados_declarados.snapshot_atual['responsavel']['cpf'],
            None,
        )
        self.assertFalse(Pessoa.objects.exists())
        self.assertFalse(CorrespondenciaCadastralInscricao.objects.exists())
        self.assertFalse(VinculoConjugal.objects.exists())

    def test_adulto_pode_informar_contato_com_cpf(self):
        inscricao = self.submeter(responsavel=self.responsavel())

        self.assertEqual(
            inscricao.responsavel_declarado.cpf,
            '11144477735',
        )

    def test_menor_rejeita_responsavel_sem_cpf(self):
        with self.assertRaises(ErroFichaInscricao) as contexto:
            self.submeter(
                dados_declarados=self.dados_declarados(
                    data_nascimento=date(2012, 7, 1),
                    cpf=None,
                ),
                responsavel=self.responsavel(cpf=None),
            )

        self.assertIn('cpf', contexto.exception.message_dict)

    def test_cpf_de_responsavel_pode_repetir_entre_irmaos(self):
        menor = self.dados_declarados(
            data_nascimento=date(2012, 7, 1),
            cpf=None,
        )
        primeira = self.submeter(
            dados_declarados=menor,
            responsavel=self.responsavel(),
        )
        segunda = self.submeter(
            dados_declarados={
                **menor,
                'nome_completo': 'Irmão da Pessoa Declarada',
                'email': 'irmao@example.test',
            },
            responsavel=self.responsavel(),
        )

        self.assertEqual(
            primeira.responsavel_declarado.cpf,
            segunda.responsavel_declarado.cpf,
        )
        self.assertEqual(ResponsavelDeclaradoInscricao.objects.count(), 2)
        self.assertFalse(Pessoa.objects.exists())

    def test_regra_nao_usa_data_original_da_submissao(self):
        adulto_no_encontro = self.dados_declarados(
            data_nascimento=date(2012, 3, 1),
            cpf=None,
        )

        inscricao = self.submeter(dados_declarados=adulto_no_encontro)

        self.assertFalse(hasattr(inscricao, 'responsavel_declarado'))

    def test_ausencia_de_calendario_oficial_rejeita_sem_fallback(self):
        encontro = make_encontro(
            data_referencia=date(1990, 1, 1),
        )
        self.criar_configuracao(encontro)
        self.criar_calendario_oficial(
            encontro,
            date(2030, 6, 1),
            oficializado=False,
        )

        with self.assertRaises(ErroFichaInscricao) as contexto:
            self.submeter(encontro=encontro)

        self.assertIn('calendario', contexto.exception.message_dict)
        self.assertFalse(
            InscricaoEncontro.objects.filter(encontro=encontro).exists(),
        )

    def test_como_conheceu_outro_exige_complemento(self):
        with self.assertRaises(ErroFichaInscricao) as contexto:
            self.submeter(
                dados_declarados=self.dados_declarados(
                    como_conheceu=DadosDeclaradosInscricao.ComoConheceu.OUTRO,
                    como_conheceu_outro='',
                ),
            )
        self.assertIn('como_conheceu_outro', contexto.exception.message_dict)

        inscricao = self.submeter(
            dados_declarados=self.dados_declarados(
                como_conheceu=DadosDeclaradosInscricao.ComoConheceu.PAROQUIA,
            ),
        )
        self.assertEqual(
            inscricao.dados_declarados.como_conheceu,
            DadosDeclaradosInscricao.ComoConheceu.PAROQUIA,
        )

    def test_sacramentos_preservam_quatro_estados_sem_inferencia(self):
        estados = (
            DadosDeclaradosInscricao.Sacramento.SIM,
            DadosDeclaradosInscricao.Sacramento.NAO,
            DadosDeclaradosInscricao.Sacramento.NAO_SEI,
            DadosDeclaradosInscricao.Sacramento.NAO_INFORMADO,
        )
        for indice, estado in enumerate(estados):
            with self.subTest(estado=estado):
                inscricao = self.submeter(
                    dados_declarados=self.dados_declarados(
                        cpf=None,
                        email=f'sacramento{indice}@example.test',
                        batismo=estado,
                        primeira_comunhao=estado,
                        crisma=estado,
                    ),
                )
                self.assertEqual(inscricao.dados_declarados.batismo, estado)

        omitida = self.dados_declarados(cpf=None, email='omitida@example.test')
        omitida.pop('batismo')
        inscricao = self.submeter(dados_declarados=omitida)
        self.assertEqual(
            inscricao.dados_declarados.batismo,
            DadosDeclaradosInscricao.Sacramento.NAO_INFORMADO,
        )

    def test_cuidado_aplica_condicionais_sem_efeito_de_elegibilidade(self):
        with self.assertRaises(ErroFichaInscricao) as alergia:
            self.submeter(
                dados_cuidado=self.dados_cuidado(
                    possui_alergias=DadosCuidadoInscricao.RespostaBinaria.SIM,
                ),
            )
        self.assertIn('alergias', alergia.exception.message_dict)

        with self.assertRaises(ErroFichaInscricao) as medicamento:
            self.submeter(
                dados_cuidado=self.dados_cuidado(
                    usa_medicamentos=DadosCuidadoInscricao.RespostaBinaria.SIM,
                    medicamentos='Medicamento declarado',
                ),
            )
        self.assertIn(
            'horarios_medicamentos',
            medicamento.exception.message_dict,
        )

        inscricao = self.submeter(
            dados_cuidado=self.dados_cuidado(
                possui_alergias=DadosCuidadoInscricao.RespostaBinaria.SIM,
                alergias='Informação declarada',
                usa_medicamentos=DadosCuidadoInscricao.RespostaBinaria.SIM,
                medicamentos='Medicamento declarado',
                horarios_medicamentos='Horário declarado',
                neurodivergencia_apoio=(
                    DadosCuidadoInscricao.RespostaApoio.SIM
                ),
                necessidades_apoio='Apoio declarado',
            ),
        )
        self.assertEqual(
            inscricao.dados_cuidado.necessidades_apoio,
            'Apoio declarado',
        )
        self.assertFalse(Inscricao.objects.exists())

    def test_escalada_nao_exige_esppa_e_rejeita_payload_contraditorio(self):
        inscricao = self.submeter()
        self.assertFalse(hasattr(inscricao, 'dados_esppa'))

        with self.assertRaises(ErroFichaInscricao) as contexto:
            self.submeter(dados_esppa=self.dados_esppa())
        self.assertIn('dados_esppa', contexto.exception.message_dict)

    def test_esppa_valida_conjuge_ou_referencia_sem_criar_vinculos(self):
        encontro = make_encontro(tipo='Esppa')
        self.criar_configuracao(encontro)
        self.criar_calendario_oficial(encontro, self.primeiro_dia)
        casado = self.submeter(
            encontro=encontro,
            dados_esppa=self.dados_esppa(
                estado_civil=DadosEsppaInscricao.EstadoCivil.CASADO,
                nome_conjuge='Cônjuge Declarado',
                telefone_conjuge='61977770000',
                nome_referencia='',
                relacao_referencia='',
                telefone_referencia='',
            ),
        )
        sem_conjuge = self.submeter(
            encontro=encontro,
            dados_declarados=self.dados_declarados(
                cpf=None,
                email='referencia@example.test',
            ),
            dados_esppa=self.dados_esppa(),
        )

        self.assertEqual(
            casado.dados_esppa.nome_conjuge,
            'Cônjuge Declarado',
        )
        self.assertEqual(
            sem_conjuge.dados_esppa.nome_referencia,
            'Pessoa de Referência',
        )
        self.assertFalse(Pessoa.objects.exists())
        self.assertFalse(VinculoConjugal.objects.exists())

    def test_esppa_rejeita_combinacoes_condicionais_incompletas(self):
        encontro = make_encontro(tipo='Esppa')
        self.criar_configuracao(encontro)
        self.criar_calendario_oficial(encontro, self.primeiro_dia)
        with self.assertRaises(ErroFichaInscricao) as casado:
            self.submeter(
                encontro=encontro,
                dados_esppa=self.dados_esppa(
                    estado_civil=DadosEsppaInscricao.EstadoCivil.CASADO,
                    nome_conjuge='Cônjuge',
                    telefone_conjuge='',
                    nome_referencia='',
                    relacao_referencia='',
                    telefone_referencia='',
                ),
            )
        self.assertIn('conjuge', casado.exception.message_dict)

        with self.assertRaises(ErroFichaInscricao) as referencia:
            self.submeter(
                encontro=encontro,
                dados_esppa=self.dados_esppa(telefone_referencia=''),
            )
        self.assertIn('referencia', referencia.exception.message_dict)

    def test_atualizacao_preserva_uuid_pessoa_e_linha_atual(self):
        pessoa = Pessoa.objects.create(nome='Pessoa já resolvida')
        inscricao = self.submeter(
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
            pessoa=pessoa,
        )
        identificador = inscricao.identificador
        dados_antes = inscricao.dados_declarados.pk

        atualizada = atualizar_ficha_inscricao(
            inscricao=inscricao,
            origem_operacao=InscricaoEncontro.Origem.ADMINISTRATIVA,
            dados_declarados=self.dados_declarados(
                nome_completo='Nome Declarado Atualizado',
            ),
            dados_cuidado=self.dados_cuidado(),
            momento=self.momento,
        )
        atualizada.refresh_from_db()

        self.assertEqual(atualizada.identificador, identificador)
        self.assertEqual(atualizada.pessoa, pessoa)
        self.assertEqual(atualizada.dados_declarados.pk, dados_antes)
        self.assertEqual(
            atualizada.dados_declarados.nome_completo,
            'Nome Declarado Atualizado',
        )
        self.assertEqual(
            atualizada.dados_declarados.snapshot_atual[
                'participante'
            ]['nome_completo'],
            'Nome Declarado Atualizado',
        )
        pessoa.refresh_from_db()
        self.assertEqual(pessoa.nome, 'Pessoa já resolvida')
        self.assertEqual(InscricaoEncontro.objects.count(), 1)
        self.assertEqual(DadosDeclaradosInscricao.objects.count(), 1)

    def test_atualizacao_identica_e_noop(self):
        inscricao = self.submeter()
        inscricao.refresh_from_db()
        atualizada_em = inscricao.atualizada_em

        atualizar_ficha_inscricao(
            inscricao=inscricao,
            origem_operacao=InscricaoEncontro.Origem.PUBLICA,
            dados_declarados=self.dados_declarados(),
            dados_cuidado=self.dados_cuidado(),
            momento=self.momento,
        )
        inscricao.refresh_from_db()

        self.assertEqual(inscricao.atualizada_em, atualizada_em)

    def test_cancelamento_logico_e_idempotente_preserva_ficha_e_uuid(self):
        inscricao = self.submeter()
        identificador = inscricao.identificador
        dados_id = inscricao.dados_declarados.pk

        cancelada = cancelar_inscricao_encontro(
            inscricao=inscricao,
            origem_operacao=InscricaoEncontro.Origem.PUBLICA,
            momento=self.momento,
        )
        timestamp = cancelada.cancelada_em
        novamente = cancelar_inscricao_encontro(
            inscricao=cancelada,
            origem_operacao=InscricaoEncontro.Origem.PUBLICA,
            momento=self.momento + timedelta(hours=1),
        )

        self.assertEqual(novamente.status, InscricaoEncontro.Status.CANCELADA)
        self.assertEqual(novamente.cancelada_em, timestamp)
        self.assertEqual(novamente.identificador, identificador)
        self.assertEqual(novamente.dados_declarados.pk, dados_id)
        self.assertEqual(InscricaoEncontro.objects.count(), 1)

    def test_reativacao_publica_reutiliza_inscricao_e_respeita_janela(self):
        inscricao = self.submeter()
        cancelada = cancelar_inscricao_encontro(
            inscricao=inscricao,
            origem_operacao=InscricaoEncontro.Origem.PUBLICA,
            momento=self.momento,
        )
        identificador = cancelada.identificador
        reativada = reativar_inscricao_encontro(
            inscricao=cancelada,
            origem_operacao=InscricaoEncontro.Origem.PUBLICA,
            momento=self.momento + timedelta(hours=1),
        )
        timestamp = reativada.reativada_em
        novamente = reativar_inscricao_encontro(
            inscricao=reativada,
            origem_operacao=InscricaoEncontro.Origem.PUBLICA,
            momento=self.momento + timedelta(hours=2),
        )

        self.assertEqual(novamente.status, InscricaoEncontro.Status.ENVIADA)
        self.assertEqual(novamente.reativada_em, timestamp)
        self.assertEqual(novamente.identificador, identificador)
        self.assertEqual(InscricaoEncontro.objects.count(), 1)

        cancelar_inscricao_encontro(
            inscricao=novamente,
            origem_operacao=InscricaoEncontro.Origem.ADMINISTRATIVA,
            momento=self.momento + timedelta(days=11),
        )
        with self.assertRaises(ErroFichaInscricao) as contexto:
            reativar_inscricao_encontro(
                inscricao=novamente,
                origem_operacao=InscricaoEncontro.Origem.PUBLICA,
                momento=self.momento + timedelta(days=11),
            )
        self.assertIn('janela', contexto.exception.message_dict)

    def test_erros_de_dominio_nao_repetem_valores_sensiveis(self):
        cpf_invalido = '12345678900'
        medicamento = 'Conteúdo médico sensível e específico'

        with self.assertRaises(ValidationError) as cpf:
            self.submeter(
                dados_declarados=self.dados_declarados(cpf=cpf_invalido),
            )
        self.assertNotIn(cpf_invalido, str(cpf.exception))

        with self.assertRaises(ValidationError) as cuidado:
            self.submeter(
                dados_cuidado=self.dados_cuidado(
                    usa_medicamentos=DadosCuidadoInscricao.RespostaBinaria.NAO,
                    medicamentos=medicamento,
                ),
            )
        self.assertNotIn(medicamento, str(cuidado.exception))
