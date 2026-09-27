from datetime import date, time

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from core.models import (
    ConfiguracaoGrupo,
    CoordenacaoGrupo,
    Frequencia,
    Grupo,
    Paroquia,
    PerfilAlpinista,
    Pessoa,
    RegiaoAdministrativa,
    VinculoGrupo,
)
from core.services.grupos import (
    criar_configuracao_grupo,
    criar_coordenacao_grupo,
    criar_vinculo_grupo,
    perfil_alpinista_ativo,
    possui_acesso_transicao,
    registrar_frequencia,
)


class GrupoDomainTestCase(TestCase):
    def setUp(self):
        self.pessoa = Pessoa.objects.create(nome='Pessoa de teste')
        self.perfil = PerfilAlpinista.objects.create(pessoa=self.pessoa)
        self.usuario = User.objects.create_user(
            username='registrador',
            password='senha-de-teste',
        )
        self.grupo_a = Grupo.objects.create(nome='Grupo A')
        self.grupo_b = Grupo.objects.create(nome='Grupo B')
        self.grupo_c = Grupo.objects.create(nome='Grupo C')


class ParoquiaGrupoTests(GrupoDomainTestCase):
    def test_cria_paroquia_com_ra_opcional_e_grupo_com_nome_repetido(self):
        regiao = RegiaoAdministrativa.objects.create(nome='RA Teste')
        paroquia_sem_ra = Paroquia.objects.create(nome='Paróquia')
        paroquia_com_ra = Paroquia.objects.create(
            nome='Paróquia',
            regiao_administrativa=regiao,
        )
        grupo_repetido = Grupo.objects.create(nome=self.grupo_a.nome)

        self.assertIsNone(paroquia_sem_ra.regiao_administrativa)
        self.assertEqual(paroquia_com_ra.regiao_administrativa, regiao)
        self.assertNotEqual(grupo_repetido.pk, self.grupo_a.pk)


class ConfiguracaoGrupoTests(GrupoDomainTestCase):
    def test_permite_uma_configuracao_atual(self):
        atual = criar_configuracao_grupo(
            grupo=self.grupo_a,
            vigente_desde=date(2027, 1, 1),
            local_reuniao='Salão',
            dia_semana='sábado',
            horario=time(19, 30),
        )

        self.assertTrue(atual.ativo)
        with self.assertRaisesMessage(
            ValidationError,
            'se sobrepõe',
        ):
            criar_configuracao_grupo(
                grupo=self.grupo_a,
                vigente_desde=date(2027, 2, 1),
            )

    def test_constraint_impede_duas_configuracoes_atuais(self):
        ConfiguracaoGrupo.objects.create(
            grupo=self.grupo_a,
            vigente_desde=date(2027, 1, 1),
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ConfiguracaoGrupo.objects.create(
                grupo=self.grupo_a,
                vigente_desde=date(2027, 2, 1),
            )

    def test_permite_historico_sequencial(self):
        anterior = criar_configuracao_grupo(
            grupo=self.grupo_a,
            vigente_desde=date(2027, 1, 1),
            vigente_ate=date(2027, 1, 31),
            ativo=False,
        )
        atual = criar_configuracao_grupo(
            grupo=self.grupo_a,
            vigente_desde=date(2027, 2, 1),
        )

        self.assertEqual(anterior.vigente_ate, date(2027, 1, 31))
        self.assertIsNone(atual.vigente_ate)

    def test_rejeita_periodo_invertido_no_service_e_no_banco(self):
        with self.assertRaisesMessage(
            ValidationError,
            'data final',
        ):
            criar_configuracao_grupo(
                grupo=self.grupo_a,
                vigente_desde=date(2027, 2, 1),
                vigente_ate=date(2027, 1, 31),
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            ConfiguracaoGrupo.objects.create(
                grupo=self.grupo_b,
                vigente_desde=date(2027, 2, 1),
                vigente_ate=date(2027, 1, 31),
            )

    def test_rejeita_sobreposicao_historica(self):
        criar_configuracao_grupo(
            grupo=self.grupo_a,
            vigente_desde=date(2027, 1, 1),
            vigente_ate=date(2027, 1, 31),
        )

        with self.assertRaisesMessage(ValidationError, 'se sobrepõe'):
            criar_configuracao_grupo(
                grupo=self.grupo_a,
                vigente_desde=date(2027, 1, 15),
                vigente_ate=date(2027, 2, 15),
            )


class VinculoGrupoTests(GrupoDomainTestCase):
    def test_preserva_historico_e_permite_saida_e_reentrada(self):
        anterior = criar_vinculo_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            inicio=date(2026, 1, 1),
            fim=date(2026, 6, 30),
        )
        atual = criar_vinculo_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            inicio=date(2027, 1, 1),
        )

        self.assertEqual(anterior.fim, date(2026, 6, 30))
        self.assertIsNone(atual.fim)
        self.assertEqual(
            VinculoGrupo.objects.filter(
                perfil_alpinista=self.perfil,
                grupo=self.grupo_a,
            ).count(),
            2,
        )

    def test_bloqueia_duplicacao_atual(self):
        criar_vinculo_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            inicio=date(2027, 1, 1),
        )

        with self.assertRaisesMessage(ValidationError, 'vínculo atual'):
            criar_vinculo_grupo(
                perfil_alpinista=self.perfil,
                grupo=self.grupo_a,
                inicio=date(2027, 2, 1),
            )

    def test_constraint_bloqueia_duplicacao_atual(self):
        VinculoGrupo.objects.create(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            inicio=date(2027, 1, 1),
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            VinculoGrupo.objects.create(
                perfil_alpinista=self.perfil,
                grupo=self.grupo_a,
                inicio=date(2027, 2, 1),
            )

    def test_permite_dois_grupos_atuais_e_bloqueia_o_terceiro(self):
        criar_vinculo_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            inicio=date(2027, 1, 1),
        )
        criar_vinculo_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_b,
            inicio=date(2027, 1, 1),
        )

        with self.assertRaisesMessage(ValidationError, 'no máximo dois'):
            criar_vinculo_grupo(
                perfil_alpinista=self.perfil,
                grupo=self.grupo_c,
                inicio=date(2027, 1, 1),
            )

        self.assertEqual(
            VinculoGrupo.objects.filter(
                perfil_alpinista=self.perfil,
                fim__isnull=True,
            ).count(),
            2,
        )


class CoordenacaoGrupoTests(GrupoDomainTestCase):
    def test_aceita_tipos_jovem_e_adulto(self):
        jovem = criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            tipo=CoordenacaoGrupo.Tipo.JOVEM,
            inicio=date(2026, 1, 1),
            fim=date(2026, 6, 30),
        )
        adulto = criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_b,
            tipo=CoordenacaoGrupo.Tipo.ADULTO,
            inicio=date(2026, 7, 1),
            fim=date(2026, 12, 31),
        )

        self.assertEqual(jovem.tipo, CoordenacaoGrupo.Tipo.JOVEM)
        self.assertEqual(adulto.tipo, CoordenacaoGrupo.Tipo.ADULTO)

    def test_bloqueia_duas_coordenacoes_atuais(self):
        criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            tipo=CoordenacaoGrupo.Tipo.JOVEM,
            inicio=date(2027, 1, 1),
        )

        with self.assertRaisesMessage(ValidationError, 'se sobrepõe'):
            criar_coordenacao_grupo(
                perfil_alpinista=self.perfil,
                grupo=self.grupo_b,
                tipo=CoordenacaoGrupo.Tipo.ADULTO,
                inicio=date(2027, 2, 1),
            )

    def test_constraint_bloqueia_duas_coordenacoes_atuais(self):
        CoordenacaoGrupo.objects.create(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            tipo=CoordenacaoGrupo.Tipo.JOVEM,
            inicio=date(2027, 1, 1),
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            CoordenacaoGrupo.objects.create(
                perfil_alpinista=self.perfil,
                grupo=self.grupo_b,
                tipo=CoordenacaoGrupo.Tipo.ADULTO,
                inicio=date(2027, 2, 1),
            )

    def test_permite_nova_coordenacao_apos_termino(self):
        criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            tipo=CoordenacaoGrupo.Tipo.JOVEM,
            inicio=date(2026, 1, 1),
            fim=date(2026, 12, 31),
        )
        nova = criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_b,
            tipo=CoordenacaoGrupo.Tipo.ADULTO,
            inicio=date(2027, 1, 1),
        )

        self.assertIsNone(nova.fim)

    def test_rejeita_sobreposicao_historica(self):
        criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            tipo=CoordenacaoGrupo.Tipo.JOVEM,
            inicio=date(2027, 1, 1),
            fim=date(2027, 6, 30),
        )

        with self.assertRaisesMessage(ValidationError, 'se sobrepõe'):
            criar_coordenacao_grupo(
                perfil_alpinista=self.perfil,
                grupo=self.grupo_b,
                tipo=CoordenacaoGrupo.Tipo.ADULTO,
                inicio=date(2027, 6, 15),
                fim=date(2027, 12, 31),
            )


class AcessoTransicaoTests(GrupoDomainTestCase):
    def test_mandato_aberto_concede_acesso(self):
        criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            tipo=CoordenacaoGrupo.Tipo.JOVEM,
            inicio=date(2027, 1, 1),
        )

        self.assertTrue(
            possui_acesso_transicao(
                self.perfil,
                data_referencia=date(2027, 8, 1),
            )
        )

    def test_acesso_dura_um_mes_calendario_inclusive(self):
        criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            tipo=CoordenacaoGrupo.Tipo.ADULTO,
            inicio=date(2027, 1, 1),
            fim=date(2027, 3, 15),
        )

        self.assertTrue(
            possui_acesso_transicao(
                self.perfil,
                data_referencia=date(2027, 4, 15),
            )
        )
        self.assertFalse(
            possui_acesso_transicao(
                self.perfil,
                data_referencia=date(2027, 4, 16),
            )
        )

    def test_acesso_ajusta_meses_com_quantidades_diferentes_de_dias(self):
        criar_coordenacao_grupo(
            perfil_alpinista=self.perfil,
            grupo=self.grupo_a,
            tipo=CoordenacaoGrupo.Tipo.JOVEM,
            inicio=date(2026, 1, 1),
            fim=date(2027, 1, 31),
        )

        self.assertTrue(
            possui_acesso_transicao(
                self.perfil,
                data_referencia=date(2027, 2, 28),
            )
        )
        self.assertFalse(
            possui_acesso_transicao(
                self.perfil,
                data_referencia=date(2027, 3, 1),
            )
        )


class FrequenciaTests(GrupoDomainTestCase):
    def test_registra_frequencia_com_grupo_nulo(self):
        frequencia = registrar_frequencia(
            perfil_alpinista=self.perfil,
            data=date(2026, 1, 10),
            registrada_por=self.usuario,
            data_atual=date(2026, 12, 31),
        )

        self.assertIsNone(frequencia.grupo)

    def test_registra_frequencia_com_grupo_informado(self):
        frequencia = registrar_frequencia(
            perfil_alpinista=self.perfil,
            data=date(2026, 1, 10),
            grupo=self.grupo_a,
            registrada_por=self.usuario,
            data_atual=date(2026, 12, 31),
        )

        self.assertEqual(frequencia.grupo, self.grupo_a)
        self.assertEqual(frequencia.registrada_por, self.usuario)

    def test_bloqueia_frequencia_duplicada_mesmo_em_outro_grupo(self):
        registrar_frequencia(
            perfil_alpinista=self.perfil,
            data=date(2026, 1, 10),
            grupo=self.grupo_a,
            registrada_por=self.usuario,
            data_atual=date(2026, 12, 31),
        )

        with self.assertRaisesMessage(ValidationError, 'Já existe frequência'):
            registrar_frequencia(
                perfil_alpinista=self.perfil,
                data=date(2026, 1, 10),
                grupo=self.grupo_b,
                registrada_por=self.usuario,
                data_atual=date(2026, 12, 31),
            )

    def test_constraint_bloqueia_frequencia_duplicada(self):
        Frequencia.objects.create(
            perfil_alpinista=self.perfil,
            data=date(2026, 1, 10),
            grupo=self.grupo_a,
            registrada_por=self.usuario,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Frequencia.objects.create(
                perfil_alpinista=self.perfil,
                data=date(2026, 1, 10),
                grupo=self.grupo_b,
                registrada_por=self.usuario,
            )

    def test_bloqueia_frequencia_futura(self):
        with self.assertRaisesMessage(ValidationError, 'frequência futura'):
            registrar_frequencia(
                perfil_alpinista=self.perfil,
                data=date(2026, 10, 2),
                registrada_por=self.usuario,
                data_atual=date(2026, 10, 1),
            )


class AtividadePerfilTests(GrupoDomainTestCase):
    def test_sem_frequencia_e_ativo(self):
        self.assertTrue(
            perfil_alpinista_ativo(
                self.perfil,
                data_referencia=date(2026, 12, 31),
            )
        )

    def test_frequencia_recente_e_ativa(self):
        Frequencia.objects.create(
            perfil_alpinista=self.perfil,
            data=date(2026, 8, 1),
            registrada_por=self.usuario,
        )

        self.assertTrue(
            perfil_alpinista_ativo(
                self.perfil,
                data_referencia=date(2026, 12, 31),
            )
        )

    def test_seis_meses_exatos_ativo_e_dia_seguinte_inativo(self):
        Frequencia.objects.create(
            perfil_alpinista=self.perfil,
            data=date(2025, 3, 31),
            registrada_por=self.usuario,
        )

        self.assertTrue(
            perfil_alpinista_ativo(
                self.perfil,
                data_referencia=date(2025, 9, 30),
            )
        )
        self.assertFalse(
            perfil_alpinista_ativo(
                self.perfil,
                data_referencia=date(2025, 10, 1),
            )
        )

    def test_nova_frequencia_reativa_o_perfil(self):
        Frequencia.objects.create(
            perfil_alpinista=self.perfil,
            data=date(2025, 1, 1),
            registrada_por=self.usuario,
        )
        self.assertFalse(
            perfil_alpinista_ativo(
                self.perfil,
                data_referencia=date(2026, 1, 1),
            )
        )

        Frequencia.objects.create(
            perfil_alpinista=self.perfil,
            data=date(2025, 12, 31),
            registrada_por=self.usuario,
        )

        self.assertTrue(
            perfil_alpinista_ativo(
                self.perfil,
                data_referencia=date(2026, 1, 1),
            )
        )
