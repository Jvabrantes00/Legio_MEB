from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import (
    CalendarioEncontro,
    CampanhaConvitesEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DiaEncontro,
    EntregaConviteEncontro,
    EventoAuditoriaEncontro,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    OutboxEntregaConvite,
    Pessoa,
    RodadaConvitesEncontro,
    SinalReposicaoCampanha,
    TelefonePessoa,
)
from core.notifications import (
    CategoriaFalhaEntrega,
    ProviderEntregaConvite,
    ResultadoEntregaConvite,
)
from core.roles import SiaRole
from core.services import campanhas_convites
from core.services.configuracao_encontristas import (
    alterar_configuracao_encontristas,
)
from core.services.entregas_convites import (
    ConfiguracaoOutboxInvalida,
    descriptografar_token_convite,
    processar_outbox_entrega_convite,
    reconciliar_outboxes_entrega_convite,
)
from core.services.reposicao_campanha import (
    processar_sinal_reposicao_campanha,
    registrar_transicao_lotado_para_disponivel,
)
from core.tasks import processar_prazo_campanha
from core.tests.factories import make_encontro


class _AdapterFalso:
    def __init__(self, provider, resultados):
        self.provider = provider
        self.resultados = list(resultados)
        self.payloads = []

    def entregar(self, payload):
        self.payloads.append(payload)
        return self.resultados.pop(0)


class ConviteTaskFixtureMixin:
    def preparar_dominio(self, *, capacidade=2):
        self.momento = timezone.make_aware(datetime(2030, 1, 10, 9, 0))
        self.prazo = self.momento + timedelta(days=10)
        self.usuario = get_user_model().objects.create_user(
            username=f'fichas-task-{id(self)}',
        )
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.superuser = get_user_model().objects.create_superuser(
            username=f'superuser-task-{id(self)}',
            email=f'superuser-{id(self)}@example.test',
            password='senha-exclusiva-de-teste',
        )
        self.encontro = make_encontro(data_referencia=date(2030, 6, 3))
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=capacidade,
            idade_minima=18,
            idade_maxima=30,
            inscricoes_abrem_em=self.momento - timedelta(days=30),
            inscricoes_encerram_em=self.momento - timedelta(days=1),
        )
        calendario = CalendarioEncontro.objects.create(
            encontro=self.encontro,
            versao=1,
            vigente=True,
            oficializado_em=self.momento,
        )
        DiaEncontro.objects.create(
            calendario=calendario,
            ordem=1,
            data=date(2030, 6, 3),
        )

    def criar_candidato(
        self,
        nome,
        *,
        email=True,
        whatsapp=False,
        status=ConviteEncontro.Status.CONVIDADO,
    ):
        pessoa = Pessoa.objects.create(
            nome=nome,
            email=(f'{nome.lower().replace(" ", ".")}@example.test'
                   if email else None),
            data_nascimento=date(2005, 1, 1),
        )
        if whatsapp:
            TelefonePessoa.objects.create(
                pessoa=pessoa,
                numero='61999990000',
                whatsapp=True,
            )
        InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.PUBLICA,
        )
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=status,
        )
        return pessoa, convite

    def iniciar_campanha(self):
        return campanhas_convites.iniciar_campanha(
            usuario=self.usuario,
            encontro=self.encontro,
            prazo_confirmacao=self.prazo,
            momento=self.momento,
        )

    def resultado(self, *, sucesso, provider, categoria=None, codigo=''):
        return ResultadoEntregaConvite(
            sucesso=sucesso,
            provider=provider,
            processado_em=self.momento,
            categoria_falha=categoria,
            codigo_erro=codigo,
        )


class OutboxConviteTests(ConviteTaskFixtureMixin, TestCase):
    def setUp(self):
        self.preparar_dominio()
        self.pessoa, self.convite = self.criar_candidato(
            'Pessoa Entrega',
            whatsapp=True,
        )

    def test_oportunidade_outbox_entregas_e_segredo_sao_atomicos(self):
        with patch('core.tasks.processar_outbox_convite.delay') as publicar:
            with self.captureOnCommitCallbacks(execute=False) as callbacks:
                resultado = self.iniciar_campanha()
            publicar.assert_not_called()
            self.assertEqual(len(callbacks), 1)
            callbacks[0]()

        emissao = resultado.emissoes[0]
        outbox = OutboxEntregaConvite.objects.get(
            oportunidade=emissao.oportunidade,
        )
        self.assertNotEqual(outbox.segredo_criptografado, emissao.token)
        self.assertNotIn(emissao.token, repr(outbox.__dict__))
        self.assertEqual(
            descriptografar_token_convite(outbox.segredo_criptografado),
            emissao.token,
        )
        self.assertEqual(
            set(emissao.oportunidade.entregas.values_list('canal', flat=True)),
            {'email', 'whatsapp'},
        )
        publicar.assert_called_once_with(outbox.pk)

    def test_erro_criptografico_nao_expoe_ciphertext_nem_chave(self):
        from django.conf import settings

        self.iniciar_campanha()
        outbox = OutboxEntregaConvite.objects.get()
        ciphertext = outbox.segredo_criptografado

        with self.assertRaises(ValidationError) as contexto:
            descriptografar_token_convite(f'{ciphertext}corrompido')

        mensagem = str(contexto.exception)
        self.assertNotIn(ciphertext, mensagem)
        self.assertNotIn(settings.SIA_INVITATION_OUTBOX_KEY, mensagem)

    def test_falha_na_criacao_da_outbox_reverte_toda_a_abertura(self):
        with patch(
            'core.services.campanhas_convites.criar_outbox_entrega_convite',
            side_effect=RuntimeError('falha controlada'),
        ), patch('core.tasks.processar_outbox_convite.delay') as publicar:
            with self.assertRaises(RuntimeError):
                self.iniciar_campanha()

        self.assertFalse(CampanhaConvitesEncontro.objects.exists())
        self.assertFalse(RodadaConvitesEncontro.objects.exists())
        self.assertFalse(OportunidadeConviteEncontro.objects.exists())
        self.assertFalse(OutboxEntregaConvite.objects.exists())
        publicar.assert_not_called()

    def test_falha_do_broker_pos_commit_preserva_e_reconciliador_republica_id(self):
        with patch(
            'core.services.entregas_convites._publicar_outbox_apos_commit',
            return_value=False,
        ) as publicar:
            with self.captureOnCommitCallbacks(execute=True):
                self.iniciar_campanha()

        outbox = OutboxEntregaConvite.objects.get()
        self.assertEqual(outbox.status, OutboxEntregaConvite.Status.PENDENTE)
        publicar.assert_called_once_with(outbox.pk)
        with patch(
            'core.services.entregas_convites._publicar_outbox_apos_commit',
            return_value=True,
        ) as republicar:
            self.assertEqual(
                reconciliar_outboxes_entrega_convite(),
                (outbox.pk,),
            )
        republicar.assert_called_once_with(outbox.pk)

    def test_worker_envia_canais_independentes_e_limpa_ciphertext(self):
        self.iniciar_campanha()
        outbox = OutboxEntregaConvite.objects.get()
        email = _AdapterFalso(ProviderEntregaConvite.SMTP, [
            self.resultado(sucesso=True, provider=ProviderEntregaConvite.SMTP),
        ])
        whatsapp = _AdapterFalso(ProviderEntregaConvite.WHATSAPP_MOCK, [
            self.resultado(
                sucesso=False,
                provider=ProviderEntregaConvite.WHATSAPP_MOCK,
                categoria=CategoriaFalhaEntrega.PERMANENTE,
                codigo='falha_mock',
            ),
        ])
        adapters = {'email': email, 'whatsapp': whatsapp}

        processar_outbox_entrega_convite(
            outbox_id=outbox.pk,
            momento=self.momento + timedelta(minutes=1),
            resolver_adapter=adapters.__getitem__,
        )

        outbox.refresh_from_db()
        estados = dict(
            EntregaConviteEncontro.objects.values_list('canal', 'status')
        )
        self.assertEqual(estados['email'], EntregaConviteEncontro.Status.ENTREGUE)
        self.assertEqual(estados['whatsapp'], EntregaConviteEncontro.Status.FALHOU)
        self.assertEqual(len(email.payloads), 1)
        self.assertEqual(len(whatsapp.payloads), 1)
        self.assertEqual(outbox.status, OutboxEntregaConvite.Status.CONCLUIDA)
        self.assertIsNone(outbox.segredo_criptografado)
        self.assertIsNotNone(outbox.segredo_destruido_em)

    def test_retry_e_limitado_e_ciphertext_permanece_ate_terminal(self):
        self.iniciar_campanha()
        outbox = OutboxEntregaConvite.objects.get()
        sucesso = self.resultado(
            sucesso=True,
            provider=ProviderEntregaConvite.WHATSAPP_MOCK,
        )
        temporarias = [
            self.resultado(
                sucesso=False,
                provider=ProviderEntregaConvite.SMTP,
                categoria=CategoriaFalhaEntrega.TEMPORARIA,
                codigo='smtp_temporario',
            )
            for _ in range(3)
        ]
        email = _AdapterFalso(ProviderEntregaConvite.SMTP, temporarias)
        whatsapp = _AdapterFalso(ProviderEntregaConvite.WHATSAPP_MOCK, [sucesso])
        adapters = {'email': email, 'whatsapp': whatsapp}

        for deslocamento in (1, 2, 7):
            processar_outbox_entrega_convite(
                outbox_id=outbox.pk,
                momento=self.momento + timedelta(minutes=deslocamento),
                resolver_adapter=adapters.__getitem__,
            )
            outbox.refresh_from_db()
            if deslocamento < 7:
                self.assertIsNotNone(outbox.segredo_criptografado)

        email_entrega = EntregaConviteEncontro.objects.get(canal='email')
        whatsapp_entrega = EntregaConviteEncontro.objects.get(canal='whatsapp')
        self.assertEqual(email_entrega.tentativas, 3)
        self.assertEqual(email_entrega.status, EntregaConviteEncontro.Status.FALHOU)
        self.assertEqual(whatsapp_entrega.tentativas, 1)
        self.assertEqual(outbox.status, OutboxEntregaConvite.Status.CONCLUIDA)
        self.assertIsNone(outbox.segredo_criptografado)

    def test_task_repetida_em_outbox_terminal_nao_reenvia_nem_duplica(self):
        self.iniciar_campanha()
        outbox = OutboxEntregaConvite.objects.get()
        adapter = _AdapterFalso(ProviderEntregaConvite.SMTP, [
            self.resultado(sucesso=True, provider=ProviderEntregaConvite.SMTP),
        ])
        resolver = Mock(return_value=adapter)
        EntregaConviteEncontro.objects.filter(canal='whatsapp').delete()

        processar_outbox_entrega_convite(
            outbox_id=outbox.pk,
            momento=self.momento + timedelta(minutes=1),
            resolver_adapter=resolver,
        )
        processar_outbox_entrega_convite(
            outbox_id=outbox.pk,
            momento=self.momento + timedelta(minutes=2),
            resolver_adapter=resolver,
        )

        self.assertEqual(len(adapter.payloads), 1)
        self.assertEqual(EntregaConviteEncontro.objects.count(), 1)
        self.assertEqual(OportunidadeConviteEncontro.objects.count(), 1)

    @override_settings(SIA_INVITATION_OUTBOX_KEY='')
    def test_configuracao_sem_chave_falha_sem_expor_token(self):
        with self.assertRaises(ConfiguracaoOutboxInvalida) as contexto:
            self.iniciar_campanha()

        self.assertNotIn('token', str(contexto.exception).lower())
        self.assertFalse(OportunidadeConviteEncontro.objects.exists())
        self.assertFalse(OutboxEntregaConvite.objects.exists())

    def test_oportunidade_historica_nao_recebe_outbox_retroativa(self):
        self.iniciar_campanha()
        OutboxEntregaConvite.objects.all().delete()
        EntregaConviteEncontro.objects.all().delete()

        self.assertEqual(reconciliar_outboxes_entrega_convite(), ())
        self.assertTrue(OportunidadeConviteEncontro.objects.exists())
        self.assertFalse(OutboxEntregaConvite.objects.exists())


class AutomacaoCampanhaTests(ConviteTaskFixtureMixin, TestCase):
    def setUp(self):
        self.preparar_dominio()
        self.criar_candidato('Pessoa Prazo')

    def test_prazo_automatico_e_idempotente_sem_decisao_humana(self):
        campanha = self.iniciar_campanha().campanha
        momento = self.prazo + timedelta(seconds=1)

        with patch('core.tasks.timezone.now', return_value=momento):
            processar_prazo_campanha.run(campanha.pk)
            processar_prazo_campanha.run(campanha.pk)

        campanha.refresh_from_db()
        eventos = EventoAuditoriaEncontro.objects.filter(
            fato='campanha_convites.prazo_processado',
        )
        self.assertEqual(
            campanha.status,
            CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO,
        )
        self.assertEqual(eventos.count(), 1)
        evento = eventos.get()
        self.assertIsNone(evento.ator_id)
        self.assertEqual(evento.valor_novo['origem'], 'automatica')
        self.assertIsNone(campanha.encerrada_em)


class SinalReposicaoTests(ConviteTaskFixtureMixin, TestCase):
    def setUp(self):
        self.preparar_dominio(capacidade=1)
        self.ocupante, self.convite_ocupante = self.criar_candidato(
            'Pessoa Confirmada',
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        self.candidato, self.convite_candidato = self.criar_candidato(
            'Pessoa Espera',
        )
        self.campanha = self.iniciar_campanha().campanha

    def test_aumento_de_capacidade_cheia_cria_um_sinal_pos_commit(self):
        with patch('core.tasks.processar_sinal_reposicao.delay') as publicar:
            with self.captureOnCommitCallbacks(execute=True):
                alterar_configuracao_encontristas(
                    usuario=self.superuser,
                    configuracao=self.configuracao,
                    capacidade=2,
                )

        sinal = SinalReposicaoCampanha.objects.get()
        self.assertEqual(
            sinal.motivo,
            SinalReposicaoCampanha.Motivo.CAPACIDADE_AUMENTADA,
        )
        publicar.assert_called_once_with(sinal.pk)

        alterar_configuracao_encontristas(
            usuario=self.superuser,
            configuracao=self.configuracao,
            capacidade=2,
        )
        self.assertEqual(SinalReposicaoCampanha.objects.count(), 1)

    def test_estado_subocupado_ou_recusa_nao_confirmada_nao_inventa_sinal(self):
        sinal = registrar_transicao_lotado_para_disponivel(
            encontro=self.encontro,
            ocupacao_antes=0,
            capacidade_antes=1,
            ocupacao_depois=0,
            capacidade_depois=2,
            motivo=SinalReposicaoCampanha.Motivo.CAPACIDADE_AUMENTADA,
        )
        self.assertIsNone(sinal)
        self.assertFalse(SinalReposicaoCampanha.objects.exists())

    def test_confirmado_que_libera_lotacao_usa_sinal_duravel(self):
        sinal = registrar_transicao_lotado_para_disponivel(
            encontro=self.encontro,
            ocupacao_antes=1,
            capacidade_antes=1,
            ocupacao_depois=0,
            capacidade_depois=1,
            motivo=SinalReposicaoCampanha.Motivo.CONFIRMACAO_LIBERADA,
        )
        self.assertIsNotNone(sinal)
        self.assertEqual(SinalReposicaoCampanha.objects.count(), 1)

    def test_processamento_e_reexecucao_criam_uma_reposicao(self):
        alterar_configuracao_encontristas(
            usuario=self.superuser,
            configuracao=self.configuracao,
            capacidade=2,
        )
        sinal = SinalReposicaoCampanha.objects.get()

        processar_sinal_reposicao_campanha(
            sinal_id=sinal.pk,
            momento=self.momento + timedelta(minutes=1),
        )
        processar_sinal_reposicao_campanha(
            sinal_id=sinal.pk,
            momento=self.momento + timedelta(minutes=2),
        )

        sinal.refresh_from_db()
        reposicoes = RodadaConvitesEncontro.objects.filter(
            campanha=self.campanha,
            tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
        )
        self.assertEqual(reposicoes.count(), 1)
        self.assertEqual(reposicoes.get().oportunidades.count(), 1)
        self.assertEqual(
            sinal.status,
            SinalReposicaoCampanha.Status.PROCESSADO,
        )
        evento = EventoAuditoriaEncontro.objects.get(
            fato='campanha_convites.reposicao_aberta',
        )
        self.assertIsNone(evento.ator_id)
        self.assertEqual(evento.valor_novo['origem'], 'automatica')

    def test_falha_transacional_mantem_sinal_pendente_sem_rodada(self):
        sinal = registrar_transicao_lotado_para_disponivel(
            encontro=self.encontro,
            ocupacao_antes=1,
            capacidade_antes=1,
            ocupacao_depois=0,
            capacidade_depois=1,
            motivo=SinalReposicaoCampanha.Motivo.CONFIRMACAO_LIBERADA,
        )
        rodadas_antes = RodadaConvitesEncontro.objects.count()
        with patch(
            'core.services.campanhas_convites.'
            'abrir_reposicao_nova_vaga_automaticamente',
            side_effect=RuntimeError('falha controlada'),
        ):
            with self.assertRaises(RuntimeError):
                processar_sinal_reposicao_campanha(sinal_id=sinal.pk)

        sinal.refresh_from_db()
        self.assertEqual(sinal.status, SinalReposicaoCampanha.Status.PENDENTE)
        self.assertEqual(RodadaConvitesEncontro.objects.count(), rodadas_antes)


class AuditoriaAutomaticaTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro()
        self.ator = get_user_model().objects.create_user(
            username='ator-auditoria-automatica',
        )

    def _registrar(self, *, origem, ator):
        from core.services.auditoria_encontros import (
            registrar_evento_auditoria_encontro,
        )

        return registrar_evento_auditoria_encontro(
            encontro=self.encontro,
            ator=ator,
            origem=origem,
            fato='campanha_convites.automatizada',
            entidade='campanha_convites',
            objeto_id='1',
            valor_anterior={'status': 'ativa'},
            valor_novo={'status': 'aguardando_decisao'},
            campos_permitidos={'status', 'origem'},
        )

    def test_origem_automatica_exige_ator_nulo(self):
        evento = self._registrar(origem='automatica', ator=None)
        self.assertIsNone(evento.ator_id)
        self.assertEqual(evento.valor_novo['origem'], 'automatica')

        with self.assertRaises(ValidationError):
            self._registrar(origem='automatica', ator=self.ator)
        with self.assertRaises(ValidationError):
            self._registrar(origem='interna', ator=None)
        with self.assertRaises(ValidationError):
            self._registrar(origem='publica', ator=self.ator)
