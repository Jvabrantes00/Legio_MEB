from django.test import SimpleTestCase

from core.formacao_catalogo import (
    BlocoFormativo,
    TEMAS_FORMATIVOS,
    TipoConteudoFormativo,
)
from core.models import Encontro


PALESTRAS_ESPERADAS = (
    ('PALESTRA_SER_PESSOA', 'Ser Pessoa', 1, BlocoFormativo.PRE_ESCALADA),
    (
        'PALESTRA_VALORES_CONTRAVALORES',
        'Valores e Contravalores',
        2,
        BlocoFormativo.PRE_ESCALADA,
    ),
    (
        'PALESTRA_AMOR_DE_DEUS',
        'Amor de Deus',
        3,
        BlocoFormativo.PRE_ESCALADA,
    ),
    ('PALESTRA_JESUS_CRISTO', 'Jesus Cristo', 4, BlocoFormativo.SABADO),
    ('PALESTRA_AMOR_DE_MARIA', 'Amor de Maria', 5, BlocoFormativo.SABADO),
    ('PALESTRA_PERDAO', 'Perdão', 6, BlocoFormativo.SABADO),
    (
        'PALESTRA_AMOR_SEXUALIDADE',
        'Amor e Sexualidade',
        7,
        BlocoFormativo.DOMINGO,
    ),
    ('PALESTRA_FAMILIA', 'Família', 8, BlocoFormativo.DOMINGO),
    (
        'PALESTRA_ESTRUTURA_MOVIMENTO',
        'Estrutura do Movimento',
        9,
        BlocoFormativo.DOMINGO,
    ),
)

BATE_PAPOS_ESPERADOS = (
    (
        'BATE_PAPO_JESUS_DEUS_HOMEM',
        'Jesus, Deus e Homem',
        1,
        BlocoFormativo.PRE_AVC,
    ),
    (
        'BATE_PAPO_DEPOIMENTO_SANTO_1',
        '1º Depoimento de um santo',
        2,
        BlocoFormativo.PRE_AVC,
    ),
    (
        'BATE_PAPO_DEPOIMENTO_SANTO_2',
        '2º Depoimento de um santo',
        3,
        BlocoFormativo.PRE_AVC,
    ),
    (
        'BATE_PAPO_DEPOIMENTO_SANTO_3',
        '3º Depoimento de um santo',
        4,
        BlocoFormativo.PRE_AVC,
    ),
    (
        'BATE_PAPO_ALIANCAS_DEUS_HOMEM',
        'As alianças de Deus com o homem',
        5,
        BlocoFormativo.SEXTA,
    ),
    ('BATE_PAPO_SER_PROFETA', 'Ser profeta', 6, BlocoFormativo.SEXTA),
    (
        'BATE_PAPO_NECESSIDADES_SER_HUMANO',
        'As necessidades do ser humano',
        7,
        BlocoFormativo.SABADO,
    ),
    (
        'BATE_PAPO_IMPORTANCIA_SACRAMENTOS_PROFETA',
        'A importância dos sacramentos para o profeta',
        8,
        BlocoFormativo.SABADO,
    ),
    (
        'BATE_PAPO_CAMPANHA_FRATERNIDADE',
        'Campanha da Fraternidade',
        9,
        BlocoFormativo.DOMINGO,
    ),
    (
        'BATE_PAPO_BIOGRAFIA_SANTO',
        'Biografia de um santo (5 pessoas)',
        10,
        BlocoFormativo.DOMINGO,
    ),
    (
        'BATE_PAPO_PROFETA_IGREJA',
        'Profeta e a igreja',
        11,
        BlocoFormativo.DOMINGO,
    ),
)


class FormationCatalogTests(SimpleTestCase):
    def _temas(self, tipo_conteudo):
        return tuple(
            tema
            for tema in TEMAS_FORMATIVOS.values()
            if tema.tipo_conteudo == tipo_conteudo
        )

    def test_catalogos_possuem_quantidades_e_conteudo_exatos(self):
        palestras = self._temas(TipoConteudoFormativo.PALESTRA)
        bate_papos = self._temas(TipoConteudoFormativo.BATE_PAPO)

        self.assertEqual(len(palestras), 9)
        self.assertEqual(len(bate_papos), 11)
        self.assertEqual(
            tuple(
                (tema.codigo, tema.titulo, tema.ordem, tema.bloco)
                for tema in palestras
            ),
            PALESTRAS_ESPERADAS,
        )
        self.assertEqual(
            tuple(
                (tema.codigo, tema.titulo, tema.ordem, tema.bloco)
                for tema in bate_papos
            ),
            BATE_PAPOS_ESPERADOS,
        )

    def test_codigos_e_ordens_sao_unicos(self):
        temas = tuple(TEMAS_FORMATIVOS.values())
        codigos = [tema.codigo for tema in temas]
        self.assertEqual(len(codigos), len(set(codigos)))
        self.assertEqual(set(TEMAS_FORMATIVOS), set(codigos))

        for tipo_conteudo in TipoConteudoFormativo:
            ordens = [
                tema.ordem
                for tema in temas
                if tema.tipo_conteudo == tipo_conteudo
            ]
            self.assertEqual(len(ordens), len(set(ordens)))
            self.assertEqual(ordens, list(range(1, len(ordens) + 1)))

    def test_escalada_e_esppa_compartilham_palestras(self):
        palestras = self._temas(TipoConteudoFormativo.PALESTRA)

        for tema in palestras:
            with self.subTest(codigo=tema.codigo):
                self.assertEqual(
                    tema.tipos_encontro,
                    frozenset({Encontro.Tipo.ESCALADA, Encontro.Tipo.ESPPA}),
                )

    def test_avc_possui_catalogo_separado_e_acampamento_nao_possui_tema(self):
        bate_papos = self._temas(TipoConteudoFormativo.BATE_PAPO)

        for tema in bate_papos:
            with self.subTest(codigo=tema.codigo):
                self.assertEqual(
                    tema.tipos_encontro,
                    frozenset({Encontro.Tipo.AVC}),
                )
        self.assertFalse(any(
            Encontro.Tipo.ACAMPAMENTO in tema.tipos_encontro
            for tema in TEMAS_FORMATIVOS.values()
        ))

    def test_lookup_por_tema_codigo_e_registry_imutavel(self):
        tema = TEMAS_FORMATIVOS['PALESTRA_SER_PESSOA']

        self.assertEqual(tema.titulo, 'Ser Pessoa')
        self.assertEqual(tema.bloco, BlocoFormativo.PRE_ESCALADA)
        with self.assertRaises(TypeError):
            TEMAS_FORMATIVOS['NOVO_TEMA'] = tema
