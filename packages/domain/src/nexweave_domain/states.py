"""Frozen R1 vocabulary; transitions are enforced by application services later."""

from enum import StrEnum


class DataClassification(StrEnum):
    PUBLIC = "PUBLIC"
    INTERNAL = "INTERNAL"
    CONFIDENTIAL = "CONFIDENTIAL"
    HIGHLY_RESTRICTED = "HIGHLY_RESTRICTED"


class LocatorStatus(StrEnum):
    VALID = "VALID"
    STALE = "STALE"
    UNRESOLVED = "UNRESOLVED"
    REVOKED = "REVOKED"


class EvidenceRole(StrEnum):
    SUPPORTS = "SUPPORTS"
    OPPOSES = "OPPOSES"
    CONTEXT = "CONTEXT"


class SourceState(StrEnum):
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class SourceVersionState(StrEnum):
    STORED = "STORED"
    PARSING = "PARSING"
    PARTIAL = "PARTIAL"
    PARSED = "PARSED"
    FAILED = "FAILED"
    SUPERSEDED = "SUPERSEDED"


class ReviewState(StrEnum):
    OPEN = "OPEN"
    CLAIMED = "CLAIMED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class ReleaseState(StrEnum):
    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY_FOR_APPROVAL = "READY_FOR_APPROVAL"
    APPROVED = "APPROVED"
    PUBLISHING = "PUBLISHING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    DEPRECATED = "DEPRECATED"
