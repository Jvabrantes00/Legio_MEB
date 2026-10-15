import os
from datetime import date, datetime, timedelta, timezone as datetime_timezone
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from core.models import (
    AtendimentoPreEncontro,
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    DadosDeclaradosInscricao,
    DiaEncontro,
    InscricaoEncontro,
    PerfilAlpinista,
    Pessoa,
)
from core.services.encontro_workspace import (
    SituacaoCandidatoWorkspace,
    listar_encontristas,
    situacao_candidato,
)
from core.services.inscricoes_encontro import _idade_em as calcular_idade
from core.tests.factories import make_encontro


SEED_ENV = {'SIA_ENVIRONMENT': 'development'}


@override_settings(DEBUG=True)
class SeedInscricoesWorkspaceCommandTests(TestCase):
    def setUp(self):
        self.momento = datetime(
            2030, 1, 10, 12, tzinfo=datetime_timezone.utc,
        )
        self.encontro = make_encontro()
        ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=30,
            idade_minima=16,
            idade_maxima=22,
            inscricoes_abrem_em=self.momento - timedelta(days=10),
            inscricoes_encerram_em=self.momento - timedelta(days=5),
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

    def _run(self, encontro=None, **options):
        output = StringIO()
        with patch.dict(os.environ, SEED_ENV, clear=False):
            call_command(
                'seed_inscricoes_workspace',
                encontro_id=(encontro or self.encontro).pk,
                stdout=output,
                **options,
            )
        return output.getvalue()

    def _data_futura(self, anos):
        hoje = timezone.localdate()
        try:
            return hoje.replace(year=hoje.year + anos)
        except ValueError:
            return hoje.replace(year=hoje.year + anos, day=28)

    def _encontro_futuro(self, *, idade_minima=5, idade_maxima=20):
        encontro = make_encontro()
        agora = timezone.now()
        configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=encontro,
            capacidade=30,
            idade_minima=idade_minima,
            idade_maxima=idade_maxima,
            inscricoes_abrem_em=agora - timedelta(days=1),
            inscricoes_encerram_em=agora + timedelta(days=1),
        )
        primeiro_dia = self._data_futura(10)
        calendario = CalendarioEncontro.objects.create(
            encontro=encontro,
            versao=1,
            vigente=True,
            oficializado_em=agora,
        )
        DiaEncontro.objects.create(
            calendario=calendario,
            ordem=1,
            data=primeiro_dia,
        )
        return encontro, configuracao, primeiro_dia

    def test_cria_inscricoes_nao_verificadas_pelo_fluxo_canonico(self):
        output = self._run(quantidade=5)

        inscricoes = InscricaoEncontro.objects.filter(encontro=self.encontro)
        self.assertEqual(inscricoes.count(), 5)
        self.assertFalse(inscricoes.exclude(status=InscricaoEncontro.Status.ENVIADA).exists())
        self.assertFalse(inscricoes.exclude(origem=InscricaoEncontro.Origem.PUBLICA).exists())
        self.assertFalse(inscricoes.exclude(pessoa__isnull=True).exists())
        self.assertEqual(Pessoa.objects.count(), 0)
        self.assertEqual(PerfilAlpinista.objects.count(), 0)
        self.assertEqual(AtendimentoPreEncontro.objects.count(), 0)
        candidatos = listar_encontristas(encontro=self.encontro)
        self.assertEqual(len(candidatos), 5)
        self.assertTrue(all(
            situacao_candidato(item) == SituacaoCandidatoWorkspace.INSCRITO
            for item in candidatos
        ))
        self.assertIn('Criadas: 5', output)
        self.assertIn('Nenhuma Pessoa criada.', output)

    def test_reexecucao_e_idempotente(self):
        self._run(quantidade=3)
        output = self._run(quantidade=3)

        self.assertEqual(
            InscricaoEncontro.objects.filter(encontro=self.encontro).count(),
            3,
        )
        self.assertIn('Criadas: 0', output)
        self.assertIn('Já existentes: 3', output)

    def test_encontro_futuro_limita_nascimento_a_hoje_sem_quebrar_idade(self):
        encontro, configuracao, primeiro_dia = self._encontro_futuro()

        self._run(encontro=encontro, quantidade=25)

        nascimentos = list(
            DadosDeclaradosInscricao.objects
            .filter(inscricao__encontro=encontro)
            .values_list('data_nascimento', flat=True)
        )
        self.assertEqual(len(nascimentos), 25)
        self.assertTrue(all(
            nascimento <= timezone.localdate()
            for nascimento in nascimentos
        ))
        self.assertTrue(all(
            configuracao.idade_minima
            <= calcular_idade(nascimento, primeiro_dia)
            <= configuracao.idade_maxima
            for nascimento in nascimentos
        ))
        self.assertGreater(len(set(nascimentos)), 1)

    def test_configuracao_sem_intersecao_de_datas_falha_sem_escrever(self):
        encontro, _, _ = self._encontro_futuro(
            idade_minima=0,
            idade_maxima=1,
        )

        with self.assertRaisesMessage(
            CommandError,
            'Não existe data de nascimento válida',
        ):
            self._run(encontro=encontro, quantidade=1)

        self.assertFalse(
            InscricaoEncontro.objects.filter(encontro=encontro).exists()
        )

    def test_encontro_inexistente_e_configuracao_incompleta_falham(self):
        with patch.dict(os.environ, SEED_ENV, clear=False):
            with self.assertRaisesMessage(CommandError, 'não encontrado'):
                call_command(
                    'seed_inscricoes_workspace',
                    encontro_id=999999,
                )
        sem_configuracao = make_encontro()
        with patch.dict(os.environ, SEED_ENV, clear=False):
            with self.assertRaisesMessage(CommandError, 'não possui'):
                call_command(
                    'seed_inscricoes_workspace',
                    encontro_id=sem_configuracao.pk,
                )

    def test_limpar_remove_apenas_seed_e_preserva_inscricao_real(self):
        self._run(quantidade=2)
        real = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            origem=InscricaoEncontro.Origem.PUBLICA,
        )
        DadosDeclaradosInscricao.objects.create(
            inscricao=real,
            nome_completo='Inscrição Real Preservada',
            data_nascimento=date(2000, 1, 1),
            email='real@example.org',
            telefone_whatsapp='61000000000',
            cep='70000-000',
            logradouro='Rua Real',
            numero='1',
            bairro='Centro',
            cidade='Brasília',
            uf='DF',
            como_conheceu=DadosDeclaradosInscricao.ComoConheceu.INDICACAO,
        )

        output = self._run(limpar=True)

        self.assertTrue(InscricaoEncontro.objects.filter(pk=real.pk).exists())
        self.assertEqual(
            InscricaoEncontro.objects.filter(encontro=self.encontro).count(),
            1,
        )
        self.assertIn('Removidas: 2', output)

    def test_limpar_preserva_seed_que_avancou_para_pessoa(self):
        self._run(quantidade=1)
        inscricao = InscricaoEncontro.objects.get(encontro=self.encontro)
        inscricao.pessoa = Pessoa.objects.create(nome='Pessoa resolvida')
        inscricao.save(update_fields=['pessoa'])

        output = self._run(limpar=True)

        self.assertTrue(InscricaoEncontro.objects.filter(pk=inscricao.pk).exists())
        self.assertIn('Ignoradas por avanço operacional: 1', output)

    def test_command_falha_fechado_fora_do_desenvolvimento(self):
        with override_settings(DEBUG=False), patch.dict(
            os.environ,
            SEED_ENV,
            clear=False,
        ):
            with self.assertRaisesMessage(CommandError, 'bloqueado'):
                call_command(
                    'seed_inscricoes_workspace',
                    encontro_id=self.encontro.pk,
                )
