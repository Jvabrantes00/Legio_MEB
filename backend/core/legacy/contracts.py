from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Generic, TypeVar

from core.roles import SiaRole

from .issues import IssueSeverity, MigrationIssue


T = TypeVar('T')


@dataclass(frozen=True, slots=True)
class TransformationResult(Generic[T]):
    value: T | None
    issues: tuple[MigrationIssue, ...] = ()

    @property
    def is_valid(self) -> bool:
        return self.value is not None and not any(
            issue.severity in {IssueSeverity.ERROR, IssueSeverity.FATAL}
            for issue in self.issues
        )


@dataclass(frozen=True, slots=True)
class CanonicalAddress:
    street: str | None
    cep: str | None
    district: str | None
    city: str | None
    state: str | None


@dataclass(frozen=True, slots=True)
class CanonicalResponsible:
    relationship: str
    name: str | None
    phone: str | None


@dataclass(frozen=True, slots=True)
class CanonicalLegacyAlpinista:
    legacy_id: int | None
    name: str | None
    birth_date: date | None
    nickname: str | None
    address: CanonicalAddress
    email: str | None
    phones: tuple[str, ...]
    responsibles: tuple[CanonicalResponsible, ...]
    cpf: str | None
    is_violeiro: bool | None
    photo_reference: str | None
    private_notes: str | None
    deferred: dict[str, Any] = field(default_factory=dict)
    legacy_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalLegacyEncontro:
    legacy_id: int | None
    reference_date: date | None
    name: str | None
    encounter_type: str | None
    description: str | None
    message: str | None
    legacy_date_text: str | None
    media_reference: str | None
    deferred: dict[str, Any] = field(default_factory=dict)
    legacy_metadata: dict[str, Any] = field(default_factory=dict)


class ParticipationKind(StrEnum):
    ENCONTRISTA = 'ENCONTRISTA'
    EQUIPE = 'EQUIPE'


@dataclass(frozen=True, slots=True)
class CandidateParticipation:
    source_table: str
    source_id: int | str | None
    alpinista_legacy_id: int | None
    encontro_legacy_id: int | None
    kind: ParticipationKind
    canonical_function: str | None = None
    source_order: Decimal | None = None
    legacy_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalLegacyGroup:
    legacy_id: int | None
    created_at: date | None
    name: str | None
    description: str | None
    meeting_date_text: str | None
    address: str | None
    district: str | None
    active: bool | None
    logo_reference: str | None
    unresolved_people: dict[str, Any] = field(default_factory=dict)
    legacy_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalLegacyAvcGroup:
    legacy_id: int | None
    name: str | None
    description: str | None
    legacy_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalLegacyEvent:
    legacy_id: int | None
    event_date: date | None
    name: str | None
    description: str | None
    notes: str | None
    media_reference: str | None
    deferred: dict[str, Any] = field(default_factory=dict)
    legacy_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CandidateEventTeam:
    source_id: int | None
    event_legacy_id: int | None
    alpinista_legacy_id: int | None
    canonical_function: str | None
    source_order: Decimal | None
    legacy_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CanonicalLegacyUser:
    legacy_id: str | None
    name: str | None
    login: str | None
    sia_role: SiaRole | None
    deferred_group: str | None
    legacy_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CrosswalkEntry:
    source_table: str
    source_id: int | str
    target_model: str
    target_id: int | str


@dataclass(frozen=True, slots=True)
class LegacyFinancialRecord:
    legacy_id: int | None
    amount: Decimal | None
    occurred_on: date | None
    loaded_at: datetime | None
    deferred: dict[str, Any] = field(default_factory=dict)
