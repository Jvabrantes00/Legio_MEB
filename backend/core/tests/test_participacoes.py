from rest_framework import status
from unittest.mock import patch

from django.db import IntegrityError

from core.models import ParticipacaoEncontro
from core.tests.base import (
    AuthenticatedAPITestCase,
    AuthenticatedAPITransactionTestCase,
)
from core.tests.factories import make_alpinista, make_encontro, make_funcao


class ParticipacaoRegressionTests(AuthenticatedAPITestCase):
    def test_efetivacao_cria_participacao_e_confirma_alpinista(self):
        # Arrange
        alpinista = make_alpinista(status='pendente')
        encontro = make_encontro()

        # Act
        response = self.client.post(
            f'/api/encontros/{encontro.pk}/efetivar-encontristas/',
            {'alpinistas_ids': [alpinista.pk]},
            format='json',
        )
        alpinista.refresh_from_db()

        # Assert: hoje o signal troca o status para Ativo antes da confirmação.
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(
            ParticipacaoEncontro.objects.filter(
                encontro=encontro,
                alpinista=alpinista,
                funcao__tipo='encontrista',
            ).exists()
        )
        self.assertEqual(alpinista.status, 'confirmado')

    def test_remocao_exclui_participacao_e_retorna_para_pendente(self):
        # Arrange
        alpinista = make_alpinista(status='confirmado')
        encontro = make_encontro()
        funcao = make_funcao(nome='Encontrista', tipo='encontrista')
        ParticipacaoEncontro.objects.create(
            alpinista=alpinista,
            encontro=encontro,
            funcao=funcao,
        )
        alpinista.status = 'confirmado'
        alpinista.save(update_fields=['status'])

        # Act
        response = self.client.post(
            f'/api/encontros/{encontro.pk}/remover-encontristas/',
            {'alpinistas_ids': [alpinista.pk]},
            format='json',
        )
        alpinista.refresh_from_db()

        # Assert
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(
            ParticipacaoEncontro.objects.filter(
                encontro=encontro,
                alpinista=alpinista,
            ).exists()
        )
        self.assertEqual(alpinista.status, 'pendente')


    def test_criacao_de_participacao_nao_imprime_nome_em_stdout(self):
        with patch('builtins.print') as mocked_print:
            ParticipacaoEncontro.objects.create(
                alpinista=make_alpinista(),
                encontro=make_encontro(),
                funcao=make_funcao(nome='Encontrista', tipo='encontrista'),
            )

        mocked_print.assert_not_called()


class ParticipacaoLoteRegressionTests(AuthenticatedAPITransactionTestCase):
    reset_sequences = True

    def test_efetivacao_em_lote_valido_persiste_todos(self):
        encontro = make_encontro()
        primeiro = make_alpinista()
        segundo = make_alpinista()

        response = self.client.post(
            f'/api/encontros/{encontro.pk}/efetivar-encontristas/',
            {'alpinistas_ids': [primeiro.pk, segundo.pk]},
            format='json',
        )
        primeiro.refresh_from_db()
        segundo.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            ParticipacaoEncontro.objects.filter(
                encontro=encontro,
                alpinista__in=(primeiro, segundo),
                funcao__tipo='encontrista',
            ).count(),
            2,
        )
        self.assertEqual(primeiro.status, 'confirmado')
        self.assertEqual(segundo.status, 'confirmado')

    def test_efetivacao_em_lote_nao_deve_persistir_resultado_parcial(self):
        # Arrange
        encontro = make_encontro()
        primeiro = make_alpinista()
        segundo = make_alpinista()
        funcao_equipe = make_funcao(nome='Equipe', tipo='equipe')
        make_funcao(nome='Encontrista', tipo='encontrista')
        ParticipacaoEncontro.objects.create(
            alpinista=segundo,
            encontro=encontro,
            funcao=funcao_equipe,
        )

        # Act: o segundo item viola a unicidade alpinista/encontro.
        response = self.client.post(
            f'/api/encontros/{encontro.pk}/efetivar-encontristas/',
            {'alpinistas_ids': [primeiro.pk, segundo.pk]},
            format='json',
        )
        primeiro.refresh_from_db()

        # Assert: participação e status do primeiro item devem sofrer rollback.
        self.assertFalse(
            ParticipacaoEncontro.objects.filter(
                encontro=encontro,
                alpinista=primeiro,
            ).exists()
        )
        self.assertEqual(primeiro.status, 'pendente')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_efetivacao_com_funcoes_encontrista_duplicadas_e_deterministica(self):
        encontro = make_encontro()
        alpinista = make_alpinista()
        primeira_funcao = make_funcao(nome='Encontrista A', tipo='encontrista')
        make_funcao(nome='Encontrista B', tipo='encontrista')

        response = self.client.post(
            f'/api/encontros/{encontro.pk}/efetivar-encontristas/',
            {'alpinistas_ids': [alpinista.pk]},
            format='json',
        )

        participacao = ParticipacaoEncontro.objects.get(
            encontro=encontro,
            alpinista=alpinista,
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(participacao.funcao, primeira_funcao)

    def test_remocao_em_lote_reverte_tudo_quando_auditoria_falha(self):
        encontro = make_encontro()
        funcao = make_funcao(nome='Encontrista', tipo='encontrista')
        primeiro = make_alpinista(status='confirmado')
        segundo = make_alpinista(status='confirmado')
        for alpinista in (primeiro, segundo):
            ParticipacaoEncontro.objects.create(
                encontro=encontro,
                alpinista=alpinista,
                funcao=funcao,
            )
            alpinista.status = 'confirmado'
            alpinista.save(update_fields=['status'])

        with patch(
            'core.views.LogSistema.objects.create',
            side_effect=IntegrityError,
        ):
            response = self.client.post(
                f'/api/encontros/{encontro.pk}/remover-encontristas/',
                {'alpinistas_ids': [primeiro.pk, segundo.pk]},
                format='json',
            )

        primeiro.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            ParticipacaoEncontro.objects.filter(
                encontro=encontro,
                alpinista__in=(primeiro, segundo),
            ).count(),
            2,
        )
        self.assertEqual(primeiro.status, 'confirmado')
        self.assertEqual(segundo.status, 'confirmado')
