from collections.abc import Iterable, Mapping, Set
from typing import Any

from ..contracts import CandidateParticipation, ParticipationKind, TransformationResult
from ..issues import IssueCode, IssueSeverity, MigrationIssue
from ..mappings import LEGACY_FUNCTION_TO_CANONICAL, map_explicit
from ..normalizers import (
    normalize_legacy_decimal,
    normalize_legacy_id,
    normalize_nullable_text,
)
from .common import safe_normalize, unknown_metadata


def _source_id(row, id_field, fallback_fields=()):
    if id_field and row.get(id_field) is not None:
        return normalize_nullable_text(row.get(id_field))
    parts = [normalize_nullable_text(row.get(field)) for field in fallback_fields]
    return ':'.join(part or '?' for part in parts)


def transform_encounter_participant(
    row: Mapping[str, Any],
) -> TransformationResult[CandidateParticipation]:
    table = 'encontros_alpinista'
    source_id = _source_id(row, None, ('CD_REGISTRO', 'CD_ENCONTRO'))
    issues: list[MigrationIssue] = []

    def legacy_id(field):
        return safe_normalize(
            normalize_legacy_id, row.get(field), issues=issues, table=table,
            legacy_id=source_id, field=field,
        )

    dto = CandidateParticipation(
        source_table=table,
        source_id=source_id,
        alpinista_legacy_id=legacy_id('CD_REGISTRO'),
        encontro_legacy_id=legacy_id('CD_ENCONTRO'),
        kind=ParticipationKind.ENCONTRISTA,
        legacy_metadata=unknown_metadata(
            row,
            {'CD_REGISTRO', 'CD_ENCONTRO'},
        ),
    )
    return TransformationResult(dto, tuple(issues))


def transform_encounter_team(
    row: Mapping[str, Any],
) -> TransformationResult[CandidateParticipation]:
    table = 'encontro_equipe'
    source_id = _source_id(row, 'CD_EQUIPE')
    issues: list[MigrationIssue] = []

    def normalized(normalizer, field, **kwargs):
        return safe_normalize(
            normalizer, row.get(field), issues=issues, table=table,
            legacy_id=source_id, field=field, **kwargs,
        )

    function = safe_normalize(
        map_explicit,
        row.get('NM_FUNCAO'),
        issues=issues,
        table=table,
        legacy_id=source_id,
        field='NM_FUNCAO',
        mapping=LEGACY_FUNCTION_TO_CANONICAL,
        unknown_code=IssueCode.UNKNOWN_FUNCTION,
        concept='função de encontro',
    )
    dto = CandidateParticipation(
        source_table=table,
        source_id=source_id,
        alpinista_legacy_id=normalized(normalize_legacy_id, 'CD_REGISTRO'),
        encontro_legacy_id=normalized(normalize_legacy_id, 'CD_ENCONTRO'),
        kind=ParticipationKind.EQUIPE,
        canonical_function=function,
        source_order=normalized(normalize_legacy_decimal, 'NR_ORDEM'),
        legacy_metadata=unknown_metadata(
            row,
            {'CD_EQUIPE', 'CD_REGISTRO', 'CD_ENCONTRO', 'NM_FUNCAO', 'NR_ORDEM'},
        ),
    )
    return TransformationResult(dto, tuple(issues))


def validate_participation_set(
    participations: Iterable[CandidateParticipation],
    *,
    known_alpinista_ids: Set[int],
    known_encontro_ids: Set[int],
) -> tuple[MigrationIssue, ...]:
    issues: list[MigrationIssue] = []
    seen: dict[tuple[int | None, int | None], CandidateParticipation] = {}
    for participation in participations:
        if participation.alpinista_legacy_id not in known_alpinista_ids:
            issues.append(MigrationIssue(
                code=IssueCode.ORPHAN_ALPINISTA,
                severity=IssueSeverity.ERROR,
                table=participation.source_table,
                legacy_id=participation.source_id,
                field='CD_REGISTRO',
                description='Participação referencia Alpinista legado inexistente.',
            ))
        if participation.encontro_legacy_id not in known_encontro_ids:
            issues.append(MigrationIssue(
                code=IssueCode.ORPHAN_ENCONTRO,
                severity=IssueSeverity.ERROR,
                table=participation.source_table,
                legacy_id=participation.source_id,
                field='CD_ENCONTRO',
                description='Participação referencia Encontro legado inexistente.',
            ))

        key = (
            participation.alpinista_legacy_id,
            participation.encontro_legacy_id,
        )
        previous = seen.get(key)
        if previous is None:
            seen[key] = participation
            continue
        same_classification = (
            previous.kind == participation.kind
            and previous.canonical_function == participation.canonical_function
        )
        issues.append(MigrationIssue(
            code=(
                IssueCode.DUPLICATE_PARTICIPATION
                if same_classification
                else IssueCode.INCOMPATIBLE_FUNCTIONS
            ),
            severity=IssueSeverity.ERROR,
            table=participation.source_table,
            legacy_id=participation.source_id,
            field='CD_REGISTRO,CD_ENCONTRO',
            description=(
                'Participação legada duplicada para a mesma pessoa e encontro.'
                if same_classification
                else 'Pessoa possui classificações incompatíveis no mesmo encontro.'
            ),
        ))
    return tuple(issues)
