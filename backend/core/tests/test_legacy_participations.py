from dataclasses import replace

from django.test import SimpleTestCase

from core.legacy.contracts import ParticipationKind
from core.legacy.issues import IssueCode
from core.legacy.transformers import (
    transform_encounter_participant,
    transform_encounter_team,
    validate_participation_set,
)


class LegacyParticipationTests(SimpleTestCase):
    def test_encontrista_preserva_chaves_legadas_sem_usar_pk_novo(self):
        result = transform_encounter_participant({
            'CD_REGISTRO': '10',
            'CD_ENCONTRO': '20',
            'NO_ALPINISTA': 'campo legado sem destino comprovado',
        })

        self.assertTrue(result.is_valid)
        self.assertEqual(result.value.alpinista_legacy_id, 10)
        self.assertEqual(result.value.encontro_legacy_id, 20)
        self.assertEqual(result.value.kind, ParticipationKind.ENCONTRISTA)
        self.assertIn('NO_ALPINISTA', result.value.legacy_metadata)

    def test_referencias_orfas_sao_detectadas_sem_banco(self):
        candidate = transform_encounter_participant({
            'CD_REGISTRO': 99,
            'CD_ENCONTRO': 88,
        }).value

        issues = validate_participation_set(
            [candidate],
            known_alpinista_ids={10},
            known_encontro_ids={20},
        )

        self.assertEqual(
            {issue.code for issue in issues},
            {IssueCode.ORPHAN_ALPINISTA, IssueCode.ORPHAN_ENCONTRO},
        )

    def test_participacao_duplicada_e_detectada(self):
        candidate = transform_encounter_participant({
            'CD_REGISTRO': 10,
            'CD_ENCONTRO': 20,
        }).value

        issues = validate_participation_set(
            [candidate, candidate],
            known_alpinista_ids={10},
            known_encontro_ids={20},
        )

        self.assertEqual([issue.code for issue in issues], [IssueCode.DUPLICATE_PARTICIPATION])

    def test_duas_classificacoes_no_mesmo_encontro_exigem_decisao(self):
        participant = transform_encounter_participant({
            'CD_REGISTRO': 10,
            'CD_ENCONTRO': 20,
        }).value
        team = replace(
            participant,
            source_table='encontro_equipe',
            source_id=30,
            kind=ParticipationKind.EQUIPE,
            canonical_function='funcao-canonica-sintetica',
        )

        issues = validate_participation_set(
            [participant, team],
            known_alpinista_ids={10},
            known_encontro_ids={20},
        )

        self.assertEqual([issue.code for issue in issues], [IssueCode.INCOMPATIBLE_FUNCTIONS])

    def test_ordem_da_equipe_e_preservada_como_metadata_tipado(self):
        result = transform_encounter_team({
            'CD_EQUIPE': 30,
            'CD_REGISTRO': 10,
            'CD_ENCONTRO': 20,
            'NR_ORDEM': '3.5',
            'NM_FUNCAO': None,
        })

        self.assertEqual(str(result.value.source_order), '3.5')
