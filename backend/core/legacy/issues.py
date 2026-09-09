from dataclasses import dataclass
from enum import StrEnum


class IssueSeverity(StrEnum):
    INFO = 'INFO'
    WARNING = 'WARNING'
    ERROR = 'ERROR'
    FATAL = 'FATAL'


class IssueCode(StrEnum):
    INVALID_CPF = 'INVALID_CPF'
    DUPLICATE_CPF = 'DUPLICATE_CPF'
    INVALID_EMAIL = 'INVALID_EMAIL'
    DUPLICATE_EMAIL = 'DUPLICATE_EMAIL'
    INVALID_PHONE = 'INVALID_PHONE'
    PHONE_CONFLICT = 'PHONE_CONFLICT'
    INVALID_DATE = 'INVALID_DATE'
    INVALID_CEP = 'INVALID_CEP'
    INVALID_UF = 'INVALID_UF'
    INVALID_ID = 'INVALID_ID'
    INVALID_NUMBER = 'INVALID_NUMBER'
    INVALID_MONEY = 'INVALID_MONEY'
    INVALID_MEDIA_REFERENCE = 'INVALID_MEDIA_REFERENCE'
    MISSING_REQUIRED_NAME = 'MISSING_REQUIRED_NAME'
    UNKNOWN_BOOLEAN_VALUE = 'UNKNOWN_BOOLEAN_VALUE'
    UNKNOWN_STATUS = 'UNKNOWN_STATUS'
    UNKNOWN_USER_TYPE = 'UNKNOWN_USER_TYPE'
    UNKNOWN_ENCOUNTER_TYPE = 'UNKNOWN_ENCOUNTER_TYPE'
    UNKNOWN_FUNCTION = 'UNKNOWN_FUNCTION'
    ORPHAN_ALPINISTA = 'ORPHAN_ALPINISTA'
    ORPHAN_ENCONTRO = 'ORPHAN_ENCONTRO'
    DUPLICATE_PARTICIPATION = 'DUPLICATE_PARTICIPATION'
    INCOMPATIBLE_FUNCTIONS = 'INCOMPATIBLE_FUNCTIONS'
    AMBIGUOUS_PERSON_MATCH = 'AMBIGUOUS_PERSON_MATCH'
    MEDIA_NOT_FOUND = 'MEDIA_NOT_FOUND'
    ENCODING_PROBLEM = 'ENCODING_PROBLEM'
    LEGACY_SECRET_IGNORED = 'LEGACY_SECRET_IGNORED'


@dataclass(frozen=True, slots=True)
class MigrationIssue:
    code: IssueCode
    severity: IssueSeverity
    table: str
    legacy_id: int | str | None
    field: str | None
    description: str

    def __post_init__(self):
        if not self.description.strip():
            raise ValueError('A descrição segura da issue é obrigatória.')


class LegacyNormalizationError(ValueError):
    """Typed failure whose message is safe to place in a migration report."""

    def __init__(self, code: IssueCode, safe_description: str):
        self.code = code
        self.safe_description = safe_description
        super().__init__(safe_description)


def issue_from_error(
    error: LegacyNormalizationError,
    *,
    table: str,
    legacy_id: int | str | None,
    field: str,
    severity: IssueSeverity = IssueSeverity.ERROR,
) -> MigrationIssue:
    return MigrationIssue(
        code=error.code,
        severity=severity,
        table=table,
        legacy_id=legacy_id,
        field=field,
        description=error.safe_description,
    )
