from datetime import UTC, date, datetime
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import CalendarioEncontro, DiaEncontro, Encontro
from core.serializers import EncontroSerializer
from core.services.encontros import (
    adiar_encontro,
    cancelar_encontro,
    criar_encontro_com_agenda,
    editar_planejamento,
    finalizar_encontro,
    iniciar_encontro,
    iniciar_novo_planejamento,
    iniciar_preparacao,
    oficializar_agenda,
    reprogramar_agenda,
)


class NucleoEncontroTestCase(TestCase):
    dias_iniciais = (
        {
            'ordem': 1,
            'data': date(2027, 3, 7),
            'descricao': 'Pré-encontro',
        },
        {
            'ordem': 2,
            'data': date(2027, 3, 12),
            'descricao': 'Sexta-feira',
        },
        {
            'ordem': 3,
            'data': date(2027, 3, 13),
            'descricao': 'Sábado',
        },
        {
            'ordem': 4,
            'data': date(2027, 3, 14),
            'descricao': 'Domingo',
        },
    )
    dias_reprogramados = (
        {'ordem': 1, 'data': date(2027, 6, 9)},
        {'ordem': 2, 'data': date(2027, 6, 11)},
    )
    momento_oficializacao = datetime(2027, 1, 10, 12, tzinfo=UTC)
    momento_substituicao = datetime(2027, 2, 10, 12, tzinfo=UTC)

    def criar_planejado(self, **overrides):
        dados = {
            'encontro': 'Escalada I 2027',
            'tipo': Encontro.Tipo.ESCALADA,
            'data_referencia': date(2027, 3, 7),
            'data_exato': '7, 12, 13 e 14 de março de 2027',
            'local': 'Nova Betânia',
            'dias': self.dias_iniciais,
        }
        dados.update(overrides)
        return criar_encontro_com_agenda(**dados)

    def criar_agendado(self):
        encontro = self.criar_planejado()
        oficializar_agenda(
            encontro,
            momento=self.momento_oficializacao,
        )
        encontro.refresh_from_db()
        return encontro


class CriacaoAgendaTests(NucleoEncontroTestCase):
    def test_cria_encontro_planejado_com_calendario_v1_e_multiplos_dias(self):
        encontro = self.criar_planejado()
        calendario = encontro.calendarios.get()

        self.assertEqual(encontro.status, Encontro.Status.EM_AGENDAMENTO)
        self.assertEqual(calendario.versao, 1)
        self.assertTrue(calendario.vigente)
        self.assertIsNone(calendario.oficializado_em)
        self.assertEqual(calendario.dias.count(), 4)

    def test_suporta_dias_nao_consecutivos(self):
        calendario = self.criar_planejado().calendarios.get()

        self.assertEqual(
            list(calendario.dias.order_by('ordem').values_list('data', flat=True)),
            [
                date(2027, 3, 7),
                date(2027, 3, 12),
                date(2027, 3, 13),
                date(2027, 3, 14),
            ],
        )

    def test_aceita_todos_os_tipos_legados_de_encontro(self):
        for indice, tipo in enumerate(Encontro.Tipo.values, start=1):
            with self.subTest(tipo=tipo):
                encontro = self.criar_planejado(
                    encontro=f'{tipo} {indice}',
                    tipo=tipo,
                )
                self.assertEqual(encontro.tipo, tipo)

    def test_rejeita_ordem_nao_positiva_sem_criar_dados(self):
        with self.assertRaisesMessage(ValidationError, 'ordem'):
            self.criar_planejado(
                dias=[{'ordem': 0, 'data': date(2027, 3, 7)}]
            )

        self.assertFalse(Encontro.objects.exists())
        self.assertFalse(CalendarioEncontro.objects.exists())

    def test_constraints_impedem_ordem_e_data_repetidas(self):
        calendario = self.criar_planejado().calendarios.get()

        with self.assertRaises(IntegrityError), transaction.atomic():
            DiaEncontro.objects.create(
                calendario=calendario,
                ordem=1,
                data=date(2027, 8, 1),
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            DiaEncontro.objects.create(
                calendario=calendario,
                ordem=10,
                data=date(2027, 3, 7),
            )

    def test_constraints_impedem_versao_e_calendario_vigente_repetidos(self):
        encontro = self.criar_planejado()

        with self.assertRaises(IntegrityError), transaction.atomic():
            CalendarioEncontro.objects.create(
                encontro=encontro,
                versao=1,
                vigente=False,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            CalendarioEncontro.objects.create(
                encontro=encontro,
                versao=2,
                vigente=True,
            )


class PlanejamentoOficializacaoTests(NucleoEncontroTestCase):
    def test_edita_planejamento_na_mesma_versao(self):
        encontro = self.criar_planejado()
        calendario_original = encontro.calendarios.get()

        calendario = editar_planejamento(
            encontro,
            dias=self.dias_reprogramados,
        )

        self.assertEqual(calendario.pk, calendario_original.pk)
        self.assertEqual(calendario.versao, 1)
        self.assertTrue(calendario.vigente)
        self.assertIsNone(calendario.oficializado_em)
        self.assertEqual(encontro.calendarios.count(), 1)
        self.assertEqual(
            list(calendario.dias.order_by('ordem').values_list('data', flat=True)),
            [date(2027, 6, 9), date(2027, 6, 11)],
        )

    def test_oficializa_mesmo_calendario_e_muda_status(self):
        encontro = self.criar_planejado()
        calendario_original = encontro.calendarios.get()

        calendario = oficializar_agenda(
            encontro,
            momento=self.momento_oficializacao,
        )
        encontro.refresh_from_db()

        self.assertEqual(encontro.status, Encontro.Status.AGENDADO)
        self.assertEqual(calendario.pk, calendario_original.pk)
        self.assertEqual(
            calendario.oficializado_em,
            self.momento_oficializacao,
        )
        self.assertEqual(encontro.calendarios.count(), 1)

    def test_agenda_oficial_nao_pode_ser_editada_in_place(self):
        encontro = self.criar_agendado()
        calendario = encontro.calendarios.get()
        dias_anteriores = list(
            calendario.dias.order_by('ordem').values_list('data', flat=True)
        )

        with self.assertRaisesMessage(ValidationError, 'Somente Encontro'):
            editar_planejamento(encontro, dias=self.dias_reprogramados)

        calendario.refresh_from_db()
        self.assertEqual(
            list(calendario.dias.order_by('ordem').values_list('data', flat=True)),
            dias_anteriores,
        )

    def test_status_nao_muda_apenas_pela_passagem_da_data(self):
        encontro = self.criar_planejado(
            data_referencia=date(2020, 1, 1),
            dias=[{'ordem': 1, 'data': date(2020, 1, 1)}],
        )

        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.EM_AGENDAMENTO)


class ReprogramacaoAdiamentoTests(NucleoEncontroTestCase):
    def test_reprogramacao_preserva_agenda_oficial_e_cria_proxima_versao(self):
        encontro = self.criar_agendado()
        encontro_id = encontro.pk
        anterior = encontro.calendarios.get()
        dias_anteriores = list(
            anterior.dias.order_by('ordem').values_list('data', flat=True)
        )

        nova = reprogramar_agenda(
            encontro,
            dias=self.dias_reprogramados,
            momento=self.momento_substituicao,
        )
        anterior.refresh_from_db()

        self.assertEqual(encontro.pk, encontro_id)
        self.assertFalse(anterior.vigente)
        self.assertEqual(
            anterior.substituido_em,
            self.momento_substituicao,
        )
        self.assertEqual(
            list(anterior.dias.order_by('ordem').values_list('data', flat=True)),
            dias_anteriores,
        )
        self.assertEqual(nova.versao, 2)
        self.assertTrue(nova.vigente)
        self.assertEqual(nova.oficializado_em, self.momento_substituicao)
        self.assertEqual(
            list(nova.dias.order_by('ordem').values_list('data', flat=True)),
            [date(2027, 6, 9), date(2027, 6, 11)],
        )

    def test_adiamento_sem_datas_deixa_agendas_apenas_historicas(self):
        encontro = self.criar_agendado()
        calendario = encontro.calendarios.get()

        adiar_encontro(encontro, momento=self.momento_substituicao)
        encontro.refresh_from_db()
        calendario.refresh_from_db()

        self.assertEqual(encontro.status, Encontro.Status.ADIADO)
        self.assertTrue(Encontro.objects.filter(pk=encontro.pk).exists())
        self.assertFalse(calendario.vigente)
        self.assertEqual(
            calendario.substituido_em,
            self.momento_substituicao,
        )
        self.assertEqual(calendario.dias.count(), 4)
        self.assertFalse(encontro.calendarios.filter(vigente=True).exists())

    def test_adiado_inicia_novo_planejamento_e_o_oficializa(self):
        encontro = self.criar_agendado()
        adiar_encontro(encontro, momento=self.momento_substituicao)
        encontro.refresh_from_db()

        calendario = iniciar_novo_planejamento(
            encontro,
            dias=self.dias_reprogramados,
        )
        encontro.refresh_from_db()

        self.assertEqual(encontro.status, Encontro.Status.EM_AGENDAMENTO)
        self.assertEqual(calendario.versao, 2)
        self.assertTrue(calendario.vigente)
        self.assertIsNone(calendario.oficializado_em)

        oficializar_agenda(encontro, momento=self.momento_substituicao)
        encontro.refresh_from_db()
        calendario.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.AGENDADO)
        self.assertEqual(
            calendario.oficializado_em,
            self.momento_substituicao,
        )

    def test_adiado_pode_ser_reprogramado_diretamente_com_novas_datas(self):
        encontro = self.criar_agendado()
        adiar_encontro(encontro, momento=self.momento_substituicao)
        encontro.refresh_from_db()

        calendario = reprogramar_agenda(
            encontro,
            dias=self.dias_reprogramados,
            momento=self.momento_substituicao,
        )
        encontro.refresh_from_db()

        self.assertEqual(encontro.status, Encontro.Status.AGENDADO)
        self.assertEqual(calendario.versao, 2)
        self.assertIsNotNone(calendario.oficializado_em)


class LifecycleEncontroTests(NucleoEncontroTestCase):
    def test_fluxo_principal_completo(self):
        encontro = self.criar_agendado()

        iniciar_preparacao(encontro)
        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.EM_PREPARACAO)

        iniciar_encontro(encontro)
        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.EM_ANDAMENTO)

        finalizar_encontro(encontro)
        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.FINALIZADO)

    def test_transicao_invalida_e_bloqueada(self):
        encontro = self.criar_planejado()

        with self.assertRaisesMessage(ValidationError, 'Transição'):
            finalizar_encontro(encontro)

        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.EM_AGENDAMENTO)

    def test_finalizado_nao_reabre(self):
        encontro = self.criar_agendado()
        iniciar_preparacao(encontro)
        encontro.refresh_from_db()
        iniciar_encontro(encontro)
        encontro.refresh_from_db()
        finalizar_encontro(encontro)
        encontro.refresh_from_db()

        with self.assertRaisesMessage(ValidationError, 'Transição'):
            iniciar_encontro(encontro)

        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.FINALIZADO)

    def test_cancelamento_preserva_encontro_calendario_e_dias(self):
        encontro = self.criar_agendado()
        calendario = encontro.calendarios.get()

        cancelar_encontro(encontro)
        encontro.refresh_from_db()

        self.assertEqual(encontro.status, Encontro.Status.CANCELADO)
        self.assertTrue(Encontro.objects.filter(pk=encontro.pk).exists())
        self.assertTrue(
            CalendarioEncontro.objects.filter(pk=calendario.pk).exists()
        )
        self.assertEqual(calendario.dias.count(), 4)

        with self.assertRaisesMessage(ValidationError, 'Transição'):
            iniciar_preparacao(encontro)


class AtomicidadeEncontroTests(NucleoEncontroTestCase):
    def test_erro_na_criacao_nao_deixa_dados_parciais(self):
        with patch(
            'core.services.encontros._criar_dias',
            side_effect=IntegrityError,
        ):
            with self.assertRaises(IntegrityError):
                self.criar_planejado()

        self.assertFalse(Encontro.objects.exists())
        self.assertFalse(CalendarioEncontro.objects.exists())

    def test_erro_na_edicao_preserva_dias_anteriores(self):
        encontro = self.criar_planejado()
        calendario = encontro.calendarios.get()
        dias_anteriores = list(
            calendario.dias.order_by('ordem').values_list('data', flat=True)
        )

        with patch(
            'core.services.encontros._criar_dias',
            side_effect=IntegrityError,
        ):
            with self.assertRaises(IntegrityError):
                editar_planejamento(encontro, dias=self.dias_reprogramados)

        self.assertEqual(
            list(calendario.dias.order_by('ordem').values_list('data', flat=True)),
            dias_anteriores,
        )

    def test_erro_na_reprogramacao_preserva_agenda_anterior(self):
        encontro = self.criar_agendado()
        anterior = encontro.calendarios.get()

        with patch(
            'core.services.encontros._criar_dias',
            side_effect=IntegrityError,
        ):
            with self.assertRaises(IntegrityError):
                reprogramar_agenda(
                    encontro,
                    dias=self.dias_reprogramados,
                    momento=self.momento_substituicao,
                )

        anterior.refresh_from_db()
        encontro.refresh_from_db()
        self.assertTrue(anterior.vigente)
        self.assertIsNone(anterior.substituido_em)
        self.assertEqual(encontro.status, Encontro.Status.AGENDADO)
        self.assertEqual(encontro.calendarios.count(), 1)

    def test_falha_na_oficializacao_nao_altera_status(self):
        encontro = Encontro.objects.create(
            encontro='Encontro legado sem calendário',
            tipo=Encontro.Tipo.ESPPA,
            data_referencia=date(2027, 5, 1),
            data_exato='1 de maio de 2027',
        )

        with self.assertRaisesMessage(ValidationError, 'calendário vigente'):
            oficializar_agenda(encontro)

        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.EM_AGENDAMENTO)


class CompatibilidadeEncontroTests(NucleoEncontroTestCase):
    def test_serializer_preserva_campos_e_status_de_escrita_legados(self):
        serializer = EncontroSerializer()

        self.assertEqual(
            set(serializer.fields),
            {
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
            },
        )
        self.assertEqual(
            set(serializer.fields['status'].choices),
            {
                Encontro.Status.EM_AGENDAMENTO,
                Encontro.Status.AGENDADO,
            },
        )

    def test_serializer_mantem_status_opcional_na_criacao_legada(self):
        serializer = EncontroSerializer(data={
            'encontro': 'Criação pela API legada',
            'tipo': 'Escalada',
            'data_referencia': '2027-10-10',
            'data_exato': '10 de outubro de 2027',
            'local': 'Nova Betânia',
        })

        self.assertTrue(serializer.is_valid(), serializer.errors)
        encontro = serializer.save()
        self.assertEqual(
            encontro.status,
            Encontro.Status.EM_AGENDAMENTO,
        )

    def test_registros_legados_podem_permanecer_sem_calendario(self):
        encontro = Encontro.objects.create(
            encontro='Registro legado',
            tipo='Esppa',
            data_referencia=date(2026, 11, 25),
            data_exato='25 de Novembro de 2026',
            local='Nova Betânia',
            status='em_agendamento',
        )

        self.assertFalse(encontro.calendarios.exists())
        self.assertEqual(encontro.tipo, 'Esppa')
        self.assertEqual(encontro.status, 'em_agendamento')
