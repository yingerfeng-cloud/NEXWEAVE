"""M1 governance object lifecycle vocabulary."""

from enum import StrEnum


class GovernanceStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DEPRECATED = "DEPRECATED"


class ConnectorDefinitionStatus(StrEnum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"


class ScanStatus(StrEnum):
    PENDING = "PENDING"
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    FAILED = "FAILED"


class UploadSessionStatus(StrEnum):
    INITIATED = "INITIATED"
    UPLOADING = "UPLOADING"
    COMPLETED = "COMPLETED"
    ABORTED = "ABORTED"
    EXPIRED = "EXPIRED"
