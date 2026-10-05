from itertools import count

from django.test import TestCase
from django.utils import timezone

from core.models import (
    ConviteEncontro,
    DadosSaudePessoa,
    Encontro,
    EquipeEncontro,
    Frequencia,
    ParticipacaoEncontro,
    PerfilAlpinista,
    Pessoa,
    RoleEquipeEncontro,
    TemplateEquipeEncontro,
    TemplateRoleEquipe,
    TrabalhoEncontro,
)
from core.services.elegibilidade_trabalho import (
    AvisosElegibilidadePendentes,
    BloqueioElegibilidadeTrabalho,
    CodigoElegibilidade,
    ResultadoElegibilidade,
    avaliar_capacidade_equipe,
    avaliar_composicao_estrutural,
    avaliar_elegibilidade_trabalho,
)
from core.services.trabalhos import (
    alocar_trabalho,
    criar_convite_trabalho,
)
from core.tests.factories import make_alpinista, make_encontro


class EncounterWorkEligibilityTests(TestCase):
    def setUp(self):
        self._sequencia = count(1)

    def _pessoa_alpinista(self, *, status='ativo', com_perfil=True):
        numero = next(self._sequencia)
        pessoa = Pessoa.objects.create(nome=f'Pessoa elegível {numero}')
        if com_perfil:
            PerfilAlpinista.objects.create(pessoa=pessoa)
        alpinista = make_alpinista(pessoa=pessoa, status=status)
        return pessoa, alpinista

    def _concluir(self, pessoa, tipo):
        encontro = make_encontro(tipo=tipo)
        return ParticipacaoEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            resultado=ParticipacaoEncontro.Resultado.CONCLUIU,
            tipo_encontro=tipo,
        )

    def _equipe_role(
        self,
        encontro,
        *,
        codigo=None,
        minimo=None,
        maximo=None,
        quantidade=None,
    ):
        numero = next(self._sequencia)
        codigo = codigo or f'equipe-{numero}'
        template = TemplateEquipeEncontro.objects.create(
            tipo_encontro=encontro.tipo,
            codigo=codigo,
            nome=f'Equipe {numero}',
        )
        template_role = TemplateRoleEquipe.objects.create(
            template_equipe=template,
            codigo='integrante',
            nome='Integrante',
            quantidade_estrutural=quantidade,
        )
        equipe = EquipeEncontro.objects.create(
            encontro=encontro,
            template_origem=template,
            codigo=codigo,
            nome=template.nome,
            capacidade_minima_recomendada=minimo,
            capacidade_maxima_recomendada=maximo,
        )
        role = RoleEquipeEncontro.objects.create(
            equipe_encontro=equipe,
            template_origem=template_role,
            codigo=template_role.codigo,
            nome=template_role.nome,
            quantidade_estrutural=quantidade,
        )
        return equipe, role

    def _trabalho(self, pessoa, encontro, *, role=None, status=None):
        convite = ConviteEncontro.objects.create(
            pessoa=pessoa,
            encontro=encontro,
            finalidade=ConviteEncontro.Finalidade.TRABALHAR,
            status=ConviteEncontro.Status.CONFIRMADO,
        )
        valores = {
            'pessoa': pessoa,
            'encontro': encontro,
            'convite': convite,
        }
        if role is not None:
            valores['role_equipe'] = role
            valores['status'] = status or TrabalhoEncontro.Status.ALOCADO
            if valores['status'] in {
                TrabalhoEncontro.Status.TRABALHOU,
                TrabalhoEncontro.Status.FALTOU,
            }:
                valores['resultado_registrado_em'] = timezone.now()
        return TrabalhoEncontro.objects.create(**valores)

    def test_alpinista_ativo_e_elegivel_no_caminho_escalada(self):
        pessoa, _ = self._pessoa_alpinista()
        self._concluir(pessoa, Encontro.Tipo.ESCALADA)
        self._concluir(pessoa, Encontro.Tipo.AVC)

        avaliacao = avaliar_elegibilidade_trabalho(
            pessoa,
            make_encontro(tipo=Encontro.Tipo.ESCALADA),
        )

        self.assertEqual(avaliacao.resultado, ResultadoElegibilidade.ELEGIVEL)
        self.assertEqual(avaliacao.codigos, ())
        self.assertEqual(avaliacao.as_dict()['resultado'], 'ELEGIVEL')

    def test_alpinista_inativo_e_permitido_com_codigo_de_aviso(self):
        pessoa, _ = self._pessoa_alpinista(status='inativo')
        self._concluir(pessoa, Encontro.Tipo.ESPPA)

        avaliacao = avaliar_elegibilidade_trabalho(
            pessoa,
            make_encontro(tipo=Encontro.Tipo.ESCALADA),
        )

        self.assertEqual(avaliacao.resultado, ResultadoElegibilidade.AVISO)
        self.assertIn(
            CodigoElegibilidade.ALPINISTA_INATIVO.value,
            avaliacao.codigos,
        )
        self.assertFalse(avaliacao.bloqueios)
        self.assertTrue(avaliacao.avisos[0].mensagem)

    def test_perfil_ausente_e_atividade_desconhecida_produzem_avisos(self):
        pessoa_sem_perfil, _ = self._pessoa_alpinista(com_perfil=False)
        self._concluir(pessoa_sem_perfil, Encontro.Tipo.ESPPA)
        sem_perfil = avaliar_elegibilidade_trabalho(
            pessoa_sem_perfil,
            make_encontro(tipo=Encontro.Tipo.ESPPA),
        )
        self.assertIn(
            CodigoElegibilidade.PERFIL_ALPINISTA_AUSENTE.value,
            sem_perfil.codigos,
        )

        pessoa_sem_estado = Pessoa.objects.create(nome='Sem estado legado')
        PerfilAlpinista.objects.create(pessoa=pessoa_sem_estado)
        self._concluir(pessoa_sem_estado, Encontro.Tipo.ESPPA)
        sem_estado = avaliar_elegibilidade_trabalho(
            pessoa_sem_estado,
            make_encontro(tipo=Encontro.Tipo.ESPPA),
        )
        self.assertIn(
            CodigoElegibilidade.ATIVIDADE_NAO_DETERMINADA.value,
            sem_estado.codigos,
        )

    def test_caminho_escalada_sem_avc_e_bloqueado(self):
        pessoa, _ = self._pessoa_alpinista()
        self._concluir(pessoa, Encontro.Tipo.ESCALADA)

        avaliacao = avaliar_elegibilidade_trabalho(
            pessoa,
            make_encontro(tipo=Encontro.Tipo.ESCALADA),
        )

        self.assertEqual(avaliacao.resultado, ResultadoElegibilidade.BLOQUEIO)
        self.assertEqual(
            avaliacao.bloqueios[0].codigo,
            CodigoElegibilidade.AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA,
        )

    def test_caminho_esppa_habilita_trabalho_em_escalada_e_esppa(self):
        pessoa, _ = self._pessoa_alpinista()
        self._concluir(pessoa, Encontro.Tipo.ESPPA)

        for tipo in (Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA):
            with self.subTest(tipo=tipo):
                avaliacao = avaliar_elegibilidade_trabalho(
                    pessoa,
                    make_encontro(tipo=tipo),
                )
                self.assertEqual(
                    avaliacao.resultado,
                    ResultadoElegibilidade.ELEGIVEL,
                )

    def test_escalada_mais_avc_habilita_trabalho_em_esppa(self):
        pessoa, _ = self._pessoa_alpinista()
        self._concluir(pessoa, Encontro.Tipo.ESCALADA)
        self._concluir(pessoa, Encontro.Tipo.AVC)

        avaliacao = avaliar_elegibilidade_trabalho(
            pessoa,
            make_encontro(tipo=Encontro.Tipo.ESPPA),
        )

        self.assertEqual(avaliacao.resultado, ResultadoElegibilidade.ELEGIVEL)

    def test_caminho_sem_evidencia_exige_revisao_sem_bloquear(self):
        pessoa, _ = self._pessoa_alpinista()

        avaliacao = avaliar_elegibilidade_trabalho(
            pessoa,
            make_encontro(tipo=Encontro.Tipo.ESCALADA),
        )

        self.assertEqual(avaliacao.resultado, ResultadoElegibilidade.AVISO)
        self.assertIn(
            CodigoElegibilidade.CAMINHO_FORMATIVO_NAO_DETERMINADO.value,
            avaliacao.codigos,
        )
        self.assertFalse(avaliacao.bloqueios)

    def test_avc_e_acampamento_usam_revisao_manual_sem_regra_inventada(self):
        pessoa, _ = self._pessoa_alpinista()
        casos = (
            (
                Encontro.Tipo.AVC,
                CodigoElegibilidade.REVISAO_MANUAL_TRABALHO_AVC,
            ),
            (
                Encontro.Tipo.ACAMPAMENTO,
                CodigoElegibilidade.REVISAO_MANUAL_TRABALHO_ACAMPAMENTO,
            ),
        )

        for tipo, codigo in casos:
            with self.subTest(tipo=tipo):
                avaliacao = avaliar_elegibilidade_trabalho(
                    pessoa,
                    make_encontro(tipo=tipo),
                )
                self.assertEqual(
                    avaliacao.resultado,
                    ResultadoElegibilidade.AVISO,
                )
                self.assertIn(codigo.value, avaliacao.codigos)
                self.assertFalse(avaliacao.bloqueios)

    def test_capacidade_e_consultiva_dentro_e_fora_da_referencia(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ESPPA)
        equipe, _ = self._equipe_role(
            encontro,
            minimo=1,
            maximo=1,
        )

        dentro = avaliar_capacidade_equipe(equipe, ocupacao_adicional=1)
        abaixo = avaliar_capacidade_equipe(equipe)
        acima = avaliar_capacidade_equipe(equipe, ocupacao_adicional=2)

        self.assertEqual(dentro.resultado, ResultadoElegibilidade.ELEGIVEL)
        self.assertIn(
            CodigoElegibilidade.CAPACIDADE_MINIMA_NAO_ATINGIDA.value,
            abaixo.codigos,
        )
        self.assertIn(
            CodigoElegibilidade.CAPACIDADE_MAXIMA_EXCEDIDA.value,
            acima.codigos,
        )
        self.assertFalse(abaixo.bloqueios)
        self.assertFalse(acima.bloqueios)

    def test_composicao_estrutural_distingue_pendente_valida_e_excedida(self):
        encontro = make_encontro(tipo=Encontro.Tipo.ESPPA)
        equipe, role = self._equipe_role(encontro, quantidade=1)
        pendente = avaliar_composicao_estrutural(equipe)
        self.assertIn(
            CodigoElegibilidade.COMPOSICAO_ESTRUTURAL_INCOMPLETA.value,
            pendente.codigos,
        )
        self.assertFalse(pendente.bloqueios)

        primeira, _ = self._pessoa_alpinista()
        self._trabalho(primeira, encontro, role=role)
        valida = avaliar_composicao_estrutural(equipe)
        self.assertEqual(valida.resultado, ResultadoElegibilidade.ELEGIVEL)

        segunda, _ = self._pessoa_alpinista()
        self._trabalho(segunda, encontro, role=role)
        excedida = avaliar_composicao_estrutural(equipe)
        self.assertEqual(excedida.resultado, ResultadoElegibilidade.BLOQUEIO)
        self.assertIn(
            CodigoElegibilidade.QUANTIDADE_ESTRUTURAL_EXCEDIDA.value,
            excedida.codigos,
        )

    def test_convite_bloqueia_invariante_e_exige_override_para_aviso(self):
        pessoa_bloqueada, _ = self._pessoa_alpinista()
        self._concluir(pessoa_bloqueada, Encontro.Tipo.ESCALADA)
        escalada = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        with self.assertRaises(BloqueioElegibilidadeTrabalho) as bloqueio:
            criar_convite_trabalho(
                pessoa=pessoa_bloqueada,
                encontro=escalada,
                confirmar_avisos=True,
            )
        self.assertIn(
            CodigoElegibilidade.AVC_NAO_CONCLUIDO_CAMINHO_ESCALADA.value,
            bloqueio.exception.avaliacao.codigos,
        )
        self.assertFalse(ConviteEncontro.objects.filter(encontro=escalada).exists())

        pessoa_aviso, _ = self._pessoa_alpinista(status='inativo')
        self._concluir(pessoa_aviso, Encontro.Tipo.ESPPA)
        esppa = make_encontro(tipo=Encontro.Tipo.ESPPA)
        with self.assertRaises(AvisosElegibilidadePendentes):
            criar_convite_trabalho(pessoa=pessoa_aviso, encontro=esppa)
        convite = criar_convite_trabalho(
            pessoa=pessoa_aviso,
            encontro=esppa,
            confirmar_avisos=True,
        )
        self.assertIn(
            CodigoElegibilidade.ALPINISTA_INATIVO.value,
            convite.avaliacao_elegibilidade.codigos,
        )

    def test_alocacao_respeita_bloqueio_estrutural(self):
        pessoa, _ = self._pessoa_alpinista()
        self._concluir(pessoa, Encontro.Tipo.ESCALADA)
        encontro = make_encontro(tipo=Encontro.Tipo.ESCALADA)
        _, role = self._equipe_role(encontro)
        trabalho = self._trabalho(pessoa, encontro)

        with self.assertRaises(BloqueioElegibilidadeTrabalho):
            alocar_trabalho(
                trabalho,
                role,
                confirmar_avisos=True,
            )

        trabalho.refresh_from_db()
        self.assertEqual(
            trabalho.status,
            TrabalhoEncontro.Status.AGUARDANDO_ALOCACAO,
        )
        self.assertIsNone(trabalho.role_equipe)

    def test_alocacao_com_aviso_exige_confirmacao_e_preserva_codigos(self):
        pessoa, _ = self._pessoa_alpinista(status='inativo')
        self._concluir(pessoa, Encontro.Tipo.ESPPA)
        encontro = make_encontro(tipo=Encontro.Tipo.ESPPA)
        _, role = self._equipe_role(encontro)
        trabalho = self._trabalho(pessoa, encontro)

        with self.assertRaises(AvisosElegibilidadePendentes):
            alocar_trabalho(trabalho, role)
        alocado = alocar_trabalho(
            trabalho,
            role,
            confirmar_avisos=True,
        )

        self.assertEqual(alocado.status, TrabalhoEncontro.Status.ALOCADO)
        self.assertIn(
            CodigoElegibilidade.ALPINISTA_INATIVO.value,
            alocado.avaliacao_elegibilidade.codigos,
        )

    def test_realocacao_reavalia_estado_atual(self):
        pessoa, alpinista = self._pessoa_alpinista()
        self._concluir(pessoa, Encontro.Tipo.ESPPA)
        encontro = make_encontro(tipo=Encontro.Tipo.ESPPA)
        _, role_origem = self._equipe_role(encontro, codigo='origem')
        _, role_destino = self._equipe_role(encontro, codigo='destino')
        trabalho = self._trabalho(pessoa, encontro)
        alocar_trabalho(trabalho, role_origem)

        alpinista.status = 'inativo'
        alpinista.save(update_fields=['status'])
        with self.assertRaises(AvisosElegibilidadePendentes):
            alocar_trabalho(trabalho, role_destino)
        realocado = alocar_trabalho(
            trabalho,
            role_destino,
            confirmar_avisos=True,
        )

        self.assertEqual(realocado.role_equipe, role_destino)
        self.assertIn(
            CodigoElegibilidade.ALPINISTA_INATIVO.value,
            realocado.avaliacao_elegibilidade.codigos,
        )

    def test_fluxo_nao_cria_frequencia_nem_altera_saude(self):
        pessoa, _ = self._pessoa_alpinista(status='inativo')
        self._concluir(pessoa, Encontro.Tipo.ESPPA)
        saude = DadosSaudePessoa.objects.create(
            pessoa=pessoa,
            alergias='Dado preservado',
            medicamentos='Dado preservado',
        )
        encontro = make_encontro(tipo=Encontro.Tipo.ESPPA)
        _, role = self._equipe_role(encontro)
        trabalho = self._trabalho(pessoa, encontro)

        alocar_trabalho(trabalho, role, confirmar_avisos=True)

        saude.refresh_from_db()
        self.assertEqual(saude.alergias, 'Dado preservado')
        self.assertEqual(saude.medicamentos, 'Dado preservado')
        self.assertFalse(Frequencia.objects.exists())

    def test_avaliacao_posterior_nao_altera_historico_concluido(self):
        pessoa, alpinista = self._pessoa_alpinista()
        self._concluir(pessoa, Encontro.Tipo.ESPPA)
        encontro_anterior = make_encontro(tipo=Encontro.Tipo.ESPPA)
        _, role = self._equipe_role(encontro_anterior)
        trabalho = self._trabalho(
            pessoa,
            encontro_anterior,
            role=role,
            status=TrabalhoEncontro.Status.TRABALHOU,
        )
        resultado_em = trabalho.resultado_registrado_em
        alpinista.status = 'inativo'
        alpinista.save(update_fields=['status'])

        avaliar_elegibilidade_trabalho(
            pessoa,
            make_encontro(tipo=Encontro.Tipo.ESPPA),
        )

        trabalho.refresh_from_db()
        self.assertEqual(trabalho.status, TrabalhoEncontro.Status.TRABALHOU)
        self.assertEqual(trabalho.resultado_registrado_em, resultado_em)
