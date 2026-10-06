from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import close_old_connections, connection
from django.test import TransactionTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    CalendarioEncontro,
    DiaEncontro,
    Encontro,
    LogSistema,
)
from core.roles import SiaRole
from core.services import comandos_calendario as command_services
from core.tests.factories import make_encontro
from core.tests.test_calendario_institucional import criar_encontro_canonico


class CalendarioInstitucionalCommandApiTests(APITestCase):
    base_url = '/api/calendario-institucional/encontros/'

    def setUp(self):
        self.user = self._make_user('suporte', SiaRole.SUPORTE)
        self.client.force_authenticate(self.user)

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

    def _payload_criacao(self, *, titulo='Escalada pelo calendário', datas=None):
        datas = datas or [date(2034, 4, 3), date(2034, 4, 6)]
        return {
            'encontro': titulo,
            'tipo': Encontro.Tipo.ESCALADA,
            'local': 'Nova Betânia',
            'dias': [
                {
                    'ordem': ordem,
                    'data': data_dia.isoformat(),
                    'descricao': f'Dia {ordem}',
                }
                for ordem, data_dia in enumerate(datas, start=1)
            ],
        }

    def _criar(self, **kwargs):
        return self.client.post(
            self.base_url,
            self._payload_criacao(**kwargs),
            format='json',
        )

    def _oficializar(self, encontro):
        return self.client.post(
            f'{self.base_url}{encontro.pk}/oficializar/',
            {},
            format='json',
        )

    def test_criacao_transacional_produz_dominio_real_e_projecao(self):
        response = self._criar()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        encontro = Encontro.objects.get(pk=response.json()['encontro_id'])
        calendario = encontro.calendarios.get()
        self.assertEqual(encontro.status, Encontro.Status.EM_AGENDAMENTO)
        self.assertEqual(calendario.versao, 1)
        self.assertTrue(calendario.vigente)
        self.assertIsNone(calendario.oficializado_em)
        self.assertEqual(
            list(calendario.dias.values_list('data', flat=True)),
            [date(2034, 4, 3), date(2034, 4, 6)],
        )
        self.assertEqual(encontro.data_referencia, date(2034, 4, 3))
        self.assertEqual(encontro.data_exato, '2034-04-03, 2034-04-06')
        self.assertEqual(response.json()['confirmacao'], 'PROVISORIA')

        projection = self.client.get(
            '/api/calendario-institucional/',
            {'inicio': '2034-04-01', 'fim': '2034-04-30'},
        )
        self.assertEqual(projection.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [item['encontro_id'] for item in projection.json()['itens']],
            [encontro.pk],
        )
        log = LogSistema.objects.get(modulo='CalendarioInstitucional')
        self.assertEqual(log.acao, 'CREATE')
        self.assertIn(f'Encontro ID {encontro.pk}', log.descricao)
        self.assertNotIn(encontro.encontro, log.descricao)

    def test_diretoria_suporte_e_superuser_podem_criar(self):
        usuarios = (
            self.user,
            self._make_user('diretoria', SiaRole.DIRETORIA),
            self._make_user('superuser', superuser=True),
        )
        for indice, usuario in enumerate(usuarios):
            self.client.force_authenticate(usuario)
            with self.subTest(usuario=usuario.username):
                response = self._criar(
                    titulo=f'Encontro autorizado {indice}',
                    datas=[date(2034, 5, indice + 1)],
                )
                self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_demais_papeis_sao_somente_leitura_e_anonimo_recebe_401(self):
        read_only_roles = (
            SiaRole.FICHAS,
            SiaRole.MME,
            SiaRole.FORMACAO,
            SiaRole.SECRETARIA,
            SiaRole.ACAO_SOCIAL,
            SiaRole.LITURGIA,
            SiaRole.EVENTOS,
            SiaRole.COMUNICACAO,
        )
        for indice, role in enumerate(read_only_roles):
            user = self._make_user(f'read-only-{indice}', role)
            self.client.force_authenticate(user)
            with self.subTest(role=role.value):
                self.assertEqual(
                    self._criar(titulo=f'Negado {indice}').status_code,
                    status.HTTP_403_FORBIDDEN,
                )
                leitura = self.client.get(
                    '/api/calendario-institucional/',
                    {'inicio': '2034-01-01', 'fim': '2034-12-31'},
                )
                self.assertEqual(leitura.status_code, status.HTTP_200_OK)
                self.assertFalse(
                    leitura.json()['capabilities']['pode_gerir_calendario']
                )

        self.client.force_authenticate(user=None)
        self.assertEqual(
            self._criar(titulo='Anônimo').status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_falha_na_auditoria_reverte_criacao_integralmente(self):
        self.client.raise_request_exception = False
        with patch(
            'core.views.LogSistema.objects.create',
            side_effect=RuntimeError('falha de auditoria'),
        ):
            response = self._criar(titulo='Deve reverter')

        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertFalse(Encontro.objects.filter(encontro='Deve reverter').exists())
        self.assertEqual(CalendarioEncontro.objects.count(), 0)
        self.assertEqual(DiaEncontro.objects.count(), 0)

    def test_entrada_de_dias_invalida_retorna_400_sem_criacao_parcial(self):
        payload = self._payload_criacao(titulo='Inválido')
        payload['dias'][1]['data'] = payload['dias'][0]['data']

        response = self.client.post(self.base_url, payload, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Encontro.objects.filter(encontro='Inválido').exists())

    def test_dados_basicos_alteram_apenas_nome_e_local(self):
        encontro_id = self._criar().json()['encontro_id']
        response = self.client.patch(
            f'{self.base_url}{encontro_id}/dados-basicos/',
            {'encontro': 'Novo nome', 'local': 'Novo local'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        encontro = Encontro.objects.get(pk=encontro_id)
        self.assertEqual(encontro.encontro, 'Novo nome')
        self.assertEqual(encontro.local, 'Novo local')
        self.assertEqual(encontro.status, Encontro.Status.EM_AGENDAMENTO)
        self.assertEqual(encontro.calendarios.count(), 1)

    def test_planejamento_edita_in_place_e_permanece_provisorio(self):
        criado = self._criar()
        encontro = Encontro.objects.get(pk=criado.json()['encontro_id'])
        calendario_id = criado.json()['calendario_id']
        novos_dias = [
            {'ordem': 1, 'data': '2034-06-02'},
            {'ordem': 2, 'data': '2034-06-09'},
            {'ordem': 3, 'data': '2034-06-20'},
        ]

        response = self.client.patch(
            f'{self.base_url}{encontro.pk}/planejamento/',
            {'dias': novos_dias},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['calendario_id'], calendario_id)
        self.assertEqual(response.json()['calendario_versao'], 1)
        self.assertEqual(response.json()['confirmacao'], 'PROVISORIA')
        encontro.refresh_from_db()
        self.assertEqual(encontro.data_referencia, date(2034, 6, 2))
        self.assertEqual(
            list(encontro.calendarios.get().dias.values_list('data', flat=True)),
            [date(2034, 6, 2), date(2034, 6, 9), date(2034, 6, 20)],
        )

    def test_oficializacao_e_manual_e_transicao_invalida_retorna_400(self):
        encontro_id = self._criar().json()['encontro_id']
        encontro = Encontro.objects.get(pk=encontro_id)
        self.assertEqual(encontro.status, Encontro.Status.EM_AGENDAMENTO)

        response = self._oficializar(encontro)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], Encontro.Status.AGENDADO)
        self.assertEqual(response.json()['confirmacao'], 'OFICIAL')
        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.AGENDADO)
        self.assertIsNotNone(encontro.calendarios.get().oficializado_em)
        repetida = self._oficializar(encontro)
        self.assertEqual(repetida.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reprogramacao_preserva_historico_e_atualiza_projecao(self):
        encontro_id = self._criar().json()['encontro_id']
        encontro = Encontro.objects.get(pk=encontro_id)
        self._oficializar(encontro)
        antiga = encontro.calendarios.get()

        response = self.client.post(
            f'{self.base_url}{encontro.pk}/reprogramar/',
            {
                'dias': [
                    {'ordem': 1, 'data': '2034-07-15'},
                    {'ordem': 2, 'data': '2034-07-17'},
                ]
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['encontro_id'], encontro.pk)
        self.assertEqual(response.json()['calendario_versao'], 2)
        antiga.refresh_from_db()
        self.assertFalse(antiga.vigente)
        self.assertIsNotNone(antiga.substituido_em)
        self.assertEqual(encontro.calendarios.count(), 2)
        atual = encontro.calendarios.get(vigente=True)
        self.assertEqual(atual.versao, 2)
        self.assertIsNotNone(atual.oficializado_em)

        projection = self.client.get(
            '/api/calendario-institucional/',
            {'inicio': '2034-07-01', 'fim': '2034-07-31'},
        )
        self.assertEqual(
            projection.json()['itens'][0]['calendario_versao'],
            2,
        )

    def test_adiamento_e_novo_planejamento_preservam_historico(self):
        encontro_id = self._criar().json()['encontro_id']
        encontro = Encontro.objects.get(pk=encontro_id)
        self._oficializar(encontro)

        adiado = self.client.post(
            f'{self.base_url}{encontro.pk}/adiar/',
            {},
            format='json',
        )

        self.assertEqual(adiado.status_code, status.HTTP_200_OK)
        self.assertEqual(adiado.json()['status'], Encontro.Status.ADIADO)
        self.assertIsNone(adiado.json()['calendario_id'])
        self.assertEqual(encontro.calendarios.count(), 1)
        self.assertFalse(encontro.calendarios.get().vigente)

        novo = self.client.post(
            f'{self.base_url}{encontro.pk}/iniciar-planejamento/',
            {'dias': [{'ordem': 1, 'data': '2034-08-20'}]},
            format='json',
        )
        self.assertEqual(novo.status_code, status.HTTP_200_OK)
        self.assertEqual(novo.json()['status'], Encontro.Status.EM_AGENDAMENTO)
        self.assertEqual(novo.json()['calendario_versao'], 2)
        self.assertEqual(novo.json()['confirmacao'], 'PROVISORIA')
        self.assertEqual(encontro.calendarios.count(), 2)

    def test_cancelamento_preserva_encontro_agenda_e_projecao(self):
        encontro_id = self._criar(
            datas=[date(2034, 9, 10)],
        ).json()['encontro_id']
        encontro = Encontro.objects.get(pk=encontro_id)
        self._oficializar(encontro)
        calendario = encontro.calendarios.get()

        response = self.client.post(
            f'{self.base_url}{encontro.pk}/cancelar/',
            {},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], Encontro.Status.CANCELADO)
        self.assertTrue(Encontro.objects.filter(pk=encontro.pk).exists())
        self.assertTrue(CalendarioEncontro.objects.filter(pk=calendario.pk).exists())
        projection = self.client.get(
            '/api/calendario-institucional/',
            {'inicio': '2034-09-01', 'fim': '2034-09-30'},
        )
        self.assertEqual(
            projection.json()['itens'][0]['status'],
            Encontro.Status.CANCELADO,
        )

    def test_conflito_reutiliza_detector_e_nao_bloqueia_comando(self):
        existente, _ = criar_encontro_canonico(
            'Existente',
            [date(2034, 10, 10)],
        )

        response = self._criar(
            titulo='Conflitante',
            datas=[date(2034, 10, 10), date(2034, 10, 12)],
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        novo_id = response.json()['encontro_id']
        self.assertEqual(len(response.json()['avisos_conflito']), 1)
        aviso = response.json()['avisos_conflito'][0]
        self.assertEqual(aviso['data'], '2034-10-10')
        self.assertEqual(
            aviso['encontro_ids'],
            sorted((existente.pk, novo_id)),
        )
        self.assertTrue(Encontro.objects.filter(pk=novo_id).exists())

    def test_actions_rejeitam_campos_extras_e_metodos_nao_expostos(self):
        encontro_id = self._criar().json()['encontro_id']
        extra = self.client.post(
            f'{self.base_url}{encontro_id}/oficializar/',
            {'status': Encontro.Status.AGENDADO},
            format='json',
        )
        lista = self.client.get(self.base_url)
        delete = self.client.delete(f'{self.base_url}{encontro_id}/')

        self.assertEqual(extra.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(lista.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(delete.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_write_legado_permanece_compativel_sem_backfill_heuristico(self):
        fichas = self._make_user('fichas-legado', SiaRole.FICHAS)
        self.client.force_authenticate(fichas)
        response = self.client.post(
            '/api/encontros/',
            {
                'encontro': 'Contrato legado',
                'tipo': Encontro.Tipo.ESPPA,
                'data_referencia': '2034-11-01',
                'data_exato': '1, 7 e 8 de novembro de 2034',
                'local': 'Local legado',
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        encontro = Encontro.objects.get(pk=response.json()['id'])
        self.assertFalse(encontro.calendarios.exists())


@skipUnless(
    connection.vendor == 'postgresql',
    'Concorrência temporal exige PostgreSQL real.',
)
class CalendarioInstitucionalConcurrencyTests(TransactionTestCase):
    def _run_parallel(self, *callbacks):
        barrier = Barrier(len(callbacks))

        def runner(callback):
            close_old_connections()
            barrier.wait()
            try:
                callback()
                return 'ok'
            except DjangoValidationError:
                return 'domain_error'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(callbacks)) as executor:
            return list(executor.map(runner, callbacks))

    def _novo_planejamento(self):
        return command_services.criar_encontro(
            titulo='Concorrência',
            tipo=Encontro.Tipo.ESCALADA,
            local='Local',
            dias=[{'ordem': 1, 'data': date(2035, 1, 10)}],
        )

    def test_oficializacao_concorrente_tem_um_unico_sucesso(self):
        encontro = self._novo_planejamento()

        resultados = self._run_parallel(
            *(
                lambda: command_services.oficializar_agenda(
                    Encontro.objects.get(pk=encontro.pk)
                )
                for _ in range(2)
            )
        )

        self.assertCountEqual(resultados, ['ok', 'domain_error'])
        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.AGENDADO)
        self.assertEqual(encontro.calendarios.filter(vigente=True).count(), 1)

    def test_edicoes_concorrentes_nao_misturam_dias(self):
        encontro = self._novo_planejamento()
        opcoes = (
            [
                {'ordem': 1, 'data': date(2035, 2, 1)},
                {'ordem': 2, 'data': date(2035, 2, 2)},
            ],
            [
                {'ordem': 1, 'data': date(2035, 3, 1)},
                {'ordem': 2, 'data': date(2035, 3, 3)},
            ],
        )

        resultados = self._run_parallel(
            *(
                lambda dias=dias: command_services.editar_planejamento(
                    Encontro.objects.get(pk=encontro.pk),
                    dias=dias,
                )
                for dias in opcoes
            )
        )

        self.assertEqual(resultados, ['ok', 'ok'])
        finais = set(
            encontro.calendarios.get(vigente=True).dias.values_list(
                'data',
                flat=True,
            )
        )
        self.assertIn(finais, [{item['data'] for item in dias} for dias in opcoes])

    def test_reprogramacoes_concorrentes_preservam_todas_as_versoes(self):
        encontro = self._novo_planejamento()
        command_services.oficializar_agenda(encontro)
        opcoes = (
            [{'ordem': 1, 'data': date(2035, 4, 1)}],
            [{'ordem': 1, 'data': date(2035, 5, 1)}],
        )

        resultados = self._run_parallel(
            *(
                lambda dias=dias: command_services.reprogramar_agenda(
                    Encontro.objects.get(pk=encontro.pk),
                    dias=dias,
                )
                for dias in opcoes
            )
        )

        self.assertEqual(resultados, ['ok', 'ok'])
        self.assertEqual(encontro.calendarios.count(), 3)
        self.assertEqual(encontro.calendarios.filter(vigente=True).count(), 1)
        self.assertEqual(
            list(encontro.calendarios.order_by('versao').values_list('versao', flat=True)),
            [1, 2, 3],
        )

    def test_edicao_concorrente_com_oficializacao_preserva_invariantes(self):
        encontro = self._novo_planejamento()
        novos_dias = [{'ordem': 1, 'data': date(2035, 6, 1)}]

        resultados = self._run_parallel(
            lambda: command_services.editar_planejamento(
                Encontro.objects.get(pk=encontro.pk),
                dias=novos_dias,
            ),
            lambda: command_services.oficializar_agenda(
                Encontro.objects.get(pk=encontro.pk)
            ),
        )

        self.assertIn(resultados, (['ok', 'ok'], ['domain_error', 'ok']))
        encontro.refresh_from_db()
        calendario = encontro.calendarios.get(vigente=True)
        self.assertEqual(encontro.status, Encontro.Status.AGENDADO)
        self.assertIsNotNone(calendario.oficializado_em)
        self.assertEqual(calendario.dias.count(), 1)

    def test_edicao_concorrente_com_cancelamento_nao_corrompe_agenda(self):
        encontro = self._novo_planejamento()
        novos_dias = [{'ordem': 1, 'data': date(2035, 7, 1)}]

        resultados = self._run_parallel(
            lambda: command_services.editar_planejamento(
                Encontro.objects.get(pk=encontro.pk),
                dias=novos_dias,
            ),
            lambda: command_services.cancelar_encontro(
                Encontro.objects.get(pk=encontro.pk)
            ),
        )

        self.assertIn(resultados, (['ok', 'ok'], ['domain_error', 'ok']))
        encontro.refresh_from_db()
        self.assertEqual(encontro.status, Encontro.Status.CANCELADO)
        self.assertEqual(encontro.calendarios.filter(vigente=True).count(), 1)
        self.assertEqual(encontro.calendarios.get(vigente=True).dias.count(), 1)
