"""Pure row-to-DTO transformers for the legacy SIA schema."""

from .alpinistas import transform_alpinista
from .encontros import transform_encontro
from .eventos import transform_event, transform_event_team
from .grupos import transform_avc_group, transform_group
from .participacoes import (
    transform_encounter_participant,
    transform_encounter_team,
    validate_participation_set,
)
from .usuarios import transform_user

__all__ = (
    'transform_alpinista',
    'transform_avc_group',
    'transform_encounter_participant',
    'transform_encounter_team',
    'transform_encontro',
    'transform_event',
    'transform_event_team',
    'transform_group',
    'transform_user',
    'validate_participation_set',
)
