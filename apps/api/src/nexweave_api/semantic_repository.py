"""PostgreSQL M4 SchemaVersion service; Pack composition stays pure-domain."""

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_api.repository import JsonDict, _json_value
from nexweave_api.source_repository import SourceRepository
from nexweave_contracts import SemanticDeclarations
from nexweave_domain import (
    ActorType,
    DataClassification,
    Principal,
    Role,
    SemanticRuleViolation,
    analyze_compatibility,
    canonical_json,
    compose_declarations,
    new_uuid7,
    semver_satisfies,
    sha256_checksum,
    validate_stable_key,
    verify_pack,
    verify_signed_revocation_list,
)


class SemanticRepository(SourceRepository):
    async def register_domain_pack_trust_key(
        self,
        *,
        principal: Principal,
        payload: dict[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        if (
            payload["key_namespace"]
            in {
                "nexweave.io",
                "local.nexweave.io",
                "test.nexweave.io",
            }
            and Role.PLATFORM_ADMIN not in principal.tenant_roles
        ):
            raise ApiProblem(
                403,
                "PACK_NAMESPACE_DENIED",
                "Reserved Pack namespace denied",
                "Only a platform administrator can register a reserved namespace trust root.",
            )
        try:
            encoded = str(payload["public_key_base64url"])
            public_key = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        except (ValueError, binascii.Error) as exc:
            raise ApiProblem(
                422,
                "PACK_TRUST_KEY_INVALID",
                "Invalid Pack trust key",
                "The Ed25519 public key is not valid base64url.",
            ) from exc
        if len(public_key) != 32:
            raise ApiProblem(
                422,
                "PACK_TRUST_KEY_INVALID",
                "Invalid Pack trust key",
                "The Ed25519 public key must be exactly 32 bytes.",
            )
        fingerprint = sha256_checksum(public_key)
        key_id, now = new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            await connection.execute(
                text(
                    "INSERT INTO domain_pack_trust_keys "
                    "(id,tenant_id,key_id,key_namespace,algorithm,public_key,fingerprint,status,"
                    "valid_from,valid_until,version,created_at,created_by,updated_at,updated_by) "
                    "VALUES (:id,:tenant,:key_id,:namespace,'Ed25519',:public_key,:fingerprint,"
                    "'ACTIVE',:valid_from,:valid_until,1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": key_id,
                    "tenant": principal.tenant_id,
                    "key_id": payload["key_id"],
                    "namespace": payload["key_namespace"],
                    "public_key": public_key,
                    "fingerprint": fingerprint,
                    "valid_from": payload["valid_from"],
                    "valid_until": payload.get("valid_until"),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="governance.manage",
                resource_type="DomainPackTrustKey",
                resource_id=key_id,
                space_id=None,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "key_id": payload["key_id"],
                    "key_namespace": payload["key_namespace"],
                    "fingerprint": fingerprint,
                },
            )
            return _json_value(
                {
                    "id": key_id,
                    "tenant_id": principal.tenant_id,
                    "key_id": payload["key_id"],
                    "key_namespace": payload["key_namespace"],
                    "algorithm": "Ed25519",
                    "fingerprint": fingerprint,
                    "status": "ACTIVE",
                    "valid_from": payload["valid_from"],
                    "valid_until": payload.get("valid_until"),
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation="pack.trust-key.register",
            key=idempotency_key,
            request=payload,
            mutation=mutation,
        )

    async def register_domain_pack(
        self,
        *,
        principal: Principal,
        manifest: dict[str, Any],
        contents: dict[str, dict[str, Any]],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        metadata = dict(manifest["metadata"])
        signature = dict(manifest["security"]["signature"])
        files = {path: canonical_json(value) for path, value in contents.items()}
        async with self._database.engine.connect() as connection:
            trust = (
                (
                    await connection.execute(
                        text(
                            "SELECT public_key,key_namespace,valid_from,valid_until FROM domain_pack_trust_keys "
                            "WHERE tenant_id=:tenant AND key_id=:key_id AND status='ACTIVE'"
                        ),
                        {"tenant": principal.tenant_id, "key_id": signature["keyId"]},
                    )
                )
                .mappings()
                .first()
            )
            revoked = (
                await connection.execute(
                    text(
                        "SELECT 1 FROM domain_pack_revocations WHERE tenant_id=:tenant "
                        "AND key_id=:key_id LIMIT 1"
                    ),
                    {"tenant": principal.tenant_id, "key_id": signature["keyId"]},
                )
            ).first()
        now = datetime.now(UTC)
        if trust is None or revoked is not None:
            raise ApiProblem(
                403,
                "PACK_SIGNATURE_INVALID",
                "Pack trust rejected",
                "The Pack signing key is unknown or revoked.",
            )
        if trust["key_namespace"] != metadata["keyNamespace"]:
            raise ApiProblem(
                403,
                "PACK_NAMESPACE_DENIED",
                "Pack namespace denied",
                "The signing key does not own the declared key namespace.",
            )
        if now < trust["valid_from"] or (
            trust["valid_until"] is not None and now >= trust["valid_until"]
        ):
            raise ApiProblem(
                403,
                "PACK_SIGNATURE_INVALID",
                "Pack trust expired",
                "The Pack signing key is outside its validity window.",
            )
        compatibility = dict(manifest["compatibility"])
        if not semver_satisfies("1.4.0", str(compatibility["platform"])) or not semver_satisfies(
            "1.0.0", str(compatibility["semanticContract"])
        ):
            raise ApiProblem(
                409,
                "PACK_DEPENDENCY_CONFLICT",
                "Pack contract incompatible",
                "The Pack does not support this platform or semantic-contract version.",
            )
        verification = verify_pack(
            manifest=manifest, files=files, public_key=bytes(trust["public_key"])
        )
        async with self._database.engine.connect() as connection:
            artifact_revoked = (
                await connection.execute(
                    text(
                        "SELECT 1 FROM domain_pack_revocations WHERE tenant_id=:tenant "
                        "AND content_checksum=:checksum LIMIT 1"
                    ),
                    {
                        "tenant": principal.tenant_id,
                        "checksum": verification.content_checksum,
                    },
                )
            ).first()
        if artifact_revoked is not None:
            raise ApiProblem(
                403,
                "PACK_REVOKED",
                "Pack artifact revoked",
                "The exact signed Pack artifact has been revoked.",
            )
        self._validate_pack_owned_keys(contents, str(metadata["keyNamespace"]))
        pack_id, pack_version_id = new_uuid7(), new_uuid7()

        async def mutation(connection: AsyncConnection) -> JsonDict:
            existing_pack = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,publisher,key_namespace FROM domain_packs "
                            "WHERE tenant_id=:tenant AND pack_key=:pack_key FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "pack_key": metadata["id"]},
                    )
                )
                .mappings()
                .first()
            )
            resolved_pack_id = pack_id
            if existing_pack is None:
                await connection.execute(
                    text(
                        "INSERT INTO domain_packs "
                        "(id,tenant_id,pack_key,publisher,key_namespace,status,version,created_at,"
                        "created_by,updated_at,updated_by) VALUES "
                        "(:id,:tenant,:pack_key,:publisher,:namespace,'ACTIVE',1,:now,:actor,:now,:actor)"
                    ),
                    {
                        "id": pack_id,
                        "tenant": principal.tenant_id,
                        "pack_key": metadata["id"],
                        "publisher": metadata["publisher"],
                        "namespace": metadata["keyNamespace"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            else:
                if (
                    existing_pack["publisher"] != metadata["publisher"]
                    or existing_pack["key_namespace"] != metadata["keyNamespace"]
                ):
                    raise ApiProblem(
                        409,
                        "PACK_NAMESPACE_CONFLICT",
                        "Pack identity conflict",
                        "The Pack identity is already owned by another publisher or namespace.",
                    )
                resolved_pack_id = existing_pack["id"]
            await connection.execute(
                text(
                    "INSERT INTO domain_pack_versions "
                    "(id,tenant_id,domain_pack_id,pack_version,content_checksum,manifest,"
                    "signature_key_id,status,created_at,created_by) VALUES "
                    "(:id,:tenant,:pack,:version,:checksum,CAST(:manifest AS jsonb),:key_id,"
                    "'PUBLISHED',:now,:actor)"
                ),
                {
                    "id": pack_version_id,
                    "tenant": principal.tenant_id,
                    "pack": resolved_pack_id,
                    "version": metadata["version"],
                    "checksum": verification.content_checksum,
                    "manifest": json.dumps(manifest),
                    "key_id": verification.key_id,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            manifest_content = dict(manifest["content"])
            for content_key, descriptor in sorted(manifest_content.items()):
                path = str(descriptor["path"])
                await connection.execute(
                    text(
                        "INSERT INTO domain_pack_contents "
                        "(id,tenant_id,domain_pack_version_id,content_key,path,checksum,declaration,"
                        "created_at,created_by) VALUES "
                        "(:id,:tenant,:version,:content_key,:path,:checksum,CAST(:declaration AS jsonb),"
                        ":now,:actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "version": pack_version_id,
                        "content_key": content_key,
                        "path": path,
                        "checksum": descriptor["sha256"],
                        "declaration": json.dumps(contents[path]),
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            for dependency in manifest["compatibility"]["dependencies"]:
                await connection.execute(
                    text(
                        "INSERT INTO domain_pack_dependencies "
                        "(id,tenant_id,domain_pack_version_id,dependency_pack_key,requested_range,"
                        "created_at,created_by) VALUES "
                        "(:id,:tenant,:version,:pack_key,:version_range,:now,:actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "version": pack_version_id,
                        "pack_key": dependency["id"],
                        "version_range": dependency["versionRange"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="pack.publish",
                resource_type="DomainPackVersion",
                resource_id=pack_version_id,
                space_id=None,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "pack_key": metadata["id"],
                    "pack_version": metadata["version"],
                    "content_checksum": verification.content_checksum,
                    "signature_key_id": verification.key_id,
                },
            )
            return _json_value(
                {
                    "id": pack_version_id,
                    "tenant_id": principal.tenant_id,
                    "pack_key": metadata["id"],
                    "pack_version": metadata["version"],
                    "publisher": metadata["publisher"],
                    "key_namespace": metadata["keyNamespace"],
                    "content_checksum": verification.content_checksum,
                    "signature_key_id": verification.key_id,
                    "status": "PUBLISHED",
                    "created_at": now,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation="pack.register",
            key=idempotency_key,
            request={"manifest": manifest, "contents": contents},
            mutation=mutation,
        )

    async def import_pack_revocation_list(
        self,
        *,
        principal: Principal,
        document: dict[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        signature = dict(document["security"]["signature"])
        async with self._database.engine.connect() as connection:
            trust = (
                (
                    await connection.execute(
                        text(
                            "SELECT public_key,key_namespace FROM domain_pack_trust_keys "
                            "WHERE tenant_id=:tenant AND key_id=:key_id AND status='ACTIVE'"
                        ),
                        {"tenant": principal.tenant_id, "key_id": signature["keyId"]},
                    )
                )
                .mappings()
                .first()
            )
        if trust is None or trust["key_namespace"] != "nexweave.io":
            raise ApiProblem(
                403,
                "PACK_SIGNATURE_INVALID",
                "Revocation trust rejected",
                "Revocation lists require an active platform trust root.",
            )
        verification = verify_signed_revocation_list(
            document=document, public_key=bytes(trust["public_key"])
        )

        async def mutation(connection: AsyncConnection) -> JsonDict:
            imported_ids: list[str] = []
            for entry in document["revoked"]:
                version_id: UUID | None = None
                checksum = entry.get("contentChecksum")
                if entry.get("packId") is not None:
                    row = (
                        (
                            await connection.execute(
                                text(
                                    "SELECT pv.id FROM domain_pack_versions pv "
                                    "JOIN domain_packs p ON p.id=pv.domain_pack_id "
                                    "WHERE pv.tenant_id=:tenant AND p.pack_key=:pack_key "
                                    "AND pv.pack_version=:version AND pv.content_checksum=:checksum"
                                ),
                                {
                                    "tenant": principal.tenant_id,
                                    "pack_key": entry["packId"],
                                    "version": entry["version"],
                                    "checksum": checksum,
                                },
                            )
                        )
                        .mappings()
                        .first()
                    )
                    if row is None:
                        raise ApiProblem(
                            404,
                            "RESOURCE_NOT_FOUND",
                            "Revocation target not found",
                            "The exact PackVersion checksum is not registered in this tenant.",
                        )
                    version_id = row["id"]
                revoked_at = datetime.fromisoformat(str(entry["revokedAt"]).replace("Z", "+00:00"))
                revocation_id = new_uuid7()
                await connection.execute(
                    text(
                        "INSERT INTO domain_pack_revocations "
                        "(id,tenant_id,key_id,domain_pack_version_id,content_checksum,reason_code,"
                        "evidence_checksum,revoked_at,created_at,created_by) VALUES "
                        "(:id,:tenant,:key_id,:version_id,:checksum,:reason,:evidence,:revoked_at,"
                        ":now,:actor)"
                    ),
                    {
                        "id": revocation_id,
                        "tenant": principal.tenant_id,
                        "key_id": entry.get("keyId"),
                        "version_id": version_id,
                        "checksum": checksum,
                        "reason": entry["reasonCode"],
                        "evidence": verification.content_checksum,
                        "revoked_at": revoked_at,
                        "now": datetime.now(UTC),
                        "actor": principal.actor_id,
                    },
                )
                if entry.get("keyId") is not None:
                    await connection.execute(
                        text(
                            "UPDATE domain_pack_trust_keys SET status='REVOKED',version=version+1,"
                            "updated_at=:now,updated_by=:actor WHERE tenant_id=:tenant AND key_id=:key_id"
                        ),
                        {
                            "now": datetime.now(UTC),
                            "actor": principal.actor_id,
                            "tenant": principal.tenant_id,
                            "key_id": entry["keyId"],
                        },
                    )
                imported_ids.append(str(revocation_id))
            await self._insert_audit(
                connection,
                principal=principal,
                action="governance.manage",
                resource_type="DomainPackRevocationList",
                resource_id=UUID(imported_ids[0]),
                space_id=None,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "evidence_checksum": verification.content_checksum,
                    "entry_count": len(imported_ids),
                    "signing_key_id": verification.key_id,
                },
            )
            return {
                "evidence_checksum": verification.content_checksum,
                "signing_key_id": verification.key_id,
                "revocation_ids": imported_ids,
            }

        return await self._idempotent(
            principal=principal,
            operation="pack.revocation-list.import",
            key=idempotency_key,
            request=document,
            mutation=mutation,
        )

    @staticmethod
    def _validate_pack_owned_keys(contents: dict[str, dict[str, Any]], namespace: str) -> None:
        for declaration in contents.values():
            try:
                SemanticDeclarations.model_validate(declaration)
            except ValidationError as exc:
                raise SemanticRuleViolation(
                    "PACK_ARTIFACT_INVALID", "Pack semantic declarations violate the contract."
                ) from exc
            for section in (
                "types",
                "properties",
                "relations",
                "templates",
                "lintRules",
                "evaluationSuites",
                "ui",
            ):
                for item in declaration.get(section, ()):
                    validate_stable_key(str(item.get("key", "")), namespace=namespace)
                    SemanticRepository._validate_declarative_value(item.get("definition", {}))
            for item in declaration.get("ui", ()):
                definition = item.get("definition", {})
                if set(definition) - {
                    "icon",
                    "colorToken",
                    "form",
                    "list",
                    "semanticModel",
                    "helpText",
                }:
                    raise ApiProblem(
                        422,
                        "PACK_ARTIFACT_INVALID",
                        "Declarative UI invalid",
                        "The UI declaration contains a field outside the M4 allowlist.",
                    )

    @staticmethod
    def _validate_declarative_value(value: Any) -> None:
        forbidden = {
            "script",
            "javascript",
            "html",
            "css",
            "iframe",
            "url",
            "remote",
            "include",
            "macro",
            "expression",
            "handler",
            "onclick",
        }
        if isinstance(value, dict):
            for key, item in value.items():
                lowered = str(key).lower()
                if any(token in lowered for token in forbidden):
                    raise ApiProblem(
                        422,
                        "PACK_ARTIFACT_INVALID",
                        "Executable declaration rejected",
                        "Pack declarations cannot contain executable or remote content.",
                    )
                SemanticRepository._validate_declarative_value(item)
        elif isinstance(value, list):
            for item in value:
                SemanticRepository._validate_declarative_value(item)
        elif isinstance(value, str) and (
            value.strip().lower().startswith(("javascript:", "http://", "https://"))
            or "<script" in value.lower()
        ):
            raise ApiProblem(
                422,
                "PACK_ARTIFACT_INVALID",
                "Executable declaration rejected",
                "Pack declarations cannot contain executable or remote content.",
            )

    async def list_domain_pack_versions(self, *, principal: Principal) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT pv.id,pv.tenant_id,p.pack_key,p.publisher,p.key_namespace,"
                            "pv.pack_version,pv.content_checksum,pv.signature_key_id,pv.status,pv.created_at "
                            "FROM domain_pack_versions pv JOIN domain_packs p ON p.id=pv.domain_pack_id "
                            "WHERE pv.tenant_id=:tenant AND pv.status IN ('VALIDATED','PUBLISHED') "
                            "AND NOT EXISTS (SELECT 1 FROM domain_pack_revocations r "
                            "WHERE r.tenant_id=pv.tenant_id AND (r.domain_pack_version_id=pv.id "
                            "OR r.content_checksum=pv.content_checksum OR r.key_id=pv.signature_key_id)) "
                            "ORDER BY p.pack_key,pv.pack_version"
                        ),
                        {"tenant": principal.tenant_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def create_installation(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        domain_pack_version_id: UUID,
        schema_definition_id: UUID,
        requested_semantic_version: str,
        operation: str,
        previous_installation_id: UUID | None,
        workflow_task_id: UUID,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        installation_id, now = new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            target = (
                (
                    await connection.execute(
                        text(
                            "SELECT pv.id,pv.pack_version,wt.workflow_id FROM domain_pack_versions pv "
                            "JOIN workflow_tasks wt ON wt.tenant_id=pv.tenant_id "
                            "AND wt.space_id=:space AND wt.id=:task "
                            "JOIN schema_definitions sd ON sd.tenant_id=pv.tenant_id "
                            "AND sd.space_id=:space AND sd.id=:schema AND sd.status='ACTIVE' "
                            "WHERE pv.tenant_id=:tenant AND pv.id=:pack AND pv.status='PUBLISHED' "
                            "AND NOT EXISTS (SELECT 1 FROM domain_pack_revocations r "
                            "WHERE r.tenant_id=pv.tenant_id AND (r.domain_pack_version_id=pv.id "
                            "OR r.content_checksum=pv.content_checksum OR r.key_id=pv.signature_key_id)) "
                            "FOR SHARE"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": space_id,
                            "task": workflow_task_id,
                            "schema": schema_definition_id,
                            "pack": domain_pack_version_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            if target is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Pack or Schema unavailable",
                    "The exact PackVersion or target SchemaDefinition is unavailable.",
                )
            await connection.execute(
                text(
                    "INSERT INTO domain_pack_installations "
                    "(id,tenant_id,space_id,domain_pack_version_id,schema_definition_id,"
                    "requested_semantic_version,operation,previous_installation_id,workflow_task_id,"
                    "workflow_id,status,version,created_at,created_by,updated_at,updated_by) VALUES "
                    "(:id,:tenant,:space,:pack,:schema,:semantic_version,:operation,:previous,:task,"
                    ":workflow_id,'PLANNED',1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": installation_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "pack": domain_pack_version_id,
                    "schema": schema_definition_id,
                    "semantic_version": requested_semantic_version,
                    "operation": operation,
                    "previous": previous_installation_id,
                    "task": workflow_task_id,
                    "workflow_id": target["workflow_id"],
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="pack.install",
                resource_type="DomainPackInstallation",
                resource_id=installation_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "domain_pack_version_id": str(domain_pack_version_id),
                    "schema_definition_id": str(schema_definition_id),
                    "workflow_task_id": str(workflow_task_id),
                },
            )
            return _json_value(
                {
                    "id": installation_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": space_id,
                    "domain_pack_version_id": domain_pack_version_id,
                    "schema_definition_id": schema_definition_id,
                    "requested_semantic_version": requested_semantic_version,
                    "operation": operation,
                    "previous_installation_id": previous_installation_id,
                    "workflow_task_id": workflow_task_id,
                    "workflow_id": target["workflow_id"],
                    "run_id": None,
                    "candidate_schema_version_id": None,
                    "composition_report_id": None,
                    "status": "PLANNED",
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"pack.install:{space_id}",
            key=idempotency_key,
            request={
                "pack": str(domain_pack_version_id),
                "schema": str(schema_definition_id),
                "semantic_version": requested_semantic_version,
                "operation": operation,
                "previous": str(previous_installation_id) if previous_installation_id else None,
            },
            mutation=mutation,
        )

    async def mark_installation_started(
        self, *, installation_id: UUID, run_id: str, actor_id: UUID
    ) -> JsonDict:
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE domain_pack_installations SET run_id=:run,status='INSTALLING',"
                    "version=version+1,updated_at=:now,updated_by=:actor "
                    "WHERE id=:id AND status='PLANNED'"
                ),
                {
                    "run": run_id,
                    "now": datetime.now(UTC),
                    "actor": actor_id,
                    "id": installation_id,
                },
            )
        return await self.get_installation(installation_id=installation_id)

    async def get_installation(self, *, installation_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM domain_pack_installations WHERE id=:id"),
                        {"id": installation_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Pack installation not found",
                "The requested DomainPackInstallation is unavailable.",
            )
        return _json_value(dict(row))

    async def execute_pack_installation(
        self, *, installation_id: UUID, run_id: str, trace_id: str
    ) -> JsonDict:
        """Resolve, compose and persist one installation atomically and idempotently."""

        async with self._database.engine.begin() as connection:
            installation = (
                (
                    await connection.execute(
                        text("SELECT * FROM domain_pack_installations WHERE id=:id FOR UPDATE"),
                        {"id": installation_id},
                    )
                )
                .mappings()
                .first()
            )
            if installation is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Pack installation not found",
                    "The requested DomainPackInstallation is unavailable.",
                )
            if installation["status"] == "ACTIVE":
                return _json_value(dict(installation))
            if installation["status"] not in {"PLANNED", "INSTALLING", "ROLLING_BACK"}:
                raise ApiProblem(
                    409,
                    "PACK_INSTALLATION_STATE_CONFLICT",
                    "Pack installation state conflict",
                    "The installation cannot be executed from its current state.",
                )
            principal = Principal(
                actor_type=ActorType.SERVICE,
                actor_id=installation["created_by"],
                tenant_id=installation["tenant_id"],
                subject="domain-pack-install-workflow",
                audience=("nexweave-api",),
                tenant_roles=frozenset({Role.SERVICE}),
                clearance=DataClassification.INTERNAL,
                token_id=f"workflow:{run_id}",
            )
            operation = str(installation["operation"])
            if operation == "ROLLBACK":
                return await self._restore_installation_pointer(
                    connection,
                    installation=installation,
                    principal=principal,
                    run_id=run_id,
                    trace_id=trace_id,
                )
            active_rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT i.id,i.domain_pack_version_id,p.pack_key FROM domain_pack_installations i "
                            "JOIN domain_pack_versions pv ON pv.id=i.domain_pack_version_id "
                            "JOIN domain_packs p ON p.id=pv.domain_pack_id "
                            "WHERE i.tenant_id=:tenant AND i.space_id=:space "
                            "AND i.schema_definition_id=:schema AND i.status='ACTIVE'"
                        ),
                        {
                            "tenant": installation["tenant_id"],
                            "space": installation["space_id"],
                            "schema": installation["schema_definition_id"],
                        },
                    )
                )
                .mappings()
                .all()
            )
            target_pack = (
                await connection.execute(
                    text(
                        "SELECT p.pack_key FROM domain_pack_versions pv "
                        "JOIN domain_packs p ON p.id=pv.domain_pack_id "
                        "WHERE pv.tenant_id=:tenant AND pv.id=:id"
                    ),
                    {
                        "tenant": installation["tenant_id"],
                        "id": installation["domain_pack_version_id"],
                    },
                )
            ).scalar_one()
            roots: dict[str, UUID] = {
                str(row["pack_key"]): row["domain_pack_version_id"] for row in active_rows
            }
            if operation == "DISABLE":
                roots.pop(str(target_pack), None)
            else:
                roots[str(target_pack)] = installation["domain_pack_version_id"]
            packs, dependencies, input_rows = await self._resolve_pack_graph(
                connection, tenant_id=installation["tenant_id"], roots=roots
            )
            local = (
                await connection.execute(
                    text(
                        "SELECT local_declarations FROM schema_versions "
                        "WHERE tenant_id=:tenant AND space_id=:space "
                        "AND schema_definition_id=:schema ORDER BY created_at DESC,id DESC LIMIT 1"
                    ),
                    {
                        "tenant": installation["tenant_id"],
                        "space": installation["space_id"],
                        "schema": installation["schema_definition_id"],
                    },
                )
            ).scalar_one_or_none()
            packs["space-local"] = dict(local or {})
            dependencies["space-local"] = tuple(sorted(packs.keys() - {"space-local"}))
            composition = compose_declarations(packs=packs, dependencies=dependencies)
            previous = (
                (
                    await connection.execute(
                        text(
                            "SELECT normalized_snapshot,composition_checksum FROM schema_versions "
                            "WHERE tenant_id=:tenant AND space_id=:space AND schema_definition_id=:schema "
                            "AND status='PUBLISHED' ORDER BY published_at DESC,id DESC LIMIT 1"
                        ),
                        {
                            "tenant": installation["tenant_id"],
                            "space": installation["space_id"],
                            "schema": installation["schema_definition_id"],
                        },
                    )
                )
                .mappings()
                .first()
            )
            compatibility = analyze_compatibility(
                dict(previous["normalized_snapshot"]) if previous is not None else None,
                composition.normalized_snapshot,
            )
            version_id, report_id, now = new_uuid7(), new_uuid7(), datetime.now(UTC)
            input_checksum = sha256_checksum(
                canonical_json(
                    {
                        "packs": [
                            {"id": str(row["id"]), "checksum": row["content_checksum"]}
                            for row in input_rows
                        ],
                        "local": dict(local or {}),
                    }
                )
            )
            report = {
                "compatible": not compatibility.breaking,
                "classification": compatibility.classification,
                "resolvedPacks": [
                    {
                        "packKey": row["pack_key"],
                        "version": row["pack_version"],
                        "checksum": row["content_checksum"],
                    }
                    for row in input_rows
                ],
                "packOrder": list(composition.pack_order),
                "conflicts": [],
                "changes": list(compatibility.changes),
                "impact": {
                    "entities": [],
                    "relations": [],
                    "claims": [],
                    "pages": [],
                    "releases": [],
                },
                "migrationPreview": {
                    "mode": "M4_PREVIEW_ONLY",
                    "dslVersion": "nexweave.schema-migration/1alpha1",
                    "operations": list(compatibility.migration_operations),
                },
            }
            await connection.execute(
                text(
                    "INSERT INTO schema_versions "
                    "(id,tenant_id,space_id,schema_definition_id,semantic_version,status,"
                    "local_declarations,normalized_snapshot,content_checksum,composition_checksum,"
                    "canonicalization_algorithm,breaking_change,version,created_at,created_by,"
                    "updated_at,updated_by) VALUES "
                    "(:id,:tenant,:space,:schema,:semantic_version,'DRAFT',CAST(:local AS jsonb),"
                    "CAST(:snapshot AS jsonb),:content,:composition,'nexweave.semantic-compose/1',"
                    ":breaking,1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": version_id,
                    "tenant": installation["tenant_id"],
                    "space": installation["space_id"],
                    "schema": installation["schema_definition_id"],
                    "semantic_version": installation["requested_semantic_version"],
                    "local": json.dumps(dict(local or {})),
                    "snapshot": json.dumps(composition.normalized_snapshot),
                    "content": input_checksum,
                    "composition": composition.composition_checksum,
                    "breaking": compatibility.breaking,
                    "now": now,
                    "actor": installation["created_by"],
                },
            )
            await self._persist_semantic_snapshot(
                connection,
                principal=principal,
                space_id=installation["space_id"],
                schema_version_id=version_id,
                snapshot=composition.normalized_snapshot,
            )
            for index, row in enumerate(input_rows):
                await connection.execute(
                    text(
                        "INSERT INTO schema_version_pack_inputs "
                        "(id,tenant_id,space_id,schema_version_id,domain_pack_version_id,input_order,"
                        "content_checksum,created_at,created_by) VALUES "
                        "(:id,:tenant,:space,:schema_version,:pack_version,:input_order,:checksum,"
                        ":now,:actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": installation["tenant_id"],
                        "space": installation["space_id"],
                        "schema_version": version_id,
                        "pack_version": row["id"],
                        "input_order": index,
                        "checksum": row["content_checksum"],
                        "now": now,
                        "actor": installation["created_by"],
                    },
                )
            await connection.execute(
                text(
                    "INSERT INTO schema_composition_reports "
                    "(id,tenant_id,space_id,schema_version_id,input_checksum,result_checksum,report,"
                    "created_at,created_by) VALUES "
                    "(:id,:tenant,:space,:schema_version,:input,:result,CAST(:report AS jsonb),:now,:actor)"
                ),
                {
                    "id": report_id,
                    "tenant": installation["tenant_id"],
                    "space": installation["space_id"],
                    "schema_version": version_id,
                    "input": input_checksum,
                    "result": composition.composition_checksum,
                    "report": json.dumps(report),
                    "now": now,
                    "actor": installation["created_by"],
                },
            )
            for row in active_rows:
                if str(row["pack_key"]) == str(target_pack) and operation in {
                    "UPGRADE",
                    "DISABLE",
                }:
                    await connection.execute(
                        text(
                            "UPDATE domain_pack_installations SET status='DISABLED',version=version+1,"
                            "updated_at=:now,updated_by=:actor WHERE id=:id AND status='ACTIVE'"
                        ),
                        {"now": now, "actor": installation["created_by"], "id": row["id"]},
                    )
            await connection.execute(
                text(
                    "UPDATE domain_pack_installations SET status=:status,run_id=:run,"
                    "candidate_schema_version_id=:schema_version,composition_report_id=:report,"
                    "version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {
                    "run": run_id,
                    "status": "DISABLED" if operation == "DISABLE" else "ACTIVE",
                    "schema_version": version_id,
                    "report": report_id,
                    "now": now,
                    "actor": installation["created_by"],
                    "id": installation_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="pack.install" if operation != "ROLLBACK" else "pack.rollback",
                resource_type="DomainPackInstallation",
                resource_id=installation_id,
                space_id=installation["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "operation": operation,
                    "candidate_schema_version_id": str(version_id),
                    "composition_checksum": composition.composition_checksum,
                },
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.pack.installed.v1",
                aggregate_type="DomainPackInstallation",
                aggregate_id=installation_id,
                aggregate_version=int(installation["version"]) + 1,
                space_id=installation["space_id"],
                trace_id=trace_id,
                payload={
                    "installation_id": str(installation_id),
                    "domain_pack_version_id": str(installation["domain_pack_version_id"]),
                    "candidate_schema_version_id": str(version_id),
                    "composition_checksum": composition.composition_checksum,
                    "operation": operation,
                },
            )
        return await self.get_installation(installation_id=installation_id)

    async def _restore_installation_pointer(
        self,
        connection: AsyncConnection,
        *,
        installation: Any,
        principal: Principal,
        run_id: str,
        trace_id: str,
    ) -> JsonDict:
        target_id = installation["previous_installation_id"]
        target = (
            (
                await connection.execute(
                    text(
                        "SELECT * FROM domain_pack_installations WHERE tenant_id=:tenant "
                        "AND space_id=:space AND id=:id AND candidate_schema_version_id IS NOT NULL "
                        "FOR UPDATE"
                    ),
                    {
                        "tenant": installation["tenant_id"],
                        "space": installation["space_id"],
                        "id": target_id,
                    },
                )
            )
            .mappings()
            .first()
        )
        if target is None:
            raise ApiProblem(
                409,
                "PACK_INSTALLATION_STATE_CONFLICT",
                "Rollback target unavailable",
                "Rollback requires a completed historical installation in the same space.",
            )
        now = datetime.now(UTC)
        await connection.execute(
            text(
                "UPDATE domain_pack_installations SET status='DISABLED',version=version+1,"
                "updated_at=:now,updated_by=:actor WHERE tenant_id=:tenant AND space_id=:space "
                "AND schema_definition_id=:schema AND status='ACTIVE' AND id<>:target"
            ),
            {
                "now": now,
                "actor": installation["created_by"],
                "tenant": installation["tenant_id"],
                "space": installation["space_id"],
                "schema": installation["schema_definition_id"],
                "target": target_id,
            },
        )
        await connection.execute(
            text(
                "UPDATE domain_pack_installations SET status='ACTIVE',version=version+1,"
                "updated_at=:now,updated_by=:actor WHERE id=:id"
            ),
            {"now": now, "actor": installation["created_by"], "id": target_id},
        )
        await connection.execute(
            text(
                "UPDATE domain_pack_installations SET status='ROLLED_BACK',run_id=:run,"
                "candidate_schema_version_id=:schema_version,composition_report_id=:report,"
                "version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
            ),
            {
                "run": run_id,
                "schema_version": target["candidate_schema_version_id"],
                "report": target["composition_report_id"],
                "now": now,
                "actor": installation["created_by"],
                "id": installation["id"],
            },
        )
        await self._insert_audit(
            connection,
            principal=principal,
            action="pack.rollback",
            resource_type="DomainPackInstallation",
            resource_id=installation["id"],
            space_id=installation["space_id"],
            trace_id=trace_id,
            outcome="SUCCEEDED",
            metadata={
                "restored_installation_id": str(target_id),
                "candidate_schema_version_id": str(target["candidate_schema_version_id"]),
            },
        )
        await self._insert_outbox(
            connection,
            principal=principal,
            event_type="io.nexweave.pack.installed.v1",
            aggregate_type="DomainPackInstallation",
            aggregate_id=installation["id"],
            aggregate_version=int(installation["version"]) + 1,
            space_id=installation["space_id"],
            trace_id=trace_id,
            payload={
                "installation_id": str(installation["id"]),
                "domain_pack_version_id": str(target["domain_pack_version_id"]),
                "candidate_schema_version_id": str(target["candidate_schema_version_id"]),
                "composition_checksum": None,
                "operation": "ROLLBACK",
            },
        )
        refreshed = dict(installation)
        refreshed.update(
            {
                "status": "ROLLED_BACK",
                "run_id": run_id,
                "candidate_schema_version_id": target["candidate_schema_version_id"],
                "composition_report_id": target["composition_report_id"],
                "version": int(installation["version"]) + 1,
                "updated_at": now,
            }
        )
        return _json_value(refreshed)

    async def fail_pack_installation(
        self, *, installation_id: UUID, code: str, actor_id: UUID, trace_id: str
    ) -> None:
        async with self._database.engine.begin() as connection:
            failed = (
                (
                    await connection.execute(
                        text(
                            "UPDATE domain_pack_installations SET status='FAILED',version=version+1,"
                            "updated_at=:now,updated_by=:actor WHERE id=:id "
                            "AND status IN ('PLANNED','INSTALLING','ROLLING_BACK') "
                            "RETURNING tenant_id,space_id"
                        ),
                        {
                            "now": datetime.now(UTC),
                            "actor": actor_id,
                            "id": installation_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            if failed is None:
                return
            await self._insert_audit(
                connection,
                principal=Principal(
                    actor_type=ActorType.SERVICE,
                    actor_id=actor_id,
                    tenant_id=UUID(str(failed["tenant_id"])),
                    subject="domain-pack-install-workflow",
                    audience=("nexweave-api",),
                    tenant_roles=frozenset(),
                    clearance=DataClassification.INTERNAL,
                    token_id="temporal-activity",  # noqa: S106 - opaque audit subject, not a secret
                ),
                action="pack.install",
                resource_type="DomainPackInstallation",
                resource_id=installation_id,
                space_id=UUID(str(failed["space_id"])),
                trace_id=trace_id,
                outcome="FAILED",
                metadata={"error_code": code},
            )

    async def _resolve_pack_graph(
        self,
        connection: AsyncConnection,
        *,
        tenant_id: UUID,
        roots: dict[str, UUID],
    ) -> tuple[dict[str, dict[str, Any]], dict[str, tuple[str, ...]], list[Any]]:
        resolved: dict[str, Any] = {}
        edges_by_key: dict[str, tuple[str, ...]] = {}
        visiting: set[str] = set()

        async def resolve(pack_key: str, exact_id: UUID | None, requested_range: str) -> str:
            if pack_key in visiting:
                raise ApiProblem(
                    409,
                    "PACK_DEPENDENCY_CONFLICT",
                    "Pack dependency cycle",
                    "The Domain Pack dependency graph contains a cycle.",
                )
            if pack_key in resolved:
                row = resolved[pack_key]
                if not semver_satisfies(str(row["pack_version"]), requested_range):
                    raise ApiProblem(
                        409,
                        "PACK_DEPENDENCY_CONFLICT",
                        "Pack dependency conflict",
                        "Resolved PackVersion does not satisfy every requested range.",
                    )
                return str(row["node_key"])
            query = (
                "SELECT pv.id,p.pack_key,pv.pack_version,pv.content_checksum,pv.signature_key_id "
                "FROM domain_pack_versions pv JOIN domain_packs p ON p.id=pv.domain_pack_id "
                "WHERE pv.tenant_id=:tenant AND p.pack_key=:pack_key AND pv.status='PUBLISHED' "
                "AND NOT EXISTS (SELECT 1 FROM domain_pack_revocations r "
                "WHERE r.tenant_id=pv.tenant_id AND (r.domain_pack_version_id=pv.id "
                "OR r.content_checksum=pv.content_checksum OR r.key_id=pv.signature_key_id))"
            )
            params: dict[str, Any] = {"tenant": tenant_id, "pack_key": pack_key}
            if exact_id is not None:
                query += " AND pv.id=:exact_id"
                params["exact_id"] = exact_id
            candidates = (await connection.execute(text(query), params)).mappings().all()
            matching = [
                row
                for row in candidates
                if semver_satisfies(str(row["pack_version"]), requested_range)
            ]
            if not matching:
                raise ApiProblem(
                    409,
                    "PACK_DEPENDENCY_CONFLICT",
                    "Pack dependency unavailable",
                    "No trusted PackVersion satisfies the requested dependency range.",
                )
            matching.sort(key=lambda row: self._semver_sort_key(str(row["pack_version"])))
            selected = dict(matching[-1])
            node_key = (
                f"{selected['pack_key']}@{selected['pack_version']}#{selected['content_checksum']}"
            )
            selected["node_key"] = node_key
            resolved[pack_key] = selected
            visiting.add(pack_key)
            dependency_rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT dependency_pack_key,requested_range FROM domain_pack_dependencies "
                            "WHERE tenant_id=:tenant AND domain_pack_version_id=:version "
                            "ORDER BY dependency_pack_key"
                        ),
                        {"tenant": tenant_id, "version": selected["id"]},
                    )
                )
                .mappings()
                .all()
            )
            dependency_nodes = []
            for dependency in dependency_rows:
                dependency_nodes.append(
                    await resolve(
                        str(dependency["dependency_pack_key"]),
                        None,
                        str(dependency["requested_range"]),
                    )
                )
            visiting.remove(pack_key)
            edges_by_key[pack_key] = tuple(sorted(dependency_nodes))
            return node_key

        for pack_key, version_id in sorted(roots.items()):
            await resolve(pack_key, version_id, ">=0.0.0")
        packs: dict[str, dict[str, Any]] = {}
        dependencies: dict[str, tuple[str, ...]] = {}
        ordered_rows = sorted(resolved.values(), key=lambda row: str(row["node_key"]))
        for row in ordered_rows:
            declarations: dict[str, list[Any]] = {}
            content_rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT declaration FROM domain_pack_contents "
                            "WHERE tenant_id=:tenant AND domain_pack_version_id=:version "
                            "ORDER BY content_key"
                        ),
                        {"tenant": tenant_id, "version": row["id"]},
                    )
                )
                .scalars()
                .all()
            )
            for content in content_rows:
                for section, values in dict(content).items():
                    if not isinstance(values, list):
                        raise ApiProblem(
                            422,
                            "PACK_ARTIFACT_INVALID",
                            "Pack declaration invalid",
                            "Semantic declaration sections must contain arrays.",
                        )
                    declarations.setdefault(section, []).extend(values)
            packs[str(row["node_key"])] = declarations
            dependencies[str(row["node_key"])] = edges_by_key[str(row["pack_key"])]
        return packs, dependencies, ordered_rows

    @staticmethod
    def _semver_sort_key(value: str) -> tuple[int, int, int, int, str]:
        core, separator, prerelease = value.partition("-")
        major, minor, patch = (int(item) for item in core.split("."))
        return major, minor, patch, 0 if separator else 1, prerelease

    async def create_schema(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: dict[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        schema_key = validate_stable_key(str(payload["schema_key"]))
        declarations = dict(payload["snapshot"])
        content_checksum = sha256_checksum(canonical_json(declarations))
        composition = compose_declarations(
            packs={"space-local": declarations}, dependencies={"space-local": ()}
        )
        snapshot = composition.normalized_snapshot
        definition_id, version_id, now = new_uuid7(), new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            await connection.execute(
                text(
                    "INSERT INTO schema_definitions (id,tenant_id,space_id,schema_key,display_name,status,version,created_at,created_by,updated_at,updated_by) VALUES (:id,:tenant,:space,:key,:name,'ACTIVE',1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": definition_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "key": schema_key,
                    "name": payload["display_name"],
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await connection.execute(
                text(
                    "INSERT INTO schema_versions (id,tenant_id,space_id,schema_definition_id,semantic_version,status,local_declarations,normalized_snapshot,content_checksum,composition_checksum,canonicalization_algorithm,breaking_change,version,created_at,created_by,updated_at,updated_by) VALUES (:id,:tenant,:space,:definition,:semantic_version,'DRAFT',CAST(:local AS jsonb),CAST(:snapshot AS jsonb),:checksum,:composition_checksum,'nexweave.semantic-compose/1',false,1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": version_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "definition": definition_id,
                    "semantic_version": payload["semantic_version"],
                    "local": json.dumps(declarations),
                    "snapshot": json.dumps(snapshot),
                    "checksum": content_checksum,
                    "composition_checksum": composition.composition_checksum,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            result = self._schema_value(
                {
                    "id": version_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": space_id,
                    "schema_definition_id": definition_id,
                    "schema_key": schema_key,
                    "semantic_version": payload["semantic_version"],
                    "status": "DRAFT",
                    "normalized_snapshot": snapshot,
                    "content_checksum": content_checksum,
                    "composition_checksum": composition.composition_checksum,
                    "canonicalization_algorithm": "nexweave.semantic-compose/1",
                    "breaking_change": False,
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )
            await self._persist_semantic_snapshot(
                connection,
                principal=principal,
                space_id=space_id,
                schema_version_id=version_id,
                snapshot=snapshot,
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="schema.edit",
                resource_type="SchemaVersion",
                resource_id=version_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "CREATE", "schema_key": schema_key},
            )
            return result

        return await self._idempotent(
            principal=principal,
            operation=f"schema.create:{space_id}",
            key=idempotency_key,
            request=payload,
            mutation=mutation,
        )

    async def create_schema_version(
        self,
        *,
        principal: Principal,
        schema_id: UUID,
        payload: dict[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        declarations = dict(payload["snapshot"])
        composition = compose_declarations(
            packs={"space-local": declarations}, dependencies={"space-local": ()}
        )
        snapshot = composition.normalized_snapshot
        content_checksum = sha256_checksum(canonical_json(declarations))
        version_id, now = new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            definition = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,space_id,schema_key FROM schema_definitions "
                            "WHERE tenant_id=:tenant AND id=:id AND status='ACTIVE' FOR SHARE"
                        ),
                        {"tenant": principal.tenant_id, "id": schema_id},
                    )
                )
                .mappings()
                .first()
            )
            if definition is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Schema not found",
                    "The target SchemaDefinition is unavailable.",
                )
            await connection.execute(
                text(
                    "INSERT INTO schema_versions "
                    "(id,tenant_id,space_id,schema_definition_id,semantic_version,status,"
                    "local_declarations,normalized_snapshot,content_checksum,composition_checksum,"
                    "canonicalization_algorithm,breaking_change,version,created_at,created_by,"
                    "updated_at,updated_by) VALUES "
                    "(:id,:tenant,:space,:definition,:semantic_version,'DRAFT',CAST(:local AS jsonb),"
                    "CAST(:snapshot AS jsonb),:content,:composition,'nexweave.semantic-compose/1',"
                    "false,1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": version_id,
                    "tenant": principal.tenant_id,
                    "space": definition["space_id"],
                    "definition": schema_id,
                    "semantic_version": payload["semantic_version"],
                    "local": json.dumps(declarations),
                    "snapshot": json.dumps(snapshot),
                    "content": content_checksum,
                    "composition": composition.composition_checksum,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._persist_semantic_snapshot(
                connection,
                principal=principal,
                space_id=definition["space_id"],
                schema_version_id=version_id,
                snapshot=snapshot,
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="schema.edit",
                resource_type="SchemaVersion",
                resource_id=version_id,
                space_id=definition["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "NEW_VERSION", "schema_id": str(schema_id)},
            )
            return self._schema_value(
                {
                    "id": version_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": definition["space_id"],
                    "schema_definition_id": schema_id,
                    "schema_key": definition["schema_key"],
                    "semantic_version": payload["semantic_version"],
                    "status": "DRAFT",
                    "normalized_snapshot": snapshot,
                    "content_checksum": content_checksum,
                    "composition_checksum": composition.composition_checksum,
                    "canonicalization_algorithm": "nexweave.semantic-compose/1",
                    "breaking_change": False,
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"schema.version.create:{schema_id}",
            key=idempotency_key,
            request=payload,
            mutation=mutation,
        )

    async def compose_schema_candidate(
        self,
        *,
        principal: Principal,
        schema_id: UUID,
        payload: dict[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        candidate_id, report_id, now = new_uuid7(), new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            definition = (
                (
                    await connection.execute(
                        text(
                            "SELECT space_id FROM schema_definitions WHERE tenant_id=:tenant "
                            "AND id=:id AND status='ACTIVE' FOR SHARE"
                        ),
                        {"tenant": principal.tenant_id, "id": schema_id},
                    )
                )
                .mappings()
                .first()
            )
            if definition is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Schema not found",
                    "The target SchemaDefinition is unavailable.",
                )
            roots: dict[str, UUID] = {}
            for version_id in payload["domain_pack_version_ids"]:
                pack_key = (
                    await connection.execute(
                        text(
                            "SELECT p.pack_key FROM domain_pack_versions pv "
                            "JOIN domain_packs p ON p.id=pv.domain_pack_id "
                            "WHERE pv.tenant_id=:tenant AND pv.id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": UUID(str(version_id))},
                    )
                ).scalar_one_or_none()
                if pack_key is None or pack_key in roots:
                    raise ApiProblem(
                        409,
                        "PACK_DEPENDENCY_CONFLICT",
                        "Pack composition input conflict",
                        "Every requested Pack root must exist and have a unique Pack identity.",
                    )
                roots[str(pack_key)] = UUID(str(version_id))
            packs, dependencies, input_rows = await self._resolve_pack_graph(
                connection, tenant_id=principal.tenant_id, roots=roots
            )
            local = dict(payload["local_declarations"])
            packs["space-local"] = local
            dependencies["space-local"] = tuple(sorted(packs.keys() - {"space-local"}))
            composition = compose_declarations(packs=packs, dependencies=dependencies)
            previous = (
                (
                    await connection.execute(
                        text(
                            "SELECT normalized_snapshot FROM schema_versions WHERE tenant_id=:tenant "
                            "AND space_id=:space AND schema_definition_id=:schema AND status='PUBLISHED' "
                            "ORDER BY published_at DESC,id DESC LIMIT 1"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": definition["space_id"],
                            "schema": schema_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            compatibility = analyze_compatibility(
                dict(previous["normalized_snapshot"]) if previous is not None else None,
                composition.normalized_snapshot,
            )
            input_checksum = sha256_checksum(
                canonical_json(
                    {
                        "packs": [
                            {"id": str(row["id"]), "checksum": row["content_checksum"]}
                            for row in input_rows
                        ],
                        "local": local,
                    }
                )
            )
            report = {
                "compatible": not compatibility.breaking,
                "classification": compatibility.classification,
                "resolvedPacks": [
                    {
                        "packKey": row["pack_key"],
                        "version": row["pack_version"],
                        "checksum": row["content_checksum"],
                    }
                    for row in input_rows
                ],
                "packOrder": list(composition.pack_order),
                "conflicts": [],
                "changes": list(compatibility.changes),
                "impact": {
                    "entities": [],
                    "relations": [],
                    "claims": [],
                    "pages": [],
                    "releases": [],
                },
                "migrationPreview": {
                    "mode": "M4_PREVIEW_ONLY",
                    "dslVersion": "nexweave.schema-migration/1alpha1",
                    "operations": list(compatibility.migration_operations),
                },
            }
            await connection.execute(
                text(
                    "INSERT INTO schema_versions "
                    "(id,tenant_id,space_id,schema_definition_id,semantic_version,status,"
                    "local_declarations,normalized_snapshot,content_checksum,composition_checksum,"
                    "canonicalization_algorithm,breaking_change,version,created_at,created_by,"
                    "updated_at,updated_by) VALUES "
                    "(:id,:tenant,:space,:definition,:semantic_version,'DRAFT',CAST(:local AS jsonb),"
                    "CAST(:snapshot AS jsonb),:content,:composition,'nexweave.semantic-compose/1',"
                    ":breaking,1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": candidate_id,
                    "tenant": principal.tenant_id,
                    "space": definition["space_id"],
                    "definition": schema_id,
                    "semantic_version": payload["semantic_version"],
                    "local": json.dumps(local),
                    "snapshot": json.dumps(composition.normalized_snapshot),
                    "content": input_checksum,
                    "composition": composition.composition_checksum,
                    "breaking": compatibility.breaking,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._persist_semantic_snapshot(
                connection,
                principal=principal,
                space_id=definition["space_id"],
                schema_version_id=candidate_id,
                snapshot=composition.normalized_snapshot,
            )
            for index, row in enumerate(input_rows):
                await connection.execute(
                    text(
                        "INSERT INTO schema_version_pack_inputs "
                        "(id,tenant_id,space_id,schema_version_id,domain_pack_version_id,input_order,"
                        "content_checksum,created_at,created_by) VALUES "
                        "(:id,:tenant,:space,:schema_version,:pack,:position,:checksum,:now,:actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "space": definition["space_id"],
                        "schema_version": candidate_id,
                        "pack": row["id"],
                        "position": index,
                        "checksum": row["content_checksum"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            await connection.execute(
                text(
                    "INSERT INTO schema_composition_reports "
                    "(id,tenant_id,space_id,schema_version_id,input_checksum,result_checksum,report,"
                    "created_at,created_by) VALUES "
                    "(:id,:tenant,:space,:schema_version,:input,:result,CAST(:report AS jsonb),:now,:actor)"
                ),
                {
                    "id": report_id,
                    "tenant": principal.tenant_id,
                    "space": definition["space_id"],
                    "schema_version": candidate_id,
                    "input": input_checksum,
                    "result": composition.composition_checksum,
                    "report": json.dumps(report),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="schema.validate",
                resource_type="SchemaCompositionReport",
                resource_id=report_id,
                space_id=definition["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "COMPOSE", "schema_version_id": str(candidate_id)},
            )
            return _json_value(
                {
                    "id": report_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": definition["space_id"],
                    "schema_version_id": candidate_id,
                    "input_checksum": input_checksum,
                    "result_checksum": composition.composition_checksum,
                    "report": report,
                    "version": 1,
                    "created_at": now,
                    "created_by": principal.actor_id,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"schema.compose:{schema_id}",
            key=idempotency_key,
            request=payload,
            mutation=mutation,
        )

    async def list_schemas(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT sv.*,sd.schema_key FROM schema_versions sv JOIN schema_definitions sd ON sd.id=sv.schema_definition_id AND sd.tenant_id=sv.tenant_id AND sd.space_id=sv.space_id WHERE sv.tenant_id=:tenant AND sv.space_id=:space ORDER BY sv.created_at DESC,sv.id DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [self._schema_value(row) for row in rows]

    async def get_schema_version_chain_space(
        self, *, principal: Principal, schema_id: UUID
    ) -> UUID:
        async with self._database.engine.connect() as connection:
            space_id = (
                await connection.execute(
                    text(
                        "SELECT space_id FROM schema_definitions "
                        "WHERE tenant_id=:tenant AND id=:id AND status='ACTIVE'"
                    ),
                    {"tenant": principal.tenant_id, "id": schema_id},
                )
            ).scalar_one_or_none()
        if space_id is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Schema not found",
                "The target SchemaDefinition is unavailable.",
            )
        return UUID(str(space_id))

    async def get_schema_version(
        self, *, principal: Principal, schema_id: UUID, semantic_version: str
    ) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT sv.*,sd.schema_key FROM schema_versions sv JOIN schema_definitions sd ON sd.id=sv.schema_definition_id AND sd.tenant_id=sv.tenant_id AND sd.space_id=sv.space_id WHERE sv.tenant_id=:tenant AND sv.schema_definition_id=:schema AND sv.semantic_version=:version"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "schema": schema_id,
                            "version": semantic_version,
                        },
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Schema version not found",
                "The requested SchemaVersion is unavailable.",
            )
        return self._schema_value(row)

    async def validate_schema(
        self, *, principal: Principal, schema_id: UUID, semantic_version: str, trace_id: str
    ) -> JsonDict:
        schema = await self.get_schema_version(
            principal=principal, schema_id=schema_id, semantic_version=semantic_version
        )
        async with self._database.engine.connect() as connection:
            previous = (
                (
                    await connection.execute(
                        text(
                            "SELECT normalized_snapshot,composition_checksum FROM schema_versions "
                            "WHERE tenant_id=:tenant AND space_id=:space "
                            "AND schema_definition_id=:definition AND status='PUBLISHED' "
                            "AND id<>:id ORDER BY published_at DESC,id DESC LIMIT 1"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": schema["space_id"],
                            "definition": schema_id,
                            "id": schema["id"],
                        },
                    )
                )
                .mappings()
                .first()
            )
        compatibility = analyze_compatibility(
            dict(previous["normalized_snapshot"]) if previous is not None else None,
            dict(schema["normalized_snapshot"]),
        )
        report_id, plan_id, now = new_uuid7(), new_uuid7(), datetime.now(UTC)
        report_created_at = now
        report_created_by = principal.actor_id
        report = {
            "compatible": not compatibility.breaking,
            "classification": compatibility.classification,
            "conflicts": [],
            "changes": list(compatibility.changes),
            "impact": {"entities": [], "relations": [], "claims": [], "pages": [], "releases": []},
            "migrationPreview": {
                "mode": "M4_PREVIEW_ONLY",
                "dslVersion": "nexweave.schema-migration/1alpha1",
                "operations": list(compatibility.migration_operations),
            },
        }
        async with self._database.engine.begin() as connection:
            existing_report = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,report,created_at,created_by FROM schema_composition_reports "
                            "WHERE tenant_id=:tenant AND space_id=:space "
                            "AND schema_version_id=:schema_version AND input_checksum=:input"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": schema["space_id"],
                            "schema_version": schema["id"],
                            "input": schema["content_checksum"],
                        },
                    )
                )
                .mappings()
                .first()
            )
            if existing_report is None:
                await connection.execute(
                    text(
                        "INSERT INTO schema_composition_reports "
                        "(id,tenant_id,space_id,schema_version_id,input_checksum,result_checksum,"
                        "report,created_at,created_by) VALUES "
                        "(:id,:tenant,:space,:schema_version,:input,:result,CAST(:report AS jsonb),"
                        ":now,:actor)"
                    ),
                    {
                        "id": report_id,
                        "tenant": principal.tenant_id,
                        "space": schema["space_id"],
                        "schema_version": schema["id"],
                        "input": schema["content_checksum"],
                        "result": schema["composition_checksum"],
                        "report": json.dumps(report),
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            else:
                report_id = existing_report["id"]
                report = dict(existing_report["report"])
                report_created_at = existing_report["created_at"]
                report_created_by = existing_report["created_by"]
            if compatibility.migration_operations:
                await connection.execute(
                    text(
                        "INSERT INTO schema_migration_plans "
                        "(id,tenant_id,space_id,schema_version_id,from_checksum,to_checksum,"
                        "dsl_version,operations,rollback_operations,breaking,status,created_at,created_by) "
                        "VALUES (:id,:tenant,:space,:schema_version,:from_checksum,:to_checksum,"
                        "'nexweave.schema-migration/1alpha1',CAST(:operations AS jsonb),'[]'::jsonb,"
                        ":breaking,'PREVIEWED',:now,:actor) ON CONFLICT DO NOTHING"
                    ),
                    {
                        "id": plan_id,
                        "tenant": principal.tenant_id,
                        "space": schema["space_id"],
                        "schema_version": schema["id"],
                        "from_checksum": previous["composition_checksum"]
                        if previous is not None
                        else schema["content_checksum"],
                        "to_checksum": schema["composition_checksum"],
                        "operations": json.dumps(list(compatibility.migration_operations)),
                        "breaking": compatibility.breaking,
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            await connection.execute(
                text(
                    "UPDATE schema_versions SET status='TESTING',breaking_change=:breaking,"
                    "version=version+1,updated_at=:now,updated_by=:actor "
                    "WHERE tenant_id=:tenant AND id=:id AND status='DRAFT'"
                ),
                {
                    "breaking": compatibility.breaking,
                    "now": now,
                    "actor": principal.actor_id,
                    "tenant": principal.tenant_id,
                    "id": schema["id"],
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="schema.validate",
                resource_type="SchemaCompositionReport",
                resource_id=report_id,
                space_id=UUID(str(schema["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"schema_version_id": str(schema["id"])},
            )
        return _json_value(
            {
                "id": report_id,
                "tenant_id": principal.tenant_id,
                "space_id": schema["space_id"],
                "schema_version_id": schema["id"],
                "input_checksum": schema["content_checksum"],
                "result_checksum": schema["composition_checksum"],
                "report": report,
                "version": 1,
                "created_at": report_created_at,
                "created_by": report_created_by,
                "updated_at": report_created_at,
                "updated_by": report_created_by,
            }
        )

    async def publish_schema(
        self,
        *,
        principal: Principal,
        schema_id: UUID,
        semantic_version: str,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        schema = await self.get_schema_version(
            principal=principal, schema_id=schema_id, semantic_version=semantic_version
        )
        if schema["created_by"] == str(principal.actor_id):
            raise ApiProblem(
                403,
                "DUTY_SEPARATION_DENIED",
                "Independent approval required",
                "The SchemaVersion author cannot publish this semantic snapshot.",
            )
        if schema["status"] != "TESTING" or schema["breaking_change"]:
            raise ApiProblem(
                409,
                "SCHEMA_BREAKING_CHANGE",
                "Schema cannot be published",
                "Only validated, non-breaking TESTING SchemaVersions are publishable in M4.",
            )

        async def mutation(connection: AsyncConnection) -> JsonDict:
            now = datetime.now(UTC)
            pack_inputs = (
                (
                    await connection.execute(
                        text(
                            "SELECT domain_pack_version_id,content_checksum "
                            "FROM schema_version_pack_inputs WHERE tenant_id=:tenant "
                            "AND space_id=:space AND schema_version_id=:schema_version "
                            "ORDER BY input_order"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": schema["space_id"],
                            "schema_version": schema["id"],
                        },
                    )
                )
                .mappings()
                .all()
            )
            updated = await connection.execute(
                text(
                    "UPDATE schema_versions SET status='PUBLISHED',published_at=:now,published_by=:actor,version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id AND tenant_id=:tenant AND version=:version"
                ),
                {
                    "now": now,
                    "actor": principal.actor_id,
                    "id": schema["id"],
                    "tenant": principal.tenant_id,
                    "version": expected_version,
                },
            )
            if updated.rowcount != 1:
                raise ApiProblem(
                    412,
                    "VERSION_CONFLICT",
                    "Schema version conflict",
                    "The SchemaVersion was changed by another request.",
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="schema.publish",
                resource_type="SchemaVersion",
                resource_id=UUID(str(schema["id"])),
                space_id=UUID(str(schema["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"composition_checksum": schema["composition_checksum"]},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.schema.published.v1",
                aggregate_type="SchemaVersion",
                aggregate_id=UUID(str(schema["id"])),
                aggregate_version=expected_version + 1,
                space_id=UUID(str(schema["space_id"])),
                trace_id=trace_id,
                payload={
                    "schema_definition_id": str(schema_id),
                    "schema_version_id": str(schema["id"]),
                    "semantic_version": schema["semantic_version"],
                    "composition_checksum": schema["composition_checksum"],
                    "pack_inputs": [
                        {
                            "domain_pack_version_id": str(item["domain_pack_version_id"]),
                            "content_checksum": item["content_checksum"],
                        }
                        for item in pack_inputs
                    ],
                },
            )
            return self._schema_value(
                {
                    **schema,
                    "status": "PUBLISHED",
                    "version": expected_version + 1,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"schema.publish:{schema['id']}",
            key=idempotency_key,
            request={"expected_version": expected_version},
            mutation=mutation,
        )

    async def get_composition_report(self, *, principal: Principal, report_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,tenant_id,space_id,schema_version_id,input_checksum,"
                            "result_checksum,report,created_at,created_by FROM schema_composition_reports "
                            "WHERE tenant_id=:tenant AND id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": report_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Composition report not found",
                "The requested SchemaCompositionReport is unavailable.",
            )
        value = dict(row)
        value.update(
            {
                "version": 1,
                "updated_at": value["created_at"],
                "updated_by": value["created_by"],
            }
        )
        return _json_value(value)

    async def deprecate_schema(
        self,
        *,
        principal: Principal,
        schema_id: UUID,
        semantic_version: str,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        schema = await self.get_schema_version(
            principal=principal, schema_id=schema_id, semantic_version=semantic_version
        )
        if schema["status"] != "PUBLISHED":
            raise ApiProblem(
                409,
                "SCHEMA_STATE_CONFLICT",
                "Schema cannot be deprecated",
                "Only a PUBLISHED SchemaVersion can be deprecated.",
            )

        async def mutation(connection: AsyncConnection) -> JsonDict:
            now = datetime.now(UTC)
            updated = await connection.execute(
                text(
                    "UPDATE schema_versions SET status='DEPRECATED',version=version+1,"
                    "updated_at=:now,updated_by=:actor WHERE tenant_id=:tenant AND id=:id "
                    "AND version=:version AND status='PUBLISHED'"
                ),
                {
                    "now": now,
                    "actor": principal.actor_id,
                    "tenant": principal.tenant_id,
                    "id": schema["id"],
                    "version": expected_version,
                },
            )
            if updated.rowcount != 1:
                raise ApiProblem(
                    412,
                    "VERSION_CONFLICT",
                    "Schema version conflict",
                    "The SchemaVersion was changed by another request.",
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="schema.publish",
                resource_type="SchemaVersion",
                resource_id=UUID(str(schema["id"])),
                space_id=UUID(str(schema["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "DEPRECATE"},
            )
            return self._schema_value(
                {
                    **schema,
                    "status": "DEPRECATED",
                    "version": expected_version + 1,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"schema.deprecate:{schema['id']}",
            key=idempotency_key,
            request={"expected_version": expected_version},
            mutation=mutation,
        )

    async def _persist_semantic_snapshot(
        self,
        connection: AsyncConnection,
        *,
        principal: Principal,
        space_id: UUID,
        schema_version_id: UUID,
        snapshot: dict[str, Any],
    ) -> None:
        type_ids: dict[str, UUID] = {}
        for definition in snapshot.get("types", ()):
            type_id = new_uuid7()
            type_ids[str(definition["key"])] = type_id
            await connection.execute(
                text(
                    "INSERT INTO entity_types "
                    "(id,tenant_id,space_id,schema_version_id,type_key,display_name,definition) "
                    "VALUES (:id,:tenant,:space,:schema,:key,:name,CAST(:definition AS jsonb))"
                ),
                {
                    "id": type_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": schema_version_id,
                    "key": definition["key"],
                    "name": definition.get("displayName", definition["key"]),
                    "definition": json.dumps(definition),
                },
            )
        for definition in snapshot.get("properties", ()):
            await connection.execute(
                text(
                    "INSERT INTO property_definitions "
                    "(id,tenant_id,space_id,schema_version_id,entity_type_id,property_key,definition) "
                    "VALUES (:id,:tenant,:space,:schema,:entity_type,:key,CAST(:definition AS jsonb))"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": schema_version_id,
                    "entity_type": type_ids[str(definition["typeKey"])],
                    "key": definition["key"],
                    "definition": json.dumps(definition),
                },
            )
        for definition in snapshot.get("relations", ()):
            await connection.execute(
                text(
                    "INSERT INTO relation_types "
                    "(id,tenant_id,space_id,schema_version_id,relation_type_key,definition) "
                    "VALUES (:id,:tenant,:space,:schema,:key,CAST(:definition AS jsonb))"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": schema_version_id,
                    "key": definition["key"],
                    "definition": json.dumps(definition),
                },
            )
        for edge in snapshot.get("hierarchy", ()):
            await connection.execute(
                text(
                    "INSERT INTO type_hierarchy_edges "
                    "(id,tenant_id,space_id,schema_version_id,child_type_key,parent_type_key) "
                    "VALUES (:id,:tenant,:space,:schema,:child,:parent)"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": schema_version_id,
                    "child": edge["child"],
                    "parent": edge["parent"],
                },
            )
        for term in snapshot.get("terms", ()):
            await connection.execute(
                text(
                    "INSERT INTO type_terms "
                    "(id,tenant_id,space_id,schema_version_id,target_key,language,term,term_kind,scope) "
                    "VALUES (:id,:tenant,:space,:schema,:target,:language,:term,:kind,:scope)"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": schema_version_id,
                    "target": term["targetKey"],
                    "language": term["language"],
                    "term": term["term"],
                    "kind": term["kind"],
                    "scope": term.get("scope", "GLOBAL"),
                },
            )
        for mapping in snapshot.get("mappings", ()):
            await connection.execute(
                text(
                    "INSERT INTO concept_mappings "
                    "(id,tenant_id,space_id,schema_version_id,source_key,target_key,kind,approval_status) "
                    "VALUES (:id,:tenant,:space,:schema,:source,:target,:kind,:approval)"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": schema_version_id,
                    "source": mapping["source"],
                    "target": mapping["target"],
                    "kind": mapping["kind"],
                    "approval": mapping.get("reviewStatus", "PENDING"),
                },
            )
        for section, table, key_column in (
            ("templates", "page_templates", "template_key"),
            ("lintRules", "lint_rules", "rule_key"),
            ("evaluationSuites", "evaluation_suites", "suite_key"),
            ("ui", "ui_declarations", "ui_key"),
        ):
            for definition in snapshot.get(section, ()):
                actor_column = ",created_by" if table == "evaluation_suites" else ""
                actor_value = ",:actor" if table == "evaluation_suites" else ""
                parameters = {
                    "id": new_uuid7(),
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": schema_version_id,
                    "key": definition["key"],
                    "definition": json.dumps(definition),
                }
                if table == "evaluation_suites":
                    parameters["actor"] = principal.actor_id
                await connection.execute(
                    text(
                        f"INSERT INTO {table} "  # noqa: S608
                        f"(id,tenant_id,space_id,schema_version_id,{key_column},definition{actor_column}) "  # noqa: S608,E501
                        "VALUES (:id,:tenant,:space,:schema,:key,CAST(:definition AS jsonb)"
                        f"{actor_value})"  # noqa: S608
                    ),
                    parameters,
                )

    @staticmethod
    def _schema_value(row: Any) -> JsonDict:
        allowed = {
            "id",
            "tenant_id",
            "space_id",
            "schema_definition_id",
            "schema_key",
            "semantic_version",
            "status",
            "normalized_snapshot",
            "content_checksum",
            "composition_checksum",
            "canonicalization_algorithm",
            "breaking_change",
            "version",
            "created_at",
            "created_by",
            "updated_at",
            "updated_by",
        }
        value = {key: item for key, item in dict(row).items() if key in allowed}
        value["normalized_snapshot"] = dict(value["normalized_snapshot"])
        return _json_value(value)
