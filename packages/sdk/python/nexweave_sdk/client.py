"""Typed asynchronous client for the M8 public API."""

from __future__ import annotations

from types import TracebackType
from typing import Any, Self
from uuid import uuid4

import httpx

from nexweave_contracts import (
    AuditLogListResponse,
    ClaimListResponse,
    CompileJobCreate,
    CompileJobListResponse,
    CompileJobResponse,
    CompositionReportResponse,
    ConflictListResponse,
    ConflictResolutionCreate,
    ConnectorInstanceCreate,
    ConnectorInstanceListResponse,
    ConnectorInstanceResponse,
    ConnectorSyncRunCreate,
    ConnectorSyncRunResponse,
    DomainPackInstallationCreate,
    DomainPackInstallationResponse,
    DomainPackRegisterRequest,
    DomainPackRollbackCreate,
    DomainPackTrustKeyCreate,
    EvaluationSuiteCreate,
    EvaluationSuiteResponse,
    GraphTraverseResponse,
    ImportBatchCreate,
    ImportBatchResponse,
    KnowledgeSpaceResponse,
    ManagedObjectResponse,
    MembershipPolicy,
    ObjectUploadCreate,
    ObjectUploadSessionResponse,
    ObsidianExportResponse,
    ObsidianImportCreate,
    ObsidianImportResponse,
    ParseJobResponse,
    PreviewResponse,
    PrincipalResponse,
    QueryAnswerResponse,
    QueryCreate,
    ReleaseCandidateCreate,
    ReleaseCandidateListResponse,
    ReleaseCandidateResponse,
    ReleaseListResponse,
    ReleasePointerResponse,
    ReleasePointerSwitch,
    ReleasePublish,
    ReleaseResponse,
    ReparseRequest,
    ReviewActionCreate,
    ReviewCaseCreate,
    ReviewCaseListResponse,
    ReviewCaseResponse,
    ReviewPolicyCreate,
    ReviewPolicyResponse,
    SchemaCreate,
    SchemaListResponse,
    SchemaVersionCreate,
    SchemaVersionResponse,
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
    WikiLinkGraphResponse,
    WikiPageEdit,
    WikiPageListResponse,
    WikiPageResponse,
    WikiPageVersionListResponse,
    WikiPageVersionResponse,
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
    """M8 client with bearer auth, trace context, idempotency and ETag support."""

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

    async def list_schemas(self, space_id: str) -> SchemaListResponse:
        value = await self._request("GET", f"/api/v1/spaces/{space_id}/schemas")
        return SchemaListResponse.model_validate(value)

    async def create_schema(
        self, space_id: str, command: SchemaCreate, *, idempotency_key: str
    ) -> SchemaVersionResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/schemas",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return SchemaVersionResponse.model_validate(value)

    async def create_schema_version(
        self, schema_id: str, command: SchemaVersionCreate, *, idempotency_key: str
    ) -> SchemaVersionResponse:
        value = await self._request(
            "POST",
            f"/api/v1/schemas/{schema_id}/versions",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return SchemaVersionResponse.model_validate(value)

    async def validate_schema(
        self, schema_id: str, semantic_version: str
    ) -> CompositionReportResponse:
        value = await self._request(
            "POST", f"/api/v1/schemas/{schema_id}/versions/{semantic_version}/validate"
        )
        return CompositionReportResponse.model_validate(value)

    async def publish_schema(
        self,
        schema_id: str,
        semantic_version: str,
        *,
        version: int,
        idempotency_key: str,
    ) -> SchemaVersionResponse:
        value = await self._request(
            "POST",
            f"/api/v1/schemas/{schema_id}/versions/{semantic_version}/publish",
            version=version,
            idempotency_key=idempotency_key,
        )
        return SchemaVersionResponse.model_validate(value)

    async def list_domain_packs(self) -> dict[str, Any]:
        return await self._request("GET", "/api/v1/domain-packs")

    async def register_domain_pack_trust_key(
        self, command: DomainPackTrustKeyCreate, *, idempotency_key: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/domain-pack-trust-keys",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )

    async def register_domain_pack(
        self, command: DomainPackRegisterRequest, *, idempotency_key: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            "/api/v1/domain-packs",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )

    async def install_domain_pack(
        self,
        space_id: str,
        command: DomainPackInstallationCreate,
        *,
        idempotency_key: str,
    ) -> DomainPackInstallationResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/domain-pack-installations",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return DomainPackInstallationResponse.model_validate(value)

    async def get_domain_pack_installation(
        self, installation_id: str
    ) -> DomainPackInstallationResponse:
        value = await self._request("GET", f"/api/v1/domain-pack-installations/{installation_id}")
        return DomainPackInstallationResponse.model_validate(value)

    async def rollback_domain_pack(
        self,
        space_id: str,
        command: DomainPackRollbackCreate,
        *,
        idempotency_key: str,
    ) -> DomainPackInstallationResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/domain-pack-installations/rollback",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return DomainPackInstallationResponse.model_validate(value)

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

    async def create_compile_job(
        self, space_id: str, command: CompileJobCreate, *, idempotency_key: str
    ) -> CompileJobResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/compile-jobs",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return CompileJobResponse.model_validate(value)

    async def list_compile_jobs(self, space_id: str) -> CompileJobListResponse:
        return CompileJobListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/compile-jobs")
        )

    async def get_compile_job(self, compile_job_id: str) -> CompileJobResponse:
        return CompileJobResponse.model_validate(
            await self._request("GET", f"/api/v1/compile-jobs/{compile_job_id}")
        )

    async def list_wiki_pages(self, space_id: str) -> WikiPageListResponse:
        return WikiPageListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/wiki/pages")
        )

    async def get_wiki_link_graph(
        self,
        space_id: str,
        *,
        focus_page_id: str | None = None,
        max_depth: int = 2,
        node_limit: int = 180,
    ) -> WikiLinkGraphResponse:
        params: dict[str, str | int] = {
            "max_depth": max_depth,
            "node_limit": node_limit,
        }
        if focus_page_id is not None:
            params["focus_page_id"] = focus_page_id
        return WikiLinkGraphResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/wiki-link-graph", params=params)
        )

    async def get_wiki_page(self, page_id: str) -> WikiPageResponse:
        return WikiPageResponse.model_validate(
            await self._request("GET", f"/api/v1/wiki/pages/{page_id}")
        )

    async def edit_wiki_page(
        self,
        page_id: str,
        version_id: str,
        command: WikiPageEdit,
        *,
        page_version: int,
        idempotency_key: str,
    ) -> WikiPageResponse:
        value = await self._request(
            "PATCH",
            f"/api/v1/wiki/pages/{page_id}/drafts/{version_id}",
            json=command.model_dump(mode="json"),
            version=page_version,
            idempotency_key=idempotency_key,
        )
        return WikiPageResponse.model_validate(value)

    async def list_wiki_page_versions(self, page_id: str) -> WikiPageVersionListResponse:
        return WikiPageVersionListResponse.model_validate(
            await self._request("GET", f"/api/v1/wiki/pages/{page_id}/versions")
        )

    async def get_wiki_page_version(self, page_id: str, version_id: str) -> WikiPageVersionResponse:
        return WikiPageVersionResponse.model_validate(
            await self._request("GET", f"/api/v1/wiki/pages/{page_id}/versions/{version_id}")
        )

    async def list_claims(self, space_id: str) -> ClaimListResponse:
        return ClaimListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/claims")
        )

    async def create_review_policy(
        self, space_id: str, command: ReviewPolicyCreate, *, idempotency_key: str
    ) -> ReviewPolicyResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/review-policies",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ReviewPolicyResponse.model_validate(value)

    async def create_review_case(
        self, space_id: str, command: ReviewCaseCreate, *, idempotency_key: str
    ) -> ReviewCaseResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/review-cases",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ReviewCaseResponse.model_validate(value)

    async def list_review_cases(self, space_id: str) -> ReviewCaseListResponse:
        return ReviewCaseListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/review-cases")
        )

    async def act_on_review(
        self, case_id: str, task_id: str, command: ReviewActionCreate, *, idempotency_key: str
    ) -> ReviewCaseResponse:
        value = await self._request(
            "POST",
            f"/api/v1/review-cases/{case_id}/tasks/{task_id}/actions",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ReviewCaseResponse.model_validate(value)

    async def list_conflicts(self, space_id: str) -> ConflictListResponse:
        return ConflictListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/conflicts")
        )

    async def resolve_conflict(
        self, conflict_id: str, command: ConflictResolutionCreate, *, idempotency_key: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/conflicts/{conflict_id}/decisions",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )

    async def create_evaluation_suite(
        self, space_id: str, command: EvaluationSuiteCreate, *, idempotency_key: str
    ) -> EvaluationSuiteResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/evaluation-suites",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return EvaluationSuiteResponse.model_validate(value)

    async def list_evaluation_suites(self, space_id: str) -> list[EvaluationSuiteResponse]:
        response = await self._send("GET", f"/api/v1/spaces/{space_id}/evaluation-suites")
        return [EvaluationSuiteResponse.model_validate(value) for value in response.json()]

    async def create_release_candidate(
        self, space_id: str, command: ReleaseCandidateCreate, *, idempotency_key: str
    ) -> ReleaseCandidateResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/release-candidates",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ReleaseCandidateResponse.model_validate(value)

    async def list_release_candidates(self, space_id: str) -> ReleaseCandidateListResponse:
        return ReleaseCandidateListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/release-candidates")
        )

    async def publish_release_candidate(
        self, candidate_id: str, command: ReleasePublish, *, idempotency_key: str
    ) -> ReleaseCandidateResponse:
        value = await self._request(
            "POST",
            f"/api/v1/release-candidates/{candidate_id}/publish",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ReleaseCandidateResponse.model_validate(value)

    async def list_releases(self, space_id: str) -> ReleaseListResponse:
        return ReleaseListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/releases")
        )

    async def get_release(self, release_id: str) -> ReleaseResponse:
        return ReleaseResponse.model_validate(
            await self._request("GET", f"/api/v1/releases/{release_id}")
        )

    async def get_release_pointer(
        self, space_id: str, *, channel: str = "stable"
    ) -> ReleasePointerResponse:
        return ReleasePointerResponse.model_validate(
            await self._request(
                "GET", f"/api/v1/spaces/{space_id}/release-pointer", params={"channel": channel}
            )
        )

    async def switch_release_pointer(
        self,
        space_id: str,
        command: ReleasePointerSwitch,
        *,
        expected_version: int,
        idempotency_key: str,
    ) -> ReleasePointerResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/release-pointer",
            json=command.model_dump(mode="json"),
            headers={"If-Match": f'"v{expected_version}"'},
            idempotency_key=idempotency_key,
        )
        return ReleasePointerResponse.model_validate(value)

    async def export_release_json(self, release_id: str) -> dict[str, Any]:
        return await self._request(
            "GET", f"/api/v1/releases/{release_id}/export", params={"format": "json"}
        )

    async def rebuild_release_projection(
        self, release_id: str, *, idempotency_key: str
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/api/v1/releases/{release_id}/projections/rebuild",
            idempotency_key=idempotency_key,
        )

    async def ask_release(self, release_id: str, command: QueryCreate) -> QueryAnswerResponse:
        value = await self._request(
            "POST",
            f"/api/v1/releases/{release_id}/queries",
            json=command.model_dump(mode="json"),
        )
        return QueryAnswerResponse.model_validate(value)

    async def get_query_answer(self, answer_id: str) -> QueryAnswerResponse:
        return QueryAnswerResponse.model_validate(
            await self._request("GET", f"/api/v1/query-answers/{answer_id}")
        )

    async def traverse_release_graph(
        self,
        release_id: str,
        *,
        start_entity_id: str,
        max_depth: int = 1,
        mode: str = "TRAVERSE",
    ) -> GraphTraverseResponse:
        value = await self._request(
            "GET",
            f"/api/v1/releases/{release_id}/graph/traverse",
            params={
                "start_entity_id": start_entity_id,
                "max_depth": max_depth,
                "mode": mode,
            },
        )
        return GraphTraverseResponse.model_validate(value)

    async def create_connector_instance(
        self, space_id: str, command: ConnectorInstanceCreate, *, idempotency_key: str
    ) -> ConnectorInstanceResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/connector-instances",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ConnectorInstanceResponse.model_validate(value)

    async def list_connector_instances(self, space_id: str) -> ConnectorInstanceListResponse:
        return ConnectorInstanceListResponse.model_validate(
            await self._request("GET", f"/api/v1/spaces/{space_id}/connector-instances")
        )

    async def create_connector_sync_run(
        self,
        space_id: str,
        instance_id: str,
        command: ConnectorSyncRunCreate,
        *,
        idempotency_key: str,
    ) -> ConnectorSyncRunResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/connector-instances/{instance_id}/sync-runs",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ConnectorSyncRunResponse.model_validate(value)

    async def export_obsidian_page(self, page_id: str) -> ObsidianExportResponse:
        return ObsidianExportResponse.model_validate(
            await self._request("POST", f"/api/v1/wiki/pages/{page_id}/obsidian-exports")
        )

    async def import_obsidian_markdown(
        self, space_id: str, command: ObsidianImportCreate, *, idempotency_key: str
    ) -> ObsidianImportResponse:
        value = await self._request(
            "POST",
            f"/api/v1/spaces/{space_id}/obsidian-imports",
            json=command.model_dump(mode="json"),
            idempotency_key=idempotency_key,
        )
        return ObsidianImportResponse.model_validate(value)

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
