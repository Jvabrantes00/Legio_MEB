from datetime import timedelta
from hashlib import sha256

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from core.models import (
    CampanhaConvitesEncontro,
    ConviteEncontro,
    EntregaConviteEncontro,
    OportunidadeConviteEncontro,
    Pessoa,
    RodadaConvitesEncontro,
)
from core.tests.factories import make_encontro


class CampanhaConvitesModelTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='fichas.campanha',
        )
        self.encontro = make_encontro()
        self.pessoa = Pessoa.objects.create(nome='Pessoa convidada')
        self.convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )
        self.inicio = timezone.now()
        self.campanha = CampanhaConvitesEncontro.objects.create(
            encontro=self.encontro,
            iniciada_por=self.usuario,
            iniciada_em=self.inicio,
            prazo_confirmacao=self.inicio + timedelta(days=7),
        )
        self.rodada = RodadaConvitesEncontro.objects.create(
            campanha=self.campanha,
            sequencia=1,
            tipo=RodadaConvitesEncontro.Tipo.INICIAL,
            aberta_em=self.inicio,
        )

    @staticmethod
    def digest(valor):
        return sha256(valor.encode()).hexdigest()

    def criar_oportunidade(self, *, rodada=None, convite=None, segredo='segredo-1'):
        return OportunidadeConviteEncontro.objects.create(
            rodada=rodada or self.rodada,
            convite=convite or self.convite,
            token_digest=self.digest(segredo),
            expira_em=timezone.now() + timedelta(days=2),
        )

    def test_campanha_possui_varias_rodadas_ordenadas(self):
        segunda = RodadaConvitesEncontro.objects.create(
            campanha=self.campanha,
            sequencia=2,
            tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
            aberta_em=self.inicio + timedelta(days=1),
        )

        self.assertEqual(
            list(self.campanha.rodadas.values_list('pk', flat=True)),
            [self.rodada.pk, segunda.pk],
        )

    def test_sequencia_e_unica_dentro_da_campanha(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            RodadaConvitesEncontro.objects.create(
                campanha=self.campanha,
                sequencia=1,
                tipo=RodadaConvitesEncontro.Tipo.PRORROGACAO,
            )

    def test_mesma_sequencia_e_permitida_em_campanhas_diferentes(self):
        outro_encontro = make_encontro()
        outra_campanha = CampanhaConvitesEncontro.objects.create(
            encontro=outro_encontro,
            iniciada_por=self.usuario,
            iniciada_em=self.inicio,
            prazo_confirmacao=self.inicio + timedelta(days=7),
        )

        rodada = RodadaConvitesEncontro.objects.create(
            campanha=outra_campanha,
            sequencia=1,
            tipo=RodadaConvitesEncontro.Tipo.INICIAL,
        )

        self.assertEqual(rodada.sequencia, self.rodada.sequencia)

    def test_oportunidade_vincula_convite_logico_a_rodada(self):
        oportunidade = self.criar_oportunidade()

        self.assertEqual(oportunidade.convite, self.convite)
        self.assertEqual(oportunidade.rodada, self.rodada)
        self.assertEqual(oportunidade.status, OportunidadeConviteEncontro.Status.PENDENTE)

    def test_oportunidade_e_unica_por_convite_e_rodada(self):
        self.criar_oportunidade()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_oportunidade(segredo='segredo-2')

    def test_mesmo_convite_pode_receber_oportunidade_em_rodada_posterior(self):
        primeira = self.criar_oportunidade()
        rodada_posterior = RodadaConvitesEncontro.objects.create(
            campanha=self.campanha,
            sequencia=2,
            tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
        )
        segunda = self.criar_oportunidade(
            rodada=rodada_posterior,
            segredo='segredo-2',
        )

        self.assertEqual(primeira.convite, segunda.convite)
        self.assertNotEqual(primeira.rodada, segunda.rodada)

    def test_digest_e_unico_e_nao_armazena_token_reversivel(self):
        segredo = 'token-publico-que-nao-pode-ser-persistido'
        oportunidade = self.criar_oportunidade(segredo=segredo)
        pessoa_2 = Pessoa.objects.create(nome='Outra pessoa')
        convite_2 = ConviteEncontro.objects.create(
            pessoa=pessoa_2,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )

        oportunidade.refresh_from_db()
        self.assertEqual(oportunidade.token_digest, self.digest(segredo))
        self.assertNotEqual(oportunidade.token_digest, segredo)
        self.assertNotIn(
            'token',
            {campo.name for campo in oportunidade._meta.concrete_fields},
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            OportunidadeConviteEncontro.objects.create(
                rodada=self.rodada,
                convite=convite_2,
                token_digest=oportunidade.token_digest,
                expira_em=timezone.now() + timedelta(days=2),
            )

    def test_entregas_email_e_whatsapp_compartilham_a_oportunidade(self):
        oportunidade = self.criar_oportunidade()
        email = EntregaConviteEncontro.objects.create(
            oportunidade=oportunidade,
            canal=EntregaConviteEncontro.Canal.EMAIL,
        )
        whatsapp = EntregaConviteEncontro.objects.create(
            oportunidade=oportunidade,
            canal=EntregaConviteEncontro.Canal.WHATSAPP,
        )

        self.assertEqual(email.status, EntregaConviteEncontro.Status.PENDENTE)
        self.assertEqual(whatsapp.status, EntregaConviteEncontro.Status.PENDENTE)
        self.assertEqual(oportunidade.entregas.count(), 2)
        with self.assertRaises(IntegrityError), transaction.atomic():
            EntregaConviteEncontro.objects.create(
                oportunidade=oportunidade,
                canal=EntregaConviteEncontro.Canal.EMAIL,
            )

    def test_constraints_de_timestamps_rejeitam_estados_incoerentes(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            CampanhaConvitesEncontro.objects.create(
                encontro=make_encontro(),
                iniciada_por=self.usuario,
                iniciada_em=self.inicio,
                prazo_confirmacao=self.inicio - timedelta(seconds=1),
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            RodadaConvitesEncontro.objects.create(
                campanha=self.campanha,
                sequencia=2,
                tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
                status=RodadaConvitesEncontro.Status.ENCERRADA,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            OportunidadeConviteEncontro.objects.create(
                rodada=self.rodada,
                convite=self.convite,
                token_digest=self.digest('expiracao-invalida'),
                expira_em=timezone.now() - timedelta(seconds=1),
            )

        oportunidade = self.criar_oportunidade(segredo='entrega-incoerente')
        with self.assertRaises(IntegrityError), transaction.atomic():
            EntregaConviteEncontro.objects.create(
                oportunidade=oportunidade,
                canal=EntregaConviteEncontro.Canal.EMAIL,
                tentativas=1,
            )
        with self.assertRaises(IntegrityError), transaction.atomic():
            EntregaConviteEncontro.objects.create(
                oportunidade=oportunidade,
                canal=EntregaConviteEncontro.Canal.WHATSAPP,
                status=EntregaConviteEncontro.Status.ENTREGUE,
                entregue_em=timezone.now(),
            )

    def test_vinculos_historicos_sao_protegidos(self):
        oportunidade = self.criar_oportunidade()
        EntregaConviteEncontro.objects.create(
            oportunidade=oportunidade,
            canal=EntregaConviteEncontro.Canal.EMAIL,
        )

        for objeto in (
            self.usuario,
            self.encontro,
            self.campanha,
            self.rodada,
            self.convite,
            oportunidade,
        ):
            with self.subTest(model=type(objeto).__name__):
                with self.assertRaises(ProtectedError):
                    objeto.delete()

    def test_convite_encontro_preserva_semantica_e_unicidade_originais(self):
        self.assertEqual(
            set(ConviteEncontro.Status.values),
            {'convidado', 'confirmado', 'recusado', 'sem_resposta'},
        )
        self.assertEqual(
            self.convite.finalidade,
            ConviteEncontro.Finalidade.PARTICIPAR,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ConviteEncontro.objects.create(
                pessoa=self.pessoa,
                encontro=self.encontro,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            )
