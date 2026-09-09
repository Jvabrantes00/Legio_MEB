from collections.abc import Mapping
from typing import Any

from ..contracts import CanonicalLegacyEncontro, TransformationResult
from ..issues import IssueCode, IssueSeverity, MigrationIssue
from ..mappings import LEGACY_ENCOUNTER_TYPE_TO_CANONICAL, map_explicit
from ..normalizers import (
    normalize_legacy_date,
    normalize_legacy_id,
    normalize_media_reference,
    normalize_nullable_text,
)
from .common import safe_normalize, unknown_metadata


TABLE = 'encontro'
FIELDS = {
    'CD_ENCONTRO', 'DT_ENCONTRO', 'NO_ENCONTRO', 'IN_TIPO_ENCONTRO',
    'DS_ENCONTRO', 'DS_MENSAGEM', 'DT_ENCONTRO_COMPLETA', 'URL_ENCONTRO',
}


def transform_encontro(row: Mapping[str, Any]) -> TransformationResult[CanonicalLegacyEncontro]:
    issues: list[MigrationIssue] = []
    raw_id = normalize_nullable_text(row.get('CD_ENCONTRO'))
    legacy_id = safe_normalize(
        normalize_legacy_id, row.get('CD_ENCONTRO'), issues=issues,
        table=TABLE, legacy_id=raw_id, field='CD_ENCONTRO',
    )
    name = normalize_nullable_text(row.get('NO_ENCONTRO'))
    if name is None:
        issues.append(MigrationIssue(
            code=IssueCode.MISSING_REQUIRED_NAME,
            severity=IssueSeverity.ERROR,
            table=TABLE,
            legacy_id=legacy_id or raw_id,
            field='NO_ENCONTRO',
            description='Encontro legado não possui nome utilizável.',
        ))

    def normalized(normalizer, field, **kwargs):
        return safe_normalize(
            normalizer, row.get(field), issues=issues, table=TABLE,
            legacy_id=legacy_id or raw_id, field=field, **kwargs,
        )

    encounter_type = safe_normalize(
        map_explicit,
        row.get('IN_TIPO_ENCONTRO'),
        issues=issues,
        table=TABLE,
        legacy_id=legacy_id or raw_id,
        field='IN_TIPO_ENCONTRO',
        mapping=LEGACY_ENCOUNTER_TYPE_TO_CANONICAL,
        unknown_code=IssueCode.UNKNOWN_ENCOUNTER_TYPE,
        concept='tipo de encontro',
    )
    dto = CanonicalLegacyEncontro(
        legacy_id=legacy_id,
        reference_date=normalized(normalize_legacy_date, 'DT_ENCONTRO'),
        name=name,
        encounter_type=encounter_type,
        description=normalize_nullable_text(row.get('DS_ENCONTRO')),
        message=normalize_nullable_text(row.get('DS_MENSAGEM')),
        legacy_date_text=normalize_nullable_text(row.get('DT_ENCONTRO_COMPLETA')),
        media_reference=normalized(normalize_media_reference, 'URL_ENCONTRO'),
        deferred={'status': None},
        legacy_metadata=unknown_metadata(row, FIELDS),
    )
    return TransformationResult(value=dto, issues=tuple(issues))
