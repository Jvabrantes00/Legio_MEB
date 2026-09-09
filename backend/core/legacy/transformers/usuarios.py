from collections.abc import Mapping
from typing import Any

from ..contracts import CanonicalLegacyUser, TransformationResult
from ..issues import IssueCode, IssueSeverity, MigrationIssue
from ..mappings import LEGACY_USER_TYPE_TO_SIA_ROLE, map_explicit
from ..normalizers import normalize_nullable_text
from .common import safe_normalize, unknown_metadata


def transform_user(row: Mapping[str, Any]) -> TransformationResult[CanonicalLegacyUser]:
    table = 'adm_usu'
    issues: list[MigrationIssue] = []
    legacy_id = normalize_nullable_text(row.get('usu_login'))
    role = safe_normalize(
        map_explicit,
        row.get('usu_tipo'),
        issues=issues,
        table=table,
        legacy_id=legacy_id,
        field='usu_tipo',
        mapping=LEGACY_USER_TYPE_TO_SIA_ROLE,
        unknown_code=IssueCode.UNKNOWN_USER_TYPE,
        concept='tipo de usuário',
    )
    if row.get('usu_senha') is not None:
        issues.append(MigrationIssue(
            code=IssueCode.LEGACY_SECRET_IGNORED,
            severity=IssueSeverity.WARNING,
            table=table,
            legacy_id=legacy_id,
            field='usu_senha',
            description='Credencial histórica ignorada; deve ser rotacionada, não migrada.',
        ))
    dto = CanonicalLegacyUser(
        legacy_id=legacy_id,
        name=normalize_nullable_text(row.get('usu_nome')),
        login=legacy_id,
        sia_role=role,
        deferred_group=normalize_nullable_text(row.get('grupo')),
        legacy_metadata=unknown_metadata(
            row,
            {'usu_nome', 'usu_login', 'usu_senha', 'usu_tipo', 'grupo'},
        ),
    )
    return TransformationResult(dto, tuple(issues))
