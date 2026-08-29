"""PostgreSQL adapter for M1 identity, workspace, governance and object metadata."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import UUID

from opentelemetry import metrics
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.database import Database
from nexweave_api.errors import ApiProblem, AuthenticationFailed
from nexweave_api.identity import LocalDevIdentityProvider
from nexweave_application import StoredObjectInfo, canonical_request_hash
from nexweave_domain import (
    ActorType,
    AuthorizationRequest,
    DataClassification,
    DomainRuleViolation,
    KnowledgeSpace,
    MembershipStatus,
    Principal,
    Role,
    ScanStatus,
    SpaceStatus,
    authorize,
    new_uuid7,
)

JsonDict = dict[str, Any]
Mutation = Callable[[AsyncConnection], Awaitable[JsonDict]]
METER = metrics.get_meter("nexweave.repository")
AUDIT_COUNTER = METER.create_counter("nexweave.audit.records")
OUTBOX_COUNTER = METER.create_counter("nexweave.outbox.events")


@dataclass(frozen=True, slots=True)
class SpaceSecurityFacts:
    tenant_id: UUID
    space_id: UUID
    classification: DataClassification
    archived: bool
    member_roles: frozenset[Role]
    membership_active: bool


def _json_value(value: Any) -> JsonDict:
    return cast(JsonDict, json.loads(json.dumps(dict(value), default=str)))


def _space_from_mapping(row: Any) -> KnowledgeSpace:
    return KnowledgeSpace(
        id=row["id"],
        tenant_id=row["tenant_id"],
        organization_id=row["organization_id"],
        slug=row["slug"],
        display_name=row["display_name"],
        description=row["description"],
        default_classification=DataClassification(row["default_classification"]),
        status=SpaceStatus(row["status"]),
        version=row["version"],
        created_at=row["created_at"],
        created_by=row["created_by"],
        updated_at=row["updated_at"],
        updated_by=row["updated_by"],
        archived_at=row["archived_at"],
    )


def _space_dict(space: KnowledgeSpace) -> JsonDict:
    return _json_value(
        {
            "id": space.id,
            "tenant_id": space.tenant_id,
            "organization_id": space.organization_id,
            "slug": space.slug,
            "display_name": space.display_name,
            "description": space.description,
            "default_classification": space.default_classification.value,
            "status": space.status.value,
            "version": space.version,
            "created_at": space.created_at,
            "created_by": space.created_by,
            "updated_at": space.updated_at,
            "updated_by": space.updated_by,
            "archived_at": space.archived_at,
        }
    )


class PlatformRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    async def bootstrap_local_development(self, *, tenant_slug: str, subject: str) -> Principal:
        """Create an idempotent synthetic local tenant/admin in a real database."""
        issuer = LocalDevIdentityProvider.issuer
        async with self._database.engine.begin() as connection:
            tenant_row = (
                (
                    await connection.execute(
                        text("SELECT id FROM tenants WHERE slug = :slug"), {"slug": tenant_slug}
                    )
                )
                .mappings()
                .first()
            )
            if tenant_row is None:
                tenant_id, actor_id, organization_id = new_uuid7(), new_uuid7(), new_uuid7()
                now = datetime.now(UTC)
                await connection.execute(
                    text(
                        "INSERT INTO tenants "
                        "(id, slug, display_name, status, version, created_at, created_by, "
                        "updated_at, updated_by) VALUES "
                        "(:id, :slug, :name, 'ACTIVE', 1, :now, :actor, :now, :actor)"
                    ),
                    {
                        "id": tenant_id,
                        "slug": tenant_slug,
                        "name": "NEXWEAVE Local Development",
                        "now": now,
                        "actor": actor_id,
                    },
                )
                await connection.execute(
                    text(
                        "INSERT INTO organizations "
                        "(id, tenant_id, slug, display_name, status, version, created_at, created_by, "
                        "updated_at, updated_by) VALUES "
                        "(:id, :tenant, 'default', 'Default Organization', 'ACTIVE', 1, :now, "
                        ":actor, :now, :actor)"
                    ),
                    {"id": organization_id, "tenant": tenant_id, "now": now, "actor": actor_id},
                )
                await connection.execute(
                    text(
                        "INSERT INTO user_identities "
                        "(id, tenant_id, issuer, subject, display_name, status, clearance, version, "
                        "created_at, created_by, updated_at, updated_by) VALUES "
                        "(:id, :tenant, :issuer, :subject, 'Local Administrator', 'ACTIVE', "
                        "'HIGHLY_RESTRICTED', 1, :now, :id, :now, :id)"
                    ),
                    {
                        "id": actor_id,
                        "tenant": tenant_id,
                        "issuer": issuer,
                        "subject": subject,
                        "now": now,
                    },
                )
                for role in (Role.TENANT_ADMIN, Role.PLATFORM_ADMIN):
                    await connection.execute(
                        text(
                            "INSERT INTO tenant_role_assignments "
                            "(id, tenant_id, subject_type, user_identity_id, role, status, version, "
                            "created_at, created_by, updated_at, updated_by) VALUES "
                            "(:id, :tenant, 'USER', :actor, :role, 'ACTIVE', 1, :now, :actor, "
                            ":now, :actor)"
                        ),
                        {
                            "id": new_uuid7(),
                            "tenant": tenant_id,
                            "actor": actor_id,
                            "role": role.value,
                            "now": now,
                        },
                    )
            else:
                tenant_id = tenant_row["id"]
                actor_row = (
                    (
                        await connection.execute(
                            text(
                                "SELECT id FROM user_identities "
                                "WHERE tenant_id = :tenant AND issuer = :issuer AND subject = :subject"
                            ),
                            {"tenant": tenant_id, "issuer": issuer, "subject": subject},
                        )
                    )
                    .mappings()
                    .first()
                )
                if actor_row is None:
                    raise ApiProblem(
                        409,
                        "VERSION_CONFLICT",
                        "Local identity conflict",
                        "The configured local tenant exists without the configured local identity.",
                    )
                actor_id = actor_row["id"]
        return await self.get_local_principal(subject)

    async def get_local_principal(self, subject: str) -> Principal:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, tenant_id, subject, clearance FROM user_identities "
                            "WHERE issuer = :issuer AND subject = :subject AND status = 'ACTIVE'"
                        ),
                        {"issuer": LocalDevIdentityProvider.issuer, "subject": subject},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise AuthenticationFailed("The local development identity is not provisioned.")
            roles = await self._tenant_roles(
                connection, row["tenant_id"], ActorType.USER, row["id"]
            )
        return Principal(
            actor_type=ActorType.USER,
            actor_id=row["id"],
            tenant_id=row["tenant_id"],
            subject=row["subject"],
            audience=("nexweave-api",),
            tenant_roles=roles,
            clearance=DataClassification(row["clearance"]),
            token_id=str(new_uuid7()),
        )

    async def resolve_principal(self, verified: Principal) -> Principal:
        table = "user_identities" if verified.actor_type is ActorType.USER else "service_identities"
        subject_column = "subject" if verified.actor_type is ActorType.USER else "client_id"
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            f"SELECT id, tenant_id, {subject_column} AS subject, clearance, status "  # noqa: S608
                            f"FROM {table} WHERE id = :id AND tenant_id = :tenant"  # noqa: S608
                        ),
                        {"id": verified.actor_id, "tenant": verified.tenant_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None or row["status"] != "ACTIVE" or row["subject"] != verified.subject:
                raise AuthenticationFailed("The verified identity is disabled or not provisioned.")
            roles = await self._tenant_roles(
                connection, verified.tenant_id, verified.actor_type, verified.actor_id
            )
        return replace(
            verified,
            tenant_roles=roles,
            clearance=DataClassification(row["clearance"]),
        )

    async def _tenant_roles(
        self, connection: AsyncConnection, tenant_id: UUID, actor_type: ActorType, actor_id: UUID
    ) -> frozenset[Role]:
        column = "user_identity_id" if actor_type is ActorType.USER else "service_identity_id"
        rows = (
            await connection.execute(
                text(
                    f"SELECT role FROM tenant_role_assignments WHERE tenant_id = :tenant "  # noqa: S608
                    f"AND subject_type = :subject_type AND {column} = :actor "  # noqa: S608
                    "AND status = 'ACTIVE'"
                ),
                {"tenant": tenant_id, "subject_type": actor_type.value, "actor": actor_id},
            )
        ).scalars()
        return frozenset(Role(value) for value in rows)

    async def list_users(self, principal: Principal) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, tenant_id, issuer, subject, display_name, status, clearance, "
                            "version, created_at, created_by, updated_at, updated_by "
                            "FROM user_identities WHERE tenant_id = :tenant ORDER BY display_name, id"
                        ),
                        {"tenant": principal.tenant_id},
                    )
                )
                .mappings()
                .all()
            )
            result = []
            for row in rows:
                roles = await self._tenant_roles(
                    connection, principal.tenant_id, ActorType.USER, row["id"]
                )
                result.append(
                    _json_value(
                        {
                            **row,
                            "tenant_roles": sorted(role.value for role in roles),
                        }
                    )
                )
            return result

    async def list_organizations(self, principal: Principal) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, tenant_id, slug, display_name, status, version, "
                            "created_at, created_by, updated_at, updated_by "
                            "FROM organizations WHERE tenant_id = :tenant ORDER BY display_name, id"
                        ),
                        {"tenant": principal.tenant_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def create_user(
        self,
        *,
        principal: Principal,
        payload: Mapping[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        async def mutation(connection: AsyncConnection) -> JsonDict:
            now, user_id = datetime.now(UTC), new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO user_identities "
                    "(id, tenant_id, issuer, subject, display_name, status, clearance, version, "
                    "created_at, created_by, updated_at, updated_by) VALUES "
                    "(:id, :tenant, :issuer, :subject, :name, 'ACTIVE', :clearance, 1, "
                    ":now, :actor, :now, :actor)"
                ),
                {
                    "id": user_id,
                    "tenant": principal.tenant_id,
                    "issuer": payload["issuer"],
                    "subject": payload["subject"],
                    "name": payload["display_name"],
                    "clearance": payload["clearance"],
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            for role in sorted(set(payload.get("tenant_roles", ()))):
                await connection.execute(
                    text(
                        "INSERT INTO tenant_role_assignments "
                        "(id, tenant_id, subject_type, user_identity_id, role, status, version, "
                        "created_at, created_by, updated_at, updated_by) VALUES "
                        "(:id, :tenant, 'USER', :subject, :role, 'ACTIVE', 1, :now, :actor, "
                        ":now, :actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "subject": user_id,
                        "role": role,
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            body = _json_value(
                {
                    **payload,
                    "id": user_id,
                    "tenant_id": principal.tenant_id,
                    "status": "ACTIVE",
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="identity.manage",
                resource_type="User",
                resource_id=user_id,
                space_id=None,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "CREATE"},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.user.created.v1",
                aggregate_type="User",
                aggregate_id=user_id,
                aggregate_version=1,
                space_id=None,
                trace_id=trace_id,
                payload={
                    "entity_kind": "USER",
                    "entity_id": user_id,
                    "space_id": None,
                    "version": 1,
                    "status": "ACTIVE",
                    "change": "CREATED",
                    "checksum": None,
                },
            )
            return body

        return await self._idempotent(
            principal=principal,
            operation="user.create",
            key=idempotency_key,
            request=payload,
            mutation=mutation,
        )

    async def create_service_identity(
        self,
        *,
        principal: Principal,
        payload: Mapping[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        credential_ref = payload.get("credential_ref")
        if credential_ref is not None and not str(credential_ref).startswith(
            ("env://", "vault://", "secret://", "kms://")
        ):
            raise ApiProblem(
                422,
                "VALIDATION_ERROR",
                "Invalid credential reference",
                "Credentials must use an approved Secret Provider reference.",
            )

        async def mutation(connection: AsyncConnection) -> JsonDict:
            now, service_id = datetime.now(UTC), new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO service_identities "
                    "(id, tenant_id, client_id, display_name, status, clearance, credential_ref, "
                    "version, created_at, created_by, updated_at, updated_by) VALUES "
                    "(:id, :tenant, :client_id, :name, 'ACTIVE', :clearance, :credential_ref, 1, "
                    ":now, :actor, :now, :actor)"
                ),
                {
                    "id": service_id,
                    "tenant": principal.tenant_id,
                    "client_id": payload["client_id"],
                    "name": payload["display_name"],
                    "clearance": payload["clearance"],
                    "credential_ref": credential_ref,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            for audience in sorted(set(payload["audiences"])):
                await connection.execute(
                    text(
                        "INSERT INTO service_identity_audiences "
                        "(tenant_id, service_identity_id, audience) VALUES "
                        "(:tenant, :service, :audience)"
                    ),
                    {
                        "tenant": principal.tenant_id,
                        "service": service_id,
                        "audience": audience,
                    },
                )
            for role in sorted(set(payload.get("tenant_roles", ()))):
                await connection.execute(
                    text(
                        "INSERT INTO tenant_role_assignments "
                        "(id, tenant_id, subject_type, service_identity_id, role, status, version, "
                        "created_at, created_by, updated_at, updated_by) VALUES "
                        "(:id, :tenant, 'SERVICE', :subject, :role, 'ACTIVE', 1, :now, :actor, "
                        ":now, :actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "subject": service_id,
                        "role": role,
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            body = _json_value(
                {
                    **payload,
                    "id": service_id,
                    "tenant_id": principal.tenant_id,
                    "status": "ACTIVE",
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="identity.manage",
                resource_type="ServiceIdentity",
                resource_id=service_id,
                space_id=None,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "CREATE", "audiences": payload["audiences"]},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.service_identity.created.v1",
                aggregate_type="ServiceIdentity",
                aggregate_id=service_id,
                aggregate_version=1,
                space_id=None,
                trace_id=trace_id,
                payload={
                    "entity_kind": "SERVICE_IDENTITY",
                    "entity_id": service_id,
                    "space_id": None,
                    "version": 1,
                    "status": "ACTIVE",
                    "change": "CREATED",
                    "checksum": None,
                },
            )
            return body

        return await self._idempotent(
            principal=principal,
            operation="service_identity.create",
            key=idempotency_key,
            request=payload,
            mutation=mutation,
        )

    async def list_service_identities(self, principal: Principal) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, tenant_id, client_id, display_name, status, clearance, "
                            "credential_ref, version, created_at, created_by, updated_at, updated_by "
                            "FROM service_identities "
                            "WHERE tenant_id = :tenant ORDER BY display_name, id"
                        ),
                        {"tenant": principal.tenant_id},
                    )
                )
                .mappings()
                .all()
            )
            result: list[JsonDict] = []
            for row in rows:
                audiences = list(
                    (
                        await connection.execute(
                            text(
                                "SELECT audience FROM service_identity_audiences "
                                "WHERE tenant_id = :tenant AND service_identity_id = :service "
                                "ORDER BY audience"
                            ),
                            {"tenant": principal.tenant_id, "service": row["id"]},
                        )
                    ).scalars()
                )
                roles = await self._tenant_roles(
                    connection, principal.tenant_id, ActorType.SERVICE, row["id"]
                )
                result.append(
                    _json_value(
                        {
                            **row,
                            "audiences": audiences,
                            "tenant_roles": sorted(role.value for role in roles),
                        }
                    )
                )
        return result

    async def get_space_facts(self, space_id: UUID, principal: Principal) -> SpaceSecurityFacts:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT tenant_id, id, default_classification, status "
                            "FROM knowledge_spaces WHERE id = :id"
                        ),
                        {"id": space_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Space not found", "The space is unavailable."
                )
            member_column = (
                "user_identity_id"
                if principal.actor_type is ActorType.USER
                else "service_identity_id"
            )
            member = (
                (
                    await connection.execute(
                        text(
                            f"SELECT id, status FROM space_members WHERE tenant_id = :tenant "  # noqa: S608
                            f"AND space_id = :space AND subject_type = :subject_type "  # noqa: S608
                            f"AND {member_column} = :actor ORDER BY version DESC LIMIT 1"  # noqa: S608
                        ),
                        {
                            "tenant": row["tenant_id"],
                            "space": space_id,
                            "subject_type": principal.actor_type.value,
                            "actor": principal.actor_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            roles: frozenset[Role] = frozenset()
            if member is not None and member["status"] == "ACTIVE":
                role_rows = (
                    await connection.execute(
                        text(
                            "SELECT role FROM space_member_roles WHERE tenant_id = :tenant "
                            "AND space_id = :space AND space_member_id = :member"
                        ),
                        {"tenant": row["tenant_id"], "space": space_id, "member": member["id"]},
                    )
                ).scalars()
                roles = frozenset(Role(value) for value in role_rows)
        return SpaceSecurityFacts(
            tenant_id=row["tenant_id"],
            space_id=space_id,
            classification=DataClassification(row["default_classification"]),
            archived=row["status"] == "ARCHIVED",
            member_roles=roles,
            membership_active=member is not None and member["status"] == "ACTIVE",
        )

    async def authorize_space(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        action: str,
        trace_id: str,
        classification: DataClassification | None = None,
    ) -> SpaceSecurityFacts:
        facts = await self.get_space_facts(space_id, principal)
        decision = authorize(
            principal,
            AuthorizationRequest(
                action=action,
                resource_tenant_id=facts.tenant_id,
                resource_space_id=facts.space_id,
                member_roles=facts.member_roles,
                membership_active=facts.membership_active,
                classification=classification or facts.classification,
                resource_archived=facts.archived,
            ),
        )
        if not decision.allowed:
            await self.record_denial(
                principal=principal,
                action=action,
                resource_type="KnowledgeSpace",
                resource_id=space_id,
                space_id=space_id if facts.tenant_id == principal.tenant_id else None,
                trace_id=trace_id,
                reason=decision.reason,
            )
            status = 404 if decision.reason == "TENANT_MISMATCH" else 403
            code = "RESOURCE_NOT_FOUND" if status == 404 else "ACCESS_DENIED"
            raise ApiProblem(status, code, "Access denied", "The requested action is not allowed.")
        return facts

    async def authorize_tenant(self, *, principal: Principal, action: str, trace_id: str) -> None:
        decision = authorize(
            principal,
            AuthorizationRequest(action=action, resource_tenant_id=principal.tenant_id),
        )
        if not decision.allowed:
            await self.record_denial(
                principal=principal,
                action=action,
                resource_type="Tenant",
                resource_id=principal.tenant_id,
                space_id=None,
                trace_id=trace_id,
                reason=decision.reason,
            )
            raise ApiProblem(403, "ACCESS_DENIED", "Access denied", "The action is not allowed.")

    async def record_denial(
        self,
        *,
        principal: Principal,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        space_id: UUID | None,
        trace_id: str,
        reason: str,
    ) -> None:
        async with self._database.engine.begin() as connection:
            await self._insert_audit(
                connection,
                principal=principal,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="DENIED",
                metadata={"reason": reason},
            )

    async def _insert_audit(
        self,
        connection: AsyncConnection,
        *,
        principal: Principal,
        action: str,
        resource_type: str,
        resource_id: UUID | None,
        space_id: UUID | None,
        trace_id: str,
        outcome: str,
        metadata: Mapping[str, Any],
    ) -> None:
        await connection.execute(
            text(
                "INSERT INTO audit_logs "
                "(id, tenant_id, space_id, actor_type, actor_id, action, resource_type, "
                "resource_id, trace_id, correlation_id, outcome, metadata) VALUES "
                "(:id, :tenant, :space, :actor_type, :actor, :action, :resource_type, "
                ":resource_id, :trace, :correlation, :outcome, CAST(:metadata AS jsonb))"
            ),
            {
                "id": new_uuid7(),
                "tenant": principal.tenant_id,
                "space": space_id,
                "actor_type": principal.actor_type.value,
                "actor": principal.actor_id,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "trace": trace_id,
                "correlation": new_uuid7(),
                "outcome": outcome,
                "metadata": json.dumps(metadata, default=str),
            },
        )
        AUDIT_COUNTER.add(1, {"outcome": outcome, "action": action})

    async def _insert_outbox(
        self,
        connection: AsyncConnection,
        *,
        principal: Principal,
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        aggregate_version: int,
        space_id: UUID | None,
        trace_id: str,
        payload: Mapping[str, Any],
        correlation_id: UUID | None = None,
        causation_id: UUID | None = None,
    ) -> None:
        await connection.execute(
            text(
                "INSERT INTO outbox_events "
                "(id, tenant_id, space_id, event_type, schema_version, aggregate_type, "
                "aggregate_id, aggregate_version, correlation_id, causation_id, trace_id, payload) VALUES "
                "(:id, :tenant, :space, :event_type, '1.0', :aggregate_type, :aggregate_id, "
                ":aggregate_version, :correlation, :causation, :trace, CAST(:payload AS jsonb))"
            ),
            {
                "id": new_uuid7(),
                "tenant": principal.tenant_id,
                "space": space_id,
                "event_type": event_type,
                "aggregate_type": aggregate_type,
                "aggregate_id": aggregate_id,
                "aggregate_version": aggregate_version,
                "correlation": correlation_id or new_uuid7(),
                "causation": causation_id,
                "trace": trace_id,
                "payload": json.dumps(payload, default=str),
            },
        )
        OUTBOX_COUNTER.add(1, {"event_type": event_type})

    async def _idempotent(
        self,
        *,
        principal: Principal,
        operation: str,
        key: str,
        request: Mapping[str, Any],
        mutation: Mutation,
    ) -> JsonDict:
        request_hash = canonical_request_hash(request)
        try:
            async with self._database.engine.begin() as connection:
                existing = (
                    (
                        await connection.execute(
                            text(
                                "SELECT request_hash, response_body FROM idempotency_records "
                                "WHERE tenant_id = :tenant AND actor_id = :actor "
                                "AND operation = :operation AND idempotency_key = :key"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "actor": principal.actor_id,
                                "operation": operation,
                                "key": key,
                            },
                        )
                    )
                    .mappings()
                    .first()
                )
                if existing is not None:
                    if existing["request_hash"] != request_hash:
                        raise ApiProblem(
                            409,
                            "IDEMPOTENCY_KEY_REUSED",
                            "Idempotency key reused",
                            "The key was already used with a different request.",
                        )
                    return dict(existing["response_body"])
                body = await mutation(connection)
                await connection.execute(
                    text(
                        "INSERT INTO idempotency_records "
                        "(id, tenant_id, actor_id, operation, idempotency_key, request_hash, "
                        "response_status, response_body, resource_id, expires_at, created_by) VALUES "
                        "(:id, :tenant, :actor, :operation, :key, :request_hash, 200, "
                        "CAST(:body AS jsonb), :resource_id, :expires_at, :actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "actor": principal.actor_id,
                        "operation": operation,
                        "key": key,
                        "request_hash": request_hash,
                        "body": json.dumps(body, default=str),
                        "resource_id": body.get("id"),
                        "expires_at": datetime.now(UTC) + timedelta(hours=24),
                    },
                )
                return body
        except IntegrityError as exc:
            raise ApiProblem(
                409,
                "VERSION_CONFLICT",
                "Resource conflict",
                "A resource with the same governed identity already exists.",
            ) from exc

    async def create_space(
        self,
        *,
        principal: Principal,
        idempotency_key: str,
        trace_id: str,
        organization_id: UUID,
        slug: str,
        display_name: str,
        description: str,
        default_classification: DataClassification,
    ) -> JsonDict:
        request = {
            "organization_id": organization_id,
            "slug": slug,
            "display_name": display_name,
            "description": description,
            "default_classification": default_classification.value,
        }

        async def mutation(connection: AsyncConnection) -> JsonDict:
            organization = (
                await connection.execute(
                    text(
                        "SELECT id FROM organizations WHERE id = :id AND tenant_id = :tenant "
                        "AND status = 'ACTIVE'"
                    ),
                    {"id": organization_id, "tenant": principal.tenant_id},
                )
            ).first()
            if organization is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Organization not found",
                    "The organization is unavailable in this tenant.",
                )
            now, space_id = datetime.now(UTC), new_uuid7()
            try:
                space = KnowledgeSpace.create(
                    space_id=space_id,
                    tenant_id=principal.tenant_id,
                    organization_id=organization_id,
                    slug=slug,
                    display_name=display_name,
                    description=description,
                    default_classification=default_classification,
                    actor_id=principal.actor_id,
                    now=now,
                )
            except DomainRuleViolation as exc:
                raise ApiProblem(422, "VALIDATION_ERROR", "Invalid space", str(exc)) from exc
            await connection.execute(
                text(
                    "INSERT INTO knowledge_spaces "
                    "(id, tenant_id, organization_id, slug, display_name, description, "
                    "default_classification, status, version, created_at, created_by, updated_at, "
                    "updated_by) VALUES (:id, :tenant, :organization, :slug, :name, :description, "
                    ":classification, 'ACTIVE', 1, :now, :actor, :now, :actor)"
                ),
                {
                    "id": space.id,
                    "tenant": space.tenant_id,
                    "organization": space.organization_id,
                    "slug": space.slug,
                    "name": space.display_name,
                    "description": space.description,
                    "classification": space.default_classification.value,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            if principal.actor_type is ActorType.USER:
                await self._grant_creator_membership(connection, principal, space.id, now)
            await self._insert_audit(
                connection,
                principal=principal,
                action="space.create",
                resource_type="KnowledgeSpace",
                resource_id=space.id,
                space_id=space.id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"version": 1},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.space.created.v1",
                aggregate_type="KnowledgeSpace",
                aggregate_id=space.id,
                aggregate_version=1,
                space_id=space.id,
                trace_id=trace_id,
                payload={
                    "space_id": space.id,
                    "status": "ACTIVE",
                    "version": 1,
                    "change": "CREATED",
                },
            )
            return _space_dict(space)

        return await self._idempotent(
            principal=principal,
            operation="space.create",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def _grant_creator_membership(
        self,
        connection: AsyncConnection,
        principal: Principal,
        space_id: UUID,
        now: datetime,
    ) -> None:
        member_id = new_uuid7()
        await connection.execute(
            text(
                "INSERT INTO space_members "
                "(id, tenant_id, space_id, subject_type, user_identity_id, clearance, status, "
                "version, created_at, created_by, updated_at, updated_by) VALUES "
                "(:id, :tenant, :space, 'USER', :actor, :clearance, 'ACTIVE', 1, :now, :actor, "
                ":now, :actor)"
            ),
            {
                "id": member_id,
                "tenant": principal.tenant_id,
                "space": space_id,
                "actor": principal.actor_id,
                "clearance": principal.clearance.value,
                "now": now,
            },
        )
        await connection.execute(
            text(
                "INSERT INTO space_member_roles (tenant_id, space_id, space_member_id, role) "
                "VALUES (:tenant, :space, :member, 'space_admin')"
            ),
            {"tenant": principal.tenant_id, "space": space_id, "member": member_id},
        )

    async def list_spaces(self, principal: Principal) -> list[JsonDict]:
        tenant_admin = bool(
            principal.tenant_roles.intersection({Role.PLATFORM_ADMIN, Role.TENANT_ADMIN})
        )
        async with self._database.engine.connect() as connection:
            if tenant_admin:
                statement = text(
                    "SELECT * FROM knowledge_spaces WHERE tenant_id = :tenant ORDER BY created_at, id"
                )
                params = {"tenant": principal.tenant_id}
            else:
                actor_column = (
                    "user_identity_id"
                    if principal.actor_type is ActorType.USER
                    else "service_identity_id"
                )
                statement = text(
                    f"SELECT s.* FROM knowledge_spaces s JOIN space_members m "  # noqa: S608
                    "ON m.tenant_id = s.tenant_id AND m.space_id = s.id "
                    f"WHERE s.tenant_id = :tenant AND m.{actor_column} = :actor "  # noqa: S608
                    "AND m.status = 'ACTIVE' ORDER BY s.created_at, s.id"
                )
                params = {"tenant": principal.tenant_id, "actor": principal.actor_id}
            rows = (await connection.execute(statement, params)).mappings().all()
        return [_space_dict(_space_from_mapping(row)) for row in rows]

    async def get_space(self, space_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM knowledge_spaces WHERE id = :id"), {"id": space_id}
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Space not found", "The space is unavailable."
            )
        return _space_dict(_space_from_mapping(row))

    async def update_space(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
        display_name: str | None,
        description: str | None,
        default_classification: DataClassification | None,
    ) -> JsonDict:
        request = {
            "space_id": space_id,
            "expected_version": expected_version,
            "display_name": display_name,
            "description": description,
            "default_classification": (
                default_classification.value if default_classification is not None else None
            ),
        }

        async def mutation(connection: AsyncConnection) -> JsonDict:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM knowledge_spaces WHERE id = :id FOR UPDATE"),
                        {"id": space_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Space not found", "The space is unavailable."
                )
            try:
                updated = _space_from_mapping(row).edit(
                    display_name=display_name,
                    description=description,
                    default_classification=default_classification,
                    expected_version=expected_version,
                    actor_id=principal.actor_id,
                    now=datetime.now(UTC),
                )
            except DomainRuleViolation as exc:
                code, status = (
                    ("PRECONDITION_FAILED", 412)
                    if "version" in str(exc)
                    else ("STATE_TRANSITION_NOT_ALLOWED", 409)
                )
                raise ApiProblem(status, code, "Space update rejected", str(exc)) from exc
            await connection.execute(
                text(
                    "UPDATE knowledge_spaces SET display_name = :name, description = :description, "
                    "default_classification = :classification, version = :version, "
                    "updated_at = :updated_at, updated_by = :updated_by WHERE id = :id"
                ),
                {
                    "name": updated.display_name,
                    "description": updated.description,
                    "classification": updated.default_classification.value,
                    "version": updated.version,
                    "updated_at": updated.updated_at,
                    "updated_by": updated.updated_by,
                    "id": updated.id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="space.edit",
                resource_type="KnowledgeSpace",
                resource_id=space_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"version": updated.version},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.space.updated.v1",
                aggregate_type="KnowledgeSpace",
                aggregate_id=space_id,
                aggregate_version=updated.version,
                space_id=space_id,
                trace_id=trace_id,
                payload={
                    "space_id": space_id,
                    "status": updated.status.value,
                    "version": updated.version,
                    "change": "UPDATED",
                },
            )
            return _space_dict(updated)

        return await self._idempotent(
            principal=principal,
            operation=f"space.update:{space_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def archive_space(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        request = {"space_id": space_id, "expected_version": expected_version}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM knowledge_spaces WHERE id = :id FOR UPDATE"),
                        {"id": space_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Space not found", "The space is unavailable."
                )
            try:
                archived = _space_from_mapping(row).archive(
                    expected_version=expected_version,
                    actor_id=principal.actor_id,
                    now=datetime.now(UTC),
                )
            except DomainRuleViolation as exc:
                raise ApiProblem(
                    412, "PRECONDITION_FAILED", "Space archive rejected", str(exc)
                ) from exc
            await connection.execute(
                text(
                    "UPDATE knowledge_spaces SET status = 'ARCHIVED', version = :version, "
                    "archived_at = :archived_at, updated_at = :updated_at, updated_by = :updated_by "
                    "WHERE id = :id"
                ),
                {
                    "version": archived.version,
                    "archived_at": archived.archived_at,
                    "updated_at": archived.updated_at,
                    "updated_by": archived.updated_by,
                    "id": archived.id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="space.archive",
                resource_type="KnowledgeSpace",
                resource_id=space_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"version": archived.version},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.space.archived.v1",
                aggregate_type="KnowledgeSpace",
                aggregate_id=space_id,
                aggregate_version=archived.version,
                space_id=space_id,
                trace_id=trace_id,
                payload={
                    "space_id": space_id,
                    "status": "ARCHIVED",
                    "version": archived.version,
                    "change": "ARCHIVED",
                },
            )
            return _space_dict(archived)

        return await self._idempotent(
            principal=principal,
            operation=f"space.archive:{space_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def grant_member(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        subject_id: UUID,
        subject_type: ActorType,
        roles: tuple[Role, ...],
        clearance: DataClassification,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        if not roles or any(role in {Role.PLATFORM_ADMIN, Role.TENANT_ADMIN} for role in roles):
            raise ApiProblem(
                422,
                "VALIDATION_ERROR",
                "Invalid space role",
                "Space memberships require at least one space-scoped role.",
            )
        request = {
            "space_id": space_id,
            "subject_id": subject_id,
            "subject_type": subject_type.value,
            "roles": sorted(role.value for role in roles),
            "clearance": clearance.value,
        }

        async def mutation(connection: AsyncConnection) -> JsonDict:
            identity_table = (
                "user_identities" if subject_type is ActorType.USER else "service_identities"
            )
            identity = (
                await connection.execute(
                    text(
                        f"SELECT id FROM {identity_table} WHERE id = :id AND tenant_id = :tenant "  # noqa: S608
                        "AND status = 'ACTIVE'"
                    ),
                    {"id": subject_id, "tenant": principal.tenant_id},
                )
            ).first()
            if identity is None:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Identity not found", "The subject is unavailable."
                )
            subject_column = (
                "user_identity_id" if subject_type is ActorType.USER else "service_identity_id"
            )
            existing = (
                (
                    await connection.execute(
                        text(
                            f"SELECT * FROM space_members WHERE tenant_id = :tenant AND space_id = :space "  # noqa: S608
                            f"AND subject_type = :subject_type AND {subject_column} = :subject "  # noqa: S608
                            "ORDER BY version DESC LIMIT 1 FOR UPDATE"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": space_id,
                            "subject_type": subject_type.value,
                            "subject": subject_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            now = datetime.now(UTC)
            if existing is None:
                member_id, version, created_at, created_by = new_uuid7(), 1, now, principal.actor_id
                await connection.execute(
                    text(
                        f"INSERT INTO space_members "  # noqa: S608
                        f"(id, tenant_id, space_id, subject_type, {subject_column}, clearance, "  # noqa: S608
                        "status, version, created_at, created_by, updated_at, updated_by) VALUES "
                        "(:id, :tenant, :space, :subject_type, :subject, :clearance, 'ACTIVE', 1, "
                        ":now, :actor, :now, :actor)"
                    ),
                    {
                        "id": member_id,
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "subject_type": subject_type.value,
                        "subject": subject_id,
                        "clearance": clearance.value,
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            else:
                member_id, version = existing["id"], existing["version"] + 1
                created_at, created_by = existing["created_at"], existing["created_by"]
                await connection.execute(
                    text(
                        "UPDATE space_members SET clearance = :clearance, status = 'ACTIVE', "
                        "version = :version, revoked_at = NULL, updated_at = :now, updated_by = :actor "
                        "WHERE id = :id"
                    ),
                    {
                        "clearance": clearance.value,
                        "version": version,
                        "now": now,
                        "actor": principal.actor_id,
                        "id": member_id,
                    },
                )
                await connection.execute(
                    text("DELETE FROM space_member_roles WHERE space_member_id = :id"),
                    {"id": member_id},
                )
            for role in sorted(set(roles), key=str):
                await connection.execute(
                    text(
                        "INSERT INTO space_member_roles "
                        "(tenant_id, space_id, space_member_id, role) VALUES "
                        "(:tenant, :space, :member, :role)"
                    ),
                    {
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "member": member_id,
                        "role": role.value,
                    },
                )
            body = _json_value(
                {
                    "id": member_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": space_id,
                    "subject_type": subject_type.value,
                    "subject_id": subject_id,
                    "roles": sorted(role.value for role in set(roles)),
                    "clearance": clearance.value,
                    "status": MembershipStatus.ACTIVE.value,
                    "version": version,
                    "created_at": created_at,
                    "created_by": created_by,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                    "revoked_at": None,
                }
            )
            await self._membership_facts(connection, principal, trace_id, body, "GRANTED")
            return body

        return await self._idempotent(
            principal=principal,
            operation=f"membership.grant:{space_id}:{subject_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def _membership_facts(
        self,
        connection: AsyncConnection,
        principal: Principal,
        trace_id: str,
        body: JsonDict,
        change: str,
    ) -> None:
        space_id, subject_id = UUID(body["space_id"]), UUID(body["subject_id"])
        await self._insert_audit(
            connection,
            principal=principal,
            action="member.grant" if change == "GRANTED" else "member.revoke",
            resource_type="SpaceMember",
            resource_id=UUID(body["id"]),
            space_id=space_id,
            trace_id=trace_id,
            outcome="SUCCEEDED",
            metadata={
                "subject_id": str(subject_id),
                "policy_version": body["version"],
                "change": change,
            },
        )
        await self._insert_outbox(
            connection,
            principal=principal,
            event_type="io.nexweave.membership.changed.v1",
            aggregate_type="SpaceMember",
            aggregate_id=UUID(body["id"]),
            aggregate_version=body["version"],
            space_id=space_id,
            trace_id=trace_id,
            payload={
                "space_id": space_id,
                "subject_type": body["subject_type"],
                "subject_id": subject_id,
                "roles": body["roles"],
                "clearance": body["clearance"],
                "status": body["status"],
                "policy_version": body["version"],
            },
        )

    async def revoke_member(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        subject_id: UUID,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        request = {"space_id": space_id, "subject_id": subject_id}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT *, COALESCE(user_identity_id, service_identity_id) AS subject_id "
                            "FROM space_members WHERE tenant_id = :tenant AND space_id = :space "
                            "AND (user_identity_id = :subject OR service_identity_id = :subject) "
                            "ORDER BY version DESC LIMIT 1 FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id, "subject": subject_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Membership not found",
                    "The membership is unavailable.",
                )
            roles = list(
                (
                    await connection.execute(
                        text("SELECT role FROM space_member_roles WHERE space_member_id = :id"),
                        {"id": row["id"]},
                    )
                ).scalars()
            )
            now, version = (
                datetime.now(UTC),
                row["version"] + (0 if row["status"] == "REVOKED" else 1),
            )
            if row["status"] != "REVOKED":
                await connection.execute(
                    text(
                        "UPDATE space_members SET status = 'REVOKED', version = :version, "
                        "revoked_at = :now, updated_at = :now, updated_by = :actor WHERE id = :id"
                    ),
                    {"version": version, "now": now, "actor": principal.actor_id, "id": row["id"]},
                )
            body = _json_value(
                {
                    "id": row["id"],
                    "tenant_id": row["tenant_id"],
                    "space_id": row["space_id"],
                    "subject_type": row["subject_type"],
                    "subject_id": row["subject_id"],
                    "roles": sorted(roles),
                    "clearance": row["clearance"],
                    "status": "REVOKED",
                    "version": version,
                    "created_at": row["created_at"],
                    "created_by": row["created_by"],
                    "updated_at": now if row["status"] != "REVOKED" else row["updated_at"],
                    "updated_by": principal.actor_id
                    if row["status"] != "REVOKED"
                    else row["updated_by"],
                    "revoked_at": now if row["status"] != "REVOKED" else row["revoked_at"],
                }
            )
            await self._membership_facts(connection, principal, trace_id, body, "REVOKED")
            return body

        return await self._idempotent(
            principal=principal,
            operation=f"membership.revoke:{space_id}:{subject_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def list_members(self, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT m.*, COALESCE(m.user_identity_id, m.service_identity_id) AS subject_id, "
                            "ARRAY(SELECT r.role FROM space_member_roles r WHERE r.space_member_id = m.id "
                            "ORDER BY r.role) AS roles FROM space_members m "
                            "WHERE m.tenant_id = :tenant AND m.space_id = :space ORDER BY m.created_at, m.id"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [
            _json_value(
                {
                    "id": row["id"],
                    "tenant_id": row["tenant_id"],
                    "space_id": row["space_id"],
                    "subject_type": row["subject_type"],
                    "subject_id": row["subject_id"],
                    "roles": row["roles"],
                    "clearance": row["clearance"],
                    "status": row["status"],
                    "version": row["version"],
                    "created_at": row["created_at"],
                    "created_by": row["created_by"],
                    "updated_at": row["updated_at"],
                    "updated_by": row["updated_by"],
                    "revoked_at": row["revoked_at"],
                }
            )
            for row in rows
        ]

    async def list_audit_logs(self, principal: Principal) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT id, tenant_id, space_id, occurred_at, actor_type, actor_id, action, "
                            "resource_type, resource_id, trace_id, outcome, metadata FROM audit_logs "
                            "WHERE tenant_id = :tenant ORDER BY occurred_at DESC, id DESC"
                        ),
                        {"tenant": principal.tenant_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def create_governance_object(
        self,
        *,
        kind: str,
        principal: Principal,
        payload: Mapping[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        if kind == "model_profile":
            return await self._create_model_profile(principal, payload, idempotency_key, trace_id)
        if kind == "prompt_version":
            return await self._create_prompt_version(principal, payload, idempotency_key, trace_id)
        if kind == "connector_definition":
            return await self._create_connector_definition(
                principal, payload, idempotency_key, trace_id
            )
        raise ValueError(f"unknown governance object: {kind}")

    async def _create_model_profile(
        self, principal: Principal, payload: Mapping[str, Any], key: str, trace_id: str
    ) -> JsonDict:
        credential_ref = payload.get("credential_ref")
        if credential_ref is not None and not str(credential_ref).startswith(
            ("env://", "vault://", "secret://", "kms://")
        ):
            raise ApiProblem(
                422,
                "VALIDATION_ERROR",
                "Invalid credential reference",
                "Credentials must use an approved Secret Provider reference.",
            )
        if (
            payload.get("externally_hosted")
            and payload.get("maximum_classification") == "HIGHLY_RESTRICTED"
        ):
            raise ApiProblem(
                422,
                "SEMANTIC_POLICY_FAILED",
                "Model policy rejected",
                "Externally hosted models cannot receive highly restricted data.",
            )

        async def mutation(connection: AsyncConnection) -> JsonDict:
            now, object_id = datetime.now(UTC), new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO model_profiles "
                    "(id, tenant_id, space_id, name, provider, model_name, credential_ref, "
                    "externally_hosted, maximum_classification, config, status, version, created_at, "
                    "created_by, updated_at, updated_by) VALUES (:id, :tenant, :space, :name, "
                    ":provider, :model_name, :credential_ref, :externally_hosted, :classification, "
                    "CAST(:config AS jsonb), 'DRAFT', 1, :now, :actor, :now, :actor)"
                ),
                {
                    "id": object_id,
                    "tenant": principal.tenant_id,
                    "space": payload.get("space_id"),
                    "name": payload["name"],
                    "provider": payload["provider"],
                    "model_name": payload["model_name"],
                    "credential_ref": credential_ref,
                    "externally_hosted": payload.get("externally_hosted", False),
                    "classification": payload["maximum_classification"],
                    "config": json.dumps(payload.get("config", {})),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            body = _json_value(
                {
                    **payload,
                    "id": object_id,
                    "tenant_id": principal.tenant_id,
                    "status": "DRAFT",
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="governance.manage",
                resource_type="ModelProfile",
                resource_id=object_id,
                space_id=payload.get("space_id"),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"version": 1},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.model_profile.created.v1",
                aggregate_type="ModelProfile",
                aggregate_id=object_id,
                aggregate_version=1,
                space_id=payload.get("space_id"),
                trace_id=trace_id,
                payload={
                    "entity_kind": "MODEL_PROFILE",
                    "entity_id": object_id,
                    "space_id": payload.get("space_id"),
                    "version": 1,
                    "status": "DRAFT",
                    "change": "CREATED",
                    "checksum": None,
                },
            )
            return body

        return await self._idempotent(
            principal=principal,
            operation="model_profile.create",
            key=key,
            request=payload,
            mutation=mutation,
        )

    async def _create_prompt_version(
        self, principal: Principal, payload: Mapping[str, Any], key: str, trace_id: str
    ) -> JsonDict:
        checksum = f"sha256:{hashlib.sha256(str(payload['content']).encode()).hexdigest()}"

        async def mutation(connection: AsyncConnection) -> JsonDict:
            revision = (
                await connection.execute(
                    text(
                        "SELECT COALESCE(MAX(revision), 0) + 1 FROM prompt_versions "
                        "WHERE tenant_id = :tenant AND prompt_key = :key "
                        "AND space_id IS NOT DISTINCT FROM :space"
                    ),
                    {
                        "tenant": principal.tenant_id,
                        "key": payload["prompt_key"],
                        "space": payload.get("space_id"),
                    },
                )
            ).scalar_one()
            now, object_id = datetime.now(UTC), new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO prompt_versions "
                    "(id, tenant_id, space_id, prompt_key, revision, content, output_contract, "
                    "checksum, status, created_at, created_by) VALUES (:id, :tenant, :space, :key, "
                    ":revision, :content, CAST(:contract AS jsonb), :checksum, 'DRAFT', :now, :actor)"
                ),
                {
                    "id": object_id,
                    "tenant": principal.tenant_id,
                    "space": payload.get("space_id"),
                    "key": payload["prompt_key"],
                    "revision": revision,
                    "content": payload["content"],
                    "contract": json.dumps(payload.get("output_contract", {})),
                    "checksum": checksum,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            body = _json_value(
                {
                    **payload,
                    "id": object_id,
                    "tenant_id": principal.tenant_id,
                    "revision": revision,
                    "checksum": checksum,
                    "status": "DRAFT",
                    "created_at": now,
                    "created_by": principal.actor_id,
                }
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="governance.manage",
                resource_type="PromptVersion",
                resource_id=object_id,
                space_id=payload.get("space_id"),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"revision": revision, "checksum": checksum},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.prompt_version.created.v1",
                aggregate_type="PromptVersion",
                aggregate_id=object_id,
                aggregate_version=revision,
                space_id=payload.get("space_id"),
                trace_id=trace_id,
                payload={
                    "entity_kind": "PROMPT_VERSION",
                    "entity_id": object_id,
                    "space_id": payload.get("space_id"),
                    "version": revision,
                    "status": "DRAFT",
                    "change": "CREATED",
                    "checksum": checksum,
                },
            )
            return body

        return await self._idempotent(
            principal=principal,
            operation="prompt_version.create",
            key=key,
            request=payload,
            mutation=mutation,
        )

    async def _create_connector_definition(
        self, principal: Principal, payload: Mapping[str, Any], key: str, trace_id: str
    ) -> JsonDict:
        async def mutation(connection: AsyncConnection) -> JsonDict:
            now, object_id = datetime.now(UTC), new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO connector_definitions "
                    "(id, tenant_id, space_id, name, connector_type, config_schema, status, version, "
                    "created_at, created_by, updated_at, updated_by) VALUES (:id, :tenant, :space, "
                    ":name, :connector_type, CAST(:schema AS jsonb), 'DRAFT', 1, :now, :actor, "
                    ":now, :actor)"
                ),
                {
                    "id": object_id,
                    "tenant": principal.tenant_id,
                    "space": payload.get("space_id"),
                    "name": payload["name"],
                    "connector_type": payload["connector_type"],
                    "schema": json.dumps(payload.get("config_schema", {})),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            body = _json_value(
                {
                    **payload,
                    "id": object_id,
                    "tenant_id": principal.tenant_id,
                    "status": "DRAFT",
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="governance.manage",
                resource_type="ConnectorDefinition",
                resource_id=object_id,
                space_id=payload.get("space_id"),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"version": 1},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.connector_definition.created.v1",
                aggregate_type="ConnectorDefinition",
                aggregate_id=object_id,
                aggregate_version=1,
                space_id=payload.get("space_id"),
                trace_id=trace_id,
                payload={
                    "entity_kind": "CONNECTOR_DEFINITION",
                    "entity_id": object_id,
                    "space_id": payload.get("space_id"),
                    "version": 1,
                    "status": "DRAFT",
                    "change": "CREATED",
                    "checksum": None,
                },
            )
            return body

        return await self._idempotent(
            principal=principal,
            operation="connector_definition.create",
            key=key,
            request=payload,
            mutation=mutation,
        )

    async def list_governance_objects(self, kind: str, principal: Principal) -> list[JsonDict]:
        queries = {
            "model_profile": "SELECT * FROM model_profiles WHERE tenant_id = :tenant ORDER BY created_at, id",
            "prompt_version": "SELECT * FROM prompt_versions WHERE tenant_id = :tenant ORDER BY prompt_key, revision",
            "connector_definition": "SELECT * FROM connector_definitions WHERE tenant_id = :tenant ORDER BY created_at, id",
        }
        if kind not in queries:
            raise ValueError(f"unknown governance object: {kind}")
        async with self._database.engine.connect() as connection:
            rows = (
                (await connection.execute(text(queries[kind]), {"tenant": principal.tenant_id}))
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def create_upload_session(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: Mapping[str, Any],
        idempotency_key: str,
        trace_id: str,
        ttl_seconds: int,
    ) -> JsonDict:
        request = {"space_id": space_id, **payload}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            now, upload_id = datetime.now(UTC), new_uuid7()
            expires_at = now + timedelta(seconds=ttl_seconds)
            await connection.execute(
                text(
                    "INSERT INTO object_upload_sessions "
                    "(id, tenant_id, space_id, filename, content_type, expected_size, classification, "
                    "status, version, expires_at, created_at, created_by, updated_at, updated_by) "
                    "VALUES (:id, :tenant, :space, :filename, :content_type, :expected_size, "
                    ":classification, 'INITIATED', 1, :expires_at, :now, :actor, :now, :actor)"
                ),
                {
                    "id": upload_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "filename": payload["filename"],
                    "content_type": payload["content_type"],
                    "expected_size": payload["expected_size"],
                    "classification": payload["classification"],
                    "expires_at": expires_at,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            body = _json_value(
                {
                    "id": upload_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": space_id,
                    **payload,
                    "status": "INITIATED",
                    "version": 1,
                    "upload_url": f"/api/v1/object-uploads/{upload_id}/content",
                    "expires_at": expires_at,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="object.upload",
                resource_type="ObjectUploadSession",
                resource_id=upload_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "expected_size": payload["expected_size"],
                    "classification": payload["classification"],
                },
            )
            return body

        return await self._idempotent(
            principal=principal,
            operation=f"object_upload.create:{space_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def get_upload_session(self, upload_id: UUID) -> JsonDict:
        expired = False
        async with self._database.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM object_upload_sessions WHERE id = :id"),
                        {"id": upload_id},
                    )
                )
                .mappings()
                .first()
            )
            if (
                row is not None
                and row["status"] in {"INITIATED", "UPLOADING"}
                and row["expires_at"] <= datetime.now(UTC)
            ):
                await connection.execute(
                    text(
                        "UPDATE object_upload_sessions SET status = 'EXPIRED', "
                        "version = version + 1, updated_at = :now WHERE id = :id"
                    ),
                    {"id": upload_id, "now": datetime.now(UTC)},
                )
                expired = True
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Upload not found", "The upload session is unavailable."
            )
        result = _json_value(row)
        if expired:
            result.update({"status": "EXPIRED", "version": row["version"] + 1})
        return result

    async def complete_upload(
        self,
        *,
        principal: Principal,
        upload_id: UUID,
        info: StoredObjectInfo,
        filename: str,
        classification: DataClassification,
        scan_status: ScanStatus,
        trace_id: str,
    ) -> JsonDict:
        async with self._database.engine.begin() as connection:
            session = (
                (
                    await connection.execute(
                        text("SELECT * FROM object_upload_sessions WHERE id = :id FOR UPDATE"),
                        {"id": upload_id},
                    )
                )
                .mappings()
                .first()
            )
            if session is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Upload not found",
                    "The upload session is unavailable.",
                )
            if session["status"] == "COMPLETED":
                existing = (
                    (
                        await connection.execute(
                            text("SELECT * FROM managed_objects WHERE id = :id"), {"id": upload_id}
                        )
                    )
                    .mappings()
                    .one()
                )
                return _json_value(existing)
            if session["status"] not in {"INITIATED", "UPLOADING"}:
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Upload unavailable",
                    "The upload session is no longer writable.",
                )
            now = datetime.now(UTC)
            await connection.execute(
                text(
                    "INSERT INTO managed_objects "
                    "(id, tenant_id, space_id, upload_session_id, filename, object_key, "
                    "object_version_id, checksum, content_type, size, classification, scan_status, "
                    "version, created_at, created_by, updated_at, updated_by) VALUES "
                    "(:id, :tenant, :space, :upload, :filename, :key, "
                    ":version_id, :checksum, :content_type, :size, :classification, :scan_status, "
                    "1, :now, :actor, :now, :actor)"
                ),
                {
                    "id": upload_id,
                    "tenant": principal.tenant_id,
                    "space": session["space_id"],
                    "upload": upload_id,
                    "filename": filename,
                    "key": info.key,
                    "version_id": info.version_id,
                    "checksum": info.checksum_sha256,
                    "content_type": info.content_type,
                    "size": info.size,
                    "classification": classification.value,
                    "scan_status": scan_status.value,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await connection.execute(
                text(
                    "UPDATE object_upload_sessions SET status = 'COMPLETED', version = version + 1, "
                    "completed_object_id = :object, updated_at = :now, updated_by = :actor WHERE id = :id"
                ),
                {"object": upload_id, "now": now, "actor": principal.actor_id, "id": upload_id},
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="object.upload.complete",
                resource_type="ManagedObject",
                resource_id=upload_id,
                space_id=session["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED" if scan_status is ScanStatus.CLEAN else "FAILED",
                metadata={
                    "checksum": info.checksum_sha256,
                    "size": info.size,
                    "scan_status": scan_status.value,
                },
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.managed_object.stored.v1",
                aggregate_type="ManagedObject",
                aggregate_id=upload_id,
                aggregate_version=1,
                space_id=session["space_id"],
                trace_id=trace_id,
                payload={
                    "entity_kind": "MANAGED_OBJECT",
                    "entity_id": upload_id,
                    "space_id": session["space_id"],
                    "version": 1,
                    "status": scan_status.value,
                    "change": "STORED",
                    "checksum": info.checksum_sha256,
                },
            )
            return _json_value(
                {
                    "id": upload_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": session["space_id"],
                    "upload_session_id": upload_id,
                    "filename": filename,
                    "object_key": info.key,
                    "object_version_id": info.version_id,
                    "checksum": info.checksum_sha256,
                    "content_type": info.content_type,
                    "size": info.size,
                    "classification": classification.value,
                    "scan_status": scan_status.value,
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )

    async def get_managed_object(self, object_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM managed_objects WHERE id = :id"), {"id": object_id}
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Object not found", "The object is unavailable."
            )
        return _json_value(row)
