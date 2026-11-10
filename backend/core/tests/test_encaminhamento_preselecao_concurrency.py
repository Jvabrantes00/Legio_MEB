from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timedelta
from hashlib import sha256
from threading import Barrier, Event
from unittest import skipUnless

from django.contrib.auth.models import Group, User
from django.db import (
    close_old_connections,
    connection,
    connections,
    transaction,
)
from django.test import TransactionTestCase
from django.utils import timezone

from core.models import (
    AtendimentoPreEncontro,
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
    PreEncontro,
    PreSelecaoEncontrista,
    RodadaConvitesEncontro,
)
from core.roles import SiaRole
from core.services import campanhas_convites
from core.services.configuracao_encontristas import (
    alterar_configuracao_encontristas,
)
from core.services.preselecoes_encontristas import (
    ErroPreSelecaoEncontrista,
    aprovar_encaminhamento_preselecao,
    preselecionar_encontrista,
)
from core.tests.factories import make_encontro


@skipUnless(connection.vendor == 'postgresql', 'exige PostgreSQL real')
class EncaminhamentoPreSelecaoConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.usuario = User.objects.create_user(username='fichas-concorrencia')
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.encontro = make_encontro(
            tipo=Encontro.Tipo.ESCALADA,
            status=Encontro.Status.EM_PREPARACAO,
            data_referencia=date(2030, 6, 1),
        )
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
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
            nome='Pessoa concorrente encaminhamento',
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

    def _criar_campanha(self, *, prazo=None):
        iniciada_em = timezone.now() - timedelta(days=2)
        return CampanhaConvitesEncontro.objects.create(
            encontro=self.encontro,
            status=CampanhaConvitesEncontro.Status.ATIVA,
            iniciada_por=self.usuario,
            iniciada_em=iniciada_em,
            prazo_confirmacao=prazo or timezone.now() + timedelta(days=10),
        )

    def _criar_oportunidade(self, campanha):
        convite = ConviteEncontro.objects.create(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )
        rodada = RodadaConvitesEncontro.objects.create(
            campanha=campanha,
            sequencia=1,
            tipo=RodadaConvitesEncontro.Tipo.INICIAL,
        )
        oportunidade = OportunidadeConviteEncontro.objects.create(
            rodada=rodada,
            convite=convite,
            token_digest=sha256(b'convite-c2').hexdigest(),
            expira_em=campanha.prazo_confirmacao,
        )
        return convite, oportunidade

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

    def _assert_somente_erros_de_dominio(self, resultados):
        inesperados = [
            valor
            for estado, valor in resultados
            if estado == 'erro'
            and not isinstance(valor, ErroPreSelecaoEncontrista)
        ]
        self.assertEqual(inesperados, [])

    def _ordem_forcada_por_lock_do_encontro(self, primeira, segunda):
        lock_adquirido = Event()
        segunda_iniciada = Event()

        def executar_primeira():
            close_old_connections()
            try:
                with transaction.atomic():
                    Encontro.objects.select_for_update(of=('self',)).get(
                        pk=self.encontro.pk,
                    )
                    lock_adquirido.set()
                    if not segunda_iniciada.wait(timeout=10):
                        raise TimeoutError('Segunda operação não foi iniciada.')
                    return 'sucesso', primeira()
            except Exception as error:
                return 'erro', error
            finally:
                connections['default'].close()
                close_old_connections()

        def executar_segunda():
            close_old_connections()
            try:
                if not lock_adquirido.wait(timeout=10):
                    raise TimeoutError('Lock inicial não foi adquirido.')
                segunda_iniciada.set()
                return 'sucesso', segunda()
            except Exception as error:
                return 'erro', error
            finally:
                connections['default'].close()
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            futuro_primeiro = executor.submit(executar_primeira)
            futuro_segundo = executor.submit(executar_segunda)
            return [
                futuro_primeiro.result(timeout=20),
                futuro_segundo.result(timeout=20),
            ]

    def _aprovar(self, barreira):
        close_old_connections()
        try:
            barreira.wait()
            resultado = aprovar_encaminhamento_preselecao(
                usuario=User.objects.get(pk=self.usuario.pk),
                encontro=Encontro.objects.get(pk=self.encontro.pk),
                preselecao=PreSelecaoEncontrista.objects.get(
                    pk=self.preselecao.pk,
                ),
            )
            return resultado.convite.pk
        finally:
            close_old_connections()

    def test_aprovacoes_simultaneas_sao_idempotentes(self):
        barreira = Barrier(2)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futuros = [
                executor.submit(self._aprovar, barreira)
                for _ in range(2)
            ]
            resultados = [futuro.result() for futuro in futuros]

        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(ConviteEncontro.objects.count(), 1)
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.encaminhamento_aprovado',
            ).count(),
            1,
        )
        self.preselecao.refresh_from_db()
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.ENCAMINHADA,
        )

    def test_aprovacao_concorre_com_recusa_administrativa(self):
        campanha = self._criar_campanha()
        convite, oportunidade = self._criar_oportunidade(campanha)

        resultados = self._corrida(
            lambda: aprovar_encaminhamento_preselecao(
                usuario=User.objects.get(pk=self.usuario.pk),
                encontro=Encontro.objects.get(pk=self.encontro.pk),
                preselecao=PreSelecaoEncontrista.objects.get(
                    pk=self.preselecao.pk,
                ),
            ).convite.pk,
            lambda: campanhas_convites.registrar_recusa(
                usuario=User.objects.get(pk=self.usuario.pk),
                oportunidade=OportunidadeConviteEncontro.objects.get(
                    pk=oportunidade.pk,
                ),
                momento=timezone.now(),
            ).status,
        )

        self._assert_somente_erros_de_dominio(resultados)
        convite.refresh_from_db()
        oportunidade.refresh_from_db()
        self.preselecao.refresh_from_db()
        self.assertEqual(convite.status, ConviteEncontro.Status.RECUSADO)
        self.assertEqual(
            oportunidade.status,
            OportunidadeConviteEncontro.Status.CONSUMIDA,
        )
        self.assertIn(
            self.preselecao.estado,
            {
                PreSelecaoEncontrista.Estado.PRESELECIONADA,
                PreSelecaoEncontrista.Estado.ENCAMINHADA,
            },
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.encaminhamento_aprovado',
            ).count(),
            int(
                self.preselecao.estado
                == PreSelecaoEncontrista.Estado.ENCAMINHADA
            ),
        )
        self.assertEqual(OportunidadeConviteEncontro.objects.count(), 1)
        self.assertFalse(EntregaConviteEncontro.objects.exists())
        self.assertFalse(OutboxEntregaConvite.objects.exists())

    def test_aprovacao_concorre_com_alteracao_de_configuracao(self):
        resultados = self._corrida(
            lambda: aprovar_encaminhamento_preselecao(
                usuario=User.objects.get(pk=self.usuario.pk),
                encontro=Encontro.objects.get(pk=self.encontro.pk),
                preselecao=PreSelecaoEncontrista.objects.get(
                    pk=self.preselecao.pk,
                ),
            ).convite.pk,
            lambda: alterar_configuracao_encontristas(
                usuario=User.objects.get(pk=self.usuario.pk),
                configuracao=ConfiguracaoEncontristasEncontro.objects.get(
                    pk=self.configuracao.pk,
                ),
                idade_minima=21,
            ).idade_minima,
        )

        self._assert_somente_erros_de_dominio(resultados)
        self.configuracao.refresh_from_db()
        self.preselecao.refresh_from_db()
        self.assertEqual(self.configuracao.idade_minima, 21)
        self.assertIn(
            self.preselecao.estado,
            {
                PreSelecaoEncontrista.Estado.PRESELECIONADA,
                PreSelecaoEncontrista.Estado.ENCAMINHADA,
            },
        )
        convites = ConviteEncontro.objects.filter(
            pessoa=self.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )
        self.assertEqual(
            convites.count(),
            int(
                self.preselecao.estado
                == PreSelecaoEncontrista.Estado.ENCAMINHADA
            ),
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.encaminhamento_aprovado',
            ).count(),
            convites.count(),
        )

    def _preparar_encerramento_concorrente(self):
        prazo = timezone.now() - timedelta(days=1)
        campanha = self._criar_campanha(prazo=prazo)

        def processar_e_encerrar():
            with transaction.atomic():
                campanha_atual = CampanhaConvitesEncontro.objects.get(
                    pk=campanha.pk,
                )
                campanhas_convites.processar_prazo(
                    usuario=User.objects.get(pk=self.usuario.pk),
                    campanha=campanha_atual,
                    momento=timezone.now(),
                )
                return campanhas_convites.encerrar_campanha(
                    usuario=User.objects.get(pk=self.usuario.pk),
                    campanha=campanha_atual,
                    momento=timezone.now(),
                ).status

        def aprovar():
            return aprovar_encaminhamento_preselecao(
                usuario=User.objects.get(pk=self.usuario.pk),
                encontro=Encontro.objects.get(pk=self.encontro.pk),
                preselecao=PreSelecaoEncontrista.objects.get(
                    pk=self.preselecao.pk,
                ),
            ).convite.pk

        return campanha, aprovar, processar_e_encerrar

    def test_aprovacao_vence_encerramento_e_permanece_historica(self):
        campanha, aprovar, processar_e_encerrar = (
            self._preparar_encerramento_concorrente()
        )

        resultados = self._ordem_forcada_por_lock_do_encontro(
            aprovar,
            processar_e_encerrar,
        )

        self._assert_somente_erros_de_dominio(resultados)
        self.assertEqual(
            [estado for estado, _ in resultados],
            ['sucesso', 'sucesso'],
        )
        campanha.refresh_from_db()
        self.preselecao.refresh_from_db()
        self.assertEqual(
            campanha.status,
            CampanhaConvitesEncontro.Status.ENCERRADA,
        )
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.ENCAMINHADA,
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.encaminhamento_aprovado',
            ).count(),
            1,
        )
        self.assertFalse(OportunidadeConviteEncontro.objects.exists())
        self.assertFalse(EntregaConviteEncontro.objects.exists())
        self.assertFalse(OutboxEntregaConvite.objects.exists())

    def test_encerramento_vence_e_bloqueia_nova_aprovacao(self):
        campanha, aprovar, processar_e_encerrar = (
            self._preparar_encerramento_concorrente()
        )

        resultados = self._ordem_forcada_por_lock_do_encontro(
            processar_e_encerrar,
            aprovar,
        )

        self._assert_somente_erros_de_dominio(resultados)
        self.assertEqual(resultados[0][0], 'sucesso')
        self.assertEqual(resultados[1][0], 'erro')
        campanha.refresh_from_db()
        self.preselecao.refresh_from_db()
        self.assertEqual(
            campanha.status,
            CampanhaConvitesEncontro.Status.ENCERRADA,
        )
        self.assertEqual(
            self.preselecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )
        self.assertFalse(ConviteEncontro.objects.exists())
        self.assertFalse(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.encaminhamento_aprovado',
            ).exists()
        )

    def test_origem_pessoa_bloqueia_apenas_atendimento_no_postgresql(self):
        pessoa = Pessoa.objects.create(
            nome='Pessoa por atendimento PostgreSQL',
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
        self.assertFalse(
            InscricaoEncontro.objects.filter(pessoa=pessoa).exists()
        )

    def test_origem_avulsa_regularizada_preserva_origem_no_postgresql(self):
        atendimento = AtendimentoPreEncontro.objects.create(
            pre_encontro=self.pre_encontro,
            registrado_por=self.usuario,
            nome_informado='Pessoa avulsa PostgreSQL',
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
            nome='Pessoa avulsa regularizada PostgreSQL',
            data_nascimento=date(2010, 3, 1),
        )
        atendimento.pessoa = pessoa
        atendimento.save(update_fields=['pessoa', 'atualizado_em'])

        resultado = aprovar_encaminhamento_preselecao(
            usuario=self.usuario,
            encontro=self.encontro,
            preselecao=preselecao,
        )

        self.assertEqual(
            resultado.preselecao.origem_tipo,
            PreSelecaoEncontrista.OrigemTipo.AVULSO,
        )
        self.assertEqual(resultado.preselecao.pessoa_resolvida, pessoa)
        self.assertFalse(
            InscricaoEncontro.objects.filter(pessoa=pessoa).exists()
        )
