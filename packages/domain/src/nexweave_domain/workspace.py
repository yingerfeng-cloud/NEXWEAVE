"""Knowledge-space and membership aggregates."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from nexweave_domain.access import ActorType, Role
from nexweave_domain.states import DataClassification

SLUG_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


class SpaceStatus(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class MembershipStatus(StrEnum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class DomainRuleViolation(ValueError):
    """Raised when a command violates an aggregate invariant."""


@dataclass(frozen=True, slots=True)
class KnowledgeSpace:
    id: UUID
    tenant_id: UUID
    organization_id: UUID
    slug: str
    display_name: str
    description: str
    default_classification: DataClassification
    status: SpaceStatus
    version: int
    created_at: datetime
    created_by: UUID
    updated_at: datetime
    updated_by: UUID
    archived_at: datetime | None = None

    @classmethod
    def create(
        cls,
        *,
        space_id: UUID,
        tenant_id: UUID,
        organization_id: UUID,
        slug: str,
        display_name: str,
        description: str,
        default_classification: DataClassification,
        actor_id: UUID,
        now: datetime,
    ) -> KnowledgeSpace:
        normalized_slug = slug.strip().lower()
        if not SLUG_PATTERN.fullmatch(normalized_slug):
            raise DomainRuleViolation("space slug must use lowercase letters, digits and hyphens")
        normalized_name = display_name.strip()
        if not normalized_name:
            raise DomainRuleViolation("space display name is required")
        return cls(
            id=space_id,
            tenant_id=tenant_id,
            organization_id=organization_id,
            slug=normalized_slug,
            display_name=normalized_name,
            description=description.strip(),
            default_classification=default_classification,
            status=SpaceStatus.ACTIVE,
            version=1,
            created_at=now,
            created_by=actor_id,
            updated_at=now,
            updated_by=actor_id,
        )

    def edit(
        self,
        *,
        display_name: str | None,
        description: str | None,
        default_classification: DataClassification | None,
        expected_version: int,
        actor_id: UUID,
        now: datetime,
    ) -> KnowledgeSpace:
        if self.status is SpaceStatus.ARCHIVED:
            raise DomainRuleViolation("archived spaces cannot be edited")
        if self.version != expected_version:
            raise DomainRuleViolation("space version does not match")
        next_name = self.display_name if display_name is None else display_name.strip()
        if not next_name:
            raise DomainRuleViolation("space display name is required")
        return replace(
            self,
            display_name=next_name,
            description=self.description if description is None else description.strip(),
            default_classification=(
                self.default_classification
                if default_classification is None
                else default_classification
            ),
            version=self.version + 1,
            updated_at=now,
            updated_by=actor_id,
        )

    def archive(self, *, expected_version: int, actor_id: UUID, now: datetime) -> KnowledgeSpace:
        if self.version != expected_version:
            raise DomainRuleViolation("space version does not match")
        if self.status is SpaceStatus.ARCHIVED:
            return self
        return replace(
            self,
            status=SpaceStatus.ARCHIVED,
            version=self.version + 1,
            updated_at=now,
            updated_by=actor_id,
            archived_at=now,
        )


@dataclass(frozen=True, slots=True)
class SpaceMember:
    id: UUID
    tenant_id: UUID
    space_id: UUID
    subject_type: ActorType
    subject_id: UUID
    roles: frozenset[Role]
    clearance: DataClassification
    status: MembershipStatus
    version: int

    def revoke(self) -> SpaceMember:
        if self.status is MembershipStatus.REVOKED:
            return self
        return replace(self, status=MembershipStatus.REVOKED, version=self.version + 1)
