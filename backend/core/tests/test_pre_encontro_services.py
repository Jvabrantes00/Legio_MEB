from datetime import date, time, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from core.models import (
    AtendimentoPreEncontro,
    ConferenciaCuidadoPreEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DadosCuidadoInscricao,
    DecisaoVagaPreEncontro,
    Encontro,
    EventoAuditoriaEncontro,
    InscricaoEncontro,
    PagamentoPreEncontro,
    PerfilAlpinista,
    Pessoa,
    PreEncontro,
)
from core.roles import SiaRole
from core.services.pre_encontro import (
    SituacaoAptidaoPreEncontro,
    aumentar_capacidade_pre_encontro,
    avaliar_aptidao_pre_encontro,
    conferir_cuidados_pre_encontro,
    registrar_checkin_pre_encontro,
    registrar_pagamento_pre_encontro,
    regularizar_atendimento_pre_encontro,
    resolver_vaga_pre_encontro,
)
from core.services.configuracao_encontristas import (
    alterar_configuracao_encontristas,
)
from core.tests.factories import make_encontro


class PreEncontroServiceTests(TestCase):
    def setUp(self):
        self.usuario_fichas = self.criar_usuario('fichas', SiaRole.FICHAS)
        self.usuario_diretoria = self.criar_usuario(
            'diretoria',
            SiaRole.DIRETORIA,
        )
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.pre_encontro = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 1, 1),
            horario=time(14),
            local='Local do Pré',
        )
        agora = timezone.now()
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=3,
            idade_minima=15,
            idade_maxima=17,
            inscricoes_abrem_em=agora - timedelta(days=1),
            inscricoes_encerram_em=agora + timedelta(days=1),
        )

    def criar_usuario(self, username, role):
        usuario = User.objects.create_user(username=username)
        grupo, _ = Group.objects.get_or_create(name=role.value)
        usuario.groups.add(grupo)
        return usuario

    def criar_inscricao(self, *, encontro=None, pessoa=None):
        return InscricaoEncontro.objects.create(
            encontro=encontro or self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )

    def checkin_pessoa(self, nome='Pessoa regularizada'):
        pessoa = Pessoa.objects.create(nome=nome)
        atendimento = registrar_checkin_pre_encontro(
            usuario=self.usuario_fichas,
            pre_encontro=self.pre_encontro,
            pessoa=pessoa,
        )
        return pessoa, atendimento

    def test_checkin_suporta_tres_origens_e_e_idempotente(self):
        inscricao = self.criar_inscricao()
        com_inscricao = registrar_checkin_pre_encontro(
            usuario=self.usuario_fichas,
            pre_encontro=self.pre_encontro,
            inscricao=inscricao,
        )
        pessoa, com_pessoa = self.checkin_pessoa()
        avulso = registrar_checkin_pre_encontro(
            usuario=self.usuario_fichas,
            pre_encontro=self.pre_encontro,
            nome_informado='Pessoa avulsa',
            data_nascimento_informada=date(2010, 1, 1),
            telefone_informado='61999990000',
        )
        repetido = registrar_checkin_pre_encontro(
            usuario=self.usuario_fichas,
            pre_encontro=self.pre_encontro,
            pessoa=pessoa,
        )

        self.assertEqual(com_inscricao.inscricao, inscricao)
        self.assertIsNone(com_inscricao.pessoa_id)
        self.assertEqual(com_pessoa.pessoa, pessoa)
        self.assertIsNone(com_pessoa.inscricao_id)
        self.assertIsNone(avulso.pessoa_id)
        self.assertIsNone(avulso.inscricao_id)
        self.assertEqual(repetido.pk, com_pessoa.pk)
        self.assertEqual(AtendimentoPreEncontro.objects.count(), 3)
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='pre_encontro.checkin_registrado',
            ).count(),
            3,
        )

    def test_inscricao_resolvida_e_pessoa_reutilizam_o_mesmo_checkin(self):
        pessoa = Pessoa.objects.create(nome='Pessoa já resolvida')
        inscricao = self.criar_inscricao(pessoa=pessoa)
        por_inscricao = registrar_checkin_pre_encontro(
            usuario=self.usuario_fichas,
            pre_encontro=self.pre_encontro,
            inscricao=inscricao,
        )

        por_pessoa = registrar_checkin_pre_encontro(
            usuario=self.usuario_fichas,
            pre_encontro=self.pre_encontro,
            pessoa=pessoa,
        )

        self.assertEqual(por_pessoa.pk, por_inscricao.pk)
        self.assertEqual(AtendimentoPreEncontro.objects.count(), 1)

    def test_avulso_nao_fica_apto_e_regularizacao_preserva_snapshot(self):
        atendimento = registrar_checkin_pre_encontro(
            usuario=self.usuario_fichas,
            pre_encontro=self.pre_encontro,
            nome_informado='Origem preservada',
            data_nascimento_informada=date(2010, 1, 1),
            cpf_informado='52998224725',
            telefone_informado='61999990000',
        )
        snapshot = (
            atendimento.nome_informado,
            atendimento.data_nascimento_informada,
            atendimento.cpf_informado,
            atendimento.telefone_informado,
        )
        self.assertFalse(avaliar_aptidao_pre_encontro(atendimento).apto)

        pessoa = Pessoa.objects.create(nome='Pessoa canônica')
        inscricao = self.criar_inscricao(pessoa=pessoa)
        regularizado = regularizar_atendimento_pre_encontro(
            usuario=self.usuario_fichas,
            atendimento=atendimento,
            pessoa=pessoa,
            inscricao=inscricao,
        )
        repetido = regularizar_atendimento_pre_encontro(
            usuario=self.usuario_fichas,
            atendimento=regularizado,
            pessoa=pessoa,
            inscricao=inscricao,
        )
        regularizado.refresh_from_db()

        self.assertEqual(repetido.pk, regularizado.pk)
        self.assertEqual(
            (
                regularizado.nome_informado,
                regularizado.data_nascimento_informada,
                regularizado.cpf_informado,
                regularizado.telefone_informado,
            ),
            snapshot,
        )
        self.assertTrue(avaliar_aptidao_pre_encontro(regularizado).apto)
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='pre_encontro.atendimento_regularizado',
            ).count(),
            1,
        )

    def test_regularizacao_rejeita_inscricao_de_outro_encontro(self):
        _, atendimento = self.checkin_pessoa()
        outro_encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        inscricao = self.criar_inscricao(encontro=outro_encontro)

        with self.assertRaises(ValidationError):
            regularizar_atendimento_pre_encontro(
                usuario=self.usuario_fichas,
                atendimento=atendimento,
                inscricao=inscricao,
            )

    def test_pagamento_foto_e_cuidado_nao_bloqueiam_aptidao(self):
        pessoa, atendimento = self.checkin_pessoa()
        capacidade = self.configuracao.capacidade
        decisoes = DecisaoVagaPreEncontro.objects.count()
        self.assertTrue(avaliar_aptidao_pre_encontro(atendimento).apto)

        pagamento = registrar_pagamento_pre_encontro(
            usuario=self.usuario_fichas,
            atendimento=atendimento,
            status=PagamentoPreEncontro.Status.PENDENTE,
        )
        self.assertEqual(pagamento.status, 'pendente')
        self.assertTrue(avaliar_aptidao_pre_encontro(atendimento).apto)
        self.assertFalse(hasattr(atendimento, 'foto_privada'))
        self.assertFalse(hasattr(atendimento, 'conferencia_cuidado'))
        self.assertFalse(PerfilAlpinista.objects.exists())
        self.configuracao.refresh_from_db()
        self.assertEqual(self.configuracao.capacidade, capacidade)
        self.assertEqual(DecisaoVagaPreEncontro.objects.count(), decisoes)
        self.assertFalse(ConviteEncontro.objects.exists())

        atualizado = registrar_pagamento_pre_encontro(
            usuario=self.usuario_fichas,
            atendimento=atendimento,
            status=PagamentoPreEncontro.Status.PAGO,
            valor=Decimal('50.00'),
            forma=PagamentoPreEncontro.Forma.PIX,
            pago_em=timezone.now(),
        )
        self.assertEqual(atualizado.pk, pagamento.pk)
        self.assertEqual(PagamentoPreEncontro.objects.count(), 1)
        self.assertTrue(avaliar_aptidao_pre_encontro(atendimento).apto)
        self.assertEqual(pessoa.pk, atendimento.pessoa_id)
        mesma_linha = registrar_pagamento_pre_encontro(
            usuario=self.usuario_fichas,
            atendimento=atendimento,
            status=PagamentoPreEncontro.Status.PAGO,
            valor=Decimal('50.00'),
            forma=PagamentoPreEncontro.Forma.PIX,
            pago_em=atualizado.pago_em,
            observacao='Observação operacional atualizada.',
        )
        self.assertEqual(mesma_linha.pk, pagamento.pk)
        self.assertEqual(
            mesma_linha.observacao,
            'Observação operacional atualizada.',
        )

    def test_conferencia_e_fato_operacional_versionado_e_auditado(self):
        pessoa = Pessoa.objects.create(nome='Pessoa com cuidados')
        inscricao = self.criar_inscricao(pessoa=pessoa)
        dados = DadosCuidadoInscricao.objects.create(
            inscricao=inscricao,
            possui_alergias=DadosCuidadoInscricao.RespostaBinaria.NAO,
        )
        atendimento = registrar_checkin_pre_encontro(
            usuario=self.usuario_fichas,
            pre_encontro=self.pre_encontro,
            inscricao=inscricao,
            pessoa=pessoa,
        )
        aptidao_antes = avaliar_aptidao_pre_encontro(atendimento)
        momento_primeiro = timezone.now()
        primeira = conferir_cuidados_pre_encontro(
            usuario=self.usuario_fichas,
            atendimento=atendimento,
            dados_cuidado=dados,
            momento=momento_primeiro,
        )
        marcador = primeira.dados_cuidado_atualizado_em
        dados_antes = dados.possui_alergias

        dados.outras_informacoes = 'Informação atualizada posteriormente.'
        dados.save(update_fields=['outras_informacoes', 'atualizado_em'])
        dados.refresh_from_db()
        primeira.refresh_from_db()
        self.assertLess(
            primeira.dados_cuidado_atualizado_em,
            dados.atualizado_em,
        )
        momento_segundo = momento_primeiro + timedelta(minutes=1)
        segunda = conferir_cuidados_pre_encontro(
            usuario=self.usuario_diretoria,
            atendimento=atendimento,
            dados_cuidado=dados,
            momento=momento_segundo,
        )

        self.assertEqual(primeira.pk, segunda.pk)
        self.assertEqual(ConferenciaCuidadoPreEncontro.objects.count(), 1)
        self.assertEqual(segunda.dados_cuidado, dados)
        self.assertEqual(segunda.conferido_por, self.usuario_diretoria)
        self.assertEqual(segunda.conferido_em, momento_segundo)
        self.assertEqual(segunda.dados_cuidado_atualizado_em, dados.atualizado_em)
        self.assertLess(marcador, dados.atualizado_em)
        self.assertEqual(dados.possui_alergias, dados_antes)
        self.assertEqual(
            avaliar_aptidao_pre_encontro(atendimento),
            aptidao_antes,
        )
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='pre_encontro.cuidados_conferidos',
            ).count(),
            2,
        )

    def test_capacidade_suficiente_deriva_aptidao_sem_persisti_la(self):
        _, atendimento = self.checkin_pessoa()

        resultado = avaliar_aptidao_pre_encontro(atendimento)

        self.assertTrue(resultado.apto)
        self.assertEqual(
            resultado.situacao,
            SituacaoAptidaoPreEncontro.APTO,
        )
        self.assertNotIn(
            'apto',
            {campo.name for campo in AtendimentoPreEncontro._meta.fields},
        )

    def test_excesso_coloca_todos_em_disputa_sem_prioridade(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        _, primeiro = self.checkin_pessoa('Primeiro check-in')
        self.assertTrue(avaliar_aptidao_pre_encontro(primeiro).apto)
        _, segundo = self.checkin_pessoa('Segundo check-in')

        primeiro.refresh_from_db()
        segundo.refresh_from_db()
        self.assertEqual(
            primeiro.decisao_vaga.status,
            DecisaoVagaPreEncontro.Status.AGUARDANDO_DECISAO_DIRETORIA,
        )
        self.assertEqual(
            segundo.decisao_vaga.status,
            DecisaoVagaPreEncontro.Status.AGUARDANDO_DECISAO_DIRETORIA,
        )
        self.assertFalse(avaliar_aptidao_pre_encontro(primeiro).apto)
        self.assertFalse(avaliar_aptidao_pre_encontro(segundo).apto)
        self.assertFalse(ConviteEncontro.objects.exists())

    def test_diretoria_aprova_um_e_nao_aprova_outro_sem_apagar_presenca(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        _, primeiro = self.checkin_pessoa('Candidato aprovado')
        _, segundo = self.checkin_pessoa('Candidato não aprovado')

        aprovada = resolver_vaga_pre_encontro(
            usuario=self.usuario_diretoria,
            atendimento=primeiro,
            status=DecisaoVagaPreEncontro.Status.APROVADO,
            justificativa='Decisão da Diretoria.',
        )
        nao_aprovada = resolver_vaga_pre_encontro(
            usuario=self.usuario_diretoria,
            atendimento=segundo,
            status=DecisaoVagaPreEncontro.Status.NAO_APROVADO,
            justificativa='Decisão da Diretoria.',
        )
        repetida = resolver_vaga_pre_encontro(
            usuario=self.usuario_diretoria,
            atendimento=primeiro,
            status=DecisaoVagaPreEncontro.Status.APROVADO,
        )

        self.assertEqual(repetida.pk, aprovada.pk)
        self.assertTrue(avaliar_aptidao_pre_encontro(primeiro).apto)
        self.assertFalse(avaliar_aptidao_pre_encontro(segundo).apto)
        self.assertEqual(nao_aprovada.status, 'nao_aprovado')
        self.assertEqual(AtendimentoPreEncontro.objects.count(), 2)
        self.assertEqual(Pessoa.objects.count(), 2)
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='pre_encontro.vaga_resolvida',
            ).count(),
            2,
        )

    def test_aumento_recalcula_todos_sem_escolher_primeiro(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        _, primeiro = self.checkin_pessoa('Primeiro')
        _, segundo = self.checkin_pessoa('Segundo')
        self.assertEqual(DecisaoVagaPreEncontro.objects.count(), 2)

        aumentar_capacidade_pre_encontro(
            usuario=self.usuario_diretoria,
            configuracao=self.configuracao,
            capacidade=2,
            justificativa='Capacidade operacional ampliada.',
        )

        self.assertFalse(DecisaoVagaPreEncontro.objects.exists())
        self.assertTrue(avaliar_aptidao_pre_encontro(primeiro).apto)
        self.assertTrue(avaliar_aptidao_pre_encontro(segundo).apto)

    def test_vaga_aprovada_impede_reducao_que_geraria_overbooking(self):
        self.configuracao.capacidade = 2
        self.configuracao.save(update_fields=['capacidade'])
        pessoa_confirmada = Pessoa.objects.create(nome='Pessoa confirmada')
        ConviteEncontro.objects.create(
            pessoa=pessoa_confirmada,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        _, primeiro = self.checkin_pessoa('Primeiro')
        self.checkin_pessoa('Segundo')
        resolver_vaga_pre_encontro(
            usuario=self.usuario_diretoria,
            atendimento=primeiro,
            status=DecisaoVagaPreEncontro.Status.APROVADO,
        )

        with self.assertRaises(ValidationError):
            alterar_configuracao_encontristas(
                usuario=self.usuario_diretoria,
                configuracao=self.configuracao,
                capacidade=1,
            )

    def test_confirmados_ocupam_capacidade_canonica(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoa_confirmada = Pessoa.objects.create(nome='Pessoa confirmada')
        ConviteEncontro.objects.create(
            pessoa=pessoa_confirmada,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        _, candidato = self.checkin_pessoa('Pessoa excedente')

        self.assertEqual(
            candidato.decisao_vaga.status,
            DecisaoVagaPreEncontro.Status.AGUARDANDO_DECISAO_DIRETORIA,
        )
        with self.assertRaises(ValidationError):
            resolver_vaga_pre_encontro(
                usuario=self.usuario_diretoria,
                atendimento=candidato,
                status=DecisaoVagaPreEncontro.Status.APROVADO,
            )

    def test_lifecycle_bloqueia_encerrados_e_suspende_adiado(self):
        for status in (
            Encontro.Status.CANCELADO,
            Encontro.Status.FINALIZADO,
            Encontro.Status.ADIADO,
        ):
            with self.subTest(status=status):
                self.encontro.status = status
                self.encontro.save(update_fields=['status'])
                with self.assertRaises(ValidationError):
                    self.checkin_pessoa(f'Pessoa {status}')

        self.encontro.status = Encontro.Status.EM_PREPARACAO
        self.encontro.save(update_fields=['status'])
        _, atendimento = self.checkin_pessoa('Pessoa após reprogramação')
        self.encontro.status = Encontro.Status.ADIADO
        self.encontro.save(update_fields=['status'])
        quantidade = AtendimentoPreEncontro.objects.count()
        self.encontro.status = Encontro.Status.EM_PREPARACAO
        self.encontro.save(update_fields=['status'])

        self.assertEqual(AtendimentoPreEncontro.objects.count(), quantidade)
        self.assertTrue(avaliar_aptidao_pre_encontro(atendimento).apto)

    def test_save_direto_nao_cria_aptidao_nem_overbooking(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoas = [Pessoa.objects.create(nome=f'Pessoa {i}') for i in range(2)]

        for pessoa in pessoas:
            AtendimentoPreEncontro.objects.create(
                pre_encontro=self.pre_encontro,
                pessoa=pessoa,
                registrado_por=self.usuario_fichas,
            )

        self.configuracao.refresh_from_db()
        self.assertEqual(self.configuracao.capacidade, 1)
        self.assertFalse(ConviteEncontro.objects.exists())
        self.assertFalse(PerfilAlpinista.objects.exists())
