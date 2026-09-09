from collections.abc import Callable, Mapping
from typing import Any, TypeVar

from ..issues import (
    IssueSeverity,
    LegacyNormalizationError,
    MigrationIssue,
    issue_from_error,
)


T = TypeVar('T')


def safe_normalize(
    normalizer: Callable[..., T],
    value,
    *,
    issues: list[MigrationIssue],
    table: str,
    legacy_id: int | str | None,
    field: str,
    severity: IssueSeverity = IssueSeverity.ERROR,
    **kwargs,
) -> T | None:
    try:
        return normalizer(value, **kwargs)
    except LegacyNormalizationError as error:
        issues.append(
            issue_from_error(
                error,
                table=table,
                legacy_id=legacy_id,
                field=field,
                severity=severity,
            )
        )
        return None


def unknown_metadata(row: Mapping[str, Any], consumed_fields: set[str]) -> dict[str, Any]:
    return {
        field: value
        for field, value in row.items()
        if field not in consumed_fields
    }
