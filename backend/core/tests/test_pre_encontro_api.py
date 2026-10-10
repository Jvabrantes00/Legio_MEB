from datetime import date, time, timedelta
from io import BytesIO

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APIClient

from core.models import (
    AtendimentoPreEncontro,
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DadosCuidadoInscricao,
    DecisaoVagaPreEncontro,
    Encontro,
    EquipeEncontro,
    FotoTemporariaPreEncontro,
    InscricaoEncontro,
    PagamentoPreEncontro,
    Pessoa,
    PreEncontro,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
    VinculoUsuarioPessoa,
)
from core.roles import SiaRole
from core.permissions import (
    pode_aumentar_capacidade_pre_encontro,
    pode_consultar_operacao_pre_encontro,
    pode_operar_checkin_pre_encontro,
    pode_registrar_pagamento_pre_encontro,
    pode_resolver_vaga_pre_encontro,
)
from core.services.pre_encontro import registrar_checkin_pre_encontro
from core.tests.factories import make_encontro


@override_settings(MEDIA_ROOT='/tmp/sia-pre-encontro-api-tests')
class PreEncontroApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.fichas = self._usuario('fichas-api', SiaRole.FICHAS)
        self.diretoria = self._usuario('diretoria-api', SiaRole.DIRETORIA)
        self.comunicacao = self._usuario('comunicacao-api', SiaRole.COMUNICACAO)
        self.suporte = self._usuario('suporte-api', SiaRole.SUPORTE)
        self.sem_papel = User.objects.create_user('sem-papel-api')
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.pre = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 1, 1),
            horario=time(14),
            local='Local do Pré',
        )
        agora = timezone.now()
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=10,
            idade_minima=15,
            idade_maxima=17,
            inscricoes_abrem_em=agora - timedelta(days=1),
            inscricoes_encerram_em=agora + timedelta(days=1),
        )
        self.pessoa = Pessoa.objects.create(
            nome='Maria Operacional',
            cpf='52998224725',
        )
        self.inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=self.pessoa,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )
        self.cuidado = DadosCuidadoInscricao.objects.create(
            inscricao=self.inscricao,
            possui_alergias=DadosCuidadoInscricao.RespostaBinaria.SIM,
            alergias='Dado sensível não pode aparecer no contrato comum.',
        )
        self.atendimento = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre,
            inscricao=self.inscricao,
            pessoa=self.pessoa,
            telefone_informado='61999990000',
        )

    def _usuario(self, username, role):
        usuario = User.objects.create_user(username)
        grupo, _ = Group.objects.get_or_create(name=role.value)
        usuario.groups.add(grupo)
        return usuario

    def _autenticar(self, usuario):
        self.client.force_authenticate(usuario)

    def _base(self, encontro=None):
        encontro = encontro or self.encontro
        return f'/api/encontros/{encontro.pk}/pre-encontro'

    def _atendimento_url(self, suffix='', *, encontro=None, atendimento=None):
        atendimento = atendimento or self.atendimento
        return f'{self._base(encontro)}/atendimentos/{atendimento.pk}/{suffix}'

    def _capabilities_url(self, encontro=None):
        return f'{self._base(encontro)}/capabilities/'

    def _foto(self, nome='foto.png'):
        arquivo = BytesIO()
        Image.new('RGB', (2, 2), 'white').save(arquivo, format='PNG')
        return SimpleUploadedFile(nome, arquivo.getvalue(), content_type='image/png')

    def _outro_contexto(self):
        encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        pre = PreEncontro.objects.create(
            encontro=encontro,
            data=date(2030, 2, 1),
            horario=time(14),
            local='Outro Pré',
        )
        ConfiguracaoEncontristasEncontro.objects.create(
            encontro=encontro,
            capacidade=5,
            idade_minima=15,
            idade_maxima=17,
            inscricoes_abrem_em=timezone.now() - timedelta(days=1),
            inscricoes_encerram_em=timezone.now() + timedelta(days=1),
        )
        pessoa = Pessoa.objects.create(nome='Outro contexto')
        atendimento = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=pre,
            pessoa=pessoa,
        )
        return encontro, atendimento

    def _coordenacao(self, username='coordenacao-api', encontro=None):
        encontro = encontro or self.encontro
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=encontro.tipo,
            codigo=f'coord-api-{encontro.pk}',
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
        pessoa = Pessoa.objects.create(nome=f'Pessoa {username}')
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
        usuario = User.objects.create_user(username)
        VinculoUsuarioPessoa.objects.create(usuario=usuario, pessoa=pessoa)
        return usuario

    def test_lista_e_paginada_escopada_e_sem_dados_sensiveis(self):
        outro_encontro, outro_atendimento = self._outro_contexto()
        del outro_encontro
        for indice in range(11):
            registrar_checkin_pre_encontro(
                usuario=self.fichas,
                pre_encontro=self.pre,
                pessoa=Pessoa.objects.create(nome=f'Pessoa {indice:02d}'),
            )
        self._autenticar(self.fichas)

        primeira = self.client.get(f'{self._base()}/atendimentos/')
        segunda = self.client.get(f'{self._base()}/atendimentos/?page=2')

        self.assertEqual(primeira.status_code, status.HTTP_200_OK)
        self.assertEqual(primeira.data['count'], 12)
        self.assertEqual(len(primeira.data['results']), 10)
        self.assertEqual(len(segunda.data['results']), 2)
        ids = {item['id'] for item in primeira.data['results'] + segunda.data['results']}
        self.assertNotIn(outro_atendimento.pk, ids)
        for item in primeira.data['results']:
            self.assertNotIn('alergias', item)
            self.assertNotIn('medicamentos', item)
            self.assertNotIn('observacoes', item)

    def test_capabilities_contextuais_reutilizam_policies_e_default_deny(self):
        casos = (
            (self.fichas, True, True, False),
            (self.comunicacao, True, False, False),
            (self.suporte, True, True, True),
            (self.sem_papel, False, False, False),
        )
        for usuario, consultar, checkin, capacidade in casos:
            self._autenticar(usuario)
            resposta = self.client.get(self._capabilities_url())
            self.assertEqual(resposta.status_code, status.HTTP_200_OK)
            self.assertEqual(resposta.data, {
                'consultar_operacao': consultar,
                'registrar_checkin': checkin,
                'aumentar_capacidade': capacidade,
            })
            self.assertEqual(
                resposta.data['consultar_operacao'],
                pode_consultar_operacao_pre_encontro(usuario, self.encontro),
            )
            self.assertEqual(
                resposta.data['registrar_checkin'],
                pode_operar_checkin_pre_encontro(usuario, self.encontro),
            )
            self.assertEqual(
                resposta.data['aumentar_capacidade'],
                pode_aumentar_capacidade_pre_encontro(usuario, self.encontro),
            )
            self.assertNotIn('roles', resposta.data)

    def test_capabilities_de_item_por_policy_sem_vazar_cuidado(self):
        coordenacao = self._coordenacao('coord-capabilities')
        casos = (
            (self.fichas, True, True, True, False),
            (coordenacao, True, True, True, False),
            (self.comunicacao, False, False, True, False),
        )
        for usuario, pagamento, cuidados, foto, decisao in casos:
            self._autenticar(usuario)
            resposta = self.client.get(self._atendimento_url())
            self.assertEqual(resposta.status_code, status.HTTP_200_OK)
            capabilities = resposta.data['capabilities']
            self.assertEqual(capabilities['registrar_pagamento'], pagamento)
            self.assertEqual(capabilities['consultar_cuidados'], cuidados)
            self.assertEqual(capabilities['conferir_cuidados'], cuidados)
            self.assertEqual(capabilities['alterar_foto'], foto)
            self.assertFalse(capabilities['visualizar_foto'])
            self.assertEqual(capabilities['decidir_vaga'], decisao)
            self.assertEqual(
                capabilities['registrar_pagamento'],
                pode_registrar_pagamento_pre_encontro(usuario, self.encontro),
            )
            self.assertNotIn('alergias', resposta.data)
            self.assertNotIn('medicamentos', resposta.data)

    def test_coordenacao_de_outro_encontro_nao_recebe_capability_contextual(self):
        outro_encontro, _ = self._outro_contexto()
        coordenacao = self._coordenacao(
            'coord-outro-capabilities',
            encontro=outro_encontro,
        )
        self._autenticar(coordenacao)
        contexto = self.client.get(self._capabilities_url())
        detalhe = self.client.get(self._atendimento_url())
        mismatch = self.client.get(
            self._atendimento_url(encontro=outro_encontro),
        )
        self.assertEqual(contexto.status_code, status.HTTP_200_OK)
        self.assertEqual(contexto.data, {
            'consultar_operacao': False,
            'registrar_checkin': False,
            'aumentar_capacidade': False,
        })
        self.assertEqual(detalhe.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(mismatch.status_code, status.HTTP_404_NOT_FOUND)

    def test_lifecycle_bloqueia_capabilities_mutaveis(self):
        self._autenticar(self.suporte)
        for estado in (Encontro.Status.CANCELADO, Encontro.Status.FINALIZADO):
            self.encontro.status = estado
            self.encontro.save(update_fields=['status'])
            contexto = self.client.get(self._capabilities_url()).data
            detalhe = self.client.get(self._atendimento_url()).data
            self.assertTrue(contexto['consultar_operacao'])
            self.assertFalse(contexto['registrar_checkin'])
            self.assertFalse(contexto['aumentar_capacidade'])
            self.assertFalse(detalhe['capabilities']['regularizar'])
            self.assertFalse(detalhe['capabilities']['registrar_pagamento'])
            self.assertFalse(detalhe['capabilities']['conferir_cuidados'])
            self.assertFalse(detalhe['capabilities']['alterar_foto'])
            self.assertFalse(detalhe['capabilities']['decidir_vaga'])

        self.encontro.status = Encontro.Status.ADIADO
        self.encontro.save(update_fields=['status'])
        contexto = self.client.get(self._capabilities_url()).data
        detalhe = self.client.get(self._atendimento_url()).data
        self.assertFalse(contexto['registrar_checkin'])
        self.assertTrue(contexto['aumentar_capacidade'])
        self.assertTrue(detalhe['capabilities']['registrar_pagamento'])
        self.assertTrue(detalhe['capabilities']['alterar_foto'])
        self.assertFalse(detalhe['capabilities']['decidir_vaga'])

    def test_decidir_vaga_so_quando_policy_e_estado_permitem(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        segundo = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre,
            pessoa=Pessoa.objects.create(nome='Capabilities em disputa'),
        )
        self.assertTrue(
            DecisaoVagaPreEncontro.objects.filter(atendimento=segundo).exists(),
        )
        for usuario, esperado in (
            (self.diretoria, True),
            (self.fichas, False),
            (self._coordenacao('coord-cap-sem-decisao'), False),
            (self.comunicacao, False),
            (self.suporte, False),
        ):
            self._autenticar(usuario)
            resposta = self.client.get(
                self._atendimento_url(atendimento=segundo),
            )
            self.assertEqual(resposta.status_code, status.HTTP_200_OK)
            self.assertEqual(
                resposta.data['capabilities']['decidir_vaga'],
                esperado,
            )
            self.assertEqual(
                esperado,
                pode_resolver_vaga_pre_encontro(usuario, self.encontro),
            )

        superuser = User.objects.create_superuser('super-capabilities')
        self._autenticar(superuser)
        resposta = self.client.get(self._atendimento_url(atendimento=segundo))
        self.assertTrue(resposta.data['capabilities']['decidir_vaga'])

    def test_busca_por_nome_cpf_telefone_e_inscricao_e_escopada(self):
        outro_encontro, outro_atendimento = self._outro_contexto()
        outro_atendimento.nome_informado = 'Termo exclusivo externo'
        outro_atendimento.save(update_fields=['nome_informado'])
        self._autenticar(self.fichas)
        buscas = (
            'Maria',
            '52998224725',
            '61999990000',
            str(self.inscricao.identificador),
        )
        for termo in buscas:
            resposta = self.client.get(
                f'{self._base()}/atendimentos/busca/',
                {'q': termo},
            )
            self.assertEqual(resposta.status_code, status.HTTP_200_OK)
            self.assertEqual(resposta.data['count'], 1)
            self.assertEqual(resposta.data['results'][0]['id'], self.atendimento.pk)
            self.assertNotIn('alergias', resposta.data['results'][0])
        externa = self.client.get(
            f'{self._base()}/atendimentos/busca/',
            {'q': 'Termo exclusivo externo'},
        )
        self.assertEqual(externa.data['count'], 0)
        self.assertNotEqual(outro_encontro.pk, self.encontro.pk)

    def test_detalhe_minimo_indicadores_e_nested_mismatch(self):
        outro_encontro, _ = self._outro_contexto()
        self._autenticar(self.fichas)
        resposta = self.client.get(self._atendimento_url())
        mismatch = self.client.get(self._atendimento_url(encontro=outro_encontro))

        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertTrue(resposta.data['possui_dados_cuidado'])
        self.assertFalse(resposta.data['cuidado_conferido'])
        self.assertNotIn('alergias', resposta.data)
        self.assertNotIn('medicamentos', resposta.data)
        self.assertEqual(mismatch.status_code, status.HTTP_404_NOT_FOUND)

    def test_nested_mismatch_e_404_em_todos_os_subrecursos(self):
        outro_encontro, _ = self._outro_contexto()
        self._autenticar(self.diretoria)
        casos = (
            ('get', self._atendimento_url(encontro=outro_encontro), None),
            ('post', self._atendimento_url('regularizar/', encontro=outro_encontro), {'pessoa_id': self.pessoa.pk}),
            ('put', self._atendimento_url('pagamento/', encontro=outro_encontro), {'status': 'pendente'}),
            ('get', self._atendimento_url('cuidados/', encontro=outro_encontro), None),
            ('post', self._atendimento_url('cuidados/conferir/', encontro=outro_encontro), {}),
            ('get', self._atendimento_url('foto/', encontro=outro_encontro), None),
            ('post', self._atendimento_url('decisao-vaga/', encontro=outro_encontro), {'status': 'nao_aprovado'}),
        )
        for metodo, url, payload in casos:
            resposta = getattr(self.client, metodo)(url, payload or {}, format='json')
            self.assertEqual(resposta.status_code, status.HTTP_404_NOT_FOUND)

    def test_checkin_usa_command_e_default_deny(self):
        pessoa = Pessoa.objects.create(nome='Novo check-in')
        self._autenticar(self.fichas)
        resposta = self.client.post(
            f'{self._base()}/check-in/',
            {'pessoa_id': pessoa.pk},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_201_CREATED)
        self.assertTrue(
            AtendimentoPreEncontro.objects.filter(
                pre_encontro=self.pre,
                pessoa=pessoa,
            ).exists(),
        )
        self._autenticar(self.sem_papel)
        negado = self.client.post(
            f'{self._base()}/check-in/',
            {'pessoa_id': Pessoa.objects.create(nome='Negada').pk},
            format='json',
        )
        self.assertEqual(negado.status_code, status.HTTP_403_FORBIDDEN)

    def test_default_deny_em_todas_as_rotas_operacionais(self):
        self._autenticar(self.sem_papel)
        casos = (
            ('get', f'{self._base()}/atendimentos/', None),
            ('get', f'{self._base()}/atendimentos/busca/?q=Maria', None),
            ('get', self._atendimento_url(), None),
            ('post', f'{self._base()}/check-in/', {'pessoa_id': self.pessoa.pk}),
            ('post', self._atendimento_url('regularizar/'), {'pessoa_id': self.pessoa.pk}),
            ('put', self._atendimento_url('pagamento/'), {'status': 'pendente'}),
            ('get', self._atendimento_url('cuidados/'), None),
            ('post', self._atendimento_url('cuidados/conferir/'), {}),
            ('get', self._atendimento_url('foto/'), None),
            ('put', self._atendimento_url('foto/'), {'foto': self._foto()}),
            ('post', self._atendimento_url('decisao-vaga/'), {'status': 'nao_aprovado'}),
            ('post', f'{self._base()}/capacidade/', {'capacidade': 20}),
        )
        for metodo, url, payload in casos:
            formato = 'multipart' if payload and 'foto' in payload else 'json'
            resposta = getattr(self.client, metodo)(url, payload or {}, format=formato)
            self.assertEqual(resposta.status_code, status.HTTP_403_FORBIDDEN)

    def test_regularizacao_autorizada_e_outro_encontro_404(self):
        avulso = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre,
            nome_informado='Avulso',
            data_nascimento_informada=date(2010, 1, 1),
            telefone_informado='61111111111',
        )
        pessoa = Pessoa.objects.create(nome='Regularizada')
        self._autenticar(self.fichas)
        resposta = self.client.post(
            self._atendimento_url('regularizar/', atendimento=avulso),
            {'pessoa_id': pessoa.pk},
            format='json',
        )
        outro_encontro, _ = self._outro_contexto()
        mismatch = self.client.post(
            self._atendimento_url(
                'regularizar/', encontro=outro_encontro, atendimento=avulso,
            ),
            {'pessoa_id': pessoa.pk},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(mismatch.status_code, status.HTTP_404_NOT_FOUND)

    def test_pagamento_fichas_e_coordenacao_comunicacao_negada(self):
        self._autenticar(self.fichas)
        resposta = self.client.put(
            self._atendimento_url('pagamento/'),
            {'status': 'pago', 'forma': 'pix', 'valor': '20.00'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        coordenacao = self._coordenacao()
        self._autenticar(coordenacao)
        isento = self.client.put(
            self._atendimento_url('pagamento/'),
            {'status': 'isento'},
            format='json',
        )
        self.assertEqual(isento.status_code, status.HTTP_200_OK)
        self._autenticar(self.comunicacao)
        negado = self.client.put(
            self._atendimento_url('pagamento/'),
            {'status': 'pendente'},
            format='json',
        )
        self.assertEqual(negado.status_code, status.HTTP_403_FORBIDDEN)

    def test_cuidados_e_conferencia_sao_separados_e_contextuais(self):
        coordenacao = self._coordenacao()
        for usuario in (self.fichas, coordenacao):
            self._autenticar(usuario)
            consulta = self.client.get(self._atendimento_url('cuidados/'))
            conferencia = self.client.post(
                self._atendimento_url('cuidados/conferir/'),
                {},
                format='json',
            )
            self.assertEqual(consulta.status_code, status.HTTP_200_OK)
            self.assertEqual(consulta.data['alergias'], self.cuidado.alergias)
            self.assertEqual(conferencia.status_code, status.HTTP_200_OK)
            self.assertTrue(conferencia.data['conferido'])
        self._autenticar(self.comunicacao)
        self.assertEqual(
            self.client.get(self._atendimento_url('cuidados/')).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                self._atendimento_url('cuidados/conferir/'), {}, format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_foto_privada_por_fichas_coordenacao_e_comunicacao(self):
        coordenacao = self._coordenacao()
        for indice, usuario in enumerate((self.fichas, coordenacao, self.comunicacao)):
            self._autenticar(usuario)
            upload = self.client.put(
                self._atendimento_url('foto/'),
                {'foto': self._foto(f'foto-{indice}.png')},
                format='multipart',
            )
            preview = self.client.get(self._atendimento_url('foto/'))
            detalhe = self.client.get(self._atendimento_url())
            self.assertEqual(upload.status_code, status.HTTP_200_OK)
            self.assertEqual(preview.status_code, status.HTTP_200_OK)
            self.assertEqual(preview['Cache-Control'], 'private, no-store')
            self.assertNotIn('/media/', str(preview.headers))
            self.assertTrue(detalhe.data['capabilities']['visualizar_foto'])
            self.assertTrue(detalhe.data['capabilities']['alterar_foto'])
        foto = FotoTemporariaPreEncontro.objects.get(atendimento=self.atendimento)
        self.assertNotIn(foto.arquivo.name, str(upload.data))

    def test_foto_nested_mismatch_e_sem_rota_publica_media(self):
        self._autenticar(self.fichas)
        self.client.put(
            self._atendimento_url('foto/'),
            {'foto': self._foto()},
            format='multipart',
        )
        outro_encontro, _ = self._outro_contexto()
        mismatch = self.client.get(self._atendimento_url('foto/', encontro=outro_encontro))
        publico = self.client.get('/media/pre_encontros/fotos/inexistente')
        self.assertEqual(mismatch.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(publico.status_code, status.HTTP_404_NOT_FOUND)

    def test_comunicacao_tem_somente_leitura_minima_e_foto(self):
        self._autenticar(self.comunicacao)
        self.assertEqual(
            self.client.get(f'{self._base()}/atendimentos/').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.get(
                f'{self._base()}/atendimentos/busca/', {'q': 'Maria'},
            ).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(
                self._atendimento_url('regularizar/'),
                {'pessoa_id': self.pessoa.pk},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                self._atendimento_url('decisao-vaga/'),
                {'status': 'aprovado'},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )
        self.assertEqual(
            self.client.post(
                f'{self._base()}/capacidade/', {'capacidade': 20}, format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_decisao_vaga_somente_diretoria(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        segundo = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre,
            pessoa=Pessoa.objects.create(nome='Disputa'),
        )
        self.assertTrue(
            DecisaoVagaPreEncontro.objects.filter(atendimento=segundo).exists(),
        )
        url = self._atendimento_url('decisao-vaga/', atendimento=segundo)
        for usuario in (self.fichas, self._coordenacao('coord-sem-decisao'), self.comunicacao):
            self._autenticar(usuario)
            self.assertEqual(
                self.client.post(
                    url, {'status': 'nao_aprovado'}, format='json',
                ).status_code,
                status.HTTP_403_FORBIDDEN,
            )
        self._autenticar(self.diretoria)
        resposta = self.client.post(
            url,
            {'status': 'nao_aprovado', 'justificativa': 'Sem vaga.'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data['status'], 'nao_aprovado')

    def test_capacidade_apenas_admin_amplo_e_sem_crud_generico(self):
        self._autenticar(self.suporte)
        resposta = self.client.post(
            f'{self._base()}/capacidade/',
            {'capacidade': 20, 'justificativa': 'Aumento autorizado.'},
            format='json',
        )
        self.assertEqual(resposta.status_code, status.HTTP_200_OK)
        self.assertEqual(resposta.data['capacidade'], 20)
        self._autenticar(self.fichas)
        negado = self.client.post(
            f'{self._base()}/capacidade/', {'capacidade': 21}, format='json',
        )
        delete = self.client.delete(self._atendimento_url())
        patch = self.client.patch(
            self._atendimento_url(), {'pessoa_id': None}, format='json',
        )
        self.assertEqual(negado.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(patch.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_lifecycle_cancelado_finalizado_e_adiado_permanece_no_service(self):
        pessoa = Pessoa.objects.create(nome='Lifecycle')
        self._autenticar(self.fichas)
        for estado in (
            Encontro.Status.CANCELADO,
            Encontro.Status.FINALIZADO,
            Encontro.Status.ADIADO,
        ):
            self.encontro.status = estado
            self.encontro.save(update_fields=['status'])
            resposta = self.client.post(
                f'{self._base()}/check-in/',
                {'pessoa_id': pessoa.pk},
                format='json',
            )
            self.assertEqual(resposta.status_code, status.HTTP_400_BAD_REQUEST)
