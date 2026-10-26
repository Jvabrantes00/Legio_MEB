from datetime import date, time, timedelta

from django.contrib.auth.models import Group, User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    Alpinista,
    AtendimentoPreEncontro,
    CalendarioEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DadosDeclaradosInscricao,
    DecisaoVagaPreEncontro,
    DiaEncontro,
    Encontro,
    EquipeEncontro,
    FuncaoEncontro,
    InscricaoEncontro,
    Pessoa,
    PreEncontro,
    RoleEquipeEncontro,
    SessaoFormativa,
    TelefonePessoa,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoEncontroLegado,
    VinculoUsuarioPessoa,
)
from core.roles import SiaRole
from core.tests.factories import make_encontro


class EncontroWorkspaceApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.fichas = self._usuario('workspace-fichas', SiaRole.FICHAS)
        self.comunicacao = self._usuario(
            'workspace-comunicacao', SiaRole.COMUNICACAO,
        )
        self.diretoria = self._usuario('workspace-diretoria', SiaRole.DIRETORIA)
        self.suporte = self._usuario('workspace-suporte', SiaRole.SUPORTE)
        self.sem_papel = User.objects.create_user('workspace-sem-papel')
        self.superuser = User.objects.create_superuser(
            'workspace-root', email='root@example.test', password='senha',
        )
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        agora = timezone.now()
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=20,
            idade_minima=15,
            idade_maxima=18,
            inscricoes_abrem_em=agora - timedelta(days=1),
            inscricoes_encerram_em=agora + timedelta(days=1),
        )
        self.calendario = CalendarioEncontro.objects.create(
            encontro=self.encontro,
            versao=1,
            vigente=True,
            oficializado_em=agora,
            pre_encontro_data=date(2030, 1, 5),
        )
        DiaEncontro.objects.create(
            calendario=self.calendario,
            ordem=1,
            data=date(2030, 1, 10),
            rotulo='Primeiro dia',
        )
        self.pre = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 1, 5),
            horario=time(14),
            local='Local do Pré',
        )

    def _usuario(self, username, role):
        usuario = User.objects.create_user(username)
        grupo, _ = Group.objects.get_or_create(name=role.value)
        usuario.groups.add(grupo)
        return usuario

    def _auth(self, usuario):
        self.client.force_authenticate(usuario)

    def _url(self, suffix=''):
        return f'/api/encontros/{self.encontro.pk}/workspace/{suffix}'

    def _inscricao(self, nome='Ana Candidata', *, pessoa=None, status_inscricao=None):
        inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.PUBLICA,
            status=status_inscricao or InscricaoEncontro.Status.ENVIADA,
            cancelada_em=(
                timezone.now()
                if status_inscricao == InscricaoEncontro.Status.CANCELADA
                else None
            ),
        )
        DadosDeclaradosInscricao.objects.create(
            inscricao=inscricao,
            nome_completo=nome,
            data_nascimento=date(2010, 1, 1),
            email=f'{inscricao.pk}@example.test',
            telefone_whatsapp='61999990000',
            cep='71900-000',
            logradouro='Rua Teste',
            numero='1',
            bairro='Centro',
            cidade='Brasília',
            uf='DF',
            como_conheceu=DadosDeclaradosInscricao.ComoConheceu.INDICACAO,
        )
        return inscricao

    def _atendimento(self, *, inscricao=None, pessoa=None, nome='Avulso'):
        return AtendimentoPreEncontro.objects.create(
            pre_encontro=self.pre,
            inscricao=inscricao,
            pessoa=pessoa,
            nome_informado=nome if not inscricao and not pessoa else '',
            data_nascimento_informada=(
                date(2010, 1, 1) if not inscricao and not pessoa else None
            ),
            telefone_informado=(
                '61988880000' if not inscricao and not pessoa else ''
            ),
            registrado_por=self.fichas,
        )

    def test_summary_autorizado_lifecycle_e_agregados_sem_pii(self):
        self._inscricao()
        self._auth(self.fichas)
        resposta = self.client.get(self._url())
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data['lifecycle'], Encontro.Status.EM_PREPARACAO)
        self.assertEqual(resposta.data['encontristas']['inscricoes_recebidas'], 1)
        self.assertEqual(resposta.data['encontristas']['pendentes'], 1)
        self.assertEqual(resposta.data['encontristas']['confirmados'], 0)
        self.assertEqual(resposta.data['encontristas']['total_funil'], 1)
        self.assertNotIn('cpf', str(resposta.data).lower())
        self.assertNotIn('telefone', str(resposta.data).lower())
        self.assertNotIn('cuidados', str(resposta.data).lower())
        self.assertNotIn('foto', str(resposta.data).lower())

    def test_default_deny_e_superuser_bypass(self):
        self._auth(self.sem_papel)
        self.assertEqual(self.client.get(self._url()).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self._url('encontristas/')).status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(self.client.get(self._url('capabilities/')).status_code, status.HTTP_403_FORBIDDEN)
        self._auth(self.superuser)
        self.assertEqual(self.client.get(self._url()).status_code, status.HTTP_200_OK)

    def test_lifecycle_historico_permanece_consultavel(self):
        self._auth(self.fichas)
        for lifecycle in (Encontro.Status.FINALIZADO, Encontro.Status.CANCELADO, Encontro.Status.ADIADO):
            self.encontro.status = lifecycle
            self.encontro.save(update_fields=['status'])
            resposta = self.client.get(self._url())
            self.assertEqual(resposta.status_code, status.HTTP_200_OK)
            self.assertEqual(resposta.data['lifecycle'], lifecycle)

    def test_toda_inscricao_sem_pre_e_sem_pessoa_aparece(self):
        inscricao = self._inscricao()
        self._auth(self.fichas)
        lista = self.client.get(self._url('encontristas/'))
        self.assertEqual(lista.data['count'], 1)
        item = lista.data['results'][0]
        self.assertEqual(item['ref']['origem_id'], str(inscricao.identificador))
        self.assertEqual(item['origem']['codigo'], 'INSCRICAO')
        self.assertEqual(item['situacao']['codigo'], 'INSCRITO')
        self.assertFalse(item['presenca_pre'])
        self.assertIsNone(item['pessoa_id'])

    def test_pessoa_e_avulso_sem_inscricao_aparecem_sem_incrementar_inscricoes(self):
        pessoa = Pessoa.objects.create(nome='Pessoa do Pré')
        self._atendimento(pessoa=pessoa)
        self._atendimento(nome='Avulso do Pré')
        self._auth(self.fichas)
        lista = self.client.get(self._url('encontristas/'))
        resumo = self.client.get(self._url())
        self.assertEqual(lista.data['count'], 2)
        self.assertEqual(
            {item['origem']['codigo'] for item in lista.data['results']},
            {'PESSOA', 'AVULSO'},
        )
        self.assertEqual(resumo.data['encontristas']['inscricoes_recebidas'], 0)
        self.assertEqual(resumo.data['encontristas']['total_funil'], 2)

    def test_vinculo_posterior_enriquece_sem_duplicar(self):
        pessoa = Pessoa.objects.create(nome='Pessoa regularizada')
        inscricao = self._inscricao(pessoa=pessoa)
        atendimento = self._atendimento(inscricao=inscricao, pessoa=pessoa)
        self._auth(self.fichas)
        lista = self.client.get(self._url('encontristas/'))
        self.assertEqual(lista.data['count'], 1)
        self.assertTrue(lista.data['results'][0]['presenca_pre'])
        self.assertEqual(lista.data['results'][0]['pessoa_id'], pessoa.pk)
        self.assertEqual(lista.data['results'][0]['ref']['origem_tipo'], 'INSCRICAO')
        self.assertEqual(atendimento.inscricao_id, inscricao.pk)

    def test_situacoes_cancelado_apto_nao_apto_aguardando_e_confirmado(self):
        self._inscricao('Cancelada', status_inscricao=InscricaoEncontro.Status.CANCELADA)
        apta = self._inscricao('Apta')
        self._atendimento(inscricao=apta)
        avulso = self._atendimento(nome='Sem regularização')
        pendente = self._inscricao('Decisão')
        atendimento_pendente = self._atendimento(inscricao=pendente)
        DecisaoVagaPreEncontro.objects.create(atendimento=atendimento_pendente)
        pessoa = Pessoa.objects.create(nome='Confirmada')
        confirmada = self._inscricao('Confirmada', pessoa=pessoa)
        self._atendimento(inscricao=confirmada, pessoa=pessoa)
        ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        self._auth(self.fichas)
        codigos = {
            item['nome']: item['situacao']['codigo']
            for item in self.client.get(self._url('encontristas/')).data['results']
        }
        self.assertEqual(codigos['Cancelada'], 'CANCELADO')
        self.assertEqual(codigos['Apta'], 'APTO')
        self.assertEqual(codigos['Sem regularização'], 'NAO_APTO')
        self.assertEqual(codigos['Decisão'], 'AGUARDANDO_DECISAO')
        self.assertEqual(codigos['Confirmada'], 'CONFIRMADO')
        self.assertIsNotNone(avulso.pk)
        resumo = self.client.get(self._url()).data['encontristas']['por_situacao']
        agregados = self.client.get(self._url()).data['encontristas']
        self.assertEqual(agregados['pendentes'], 2)
        self.assertEqual(agregados['confirmados'], 1)
        for codigo in set(codigos.values()):
            filtrada = self.client.get(
                self._url(f'encontristas/?situacao={codigo}'),
            )
            self.assertEqual(filtrada.data['count'], resumo[codigo])

    def test_filtros_contagens_e_count_independem_da_pagina(self):
        for indice in range(12):
            self._inscricao(f'Pessoa {indice:02d}')
        self._auth(self.fichas)
        primeira = self.client.get(self._url('encontristas/'))
        segunda = self.client.get(self._url('encontristas/?page=2'))
        filtrada = self.client.get(self._url('encontristas/?situacao=INSCRITO&origem=INSCRICAO'))
        resumo = self.client.get(self._url())
        self.assertEqual(primeira.data['count'], 12)
        self.assertEqual(len(primeira.data['results']), 10)
        self.assertEqual(segunda.data['count'], 12)
        self.assertEqual(len(segunda.data['results']), 2)
        self.assertEqual(filtrada.data['count'], 12)
        self.assertEqual(resumo.data['encontristas']['por_situacao']['INSCRITO'], 12)

    def test_busca_por_nome_e_telefone_respeita_capability(self):
        self._inscricao('Nome Encontrável')
        self._auth(self.fichas)
        self.assertEqual(self.client.get(self._url('encontristas/?search=Encontrável')).data['count'], 1)
        por_telefone = self.client.get(self._url('encontristas/?search=9999'))
        self.assertEqual(por_telefone.data['count'], 1)
        self.assertIn('telefone', por_telefone.data['results'][0])
        self.assertNotIn('cpf', str(por_telefone.data).lower())
        self.assertNotIn('cuidados', str(por_telefone.data).lower())
        self.assertNotIn('foto', str(por_telefone.data).lower())
        self.assertNotIn('endereco', str(por_telefone.data).lower())
        self._auth(self.comunicacao)
        resumo = self.client.get(self._url('encontristas/?search=Encontrável'))
        telefone = self.client.get(self._url('encontristas/?search=9999'))
        self.assertEqual(resumo.data['count'], 1)
        self.assertNotIn('telefone', resumo.data['results'][0])
        self.assertEqual(telefone.data['count'], 0)

    def test_telefone_usa_precedencia_canonica(self):
        pessoa = Pessoa.objects.create(nome='Contato')
        TelefonePessoa.objects.create(pessoa=pessoa, numero='61111111111', whatsapp=True)
        inscricao = self._inscricao('Contato', pessoa=pessoa)
        self._atendimento(inscricao=inscricao, pessoa=pessoa)
        self._auth(self.fichas)
        item = self.client.get(self._url('encontristas/')).data['results'][0]
        self.assertEqual(item['telefone'], '61999990000')

    def test_capabilities_sao_granulares_e_server_driven(self):
        self._auth(self.comunicacao)
        summary = self.client.get(self._url())
        encontristas = self.client.get(self._url('encontristas/'))
        comunicacao = self.client.get(self._url('capabilities/')).data
        self.assertEqual(summary.status_code, status.HTTP_200_OK)
        self.assertEqual(encontristas.status_code, status.HTTP_200_OK)
        self.assertNotIn('cpf', str(summary.data).lower())
        self.assertNotIn('telefone', str(encontristas.data).lower())
        self.assertNotIn('cuidados', str(encontristas.data).lower())
        self.assertNotIn('foto', str(encontristas.data).lower())
        self.assertTrue(comunicacao['consultar_resumo'])
        self.assertTrue(comunicacao['consultar_encontristas'])
        self.assertFalse(comunicacao['consultar_contato'])
        self.assertTrue(comunicacao['acessar_pre_encontro'])
        self.assertFalse(comunicacao['acessar_equipes'])
        self.assertFalse(comunicacao['acessar_formacao'])
        self.assertTrue(comunicacao['acessar_agenda'])
        self.assertFalse(comunicacao['consultar_inscricoes'])
        self.assertFalse(comunicacao['configurar_inscricoes'])
        self._auth(self.fichas)
        fichas = self.client.get(self._url('capabilities/')).data
        self.assertTrue(fichas['consultar_inscricoes'])
        self.assertTrue(fichas['configurar_inscricoes'])
        self._auth(self.superuser)
        self.assertTrue(all(self.client.get(self._url('capabilities/')).data.values()))

    def test_coordenacao_contextual_nao_vaza_para_outro_encontro(self):
        coordenador = self._criar_coordenador_contextual()
        self._auth(coordenador)
        self.assertEqual(self.client.get(self._url()).status_code, status.HTTP_200_OK)
        outro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.assertEqual(
            self.client.get(f'/api/encontros/{outro.pk}/workspace/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def _criar_coordenador_contextual(self):
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=self.encontro.tipo,
            codigo='coordenacao-workspace',
            nome='Coordenação Geral',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=template,
            codigo='coordenacao-geral',
            nome='Coordenação Geral',
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo='integrante',
            nome='Integrante',
        )
        pessoa = Pessoa.objects.create(nome='Coordenação')
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        TrabalhoEncontro.objects.create(
            pessoa=pessoa,
            encontro=self.encontro,
            convite=convite,
            role_equipe=role,
            status=TrabalhoEncontro.Status.ALOCADO,
        )
        usuario = User.objects.create_user('workspace-coordenacao')
        VinculoUsuarioPessoa.objects.create(usuario=usuario, pessoa=pessoa)
        return usuario

    def test_agenda_e_pre_usam_somente_calendario_canonico(self):
        self.encontro.data_referencia = date(1999, 1, 1)
        self.encontro.data_exato = 'Texto legado conflitante'
        self.encontro.save(update_fields=['data_referencia', 'data_exato'])
        self._auth(self.fichas)
        agenda = self.client.get(self._url()).data['agenda']
        self.assertTrue(agenda['configurada'])
        self.assertTrue(agenda['oficializada'])
        self.assertEqual(str(agenda['pre_encontro_data']), '2030-01-05')
        self.assertEqual([str(item) for item in agenda['datas_principais']], ['2030-01-10'])
        self.assertNotIn('1999', str(agenda))
        self.calendario.delete()
        agenda_sem_calendario = self.client.get(self._url()).data['agenda']
        self.assertFalse(agenda_sem_calendario['configurada'])
        self.assertEqual(agenda_sem_calendario['datas_principais'], [])

    def test_resumos_equipes_e_formacao_usam_dominios_atuais(self):
        self._criar_coordenador_contextual()
        SessaoFormativa.objects.create(
            encontro=self.encontro,
            tema_codigo='tema-teste',
            tipo_conteudo='palestra',
            titulo_snapshot='Tema de teste',
        )
        self._auth(self.fichas)
        resumo = self.client.get(self._url()).data
        self.assertEqual(resumo['equipes']['quantidade_equipes'], 1)
        self.assertEqual(resumo['equipes']['quantidade_funcoes'], 1)
        self.assertEqual(resumo['equipes']['vagas_preenchidas'], 1)
        self.assertEqual(resumo['formacao']['total_sessoes'], 1)
        self.assertEqual(resumo['formacao']['planejadas'], 1)

    def test_legado_conflitante_nao_altera_lista_ou_contagens(self):
        self._inscricao()
        alpinista = Alpinista.objects.create(
            nome='Legado confirmado',
            email='legado-workspace@example.test',
            telefone='61900000000',
            status=Alpinista.Status.CONFIRMADO,
        )
        funcao = FuncaoEncontro.objects.create(nome='Encontrista legado', tipo='encontrista')
        VinculoEncontroLegado.objects.create(
            alpinista=alpinista,
            encontro=self.encontro,
            funcao=funcao,
        )
        self._auth(self.fichas)
        lista = self.client.get(self._url('encontristas/'))
        resumo = self.client.get(self._url())
        self.assertEqual(lista.data['count'], 1)
        self.assertEqual(lista.data['results'][0]['situacao']['codigo'], 'INSCRITO')
        self.assertEqual(resumo.data['encontristas']['total_funil'], 1)

    def test_nested_inexistente_404_e_workspace_sem_commands(self):
        self._auth(self.fichas)
        self.assertEqual(self.client.get('/api/encontros/999999/workspace/').status_code, status.HTTP_404_NOT_FOUND)
        for method in ('post', 'put', 'patch', 'delete'):
            self.assertEqual(getattr(self.client, method)(self._url()).status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_parametros_e_filtros_invalidos_sao_rejeitados(self):
        self._auth(self.fichas)
        self.assertEqual(self.client.get(self._url('encontristas/?fields=cpf')).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(self._url('encontristas/?situacao=LEGADO')).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.get(self._url('encontristas/?origem=LEGADO')).status_code, status.HTTP_400_BAD_REQUEST)

    def test_alertas_derivam_de_fatos_reais(self):
        self.pre.delete()
        self.calendario.pre_encontro_data = None
        self.calendario.save(update_fields=['pre_encontro_data'])
        self._auth(self.fichas)
        codigos = {item['codigo'] for item in self.client.get(self._url()).data['alertas']}
        self.assertIn('PRE_NAO_CONFIGURADO', codigos)
        self.assertIn('DATA_PRE_AUSENTE', codigos)

    def test_queries_da_lista_nao_crescem_linearmente(self):
        self._inscricao('Primeira')
        self._auth(self.fichas)
        with CaptureQueriesContext(connection) as pequena:
            self.client.get(self._url('encontristas/'))
        for indice in range(8):
            self._inscricao(f'Extra {indice}')
        with CaptureQueriesContext(connection) as maior:
            self.client.get(self._url('encontristas/'))
        self.assertLessEqual(len(maior), len(pequena) + 2)
