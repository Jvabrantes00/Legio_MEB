from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase

from core.models import (
    ConviteEncontro,
    Encontro,
    Frequencia,
    Inscricao,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
)
from core.services.participacoes import (
    criar_convite,
    criar_inscricao,
    registrar_resultado_participacao,
    responder_convite,
)
from core.tests.factories import make_encontro


class EncounterParticipationServiceTests(TestCase):
    def setUp(self):
        self.pessoa = Pessoa.objects.create(nome='Pessoa candidata')
        self.escalada = make_encontro(
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia=date(2030, 1, 1),
        )
        self.outra_escalada = make_encontro(
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia=date(2031, 1, 1),
        )
        self.esppa = make_encontro(
            tipo=Encontro.Tipo.ESPPA,
            data_referencia=date(2030, 6, 1),
        )

    def _criar_convite(self, encontro=None, inscricao=None):
        return criar_convite(
            pessoa=self.pessoa,
            encontro=encontro or self.escalada,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            inscricao=inscricao,
        )

    def test_cria_inscricoes_de_escalada_e_esppa_sem_prioridade(self):
        escalada = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )
        esppa = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESPPA,
        )

        self.assertEqual(escalada.status, Inscricao.Status.PENDENTE)
        self.assertEqual(esppa.status, Inscricao.Status.PENDENTE)
        self.assertFalse(hasattr(escalada, 'prioridade'))
        self.assertFalse(hasattr(escalada, 'encontro'))

    def test_rejeita_duplicacao_de_inscricao_ativa(self):
        criar_inscricao(pessoa=self.pessoa, tipo=Inscricao.Tipo.ESCALADA)

        with self.assertRaisesMessage(ValidationError, 'Já existe inscrição'):
            criar_inscricao(pessoa=self.pessoa, tipo=Inscricao.Tipo.ESCALADA)

        self.assertEqual(Inscricao.objects.count(), 1)

    def test_cria_convite_ligado_a_inscricao_e_e_idempotente(self):
        inscricao = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )

        convite = self._criar_convite(inscricao=inscricao)
        repetido = self._criar_convite(inscricao=inscricao)

        self.assertEqual(convite.inscricao, inscricao)
        self.assertEqual(repetido.pk, convite.pk)
        self.assertEqual(ConviteEncontro.objects.count(), 1)

    def test_cria_convite_avc_sem_inscricao_quando_elegivel(self):
        ParticipacaoEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=Encontro.Tipo.ESCALADA,
        )
        avc = make_encontro(
            tipo=Encontro.Tipo.AVC,
            data_referencia=date(2032, 1, 1),
        )

        convite = self._criar_convite(encontro=avc)

        self.assertIsNone(convite.inscricao)

    def test_confirmado_nao_cria_participacao_e_mantem_inscricao(self):
        inscricao = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )
        convite = self._criar_convite(inscricao=inscricao)

        respondido = responder_convite(
            convite,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        inscricao.refresh_from_db()
        self.assertEqual(respondido.status, ConviteEncontro.Status.CONFIRMADO)
        self.assertEqual(inscricao.status, Inscricao.Status.PENDENTE)
        self.assertFalse(ParticipacaoEncontro.objects.exists())

    def test_recusado_e_sem_resposta_mantem_inscricao_pendente(self):
        for status in (
            ConviteEncontro.Status.RECUSADO,
            ConviteEncontro.Status.SEM_RESPOSTA,
        ):
            with self.subTest(status=status):
                pessoa = Pessoa.objects.create(nome=f'Pessoa {status}')
                inscricao = criar_inscricao(
                    pessoa=pessoa,
                    tipo=Inscricao.Tipo.ESCALADA,
                )
                convite = criar_convite(
                    pessoa=pessoa,
                    encontro=self.escalada,
                    finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
                    inscricao=inscricao,
                )

                responder_convite(convite, status=status)

                inscricao.refresh_from_db()
                self.assertEqual(inscricao.status, Inscricao.Status.PENDENTE)
                self.assertFalse(
                    ParticipacaoEncontro.objects.filter(pessoa=pessoa).exists()
                )

    def test_resposta_identica_e_idempotente_e_resposta_diversa_e_bloqueada(self):
        convite = self._criar_convite()
        respondido = responder_convite(
            convite,
            status=ConviteEncontro.Status.RECUSADO,
        )

        repetido = responder_convite(
            respondido,
            status=ConviteEncontro.Status.RECUSADO,
        )

        self.assertEqual(repetido.pk, respondido.pk)
        with self.assertRaisesMessage(ValidationError, 'resposta definitiva'):
            responder_convite(
                respondido,
                status=ConviteEncontro.Status.CONFIRMADO,
            )

    def test_conclusao_cria_perfil_e_cumpre_inscricao(self):
        inscricao = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )
        convite = self._criar_convite(inscricao=inscricao)

        participacao = registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.escalada,
            convite=convite,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
        )

        inscricao.refresh_from_db()
        self.assertEqual(participacao.pessoa, self.pessoa)
        self.assertEqual(participacao.tipo_encontro, Encontro.Tipo.ESCALADA)
        self.assertEqual(inscricao.status, Inscricao.Status.CUMPRIDA)
        self.assertIsNotNone(inscricao.cumprida_em)
        self.assertTrue(PerfilAlpinista.objects.filter(pessoa=self.pessoa).exists())

    def test_faltou_e_desistiu_nao_criam_perfil_e_mantem_inscricao(self):
        for resultado in (
            ParticipacaoEncontro.Resultado.FALTOU,
            ParticipacaoEncontro.Resultado.DESISTIU,
        ):
            with self.subTest(resultado=resultado):
                pessoa = Pessoa.objects.create(nome=f'Pessoa {resultado}')
                inscricao = criar_inscricao(
                    pessoa=pessoa,
                    tipo=Inscricao.Tipo.ESCALADA,
                )
                convite = criar_convite(
                    pessoa=pessoa,
                    encontro=self.escalada,
                    finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
                    inscricao=inscricao,
                )

                registrar_resultado_participacao(
                    pessoa=pessoa,
                    encontro=self.escalada,
                    convite=convite,
                    resultado=resultado,
                )

                inscricao.refresh_from_db()
                self.assertEqual(inscricao.status, Inscricao.Status.PENDENTE)
                self.assertFalse(
                    PerfilAlpinista.objects.filter(pessoa=pessoa).exists()
                )

    def test_nova_tentativa_e_permitida_apos_falta_ou_desistencia(self):
        for primeiro_resultado in (
            ParticipacaoEncontro.Resultado.FALTOU,
            ParticipacaoEncontro.Resultado.DESISTIU,
        ):
            with self.subTest(primeiro_resultado=primeiro_resultado):
                pessoa = Pessoa.objects.create(nome=f'Pessoa {primeiro_resultado}')
                inscricao = criar_inscricao(
                    pessoa=pessoa,
                    tipo=Inscricao.Tipo.ESCALADA,
                )
                registrar_resultado_participacao(
                    pessoa=pessoa,
                    encontro=self.escalada,
                    resultado=primeiro_resultado,
                )

                registrar_resultado_participacao(
                    pessoa=pessoa,
                    encontro=self.outra_escalada,
                    resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
                )

                inscricao.refresh_from_db()
                self.assertEqual(inscricao.status, Inscricao.Status.CUMPRIDA)

    def test_um_resultado_por_pessoa_e_encontro(self):
        registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
        )

        with self.assertRaisesMessage(ValidationError, 'outro resultado'):
            registrar_resultado_participacao(
                pessoa=self.pessoa,
                encontro=self.escalada,
                resultado=ParticipacaoEncontro.Resultado.DESISTIU,
            )

        self.assertEqual(ParticipacaoEncontro.objects.count(), 1)

    def test_falta_pode_ser_corrigida_para_conclusao(self):
        participacao = registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
        )

        corrigida = registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
        )

        self.assertEqual(corrigida.pk, participacao.pk)
        self.assertEqual(corrigida.resultado, ParticipacaoEncontro.Resultado.CONCLUIU)
        self.assertTrue(PerfilAlpinista.objects.filter(pessoa=self.pessoa).exists())

    def test_bloqueia_segunda_conclusao_do_mesmo_tipo(self):
        registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
        )

        with self.assertRaisesMessage(ValidationError, 'já concluiu'):
            registrar_resultado_participacao(
                pessoa=self.pessoa,
                encontro=self.outra_escalada,
                resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            )

        self.assertEqual(
            ParticipacaoEncontro.objects.filter(
                resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            ).count(),
            1,
        )

    def test_perfil_existente_nao_e_duplicado_em_conclusao_esppa(self):
        perfil = PerfilAlpinista.objects.create(pessoa=self.pessoa)

        registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.esppa,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
        )

        self.assertEqual(PerfilAlpinista.objects.count(), 1)
        self.assertTrue(PerfilAlpinista.objects.filter(pk=perfil.pk).exists())

    def test_avc_e_acampamento_nao_criam_perfil(self):
        for tipo in (Encontro.Tipo.AVC, Encontro.Tipo.ACAMPAMENTO):
            with self.subTest(tipo=tipo):
                pessoa = Pessoa.objects.create(nome=f'Pessoa {tipo}')
                escalada = make_encontro(
                    tipo=Encontro.Tipo.ESCALADA,
                    data_referencia=date(2027, 1, 1),
                )
                ParticipacaoEncontro.objects.create(
                    pessoa=pessoa,
                    encontro=escalada,
                    resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
                    tipo_encontro=Encontro.Tipo.ESCALADA,
                )
                encontro = make_encontro(
                    tipo=tipo,
                    data_referencia=date(2030, 1, 1),
                )

                registrar_resultado_participacao(
                    pessoa=pessoa,
                    encontro=encontro,
                    resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
                )

                self.assertFalse(
                    PerfilAlpinista.objects.filter(pessoa=pessoa).exists()
                )

    def test_avc_e_acampamento_exigem_conclusao_anterior_de_escalada(self):
        for tipo in (Encontro.Tipo.AVC, Encontro.Tipo.ACAMPAMENTO):
            with self.subTest(tipo=tipo):
                encontro = make_encontro(
                    tipo=tipo,
                    data_referencia=date(2032, 1, 1),
                )

                with self.assertRaisesMessage(
                    ValidationError,
                    'exige conclusão anterior de Escalada',
                ):
                    registrar_resultado_participacao(
                        pessoa=self.pessoa,
                        encontro=encontro,
                        resultado=ParticipacaoEncontro.Resultado.FALTOU,
                    )

        self.assertFalse(ParticipacaoEncontro.objects.exists())

    def test_fluxos_nao_criam_frequencia(self):
        inscricao = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )
        convite = self._criar_convite(inscricao=inscricao)
        responder_convite(
            convite,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.escalada,
            convite=convite,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
        )

        self.assertFalse(Frequencia.objects.exists())

    def test_falha_intermediaria_desfaz_participacao_e_cumprimento(self):
        inscricao = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )

        with patch(
            'core.services.participacoes.PerfilAlpinista.objects.get_or_create',
            side_effect=RuntimeError('falha intermediária'),
        ):
            with self.assertRaisesMessage(RuntimeError, 'falha intermediária'):
                registrar_resultado_participacao(
                    pessoa=self.pessoa,
                    encontro=self.escalada,
                    resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
                )

        inscricao.refresh_from_db()
        self.assertEqual(inscricao.status, Inscricao.Status.PENDENTE)
        self.assertFalse(ParticipacaoEncontro.objects.exists())
        self.assertFalse(PerfilAlpinista.objects.exists())

    def test_registro_repetido_do_mesmo_resultado_e_idempotente(self):
        participacao = registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
        )

        repetida = registrar_resultado_participacao(
            pessoa=self.pessoa,
            encontro=self.escalada,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
        )

        self.assertEqual(repetida.pk, participacao.pk)
        self.assertEqual(ParticipacaoEncontro.objects.count(), 1)


@skipUnless(connection.vendor == 'postgresql', 'exige PostgreSQL')
class EncounterParticipationConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def _executar_em_threads(self, funcao):
        barreira = Barrier(2)

        def executar():
            close_old_connections()
            try:
                barreira.wait()
                return funcao()
            except ValidationError:
                return 'bloqueada'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(lambda _: executar(), range(2)))

    def test_criacao_concorrente_mantem_uma_inscricao_ativa(self):
        pessoa = Pessoa.objects.create(nome='Pessoa concorrente')

        resultados = self._executar_em_threads(
            lambda: criar_inscricao(
                pessoa=Pessoa.objects.get(pk=pessoa.pk),
                tipo=Inscricao.Tipo.ESCALADA,
            ).pk
        )

        self.assertEqual(resultados.count('bloqueada'), 1)
        self.assertEqual(Inscricao.objects.count(), 1)

    def test_conclusoes_concorrentes_mantem_um_resultado_e_um_perfil(self):
        pessoa = Pessoa.objects.create(nome='Pessoa concorrente')
        encontros = [
            make_encontro(tipo=Encontro.Tipo.ESCALADA),
            make_encontro(tipo=Encontro.Tipo.ESCALADA),
        ]
        indice = iter(range(2))

        def concluir():
            encontro = encontros[next(indice)]
            return registrar_resultado_participacao(
                pessoa=Pessoa.objects.get(pk=pessoa.pk),
                encontro=Encontro.objects.get(pk=encontro.pk),
                resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            ).pk

        resultados = self._executar_em_threads(concluir)

        self.assertEqual(resultados.count('bloqueada'), 1)
        self.assertEqual(ParticipacaoEncontro.objects.count(), 1)
        self.assertEqual(PerfilAlpinista.objects.count(), 1)
