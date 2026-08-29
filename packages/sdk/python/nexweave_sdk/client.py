"""Typed asynchronous client for the M3 public API."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self
from uuid import uuid4

import httpx

from nexweave_contracts import (
    AuditLogListResponse,
    ImportBatchCreate,
    ImportBatchResponse,
    KnowledgeSpaceResponse,
    ManagedObjectResponse,
    MembershipPolicy,
    ObjectUploadCreate,
    ObjectUploadSessionResponse,
    ParseJobResponse,
    PreviewResponse,
    PrincipalResponse,
    ReparseRequest,
    SegmentListResponse,
    SourceDocumentResponse,
    SourceInvalidationCreate,
    SourceInvalidationResponse,
    SourceListResponse,
    SourceUploadComplete,
    SourceUploadCompleteResponse,
    SourceUploadCreate,
    SourceUploadSessionResponse,
    SourceVersionResponse,
    SpaceCreate,
    SpaceListResponse,
    SpaceMemberResponse,
    SpacePatch,
    WorkflowCommandRequest,
    WorkflowCommandResponse,
    WorkflowReconcileResponse,
    WorkflowTaskCreate,
    WorkflowTaskDetailResponse,
    WorkflowTaskListResponse,
    WorkflowTaskResponse,
)


class NexweaveSdkError(RuntimeError):
    def __init__(self, status: int, code: str, detail: str, trace_id: str | None) -> None:
        super().__init__(detail)
        self.status = status
        self.code = code
        self.trace_id = trace_id


class NexweaveClient:
    """M3 client with bearer auth, trace context, idempotency and ETag support."""

    def __init__(
        self,
        base_url: str,
        access_token: str,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._client = httpx.AsyncClient(
            base_url=base_url.rstrip("/"), transport=transport, timeout=timeout
        )
        self._access_token = access_token

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc, traceback
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def me(self) -> PrincipalResponse:
        return PrincipalResponse.model_validate(await self._request("GET", "/api/v1/auth/me"))

    async def list_spaces(self) -> SpaceListResponse:
        return SpaceListResponse.model_validate(await self._request("GET", "/api/v1/spaces"))

    async def create_space(
        self, command: SpaceCreate, *, idempotency_key: str
    ) -> KnowledgeSpaceResponse:
        value = await self._request(
            "POST",
            "/api/v1/spaces",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return KnowledgeSpaceResponse.model_validate(value)

    async def update_space(
        self,
        space_id: str,
        command: SpacePatch,
        *,
        version: int,
        idempotency_key: str,
    ) -> KnowledgeSpaceResponse:
        value = await self._request(
            "PATCH",
            f"/api/v1/spaces/{space_id}",
            json=command.model_dump(mode="json", exclude_unset=True),
            idempotency_key=idempotency_key,
            version=version,
        )
        return KnowledgeSpaceResponse.model_validate(value)

    async def archive_space(
        self, space_id: str, *, version: int, idempotency_key: str
    ) -> KnowledgeSpaceResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/archive",
            idempotency_key=idempotency_key,
            version=version,
        )
        return KnowledgeSpaceResponse.model_validate(value)

    async def grant_member(
        self,
        space_id: str,
        subject_id: str,
        policy: MembershipPolicy,
        *,
        idempotency_key: str,
    ) -> SpaceMemberResponse:
        value = await self._request(
            "PUT",
            f"/api/v1/spaces/{space_id}/members/{subject_id}",
            json=policy.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return SpaceMemberResponse.model_validate(value)

    async def revoke_member(
        self, space_id: str, subject_id: str, *, idempotency_key: str
    ) -> SpaceMemberResponse:
        value = await self._request(
            "DELETE",
            f"/api/v1/spaces/{space_id}/members/{subject_id}",
            idempotency_key=idempotency_key,
        )
        return SpaceMemberResponse.model_validate(value)

    async def create_upload(
        self, space_id: str, command: ObjectUploadCreate, *, idempotency_key: str
    ) -> ObjectUploadSessionResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/object-uploads",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ObjectUploadSessionResponse.model_validate(value)

    async def upload_content(
        self, upload_id: str, content: bytes, *, content_type: str
    ) -> ManagedObjectResponse:
        value = await self._request(
            "PUT",
            f"/api/v1/object-uploads/{upload_id}/content",
            content=content,
            content_type=content_type,
        )
        return ManagedObjectResponse.model_validate(value)

    async def download_object(self, object_id: str) -> bytes:
        response = await self._send("GET", f"/api/v1/objects/{object_id}/content")
        return response.content

    async def list_audit_logs(self, *, limit: int = 50) -> AuditLogListResponse:
        value = await self._request("GET", f"/api/v1/audit-logs?limit={limit}")
        return AuditLogListResponse.model_validate(value)

    async def list_workflow_tasks(self, space_id: str) -> WorkflowTaskListResponse:
        value = await self._request("GET", f"/api/v1/spaces/{space_id}/workflow-tasks")
        return WorkflowTaskListResponse.model_validate(value)

    async def get_workflow_task(self, task_id: str) -> WorkflowTaskDetailResponse:
        value = await self._request("GET", f"/api/v1/workflow-tasks/{task_id}")
        return WorkflowTaskDetailResponse.model_validate(value)

    async def create_workflow_task(
        self, space_id: str, command: WorkflowTaskCreate, *, idempotency_key: str
    ) -> WorkflowTaskResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/workflow-tasks",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return WorkflowTaskResponse.model_validate(value)

    async def command_workflow_task(
        self,
        task_id: str,
        command: WorkflowCommandRequest,
        *,
        version: int,
        idempotency_key: str,
    ) -> WorkflowCommandResponse:
        value = await self._request(
            "POST",
            f"/api/v1/workflow-tasks/{task_id}/commands",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            version=version,
        )
        return WorkflowCommandResponse.model_validate(value)

    async def reconcile_workflow_task(self, task_id: str) -> WorkflowReconcileResponse:
        value = await self._request("POST", f"/api/v1/workflow-tasks/{task_id}/reconcile")
        return WorkflowReconcileResponse.model_validate(value)

    async def create_source_import_batch(
        self, space_id: str, command: ImportBatchCreate, *, idempotency_key: str
    ) -> ImportBatchResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/source-import-batches",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ImportBatchResponse.model_validate(value)

    async def get_source_import_batch(self, batch_id: str) -> ImportBatchResponse:
        return ImportBatchResponse.model_validate(
            await self._request("GET", f"/api/v1/source-import-batches/{batch_id}")
        )

    async def create_source_upload(
        self, space_id: str, command: SourceUploadCreate, *, idempotency_key: str
    ) -> SourceUploadSessionResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/sources/uploads",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return SourceUploadSessionResponse.model_validate(value)

    async def upload_source_content(
        self, upload_id: str, content: bytes, *, content_type: str
    ) -> SourceUploadSessionResponse:
        value = await self._request(
            "PUT",
            f"/api/v1/sources/uploads/{upload_id}/content",
            content=content,
            content_type=content_type,
        )
        return SourceUploadSessionResponse.model_validate(value)

    async def complete_source_upload(
        self, upload_id: str, command: SourceUploadComplete, *, idempotency_key: str
    ) -> SourceUploadCompleteResponse:
        value = await self._request(
            "POST",
            f"/api/v1/sources/uploads/{upload_id}/complete",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return SourceUploadCompleteResponse.model_validate(value)

    async def list_sources(
        self,
        space_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
        status: str | None = None,
        content_type: str | None = None,
        classification: str | None = None,
        search: str | None = None,
    ) -> SourceListResponse:
        params: dict[str, str | int] = {"limit": limit}
        params.update(
            {
                key: value
                for key, value in {
                    "cursor": cursor,
                    "status": status,
                    "content_type": content_type,
                    "classification": classification,
                    "search": search,
                }.items()
                if value is not None
            }
        )
        return SourceListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/sources", params=params)
        )

    async def get_source(self, source_id: str) -> SourceDocumentResponse:
        return SourceDocumentResponse.model_validate(
            await self._request("GET", f"/api/v1/sources/{source_id}")
        )

    async def archive_source(
        self, source_id: str, *, version: int, idempotency_key: str
    ) -> SourceDocumentResponse:
        value = await self._request(
            "POST",
            f"/api/v1/sources/{source_id}/archive",
            idempotency_key=idempotency_key,
            version=version,
        )
        return SourceDocumentResponse.model_validate(value)

    async def get_source_version(self, source_id: str, version_id: str) -> SourceVersionResponse:
        value = await self._request("GET", f"/api/v1/sources/{source_id}/versions/{version_id}")
        return SourceVersionResponse.model_validate(value)

    async def download_source_version(self, version_id: str) -> bytes:
        response = await self._send("GET", f"/api/v1/source-versions/{version_id}/content")
        return response.content

    async def reparse_source_version(
        self,
        version_id: str,
        command: ReparseRequest,
        *,
        version: int,
        idempotency_key: str,
    ) -> ParseJobResponse:
        value = await self._request(
            "POST",
            f"/api/v1/source-versions/{version_id}/parse",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            version=version,
        )
        return ParseJobResponse.model_validate(value)

    async def retry_parse_job(
        self, parse_job_id: str, *, version: int, idempotency_key: str
    ) -> ParseJobResponse:
        value = await self._request(
            "POST",
            f"/api/v1/parse-jobs/{parse_job_id}/retry",
            idempotency_key=idempotency_key,
            version=version,
        )
        return ParseJobResponse.model_validate(value)

    async def cancel_parse_job(
        self, parse_job_id: str, *, version: int, idempotency_key: str
    ) -> ParseJobResponse:
        value = await self._request(
            "POST",
            f"/api/v1/parse-jobs/{parse_job_id}/cancel",
            idempotency_key=idempotency_key,
            version=version,
        )
        return ParseJobResponse.model_validate(value)

    async def get_parse_job(self, parse_job_id: str) -> ParseJobResponse:
        return ParseJobResponse.model_validate(
            await self._request("GET", f"/api/v1/parse-jobs/{parse_job_id}")
        )

    async def list_source_segments(
        self,
        version_id: str,
        *,
        limit: int = 50,
        cursor: str | None = None,
        parse_job_id: str | None = None,
    ) -> SegmentListResponse:
        params = {
            key: value
            for key, value in {
                "limit": limit,
                "cursor": cursor,
                "parse_job_id": parse_job_id,
            }.items()
            if value is not None
        }
        return SegmentListResponse.model_validate(
            await self._request(
                "GET", f"/api/v1/source-versions/{version_id}/segments", params=params
            )
        )

    async def preview_source_version(
        self, version_id: str, *, anchor_id: str | None = None
    ) -> PreviewResponse:
        params = {"anchor_id": anchor_id} if anchor_id is not None else None
        return PreviewResponse.model_validate(
            await self._request(
                "GET", f"/api/v1/source-versions/{version_id}/preview", params=params
            )
        )

    async def invalidate_source_version(
        self,
        version_id: str,
        command: SourceInvalidationCreate,
        *,
        version: int,
        idempotency_key: str,
    ) -> SourceInvalidationResponse:
        value = await self._request(
            "POST",
            f"/api/v1/source-versions/{version_id}/invalidate",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            version=version,
        )
        return SourceInvalidationResponse.model_validate(value)

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._send(method, path, **kwargs)
        value = response.json()
        if not isinstance(value, dict):
            raise NexweaveSdkError(
                response.status_code,
                "INVALID_RESPONSE",
                "The API returned a non-object JSON response.",
                response.headers.get("X-Trace-Id"),
            )
        return value

    async def _send(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        content: bytes | None = None,
        content_type: str | None = None,
        idempotency_key: str | None = None,
        version: int | None = None,
        params: dict[str, str | int] | None = None,
    ) -> httpx.Response:
        trace_id, span_id = uuid4().hex, uuid4().hex[:16]
        headers = {
            "Authorization": f"Bearer {self._access_token}",
            "Accept": "application/json",
            "traceparent": f"00-{trace_id}-{span_id}-01",
        }
        if content_type is not None:
            headers["Content-Type"] = content_type
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if version is not None:
            headers["If-Match"] = f'"v{version}"'
        response = await self._client.request(
            method, path, headers=headers, json=json, content=content, params=params
        )
        if response.is_error:
            problem = response.json()
            raise NexweaveSdkError(
                response.status_code,
                str(problem.get("code", "API_ERROR")),
                str(problem.get("detail", "The API request failed.")),
                problem.get("trace_id") or response.headers.get("X-Trace-Id"),
            )
        return response
