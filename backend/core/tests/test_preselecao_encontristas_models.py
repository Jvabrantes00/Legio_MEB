from datetime import date, time
from importlib import import_module

from django.contrib.auth import get_user_model
from django.db import IntegrityError, migrations, models, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.utils import timezone

from core.models import (
    AtendimentoPreEncontro,
    ConviteEncontro,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    ParticipacaoEncontro,
    Pessoa,
    PreEncontro,
    PreSelecaoEncontrista,
    VinculoEncontroLegado,
)
from core.tests.factories import make_encontro


class PreSelecaoEncontristaModelTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='operador.preselecao',
        )
        self.encontro = make_encontro()
        self.pre_encontro = self._criar_pre_encontro(self.encontro)

    def _criar_pre_encontro(self, encontro):
        return PreEncontro.objects.create(
            encontro=encontro,
            data=date(2030, 1, 1),
            horario=time(14, 0),
            local='Local do Pré-Encontro',
        )

    def _criar_inscricao(self, *, encontro=None, pessoa=None):
        return InscricaoEncontro.objects.create(
            encontro=encontro or self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.PUBLICA,
        )

    def _criar_atendimento(
        self,
        *,
        pre_encontro=None,
        pessoa=None,
        nome='Pessoa avulsa',
    ):
        valores = {
            'pre_encontro': pre_encontro or self.pre_encontro,
            'pessoa': pessoa,
            'registrado_por': self.usuario,
        }
        if pessoa is None:
            valores.update({
                'nome_informado': nome,
                'data_nascimento_informada': date(2010, 5, 10),
                'telefone_informado': '61999990000',
            })
        return AtendimentoPreEncontro.objects.create(**valores)

    def _criar_por_inscricao(self, *, inscricao=None, **overrides):
        valores = {
            'encontro': self.encontro,
            'origem_tipo': PreSelecaoEncontrista.OrigemTipo.INSCRICAO,
            'inscricao_origem': inscricao or self._criar_inscricao(),
            'registrada_por': self.usuario,
        }
        valores.update(overrides)
        return PreSelecaoEncontrista.objects.create(**valores)

    def _criar_por_atendimento(
        self,
        *,
        atendimento,
        origem_tipo,
        pessoa_resolvida=None,
        **overrides,
    ):
        valores = {
            'encontro': self.encontro,
            'origem_tipo': origem_tipo,
            'atendimento_origem': atendimento,
            'pessoa_resolvida': pessoa_resolvida,
            'registrada_por': self.usuario,
        }
        valores.update(overrides)
        return PreSelecaoEncontrista.objects.create(**valores)

    def test_aceita_as_tres_origens_estruturalmente_validas(self):
        inscricao = self._criar_por_inscricao()
        pessoa = Pessoa.objects.create(nome='Pessoa identificada')
        atendimento_pessoa = self._criar_atendimento(pessoa=pessoa)
        por_pessoa = self._criar_por_atendimento(
            atendimento=atendimento_pessoa,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa_resolvida=pessoa,
        )
        atendimento_avulso = self._criar_atendimento(nome='Pessoa avulsa 2')
        avulso = self._criar_por_atendimento(
            atendimento=atendimento_avulso,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
        )

        self.assertIsNotNone(inscricao.pk)
        self.assertEqual(por_pessoa.pessoa_resolvida, pessoa)
        self.assertIsNone(avulso.pessoa_resolvida)

    def test_avulso_pode_preservar_origem_apos_resolucao_da_pessoa(self):
        pessoa = Pessoa.objects.create(nome='Pessoa regularizada')
        atendimento = self._criar_atendimento()

        pre_selecao = self._criar_por_atendimento(
            atendimento=atendimento,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            pessoa_resolvida=pessoa,
        )

        self.assertEqual(
            pre_selecao.origem_tipo,
            PreSelecaoEncontrista.OrigemTipo.AVULSO,
        )
        self.assertEqual(pre_selecao.pessoa_resolvida, pessoa)

    def test_rejeita_origens_com_referencias_incoerentes(self):
        pessoa = Pessoa.objects.create(nome='Pessoa sem referência coerente')
        inscricao = self._criar_inscricao()
        atendimento = self._criar_atendimento()
        casos = (
            {
                'origem_tipo': PreSelecaoEncontrista.OrigemTipo.PESSOA,
                'atendimento_origem': atendimento,
            },
            {
                'origem_tipo': PreSelecaoEncontrista.OrigemTipo.INSCRICAO,
                'inscricao_origem': inscricao,
                'atendimento_origem': atendimento,
            },
            {
                'origem_tipo': PreSelecaoEncontrista.OrigemTipo.AVULSO,
                'pessoa_resolvida': pessoa,
            },
        )

        for campos in casos:
            with self.subTest(campos=campos):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    PreSelecaoEncontrista.objects.create(
                        encontro=self.encontro,
                        registrada_por=self.usuario,
                        **campos,
                    )

    def test_estado_inicial_e_coerente(self):
        pre_selecao = self._criar_por_inscricao()

        self.assertEqual(
            pre_selecao.estado,
            PreSelecaoEncontrista.Estado.PRESELECIONADA,
        )
        self.assertIsNone(pre_selecao.encaminhada_por)
        self.assertIsNone(pre_selecao.encerrada_por)

    def test_rejeita_estados_com_metadados_incoerentes(self):
        agora = timezone.now()
        casos = (
            {
                'estado': PreSelecaoEncontrista.Estado.ENCAMINHADA,
            },
            {
                'estado': PreSelecaoEncontrista.Estado.ENCAMINHADA,
                'encaminhada_por': self.usuario,
            },
            {
                'estado': PreSelecaoEncontrista.Estado.ENCERRADA,
            },
            {
                'estado': PreSelecaoEncontrista.Estado.ENCERRADA,
                'encerrada_por': self.usuario,
            },
            {
                'estado': PreSelecaoEncontrista.Estado.PRESELECIONADA,
                'encaminhada_por': self.usuario,
                'encaminhada_em': agora,
            },
            {
                'estado': PreSelecaoEncontrista.Estado.ENCAMINHADA,
                'encaminhada_por': self.usuario,
                'encaminhada_em': agora,
                'encerrada_por': self.usuario,
                'encerrada_em': agora,
            },
        )

        for metadados in casos:
            with self.subTest(metadados=metadados):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self._criar_por_inscricao(**metadados)

    def test_encerramento_preserva_metadados_de_encaminhamento(self):
        encaminhada_em = timezone.now()
        pre_selecao = self._criar_por_inscricao(
            estado=PreSelecaoEncontrista.Estado.ENCAMINHADA,
            encaminhada_por=self.usuario,
            encaminhada_em=encaminhada_em,
        )

        pre_selecao.estado = PreSelecaoEncontrista.Estado.ENCERRADA
        pre_selecao.encerrada_por = self.usuario
        pre_selecao.encerrada_em = timezone.now()
        pre_selecao.save()
        pre_selecao.refresh_from_db()

        self.assertEqual(pre_selecao.encaminhada_por, self.usuario)
        self.assertEqual(pre_selecao.encaminhada_em, encaminhada_em)
        self.assertIsNotNone(pre_selecao.encerrada_em)

    def test_unicidade_de_inscricao_em_aberto(self):
        inscricao = self._criar_inscricao()
        self._criar_por_inscricao(inscricao=inscricao)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self._criar_por_inscricao(inscricao=inscricao)

    def test_unicidade_de_atendimento_em_aberto(self):
        atendimento = self._criar_atendimento()
        self._criar_por_atendimento(
            atendimento=atendimento,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self._criar_por_atendimento(
                atendimento=atendimento,
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            )

    def test_unicidade_de_pessoa_resolvida_abrange_origens_distintas(self):
        pessoa = Pessoa.objects.create(nome='Pessoa em duas origens')
        inscricao = self._criar_inscricao(pessoa=pessoa)
        self._criar_por_inscricao(
            inscricao=inscricao,
            pessoa_resolvida=pessoa,
        )
        atendimento = self._criar_atendimento(pessoa=pessoa)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self._criar_por_atendimento(
                atendimento=atendimento,
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
                pessoa_resolvida=pessoa,
            )

    def test_mesma_pessoa_pode_ser_preselecionada_em_encontros_distintos(self):
        pessoa = Pessoa.objects.create(nome='Pessoa em dois Encontros')
        primeiro = self._criar_por_atendimento(
            atendimento=self._criar_atendimento(pessoa=pessoa),
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa_resolvida=pessoa,
        )
        outro_encontro = make_encontro()
        outro_pre = self._criar_pre_encontro(outro_encontro)
        segundo = self._criar_por_atendimento(
            atendimento=self._criar_atendimento(
                pre_encontro=outro_pre,
                pessoa=pessoa,
            ),
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa_resolvida=pessoa,
            encontro=outro_encontro,
        )

        self.assertNotEqual(primeiro.encontro_id, segundo.encontro_id)

    def test_encerramento_permite_nova_preselecao_sem_apagar_historico(self):
        inscricao = self._criar_inscricao()
        anterior = self._criar_por_inscricao(inscricao=inscricao)
        anterior.estado = PreSelecaoEncontrista.Estado.ENCERRADA
        anterior.encerrada_por = self.usuario
        anterior.encerrada_em = timezone.now()
        anterior.save()

        nova = self._criar_por_inscricao(inscricao=inscricao)

        self.assertNotEqual(anterior.pk, nova.pk)
        self.assertEqual(
            PreSelecaoEncontrista.objects.filter(
                encontro=self.encontro,
                inscricao_origem=inscricao,
            ).count(),
            2,
        )

    def test_referencias_historicas_usam_protect(self):
        campos = (
            'encontro',
            'inscricao_origem',
            'atendimento_origem',
            'pessoa_resolvida',
            'registrada_por',
            'encaminhada_por',
            'encerrada_por',
        )
        for nome in campos:
            with self.subTest(campo=nome):
                self.assertIs(
                    PreSelecaoEncontrista._meta.get_field(nome).remote_field.on_delete,
                    models.PROTECT,
                )

        inscricao = self._criar_inscricao()
        self._criar_por_inscricao(inscricao=inscricao)
        with self.assertRaises(ProtectedError):
            inscricao.delete()

    def test_persistencia_nao_produz_efeitos_operacionais(self):
        atendimento = self._criar_atendimento()
        contagens_antes = {
            'pessoas': Pessoa.objects.count(),
            'inscricoes': InscricaoEncontro.objects.count(),
            'convites': ConviteEncontro.objects.count(),
            'oportunidades': OportunidadeConviteEncontro.objects.count(),
            'participacoes': ParticipacaoEncontro.objects.count(),
            'vinculos_legados': VinculoEncontroLegado.objects.count(),
        }

        self._criar_por_atendimento(
            atendimento=atendimento,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
        )

        self.assertEqual(Pessoa.objects.count(), contagens_antes['pessoas'])
        self.assertEqual(
            InscricaoEncontro.objects.count(),
            contagens_antes['inscricoes'],
        )
        self.assertEqual(ConviteEncontro.objects.count(), contagens_antes['convites'])
        self.assertEqual(
            OportunidadeConviteEncontro.objects.count(),
            contagens_antes['oportunidades'],
        )
        self.assertEqual(
            ParticipacaoEncontro.objects.count(),
            contagens_antes['participacoes'],
        )
        self.assertEqual(
            VinculoEncontroLegado.objects.count(),
            contagens_antes['vinculos_legados'],
        )

    def test_model_nao_persiste_copias_de_dados_pessoais(self):
        nomes = {campo.name for campo in PreSelecaoEncontrista._meta.fields}

        self.assertTrue({'encontro', 'pessoa_resolvida'} <= nomes)
        self.assertFalse({'cpf', 'telefone', 'nome', 'email'} & nomes)

    def test_indices_estruturais_possuem_nomes_estaveis(self):
        nomes = {indice.name for indice in PreSelecaoEncontrista._meta.indexes}

        self.assertEqual(nomes, {
            'pre_sel_enc_estado_idx',
            'pre_sel_pessoa_estado_idx',
            'pre_sel_registrada_idx',
        })

    def test_migration_e_somente_expansiva_e_sem_operacao_de_dados(self):
        modulo = import_module('core.migrations.0050_preselecaoencontrista')

        self.assertEqual(len(modulo.Migration.operations), 1)
        self.assertIsInstance(
            modulo.Migration.operations[0],
            migrations.CreateModel,
        )
        self.assertFalse(any(
            isinstance(operacao, migrations.RunPython)
            for operacao in modulo.Migration.operations
        ))
