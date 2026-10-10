from datetime import date, time, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from core.models import (
    AtendimentoPreEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DecisaoVagaPreEncontro,
    FotoTemporariaPreEncontro,
    InscricaoEncontro,
    PagamentoPreEncontro,
    PerfilAlpinista,
    Pessoa,
    PreEncontro,
)
from core.tests.factories import make_encontro


class PreEncontroModelTests(TestCase):
    cpf_origem = '52998224725'

    def setUp(self):
        self.encontro = make_encontro()
        self.usuario = get_user_model().objects.create_user(
            username='operador-pre-encontro',
        )
        self.pre_encontro = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 1, 1),
            horario=time(14, 0),
            local='Local do Pré-Encontro',
        )

    def criar_atendimento_avulso(self, **overrides):
        valores = {
            'pre_encontro': self.pre_encontro,
            'nome_informado': 'Pessoa avulsa',
            'data_nascimento_informada': date(2010, 5, 10),
            'telefone_informado': '61999990000',
            'registrado_por': self.usuario,
        }
        valores.update(overrides)
        return AtendimentoPreEncontro.objects.create(**valores)

    def criar_inscricao(self, **overrides):
        valores = {
            'encontro': self.encontro,
            'origem': InscricaoEncontro.Origem.PUBLICA,
        }
        valores.update(overrides)
        return InscricaoEncontro.objects.create(**valores)

    def test_pre_encontro_e_zero_ou_um_por_encontro(self):
        self.assertEqual(self.encontro.pre_encontro, self.pre_encontro)

        with self.assertRaises(IntegrityError), transaction.atomic():
            PreEncontro.objects.create(
                encontro=self.encontro,
                data=date(2030, 1, 2),
                horario=time(14, 0),
                local='Outro local',
            )

    def test_atendimento_com_inscricao_nao_exige_pessoa(self):
        atendimento = AtendimentoPreEncontro.objects.create(
            pre_encontro=self.pre_encontro,
            inscricao=self.criar_inscricao(),
            registrado_por=self.usuario,
        )

        self.assertIsNone(atendimento.pessoa_id)

    def test_atendimento_com_pessoa_nao_exige_inscricao(self):
        pessoa = Pessoa.objects.create(nome='Pessoa identificada')
        atendimento = AtendimentoPreEncontro.objects.create(
            pre_encontro=self.pre_encontro,
            pessoa=pessoa,
            registrado_por=self.usuario,
        )

        self.assertIsNone(atendimento.inscricao_id)

    def test_atendimento_avulso_exige_snapshot_minimo(self):
        atendimento = self.criar_atendimento_avulso()

        self.assertEqual(atendimento.nome_informado, 'Pessoa avulsa')
        self.assertIsNone(atendimento.cpf_informado)

        casos_invalidos = (
            {'nome_informado': ''},
            {'data_nascimento_informada': None},
            {'telefone_informado': ''},
        )
        for overrides in casos_invalidos:
            with self.subTest(overrides=overrides):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.criar_atendimento_avulso(**overrides)

    def test_cpf_opcional_nao_cria_falsa_unicidade(self):
        primeiro = self.criar_atendimento_avulso()
        segundo = self.criar_atendimento_avulso(
            nome_informado='Outra pessoa',
            data_nascimento_informada=date(2011, 6, 11),
            telefone_informado='61999990001',
        )

        self.assertIsNone(primeiro.cpf_informado)
        self.assertIsNone(segundo.cpf_informado)

    def test_cpf_usa_canonicalizacao_existente(self):
        atendimento = AtendimentoPreEncontro(
            pre_encontro=self.pre_encontro,
            nome_informado='Pessoa com CPF formatado',
            data_nascimento_informada=date(2010, 5, 10),
            cpf_informado='529.982.247-25',
            telefone_informado='61999990000',
            registrado_por=self.usuario,
        )

        atendimento.full_clean()
        atendimento.save()
        atendimento.refresh_from_db()

        self.assertEqual(atendimento.cpf_informado, self.cpf_origem)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_atendimento_avulso(
                nome_informado='CPF não canonicalizado',
                telefone_informado='61999990001',
                cpf_informado='111.444.777-35',
            )

    def test_unicidades_fortes_valem_dentro_do_mesmo_pre_encontro(self):
        pessoa = Pessoa.objects.create(nome='Pessoa única')
        inscricao = self.criar_inscricao()
        self.criar_atendimento_avulso(
            pessoa=pessoa,
            inscricao=inscricao,
            cpf_informado=self.cpf_origem,
        )

        duplicidades = (
            {'pessoa': pessoa},
            {'inscricao': inscricao},
            {'cpf_informado': self.cpf_origem},
        )
        for overrides in duplicidades:
            with self.subTest(overrides=tuple(overrides)):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self.criar_atendimento_avulso(**overrides)

    def test_identificadores_podem_repetir_em_outro_pre_encontro(self):
        pessoa = Pessoa.objects.create(nome='Pessoa em dois Pré-Encontros')
        primeiro = self.criar_atendimento_avulso(
            pessoa=pessoa,
            cpf_informado=self.cpf_origem,
        )
        outro_encontro = make_encontro()
        outro_pre = PreEncontro.objects.create(
            encontro=outro_encontro,
            data=date(2030, 2, 1),
            horario=time(14, 0),
            local='Outro local',
        )
        segundo = AtendimentoPreEncontro.objects.create(
            pre_encontro=outro_pre,
            pessoa=pessoa,
            nome_informado='Pessoa em dois Pré-Encontros',
            data_nascimento_informada=date(2010, 5, 10),
            cpf_informado=self.cpf_origem,
            telefone_informado='61999990000',
            registrado_por=self.usuario,
        )

        self.assertNotEqual(primeiro.pre_encontro, segundo.pre_encontro)

    def test_regularizacao_preserva_snapshot_de_origem(self):
        atendimento = self.criar_atendimento_avulso(
            cpf_informado=self.cpf_origem,
        )
        snapshot = {
            'nome_informado': atendimento.nome_informado,
            'data_nascimento_informada': atendimento.data_nascimento_informada,
            'cpf_informado': atendimento.cpf_informado,
            'telefone_informado': atendimento.telefone_informado,
        }

        atendimento.pessoa = Pessoa.objects.create(nome='Pessoa regularizada')
        atendimento.inscricao = self.criar_inscricao(
            pessoa=atendimento.pessoa,
        )
        atendimento.save(update_fields=['pessoa', 'inscricao'])
        atendimento.refresh_from_db()

        for campo, valor in snapshot.items():
            self.assertEqual(getattr(atendimento, campo), valor)

    def test_pagamentos_pendente_pago_e_isento_sao_fatos_operacionais(self):
        pessoa = Pessoa.objects.create(nome='Pessoa com pagamento')
        inscricao = self.criar_inscricao(pessoa=pessoa)
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )
        configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=3,
            idade_minima=15,
            idade_maxima=17,
            inscricoes_abrem_em=timezone.now(),
            inscricoes_encerram_em=timezone.now() + timedelta(days=1),
        )
        atendimentos = [
            AtendimentoPreEncontro.objects.create(
                pre_encontro=self.pre_encontro,
                inscricao=inscricao,
                pessoa=pessoa,
                registrado_por=self.usuario,
            ),
            self.criar_atendimento_avulso(
                nome_informado='Pessoa paga',
                telefone_informado='61999990001',
            ),
            self.criar_atendimento_avulso(
                nome_informado='Pessoa isenta',
                telefone_informado='61999990002',
            ),
        ]
        estado_atendimento = {
            campo: getattr(atendimentos[0], campo)
            for campo in (
                'inscricao_id',
                'pessoa_id',
                'registrado_em',
                'observacoes',
                'atualizado_em',
            )
        }
        estado_inscricao = (
            inscricao.status,
            inscricao.cancelada_em,
            inscricao.reativada_em,
            inscricao.atualizada_em,
        )
        estado_convite = (convite.status, convite.atualizado_em)
        capacidade = configuracao.capacidade
        perfis = PerfilAlpinista.objects.count()

        pendente = PagamentoPreEncontro.objects.create(
            atendimento=atendimentos[0],
        )
        pago = PagamentoPreEncontro.objects.create(
            atendimento=atendimentos[1],
            status=PagamentoPreEncontro.Status.PAGO,
            valor=Decimal('50.00'),
            forma=PagamentoPreEncontro.Forma.PIX,
            pago_em=timezone.now(),
        )
        isento = PagamentoPreEncontro.objects.create(
            atendimento=atendimentos[2],
            status=PagamentoPreEncontro.Status.ISENTO,
        )

        self.assertEqual(pendente.status, 'pendente')
        self.assertEqual(pago.valor, Decimal('50.00'))
        self.assertEqual(isento.status, 'isento')
        atendimentos[0].refresh_from_db()
        inscricao.refresh_from_db()
        convite.refresh_from_db()
        configuracao.refresh_from_db()
        self.assertEqual(
            {
                campo: getattr(atendimentos[0], campo)
                for campo in estado_atendimento
            },
            estado_atendimento,
        )
        self.assertEqual(
            (
                inscricao.status,
                inscricao.cancelada_em,
                inscricao.reativada_em,
                inscricao.atualizada_em,
            ),
            estado_inscricao,
        )
        self.assertEqual(
            (convite.status, convite.atualizado_em),
            estado_convite,
        )
        self.assertEqual(configuracao.capacidade, capacidade)
        self.assertEqual(PerfilAlpinista.objects.count(), perfis)
        self.assertEqual(ConviteEncontro.objects.count(), 1)
        self.assertFalse(DecisaoVagaPreEncontro.objects.exists())

    def test_pagamento_rejeita_valor_negativo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PagamentoPreEncontro.objects.create(
                atendimento=self.criar_atendimento_avulso(),
                valor=Decimal('-0.01'),
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            PagamentoPreEncontro.objects.create(
                atendimento=self.criar_atendimento_avulso(
                    nome_informado='Forma inválida',
                    telefone_informado='61999990001',
                ),
                forma='cheque',
            )

    def test_decisao_de_vaga_representa_espera_e_resultados(self):
        espera = DecisaoVagaPreEncontro.objects.create(
            atendimento=self.criar_atendimento_avulso(),
        )
        aprovada = DecisaoVagaPreEncontro.objects.create(
            atendimento=self.criar_atendimento_avulso(
                nome_informado='Pessoa aprovada',
                telefone_informado='61999990001',
            ),
            status=DecisaoVagaPreEncontro.Status.APROVADO,
            decidida_por=self.usuario,
            decidida_em=timezone.now(),
        )
        nao_aprovada = DecisaoVagaPreEncontro.objects.create(
            atendimento=self.criar_atendimento_avulso(
                nome_informado='Pessoa não aprovada',
                telefone_informado='61999990002',
            ),
            status=DecisaoVagaPreEncontro.Status.NAO_APROVADO,
            decidida_por=self.usuario,
            decidida_em=timezone.now(),
        )

        self.assertEqual(
            espera.status,
            'aguardando_decisao_diretoria',
        )
        self.assertEqual(aprovada.status, 'aprovado')
        self.assertEqual(nao_aprovada.status, 'nao_aprovado')

    def test_decisao_final_exige_ator_e_instante(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            DecisaoVagaPreEncontro.objects.create(
                atendimento=self.criar_atendimento_avulso(),
                status=DecisaoVagaPreEncontro.Status.APROVADO,
            )

    def test_foto_privada_independe_de_pessoa_e_sobrevive_regularizacao(self):
        atendimento = self.criar_atendimento_avulso()
        self.assertIsNone(atendimento.pessoa_id)

        with TemporaryDirectory() as media_root, self.settings(
            MEDIA_ROOT=media_root,
        ):
            foto = FotoTemporariaPreEncontro.objects.create(
                atendimento=atendimento,
                arquivo=SimpleUploadedFile(
                    'foto.png',
                    b'conteudo-de-foto-de-teste',
                    content_type='image/png',
                ),
                nome_original='foto.png',
                content_type='image/png',
                tamanho=24,
                sha256='a' * 64,
            )
            referencia = foto.arquivo.name
            arquivos_antes = sorted(
                caminho.relative_to(media_root)
                for caminho in Path(media_root).rglob('*')
                if caminho.is_file()
            )

            self.assertRegex(
                referencia,
                r'^pre_encontros/fotos/[0-9a-f]{32}$',
            )
            self.assertEqual(len(arquivos_antes), 1)
            self.assertEqual(
                self.client.get(f'/media/{referencia}').status_code,
                404,
            )

            atendimento.pessoa = Pessoa.objects.create(nome='Pessoa com foto')
            atendimento.save(update_fields=['pessoa'])
            foto.refresh_from_db()
            arquivos_depois = sorted(
                caminho.relative_to(media_root)
                for caminho in Path(media_root).rglob('*')
                if caminho.is_file()
            )

            self.assertEqual(foto.arquivo.name, referencia)
            self.assertEqual(arquivos_depois, arquivos_antes)

    def test_models_nao_se_relacionam_com_preparatorias(self):
        models_pre = (
            PreEncontro,
            AtendimentoPreEncontro,
            PagamentoPreEncontro,
            DecisaoVagaPreEncontro,
            FotoTemporariaPreEncontro,
        )

        for model in models_pre:
            with self.subTest(model=model.__name__):
                relacionados = {
                    campo.related_model.__name__
                    for campo in model._meta.fields
                    if campo.is_relation
                }
                self.assertNotIn('ReuniaoPreparatoriaEncontro', relacionados)
                self.assertNotIn('AgendaEncontro', relacionados)

    def test_criacao_e_alteracao_nao_geram_aptidao_ou_overbooking(self):
        configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=1,
            idade_minima=15,
            idade_maxima=17,
            inscricoes_abrem_em=timezone.now(),
            inscricoes_encerram_em=timezone.now() + timedelta(days=1),
        )
        pessoa = Pessoa.objects.create(nome='Pessoa em atendimento')
        inscricao = self.criar_inscricao(pessoa=pessoa)
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
        )
        atendimento = AtendimentoPreEncontro.objects.create(
            pre_encontro=self.pre_encontro,
            inscricao=inscricao,
            pessoa=pessoa,
            registrado_por=self.usuario,
        )
        DecisaoVagaPreEncontro.objects.create(
            atendimento=atendimento,
            status=DecisaoVagaPreEncontro.Status.APROVADO,
            decidida_por=self.usuario,
            decidida_em=timezone.now(),
        )

        estado_inscricao = (inscricao.status, inscricao.atualizada_em)
        estado_convite = (convite.status, convite.atualizado_em)
        capacidade = configuracao.capacidade
        atendimentos = AtendimentoPreEncontro.objects.count()
        atendimento.observacoes = 'Observação operacional corrigida.'
        atendimento.save(update_fields=['observacoes'])

        atendimento.refresh_from_db()
        configuracao.refresh_from_db()
        inscricao.refresh_from_db()
        convite.refresh_from_db()
        self.assertEqual(
            atendimento.observacoes,
            'Observação operacional corrigida.',
        )
        self.assertEqual(
            AtendimentoPreEncontro.objects.count(),
            atendimentos,
        )
        self.assertEqual(configuracao.capacidade, capacidade)
        self.assertEqual(
            (inscricao.status, inscricao.atualizada_em),
            estado_inscricao,
        )
        self.assertEqual(
            (convite.status, convite.atualizado_em),
            estado_convite,
        )
        self.assertEqual(ConviteEncontro.objects.count(), 1)
        self.assertFalse(PerfilAlpinista.objects.exists())
