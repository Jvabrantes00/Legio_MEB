from collections.abc import Mapping
from typing import Any

from ..contracts import CandidateEventTeam, CanonicalLegacyEvent, TransformationResult
from ..issues import IssueCode
from ..mappings import LEGACY_FUNCTION_TO_CANONICAL, map_explicit
from ..normalizers import (
    normalize_legacy_date,
    normalize_legacy_decimal,
    normalize_legacy_id,
    normalize_media_reference,
    normalize_nullable_text,
)
from .common import safe_normalize, unknown_metadata


def transform_event(row: Mapping[str, Any]) -> TransformationResult[CanonicalLegacyEvent]:
    table = 'evento'
    issues = []
    raw_id = normalize_nullable_text(row.get('CD_EVENTO'))

    def normalized(normalizer, field, **kwargs):
        return safe_normalize(
            normalizer, row.get(field), issues=issues, table=table,
            legacy_id=raw_id, field=field, **kwargs,
        )

    dto = CanonicalLegacyEvent(
        legacy_id=normalized(normalize_legacy_id, 'CD_EVENTO'),
        event_date=normalized(normalize_legacy_date, 'DT_EVENTO'),
        name=normalize_nullable_text(row.get('NO_EVENTO')),
        description=normalize_nullable_text(row.get('DS_EVENTO')),
        notes=normalize_nullable_text(row.get('OBS_EVENTO')),
        media_reference=normalized(normalize_media_reference, 'URL_EVENTO'),
        deferred={
            'IN_TIPO_EVENTO': row.get('IN_TIPO_EVENTO'),
            'NO_TIPO_EVENTO': row.get('NO_TIPO_EVENTO'),
        },
        legacy_metadata=unknown_metadata(row, {
            'CD_EVENTO', 'DT_EVENTO', 'NO_EVENTO', 'IN_TIPO_EVENTO',
            'NO_TIPO_EVENTO', 'DS_EVENTO', 'OBS_EVENTO', 'URL_EVENTO',
        }),
    )
    return TransformationResult(dto, tuple(issues))


def transform_event_team(row: Mapping[str, Any]) -> TransformationResult[CandidateEventTeam]:
    table = 'evento_equipe'
    issues = []
    raw_id = normalize_nullable_text(row.get('CD_EVENTO_EQUIPE'))

    def normalized(normalizer, field, **kwargs):
        return safe_normalize(
            normalizer, row.get(field), issues=issues, table=table,
            legacy_id=raw_id, field=field, **kwargs,
        )

    function = safe_normalize(
        map_explicit, row.get('NM_FUNCAO'), issues=issues, table=table,
        legacy_id=raw_id, field='NM_FUNCAO',
        mapping=LEGACY_FUNCTION_TO_CANONICAL,
        unknown_code=IssueCode.UNKNOWN_FUNCTION,
        concept='função de equipe de evento',
    )
    dto = CandidateEventTeam(
        source_id=normalized(normalize_legacy_id, 'CD_EVENTO_EQUIPE'),
        event_legacy_id=normalized(normalize_legacy_id, 'CD_EVENTO'),
        alpinista_legacy_id=normalized(normalize_legacy_id, 'CD_REGISTRO'),
        canonical_function=function,
        source_order=normalized(normalize_legacy_decimal, 'NR_ORDEM'),
        legacy_metadata=unknown_metadata(row, {
            'CD_EVENTO_EQUIPE', 'CD_EVENTO', 'CD_REGISTRO', 'NR_ORDEM',
            'NM_FUNCAO',
        }),
    )
    return TransformationResult(dto, tuple(issues))
