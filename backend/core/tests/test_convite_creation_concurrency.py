from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase

from core.models import (
    ConviteEncontro,
    Encontro,
    Inscricao,
    ParticipacaoEncontro,
    Pessoa,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.services.participacoes import (
    criar_convite,
    criar_inscricao,
    registrar_resultado_participacao,
    responder_convite,
)
from core.services.trabalhos import (
    alocar_trabalho,
    criar_convite_trabalho,
    desalocar_trabalho,
    iniciar_trabalho_confirmado,
    preparar_equipes_encontro,
    substituir_trabalho,
)
from core.tests.factories import make_encontro


@skipUnless(connection.vendor == 'postgresql', 'exige PostgreSQL real')
class ConviteCreationConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.pessoa = Pessoa.objects.create(nome='Pessoa concorrente')

    def _executar_concorrentes(self, *operacoes):
        barreira = Barrier(len(operacoes))

        def executar(operacao):
            close_old_connections()
            try:
                barreira.wait()
                return operacao()
            except ValidationError:
                return 'bloqueada'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(operacoes)) as executor:
            futuros = [executor.submit(executar, operacao) for operacao in operacoes]
            return [futuro.result() for futuro in futuros]

    def _criar_convite_participacao(self, *, inscricao=None):
        return criar_convite(
            pessoa=Pessoa.objects.get(pk=self.pessoa.pk),
            encontro=Encontro.objects.get(pk=self.encontro.pk),
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            inscricao=(
                Inscricao.objects.get(pk=inscricao.pk)
                if inscricao is not None
                else None
            ),
        ).pk

    def _criar_convite_trabalho(self):
        return criar_convite_trabalho(
            pessoa=Pessoa.objects.get(pk=self.pessoa.pk),
            encontro=Encontro.objects.get(pk=self.encontro.pk),
            confirmar_avisos=True,
        ).pk

    def test_criacoes_simultaneas_reutilizam_convite_de_participacao(self):
        resultados = self._executar_concorrentes(
            self._criar_convite_participacao,
            self._criar_convite_participacao,
        )

        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(ConviteEncontro.objects.count(), 1)

    def test_criacoes_simultaneas_reutilizam_convite_de_trabalho(self):
        resultados = self._executar_concorrentes(
            self._criar_convite_trabalho,
            self._criar_convite_trabalho,
        )

        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(ConviteEncontro.objects.count(), 1)
        self.assertFalse(TrabalhoEncontro.objects.exists())

    def test_convites_de_finalidades_distintas_concorrem_sem_deadlock(self):
        resultados = self._executar_concorrentes(
            self._criar_convite_participacao,
            self._criar_convite_trabalho,
        )

        self.assertNotIn('bloqueada', resultados)
        self.assertEqual(len(set(resultados)), 2)
        self.assertEqual(
            set(ConviteEncontro.objects.values_list('finalidade', flat=True)),
            {
                ConviteEncontro.Finalidade.PARTICIPAR,
                ConviteEncontro.Finalidade.TRABALHAR,
            },
        )

    def test_recriacao_concorre_com_inicio_do_trabalho_confirmado(self):
        convite = criar_convite_trabalho(
            pessoa=self.pessoa,
            encontro=self.encontro,
            confirmar_avisos=True,
        )
        responder_convite(convite, status=ConviteEncontro.Status.CONFIRMADO)

        def iniciar_trabalho():
            return iniciar_trabalho_confirmado(
                ConviteEncontro.objects.get(pk=convite.pk),
                confirmar_avisos=True,
            ).pk

        resultados = self._executar_concorrentes(
            self._criar_convite_trabalho,
            iniciar_trabalho,
        )

        self.assertNotIn('bloqueada', resultados)
        self.assertEqual(ConviteEncontro.objects.count(), 1)
        self.assertEqual(TrabalhoEncontro.objects.count(), 1)

    def test_recriacao_concorre_com_resultado_de_participacao(self):
        convite = criar_convite(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )

        def registrar_resultado():
            return registrar_resultado_participacao(
                pessoa=Pessoa.objects.get(pk=self.pessoa.pk),
                encontro=Encontro.objects.get(pk=self.encontro.pk),
                convite=ConviteEncontro.objects.get(pk=convite.pk),
                resultado=ParticipacaoEncontro.Resultado.FALTOU,
            ).pk

        resultados = self._executar_concorrentes(
            self._criar_convite_participacao,
            registrar_resultado,
        )

        self.assertNotIn('bloqueada', resultados)
        self.assertEqual(ConviteEncontro.objects.count(), 1)
        self.assertEqual(ParticipacaoEncontro.objects.count(), 1)

    def test_criacoes_simultaneas_preservam_inscricao_legada(self):
        inscricao = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )

        def criar_com_inscricao():
            return self._criar_convite_participacao(inscricao=inscricao)

        resultados = self._executar_concorrentes(
            criar_com_inscricao,
            criar_com_inscricao,
        )

        self.assertEqual(resultados[0], resultados[1])
        convite = ConviteEncontro.objects.get()
        self.assertEqual(convite.inscricao_id, inscricao.pk)

    def test_associacoes_incompativeis_nao_deixam_convite_parcial(self):
        inscricao = criar_inscricao(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )

        resultados = self._executar_concorrentes(
            lambda: self._criar_convite_participacao(inscricao=inscricao),
            self._criar_convite_participacao,
        )

        self.assertEqual(resultados.count('bloqueada'), 1)
        self.assertEqual(ConviteEncontro.objects.count(), 1)
        convite = ConviteEncontro.objects.get()
        self.assertIn(convite.inscricao_id, {None, inscricao.pk})

    def test_substituicao_concorre_com_operacao_contextual_sem_deadlock(self):
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.ESCALADA,
            codigo='equipe-concorrente',
            nome='Equipe concorrente',
            ordem=1,
        )
        TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante-concorrente',
            nome='Integrante concorrente',
            ordem=1,
            quantidade_estrutural=1,
        )
        role = preparar_equipes_encontro(self.encontro)[0].roles.get()
        trabalhos = []
        for indice in range(2):
            pessoa = Pessoa.objects.create(nome=f'Pessoa trabalho {indice}')
            convite = criar_convite_trabalho(
                pessoa=pessoa,
                encontro=self.encontro,
                confirmar_avisos=True,
            )
            responder_convite(
                convite,
                status=ConviteEncontro.Status.CONFIRMADO,
            )
            trabalhos.append(iniciar_trabalho_confirmado(
                convite,
                confirmar_avisos=True,
            ))
        anterior = alocar_trabalho(
            trabalhos[0],
            role,
            confirmar_avisos=True,
        )
        novo = trabalhos[1]

        def substituir():
            retirado, alocado = substituir_trabalho(
                TrabalhoEncontro.objects.get(pk=anterior.pk),
                TrabalhoEncontro.objects.get(pk=novo.pk),
                role,
                confirmar_avisos=True,
            )
            return retirado.status, alocado.status

        def desalocar():
            return desalocar_trabalho(
                TrabalhoEncontro.objects.get(pk=anterior.pk)
            ).status

        resultados = self._executar_concorrentes(substituir, desalocar)

        self.assertEqual(resultados.count('bloqueada'), 1)
        anterior.refresh_from_db()
        novo.refresh_from_db()
        self.assertIn(
            (anterior.status, novo.status),
            {
                (
                    TrabalhoEncontro.Status.RETIRADO,
                    TrabalhoEncontro.Status.ALOCADO,
                ),
                (
                    TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO,
                    TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO,
                ),
            },
        )
