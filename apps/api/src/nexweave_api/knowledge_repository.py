"""M5 Compile and Wiki PostgreSQL application service."""

from __future__ import annotations

import difflib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_api.model_gateway import LocalModelGateway
from nexweave_api.repository import JsonDict, _json_value
from nexweave_api.semantic_repository import SemanticRepository
from nexweave_application import ModelGatewayRequest
from nexweave_domain import (
    ActorType,
    CompileLock,
    CompileMode,
    CompileRuleViolation,
    DataClassification,
    LockedSource,
    Principal,
    canonical_json,
    compile_input_fingerprint,
    merge_recompiled_page,
    new_uuid7,
    render_wiki_markdown,
    sha256_checksum,
)

JOB_COLUMNS = (
    "id,tenant_id,space_id,schema_version_id,composition_checksum,prompt_version_id,"
    "model_profile_id,workflow_task_id,workflow_id,run_id,mode,status,input_fingerprint,"
    "normalization_version,scope,progress,cost_summary,result_summary,error_code,error_detail,"
    "version,created_at,created_by,updated_at,updated_by"
)
JOB_COLUMNS_QUALIFIED = ",".join(f"cj.{column}" for column in JOB_COLUMNS.split(","))
PAGE_COLUMNS = (
    "id,tenant_id,space_id,schema_version_id,primary_entity_id,template_key,slug,title,status,"
    "current_version_id,version,created_at,created_by,updated_at,updated_by"
)
PAGE_VERSION_COLUMNS = (
    "id,wiki_page_id,compile_job_id,revision,generated_sections,protected_sections,properties,"
    "markdown,content_checksum,status,edit_reason,created_at,created_by"
)


class KnowledgeRepository(SemanticRepository):
    def __init__(self, database: Any, model_gateway: LocalModelGateway | None = None) -> None:
        super().__init__(database)
        self._model_gateway = model_gateway or LocalModelGateway()

    async def create_compile_job(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: Mapping[str, Any],
        workflow_task_id: UUID,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        job_id, now = new_uuid7(), datetime.now(UTC)
        source_ids = sorted(UUID(str(item)) for item in payload["source_version_ids"])

        async def mutation(connection: AsyncConnection) -> JsonDict:
            locked = (
                (
                    await connection.execute(
                        text(
                            "SELECT sv.id AS schema_version_id,sv.status AS schema_status,"
                            "sv.composition_checksum,pv.id AS prompt_version_id,pv.status AS prompt_status,"
                            "mp.id AS model_profile_id,mp.status AS model_status,mp.externally_hosted,"
                            "mp.maximum_classification,wt.workflow_id "
                            "FROM schema_versions sv JOIN prompt_versions pv ON pv.tenant_id=sv.tenant_id "
                            "AND pv.id=:prompt AND (pv.space_id IS NULL OR pv.space_id=sv.space_id) "
                            "JOIN model_profiles mp ON mp.tenant_id=sv.tenant_id AND mp.id=:model "
                            "AND (mp.space_id IS NULL OR mp.space_id=sv.space_id) "
                            "JOIN workflow_tasks wt ON wt.tenant_id=sv.tenant_id AND wt.space_id=sv.space_id "
                            "AND wt.id=:task AND wt.workflow_type='KNOWLEDGE_COMPILE' "
                            "WHERE sv.tenant_id=:tenant AND sv.space_id=:space AND sv.id=:schema FOR SHARE"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": space_id,
                            "schema": payload["schema_version_id"],
                            "prompt": payload["prompt_version_id"],
                            "model": payload["model_profile_id"],
                            "task": workflow_task_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            if locked is None:
                raise ApiProblem(
                    404,
                    "COMPILE_INPUT_UNAVAILABLE",
                    "Compile input unavailable",
                    "The exact Schema, Prompt, Model or Workflow input is unavailable.",
                )
            statement = text(
                "SELECT id,checksum,active_parse_job_id,classification,status FROM source_versions "
                "WHERE tenant_id=:tenant AND space_id=:space AND id IN :ids FOR SHARE"
            ).bindparams(bindparam("ids", expanding=True))
            rows = (
                (
                    await connection.execute(
                        statement,
                        {"tenant": principal.tenant_id, "space": space_id, "ids": source_ids},
                    )
                )
                .mappings()
                .all()
            )
            if len(rows) != len(source_ids) or any(
                row["active_parse_job_id"] is None or row["status"] not in {"PARSED", "PARTIAL"}
                for row in rows
            ):
                raise ApiProblem(
                    409,
                    "COMPILE_SOURCE_NOT_READY",
                    "Source is not ready",
                    "Every fixed SourceVersion must have an active parsed result.",
                )
            sources = tuple(
                LockedSource(
                    str(row["id"]),
                    str(row["checksum"]),
                    str(row["active_parse_job_id"]),
                    DataClassification(str(row["classification"])),
                )
                for row in sorted(rows, key=lambda item: str(item["id"]))
            )
            lock = CompileLock(
                str(locked["schema_version_id"]),
                str(locked["schema_status"]),
                str(locked["composition_checksum"]),
                str(locked["prompt_version_id"]),
                str(locked["prompt_status"]),
                str(locked["model_profile_id"]),
                str(locked["model_status"]),
                bool(locked["externally_hosted"]),
                DataClassification(str(locked["maximum_classification"])),
                sources,
                CompileMode(str(payload["mode"])),
            )
            try:
                fingerprint = compile_input_fingerprint(lock)
            except CompileRuleViolation as exc:
                raise ApiProblem(422, exc.code, "Compile policy rejected", str(exc)) from exc
            await connection.execute(
                text(
                    "INSERT INTO compile_jobs (id,tenant_id,space_id,schema_version_id,"
                    "composition_checksum,prompt_version_id,model_profile_id,workflow_task_id,"
                    "workflow_id,mode,status,input_fingerprint,normalization_version,scope,progress,"
                    "cost_summary,result_summary,version,created_at,created_by,updated_at,updated_by) "
                    "VALUES (:id,:tenant,:space,:schema,:composition,:prompt,:model,:task,:workflow,"
                    ":mode,'CREATED',:fingerprint,'nexweave.normalize/1',CAST(:scope AS jsonb),0,"
                    "'{}'::jsonb,'{}'::jsonb,1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": job_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "schema": locked["schema_version_id"],
                    "composition": locked["composition_checksum"],
                    "prompt": locked["prompt_version_id"],
                    "model": locked["model_profile_id"],
                    "task": workflow_task_id,
                    "workflow": locked["workflow_id"],
                    "mode": payload["mode"],
                    "fingerprint": fingerprint,
                    "scope": json.dumps(dict(payload.get("scope", {}))),
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            for index, source in enumerate(sources):
                await connection.execute(
                    text(
                        "INSERT INTO compile_job_sources (id,tenant_id,space_id,compile_job_id,"
                        "source_version_id,source_checksum,parse_job_id,input_order,created_at) "
                        "VALUES (:id,:tenant,:space,:job,:source,:checksum,:parse,:position,:now)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "job": job_id,
                        "source": UUID(source.source_version_id),
                        "checksum": source.checksum,
                        "parse": UUID(source.parse_job_id),
                        "position": index,
                        "now": now,
                    },
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="compile.create",
                resource_type="CompileJob",
                resource_id=job_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"input_fingerprint": fingerprint, "source_count": len(sources)},
            )
            return await self._get_compile_job_in_connection(connection, job_id)

        return await self._idempotent(
            principal=principal,
            operation=f"compile.create:{space_id}",
            key=idempotency_key,
            request={**dict(payload), "workflow_task_id": str(workflow_task_id)},
            mutation=mutation,
        )

    async def mark_compile_started(
        self, *, compile_job_id: UUID, run_id: str, actor_id: UUID
    ) -> JsonDict:
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE compile_jobs SET run_id=:run,status='RUNNING',progress=1,version=version+1,"
                    "updated_at=:now,updated_by=:actor WHERE id=:id AND status='CREATED'"
                ),
                {"run": run_id, "now": datetime.now(UTC), "actor": actor_id, "id": compile_job_id},
            )
            return await self._get_compile_job_in_connection(connection, compile_job_id)

    async def list_compile_jobs(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {JOB_COLUMNS} FROM compile_jobs WHERE tenant_id=:tenant AND space_id=:space ORDER BY created_at DESC,id DESC"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def get_compile_job(self, *, principal: Principal, compile_job_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = await self._get_compile_job_in_connection(
                connection, compile_job_id, principal.tenant_id
            )
        return row

    async def _get_compile_job_in_connection(
        self, connection: AsyncConnection, compile_job_id: UUID, tenant_id: UUID | None = None
    ) -> JsonDict:
        where = "id=:id" if tenant_id is None else "tenant_id=:tenant AND id=:id"
        params: dict[str, Any] = {"id": compile_job_id}
        if tenant_id is not None:
            params["tenant"] = tenant_id
        row = (
            (
                await connection.execute(
                    text(f"SELECT {JOB_COLUMNS} FROM compile_jobs WHERE {where}"), params
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Compile job not found", "The CompileJob is unavailable."
            )
        sources = (
            (
                await connection.execute(
                    text(
                        "SELECT source_version_id,source_checksum,parse_job_id,input_order FROM compile_job_sources WHERE compile_job_id=:id ORDER BY input_order"
                    ),
                    {"id": compile_job_id},
                )
            )
            .mappings()
            .all()
        )
        steps = (
            (
                await connection.execute(
                    text(
                        "SELECT id,step_key,input_checksum,status,attempt,output_summary,error_code,started_at,completed_at FROM compile_steps WHERE compile_job_id=:id ORDER BY created_at,id"
                    ),
                    {"id": compile_job_id},
                )
            )
            .mappings()
            .all()
        )
        return _json_value(
            {
                **row,
                "sources": [dict(source) for source in sources],
                "steps": [dict(step) for step in steps],
            }
        )

    async def execute_compile(
        self, *, compile_job_id: UUID, run_id: str, trace_id: str
    ) -> JsonDict:
        now = datetime.now(UTC)
        async with self._database.engine.begin() as connection:
            job = (
                (
                    await connection.execute(
                        text(f"SELECT {JOB_COLUMNS} FROM compile_jobs WHERE id=:id FOR UPDATE"),
                        {"id": compile_job_id},
                    )
                )
                .mappings()
                .first()
            )
            if job is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Compile job not found",
                    "The CompileJob is unavailable.",
                )
            if job["status"] == "SUCCEEDED":
                return _json_value(job["result_summary"])
            step_id = await self._start_compile_step(
                connection, dict(job), "structured-extract", now
            )
            await connection.execute(
                text(
                    "UPDATE compile_jobs SET run_id=:run,status='RUNNING',progress=20,version=version+1,updated_at=:now WHERE id=:id"
                ),
                {"run": run_id, "now": now, "id": compile_job_id},
            )

        async with self._database.engine.connect() as connection:
            context = await self._load_compile_context(connection, compile_job_id)
        if context["model_provider"] != "nexweave.local":
            raise ApiProblem(
                503,
                "MODEL_PROVIDER_UNAVAILABLE",
                "Model provider is unavailable",
                "M5 only enables the governed no-network local provider; the selected external provider has no configured adapter.",
            )
        request = ModelGatewayRequest(
            model_profile_id=str(context["job"]["model_profile_id"]),
            prompt_version_id=str(context["job"]["prompt_version_id"]),
            classification=str(context["classification"]),
            schema_snapshot=dict(context["schema_snapshot"]),
            segments=tuple(context["segments"]),
            budget_units=int(context["model_config"].get("max_input_units", 200_000)),
        )
        result = await self._model_gateway.structured_output(request)

        async with self._database.engine.begin() as connection:
            job = (
                (
                    await connection.execute(
                        text(f"SELECT {JOB_COLUMNS} FROM compile_jobs WHERE id=:id FOR UPDATE"),
                        {"id": compile_job_id},
                    )
                )
                .mappings()
                .one()
            )
            if job["status"] == "SUCCEEDED":
                return _json_value(job["result_summary"])
            invocation_id = new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO model_invocations (id,tenant_id,space_id,compile_job_id,compile_step_id,"
                    "model_profile_id,prompt_version_id,capability,provider_request_id,input_checksum,"
                    "output_checksum,status,input_units,output_units,latency_ms,estimated_cost_microunits,"
                    "created_at) VALUES (:id,:tenant,:space,:job,:step,:model,:prompt,'STRUCTURED_OUTPUT',"
                    ":request,:input,:output,'SUCCEEDED',:input_units,:output_units,:latency,:cost,:now)"
                ),
                {
                    "id": invocation_id,
                    "tenant": job["tenant_id"],
                    "space": job["space_id"],
                    "job": compile_job_id,
                    "step": step_id,
                    "model": job["model_profile_id"],
                    "prompt": job["prompt_version_id"],
                    "request": result.provider_request_id,
                    "input": result.input_checksum,
                    "output": result.output_checksum,
                    "input_units": result.input_units,
                    "output_units": result.output_units,
                    "latency": result.latency_ms,
                    "cost": result.estimated_cost_microunits,
                    "now": datetime.now(UTC),
                },
            )
            outputs = await self._persist_compile_output(
                connection, job=dict(job), output=result.structured_output, trace_id=trace_id
            )
            summary = {
                **outputs,
                "model_invocation_id": str(invocation_id),
                "provider": "nexweave.local-structured/1",
                "external_llm_called": False,
            }
            completed_at = datetime.now(UTC)
            await connection.execute(
                text(
                    "UPDATE compile_steps SET status='SUCCEEDED',output_summary=CAST(:summary AS jsonb),"
                    "completed_at=:now WHERE id=:id"
                ),
                {"summary": json.dumps(summary), "now": completed_at, "id": step_id},
            )
            await connection.execute(
                text(
                    "UPDATE compile_jobs SET status='SUCCEEDED',progress=100,cost_summary=CAST(:cost AS jsonb),"
                    "result_summary=CAST(:result AS jsonb),version=version+1,updated_at=:now WHERE id=:id"
                ),
                {
                    "cost": json.dumps(
                        {
                            "input_units": result.input_units,
                            "output_units": result.output_units,
                            "estimated_cost_microunits": result.estimated_cost_microunits,
                        }
                    ),
                    "result": json.dumps(summary),
                    "now": completed_at,
                    "id": compile_job_id,
                },
            )
            principal = self._job_principal(dict(job))
            await self._insert_audit(
                connection,
                principal=principal,
                action="compile.execute",
                resource_type="CompileJob",
                resource_id=compile_job_id,
                space_id=job["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "input_fingerprint": job["input_fingerprint"],
                    "stats": summary.get("stats", {}),
                },
            )
            source_ids = (
                (
                    await connection.execute(
                        text(
                            "SELECT source_version_id FROM compile_job_sources WHERE compile_job_id=:id ORDER BY input_order"
                        ),
                        {"id": compile_job_id},
                    )
                )
                .scalars()
                .all()
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.compile.completed.v1",
                aggregate_type="CompileJob",
                aggregate_id=compile_job_id,
                aggregate_version=int(job["version"]) + 1,
                space_id=job["space_id"],
                trace_id=trace_id,
                payload={
                    "compile_job_id": str(compile_job_id),
                    "schema_version_id": str(job["schema_version_id"]),
                    "composition_checksum": job["composition_checksum"],
                    "prompt_version_id": str(job["prompt_version_id"]),
                    "model_profile_id": str(job["model_profile_id"]),
                    "source_version_ids": [str(value) for value in source_ids],
                    "output_versions": outputs["output_versions"],
                    "stats": outputs["stats"],
                },
            )
            return _json_value(summary)

    async def fail_compile(
        self, *, compile_job_id: UUID, code: str, detail: str, trace_id: str
    ) -> None:
        async with self._database.engine.begin() as connection:
            job = (
                (
                    await connection.execute(
                        text(f"SELECT {JOB_COLUMNS} FROM compile_jobs WHERE id=:id FOR UPDATE"),
                        {"id": compile_job_id},
                    )
                )
                .mappings()
                .first()
            )
            if job is None or job["status"] == "SUCCEEDED":
                return
            now = datetime.now(UTC)
            await connection.execute(
                text(
                    "UPDATE compile_jobs SET status='FAILED',error_code=:code,error_detail=:detail,version=version+1,updated_at=:now WHERE id=:id"
                ),
                {"code": code, "detail": detail[:1024], "now": now, "id": compile_job_id},
            )
            await connection.execute(
                text(
                    "UPDATE compile_steps SET status='FAILED',error_code=:code,completed_at=:now WHERE compile_job_id=:id AND status='RUNNING'"
                ),
                {"code": code, "now": now, "id": compile_job_id},
            )
            await self._insert_audit(
                connection,
                principal=self._job_principal(dict(job)),
                action="compile.execute",
                resource_type="CompileJob",
                resource_id=compile_job_id,
                space_id=job["space_id"],
                trace_id=trace_id,
                outcome="FAILED",
                metadata={"error_code": code},
            )

    async def _start_compile_step(
        self, connection: AsyncConnection, job: Mapping[str, Any], step_key: str, now: datetime
    ) -> UUID:
        checksum = sha256_checksum(
            canonical_json(
                {"job": str(job["id"]), "fingerprint": job["input_fingerprint"], "step": step_key}
            )
        )
        existing = (
            (
                await connection.execute(
                    text(
                        "SELECT id,status FROM compile_steps WHERE compile_job_id=:job AND step_key=:step AND input_checksum=:checksum FOR UPDATE"
                    ),
                    {"job": job["id"], "step": step_key, "checksum": checksum},
                )
            )
            .mappings()
            .first()
        )
        if existing is not None:
            await connection.execute(
                text(
                    "UPDATE compile_steps SET status='RUNNING',attempt=attempt+1,started_at=:now,completed_at=NULL,error_code=NULL WHERE id=:id"
                ),
                {"now": now, "id": existing["id"]},
            )
            return UUID(str(existing["id"]))
        step_id = new_uuid7()
        await connection.execute(
            text(
                "INSERT INTO compile_steps (id,tenant_id,space_id,compile_job_id,step_key,input_checksum,"
                "status,attempt,output_summary,started_at,created_at) VALUES "
                "(:id,:tenant,:space,:job,:step,:checksum,'RUNNING',1,'{}'::jsonb,:now,:now)"
            ),
            {
                "id": step_id,
                "tenant": job["tenant_id"],
                "space": job["space_id"],
                "job": job["id"],
                "step": step_key,
                "checksum": checksum,
                "now": now,
            },
        )
        return step_id

    async def _load_compile_context(
        self, connection: AsyncConnection, compile_job_id: UUID
    ) -> dict[str, Any]:
        job = (
            (
                await connection.execute(
                    text(
                        f"SELECT {JOB_COLUMNS_QUALIFIED},sv.normalized_snapshot AS schema_snapshot,"
                        "mp.config AS model_config,mp.provider AS model_provider FROM compile_jobs cj "
                        "JOIN schema_versions sv ON sv.id=cj.schema_version_id "
                        "JOIN model_profiles mp ON mp.id=cj.model_profile_id WHERE cj.id=:id"
                    ),
                    {"id": compile_job_id},
                )
            )
            .mappings()
            .one()
        )
        source_rows = (
            (
                await connection.execute(
                    text(
                        "SELECT cjs.source_version_id,cjs.parse_job_id,sv.classification FROM compile_job_sources cjs "
                        "JOIN source_versions sv ON sv.id=cjs.source_version_id WHERE cjs.compile_job_id=:job ORDER BY cjs.input_order"
                    ),
                    {"job": compile_job_id},
                )
            )
            .mappings()
            .all()
        )
        segments: list[dict[str, Any]] = []
        for source in source_rows:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT ds.id,ds.normalized_text,ds.text_checksum,ds.locators,"
                            "(SELECT sa.id FROM source_anchors sa WHERE sa.source_version_id=ds.source_version_id "
                            "AND sa.parse_job_id=ds.parse_job_id AND sa.excerpt_hash=ds.text_checksum AND sa.status='VALID' "
                            "ORDER BY sa.created_at,sa.id LIMIT 1) AS anchor_id "
                            "FROM document_segments ds WHERE ds.source_version_id=:source AND ds.parse_job_id=:parse "
                            "AND ds.status='VALID' ORDER BY ds.sequence,ds.id"
                        ),
                        {"source": source["source_version_id"], "parse": source["parse_job_id"]},
                    )
                )
                .mappings()
                .all()
            )
            segments.extend(
                {
                    "id": str(row["id"]),
                    "normalized_text": str(row["normalized_text"]),
                    "text_checksum": str(row["text_checksum"]),
                    "locators": [dict(locator) for locator in row["locators"]],
                    "anchor_id": str(row["anchor_id"]) if row["anchor_id"] else None,
                }
                for row in rows
            )
        levels = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "HIGHLY_RESTRICTED": 3}
        classification = max(
            (str(row["classification"]) for row in source_rows), key=lambda value: levels[value]
        )
        return {
            "job": job,
            "schema_snapshot": job["schema_snapshot"],
            "model_config": job["model_config"],
            "model_provider": job["model_provider"],
            "segments": segments,
            "classification": classification,
        }

    async def _persist_compile_output(
        self,
        connection: AsyncConnection,
        *,
        job: Mapping[str, Any],
        output: Mapping[str, Any],
        trace_id: str,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        actor = job["created_by"]
        entity_ids: dict[str, UUID] = {}
        page_by_entity: dict[UUID, UUID] = {}
        entity_version_ids: list[str] = []
        page_ids: list[str] = []
        page_version_ids: list[str] = []
        snapshot = (
            await connection.execute(
                text("SELECT normalized_snapshot FROM schema_versions WHERE id=:id"),
                {"id": job["schema_version_id"]},
            )
        ).scalar_one()
        template_key = str(
            (snapshot.get("templates") or [{"key": "nexweave.io/default-page"}])[0]["key"]
        )
        for item in output.get("entities", []):
            identity = f"{item['type_key']}:{item['normalized_key']}"
            entity_row = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM knowledge_entities WHERE space_id=:space AND schema_version_id=:schema AND type_key=:type AND normalized_key=:key FOR UPDATE"
                        ),
                        {
                            "space": job["space_id"],
                            "schema": job["schema_version_id"],
                            "type": item["type_key"],
                            "key": item["normalized_key"],
                        },
                    )
                )
                .mappings()
                .first()
            )
            entity: Mapping[str, Any]
            if entity_row is None:
                entity_id = new_uuid7()
                await connection.execute(
                    text(
                        "INSERT INTO knowledge_entities (id,tenant_id,space_id,schema_version_id,type_key,"
                        "normalized_key,display_name,status,version,created_at,created_by,updated_at,updated_by) "
                        "VALUES (:id,:tenant,:space,:schema,:type,:key,:display,'DRAFT',1,:now,:actor,:now,:actor)"
                    ),
                    {
                        "id": entity_id,
                        "tenant": job["tenant_id"],
                        "space": job["space_id"],
                        "schema": job["schema_version_id"],
                        "type": item["type_key"],
                        "key": item["normalized_key"],
                        "display": item["display_name"],
                        "now": now,
                        "actor": actor,
                    },
                )
                entity = {"id": entity_id, "current_version_id": None}
            else:
                entity = dict(entity_row)
            entity_id = UUID(str(entity["id"]))
            entity_ids[identity] = entity_id
            content_checksum = sha256_checksum(
                canonical_json({"attributes": item["attributes"], "aliases": item["aliases"]})
            )
            existing_version = (
                await connection.execute(
                    text(
                        "SELECT id FROM knowledge_entity_versions WHERE entity_id=:entity AND content_checksum=:checksum"
                    ),
                    {"entity": entity_id, "checksum": content_checksum},
                )
            ).scalar_one_or_none()
            if existing_version is None:
                revision = int(
                    (
                        await connection.execute(
                            text(
                                "SELECT COALESCE(MAX(revision),0)+1 FROM knowledge_entity_versions WHERE entity_id=:entity"
                            ),
                            {"entity": entity_id},
                        )
                    ).scalar_one()
                )
                entity_version_id = new_uuid7()
                provenance = {
                    "compile_job_id": str(job["id"]),
                    "schema_version_id": str(job["schema_version_id"]),
                    "prompt_version_id": str(job["prompt_version_id"]),
                    "model_profile_id": str(job["model_profile_id"]),
                    "segment_id": item["segment_id"],
                    "source_anchor_id": item.get("anchor_id"),
                }
                await connection.execute(
                    text(
                        "INSERT INTO knowledge_entity_versions (id,tenant_id,space_id,entity_id,compile_job_id,revision,attributes,aliases,provenance,content_checksum,status,created_at,created_by) VALUES (:id,:tenant,:space,:entity,:job,:revision,CAST(:attributes AS jsonb),CAST(:aliases AS jsonb),CAST(:provenance AS jsonb),:checksum,'AI_DRAFT',:now,:actor)"
                    ),
                    {
                        "id": entity_version_id,
                        "tenant": job["tenant_id"],
                        "space": job["space_id"],
                        "entity": entity_id,
                        "job": job["id"],
                        "revision": revision,
                        "attributes": json.dumps(item["attributes"]),
                        "aliases": json.dumps(item["aliases"]),
                        "provenance": json.dumps(provenance),
                        "checksum": content_checksum,
                        "now": now,
                        "actor": actor,
                    },
                )
                await connection.execute(
                    text(
                        "UPDATE knowledge_entities SET current_version_id=:version,display_name=:display,version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
                    ),
                    {
                        "version": entity_version_id,
                        "display": item["display_name"],
                        "now": now,
                        "actor": actor,
                        "id": entity_id,
                    },
                )
                entity_version_ids.append(str(entity_version_id))
            page, page_version = await self._upsert_compiled_page(
                connection,
                job=job,
                entity_id=entity_id,
                entity=item,
                template_key=template_key,
                now=now,
            )
            page_ids.append(str(page))
            page_by_entity[entity_id] = page
            if page_version is not None:
                page_version_ids.append(str(page_version))

        claim_ids: list[str] = []
        evidence_ids: list[str] = []
        conflict_ids: list[str] = []
        for item in output.get("claims", []):
            claim_entity_id = entity_ids.get(str(item["entity_key"]))
            if claim_entity_id is None:
                continue
            prior_claim = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,compile_job_id,statement FROM claim_candidates "
                            "WHERE tenant_id=:tenant AND space_id=:space AND subject_entity_id=:entity "
                            "AND predicate_key=:predicate AND statement<>:statement "
                            "ORDER BY created_at DESC,id DESC LIMIT 1"
                        ),
                        {
                            "tenant": job["tenant_id"],
                            "space": job["space_id"],
                            "entity": claim_entity_id,
                            "predicate": item["predicate_key"],
                            "statement": item["statement"],
                        },
                    )
                )
                .mappings()
                .first()
            )
            claim_id = new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO claim_candidates (id,tenant_id,space_id,compile_job_id,schema_version_id,subject_entity_id,predicate_key,object_value,statement,status,provenance,created_at,created_by) VALUES (:id,:tenant,:space,:job,:schema,:entity,:predicate,CAST(:object AS jsonb),:statement,:status,CAST(:provenance AS jsonb),:now,:actor) ON CONFLICT DO NOTHING"
                ),
                {
                    "id": claim_id,
                    "tenant": job["tenant_id"],
                    "space": job["space_id"],
                    "job": job["id"],
                    "schema": job["schema_version_id"],
                    "entity": claim_entity_id,
                    "predicate": item["predicate_key"],
                    "object": json.dumps(item["object_value"]),
                    "statement": item["statement"],
                    "status": "CANDIDATE" if item.get("anchor_id") else "NEEDS_EVIDENCE",
                    "provenance": json.dumps(
                        {"compile_job_id": str(job["id"]), "segment_id": item["segment_id"]}
                    ),
                    "now": now,
                    "actor": actor,
                },
            )
            inserted = (
                await connection.execute(
                    text(
                        "SELECT id FROM claim_candidates WHERE compile_job_id=:job AND subject_entity_id=:entity AND predicate_key=:predicate AND statement=:statement"
                    ),
                    {
                        "job": job["id"],
                        "entity": claim_entity_id,
                        "predicate": item["predicate_key"],
                        "statement": item["statement"],
                    },
                )
            ).scalar_one()
            claim_ids.append(str(inserted))
            if prior_claim is not None:
                conflict_id = new_uuid7()
                await connection.execute(
                    text(
                        "INSERT INTO conflict_candidates (id,tenant_id,space_id,compile_job_id,code,severity,object_type,object_id,details,status,created_at) "
                        "VALUES (:id,:tenant,:space,:job,'CLAIM_VALUE_CONFLICT','WARNING','ClaimCandidate',:object,CAST(:details AS jsonb),'OPEN',:now)"
                    ),
                    {
                        "id": conflict_id,
                        "tenant": job["tenant_id"],
                        "space": job["space_id"],
                        "job": job["id"],
                        "object": UUID(str(inserted)),
                        "details": json.dumps(
                            {
                                "left_claim_candidate_id": str(prior_claim["id"]),
                                "left_compile_job_id": str(prior_claim["compile_job_id"]),
                                "left_statement": str(prior_claim["statement"]),
                                "right_claim_candidate_id": str(inserted),
                                "right_statement": str(item["statement"]),
                            }
                        ),
                        "now": now,
                    },
                )
                conflict_ids.append(str(conflict_id))
            if item.get("anchor_id"):
                evidence = await self._insert_evidence(
                    connection,
                    job,
                    claim_id=UUID(str(inserted)),
                    relation_id=None,
                    anchor_id=UUID(str(item["anchor_id"])),
                    now=now,
                )
                if evidence:
                    evidence_ids.append(str(evidence))
            else:
                await self._insert_lint(
                    connection,
                    job,
                    "EVIDENCE_INSUFFICIENT",
                    "ERROR",
                    "ClaimCandidate",
                    UUID(str(inserted)),
                    {"reason": "No VALID SourceAnchor"},
                    now,
                )

        relation_ids: list[str] = []
        for item in output.get("relations", []):
            source_id, target_id = (
                entity_ids.get(str(item["source_entity_key"])),
                entity_ids.get(str(item["target_entity_key"])),
            )
            if source_id is None or target_id is None:
                continue
            relation_id = new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO candidate_relations (id,tenant_id,space_id,compile_job_id,schema_version_id,relation_type_key,source_entity_id,target_entity_id,source_anchor_id,status,confidence,provenance,created_at,created_by) VALUES (:id,:tenant,:space,:job,:schema,:key,:source,:target,:anchor,:status,1.0,CAST(:provenance AS jsonb),:now,:actor) ON CONFLICT DO NOTHING"
                ),
                {
                    "id": relation_id,
                    "tenant": job["tenant_id"],
                    "space": job["space_id"],
                    "job": job["id"],
                    "schema": job["schema_version_id"],
                    "key": item["relation_type_key"],
                    "source": source_id,
                    "target": target_id,
                    "anchor": UUID(str(item["anchor_id"])) if item.get("anchor_id") else None,
                    "status": "CANDIDATE" if item.get("anchor_id") else "NEEDS_EVIDENCE",
                    "provenance": json.dumps(
                        {"compile_job_id": str(job["id"]), "segment_id": item["segment_id"]}
                    ),
                    "now": now,
                    "actor": actor,
                },
            )
            inserted = (
                await connection.execute(
                    text(
                        "SELECT id FROM candidate_relations WHERE compile_job_id=:job AND relation_type_key=:key AND source_entity_id=:source AND target_entity_id=:target AND source_anchor_id IS NOT DISTINCT FROM :anchor"
                    ),
                    {
                        "job": job["id"],
                        "key": item["relation_type_key"],
                        "source": source_id,
                        "target": target_id,
                        "anchor": UUID(str(item["anchor_id"])) if item.get("anchor_id") else None,
                    },
                )
            ).scalar_one()
            relation_ids.append(str(inserted))
            source_page = page_by_entity.get(source_id)
            target_page = page_by_entity.get(target_id)
            if source_page is not None and target_page is not None and source_page != target_page:
                await connection.execute(
                    text(
                        "INSERT INTO wiki_page_links (id,tenant_id,space_id,source_page_id,target_page_id,link_kind,created_at,created_by) "
                        "VALUES (:id,:tenant,:space,:source,:target,'SCHEMA_RELATION',:now,:actor) "
                        "ON CONFLICT (source_page_id,target_page_id,link_kind) DO NOTHING"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": job["tenant_id"],
                        "space": job["space_id"],
                        "source": source_page,
                        "target": target_page,
                        "now": now,
                        "actor": actor,
                    },
                )
            if item.get("anchor_id"):
                evidence = await self._insert_evidence(
                    connection,
                    job,
                    claim_id=None,
                    relation_id=UUID(str(inserted)),
                    anchor_id=UUID(str(item["anchor_id"])),
                    now=now,
                )
                if evidence:
                    evidence_ids.append(str(evidence))

        for proposal in output.get("semantic_proposals", []):
            await connection.execute(
                text(
                    "INSERT INTO semantic_change_proposals (id,tenant_id,space_id,compile_job_id,schema_version_id,proposal_kind,candidate_key,term,proposal,status,created_at,created_by) VALUES (:id,:tenant,:space,:job,:schema,:kind,:key,:term,CAST(:proposal AS jsonb),'CANDIDATE',:now,:actor) ON CONFLICT DO NOTHING"
                ),
                {
                    "id": new_uuid7(),
                    "tenant": job["tenant_id"],
                    "space": job["space_id"],
                    "job": job["id"],
                    "schema": job["schema_version_id"],
                    "kind": proposal["proposal_kind"],
                    "key": proposal.get("candidate_key"),
                    "term": proposal["term"],
                    "proposal": json.dumps(proposal["proposal"]),
                    "now": now,
                    "actor": actor,
                },
            )
        stats = {
            "entities": len(entity_ids),
            "entity_versions_created": len(entity_version_ids),
            "pages": len(set(page_ids)),
            "page_versions_created": len(page_version_ids),
            "claims": len(claim_ids),
            "relations": len(relation_ids),
            "evidence_candidates": len(evidence_ids),
            "conflicts": len(conflict_ids),
        }
        return {
            "stats": stats,
            "output_versions": {
                "entity_versions": entity_version_ids,
                "wiki_page_versions": page_version_ids,
                "claims": claim_ids,
                "relations": relation_ids,
                "evidence_candidates": evidence_ids,
                "conflicts": conflict_ids,
            },
            "page_ids": sorted(set(page_ids)),
        }

    async def _upsert_compiled_page(
        self,
        connection: AsyncConnection,
        *,
        job: Mapping[str, Any],
        entity_id: UUID,
        entity: Mapping[str, Any],
        template_key: str,
        now: datetime,
    ) -> tuple[UUID, UUID | None]:
        page_row = (
            (
                await connection.execute(
                    text(
                        "SELECT * FROM wiki_pages WHERE space_id=:space AND primary_entity_id=:entity AND template_key=:template FOR UPDATE"
                    ),
                    {"space": job["space_id"], "entity": entity_id, "template": template_key},
                )
            )
            .mappings()
            .first()
        )
        page: Mapping[str, Any]
        if page_row is None:
            page_id = new_uuid7()
            slug = f"{str(entity['normalized_key'])[:220]}-{str(entity_id)[:8]}"
            await connection.execute(
                text(
                    "INSERT INTO wiki_pages (id,tenant_id,space_id,schema_version_id,primary_entity_id,template_key,slug,title,status,version,created_at,created_by,updated_at,updated_by) VALUES (:id,:tenant,:space,:schema,:entity,:template,:slug,:title,'DRAFT',1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": page_id,
                    "tenant": job["tenant_id"],
                    "space": job["space_id"],
                    "schema": job["schema_version_id"],
                    "entity": entity_id,
                    "template": template_key,
                    "slug": slug,
                    "title": entity["display_name"],
                    "now": now,
                    "actor": job["created_by"],
                },
            )
            page = {"id": page_id, "current_version_id": None}
        else:
            page = dict(page_row)
        page_id = UUID(str(page["id"]))
        protected: dict[str, str] = {}
        properties: dict[str, Any] = {
            "type_key": entity["type_key"],
            "entity_id": str(entity_id),
            "schema_version_id": str(job["schema_version_id"]),
        }
        if page.get("current_version_id"):
            current = (
                (
                    await connection.execute(
                        text(
                            "SELECT protected_sections,properties FROM wiki_page_versions WHERE id=:id"
                        ),
                        {"id": page["current_version_id"]},
                    )
                )
                .mappings()
                .one()
            )
            protected = dict(current["protected_sections"])
            properties = {**dict(current["properties"]), **properties}
        generated, protected = merge_recompiled_page(
            generated_sections={
                "概览": str(entity["attributes"].get("source_excerpt", entity["display_name"]))
            },
            existing_protected_sections=protected,
            ai_generated=True,
        )
        markdown = render_wiki_markdown(
            title=str(entity["display_name"]),
            generated_sections=generated,
            protected_sections=protected,
        )
        checksum = sha256_checksum(
            canonical_json(
                {
                    "generated": generated,
                    "protected": protected,
                    "properties": properties,
                    "markdown": markdown,
                }
            )
        )
        existing = (
            await connection.execute(
                text(
                    "SELECT id FROM wiki_page_versions WHERE wiki_page_id=:page AND content_checksum=:checksum"
                ),
                {"page": page_id, "checksum": checksum},
            )
        ).scalar_one_or_none()
        if existing is not None:
            return page_id, None
        revision = int(
            (
                await connection.execute(
                    text(
                        "SELECT COALESCE(MAX(revision),0)+1 FROM wiki_page_versions WHERE wiki_page_id=:page"
                    ),
                    {"page": page_id},
                )
            ).scalar_one()
        )
        version_id = new_uuid7()
        await connection.execute(
            text(
                "INSERT INTO wiki_page_versions (id,tenant_id,space_id,wiki_page_id,compile_job_id,revision,generated_sections,protected_sections,properties,markdown,content_checksum,status,edit_reason,created_at,created_by) VALUES (:id,:tenant,:space,:page,:job,:revision,CAST(:generated AS jsonb),CAST(:protected AS jsonb),CAST(:properties AS jsonb),:markdown,:checksum,'AI_DRAFT','M5 deterministic compile',:now,:actor)"
            ),
            {
                "id": version_id,
                "tenant": job["tenant_id"],
                "space": job["space_id"],
                "page": page_id,
                "job": job["id"],
                "revision": revision,
                "generated": json.dumps(generated),
                "protected": json.dumps(protected),
                "properties": json.dumps(properties),
                "markdown": markdown,
                "checksum": checksum,
                "now": now,
                "actor": job["created_by"],
            },
        )
        await connection.execute(
            text(
                "UPDATE wiki_pages SET current_version_id=:version,title=:title,version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
            ),
            {
                "version": version_id,
                "title": entity["display_name"],
                "now": now,
                "actor": job["created_by"],
                "id": page_id,
            },
        )
        return page_id, version_id

    async def _insert_evidence(
        self,
        connection: AsyncConnection,
        job: Mapping[str, Any],
        *,
        claim_id: UUID | None,
        relation_id: UUID | None,
        anchor_id: UUID,
        now: datetime,
    ) -> UUID | None:
        excerpt = (
            await connection.execute(
                text("SELECT excerpt_hash FROM source_anchors WHERE id=:id AND status='VALID'"),
                {"id": anchor_id},
            )
        ).scalar_one_or_none()
        if excerpt is None:
            return None
        existing = (
            await connection.execute(
                text(
                    "SELECT id FROM evidence_candidates WHERE compile_job_id=:job AND claim_candidate_id IS NOT DISTINCT FROM :claim AND relation_candidate_id IS NOT DISTINCT FROM :relation AND source_anchor_id=:anchor"
                ),
                {"job": job["id"], "claim": claim_id, "relation": relation_id, "anchor": anchor_id},
            )
        ).scalar_one_or_none()
        if existing is not None:
            return UUID(str(existing))
        evidence_id = new_uuid7()
        await connection.execute(
            text(
                "INSERT INTO evidence_candidates (id,tenant_id,space_id,compile_job_id,claim_candidate_id,relation_candidate_id,source_anchor_id,stance,excerpt_hash,status,created_at,created_by) VALUES (:id,:tenant,:space,:job,:claim,:relation,:anchor,'SUPPORTS',:excerpt,'CANDIDATE',:now,:actor)"
            ),
            {
                "id": evidence_id,
                "tenant": job["tenant_id"],
                "space": job["space_id"],
                "job": job["id"],
                "claim": claim_id,
                "relation": relation_id,
                "anchor": anchor_id,
                "excerpt": excerpt,
                "now": now,
                "actor": job["created_by"],
            },
        )
        return evidence_id

    async def _insert_lint(
        self,
        connection: AsyncConnection,
        job: Mapping[str, Any],
        code: str,
        severity: str,
        object_type: str,
        object_id: UUID | None,
        details: Mapping[str, Any],
        now: datetime,
    ) -> None:
        await connection.execute(
            text(
                "INSERT INTO lint_findings (id,tenant_id,space_id,compile_job_id,code,severity,object_type,object_id,details,status,created_at) VALUES (:id,:tenant,:space,:job,:code,:severity,:type,:object,CAST(:details AS jsonb),'OPEN',:now)"
            ),
            {
                "id": new_uuid7(),
                "tenant": job["tenant_id"],
                "space": job["space_id"],
                "job": job["id"],
                "code": code,
                "severity": severity,
                "type": object_type,
                "object": object_id,
                "details": json.dumps(dict(details)),
                "now": now,
            },
        )

    async def list_entities(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,tenant_id,space_id,schema_version_id,type_key,normalized_key,display_name,status,current_version_id,version,created_at,created_by,updated_at,updated_by FROM knowledge_entities WHERE tenant_id=:tenant AND space_id=:space ORDER BY display_name,id"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def list_wiki_pages(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {PAGE_COLUMNS} FROM wiki_pages WHERE tenant_id=:tenant AND space_id=:space ORDER BY title,id"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def get_wiki_link_graph(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        focus_page_id: UUID | None,
        max_depth: int,
        node_limit: int,
    ) -> JsonDict:
        """Build a bounded Wiki-link navigation projection from existing link facts."""
        page_statement = text(
            f"SELECT {PAGE_COLUMNS} FROM wiki_pages "
            "WHERE tenant_id=:tenant AND space_id=:space AND id IN :ids"
        ).bindparams(bindparam("ids", expanding=True))
        async with self._database.engine.connect() as connection:
            truncated = False
            if focus_page_id is None:
                page_rows = (
                    (
                        await connection.execute(
                            text(
                                f"SELECT {PAGE_COLUMNS} FROM wiki_pages "
                                "WHERE tenant_id=:tenant AND space_id=:space "
                                "ORDER BY title,id LIMIT :limit"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "space": space_id,
                                "limit": node_limit + 1,
                            },
                        )
                    )
                    .mappings()
                    .all()
                )
                truncated = len(page_rows) > node_limit
                page_rows = page_rows[:node_limit]
                node_ids = {UUID(str(row["id"])) for row in page_rows}
                link_rows: list[Any] = []
                if node_ids:
                    link_statement = text(
                        "SELECT id,source_page_id,target_page_id,link_kind "
                        "FROM wiki_page_links WHERE tenant_id=:tenant AND space_id=:space "
                        "AND source_page_id IN :ids AND target_page_id IN :ids "
                        "ORDER BY created_at,id"
                    ).bindparams(bindparam("ids", expanding=True))
                    link_rows = list(
                        (
                            await connection.execute(
                                link_statement,
                                {
                                    "tenant": principal.tenant_id,
                                    "space": space_id,
                                    "ids": list(node_ids),
                                },
                            )
                        )
                        .mappings()
                        .all()
                    )
            else:
                focused = (
                    (
                        await connection.execute(
                            text(
                                f"SELECT {PAGE_COLUMNS} FROM wiki_pages "
                                "WHERE tenant_id=:tenant AND space_id=:space AND id=:id"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "space": space_id,
                                "id": focus_page_id,
                            },
                        )
                    )
                    .mappings()
                    .first()
                )
                if focused is None:
                    raise ApiProblem(
                        404,
                        "RESOURCE_NOT_FOUND",
                        "Wiki page not found",
                        "The requested graph focus page is unavailable in this space.",
                    )
                link_cap = min(node_limit * 20, 5_000)
                all_links = (
                    (
                        await connection.execute(
                            text(
                                "SELECT id,source_page_id,target_page_id,link_kind "
                                "FROM wiki_page_links WHERE tenant_id=:tenant AND space_id=:space "
                                "ORDER BY created_at,id LIMIT :limit"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "space": space_id,
                                "limit": link_cap + 1,
                            },
                        )
                    )
                    .mappings()
                    .all()
                )
                if len(all_links) > link_cap:
                    truncated = True
                    all_links = all_links[:link_cap]
                adjacency: dict[UUID, set[UUID]] = {}
                for link in all_links:
                    source, target = (
                        UUID(str(link["source_page_id"])),
                        UUID(str(link["target_page_id"])),
                    )
                    adjacency.setdefault(source, set()).add(target)
                    adjacency.setdefault(target, set()).add(source)
                node_ids = {focus_page_id}
                frontier = {focus_page_id}
                for _ in range(max_depth):
                    next_frontier: set[UUID] = set()
                    for node_id in frontier:
                        for neighbor in sorted(adjacency.get(node_id, set()), key=str):
                            if neighbor in node_ids:
                                continue
                            if len(node_ids) >= node_limit:
                                truncated = True
                                break
                            node_ids.add(neighbor)
                            next_frontier.add(neighbor)
                        if len(node_ids) >= node_limit:
                            break
                    frontier = next_frontier
                    if not frontier:
                        break
                page_rows = (
                    (
                        await connection.execute(
                            page_statement,
                            {
                                "tenant": principal.tenant_id,
                                "space": space_id,
                                "ids": list(node_ids),
                            },
                        )
                    )
                    .mappings()
                    .all()
                )
                node_ids = {UUID(str(row["id"])) for row in page_rows}
                link_rows = [
                    link
                    for link in all_links
                    if UUID(str(link["source_page_id"])) in node_ids
                    and UUID(str(link["target_page_id"])) in node_ids
                ]
        outbound_counts = {node_id: 0 for node_id in node_ids}
        backlink_counts = {node_id: 0 for node_id in node_ids}
        for link in link_rows:
            outbound_counts[UUID(str(link["source_page_id"]))] += 1
            backlink_counts[UUID(str(link["target_page_id"]))] += 1
        nodes = [
            {
                "id": row["id"],
                "title": row["title"],
                "template_key": row["template_key"],
                "status": row["status"],
                "version": row["version"],
                "updated_at": row["updated_at"],
                "outbound_count": outbound_counts[UUID(str(row["id"]))],
                "backlink_count": backlink_counts[UUID(str(row["id"]))],
            }
            for row in sorted(page_rows, key=lambda item: (str(item["title"]), str(item["id"])))
        ]
        return _json_value(
            {
                "space_id": space_id,
                "focus_page_id": focus_page_id,
                "max_depth": max_depth,
                "node_limit": node_limit,
                "truncated": truncated,
                "nodes": nodes,
                "edges": [dict(link) for link in link_rows],
            }
        )

    async def get_wiki_page(self, *, principal: Principal, page_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            page = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {PAGE_COLUMNS} FROM wiki_pages WHERE tenant_id=:tenant AND id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": page_id},
                    )
                )
                .mappings()
                .first()
            )
            if page is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Wiki page not found",
                    "The Wiki page is unavailable.",
                )
            current = None
            if page["current_version_id"]:
                current = (
                    (
                        await connection.execute(
                            text(
                                f"SELECT {PAGE_VERSION_COLUMNS} FROM wiki_page_versions WHERE id=:id"
                            ),
                            {"id": page["current_version_id"]},
                        )
                    )
                    .mappings()
                    .one()
                )
            outbound = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,target_page_id,link_kind FROM wiki_page_links WHERE source_page_id=:id"
                        ),
                        {"id": page_id},
                    )
                )
                .mappings()
                .all()
            )
            backlinks = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,source_page_id,link_kind FROM wiki_page_links WHERE target_page_id=:id"
                        ),
                        {"id": page_id},
                    )
                )
                .mappings()
                .all()
            )
            comments = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,wiki_page_id,body,status,created_at,created_by FROM wiki_page_comments WHERE wiki_page_id=:id ORDER BY created_at,id"
                        ),
                        {"id": page_id},
                    )
                )
                .mappings()
                .all()
            )
            evidence = (
                (
                    await connection.execute(
                        text(
                            "SELECT ec.id,ec.claim_candidate_id,ec.relation_candidate_id,"
                            "ec.source_anchor_id,ec.stance,ec.excerpt_hash,ec.status "
                            "FROM evidence_candidates ec "
                            "LEFT JOIN claim_candidates cc ON cc.id=ec.claim_candidate_id "
                            "LEFT JOIN candidate_relations cr ON cr.id=ec.relation_candidate_id "
                            "WHERE cc.subject_entity_id=:entity OR cr.source_entity_id=:entity "
                            "OR cr.target_entity_id=:entity ORDER BY ec.created_at,ec.id"
                        ),
                        {"entity": page["primary_entity_id"]},
                    )
                )
                .mappings()
                .all()
            )
            followed = (
                await connection.execute(
                    text(
                        "SELECT 1 FROM wiki_page_follows WHERE wiki_page_id=:page AND actor_id=:actor"
                    ),
                    {"page": page_id, "actor": principal.actor_id},
                )
            ).first() is not None
        return _json_value(
            {
                **page,
                "current_version": dict(current) if current is not None else None,
                "outbound_links": [dict(link) for link in outbound],
                "backlinks": [dict(link) for link in backlinks],
                "comments": [dict(comment) for comment in comments],
                "evidence_candidates": [dict(item) for item in evidence],
                "followed": followed,
            }
        )

    async def list_wiki_page_versions(
        self, *, principal: Principal, page_id: UUID
    ) -> list[JsonDict]:
        page = await self.get_wiki_page(principal=principal, page_id=page_id)
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {PAGE_VERSION_COLUMNS} FROM wiki_page_versions "
                            "WHERE wiki_page_id=:page ORDER BY revision DESC"
                        ),
                        {"page": page_id},
                    )
                )
                .mappings()
                .all()
            )
        if UUID(str(page["tenant_id"])) != principal.tenant_id:
            return []
        return [_json_value(row) for row in rows]

    async def get_wiki_page_version(
        self, *, principal: Principal, page_id: UUID, version_id: UUID
    ) -> JsonDict:
        versions = await self.list_wiki_page_versions(principal=principal, page_id=page_id)
        selected = next((item for item in versions if UUID(str(item["id"])) == version_id), None)
        if selected is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Wiki version not found",
                "The requested Wiki page version is unavailable.",
            )
        return selected

    async def edit_wiki_page(
        self,
        *,
        principal: Principal,
        page_id: UUID,
        expected_version: int,
        payload: Mapping[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        async def mutation(connection: AsyncConnection) -> JsonDict:
            page = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {PAGE_COLUMNS} FROM wiki_pages WHERE tenant_id=:tenant AND id=:id FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "id": page_id},
                    )
                )
                .mappings()
                .first()
            )
            if page is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Wiki page not found",
                    "The Wiki page is unavailable.",
                )
            if int(page["version"]) != expected_version:
                raise ApiProblem(
                    412,
                    "VERSION_CONFLICT",
                    "Wiki version conflict",
                    "The Wiki page has changed; reload before editing.",
                )
            current = (
                (
                    await connection.execute(
                        text(f"SELECT {PAGE_VERSION_COLUMNS} FROM wiki_page_versions WHERE id=:id"),
                        {"id": page["current_version_id"]},
                    )
                )
                .mappings()
                .one()
            )
            generated, protected = merge_recompiled_page(
                generated_sections=dict(current["generated_sections"]),
                existing_protected_sections=dict(current["protected_sections"]),
                requested_protected_sections=dict(payload.get("protected_sections", {})),
                ai_generated=False,
            )
            properties = {**dict(current["properties"]), **dict(payload.get("properties", {}))}
            title = str(payload.get("title") or page["title"])
            markdown = render_wiki_markdown(
                title=title, generated_sections=generated, protected_sections=protected
            )
            checksum = sha256_checksum(
                canonical_json(
                    {
                        "generated": generated,
                        "protected": protected,
                        "properties": properties,
                        "markdown": markdown,
                    }
                )
            )
            version_id, now = new_uuid7(), datetime.now(UTC)
            revision = int(current["revision"]) + 1
            await connection.execute(
                text(
                    "INSERT INTO wiki_page_versions (id,tenant_id,space_id,wiki_page_id,compile_job_id,revision,generated_sections,protected_sections,properties,markdown,content_checksum,status,edit_reason,created_at,created_by) VALUES (:id,:tenant,:space,:page,NULL,:revision,CAST(:generated AS jsonb),CAST(:protected AS jsonb),CAST(:properties AS jsonb),:markdown,:checksum,'EDITING',:reason,:now,:actor)"
                ),
                {
                    "id": version_id,
                    "tenant": page["tenant_id"],
                    "space": page["space_id"],
                    "page": page_id,
                    "revision": revision,
                    "generated": json.dumps(generated),
                    "protected": json.dumps(protected),
                    "properties": json.dumps(properties),
                    "markdown": markdown,
                    "checksum": checksum,
                    "reason": payload["reason"],
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await connection.execute(
                text(
                    "UPDATE wiki_pages SET current_version_id=:current,title=:title,version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {
                    "current": version_id,
                    "title": title,
                    "now": now,
                    "actor": principal.actor_id,
                    "id": page_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="page.edit",
                resource_type="WikiPage",
                resource_id=page_id,
                space_id=page["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"from_version_id": str(current["id"]), "to_version_id": str(version_id)},
            )
            return _json_value(
                {
                    **page,
                    "title": title,
                    "current_version_id": version_id,
                    "version": int(page["version"]) + 1,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                    "current_version": {
                        "id": version_id,
                        "wiki_page_id": page_id,
                        "compile_job_id": None,
                        "revision": revision,
                        "generated_sections": generated,
                        "protected_sections": protected,
                        "properties": properties,
                        "markdown": markdown,
                        "content_checksum": checksum,
                        "status": "EDITING",
                        "edit_reason": payload["reason"],
                        "created_at": now,
                        "created_by": principal.actor_id,
                    },
                    "outbound_links": [],
                    "backlinks": [],
                    "comments": [],
                    "followed": False,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"wiki.edit:{page_id}",
            key=idempotency_key,
            request={**dict(payload), "expected_version": expected_version},
            mutation=mutation,
        )

    async def diff_wiki_page(
        self, *, principal: Principal, page_id: UUID, from_version_id: UUID, to_version_id: UUID
    ) -> JsonDict:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {PAGE_VERSION_COLUMNS} FROM wiki_page_versions WHERE wiki_page_id=:page AND id IN (:old,:new) ORDER BY CASE WHEN id=:old THEN 0 ELSE 1 END"
                        ),
                        {"page": page_id, "old": from_version_id, "new": to_version_id},
                    )
                )
                .mappings()
                .all()
            )
        if len(rows) != 2:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Wiki version not found",
                "Both versions must belong to the requested page.",
            )
        old, new = rows
        return _json_value(
            {
                "page_id": page_id,
                "from_version_id": from_version_id,
                "to_version_id": to_version_id,
                "markdown_diff": "".join(
                    difflib.unified_diff(
                        str(old["markdown"]).splitlines(keepends=True),
                        str(new["markdown"]).splitlines(keepends=True),
                        fromfile=str(from_version_id),
                        tofile=str(to_version_id),
                    )
                ),
                "generated_changed": sorted(
                    set(old["generated_sections"]) ^ set(new["generated_sections"])
                    | {
                        key
                        for key in set(old["generated_sections"]) & set(new["generated_sections"])
                        if old["generated_sections"][key] != new["generated_sections"][key]
                    }
                ),
                "protected_changed": sorted(
                    set(old["protected_sections"]) ^ set(new["protected_sections"])
                    | {
                        key
                        for key in set(old["protected_sections"]) & set(new["protected_sections"])
                        if old["protected_sections"][key] != new["protected_sections"][key]
                    }
                ),
                "properties_changed": sorted(
                    set(old["properties"]) ^ set(new["properties"])
                    | {
                        key
                        for key in set(old["properties"]) & set(new["properties"])
                        if old["properties"][key] != new["properties"][key]
                    }
                ),
            }
        )

    async def add_wiki_comment(
        self, *, principal: Principal, page_id: UUID, body: str, trace_id: str
    ) -> JsonDict:
        page = await self.get_wiki_page(principal=principal, page_id=page_id)
        comment_id, now = new_uuid7(), datetime.now(UTC)
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO wiki_page_comments (id,tenant_id,space_id,wiki_page_id,body,status,created_at,created_by) VALUES (:id,:tenant,:space,:page,:body,'OPEN',:now,:actor)"
                ),
                {
                    "id": comment_id,
                    "tenant": principal.tenant_id,
                    "space": page["space_id"],
                    "page": page_id,
                    "body": body,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="page.comment",
                resource_type="WikiPage",
                resource_id=page_id,
                space_id=UUID(str(page["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"comment_id": str(comment_id)},
            )
        return _json_value(
            {
                "id": comment_id,
                "wiki_page_id": page_id,
                "body": body,
                "status": "OPEN",
                "created_at": now,
                "created_by": principal.actor_id,
            }
        )

    async def set_wiki_follow(
        self, *, principal: Principal, page_id: UUID, follow: bool
    ) -> JsonDict:
        page = await self.get_wiki_page(principal=principal, page_id=page_id)
        async with self._database.engine.begin() as connection:
            if follow:
                await connection.execute(
                    text(
                        "INSERT INTO wiki_page_follows (id,tenant_id,space_id,wiki_page_id,actor_id,created_at) VALUES (:id,:tenant,:space,:page,:actor,:now) ON CONFLICT DO NOTHING"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "space": page["space_id"],
                        "page": page_id,
                        "actor": principal.actor_id,
                        "now": datetime.now(UTC),
                    },
                )
            else:
                await connection.execute(
                    text(
                        "DELETE FROM wiki_page_follows WHERE wiki_page_id=:page AND actor_id=:actor"
                    ),
                    {"page": page_id, "actor": principal.actor_id},
                )
        return {"page_id": str(page_id), "followed": follow}

    def _job_principal(self, job: Mapping[str, Any]) -> Principal:
        return Principal(
            ActorType.USER,
            UUID(str(job["created_by"])),
            UUID(str(job["tenant_id"])),
            "compile-job",
            ("nexweave-api",),
            frozenset(),
            DataClassification.HIGHLY_RESTRICTED,
            f"compile:{job['id']}",
        )
