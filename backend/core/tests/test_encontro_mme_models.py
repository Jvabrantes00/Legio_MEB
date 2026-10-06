from datetime import date

from django.db import IntegrityError, models, transaction
from django.test import TestCase
from django.utils import timezone

from core.models import (
    ConviteEncontro,
    Encontro,
    Frequencia,
    ItemPropostaVioleiros,
    PerfilAlpinista,
    Pessoa,
    PropostaVioleiros,
    TrabalhoEncontro,
    VinculoEncontroLegado,
)


class PropostaVioleirosModelTests(TestCase):
    def setUp(self):
        self.encontro = Encontro.objects.create(
            encontro='Escalada MME',
            tipo=Encontro.Tipo.ESCALADA,
            data_referencia=date(2027, 1, 10),
            data_exato='10 de janeiro de 2027',
        )

    def criar_perfil(self, indice):
        pessoa = Pessoa.objects.create(nome=f'Pessoa {indice}')
        return PerfilAlpinista.objects.create(
            pessoa=pessoa,
            violeiro=True,
            canta=indice % 2 == 0,
            disponivel_mme=True,
        )

    def criar_item(
        self,
        proposta,
        perfil,
        papel,
        posicao,
        *,
        vigente=True,
    ):
        return ItemPropostaVioleiros.objects.create(
            proposta=proposta,
            perfil_alpinista=perfil,
            papel_sugerido=papel,
            posicao=posicao,
            vigente=vigente,
            retirado_em=None if vigente else timezone.now(),
        )

    def preencher_cinco_slots(self, proposta, inicio=1):
        itens = [
            self.criar_item(
                proposta,
                self.criar_perfil(inicio),
                ItemPropostaVioleiros.PapelSugerido.COORDENADOR,
                1,
            )
        ]
        for posicao in range(1, 5):
            itens.append(self.criar_item(
                proposta,
                self.criar_perfil(inicio + posicao),
                ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
                posicao,
            ))
        return itens

    def test_multiplas_propostas_e_nome_opcional(self):
        sem_nome = PropostaVioleiros.objects.create(encontro=self.encontro)
        nomeada = PropostaVioleiros.objects.create(
            encontro=self.encontro,
            nome='Alternativa B',
        )

        self.assertEqual(sem_nome.nome, '')
        self.assertEqual(nomeada.nome, 'Alternativa B')
        self.assertEqual(
            PropostaVioleiros.objects.filter(encontro=self.encontro).count(),
            2,
        )

    def test_estados_aberta_e_encerrada_sao_estruturalmente_validos(self):
        aberta = PropostaVioleiros.objects.create(encontro=self.encontro)
        encerrada = PropostaVioleiros.objects.create(
            encontro=self.encontro,
            status=PropostaVioleiros.Status.ENCERRADA,
            encerrada_em=timezone.now(),
        )

        self.assertEqual(aberta.status, PropostaVioleiros.Status.ABERTA)
        self.assertIsNone(aberta.encerrada_em)
        self.assertEqual(encerrada.status, PropostaVioleiros.Status.ENCERRADA)
        self.assertIsNotNone(encerrada.encerrada_em)

    def test_estado_e_timestamp_de_encerramento_devem_ser_coerentes(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PropostaVioleiros.objects.create(
                encontro=self.encontro,
                status=PropostaVioleiros.Status.ENCERRADA,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            PropostaVioleiros.objects.create(
                encontro=self.encontro,
                status=PropostaVioleiros.Status.ABERTA,
                encerrada_em=timezone.now(),
            )

    def test_cria_um_coordenador_e_quatro_integrantes_vigentes(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)

        itens = self.preencher_cinco_slots(proposta)

        self.assertEqual(len(itens), 5)
        self.assertEqual(proposta.itens.filter(vigente=True).count(), 5)
        self.assertEqual(
            proposta.itens.filter(
                vigente=True,
                papel_sugerido=(
                    ItemPropostaVioleiros.PapelSugerido.COORDENADOR
                ),
            ).count(),
            1,
        )

    def test_rejeita_segundo_coordenador_vigente(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)
        self.criar_item(
            proposta,
            self.criar_perfil(1),
            ItemPropostaVioleiros.PapelSugerido.COORDENADOR,
            1,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_item(
                proposta,
                self.criar_perfil(2),
                ItemPropostaVioleiros.PapelSugerido.COORDENADOR,
                1,
            )

    def test_rejeita_quinto_integrante_vigente(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)
        for posicao in range(1, 5):
            self.criar_item(
                proposta,
                self.criar_perfil(posicao),
                ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
                posicao,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_item(
                proposta,
                self.criar_perfil(5),
                ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
                5,
            )

    def test_role_e_posicao_devem_formar_slot_valido(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_item(
                proposta,
                self.criar_perfil(1),
                ItemPropostaVioleiros.PapelSugerido.COORDENADOR,
                2,
            )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_item(
                proposta,
                self.criar_perfil(2),
                'outra_role',
                1,
            )

    def test_preserva_historico_acima_de_cinco_registros(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)
        itens = self.preencher_cinco_slots(proposta)
        primeiro = itens[1]
        primeiro.vigente = False
        primeiro.retirado_em = timezone.now()
        primeiro.save(update_fields=['vigente', 'retirado_em', 'atualizado_em'])

        substituto = self.criar_item(
            proposta,
            self.criar_perfil(6),
            ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
            1,
        )

        self.assertEqual(proposta.itens.count(), 6)
        self.assertEqual(proposta.itens.filter(vigente=True).count(), 5)
        self.assertTrue(proposta.itens.filter(pk=primeiro.pk).exists())
        self.assertTrue(substituto.vigente)

    def test_vigencia_e_retirada_devem_ser_coerentes(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)

        with self.assertRaises(IntegrityError), transaction.atomic():
            ItemPropostaVioleiros.objects.create(
                proposta=proposta,
                perfil_alpinista=self.criar_perfil(1),
                papel_sugerido=(
                    ItemPropostaVioleiros.PapelSugerido.INTEGRANTE
                ),
                posicao=1,
                vigente=False,
                retirado_em=None,
            )

    def test_mesmo_perfil_nao_pode_ocupar_dois_slots_vigentes(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)
        perfil = self.criar_perfil(1)
        self.criar_item(
            proposta,
            perfil,
            ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
            1,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.criar_item(
                proposta,
                perfil,
                ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
                2,
            )

    def test_mesmo_perfil_pode_aparecer_em_propostas_diferentes(self):
        perfil = self.criar_perfil(1)
        proposta_a = PropostaVioleiros.objects.create(encontro=self.encontro)
        proposta_b = PropostaVioleiros.objects.create(encontro=self.encontro)

        self.criar_item(
            proposta_a,
            perfil,
            ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
            1,
        )
        self.criar_item(
            proposta_b,
            perfil,
            ItemPropostaVioleiros.PapelSugerido.COORDENADOR,
            1,
        )

        self.assertEqual(
            ItemPropostaVioleiros.objects.filter(
                perfil_alpinista=perfil,
                vigente=True,
            ).count(),
            2,
        )

    def test_perfil_historico_pode_voltar_sem_duplicidade_simultanea(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)
        perfil = self.criar_perfil(1)
        historico = self.criar_item(
            proposta,
            perfil,
            ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
            1,
            vigente=False,
        )

        atual = self.criar_item(
            proposta,
            perfil,
            ItemPropostaVioleiros.PapelSugerido.INTEGRANTE,
            2,
        )

        self.assertFalse(historico.vigente)
        self.assertTrue(atual.vigente)

    def test_fks_protegem_historico_e_reutilizam_perfil_canonico(self):
        self.assertIs(
            PropostaVioleiros._meta.get_field('encontro').remote_field.on_delete,
            models.PROTECT,
        )
        self.assertIs(
            ItemPropostaVioleiros._meta.get_field(
                'proposta'
            ).remote_field.on_delete,
            models.PROTECT,
        )
        perfil_field = ItemPropostaVioleiros._meta.get_field('perfil_alpinista')
        self.assertIs(perfil_field.remote_field.model, PerfilAlpinista)
        self.assertIs(perfil_field.remote_field.on_delete, models.PROTECT)

    def test_nao_possui_substituicao_nem_copia_de_trabalho(self):
        campos = {
            field.name for field in ItemPropostaVioleiros._meta.get_fields()
        }

        self.assertNotIn('substituido_por', campos)
        self.assertNotIn('equipe_atual', campos)
        self.assertNotIn('trabalho_atual', campos)
        self.assertNotIn('indisponivel_por_equipe', campos)

    def test_criacao_estrutural_nao_produz_efeitos_em_outros_dominios(self):
        proposta = PropostaVioleiros.objects.create(encontro=self.encontro)
        self.criar_item(
            proposta,
            self.criar_perfil(1),
            ItemPropostaVioleiros.PapelSugerido.COORDENADOR,
            1,
        )

        self.assertFalse(TrabalhoEncontro.objects.exists())
        self.assertFalse(ConviteEncontro.objects.exists())
        self.assertFalse(Frequencia.objects.exists())
        self.assertEqual(
            ItemPropostaVioleiros.objects.count(),
            1,
        )

    def test_estrutura_legada_permanece_disponivel(self):
        campos_legados = {
            field.name for field in VinculoEncontroLegado._meta.get_fields()
        }

        self.assertTrue({'alpinista', 'encontro', 'funcao'} <= campos_legados)
