from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from types import MappingProxyType
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from core.formacao_catalogo import TemaFormativo, TipoConteudoFormativo
from core.models import (
    Alpinista,
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Frequencia,
    Palestra,
    PalestranteSessao,
    PerfilAlpinista,
    Pessoa,
    RoleEquipeEncontro,
    SessaoFormativa,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.services.formacoes import (
    adicionar_palestrante_alpinista,
    adicionar_palestrante_externo,
    alterar_tema_sessao,
    cancelar_sessao_formativa,
    criar_sessao_formativa,
    obter_historico_formativo,
    registrar_realizacao_sessao,
    remover_palestrante,
)
from core.services.trabalhos import (
    registrar_resultado_trabalho,
    retirar_trabalho,
)
from core.tests.factories import make_encontro


REGISTRY_TESTE = MappingProxyType({
    'palestra-base': TemaFormativo(
        codigo='palestra-base',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Palestra de teste',
        tipos_encontro=frozenset({
            Encontro.Tipo.ESCALADA,
            Encontro.Tipo.ESPPA,
        }),
    ),
    'palestra-alternativa': TemaFormativo(
        codigo='palestra-alternativa',
        tipo_conteudo=TipoConteudoFormativo.PALESTRA,
        titulo='Palestra alternativa',
        tipos_encontro=frozenset({Encontro.Tipo.ESCALADA}),
    ),
    'bate-papo-avc': TemaFormativo(
        codigo='bate-papo-avc',
        tipo_conteudo=TipoConteudoFormativo.BATE_PAPO,
        titulo='Bate-papo de teste',
        tipos_encontro=frozenset({Encontro.Tipo.AVC}),
    ),
})


class EncounterFormationServiceTests(TestCase):
    def setUp(self):
        patcher = patch(
            'core.services.formacoes.TEMAS_FORMATIVOS',
            REGISTRY_TESTE,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.pessoa = Pessoa.objects.create(nome='Palestrante interno')
        self.perfil = PerfilAlpinista.objects.create(pessoa=self.pessoa)

    def _sessao(self, *, encontro=None, tema_codigo='palestra-base'):
        return criar_sessao_formativa(
            encontro=encontro or self.encontro,
            tema_codigo=tema_codigo,
        )

    def _trabalho_avc(self, *, pessoa, encontro, status=None):
        codigo = f'equipe-avc-{encontro.pk}'
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=Encontro.Tipo.AVC,
            codigo=codigo,
            nome='Equipe AVC',
            ordem=1,
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
            ordem=1,
        )
        equipe = EquipeEncontro.objects.create(
            encontro=encontro,
            template_origem=template,
            codigo=codigo,
            nome='Equipe AVC',
            ordem=1,
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo='integrante',
            nome='Integrante',
            ordem=1,
        )
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        status_trabalho = status or TrabalhoEncontro.Status.ALOCADO
        return TrabalhoEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            convite=convite,
            role_equipe=role,
            status=status_trabalho,
            resultado_registrado_em=(
                timezone.now()
                if status_trabalho in {
                    TrabalhoEncontro.Status.TRABALHOU,
                    TrabalhoEncontro.Status.FALTOU,
                }
                else None
            ),
        )

    def test_cria_sessao_valida_com_snapshot_do_registry(self):
        sessao = self._sessao()

        self.assertEqual(sessao.tema_codigo, 'palestra-base')
        self.assertEqual(sessao.tipo_conteudo, 'palestra')
        self.assertEqual(sessao.titulo_snapshot, 'Palestra de teste')
        self.assertEqual(sessao.status, SessaoFormativa.Status.PLANEJADA)

    def test_rejeita_tema_invalido_ou_incompativel(self):
        with self.assertRaisesMessage(ValidationError, 'Tema formativo inválido'):
            self._sessao(tema_codigo='tema-inexistente')

        avc = make_encontro(tipo=Encontro.Tipo.AVC)
        with self.assertRaisesMessage(ValidationError, 'tipo de conteúdo'):
            self._sessao(encontro=avc, tema_codigo='palestra-base')

        self.assertFalse(SessaoFormativa.objects.exists())

    def test_altera_tema_planejado_e_preserva_snapshot_realizado(self):
        sessao = self._sessao()
        alterada = alterar_tema_sessao(
            sessao,
            tema_codigo='palestra-alternativa',
        )
        self.assertEqual(alterada.titulo_snapshot, 'Palestra alternativa')

        palestrante = adicionar_palestrante_alpinista(alterada, self.perfil)
        registrar_realizacao_sessao(
            alterada,
            resultados={palestrante.pk: PalestranteSessao.Status.MINISTROU},
        )
        registry_alterado = MappingProxyType({
            **REGISTRY_TESTE,
            'palestra-alternativa': TemaFormativo(
                codigo='palestra-alternativa',
                tipo_conteudo=TipoConteudoFormativo.PALESTRA,
                titulo='Título futuro',
                tipos_encontro=frozenset({Encontro.Tipo.ESCALADA}),
            ),
        })
        with patch(
            'core.services.formacoes.TEMAS_FORMATIVOS',
            registry_alterado,
        ):
            with self.assertRaisesMessage(ValidationError, 'planejada'):
                alterar_tema_sessao(
                    alterada,
                    tema_codigo='palestra-alternativa',
                )

        alterada.refresh_from_db()
        self.assertEqual(alterada.titulo_snapshot, 'Palestra alternativa')

    def test_multiplos_palestrantes_internos_e_externos(self):
        sessao = self._sessao()
        outro_perfil = PerfilAlpinista.objects.create(
            pessoa=Pessoa.objects.create(nome='Segundo palestrante'),
        )

        interno = adicionar_palestrante_alpinista(sessao, self.perfil)
        repetido = adicionar_palestrante_alpinista(sessao, self.perfil)
        adicionar_palestrante_alpinista(sessao, outro_perfil)
        externo = adicionar_palestrante_externo(
            sessao,
            nome_externo='  Nome   Externo  ',
        )

        self.assertEqual(repetido.pk, interno.pk)
        self.assertEqual(externo.nome_externo, 'Nome Externo')
        self.assertEqual(sessao.palestrantes.count(), 3)

    def test_externo_e_permitido_em_escalada_e_esppa_sem_criar_entidades(self):
        contagens_antes = {
            'pessoa': Pessoa.objects.count(),
            'perfil': PerfilAlpinista.objects.count(),
            'user': User.objects.count(),
            'trabalho': TrabalhoEncontro.objects.count(),
            'frequencia': Frequencia.objects.count(),
        }
        for tipo in (Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA):
            with self.subTest(tipo=tipo):
                encontro = make_encontro(tipo=tipo)
                sessao = self._sessao(encontro=encontro)
                adicionar_palestrante_externo(
                    sessao,
                    nome_externo=f'Externo {tipo}',
                )

        self.assertEqual(Pessoa.objects.count(), contagens_antes['pessoa'])
        self.assertEqual(
            PerfilAlpinista.objects.count(),
            contagens_antes['perfil'],
        )
        self.assertEqual(User.objects.count(), contagens_antes['user'])
        self.assertEqual(
            TrabalhoEncontro.objects.count(),
            contagens_antes['trabalho'],
        )
        self.assertEqual(
            Frequencia.objects.count(),
            contagens_antes['frequencia'],
        )

    def test_avc_bloqueia_externo(self):
        avc = make_encontro(tipo=Encontro.Tipo.AVC)
        sessao = self._sessao(encontro=avc, tema_codigo='bate-papo-avc')

        with self.assertRaisesMessage(ValidationError, 'não permite'):
            adicionar_palestrante_externo(
                sessao,
                nome_externo='Externo não permitido',
            )

        self.assertFalse(sessao.palestrantes.exists())

    def test_avc_aceita_alpinista_trabalhando_no_mesmo_encontro(self):
        avc = make_encontro(tipo=Encontro.Tipo.AVC)
        trabalho = self._trabalho_avc(pessoa=self.pessoa, encontro=avc)
        sessao = self._sessao(encontro=avc, tema_codigo='bate-papo-avc')

        palestrante = adicionar_palestrante_alpinista(sessao, self.perfil)

        self.assertEqual(palestrante.perfil_alpinista, self.perfil)
        trabalho.refresh_from_db()
        self.assertEqual(trabalho.status, TrabalhoEncontro.Status.ALOCADO)

    def test_avc_bloqueia_alpinista_sem_trabalho_no_mesmo_encontro(self):
        avc = make_encontro(tipo=Encontro.Tipo.AVC)
        sessao = self._sessao(encontro=avc, tema_codigo='bate-papo-avc')

        with self.assertRaisesMessage(ValidationError, 'mesmo Encontro'):
            adicionar_palestrante_alpinista(sessao, self.perfil)

        outro_avc = make_encontro(tipo=Encontro.Tipo.AVC)
        self._trabalho_avc(pessoa=self.pessoa, encontro=outro_avc)
        with self.assertRaisesMessage(ValidationError, 'mesmo Encontro'):
            adicionar_palestrante_alpinista(sessao, self.perfil)

    def test_acampamento_bloqueia_sessao_formativa(self):
        acampamento = make_encontro(tipo=Encontro.Tipo.ACAMPAMENTO)

        with self.assertRaisesMessage(ValidationError, 'Acampamento'):
            self._sessao(
                encontro=acampamento,
                tema_codigo='palestra-base',
            )

    def test_realizacao_registra_resultados_e_e_idempotente(self):
        sessao = self._sessao()
        interno = adicionar_palestrante_alpinista(sessao, self.perfil)
        externo = adicionar_palestrante_externo(
            sessao,
            nome_externo='Externo previsto',
        )
        resultados = {
            interno.pk: PalestranteSessao.Status.MINISTROU,
            externo.pk: PalestranteSessao.Status.NAO_MINISTROU,
        }
        momento = timezone.now()

        realizada = registrar_realizacao_sessao(
            sessao,
            resultados=resultados,
            momento=momento,
        )
        repetida = registrar_realizacao_sessao(
            realizada,
            resultados=resultados,
        )

        interno.refresh_from_db()
        externo.refresh_from_db()
        self.assertEqual(repetida.pk, realizada.pk)
        self.assertEqual(realizada.status, SessaoFormativa.Status.REALIZADA)
        self.assertEqual(realizada.realizada_em, momento)
        self.assertEqual(interno.status, PalestranteSessao.Status.MINISTROU)
        self.assertEqual(interno.ministrou_em, momento)
        self.assertEqual(
            externo.status,
            PalestranteSessao.Status.NAO_MINISTROU,
        )
        self.assertIsNone(externo.ministrou_em)

    def test_realizacao_exige_resultado_completo_e_alguem_que_ministrou(self):
        sessao = self._sessao()
        interno = adicionar_palestrante_alpinista(sessao, self.perfil)
        externo = adicionar_palestrante_externo(
            sessao,
            nome_externo='Externo',
        )

        with self.assertRaisesMessage(ValidationError, 'todos os palestrantes'):
            registrar_realizacao_sessao(
                sessao,
                resultados={
                    interno.pk: PalestranteSessao.Status.MINISTROU,
                },
            )
        with self.assertRaisesMessage(ValidationError, 'Ao menos um'):
            registrar_realizacao_sessao(
                sessao,
                resultados={
                    interno.pk: PalestranteSessao.Status.NAO_MINISTROU,
                    externo.pk: PalestranteSessao.Status.NAO_MINISTROU,
                },
            )

        sessao.refresh_from_db()
        self.assertEqual(sessao.status, SessaoFormativa.Status.PLANEJADA)

    def test_historico_inclui_apenas_atuacao_interna_efetiva(self):
        sessao_realizada = self._sessao()
        interno = adicionar_palestrante_alpinista(
            sessao_realizada,
            self.perfil,
        )
        externo = adicionar_palestrante_externo(
            sessao_realizada,
            nome_externo='Externo histórico',
        )
        registrar_realizacao_sessao(
            sessao_realizada,
            resultados={
                interno.pk: PalestranteSessao.Status.MINISTROU,
                externo.pk: PalestranteSessao.Status.MINISTROU,
            },
        )

        sessao_nao_realizada = self._sessao()
        adicionar_palestrante_alpinista(sessao_nao_realizada, self.perfil)

        outro_perfil = PerfilAlpinista.objects.create(
            pessoa=Pessoa.objects.create(nome='Não ministrou'),
        )
        sessao_nao_ministrada = self._sessao()
        nao_ministrou = adicionar_palestrante_alpinista(
            sessao_nao_ministrada,
            outro_perfil,
        )
        externo_ministrou = adicionar_palestrante_externo(
            sessao_nao_ministrada,
            nome_externo='Quem ministrou',
        )
        registrar_realizacao_sessao(
            sessao_nao_ministrada,
            resultados={
                nao_ministrou.pk: PalestranteSessao.Status.NAO_MINISTROU,
                externo_ministrou.pk: PalestranteSessao.Status.MINISTROU,
            },
        )

        historico = list(obter_historico_formativo(self.perfil))
        historico_outro = list(obter_historico_formativo(outro_perfil))
        self.assertEqual([item.pk for item in historico], [interno.pk])
        self.assertEqual(
            historico[0].sessao_formativa.titulo_snapshot,
            'Palestra de teste',
        )
        self.assertEqual(historico[0].sessao_formativa.encontro, self.encontro)
        self.assertEqual(historico_outro, [])

    def test_palestra_legada_nao_entra_no_historico_canonico(self):
        alpinista = Alpinista.objects.create(
            nome='Legado',
            email='legado-formacao@example.test',
            telefone='61999990000',
            pessoa=self.pessoa,
        )
        Palestra.objects.create(
            alpinista=alpinista,
            encontro=self.encontro,
            titulo='Legado sem cutover',
        )

        self.assertEqual(list(obter_historico_formativo(self.perfil)), [])

    def test_cancelamento_preserva_registro_sem_gerar_historico(self):
        sessao = self._sessao()
        palestrante = adicionar_palestrante_alpinista(sessao, self.perfil)

        cancelada = cancelar_sessao_formativa(sessao)
        repetida = cancelar_sessao_formativa(cancelada)

        self.assertEqual(repetida.pk, cancelada.pk)
        self.assertEqual(cancelada.status, SessaoFormativa.Status.CANCELADA)
        self.assertTrue(
            PalestranteSessao.objects.filter(pk=palestrante.pk).exists()
        )
        self.assertEqual(list(obter_historico_formativo(self.perfil)), [])
        with self.assertRaisesMessage(ValidationError, 'cancelada'):
            registrar_realizacao_sessao(
                cancelada,
                resultados={
                    palestrante.pk: PalestranteSessao.Status.MINISTROU,
                },
            )

    def test_remove_somente_palestrante_previsto_de_sessao_planejada(self):
        sessao = self._sessao()
        palestrante = adicionar_palestrante_alpinista(sessao, self.perfil)

        remover_palestrante(palestrante)

        self.assertFalse(
            PalestranteSessao.objects.filter(pk=palestrante.pk).exists()
        )

    def test_avc_impede_perder_trabalho_enquanto_for_palestrante(self):
        avc = make_encontro(tipo=Encontro.Tipo.AVC)
        trabalho = self._trabalho_avc(pessoa=self.pessoa, encontro=avc)
        sessao = self._sessao(encontro=avc, tema_codigo='bate-papo-avc')
        adicionar_palestrante_alpinista(sessao, self.perfil)

        with self.assertRaisesMessage(ValidationError, 'estado operacional'):
            retirar_trabalho(trabalho)
        with self.assertRaisesMessage(ValidationError, 'estado operacional'):
            registrar_resultado_trabalho(
                trabalho,
                status=TrabalhoEncontro.Status.FALTOU,
            )

        trabalho.refresh_from_db()
        self.assertEqual(trabalho.status, TrabalhoEncontro.Status.ALOCADO)

    def test_avc_permite_resultado_trabalhou_e_revalida_na_realizacao(self):
        avc = make_encontro(tipo=Encontro.Tipo.AVC)
        trabalho = self._trabalho_avc(pessoa=self.pessoa, encontro=avc)
        sessao = self._sessao(encontro=avc, tema_codigo='bate-papo-avc')
        palestrante = adicionar_palestrante_alpinista(sessao, self.perfil)

        trabalho = registrar_resultado_trabalho(
            trabalho,
            status=TrabalhoEncontro.Status.TRABALHOU,
        )
        realizada = registrar_realizacao_sessao(
            sessao,
            resultados={palestrante.pk: PalestranteSessao.Status.MINISTROU},
        )

        self.assertEqual(trabalho.status, TrabalhoEncontro.Status.TRABALHOU)
        self.assertEqual(realizada.status, SessaoFormativa.Status.REALIZADA)

    def test_erro_intermediario_faz_rollback_integral(self):
        sessao = self._sessao()
        interno = adicionar_palestrante_alpinista(sessao, self.perfil)
        externo = adicionar_palestrante_externo(
            sessao,
            nome_externo='Falha intermediária',
        )
        save_original = PalestranteSessao.save
        chamadas = 0

        def salvar_com_falha(instancia, *args, **kwargs):
            nonlocal chamadas
            chamadas += 1
            if chamadas == 2:
                raise RuntimeError('falha intermediária simulada')
            return save_original(instancia, *args, **kwargs)

        with patch.object(
            PalestranteSessao,
            'save',
            autospec=True,
            side_effect=salvar_com_falha,
        ):
            with self.assertRaisesMessage(RuntimeError, 'falha intermediária'):
                registrar_realizacao_sessao(
                    sessao,
                    resultados={
                        interno.pk: PalestranteSessao.Status.MINISTROU,
                        externo.pk: PalestranteSessao.Status.NAO_MINISTROU,
                    },
                )

        sessao.refresh_from_db()
        interno.refresh_from_db()
        externo.refresh_from_db()
        self.assertEqual(sessao.status, SessaoFormativa.Status.PLANEJADA)
        self.assertEqual(interno.status, PalestranteSessao.Status.PREVISTO)
        self.assertEqual(externo.status, PalestranteSessao.Status.PREVISTO)
        self.assertFalse(Frequencia.objects.exists())


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL real')
class EncounterFormationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        patcher = patch(
            'core.services.formacoes.TEMAS_FORMATIVOS',
            REGISTRY_TESTE,
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        pessoa = Pessoa.objects.create(nome='Palestrante concorrente')
        self.perfil = PerfilAlpinista.objects.create(pessoa=pessoa)
        self.sessao = criar_sessao_formativa(
            encontro=self.encontro,
            tema_codigo='palestra-base',
        )

    def _adicionar_concorrente(self):
        close_old_connections()
        try:
            sessao = SessaoFormativa.objects.get(pk=self.sessao.pk)
            perfil = PerfilAlpinista.objects.get(pk=self.perfil.pk)
            return adicionar_palestrante_alpinista(sessao, perfil).pk
        finally:
            close_old_connections()

    def test_inclusao_concorrente_do_mesmo_alpinista_e_idempotente(self):
        barreira = Barrier(2)

        def adicionar():
            barreira.wait()
            return self._adicionar_concorrente()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(
                lambda _: adicionar(),
                range(2),
            ))

        self.assertEqual(len(set(resultados)), 1)
        self.assertEqual(PalestranteSessao.objects.count(), 1)

    def test_realizacoes_concorrentes_nao_sobrescrevem_resultado(self):
        segundo_perfil = PerfilAlpinista.objects.create(
            pessoa=Pessoa.objects.create(nome='Segundo concorrente'),
        )
        primeiro = adicionar_palestrante_alpinista(self.sessao, self.perfil)
        segundo = adicionar_palestrante_alpinista(self.sessao, segundo_perfil)
        mapas = (
            {
                primeiro.pk: PalestranteSessao.Status.MINISTROU,
                segundo.pk: PalestranteSessao.Status.NAO_MINISTROU,
            },
            {
                primeiro.pk: PalestranteSessao.Status.NAO_MINISTROU,
                segundo.pk: PalestranteSessao.Status.MINISTROU,
            },
        )
        barreira = Barrier(2)

        def realizar(resultados):
            close_old_connections()
            try:
                sessao = SessaoFormativa.objects.get(pk=self.sessao.pk)
                barreira.wait()
                try:
                    registrar_realizacao_sessao(
                        sessao,
                        resultados=resultados,
                    )
                except ValidationError:
                    return 'rejeitada'
                return 'realizada'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            retornos = list(executor.map(realizar, mapas))

        self.assertCountEqual(retornos, ['realizada', 'rejeitada'])
        self.sessao.refresh_from_db()
        self.assertEqual(self.sessao.status, SessaoFormativa.Status.REALIZADA)
        self.assertEqual(
            PalestranteSessao.objects.filter(
                sessao_formativa=self.sessao,
                status=PalestranteSessao.Status.MINISTROU,
            ).count(),
            1,
        )
