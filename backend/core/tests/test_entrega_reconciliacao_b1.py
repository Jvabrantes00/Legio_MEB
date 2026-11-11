from datetime import timedelta
from hashlib import sha256
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

from core.models import (
    AutorizacaoEnvioEntregaConvite as Autorizacao,
    CampanhaConvitesEncontro, ConviteEncontro, EntregaConviteEncontro as Entrega,
    EvidenciaEntregaConvite as Evidencia, OportunidadeConviteEncontro,
    PendenciaEntregaConvite as Pendencia, Pessoa, RodadaConvitesEncontro,
    TentativaEntregaConvite as Tentativa,
)
from core.tests.factories import make_encontro


class EntregaB1Tests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='b1')
        self.encontro = make_encontro()
        pessoa = Pessoa.objects.create(nome='Pessoa')
        convite = ConviteEncontro.objects.create(pessoa=pessoa, encontro=self.encontro, finalidade='participar')
        now = timezone.now()
        campanha = CampanhaConvitesEncontro.objects.create(encontro=self.encontro, iniciada_por=self.user, iniciada_em=now, prazo_confirmacao=now + timedelta(days=7))
        rodada = RodadaConvitesEncontro.objects.create(campanha=campanha, sequencia=1, tipo='inicial', aberta_em=now)
        oportunidade = OportunidadeConviteEncontro.objects.create(rodada=rodada, convite=convite, token_digest=sha256(b'teste').hexdigest(), expira_em=now + timedelta(days=2))
        self.entrega = Entrega.objects.create(oportunidade=oportunidade, canal='email', protocolo='v2')
        self.legado = Entrega.objects.create(oportunidade=oportunidade, canal='whatsapp')
        self.now = now

    def pendencia(self):
        return Pendencia.objects.create(encontro=self.encontro, entrega=self.entrega, tipo='incerta', motivo='teste')

    def autorizacao(self, **kwargs):
        return Autorizacao.objects.create(entrega=self.entrega, autorizada_por=self.user, fundamento='falha_comprovada', justificativa='teste', **kwargs)

    def tentativa(self, **kwargs):
        values = dict(entrega=self.entrega, numero=1, origem='automatica', chave_idempotencia=self.entrega.chave_idempotencia, provider='teste', lease_expira_em=self.now + timedelta(minutes=1))
        values.update(kwargs)
        return Tentativa.objects.create(**values)

    def rejeita(self, func):
        with self.assertRaises(IntegrityError), transaction.atomic():
            func()

    def test_entrega_status_protocolo_e_legado(self):
        self.assertIsNone(self.legado.protocolo)
        self.entrega.status = 'suspensa'
        self.entrega.save()
        self.rejeita(lambda: Entrega.objects.filter(pk=self.entrega.pk).update(status='incerta'))
        self.rejeita(lambda: Entrega.objects.filter(pk=self.entrega.pk).update(status='desconhecido'))
        self.rejeita(lambda: Entrega.objects.filter(pk=self.entrega.pk).update(protocolo='outro'))
        self.entrega.protocolo = None
        with self.assertRaises(ValidationError):
            self.entrega.save()

    def test_tentativa_unica_finalizacao_e_protecoes(self):
        tentativa = self.tentativa()
        self.rejeita(lambda: self.tentativa(numero=2))
        tentativa.desfecho = 'aceita'
        tentativa.finalizada_em = self.now
        tentativa.save()
        self.rejeita(lambda: self.tentativa(numero=1))
        with self.assertRaises(ValidationError):
            tentativa.save()
        with self.assertRaises(ValidationError):
            Tentativa.objects.filter(pk=tentativa.pk).update(codigo_erro='x')
        with self.assertRaises(ValidationError):
            tentativa.delete()
        with self.assertRaises(ValidationError):
            self.tentativa(entrega=self.legado, numero=3)

    def test_autorizacao_unica_e_uma_tentativa(self):
        auth = self.autorizacao()
        self.rejeita(lambda: self.autorizacao())
        t = self.tentativa(origem='autorizada', autorizacao=auth)
        t.desfecho = 'aceita'
        t.finalizada_em = self.now
        t.save()
        self.rejeita(lambda: self.tentativa(numero=2, origem='autorizada', autorizacao=auth))
        auth.consumida_em = self.now
        auth.save()
        self.autorizacao()
        with self.assertRaises(ValidationError):
            auth.save()
        self.rejeita(lambda: self.tentativa(numero=3, origem='autorizada'))

    def test_regras_de_evidencia_e_pendencia(self):
        pend = self.pendencia()
        self.rejeita(self.pendencia)
        self.rejeita(lambda: Evidencia.objects.create(pendencia=pend, tipo='prova_nao_inicio', origem='interna'))
        ev = Evidencia.objects.create(pendencia=pend, tipo='prova_nao_inicio', origem='interna', referencia='ref')
        with self.assertRaises(ValidationError):
            ev.save()
        with self.assertRaises(ValidationError):
            Evidencia.objects.all().delete()
        pend.status = 'encerrada'
        self.rejeita(pend.save)
        pend.encerrada_em = self.now
        pend.encerrada_por = self.user
        pend.decisao = 'concluida'
        pend.save()
        self.pendencia()
        self.rejeita(lambda: Autorizacao.objects.create(entrega=self.entrega, autorizada_por=self.user, fundamento='reenvio_excepcional', justificativa='x'))
        self.rejeita(lambda: Autorizacao.objects.create(entrega=self.entrega, autorizada_por=self.user, fundamento='legado_prova_nao_inicio', justificativa='x'))

    def test_autorizacao_de_outra_entrega_e_campos_imutaveis(self):
        auth = self.autorizacao()
        with self.assertRaises(ValidationError):
            self.tentativa(entrega=self.legado, origem='autorizada', autorizacao=auth)
        auth.justificativa = 'alterada'
        auth.consumida_em = self.now
        with self.assertRaises(ValidationError):
            auth.save()
        pend = self.pendencia()
        pend.tipo = 'falhou'
        with self.assertRaises(ValidationError):
            pend.save()


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL')
class EntregaB1PostgresTests(EntregaB1Tests):
    def sql(self, sql, params):
        with connection.cursor() as cursor:
            cursor.execute(sql, params)

    def test_triggers_sql_direto(self):
        self.rejeita(lambda: self.sql('UPDATE core_entregaconviteencontro SET protocolo = %s WHERE id = %s', ['v2', self.legado.pk]))
        self.sql('UPDATE core_entregaconviteencontro SET status = %s WHERE id = %s', ['suspensa', self.legado.pk])
        tentativa = self.tentativa()
        self.sql('UPDATE core_tentativaentregaconvite SET desfecho = %s, finalizada_em = %s WHERE id = %s', ['aceita', self.now, tentativa.pk])
        self.rejeita(lambda: self.sql('UPDATE core_tentativaentregaconvite SET codigo_erro = %s WHERE id = %s', ['x', tentativa.pk]))
        self.rejeita(lambda: self.sql('DELETE FROM core_tentativaentregaconvite WHERE id = %s', [tentativa.pk]))
        auth = self.autorizacao()
        self.sql('UPDATE core_autorizacaoenvioentregaconvite SET consumida_em = %s WHERE id = %s', [self.now, auth.pk])
        self.rejeita(lambda: self.sql('UPDATE core_autorizacaoenvioentregaconvite SET justificativa = %s WHERE id = %s', ['x', auth.pk]))
        self.rejeita(lambda: self.sql('DELETE FROM core_autorizacaoenvioentregaconvite WHERE id = %s', [auth.pk]))
        pend = self.pendencia()
        self.sql('UPDATE core_pendenciaentregaconvite SET versao = 1 WHERE id = %s', [pend.pk])
        self.rejeita(lambda: self.sql('UPDATE core_pendenciaentregaconvite SET tipo = %s WHERE id = %s', ['falhou', pend.pk]))
        ev = Evidencia.objects.create(pendencia=pend, tipo='suporte_nota', origem='interna')
        self.rejeita(lambda: self.sql('UPDATE core_evidenciaentregaconvite SET texto = %s WHERE id = %s', ['x', ev.pk]))
        self.rejeita(lambda: self.sql('DELETE FROM core_evidenciaentregaconvite WHERE id = %s', [ev.pk]))
        self.rejeita(lambda: self.sql('DELETE FROM core_pendenciaentregaconvite WHERE id = %s', [pend.pk]))

    def test_insert_legado_e_auditoria(self):
        from core.services.auditoria_encontros import registrar_evento_auditoria_encontro

        tentativa = self.tentativa()
        tentativa.desfecho = 'aceita'
        tentativa.finalizada_em = self.now
        tentativa.save()
        self.rejeita(lambda: self.sql(
            'UPDATE core_tentativaentregaconvite SET entrega_id = %s WHERE id = %s',
            [self.legado.pk, tentativa.pk],
        ))
        # bulk_create contorna save e exercita a trigger de INSERT diretamente.
        self.rejeita(lambda: Tentativa.objects.bulk_create([Tentativa(
            entrega=self.legado, numero=1, origem='automatica',
            chave_idempotencia=self.legado.chave_idempotencia, provider='teste',
            lease_expira_em=self.now + timedelta(minutes=1),
        )]))
        auth = self.autorizacao()
        self.rejeita(lambda: Tentativa.objects.bulk_create([Tentativa(
            entrega=self.legado, numero=2, origem='autorizada', autorizacao=auth,
            chave_idempotencia=self.legado.chave_idempotencia, provider='teste',
            lease_expira_em=self.now + timedelta(minutes=1),
        )]))
        evento = registrar_evento_auditoria_encontro(
            encontro=self.encontro, ator=self.user, fato='b1.teste',
            entidade='entrega', objeto_id=str(self.entrega.pk),
            valor_anterior={}, valor_novo={}, campos_permitidos=set(),
        )
        self.rejeita(lambda: self.sql('UPDATE core_eventoauditoriaencontro SET fato = %s WHERE id = %s', ['x', evento.pk]))
        self.rejeita(lambda: self.sql('DELETE FROM core_eventoauditoriaencontro WHERE id = %s', [evento.pk]))
