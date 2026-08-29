from dataclasses import replace
from datetime import UTC, datetime

import pytest

from nexweave_domain import (
    ActorType,
    AuthorizationRequest,
    DataClassification,
    DomainRuleViolation,
    KnowledgeSpace,
    Principal,
    Role,
    SpaceStatus,
    authorize,
    new_uuid7,
)


def principal(*roles: Role, audience: tuple[str, ...] = ("nexweave-api",)) -> Principal:
    return Principal(
        actor_type=ActorType.USER,
        actor_id=new_uuid7(),
        tenant_id=new_uuid7(),
        subject="tester",
        audience=audience,
        tenant_roles=frozenset(roles),
        clearance=DataClassification.CONFIDENTIAL,
        token_id=str(new_uuid7()),
    )


def test_authorization_is_default_deny_and_checks_audience_tenant_and_clearance() -> None:
    actor = principal(Role.TENANT_ADMIN)
    unknown_action = authorize(
        actor, AuthorizationRequest(action="unknown", resource_tenant_id=actor.tenant_id)
    )
    wrong_tenant = authorize(
        actor, AuthorizationRequest(action="space.create", resource_tenant_id=new_uuid7())
    )
    high_classification = authorize(
        actor,
        AuthorizationRequest(
            action="space.create",
            resource_tenant_id=actor.tenant_id,
            classification=DataClassification.HIGHLY_RESTRICTED,
        ),
    )
    wrong_audience_actor = principal(Role.TENANT_ADMIN, audience=("another-service",))
    wrong_audience = authorize(
        wrong_audience_actor,
        AuthorizationRequest(
            action="space.create", resource_tenant_id=wrong_audience_actor.tenant_id
        ),
    )

    assert (unknown_action.allowed, unknown_action.reason) == (False, "ACTION_NOT_GRANTED")
    assert wrong_tenant.reason == "TENANT_MISMATCH"
    assert high_classification.reason == "CLASSIFICATION_DENIED"
    assert wrong_audience.reason == "AUDIENCE_MISMATCH"


def test_space_access_requires_active_membership_and_archived_resources_reject_writes() -> None:
    actor = principal()
    space_id = new_uuid7()
    request = AuthorizationRequest(
        action="space.read",
        resource_tenant_id=actor.tenant_id,
        resource_space_id=space_id,
        member_roles=frozenset({Role.CONSUMER}),
        membership_active=False,
    )
    assert authorize(actor, request).reason == "SPACE_MEMBERSHIP_REQUIRED"
    assert authorize(actor, replace(request, membership_active=True)).allowed

    space_admin = principal(Role.TENANT_ADMIN)
    archived = authorize(
        space_admin,
        AuthorizationRequest(
            action="space.edit",
            resource_tenant_id=space_admin.tenant_id,
            resource_space_id=space_id,
            resource_archived=True,
        ),
    )
    assert archived.reason == "RESOURCE_ARCHIVED"


def test_consumer_cannot_read_draft_source_material() -> None:
    actor = principal()
    decision = authorize(
        actor,
        AuthorizationRequest(
            action="source.read",
            resource_tenant_id=actor.tenant_id,
            resource_space_id=new_uuid7(),
            member_roles=frozenset({Role.CONSUMER}),
            membership_active=True,
        ),
    )

    assert (decision.allowed, decision.reason) == (False, "ACTION_NOT_GRANTED")


def test_knowledge_space_enforces_slug_version_and_soft_archive() -> None:
    now, actor_id = datetime.now(UTC), new_uuid7()
    with pytest.raises(DomainRuleViolation):
        KnowledgeSpace.create(
            space_id=new_uuid7(),
            tenant_id=new_uuid7(),
            organization_id=new_uuid7(),
            slug="Invalid Slug",
            display_name="Space",
            description="",
            default_classification=DataClassification.INTERNAL,
            actor_id=actor_id,
            now=now,
        )

    space = KnowledgeSpace.create(
        space_id=new_uuid7(),
        tenant_id=new_uuid7(),
        organization_id=new_uuid7(),
        slug="quality-space",
        display_name="Quality Space",
        description="Trusted",
        default_classification=DataClassification.INTERNAL,
        actor_id=actor_id,
        now=now,
    )
    with pytest.raises(DomainRuleViolation, match="version"):
        space.edit(
            display_name="Changed",
            description=None,
            default_classification=None,
            expected_version=2,
            actor_id=actor_id,
            now=now,
        )
    archived = space.archive(expected_version=1, actor_id=actor_id, now=now)
    assert archived.status is SpaceStatus.ARCHIVED
    assert archived.version == 2
    with pytest.raises(DomainRuleViolation, match="archived"):
        archived.edit(
            display_name="Changed",
            description=None,
            default_classification=None,
            expected_version=2,
            actor_id=actor_id,
            now=now,
        )
