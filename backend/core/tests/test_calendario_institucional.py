from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import CalendarioEncontro, DiaEncontro, Encontro
from core.roles import RECOGNIZED_ROLES, SiaRole
from core.services.calendario_institucional import (
    CONFIRMACAO_INDETERMINADA,
    CONFIRMACAO_OFICIAL,
    CONFIRMACAO_PROVISORIA,
    ORIGEM_CANONICA,
    ORIGEM_LEGADO,
    consultar_calendario_institucional,
)
from core.tests.factories import make_encontro


def criar_encontro_canonico(
    titulo,
    datas,
    *,
    status_encontro=Encontro.Status.EM_AGENDAMENTO,
    oficial=False,
    versao=1,
    vigente=True,
):
    encontro = make_encontro(
        encontro=titulo,
        data_referencia=datas[0],
        data_exato='compatibilidade legada',
        status=status_encontro,
    )
    calendario = CalendarioEncontro.objects.create(
        encontro=encontro,
        versao=versao,
        vigente=vigente,
        oficializado_em=timezone.now() if oficial else None,
    )
    DiaEncontro.objects.bulk_create([
        DiaEncontro(calendario=calendario, ordem=ordem, data=data_dia)
        for ordem, data_dia in enumerate(datas, start=1)
    ])
    return encontro, calendario


class CalendarioInstitucionalProjectionTests(TestCase):
    def test_projeta_um_encontro_uma_vez_com_dias_inclusivos_no_periodo(self):
        encontro, calendario = criar_encontro_canonico(
            'Escalada não consecutiva',
            [date(2031, 5, 1), date(2031, 5, 3), date(2031, 6, 1)],
            status_encontro=Encontro.Status.AGENDADO,
            oficial=True,
        )

        resultado = consultar_calendario_institucional(
            date(2031, 5, 1),
            date(2031, 5, 31),
        )

        self.assertEqual(len(resultado.itens), 1)
        item = resultado.itens[0]
        self.assertEqual(item.encontro_id, encontro.pk)
        self.assertEqual(item.calendario_id, calendario.pk)
        self.assertEqual(item.categoria, 'ENCONTRO')
        self.assertEqual(item.status, Encontro.Status.AGENDADO)
        self.assertEqual(item.origem_agenda, ORIGEM_CANONICA)
        self.assertEqual(item.confirmacao, CONFIRMACAO_OFICIAL)
        self.assertEqual(
            [dia.data for dia in item.dias],
            [date(2031, 5, 1), date(2031, 5, 3)],
        )

    def test_agenda_provisoria_e_fallback_legado_sao_explicitos(self):
        criar_encontro_canonico(
            'Planejamento',
            [date(2031, 7, 10)],
        )
        legado = make_encontro(
            encontro='Legado',
            data_referencia=date(2031, 7, 11),
            data_exato='texto que não deve ser interpretado',
            status=Encontro.Status.FINALIZADO,
        )

        resultado = consultar_calendario_institucional(
            date(2031, 7, 1),
            date(2031, 7, 31),
        )
        por_id = {item.encontro_id: item for item in resultado.itens}

        provisoria = next(
            item for item in resultado.itens if item.titulo == 'Planejamento'
        )
        self.assertEqual(provisoria.confirmacao, CONFIRMACAO_PROVISORIA)
        self.assertEqual(por_id[legado.pk].origem_agenda, ORIGEM_LEGADO)
        self.assertEqual(
            por_id[legado.pk].confirmacao,
            CONFIRMACAO_INDETERMINADA,
        )
        self.assertIsNone(por_id[legado.pk].dias[0].id)

    def test_estrutura_canonica_prevalece_sem_fallback_silencioso(self):
        encontro, _ = criar_encontro_canonico(
            'Canônico fora do intervalo',
            [date(2031, 9, 1)],
        )
        encontro.data_referencia = date(2031, 8, 1)
        encontro.save(update_fields=['data_referencia'])

        resultado = consultar_calendario_institucional(
            date(2031, 8, 1),
            date(2031, 8, 31),
        )

        self.assertEqual(resultado.itens, ())

    def test_somente_agenda_vigente_e_projetada_apos_reprogramacao(self):
        encontro, antiga = criar_encontro_canonico(
            'Reprogramado',
            [date(2031, 10, 2)],
            status_encontro=Encontro.Status.AGENDADO,
            oficial=True,
            vigente=False,
        )
        antiga.substituido_em = timezone.now()
        antiga.save(update_fields=['substituido_em'])
        atual = CalendarioEncontro.objects.create(
            encontro=encontro,
            versao=2,
            vigente=True,
            oficializado_em=timezone.now(),
        )
        DiaEncontro.objects.create(
            calendario=atual,
            ordem=1,
            data=date(2031, 10, 20),
        )

        resultado = consultar_calendario_institucional(
            date(2031, 10, 1),
            date(2031, 10, 31),
        )

        self.assertEqual(len(resultado.itens), 1)
        self.assertEqual(resultado.itens[0].calendario_versao, 2)
        self.assertEqual(
            [dia.data for dia in resultado.itens[0].dias],
            [date(2031, 10, 20)],
        )

    def test_estados_adiado_cancelado_e_finalizado_seguem_agenda_atual(self):
        adiado, calendario_adiado = criar_encontro_canonico(
            'Adiado',
            [date(2031, 11, 1)],
            status_encontro=Encontro.Status.ADIADO,
            oficial=True,
            vigente=False,
        )
        calendario_adiado.substituido_em = timezone.now()
        calendario_adiado.save(update_fields=['substituido_em'])
        cancelado, _ = criar_encontro_canonico(
            'Cancelado',
            [date(2031, 11, 2)],
            status_encontro=Encontro.Status.CANCELADO,
            oficial=True,
        )
        finalizado, _ = criar_encontro_canonico(
            'Finalizado',
            [date(2031, 11, 3)],
            status_encontro=Encontro.Status.FINALIZADO,
            oficial=True,
        )

        resultado = consultar_calendario_institucional(
            date(2031, 11, 1),
            date(2031, 11, 30),
        )
        ids = {item.encontro_id for item in resultado.itens}

        self.assertNotIn(adiado.pk, ids)
        self.assertIn(cancelado.pk, ids)
        self.assertIn(finalizado.pk, ids)

    def test_conflitos_sao_consultivos_e_anotados_sem_efeitos_colaterais(self):
        primeiro, _ = criar_encontro_canonico(
            'Primeiro',
            [date(2032, 1, 1), date(2032, 1, 5)],
        )
        segundo, _ = criar_encontro_canonico(
            'Segundo',
            [date(2032, 1, 5), date(2032, 1, 8)],
        )
        quantidade_antes = (Encontro.objects.count(), DiaEncontro.objects.count())

        resultado = consultar_calendario_institucional(
            date(2032, 1, 1),
            date(2032, 1, 31),
        )

        self.assertEqual(len(resultado.conflitos), 1)
        conflito = resultado.conflitos[0]
        self.assertEqual(conflito.data, date(2032, 1, 5))
        self.assertEqual(
            conflito.encontro_ids,
            tuple(sorted((primeiro.pk, segundo.pk))),
        )
        self.assertEqual(conflito.quantidade, 2)
        for item in resultado.itens:
            dia_conflitante = next(
                dia for dia in item.dias if dia.data == date(2032, 1, 5)
            )
            self.assertEqual(dia_conflitante.conflito, conflito)
        self.assertEqual(
            (Encontro.objects.count(), DiaEncontro.objects.count()),
            quantidade_antes,
        )

    def test_ordenacao_e_query_count_sao_deterministicos(self):
        criar_encontro_canonico('Zulu', [date(2032, 2, 2)])
        criar_encontro_canonico('Beta', [date(2032, 2, 1)])
        criar_encontro_canonico('Alfa', [date(2032, 2, 1)])

        with self.assertNumQueries(4):
            resultado = consultar_calendario_institucional(
                date(2032, 1, 1),
                date(2032, 12, 31),
            )
            titulos = [item.titulo for item in resultado.itens]

        self.assertEqual(titulos, ['Alfa', 'Beta', 'Zulu'])

    def test_intervalo_invertido_ou_maior_que_um_ano_e_rejeitado(self):
        with self.assertRaises(ValueError):
            consultar_calendario_institucional(
                date(2032, 2, 1),
                date(2032, 1, 1),
            )
        with self.assertRaises(ValueError):
            consultar_calendario_institucional(
                date(2031, 1, 1),
                date(2032, 1, 2),
            )


class CalendarioInstitucionalApiTests(APITestCase):
    url = '/api/calendario-institucional/'

    def setUp(self):
        self.user = self._make_user('suporte', SiaRole.SUPORTE)
        self.client.force_authenticate(self.user)
        self.encontro, _ = criar_encontro_canonico(
            'Calendário público interno',
            [date(2033, 3, 10)],
            status_encontro=Encontro.Status.AGENDADO,
            oficial=True,
        )

    def _make_user(self, username, role=None, *, superuser=False):
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

    def _get(self, **params):
        values = {'inicio': '2033-03-01', 'fim': '2033-03-31'}
        values.update(params)
        return self.client.get(self.url, values)

    def test_retorna_contrato_allowlist_sem_dados_operacionais(self):
        response = self._get()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            set(response.json()),
            {'periodo', 'itens', 'conflitos', 'capabilities'},
        )
        item = response.json()['itens'][0]
        self.assertEqual(
            set(item),
            {
                'categoria', 'encontro_id', 'titulo', 'tipo', 'status',
                'calendario_id', 'calendario_versao', 'origem_agenda',
                'confirmacao', 'dias', 'agenda',
                'pode_editar_calendario',
            },
        )
        self.assertEqual(
            set(item['dias'][0]),
            {'id', 'data', 'ordem', 'rotulo', 'conflito'},
        )
        self.assertNotIn('status_encontro', item)
        for campo_sensivel in (
            'participantes', 'equipes', 'saude', 'inscricoes', 'convites',
            'formacao', 'observacoes', 'local',
        ):
            self.assertNotIn(campo_sensivel, item)

    def test_periodo_mensal_anual_arbitrario_e_limites_inclusivos(self):
        mensal = self._get()
        anual = self.client.get(
            self.url,
            {'inicio': '2033-01-01', 'fim': '2033-12-31'},
        )
        limite = self.client.get(
            self.url,
            {'inicio': '2033-03-10', 'fim': '2033-03-10'},
        )
        fora = self.client.get(
            self.url,
            {'inicio': '2033-03-11', 'fim': '2033-03-20'},
        )

        self.assertEqual(len(mensal.json()['itens']), 1)
        self.assertEqual(len(anual.json()['itens']), 1)
        self.assertEqual(len(limite.json()['itens']), 1)
        self.assertEqual(fora.json()['itens'], [])

    def test_parametros_invalidos_retorna_400(self):
        casos = (
            {},
            {'inicio': 'invalida', 'fim': '2033-03-31'},
            {'inicio': '2033-04-01', 'fim': '2033-03-01'},
            {'inicio': '2032-01-01', 'fim': '2033-01-02'},
            {'inicio': '2033-03-01', 'fim': '2033-03-31', 'extra': 'x'},
        )
        for params in casos:
            with self.subTest(params=params):
                response = self.client.get(self.url, params)
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_todos_os_papeis_funcionais_e_superuser_podem_ler(self):
        for index, role_name in enumerate(RECOGNIZED_ROLES):
            role = SiaRole(role_name)
            user = self._make_user(f'papel-{index}', role)
            self.client.force_authenticate(user)
            with self.subTest(role=role_name):
                self.assertEqual(self._get().status_code, status.HTTP_200_OK)

        superuser = self._make_user('superuser', superuser=True)
        self.client.force_authenticate(superuser)
        self.assertEqual(self._get().status_code, status.HTTP_200_OK)

    def test_autenticacao_default_deny_e_metodo_nao_exposto(self):
        sem_role = self._make_user('sem-role')
        self.client.force_authenticate(sem_role)
        self.assertEqual(self._get().status_code, status.HTTP_403_FORBIDDEN)

        self.client.force_authenticate(user=None)
        self.assertEqual(self._get().status_code, status.HTTP_401_UNAUTHORIZED)

        self.client.force_authenticate(self.user)
        self.assertEqual(
            self.client.post(self.url, {}, format='json').status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def test_capabilities_refletem_politica_sem_ampliar_encontros(self):
        suporte = self._get().json()
        self.assertTrue(suporte['capabilities']['pode_criar_encontro'])
        self.assertTrue(suporte['itens'][0]['pode_editar_calendario'])

        mme = self._make_user('mme', SiaRole.MME)
        self.client.force_authenticate(mme)
        resposta_mme = self._get()
        self.assertEqual(resposta_mme.status_code, status.HTTP_200_OK)
        self.assertFalse(
            resposta_mme.json()['capabilities']['pode_criar_encontro']
        )
        self.assertFalse(
            resposta_mme.json()['itens'][0]['pode_editar_calendario']
        )
        self.assertEqual(
            self.client.get('/api/encontros/').status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_resposta_nao_e_paginada_e_inclui_conflitos_estruturados(self):
        outro, _ = criar_encontro_canonico(
            'Outro',
            [date(2033, 3, 10)],
        )

        response = self._get()

        self.assertNotIn('results', response.json())
        conflito = response.json()['conflitos'][0]
        self.assertEqual(conflito['data'], '2033-03-10')
        self.assertEqual(
            conflito['encontro_ids'],
            sorted((self.encontro.pk, outro.pk)),
        )
        self.assertEqual(conflito['quantidade'], 2)

    def test_indice_de_data_esta_declarado_no_model(self):
        self.assertIn(
            'dia_encontro_data_idx',
            [index.name for index in DiaEncontro._meta.indexes],
        )
