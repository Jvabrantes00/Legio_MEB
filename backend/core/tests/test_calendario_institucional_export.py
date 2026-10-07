from datetime import UTC, date, datetime, time

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    AvaliacaoEncontro,
    PublicacaoCalendarioInstitucional,
    ReuniaoPreparatoriaEncontro,
    calendario_publicacao_upload_to,
)
from core.roles import SiaRole
from core.services.exportacao_calendario import (
    ESCOPO_INTERNO,
    ESCOPO_PUBLICO,
    MODELO_ANUAL_A,
    MODELO_ANUAL_B,
    PERIODO_ANUAL,
    PERIODO_MENSAL,
    ItemExportacaoCalendario,
    capturar_snapshot,
    montar_snapshot,
    renderizar_documento,
    renderizar_html,
    renderizar_pdf,
    sha256_pdf,
)
from core.tests.test_calendario_institucional import criar_encontro_canonico


GERADO_EM = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


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
    return ItemExportacaoCalendario(
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

    def test_publico_consume_publicabilidade_canonica(self):
        snapshot = capturar_snapshot(
            escopo=ESCOPO_PUBLICO,
            periodo=PERIODO_MENSAL,
            ano=2027,
            mes=3,
            gerado_em=GERADO_EM,
        )

        self.assertEqual(len(snapshot.itens), 1)
        self.assertEqual(snapshot.itens[0].origem, 'DIA_ENCONTRO')
        self.assertEqual(snapshot.itens[0].rotulo, 'Pré-Escalada')
        self.assertTrue(snapshot.itens[0].provisorio)

    def test_interno_inclui_preparatoria_e_avaliacao_com_termo_aprovado(self):
        snapshot = capturar_snapshot(
            escopo=ESCOPO_INTERNO,
            periodo=PERIODO_MENSAL,
            ano=2027,
            mes=3,
            gerado_em=GERADO_EM,
        )

        por_origem = {item.origem: item for item in snapshot.itens}
        self.assertEqual(
            por_origem['REUNIAO_PREPARATORIA'].rotulo,
            '3ª Preparatória',
        )
        self.assertEqual(
            por_origem['REUNIAO_PREPARATORIA'].complemento,
            'Missa de Entrega',
        )
        self.assertEqual(por_origem['AVALIACAO'].rotulo, 'Avaliação')
        html = renderizar_html(snapshot)
        self.assertIn('3ª Preparatória', html)
        self.assertNotIn('3ª Reunião', html)

    def test_snapshot_e_imutavel_serializavel_e_sem_dados_pessoais(self):
        snapshot = capturar_snapshot(
            escopo=ESCOPO_INTERNO,
            periodo=PERIODO_MENSAL,
            ano=2027,
            mes=3,
            gerado_em=GERADO_EM,
        )
        serializado = snapshot.as_dict()
        texto = str(serializado).casefold()

        self.assertIsInstance(snapshot.itens, tuple)
        self.assertEqual(serializado['schema_version'], 1)
        self.assertEqual(serializado['escopo'], 'INTERNO')
        for campo in (
            'participante', 'equipe', 'presença', 'saúde', 'telefone',
            'email', 'cpf',
        ):
            self.assertNotIn(campo, texto)


class RendererCalendarioTests(TestCase):
    def _snapshot(self, *, escopo=ESCOPO_PUBLICO, periodo=PERIODO_MENSAL):
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
        return montar_snapshot(
            escopo=escopo,
            periodo=periodo,
            ano=2027,
            mes=3 if periodo == PERIODO_MENSAL else None,
            itens=itens,
            gerado_em=GERADO_EM,
        )

    def test_mensal_gera_pdf_valido_a4_paisagem_com_overflow_resumido(self):
        snapshot = self._snapshot()
        html = renderizar_html(snapshot)
        documento = renderizar_documento(snapshot)
        pdf = documento.write_pdf()

        self.assertTrue(pdf.startswith(b'%PDF-'))
        self.assertEqual(len(documento.pages), 1)
        self.assertGreater(documento.pages[0].width, documento.pages[0].height)
        self.assertIn('@page { size: A4 landscape;', html)
        self.assertIn('Escalada 2027 *', html)
        self.assertIn('* Data ainda sujeita a confirmação.', html)
        self.assertNotIn('Confirmado', html)
        self.assertIn('+ outros compromissos neste dia', html)
        self.assertIn('overflow-wrap: anywhere', html)

    def test_anual_a_e_b_usam_o_mesmo_snapshot_sem_escolha_automatica(self):
        snapshot = self._snapshot(periodo=PERIODO_ANUAL)
        antes = snapshot.as_dict()
        documento_a = renderizar_documento(
            snapshot,
            modelo_anual=MODELO_ANUAL_A,
        )
        documento_b = renderizar_documento(
            snapshot,
            modelo_anual=MODELO_ANUAL_B,
        )
        html_a = renderizar_html(snapshot, modelo_anual=MODELO_ANUAL_A)
        html_b = renderizar_html(snapshot, modelo_anual=MODELO_ANUAL_B)

        self.assertEqual(snapshot.as_dict(), antes)
        self.assertEqual(len(documento_a.pages), 1)
        self.assertEqual(len(documento_b.pages), 1)
        self.assertIn('model-a', html_a)
        self.assertIn('mini-entry', html_a)
        self.assertIn('model-b', html_b)
        self.assertIn('compact-agenda', html_b)
        self.assertNotEqual(html_a, html_b)

    def test_template_escapa_texto_e_renderer_bloqueia_markup(self):
        nome = '<script src="https://example.test/x.js">alert(1)</script>'
        snapshot = montar_snapshot(
            escopo=ESCOPO_PUBLICO,
            periodo=PERIODO_MENSAL,
            ano=2027,
            mes=3,
            itens=(
                item_exportacao('DIA:X', date(2027, 3, 1), nome),
            ),
            gerado_em=GERADO_EM,
        )

        html = renderizar_html(snapshot)
        pdf = renderizar_pdf(snapshot)

        self.assertNotIn('<script src=', html)
        self.assertIn('&lt;script src=', html)
        self.assertTrue(pdf.startswith(b'%PDF-'))

    def test_sha256_e_calculado_sobre_os_bytes_finais(self):
        pdf = renderizar_pdf(self._snapshot())

        digest = sha256_pdf(pdf)

        self.assertEqual(len(digest), 64)
        self.assertEqual(digest, sha256_pdf(pdf))
        self.assertNotEqual(digest, sha256_pdf(pdf + b'alterado'))


class PreviewCalendarioApiTests(APITestCase):
    url = '/api/calendario-institucional/preview-pdf/'

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

    def _get(self, **overrides):
        params = {
            'escopo': 'PUBLICO',
            'periodo': 'MENSAL',
            'ano': 2027,
            'mes': 3,
        }
        params.update(overrides)
        return self.client.get(self.url, params)

    def test_diretoria_suporte_e_superuser_geram_preview_sem_publicar(self):
        usuarios = (
            self._usuario('diretoria', SiaRole.DIRETORIA),
            self._usuario('suporte', SiaRole.SUPORTE),
            self._usuario('superuser', superuser=True),
        )
        for usuario in usuarios:
            with self.subTest(usuario=usuario.username):
                self.client.force_authenticate(usuario)
                response = self._get()
                conteudo = b''.join(response.streaming_content)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(response['Content-Type'], 'application/pdf')
                self.assertEqual(response['Cache-Control'], 'no-store, private')
                self.assertTrue(conteudo.startswith(b'%PDF-'))
        self.assertEqual(PublicacaoCalendarioInstitucional.objects.count(), 0)

    def test_outros_papeis_e_anonimo_nao_geram_preview(self):
        comunicacao = self._usuario('comunicacao', SiaRole.COMUNICACAO)
        self.client.force_authenticate(comunicacao)
        self.assertEqual(self._get().status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=None)
        self.assertEqual(self._get().status_code, status.HTTP_401_UNAUTHORIZED)

    def test_query_mensal_e_anual_e_estrita(self):
        self.client.force_authenticate(
            self._usuario('diretoria-query', SiaRole.DIRETORIA)
        )
        casos_invalidos = (
            {'mes': None},
            {'modelo_anual': 'A'},
            {'periodo': 'ANUAL', 'mes': 3, 'modelo_anual': 'A'},
            {'periodo': 'ANUAL', 'mes': None},
            {'extra': 'x'},
        )
        for overrides in casos_invalidos:
            params = {
                'escopo': 'PUBLICO',
                'periodo': 'MENSAL',
                'ano': 2027,
                'mes': 3,
            }
            params.update(overrides)
            params = {k: v for k, v in params.items() if v is not None}
            with self.subTest(params=params):
                self.assertEqual(
                    self.client.get(self.url, params).status_code,
                    status.HTTP_400_BAD_REQUEST,
                )


class PublicacaoCalendarioFoundationTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='publicador',
            password='senha-de-teste',
        )

    def _publicacao(self, **overrides):
        values = {
            'escopo': 'PUBLICO',
            'periodo': 'MENSAL',
            'ano': 2027,
            'mes': 3,
            'publicado_por': self.user,
            'snapshot': {'schema_version': 1, 'itens': []},
            'arquivo_pdf': 'calendarios/divulgacoes/2027/mensal/teste.pdf',
            'sha256': 'a' * 64,
        }
        values.update(overrides)
        return PublicacaoCalendarioInstitucional.objects.create(**values)

    def test_republicacoes_do_mes_coexistem_e_autor_e_protegido(self):
        primeira = self._publicacao()
        segunda = self._publicacao(sha256='b' * 64)

        self.assertNotEqual(primeira.pk, segunda.pk)
        with self.assertRaises(ProtectedError):
            self.user.delete()

    def test_constraint_periodo_mes(self):
        self._publicacao(
            periodo='ANUAL',
            mes=None,
            arquivo_pdf='calendarios/divulgacoes/2027/anual/teste.pdf',
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._publicacao(periodo='ANUAL', mes=3)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._publicacao(mes=13)
        with self.assertRaises(IntegrityError), transaction.atomic():
            self._publicacao(escopo='IRRESTRITO')

    def test_path_privado_nao_reutiliza_nome_fornecido(self):
        publicacao = PublicacaoCalendarioInstitucional(
            escopo='INTERNO',
            periodo='ANUAL',
            ano=2027,
            mes=None,
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
