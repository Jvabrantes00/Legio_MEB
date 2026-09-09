"""Pure compatibility layer for the future migration from the legacy SIA."""

from .contracts import TransformationResult
from .issues import IssueCode, IssueSeverity, MigrationIssue

__all__ = (
    'IssueCode',
    'IssueSeverity',
    'MigrationIssue',
    'TransformationResult',
)
