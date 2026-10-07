import base64
import hashlib
from datetime import UTC, date, datetime, time
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    AvaliacaoEncontro,
    PublicacaoCalendarioInstitucional,
    ReuniaoPreparatoriaEncontro,
    calendario_publicacao_upload_to,
)
from core.roles import SiaRole
from core.services import exportacao_calendario as exportacao
from core.tests.test_calendario_institucional import criar_encontro_canonico


GERADO_EM = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)
TEST_LOGO = 'data:image/svg+xml;base64,' + base64.b64encode(
    b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10">'
    b'<path d="M0 0h10v10H0z"/></svg>'
).decode('ascii')


def item_exportacao(
    identificador,
    data_item,
    titulo,
    *,
    publicavel=True,
    provisorio=False,
    rotulo='Pré-Escalada',
    complemento=None,
):
    return exportacao.ItemExportacaoCalendario(
        id=identificador,
        origem='DIA_ENCONTRO',
        origem_id=1,
        data=data_item,
        encontro_id=1,
        encontro_titulo=titulo,
        encontro_tipo='Escalada',
        encontro_status='em_agendamento' if provisorio else 'agendado',
        rotulo=rotulo,
        complemento=complemento,
        categoria='ENCONTRO',
        provisorio=provisorio,
        publicavel_externamente=publicavel,
        conflito=False,
    )


def snapshot_controlado(
    *,
    escopo=exportacao.ESCOPO_PUBLICO,
    periodo=exportacao.PERIODO_MES,
    layout=exportacao.LAYOUT_MENSAL,
):
    itens = (
        item_exportacao(
            'DIA:1',
            date(2027, 3, 7),
            'Escalada 2027',
            provisorio=True,
        ),
        item_exportacao(
            'DIA:2',
            date(2027, 3, 21),
            'AVC Nossa Senhora da Esperança e da Juventude',
            rotulo='Encontro principal com um rótulo controladamente longo',
        ),
        item_exportacao(
            'DIA:3',
            date(2027, 3, 21),
            'ESPPA Regional',
            rotulo='Formação comunitária',
        ),
        item_exportacao(
            'DIA:4',
            date(2027, 6, 12),
            'Acampamento de Inverno',
        ),
    )
    return exportacao.montar_snapshot(
        escopo=escopo,
        periodo=periodo,
        layout=layout,
        ano=2027,
        mes=3 if periodo == exportacao.PERIODO_MES else None,
        itens=itens,
        gerado_em=GERADO_EM,
    )


class SnapshotCalendarioTests(TestCase):
    def setUp(self):
        self.encontro, calendario = criar_encontro_canonico(
            'Escalada 2027',
            [date(2027, 3, 21)],
        )
        dia = calendario.dias.get()
        dia.rotulo = 'Pré-Escalada'
        dia.save(update_fields=['rotulo'])
        ReuniaoPreparatoriaEncontro.objects.create(
            encontro=self.encontro,
            ordem=3,
            data=date(2027, 3, 17),
            horario=time(19, 30),
            local='Paróquia',
            complemento='Missa de Entrega',
        )
        AvaliacaoEncontro.objects.create(
            encontro=self.encontro,
            data=date(2027, 3, 30),
        )

    def _capturar(self, escopo):
        return exportacao.capturar_snapshot(
            escopo=escopo,
            periodo=exportacao.PERIODO_MES,
            layout=exportacao.LAYOUT_MENSAL,
            ano=2027,
            mes=3,
            gerado_em=GERADO_EM,
        )

    def test_publico_e_interno_consumem_publicabilidade_canonica(self):
        publico = self._capturar(exportacao.ESCOPO_PUBLICO)
        interno = self._capturar(exportacao.ESCOPO_INTERNO)

        self.assertEqual([item.origem for item in publico.itens], ['DIA_ENCONTRO'])
        por_origem = {item.origem: item for item in interno.itens}
        self.assertEqual(
            por_origem['REUNIAO_PREPARATORIA'].rotulo,
            '3ª Preparatória',
        )
        self.assertEqual(
            por_origem['REUNIAO_PREPARATORIA'].complemento,
            'Missa de Entrega',
        )
        self.assertEqual(por_origem['AVALIACAO'].rotulo, 'Avaliação')
        self.assertNotIn('3ª Reunião', exportacao.renderizar_html(interno))

    def test_snapshot_v2_registra_periodo_layout_e_nao_contem_pii(self):
        serializado = self._capturar(exportacao.ESCOPO_INTERNO).as_dict()
        texto = str(serializado).casefold()

        self.assertEqual(serializado['schema_version'], 2)
        self.assertEqual(serializado['periodo'], 'MES')
        self.assertEqual(serializado['layout'], 'MENSAL')
        for campo in (
            'participante', 'equipe', 'presença', 'saúde', 'telefone',
            'email', 'cpf',
        ):
            self.assertNotIn(campo, texto)

    def test_modalidades_validas_e_combinacao_invalida(self):
        for periodo, layout, mes in (
            ('MES', 'MENSAL', 3),
            ('ANO', 'MENSAL', None),
            ('ANO', 'ANUAL_RESUMIDO', None),
        ):
            with self.subTest(periodo=periodo, layout=layout):
                exportacao.validar_modalidade(periodo, layout, mes)
        with self.assertRaisesRegex(ValueError, 'Combinação'):
            exportacao.validar_modalidade('MES', 'ANUAL_RESUMIDO', 3)


class RendererCalendarioTests(TestCase):
    @patch.object(exportacao, 'carregar_logo_oficial', return_value=TEST_LOGO)
    def test_mensal_mes_e_a4_paisagem_com_logo(self, logo):
        snapshot = snapshot_controlado()
        documento = exportacao.renderizar_documento(snapshot)
        html = exportacao.renderizar_html(snapshot)

        self.assertEqual(len(documento.pages), 1)
        self.assertGreater(documento.pages[0].width, documento.pages[0].height)
        self.assertIn('@page { size: A4 landscape;', html)
        self.assertIn('Escalada 2027 *', html)
        self.assertIn('+ outros compromissos neste dia', html)
        self.assertIn('Símbolo oficial do Movimento', html)
        logo.assert_called()

    @patch.object(exportacao, 'carregar_logo_oficial', return_value=TEST_LOGO)
    def test_ano_layout_mensal_gera_exatamente_doze_paginas(self, _logo):
        snapshot = snapshot_controlado(
            periodo=exportacao.PERIODO_ANO,
            layout=exportacao.LAYOUT_MENSAL,
        )
        documento = exportacao.renderizar_documento(snapshot)
        html = exportacao.renderizar_html(snapshot)

        self.assertEqual(len(documento.pages), 12)
        for mes in exportacao._MESES:
            self.assertIn(f'{mes} 2027', html)

    @patch.object(exportacao, 'carregar_logo_oficial', return_value=TEST_LOGO)
    def test_anual_resumido_usa_somente_modelo_b_em_uma_pagina(self, _logo):
        snapshot = snapshot_controlado(
            periodo=exportacao.PERIODO_ANO,
            layout=exportacao.LAYOUT_ANUAL_RESUMIDO,
        )
        documento = exportacao.renderizar_documento(snapshot)
        html = exportacao.renderizar_html(snapshot)

        self.assertEqual(len(documento.pages), 1)
        self.assertIn('model-b', html)
        self.assertIn('compact-agenda', html)
        self.assertNotIn('model-a', html)
        self.assertNotIn('mini-entry', html)

    @patch.object(exportacao, 'carregar_logo_oficial', return_value=None)
    def test_preview_sem_asset_nao_inventa_logo(self, _logo):
        html = exportacao.renderizar_html(snapshot_controlado())

        self.assertIn('PREVIEW — NÃO PUBLICADO', html)
        self.assertNotIn('<img', html)

    def test_asset_oficial_e_svg_local_sem_recursos_externos(self):
        data_uri = exportacao.carregar_logo_oficial(obrigatoria=True)
        conteudo = base64.b64decode(data_uri.partition(',')[2])
        texto = conteudo.decode('utf-8')

        self.assertEqual(
            exportacao.LOGO_OFICIAL_PATH.name,
            'Logo Escalada.svg',
        )
        self.assertIn('<svg', texto)
        self.assertNotIn('<text', texto)
        self.assertNotIn('<script', texto)
        self.assertNotIn('href=', texto)

    def test_template_escapa_html_arbitrario(self):
        nome = '<script src="https://example.test/x.js">alert(1)</script>'
        snapshot = exportacao.montar_snapshot(
            escopo='PUBLICO',
            periodo='MES',
            layout='MENSAL',
            ano=2027,
            mes=3,
            itens=(item_exportacao('DIA:X', date(2027, 3, 1), nome),),
            gerado_em=GERADO_EM,
        )

        html = exportacao.renderizar_html(snapshot)

        self.assertNotIn('<script src=', html)
        self.assertIn('&lt;script src=', html)

    def test_nomes_de_download_sao_previsiveis_e_sem_dados_pessoais(self):
        self.assertEqual(
            exportacao.nome_arquivo(snapshot_controlado()),
            'calendario-publico-marco-2027.pdf',
        )
        self.assertEqual(
            exportacao.nome_arquivo(snapshot_controlado(
                periodo='ANO',
                layout='MENSAL',
            )),
            'calendario-publico-2027-mensal.pdf',
        )
        self.assertEqual(
            exportacao.nome_arquivo(snapshot_controlado(
                periodo='ANO',
                layout='ANUAL_RESUMIDO',
            )),
            'calendario-publico-2027-resumido.pdf',
        )


class PublicacaoCalendarioServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='publicador',
            password='senha-de-teste',
        )
        self.temp_media = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.settings_override.enable()

    def tearDown(self):
        self.settings_override.disable()
        self.temp_media.cleanup()

    def _publicar(self, **overrides):
        values = {
            'escopo': 'PUBLICO',
            'periodo': 'MES',
            'layout': 'MENSAL',
            'ano': 2027,
            'mes': 3,
            'autor': self.user,
        }
        values.update(overrides)
        with patch.object(
            exportacao,
            'carregar_logo_oficial',
            return_value=TEST_LOGO,
        ):
            return exportacao.publicar_calendario(**values)

    def test_publicacao_persiste_snapshot_pdf_e_sha_dos_bytes(self):
        publicacao = self._publicar()

        with publicacao.arquivo_pdf.open('rb') as arquivo:
            conteudo = arquivo.read()
        self.assertTrue(conteudo.startswith(b'%PDF-'))
        self.assertEqual(publicacao.sha256, hashlib.sha256(conteudo).hexdigest())
        self.assertEqual(publicacao.snapshot['periodo'], 'MES')
        self.assertEqual(publicacao.snapshot['layout'], 'MENSAL')
        self.assertNotIn('PREVIEW', conteudo.decode('latin1', errors='ignore'))

    def test_republicacoes_coexistem_e_publicacao_e_imutavel(self):
        primeira = self._publicar()
        segunda = self._publicar()

        self.assertNotEqual(primeira.pk, segunda.pk)
        self.assertNotEqual(primeira.arquivo_pdf.name, segunda.arquivo_pdf.name)
        primeira.sha256 = 'b' * 64
        with self.assertRaises(ValidationError):
            primeira.save()
        with self.assertRaises(ValidationError):
            primeira.delete()
        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_falha_de_render_nao_cria_publicacao(self):
        with patch.object(
            exportacao,
            'renderizar_pdf',
            side_effect=RuntimeError('falha controlada'),
        ), self.assertRaisesRegex(RuntimeError, 'falha controlada'):
            exportacao.publicar_calendario(
                escopo='PUBLICO',
                periodo='MES',
                layout='MENSAL',
                ano=2027,
                mes=3,
                autor=self.user,
            )
        self.assertFalse(PublicacaoCalendarioInstitucional.objects.exists())
        self.assertEqual(list(Path(self.temp_media.name).rglob('*.pdf')), [])

    def test_falha_de_banco_remove_arquivo_novo(self):
        with patch.object(
            exportacao,
            'carregar_logo_oficial',
            return_value=TEST_LOGO,
        ), patch.object(
            PublicacaoCalendarioInstitucional,
            'save',
            side_effect=IntegrityError('falha controlada'),
        ), self.assertRaises(IntegrityError):
            exportacao.publicar_calendario(
                escopo='PUBLICO',
                periodo='MES',
                layout='MENSAL',
                ano=2027,
                mes=3,
                autor=self.user,
            )
        self.assertFalse(PublicacaoCalendarioInstitucional.objects.exists())
        self.assertEqual(list(Path(self.temp_media.name).rglob('*.pdf')), [])


class PublicacaoCalendarioConstraintTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='autor')

    def _criar(self, **overrides):
        values = {
            'escopo': 'PUBLICO',
            'periodo': PublicacaoCalendarioInstitucional.Periodo.MES,
            'layout': PublicacaoCalendarioInstitucional.Layout.MENSAL,
            'ano': 2027,
            'mes': 3,
            'publicado_por': self.user,
            'snapshot': {'schema_version': 2, 'itens': []},
            'arquivo_pdf': 'calendarios/divulgacoes/2027/mensal/teste.pdf',
            'sha256': 'a' * 64,
        }
        values.update(overrides)
        return PublicacaoCalendarioInstitucional.objects.create(**values)

    def test_constraints_de_periodo_layout_mes_e_escopo(self):
        self._criar()
        for overrides in (
            {'periodo': 'MENSAL', 'layout': 'ANUAL_RESUMIDO'},
            {'periodo': 'ANUAL', 'layout': 'MENSAL', 'mes': 3},
            {'periodo': 'MENSAL', 'layout': 'MENSAL', 'mes': 13},
            {'escopo': 'IRRESTRITO'},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    self._criar(**overrides)

    def test_path_privado_descarta_nome_fornecido(self):
        publicacao = PublicacaoCalendarioInstitucional(
            escopo='INTERNO',
            periodo=PublicacaoCalendarioInstitucional.Periodo.ANO,
            layout=PublicacaoCalendarioInstitucional.Layout.ANUAL_RESUMIDO,
            ano=2027,
            publicado_por=self.user,
        )
        caminho = calendario_publicacao_upload_to(
            publicacao,
            '../../nome-com-dado-pessoal.pdf',
        )

        self.assertRegex(
            caminho,
            r'^calendarios/divulgacoes/2027/anual/[0-9a-f]{32}\.pdf$',
        )
        self.assertNotIn('nome-com-dado-pessoal', caminho)


class PublicacaoCalendarioApiTests(APITestCase):
    preview_url = '/api/calendario-institucional/preview-pdf/'
    publicacoes_url = '/api/calendario-institucional/publicacoes/'

    def setUp(self):
        self.temp_media = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.temp_media.name)
        self.settings_override.enable()
        self.diretoria = self._usuario('diretoria', SiaRole.DIRETORIA)
        self.comunicacao = self._usuario('comunicacao', SiaRole.COMUNICACAO)

    def tearDown(self):
        self.settings_override.disable()
        self.temp_media.cleanup()

    def _usuario(self, username, role=None, *, superuser=False):
        user = get_user_model().objects.create_user(
            username=username,
            password='senha-de-teste',
            is_superuser=superuser,
            is_staff=superuser,
        )
        if role is not None:
            group, _ = Group.objects.get_or_create(name=role.value)
            user.groups.add(group)
        return user

    def _payload(self, **overrides):
        values = {
            'escopo': 'PUBLICO',
            'periodo': 'MES',
            'layout': 'MENSAL',
            'ano': 2027,
            'mes': 3,
        }
        values.update(overrides)
        return values

    def _publicar(self, **overrides):
        self.client.force_authenticate(self.diretoria)
        with patch.object(
            exportacao,
            'carregar_logo_oficial',
            return_value=TEST_LOGO,
        ):
            return self.client.post(
                self.publicacoes_url,
                self._payload(**overrides),
                format='json',
            )

    def test_preview_nao_publica_e_modelo_a_nao_existe_no_contrato(self):
        self.client.force_authenticate(self.diretoria)
        response = self.client.get(self.preview_url, self._payload())
        invalido = self.client.get(
            self.preview_url,
            {**self._payload(), 'modelo_anual': 'A'},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(b''.join(response.streaming_content).startswith(b'%PDF-'))
        self.assertEqual(invalido.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(PublicacaoCalendarioInstitucional.objects.exists())

    def test_publicar_listar_e_baixar_recalcula_sha(self):
        criada = self._publicar()
        self.assertEqual(criada.status_code, status.HTTP_201_CREATED)
        publicacao = PublicacaoCalendarioInstitucional.objects.get()

        lista = self.client.get(self.publicacoes_url)
        download = self.client.get(criada.json()['download_url'])
        conteudo = b''.join(download.streaming_content)

        self.assertEqual(lista.status_code, status.HTTP_200_OK)
        self.assertEqual(lista.json()[0]['publicado_por'], 'diretoria')
        self.assertEqual(download.status_code, status.HTTP_200_OK)
        self.assertEqual(download['Content-Type'], 'application/pdf')
        self.assertIn('calendario-publico-marco-2027.pdf', download['Content-Disposition'])
        self.assertEqual(hashlib.sha256(conteudo).hexdigest(), publicacao.sha256)

    def test_publico_e_acessivel_para_leitura_e_interno_restrito(self):
        publica = self._publicar()
        interna = self._publicar(escopo='INTERNO')
        self.client.force_authenticate(self.comunicacao)

        lista = self.client.get(self.publicacoes_url)
        lista_interna = self.client.get(self.publicacoes_url, {'escopo': 'INTERNO'})
        download_publico = self.client.get(publica.json()['download_url'])
        download_interno = self.client.get(interna.json()['download_url'])

        self.assertEqual([item['escopo'] for item in lista.json()], ['PUBLICO'])
        self.assertEqual(lista_interna.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(download_publico.status_code, status.HTTP_200_OK)
        self.assertEqual(download_interno.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_only_nao_gera_preview_nem_publica(self):
        self.client.force_authenticate(self.comunicacao)

        self.assertEqual(
            self.client.get(self.preview_url, self._payload()).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                self.publicacoes_url,
                self._payload(),
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_suporte_e_superuser_podem_publicar(self):
        suporte = self._usuario('suporte', SiaRole.SUPORTE)
        superuser = self._usuario('superuser', superuser=True)

        for usuario in (suporte, superuser):
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(usuario)
                with patch.object(
                    exportacao,
                    'carregar_logo_oficial',
                    return_value=TEST_LOGO,
                ):
                    resposta = self.client.post(
                        self.publicacoes_url,
                        self._payload(),
                        format='json',
                    )
                self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)

    def test_anonimo_recebe_401(self):
        self.client.force_authenticate(user=None)

        self.assertEqual(
            self.client.get(self.publicacoes_url).status_code,
            status.HTTP_401_UNAUTHORIZED,
        )
