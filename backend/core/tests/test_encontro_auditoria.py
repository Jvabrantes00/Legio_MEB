from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from core.models import Encontro, EventoAuditoriaEncontro, LogSistema
from core.roles import SiaRole
from core.services.auditoria_encontros import (
    consultar_eventos_auditoria_encontro,
    registrar_evento_auditoria_encontro,
)
from core.tests.factories import make_encontro


class EventoAuditoriaEncontroTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro()
        self.ator = get_user_model().objects.create_user(
            username='auditor_teste',
            password='senha-exclusiva-de-teste',
        )

    def registrar(self, **overrides):
        valores = {
            'encontro': self.encontro,
            'ator': self.ator,
            'fato': 'capacidade.alterada',
            'entidade': 'configuracao_encontristas',
            'objeto_id': 'config:10',
            'valor_anterior': {'capacidade': 80},
            'valor_novo': {'capacidade': 90},
            'campos_permitidos': {'capacidade'},
            'justificativa': 'Ajuste operacional aprovado.',
        }
        valores.update(overrides)
        return registrar_evento_auditoria_encontro(**valores)

    def test_service_cria_evento_estruturado_sem_log_legado(self):
        evento = self.registrar()

        self.assertEqual(evento.encontro, self.encontro)
        self.assertEqual(evento.ator, self.ator)
        self.assertEqual(evento.valor_anterior, {'capacidade': 80})
        self.assertEqual(evento.valor_novo, {'capacidade': 90})
        self.assertEqual(evento.justificativa, 'Ajuste operacional aprovado.')
        self.assertEqual(LogSistema.objects.count(), 0)

    def test_constraints_rejeitam_identificadores_vazios(self):
        campos = ('fato', 'entidade', 'objeto_id')
        for campo in campos:
            with self.subTest(campo=campo):
                valores = {
                    'encontro': self.encontro,
                    'ator': self.ator,
                    'fato': 'capacidade.alterada',
                    'entidade': 'configuracao_encontristas',
                    'objeto_id': '1',
                }
                valores[campo] = ''
                with self.assertRaises(IntegrityError), transaction.atomic():
                    EventoAuditoriaEncontro.objects.create(**valores)

    def test_evento_e_imutavel_por_instancia_e_queryset(self):
        evento = self.registrar()
        evento.justificativa = 'Tentativa de alteração.'

        with self.assertRaises(ValidationError):
            evento.save()
        with self.assertRaises(ValidationError):
            evento.delete()
        with self.assertRaises(ValidationError):
            EventoAuditoriaEncontro.objects.filter(pk=evento.pk).update(
                justificativa='Tentativa em lote.'
            )
        with self.assertRaises(ValidationError):
            EventoAuditoriaEncontro.objects.filter(pk=evento.pk).delete()
        with self.assertRaises(ValidationError):
            EventoAuditoriaEncontro.objects.bulk_update(
                [evento],
                ['justificativa'],
            )

    def test_relacoes_protegidas_preservam_auditoria(self):
        self.registrar()

        with self.assertRaises(ProtectedError):
            self.encontro.delete()
        with self.assertRaises(ProtectedError):
            self.ator.delete()

    def test_service_exige_allowlist_e_rejeita_campo_sensivel(self):
        cpf = '12345678901'

        with self.assertRaises(ValidationError) as contexto:
            self.registrar(
                valor_anterior={'cpf': cpf},
                valor_novo={'cpf': cpf},
                campos_permitidos={'cpf'},
            )

        self.assertNotIn(cpf, str(contexto.exception))
        self.assertEqual(EventoAuditoriaEncontro.objects.count(), 0)

        with self.assertRaises(ValidationError):
            self.registrar(
                valor_novo={'status': 'confirmado'},
                campos_permitidos={'capacidade'},
            )

    def test_falha_da_transacao_reverte_evento(self):
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                self.registrar()
                raise RuntimeError('Falha intermediária controlada.')

        self.assertEqual(EventoAuditoriaEncontro.objects.count(), 0)


class ConsultaAuditoriaEncontroTests(TestCase):
    def setUp(self):
        self.encontro = make_encontro()
        self.outro_encontro = make_encontro()
        self.user_model = get_user_model()
        self.ator = self.user_model.objects.create_user(
            username='ator_auditoria',
        )
        self.evento = registrar_evento_auditoria_encontro(
            encontro=self.encontro,
            ator=self.ator,
            fato='capacidade.alterada',
            entidade='configuracao_encontristas',
            objeto_id='1',
            valor_anterior={'capacidade': 80},
            valor_novo={'capacidade': 90},
            campos_permitidos={'capacidade'},
        )

    def usuario_com_papel(self, nome, papel):
        usuario = self.user_model.objects.create_user(username=nome)
        grupo, _ = Group.objects.get_or_create(name=papel.value)
        usuario.groups.add(grupo)
        return usuario

    def test_suporte_diretoria_e_superuser_podem_consultar(self):
        usuarios = (
            self.usuario_com_papel('suporte', SiaRole.SUPORTE),
            self.usuario_com_papel('diretoria', SiaRole.DIRETORIA),
            self.user_model.objects.create_superuser(
                username='superuser',
                password='senha-exclusiva-de-teste',
                email='superuser@example.test',
            ),
        )

        for usuario in usuarios:
            with self.subTest(usuario=usuario.username):
                eventos = consultar_eventos_auditoria_encontro(
                    usuario=usuario,
                    encontro=self.encontro,
                )
                self.assertEqual(list(eventos), [self.evento])

    def test_consulta_restringe_encontro_e_nega_demais_usuarios(self):
        suporte = self.usuario_com_papel('suporte_escopo', SiaRole.SUPORTE)
        fichas = self.usuario_com_papel('fichas', SiaRole.FICHAS)
        sem_papel = self.user_model.objects.create_user(username='sem_papel')

        self.assertEqual(
            list(consultar_eventos_auditoria_encontro(
                usuario=suporte,
                encontro=self.outro_encontro,
            )),
            [],
        )
        for usuario in (fichas, sem_papel):
            with self.subTest(usuario=usuario.username):
                with self.assertRaises(PermissionDenied):
                    consultar_eventos_auditoria_encontro(
                        usuario=usuario,
                        encontro=self.encontro,
                    )
