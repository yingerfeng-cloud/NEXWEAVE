from typing import Literal

from pydantic import UUID7

from nexweave_contracts.base import ContractModel
from nexweave_domain import ActorType, DataClassification, MembershipStatus, Role, SpaceStatus


class SpaceChangedEventData(ContractModel):
    space_id: UUID7
    status: SpaceStatus
    version: int
    change: Literal["CREATED", "UPDATED", "ARCHIVED"]


class MembershipChangedEventData(ContractModel):
    space_id: UUID7
    subject_type: ActorType
    subject_id: UUID7
    roles: tuple[Role, ...]
    clearance: DataClassification
    status: MembershipStatus
    policy_version: int


class PlatformEntityChangedEventData(ContractModel):
    entity_kind: Literal[
        "USER",
        "SERVICE_IDENTITY",
        "MODEL_PROFILE",
        "PROMPT_VERSION",
        "CONNECTOR_DEFINITION",
        "MANAGED_OBJECT",
    ]
    entity_id: UUID7
    space_id: UUID7 | None = None
    version: int
    status: str
    change: Literal["CREATED", "STORED"]
    checksum: str | None = None
