"""M8 Connector execution facts and Obsidian exchange adapter."""
# ruff: noqa: E501

from __future__ import annotations

import difflib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_api.release_repository import ReleaseRepository
from nexweave_api.repository import JsonDict, _json_value
from nexweave_domain import Principal, WorkflowType, canonical_json, new_uuid7, sha256_checksum


def _diff(before: str, after: str) -> str:
    return "\n".join(
        difflib.unified_diff(
            before.splitlines(),
            after.splitlines(),
            fromfile="nexweave",
            tofile="obsidian",
            lineterm="",
        )
    )


def _frontmatter(markdown: str) -> tuple[dict[str, str], str]:
    if not markdown.startswith("---\n"):
        return {}, markdown
    marker = markdown.find("\n---\n", 4)
    if marker < 0:
        return {}, markdown
    facts: dict[str, str] = {}
    for line in markdown[4:marker].splitlines():
        key, separator, value = line.partition(":")
        if not separator or not key.strip():
            return {}, markdown
        facts[key.strip()] = value.strip().strip('"')
    return facts, markdown[marker + 5 :]


class IntegrationRepository(ReleaseRepository):
    async def create_connector_instance(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: dict[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        instance_id, now = new_uuid7(), datetime.now(UTC)
        config_checksum = sha256_checksum(
            canonical_json(
                {
                    "allowlist": payload["allowlist"],
                    "config": payload["config"],
                    "field_mapping": payload["field_mapping"],
                }
            )
        )

        async def mutation(connection: AsyncConnection) -> JsonDict:
            definition = (
                await connection.execute(
                    text("SELECT id FROM connector_definitions WHERE tenant_id=:tenant AND id=:id"),
                    {"tenant": principal.tenant_id, "id": payload["definition_id"]},
                )
            ).scalar_one_or_none()
            if definition is None:
                raise ApiProblem(
                    404,
                    "CONNECTOR_DEFINITION_UNAVAILABLE",
                    "Connector Definition unavailable",
                    "The governed ConnectorDefinition is unavailable in this tenant.",
                )
            await connection.execute(
                text(
                    "INSERT INTO connector_instances (id,tenant_id,space_id,definition_id,name,kind,credential_ref,allowlist,config,field_mapping,classification,config_checksum,watermark,status,version,created_at,created_by,updated_at,updated_by) VALUES (:id,:tenant,:space,:definition,:name,:kind,:credential,CAST(:allowlist AS jsonb),CAST(:config AS jsonb),CAST(:mapping AS jsonb),:classification,:checksum,'{}'::jsonb,'ACTIVE',1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": instance_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "definition": payload["definition_id"],
                    "name": payload["name"],
                    "kind": payload["kind"],
                    "credential": payload.get("credential_ref"),
                    "allowlist": json.dumps(payload["allowlist"]),
                    "config": json.dumps(payload["config"]),
                    "mapping": json.dumps(payload["field_mapping"]),
                    "classification": payload["classification"],
                    "checksum": config_checksum,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="connector.instance.create",
                resource_type="ConnectorInstance",
                resource_id=instance_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "kind": payload["kind"],
                    "allowlist_count": len(payload["allowlist"]),
                    "credential_ref_present": bool(payload.get("credential_ref")),
                },
            )
            return await self._connector_instance(connection, principal.tenant_id, instance_id)

        return await self._idempotent(
            principal=principal,
            operation=f"connector.instance.create:{space_id}",
            key=idempotency_key,
            request=payload,
            mutation=mutation,
        )

    async def list_connector_instances(
        self, *, principal: Principal, space_id: UUID
    ) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            ids = (
                (
                    await connection.execute(
                        text(
                            "SELECT id FROM connector_instances WHERE tenant_id=:tenant AND space_id=:space ORDER BY created_at,id"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .scalars()
                .all()
            )
            return [
                await self._connector_instance(connection, principal.tenant_id, UUID(str(item)))
                for item in ids
            ]

    async def get_connector_instance(self, *, principal: Principal, instance_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            return await self._connector_instance(connection, principal.tenant_id, instance_id)

    async def create_connector_sync_run(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        instance_id: UUID,
        payload: dict[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        instance = await self.get_connector_instance(principal=principal, instance_id=instance_id)
        if UUID(str(instance["space_id"])) != space_id or instance["status"] != "ACTIVE":
            raise ApiProblem(
                409,
                "CONNECTOR_NOT_ACTIVE",
                "Connector unavailable",
                "The ConnectorInstance is not active in this space.",
            )
        business_key = f"{instance_id}:{sha256_checksum(canonical_json(payload))[7:23]}"
        task = await self.create_workflow_task(
            principal=principal,
            space_id=space_id,
            payload={
                "workflow_type": WorkflowType.CONNECTOR_SYNC.value,
                "business_key": business_key,
                "display_name": f"Read-only connector sync: {instance['name']}",
                "input_refs": {"connector_instance_id": str(instance_id)},
                "start_paused": False,
            },
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )
        run_id, now = new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            existing = (
                (
                    await connection.execute(
                        text("SELECT * FROM connector_sync_runs WHERE workflow_task_id=:task"),
                        {"task": task["id"]},
                    )
                )
                .mappings()
                .first()
            )
            if existing is not None:
                return _json_value(existing)
            await connection.execute(
                text(
                    "INSERT INTO connector_sync_runs (id,tenant_id,space_id,connector_instance_id,workflow_task_id,workflow_id,status,requested_watermark,resulting_watermark,result_summary,created_at,created_by,updated_at,updated_by) VALUES (:id,:tenant,:space,:instance,:task,:workflow,'CREATED',CAST(:requested AS jsonb),'{}'::jsonb,'{}'::jsonb,:now,:actor,:now,:actor)"
                ),
                {
                    "id": run_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "instance": instance_id,
                    "task": task["id"],
                    "workflow": task["workflow_id"],
                    "requested": json.dumps(payload.get("requested_watermark", {})),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="connector.sync.create",
                resource_type="ConnectorSyncRun",
                resource_id=run_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "connector_instance_id": str(instance_id),
                    "workflow_id": task["workflow_id"],
                },
            )
            return await self._sync_run(connection, principal.tenant_id, run_id)

        return await self._idempotent(
            principal=principal,
            operation=f"connector.sync.create:{instance_id}",
            key=idempotency_key,
            request={"instance_id": str(instance_id), **payload},
            mutation=mutation,
        )

    async def get_connector_sync_run(self, *, principal: Principal, run_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            return await self._sync_run(connection, principal.tenant_id, run_id)

    async def mark_connector_sync_started(
        self, *, run_id: UUID, temporal_run_id: str, actor_id: UUID
    ) -> JsonDict:
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE connector_sync_runs SET temporal_run_id=:temporal,status='RUNNING',updated_at=:now,updated_by=:actor WHERE id=:id AND status='CREATED'"
                ),
                {
                    "temporal": temporal_run_id,
                    "now": datetime.now(UTC),
                    "actor": actor_id,
                    "id": run_id,
                },
            )
            row = (
                (
                    await connection.execute(
                        text("SELECT tenant_id FROM connector_sync_runs WHERE id=:id"),
                        {"id": run_id},
                    )
                )
                .mappings()
                .one()
            )
            return await self._sync_run(connection, UUID(str(row["tenant_id"])), run_id)

    async def connector_sync_context(self, *, run_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT sr.*,ci.name AS connector_name,ci.kind,ci.allowlist,ci.config,ci.field_mapping,ci.classification,ci.credential_ref FROM connector_sync_runs sr JOIN connector_instances ci ON ci.id=sr.connector_instance_id AND ci.tenant_id=sr.tenant_id WHERE sr.id=:id"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Connector sync not found",
                    "The connector sync run is unavailable.",
                )
            return _json_value(row)

    async def complete_connector_sync_run(
        self,
        *,
        run_id: UUID,
        status: str,
        resulting_watermark: dict[str, Any],
        result_summary: dict[str, Any],
        error_code: str | None = None,
    ) -> JsonDict:
        async with self._database.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT tenant_id,space_id,connector_instance_id,created_by FROM connector_sync_runs WHERE id=:id FOR UPDATE"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .one()
            )
            now = datetime.now(UTC)
            await connection.execute(
                text(
                    "UPDATE connector_sync_runs SET status=:status,resulting_watermark=CAST(:watermark AS jsonb),result_summary=CAST(:summary AS jsonb),error_code=:error,updated_at=:now,updated_by=created_by WHERE id=:id"
                ),
                {
                    "status": status,
                    "watermark": json.dumps(resulting_watermark),
                    "summary": json.dumps(result_summary),
                    "error": error_code,
                    "now": now,
                    "id": run_id,
                },
            )
            await connection.execute(
                text(
                    "UPDATE connector_instances SET watermark=CAST(:watermark AS jsonb),version=version+1,updated_at=:now,updated_by=:actor WHERE id=:instance AND :status='SUCCEEDED'"
                ),
                {
                    "watermark": json.dumps(resulting_watermark),
                    "now": now,
                    "actor": row["created_by"],
                    "instance": row["connector_instance_id"],
                    "status": status,
                },
            )
            return await self._sync_run(connection, UUID(str(row["tenant_id"])), run_id)

    async def export_obsidian_page(
        self, *, principal: Principal, page_id: UUID, trace_id: str
    ) -> JsonDict:
        page = await self.get_wiki_page(principal=principal, page_id=page_id)
        current = page.get("current_version")
        if current is None:
            raise ApiProblem(
                409,
                "OBSIDIAN_PAGE_EMPTY",
                "Wiki page unavailable",
                "Only a page with a fixed current version can be exported.",
            )
        export_id, now = new_uuid7(), datetime.now(UTC)
        frontmatter = "\n".join(
            (
                "---",
                f'nexweave_page_id: "{page_id}"',
                f'nexweave_base_version_id: "{current["id"]}"',
                f'nexweave_content_checksum: "{current["content_checksum"]}"',
                'nexweave_exchange: "v1"',
                "---",
                "",
            )
        )
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO obsidian_exports (id,tenant_id,space_id,wiki_page_id,wiki_page_version_id,content_checksum,created_at,created_by) VALUES (:id,:tenant,:space,:page,:version,:checksum,:now,:actor)"
                ),
                {
                    "id": export_id,
                    "tenant": principal.tenant_id,
                    "space": page["space_id"],
                    "page": page_id,
                    "version": current["id"],
                    "checksum": current["content_checksum"],
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="obsidian.export",
                resource_type="WikiPage",
                resource_id=page_id,
                space_id=UUID(str(page["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"export_id": str(export_id), "base_version_id": str(current["id"])},
            )
        return {
            "export_id": export_id,
            "wiki_page_id": page_id,
            "wiki_page_version_id": current["id"],
            "content_checksum": current["content_checksum"],
            "markdown": frontmatter + current["markdown"],
        }

    async def import_obsidian_markdown(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        markdown: str,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        facts, body = _frontmatter(markdown)
        markdown_checksum = sha256_checksum(markdown.encode("utf-8"))
        page_id_text, base_id_text, checksum = (
            facts.get("nexweave_page_id"),
            facts.get("nexweave_base_version_id"),
            facts.get("nexweave_content_checksum"),
        )
        if not page_id_text or not base_id_text or not checksum:
            return await self._record_obsidian_import(
                principal=principal,
                space_id=space_id,
                markdown=markdown,
                markdown_checksum=markdown_checksum,
                markdown_diff="",
                status="DRAFT_CREATED",
                page_id=None,
                base_id=None,
                draft_id=None,
                conflict=None,
                idempotency_key=idempotency_key,
                trace_id=trace_id,
            )
        try:
            page_id, base_id = UUID(page_id_text), UUID(base_id_text)
        except ValueError:
            return await self._record_obsidian_import(
                principal=principal,
                space_id=space_id,
                markdown=markdown,
                markdown_checksum=markdown_checksum,
                markdown_diff="",
                status="CONFLICT",
                page_id=None,
                base_id=None,
                draft_id=None,
                conflict=(
                    "OBSIDIAN_STABLE_ID_INVALID",
                    {"reason": "frontmatter identifiers are invalid"},
                ),
                idempotency_key=idempotency_key,
                trace_id=trace_id,
            )
        page = await self.get_wiki_page(principal=principal, page_id=page_id)
        if UUID(str(page["space_id"])) != space_id:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Obsidian page unavailable",
                "The exported page is unavailable in this space.",
            )
        base = await self.get_wiki_page_version(
            principal=principal, page_id=page_id, version_id=base_id
        )
        current = page.get("current_version")
        diff = _diff(str(base["markdown"]), body)
        conflict: tuple[str, dict[str, Any]] | None = None
        if str(base["content_checksum"]) != checksum:
            conflict = (
                "OBSIDIAN_EXPORT_TAMPERED",
                {"reason": "the export baseline checksum does not match"},
            )
        elif current is None or str(current["id"]) != str(base_id):
            conflict = (
                "OBSIDIAN_BASE_DRIFT",
                {
                    "base_version_id": str(base_id),
                    "current_version_id": str(current["id"]) if current else None,
                },
            )
        if conflict is not None:
            return await self._record_obsidian_import(
                principal=principal,
                space_id=space_id,
                markdown=markdown,
                markdown_checksum=markdown_checksum,
                markdown_diff=diff,
                status="CONFLICT",
                page_id=page_id,
                base_id=base_id,
                draft_id=None,
                conflict=conflict,
                idempotency_key=idempotency_key,
                trace_id=trace_id,
            )
        edited = await self.edit_wiki_page(
            principal=principal,
            page_id=page_id,
            expected_version=int(page["version"]),
            payload={
                "protected_sections": {"obsidian-import": body},
                "properties": {"obsidian_base_version_id": str(base_id)},
                "reason": "Obsidian import; review required",
            },
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )
        draft_id = UUID(str(edited["current_version_id"]))
        return await self._record_obsidian_import(
            principal=principal,
            space_id=space_id,
            markdown=markdown,
            markdown_checksum=markdown_checksum,
            markdown_diff=diff,
            status="DRAFT_CREATED",
            page_id=page_id,
            base_id=base_id,
            draft_id=draft_id,
            conflict=None,
            idempotency_key=idempotency_key,
            trace_id=trace_id,
        )

    async def _record_obsidian_import(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        markdown: str,
        markdown_checksum: str,
        markdown_diff: str,
        status: str,
        page_id: UUID | None,
        base_id: UUID | None,
        draft_id: UUID | None,
        conflict: tuple[str, dict[str, Any]] | None,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        import_id, now = new_uuid7(), datetime.now(UTC)

        async def mutation(connection: AsyncConnection) -> JsonDict:
            await connection.execute(
                text(
                    "INSERT INTO obsidian_imports (id,tenant_id,space_id,wiki_page_id,base_version_id,draft_version_id,status,markdown,markdown_checksum,markdown_diff,created_at,created_by) VALUES (:id,:tenant,:space,:page,:base,:draft,:status,:markdown,:checksum,:diff,:now,:actor)"
                ),
                {
                    "id": import_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "page": page_id,
                    "base": base_id,
                    "draft": draft_id,
                    "status": status,
                    "markdown": markdown,
                    "checksum": markdown_checksum,
                    "diff": markdown_diff,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            conflict_id = None
            if conflict is not None:
                conflict_id = new_uuid7()
                await connection.execute(
                    text(
                        "INSERT INTO obsidian_import_conflicts (id,tenant_id,space_id,import_id,code,details,created_at) VALUES (:id,:tenant,:space,:import,:code,CAST(:details AS jsonb),:now)"
                    ),
                    {
                        "id": conflict_id,
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "import": import_id,
                        "code": conflict[0],
                        "details": json.dumps(conflict[1]),
                        "now": now,
                    },
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="obsidian.import",
                resource_type="ObsidianImport",
                resource_id=import_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "status": status,
                    "wiki_page_id": str(page_id) if page_id else None,
                    "conflict_code": conflict[0] if conflict else None,
                },
            )
            return {
                "id": import_id,
                "status": status,
                "wiki_page_id": page_id,
                "base_version_id": base_id,
                "draft_version_id": draft_id,
                "conflict_id": conflict_id,
                "markdown_diff": markdown_diff,
            }

        return await self._idempotent(
            principal=principal,
            operation=f"obsidian.import:{space_id}",
            key=idempotency_key,
            request={"markdown_checksum": markdown_checksum},
            mutation=mutation,
        )

    async def _connector_instance(
        self, connection: AsyncConnection, tenant_id: UUID, instance_id: UUID
    ) -> JsonDict:
        row = (
            (
                await connection.execute(
                    text("SELECT * FROM connector_instances WHERE tenant_id=:tenant AND id=:id"),
                    {"tenant": tenant_id, "id": instance_id},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Connector instance not found",
                "The connector instance is unavailable.",
            )
        return _json_value(row)

    async def _sync_run(
        self, connection: AsyncConnection, tenant_id: UUID, run_id: UUID
    ) -> JsonDict:
        row = (
            (
                await connection.execute(
                    text("SELECT * FROM connector_sync_runs WHERE tenant_id=:tenant AND id=:id"),
                    {"tenant": tenant_id, "id": run_id},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Connector sync not found",
                "The connector sync run is unavailable.",
            )
        return _json_value(row)
