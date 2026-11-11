"""Casos complementares das matrizes de integridade B1, seções 16.7 e 16.12."""
from datetime import timedelta
from unittest import skipUnless

from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase

from core.models import (
    AutorizacaoEnvioEntregaConvite as Autorizacao,
    EntregaConviteEncontro as Entrega,
    EvidenciaEntregaConvite as Evidencia,
    PendenciaEntregaConvite as Pendencia,
    TentativaEntregaConvite as Tentativa,
)
from core.tests import test_entrega_reconciliacao_b1 as fixtures


class FixtureMixin:
    setUp = fixtures.EntregaB1Tests.setUp
    pendencia = fixtures.EntregaB1Tests.pendencia
    autorizacao = fixtures.EntregaB1Tests.autorizacao
    tentativa = fixtures.EntregaB1Tests.tentativa
    rejeita = fixtures.EntregaB1Tests.rejeita


class MatrizB1SQLiteTests(FixtureMixin, TestCase):
    def test_estados_e_contador(self):
        for status in ('enviando', 'incerta'):
            with self.subTest(status=status, tentativas=0):
                self.rejeita(lambda: Entrega.objects.filter(pk=self.entrega.pk).update(status=status))
            with self.subTest(status=status, tentativas=1):
                with transaction.atomic():
                    instante = self.entrega.criada_em + timedelta(seconds=1)
                    Entrega.objects.filter(pk=self.entrega.pk).update(status=status, tentativas=1, primeira_tentativa_em=instante, ultima_tentativa_em=instante)
                    self.assertEqual(Entrega.objects.get(pk=self.entrega.pk).status, status)
                    transaction.set_rollback(True)
        for status in ('pendente', 'suspensa'):
            with self.subTest(status=status):
                Entrega.objects.filter(pk=self.entrega.pk).update(status=status)
                self.assertEqual(Entrega.objects.get(pk=self.entrega.pk).status, status)

    def test_origem_autorizacao_combinacoes(self):
        auth = self.autorizacao()
        for origem, autorizacao, valido in (
            ('automatica', None, True), ('autorizada', auth, True),
            ('automatica', auth, False), ('autorizada', None, False),
        ):
            with self.subTest(origem=origem, autorizacao=bool(autorizacao)):
                with transaction.atomic():
                    if valido:
                        self.tentativa(origem=origem, autorizacao=autorizacao)
                    else:
                        self.rejeita(lambda: self.tentativa(origem=origem, autorizacao=autorizacao))
                    transaction.set_rollback(True)

    def test_fundamentos_ciencia_e_evidencia(self):
        pend = self.pendencia()
        evidencia = Evidencia.objects.create(pendencia=pend, tipo='prova_nao_inicio', origem='interna', referencia='ref')
        fundamentos = {
            'nao_aceitacao_confirmada': (False, True),
            'falha_comprovada': (False, False),
            'reenvio_excepcional': (True, False),
            'legado_prova_nao_inicio': (False, True),
            'legado_nao_aceitacao_confirmada': (False, True),
            'legado_sem_prova_reconciliado': (True, False),
        }
        for fundamento, (exige_ciencia, exige_evidencia) in fundamentos.items():
            for ciencia in (False, True):
                for com_evidencia in (False, True):
                    with self.subTest(fundamento=fundamento, ciencia=ciencia, evidencia=com_evidencia):
                        kwargs = dict(entrega=self.entrega, autorizada_por=self.user, fundamento=fundamento, justificativa='teste', ciencia_duplicidade=ciencia, evidencia_base=evidencia if com_evidencia else None)
                        valido = (not exige_ciencia or ciencia) and (not exige_evidencia or com_evidencia)
                        with transaction.atomic():
                            if valido:
                                Autorizacao.objects.create(**kwargs)
                            else:
                                self.rejeita(lambda: Autorizacao.objects.create(**kwargs))
                            transaction.set_rollback(True)

    def test_evidencias_conclusivas_exigem_referencia(self):
        pend = self.pendencia()
        for tipo in ('prova_nao_inicio', 'provedor_confirmou_nao_aceitacao', 'provedor_confirmou_aceitacao'):
            for referencia in ('', 'ref-verificavel'):
                with self.subTest(tipo=tipo, referencia=referencia):
                    if referencia:
                        Evidencia.objects.create(pendencia=pend, tipo=tipo, origem='interna', referencia=referencia)
                    else:
                        self.rejeita(lambda: Evidencia.objects.create(pendencia=pend, tipo=tipo, origem='interna', referencia=referencia))

    def test_pendencia_encerrada_exige_cada_campo(self):
        pend = self.pendencia()
        for campo in ('encerrada_em', 'encerrada_por', 'decisao'):
            with self.subTest(campo_ausente=campo):
                valores = dict(status='encerrada', encerrada_em=self.now, encerrada_por=self.user, decisao='concluida')
                valores[campo] = '' if campo == 'decisao' else None
                for chave, valor in valores.items():
                    setattr(pend, chave, valor)
                self.rejeita(pend.save)
        pend.encerrada_em, pend.encerrada_por, pend.decisao = self.now, self.user, 'concluida'
        pend.save()
        self.assertEqual(pend.status, 'encerrada')

    def test_imutabilidade_e_exclusao_no_orm(self):
        pend = self.pendencia()
        ev = Evidencia.objects.create(pendencia=pend, tipo='suporte_nota', origem='interna')
        auth = self.autorizacao()
        tent = self.tentativa(origem='autorizada', autorizacao=auth)
        for obj in (pend, ev, auth, tent):
            with self.subTest(modelo=type(obj).__name__, operacao='delete'):
                with self.assertRaises(ValidationError):
                    obj.delete()
            with self.subTest(modelo=type(obj).__name__, operacao='queryset.delete'):
                with self.assertRaises(ValidationError):
                    type(obj).objects.filter(pk=obj.pk).delete()
            with self.subTest(modelo=type(obj).__name__, operacao='queryset.update'):
                with self.assertRaises(ValidationError):
                    type(obj).objects.filter(pk=obj.pk).update(pk=obj.pk)
            with self.subTest(modelo=type(obj).__name__, operacao='bulk_update'):
                with self.assertRaises(ValidationError):
                    type(obj).objects.bulk_update([obj], ['id'])

    def test_dependencias_protect(self):
        self.pendencia()
        for obj in (self.entrega, self.user, self.encontro):
            with self.subTest(modelo=type(obj).__name__):
                with self.assertRaises(ProtectedError):
                    obj.delete()


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL descartável')
class MatrizB1PostgresTests(FixtureMixin, TestCase):
    def sql(self, statement, params):
        with connection.cursor() as cursor:
            cursor.execute(statement, params)

    def test_protocolo_v2_para_null(self):
        self.rejeita(lambda: self.sql('UPDATE core_entregaconviteencontro SET protocolo = NULL WHERE id = %s', [self.entrega.pk]))

    def test_identidade_de_tentativa_aberta(self):
        tentativa = self.tentativa()
        self.rejeita(lambda: self.sql('UPDATE core_tentativaentregaconvite SET numero = %s, desfecho = %s, finalizada_em = %s WHERE id = %s', [2, 'aceita', self.now, tentativa.pk]))
        tentativa.refresh_from_db()
        self.assertEqual(tentativa.desfecho, 'iniciada')

    def test_status_e_contadores_legados(self):
        instante = self.legado.criada_em + timedelta(seconds=1)
        self.sql('UPDATE core_entregaconviteencontro SET status = %s, tentativas = %s, primeira_tentativa_em = %s, ultima_tentativa_em = %s WHERE id = %s', ['enviando', 1, instante, instante, self.legado.pk])
        self.legado.refresh_from_db()
        self.assertEqual((self.legado.status, self.legado.tentativas, self.legado.protocolo), ('enviando', 1, None))

    def test_segundo_consumo_e_identidade_autorizacao_aberta(self):
        auth = self.autorizacao()
        self.rejeita(lambda: self.sql('UPDATE core_autorizacaoenvioentregaconvite SET justificativa = %s, consumida_em = %s WHERE id = %s', ['outra', self.now, auth.pk]))
        self.sql('UPDATE core_autorizacaoenvioentregaconvite SET consumida_em = %s WHERE id = %s', [self.now, auth.pk])
        self.rejeita(lambda: self.sql('UPDATE core_autorizacaoenvioentregaconvite SET consumida_em = %s WHERE id = %s', [self.now + timedelta(seconds=1), auth.pk]))
