"""PostgreSQL adapter for the M3 Source/Parse business aggregates."""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_api.repository import JsonDict, _json_value
from nexweave_api.workflow_repository import WorkflowRepository
from nexweave_application import StoredObjectInfo, canonical_request_hash
from nexweave_contracts import ParserConfig, ParseResultManifest
from nexweave_domain import (
    ActorType,
    DataClassification,
    ParseJobStatus,
    Principal,
    SourceDocumentStatus,
    SourceUploadStatus,
    SourceVersionState,
    canonical_raw_key,
    new_uuid7,
)
from nexweave_domain.access import CLASSIFICATION_LEVEL

SOURCE_COLUMNS = (
    "id, tenant_id, space_id, display_name, description, classification, source_level, tags, "
    "valid_until, status, version, created_at, created_by, updated_at, updated_by, archived_at"
)
VERSION_COLUMNS = (
    "id, tenant_id, space_id, source_document_id, filename, content_type, size, checksum, "
    "object_key, object_version_id, classification, status, version, active_parse_job_id, "
    "latest_parse_job_id, supersedes_source_version_id, created_at, created_by"
)
PARSE_COLUMNS = (
    "id, tenant_id, space_id, source_version_id, workflow_task_id, workflow_id, temporal_run_id, "
    "status, version, parser_id, parser_version, config, config_checksum, document_model_version, "
    "locator_version, ocr_provider_id, ocr_provider_version, malware_scan_status, "
    "malware_scanner_provider, malware_scanner_version, malware_policy_version, "
    "result_checksum, result_stats, error_code, error_detail, correlation_id, trace_id, "
    "requested_by_actor_type, created_at, created_by, updated_at, updated_by"
)


class SourceRepository(WorkflowRepository):
    async def create_import_batch(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        display_name: str,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        async def mutation(connection: AsyncConnection) -> JsonDict:
            batch_id, now = new_uuid7(), datetime.now(UTC)
            await connection.execute(
                text(
                    "INSERT INTO source_import_batches "
                    "(id, tenant_id, space_id, display_name, status, version, created_at, "
                    "created_by, updated_at, updated_by) VALUES "
                    "(:id,:tenant,:space,:name,'CREATED',1,:now,:actor,:now,:actor)"
                ),
                {
                    "id": batch_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "name": display_name,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.upload",
                resource_type="ImportBatch",
                resource_id=batch_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "CREATE"},
            )
            return _json_value(
                {
                    "id": batch_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": space_id,
                    "display_name": display_name,
                    "status": "CREATED",
                    "version": 1,
                    "item_summary": {},
                    "created_at": now,
                    "created_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"source_batch.create:{space_id}",
            key=idempotency_key,
            request={"space_id": space_id, "display_name": display_name},
            mutation=mutation,
        )

    async def get_import_batch(self, *, principal: Principal, batch_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            batch = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,tenant_id,space_id,display_name,status,version,created_at,"
                            "created_by FROM source_import_batches "
                            "WHERE tenant_id=:tenant AND id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": batch_id},
                    )
                )
                .mappings()
                .first()
            )
            if batch is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Import batch not found",
                    "The import batch is unavailable.",
                )
            items = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,upload_session_id,source_document_id,source_version_id,"
                            "filename,status,error_code,safe_detail,created_at,updated_at "
                            "FROM source_import_batch_items WHERE tenant_id=:tenant "
                            "AND space_id=:space AND import_batch_id=:batch ORDER BY created_at,id"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": batch["space_id"],
                            "batch": batch_id,
                        },
                    )
                )
                .mappings()
                .all()
            )
        summary: dict[str, int] = {}
        for item in items:
            summary[str(item["status"])] = summary.get(str(item["status"]), 0) + 1
        return _json_value(
            {**batch, "item_summary": summary, "items": [dict(item) for item in items]}
        )

    async def create_source_upload(
        self,
        *,
        principal: Principal,
        space_id: UUID,
        payload: Mapping[str, Any],
        idempotency_key: str,
        ttl_seconds: int,
        trace_id: str,
    ) -> JsonDict:
        source_document_id = (
            UUID(str(payload["source_document_id"]))
            if payload.get("source_document_id")
            else new_uuid7()
        )
        source_version_id, upload_id = new_uuid7(), new_uuid7()
        object_key = canonical_raw_key(
            principal.tenant_id,
            space_id,
            source_document_id,
            source_version_id,
            str(payload["expected_checksum"]),
        )
        request = {"space_id": space_id, **payload}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            if payload.get("import_batch_id"):
                batch = (
                    (
                        await connection.execute(
                            text(
                                "SELECT status FROM source_import_batches "
                                "WHERE tenant_id=:tenant AND space_id=:space AND id=:batch FOR UPDATE"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "space": space_id,
                                "batch": payload["import_batch_id"],
                            },
                        )
                    )
                    .mappings()
                    .first()
                )
                if batch is None:
                    raise ApiProblem(
                        404,
                        "RESOURCE_NOT_FOUND",
                        "Import batch not found",
                        "The import batch is unavailable.",
                    )
                if batch["status"] == "CANCELED":
                    raise ApiProblem(
                        409,
                        "STATE_TRANSITION_NOT_ALLOWED",
                        "Import batch closed",
                        "The import batch no longer accepts upload items.",
                    )
            if payload.get("source_document_id"):
                document = (
                    (
                        await connection.execute(
                            text(
                                "SELECT id,status,classification FROM source_documents "
                                "WHERE tenant_id=:tenant AND space_id=:space AND id=:id FOR SHARE"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "space": space_id,
                                "id": source_document_id,
                            },
                        )
                    )
                    .mappings()
                    .first()
                )
                if document is None:
                    raise ApiProblem(
                        404, "RESOURCE_NOT_FOUND", "Source not found", "The source is unavailable."
                    )
                if document["status"] == "ARCHIVED":
                    raise ApiProblem(
                        409,
                        "STATE_TRANSITION_NOT_ALLOWED",
                        "Source archived",
                        "An archived source cannot receive a new version.",
                    )
                if document["classification"] != payload["classification"]:
                    raise ApiProblem(
                        409,
                        "CLASSIFICATION_CONFLICT",
                        "Source classification conflict",
                        "Every version of a Source must use the Source classification.",
                    )
            if payload.get("supersedes_source_version_id"):
                prior = (
                    (
                        await connection.execute(
                            text(
                                "SELECT id,status FROM source_versions WHERE tenant_id=:tenant "
                                "AND space_id=:space AND source_document_id=:source AND id=:version "
                                "FOR SHARE"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "space": space_id,
                                "source": source_document_id,
                                "version": payload["supersedes_source_version_id"],
                            },
                        )
                    )
                    .mappings()
                    .first()
                )
                if prior is None:
                    raise ApiProblem(
                        409,
                        "VERSION_CONFLICT",
                        "Replacement conflict",
                        "The superseded version does not belong to this source.",
                    )
                if prior["status"] == "SUPERSEDED":
                    raise ApiProblem(
                        409,
                        "VERSION_CONFLICT",
                        "Replacement conflict",
                        "The selected predecessor was already superseded.",
                    )
            now = datetime.now(UTC)
            expires_at = now + timedelta(seconds=ttl_seconds)
            await connection.execute(
                text(
                    "INSERT INTO source_upload_sessions "
                    "(id,tenant_id,space_id,source_document_id,source_version_id,import_batch_id,"
                    "supersedes_source_version_id,filename,content_type,expected_size,"
                    "expected_checksum,object_key,display_name,description,classification,"
                    "source_level,tags,valid_until,status,version,expires_at,created_at,created_by,"
                    "updated_at,updated_by) VALUES "
                    "(:id,:tenant,:space,:source,:source_version,:batch,:supersedes,:filename,"
                    ":content_type,:size,:checksum,:key,:name,:description,:classification,"
                    ":source_level,CAST(:tags AS jsonb),:valid_until,'INITIATED',1,:expires,:now,"
                    ":actor,:now,:actor)"
                ),
                {
                    "id": upload_id,
                    "tenant": principal.tenant_id,
                    "space": space_id,
                    "source": source_document_id,
                    "source_version": source_version_id,
                    "batch": payload.get("import_batch_id"),
                    "supersedes": payload.get("supersedes_source_version_id"),
                    "filename": payload["filename"],
                    "content_type": payload["content_type"],
                    "size": payload["expected_size"],
                    "checksum": payload["expected_checksum"],
                    "key": object_key,
                    "name": payload["display_name"],
                    "description": payload.get("description", ""),
                    "classification": payload["classification"],
                    "source_level": payload.get("source_level"),
                    "tags": json.dumps(payload.get("tags", ())),
                    "valid_until": payload.get("valid_until"),
                    "expires": expires_at,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            if payload.get("import_batch_id"):
                await connection.execute(
                    text(
                        "INSERT INTO source_import_batch_items "
                        "(id,tenant_id,space_id,import_batch_id,upload_session_id,filename,status,"
                        "created_at,created_by,updated_at,updated_by) VALUES "
                        "(:id,:tenant,:space,:batch,:upload,:filename,'UPLOADING',"
                        ":now,:actor,:now,:actor)"
                    ),
                    {
                        "id": new_uuid7(),
                        "tenant": principal.tenant_id,
                        "space": space_id,
                        "batch": payload["import_batch_id"],
                        "upload": upload_id,
                        "filename": payload["filename"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
                await connection.execute(
                    text(
                        "UPDATE source_import_batches SET status='UPLOADING',"
                        "version=version+1,updated_at=:now,updated_by=:actor "
                        "WHERE id=:batch AND status <> 'CANCELED'"
                    ),
                    {
                        "batch": payload["import_batch_id"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.upload",
                resource_type="SourceUploadSession",
                resource_id=upload_id,
                space_id=space_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "expected_size": payload["expected_size"],
                    "content_type": payload["content_type"],
                },
            )
            return _json_value(
                {
                    "id": upload_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": space_id,
                    "source_document_id": source_document_id,
                    "source_version_id": source_version_id,
                    "import_batch_id": payload.get("import_batch_id"),
                    "filename": payload["filename"],
                    "content_type": payload["content_type"],
                    "expected_size": payload["expected_size"],
                    "expected_checksum": payload["expected_checksum"],
                    "object_key": object_key,
                    "status": SourceUploadStatus.INITIATED.value,
                    "version": 1,
                    "upload_url": f"/api/v1/sources/uploads/{upload_id}/content",
                    "expires_at": expires_at,
                    "created_at": now,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"source_upload.create:{space_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def get_source_upload(self, *, principal: Principal, upload_id: UUID) -> JsonDict:
        async with self._database.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM source_upload_sessions "
                            "WHERE tenant_id=:tenant AND id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": upload_id},
                    )
                )
                .mappings()
                .first()
            )
            result = dict(row) if row is not None else None
            if (
                result
                and result["status"] in {"INITIATED", "UPLOADING"}
                and result["expires_at"] <= datetime.now(UTC)
            ):
                now = datetime.now(UTC)
                await connection.execute(
                    text(
                        "UPDATE source_upload_sessions SET status='EXPIRED',version=version+1,"
                        "updated_at=:now,updated_by=:actor WHERE id=:id"
                    ),
                    {"id": upload_id, "now": now, "actor": principal.actor_id},
                )
                if result["import_batch_id"]:
                    await connection.execute(
                        text(
                            "UPDATE source_import_batch_items SET status='FAILED',"
                            "error_code='SOURCE_UPLOAD_EXPIRED',"
                            "safe_detail='The controlled upload session expired.',"
                            "updated_at=:now,updated_by=:actor "
                            "WHERE upload_session_id=:upload AND status='UPLOADING'"
                        ),
                        {"upload": upload_id, "now": now, "actor": principal.actor_id},
                    )
                    await self._refresh_batch_status(
                        connection,
                        batch_id=result["import_batch_id"],
                        actor_id=principal.actor_id,
                        now=now,
                    )
                result = {
                    **result,
                    "status": "EXPIRED",
                    "version": result["version"] + 1,
                }
        if result is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Upload not found", "The upload is unavailable."
            )
        return _json_value(result)

    async def terminate_source_upload(
        self,
        *,
        principal: Principal,
        upload_id: UUID,
        reason_code: str,
        safe_detail: str,
        canceled: bool,
        trace_id: str,
    ) -> JsonDict:
        async with self._database.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM source_upload_sessions WHERE id=:id FOR UPDATE"),
                        {"id": upload_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None or row["tenant_id"] != principal.tenant_id:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Upload not found", "The upload is unavailable."
                )
            if row["status"] not in {"INITIATED", "UPLOADING", "COMPLETING"}:
                return _json_value(row)
            now = datetime.now(UTC)
            await connection.execute(
                text(
                    "UPDATE source_upload_sessions SET status='ABORTED',version=version+1,"
                    "updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"id": upload_id, "now": now, "actor": principal.actor_id},
            )
            if row["import_batch_id"]:
                await connection.execute(
                    text(
                        "UPDATE source_import_batch_items SET status=:status,error_code=:code,"
                        "safe_detail=:detail,updated_at=:now,updated_by=:actor "
                        "WHERE upload_session_id=:upload AND status='UPLOADING'"
                    ),
                    {
                        "status": "CANCELED" if canceled else "FAILED",
                        "code": reason_code,
                        "detail": safe_detail[:1024],
                        "now": now,
                        "actor": principal.actor_id,
                        "upload": upload_id,
                    },
                )
                await self._refresh_batch_status(
                    connection,
                    batch_id=row["import_batch_id"],
                    actor_id=principal.actor_id,
                    now=now,
                )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.upload.abort",
                resource_type="SourceUploadSession",
                resource_id=upload_id,
                space_id=row["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED" if canceled else "FAILED",
                metadata={"reason_code": reason_code, "safe_detail": safe_detail[:1024]},
            )
            return _json_value(
                {**row, "status": "ABORTED", "version": row["version"] + 1, "updated_at": now}
            )

    async def mark_source_content_uploaded(
        self,
        *,
        principal: Principal,
        upload_id: UUID,
        info: StoredObjectInfo,
        trace_id: str,
    ) -> JsonDict:
        async with self._database.engine.begin() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM source_upload_sessions WHERE id=:id FOR UPDATE"),
                        {"id": upload_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None or row["tenant_id"] != principal.tenant_id:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Upload not found", "The upload is unavailable."
                )
            if row["status"] == "UPLOADING" and row["object_version_id"] == info.version_id:
                return _json_value(row)
            if row["status"] != "INITIATED":
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Upload unavailable",
                    "The upload no longer accepts bytes.",
                )
            now = datetime.now(UTC)
            await connection.execute(
                text(
                    "UPDATE source_upload_sessions SET status='UPLOADING',object_version_id=:object_version,"
                    "version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {
                    "id": upload_id,
                    "object_version": info.version_id,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.upload.content",
                resource_type="SourceUploadSession",
                resource_id=upload_id,
                space_id=row["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "checksum": info.checksum_sha256,
                    "size": info.size,
                    "object_version_id": info.version_id,
                },
            )
            return _json_value(
                {
                    **row,
                    "status": "UPLOADING",
                    "version": row["version"] + 1,
                    "object_version_id": info.version_id,
                    "updated_at": now,
                }
            )

    async def register_raw_and_parse_job(
        self,
        *,
        principal: Principal,
        upload_id: UUID,
        verified_info: StoredObjectInfo,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        request = {
            "upload_id": upload_id,
            "object_key": verified_info.key,
            "object_version_id": verified_info.version_id,
            "checksum": verified_info.checksum_sha256,
            "size": verified_info.size,
            "content_type": verified_info.content_type,
        }

        async def mutation(connection: AsyncConnection) -> JsonDict:
            upload = (
                (
                    await connection.execute(
                        text("SELECT * FROM source_upload_sessions WHERE id=:id FOR UPDATE"),
                        {"id": upload_id},
                    )
                )
                .mappings()
                .first()
            )
            if upload is None or upload["tenant_id"] != principal.tenant_id:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Upload not found", "The upload is unavailable."
                )
            if upload["status"] != "UPLOADING":
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Upload incomplete",
                    "The immutable object must be uploaded before completion.",
                )
            if (
                verified_info.key != upload["object_key"]
                or verified_info.version_id != upload["object_version_id"]
                or verified_info.size != upload["expected_size"]
                or verified_info.checksum_sha256 != upload["expected_checksum"]
                or verified_info.content_type != upload["content_type"]
            ):
                raise ApiProblem(
                    422,
                    "SOURCE_CHECKSUM_MISMATCH",
                    "Raw verification failed",
                    "The server-read Raw object does not match the controlled upload session.",
                )
            now, parse_job_id = datetime.now(UTC), new_uuid7()
            source_id, version_id = upload["source_document_id"], upload["source_version_id"]
            document = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,status,classification FROM source_documents "
                            "WHERE tenant_id=:tenant AND space_id=:space AND id=:id FOR UPDATE"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": upload["space_id"],
                            "id": source_id,
                        },
                    )
                )
                .mappings()
                .first()
            )
            if document is None:
                await connection.execute(
                    text(
                        "INSERT INTO source_documents "
                        "(id,tenant_id,space_id,display_name,description,classification,source_level,"
                        "tags,valid_until,status,version,created_at,created_by,updated_at,updated_by) "
                        "VALUES (:id,:tenant,:space,:name,:description,:classification,:source_level,"
                        "CAST(:tags AS jsonb),:valid_until,'ACTIVE',1,:now,:actor,:now,:actor)"
                    ),
                    {
                        "id": source_id,
                        "tenant": principal.tenant_id,
                        "space": upload["space_id"],
                        "name": upload["display_name"],
                        "description": upload["description"],
                        "classification": upload["classification"],
                        "source_level": upload["source_level"],
                        "tags": json.dumps(upload["tags"]),
                        "valid_until": upload["valid_until"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            elif (
                document["status"] == "ARCHIVED"
                or document["classification"] != upload["classification"]
            ):
                raise ApiProblem(
                    409,
                    "CLASSIFICATION_CONFLICT"
                    if document["classification"] != upload["classification"]
                    else "STATE_TRANSITION_NOT_ALLOWED",
                    "Source classification conflict"
                    if document["classification"] != upload["classification"]
                    else "Source archived",
                    "Every version of a Source must use the Source classification."
                    if document["classification"] != upload["classification"]
                    else "An archived source cannot receive a new version.",
                )
            superseded_version: int | None = None
            if upload["supersedes_source_version_id"]:
                predecessor = (
                    (
                        await connection.execute(
                            text(
                                "SELECT id,status FROM source_versions WHERE tenant_id=:tenant "
                                "AND space_id=:space AND source_document_id=:source AND id=:old "
                                "FOR UPDATE"
                            ),
                            {
                                "tenant": principal.tenant_id,
                                "space": upload["space_id"],
                                "source": source_id,
                                "old": upload["supersedes_source_version_id"],
                            },
                        )
                    )
                    .mappings()
                    .first()
                )
                if predecessor is None or predecessor["status"] == "SUPERSEDED":
                    raise ApiProblem(
                        409,
                        "VERSION_CONFLICT",
                        "Replacement conflict",
                        "The selected predecessor is unavailable or was already superseded.",
                    )
                superseded_version = (
                    await connection.execute(
                        text(
                            "UPDATE source_versions SET status='SUPERSEDED',version=version+1 "
                            "WHERE tenant_id=:tenant AND space_id=:space AND source_document_id=:source "
                            "AND id=:old AND status <> 'SUPERSEDED' RETURNING version"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": upload["space_id"],
                            "source": source_id,
                            "old": upload["supersedes_source_version_id"],
                        },
                    )
                ).scalar_one_or_none()
                if superseded_version is None:
                    raise ApiProblem(
                        409,
                        "VERSION_CONFLICT",
                        "Replacement conflict",
                        "The selected predecessor changed before replacement completed.",
                    )
            await connection.execute(
                text(
                    "INSERT INTO source_versions "
                    "(id,tenant_id,space_id,source_document_id,upload_session_id,filename,content_type,"
                    "size,checksum,object_key,object_version_id,classification,status,version,"
                    "supersedes_source_version_id,created_at,created_by) VALUES "
                    "(:id,:tenant,:space,:source,:upload,:filename,:content_type,:size,:checksum,:key,"
                    ":object_version,:classification,'STORED',1,:supersedes,:now,:actor)"
                ),
                {
                    "id": version_id,
                    "tenant": principal.tenant_id,
                    "space": upload["space_id"],
                    "source": source_id,
                    "upload": upload_id,
                    "filename": upload["filename"],
                    "content_type": upload["content_type"],
                    "size": verified_info.size,
                    "checksum": verified_info.checksum_sha256,
                    "key": upload["object_key"],
                    "object_version": verified_info.version_id,
                    "classification": upload["classification"],
                    "supersedes": upload["supersedes_source_version_id"],
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            parser_config = ParserConfig().model_dump(mode="json")
            config_checksum = canonical_request_hash(parser_config)
            workflow_id = f"source-ingestion/{principal.tenant_id}/{parse_job_id}"
            correlation_id = new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO parse_jobs "
                    "(id,tenant_id,space_id,source_version_id,workflow_id,status,version,parser_id,"
                    "parser_version,config,config_checksum,document_model_version,locator_version,"
                    "correlation_id,trace_id,requested_by_actor_type,"
                    "created_at,created_by,updated_at,updated_by) VALUES "
                    "(:id,:tenant,:space,:source_version,:workflow,'QUEUED',1,'nexweave.parser.builtin',"
                    "'1.0.0',CAST(:config AS jsonb),:config_checksum,'1.0','1.0',"
                    ":correlation,:trace,:actor_type,"
                    ":now,:actor,:now,:actor)"
                ),
                {
                    "id": parse_job_id,
                    "tenant": principal.tenant_id,
                    "space": upload["space_id"],
                    "source_version": version_id,
                    "workflow": workflow_id,
                    "config": json.dumps(parser_config),
                    "config_checksum": config_checksum,
                    "correlation": correlation_id,
                    "trace": trace_id,
                    "actor_type": principal.actor_type.value,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await connection.execute(
                text(
                    "UPDATE source_versions SET status='PARSING',latest_parse_job_id=:job,version=2 WHERE id=:id"
                ),
                {"id": version_id, "job": parse_job_id},
            )
            await connection.execute(
                text(
                    "UPDATE source_upload_sessions SET status='COMPLETED',completed_at=:now,version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"id": upload_id, "now": now, "actor": principal.actor_id},
            )
            if upload["import_batch_id"]:
                await connection.execute(
                    text(
                        "UPDATE source_import_batch_items SET status='PROCESSING',"
                        "source_document_id=:source,source_version_id=:version,"
                        "updated_at=:now,updated_by=:actor WHERE upload_session_id=:upload"
                    ),
                    {
                        "source": source_id,
                        "version": version_id,
                        "now": now,
                        "actor": principal.actor_id,
                        "upload": upload_id,
                    },
                )
                await connection.execute(
                    text(
                        "UPDATE source_import_batches SET status='PROCESSING',"
                        "version=version+1,updated_at=:now,updated_by=:actor "
                        "WHERE id=:batch"
                    ),
                    {
                        "batch": upload["import_batch_id"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
            duplicate_ids = list(
                (
                    await connection.execute(
                        text(
                            "SELECT id FROM source_versions WHERE tenant_id=:tenant AND space_id=:space AND checksum=:checksum AND id<>:id ORDER BY created_at,id"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": upload["space_id"],
                            "checksum": upload["expected_checksum"],
                            "id": version_id,
                        },
                    )
                ).scalars()
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.upload.complete",
                resource_type="SourceVersion",
                resource_id=version_id,
                space_id=upload["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "checksum": upload["expected_checksum"],
                    "parse_job_id": parse_job_id,
                    "duplicate_count": len(duplicate_ids),
                },
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.source.version-ready.v1",
                aggregate_type="SourceVersion",
                aggregate_id=version_id,
                aggregate_version=1,
                space_id=upload["space_id"],
                trace_id=trace_id,
                payload={
                    "tenant_id": principal.tenant_id,
                    "space_id": upload["space_id"],
                    "source_id": source_id,
                    "source_version_id": version_id,
                    "aggregate_version": 1,
                    "status": "STORED",
                    "checksum": verified_info.checksum_sha256,
                    "classification": upload["classification"],
                    "parse_job_id": parse_job_id,
                    "workflow_id": workflow_id,
                    "run_id": None,
                    "correlation_id": correlation_id,
                    "causation_id": None,
                    "trace_id": trace_id,
                },
                correlation_id=correlation_id,
            )
            if upload["supersedes_source_version_id"]:
                await self._insert_outbox(
                    connection,
                    principal=principal,
                    event_type="io.nexweave.source.version-superseded.v1",
                    aggregate_type="SourceVersion",
                    aggregate_id=upload["supersedes_source_version_id"],
                    aggregate_version=superseded_version or 1,
                    space_id=upload["space_id"],
                    trace_id=trace_id,
                    correlation_id=correlation_id,
                    causation_id=version_id,
                    payload={
                        "tenant_id": principal.tenant_id,
                        "space_id": upload["space_id"],
                        "source_id": source_id,
                        "source_version_id": upload["supersedes_source_version_id"],
                        "aggregate_version": superseded_version or 1,
                        "old_source_version_id": upload["supersedes_source_version_id"],
                        "new_source_version_id": version_id,
                        "reason": "explicit-replacement",
                        "correlation_id": correlation_id,
                        "causation_id": version_id,
                        "trace_id": trace_id,
                    },
                )
            return _json_value(
                {
                    "id": version_id,
                    "source_id": source_id,
                    "source_version_id": version_id,
                    "parse_job_id": parse_job_id,
                    "workflow_id": workflow_id,
                    "run_id": None,
                    "duplicate_source_version_ids": duplicate_ids,
                    "source_status": SourceDocumentStatus.ACTIVE.value,
                    "version_status": SourceVersionState.PARSING.value,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation="source_upload.complete",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def attach_parse_run(self, parse_job_id: UUID, run_id: str) -> None:
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE parse_jobs SET temporal_run_id=:run,updated_at=:now WHERE id=:id AND (temporal_run_id IS NULL OR temporal_run_id=:run)"
                ),
                {"id": parse_job_id, "run": run_id, "now": datetime.now(UTC)},
            )

    async def list_sources(self, *, principal: Principal, space_id: UUID) -> list[JsonDict]:
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {SOURCE_COLUMNS} FROM source_documents WHERE tenant_id=:tenant AND space_id=:space ORDER BY created_at,id"
                        ),
                        {"tenant": principal.tenant_id, "space": space_id},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value({**row, "versions": ()}) for row in rows]

    async def get_source(self, *, principal: Principal, source_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {SOURCE_COLUMNS} FROM source_documents WHERE tenant_id=:tenant AND id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": source_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApiProblem(
                    404, "RESOURCE_NOT_FOUND", "Source not found", "The source is unavailable."
                )
            versions = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {VERSION_COLUMNS} FROM source_versions WHERE tenant_id=:tenant AND space_id=:space AND source_document_id=:source ORDER BY created_at,id"
                        ),
                        {
                            "tenant": principal.tenant_id,
                            "space": row["space_id"],
                            "source": source_id,
                        },
                    )
                )
                .mappings()
                .all()
            )
        visible_versions = [
            dict(version)
            for version in versions
            if CLASSIFICATION_LEVEL[DataClassification(version["classification"])]
            <= CLASSIFICATION_LEVEL[principal.clearance]
        ]
        return _json_value({**row, "versions": visible_versions})

    async def get_source_version(self, *, principal: Principal, version_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {VERSION_COLUMNS} FROM source_versions WHERE tenant_id=:tenant AND id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": version_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Source version not found",
                "The source version is unavailable.",
            )
        return _json_value(row)

    async def get_parse_job(self, *, principal: Principal, parse_job_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {PARSE_COLUMNS} FROM parse_jobs WHERE tenant_id=:tenant AND id=:id"
                        ),
                        {"tenant": principal.tenant_id, "id": parse_job_id},
                    )
                )
                .mappings()
                .first()
            )
            if row is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Parse job not found",
                    "The parse job is unavailable.",
                )
            failures = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,parse_job_id,error_code,scope,scope_ref,retryable,safe_detail FROM parse_failure_units WHERE parse_job_id=:id ORDER BY created_at,id"
                        ),
                        {"id": parse_job_id},
                    )
                )
                .mappings()
                .all()
            )
        return _json_value({**row, "failure_units": [dict(failure) for failure in failures]})

    async def list_segments(
        self, *, principal: Principal, version_id: UUID, parse_job_id: UUID | None
    ) -> list[JsonDict]:
        version = await self.get_source_version(principal=principal, version_id=version_id)
        selected = parse_job_id or version["active_parse_job_id"]
        if selected is None:
            return []
        async with self._database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        text(
                            "SELECT id,source_version_id,parse_job_id,sequence,block_type,structure_path,normalized_text,derived_object_key,text_checksum,page_number,sheet_name,table_id,row_index,column_index,locators,parser_id,parser_version,config_checksum,document_model_version,locator_version FROM document_segments WHERE tenant_id=:tenant AND source_version_id=:version AND parse_job_id=:job ORDER BY sequence,id"
                        ),
                        {"tenant": principal.tenant_id, "version": version_id, "job": selected},
                    )
                )
                .mappings()
                .all()
            )
        return [_json_value(row) for row in rows]

    async def get_anchor(self, *, principal: Principal, anchor_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text("SELECT * FROM source_anchors WHERE tenant_id=:tenant AND id=:id"),
                        {"tenant": principal.tenant_id, "id": anchor_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Anchor not found", "The anchor is unavailable."
            )
        return _json_value(row)

    async def create_reparse(
        self,
        *,
        principal: Principal,
        version_id: UUID,
        expected_version: int,
        payload: Mapping[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        if (
            payload["parser_id"] != "nexweave.parser.builtin"
            or payload["parser_version"] != "1.0.0"
        ):
            raise ApiProblem(
                422,
                "PARSER_CAPABILITY_UNAVAILABLE",
                "Parser unavailable",
                "The requested parser is not registered in the isolated M3 worker.",
            )
        if payload.get("ocr_provider_id"):
            raise ApiProblem(
                422,
                "PARSER_CAPABILITY_UNAVAILABLE",
                "OCR provider unavailable",
                "No approved real OCR provider is configured for M3.",
            )
        request = {"source_version_id": version_id, "expected_version": expected_version, **payload}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            version = (
                (
                    await connection.execute(
                        text(
                            "SELECT v.*,d.status AS source_status FROM source_versions v "
                            "JOIN source_documents d ON d.tenant_id=v.tenant_id "
                            "AND d.space_id=v.space_id AND d.id=v.source_document_id "
                            "WHERE v.tenant_id=:tenant AND v.id=:id FOR UPDATE OF v"
                        ),
                        {"tenant": principal.tenant_id, "id": version_id},
                    )
                )
                .mappings()
                .first()
            )
            if version is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Source version not found",
                    "The source version is unavailable.",
                )
            if version["version"] != expected_version:
                raise ApiProblem(
                    412,
                    "PRECONDITION_FAILED",
                    "Version changed",
                    "Refresh the SourceVersion and retry with its current ETag.",
                )
            if version["source_status"] == "ARCHIVED" or version["status"] == "SUPERSEDED":
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Source version unavailable",
                    "Archived or superseded SourceVersions cannot be reparsed.",
                )
            invalidated = (
                await connection.execute(
                    text(
                        "SELECT 1 FROM source_invalidations WHERE tenant_id=:tenant "
                        "AND space_id=:space AND source_version_id=:version LIMIT 1"
                    ),
                    {
                        "tenant": principal.tenant_id,
                        "space": version["space_id"],
                        "version": version_id,
                    },
                )
            ).first()
            if invalidated:
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Source version invalidated",
                    "An invalidated SourceVersion cannot be reparsed.",
                )
            now, parse_job_id, correlation_id = datetime.now(UTC), new_uuid7(), new_uuid7()
            config_checksum = canonical_request_hash(payload.get("config", {}))
            workflow_id = f"source-ingestion/{principal.tenant_id}/{parse_job_id}"
            await connection.execute(
                text(
                    "INSERT INTO parse_jobs "
                    "(id,tenant_id,space_id,source_version_id,workflow_id,status,version,parser_id,"
                    "parser_version,config,config_checksum,document_model_version,locator_version,"
                    "ocr_provider_id,ocr_provider_version,correlation_id,trace_id,"
                    "requested_by_actor_type,created_at,created_by,updated_at,updated_by) VALUES "
                    "(:id,:tenant,:space,:source_version,:workflow,'QUEUED',1,:parser_id,"
                    ":parser_version,CAST(:config AS jsonb),:config_checksum,'1.0','1.0',"
                    ":ocr_provider_id,:ocr_provider_version,:correlation,:trace,:actor_type,"
                    ":now,:actor,:now,:actor)"
                ),
                {
                    "id": parse_job_id,
                    "tenant": principal.tenant_id,
                    "space": version["space_id"],
                    "source_version": version_id,
                    "workflow": workflow_id,
                    "parser_id": payload["parser_id"],
                    "parser_version": payload["parser_version"],
                    "config": json.dumps(payload.get("config", {})),
                    "config_checksum": config_checksum,
                    "ocr_provider_id": payload.get("ocr_provider_id"),
                    "ocr_provider_version": payload.get("ocr_provider_version"),
                    "correlation": correlation_id,
                    "trace": trace_id,
                    "actor_type": principal.actor_type.value,
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await connection.execute(
                text(
                    "UPDATE source_versions SET "
                    "status=CASE WHEN active_parse_job_id IS NULL THEN 'PARSING' ELSE status END,"
                    "latest_parse_job_id=:job,version=version+1 WHERE id=:version"
                ),
                {"job": parse_job_id, "version": version_id},
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.parse",
                resource_type="ParseJob",
                resource_id=parse_job_id,
                space_id=version["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "operation": "REPARSE",
                    "source_version_id": version_id,
                    "workflow_id": workflow_id,
                    "config_checksum": config_checksum,
                },
            )
            return _json_value(
                {
                    "id": parse_job_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": version["space_id"],
                    "source_version_id": version_id,
                    "status": "QUEUED",
                    "version": 1,
                    "parser_id": payload["parser_id"],
                    "parser_version": payload["parser_version"],
                    "config_checksum": config_checksum,
                    "document_model_version": "1.0",
                    "locator_version": "1.0",
                    "ocr_provider_id": payload.get("ocr_provider_id"),
                    "ocr_provider_version": payload.get("ocr_provider_version"),
                    "workflow_id": workflow_id,
                    "temporal_run_id": None,
                    "result_checksum": None,
                    "failure_units": (),
                    "created_at": now,
                    "updated_at": now,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"source_version.reparse:{version_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def prepare_parse_retry(
        self,
        *,
        principal: Principal,
        parse_job_id: UUID,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        request = {"parse_job_id": parse_job_id, "expected_version": expected_version}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            job = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM parse_jobs WHERE tenant_id=:tenant AND id=:id FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "id": parse_job_id},
                    )
                )
                .mappings()
                .first()
            )
            if job is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Parse job not found",
                    "The parse job is unavailable.",
                )
            if job["version"] != expected_version:
                raise ApiProblem(
                    412,
                    "PRECONDITION_FAILED",
                    "Version changed",
                    "Refresh the ParseJob and retry with its current ETag.",
                )
            if job["status"] != "FAILED" or job["result_checksum"] is not None:
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Parse job is not retryable",
                    "Only an incomplete failed ParseJob can start a same-input retry Run.",
                )
            retryable = bool(
                (
                    await connection.execute(
                        text(
                            "SELECT 1 FROM parse_failure_units WHERE parse_job_id=:job "
                            "AND retryable=true LIMIT 1"
                        ),
                        {"job": parse_job_id},
                    )
                ).first()
            ) or job["error_code"] in {
                "DEPENDENCY_UNAVAILABLE",
                "SOURCE_MALWARE_SCANNER_UNAVAILABLE",
                "PARSER_DEPENDENCY_UNAVAILABLE",
                "SOURCE_PARSE_ACTIVITY_FAILED",
            }
            if not retryable:
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Parse job is not retryable",
                    "The recorded failure requires reparse or a policy correction.",
                )
            now = datetime.now(UTC)
            scan_status = (
                "PENDING"
                if job["malware_scan_status"] in {"FAILED", "INFECTED"}
                else job["malware_scan_status"]
            )
            await connection.execute(
                text(
                    "UPDATE parse_jobs SET status='QUEUED',malware_scan_status=:scan_status,"
                    "error_code=NULL,error_detail=NULL,version=version+1,updated_at=:now,"
                    "updated_by=:actor WHERE id=:id"
                ),
                {
                    "scan_status": scan_status,
                    "now": now,
                    "actor": principal.actor_id,
                    "id": parse_job_id,
                },
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.parse",
                resource_type="ParseJob",
                resource_id=parse_job_id,
                space_id=job["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "RETRY", "workflow_id": job["workflow_id"]},
            )
            return _json_value(
                {
                    **job,
                    "status": "QUEUED",
                    "version": job["version"] + 1,
                    "malware_scan_status": scan_status,
                    "error_code": None,
                    "error_detail": None,
                    "updated_at": now,
                    "failure_units": (),
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"parse_job.retry:{parse_job_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def cancel_parse_job(
        self,
        *,
        principal: Principal,
        parse_job_id: UUID,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        request = {"parse_job_id": parse_job_id, "expected_version": expected_version}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            job = (
                (
                    await connection.execute(
                        text(
                            "SELECT p.*,v.source_document_id,v.classification,"
                            "v.active_parse_job_id,v.latest_parse_job_id,u.import_batch_id "
                            "FROM parse_jobs p JOIN source_versions v "
                            "ON v.tenant_id=p.tenant_id AND v.space_id=p.space_id "
                            "AND v.id=p.source_version_id JOIN source_upload_sessions u "
                            "ON u.id=v.upload_session_id WHERE p.tenant_id=:tenant AND p.id=:id "
                            "FOR UPDATE OF p,v"
                        ),
                        {"tenant": principal.tenant_id, "id": parse_job_id},
                    )
                )
                .mappings()
                .first()
            )
            if job is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Parse job not found",
                    "The parse job is unavailable.",
                )
            if job["version"] != expected_version:
                raise ApiProblem(
                    412,
                    "PRECONDITION_FAILED",
                    "Version changed",
                    "Refresh the ParseJob and retry with its current ETag.",
                )
            if job["status"] == "CANCELED":
                return _json_value({**job, "failure_units": ()})
            if job["status"] in {"SUCCEEDED", "PARTIAL_FAILED", "FAILED"}:
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Parse job is terminal",
                    "A completed ParseJob cannot be canceled.",
                )
            now = datetime.now(UTC)
            next_version = int(job["version"]) + 1
            await connection.execute(
                text(
                    "UPDATE parse_jobs SET status='CANCELED',error_code='PARSE_CANCELED',"
                    "error_detail='The parse was canceled by an authorized user.',"
                    "version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"id": parse_job_id, "now": now, "actor": principal.actor_id},
            )
            await connection.execute(
                text(
                    "UPDATE source_versions SET "
                    "status=CASE WHEN active_parse_job_id IS NULL THEN 'STORED' ELSE status END,"
                    "version=version+1 WHERE id=:version AND latest_parse_job_id=:job "
                    "AND status <> 'SUPERSEDED'"
                ),
                {"version": job["source_version_id"], "job": parse_job_id},
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.parse.cancel",
                resource_type="ParseJob",
                resource_id=parse_job_id,
                space_id=job["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"workflow_id": job["workflow_id"], "operation": "CANCEL"},
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.parse.failed.v1",
                aggregate_type="ParseJob",
                aggregate_id=parse_job_id,
                aggregate_version=next_version,
                space_id=job["space_id"],
                trace_id=trace_id,
                correlation_id=job["correlation_id"],
                causation_id=parse_job_id,
                payload={
                    "tenant_id": job["tenant_id"],
                    "space_id": job["space_id"],
                    "source_id": job["source_document_id"],
                    "source_version_id": job["source_version_id"],
                    "aggregate_version": next_version,
                    "parse_job_id": parse_job_id,
                    "status": "CANCELED",
                    "parser_id": job["parser_id"],
                    "parser_version": job["parser_version"],
                    "config_checksum": job["config_checksum"],
                    "document_model_version": job["document_model_version"],
                    "locator_version": job["locator_version"],
                    "result_checksum": None,
                    "failure_count": 0,
                    "error_code": "PARSE_CANCELED",
                    "workflow_id": job["workflow_id"],
                    "run_id": job["temporal_run_id"] or "not-started",
                    "correlation_id": job["correlation_id"],
                    "causation_id": parse_job_id,
                    "trace_id": trace_id,
                },
            )
            if job["import_batch_id"]:
                await connection.execute(
                    text(
                        "UPDATE source_import_batch_items SET status='CANCELED',"
                        "error_code='PARSE_CANCELED',"
                        "safe_detail='The parse was canceled by an authorized user.',"
                        "updated_at=:now,updated_by=:actor WHERE source_version_id=:version"
                    ),
                    {
                        "version": job["source_version_id"],
                        "now": now,
                        "actor": principal.actor_id,
                    },
                )
                await self._refresh_batch_status(
                    connection,
                    batch_id=job["import_batch_id"],
                    actor_id=principal.actor_id,
                    now=now,
                )
            return _json_value(
                {
                    **job,
                    "status": "CANCELED",
                    "version": next_version,
                    "error_code": "PARSE_CANCELED",
                    "error_detail": "The parse was canceled by an authorized user.",
                    "updated_at": now,
                    "failure_units": (),
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"parse_job.cancel:{parse_job_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def invalidate_source_version(
        self,
        *,
        principal: Principal,
        version_id: UUID,
        expected_version: int,
        payload: Mapping[str, Any],
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        request = {"source_version_id": version_id, "expected_version": expected_version, **payload}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            version = (
                (
                    await connection.execute(
                        text(
                            "SELECT * FROM source_versions WHERE tenant_id=:tenant AND id=:id "
                            "FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "id": version_id},
                    )
                )
                .mappings()
                .first()
            )
            if version is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Source version not found",
                    "The source version is unavailable.",
                )
            if version["version"] != expected_version:
                raise ApiProblem(
                    412,
                    "PRECONDITION_FAILED",
                    "Version changed",
                    "Refresh the SourceVersion and retry with its current ETag.",
                )
            now, invalidation_id, correlation_id = datetime.now(UTC), new_uuid7(), new_uuid7()
            await connection.execute(
                text(
                    "INSERT INTO source_invalidations "
                    "(id,tenant_id,space_id,source_version_id,reason_code,reason,policy_version,"
                    "created_at,created_by) VALUES "
                    "(:id,:tenant,:space,:version,:code,:reason,:policy,:now,:actor)"
                ),
                {
                    "id": invalidation_id,
                    "tenant": principal.tenant_id,
                    "space": version["space_id"],
                    "version": version_id,
                    "code": payload["reason_code"],
                    "reason": payload["reason"],
                    "policy": payload["policy_version"],
                    "now": now,
                    "actor": principal.actor_id,
                },
            )
            await connection.execute(
                text("UPDATE source_versions SET version=version+1 WHERE id=:id"),
                {"id": version_id},
            )
            await connection.execute(
                text(
                    "UPDATE source_anchors SET status='REVOKED',updated_at=:now "
                    "WHERE source_version_id=:version AND status <> 'REVOKED'"
                ),
                {"version": version_id, "now": now},
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.invalidate",
                resource_type="SourceVersion",
                resource_id=version_id,
                space_id=version["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "invalidation_id": invalidation_id,
                    "reason_code": payload["reason_code"],
                    "policy_version": payload["policy_version"],
                },
            )
            await self._insert_outbox(
                connection,
                principal=principal,
                event_type="io.nexweave.source.invalidated.v1",
                aggregate_type="SourceVersion",
                aggregate_id=version_id,
                aggregate_version=version["version"] + 1,
                space_id=version["space_id"],
                trace_id=trace_id,
                correlation_id=correlation_id,
                payload={
                    "tenant_id": principal.tenant_id,
                    "space_id": version["space_id"],
                    "source_id": version["source_document_id"],
                    "source_version_id": version_id,
                    "aggregate_version": version["version"] + 1,
                    "status": version["status"],
                    "reason_code": payload["reason_code"],
                    "policy_version": payload["policy_version"],
                    "correlation_id": correlation_id,
                    "causation_id": invalidation_id,
                    "trace_id": trace_id,
                },
                causation_id=invalidation_id,
            )
            return _json_value(
                {
                    "id": invalidation_id,
                    "tenant_id": principal.tenant_id,
                    "space_id": version["space_id"],
                    "source_version_id": version_id,
                    **payload,
                    "created_at": now,
                    "created_by": principal.actor_id,
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"source_version.invalidate:{version_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def archive_source(
        self,
        *,
        principal: Principal,
        source_id: UUID,
        expected_version: int,
        idempotency_key: str,
        trace_id: str,
    ) -> JsonDict:
        request = {"source_id": source_id, "expected_version": expected_version}

        async def mutation(connection: AsyncConnection) -> JsonDict:
            source = (
                (
                    await connection.execute(
                        text(
                            f"SELECT {SOURCE_COLUMNS} FROM source_documents "
                            "WHERE tenant_id=:tenant AND id=:id FOR UPDATE"
                        ),
                        {"tenant": principal.tenant_id, "id": source_id},
                    )
                )
                .mappings()
                .first()
            )
            if source is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Source not found",
                    "The source is unavailable.",
                )
            if source["version"] != expected_version:
                raise ApiProblem(
                    412,
                    "PRECONDITION_FAILED",
                    "Version changed",
                    "Refresh the SourceDocument and retry with its current ETag.",
                )
            if source["status"] == "ARCHIVED":
                raise ApiProblem(
                    409,
                    "STATE_TRANSITION_NOT_ALLOWED",
                    "Source already archived",
                    "The SourceDocument is already archived.",
                )
            now = datetime.now(UTC)
            await connection.execute(
                text(
                    "UPDATE source_documents SET status='ARCHIVED',archived_at=:now,"
                    "version=version+1,updated_at=:now,updated_by=:actor WHERE id=:id"
                ),
                {"now": now, "actor": principal.actor_id, "id": source_id},
            )
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.archive",
                resource_type="SourceDocument",
                resource_id=source_id,
                space_id=source["space_id"],
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"operation": "ARCHIVE"},
            )
            return _json_value(
                {
                    **source,
                    "status": "ARCHIVED",
                    "version": source["version"] + 1,
                    "updated_at": now,
                    "updated_by": principal.actor_id,
                    "archived_at": now,
                    "versions": (),
                }
            )

        return await self._idempotent(
            principal=principal,
            operation=f"source.archive:{source_id}",
            key=idempotency_key,
            request=request,
            mutation=mutation,
        )

    async def record_source_download(
        self, *, principal: Principal, version: Mapping[str, Any], trace_id: str
    ) -> None:
        async with self._database.engine.begin() as connection:
            await self._insert_audit(
                connection,
                principal=principal,
                action="source.download",
                resource_type="SourceVersion",
                resource_id=UUID(str(version["id"])),
                space_id=UUID(str(version["space_id"])),
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"checksum": version["checksum"], "delivery": "CONTROLLED_STREAM"},
            )

    async def is_source_version_invalidated(
        self, *, principal: Principal, version_id: UUID
    ) -> bool:
        async with self._database.engine.connect() as connection:
            return bool(
                (
                    await connection.execute(
                        text(
                            "SELECT 1 FROM source_invalidations WHERE tenant_id=:tenant "
                            "AND source_version_id=:version LIMIT 1"
                        ),
                        {"tenant": principal.tenant_id, "version": version_id},
                    )
                ).first()
            )

    async def load_parse_context(self, parse_job_id: UUID) -> JsonDict:
        async with self._database.engine.connect() as connection:
            row = (
                (
                    await connection.execute(
                        text(
                            f"SELECT p.{PARSE_COLUMNS.replace(', ', ', p.')}, "
                            "v.filename,v.content_type,v.size,v.checksum,v.object_key,"
                            "v.object_version_id,v.classification,v.source_document_id,"
                            "v.status AS source_version_status,v.latest_parse_job_id,"
                            "d.status AS source_document_status,"
                            "EXISTS (SELECT 1 FROM source_invalidations i "
                            "WHERE i.tenant_id=v.tenant_id AND i.space_id=v.space_id "
                            "AND i.source_version_id=v.id) AS invalidated "
                            "FROM parse_jobs p JOIN source_versions v "
                            "ON v.tenant_id=p.tenant_id AND v.space_id=p.space_id "
                            "AND v.id=p.source_version_id JOIN source_documents d "
                            "ON d.tenant_id=v.tenant_id AND d.space_id=v.space_id "
                            "AND d.id=v.source_document_id WHERE p.id=:id"
                        ),
                        {"id": parse_job_id},
                    )
                )
                .mappings()
                .first()
            )
        if row is None:
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Parse job not found", "The parse job is unavailable."
            )
        return _json_value(row)

    async def mark_parse_running(self, parse_job_id: UUID, run_id: str) -> None:
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE parse_jobs SET status='RUNNING',temporal_run_id=:run,version=version+1,updated_at=:now WHERE id=:id AND status IN ('CREATED','QUEUED')"
                ),
                {"id": parse_job_id, "run": run_id, "now": datetime.now(UTC)},
            )

    async def mark_malware_scan_clean(self, parse_job_id: UUID, run_id: str) -> None:
        async with self._database.engine.begin() as connection:
            await connection.execute(
                text(
                    "UPDATE parse_jobs SET malware_scan_status='CLEAN',temporal_run_id=:run,"
                    "version=version+1,updated_at=:now "
                    "WHERE id=:id AND status='RUNNING' AND malware_scan_status='PENDING'"
                ),
                {"id": parse_job_id, "run": run_id, "now": datetime.now(UTC)},
            )

    async def _refresh_batch_status(
        self,
        connection: AsyncConnection,
        *,
        batch_id: UUID,
        actor_id: UUID,
        now: datetime,
    ) -> None:
        rows = (
            (
                await connection.execute(
                    text(
                        "SELECT status,COUNT(*) AS count FROM source_import_batch_items "
                        "WHERE import_batch_id=:batch GROUP BY status"
                    ),
                    {"batch": batch_id},
                )
            )
            .mappings()
            .all()
        )
        counts: dict[str, int] = {str(row["status"]): int(row["count"]) for row in rows}
        in_progress = sum(counts.get(value, 0) for value in ("UPLOADING", "PROCESSING"))
        succeeded = counts.get("SUCCEEDED", 0)
        partial = counts.get("PARTIAL", 0)
        failed = counts.get("FAILED", 0)
        canceled = counts.get("CANCELED", 0)
        if in_progress:
            status = "PROCESSING"
        elif (succeeded or partial) and (failed or canceled):
            status = "PARTIAL"
        elif partial:
            status = "PARTIAL"
        elif succeeded:
            status = "SUCCEEDED"
        elif canceled and not failed:
            status = "CANCELED"
        else:
            status = "FAILED"
        await connection.execute(
            text(
                "UPDATE source_import_batches SET status=:status,version=version+1,"
                "updated_at=:now,updated_by=:actor WHERE id=:batch"
            ),
            {"status": status, "now": now, "actor": actor_id, "batch": batch_id},
        )

    async def persist_parse_result(self, manifest: ParseResultManifest, run_id: str) -> JsonDict:
        async with self._database.engine.begin() as connection:
            job = (
                (
                    await connection.execute(
                        text(
                            "SELECT p.*,v.source_document_id,v.checksum AS source_checksum,"
                            "v.classification,v.status AS source_version_status,"
                            "v.active_parse_job_id,v.latest_parse_job_id,"
                            "d.status AS source_document_status,"
                            "EXISTS (SELECT 1 FROM source_invalidations i "
                            "WHERE i.tenant_id=v.tenant_id AND i.space_id=v.space_id "
                            "AND i.source_version_id=v.id) AS invalidated,u.import_batch_id "
                            "FROM parse_jobs p JOIN source_versions v "
                            "ON v.tenant_id=p.tenant_id AND v.space_id=p.space_id "
                            "AND v.id=p.source_version_id "
                            "JOIN source_documents d ON d.tenant_id=v.tenant_id "
                            "AND d.space_id=v.space_id AND d.id=v.source_document_id "
                            "JOIN source_upload_sessions u ON u.id=v.upload_session_id "
                            "WHERE p.id=:id FOR UPDATE OF p,v,d"
                        ),
                        {"id": manifest.parse_job_id},
                    )
                )
                .mappings()
                .first()
            )
            if job is None:
                raise ApiProblem(
                    404,
                    "RESOURCE_NOT_FOUND",
                    "Parse job not found",
                    "The parse job is unavailable.",
                )
            if job["result_checksum"] is not None:
                if job["result_checksum"] != manifest.result_checksum:
                    raise ApiProblem(
                        409,
                        "PARSE_RESULT_INVALID",
                        "Parse result conflict",
                        "A different immutable result is already registered.",
                    )
                return _json_value(job)
            if (
                job["status"] != "RUNNING"
                or job["source_document_status"] == "ARCHIVED"
                or job["source_version_status"] == "SUPERSEDED"
                or job["invalidated"]
                or job["latest_parse_job_id"] != job["id"]
            ):
                raise ApiProblem(
                    409,
                    "SOURCE_SECURITY_POLICY_FAILED",
                    "Parse result is no longer current",
                    "Archived, invalidated, superseded or stale parse output cannot be persisted.",
                )
            if job["malware_scan_status"] != "CLEAN":
                raise ApiProblem(
                    409,
                    "SOURCE_SECURITY_POLICY_FAILED",
                    "Scan gate not satisfied",
                    "The parser result cannot be accepted before a clean ClamAV result.",
                )
            if (
                manifest.source_version_id != job["source_version_id"]
                or manifest.source_checksum != job["source_checksum"]
                or manifest.parser_id != job["parser_id"]
                or manifest.parser_version != job["parser_version"]
                or manifest.config_checksum != job["config_checksum"]
                or manifest.document_model_version != job["document_model_version"]
                or manifest.locator_version != job["locator_version"]
            ):
                raise ApiProblem(
                    409,
                    "PARSE_RESULT_INVALID",
                    "Parse result mismatch",
                    "The immutable result manifest does not match its registered ParseJob.",
                )
            now = datetime.now(UTC)
            for failure in manifest.failure_units:
                await connection.execute(
                    text(
                        "INSERT INTO parse_failure_units "
                        "(id,tenant_id,space_id,parse_job_id,error_code,scope,scope_ref,"
                        "retryable,safe_detail,created_at) VALUES "
                        "(:id,:tenant,:space,:job,:code,:scope,:scope_ref,:retryable,:detail,:now)"
                    ),
                    {
                        "id": failure.id,
                        "tenant": job["tenant_id"],
                        "space": job["space_id"],
                        "job": job["id"],
                        "code": failure.error_code,
                        "scope": failure.scope.value,
                        "scope_ref": failure.scope_ref,
                        "retryable": failure.retryable,
                        "detail": failure.safe_detail,
                        "now": now,
                    },
                )
            for segment in manifest.segments:
                if (
                    segment.source_version_id != job["source_version_id"]
                    or segment.parse_job_id != job["id"]
                ):
                    raise ApiProblem(
                        409,
                        "PARSE_RESULT_INVALID",
                        "Segment binding mismatch",
                        "A segment is not bound to the immutable ParseJob input.",
                    )
                value = segment.model_dump(mode="json")
                await connection.execute(
                    text(
                        "INSERT INTO document_segments "
                        "(id,tenant_id,space_id,source_version_id,parse_job_id,sequence,"
                        "block_type,structure_path,normalized_text,derived_object_key,text_checksum,"
                        "page_number,sheet_name,table_id,row_index,column_index,locators,parser_id,"
                        "parser_version,config_checksum,document_model_version,locator_version,"
                        "created_at) VALUES "
                        "(:id,:tenant,:space,:source_version,:job,:sequence,:block_type,:path,"
                        ":text,:derived,:checksum,:page,:sheet,:table,:row,:column,"
                        "CAST(:locators AS jsonb),:parser_id,:parser_version,:config_checksum,"
                        ":document_model,:locator_version,:now)"
                    ),
                    {
                        "id": segment.id,
                        "tenant": job["tenant_id"],
                        "space": job["space_id"],
                        "source_version": segment.source_version_id,
                        "job": segment.parse_job_id,
                        "sequence": segment.sequence,
                        "block_type": segment.block_type.value,
                        "path": segment.structure_path,
                        "text": segment.normalized_text,
                        "derived": segment.derived_object_key,
                        "checksum": segment.text_checksum,
                        "page": segment.page_number,
                        "sheet": segment.sheet_name,
                        "table": segment.table_id,
                        "row": segment.row_index,
                        "column": segment.column_index,
                        "locators": json.dumps(value["locators"]),
                        "parser_id": segment.parser_id,
                        "parser_version": segment.parser_version,
                        "config_checksum": segment.config_checksum,
                        "document_model": segment.document_model_version,
                        "locator_version": segment.locator_version,
                        "now": now,
                    },
                )
            old_anchors: list[Mapping[str, Any]] = []
            if job["active_parse_job_id"] and job["active_parse_job_id"] != job["id"]:
                anchor_rows = (
                    (
                        await connection.execute(
                            text(
                                "SELECT id,excerpt_hash FROM source_anchors "
                                "WHERE tenant_id=:tenant AND space_id=:space "
                                "AND source_version_id=:version AND parse_job_id=:job "
                                "AND status='VALID' ORDER BY created_at,id FOR UPDATE"
                            ),
                            {
                                "tenant": job["tenant_id"],
                                "space": job["space_id"],
                                "version": job["source_version_id"],
                                "job": job["active_parse_job_id"],
                            },
                        )
                    )
                    .mappings()
                    .all()
                )
                old_anchors = [dict(row) for row in anchor_rows]
            old_by_excerpt: dict[str, list[UUID]] = {}
            for old_anchor in old_anchors:
                old_by_excerpt.setdefault(str(old_anchor["excerpt_hash"]), []).append(
                    old_anchor["id"]
                )
            relocated_old_ids: set[UUID] = set()
            for anchor in manifest.anchors:
                if (
                    anchor.source_version_id != job["source_version_id"]
                    or anchor.parse_job_id != job["id"]
                    or anchor.source_checksum != job["source_checksum"]
                ):
                    raise ApiProblem(
                        409,
                        "PARSE_RESULT_INVALID",
                        "Anchor binding mismatch",
                        "An anchor is not bound to the immutable ParseJob input.",
                    )
                value = anchor.model_dump(mode="json")
                relocated_from = anchor.relocated_from_anchor_id
                candidates = old_by_excerpt.get(anchor.excerpt_hash, [])
                if relocated_from is None and len(candidates) == 1:
                    relocated_from = candidates[0]
                if relocated_from is not None and (
                    relocated_from not in {item["id"] for item in old_anchors}
                    or relocated_from in relocated_old_ids
                ):
                    raise ApiProblem(
                        409,
                        "ANCHOR_UNRESOLVED",
                        "Anchor relocation is ambiguous",
                        "A relocation target must identify one unique prior SourceAnchor.",
                    )
                if relocated_from:
                    relocated_old_ids.add(relocated_from)
                await connection.execute(
                    text(
                        "INSERT INTO source_anchors "
                        "(id,tenant_id,space_id,source_version_id,source_checksum,parse_job_id,"
                        "locator_version,excerpt_hash,locators,status,relocated_from_anchor_id,"
                        "created_at,created_by,updated_at) VALUES "
                        "(:id,:tenant,:space,:source_version,:source_checksum,:job,"
                        ":locator_version,:excerpt_hash,CAST(:locators AS jsonb),:status,"
                        ":relocated,:now,:actor,:now)"
                    ),
                    {
                        "id": anchor.id,
                        "tenant": job["tenant_id"],
                        "space": job["space_id"],
                        "source_version": anchor.source_version_id,
                        "source_checksum": anchor.source_checksum,
                        "job": anchor.parse_job_id,
                        "locator_version": anchor.locator_version,
                        "excerpt_hash": anchor.excerpt_hash,
                        "locators": json.dumps(value["locators"]),
                        "status": anchor.status.value,
                        "relocated": relocated_from,
                        "now": now,
                        "actor": job["created_by"],
                    },
                )
            unresolved_ids = [
                old_anchor["id"]
                for old_anchor in old_anchors
                if old_anchor["id"] not in relocated_old_ids
            ]
            if unresolved_ids:
                await connection.execute(
                    text(
                        "UPDATE source_anchors SET status='UNRESOLVED',updated_at=:now "
                        "WHERE id=ANY(:ids) AND status IN ('VALID','STALE')"
                    ),
                    {"ids": unresolved_ids, "now": now},
                )
            await connection.execute(
                text(
                    "UPDATE parse_jobs SET status=:status,result_checksum=:checksum,"
                    "result_stats=CAST(:stats AS jsonb),temporal_run_id=:run,"
                    "version=version+1,updated_at=:now WHERE id=:id"
                ),
                {
                    "id": job["id"],
                    "status": manifest.status.value,
                    "checksum": manifest.result_checksum,
                    "stats": manifest.security_stats.model_dump_json(),
                    "run": run_id,
                    "now": now,
                },
            )
            version_state = {
                ParseJobStatus.SUCCEEDED: "PARSED",
                ParseJobStatus.PARTIAL_FAILED: "PARTIAL",
                ParseJobStatus.FAILED: "FAILED",
                ParseJobStatus.CANCELED: "STORED",
            }[manifest.status]
            activate = manifest.status in {
                ParseJobStatus.SUCCEEDED,
                ParseJobStatus.PARTIAL_FAILED,
            }
            await connection.execute(
                text(
                    "UPDATE source_versions SET "
                    "status=CASE WHEN active_parse_job_id IS NULL OR :activate "
                    "THEN :state ELSE status END,"
                    "active_parse_job_id=CASE WHEN :activate THEN :job ELSE active_parse_job_id END,"
                    "latest_parse_job_id=:job,version=version+1 WHERE id=:version"
                ),
                {
                    "version": job["source_version_id"],
                    "state": version_state,
                    "activate": activate,
                    "job": job["id"],
                },
            )
            event_type = {
                ParseJobStatus.SUCCEEDED: "io.nexweave.parse.completed.v1",
                ParseJobStatus.PARTIAL_FAILED: "io.nexweave.parse.partial-failed.v1",
                ParseJobStatus.FAILED: "io.nexweave.parse.failed.v1",
                ParseJobStatus.CANCELED: "io.nexweave.parse.failed.v1",
            }[manifest.status]
            workflow_principal = Principal(
                actor_type=ActorType(job["requested_by_actor_type"]),
                actor_id=job["created_by"],
                tenant_id=job["tenant_id"],
                subject="temporal-source-ingestion-v2",
                audience=("nexweave-api",),
                tenant_roles=frozenset(),
                clearance=DataClassification(job["classification"]),
                token_id=f"workflow:{job['id']}",
            )
            await self._insert_audit(
                connection,
                principal=workflow_principal,
                action="source.parse.finalize",
                resource_type="ParseJob",
                resource_id=job["id"],
                space_id=job["space_id"],
                trace_id=job["trace_id"] or "",
                outcome="SUCCEEDED",
                metadata={
                    "status": manifest.status.value,
                    "result_checksum": manifest.result_checksum,
                    "workflow_id": job["workflow_id"],
                    "run_id": run_id,
                    "executor": "TEMPORAL_ACTIVITY",
                },
            )
            await self._insert_outbox(
                connection,
                principal=workflow_principal,
                event_type=event_type,
                aggregate_type="ParseJob",
                aggregate_id=job["id"],
                aggregate_version=job["version"] + 1,
                space_id=job["space_id"],
                trace_id=job["trace_id"] or "",
                correlation_id=job["correlation_id"],
                payload={
                    "tenant_id": job["tenant_id"],
                    "space_id": job["space_id"],
                    "source_id": job["source_document_id"],
                    "source_version_id": job["source_version_id"],
                    "aggregate_version": job["version"] + 1,
                    "parse_job_id": job["id"],
                    "status": manifest.status.value,
                    "parser_id": job["parser_id"],
                    "parser_version": job["parser_version"],
                    "config_checksum": job["config_checksum"],
                    "document_model_version": job["document_model_version"],
                    "locator_version": job["locator_version"],
                    "result_checksum": manifest.result_checksum,
                    "failure_count": len(manifest.failure_units),
                    "workflow_id": job["workflow_id"],
                    "run_id": run_id,
                    "correlation_id": job["correlation_id"],
                    "causation_id": job["source_version_id"],
                    "trace_id": job["trace_id"],
                },
                causation_id=job["source_version_id"],
            )
            if job["import_batch_id"]:
                item_status = {
                    ParseJobStatus.SUCCEEDED: "SUCCEEDED",
                    ParseJobStatus.PARTIAL_FAILED: "PARTIAL",
                    ParseJobStatus.FAILED: "FAILED",
                    ParseJobStatus.CANCELED: "CANCELED",
                }[manifest.status]
                await connection.execute(
                    text(
                        "UPDATE source_import_batch_items SET status=:status,"
                        "updated_at=:now,updated_by=:actor WHERE source_version_id=:version"
                    ),
                    {
                        "status": item_status,
                        "now": now,
                        "actor": job["created_by"],
                        "version": job["source_version_id"],
                    },
                )
                await self._refresh_batch_status(
                    connection,
                    batch_id=job["import_batch_id"],
                    actor_id=job["created_by"],
                    now=now,
                )
        return _json_value(
            {
                "parse_job_id": manifest.parse_job_id,
                "status": manifest.status.value,
                "result_checksum": manifest.result_checksum,
            }
        )

    async def fail_parse_job(self, parse_job_id: UUID, run_id: str, code: str, detail: str) -> None:
        async with self._database.engine.begin() as connection:
            job = (
                (
                    await connection.execute(
                        text(
                            "SELECT p.*,v.source_document_id,v.classification,v.status AS "
                            "source_version_status,v.active_parse_job_id,v.latest_parse_job_id,"
                            "EXISTS (SELECT 1 FROM source_invalidations i "
                            "WHERE i.tenant_id=v.tenant_id AND i.space_id=v.space_id "
                            "AND i.source_version_id=v.id) AS invalidated,"
                            "u.import_batch_id FROM parse_jobs p JOIN source_versions v "
                            "ON v.tenant_id=p.tenant_id AND v.space_id=p.space_id "
                            "AND v.id=p.source_version_id JOIN source_upload_sessions u "
                            "ON u.id=v.upload_session_id WHERE p.id=:id FOR UPDATE OF p,v"
                        ),
                        {"id": parse_job_id},
                    )
                )
                .mappings()
                .first()
            )
            if job is None:
                return
            if job["status"] == "FAILED" and job["error_code"] == code:
                return
            if job["status"] in {"SUCCEEDED", "PARTIAL_FAILED", "CANCELED"}:
                return
            now = datetime.now(UTC)
            scan_status = (
                "INFECTED"
                if code == "SOURCE_MALWARE_DETECTED"
                else "FAILED"
                if code
                in {
                    "SOURCE_MALWARE_SCANNER_UNAVAILABLE",
                    "SOURCE_MALWARE_SCAN_FAILED",
                }
                else job["malware_scan_status"]
            )
            await connection.execute(
                text(
                    "UPDATE parse_jobs SET status='FAILED',error_code=:code,error_detail=:detail,"
                    "malware_scan_status=:scan_status,temporal_run_id=:run,version=version+1,"
                    "updated_at=:now WHERE id=:id"
                ),
                {
                    "id": parse_job_id,
                    "code": code,
                    "detail": detail[:1024],
                    "scan_status": scan_status,
                    "run": run_id,
                    "now": now,
                },
            )
            await connection.execute(
                text(
                    "UPDATE source_versions SET "
                    "status=CASE WHEN active_parse_job_id IS NULL THEN 'FAILED' ELSE status END,"
                    "version=version+1 WHERE id=:version AND latest_parse_job_id=:job "
                    "AND status <> 'SUPERSEDED' AND NOT :invalidated"
                ),
                {
                    "version": job["source_version_id"],
                    "job": parse_job_id,
                    "invalidated": job["invalidated"],
                },
            )
            workflow_principal = Principal(
                actor_type=ActorType(job["requested_by_actor_type"]),
                actor_id=job["created_by"],
                tenant_id=job["tenant_id"],
                subject="temporal-source-ingestion-v2",
                audience=("nexweave-api",),
                tenant_roles=frozenset(),
                clearance=DataClassification(job["classification"]),
                token_id=f"workflow:{job['id']}",
            )
            await self._insert_audit(
                connection,
                principal=workflow_principal,
                action="source.parse.finalize",
                resource_type="ParseJob",
                resource_id=parse_job_id,
                space_id=job["space_id"],
                trace_id=job["trace_id"] or "",
                outcome="FAILED",
                metadata={
                    "error_code": code,
                    "workflow_id": job["workflow_id"],
                    "run_id": run_id,
                    "executor": "TEMPORAL_ACTIVITY",
                },
            )
            await self._insert_outbox(
                connection,
                principal=workflow_principal,
                event_type="io.nexweave.parse.failed.v1",
                aggregate_type="ParseJob",
                aggregate_id=parse_job_id,
                aggregate_version=job["version"] + 1,
                space_id=job["space_id"],
                trace_id=job["trace_id"] or "",
                correlation_id=job["correlation_id"],
                payload={
                    "tenant_id": job["tenant_id"],
                    "space_id": job["space_id"],
                    "source_id": job["source_document_id"],
                    "source_version_id": job["source_version_id"],
                    "aggregate_version": job["version"] + 1,
                    "parse_job_id": parse_job_id,
                    "status": "FAILED",
                    "parser_id": job["parser_id"],
                    "parser_version": job["parser_version"],
                    "config_checksum": job["config_checksum"],
                    "document_model_version": job["document_model_version"],
                    "locator_version": job["locator_version"],
                    "result_checksum": None,
                    "failure_count": 1,
                    "error_code": code,
                    "workflow_id": job["workflow_id"],
                    "run_id": run_id,
                    "correlation_id": job["correlation_id"],
                    "causation_id": job["source_version_id"],
                    "trace_id": job["trace_id"],
                },
                causation_id=job["source_version_id"],
            )
            if job["import_batch_id"]:
                await connection.execute(
                    text(
                        "UPDATE source_import_batch_items SET status='FAILED',error_code=:code,"
                        "safe_detail=:detail,updated_at=:now,updated_by=:actor "
                        "WHERE source_version_id=:version"
                    ),
                    {
                        "code": code,
                        "detail": detail[:1024],
                        "now": now,
                        "actor": job["created_by"],
                        "version": job["source_version_id"],
                    },
                )
                await self._refresh_batch_status(
                    connection,
                    batch_id=job["import_batch_id"],
                    actor_id=job["created_by"],
                    now=now,
                )
