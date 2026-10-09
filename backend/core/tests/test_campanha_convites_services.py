from datetime import date, datetime, timedelta
from hashlib import sha256
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

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
    Pessoa,
    RodadaConvitesEncontro,
)
from core.roles import SiaRole
from core.services import campanhas_convites as services
from core.tests.factories import make_encontro


class CampanhaConvitesServiceTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='fichas-campanha-services',
        )
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.momento = timezone.make_aware(datetime(2030, 1, 10, 9, 0))
        self.prazo = self.momento + timedelta(days=10)
        self.encontro = make_encontro(
            data_referencia=date(2030, 6, 1),
        )
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
            data=date(2030, 6, 1),
        )
        self.pessoa, self.inscricao, self.convite = self.criar_candidato(
            nome='Pessoa elegível',
            email='candidata@example.test',
        )

    def criar_candidato(self, *, nome, email='', status=None):
        pessoa = Pessoa.objects.create(
            nome=nome,
            email=email or None,
            data_nascimento=date(2010, 1, 1),
        )
        inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.PUBLICA,
        )
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=status or ConviteEncontro.Status.CONVIDADO,
        )
        return pessoa, inscricao, convite

    def emitir_inicial(self):
        return services.iniciar_campanha(
            usuario=self.usuario,
            encontro=self.encontro,
            prazo_confirmacao=self.prazo,
            momento=self.momento,
        )

    def iniciar(self):
        return self.emitir_inicial().campanha

    def test_inicio_manual_cria_uma_campanha_rodada_inicial_e_oportunidade(self):
        resultado = self.emitir_inicial()
        campanha = resultado.campanha

        rodada = campanha.rodadas.get()
        oportunidade = rodada.oportunidades.get()
        self.assertEqual(campanha.status, CampanhaConvitesEncontro.Status.ATIVA)
        self.assertEqual(rodada.tipo, RodadaConvitesEncontro.Tipo.INICIAL)
        self.assertEqual(rodada.sequencia, 1)
        self.assertEqual(oportunidade.convite, self.convite)
        self.assertEqual(oportunidade.expira_em, self.prazo)
        self.assertEqual(len(resultado.emissoes), 1)
        emissao = resultado.emissoes[0]
        self.assertEqual(emissao.oportunidade, oportunidade)
        self.assertEqual(
            oportunidade.token_digest,
            sha256(emissao.token.encode()).hexdigest(),
        )
        self.assertNotEqual(oportunidade.token_digest, emissao.token)
        persistida = OportunidadeConviteEncontro.objects.values().get(
            pk=oportunidade.pk,
        )
        self.assertNotIn(emissao.token, repr(persistida))
        self.assertFalse(hasattr(oportunidade, 'token'))
        self.assertNotIn(emissao.token, repr(emissao))
        self.assertNotIn(emissao.token, repr(resultado))
        self.assertFalse(EntregaConviteEncontro.objects.exists())

    def test_segundo_inicio_e_negado_sem_duplicar(self):
        self.iniciar()

        with self.assertRaises(ValidationError):
            self.iniciar()

        self.assertEqual(CampanhaConvitesEncontro.objects.count(), 1)
        self.assertEqual(RodadaConvitesEncontro.objects.count(), 1)
        self.assertEqual(OportunidadeConviteEncontro.objects.count(), 1)

    def test_inicio_exige_prazo_futuro(self):
        with self.assertRaises(ValidationError):
            services.iniciar_campanha(
                usuario=self.usuario,
                encontro=self.encontro,
                prazo_confirmacao=self.momento,
                momento=self.momento,
            )

        self.assertFalse(CampanhaConvitesEncontro.objects.exists())

    def test_expiracao_e_idempotente_e_aguarda_decisao_sem_prorrogar(self):
        campanha = self.iniciar()
        oportunidade = OportunidadeConviteEncontro.objects.get()
        instante = self.prazo + timedelta(seconds=1)

        services.processar_prazo(
            usuario=self.usuario,
            campanha=campanha,
            momento=instante,
        )
        services.processar_prazo(
            usuario=self.usuario,
            campanha=campanha,
            momento=instante,
        )

        campanha.refresh_from_db()
        oportunidade.refresh_from_db()
        self.convite.refresh_from_db()
        self.assertEqual(
            campanha.status,
            CampanhaConvitesEncontro.Status.AGUARDANDO_DECISAO,
        )
        self.assertEqual(
            oportunidade.status,
            OportunidadeConviteEncontro.Status.EXPIRADA,
        )
        self.assertEqual(
            self.convite.status,
            ConviteEncontro.Status.SEM_RESPOSTA,
        )
        self.assertEqual(campanha.rodadas.count(), 1)

    def test_encerramento_e_explicito_e_idempotente(self):
        campanha = self.iniciar()
        services.processar_prazo(
            usuario=self.usuario,
            campanha=campanha,
            momento=self.prazo + timedelta(seconds=1),
        )

        encerrada = services.encerrar_campanha(
            usuario=self.usuario,
            campanha=campanha,
            justificativa='Encerramento decidido por Fichas.',
            momento=self.prazo + timedelta(minutes=1),
        )
        repetida = services.encerrar_campanha(
            usuario=self.usuario,
            campanha=encerrada,
            momento=self.prazo + timedelta(minutes=2),
        )

        self.assertEqual(encerrada.pk, repetida.pk)
        self.assertEqual(encerrada.status, CampanhaConvitesEncontro.Status.ENCERRADA)
        self.assertIsNotNone(encerrada.encerrada_em)

    def test_prorrogacao_cria_nova_rodada_e_digest_sem_ressuscitar_anterior(self):
        campanha = self.iniciar()
        antiga = OportunidadeConviteEncontro.objects.get()
        digest_antigo = antiga.token_digest
        services.processar_prazo(
            usuario=self.usuario,
            campanha=campanha,
            momento=self.prazo + timedelta(seconds=1),
        )
        novo_prazo = self.prazo + timedelta(days=5)

        resultado = services.prorrogar_campanha(
            usuario=self.usuario,
            campanha=campanha,
            novo_prazo=novo_prazo,
            momento=self.prazo + timedelta(minutes=1),
        )
        campanha = resultado.campanha

        antiga.refresh_from_db()
        nova = OportunidadeConviteEncontro.objects.exclude(pk=antiga.pk).get()
        rodada = nova.rodada
        self.assertEqual(campanha.status, CampanhaConvitesEncontro.Status.ATIVA)
        self.assertEqual(rodada.tipo, RodadaConvitesEncontro.Tipo.PRORROGACAO)
        self.assertEqual(rodada.sequencia, 2)
        self.assertEqual(antiga.status, OportunidadeConviteEncontro.Status.EXPIRADA)
        self.assertNotEqual(nova.token_digest, digest_antigo)
        self.assertEqual(len(resultado.emissoes), 1)
        self.assertEqual(resultado.emissoes[0].oportunidade, nova)
        self.assertEqual(
            nova.token_digest,
            sha256(resultado.emissoes[0].token.encode()).hexdigest(),
        )

    def test_recusa_nao_reenvia_nem_reaparece_na_selecao_automatica(self):
        campanha = self.iniciar()
        oportunidade = OportunidadeConviteEncontro.objects.get()
        services.registrar_recusa(
            usuario=self.usuario,
            oportunidade=oportunidade,
            momento=self.momento + timedelta(days=1),
        )

        self.convite.refresh_from_db()
        oportunidade.refresh_from_db()
        projecao = services.projetar_candidatos(
            usuario=self.usuario,
            encontro=self.encontro,
        )
        self.assertEqual(self.convite.status, ConviteEncontro.Status.RECUSADO)
        self.assertEqual(
            oportunidade.status,
            OportunidadeConviteEncontro.Status.CONSUMIDA,
        )
        self.assertEqual(projecao.candidatos, ())
        self.assertEqual(campanha.rodadas.count(), 1)

    def test_reabertura_exige_justificativa_e_cria_reposicao_com_novo_digest(self):
        _, _, outro_convite = self.criar_candidato(
            nome='Outra pessoa elegível',
            email='outra@example.test',
        )
        campanha = self.iniciar()
        antiga = OportunidadeConviteEncontro.objects.get(convite=self.convite)
        oportunidade_alheia = OportunidadeConviteEncontro.objects.get(
            convite=outro_convite,
        )
        services.registrar_recusa(
            usuario=self.usuario,
            oportunidade=antiga,
            momento=self.momento + timedelta(days=1),
        )
        with self.assertRaises(ValidationError):
            services.reabrir_recusa(
                usuario=self.usuario,
                campanha=campanha,
                convite=self.convite,
                justificativa=' ',
                momento=self.momento + timedelta(days=2),
            )

        abertura = services.reabrir_recusa(
            usuario=self.usuario,
            campanha=campanha,
            convite=self.convite,
            justificativa='Contato regularizado por Fichas.',
            momento=self.momento + timedelta(days=2),
        )

        nova = next(item for item in abertura.oportunidades if item.convite_id == self.convite.pk)
        self.assertEqual(abertura.rodada.tipo, RodadaConvitesEncontro.Tipo.REPOSICAO)
        self.assertEqual(len(abertura.oportunidades), 1)
        self.assertEqual(len(abertura.emissoes), 1)
        self.assertEqual(abertura.emissoes[0].oportunidade, nova)
        self.assertNotEqual(nova.token_digest, antiga.token_digest)
        oportunidade_alheia.refresh_from_db()
        self.assertEqual(
            oportunidade_alheia.status,
            OportunidadeConviteEncontro.Status.PENDENTE,
        )
        self.convite.refresh_from_db()
        self.assertEqual(self.convite.status, ConviteEncontro.Status.CONVIDADO)

    def test_lista_de_espera_e_derivada_sem_prioridade(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoa_confirmada = Pessoa.objects.create(
            nome='Pessoa confirmada',
            data_nascimento=date(2010, 1, 1),
        )
        ConviteEncontro.objects.create(
            pessoa=pessoa_confirmada,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        projecao = services.projetar_lista_espera(
            usuario=self.usuario,
            encontro=self.encontro,
        )
        dados = projecao.as_dict()

        self.assertTrue(dados['lista_espera_ativa'])
        self.assertTrue(dados['sem_prioridade'])
        self.assertFalse(dados['ordenacao_representa_prioridade'])
        self.assertNotIn('posicao', dados['candidatos'][0])
        self.assertFalse(hasattr(projecao.candidatos[0], 'prioridade'))

    def test_capacidade_nao_cheia_nao_projeta_lista_de_espera(self):
        projecao = services.projetar_lista_espera(
            usuario=self.usuario,
            encontro=self.encontro,
        )

        self.assertFalse(projecao.lista_espera_ativa)
        self.assertEqual(projecao.candidatos, ())

    def test_nova_vaga_cria_reposicao_para_todos_sem_escolher_primeiro(self):
        self.criar_candidato(nome='Segunda pessoa', email='segunda@example.test')
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoa_confirmada = Pessoa.objects.create(
            nome='Confirmação que liberará vaga',
            data_nascimento=date(2010, 1, 1),
        )
        confirmado = ConviteEncontro.objects.create(
            pessoa=pessoa_confirmada,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        campanha = self.iniciar()
        self.assertFalse(OportunidadeConviteEncontro.objects.exists())
        confirmado.status = ConviteEncontro.Status.SEM_RESPOSTA
        confirmado.save(update_fields=['status'])

        abertura = services.abrir_reposicao_nova_vaga(
            usuario=self.usuario,
            campanha=campanha,
            momento=self.momento + timedelta(days=1),
        )
        repetida = services.abrir_reposicao_nova_vaga(
            usuario=self.usuario,
            campanha=campanha,
            momento=self.momento + timedelta(days=1),
        )

        self.assertEqual(abertura.rodada.tipo, RodadaConvitesEncontro.Tipo.REPOSICAO)
        self.assertEqual(len(abertura.oportunidades), 2)
        self.assertEqual(len(abertura.emissoes), 2)
        self.assertFalse(repetida.criada)
        self.assertEqual(repetida.emissoes, ())
        self.assertEqual(RodadaConvitesEncontro.objects.count(), 2)

    def test_sem_canal_permanece_elegivel_visivel_e_sem_entrega(self):
        self.pessoa.email = None
        self.pessoa.save(update_fields=['email'])
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoa_confirmada = Pessoa.objects.create(
            nome='Pessoa que ocupa capacidade',
            data_nascimento=date(2010, 1, 1),
        )
        ConviteEncontro.objects.create(
            pessoa=pessoa_confirmada,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        projecao = services.projetar_lista_espera(
            usuario=self.usuario,
            encontro=self.encontro,
        )

        self.assertEqual(len(projecao.candidatos), 1)
        self.assertTrue(projecao.candidatos[0].sem_canal)
        self.assertIn(
            projecao.candidatos[0].elegibilidade,
            services._RESULTADOS_ELEGIVEIS,
        )
        self.assertFalse(EntregaConviteEncontro.objects.exists())

    def test_multiwrite_reverte_quando_auditoria_falha(self):
        with patch.object(
            services,
            'registrar_evento_auditoria_encontro',
            side_effect=RuntimeError('falha auditável'),
        ):
            with self.assertRaises(RuntimeError):
                self.iniciar()

        self.assertFalse(CampanhaConvitesEncontro.objects.exists())
        self.assertFalse(RodadaConvitesEncontro.objects.exists())
        self.assertFalse(OportunidadeConviteEncontro.objects.exists())

    def test_auditoria_nao_contem_pii_token_ou_digest(self):
        resultado = self.emitir_inicial()
        campanha = resultado.campanha
        evento = EventoAuditoriaEncontro.objects.get(
            fato='campanha_convites.iniciada',
        )
        oportunidade = OportunidadeConviteEncontro.objects.get()
        conteudo = f'{evento.valor_anterior} {evento.valor_novo}'.lower()

        self.assertEqual(evento.objeto_id, str(campanha.pk))
        self.assertNotIn(self.pessoa.email, conteudo)
        self.assertNotIn('cpf', conteudo)
        self.assertNotIn('token', conteudo)
        self.assertNotIn(oportunidade.token_digest, conteudo)
        self.assertNotIn(resultado.emissoes[0].token, conteudo)

    def test_usuario_sem_papel_nao_opera_campanha(self):
        sem_papel = get_user_model().objects.create_user(username='sem-papel')

        with self.assertRaises(PermissionDenied):
            services.iniciar_campanha(
                usuario=sem_papel,
                encontro=self.encontro,
                prazo_confirmacao=self.prazo,
                momento=self.momento,
            )

    def test_diretoria_e_suporte_consultam_mas_nao_gerem(self):
        campanha = self.iniciar()

        for role in (SiaRole.DIRETORIA, SiaRole.SUPORTE):
            usuario = get_user_model().objects.create_user(
                username=f'consulta-{role.value}',
            )
            grupo, _ = Group.objects.get_or_create(name=role.value)
            usuario.groups.add(grupo)

            with self.subTest(role=role):
                self.assertEqual(
                    services.consultar_campanha(
                        usuario=usuario,
                        encontro=self.encontro,
                    ),
                    campanha,
                )
                with self.assertRaises(PermissionDenied):
                    services.encerrar_campanha(
                        usuario=usuario,
                        campanha=campanha,
                        momento=self.momento + timedelta(days=1),
                    )

    def test_superuser_mantem_bypass_tecnico_na_service(self):
        superuser = get_user_model().objects.create_superuser(
            username='superuser-campanha-services',
            email='superuser-campanha-services@example.test',
            password='senha-exclusiva-de-teste',
        )

        resultado = services.iniciar_campanha(
            usuario=superuser,
            encontro=self.encontro,
            prazo_confirmacao=self.prazo,
            momento=self.momento,
        )

        self.assertEqual(resultado.campanha.iniciada_por, superuser)
