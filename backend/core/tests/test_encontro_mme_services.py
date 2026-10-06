from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Frequencia,
    ItemPropostaVioleiros,
    PerfilAlpinista,
    Pessoa,
    PropostaVioleiros,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoEncontroLegado,
)
from core.services.propostas_violeiros import (
    SituacaoItemProposta,
    criar_proposta_violeiros,
    editar_proposta_violeiros,
    encerrar_proposta_violeiros,
    obter_situacao_item_proposta,
    preencher_posicao_proposta,
    resumir_proposta_violeiros,
    retirar_item_proposta,
    substituir_ocupacao_proposta,
)
from core.services.trabalhos import alocar_trabalho, iniciar_trabalho_confirmado


class PropostaVioleirosServiceTests(TestCase):
    def setUp(self):
        self.encontro = Encontro.objects.create(
            encontro='Escalada Services MME',
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia=date(2027, 2, 10),
            data_exato='10 de fevereiro de 2027',
        )
        self._equipes = {}

    def criar_perfil(
        self,
        indice,
        *,
        violeiro=True,
        canta=False,
        disponivel_mme=True,
    ):
        pessoa = Pessoa.objects.create(nome=f'Candidato {indice}')
        return PerfilAlpinista.objects.create(
            pessoa=pessoa,
            violeiro=violeiro,
            canta=canta,
            disponivel_mme=disponivel_mme,
        )

    def adicionar(
        self,
        proposta,
        perfil,
        papel=ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
        posicao=1,
    ):
        return preencher_posicao_proposta(
            proposta,
            perfil_alpinista=perfil,
            papel_sugerido=papel,
            posicao=posicao,
        )

    def preencher_proposta(self, proposta, inicio=1):
        itens = [self.adicionar(
            proposta,
            self.criar_perfil(inicio),
            ItemPropostaVioleiros.PapelSugerido.COORDENADOR,
            1,
        )]
        for posicao in range(1, 5):
            itens.append(self.adicionar(
                proposta,
                self.criar_perfil(inicio + posicao),
                ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
                posicao,
            ))
        return itens

    def criar_role(self, codigo_equipe):
        if codigo_equipe in self._equipes:
            return self._equipes[codigo_equipe]
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=self.encontro.tipo,
            codigo=codigo_equipe,
            nome=codigo_equipe.title(),
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=template,
            codigo=codigo_equipe,
            nome=codigo_equipe.title(),
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo='integrante',
            nome='Integrante',
        )
        self._equipes[codigo_equipe] = role
        return role

    def alocar_oficialmente(self, perfil, codigo_equipe):
        convite = ConviteEncontro.objects.create(
            pessoa=perfil.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        return TrabalhoEncontro.objects.create(
            pessoa=perfil.pessoa,
            encontro=self.encontro,
            convite=convite,
            role_equipe=self.criar_role(codigo_equipe),
            status=TrabalhoEncontro.Status.ALOCADO,
        )

    def test_cria_e_edita_proposta_aberta(self):
        proposta = criar_proposta_violeiros(
            encontro=self.encontro,
            nome='Alternativa inicial',
        )

        editada = editar_proposta_violeiros(
            proposta,
            nome='Alternativa revisada',
        )

        self.assertEqual(editada.nome, 'Alternativa revisada')
        self.assertEqual(editada.status, PropostaVioleiros.Status.ABERTA)

    def test_adiciona_coordenador_e_quatro_integrantes_e_calcula_cinco_de_cinco(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)

        self.preencher_proposta(proposta)
        resumo = resumir_proposta_violeiros(proposta)

        self.assertEqual(resumo.total_disponivel, 5)
        self.assertEqual(resumo.vagas_disponiveis, 0)
        self.assertTrue(resumo.completa)
        self.assertFalse(resumo.precisa_completar)

    def test_calcula_quatro_de_cinco_e_proposta_incompleta(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        itens = self.preencher_proposta(proposta)
        retirar_item_proposta(itens[-1])

        resumo = resumir_proposta_violeiros(proposta)

        self.assertEqual(resumo.total_disponivel, 4)
        self.assertEqual(resumo.vagas_disponiveis, 1)
        self.assertFalse(resumo.completa)
        self.assertTrue(resumo.precisa_completar)

    def test_bloqueia_mesmo_alpinista_duas_vezes_vigente(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        perfil = self.criar_perfil(1)
        self.adicionar(proposta, perfil, posicao=1)

        with self.assertRaisesMessage(ValidationError, 'já está vigente'):
            self.adicionar(proposta, perfil, posicao=2)

    def test_permite_mesmo_alpinista_em_propostas_diferentes(self):
        perfil = self.criar_perfil(1)
        proposta_a = criar_proposta_violeiros(encontro=self.encontro)
        proposta_b = criar_proposta_violeiros(encontro=self.encontro)

        item_a = self.adicionar(proposta_a, perfil)
        item_b = self.adicionar(proposta_b, perfil)

        self.assertNotEqual(item_a.pk, item_b.pk)

    def test_substituicao_preserva_item_historico(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        anterior = self.adicionar(proposta, self.criar_perfil(1))
        momento = timezone.now()

        historico, novo = substituir_ocupacao_proposta(
            anterior,
            perfil_alpinista=self.criar_perfil(2),
            momento=momento,
        )

        self.assertEqual(historico.pk, anterior.pk)
        self.assertFalse(historico.vigente)
        self.assertEqual(historico.retirado_em, momento)
        self.assertTrue(novo.vigente)
        self.assertEqual(proposta.itens.count(), 2)
        self.assertEqual(
            obter_situacao_item_proposta(historico).situacao,
            SituacaoItemProposta.HISTORICO,
        )

    def test_retirada_preserva_item_historico(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        item = self.adicionar(proposta, self.criar_perfil(1))

        retirado = retirar_item_proposta(item)

        self.assertFalse(retirado.vigente)
        self.assertIsNotNone(retirado.retirado_em)
        self.assertTrue(ItemPropostaVioleiros.objects.filter(pk=item.pk).exists())

    def test_candidato_sem_trabalho_oficial_esta_disponivel(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        item = self.adicionar(proposta, self.criar_perfil(1, canta=False))

        resultado = obter_situacao_item_proposta(item)

        self.assertEqual(resultado.situacao, SituacaoItemProposta.DISPONIVEL)
        self.assertTrue(resultado.disponivel)
        self.assertIsNotNone(resultado.avaliacao_elegibilidade)

    def test_alocado_em_violeiros_e_identificado_como_aproveitado(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        perfil = self.criar_perfil(1)
        item = self.adicionar(proposta, perfil)
        trabalho = self.alocar_oficialmente(perfil, 'violeiros')

        resultado = obter_situacao_item_proposta(item)

        self.assertEqual(
            resultado.situacao,
            SituacaoItemProposta.APROVEITADO_VIOLEIROS,
        )
        self.assertEqual(resultado.trabalho.pk, trabalho.pk)
        self.assertFalse(resultado.disponivel)

    def test_alocado_em_outra_equipe_e_identificado_como_indisponivel(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        perfil = self.criar_perfil(1)
        item = self.adicionar(proposta, perfil)
        self.alocar_oficialmente(perfil, 'apoio')

        resultado = obter_situacao_item_proposta(item)

        self.assertEqual(
            resultado.situacao,
            SituacaoItemProposta.INDISPONIVEL_OUTRA_EQUIPE,
        )

    def test_alocacao_reflete_em_todas_as_propostas_sem_dual_write(self):
        perfil = self.criar_perfil(1)
        proposta_a = criar_proposta_violeiros(encontro=self.encontro)
        proposta_b = criar_proposta_violeiros(encontro=self.encontro)
        item_a = self.adicionar(proposta_a, perfil)
        item_b = self.adicionar(proposta_b, perfil)
        self.alocar_oficialmente(perfil, 'violeiros')

        situacoes = {
            obter_situacao_item_proposta(item).situacao
            for item in (item_a, item_b)
        }

        self.assertEqual(
            situacoes,
            {SituacaoItemProposta.APROVEITADO_VIOLEIROS},
        )
        item_a.refresh_from_db()
        item_b.refresh_from_db()
        self.assertTrue(item_a.vigente)
        self.assertTrue(item_b.vigente)

    def test_item_indisponivel_deixa_vaga_e_pode_ser_substituido(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        itens = self.preencher_proposta(proposta)
        self.alocar_oficialmente(itens[-1].perfil_alpinista, 'apoio')
        resumo_incompleto = resumir_proposta_violeiros(proposta)

        anterior, novo = substituir_ocupacao_proposta(
            itens[-1],
            perfil_alpinista=self.criar_perfil(10),
        )
        resumo_completo = resumir_proposta_violeiros(proposta)

        self.assertEqual(resumo_incompleto.total_disponivel, 4)
        self.assertFalse(anterior.vigente)
        self.assertTrue(novo.vigente)
        self.assertEqual(resumo_completo.total_disponivel, 5)

    def test_perfil_indisponivel_para_mme_nao_pode_ser_adicionado(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        perfil = self.criar_perfil(1, disponivel_mme=False)

        with self.assertRaisesMessage(ValidationError, 'não está disponível'):
            self.adicionar(proposta, perfil)

        self.assertFalse(proposta.itens.exists())

    def test_perfil_nao_violeiro_nao_pode_ser_adicionado(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        perfil = self.criar_perfil(1, violeiro=False)

        with self.assertRaisesMessage(ValidationError, 'não está disponível'):
            self.adicionar(proposta, perfil)

    def test_encerramento_e_idempotente_e_pode_ser_incompleto(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        self.adicionar(proposta, self.criar_perfil(1))
        momento = timezone.now()

        encerrada = encerrar_proposta_violeiros(proposta, momento=momento)
        repetida = encerrar_proposta_violeiros(encerrada)

        self.assertEqual(encerrada.status, PropostaVioleiros.Status.ENCERRADA)
        self.assertEqual(repetida.encerrada_em, momento)
        self.assertTrue(resumir_proposta_violeiros(repetida).precisa_completar)

    def test_proposta_encerrada_bloqueia_edicao_adicao_substituicao_e_retirada(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        item = self.adicionar(proposta, self.criar_perfil(1))
        encerrar_proposta_violeiros(proposta)

        operacoes = (
            lambda: editar_proposta_violeiros(proposta, nome='Bloqueada'),
            lambda: self.adicionar(proposta, self.criar_perfil(2), posicao=2),
            lambda: substituir_ocupacao_proposta(
                item,
                perfil_alpinista=self.criar_perfil(3),
            ),
            lambda: retirar_item_proposta(item),
        )

        for operacao in operacoes:
            with self.subTest(operacao=operacao):
                with self.assertRaisesMessage(ValidationError, 'encerrada'):
                    operacao()

    def test_escala_posterior_nao_reabre_proposta(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        perfil = self.criar_perfil(1)
        item = self.adicionar(proposta, perfil)
        encerrar_proposta_violeiros(proposta)

        self.alocar_oficialmente(perfil, 'violeiros')
        proposta.refresh_from_db()

        self.assertEqual(proposta.status, PropostaVioleiros.Status.ENCERRADA)
        self.assertEqual(
            obter_situacao_item_proposta(item).situacao,
            SituacaoItemProposta.APROVEITADO_VIOLEIROS,
        )

    def test_fluxos_nao_criam_convite_trabalho_frequencia_ou_historico_legado(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        item = self.adicionar(proposta, self.criar_perfil(1))
        retirar_item_proposta(item)
        encerrar_proposta_violeiros(proposta)

        self.assertFalse(ConviteEncontro.objects.exists())
        self.assertFalse(TrabalhoEncontro.objects.exists())
        self.assertFalse(Frequencia.objects.exists())
        self.assertFalse(VinculoEncontroLegado.objects.exists())

    def test_substituicao_faz_rollback_integral_em_falha_intermediaria(self):
        proposta = criar_proposta_violeiros(encontro=self.encontro)
        anterior = self.adicionar(proposta, self.criar_perfil(1))
        novo_perfil = self.criar_perfil(2)
        save_original = ItemPropostaVioleiros.save

        def falhar_ao_criar(instancia, *args, **kwargs):
            if instancia.pk is None:
                raise RuntimeError('falha intermediária simulada')
            return save_original(instancia, *args, **kwargs)

        with patch.object(
            ItemPropostaVioleiros,
            'save',
            new=falhar_ao_criar,
        ):
            with self.assertRaisesMessage(RuntimeError, 'falha intermediária'):
                substituir_ocupacao_proposta(
                    anterior,
                    perfil_alpinista=novo_perfil,
                )

        anterior.refresh_from_db()
        self.assertTrue(anterior.vigente)
        self.assertIsNone(anterior.retirado_em)
        self.assertEqual(proposta.itens.count(), 1)


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL real')
class PropostaVioleirosConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.encontro = Encontro.objects.create(
            encontro='Escalada Concorrência MME',
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia=date(2027, 3, 10),
            data_exato='10 de março de 2027',
        )
        self.proposta = criar_proposta_violeiros(encontro=self.encontro)

    def criar_perfil(self, indice):
        return PerfilAlpinista.objects.create(
            pessoa=Pessoa.objects.create(nome=f'Concorrente {indice}'),
            violeiro=True,
            disponivel_mme=True,
        )

    def executar_em_paralelo(self, operacoes):
        barreira = Barrier(len(operacoes))

        def executar(operacao):
            close_old_connections()
            try:
                barreira.wait()
                try:
                    return operacao()
                except ValidationError:
                    return 'bloqueada'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(operacoes)) as executor:
            return list(executor.map(executar, operacoes))

    def test_duas_inclusoes_concorrentes_respeitam_o_mesmo_slot(self):
        perfis = (self.criar_perfil(1), self.criar_perfil(2))
        resultados = self.executar_em_paralelo(tuple(
            lambda perfil_id=perfil.pk: preencher_posicao_proposta(
                PropostaVioleiros.objects.get(pk=self.proposta.pk),
                perfil_alpinista=PerfilAlpinista.objects.get(pk=perfil_id),
                papel_sugerido=(
                    ItemPropostaVioleiros.PapelSugerido.INTEGRANTE
                ),
                posicao=1,
            ).pk
            for perfil in perfis
        ))

        self.assertEqual(resultados.count('bloqueada'), 1)
        self.assertEqual(
            ItemPropostaVioleiros.objects.filter(vigente=True).count(),
            1,
        )

    def test_mesmo_candidato_concorrente_ocupa_apenas_um_slot(self):
        perfil = self.criar_perfil(1)
        resultados = self.executar_em_paralelo(tuple(
            lambda posicao=posicao: preencher_posicao_proposta(
                PropostaVioleiros.objects.get(pk=self.proposta.pk),
                perfil_alpinista=PerfilAlpinista.objects.get(pk=perfil.pk),
                papel_sugerido=(
                    ItemPropostaVioleiros.PapelSugerido.INTEGRANTE
                ),
                posicao=posicao,
            ).pk
            for posicao in (1, 2)
        ))

        self.assertEqual(resultados.count('bloqueada'), 1)
        self.assertEqual(
            ItemPropostaVioleiros.objects.filter(vigente=True).count(),
            1,
        )

    def test_substituicoes_concorrentes_exigem_a_mesma_ocupacao_vigente(self):
        original = preencher_posicao_proposta(
            self.proposta,
            perfil_alpinista=self.criar_perfil(1),
            papel_sugerido=ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
            posicao=1,
        )
        perfis = (self.criar_perfil(2), self.criar_perfil(3))

        resultados = self.executar_em_paralelo(tuple(
            lambda perfil_id=perfil.pk: substituir_ocupacao_proposta(
                ItemPropostaVioleiros.objects.get(pk=original.pk),
                perfil_alpinista=PerfilAlpinista.objects.get(pk=perfil_id),
            )[1].pk
            for perfil in perfis
        ))

        self.assertEqual(resultados.count('bloqueada'), 1)
        self.assertEqual(ItemPropostaVioleiros.objects.count(), 2)
        self.assertEqual(
            ItemPropostaVioleiros.objects.filter(vigente=True).count(),
            1,
        )

    def test_encerramento_concorrente_com_edicao_preserva_estado_consistente(self):
        perfil = self.criar_perfil(1)
        resultados = self.executar_em_paralelo((
            lambda: encerrar_proposta_violeiros(
                PropostaVioleiros.objects.get(pk=self.proposta.pk)
            ).status,
            lambda: preencher_posicao_proposta(
                PropostaVioleiros.objects.get(pk=self.proposta.pk),
                perfil_alpinista=PerfilAlpinista.objects.get(pk=perfil.pk),
                papel_sugerido=(
                    ItemPropostaVioleiros.PapelSugerido.INTEGRANTE
                ),
                posicao=1,
            ).pk,
        ))

        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.status, PropostaVioleiros.Status.ENCERRADA)
        self.assertIn(
            ItemPropostaVioleiros.objects.filter(vigente=True).count(),
            (0, 1),
        )
        self.assertEqual(len(resultados), 2)

    def test_alocacao_oficial_concorrente_reflete_sem_dual_write(self):
        perfil = self.criar_perfil(1)
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=self.encontro.tipo,
            codigo='violeiros',
            nome='Violeiros',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=template,
            codigo='violeiros',
            nome='Violeiros',
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo='integrante',
            nome='Integrante',
        )
        convite = ConviteEncontro.objects.create(
            pessoa=perfil.pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        def escalar():
            trabalho = iniciar_trabalho_confirmado(
                ConviteEncontro.objects.get(pk=convite.pk),
                confirmar_avisos=True,
            )
            return alocar_trabalho(
                trabalho,
                RoleEquipeEncontro.objects.get(pk=role.pk),
                confirmar_avisos=True,
            ).pk

        resultados = self.executar_em_paralelo((
            lambda: preencher_posicao_proposta(
                PropostaVioleiros.objects.get(pk=self.proposta.pk),
                perfil_alpinista=PerfilAlpinista.objects.get(pk=perfil.pk),
                papel_sugerido=(
                    ItemPropostaVioleiros.PapelSugerido.INTEGRANTE
                ),
                posicao=1,
            ).pk,
            escalar,
        ))

        self.assertEqual(
            TrabalhoEncontro.objects.get().status,
            TrabalhoEncontro.Status.ALOCADO,
        )
        itens = ItemPropostaVioleiros.objects.all()
        self.assertIn(itens.count(), (0, 1))
        if itens.exists():
            self.assertEqual(
                obter_situacao_item_proposta(itens.get()).situacao,
                SituacaoItemProposta.APROVEITADO_VIOLEIROS,
            )
        self.assertEqual(len(resultados), 2)
