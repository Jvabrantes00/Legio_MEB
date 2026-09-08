from io import BytesIO
import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import FotoEncontro, Palestra
from core.roles import SiaRole
from core.tests.factories import make_alpinista, make_encontro


class ProtectedMediaAuthorizationTests(APITestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_root = tempfile.mkdtemp(prefix='sia-protected-media-')
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        try:
            super().tearDownClass()
        finally:
            cls.media_override.disable()
            shutil.rmtree(cls.media_root, ignore_errors=True)

    def make_user(self, username, *roles, is_superuser=False):
        user = get_user_model().objects.create_user(
            username=username,
            password='senha-exclusiva-de-teste',
            is_superuser=is_superuser,
            is_staff=is_superuser,
        )
        for role in roles:
            group, _ = Group.objects.get_or_create(name=role.value)
            user.groups.add(group)
        return user

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def make_image(self, name='imagem.png', color='blue'):
        content = BytesIO()
        Image.new('RGB', (20, 20), color=color).save(content, format='PNG')
        return SimpleUploadedFile(
            name,
            content.getvalue(),
            content_type='image/png',
        )

    def test_todos_os_papeis_resumidos_e_administrativos_leem_foto_protegida(self):
        alpinista = make_alpinista(foto=self.make_image('perfil.png'))
        expected_content = bytes(alpinista.foto.read())
        url = f'/api/alpinistas/{alpinista.pk}/foto-arquivo/'

        for index, role in enumerate(SiaRole):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'leitor-foto-{index}', role))
                response = self.client.get(url)
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertEqual(b''.join(response.streaming_content), expected_content)

        self.authenticate(self.make_user('superuser-foto', is_superuser=True))
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

    def test_foto_de_alpinista_exige_autenticacao_e_papel(self):
        alpinista = make_alpinista(foto=self.make_image())
        url = f'/api/alpinistas/{alpinista.pk}/foto-arquivo/'

        self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.authenticate(self.make_user('foto-sem-papel'))
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    def test_alpinista_sem_foto_retorna_null_no_perfil_e_404_no_arquivo(self):
        alpinista = make_alpinista(foto=None)
        self.authenticate(self.make_user('sem-foto', SiaRole.COMUNICACAO))

        perfil = self.client.get(f'/api/alpinistas/{alpinista.pk}/')
        arquivo = self.client.get(f'/api/alpinistas/{alpinista.pk}/foto-arquivo/')

        self.assertEqual(perfil.status_code, status.HTTP_200_OK)
        self.assertIsNone(perfil.json()['foto'])
        self.assertEqual(arquivo.status_code, status.HTTP_404_NOT_FOUND)

    def test_serializer_aponta_para_endpoint_protegido_e_media_publica_nao_existe(self):
        alpinista = make_alpinista(foto=self.make_image('nao-publica.png'))
        self.authenticate(self.make_user('url-protegida', SiaRole.MME))

        perfil = self.client.get(f'/api/alpinistas/{alpinista.pk}/')
        foto_url = perfil.json()['foto']

        self.assertIn(
            f'/api/alpinistas/{alpinista.pk}/foto-arquivo/',
            foto_url,
        )
        self.assertNotIn('/media/', foto_url)
        self.client.force_authenticate(user=None)
        self.assertEqual(
            self.client.get(f'/media/{alpinista.foto.name}').status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_matriz_de_leitura_do_arquivo_da_galeria(self):
        encontro = make_encontro()
        foto = FotoEncontro.objects.create(
            encontro=encontro,
            imagem=self.make_image('galeria.png'),
        )
        url = f'/api/encontros/{encontro.pk}/fotos/{foto.pk}/arquivo/'
        permitidos = (SiaRole.SUPORTE, SiaRole.DIRETORIA, SiaRole.COMUNICACAO)
        bloqueados = (
            SiaRole.FICHAS,
            SiaRole.MME,
            SiaRole.FORMACAO,
            SiaRole.SECRETARIA,
            SiaRole.ACAO_SOCIAL,
            SiaRole.LITURGIA,
            SiaRole.EVENTOS,
        )

        for index, role in enumerate(permitidos):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'galeria-leitor-{index}', role))
                self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        self.authenticate(self.make_user('galeria-superuser', is_superuser=True))
        self.assertEqual(self.client.get(url).status_code, status.HTTP_200_OK)

        for index, role in enumerate(bloqueados):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'galeria-bloqueado-{index}', role))
                self.assertEqual(
                    self.client.get(url).status_code,
                    status.HTTP_403_FORBIDDEN,
                )

        self.client.force_authenticate(user=None)
        self.assertEqual(self.client.get(url).status_code, status.HTTP_401_UNAUTHORIZED)
        self.authenticate(self.make_user('galeria-arquivo-sem-papel'))
        self.assertEqual(self.client.get(url).status_code, status.HTTP_403_FORBIDDEN)

    def test_serializer_da_galeria_aponta_para_arquivo_protegido(self):
        encontro = make_encontro()
        foto = FotoEncontro.objects.create(
            encontro=encontro,
            imagem=self.make_image('galeria-protegida.png'),
        )
        self.authenticate(self.make_user('galeria-url', SiaRole.COMUNICACAO))

        response = self.client.get(f'/api/encontros/{encontro.pk}/fotos/')
        imagem_url = response.json()[0]['imagem']

        self.assertIn(
            f'/api/encontros/{encontro.pk}/fotos/{foto.pk}/arquivo/',
            imagem_url,
        )
        self.assertNotIn('/media/', imagem_url)

    def test_arquivo_da_galeria_confirma_foto_e_encontro_contra_idor(self):
        encontro = make_encontro()
        outro_encontro = make_encontro()
        foto = FotoEncontro.objects.create(
            encontro=outro_encontro,
            imagem=self.make_image('outro.png'),
        )
        self.authenticate(self.make_user('galeria-arquivo-idor', SiaRole.COMUNICACAO))

        response = self.client.get(
            f'/api/encontros/{encontro.pk}/fotos/{foto.pk}/arquivo/'
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_nao_existe_endpoint_generico_para_path_de_arquivo(self):
        self.authenticate(self.make_user('sem-path-arbitrario', SiaRole.SUPORTE))

        self.assertEqual(
            self.client.get('/api/media-protegida/fotos/qualquer.png').status_code,
            status.HTTP_404_NOT_FOUND,
        )
        self.assertEqual(
            self.client.get('/api/media-protegida/../.env').status_code,
            status.HTTP_404_NOT_FOUND,
        )


class AlpinistaQueryAuthorizationTests(APITestCase):
    def make_user(self, username, *roles):
        user = get_user_model().objects.create_user(
            username=username,
            password='senha-exclusiva-de-teste',
        )
        for role in roles:
            group, _ = Group.objects.get_or_create(name=role.value)
            user.groups.add(group)
        return user

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def result_ids(self, response):
        return [item['id'] for item in response.json()['results']]

    def test_papeis_resumidos_nao_pesquisam_por_email(self):
        alvo = make_alpinista(
            nome='Pessoa sem email no nome',
            email='endereco-secreto@example.test',
        )

        for index, role in enumerate((SiaRole.COMUNICACAO, SiaRole.MME)):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'sem-email-{index}', role))
                response = self.client.get(
                    '/api/alpinistas/?search=endereco-secreto@example.test'
                )
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertNotIn(alvo.pk, self.result_ids(response))

    def test_papel_resumido_pesquisa_campos_operacionais_visiveis(self):
        alvo = make_alpinista(
            nome='Maria Operacional',
            telefone='61987654321',
            grupo='Grupo Visível',
        )
        self.authenticate(self.make_user('busca-operacional', SiaRole.LITURGIA))

        for termo in ('Maria Operacional', '61987654321', 'Grupo Visível'):
            with self.subTest(termo=termo):
                response = self.client.get('/api/alpinistas/', {'search': termo})
                self.assertEqual(response.status_code, status.HTTP_200_OK)
                self.assertIn(alvo.pk, self.result_ids(response))

    def test_secretaria_nao_pode_filtrar_status(self):
        self.authenticate(self.make_user('status-proibido', SiaRole.SECRETARIA))

        response = self.client.get('/api/alpinistas/?status=pendente')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_comunicacao_e_eventos_nao_podem_inferir_palestras(self):
        for index, role in enumerate((SiaRole.COMUNICACAO, SiaRole.EVENTOS)):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'palestrou-proibido-{index}', role))
                response = self.client.get('/api/alpinistas/?palestrou=true')
                self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_formacao_pode_filtrar_palestrantes(self):
        palestrante = make_alpinista()
        nao_palestrante = make_alpinista()
        Palestra.objects.create(
            alpinista=palestrante,
            encontro=make_encontro(),
            titulo='Palestra autorizada',
        )
        self.authenticate(self.make_user('formacao-filtro-autorizado', SiaRole.FORMACAO))

        response = self.client.get('/api/alpinistas/?palestrou=true')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn(palestrante.pk, self.result_ids(response))
        self.assertNotIn(nao_palestrante.pk, self.result_ids(response))

    def test_mme_pode_combinar_filtros_musicais(self):
        alvo = make_alpinista(eh_violeiro=True, canta=True)
        make_alpinista(eh_violeiro=True, canta=False)
        self.authenticate(self.make_user('mme-filtros-autorizados', SiaRole.MME))

        resposta_violeiro = self.client.get('/api/alpinistas/?eh_violeiro=true')
        resposta_canta = self.client.get('/api/alpinistas/?canta=true')
        resposta_ambos = self.client.get(
            '/api/alpinistas/?eh_violeiro=true&canta=true'
        )

        for response in (resposta_violeiro, resposta_canta, resposta_ambos):
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertIn(alvo.pk, self.result_ids(response))

    def test_papeis_administrativos_preservam_busca_e_filtros(self):
        alvo = make_alpinista(
            nome='Alvo Administrativo',
            email='administrativo-secreto@example.test',
            status='ativo',
            eh_violeiro=True,
            canta=True,
        )
        Palestra.objects.create(
            alpinista=alvo,
            encontro=make_encontro(),
            titulo='Histórico administrativo',
        )

        for index, role in enumerate(
            (SiaRole.SUPORTE, SiaRole.DIRETORIA, SiaRole.FICHAS)
        ):
            with self.subTest(role=role.value):
                self.authenticate(self.make_user(f'filtro-admin-{index}', role))
                urls = (
                    '/api/alpinistas/?search=administrativo-secreto@example.test',
                    '/api/alpinistas/?status=ativo',
                    '/api/alpinistas/?eh_violeiro=true&canta=true',
                    '/api/alpinistas/?palestrou=true',
                    '/api/alpinistas/?ordering=dataNascimento',
                )
                for url in urls:
                    response = self.client.get(url)
                    self.assertEqual(response.status_code, status.HTTP_200_OK)
                    self.assertIn(alvo.pk, self.result_ids(response))

    def test_cpf_nao_pode_ser_usado_para_inferencia_no_perfil_resumido(self):
        alvo = make_alpinista(cpf='52998224725')
        self.authenticate(self.make_user('cpf-proibido', SiaRole.ACAO_SOCIAL))

        parametro_direto = self.client.get(
            '/api/alpinistas/?cpf=52998224725'
        )
        pesquisa = self.client.get('/api/alpinistas/?search=52998224725')

        self.assertEqual(parametro_direto.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(pesquisa.status_code, status.HTTP_200_OK)
        self.assertNotIn(alvo.pk, self.result_ids(pesquisa))

    def test_ordenacao_oculta_e_proibida_e_parametro_novo_nasce_bloqueado(self):
        self.authenticate(self.make_user('query-default-deny', SiaRole.COMUNICACAO))

        ordenacao = self.client.get('/api/alpinistas/?ordering=status')
        desconhecido = self.client.get('/api/alpinistas/?campo_novo=valor')

        self.assertEqual(ordenacao.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(desconhecido.status_code, status.HTTP_400_BAD_REQUEST)

    def test_multiplos_papeis_acumulam_filtros_explicitamente_autorizados(self):
        alvo = make_alpinista(eh_violeiro=True)
        Palestra.objects.create(
            alpinista=alvo,
            encontro=make_encontro(),
            titulo='Palestra e música',
        )
        self.authenticate(
            self.make_user(
                'mme-formacao-filtros',
                SiaRole.MME,
                SiaRole.FORMACAO,
            )
        )

        response = self.client.get(
            '/api/alpinistas/?eh_violeiro=true&palestrou=true'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.result_ids(response), [alvo.pk])
