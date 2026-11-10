from datetime import date, datetime, time, timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone

from core.models import (
    AtendimentoPreEncontro,
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DiaEncontro,
    EntregaConviteEncontro,
    InscricaoEncontro,
    OportunidadeConviteEncontro,
    OutboxEntregaConvite,
    ParticipacaoEncontro,
    Pessoa,
    PreEncontro,
    PreSelecaoEncontrista,
)
from core.roles import SiaRole
from core.serializers import CandidatoCampanhaSerializer
from core.services import campanhas_convites as services
from core.tests.factories import make_encontro


class CampanhasPreSelecoesTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username='fichas-campanhas-preselecoes',
        )
        grupo, _ = Group.objects.get_or_create(name=SiaRole.FICHAS.value)
        self.usuario.groups.add(grupo)
        self.momento = timezone.make_aware(datetime(2030, 1, 10, 9, 0))
        self.encontro = make_encontro(data_referencia=date(2030, 6, 1))
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=10,
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
        self.pre_encontro = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 5, 1),
            horario=time(14),
            local='Local do Pré-Encontro',
        )

    def _pessoa(self, nome, *, data_nascimento=date(2010, 1, 1), email=None):
        return Pessoa.objects.create(
            nome=nome,
            data_nascimento=data_nascimento,
            email=email,
        )

    def _inscricao(self, pessoa, *, encontro=None, status=None):
        return InscricaoEncontro.objects.create(
            encontro=encontro or self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.PUBLICA,
            status=status or InscricaoEncontro.Status.ENVIADA,
            cancelada_em=(
                self.momento
                if status == InscricaoEncontro.Status.CANCELADA
                else None
            ),
        )

    def _convite(self, pessoa, *, encontro=None, status=None):
        return ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro or self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=status or ConviteEncontro.Status.CONVIDADO,
        )

    def _atendimento(self, pessoa=None, *, pre_encontro=None, avulso=False):
        dados = {
            'pre_encontro': pre_encontro or self.pre_encontro,
            'pessoa': pessoa,
            'registrado_por': self.usuario,
        }
        if avulso:
            dados.update({
                'nome_informado': 'Origem avulsa preservada',
                'data_nascimento_informada': date(2010, 1, 1),
                'telefone_informado': '61999990000',
            })
        return AtendimentoPreEncontro.objects.create(**dados)

    def _encaminhada(
        self,
        *,
        origem_tipo,
        pessoa,
        inscricao=None,
        atendimento=None,
        encontro=None,
    ):
        return PreSelecaoEncontrista.objects.create(
            encontro=encontro or self.encontro,
            origem_tipo=origem_tipo,
            inscricao_origem=inscricao,
            atendimento_origem=atendimento,
            pessoa_resolvida=pessoa,
            estado=PreSelecaoEncontrista.Estado.ENCAMINHADA,
            registrada_por=self.usuario,
            encaminhada_por=self.usuario,
            encaminhada_em=self.momento,
        )

    def _projetar(self):
        return services.projetar_candidatos(
            usuario=self.usuario,
            encontro=self.encontro,
        )

    def test_inscricao_tradicional_preserva_contrato_e_canais(self):
        pessoa = self._pessoa('Pessoa tradicional', email='pessoa@example.test')
        inscricao = self._inscricao(pessoa)
        convite = self._convite(pessoa)

        candidato = self._projetar().candidatos[0]
        dados = candidato.as_dict()

        self.assertEqual(candidato.pessoa, pessoa)
        self.assertEqual(candidato.inscricao, inscricao)
        self.assertEqual(candidato.convite, convite)
        self.assertIsNone(candidato.preselecao)
        self.assertEqual(dados['inscricao_id'], inscricao.pk)
        self.assertEqual(dados['origem_tipo'], 'INSCRICAO')
        self.assertIsNone(dados['preselecao_id'])
        self.assertEqual(dados['canais_disponiveis'], ['EMAIL'])

    def test_inscricoes_invalidas_sem_pessoa_ou_canceladas_nao_aparecem(self):
        pessoa = self._pessoa('Pessoa cancelada')
        self._inscricao(pessoa, status=InscricaoEncontro.Status.CANCELADA)
        self._convite(pessoa)
        InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=None,
            origem=InscricaoEncontro.Origem.PUBLICA,
        )

        self.assertEqual(self._projetar().candidatos, ())

    def test_convite_incompativel_e_elegibilidade_invalida_sao_filtrados(self):
        recusada = self._pessoa('Pessoa recusada')
        self._inscricao(recusada)
        self._convite(recusada, status=ConviteEncontro.Status.RECUSADO)
        inelegivel = self._pessoa(
            'Pessoa inelegível',
            data_nascimento=date(2025, 1, 1),
        )
        self._inscricao(inelegivel)
        self._convite(inelegivel)

        self.assertEqual(self._projetar().candidatos, ())

    def test_participacao_existente_exclui_candidatura(self):
        pessoa = self._pessoa('Pessoa com participação')
        self._inscricao(pessoa)
        convite = self._convite(pessoa)
        ParticipacaoEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            convite=convite,
            resultado=ParticipacaoEncontro.Resultado.FALTOU,
            tipo_encontro=self.encontro.tipo,
        )

        self.assertEqual(self._projetar().candidatos, ())

    def test_preselecao_encaminhada_por_inscricao_e_projetada(self):
        pessoa = self._pessoa('Pessoa encaminhada por inscrição')
        inscricao = self._inscricao(pessoa)
        convite = self._convite(pessoa)
        preselecao = self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.INSCRICAO,
            pessoa=pessoa,
            inscricao=inscricao,
        )

        candidato = self._projetar().candidatos[0]

        self.assertEqual(candidato.inscricao, inscricao)
        self.assertEqual(candidato.preselecao, preselecao)
        self.assertEqual(candidato.convite, convite)
        self.assertEqual(candidato.as_dict()['origem_tipo'], 'INSCRICAO')

    def test_preselecao_encaminhada_por_pessoa_dispensa_inscricao(self):
        pessoa = self._pessoa('Pessoa encaminhada diretamente')
        convite = self._convite(pessoa)
        atendimento = self._atendimento(pessoa)
        preselecao = self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa=pessoa,
            atendimento=atendimento,
        )

        candidato = self._projetar().candidatos[0]
        dados = candidato.as_dict()

        self.assertIsNone(candidato.inscricao)
        self.assertEqual(candidato.preselecao, preselecao)
        self.assertEqual(candidato.convite, convite)
        self.assertIsNone(dados['inscricao_id'])
        self.assertEqual(dados['origem_tipo'], 'PESSOA')
        self.assertEqual(dados['preselecao_id'], preselecao.pk)

    def test_preselecao_avulsa_regularizada_preserva_origem(self):
        pessoa = self._pessoa('Pessoa avulsa regularizada')
        convite = self._convite(pessoa)
        atendimento = self._atendimento(pessoa, avulso=True)
        preselecao = self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            pessoa=pessoa,
            atendimento=atendimento,
        )

        candidato = self._projetar().candidatos[0]
        dados = candidato.as_dict()

        self.assertEqual(candidato.convite, convite)
        self.assertIsNone(candidato.inscricao)
        self.assertEqual(dados['origem_tipo'], 'AVULSO')
        self.assertEqual(dados['preselecao_id'], preselecao.pk)

    def test_estados_nao_encaminhados_e_identidade_pendente_nao_aparecem(self):
        pessoa = self._pessoa('Pessoa ainda pré-selecionada')
        atendimento = self._atendimento(pessoa)
        self._convite(pessoa)
        PreSelecaoEncontrista.objects.create(
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            atendimento_origem=atendimento,
            pessoa_resolvida=pessoa,
            registrada_por=self.usuario,
        )
        atendimento_avulso = self._atendimento(avulso=True)
        PreSelecaoEncontrista.objects.create(
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            atendimento_origem=atendimento_avulso,
            pessoa_resolvida=None,
            estado=PreSelecaoEncontrista.Estado.ENCAMINHADA,
            registrada_por=self.usuario,
            encaminhada_por=self.usuario,
            encaminhada_em=self.momento,
        )
        encerrada = self._pessoa('Pessoa com pré-seleção encerrada')
        atendimento_encerrado = self._atendimento(encerrada)
        self._convite(encerrada)
        PreSelecaoEncontrista.objects.create(
            encontro=self.encontro,
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            atendimento_origem=atendimento_encerrado,
            pessoa_resolvida=encerrada,
            estado=PreSelecaoEncontrista.Estado.ENCERRADA,
            registrada_por=self.usuario,
            encerrada_por=self.usuario,
            encerrada_em=self.momento,
        )

        self.assertEqual(self._projetar().candidatos, ())

    def test_origem_de_outro_encontro_e_identidade_divergente_sao_ignoradas(self):
        outro = make_encontro(data_referencia=date(2030, 7, 1))
        outro_pre = PreEncontro.objects.create(
            encontro=outro,
            data=date(2030, 6, 1),
            horario=time(14),
            local='Outro local',
        )
        pessoa = self._pessoa('Pessoa da origem divergente')
        outra_pessoa = self._pessoa('Identidade divergente')
        self._convite(outra_pessoa)
        atendimento = self._atendimento(pessoa, pre_encontro=outro_pre)
        self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa=outra_pessoa,
            atendimento=atendimento,
        )

        self.assertEqual(self._projetar().candidatos, ())

    def test_sem_convite_ou_sem_elegibilidade_nao_cria_candidato(self):
        sem_convite = self._pessoa('Pessoa sem convite')
        atendimento = self._atendimento(sem_convite)
        self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa=sem_convite,
            atendimento=atendimento,
        )
        nao_avaliavel = self._pessoa(
            'Pessoa não avaliável',
            data_nascimento=None,
        )
        self._convite(nao_avaliavel)
        atendimento_sem_data = self._atendimento(nao_avaliavel)
        self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa=nao_avaliavel,
            atendimento=atendimento_sem_data,
        )

        self.assertEqual(self._projetar().candidatos, ())
        self.assertEqual(ConviteEncontro.objects.count(), 1)

    def test_deduplica_por_pessoa_preservando_as_duas_referencias(self):
        pessoa = self._pessoa('Pessoa nas duas fontes')
        inscricao = self._inscricao(pessoa)
        convite = self._convite(pessoa)
        atendimento = self._atendimento(pessoa)
        preselecao = self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa=pessoa,
            atendimento=atendimento,
        )

        candidatos = self._projetar().candidatos
        dados = candidatos[0].as_dict()

        self.assertEqual(len(candidatos), 1)
        self.assertEqual(candidatos[0].convite, convite)
        self.assertEqual(dados['inscricao_id'], inscricao.pk)
        self.assertEqual(dados['preselecao_id'], preselecao.pk)
        self.assertEqual(dados['origem_tipo'], 'PESSOA')

    def test_ordenacao_por_pessoa_nao_representa_prioridade(self):
        pessoas = [
            self._pessoa('Segunda pessoa'),
            self._pessoa('Primeira pessoa'),
        ]
        for pessoa in reversed(pessoas):
            self._convite(pessoa)
            atendimento = self._atendimento(pessoa)
            self._encaminhada(
                origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
                pessoa=pessoa,
                atendimento=atendimento,
            )

        projecao = self._projetar()
        dados = projecao.as_dict()

        self.assertEqual(
            [item.pessoa.pk for item in projecao.candidatos],
            sorted(pessoa.pk for pessoa in pessoas),
        )
        self.assertTrue(dados['sem_prioridade'])
        self.assertFalse(dados['ordenacao_representa_prioridade'])
        self.assertTrue(all('posicao' not in item for item in dados['candidatos']))

    def test_serializer_expoe_contrato_d25_a_sem_pii(self):
        pessoa = self._pessoa('Pessoa serializada')
        convite = self._convite(pessoa)
        atendimento = self._atendimento(pessoa, avulso=True)
        preselecao = self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.AVULSO,
            pessoa=pessoa,
            atendimento=atendimento,
        )
        candidato = self._projetar().candidatos[0]

        dados = CandidatoCampanhaSerializer(candidato.as_dict()).data

        self.assertIsNone(dados['inscricao_id'])
        self.assertEqual(dados['preselecao_id'], preselecao.pk)
        self.assertEqual(dados['origem_tipo'], 'AVULSO')
        self.assertEqual(dados['pessoa_id'], pessoa.pk)
        self.assertEqual(dados['convite_id'], convite.pk)
        self.assertFalse({'nome', 'email', 'telefone', 'cpf'} & set(dados))

    def test_projecao_e_somente_leitura_e_nao_produz_efeitos(self):
        pessoa = self._pessoa('Pessoa sem efeitos colaterais')
        convite = self._convite(pessoa)
        atendimento = self._atendimento(pessoa)
        preselecao = self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa=pessoa,
            atendimento=atendimento,
        )
        estado_antes = {
            'convites': ConviteEncontro.objects.count(),
            'inscricoes': InscricaoEncontro.objects.count(),
            'oportunidades': OportunidadeConviteEncontro.objects.count(),
            'outbox': OutboxEntregaConvite.objects.count(),
            'entregas': EntregaConviteEncontro.objects.count(),
            'participacoes': ParticipacaoEncontro.objects.count(),
        }

        self._projetar()

        convite.refresh_from_db()
        preselecao.refresh_from_db()
        self.assertEqual(convite.status, ConviteEncontro.Status.CONVIDADO)
        self.assertEqual(
            preselecao.estado,
            PreSelecaoEncontrista.Estado.ENCAMINHADA,
        )
        self.assertEqual(ConviteEncontro.objects.count(), estado_antes['convites'])
        self.assertEqual(InscricaoEncontro.objects.count(), estado_antes['inscricoes'])
        self.assertEqual(
            OportunidadeConviteEncontro.objects.count(),
            estado_antes['oportunidades'],
        )
        self.assertEqual(OutboxEntregaConvite.objects.count(), estado_antes['outbox'])
        self.assertEqual(EntregaConviteEncontro.objects.count(), estado_antes['entregas'])
        self.assertEqual(
            ParticipacaoEncontro.objects.count(),
            estado_antes['participacoes'],
        )

    def test_lista_de_espera_serializa_preselecao_sem_inscricao(self):
        pessoa = self._pessoa('Pessoa na lista de espera')
        self._convite(pessoa)
        atendimento = self._atendimento(pessoa)
        preselecao = self._encaminhada(
            origem_tipo=PreSelecaoEncontrista.OrigemTipo.PESSOA,
            pessoa=pessoa,
            atendimento=atendimento,
        )
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        pessoa_confirmada = self._pessoa('Pessoa confirmada que ocupa a vaga')
        self._convite(
            pessoa_confirmada,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        dados = services.projetar_lista_espera(
            usuario=self.usuario,
            encontro=self.encontro,
        ).as_dict()

        self.assertTrue(dados['lista_espera_ativa'])
        self.assertEqual(len(dados['candidatos']), 1)
        self.assertIsNone(dados['candidatos'][0]['inscricao_id'])
        self.assertEqual(dados['candidatos'][0]['preselecao_id'], preselecao.pk)
