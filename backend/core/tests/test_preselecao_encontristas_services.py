from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    AtendimentoPreEncontro,
    CampanhaConvitesEncontro,
    ConviteEncontro,
    Encontro,
    EntregaConviteEncontro,
    EventoAuditoriaEncontro,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    ParticipacaoEncontro,
    Pessoa,
    PreEncontro,
    PreSelecaoEncontrista,
    VinculoEncontroLegado,
)
from core.roles import SiaRole
from core.services.preselecoes_encontristas import (
    ErroPreSelecaoEncontrista,
    encerrar_preselecao_encontrista,
    preselecionar_encontrista,
)
from core.tests.factories import make_encontro


class PreSelecaoEncontristaServiceTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(username='fichas-preselecao')
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.pre_encontro = self._criar_pre_encontro(self.encontro)

    def _criar_pre_encontro(self, encontro):
        return PreEncontro.objects.create(
            encontro=encontro,
            data=date(2030, 1, 1),
            horario=time(14),
            local='Local do Pré-Encontro',
        )

    def _criar_inscricao(self, *, encontro=None, pessoa=None):
        return InscricaoEncontro.objects.create(
            encontro=encontro or self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )

    def _criar_atendimento(
        self,
        *,
        pre_encontro=None,
        pessoa=None,
        inscricao=None,
        nome='Pessoa avulsa',
        telefone='61999990000',
    ):
        valores = {
            'pre_encontro': pre_encontro or self.pre_encontro,
            'pessoa': pessoa,
            'inscricao': inscricao,
            'registrado_por': self.usuario,
        }
        if inscricao is None and pessoa is None:
            valores.update({
                'nome_informado': nome,
                'data_nascimento_informada': date(2010, 5, 10),
                'telefone_informado': telefone,
            })
        return AtendimentoPreEncontro.objects.create(**valores)

    def _preselecionar_inscricao(self, inscricao=None, **overrides):
        valores = {
            'usuario': self.usuario,
            'encontro': self.encontro,
            'origem_tipo': PreSelecaoEncontrista.OrigemTipo.INSCRICAO,
            'inscricao': inscricao or self._criar_inscricao(),
        }
        valores.update(overrides)
        return preselecionar_encontrista(**valores)

    def test_preseleciona_inscricao_sem_pessoa_resolvida(self):
        inscricao = self._criar_inscricao()

        preselecao = self._preselecionar_inscricao(inscricao)

        self.assertEqual(preselecao.inscricao_origem, inscricao)
        self.assertIsNone(preselecao.pessoa_resolvida)
        self.assertEqual(
            preselecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )

    def test_preseleciona_inscricao_com_pessoa_canonica(self):
        pessoa = Pessoa.objects.create(nome='Pessoa da inscrição')
        inscricao = self._criar_inscricao(pessoa=pessoa)

        preselecao = self._preselecionar_inscricao(inscricao)

        self.assertEqual(preselecao.pessoa_resolvida, pessoa)

    def test_rejeita_inscricao_de_outro_encontro(self):
        outro_encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        inscricao = self._criar_inscricao(encontro=outro_encontro)

        with self.assertRaises(ErroPreSelecaoEncontrista):
            self._preselecionar_inscricao(inscricao)

    def test_preseleciona_pessoa_somente_por_atendimento_canonico(self):
        pessoa = Pessoa.objects.create(nome='Pessoa identificada')
        atendimento = self._criar_atendimento(pessoa=pessoa)

        preselecao = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            atendimento=atendimento,
        )

        self.assertEqual(preselecao.atendimento_origem, atendimento)
        self.assertEqual(preselecao.pessoa_resolvida, pessoa)

    def test_rejeita_pessoa_sem_vinculo_canonico(self):
        atendimento = self._criar_atendimento()

        with self.assertRaises(ErroPreSelecaoEncontrista):
            preselecionar_encontrista(
                usuario=self.usuario,
                encontro=self.encontro,
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
                atendimento=atendimento,
            )

    def test_rejeita_atendimento_de_outro_pre_encontro(self):
        outro_encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        outro_pre = self._criar_pre_encontro(outro_encontro)
        pessoa = Pessoa.objects.create(nome='Pessoa de outro encontro')
        atendimento = self._criar_atendimento(
            pre_encontro=outro_pre,
            pessoa=pessoa,
        )

        with self.assertRaises(ErroPreSelecaoEncontrista):
            preselecionar_encontrista(
                usuario=self.usuario,
                encontro=self.encontro,
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
                atendimento=atendimento,
            )

    def test_preseleciona_avulso_sem_pessoa(self):
        atendimento = self._criar_atendimento()

        preselecao = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            atendimento=atendimento,
        )

        self.assertEqual(
            preselecao.origem_tipo,
            PreSelecaoEncontrista.OrigemTipo.AVULSO,
        )
        self.assertIsNone(preselecao.pessoa_resolvida)

    def test_avulso_regularizado_preserva_origem_e_pessoa_atual(self):
        atendimento = self._criar_atendimento()
        pessoa = Pessoa.objects.create(nome='Pessoa regularizada')
        atendimento.pessoa = pessoa
        atendimento.save(update_fields=['pessoa', 'atualizado_em'])

        preselecao = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            atendimento=atendimento,
        )

        self.assertEqual(
            preselecao.origem_tipo,
            PreSelecaoEncontrista.OrigemTipo.AVULSO,
        )
        self.assertEqual(preselecao.pessoa_resolvida, pessoa)

    def test_rejeita_origem_incorreta_e_atendimento_de_inscricao(self):
        pessoa = Pessoa.objects.create(nome='Pessoa inscrita')
        inscricao = self._criar_inscricao(pessoa=pessoa)
        atendimento = self._criar_atendimento(
            pessoa=pessoa,
            inscricao=inscricao,
        )

        with self.assertRaises(ErroPreSelecaoEncontrista):
            preselecionar_encontrista(
                usuario=self.usuario,
                encontro=self.encontro,
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
                atendimento=atendimento,
            )
        with self.assertRaises(ErroPreSelecaoEncontrista):
            preselecionar_encontrista(
                usuario=self.usuario,
                encontro=self.encontro,
                origem_tipo='origem-inexistente',
                atendimento=atendimento,
            )

    def test_repeticao_exata_e_idempotente_e_nao_duplica_auditoria(self):
        inscricao = self._criar_inscricao()

        primeira = self._preselecionar_inscricao(inscricao)
        repetida = self._preselecionar_inscricao(inscricao)

        self.assertEqual(repetida.pk, primeira.pk)
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.preselecionado',
            ).count(),
            1,
        )

    def test_repeticao_do_mesmo_atendimento_nao_cria_segundo_registro(self):
        atendimento = self._criar_atendimento()
        parametros = {
            'usuario': self.usuario,
            'encontro': self.encontro,
            'origem_tipo': PreSelecaoEncontrista.OrigemTipo.AVULSO,
            'atendimento': atendimento,
        }

        primeira = preselecionar_encontrista(**parametros)
        repetida = preselecionar_encontrista(**parametros)

        self.assertEqual(repetida.pk, primeira.pk)
        self.assertEqual(
            PreSelecaoEncontrista.objects.filter(
                encontro=self.encontro,
                atendimento_origem=atendimento,
                estado__in=(
                    PreSelecaoEncontrista.Estado.PRESELECIONADA,
                    PreSelecaoEncontrista.Estado.ENCAMINHADA,
                ),
            ).count(),
            1,
        )

    def test_conflito_da_mesma_pessoa_em_origens_distintas_e_bloqueado(self):
        pessoa = Pessoa.objects.create(nome='Pessoa em conflito')
        self._preselecionar_inscricao(
            self._criar_inscricao(pessoa=pessoa)
        )
        atendimento = self._criar_atendimento(pessoa=pessoa)

        with self.assertRaises(ErroPreSelecaoEncontrista):
            preselecionar_encontrista(
                usuario=self.usuario,
                encontro=self.encontro,
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
                atendimento=atendimento,
            )

    def test_regularizacao_posterior_reconhece_conflito_de_identidade(self):
        atendimento = self._criar_atendimento()
        avulso = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            atendimento=atendimento,
        )
        pessoa = Pessoa.objects.create(nome='Pessoa depois regularizada')
        self._preselecionar_inscricao(
            self._criar_inscricao(pessoa=pessoa)
        )
        atendimento.pessoa = pessoa
        atendimento.save(update_fields=['pessoa', 'atualizado_em'])

        with self.assertRaises(ErroPreSelecaoEncontrista):
            preselecionar_encontrista(
                usuario=self.usuario,
                encontro=self.encontro,
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
                atendimento=atendimento,
            )

        avulso.refresh_from_db()
        self.assertIsNone(avulso.pessoa_resolvida)

    def test_avulsos_nao_resolvidos_nao_sao_deduplicados_por_nome(self):
        primeiro = self._criar_atendimento(
            nome='Mesmo nome declarado',
            telefone='61999990001',
        )
        segundo = self._criar_atendimento(
            nome='Mesmo nome declarado',
            telefone='61999990002',
        )

        registros = tuple(
            preselecionar_encontrista(
                usuario=self.usuario,
                encontro=self.encontro,
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
                atendimento=atendimento,
            )
            for atendimento in (primeiro, segundo)
        )

        self.assertNotEqual(registros[0].pk, registros[1].pk)

    def test_encerrada_permite_nova_preselecao_e_preserva_historico(self):
        inscricao = self._criar_inscricao()
        anterior = self._preselecionar_inscricao(inscricao)
        encerrar_preselecao_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            preselecao=anterior,
        )

        nova = self._preselecionar_inscricao(inscricao)

        self.assertNotEqual(nova.pk, anterior.pk)
        anterior.refresh_from_db()
        self.assertEqual(
            anterior.estado,
            PreSelecaoEncontrista.Estado.ENCERRADA,
        )

    def test_encerramento_registra_autor_instante_e_auditoria_uma_vez(self):
        preselecao = self._preselecionar_inscricao()
        instante = timezone.now()

        encerrada = encerrar_preselecao_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            preselecao=preselecao,
            momento=instante,
        )
        repetida = encerrar_preselecao_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            preselecao=encerrada,
        )

        self.assertEqual(repetida.pk, encerrada.pk)
        self.assertEqual(encerrada.encerrada_por, self.usuario)
        self.assertEqual(encerrada.encerrada_em, instante)
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.preselecao_encerrada',
            ).count(),
            1,
        )

    def test_rejeita_encerramento_de_outro_encontro(self):
        preselecao = self._preselecionar_inscricao()
        outro_encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)

        with self.assertRaises(ErroPreSelecaoEncontrista):
            encerrar_preselecao_encontrista(
                usuario=self.usuario,
                encontro=outro_encontro,
                preselecao=preselecao,
            )

    def test_rejeita_encerramento_de_preselecao_encaminhada(self):
        preselecao = self._preselecionar_inscricao()
        preselecao.estado = PreSelecaoEncontrista.Estado.ENCAMINHADA
        preselecao.encaminhada_por = self.usuario
        preselecao.encaminhada_em = timezone.now()
        preselecao.save(update_fields=[
            'estado',
            'encaminhada_por',
            'encaminhada_em',
            'atualizada_em',
        ])

        with self.assertRaises(ErroPreSelecaoEncontrista):
            encerrar_preselecao_encontrista(
                usuario=self.usuario,
                encontro=self.encontro,
                preselecao=preselecao,
            )

    def test_lifecycle_encerrado_bloqueia_nova_operacao(self):
        self.encontro.status = Encontro.Status.FINALIZADO
        self.encontro.save(update_fields=['status'])

        with self.assertRaises(PermissionDenied):
            self._preselecionar_inscricao()

    def test_falha_de_auditoria_reverte_criacao(self):
        inscricao = self._criar_inscricao()

        with patch(
            'core.services.preselecoes_encontristas.'
            'registrar_evento_auditoria_encontro',
            side_effect=ValidationError('Falha de auditoria.'),
        ):
            with self.assertRaises(ValidationError):
                self._preselecionar_inscricao(inscricao)

        self.assertFalse(
            PreSelecaoEncontrista.objects.filter(
                inscricao_origem=inscricao,
            ).exists()
        )

    def test_falha_de_auditoria_reverte_encerramento(self):
        preselecao = self._preselecionar_inscricao()

        with patch(
            'core.services.preselecoes_encontristas.'
            'registrar_evento_auditoria_encontro',
            side_effect=ValidationError('Falha de auditoria.'),
        ):
            with self.assertRaises(ValidationError):
                encerrar_preselecao_encontrista(
                    usuario=self.usuario,
                    encontro=self.encontro,
                    preselecao=preselecao,
                )

        preselecao.refresh_from_db()
        self.assertEqual(
            preselecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )
        self.assertIsNone(preselecao.encerrada_por)
        self.assertIsNone(preselecao.encerrada_em)

    def test_auditoria_de_criacao_e_minimizada(self):
        atendimento = self._criar_atendimento(
            nome='Nome que não deve ir à auditoria',
            telefone='61999990003',
        )

        preselecao = preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            atendimento=atendimento,
        )

        evento = EventoAuditoriaEncontro.objects.get(
            fato='encontrista.preselecionado',
        )
        self.assertEqual(evento.objeto_id, str(preselecao.pk))
        self.assertEqual(
            set(evento.valor_novo),
            {'estado', 'origem_tipo', 'pessoa_resolvida'},
        )
        self.assertNotIn('nome', str(evento.valor_novo).lower())
        self.assertNotIn('telefone', str(evento.valor_novo).lower())

    def test_nao_produz_efeitos_colaterais_de_blocos_futuros(self):
        contagens_antes = {
            'convites': ConviteEncontro.objects.count(),
            'oportunidades': OportunidadeConviteEncontro.objects.count(),
            'entregas': EntregaConviteEncontro.objects.count(),
            'participacoes': ParticipacaoEncontro.objects.count(),
            'vinculos_legados': VinculoEncontroLegado.objects.count(),
            'campanhas': CampanhaConvitesEncontro.objects.count(),
            'pessoas': Pessoa.objects.count(),
            'inscricoes': InscricaoEncontro.objects.count(),
        }
        atendimento = self._criar_atendimento()

        preselecionar_encontrista(
            usuario=self.usuario,
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            atendimento=atendimento,
        )

        self.assertEqual(
            contagens_antes,
            {
                'convites': ConviteEncontro.objects.count(),
                'oportunidades': OportunidadeConviteEncontro.objects.count(),
                'entregas': EntregaConviteEncontro.objects.count(),
                'participacoes': ParticipacaoEncontro.objects.count(),
                'vinculos_legados': VinculoEncontroLegado.objects.count(),
                'campanhas': CampanhaConvitesEncontro.objects.count(),
                'pessoas': Pessoa.objects.count(),
                'inscricoes': InscricaoEncontro.objects.count(),
            },
        )


@skipUnless(
    connection.vendor == 'postgresql',
    'Concorrência real exige PostgreSQL.',
)
class PreSelecaoEncontristaConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.usuario = User.objects.create_user(
            username='fichas-concorrencia-preselecao',
        )
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )

    def test_criacao_concorrente_da_mesma_origem_e_idempotente(self):
        barreira = Barrier(2)

        def criar():
            close_old_connections()
            try:
                usuario = User.objects.get(pk=self.usuario.pk)
                encontro = Encontro.objects.get(pk=self.encontro.pk)
                inscricao = InscricaoEncontro.objects.get(pk=self.inscricao.pk)
                barreira.wait()
                return preselecionar_encontrista(
                    usuario=usuario,
                    encontro=encontro,
                    origem_tipo=PreSelecaoEncontrista.OrigemTipo.INSCRICAO,
                    inscricao=inscricao,
                ).pk
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            ids = tuple(executor.map(lambda _: criar(), range(2)))

        self.assertEqual(ids[0], ids[1])
        self.assertEqual(PreSelecaoEncontrista.objects.count(), 1)
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='encontrista.preselecionado',
            ).count(),
            1,
        )
