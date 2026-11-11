"""Matriz 16.12: concorrência das constraints e flush com triggers."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from hashlib import sha256
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.db import IntegrityError, close_old_connections, connection, connections, transaction
from django.test import TransactionTestCase
from django.utils import timezone

from core.models import (
    AutorizacaoEnvioEntregaConvite, CampanhaConvitesEncontro, ConviteEncontro,
    EntregaConviteEncontro, OportunidadeConviteEncontro, PendenciaEntregaConvite,
    Pessoa, RodadaConvitesEncontro, TentativaEntregaConvite,
)
from core.tests.factories import make_encontro


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL descartável')
class ConcorrenciaEntregaB1PostgresTests(TransactionTestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='concorrencia_b1')
        self.encontro = make_encontro()
        self.now = timezone.now()
        campanha = CampanhaConvitesEncontro.objects.create(encontro=self.encontro, iniciada_por=self.user, iniciada_em=self.now, prazo_confirmacao=self.now + timedelta(days=7))
        self.rodada = RodadaConvitesEncontro.objects.create(campanha=campanha, sequencia=1, tipo='inicial', aberta_em=self.now)

    def entrega(self, identificador):
        pessoa = Pessoa.objects.create(nome='Concorrência')
        convite = ConviteEncontro.objects.create(pessoa=pessoa, encontro=self.encontro, finalidade='participar')
        oportunidade = OportunidadeConviteEncontro.objects.create(rodada=self.rodada, convite=convite, token_digest=sha256(identificador.encode()).hexdigest(), expira_em=self.now + timedelta(days=2))
        return EntregaConviteEncontro.objects.create(oportunidade=oportunidade, canal='email', protocolo='v2')

    def disputa(self, criar):
        barrier = Barrier(2, timeout=10)

        def worker(numero):
            close_old_connections()
            try:
                with transaction.atomic():
                    barrier.wait()
                    criar(numero)
                return 'ok'
            except IntegrityError:
                return 'integridade'
            finally:
                connections['default'].close()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(worker, numero) for numero in (1, 2)]
            resultados = [future.result(timeout=20) for future in futures]
        self.assertCountEqual(resultados, ['ok', 'integridade'])

    def test_tentativas_abertas_concorrentes(self):
        entrega = self.entrega('tentativa')
        def criar(numero):
            TentativaEntregaConvite.objects.create(entrega_id=entrega.pk, numero=numero, origem='automatica', chave_idempotencia=entrega.chave_idempotencia, provider='teste', lease_expira_em=self.now + timedelta(minutes=1))
        self.disputa(criar)
        self.assertEqual(TentativaEntregaConvite.objects.filter(entrega=entrega).count(), 1)

    def test_autorizacoes_abertas_concorrentes(self):
        entrega = self.entrega('autorizacao')
        def criar(numero):
            AutorizacaoEnvioEntregaConvite.objects.create(entrega_id=entrega.pk, autorizada_por_id=self.user.pk, fundamento='falha_comprovada', justificativa=f'teste {numero}')
        self.disputa(criar)
        self.assertEqual(AutorizacaoEnvioEntregaConvite.objects.filter(entrega=entrega).count(), 1)

    def test_pendencias_abertas_concorrentes(self):
        entrega = self.entrega('pendencia')
        def criar(numero):
            PendenciaEntregaConvite.objects.create(encontro_id=self.encontro.pk, entrega_id=entrega.pk, tipo='incerta', motivo=f'teste {numero}')
        self.disputa(criar)
        self.assertEqual(PendenciaEntregaConvite.objects.filter(entrega=entrega).count(), 1)

    def test_flush_com_triggers_ativas(self):
        entrega = self.entrega('flush')
        PendenciaEntregaConvite.objects.create(encontro=self.encontro, entrega=entrega, tipo='incerta', motivo='teste')
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE 'sia_conv_%' AND NOT tgisinternal")
            self.assertEqual(cursor.fetchone()[0], 6)
        # O runner aponta para um banco de teste descartável, nunca o persistente.
        call_command('flush', verbosity=0, interactive=False)
        self.assertFalse(PendenciaEntregaConvite.objects.exists())
