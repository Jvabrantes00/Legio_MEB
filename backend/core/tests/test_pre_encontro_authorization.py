from datetime import date, time, timedelta

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from core.models import (
    ConfiguracaoEncontristasEncontro,
    ConviteEncontro,
    DadosCuidadoInscricao,
    DecisaoVagaPreEncontro,
    Encontro,
    EquipeEncontro,
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
from core.services.pre_encontro import (
    aumentar_capacidade_pre_encontro,
    conferir_cuidados_pre_encontro,
    registrar_checkin_pre_encontro,
    registrar_pagamento_pre_encontro,
    regularizar_atendimento_pre_encontro,
    resolver_vaga_pre_encontro,
)
from core.tests.factories import make_encontro


class PreEncontroAuthorizationTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        self.pre_encontro = PreEncontro.objects.create(
            encontro=self.encontro,
            data=date(2030, 1, 1),
            horario=time(14),
            local='Local do Pré',
        )
        agora = timezone.now()
        self.configuracao = ConfiguracaoEncontristasEncontro.objects.create(
            encontro=self.encontro,
            capacidade=5,
            idade_minima=15,
            idade_maxima=17,
            inscricoes_abrem_em=agora - timedelta(days=1),
            inscricoes_encerram_em=agora + timedelta(days=1),
        )
        self.fichas = self.criar_usuario('fichas', SiaRole.FICHAS)
        self.diretoria = self.criar_usuario('diretoria', SiaRole.DIRETORIA)
        self.suporte = self.criar_usuario('suporte', SiaRole.SUPORTE)
        self.comunicacao = self.criar_usuario(
            'comunicacao',
            SiaRole.COMUNICACAO,
        )
        self.superuser = User.objects.create_superuser(
            username='superuser',
            password='senha',
        )

    def criar_usuario(self, username, role):
        usuario = User.objects.create_user(username=username)
        grupo, _ = Group.objects.get_or_create(name=role.value)
        usuario.groups.add(grupo)
        return usuario

    def criar_contextual(self, username, *, encontro=None):
        encontro = encontro or self.encontro
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=encontro.tipo,
            codigo=f'coordenacao-geral-{encontro.pk}',
            nome='Coordenação Geral',
        )
        role_template = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
            concede_registro_presenca=False,
        )
        equipe = EquipeEncontro.objects.create(
            encontro=encontro,
            template_origem=template,
            codigo='coordenacao-geral',
            nome='Coordenação Geral',
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=role_template,
            codigo='integrante',
            nome='Integrante',
            concede_registro_presenca=False,
        )
        pessoa = Pessoa.objects.create(nome=f'Pessoa de {username}')
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
        usuario = User.objects.create_user(username=username)
        VinculoUsuarioPessoa.objects.create(usuario=usuario, pessoa=pessoa)
        return usuario

    def criar_atendimento_com_cuidado(self):
        pessoa = Pessoa.objects.create(nome='Pessoa atendida')
        inscricao = InscricaoEncontro.objects.create(
            encontro=self.encontro,
            pessoa=pessoa,
            origem=InscricaoEncontro.Origem.ADMINISTRATIVA,
        )
        dados = DadosCuidadoInscricao.objects.create(
            inscricao=inscricao,
            possui_alergias=DadosCuidadoInscricao.RespostaBinaria.NAO,
        )
        atendimento = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre_encontro,
            pessoa=pessoa,
            inscricao=inscricao,
        )
        return atendimento, dados

    def criar_disputa(self):
        self.configuracao.capacidade = 1
        self.configuracao.save(update_fields=['capacidade'])
        atendimentos = []
        for indice in range(2):
            pessoa = Pessoa.objects.create(nome=f'Candidato {indice}')
            atendimentos.append(registrar_checkin_pre_encontro(
                usuario=self.fichas,
                pre_encontro=self.pre_encontro,
                pessoa=pessoa,
            ))
        return atendimentos

    def test_fichas_realiza_checkin_regularizacao_e_pagamento(self):
        atendimento = registrar_checkin_pre_encontro(
            usuario=self.fichas,
            pre_encontro=self.pre_encontro,
            nome_informado='Pessoa avulsa',
            data_nascimento_informada=date(2010, 1, 1),
            telefone_informado='61999990000',
        )
        pessoa = Pessoa.objects.create(nome='Pessoa regularizada')
        regularizado = regularizar_atendimento_pre_encontro(
            usuario=self.fichas,
            atendimento=atendimento,
            pessoa=pessoa,
        )
        pagamento = registrar_pagamento_pre_encontro(
            usuario=self.fichas,
            atendimento=regularizado,
            status=PagamentoPreEncontro.Status.PENDENTE,
        )

        self.assertEqual(regularizado.pessoa, pessoa)
        self.assertEqual(pagamento.atendimento, atendimento)

    def test_coordenacao_do_mesmo_encontro_paga_e_confere_cuidado(self):
        coordenacao = self.criar_contextual('coordenacao-mesmo-encontro')
        atendimento, dados = self.criar_atendimento_com_cuidado()

        pagamento = registrar_pagamento_pre_encontro(
            usuario=coordenacao,
            atendimento=atendimento,
            status=PagamentoPreEncontro.Status.ISENTO,
        )
        conferencia = conferir_cuidados_pre_encontro(
            usuario=coordenacao,
            atendimento=atendimento,
            dados_cuidado=dados,
        )

        self.assertEqual(pagamento.status, 'isento')
        self.assertEqual(conferencia.conferido_por, coordenacao)

    def test_coordenacao_de_outro_encontro_e_negada(self):
        outro = make_encontro(status=Encontro.Status.EM_PREPARACAO)
        coordenacao = self.criar_contextual(
            'coordenacao-outro-encontro',
            encontro=outro,
        )
        atendimento, dados = self.criar_atendimento_com_cuidado()

        with self.assertRaises(PermissionDenied):
            registrar_pagamento_pre_encontro(
                usuario=coordenacao,
                atendimento=atendimento,
                status=PagamentoPreEncontro.Status.PENDENTE,
            )
        with self.assertRaises(PermissionDenied):
            conferir_cuidados_pre_encontro(
                usuario=coordenacao,
                atendimento=atendimento,
                dados_cuidado=dados,
            )

    def test_fichas_e_diretoria_conferem_cuidados(self):
        atendimento, dados = self.criar_atendimento_com_cuidado()
        primeira = conferir_cuidados_pre_encontro(
            usuario=self.fichas,
            atendimento=atendimento,
            dados_cuidado=dados,
        )
        segunda = conferir_cuidados_pre_encontro(
            usuario=self.diretoria,
            atendimento=atendimento,
            dados_cuidado=dados,
        )

        self.assertEqual(primeira.pk, segunda.pk)
        self.assertEqual(segunda.conferido_por, self.diretoria)

    def test_somente_diretoria_resolve_disputa_de_negocio(self):
        coordenacao = self.criar_contextual('coordenacao-sem-decisao')
        primeiro, segundo = self.criar_disputa()

        for usuario in (self.fichas, coordenacao, self.suporte):
            with self.subTest(usuario=usuario.username):
                with self.assertRaises(PermissionDenied):
                    resolver_vaga_pre_encontro(
                        usuario=usuario,
                        atendimento=primeiro,
                        status=DecisaoVagaPreEncontro.Status.APROVADO,
                    )

        decisao = resolver_vaga_pre_encontro(
            usuario=self.diretoria,
            atendimento=primeiro,
            status=DecisaoVagaPreEncontro.Status.APROVADO,
        )
        self.assertEqual(decisao.status, 'aprovado')
        self.assertEqual(
            segundo.decisao_vaga.status,
            'aguardando_decisao_diretoria',
        )

    def test_capacidade_so_diretoria_suporte_ou_superuser(self):
        coordenacao = self.criar_contextual('coordenacao-sem-capacidade')
        for usuario in (self.fichas, coordenacao, self.comunicacao):
            with self.subTest(usuario=usuario.username):
                with self.assertRaises(PermissionDenied):
                    aumentar_capacidade_pre_encontro(
                        usuario=usuario,
                        configuracao=self.configuracao,
                        capacidade=6,
                    )

        for capacidade, usuario in (
            (6, self.diretoria),
            (7, self.suporte),
            (8, self.superuser),
        ):
            atualizada = aumentar_capacidade_pre_encontro(
                usuario=usuario,
                configuracao=self.configuracao,
                capacidade=capacidade,
            )
            self.assertEqual(atualizada.capacidade, capacidade)
            self.configuracao = atualizada

    def test_papel_global_sem_capacidade_especifica_permanece_negado(self):
        with self.assertRaises(PermissionDenied):
            registrar_checkin_pre_encontro(
                usuario=self.comunicacao,
                pre_encontro=self.pre_encontro,
                pessoa=Pessoa.objects.create(nome='Pessoa negada'),
            )

    def test_superuser_e_bypass_tecnico_separado(self):
        atendimento = registrar_checkin_pre_encontro(
            usuario=self.superuser,
            pre_encontro=self.pre_encontro,
            pessoa=Pessoa.objects.create(nome='Pessoa via superuser'),
        )

        self.assertEqual(atendimento.registrado_por, self.superuser)
