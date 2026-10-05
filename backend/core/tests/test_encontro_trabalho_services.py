from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.test import TestCase, TransactionTestCase

from core.models import (
    ConviteEncontro,
    Encontro,
    EquipeEncontro,
    Frequencia,
    Pessoa,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.services.participacoes import responder_convite
from core.services.trabalhos import (
    alocar_trabalho,
    criar_convite_trabalho,
    desalocar_trabalho,
    iniciar_trabalho_confirmado,
    preparar_equipes_encontro,
    registrar_resultado_trabalho,
    retirar_trabalho,
    substituir_trabalho,
)
from core.tests.factories import make_encontro


def criar_template(
    *,
    tipo=Encontro.Tipo.ESCALADA,
    codigo='coordenacao-geral',
    nome='Coordenação Geral',
    quantidade=2,
    capacidade_maxima=6,
):
    template = TemplateEquipeEncontro.objects.create(
        tipo_encontro=tipo,
        codigo=codigo,
        nome=nome,
        ordem=1,
        capacidade_minima_recomendada=1,
        capacidade_maxima_recomendada=capacidade_maxima,
    )
    role = TemplateRoleEquipe.objects.create(
        template_equipe=template,
        codigo='integrante',
        nome='Integrante',
        ordem=1,
        quantidade_estrutural=quantidade,
    )
    return template, role


class EncounterWorkServiceTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        self.template, self.template_role = criar_template()

    def _preparar_role(self, encontro=None):
        equipes = preparar_equipes_encontro(encontro or self.encontro)
        return equipes[0].roles.get()

    def _convite_confirmado(self, pessoa, *, encontro=None, role=None):
        convite = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=encontro or self.encontro,
            role_proposta=role,
            confirmar_avisos=True,
        )
        return responder_convite(
            convite,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

    def _trabalho(self, nome, *, encontro=None, role=None):
        pessoa = Pessoa.objects.create(nome=nome)
        convite = self._convite_confirmado(
            pessoa,
            encontro=encontro,
            role=role,
        )
        return iniciar_trabalho_confirmado(convite, confirmar_avisos=True)

    def test_materializa_snapshots_do_tipo_com_roles_ativas(self):
        TemplateRoleEquipe.objects.create(
            template_equipe=self.template,
            codigo='inativa',
            nome='Inativa',
            ativo=False,
        )
        criar_template(
            tipo=Encontro.Tipo.AVC,
            codigo='equipe-avc',
            nome='Equipe AVC',
        )

        equipes = preparar_equipes_encontro(self.encontro)

        self.assertEqual(len(equipes), 1)
        equipe = equipes[0]
        role = equipe.roles.get()
        self.assertEqual(equipe.template_origem, self.template)
        self.assertEqual(equipe.nome, self.template.nome)
        self.assertEqual(role.template_origem, self.template_role)
        self.assertEqual(role.quantidade_estrutural, 2)

    def test_catalogo_vazio_nao_e_populado_automaticamente(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ACAMPAMENTO)

        equipes = preparar_equipes_encontro(encontro)

        self.assertEqual(equipes, [])
        self.assertFalse(EquipeEncontro.objects.filter(encontro=encontro).exists())

    def test_materializacao_repetida_e_idempotente_e_congela_catalogo(self):
        primeira = preparar_equipes_encontro(self.encontro)
        criar_template(
            codigo='equipe-futura',
            nome='Equipe futura',
        )

        segunda = preparar_equipes_encontro(self.encontro)

        self.assertEqual(
            [equipe.pk for equipe in segunda],
            [equipe.pk for equipe in primeira],
        )
        self.assertEqual(
            EquipeEncontro.objects.filter(encontro=self.encontro).count(),
            1,
        )

    def test_alteracao_posterior_do_template_nao_muda_snapshot(self):
        role = self._preparar_role()
        equipe = role.equipe_encontro
        self.template.nome = 'Nome futuro'
        self.template.save(update_fields=['nome'])
        self.template_role.nome = 'Role futura'
        self.template_role.save(update_fields=['nome'])

        equipe.refresh_from_db()
        role.refresh_from_db()
        self.assertEqual(equipe.nome, 'Coordenação Geral')
        self.assertEqual(role.nome, 'Integrante')

    def test_convite_trabalho_permanece_separado_do_trabalho(self):
        pessoa = Pessoa.objects.create(nome='Pessoa convidada')

        convite = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=self.encontro,
            confirmar_avisos=True,
        )
        repetido = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=self.encontro,
            confirmar_avisos=True,
        )

        self.assertEqual(convite.pk, repetido.pk)
        self.assertEqual(convite.finalidade, ConviteEncontro.Finalidade.TRABALHAR)
        self.assertFalse(TrabalhoEncontro.objects.exists())

    def test_convite_com_role_proposta_valida_contexto_e_e_idempotente(self):
        role = self._preparar_role()
        pessoa = Pessoa.objects.create(nome='Pessoa com proposta')

        convite = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=self.encontro,
            role_proposta=role,
            confirmar_avisos=True,
        )
        repetido = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=self.encontro,
            role_proposta=role,
            confirmar_avisos=True,
        )

        self.assertEqual(repetido.pk, convite.pk)
        self.assertEqual(repetido.role_trabalho_proposta, role)

        outro_encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        with self.assertRaisesMessage(ValidationError, 'snapshot deste Encontro'):
            criar_convite_trabalho(
                pessoa=Pessoa.objects.create(nome='Pessoa cross-FK'),
                encontro=outro_encontro,
                role_proposta=role,
                confirmar_avisos=True,
            )

    def test_iniciar_trabalho_exige_convite_de_trabalho_confirmado(self):
        pessoa = Pessoa.objects.create(nome='Pessoa sem confirmação')
        convite = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=self.encontro,
            confirmar_avisos=True,
        )
        with self.assertRaisesMessage(ValidationError, 'convite confirmado'):
            iniciar_trabalho_confirmado(convite)

        convite_participar = ConviteEncontro.objects.create(
            pessoa=Pessoa.objects.create(nome='Pessoa participante'),
            encontro=self.encontro,
            finalidade=ConviteEncontro.Finalidade.PARTICIPAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        with self.assertRaisesMessage(ValidationError, 'finalidade TRABALHAR'):
            iniciar_trabalho_confirmado(convite_participar)

        self.assertFalse(TrabalhoEncontro.objects.exists())

    def test_criacao_de_trabalho_sem_role_e_idempotente(self):
        pessoa = Pessoa.objects.create(nome='Pessoa confirmada')
        convite = self._convite_confirmado(pessoa)

        trabalho = iniciar_trabalho_confirmado(
            convite,
            confirmar_avisos=True,
        )
        repetido = iniciar_trabalho_confirmado(
            convite,
            confirmar_avisos=True,
        )

        self.assertEqual(repetido.pk, trabalho.pk)
        self.assertEqual(
            trabalho.status,
            TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO,
        )
        self.assertIsNone(trabalho.role_equipe)
        self.assertEqual(TrabalhoEncontro.objects.count(), 1)

    def test_role_proposta_cria_trabalho_ja_alocado(self):
        role = self._preparar_role()
        trabalho = self._trabalho('Pessoa alocada', role=role)

        self.assertEqual(trabalho.status, TrabalhoEncontro.Status.ALOCADO)
        self.assertEqual(trabalho.role_equipe, role)

    def test_aloca_e_rejeita_role_de_outro_encontro_ou_incompativel(self):
        role = self._preparar_role()
        trabalho = self._trabalho('Pessoa aguardando')

        alocado = alocar_trabalho(
            trabalho,
            role,
            confirmar_avisos=True,
        )
        self.assertEqual(alocado.status, TrabalhoEncontro.Status.ALOCADO)
        self.assertEqual(alocado.role_equipe, role)

        outro_encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        outra_equipe = EquipeEncontro.objects.create(
            encontro=outro_encontro,
            template_origem=self.template,
            codigo='outra-equipe',
            nome='Outra equipe',
        )
        role_outro_encontro = RoleEquipeEncontro.objects.create(
            equipe_encontro=outra_equipe,
            template_origem=self.template_role,
            codigo='outra-role',
            nome='Outra role',
        )
        with self.assertRaisesMessage(ValidationError, 'snapshot deste Encontro'):
            alocar_trabalho(alocado, role_outro_encontro)

        outro_template, outra_template_role = criar_template(
            codigo='outro-template',
            nome='Outro template',
        )
        self.assertNotEqual(outro_template.pk, self.template.pk)
        role_incompativel = RoleEquipeEncontro.objects.create(
            equipe_encontro=role.equipe_encontro,
            template_origem=outra_template_role,
            codigo='incompativel',
            nome='Incompatível',
        )
        with self.assertRaisesMessage(ValidationError, 'incompatível'):
            alocar_trabalho(alocado, role_incompativel)

    def test_realoca_e_desaloca_antes_do_resultado(self):
        primeira_role = self._preparar_role()
        segundo_template, segunda_template_role = criar_template(
            codigo='apoio',
            nome='Apoio',
            quantidade=None,
        )
        segunda_equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=segundo_template,
            codigo=segundo_template.codigo,
            nome=segundo_template.nome,
        )
        segunda_role = RoleEquipeEncontro.objects.create(
            equipe_encontro=segunda_equipe,
            template_origem=segunda_template_role,
            codigo=segunda_template_role.codigo,
            nome=segunda_template_role.nome,
        )
        trabalho = self._trabalho('Pessoa realocada', role=primeira_role)

        realocado = alocar_trabalho(
            trabalho,
            segunda_role,
            confirmar_avisos=True,
        )
        self.assertEqual(realocado.role_equipe, segunda_role)
        desalocado = desalocar_trabalho(realocado)
        self.assertEqual(
            desalocado.status,
            TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO,
        )
        self.assertIsNone(desalocado.role_equipe)

    def test_quantidade_estrutural_bloqueia_mas_capacidade_consultiva_nao(self):
        role_estrutural = self._preparar_role()
        role_estrutural.quantidade_estrutural = 1
        role_estrutural.save(update_fields=['quantidade_estrutural'])
        self._trabalho('Primeira estrutural', role=role_estrutural)

        with self.assertRaisesMessage(ValidationError, 'quantidade estrutural'):
            self._trabalho('Segunda estrutural', role=role_estrutural)

        template, template_role = criar_template(
            codigo='consultiva',
            nome='Consultiva',
            quantidade=None,
            capacidade_maxima=1,
        )
        equipe = EquipeEncontro.objects.create(
            encontro=self.encontro,
            template_origem=template,
            codigo=template.codigo,
            nome=template.nome,
            capacidade_maxima_recomendada=1,
        )
        role_consultiva = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo=template_role.codigo,
            nome=template_role.nome,
        )
        self._trabalho('Primeira consultiva', role=role_consultiva)
        self._trabalho('Segunda consultiva', role=role_consultiva)

        self.assertEqual(
            TrabalhoEncontro.objects.filter(
                role_equipe=role_consultiva,
                status=TrabalhoEncontro.Status.ALOCADO,
            ).count(),
            2,
        )

    def test_retirada_e_idempotente_e_nao_conta_como_trabalho(self):
        role = self._preparar_role()
        trabalho = self._trabalho('Pessoa retirada', role=role)

        retirado = retirar_trabalho(trabalho)
        repetido = retirar_trabalho(retirado)

        self.assertEqual(repetido.status, TrabalhoEncontro.Status.RETIRADO)
        self.assertEqual(repetido.role_equipe, role)
        self.assertFalse(
            TrabalhoEncontro.objects.filter(
                pessoa=trabalho.pessoa,
                status=TrabalhoEncontro.Status.TRABALHOU,
            ).exists()
        )

    def test_resultado_distingue_trabalhou_de_faltou_e_bloqueia_reabertura(self):
        role = self._preparar_role()
        trabalhou = registrar_resultado_trabalho(
            self._trabalho('Pessoa trabalhou', role=role),
            status=TrabalhoEncontro.Status.TRABALHOU,
        )
        faltou = registrar_resultado_trabalho(
            self._trabalho('Pessoa faltou', role=role),
            status=TrabalhoEncontro.Status.FALTOU,
        )

        self.assertIsNotNone(trabalhou.resultado_registrado_em)
        self.assertIsNotNone(faltou.resultado_registrado_em)
        self.assertEqual(
            TrabalhoEncontro.objects.filter(
                status=TrabalhoEncontro.Status.TRABALHOU
            ).count(),
            1,
        )
        with self.assertRaisesMessage(ValidationError, 'estado final'):
            registrar_resultado_trabalho(
                faltou,
                status=TrabalhoEncontro.Status.TRABALHOU,
            )
        with self.assertRaisesMessage(ValidationError, 'finalizado'):
            alocar_trabalho(trabalhou, role)

    def test_substitui_na_mesma_posicao_sem_vinculo_especifico(self):
        role = self._preparar_role()
        anterior = self._trabalho('Pessoa anterior', role=role)
        novo = self._trabalho('Pessoa substituta')

        retirado, alocado = substituir_trabalho(
            anterior,
            novo,
            role,
            confirmar_avisos=True,
        )
        repetido = substituir_trabalho(
            retirado,
            alocado,
            role,
            confirmar_avisos=True,
        )

        self.assertEqual(retirado.status, TrabalhoEncontro.Status.RETIRADO)
        self.assertEqual(alocado.status, TrabalhoEncontro.Status.ALOCADO)
        self.assertEqual(alocado.role_equipe, role)
        self.assertFalse(hasattr(retirado, 'substituido_por'))
        self.assertEqual(
            [trabalho.pk for trabalho in repetido],
            [retirado.pk, alocado.pk],
        )

    def test_substituicao_faz_rollback_integral_em_falha_intermediaria(self):
        role = self._preparar_role()
        anterior = self._trabalho('Pessoa anterior rollback', role=role)
        novo = self._trabalho('Pessoa nova rollback')
        save_original = TrabalhoEncontro.save

        def falhar_no_novo(instance, *args, **kwargs):
            if instance.pk == novo.pk:
                raise RuntimeError('falha intermediária')
            return save_original(instance, *args, **kwargs)

        with patch.object(TrabalhoEncontro, 'save', new=falhar_no_novo):
            with self.assertRaisesMessage(RuntimeError, 'falha intermediária'):
                substituir_trabalho(
                    anterior,
                    novo,
                    role,
                    confirmar_avisos=True,
                )

        anterior.refresh_from_db()
        novo.refresh_from_db()
        self.assertEqual(anterior.status, TrabalhoEncontro.Status.ALOCADO)
        self.assertEqual(
            novo.status,
            TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO,
        )
        self.assertIsNone(novo.role_equipe)

    def test_fluxos_nao_criam_frequencia(self):
        role = self._preparar_role()
        trabalho = self._trabalho('Pessoa sem frequência', role=role)
        registrar_resultado_trabalho(
            trabalho,
            status=TrabalhoEncontro.Status.TRABALHOU,
        )

        self.assertFalse(Frequencia.objects.exists())


@skipUnless(connection.vendor == 'postgresql', 'exige PostgreSQL')
class EncounterWorkConcurrencyTests(TransactionTestCase):
    reset_sequences = True

    def _executar_em_threads(self, funcao):
        barreira = Barrier(2)

        def executar():
            close_old_connections()
            try:
                barreira.wait()
                return funcao()
            except ValidationError:
                return 'bloqueada'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(lambda _: executar(), range(2)))

    def test_materializacao_concorrente_cria_um_snapshot(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        criar_template(quantidade=None)

        resultados = self._executar_em_threads(
            lambda: [
                equipe.pk
                for equipe in preparar_equipes_encontro(
                    Encontro.objects.get(pk=encontro.pk)
                )
            ]
        )

        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(EquipeEncontro.objects.count(), 1)
        self.assertEqual(RoleEquipeEncontro.objects.count(), 1)

    def test_inicio_concorrente_cria_um_trabalho(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        pessoa = Pessoa.objects.create(nome='Pessoa concorrente')
        convite = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=encontro,
            confirmar_avisos=True,
        )
        responder_convite(
            convite,
            status=ConviteEncontro.Status.CONFIRMADO,
        )

        resultados = self._executar_em_threads(
            lambda: iniciar_trabalho_confirmado(
                ConviteEncontro.objects.get(pk=convite.pk),
                confirmar_avisos=True,
            ).pk
        )

        self.assertEqual(resultados[0], resultados[1])
        self.assertEqual(TrabalhoEncontro.objects.count(), 1)

    def test_alocacoes_concorrentes_respeitam_quantidade_estrutural(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        criar_template(quantidade=1)
        role = preparar_equipes_encontro(encontro)[0].roles.get()
        trabalhos = []
        for indice in range(2):
            pessoa = Pessoa.objects.create(nome=f'Pessoa concorrente {indice}')
            convite = criar_convite_trabalho(
                pessoa=pessoa,
                encontro=encontro,
                confirmar_avisos=True,
            )
            responder_convite(
                convite,
                status=ConviteEncontro.Status.CONFIRMADO,
            )
            trabalhos.append(iniciar_trabalho_confirmado(
                convite,
                confirmar_avisos=True,
            ))
        indice = iter(range(2))

        resultados = self._executar_em_threads(
            lambda: alocar_trabalho(
                TrabalhoEncontro.objects.get(pk=trabalhos[next(indice)].pk),
                RoleEquipeEncontro.objects.get(pk=role.pk),
                confirmar_avisos=True,
            ).pk
        )

        self.assertEqual(resultados.count('bloqueada'), 1)
        self.assertEqual(
            TrabalhoEncontro.objects.filter(
                role_equipe=role,
                status=TrabalhoEncontro.Status.ALOCADO,
            ).count(),
            1,
        )

    def test_realocacoes_concorrentes_preservam_um_unico_estado(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        criar_template(codigo='origem', nome='Origem', quantidade=None)
        criar_template(codigo='destino-a', nome='Destino A', quantidade=None)
        criar_template(codigo='destino-b', nome='Destino B', quantidade=None)
        equipes = preparar_equipes_encontro(encontro)
        roles = {
            equipe.codigo: equipe.roles.get()
            for equipe in equipes
        }
        pessoa = Pessoa.objects.create(nome='Pessoa realocação concorrente')
        convite = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=encontro,
            role_proposta=roles['origem'],
            confirmar_avisos=True,
        )
        responder_convite(
            convite,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        trabalho = iniciar_trabalho_confirmado(
            convite,
            confirmar_avisos=True,
        )
        destinos = iter((roles['destino-a'].pk, roles['destino-b'].pk))

        resultados = self._executar_em_threads(
            lambda: alocar_trabalho(
                TrabalhoEncontro.objects.get(pk=trabalho.pk),
                RoleEquipeEncontro.objects.get(pk=next(destinos)),
                confirmar_avisos=True,
            ).role_equipe_id
        )

        self.assertEqual(
            set(resultados),
            {roles['destino-a'].pk, roles['destino-b'].pk},
        )
        trabalho.refresh_from_db()
        self.assertIn(
            trabalho.role_equipe_id,
            {roles['destino-a'].pk, roles['destino-b'].pk},
        )
        self.assertEqual(TrabalhoEncontro.objects.count(), 1)

    def test_resultados_concorrentes_mantem_um_estado_final(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        criar_template(quantidade=None)
        role = preparar_equipes_encontro(encontro)[0].roles.get()
        pessoa = Pessoa.objects.create(nome='Pessoa resultado concorrente')
        convite = criar_convite_trabalho(
            pessoa=pessoa,
            encontro=encontro,
            role_proposta=role,
            confirmar_avisos=True,
        )
        responder_convite(
            convite,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        trabalho = iniciar_trabalho_confirmado(
            convite,
            confirmar_avisos=True,
        )
        resultados_finais = iter((
            TrabalhoEncontro.Status.TRABALHOU,
            TrabalhoEncontro.Status.FALTOU,
        ))

        resultados = self._executar_em_threads(
            lambda: registrar_resultado_trabalho(
                TrabalhoEncontro.objects.get(pk=trabalho.pk),
                status=next(resultados_finais),
            ).status
        )

        self.assertEqual(resultados.count('bloqueada'), 1)
        trabalho.refresh_from_db()
        self.assertIn(
            trabalho.status,
            {
                TrabalhoEncontro.Status.TRABALHOU,
                TrabalhoEncontro.Status.FALTOU,
            },
        )
