from datetime import datetime

from pydantic import UUID7, Field, field_validator

from nexweave_contracts.base import ContractModel
from nexweave_domain import (
    ActorType,
    DataClassification,
    MembershipStatus,
    Role,
    SpaceStatus,
)


class SpaceCreate(ContractModel):
    organization_id: UUID7
    slug: str = Field(min_length=1, max_length=63, pattern=r"^[a-z0-9][a-z0-9-]*$")
    display_name: str = Field(min_length=1, max_length=255)
    description: str = Field(default="", max_length=2000)
    default_classification: DataClassification = DataClassification.INTERNAL


class SpacePatch(ContractModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    default_classification: DataClassification | None = None


class KnowledgeSpaceResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    organization_id: UUID7
    slug: str
    display_name: str
    description: str
    default_classification: DataClassification
    status: SpaceStatus
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7
    archived_at: datetime | None = None

    @field_validator("created_at", "updated_at", "archived_at")
    @classmethod
    def timestamps_must_include_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("timestamps must include a timezone")
        return value


class SpaceListResponse(ContractModel):
    items: tuple[KnowledgeSpaceResponse, ...]
    next_cursor: str | None = None


class MembershipPolicy(ContractModel):
    subject_type: ActorType
    roles: tuple[Role, ...] = Field(min_length=1)
    clearance: DataClassification = DataClassification.INTERNAL


class SpaceMemberResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    subject_type: ActorType
    subject_id: UUID7
    roles: tuple[Role, ...]
    clearance: DataClassification
    status: MembershipStatus
    version: int = Field(ge=1)
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7
    revoked_at: datetime | None = None


class SpaceMemberListResponse(ContractModel):
    items: tuple[SpaceMemberResponse, ...]
    next_cursor: str | None = None
