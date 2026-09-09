from collections.abc import Mapping
from typing import Any

from ..contracts import (
    CanonicalLegacyAvcGroup,
    CanonicalLegacyGroup,
    TransformationResult,
)
from ..issues import IssueCode, IssueSeverity, MigrationIssue
from ..normalizers import (
    normalize_legacy_date,
    normalize_legacy_id,
    normalize_media_reference,
    normalize_nullable_text,
    normalize_sn_flag,
)
from .common import safe_normalize, unknown_metadata


GROUP_FIELDS = {
    'CD_GRUPO', 'DT_CRIACAO', 'NO_GRUPO', 'TX_GRUPO', 'TX_DATA',
    'TX_ENDERECO', 'IN_BAIRRO', 'NO_PADRINHO', 'NO_MADRINHA',
    'NO_COORDENADOR1', 'NO_COORDENADOR2', 'NO_COORDENADOR3',
    'IN_ATIVO', 'URL_LOGO',
}


def transform_group(row: Mapping[str, Any]) -> TransformationResult[CanonicalLegacyGroup]:
    table = 'grupos'
    issues: list[MigrationIssue] = []
    raw_id = normalize_nullable_text(row.get('CD_GRUPO'))

    def normalized(normalizer, field, **kwargs):
        return safe_normalize(
            normalizer, row.get(field), issues=issues, table=table,
            legacy_id=raw_id, field=field, **kwargs,
        )

    legacy_id = normalized(normalize_legacy_id, 'CD_GRUPO')
    name = normalize_nullable_text(row.get('NO_GRUPO'))
    if name is None:
        issues.append(MigrationIssue(
            code=IssueCode.MISSING_REQUIRED_NAME,
            severity=IssueSeverity.ERROR,
            table=table,
            legacy_id=legacy_id or raw_id,
            field='NO_GRUPO',
            description='Grupo legado não possui nome utilizável.',
        ))
    dto = CanonicalLegacyGroup(
        legacy_id=legacy_id,
        created_at=normalized(normalize_legacy_date, 'DT_CRIACAO'),
        name=name,
        description=normalize_nullable_text(row.get('TX_GRUPO')),
        meeting_date_text=normalize_nullable_text(row.get('TX_DATA')),
        address=normalize_nullable_text(row.get('TX_ENDERECO')),
        district=normalize_nullable_text(row.get('IN_BAIRRO')),
        active=normalized(normalize_sn_flag, 'IN_ATIVO'),
        logo_reference=normalized(normalize_media_reference, 'URL_LOGO'),
        unresolved_people={
            field: row.get(field)
            for field in (
                'NO_PADRINHO', 'NO_MADRINHA', 'NO_COORDENADOR1',
                'NO_COORDENADOR2', 'NO_COORDENADOR3',
            )
            if field in row
        },
        legacy_metadata=unknown_metadata(row, GROUP_FIELDS),
    )
    return TransformationResult(dto, tuple(issues))


def transform_avc_group(
    row: Mapping[str, Any],
) -> TransformationResult[CanonicalLegacyAvcGroup]:
    table = 'grupo_avc'
    issues: list[MigrationIssue] = []
    raw_id = normalize_nullable_text(row.get('CD_GRUPO_AVC'))
    legacy_id = safe_normalize(
        normalize_legacy_id, row.get('CD_GRUPO_AVC'), issues=issues,
        table=table, legacy_id=raw_id, field='CD_GRUPO_AVC',
    )
    dto = CanonicalLegacyAvcGroup(
        legacy_id=legacy_id,
        name=normalize_nullable_text(row.get('NO_GRUPO_AVC')),
        description=normalize_nullable_text(row.get('DS_GRUPO_AVC')),
        legacy_metadata=unknown_metadata(
            row,
            {'CD_GRUPO_AVC', 'NO_GRUPO_AVC', 'DS_GRUPO_AVC'},
        ),
    )
    return TransformationResult(dto, tuple(issues))
