from datetime import date, datetime, time, timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    AtendimentoPreEncontro,
    CalendarioEncontro,
    CampanhaConvitesEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DiaEncontro,
    Encontro,
    EntregaConviteEncontro,
    EventoAuditoriaEncontro,
    Inscricao,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    OutboxEntregaConvite,
    Pessoa,
    PreEncontro,
    PreSelecaoEncontrista,
    RodadaConvitesEncontro,
)
from core.roles import SiaRole
from core.services.preselecoes_encontristas import (
    ErroPreSelecaoEncontrista,
    aprovar_encaminhamento_preselecao,
    encerrar_preselecao_encontrista,
    preselecionar_encontrista,
)
from core.tests.factories import make_encontro


class EncaminhamentoPreSelecaoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='fichas-encaminhamento')
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.encontro = make_encontro(
            tipo=Encontro.Tipo.ESCALADA,
            status=Encontro.Status.EM_PREPARACAO,
            data_referencia=date(2030, 6, 1),
        )
        ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=80,
            idade_minima=18,
            idade_maxima=25,
            inscricoes_abrem_em=timezone.make_aware(datetime(2029, 1, 1)),
            inscricoes_encerram_em=timezone.make_aware(datetime(2030, 5, 1)),
        )
        calendario = CalendarioEncontro.objects.create(
            encontro=self.encontro,
            versao=1,
            vigente=True,
            oficializado_em=timezone.now(),
        )
        DiaEncontro.objects.create(
            calendario=calendario,
            ordem=1,
            data=date(2030, 6, 1),
        )
        self.pre_encontro = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 5, 15),
            horario=time(14),
            local='Local do Pré-Encontro',
        )
        self.pessoa = Pessoa.objects.create(
            nome='Pessoa encaminhada',
            data_nascimento=date(2010, 1, 1),
        )
        self.inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=self.pessoa,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )
        self.preselecao = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.INSCRICAO,
            inscricao=self.inscricao,
        )

    def _aprovar(self):
        return aprovar_encaminhamento_preselecao(
            usuario=self.usuario,
            encontro=self.encontro,
            preselecao=self.preselecao,
        )

    def _campanha(self, status):
        iniciada_em = timezone.make_aware(datetime(2030, 1, 1, 8))
        encerrada_em = (
            timezone.make_aware(datetime(2030, 6, 1, 8))
            if status == CampanhaConvitesEncontro.Status.ENCERRADA
            else None
        )
        return CampanhaConvitesEncontro.objects.create(
            encontro=self.encontro,
            status=status,
            iniciada_por=self.usuario,
            iniciada_em=iniciada_em,
            prazo_confirmacao=timezone.make_aware(datetime(2030, 5, 1)),
            encerrada_em=encerrada_em,
        )

    def test_aprova_sem_campanha_sem_criar_entrega_oportunidade_ou_rodada(self):
        resultado = self._aprovar()

        self.preselecao.refresh_from_db()
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.ENCAMINHADA,
        )
        self.assertTrue(resultado.convite_criado)
        self.assertEqual(
            resultado.convite.status,
            ConviteEncontro.Status.CONVIDADO,
        )
        self.assertFalse(CampanhaConvitesEncontro.objects.exists())
        self.assertFalse(RodadaConvitesEncontro.objects.exists())
        self.assertFalse(OportunidadeConviteEncontro.objects.exists())
        self.assertFalse(EntregaConviteEncontro.objects.exists())
        self.assertFalse(OutboxEntregaConvite.objects.exists())

    def test_demais_papeis_nao_podem_aprovar_encaminhamento(self):
        usuario = User.objects.create_user(username='diretoria-encaminhamento')
        grupo, _ = Group.objects.get_or_create(name=SiaRole.DIRETORIA.value)
        usuario.groups.add(grupo)

        with self.assertRaises(PermissionDenied):
            aprovar_encaminhamento_preselecao(
                usuario=usuario,
                encontro=self.encontro,
                preselecao=self.preselecao,
            )

        self.assertFalse(ConviteEncontro.objects.exists())

    def test_superuser_tem_bypass_tecnico_para_aprovar_encaminhamento(self):
        usuario = User.objects.create_superuser(
            username='superuser-encaminhamento',
            email='superuser-encaminhamento@example.test',
            password='senha-exclusiva-de-teste',
        )

        resultado = aprovar_encaminhamento_preselecao(
            usuario=usuario,
            encontro=self.encontro,
            preselecao=self.preselecao,
        )

        self.assertEqual(resultado.convite.pessoa, self.pessoa)

    def test_campanha_ativa_permite_sem_criar_oportunidade(self):
        campanha = self._campanha(CampanhaConvitesEncontro.Status.ATIVA)

        resultado = self._aprovar()

        campanha.refresh_from_db()
        self.assertEqual(campanha.status, CampanhaConvitesEncontro.Status.ATIVA)
        self.assertIsNotNone(resultado.convite)
        self.assertFalse(OportunidadeConviteEncontro.objects.exists())

    def test_configuracao_ausente_bloqueia_nova_aprovacao(self):
        ConfiguracaoEncontristasEncontro.objects.filter(
            encontro=self.encontro,
        ).delete()

        with self.assertRaises(ErroPreSelecaoEncontrista):
            self._aprovar()

        self.preselecao.refresh_from_db()
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )
        self.assertFalse(ConviteEncontro.objects.exists())

    def test_campanha_encerrada_bloqueia_encaminhamento(self):
        campanha = self._campanha(CampanhaConvitesEncontro.Status.ENCERRADA)

        with self.assertRaises(ErroPreSelecaoEncontrista):
            self._aprovar()

        self.preselecao.refresh_from_db()
        campanha.refresh_from_db()
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )
        self.assertEqual(
            campanha.status,
            CampanhaConvitesEncontro.Status.ENCERRADA,
        )

    def test_campanha_aguardando_decisao_bloqueia_encaminhamento(self):
        campanha = self._campanha(
            CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO,
        )

        with self.assertRaises(ErroPreSelecaoEncontrista):
            self._aprovar()

        self.preselecao.refresh_from_db()
        campanha.refresh_from_db()
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )
        self.assertEqual(
            campanha.status,
            CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO,
        )

    def test_preselecao_encerrada_bloqueia_encaminhamento(self):
        encerrar_preselecao_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            preselecao=self.preselecao,
        )

        with self.assertRaises(ErroPreSelecaoEncontrista):
            self._aprovar()

        self.assertFalse(ConviteEncontro.objects.exists())

    def test_reutiliza_convite_confirmado_e_repeticao_e_idempotente(self):
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        primeiro = self._aprovar()
        repetido = self._aprovar()

        self.assertEqual(primeiro.convite, convite)
        self.assertEqual(repetido.convite, convite)
        self.assertTrue(repetido.confirmacao_preexistente)
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.encaminhamento_aprovado',
            ).count(),
            1,
        )

    def test_repeticao_idempotente_ignora_contexto_alterado_posteriormente(self):
        campanha = self._campanha(CampanhaConvitesEncontro.Status.ATIVA)
        primeiro = self._aprovar()
        campanha.status = CampanhaConvitesEncontro.Status.ENCERRADA
        campanha.encerrada_em = campanha.prazo_confirmacao + timedelta(days=1)
        campanha.save(update_fields=[
            'status',
            'encerrada_em',
            'atualizada_em',
        ])
        ConfiguracaoEncontristasEncontro.objects.filter(
            encontro=self.encontro,
        ).delete()

        repetido = self._aprovar()

        self.assertEqual(repetido.convite, primeiro.convite)
        self.assertFalse(repetido.convite_criado)
        campanha.refresh_from_db()
        self.assertEqual(
            campanha.status,
            CampanhaConvitesEncontro.Status.ENCERRADA,
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.encaminhamento_aprovado',
            ).count(),
            1,
        )

    def test_reutiliza_convites_convidado_e_sem_resposta_sem_alterar_status(self):
        for status in (
            ConviteEncontro.Status.CONVIDADO,
            ConviteEncontro.Status.SEM_RESPOSTA,
        ):
            with self.subTest(status=status):
                convite = ConviteEncontro.objects.create(
                    pessoa=self.pessoa,
                    encontro=self.encontro,
                    finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
                    status=status,
                )

                resultado = self._aprovar()

                convite.refresh_from_db()
                self.assertEqual(resultado.convite, convite)
                self.assertEqual(convite.status, status)
                convite.delete()
                self.preselecao.estado = (
                    PreSelecaoEncontrista.Estado.PRESELECIONADA
                )
                self.preselecao.encaminhada_por = None
                self.preselecao.encaminhada_em = None
                self.preselecao.save(update_fields=[
                    'estado',
                    'encaminhada_por',
                    'encaminhada_em',
                    'atualizada_em',
                ])

    def test_reutiliza_convite_com_inscricao_legada(self):
        inscricao_legada = Inscricao.objects.create(
            pessoa=self.pessoa,
            tipo=Inscricao.Tipo.ESCALADA,
        )
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            inscricao=inscricao_legada,
        )

        resultado = self._aprovar()

        resultado.convite.refresh_from_db()
        self.assertEqual(resultado.convite, convite)
        self.assertEqual(resultado.convite.inscricao, inscricao_legada)

    def test_convite_recusado_bloqueia_sem_reabrir(self):
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.RECUSADO,
        )

        with self.assertRaises(ErroPreSelecaoEncontrista):
            self._aprovar()

        convite.refresh_from_db()
        self.assertEqual(convite.status, ConviteEncontro.Status.RECUSADO)

    def test_origem_pessoa_por_atendimento_e_encaminhada(self):
        pessoa = Pessoa.objects.create(
            nome='Pessoa por atendimento',
            data_nascimento=date(2010, 2, 1),
        )
        atendimento = AtendimentoPreEncontro.objects.create(
            pre_encontro=self.pre_encontro,
            pessoa=pessoa,
            registrado_por=self.usuario,
        )
        preselecao = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            atendimento=atendimento,
        )

        resultado = aprovar_encaminhamento_preselecao(
            usuario=self.usuario,
            encontro=self.encontro,
            preselecao=preselecao,
        )

        self.assertEqual(resultado.convite.pessoa, pessoa)
        self.assertEqual(
            resultado.preselecao.origem_tipo,
            PreSelecaoEncontrista.OrigemTipo.PESSOA,
        )

    def test_avulso_regularizado_persiste_pessoa_sem_mudar_origem(self):
        atendimento = AtendimentoPreEncontro.objects.create(
            pre_encontro=self.pre_encontro,
            registrado_por=self.usuario,
            nome_informado='Pessoa originalmente avulsa',
            data_nascimento_informada=date(2010, 3, 1),
            telefone_informado='61999990000',
        )
        preselecao = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            atendimento=atendimento,
        )
        pessoa = Pessoa.objects.create(
            nome='Pessoa avulsa regularizada',
            data_nascimento=date(2010, 3, 1),
        )
        atendimento.pessoa = pessoa
        atendimento.save(update_fields=['pessoa', 'atualizado_em'])

        resultado = aprovar_encaminhamento_preselecao(
            usuario=self.usuario,
            encontro=self.encontro,
            preselecao=preselecao,
        )

        self.assertEqual(resultado.preselecao.pessoa_resolvida, pessoa)
        self.assertEqual(
            resultado.preselecao.origem_tipo,
            PreSelecaoEncontrista.OrigemTipo.AVULSO,
        )

    def test_avulso_sem_pessoa_resolvida_bloqueia_encaminhamento(self):
        atendimento = AtendimentoPreEncontro.objects.create(
            pre_encontro=self.pre_encontro,
            registrado_por=self.usuario,
            nome_informado='Pessoa ainda avulsa',
            data_nascimento_informada=date(2010, 4, 1),
            telefone_informado='61999990001',
        )
        preselecao = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            atendimento=atendimento,
        )

        with self.assertRaises(ErroPreSelecaoEncontrista):
            aprovar_encaminhamento_preselecao(
                usuario=self.usuario,
                encontro=self.encontro,
                preselecao=preselecao,
            )

        self.assertFalse(
            ConviteEncontro.objects.filter(
                encontro=self.encontro,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            ).exists()
        )

    def test_identidade_divergente_bloqueia_encaminhamento(self):
        outra_pessoa = Pessoa.objects.create(
            nome='Outra Pessoa',
            data_nascimento=date(2010, 5, 1),
        )
        self.inscricao.pessoa = outra_pessoa
        self.inscricao.save(update_fields=['pessoa', 'atualizada_em'])

        with self.assertRaises(ErroPreSelecaoEncontrista):
            self._aprovar()

        self.assertFalse(ConviteEncontro.objects.exists())

    def test_elegibilidade_invalida_bloqueia_encaminhamento(self):
        self.pessoa.data_nascimento = date(2020, 1, 1)
        self.pessoa.save(update_fields=['data_nascimento', 'atualizado_em'])

        with self.assertRaises(ErroPreSelecaoEncontrista):
            self._aprovar()

        self.preselecao.refresh_from_db()
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )
        self.assertFalse(ConviteEncontro.objects.exists())

    def test_falha_na_auditoria_reverte_convite_e_estado(self):
        with patch(
            'core.services.preselecoes_encontristas.'
            'registrar_evento_auditoria_encontro',
            side_effect=ValidationError('falha de auditoria'),
        ):
            with self.assertRaises(ValidationError):
                self._aprovar()

        self.preselecao.refresh_from_db()
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )
        self.assertFalse(
            ConviteEncontro.objects.filter(
                pessoa=self.pessoa,
                encontro=self.encontro,
                finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            ).exists()
        )
