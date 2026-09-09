from collections.abc import Mapping
from types import MappingProxyType
from typing import TypeVar

from core.roles import SiaRole

from .issues import IssueCode, LegacyNormalizationError
from .normalizers import normalize_nullable_text


T = TypeVar('T')

# Intentionally empty until profiling reveals the real legacy vocabulary.
LEGACY_USER_TYPE_TO_SIA_ROLE: Mapping[str, SiaRole] = MappingProxyType({})
LEGACY_ENCOUNTER_TYPE_TO_CANONICAL: Mapping[str, str] = MappingProxyType({})
LEGACY_FUNCTION_TO_CANONICAL: Mapping[str, str] = MappingProxyType({})
LEGACY_STATUS_TO_CANONICAL: Mapping[str, str] = MappingProxyType({})


def map_explicit(
    value,
    mapping: Mapping[str, T],
    *,
    unknown_code: IssueCode,
    concept: str,
) -> T | None:
    normalized = normalize_nullable_text(value)
    if normalized is None:
        return None
    key = normalized.casefold()
    normalized_mapping = {str(source).strip().casefold(): target for source, target in mapping.items()}
    try:
        return normalized_mapping[key]
    except KeyError as error:
        raise LegacyNormalizationError(
            unknown_code,
            f'Valor legado não reconhecido para {concept}; requer mapeamento explícito.',
        ) from error
