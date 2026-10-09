from datetime import date, datetime

from django.test import TestCase
from django.utils import timezone

from core.models import (
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    DiaEncontro,
    Encontro,
    ParticipacaoEncontro,
    Pessoa,
)
from core.services.comandos_calendario import reprogramar_agenda
from core.services.elegibilidade_encontristas import (
    CodigoElegibilidadeEncontrista,
    ResultadoElegibilidadeEncontrista,
    avaliar_elegibilidade_encontrista,
)
from core.tests.factories import make_encontro


class ElegibilidadeEncontristaTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro(
            tipo=Encontro.Tipo.ESCALADA,
            status=Encontro.Status.AGENDADO,
            data_referencia=date(2030, 6, 1),
        )
        self.primeiro_dia = date(2030, 6, 1)
        self.ultimo_dia = date(2030, 6, 3)
        self.data_avaliacao = date(2030, 1, 1)
        self._criar_configuracao()
        self._criar_calendario_oficial(
            self.primeiro_dia,
            self.ultimo_dia,
        )

    def _criar_configuracao(self, encontro=None, **overrides):
        valores = {
            'capacidade': 80,
            'idade_minima': 18,
            'idade_maxima': 25,
            'inscricoes_abrem_em': timezone.make_aware(
                datetime(2029, 10, 1, 8, 0)
            ),
            'inscricoes_encerram_em': timezone.make_aware(
                datetime(2030, 5, 1, 23, 59)
            ),
        }
        valores.update(overrides)
        return ConfiguracaoEncontristasEncontro.objects.create(
            encontro=encontro or self.encontro,
            **valores,
        )

    def _criar_calendario_oficial(
        self,
        primeiro_dia,
        ultimo_dia,
        *,
        encontro=None,
        vigente=True,
        versao=1,
    ):
        calendario = CalendarioEncontro.objects.create(
            encontro=encontro or self.encontro,
            versao=versao,
            vigente=vigente,
            oficializado_em=timezone.now(),
        )
        DiaEncontro.objects.create(
            calendario=calendario,
            ordem=1,
            data=primeiro_dia,
        )
        if ultimo_dia != primeiro_dia:
            DiaEncontro.objects.create(
                calendario=calendario,
                ordem=2,
                data=ultimo_dia,
            )
        return calendario

    def _avaliar(self, nascimento, *, encontro=None):
        pessoa = Pessoa.objects.create(
            nome=f'Pessoa {nascimento}',
            data_nascimento=nascimento,
        )
        resultado = avaliar_elegibilidade_encontrista(
            pessoa=pessoa,
            encontro=encontro or self.encontro,
            data_avaliacao=self.data_avaliacao,
        )
        return pessoa, resultado

    def test_idade_minima_ja_atingida_e_elegivel(self):
        _, avaliacao = self._avaliar(date(2010, 1, 1))

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.ELEGIVEL,
        )
        self.assertEqual(avaliacao.avisos, ())

    def test_completa_minima_durante_encontro_com_aviso(self):
        _, avaliacao = self._avaliar(date(2012, 6, 2))

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.ELEGIVEL_COM_AVISO,
        )
        self.assertEqual(
            avaliacao.avisos[0].codigo,
            CodigoElegibilidadeEncontrista.IDADE_MINIMA_FUTURA,
        )
        self.assertEqual(avaliacao.idade_no_primeiro_dia, 17)
        self.assertEqual(avaliacao.idade_no_ultimo_dia, 18)

    def test_abaixo_da_minima_apos_ultimo_dia_e_inelegivel(self):
        _, avaliacao = self._avaliar(date(2012, 6, 4))

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.INELEGIVEL,
        )
        self.assertEqual(
            avaliacao.motivos[0].codigo,
            CodigoElegibilidadeEncontrista.IDADE_MINIMA_NAO_ATINGIDA,
        )

    def test_no_maximo_no_primeiro_dia_pode_superar_durante_encontro(self):
        _, avaliacao = self._avaliar(date(2004, 6, 2))

        self.assertEqual(avaliacao.idade_no_primeiro_dia, 25)
        self.assertEqual(avaliacao.idade_no_ultimo_dia, 26)
        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.ELEGIVEL,
        )

    def test_acima_do_maximo_no_primeiro_dia_e_inelegivel(self):
        _, avaliacao = self._avaliar(date(2004, 5, 31))

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.INELEGIVEL,
        )
        self.assertEqual(
            avaliacao.motivos[0].codigo,
            CodigoElegibilidadeEncontrista.IDADE_MAXIMA_EXCEDIDA,
        )

    def test_conclusao_anterior_do_mesmo_tipo_bloqueia(self):
        pessoa = Pessoa.objects.create(
            nome='Pessoa que concluiu Escalada',
            data_nascimento=date(2010, 1, 1),
        )
        anterior = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        ParticipacaoEncontro.objects.create(
            pessoa=pessoa,
            encontro=anterior,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )

        avaliacao = avaliar_elegibilidade_encontrista(
            pessoa=pessoa,
            encontro=self.encontro,
            data_avaliacao=self.data_avaliacao,
        )

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.INELEGIVEL,
        )
        self.assertEqual(
            avaliacao.motivos[0].codigo,
            CodigoElegibilidadeEncontrista.CONCLUSAO_ANTERIOR_MESMO_TIPO,
        )

    def test_conclusao_de_tipo_diferente_nao_bloqueia(self):
        pessoa = Pessoa.objects.create(
            nome='Pessoa que concluiu ESPPA',
            data_nascimento=date(2010, 1, 1),
        )
        anterior = make_encontro(tipo=Encontro.Tipo.ESPPA)
        ParticipacaoEncontro.objects.create(
            pessoa=pessoa,
            encontro=anterior,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=Encontro.Tipo.ESPPA,
        )

        avaliacao = avaliar_elegibilidade_encontrista(
            pessoa=pessoa,
            encontro=self.encontro,
            data_avaliacao=self.data_avaliacao,
        )

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.ELEGIVEL,
        )

    def test_sem_data_nascimento_e_nao_avaliavel(self):
        pessoa = Pessoa.objects.create(nome='Pessoa sem nascimento')

        avaliacao = avaliar_elegibilidade_encontrista(
            pessoa=pessoa,
            encontro=self.encontro,
            data_avaliacao=self.data_avaliacao,
        )

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.NAO_AVALIAVEL,
        )
        self.assertIn(
            CodigoElegibilidadeEncontrista.DATA_NASCIMENTO_AUSENTE,
            tuple(motivo.codigo for motivo in avaliacao.motivos),
        )

    def test_sem_configuracao_e_nao_avaliavel(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self._criar_calendario_oficial(
            self.primeiro_dia,
            self.ultimo_dia,
            encontro=encontro,
        )

        _, avaliacao = self._avaliar(date(2010, 1, 1), encontro=encontro)

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.NAO_AVALIAVEL,
        )
        self.assertIn(
            CodigoElegibilidadeEncontrista.CONFIGURACAO_AUSENTE,
            tuple(motivo.codigo for motivo in avaliacao.motivos),
        )

    def test_sem_calendario_oficial_nao_usa_data_legada(self):
        encontro = make_encontro(
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia=self.primeiro_dia,
            data_exato='1 a 3 de junho de 2030',
        )
        self._criar_configuracao(encontro=encontro)

        _, avaliacao = self._avaliar(date(2010, 1, 1), encontro=encontro)

        self.assertEqual(
            avaliacao.resultado,
            ResultadoElegibilidadeEncontrista.NAO_AVALIAVEL,
        )
        self.assertIsNone(avaliacao.primeiro_dia)
        self.assertIn(
            CodigoElegibilidadeEncontrista.CALENDARIO_OFICIAL_AUSENTE,
            tuple(motivo.codigo for motivo in avaliacao.motivos),
        )

    def test_reprogramacao_muda_resultado_ao_recalcular(self):
        pessoa = Pessoa.objects.create(
            nome='Pessoa afetada pela reprogramação',
            data_nascimento=date(2012, 6, 5),
        )
        antes = avaliar_elegibilidade_encontrista(
            pessoa=pessoa,
            encontro=self.encontro,
            data_avaliacao=self.data_avaliacao,
        )

        reprogramar_agenda(
            self.encontro,
            dias=(
                {'ordem': 1, 'data': date(2030, 6, 5)},
                {'ordem': 2, 'data': date(2030, 6, 6)},
            ),
        )
        depois = avaliar_elegibilidade_encontrista(
            pessoa=pessoa,
            encontro=self.encontro,
            data_avaliacao=self.data_avaliacao,
        )

        self.assertEqual(
            antes.resultado,
            ResultadoElegibilidadeEncontrista.INELEGIVEL,
        )
        self.assertEqual(
            depois.resultado,
            ResultadoElegibilidadeEncontrista.ELEGIVEL_COM_AVISO,
        )
        self.assertEqual(depois.primeiro_dia, date(2030, 6, 5))

    def test_resultado_estruturado_nao_expoe_data_de_nascimento(self):
        _, avaliacao = self._avaliar(date(2010, 1, 1))

        resultado = avaliacao.as_dict()

        self.assertEqual(resultado['primeiro_dia'], self.primeiro_dia)
        self.assertEqual(resultado['ultimo_dia'], self.ultimo_dia)
        self.assertEqual(resultado['configuracao']['idade_minima'], 18)
        self.assertNotIn('data_nascimento', resultado)
