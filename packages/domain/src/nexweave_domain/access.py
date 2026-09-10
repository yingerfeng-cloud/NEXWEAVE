"""Pure identity, role and classification authorization vocabulary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from nexweave_domain.states import DataClassification


class ActorType(StrEnum):
    USER = "USER"
    SERVICE = "SERVICE"


class Role(StrEnum):
    PLATFORM_ADMIN = "platform_admin"
    TENANT_ADMIN = "tenant_admin"
    SPACE_ADMIN = "space_admin"
    KNOWLEDGE_ENGINEER = "knowledge_engineer"
    REVIEWER = "reviewer"
    PUBLISHER = "publisher"
    CONSUMER = "consumer"
    AUDITOR = "auditor"
    SERVICE = "service"


ROLE_ACTIONS: dict[Role, frozenset[str]] = {
    Role.PLATFORM_ADMIN: frozenset(
        {
            "tenant.manage",
            "identity.manage",
            "space.create",
            "space.read",
            "member.read",
            "governance.manage",
            "audit.read",
            "diagnostics.read",
            "workflow.read",
            "workflow.reconcile",
            "source.read",
            "source.download",
            "schema.read",
            "schema.edit",
            "schema.validate",
            "schema.publish",
            "pack.read",
            "pack.install",
            "pack.rollback",
            "compile.create",
            "compile.read",
            "compile.control",
            "knowledge.read",
            "claim.read",
            "conflict.read",
            "conflict.resolve",
            "review.policy.manage",
            "review.create",
            "review.read",
            "review.act",
            "page.read",
            "page.edit",
            "page.comment",
            "quality.manage",
            "quality.run",
            "quality.read",
            "release.create",
            "release.read",
            "release.publish",
            "release.switch",
            "release.deprecate",
            "query.release",
            "query.answer.read",
            "graph.read",
        }
    ),
    Role.TENANT_ADMIN: frozenset(
        {
            "identity.manage",
            "space.create",
            "space.read",
            "space.edit",
            "space.archive",
            "member.grant",
            "member.revoke",
            "member.read",
            "governance.manage",
            "audit.read",
            "object.upload",
            "object.download",
            "workflow.create",
            "workflow.read",
            "workflow.control",
            "workflow.review",
            "workflow.reconcile",
            "source.upload",
            "source.read",
            "source.download",
            "source.parse",
            "source.invalidate",
            "source.archive",
            "schema.read",
            "schema.edit",
            "schema.validate",
            "schema.publish",
            "pack.read",
            "pack.install",
            "pack.rollback",
            "compile.create",
            "compile.read",
            "compile.control",
            "knowledge.read",
            "claim.read",
            "conflict.read",
            "conflict.resolve",
            "review.policy.manage",
            "review.create",
            "review.read",
            "review.act",
            "page.read",
            "page.edit",
            "page.comment",
            "quality.manage",
            "quality.run",
            "quality.read",
            "release.create",
            "release.read",
            "release.publish",
            "release.switch",
            "release.deprecate",
            "query.release",
            "query.answer.read",
            "graph.read",
        }
    ),
    Role.SPACE_ADMIN: frozenset(
        {
            "space.read",
            "space.edit",
            "space.archive",
            "member.grant",
            "member.revoke",
            "member.read",
            "governance.manage",
            "audit.read",
            "object.upload",
            "object.download",
            "workflow.create",
            "workflow.read",
            "workflow.control",
            "workflow.review",
            "source.upload",
            "source.read",
            "source.download",
            "source.parse",
            "source.invalidate",
            "source.archive",
            "schema.read",
            "schema.edit",
            "schema.validate",
            "pack.read",
            "pack.install",
            "pack.rollback",
            "compile.create",
            "compile.read",
            "compile.control",
            "knowledge.read",
            "claim.read",
            "conflict.read",
            "conflict.resolve",
            "review.policy.manage",
            "review.create",
            "review.read",
            "review.act",
            "page.read",
            "page.edit",
            "page.comment",
            "quality.manage",
            "quality.run",
            "quality.read",
            "release.create",
            "release.read",
            "release.switch",
            "release.deprecate",
            "query.release",
            "query.answer.read",
            "graph.read",
        }
    ),
    Role.KNOWLEDGE_ENGINEER: frozenset(
        {
            "space.read",
            "object.upload",
            "object.download",
            "workflow.create",
            "workflow.read",
            "workflow.control",
            "source.upload",
            "source.read",
            "source.download",
            "source.parse",
            "source.invalidate",
            "source.archive",
            "schema.read",
            "schema.edit",
            "schema.validate",
            "pack.read",
            "compile.create",
            "compile.read",
            "compile.control",
            "knowledge.read",
            "claim.read",
            "conflict.read",
            "review.create",
            "review.read",
            "review.act",
            "page.read",
            "page.edit",
            "page.comment",
            "quality.manage",
            "quality.run",
            "quality.read",
            "release.create",
            "release.read",
        }
    ),
    Role.REVIEWER: frozenset(
        {
            "space.read",
            "object.download",
            "workflow.read",
            "workflow.review",
            "source.read",
            "schema.read",
            "schema.validate",
            "compile.read",
            "knowledge.read",
            "claim.read",
            "conflict.read",
            "review.read",
            "review.act",
            "page.read",
            "page.comment",
            "quality.run",
            "quality.read",
            "release.read",
        }
    ),
    Role.PUBLISHER: frozenset(
        {
            "space.read",
            "object.download",
            "workflow.read",
            "workflow.review",
            "source.read",
            "schema.read",
            "schema.publish",
            "compile.read",
            "knowledge.read",
            "claim.read",
            "conflict.read",
            "review.read",
            "review.act",
            "page.read",
            "quality.read",
            "release.read",
            "release.publish",
            "release.switch",
            "release.deprecate",
            "query.release",
            "query.answer.read",
            "graph.read",
        }
    ),
    Role.CONSUMER: frozenset(
        {
            "space.read",
            "object.download",
            "workflow.read",
            "release.read",
            "query.release",
            "query.answer.read",
            "graph.read",
        }
    ),
    Role.AUDITOR: frozenset(
        {
            "space.read",
            "member.read",
            "audit.read",
            "object.download",
            "workflow.read",
            "source.read",
            "compile.read",
            "knowledge.read",
            "claim.read",
            "conflict.read",
            "review.read",
            "page.read",
            "quality.read",
            "release.read",
            "query.answer.read",
        }
    ),
    Role.SERVICE: frozenset(),
}


CLASSIFICATION_LEVEL: dict[DataClassification, int] = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.CONFIDENTIAL: 2,
    DataClassification.HIGHLY_RESTRICTED: 3,
}


@dataclass(frozen=True, slots=True)
class Principal:
    actor_type: ActorType
    actor_id: UUID
    tenant_id: UUID
    subject: str
    audience: tuple[str, ...]
    tenant_roles: frozenset[Role]
    clearance: DataClassification
    token_id: str


@dataclass(frozen=True, slots=True)
class AuthorizationRequest:
    action: str
    resource_tenant_id: UUID
    resource_space_id: UUID | None = None
    member_roles: frozenset[Role] = frozenset()
    membership_active: bool = False
    classification: DataClassification = DataClassification.INTERNAL
    resource_archived: bool = False


@dataclass(frozen=True, slots=True)
class AuthorizationDecision:
    allowed: bool
    reason: str


def authorize(principal: Principal, request: AuthorizationRequest) -> AuthorizationDecision:
    """Evaluate default-deny RBAC+ABAC without infrastructure dependencies."""
    if principal.tenant_id != request.resource_tenant_id:
        return AuthorizationDecision(False, "TENANT_MISMATCH")
    if "nexweave-api" not in principal.audience:
        return AuthorizationDecision(False, "AUDIENCE_MISMATCH")
    if CLASSIFICATION_LEVEL[principal.clearance] < CLASSIFICATION_LEVEL[request.classification]:
        return AuthorizationDecision(False, "CLASSIFICATION_DENIED")

    roles = set(principal.tenant_roles)
    if request.resource_space_id is not None:
        tenant_override = bool(roles.intersection({Role.PLATFORM_ADMIN, Role.TENANT_ADMIN}))
        if request.membership_active:
            roles.update(request.member_roles)
        elif not tenant_override:
            return AuthorizationDecision(False, "SPACE_MEMBERSHIP_REQUIRED")

    if request.resource_archived and request.action not in {"space.read", "audit.read"}:
        return AuthorizationDecision(False, "RESOURCE_ARCHIVED")

    if any(request.action in ROLE_ACTIONS.get(role, frozenset()) for role in roles):
        return AuthorizationDecision(True, "ALLOWED")
    return AuthorizationDecision(False, "ACTION_NOT_GRANTED")
