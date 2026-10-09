import json
from datetime import date
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    CorrespondenciaCadastralInscricao,
    DadosCuidadoInscricao,
    DadosDeclaradosInscricao,
    DadosSaudePessoa,
    EnderecoPessoa,
    EventoAuditoriaEncontro,
    Grupo,
    InscricaoEncontro,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
    ResponsavelDeclaradoInscricao,
    TelefonePessoa,
    VinculoConjugal,
    VinculoGrupo,
)
from core.roles import SiaRole
from core.services import resolucao_cadastral as services
from core.services.resolucao_cadastral import (
    ErroResolucaoCadastral,
    aceitar_correspondencia_cadastral,
    aplicar_dados_declarados,
    criar_pessoa_da_inscricao,
    gerar_sugestoes_cadastrais,
    rejeitar_correspondencia_cadastral,
)
from core.tests.factories import make_encontro


class ResolucaoCadastralServiceTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro()
        self.usuario = self.criar_usuario('fichas', SiaRole.FICHAS)
        self.sem_papel = self.criar_usuario('sem-papel')

    def criar_usuario(self, username, role=None):
        usuario = get_user_model().objects.create_user(
            username=username,
            password='senha-exclusiva-de-teste',
        )
        if role is not None:
            grupo, _ = Group.objects.get_or_create(name=role.value)
            usuario.groups.add(grupo)
        return usuario

    def criar_inscricao(self, **dados_overrides):
        inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            origem=InscricaoEncontro.Origem.PUBLICA,
        )
        dados = {
            'inscricao': inscricao,
            'nome_completo': 'Pessoa Declarada',
            'apelido': 'Declarada',
            'data_nascimento': date(2000, 1, 2),
            'cpf': '52998224725',
            'email': 'declarada@example.test',
            'telefone_whatsapp': '61999990000',
            'cep': '70000-000',
            'logradouro': 'Rua Declarada',
            'numero': '10',
            'complemento': 'Casa',
            'bairro': 'Bairro',
            'cidade': 'Brasília',
            'uf': 'DF',
            'como_conheceu': DadosDeclaradosInscricao.ComoConheceu.INDICACAO,
            'batismo': DadosDeclaradosInscricao.Sacramento.SIM,
            'primeira_comunhao': DadosDeclaradosInscricao.Sacramento.NAO,
            'crisma': DadosDeclaradosInscricao.Sacramento.NAO_SEI,
            'snapshot_schema_version': 1,
            'snapshot_atual': {
                'schema_version': 1,
                'marcador': 'snapshot-declarado-imutavel',
            },
        }
        dados.update(dados_overrides)
        DadosDeclaradosInscricao.objects.create(**dados)
        return inscricao

    def criar_pessoa(self, **overrides):
        dados = {
            'nome': 'Pessoa Candidata',
            'data_nascimento': date(1999, 5, 6),
            'cpf': '52998224725',
            'email': 'canonica@example.test',
        }
        dados.update(overrides)
        return Pessoa.objects.create(**dados)

    def sugerir(self, inscricao=None, pessoa=None):
        inscricao = inscricao or self.criar_inscricao()
        pessoa = pessoa or self.criar_pessoa()
        correspondencias = gerar_sugestoes_cadastrais(
            usuario=self.usuario,
            inscricao=inscricao,
        )
        return inscricao, pessoa, correspondencias.get()

    def test_cpf_exato_gera_sugestao_sem_autoassociar(self):
        inscricao = self.criar_inscricao()
        pessoa = self.criar_pessoa()

        correspondencias = gerar_sugestoes_cadastrais(
            usuario=self.usuario,
            inscricao=inscricao,
        )
        inscricao.refresh_from_db()

        correspondencia = correspondencias.get()
        self.assertEqual(correspondencia.pessoa_candidata, pessoa)
        self.assertEqual(correspondencia.origem_sinal, 'cpf_exato')
        self.assertEqual(
            correspondencia.status,
            CorrespondenciaCadastralInscricao.Status.SUGERIDA,
        )
        self.assertIsNone(inscricao.pessoa_id)

    def test_geracao_e_idempotente_e_preserva_decisao_humana(self):
        inscricao, _, correspondencia = self.sugerir()
        rejeitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=inscricao,
            correspondencia=correspondencia,
        )

        gerar_sugestoes_cadastrais(
            usuario=self.usuario,
            inscricao=inscricao,
        )
        gerar_sugestoes_cadastrais(
            usuario=self.usuario,
            inscricao=inscricao,
        )
        correspondencia.refresh_from_db()

        self.assertEqual(
            CorrespondenciaCadastralInscricao.objects.count(),
            1,
        )
        self.assertEqual(
            correspondencia.status,
            CorrespondenciaCadastralInscricao.Status.REJEITADA,
        )

    def test_cpf_do_responsavel_nao_gera_candidata(self):
        inscricao = self.criar_inscricao(cpf=None)
        pessoa = self.criar_pessoa(cpf='11144477735')
        ResponsavelDeclaradoInscricao.objects.create(
            inscricao=inscricao,
            nome_completo='Responsável Declarado',
            cpf=pessoa.cpf,
            parentesco='Mãe',
            telefone_whatsapp='61988880000',
        )

        correspondencias = gerar_sugestoes_cadastrais(
            usuario=self.usuario,
            inscricao=inscricao,
        )

        self.assertFalse(correspondencias.exists())

    def test_aceite_associa_e_audita_sem_copiar_ficha(self):
        inscricao, pessoa, correspondencia = self.sugerir()
        nome_original = pessoa.nome
        email_original = pessoa.email

        aceita = aceitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=inscricao,
            correspondencia=correspondencia,
        )
        inscricao.refresh_from_db()
        pessoa.refresh_from_db()

        self.assertEqual(inscricao.pessoa, pessoa)
        self.assertEqual(aceita.status, aceita.Status.ACEITA)
        self.assertEqual(aceita.decidida_por, self.usuario)
        self.assertIsNotNone(aceita.decidida_em)
        self.assertEqual(pessoa.nome, nome_original)
        self.assertEqual(pessoa.email, email_original)
        self.assertEqual(EventoAuditoriaEncontro.objects.count(), 2)

    def test_aceite_repetido_da_mesma_decisao_e_noop(self):
        inscricao, _, correspondencia = self.sugerir()
        aceitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=inscricao,
            correspondencia=correspondencia,
        )
        eventos = EventoAuditoriaEncontro.objects.count()

        aceitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=inscricao,
            correspondencia=correspondencia,
        )
        gerar_sugestoes_cadastrais(
            usuario=self.usuario,
            inscricao=inscricao,
        )
        correspondencia.refresh_from_db()

        self.assertEqual(EventoAuditoriaEncontro.objects.count(), eventos)
        self.assertEqual(
            correspondencia.status,
            CorrespondenciaCadastralInscricao.Status.ACEITA,
        )

    def test_apenas_uma_correspondencia_pode_ser_aceita(self):
        inscricao, _, primeira = self.sugerir()
        segunda_pessoa = self.criar_pessoa(
            cpf='11144477735',
            email='segunda@example.test',
        )
        segunda = CorrespondenciaCadastralInscricao.objects.create(
            inscricao=inscricao,
            pessoa_candidata=segunda_pessoa,
            origem_sinal='revisao_manual',
        )
        aceitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=inscricao,
            correspondencia=primeira,
        )

        with self.assertRaises(ErroResolucaoCadastral):
            aceitar_correspondencia_cadastral(
                usuario=self.usuario,
                inscricao=inscricao,
                correspondencia=segunda,
            )

        segunda.refresh_from_db()
        self.assertEqual(
            segunda.status,
            CorrespondenciaCadastralInscricao.Status.SUGERIDA,
        )

    def test_decisoes_incompativeis_sao_rejeitadas(self):
        inscricao, _, correspondencia = self.sugerir()
        rejeitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=inscricao,
            correspondencia=correspondencia,
        )

        with self.assertRaises(ErroResolucaoCadastral):
            aceitar_correspondencia_cadastral(
                usuario=self.usuario,
                inscricao=inscricao,
                correspondencia=correspondencia,
            )

        outra_inscricao, _, outra = self.sugerir(
            inscricao=self.criar_inscricao(
                cpf='11144477735',
                email='outra@example.test',
            ),
            pessoa=self.criar_pessoa(
                cpf='11144477735',
                email='outra-canonica@example.test',
            ),
        )
        aceitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=outra_inscricao,
            correspondencia=outra,
        )
        with self.assertRaises(ErroResolucaoCadastral):
            rejeitar_correspondencia_cadastral(
                usuario=self.usuario,
                inscricao=outra_inscricao,
                correspondencia=outra,
            )

    def test_rejeicao_preserva_evidencia_sem_associar_e_e_idempotente(self):
        inscricao, _, correspondencia = self.sugerir()
        decidida = rejeitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=inscricao,
            correspondencia=correspondencia,
        )
        instante = decidida.decidida_em
        eventos = EventoAuditoriaEncontro.objects.count()

        novamente = rejeitar_correspondencia_cadastral(
            usuario=self.usuario,
            inscricao=inscricao,
            correspondencia=correspondencia,
        )
        inscricao.refresh_from_db()

        self.assertIsNone(inscricao.pessoa_id)
        self.assertEqual(novamente.decidida_em, instante)
        self.assertTrue(
            CorrespondenciaCadastralInscricao.objects.filter(
                pk=correspondencia.pk,
            ).exists(),
        )
        self.assertEqual(EventoAuditoriaEncontro.objects.count(), eventos)

    def test_conflito_pessoa_encontro_nao_faz_merge_ou_exclusao(self):
        pessoa = self.criar_pessoa()
        existente = self.criar_inscricao(email='existente@example.test')
        existente.pessoa = pessoa
        existente.save(update_fields=['pessoa'])
        nova = self.criar_inscricao(email='nova@example.test')
        correspondencia = CorrespondenciaCadastralInscricao.objects.create(
            inscricao=nova,
            pessoa_candidata=pessoa,
            origem_sinal='cpf_exato',
        )

        with self.assertRaises(ErroResolucaoCadastral) as contexto:
            aceitar_correspondencia_cadastral(
                usuario=self.usuario,
                inscricao=nova,
                correspondencia=correspondencia,
            )

        self.assertIn('conflito', str(contexto.exception).lower())
        self.assertEqual(InscricaoEncontro.objects.count(), 2)
        nova.refresh_from_db()
        self.assertIsNone(nova.pessoa_id)

    def test_aceite_faz_rollback_se_auditoria_falhar(self):
        inscricao, _, correspondencia = self.sugerir()

        with patch.object(
            services,
            'registrar_evento_auditoria_encontro',
            side_effect=RuntimeError('falha controlada'),
        ), self.assertRaisesRegex(RuntimeError, 'falha controlada'):
            aceitar_correspondencia_cadastral(
                usuario=self.usuario,
                inscricao=inscricao,
                correspondencia=correspondencia,
            )

        inscricao.refresh_from_db()
        correspondencia.refresh_from_db()
        self.assertIsNone(inscricao.pessoa_id)
        self.assertEqual(
            correspondencia.status,
            CorrespondenciaCadastralInscricao.Status.SUGERIDA,
        )

    def test_criacao_de_pessoa_e_explicita_atomica_e_sem_efeitos_colaterais(self):
        inscricao = self.criar_inscricao()

        pessoa = criar_pessoa_da_inscricao(
            usuario=self.usuario,
            inscricao=inscricao,
            campos={
                'nome',
                'data_nascimento',
                'cpf',
                'email',
                'telefone',
                'endereco',
                'sacramentos',
            },
        )
        inscricao.refresh_from_db()

        self.assertEqual(inscricao.pessoa, pessoa)
        self.assertEqual(pessoa.nome, 'Pessoa Declarada')
        self.assertTrue(pessoa.telefones.filter(numero='61999990000').exists())
        self.assertEqual(pessoa.endereco.estado, 'DF')
        self.assertTrue(pessoa.batismo)
        self.assertFalse(pessoa.primeira_comunhao)
        self.assertIsNone(pessoa.crisma)
        self.assertFalse(PerfilAlpinista.objects.exists())
        self.assertFalse(ParticipacaoEncontro.objects.exists())
        self.assertFalse(Grupo.objects.exists())
        self.assertFalse(VinculoGrupo.objects.exists())
        self.assertFalse(VinculoConjugal.objects.exists())

    def test_criacao_exige_nome_na_selecao_e_nao_e_automatica(self):
        inscricao = self.criar_inscricao()

        gerar_sugestoes_cadastrais(
            usuario=self.usuario,
            inscricao=inscricao,
        )
        self.assertFalse(Pessoa.objects.exists())
        with self.assertRaises(ErroResolucaoCadastral):
            criar_pessoa_da_inscricao(
                usuario=self.usuario,
                inscricao=inscricao,
                campos={'email'},
            )

    def test_criacao_de_pessoa_reverte_se_auditoria_falhar(self):
        inscricao = self.criar_inscricao()

        with patch.object(
            services,
            'registrar_evento_auditoria_encontro',
            side_effect=RuntimeError('falha controlada'),
        ), self.assertRaisesRegex(RuntimeError, 'falha controlada'):
            criar_pessoa_da_inscricao(
                usuario=self.usuario,
                inscricao=inscricao,
                campos={'nome', 'email'},
            )

        inscricao.refresh_from_db()
        self.assertIsNone(inscricao.pessoa_id)
        self.assertFalse(Pessoa.objects.exists())

    def test_aplicacao_seletiva_preserva_nao_selecionados_e_snapshot(self):
        inscricao = self.criar_inscricao()
        snapshot = inscricao.dados_declarados.snapshot_atual.copy()
        pessoa = self.criar_pessoa(
            nome='Nome Canônico',
            email='email-canonico@example.test',
        )
        TelefonePessoa.objects.create(
            pessoa=pessoa,
            numero='61000000000',
        )
        inscricao.pessoa = pessoa
        inscricao.save(update_fields=['pessoa'])

        resultado = aplicar_dados_declarados(
            usuario=self.usuario,
            inscricao=inscricao,
            campos={'nome'},
        )
        pessoa.refresh_from_db()
        inscricao.dados_declarados.refresh_from_db()

        self.assertEqual(resultado.campos_alterados, ('nome',))
        self.assertEqual(pessoa.nome, 'Pessoa Declarada')
        self.assertEqual(pessoa.email, 'email-canonico@example.test')
        self.assertEqual(pessoa.telefones.count(), 1)
        self.assertEqual(inscricao.dados_declarados.snapshot_atual, snapshot)

    def test_ausencia_declarada_nao_apaga_valor_canonico(self):
        inscricao = self.criar_inscricao(email='')
        pessoa = self.criar_pessoa(email='preservado@example.test')
        inscricao.pessoa = pessoa
        inscricao.save(update_fields=['pessoa'])

        resultado = aplicar_dados_declarados(
            usuario=self.usuario,
            inscricao=inscricao,
            campos={'email'},
        )
        pessoa.refresh_from_db()

        self.assertEqual(resultado.campos_alterados, ())
        self.assertEqual(pessoa.email, 'preservado@example.test')

    def test_allowlist_rejeita_campo_arbitrario(self):
        inscricao = self.criar_inscricao()
        pessoa = self.criar_pessoa()
        inscricao.pessoa = pessoa
        inscricao.save(update_fields=['pessoa'])

        with self.assertRaises(ErroResolucaoCadastral) as contexto:
            aplicar_dados_declarados(
                usuario=self.usuario,
                inscricao=inscricao,
                campos={'is_superuser'},
            )
        self.assertIn('campos', contexto.exception.message_dict)

    def test_cuidado_compativel_e_aplicado_sem_pii_na_auditoria(self):
        inscricao = self.criar_inscricao()
        DadosCuidadoInscricao.objects.create(
            inscricao=inscricao,
            alergias='Alergia altamente específica',
            medicamentos='Medicamento altamente específico',
            neurodivergencia_condicao='Condição altamente específica',
        )
        pessoa = self.criar_pessoa()
        inscricao.pessoa = pessoa
        inscricao.save(update_fields=['pessoa'])

        aplicar_dados_declarados(
            usuario=self.usuario,
            inscricao=inscricao,
            campos={'alergias', 'medicamentos', 'neurodivergencia'},
        )

        saude = DadosSaudePessoa.objects.get(pessoa=pessoa)
        self.assertEqual(saude.alergias, 'Alergia altamente específica')
        evento = EventoAuditoriaEncontro.objects.get(
            fato='resolucao_cadastral.campos_aplicados',
        )
        auditoria = json.dumps({
            'anterior': evento.valor_anterior,
            'novo': evento.valor_novo,
        })
        self.assertNotIn('altamente específica', auditoria)
        self.assertIn('alergias', auditoria)

    def test_contato_de_emergencia_nao_vira_responsavel_canonico(self):
        inscricao = self.criar_inscricao()
        ResponsavelDeclaradoInscricao.objects.create(
            inscricao=inscricao,
            nome_completo='Contato Adulto',
            cpf=None,
            parentesco='Amigo',
            telefone_whatsapp='61977770000',
        )

        pessoa = criar_pessoa_da_inscricao(
            usuario=self.usuario,
            inscricao=inscricao,
            campos={'nome'},
        )

        self.assertFalse(pessoa.responsaveis.exists())
        self.assertEqual(Pessoa.objects.count(), 1)

    def test_services_aplicam_default_deny(self):
        inscricao = self.criar_inscricao()

        with self.assertRaises(PermissionDenied):
            gerar_sugestoes_cadastrais(
                usuario=self.sem_papel,
                inscricao=inscricao,
            )
