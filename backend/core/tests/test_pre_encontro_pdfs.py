from datetime import date, time, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    AtendimentoPreEncontro,
    ConferenciaCuidadoPreEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DadosCuidadoInscricao,
    DadosDeclaradosInscricao,
    Encontro,
    EquipeEncontro,
    EventoAuditoriaEncontro,
    InscricaoEncontro,
    PagamentoPreEncontro,
    Pessoa,
    PreEncontro,
    PublicacaoCalendarioInstitucional,
    RoleEquipeEncontro,
    TelefonePessoa,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoUsuarioPessoa,
)
from core.roles import SiaRole
from core.services import exportacao_pre_encontro
from core.services.pre_encontro import (
    conferir_cuidados_pre_encontro,
    registrar_checkin_pre_encontro,
    registrar_pagamento_pre_encontro,
)
from core.tests.factories import make_encontro


class PreEncontroPdfTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media.cleanup)
        self.client = APIClient()
        self.fichas = self._usuario('fichas-pdf', SiaRole.FICHAS)
        self.comunicacao = self._usuario('comunicacao-pdf', SiaRole.COMUNICACAO)
        self.suporte = self._usuario('suporte-pdf', SiaRole.SUPORTE)
        self.diretoria = self._usuario('diretoria-pdf', SiaRole.DIRETORIA)
        self.sem_papel = User.objects.create_user('sem-papel-pdf')
        self.superuser = User.objects.create_superuser('super-pdf')
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.encontro.data_referencia = date(2040, 12, 31)
        self.encontro.save(update_fields=['data_referencia'])
        self.pre = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 5, 10),
            horario=time(14, 30),
            local='Local canônico do Pré',
        )
        agora = timezone.now()
        ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=20,
            idade_minima=15,
            idade_maxima=80,
            inscricoes_abrem_em=agora - timedelta(days=1),
            inscricoes_encerram_em=agora + timedelta(days=1),
        )
        self.atualizado, self.dados_atualizados = self._atendimento_inscricao(
            'Alice Atualizada',
            '61911112222',
            alergias='Alergia canônica atualizada',
        )
        self.conferido, self.dados_conferidos = self._atendimento_inscricao(
            'Bruno Conferido',
            '61933334444',
            medicamentos='Medicamento canônico',
        )
        self.nao_conferido, self.dados_nao_conferidos = self._atendimento_inscricao(
            'Beatriz Não Conferida',
            '61922223333',
            alergias='Cuidado ainda não conferido',
        )
        self.sem_cuidado, _ = self._atendimento_inscricao(
            'Carlos Sem Cuidado',
            '61955556666',
        )
        conferir_cuidados_pre_encontro(
            usuario=self.fichas,
            atendimento=self.atualizado,
            dados_cuidado=self.dados_atualizados,
        )
        conferir_cuidados_pre_encontro(
            usuario=self.fichas,
            atendimento=self.conferido,
            dados_cuidado=self.dados_conferidos,
        )
        self.dados_atualizados.observacoes = 'Informação posterior'
        self.dados_atualizados.save(update_fields=['observacoes', 'atualizado_em'])
        pessoa_direta = Pessoa.objects.create(nome='Daniel Pessoa')
        TelefonePessoa.objects.create(
            pessoa=pessoa_direta,
            numero='61977778888',
            whatsapp=True,
        )
        self.pessoa_direta = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre,
            pessoa=pessoa_direta,
        )
        self.avulso = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre,
            nome_informado='Érica Avulsa',
            data_nascimento_informada=date(2000, 1, 1),
            telefone_informado='61999990000',
        )
        registrar_pagamento_pre_encontro(
            usuario=self.fichas,
            atendimento=self.conferido,
            status=PagamentoPreEncontro.Status.PAGO,
            forma=PagamentoPreEncontro.Forma.PIX,
        )

    def _usuario(self, username, role):
        usuario = User.objects.create_user(username)
        grupo, _ = Group.objects.get_or_create(name=role.value)
        usuario.groups.add(grupo)
        return usuario

    def _atendimento_inscricao(
        self,
        nome,
        telefone,
        *,
        alergias='',
        medicamentos='',
    ):
        pessoa = Pessoa.objects.create(nome=nome)
        inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )
        DadosDeclaradosInscricao.objects.create(
            inscricao=inscricao,
            nome_completo=nome,
            data_nascimento=date(2000, 1, 1),
            telefone_whatsapp=telefone,
            cep='71900-000',
            logradouro='Rua de teste',
            numero='1',
            bairro='Centro',
            cidade='Brasília',
            uf='DF',
            como_conheceu=DadosDeclaradosInscricao.ComoConheceu.INDICACAO,
        )
        dados = DadosCuidadoInscricao.objects.create(
            inscricao=inscricao,
            possui_alergias=(
                DadosCuidadoInscricao.RespostaBinaria.SIM
                if alergias else DadosCuidadoInscricao.RespostaBinaria.NAO
            ),
            alergias=alergias,
            usa_medicamentos=(
                DadosCuidadoInscricao.RespostaBinaria.SIM
                if medicamentos else DadosCuidadoInscricao.RespostaBinaria.NAO
            ),
            medicamentos=medicamentos,
            possui_restricoes_intolerancias=(
                DadosCuidadoInscricao.RespostaBinaria.NAO
            ),
            neurodivergencia_apoio=DadosCuidadoInscricao.RespostaApoio.NAO,
        )
        atendimento = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre,
            pessoa=pessoa,
            inscricao=inscricao,
        )
        return atendimento, dados

    def _coordenacao(self, encontro=None):
        encontro = encontro or self.encontro
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=encontro.tipo,
            codigo=f'coord-pdf-{encontro.pk}',
            nome='Coordenação Geral',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
        )
        equipe = EquipeEncontro.objects.create(
            encontro=encontro,
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
        pessoa = Pessoa.objects.create(nome=f'Coordenação {encontro.pk}')
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        TrabalhoEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            convite=convite,
            role_equipe=role,
            status=TrabalhoEncontro.Status.ALOCADO,
        )
        usuario = User.objects.create_user(f'coord-pdf-{encontro.pk}')
        VinculoUsuarioPessoa.objects.create(usuario=usuario, pessoa=pessoa)
        return usuario

    def _url(self, tipo, encontro=None):
        encontro = encontro or self.encontro
        return f'/api/encontros/{encontro.pk}/pre-encontro/pdf/{tipo}/'

    def _conteudo(self, resposta):
        return b''.join(resposta.streaming_content)

    def test_projecao_operacional_reusa_dados_canonicos_e_ordem_alfabetica(self):
        projecao = exportacao_pre_encontro.projetar_operacional(self.pre)

        self.assertEqual(
            [linha.nome for linha in projecao.linhas],
            sorted((linha.nome for linha in projecao.linhas), key=str.casefold),
        )
        por_nome = {linha.nome: linha for linha in projecao.linhas}
        self.assertEqual(por_nome['Alice Atualizada'].telefone, '61911112222')
        self.assertEqual(por_nome['Daniel Pessoa'].telefone, '61977778888')
        self.assertEqual(por_nome['Érica Avulsa'].telefone, '61999990000')
        self.assertEqual(por_nome['Alice Atualizada'].origem, 'Inscrição')
        self.assertEqual(por_nome['Daniel Pessoa'].origem, 'Pessoa existente')
        self.assertEqual(por_nome['Érica Avulsa'].origem, 'Avulso')
        self.assertEqual(por_nome['Bruno Conferido'].pagamento, 'Pago')
        self.assertTrue(all(linha.presenca == 'Presente' for linha in projecao.linhas))
        self.assertTrue(all(linha.aptidao for linha in projecao.linhas))
        self.assertTrue(all(linha.vaga for linha in projecao.linhas))
        self.assertEqual(projecao.quantidade_linhas_extras, 10)
        self.assertEqual(projecao.cabecalho.data, self.pre.data)
        self.assertNotEqual(projecao.cabecalho.data, self.encontro.data_referencia)

    def test_html_operacional_tem_dez_linhas_e_nenhum_cuidado_ou_foto(self):
        html = exportacao_pre_encontro.renderizar_html_operacional(
            exportacao_pre_encontro.projetar_operacional(self.pre),
        )

        self.assertEqual(html.count('data-extra-line='), 10)
        self.assertIn('Alice Atualizada', html)
        self.assertIn('61911112222', html)
        self.assertNotIn('Alergia canônica atualizada', html)
        self.assertNotIn('Medicamento canônico', html)
        self.assertNotIn('pre_encontros/fotos', html)
        self.assertNotIn('<img', html)

    def test_projecao_cuidados_filtra_relevancia_e_estado_de_conferencia(self):
        projecao = exportacao_pre_encontro.projetar_cuidados(self.pre)
        por_nome = {linha.nome: linha for linha in projecao.linhas}

        self.assertEqual(
            list(por_nome),
            ['Alice Atualizada', 'Beatriz Não Conferida', 'Bruno Conferido'],
        )
        self.assertEqual(
            por_nome['Alice Atualizada'].conferencia,
            'Atualizado após conferência',
        )
        self.assertEqual(por_nome['Bruno Conferido'].conferencia, 'Conferido')
        self.assertEqual(
            por_nome['Beatriz Não Conferida'].conferencia,
            'Não conferido',
        )
        self.assertNotIn('Carlos Sem Cuidado', por_nome)
        campos = {campo.valor for campo in por_nome['Alice Atualizada'].campos}
        self.assertIn('Alergia canônica atualizada', campos)

    def test_html_cuidados_e_separado_restrito_e_sem_linhas_extras(self):
        html = exportacao_pre_encontro.renderizar_html_cuidados(
            exportacao_pre_encontro.projetar_cuidados(self.pre),
        )

        self.assertIn('RESTRITO — DADOS DE CUIDADO', html)
        self.assertIn('Alergia canônica atualizada', html)
        self.assertIn('Atualizado após conferência', html)
        self.assertIn('Conferido', html)
        self.assertIn('Não conferido', html)
        self.assertNotIn('Carlos Sem Cuidado', html)
        self.assertNotIn('data-extra-line=', html)
        self.assertNotIn('<img', html)

    def test_endpoints_geram_pdf_com_headers_privados_e_nomes_previsiveis(self):
        self.client.force_authenticate(self.fichas)

        operacional = self.client.get(self._url('operacional'))
        cuidados = self.client.get(self._url('cuidados'))

        for resposta, nome in (
            (operacional, 'pre-encontro-operacional.pdf'),
            (cuidados, 'pre-encontro-cuidados.pdf'),
        ):
            self.assertEqual(resposta.status_code, status.HTTP_200_OK)
            self.assertTrue(self._conteudo(resposta).startswith(b'%PDF'))
            self.assertEqual(resposta['Content-Type'], 'application/pdf')
            self.assertIn('attachment', resposta['Content-Disposition'])
            self.assertIn(nome, resposta['Content-Disposition'])
            self.assertEqual(resposta['Cache-Control'], 'private, no-store')
            self.assertEqual(resposta['X-Content-Type-Options'], 'nosniff')

    def test_autorizacao_operacional_reutiliza_consultar_operacao(self):
        with patch.object(
            exportacao_pre_encontro,
            'gerar_pdf_operacional_pre_encontro',
            return_value=b'%PDF',
        ):
            for usuario in (self.fichas, self.comunicacao, self.suporte):
                self.client.force_authenticate(usuario)
                self.assertEqual(
                    self.client.get(self._url('operacional')).status_code,
                    status.HTTP_200_OK,
                )
            self.client.force_authenticate(self.sem_papel)
            self.assertEqual(
                self.client.get(self._url('operacional')).status_code,
                status.HTTP_403_FORBIDDEN,
            )

    def test_cuidados_autoriza_fichas_coordenacao_e_superuser(self):
        coordenacao = self._coordenacao()
        with patch.object(
            exportacao_pre_encontro,
            'gerar_pdf_cuidados_pre_encontro',
            return_value=b'%PDF',
        ):
            for usuario in (self.fichas, coordenacao, self.superuser):
                self.client.force_authenticate(usuario)
                self.assertEqual(
                    self.client.get(self._url('cuidados')).status_code,
                    status.HTTP_200_OK,
                )

    def test_cuidados_nega_comunicacao_admin_ampla_e_default_deny_antes_da_projecao(self):
        with patch.object(
            exportacao_pre_encontro,
            'gerar_pdf_cuidados_pre_encontro',
        ) as gerar:
            for usuario in (
                self.comunicacao,
                self.suporte,
                self.diretoria,
                self.sem_papel,
            ):
                self.client.force_authenticate(usuario)
                self.assertEqual(
                    self.client.get(self._url('cuidados')).status_code,
                    status.HTTP_403_FORBIDDEN,
                )
            gerar.assert_not_called()

    def test_contexto_inexistente_e_coordenacao_de_outro_encontro_nao_vazam(self):
        outro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        coordenacao_outro = self._coordenacao(outro)
        self.client.force_authenticate(self.fichas)
        self.assertEqual(
            self.client.get(self._url('operacional', outro)).status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.client.force_authenticate(coordenacao_outro)
        self.assertEqual(
            self.client.get(self._url('cuidados')).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_geracao_e_transitoria_sem_model_storage_auditoria_ou_mutacao(self):
        estado_antes = (
            PublicacaoCalendarioInstitucional.objects.count(),
            EventoAuditoriaEncontro.objects.count(),
            AtendimentoPreEncontro.objects.count(),
            DadosCuidadoInscricao.objects.count(),
            ConferenciaCuidadoPreEncontro.objects.count(),
            PagamentoPreEncontro.objects.count(),
            self.pre.data,
            self.pre.horario,
            self.pre.local,
        )
        arquivos_antes = set(Path(self.media.name).rglob('*'))
        self.encontro.status = Encontro.Status.FINALIZADO
        self.encontro.save(update_fields=['status'])
        self.client.force_authenticate(self.fichas)

        operacional = self.client.get(self._url('operacional'))
        cuidados = self.client.get(self._url('cuidados'))

        self.pre.refresh_from_db()
        estado_depois = (
            PublicacaoCalendarioInstitucional.objects.count(),
            EventoAuditoriaEncontro.objects.count(),
            AtendimentoPreEncontro.objects.count(),
            DadosCuidadoInscricao.objects.count(),
            ConferenciaCuidadoPreEncontro.objects.count(),
            PagamentoPreEncontro.objects.count(),
            self.pre.data,
            self.pre.horario,
            self.pre.local,
        )
        self.assertEqual(operacional.status_code, status.HTTP_200_OK)
        self.assertEqual(cuidados.status_code, status.HTTP_200_OK)
        self.assertEqual(estado_depois, estado_antes)
        self.assertEqual(set(Path(self.media.name).rglob('*')), arquivos_antes)
