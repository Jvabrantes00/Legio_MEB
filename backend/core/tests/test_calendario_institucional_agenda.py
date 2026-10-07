from concurrent.futures import ThreadPoolExecutor
from datetime import date, time
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection
from django.db.migrations.executor import MigrationExecutor
from django.db.models.deletion import ProtectedError
from django.test import TestCase, TransactionTestCase
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    AvaliacaoEncontro,
    DiaEncontro,
    Encontro,
    Frequencia,
    ParticipacaoEncontro,
    ReuniaoPreparatoriaEncontro,
    TrabalhoEncontro,
)
from core.roles import SiaRole
from core.services import comandos_calendario as command_services
from core.services.avaliacoes_encontro import (
    criar_avaliacao_encontro,
    editar_avaliacao_encontro,
    remover_avaliacao_encontro,
)
from core.services.calendario_institucional import (
    TIPO_AVALIACAO,
    TIPO_DIA_ENCONTRO,
    TIPO_REUNIAO_PREPARATORIA,
    consultar_agenda_encontro,
    consultar_calendario_institucional,
)
from core.services.reunioes_preparatorias import criar_reuniao_preparatoria
from core.tests.test_calendario_institucional import criar_encontro_canonico


class AgendaEncontroServiceTests(TestCase):
    def setUp(self):
        self.encontro, self.calendario = criar_encontro_canonico(
            'Escalada 2036',
            [date(2036, 3, 21), date(2036, 3, 25)],
        )

    def test_rotulo_e_opcional_editavel_e_nao_altera_identidade(self):
        primeiro = self.calendario.dias.order_by('ordem').first()
        segundo = self.calendario.dias.order_by('ordem').last()
        self.assertEqual(primeiro.rotulo, '')

        primeiro_id = primeiro.pk
        primeiro.rotulo = 'Pré-Escalada'
        primeiro.save(update_fields=['rotulo'])
        primeiro.refresh_from_db()

        self.assertEqual(primeiro.pk, primeiro_id)
        self.assertEqual(primeiro.rotulo, 'Pré-Escalada')
        self.assertEqual(segundo.rotulo, '')

    def test_agenda_agrega_fontes_canonicas_com_ordem_e_visibilidade(self):
        dia = self.calendario.dias.order_by('ordem').first()
        dia.rotulo = 'Pré-Escalada'
        dia.save(update_fields=['rotulo'])
        reuniao = criar_reuniao_preparatoria(
            encontro=self.encontro,
            ordem=1,
            data=dia.data,
            horario=time(19, 30),
            local='Sede',
            complemento='Missa de Entrega',
            observacoes='Nota operacional que não deve vazar',
        )
        avaliacao = criar_avaliacao_encontro(
            encontro=self.encontro,
            data=date(2036, 3, 30),
        )

        resultado = consultar_agenda_encontro(self.encontro)

        self.assertEqual(
            [item.origem for item in resultado.itens],
            [
                TIPO_DIA_ENCONTRO,
                TIPO_REUNIAO_PREPARATORIA,
                TIPO_DIA_ENCONTRO,
                TIPO_AVALIACAO,
            ],
        )
        primeiro, item_reuniao, _, item_avaliacao = resultado.itens
        self.assertEqual(primeiro.titulo, 'Pré-Escalada')
        self.assertEqual(primeiro.subtitulo, self.encontro.encontro)
        self.assertTrue(primeiro.publicavel_externamente)
        self.assertEqual(item_reuniao.id, f'REUNIAO_PREPARATORIA:{reuniao.pk}')
        self.assertEqual(item_reuniao.subtitulo, 'Missa de Entrega')
        self.assertFalse(item_reuniao.publicavel_externamente)
        self.assertNotIn('Nota operacional', repr(item_reuniao))
        self.assertEqual(item_avaliacao.id, f'AVALIACAO:{avaliacao.pk}')
        self.assertFalse(item_avaliacao.publicavel_externamente)
        self.assertTrue(all(
            item.encontro_id == self.encontro.pk
            for item in resultado.itens
        ))

    def test_reuniao_e_avaliacao_entram_no_calendario_e_nos_conflitos(self):
        outro, _ = criar_encontro_canonico(
            'ESPPA 2036',
            [date(2036, 5, 20)],
        )
        criar_reuniao_preparatoria(
            encontro=self.encontro,
            ordem=1,
            data=date(2036, 4, 10),
            horario=time(19),
            local='Sede',
        )
        criar_avaliacao_encontro(
            encontro=outro,
            data=date(2036, 4, 10),
        )

        with self.assertNumQueries(5):
            resultado = consultar_calendario_institucional(
                date(2036, 4, 1),
                date(2036, 4, 30),
            )

        self.assertEqual(
            {item.encontro_id for item in resultado.itens},
            {self.encontro.pk, outro.pk},
        )
        self.assertEqual(len(resultado.conflitos), 1)
        self.assertEqual(
            set(resultado.conflitos[0].encontro_ids),
            {self.encontro.pk, outro.pk},
        )
        origens = {
            item.agenda[0].origem
            for item in resultado.itens
        }
        self.assertEqual(
            origens,
            {TIPO_REUNIAO_PREPARATORIA, TIPO_AVALIACAO},
        )

    def test_avaliacao_e_unica_editavel_removivel_e_protege_encontro(self):
        avaliacao = criar_avaliacao_encontro(
            encontro=self.encontro,
            data=date(2036, 3, 30),
        )
        with self.assertRaisesMessage(ValidationError, 'já possui'):
            criar_avaliacao_encontro(
                encontro=self.encontro,
                data=date(2036, 3, 31),
            )
        with self.assertRaises(ProtectedError):
            self.encontro.delete()

        editada = editar_avaliacao_encontro(
            avaliacao,
            data=date(2036, 4, 1),
        )
        self.assertEqual(editada.data, date(2036, 4, 1))
        remover_avaliacao_encontro(editada)
        self.assertFalse(AvaliacaoEncontro.objects.exists())

    def test_criacao_completa_e_atomica_sem_efeitos_em_outros_dominios(self):
        encontro = command_services.criar_encontro(
            titulo='Agenda completa',
            tipo=Encontro.Tipo.ESCALADA,
            local='Nova Betânia',
            dias=[
                {
                    'ordem': 1,
                    'data': date(2037, 3, 21),
                    'rotulo': 'Pré-Escalada',
                },
                {
                    'ordem': 2,
                    'data': date(2037, 3, 25),
                    'rotulo': 'Sexta-feira',
                },
            ],
            reunioes=[{
                'ordem': 1,
                'data': date(2037, 3, 3),
                'horario': time(19, 30),
                'local': 'Sede',
                'complemento': 'Missa de Entrega',
            }],
            avaliacao={'data': date(2037, 3, 30)},
        )

        self.assertEqual(encontro.calendarios.get().dias.count(), 2)
        self.assertEqual(encontro.reunioes_preparatorias.count(), 1)
        self.assertEqual(encontro.avaliacao_agenda.data, date(2037, 3, 30))
        self.assertEqual(ParticipacaoEncontro.objects.count(), 0)
        self.assertEqual(TrabalhoEncontro.objects.count(), 0)
        self.assertEqual(Frequencia.objects.count(), 0)

    def test_falha_em_reuniao_ou_avaliacao_reverte_criacao_completa(self):
        argumentos = {
            'titulo': 'Deve reverter',
            'tipo': Encontro.Tipo.ESCALADA,
            'local': 'Local',
            'dias': [{'ordem': 1, 'data': date(2037, 5, 1)}],
            'reunioes': [{
                'ordem': 1,
                'data': date(2037, 4, 1),
                'horario': time(19),
                'local': 'Sede',
            }],
            'avaliacao': {'data': date(2037, 5, 2)},
        }
        with patch(
            'core.services.comandos_calendario.reuniao_services.'
            'criar_reuniao_preparatoria',
            side_effect=ValidationError('falha reunião'),
        ):
            with self.assertRaisesMessage(ValidationError, 'falha reunião'):
                command_services.criar_encontro(**argumentos)
        self.assertFalse(Encontro.objects.filter(encontro='Deve reverter').exists())

        with patch(
            'core.services.comandos_calendario.avaliacao_services.'
            'criar_avaliacao_encontro',
            side_effect=ValidationError('falha avaliação'),
        ):
            with self.assertRaisesMessage(ValidationError, 'falha avaliação'):
                command_services.criar_encontro(**argumentos)
        self.assertFalse(Encontro.objects.filter(encontro='Deve reverter').exists())
        self.assertEqual(ReuniaoPreparatoriaEncontro.objects.count(), 0)


class AgendaEncontroApiTests(APITestCase):
    base_url = '/api/calendario-institucional/encontros/'

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='diretoria-agenda',
            password='senha-de-teste',
        )
        group, _ = Group.objects.get_or_create(name=SiaRole.DIRETORIA.value)
        self.user.groups.add(group)
        self.client.force_authenticate(self.user)

    def _payload(self):
        return {
            'encontro': 'Escalada API Agenda',
            'tipo': Encontro.Tipo.ESCALADA,
            'local': 'Nova Betânia',
            'dias': [
                {
                    'ordem': 1,
                    'data': '2038-03-21',
                    'rotulo': 'Pré-Escalada',
                },
                {
                    'ordem': 2,
                    'data': '2038-03-25',
                    'rotulo': 'Sexta-feira',
                },
            ],
            'reunioes': [{
                'ordem': 1,
                'data': '2038-03-03',
                'horario': '19:30:00',
                'local': 'Sede',
                'complemento': 'Missa de Entrega',
            }],
            'avaliacao': {'data': '2038-03-30'},
        }

    def test_cria_agenda_completa_e_consulta_allowlist(self):
        response = self.client.post(self.base_url, self._payload(), format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        encontro_id = response.json()['encontro_id']
        self.assertEqual(len(response.json()['agenda']), 4)

        agenda = self.client.get(f'{self.base_url}{encontro_id}/agenda/')
        self.assertEqual(agenda.status_code, status.HTTP_200_OK)
        self.assertEqual(set(agenda.json()), {'encontro_id', 'itens'})
        self.assertEqual(
            [item['origem'] for item in agenda.json()['itens']],
            [
                TIPO_REUNIAO_PREPARATORIA,
                TIPO_DIA_ENCONTRO,
                TIPO_DIA_ENCONTRO,
                TIPO_AVALIACAO,
            ],
        )
        self.assertEqual(
            set(agenda.json()['itens'][0]),
            {
                'id', 'origem_id', 'origem', 'data', 'titulo', 'subtitulo',
                'confirmacao', 'publicavel_externamente', 'encontro_id',
                'conflito',
            },
        )
        payload_texto = repr(agenda.json())
        for campo in ('presencas', 'participantes', 'trabalhos', 'observacoes'):
            self.assertNotIn(campo, payload_texto)

    def test_cria_edita_reuniao_e_avaliacao_pelos_comandos(self):
        payload = self._payload()
        payload.pop('reunioes')
        payload.pop('avaliacao')
        criado = self.client.post(self.base_url, payload, format='json')
        encontro_id = criado.json()['encontro_id']

        reuniao_response = self.client.post(
            f'{self.base_url}{encontro_id}/reunioes/',
            {
                'ordem': 1,
                'data': '2038-03-01',
                'horario': '19:00',
                'local': 'Sede',
            },
            format='json',
        )
        self.assertEqual(reuniao_response.status_code, status.HTTP_201_CREATED)
        reuniao = ReuniaoPreparatoriaEncontro.objects.get(encontro_id=encontro_id)
        editada = self.client.patch(
            f'{self.base_url}{encontro_id}/reunioes/{reuniao.pk}/',
            {'complemento': 'Missa de Entrega'},
            format='json',
        )
        self.assertEqual(editada.status_code, status.HTTP_200_OK)
        reuniao.refresh_from_db()
        self.assertEqual(reuniao.complemento, 'Missa de Entrega')

        criada = self.client.post(
            f'{self.base_url}{encontro_id}/avaliacao/',
            {'data': '2038-03-30'},
            format='json',
        )
        self.assertEqual(criada.status_code, status.HTTP_201_CREATED)
        alterada = self.client.patch(
            f'{self.base_url}{encontro_id}/avaliacao/',
            {'data': '2038-03-31'},
            format='json',
        )
        self.assertEqual(alterada.status_code, status.HTTP_200_OK)
        self.assertEqual(
            AvaliacaoEncontro.objects.get(encontro_id=encontro_id).data,
            date(2038, 3, 31),
        )
        removida = self.client.delete(
            f'{self.base_url}{encontro_id}/avaliacao/',
        )
        self.assertEqual(removida.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(AvaliacaoEncontro.objects.exists())

    def test_agenda_usa_leitura_ampla_sem_ampliar_gestao(self):
        encontro_id = self.client.post(
            self.base_url,
            self._payload(),
            format='json',
        ).json()['encontro_id']
        comunicacao = get_user_model().objects.create_user(
            username='comunicacao-agenda',
            password='senha-de-teste',
        )
        group, _ = Group.objects.get_or_create(name=SiaRole.COMUNICACAO.value)
        comunicacao.groups.add(group)
        self.client.force_authenticate(comunicacao)

        self.assertEqual(
            self.client.get(f'{self.base_url}{encontro_id}/agenda/').status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            self.client.post(
                f'{self.base_url}{encontro_id}/avaliacao/',
                {'data': '2038-04-01'},
                format='json',
            ).status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_edicao_de_rotulo_preserva_identidade_do_dia(self):
        payload = self._payload()
        payload.pop('reunioes')
        payload.pop('avaliacao')
        encontro_id = self.client.post(
            self.base_url,
            payload,
            format='json',
        ).json()['encontro_id']
        dia_id = DiaEncontro.objects.get(
            calendario__encontro_id=encontro_id,
            ordem=1,
        ).pk

        response = self.client.patch(
            f'{self.base_url}{encontro_id}/dias/{dia_id}/rotulo/',
            {'rotulo': 'Pré-Escalada editada'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        novo_dia = DiaEncontro.objects.get(
            calendario__encontro_id=encontro_id,
            ordem=1,
        )
        self.assertEqual(novo_dia.pk, dia_id)
        self.assertEqual(novo_dia.rotulo, 'Pré-Escalada editada')
        self.assertEqual(
            response.json()['agenda'][0]['titulo'],
            'Pré-Escalada editada',
        )

        oficializada = self.client.post(
            f'{self.base_url}{encontro_id}/oficializar/',
            {},
            format='json',
        )
        self.assertEqual(oficializada.status_code, status.HTTP_200_OK)
        rejeitada = self.client.patch(
            f'{self.base_url}{encontro_id}/dias/{dia_id}/rotulo/',
            {'rotulo': 'Não sobrescrever oficial'},
            format='json',
        )
        self.assertEqual(rejeitada.status_code, status.HTTP_400_BAD_REQUEST)
        novo_dia.refresh_from_db()
        self.assertEqual(novo_dia.rotulo, 'Pré-Escalada editada')

    def test_edicao_de_reuniao_rejeita_nested_mismatch(self):
        primeiro = self.client.post(
            self.base_url,
            self._payload(),
            format='json',
        ).json()['encontro_id']
        payload_outro = self._payload()
        payload_outro['encontro'] = 'Outro Encontro'
        payload_outro['dias'][0]['data'] = '2038-04-21'
        payload_outro['dias'][1]['data'] = '2038-04-25'
        payload_outro['reunioes'] = []
        payload_outro['avaliacao'] = None
        segundo = self.client.post(
            self.base_url,
            payload_outro,
            format='json',
        ).json()['encontro_id']
        reuniao = ReuniaoPreparatoriaEncontro.objects.get(encontro_id=primeiro)

        response = self.client.patch(
            f'{self.base_url}{segundo}/reunioes/{reuniao.pk}/',
            {'complemento': 'Não permitido'},
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        reuniao.refresh_from_db()
        self.assertEqual(reuniao.complemento, 'Missa de Entrega')


class AgendaEncontroMigrationTests(TransactionTestCase):
    migrate_from = ('core', '0035_diaencontro_data_index')
    migrate_to = ('core', '0036_expand_agenda_encontro')

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_from])
        old_apps = executor.loader.project_state([self.migrate_from]).apps
        EncontroAntigo = old_apps.get_model('core', 'Encontro')
        CalendarioAntigo = old_apps.get_model('core', 'CalendarioEncontro')
        DiaAntigo = old_apps.get_model('core', 'DiaEncontro')
        ReuniaoAntiga = old_apps.get_model(
            'core',
            'ReuniaoPreparatoriaEncontro',
        )
        encontro = EncontroAntigo.objects.create(
            encontro='Preservado D.6E',
            tipo='Escalada',
            data_referencia=date(2039, 1, 10),
            data_exato='10 de janeiro de 2039',
        )
        calendario = CalendarioAntigo.objects.create(
            encontro=encontro,
            versao=1,
            vigente=True,
        )
        self.dia_id = DiaAntigo.objects.create(
            calendario=calendario,
            ordem=1,
            data=date(2039, 1, 10),
            descricao='Descrição preservada',
        ).pk
        self.reuniao_id = ReuniaoAntiga.objects.create(
            encontro=encontro,
            ordem=1,
            data=date(2039, 1, 5),
            horario=time(19),
            local='Sede',
            observacoes='Observação preservada',
        ).pk

        executor = MigrationExecutor(connection)
        executor.migrate([self.migrate_to])
        self.apps = executor.loader.project_state([self.migrate_to]).apps

    def test_forward_preserva_legado_e_cria_campos_e_tabela_vazios(self):
        Dia = self.apps.get_model('core', 'DiaEncontro')
        Reuniao = self.apps.get_model('core', 'ReuniaoPreparatoriaEncontro')
        Avaliacao = self.apps.get_model('core', 'AvaliacaoEncontro')

        dia = Dia.objects.get(pk=self.dia_id)
        reuniao = Reuniao.objects.get(pk=self.reuniao_id)
        self.assertEqual(dia.descricao, 'Descrição preservada')
        self.assertEqual(dia.rotulo, '')
        self.assertEqual(reuniao.observacoes, 'Observação preservada')
        self.assertEqual(reuniao.complemento, '')
        self.assertEqual(Avaliacao.objects.count(), 0)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()


@skipUnless(
    connection.vendor == 'postgresql',
    'Concorrência da avaliação exige PostgreSQL real.',
)
class AgendaEncontroConcurrencyTests(TransactionTestCase):
    def test_criacao_concorrente_mantem_uma_avaliacao(self):
        encontro, _ = criar_encontro_canonico(
            'Avaliação concorrente',
            [date(2040, 1, 10)],
        )
        barrier = Barrier(2)

        def criar():
            close_old_connections()
            barrier.wait()
            try:
                criar_avaliacao_encontro(
                    encontro=Encontro.objects.get(pk=encontro.pk),
                    data=date(2040, 1, 12),
                )
                return 'ok'
            except ValidationError:
                return 'domain_error'
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as executor:
            resultados = list(executor.map(lambda _: criar(), range(2)))

        self.assertCountEqual(resultados, ['ok', 'domain_error'])
        self.assertEqual(AvaliacaoEncontro.objects.count(), 1)
