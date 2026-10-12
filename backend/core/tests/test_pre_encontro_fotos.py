from datetime import date, time, timedelta
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from core.models import (
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    EventoAuditoriaEncontro,
    FotoTemporariaPreEncontro,
    Pessoa,
    PreEncontro,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoUsuarioPessoa,
)
from core.roles import SiaRole
from core.services import pre_encontro as pre_encontro_services
from core.tests.factories import make_encontro


class PreEncontroFotoTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.settings_override = override_settings(MEDIA_ROOT=self.media.name)
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        self.addCleanup(self.media.cleanup)
        self.client = APIClient()
        self.fichas = self._usuario('fichas-foto', SiaRole.FICHAS)
        self.comunicacao = self._usuario(
            'comunicacao-foto',
            SiaRole.COMUNICACAO,
        )
        self.diretoria = self._usuario('diretoria-foto', SiaRole.DIRETORIA)
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.pre = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 1, 1),
            horario=time(14),
            local='Local do Pré',
        )
        agora = timezone.now()
        ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=10,
            idade_minima=15,
            idade_maxima=17,
            inscricoes_abrem_em=agora - timedelta(days=1),
            inscricoes_encerram_em=agora + timedelta(days=1),
        )
        self.atendimento = (
            pre_encontro_services.registrar_checkin_pre_encontro(
                usuario=self.fichas,
                pre_encontro=self.pre,
                nome_informado='Pessoa sem resolução',
                data_nascimento_informada=date(2000, 1, 1),
                telefone_informado='61999990000',
            )
        )

    def _usuario(self, username, role):
        usuario = User.objects.create_user(username)
        grupo, _ = Group.objects.get_or_create(name=role.value)
        usuario.groups.add(grupo)
        return usuario

    def _imagem(self, nome='foto.png', cor='white'):
        arquivo = BytesIO()
        Image.new('RGB', (3, 3), cor).save(arquivo, format='PNG')
        return SimpleUploadedFile(
            nome,
            arquivo.getvalue(),
            content_type='image/png',
        )

    def _url(self, sufixo='foto/', *, encontro=None, atendimento=None):
        encontro = encontro or self.encontro
        atendimento = atendimento or self.atendimento
        return (
            f'/api/encontros/{encontro.pk}/pre-encontro/atendimentos/'
            f'{atendimento.pk}/{sufixo}'
        )

    def _upload(self, usuario=None, nome='foto.png', cor='white'):
        self.client.force_authenticate(usuario or self.fichas)
        return self.client.put(
            self._url(),
            {'foto': self._imagem(nome, cor)},
            format='multipart',
        )

    def _arquivos(self):
        return {
            str(item.relative_to(self.media.name))
            for item in Path(self.media.name).rglob('*')
            if item.is_file()
        }

    def _coordenacao(self):
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=self.encontro.tipo,
            codigo='coord-foto-template',
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
        pessoa = Pessoa.objects.create(nome='Pessoa coordenadora')
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
        usuario = User.objects.create_user('coordenacao-foto')
        VinculoUsuarioPessoa.objects.create(usuario=usuario, pessoa=pessoa)
        return usuario

    def test_upload_e_preview_privados_funcionam_antes_de_existir_pessoa(self):
        self.assertIsNone(self.atendimento.pessoa_id)
        upload = self._upload()
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )

        preview = self.client.get(self._url())

        self.assertEqual(upload.status_code, status.HTTP_200_OK)
        self.assertEqual(preview.status_code, status.HTTP_200_OK)
        self.assertEqual(b''.join(preview.streaming_content)[:4], b'\x89PNG')
        self.assertEqual(preview['Cache-Control'], 'private, no-store')
        self.assertEqual(preview['X-Content-Type-Options'], 'nosniff')
        self.assertNotIn('/media/', str(preview.headers))
        self.assertNotIn(foto.arquivo.name, str(upload.data))
        self.assertEqual(len(self._arquivos()), 1)

    def test_regularizacao_associa_mesma_chave_sem_copiar_e_preserva_origem(self):
        self._upload()
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )
        chave = foto.arquivo.name
        arquivos_antes = self._arquivos()
        pessoa = Pessoa.objects.create(nome='Pessoa regularizada')

        regularizado = (
            pre_encontro_services.regularizar_atendimento_pre_encontro(
                usuario=self.fichas,
                atendimento=self.atendimento,
                pessoa=pessoa,
            )
        )

        pessoa.refresh_from_db()
        foto.refresh_from_db()
        self.assertEqual(regularizado.pessoa_id, pessoa.pk)
        self.assertEqual(pessoa.foto.name, chave)
        self.assertEqual(foto.arquivo.name, chave)
        self.assertEqual(self._arquivos(), arquivos_antes)
        self.assertTrue(
            EventoAuditoriaEncontro.objects.filter(
                fato='pre_encontro.foto_associada_pessoa_automaticamente',
                objeto_id=pessoa.pk,
            ).exists()
        )

    def test_regularizacao_preserva_foto_existente_da_pessoa_e_foto_do_pre(self):
        pessoa = Pessoa.objects.create(nome='Pessoa com foto')
        pessoa.foto.save('existente.png', self._imagem('existente.png', 'red'))
        chave_pessoa = pessoa.foto.name
        self._upload(cor='blue')
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )

        pre_encontro_services.regularizar_atendimento_pre_encontro(
            usuario=self.fichas,
            atendimento=self.atendimento,
            pessoa=pessoa,
        )

        pessoa.refresh_from_db()
        foto.refresh_from_db()
        self.assertEqual(pessoa.foto.name, chave_pessoa)
        self.assertNotEqual(foto.arquivo.name, chave_pessoa)
        self.assertTrue(pessoa.foto.storage.exists(chave_pessoa))
        self.assertTrue(foto.arquivo.storage.exists(foto.arquivo.name))

    def test_associacao_explicita_substitui_sem_copia_move_e_e_idempotente(self):
        pessoa = Pessoa.objects.create(nome='Pessoa explícita')
        pessoa.foto.save('anterior.png', self._imagem('anterior.png', 'red'))
        chave_anterior = pessoa.foto.name
        self.atendimento.pessoa = pessoa
        self.atendimento.save(update_fields=['pessoa', 'atualizado_em'])
        self._upload(cor='blue')
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )
        chave_pre = foto.arquivo.name
        self.client.force_authenticate(self.fichas)

        with self.captureOnCommitCallbacks(execute=True):
            primeira = self.client.post(
                self._url('foto/usar-na-pessoa/'),
                {},
                format='json',
            )
        segunda = self.client.post(
            self._url('foto/usar-na-pessoa/'),
            {},
            format='json',
        )

        pessoa.refresh_from_db()
        foto.refresh_from_db()
        self.assertEqual(primeira.status_code, status.HTTP_200_OK)
        self.assertEqual(segunda.status_code, status.HTTP_200_OK)
        self.assertEqual(pessoa.foto.name, chave_pre)
        self.assertEqual(foto.arquivo.name, chave_pre)
        self.assertFalse(pessoa.foto.storage.exists(chave_anterior))
        self.assertEqual(self._arquivos(), {chave_pre})
        self.assertEqual(
            EventoAuditoriaEncontro.objects.filter(
                fato='pre_encontro.foto_associada_pessoa',
                objeto_id=pessoa.pk,
            ).count(),
            1,
        )

    def test_substituicao_preserva_arquivo_antigo_referenciado_pela_pessoa(self):
        self._upload(nome='a.png', cor='red')
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )
        chave_a = foto.arquivo.name
        pessoa = Pessoa.objects.create(nome='Pessoa compartilhada')
        pre_encontro_services.regularizar_atendimento_pre_encontro(
            usuario=self.fichas,
            atendimento=self.atendimento,
            pessoa=pessoa,
        )

        with self.captureOnCommitCallbacks(execute=True):
            self._upload(nome='b.png', cor='blue')

        pessoa.refresh_from_db()
        foto.refresh_from_db()
        self.assertEqual(pessoa.foto.name, chave_a)
        self.assertNotEqual(foto.arquivo.name, chave_a)
        self.assertTrue(foto.arquivo.storage.exists(chave_a))
        self.assertEqual(len(self._arquivos()), 2)

    def test_substituicao_remove_antigo_sem_referencia_somente_apos_commit(self):
        self._upload(nome='a.png', cor='red')
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )
        chave_a = foto.arquivo.name

        with self.captureOnCommitCallbacks(execute=False) as callbacks:
            self._upload(nome='b.png', cor='blue')
        foto.refresh_from_db()
        chave_b = foto.arquivo.name
        self.assertTrue(foto.arquivo.storage.exists(chave_a))
        self.assertTrue(foto.arquivo.storage.exists(chave_b))
        for callback in callbacks:
            callback()
        self.assertFalse(foto.arquivo.storage.exists(chave_a))
        self.assertTrue(foto.arquivo.storage.exists(chave_b))

    def test_falha_no_cleanup_pos_commit_preserva_estado_correto_do_banco(self):
        self._upload(nome='a.png', cor='red')
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )
        chave_a = foto.arquivo.name

        with patch.object(
            foto.arquivo.storage,
            'delete',
            side_effect=OSError('falha controlada de storage'),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                resposta = self._upload(nome='b.png', cor='blue')

        foto.refresh_from_db()
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertNotEqual(foto.arquivo.name, chave_a)
        self.assertTrue(foto.arquivo.storage.exists(foto.arquivo.name))
        self.assertTrue(foto.arquivo.storage.exists(chave_a))

    def test_falha_transacional_limpa_novo_upload_e_preserva_anterior(self):
        self._upload(nome='anterior.png', cor='red')
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )
        chave_anterior = foto.arquivo.name
        arquivos_antes = self._arquivos()

        with patch(
            'core.services.pre_encontro._auditar',
            side_effect=RuntimeError('falha controlada'),
        ):
            with self.assertRaises(RuntimeError):
                pre_encontro_services.registrar_foto_pre_encontro(
                    usuario=self.fichas,
                    atendimento=self.atendimento,
                    arquivo=self._imagem('nova.png', 'blue'),
                )

        foto.refresh_from_db()
        self.assertEqual(foto.arquivo.name, chave_anterior)
        self.assertEqual(self._arquivos(), arquivos_antes)
        self.assertTrue(foto.arquivo.storage.exists(chave_anterior))

    def test_arquivo_ausente_falha_seguro_sem_impedir_regularizacao(self):
        self._upload()
        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )
        foto.arquivo.storage.delete(foto.arquivo.name)
        pessoa = Pessoa.objects.create(nome='Pessoa com arquivo ausente')
        self.atendimento.pessoa = pessoa
        self.atendimento.save(update_fields=['pessoa', 'atualizado_em'])
        self.client.force_authenticate(self.fichas)

        preview = self.client.get(self._url())
        associacao = self.client.post(
            self._url('foto/usar-na-pessoa/'),
            {},
            format='json',
        )
        pessoa.refresh_from_db()
        self.assertEqual(preview.status_code, status.HTTP_404_NOT_FOUND)
        self.assertNotIn(foto.arquivo.name, repr(preview.data))
        self.assertEqual(associacao.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(pessoa.foto)

        outro_atendimento = (
            pre_encontro_services.registrar_checkin_pre_encontro(
                usuario=self.fichas,
                pre_encontro=self.pre,
                nome_informado='Outra identidade',
                data_nascimento_informada=date(2001, 1, 1),
                telefone_informado='61999990001',
            )
        )
        outra_foto = pre_encontro_services.registrar_foto_pre_encontro(
            usuario=self.fichas,
            atendimento=outro_atendimento,
            arquivo=self._imagem('ausente.png'),
        )
        outra_foto.arquivo.storage.delete(outra_foto.arquivo.name)
        outra_pessoa = Pessoa.objects.create(nome='Regularização continua')
        regularizado = (
            pre_encontro_services.regularizar_atendimento_pre_encontro(
                usuario=self.fichas,
                atendimento=outro_atendimento,
                pessoa=outra_pessoa,
            )
        )
        outra_pessoa.refresh_from_db()
        self.assertEqual(regularizado.pessoa_id, outra_pessoa.pk)
        self.assertFalse(outra_pessoa.foto)
        self.assertTrue(
            FotoTemporariaPreEncontro.objects.filter(pk=outra_foto.pk).exists()
        )

    def test_associacao_autorizada_para_fichas_comunicacao_e_coordenacao(self):
        pessoa = Pessoa.objects.create(nome='Pessoa autorizada')
        self.atendimento.pessoa = pessoa
        self.atendimento.save(update_fields=['pessoa', 'atualizado_em'])
        self._upload()
        coordenacao = self._coordenacao()

        for usuario in (self.fichas, self.comunicacao, coordenacao):
            pessoa.foto = None
            pessoa.save(update_fields=['foto'])
            self.client.force_authenticate(usuario)
            resposta = self.client.post(
                self._url('foto/usar-na-pessoa/'),
                {},
                format='json',
            )
            self.assertEqual(resposta.status_code, status.HTTP_200_OK)

        pessoa.foto = None
        pessoa.save(update_fields=['foto'])
        self.client.force_authenticate(self.diretoria)
        negada = self.client.post(
            self._url('foto/usar-na-pessoa/'),
            {},
            format='json',
        )
        self.assertEqual(negada.status_code, status.HTTP_403_FORBIDDEN)
        with self.assertRaises(PermissionDenied):
            pre_encontro_services.usar_foto_pre_encontro_como_foto_pessoa(
                usuario=self.diretoria,
                atendimento=self.atendimento,
            )

    def test_nested_mismatch_retorna_404_e_nao_expoe_idor(self):
        pessoa = Pessoa.objects.create(nome='Pessoa IDOR')
        self.atendimento.pessoa = pessoa
        self.atendimento.save(update_fields=['pessoa', 'atualizado_em'])
        self._upload()
        outro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        PreEncontro.objects.create(
            encontro=outro,
            data=date(2030, 2, 1),
            horario=time(14),
            local='Outro local',
        )
        self.client.force_authenticate(self.fichas)

        for metodo, sufixo, dados in (
            ('get', 'foto/', None),
            ('put', 'foto/', {'foto': self._imagem('idor.png')}),
            ('post', 'foto/usar-na-pessoa/', {}),
        ):
            resposta = getattr(self.client, metodo)(
                self._url(sufixo, encontro=outro),
                data=dados,
                format='multipart' if metodo == 'put' else 'json',
            )
            self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_capability_explicita_exige_pessoa_foto_arquivo_lifecycle_e_policy(self):
        self._upload()
        detalhe_url = self._url('')
        self.client.force_authenticate(self.fichas)
        sem_pessoa = self.client.get(detalhe_url).data['capabilities']
        self.assertFalse(sem_pessoa['associar_foto_pessoa'])

        pessoa = Pessoa.objects.create(nome='Pessoa capability')
        self.atendimento.pessoa = pessoa
        self.atendimento.save(update_fields=['pessoa', 'atualizado_em'])
        permitida = self.client.get(detalhe_url).data['capabilities']
        self.assertTrue(permitida['associar_foto_pessoa'])
        self.assertNotIn('roles', permitida)

        self.client.force_authenticate(self.diretoria)
        negada = self.client.get(detalhe_url).data['capabilities']
        self.assertFalse(negada['associar_foto_pessoa'])

        foto = FotoTemporariaPreEncontro.objects.get(
            atendimento=self.atendimento,
        )
        foto.arquivo.storage.delete(foto.arquivo.name)
        self.client.force_authenticate(self.fichas)
        ausente = self.client.get(detalhe_url).data['capabilities']
        self.assertFalse(ausente['associar_foto_pessoa'])

    def test_command_rejeita_storage_key_e_media_publica_nao_existe(self):
        pessoa = Pessoa.objects.create(nome='Pessoa sem path do client')
        self.atendimento.pessoa = pessoa
        self.atendimento.save(update_fields=['pessoa', 'atualizado_em'])
        self._upload()
        self.client.force_authenticate(self.fichas)

        resposta = self.client.post(
            self._url('foto/usar-na-pessoa/'),
            {'path': 'pre_encontros/fotos/forjada', 'pessoa_id': pessoa.pk},
            format='json',
        )
        publico = self.client.get('/media/pre_encontros/fotos/forjada')

        pessoa.refresh_from_db()
        self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(pessoa.foto)
        self.assertNotIn('pre_encontros/fotos', repr(resposta.data))
        self.assertEqual(publico.status_code, status.HTTP_404_NOT_FOUND)
