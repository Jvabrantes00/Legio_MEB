from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from hashlib import sha256
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from core.models import (
    CalendarioEncontro,
    CampanhaConvitesEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DiaEncontro,
    EventoAuditoriaEncontro,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    Pessoa,
    RodadaConvitesEncontro,
)
from core.roles import SiaRole
from core.services import campanhas_convites
from core.services import comandos_calendario
from core.services import oportunidades_convites as services
from core.services import participacoes as participacao_services
from core.tests.factories import make_encontro


class OportunidadeConviteFixtureMixin:
    def preparar_dominio(self, *, capacidade=2):
        self.momento = timezone.make_aware(datetime(2030, 1, 10, 9, 0))
        self.prazo = self.momento + timedelta(days=10)
        self.usuario = get_user_model().objects.create_user(
            username=f'fichas-convite-{id(self)}',
        )
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.encontro = make_encontro(data_referencia=date(2030, 6, 3))
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=capacidade,
            idade_minima=18,
            idade_maxima=30,
            inscricoes_abrem_em=self.momento - timedelta(days=30),
            inscricoes_encerram_em=self.momento - timedelta(days=1),
        )
        self.calendario = CalendarioEncontro.objects.create(
            encontro=self.encontro,
            versao=1,
            vigente=True,
            oficializado_em=self.momento,
        )
        DiaEncontro.objects.create(
            calendario=self.calendario,
            ordem=1,
            data=date(2030, 6, 3),
        )

    def criar_candidato(self, nome, *, nascimento=date(2005, 1, 1)):
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

    def iniciar_campanha(self):
        resultado = campanhas_convites.iniciar_campanha(
            usuario=self.usuario,
            encontro=self.encontro,
            prazo_confirmacao=self.prazo,
            momento=self.momento,
        )
        return resultado, {
            emissao.oportunidade.convite_id: emissao
            for emissao in resultado.emissoes
        }


class OportunidadeConviteServiceTests(
    OportunidadeConviteFixtureMixin,
    TestCase,
):
    def setUp(self):
        self.preparar_dominio()
        self.pessoa, self.convite = self.criar_candidato('Pessoa Um')
        self.resultado, self.emissoes = self.iniciar_campanha()
        self.emissao = self.emissoes[self.convite.pk]
        self.token = self.emissao.token
        self.oportunidade = self.emissao.oportunidade

    def responder(self, decisao='confirmar', **overrides):
        valores = {
            'token': self.token,
            'data_nascimento': self.pessoa.data_nascimento,
            'decisao': decisao,
            'momento': self.momento + timedelta(hours=1),
        }
        valores.update(overrides)
        return services.responder_convite_publico(**valores)

    def assert_auditoria_publica_minimizada(self, fato):
        evento = EventoAuditoriaEncontro.objects.get(fato=fato)
        conteudo = f'{evento.valor_anterior} {evento.valor_novo}'.lower()
        self.assertIsNone(evento.ator_id)
        self.assertEqual(evento.valor_anterior['origem'], 'publica')
        self.assertEqual(evento.valor_novo['origem'], 'publica')
        self.assertNotIn(self.token.lower(), conteudo)
        self.assertNotIn(self.oportunidade.token_digest, conteudo)
        self.assertNotIn(self.pessoa.data_nascimento.isoformat(), conteudo)
        self.assertNotIn(self.pessoa.email.lower(), conteudo)
        return evento

    def test_token_one_shot_e_digest_autenticam_com_nascimento(self):
        self.assertEqual(
            self.oportunidade.token_digest,
            sha256(self.token.encode()).hexdigest(),
        )
        self.assertFalse(hasattr(self.oportunidade, 'token'))
        self.assertNotEqual(self.token, str(self.oportunidade.pk))
        self.assertNotEqual(self.token, str(self.convite.pk))
        resultado = services.consultar_convite_publico(
            token=self.token,
            data_nascimento=self.pessoa.data_nascimento,
            momento=self.momento,
        )
        self.assertEqual(resultado.estado, services.EstadoConvitePublico.PENDENTE)

    def test_token_inexistente_e_nascimento_incorreto_nao_autenticam(self):
        casos = (
            ('A' * 43, self.pessoa.data_nascimento),
            (self.token, date(2004, 1, 1)),
            ('malformado', self.pessoa.data_nascimento),
        )
        for token, nascimento in casos:
            with self.subTest(token=token[:4], nascimento=nascimento):
                with self.assertRaises(services.ConvitePublicoNaoValidado):
                    services.consultar_convite_publico(
                        token=token,
                        data_nascimento=nascimento,
                        momento=self.momento,
                    )

    def test_confirmacao_consume_e_replay_nao_muda_decisao(self):
        primeira = self.responder()
        eventos = EventoAuditoriaEncontro.objects.count()
        replay = self.responder('recusar')
        self.convite.refresh_from_db()
        self.oportunidade.refresh_from_db()
        self.assertEqual(primeira.estado, services.EstadoConvitePublico.CONFIRMADO)
        self.assertEqual(replay.estado, services.EstadoConvitePublico.CONFIRMADO)
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONFIRMADO)
        self.assertEqual(
            self.oportunidade.status,
            OportunidadeConviteEncontro.Status.CONSUMIDA,
        )
        self.assertEqual(EventoAuditoriaEncontro.objects.count(), eventos)
        self.assert_auditoria_publica_minimizada(
            'oportunidade_convite.confirmada_publicamente',
        )

    def test_recusa_consume_e_replay_nao_muda_decisao(self):
        primeira = self.responder('recusar')
        eventos = EventoAuditoriaEncontro.objects.count()
        replay = self.responder('confirmar')
        self.convite.refresh_from_db()
        self.assertEqual(primeira.estado, services.EstadoConvitePublico.RECUSADO)
        self.assertEqual(replay.estado, services.EstadoConvitePublico.RECUSADO)
        self.assertEqual(self.convite.status, ConviteEncontro.Status.RECUSADO)
        self.assertEqual(EventoAuditoriaEncontro.objects.count(), eventos)

    def test_estados_nao_pendentes_nao_aceitam_resposta(self):
        for estado, esperado in (
            (OportunidadeConviteEncontro.Status.INVALIDADA, 'indisponivel'),
            (OportunidadeConviteEncontro.Status.SUSPENSA, 'suspenso'),
            (OportunidadeConviteEncontro.Status.EXPIRADA, 'expirado'),
        ):
            with self.subTest(estado=estado):
                self.oportunidade.status = estado
                self.oportunidade.save(update_fields=['status'])
                resultado = self.responder()
                self.convite.refresh_from_db()
                self.assertEqual(resultado.estado.value, esperado)
                self.assertEqual(
                    self.convite.status,
                    ConviteEncontro.Status.CONVIDADO,
                )
                self.oportunidade.status = (
                    OportunidadeConviteEncontro.Status.PENDENTE
                )
                self.oportunidade.save(update_fields=['status'])

    def test_campanha_inativa_nao_aceita_resposta(self):
        campanha = self.resultado.campanha
        campanha.status = CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO
        campanha.save(update_fields=['status', 'atualizada_em'])

        resultado = self.responder()

        self.convite.refresh_from_db()
        self.assertEqual(resultado.estado, services.EstadoConvitePublico.INDISPONIVEL)
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)

    def test_rodada_encerrada_nao_aceita_resposta(self):
        rodada = self.oportunidade.rodada
        rodada.status = RodadaConvitesEncontro.Status.ENCERRADA
        rodada.encerrada_em = self.momento + timedelta(minutes=30)
        rodada.save(update_fields=['status', 'encerrada_em', 'atualizada_em'])

        resultado = self.responder()

        self.convite.refresh_from_db()
        self.assertEqual(resultado.estado, services.EstadoConvitePublico.INDISPONIVEL)
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)

    def test_prazo_vencido_expira_lazy_sem_consumir(self):
        resultado = self.responder(momento=self.prazo + timedelta(seconds=1))
        self.oportunidade.refresh_from_db()
        self.convite.refresh_from_db()
        self.assertEqual(resultado.estado, services.EstadoConvitePublico.EXPIRADO)
        self.assertEqual(
            self.oportunidade.status,
            OportunidadeConviteEncontro.Status.EXPIRADA,
        )
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)

    def test_confirmacao_revalida_e_suspende_inelegivel(self):
        self.pessoa.data_nascimento = date(2015, 1, 1)
        self.pessoa.save(update_fields=['data_nascimento'])
        resultado = self.responder()
        self.oportunidade.refresh_from_db()
        self.assertEqual(resultado.estado, services.EstadoConvitePublico.SUSPENSO)
        self.assertEqual(
            self.oportunidade.status,
            OportunidadeConviteEncontro.Status.SUSPENSA,
        )

    def test_reprogramacao_suspende_pendente_que_se_torna_inelegivel(self):
        self.pessoa.data_nascimento = date(2012, 6, 3)
        self.pessoa.save(update_fields=['data_nascimento'])
        comandos_calendario.reprogramar_agenda(
            self.encontro,
            dias=[{'ordem': 1, 'data': date(2030, 6, 2)}],
            ator=self.usuario,
        )
        self.oportunidade.refresh_from_db()
        self.convite.refresh_from_db()
        self.assertEqual(
            self.oportunidade.status,
            OportunidadeConviteEncontro.Status.SUSPENSA,
        )
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)
        evento = EventoAuditoriaEncontro.objects.get(
            fato='oportunidade_convite.suspensa_inelegibilidade',
        )
        self.assertEqual(evento.ator, self.usuario)
        self.assertNotIn('origem', evento.valor_anterior)
        self.assertNotIn('origem', evento.valor_novo)

    def test_ultima_vaga_invalida_concorrentes_sem_recusa(self):
        pessoa_dois, convite_dois = self.criar_candidato('Pessoa Dois')
        # O cenário usa uma segunda oportunidade explícita da mesma rodada,
        # com o mesmo lifecycle one-shot da emissão canônica.
        token_dois = 'B' * 43
        oportunidade_dois = OportunidadeConviteEncontro.objects.create(
            rodada=self.oportunidade.rodada,
            convite=convite_dois,
            token_digest=sha256(token_dois.encode()).hexdigest(),
            expira_em=self.prazo,
        )
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        resultado = self.responder()
        oportunidade_dois.refresh_from_db()
        convite_dois.refresh_from_db()
        self.assertEqual(resultado.estado, services.EstadoConvitePublico.CONFIRMADO)
        self.assertEqual(
            oportunidade_dois.status,
            OportunidadeConviteEncontro.Status.INVALIDADA,
        )
        self.assertEqual(convite_dois.status, ConviteEncontro.Status.CONVIDADO)
        posterior = services.responder_convite_publico(
            token=token_dois,
            data_nascimento=pessoa_dois.data_nascimento,
            decisao='confirmar',
            momento=self.momento + timedelta(hours=2),
        )
        self.assertEqual(posterior.estado.value, 'indisponivel')
        self.assertEqual(
            ConviteEncontro.objects.filter(
                encontro=self.encontro,
                status=ConviteEncontro.Status.CONFIRMADO,
            ).count(),
            1,
        )

    def test_capacidade_cheia_invalida_sem_marcar_recusa(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoa = Pessoa.objects.create(
            nome='Já confirmada',
            data_nascimento=date(2000, 1, 1),
        )
        ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        resultado = self.responder()
        self.oportunidade.refresh_from_db()
        self.convite.refresh_from_db()
        self.assertEqual(resultado.estado.value, 'indisponivel')
        self.assertEqual(
            self.oportunidade.status,
            OportunidadeConviteEncontro.Status.INVALIDADA,
        )
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)

    def test_fluxo_interno_nao_ultrapassa_capacidade_configurada(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoa = Pessoa.objects.create(
            nome='Já confirmada internamente',
            data_nascimento=date(2000, 1, 1),
        )
        ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        with self.assertRaises(ValidationError):
            participacao_services.responder_convite(
                self.convite,
                status=ConviteEncontro.Status.CONFIRMADO,
            )

        self.convite.refresh_from_db()
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)

    def test_auditoria_nao_contem_segredo_nem_pii(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=['is_active'])
        self.responder()
        self.assert_auditoria_publica_minimizada(
            'oportunidade_convite.confirmada_publicamente',
        )

    def test_recusa_publica_independe_do_iniciador_ativo(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=['is_active'])

        resultado = self.responder('recusar')

        self.assertEqual(resultado.estado, services.EstadoConvitePublico.RECUSADO)
        self.assert_auditoria_publica_minimizada(
            'oportunidade_convite.recusada_publicamente',
        )

    def test_suspensao_publica_gera_auditoria_minimizada_sem_ator(self):
        self.usuario.is_active = False
        self.usuario.save(update_fields=['is_active'])
        self.pessoa.data_nascimento = date(2015, 1, 1)
        self.pessoa.save(update_fields=['data_nascimento'])

        resultado = self.responder()

        self.assertEqual(resultado.estado, services.EstadoConvitePublico.SUSPENSO)
        self.assert_auditoria_publica_minimizada(
            'oportunidade_convite.suspensa_inelegibilidade',
        )

    def test_invalidacao_por_lotacao_gera_auditoria_minimizada(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoa = Pessoa.objects.create(
            nome='Ocupante da vaga',
            data_nascimento=date(2000, 1, 1),
        )
        ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        resultado = self.responder()

        self.assertEqual(resultado.estado, services.EstadoConvitePublico.INDISPONIVEL)
        self.assert_auditoria_publica_minimizada(
            'oportunidade_convite.invalidada_lotacao',
        )

    def test_falha_de_auditoria_reverte_convite_e_oportunidade(self):
        with patch.object(services, '_auditar', side_effect=RuntimeError):
            with self.assertRaises(RuntimeError):
                self.responder()
        self.convite.refresh_from_db()
        self.oportunidade.refresh_from_db()
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)
        self.assertEqual(
            self.oportunidade.status,
            OportunidadeConviteEncontro.Status.PENDENTE,
        )


@skipUnless(connection.vendor == 'postgresql', 'Requer PostgreSQL real')
class OportunidadeConviteConcurrencyTests(
    OportunidadeConviteFixtureMixin,
    TransactionTestCase,
):
    reset_sequences = True

    def setUp(self):
        self.preparar_dominio(capacidade=2)
        ocupante = Pessoa.objects.create(
            nome='Ocupante',
            data_nascimento=date(2000, 1, 1),
        )
        ConviteEncontro.objects.create(
            pessoa=ocupante,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        self.candidatos = (
            self.criar_candidato('Concorrente Um'),
            self.criar_candidato('Concorrente Dois'),
        )
        _, emissoes = self.iniciar_campanha()
        self.dados = [
            (emissoes[convite.pk].token, pessoa.data_nascimento)
            for pessoa, convite in self.candidatos
        ]

    def test_duas_confirmacoes_concorrentes_na_ultima_vaga(self):
        barreira = Barrier(2)

        def confirmar(dados):
            close_old_connections()
            try:
                barreira.wait()
                return services.responder_convite_publico(
                    token=dados[0],
                    data_nascimento=dados[1],
                    decisao='confirmar',
                    momento=self.momento + timedelta(hours=1),
                ).estado
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(confirmar, self.dados))

        self.assertEqual(
            ConviteEncontro.objects.filter(
                encontro=self.encontro,
                status=ConviteEncontro.Status.CONFIRMADO,
            ).count(),
            2,
        )
        self.assertEqual(
            resultados.count(services.EstadoConvitePublico.CONFIRMADO),
            1,
        )
        self.assertEqual(
            OportunidadeConviteEncontro.objects.filter(
                status=OportunidadeConviteEncontro.Status.INVALIDADA,
            ).count(),
            1,
        )

    def test_confirmacao_publica_e_interna_concorrem_pela_ultima_vaga(self):
        barreira = Barrier(2)
        token, nascimento = self.dados[0]
        convite_interno = self.candidatos[1][1]

        def confirmar_publicamente():
            close_old_connections()
            try:
                barreira.wait()
                return services.responder_convite_publico(
                    token=token,
                    data_nascimento=nascimento,
                    decisao='confirmar',
                    momento=self.momento + timedelta(hours=1),
                ).estado.value
            finally:
                close_old_connections()

        def confirmar_internamente():
            close_old_connections()
            try:
                barreira.wait()
                try:
                    participacao_services.responder_convite(
                        ConviteEncontro.objects.get(pk=convite_interno.pk),
                        status=ConviteEncontro.Status.CONFIRMADO,
                    )
                except ValidationError:
                    return 'rejeitada'
                return 'confirmada'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = (
                executor.submit(confirmar_publicamente),
                executor.submit(confirmar_internamente),
            )
            resultados = [resultado.result() for resultado in resultados]

        self.assertEqual(
            ConviteEncontro.objects.filter(
                encontro=self.encontro,
                status=ConviteEncontro.Status.CONFIRMADO,
            ).count(),
            2,
        )
        self.assertEqual(
            ConviteEncontro.objects.filter(
                pk__in=[convite.pk for _, convite in self.candidatos],
                status=ConviteEncontro.Status.CONFIRMADO,
            ).count(),
            1,
        )
        self.assertEqual(
            sum(item in {'confirmado', 'confirmada'} for item in resultados),
            1,
        )
