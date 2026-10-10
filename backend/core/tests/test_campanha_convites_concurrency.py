from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from hashlib import sha256
from threading import Barrier, Lock
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import (
    IntegrityError,
    close_old_connections,
    connection,
    connections,
    transaction,
)
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from core.models import (
    CalendarioEncontro,
    CampanhaConvitesEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DiaEncontro,
    EntregaConviteEncontro,
    Encontro,
    EventoAuditoriaEncontro,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    OutboxEntregaConvite,
    Pessoa,
    RodadaConvitesEncontro,
    SinalReposicaoCampanha,
)
from core.notifications import (
    CategoriaFalhaEntrega,
    ProviderEntregaConvite,
    ResultadoEntregaConvite,
)
from core.roles import SiaRole
from core.services import campanhas_convites
from core.services import comandos_calendario
from core.services import oportunidades_convites
from core.services.configuracao_encontristas import (
    alterar_configuracao_encontristas,
)
from core.services.entregas_convites import (
    criar_outbox_entrega_convite,
    processar_outbox_entrega_convite,
)
from core.services.reposicao_campanha import (
    processar_sinal_reposicao_campanha,
)
from core.tests import test_oportunidade_convite_services as testes_i13
from core.tests.factories import make_encontro


CHAVE_FERNET_TESTE = 'MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA='


class _AdapterConcorrente:
    def __init__(self, *, categoria_falha=None):
        self.provider = ProviderEntregaConvite.SMTP
        self.categoria_falha = categoria_falha
        self._lock = Lock()
        self.chamadas = 0

    def entregar(self, payload):
        del payload
        with self._lock:
            self.chamadas += 1
        if self.categoria_falha is None:
            return ResultadoEntregaConvite(
                sucesso=True,
                provider=self.provider,
                processado_em=timezone.now(),
            )
        return ResultadoEntregaConvite(
            sucesso=False,
            provider=self.provider,
            processado_em=timezone.now(),
            categoria_falha=self.categoria_falha,
            codigo_erro='falha_temporaria_controlada',
        )


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL real')
@override_settings(
    SIA_INVITATION_OUTBOX_KEY=CHAVE_FERNET_TESTE,
    SIA_PUBLIC_INVITATION_BASE_URL='http://testserver/convites',
)
class UltimaVagaCheckpointTests(
    testes_i13.OportunidadeConviteConcurrencyTests,
):
    """Reutiliza as duas corridas PostgreSQL canônicas introduzidas na I.13."""

    def test_duas_confirmacoes_concorrentes_na_ultima_vaga(self):
        super().test_duas_confirmacoes_concorrentes_na_ultima_vaga()
        candidatos = [convite.pk for _, convite in self.candidatos]
        self.assertFalse(
            ConviteEncontro.objects.filter(
                pk__in=candidatos,
                status=ConviteEncontro.Status.RECUSADO,
            ).exists()
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='oportunidade_convite.confirmada_publicamente',
            ).count(),
            1,
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='oportunidade_convite.invalidada_lotacao',
            ).count(),
            1,
        )

    def test_confirmacao_publica_e_interna_concorrem_pela_ultima_vaga(self):
        super().test_confirmacao_publica_e_interna_concorrem_pela_ultima_vaga()
        candidatos = [convite.pk for _, convite in self.candidatos]
        self.assertFalse(
            ConviteEncontro.objects.filter(
                pk__in=candidatos,
                status=ConviteEncontro.Status.RECUSADO,
            ).exists()
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='oportunidade_convite.invalidada_lotacao',
            ).count(),
            1,
        )
        self.assertLessEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='oportunidade_convite.confirmada_publicamente',
            ).count(),
            1,
        )


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL real')
@override_settings(
    SIA_INVITATION_OUTBOX_KEY=CHAVE_FERNET_TESTE,
    SIA_PUBLIC_INVITATION_BASE_URL='http://testserver/convites',
)
class CampanhaConvitesConcurrencyCheckpointTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.momento = timezone.now().replace(microsecond=0)
        self.prazo = self.momento + timedelta(days=10)
        self.usuario = get_user_model().objects.create_user(
            username='fichas-checkpoint-concorrencia',
        )
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.superuser = get_user_model().objects.create_superuser(
            username='superuser-checkpoint-concorrencia',
            email='superuser-checkpoint@example.test',
            password='senha-exclusiva-de-teste',
        )
        self.encontro = make_encontro(data_referencia=date(2030, 6, 3))
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=2,
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
        self.candidatos = (
            self._criar_candidato('Candidata Um'),
            self._criar_candidato('Candidata Dois'),
        )
        self._publicar_outbox = self.enterContext(patch(
            'core.services.entregas_convites._publicar_outbox_apos_commit',
            return_value=True,
        ))
        self._publicar_sinal = self.enterContext(patch(
            'core.services.reposicao_campanha._publicar_sinal_apos_commit',
            return_value=True,
        ))
        resultado = campanhas_convites.iniciar_campanha(
            usuario=self.usuario,
            encontro=self.encontro,
            prazo_confirmacao=self.prazo,
            momento=self.momento,
        )
        self.campanha = resultado.campanha
        self.rodada = resultado.abertura.rodada
        self.tokens = {
            emissao.oportunidade.convite_id: emissao.token
            for emissao in resultado.emissoes
        }

    def _criar_candidato(self, nome, *, nascimento=date(2012, 6, 3)):
        pessoa = Pessoa.objects.create(
            nome=nome,
            email=f'{nome.lower().replace(" ", ".")}@example.test',
            data_nascimento=nascimento,
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
        )
        return pessoa, convite

    def _corrida(self, *operacoes):
        barreira = Barrier(len(operacoes))

        def executar(operacao):
            close_old_connections()
            try:
                barreira.wait(timeout=10)
                return 'sucesso', operacao()
            except Exception as error:
                return 'erro', error
            finally:
                connections['default'].close()
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(operacoes)) as executor:
            futuros = [executor.submit(executar, item) for item in operacoes]
            return [futuro.result(timeout=20) for futuro in futuros]

    def _assert_erros_somente(self, resultados, tipos=()):
        inesperados = [
            valor
            for estado, valor in resultados
            if estado == 'erro' and not isinstance(valor, tipos)
        ]
        self.assertEqual(inesperados, [])

    def _responder(self, convite_id, decisao):
        pessoa_id = ConviteEncontro.objects.values_list(
            'pessoa_id', flat=True
        ).get(pk=convite_id)
        nascimento = Pessoa.objects.values_list(
            'data_nascimento', flat=True
        ).get(pk=pessoa_id)
        return oportunidades_convites.responder_convite_publico(
            token=self.tokens[convite_id],
            data_nascimento=nascimento,
            decisao=decisao,
            momento=self.momento + timedelta(hours=1),
        ).estado.value

    def test_resposta_duplicada_confirmar_confirmar(self):
        convite_id = self.candidatos[0][1].pk
        resultados = self._corrida(
            lambda: self._responder(convite_id, 'confirmar'),
            lambda: self._responder(convite_id, 'confirmar'),
        )

        self._assert_erros_somente(resultados)
        oportunidade = OportunidadeConviteEncontro.objects.get(
            convite_id=convite_id,
        )
        convite = ConviteEncontro.objects.get(pk=convite_id)
        self.assertEqual(convite.status, ConviteEncontro.Status.CONFIRMADO)
        self.assertEqual(
            oportunidade.status,
            OportunidadeConviteEncontro.Status.CONSUMIDA,
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='oportunidade_convite.confirmada_publicamente',
                objeto_id=str(oportunidade.pk),
            ).count(),
            1,
        )

    def test_resposta_concorrente_confirmar_recusar(self):
        convite_id = self.candidatos[0][1].pk
        resultados = self._corrida(
            lambda: self._responder(convite_id, 'confirmar'),
            lambda: self._responder(convite_id, 'recusar'),
        )

        self._assert_erros_somente(resultados)
        oportunidade = OportunidadeConviteEncontro.objects.get(
            convite_id=convite_id,
        )
        convite = ConviteEncontro.objects.get(pk=convite_id)
        self.assertIn(
            convite.status,
            {ConviteEncontro.Status.CONFIRMADO, ConviteEncontro.Status.RECUSADO},
        )
        self.assertEqual(
            oportunidade.status,
            OportunidadeConviteEncontro.Status.CONSUMIDA,
        )
        fatos = EventoAuditoriaEncontro.objects.filter(
            objeto_id=str(oportunidade.pk),
            fato__in={
                'oportunidade_convite.confirmada_publicamente',
                'oportunidade_convite.recusada_publicamente',
            },
        )
        self.assertEqual(fatos.count(), 1)
        fato_esperado = (
            'oportunidade_convite.confirmada_publicamente'
            if convite.status == ConviteEncontro.Status.CONFIRMADO
            else 'oportunidade_convite.recusada_publicamente'
        )
        self.assertEqual(fatos.get().fato, fato_esperado)

    def test_constraint_impede_oportunidade_duplicada_na_mesma_rodada(self):
        _, convite = self._criar_candidato('Candidata Constraint')

        def criar(indice):
            token = f'{"A" * 42}{indice}'
            try:
                with transaction.atomic():
                    oportunidade = OportunidadeConviteEncontro.objects.create(
                        rodada_id=self.rodada.pk,
                        convite_id=convite.pk,
                        token_digest=sha256(token.encode()).hexdigest(),
                        expira_em=self.prazo,
                    )
                    criar_outbox_entrega_convite(
                        oportunidade=oportunidade,
                        token=token,
                        canais=('email',),
                    )
                    return oportunidade.pk
            except IntegrityError:
                return 'integridade'

        resultados = self._corrida(
            lambda: criar(1),
            lambda: criar(2),
        )

        self._assert_erros_somente(resultados)
        valores = [valor for _, valor in resultados]
        self.assertEqual(valores.count('integridade'), 1)
        oportunidades = OportunidadeConviteEncontro.objects.filter(
            rodada=self.rodada,
            convite=convite,
        )
        self.assertEqual(oportunidades.count(), 1)
        self.assertEqual(
            OutboxEntregaConvite.objects.filter(
                oportunidade__in=oportunidades,
            ).count(),
            1,
        )
        self.assertEqual(
            EntregaConviteEncontro.objects.filter(
                oportunidade__in=oportunidades,
            ).count(),
            1,
        )

    def _preparar_reposicao(self):
        ConviteEncontro.objects.filter(
            pk__in=[convite.pk for _, convite in self.candidatos],
        ).update(status=ConviteEncontro.Status.CONFIRMADO)
        pessoa, convite = self._criar_candidato('Candidata Reposição')
        alterar_configuracao_encontristas(
            usuario=self.superuser,
            configuracao=self.configuracao,
            capacidade=3,
        )
        return pessoa, convite, SinalReposicaoCampanha.objects.get()

    def test_processamento_concorrente_do_sinal_cria_uma_rodada_reposicao(self):
        _, convite, sinal = self._preparar_reposicao()

        resultados = self._corrida(
            lambda: processar_sinal_reposicao_campanha(sinal_id=sinal.pk),
            lambda: processar_sinal_reposicao_campanha(sinal_id=sinal.pk),
        )

        self._assert_erros_somente(resultados)
        sinal.refresh_from_db()
        reposicoes = RodadaConvitesEncontro.objects.filter(
            campanha=self.campanha,
            tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
        )
        self.assertEqual(reposicoes.count(), 1)
        self.assertEqual(reposicoes.get().sequencia, 2)
        oportunidades = OportunidadeConviteEncontro.objects.filter(
            rodada=reposicoes.get(),
            convite=convite,
        )
        self.assertEqual(oportunidades.count(), 1)
        self.assertEqual(
            OutboxEntregaConvite.objects.filter(
                oportunidade__in=oportunidades,
            ).count(),
            1,
        )
        self.assertEqual(sinal.status, SinalReposicaoCampanha.Status.PROCESSADO)

    def test_processamento_concorrente_da_mesma_outbox_envia_uma_vez(self):
        outbox = OutboxEntregaConvite.objects.order_by('pk').first()
        adapter = _AdapterConcorrente()

        resultados = self._corrida(
            lambda: processar_outbox_entrega_convite(
                outbox_id=outbox.pk,
                resolver_adapter=lambda canal: adapter,
            ),
            lambda: processar_outbox_entrega_convite(
                outbox_id=outbox.pk,
                resolver_adapter=lambda canal: adapter,
            ),
        )

        self._assert_erros_somente(resultados)
        outbox.refresh_from_db()
        entrega = EntregaConviteEncontro.objects.get(
            oportunidade=outbox.oportunidade,
        )
        self.assertEqual(adapter.chamadas, 1)
        self.assertEqual(entrega.tentativas, 1)
        self.assertEqual(entrega.status, EntregaConviteEncontro.Status.ENTREGUE)
        self.assertEqual(outbox.status, OutboxEntregaConvite.Status.CONCLUIDA)
        self.assertIsNone(outbox.segredo_criptografado)
        self.assertEqual(
            OutboxEntregaConvite.objects.filter(
                oportunidade=outbox.oportunidade,
            ).count(),
            1,
        )

    def test_retry_concorrente_respeita_tres_tentativas(self):
        outbox = OutboxEntregaConvite.objects.order_by('pk').first()
        adapter = _AdapterConcorrente(
            categoria_falha=CategoriaFalhaEntrega.TEMPORARIA,
        )
        resolver = lambda canal: adapter
        primeiro = self.momento + timedelta(minutes=1)
        processar_outbox_entrega_convite(
            outbox_id=outbox.pk,
            momento=primeiro,
            resolver_adapter=resolver,
        )

        for instante in (
            primeiro + timedelta(minutes=1),
            primeiro + timedelta(minutes=6),
            primeiro + timedelta(minutes=7),
        ):
            resultados = self._corrida(
                lambda instante=instante: processar_outbox_entrega_convite(
                    outbox_id=outbox.pk,
                    momento=instante,
                    resolver_adapter=resolver,
                ),
                lambda instante=instante: processar_outbox_entrega_convite(
                    outbox_id=outbox.pk,
                    momento=instante,
                    resolver_adapter=resolver,
                ),
            )
            self._assert_erros_somente(resultados)

        outbox.refresh_from_db()
        entrega = EntregaConviteEncontro.objects.get(
            oportunidade=outbox.oportunidade,
        )
        self.assertEqual(adapter.chamadas, 3)
        self.assertEqual(entrega.tentativas, 3)
        self.assertEqual(entrega.status, EntregaConviteEncontro.Status.FALHOU)
        self.assertIsNone(entrega.proxima_tentativa_em)
        self.assertEqual(outbox.status, OutboxEntregaConvite.Status.CONCLUIDA)
        self.assertIsNone(outbox.segredo_criptografado)

    def test_aumento_de_capacidade_concorre_com_sinal_sem_duplicar_reposicao(self):
        ConviteEncontro.objects.filter(
            pk__in=[convite.pk for _, convite in self.candidatos],
        ).update(status=ConviteEncontro.Status.CONFIRMADO)
        _, terceiro = self._criar_candidato('Candidata Terceira Vaga')
        _, quarto = self._criar_candidato('Candidata Quarta Vaga')
        alterar_configuracao_encontristas(
            usuario=self.superuser,
            configuracao=self.configuracao,
            capacidade=3,
        )
        sinal = SinalReposicaoCampanha.objects.get()
        ConviteEncontro.objects.filter(pk=terceiro.pk).update(
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        def aumentar():
            return alterar_configuracao_encontristas(
                usuario=get_user_model().objects.get(pk=self.superuser.pk),
                configuracao=ConfiguracaoEncontristasEncontro.objects.get(
                    pk=self.configuracao.pk,
                ),
                capacidade=4,
            ).capacidade

        resultados = self._corrida(
            aumentar,
            lambda: processar_sinal_reposicao_campanha(sinal_id=sinal.pk),
        )

        self._assert_erros_somente(resultados, (ValidationError,))
        self.configuracao.refresh_from_db()
        self.assertEqual(self.configuracao.capacidade, 4)
        self.assertEqual(SinalReposicaoCampanha.objects.count(), 1)
        sinal.refresh_from_db()
        if sinal.status == SinalReposicaoCampanha.Status.PENDENTE:
            processar_sinal_reposicao_campanha(sinal_id=sinal.pk)
            sinal.refresh_from_db()

        reposicoes = RodadaConvitesEncontro.objects.filter(
            campanha=self.campanha,
            tipo=RodadaConvitesEncontro.Tipo.REPOSICAO,
        )
        self.assertEqual(reposicoes.count(), 1)
        self.assertEqual(
            OportunidadeConviteEncontro.objects.filter(
                rodada=reposicoes.get(),
                convite=quarto,
            ).count(),
            1,
        )
        self.assertEqual(sinal.status, SinalReposicaoCampanha.Status.PROCESSADO)

    def test_reducao_de_capacidade_concorre_com_confirmacao_sem_overbooking(self):
        primeiro = self.candidatos[0][1]
        segundo = self.candidatos[1][1]
        ConviteEncontro.objects.filter(pk=primeiro.pk).update(
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        def reduzir():
            return alterar_configuracao_encontristas(
                usuario=get_user_model().objects.get(pk=self.superuser.pk),
                configuracao=ConfiguracaoEncontristasEncontro.objects.get(
                    pk=self.configuracao.pk,
                ),
                capacidade=1,
            ).capacidade

        resultados = self._corrida(
            reduzir,
            lambda: self._responder(segundo.pk, 'confirmar'),
        )

        self._assert_erros_somente(resultados, (ValidationError,))
        self.configuracao.refresh_from_db()
        confirmados = ConviteEncontro.objects.filter(
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        ).count()
        self.assertLessEqual(confirmados, self.configuracao.capacidade)
        segundo.refresh_from_db()
        oportunidade = OportunidadeConviteEncontro.objects.get(
            convite=segundo,
        )
        self.assertIn(
            (segundo.status, oportunidade.status),
            {
                (
                    ConviteEncontro.Status.CONFIRMADO,
                    OportunidadeConviteEncontro.Status.CONSUMIDA,
                ),
                (
                    ConviteEncontro.Status.CONVIDADO,
                    OportunidadeConviteEncontro.Status.INVALIDADA,
                ),
            },
        )
        self.assertFalse(SinalReposicaoCampanha.objects.exists())

    def test_confirmacao_concorre_com_reprogramacao_sem_estado_hibrido(self):
        _, convite = self.candidatos[0]

        def reprogramar():
            return comandos_calendario.reprogramar_agenda(
                Encontro.objects.get(pk=self.encontro.pk),
                dias=[{'ordem': 1, 'data': date(2030, 6, 2)}],
                ator=get_user_model().objects.get(pk=self.usuario.pk),
            ).pk

        resultados = self._corrida(
            lambda: self._responder(convite.pk, 'confirmar'),
            reprogramar,
        )

        self._assert_erros_somente(resultados)
        convite.refresh_from_db()
        oportunidade = OportunidadeConviteEncontro.objects.get(convite=convite)
        estado = (convite.status, oportunidade.status)
        self.assertIn(
            estado,
            {
                (
                    ConviteEncontro.Status.CONFIRMADO,
                    OportunidadeConviteEncontro.Status.CONSUMIDA,
                ),
                (
                    ConviteEncontro.Status.CONVIDADO,
                    OportunidadeConviteEncontro.Status.SUSPENSA,
                ),
            },
        )
        self.assertEqual(
            CalendarioEncontro.objects.filter(
                encontro=self.encontro,
                vigente=True,
                versao=2,
            ).count(),
            1,
        )
        suspensoes = EventoAuditoriaEncontro.objects.filter(
            fato='oportunidade_convite.suspensa_inelegibilidade',
            objeto_id=str(oportunidade.pk),
        ).count()
        self.assertEqual(
            suspensoes,
            1
            if oportunidade.status
            == OportunidadeConviteEncontro.Status.SUSPENSA
            else 0,
        )
