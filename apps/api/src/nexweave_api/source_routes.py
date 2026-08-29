"""Authenticated M3 Source, immutable Raw, parse and preview APIs."""

from __future__ import annotations

import hashlib
from pathlib import PurePath
from typing import Annotated, Any, cast
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Header, Query, Request, Response, status
from fastapi.responses import Response as BinaryResponse

from nexweave_api.errors import ApiProblem
from nexweave_api.m1_routes import (
    PROBLEM_RESPONSE,
    IdempotencyKey,
    IfMatch,
    PageCursor,
    PageLimit,
    PrincipalDependency,
    _paginate,
    _settings,
    _trace_id,
    _version_from_etag,
)
from nexweave_api.source_repository import SourceRepository
from nexweave_application import ObjectStoragePort, StoredObjectInfo, WorkflowGatewayPort
from nexweave_contracts import (
    ImportBatchCreate,
    ImportBatchResponse,
    ParseJobResponse,
    PreviewResponse,
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
)
from nexweave_contracts.source import PreviewLocatorResult
from nexweave_domain import DataClassification

router = APIRouter(
    prefix="/api/v1",
    tags=["sources"],
    responses={
        400: PROBLEM_RESPONSE,
        401: PROBLEM_RESPONSE,
        403: PROBLEM_RESPONSE,
        404: PROBLEM_RESPONSE,
        409: PROBLEM_RESPONSE,
        412: PROBLEM_RESPONSE,
        413: PROBLEM_RESPONSE,
        415: PROBLEM_RESPONSE,
        422: PROBLEM_RESPONSE,
        503: PROBLEM_RESPONSE,
    },
)

SourceStatusFilter = Annotated[str | None, Query(alias="status", max_length=32)]
SourceTypeFilter = Annotated[str | None, Query(alias="content_type", max_length=255)]
ClassificationFilter = Annotated[DataClassification | None, Query()]
SearchFilter = Annotated[str | None, Query(max_length=255)]
ParseJobFilter = Annotated[UUID | None, Query(alias="parse_job_id")]
AnchorFilter = Annotated[UUID | None, Query(alias="anchor_id")]
ContentTypeHeader = Annotated[str | None, Header(alias="Content-Type")]

_CLEARANCE = {
    DataClassification.PUBLIC: 0,
    DataClassification.INTERNAL: 1,
    DataClassification.CONFIDENTIAL: 2,
    DataClassification.HIGHLY_RESTRICTED: 3,
}
_MIME_SUFFIX = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/markdown": ".md",
    "text/plain": ".txt",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def _repository(request: Request) -> SourceRepository:
    return cast(SourceRepository, request.app.state.repository)


def _storage(request: Request) -> ObjectStoragePort:
    return cast(ObjectStoragePort, request.app.state.object_storage)


def _workflow(request: Request) -> WorkflowGatewayPort:
    return cast(WorkflowGatewayPort, request.app.state.workflow_gateway)


def _fields(model: type[Any], value: dict[str, Any]) -> dict[str, Any]:
    return {name: value.get(name) for name in model.model_fields}


def _validate_controlled_type(filename: str, content_type: str, content: bytes) -> None:
    expected_suffix = _MIME_SUFFIX.get(content_type)
    suffix = PurePath(filename).suffix.lower()
    if expected_suffix is None or suffix != expected_suffix:
        raise ApiProblem(
            415,
            "SOURCE_TYPE_UNSUPPORTED",
            "Source type unsupported",
            "The extension and MIME type are not an approved M3 pair.",
        )
    if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
        raise ApiProblem(
            415,
            "SOURCE_TYPE_UNSUPPORTED",
            "Source type mismatch",
            "The PDF magic bytes do not match the controlled MIME type.",
        )
    if content_type.endswith(("wordprocessingml.document", "spreadsheetml.sheet")):
        if not content.startswith(b"PK\x03\x04"):
            raise ApiProblem(
                415,
                "SOURCE_TYPE_UNSUPPORTED",
                "Source type mismatch",
                "The OOXML magic bytes do not match the controlled MIME type.",
            )
    if content_type.startswith("text/") and b"\x00" in content[:4096]:
        raise ApiProblem(
            415,
            "SOURCE_TYPE_UNSUPPORTED",
            "Source type mismatch",
            "The controlled text input contains binary bytes.",
        )


async def _read_bounded_upload(request: Request, *, expected_size: int, maximum_size: int) -> bytes:
    limit = min(expected_size, maximum_size)
    declared_length = request.headers.get("content-length")
    if declared_length:
        try:
            parsed_length = int(declared_length)
            if parsed_length < 0:
                raise ValueError
            if parsed_length > limit:
                raise ApiProblem(
                    413,
                    "PARSER_RESOURCE_LIMIT_EXCEEDED",
                    "Upload too large",
                    "The request exceeds the controlled Source upload size.",
                )
        except ValueError as exc:
            raise ApiProblem(
                400,
                "INVALID_REQUEST",
                "Invalid content length",
                "Content-Length must be a non-negative integer.",
            ) from exc
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > limit:
            raise ApiProblem(
                413,
                "PARSER_RESOURCE_LIMIT_EXCEEDED",
                "Upload too large",
                "The streamed request exceeds the controlled Source upload size.",
            )
    return bytes(content)


def _download_content_disposition(filename: str) -> str:
    leaf = PurePath(filename).name
    clean = "".join(
        character
        for character in leaf
        if 32 <= ord(character) < 127 and character not in {'"', "\\"}
    ).strip()
    fallback = clean[:255] or "source"
    encoded = quote(
        "".join(character for character in leaf if ord(character) >= 32 and ord(character) != 127),
        safe="",
    )
    return f"attachment; filename=\"{fallback}\"; filename*=UTF-8''{encoded}"


async def _authorize_resource(
    request: Request,
    *,
    principal: Any,
    space_id: str | UUID,
    action: str,
    classification: str | DataClassification,
) -> None:
    await _repository(request).authorize_space(
        principal=principal,
        space_id=UUID(str(space_id)),
        action=action,
        trace_id=_trace_id(request),
        classification=DataClassification(classification),
    )


async def _filter_sources_by_content_type(
    repository: SourceRepository,
    *,
    principal: Any,
    items: list[dict[str, Any]],
    content_type: str,
) -> list[dict[str, Any]]:
    """Return each matching SourceDocument exactly once."""

    filtered: list[dict[str, Any]] = []
    for item in items:
        detail = await repository.get_source(principal=principal, source_id=UUID(item["id"]))
        if any(version["content_type"] == content_type for version in detail["versions"]):
            filtered.append(item)
    return filtered


async def _start_parse_workflow(
    request: Request, *, parse_job_id: UUID, workflow_id: str, trace_id: str, retry: bool = False
) -> str:
    settings = _settings(request)
    payload = {
        "workflow_type": "SOURCE_INGESTION_V2",
        "parse_job_id": str(parse_job_id),
        "trace_id": trace_id,
        "activity_task_queue": settings.temporal_parser_activity_task_queue,
    }
    if retry:
        execution = await _workflow(request).retry(
            workflow_name="nexweave.source-ingestion.v2",
            workflow_id=workflow_id,
            payload=payload,
        )
    else:
        execution = await _workflow(request).start(
            workflow_name="nexweave.source-ingestion.v2",
            workflow_id=workflow_id,
            payload=payload,
        )
    await _repository(request).attach_parse_run(parse_job_id, execution.run_id)
    return execution.run_id


@router.post(
    "/spaces/{space_id}/source-import-batches",
    response_model=ImportBatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_import_batch(
    request: Request,
    space_id: UUID,
    body: ImportBatchCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> ImportBatchResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="source.upload",
        trace_id=_trace_id(request),
    )
    result = await repository.create_import_batch(
        principal=principal,
        space_id=space_id,
        display_name=body.display_name,
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    return ImportBatchResponse.model_validate(result)


@router.get("/source-import-batches/{batch_id}", response_model=ImportBatchResponse)
async def get_import_batch(
    request: Request, batch_id: UUID, principal: PrincipalDependency, response: Response
) -> ImportBatchResponse:
    result = await _repository(request).get_import_batch(principal=principal, batch_id=batch_id)
    await _repository(request).authorize_space(
        principal=principal,
        space_id=UUID(result["space_id"]),
        action="source.read",
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return ImportBatchResponse.model_validate(result)


@router.post(
    "/spaces/{space_id}/sources/uploads",
    response_model=SourceUploadSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_source_upload(
    request: Request,
    space_id: UUID,
    body: SourceUploadCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> SourceUploadSessionResponse:
    settings, repository = _settings(request), _repository(request)
    if body.expected_size > settings.object_upload_max_bytes:
        raise ApiProblem(
            413,
            "PARSER_RESOURCE_LIMIT_EXCEEDED",
            "Upload too large",
            "The Raw input exceeds the configured bounded upload policy.",
        )
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="source.upload",
        trace_id=_trace_id(request),
        classification=body.classification,
    )
    result = await repository.create_source_upload(
        principal=principal,
        space_id=space_id,
        payload=body.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        ttl_seconds=settings.object_upload_session_seconds,
        trace_id=_trace_id(request),
    )
    return SourceUploadSessionResponse.model_validate(result)


@router.put(
    "/sources/uploads/{upload_id}/content",
    response_model=SourceUploadSessionResponse,
)
async def upload_source_content(
    request: Request,
    upload_id: UUID,
    principal: PrincipalDependency,
    content_type: ContentTypeHeader = None,
) -> SourceUploadSessionResponse:
    repository = _repository(request)
    session = await repository.get_source_upload(principal=principal, upload_id=upload_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=session["space_id"],
        action="source.upload",
        classification=session["classification"],
    )
    if session["status"] not in {"INITIATED", "UPLOADING"}:
        raise ApiProblem(
            409,
            "STATE_TRANSITION_NOT_ALLOWED",
            "Upload unavailable",
            "The controlled Source upload session no longer accepts bytes.",
        )
    try:
        content = await _read_bounded_upload(
            request,
            expected_size=int(session["expected_size"]),
            maximum_size=_settings(request).object_upload_max_bytes,
        )
        checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
        if (
            len(content) != int(session["expected_size"])
            or checksum != session["expected_checksum"]
        ):
            raise ApiProblem(
                415,
                "SOURCE_CHECKSUM_MISMATCH",
                "Raw verification failed",
                "The uploaded bytes do not match the controlled size and SHA-256.",
            )
        if content_type != session["content_type"]:
            raise ApiProblem(
                415,
                "SOURCE_TYPE_UNSUPPORTED",
                "Content type mismatch",
                "The Content-Type does not match the controlled Source upload session.",
            )
        _validate_controlled_type(session["filename"], content_type, content)
        info = await _storage(request).put_if_absent(
            key=session["object_key"],
            content=content,
            content_type=content_type,
            checksum_sha256=checksum,
        )
    except ApiProblem as exc:
        if exc.status < 500:
            await repository.terminate_source_upload(
                principal=principal,
                upload_id=upload_id,
                reason_code=exc.code,
                safe_detail=exc.detail,
                canceled=False,
                trace_id=_trace_id(request),
            )
        raise
    result = await repository.mark_source_content_uploaded(
        principal=principal,
        upload_id=upload_id,
        info=info,
        trace_id=_trace_id(request),
    )
    return SourceUploadSessionResponse.model_validate(
        {
            **_fields(SourceUploadSessionResponse, result),
            "upload_url": f"/api/v1/sources/uploads/{upload_id}/content",
        }
    )


@router.post(
    "/sources/uploads/{upload_id}/abort",
    response_model=SourceUploadSessionResponse,
)
async def abort_source_upload(
    request: Request,
    upload_id: UUID,
    principal: PrincipalDependency,
    _idempotency_key: IdempotencyKey,
) -> SourceUploadSessionResponse:
    repository = _repository(request)
    session = await repository.get_source_upload(principal=principal, upload_id=upload_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=session["space_id"],
        action="source.upload",
        classification=session["classification"],
    )
    result = await repository.terminate_source_upload(
        principal=principal,
        upload_id=upload_id,
        reason_code="SOURCE_UPLOAD_CANCELED",
        safe_detail="The user canceled the controlled upload session.",
        canceled=True,
        trace_id=_trace_id(request),
    )
    return SourceUploadSessionResponse.model_validate(
        {
            **_fields(SourceUploadSessionResponse, result),
            "upload_url": f"/api/v1/sources/uploads/{upload_id}/content",
        }
    )


@router.post(
    "/sources/uploads/{upload_id}/complete",
    response_model=SourceUploadCompleteResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def complete_source_upload(
    request: Request,
    upload_id: UUID,
    body: SourceUploadComplete,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
) -> SourceUploadCompleteResponse:
    repository = _repository(request)
    session = await repository.get_source_upload(principal=principal, upload_id=upload_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=session["space_id"],
        action="source.upload",
        classification=session["classification"],
    )
    if body.checksum != session["expected_checksum"] or body.size != session["expected_size"]:
        problem = ApiProblem(
            422,
            "SOURCE_CHECKSUM_MISMATCH",
            "Completion declaration mismatch",
            "The completion request does not match the controlled upload session.",
        )
        await repository.terminate_source_upload(
            principal=principal,
            upload_id=upload_id,
            reason_code=problem.code,
            safe_detail=problem.detail,
            canceled=False,
            trace_id=_trace_id(request),
        )
        raise problem
    try:
        head = await _storage(request).head(
            key=session["object_key"], version_id=session["object_version_id"]
        )
        content = await _storage(request).get(
            key=session["object_key"], version_id=session["object_version_id"]
        )
        computed_checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
        verified = StoredObjectInfo(
            key=session["object_key"],
            version_id=head.version_id,
            size=len(content),
            checksum_sha256=computed_checksum,
            content_type=head.content_type,
        )
        _validate_controlled_type(session["filename"], verified.content_type, content)
        result = await repository.register_raw_and_parse_job(
            principal=principal,
            upload_id=upload_id,
            verified_info=verified,
            idempotency_key=idempotency_key,
            trace_id=_trace_id(request),
        )
    except ApiProblem as exc:
        if exc.status < 500:
            await repository.terminate_source_upload(
                principal=principal,
                upload_id=upload_id,
                reason_code=exc.code,
                safe_detail=exc.detail,
                canceled=False,
                trace_id=_trace_id(request),
            )
        raise
    parse_job_id = UUID(result["parse_job_id"])
    run_id = await _start_parse_workflow(
        request,
        parse_job_id=parse_job_id,
        workflow_id=result["workflow_id"],
        trace_id=_trace_id(request),
    )
    return SourceUploadCompleteResponse.model_validate(
        {**_fields(SourceUploadCompleteResponse, result), "run_id": run_id}
    )


@router.get("/spaces/{space_id}/sources", response_model=SourceListResponse)
async def list_sources(
    request: Request,
    space_id: UUID,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
    source_status: SourceStatusFilter = None,
    content_type: SourceTypeFilter = None,
    classification: ClassificationFilter = None,
    search: SearchFilter = None,
) -> SourceListResponse:
    repository = _repository(request)
    await repository.authorize_space(
        principal=principal,
        space_id=space_id,
        action="source.read",
        trace_id=_trace_id(request),
    )
    items = await repository.list_sources(principal=principal, space_id=space_id)
    visible = [
        item
        for item in items
        if _CLEARANCE[DataClassification(item["classification"])] <= _CLEARANCE[principal.clearance]
    ]
    if source_status:
        visible = [item for item in visible if item["status"] == source_status]
    if classification:
        visible = [item for item in visible if item["classification"] == classification.value]
    if search:
        needle = search.casefold()
        visible = [
            item
            for item in visible
            if needle in item["display_name"].casefold() or needle in item["description"].casefold()
        ]
    if content_type:
        visible = await _filter_sources_by_content_type(
            repository,
            principal=principal,
            items=visible,
            content_type=content_type,
        )
    return SourceListResponse.model_validate(_paginate(visible, limit, cursor))


@router.get("/sources/{source_id}", response_model=SourceDocumentResponse)
async def get_source(
    request: Request, source_id: UUID, principal: PrincipalDependency, response: Response
) -> SourceDocumentResponse:
    result = await _repository(request).get_source(principal=principal, source_id=source_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=result["space_id"],
        action="source.read",
        classification=result["classification"],
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return SourceDocumentResponse.model_validate(result)


@router.post("/sources/{source_id}/archive", response_model=SourceDocumentResponse)
async def archive_source(
    request: Request,
    source_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    response: Response,
) -> SourceDocumentResponse:
    current = await _repository(request).get_source(principal=principal, source_id=source_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=current["space_id"],
        action="source.archive",
        classification=current["classification"],
    )
    result = await _repository(request).archive_source(
        principal=principal,
        source_id=source_id,
        expected_version=_version_from_etag(if_match),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return SourceDocumentResponse.model_validate(result)


@router.get("/sources/{source_id}/versions/{version_id}", response_model=SourceVersionResponse)
async def get_source_version(
    request: Request,
    source_id: UUID,
    version_id: UUID,
    principal: PrincipalDependency,
    response: Response,
) -> SourceVersionResponse:
    result = await _repository(request).get_source_version(
        principal=principal, version_id=version_id
    )
    if UUID(result["source_document_id"]) != source_id:
        raise ApiProblem(
            404,
            "RESOURCE_NOT_FOUND",
            "Source version not found",
            "The SourceVersion is unavailable for this SourceDocument.",
        )
    await _authorize_resource(
        request,
        principal=principal,
        space_id=result["space_id"],
        action="source.read",
        classification=result["classification"],
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return SourceVersionResponse.model_validate(_fields(SourceVersionResponse, result))


@router.get("/source-versions/{version_id}/content")
async def download_source_version(
    request: Request, version_id: UUID, principal: PrincipalDependency
) -> BinaryResponse:
    repository = _repository(request)
    version = await repository.get_source_version(principal=principal, version_id=version_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=version["space_id"],
        action="source.download",
        classification=version["classification"],
    )
    if await repository.is_source_version_invalidated(principal=principal, version_id=version_id):
        raise ApiProblem(
            409,
            "SOURCE_VERSION_INVALIDATED",
            "Source version invalidated",
            "Invalidated Raw content is retained but cannot be downloaded.",
        )
    content = await _storage(request).get(
        key=version["object_key"], version_id=version["object_version_id"]
    )
    checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
    if checksum != version["checksum"]:
        raise ApiProblem(
            409,
            "SOURCE_CHECKSUM_MISMATCH",
            "Raw integrity check failed",
            "The server-read Raw no longer matches the registered immutable checksum.",
        )
    await repository.record_source_download(
        principal=principal, version=version, trace_id=_trace_id(request)
    )
    return BinaryResponse(
        content=content,
        media_type=version["content_type"],
        headers={
            "Content-Disposition": _download_content_disposition(version["filename"]),
            "X-Content-Checksum": checksum,
        },
    )


@router.post(
    "/source-versions/{version_id}/parse",
    response_model=ParseJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def reparse_source_version(
    request: Request,
    version_id: UUID,
    body: ReparseRequest,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    response: Response,
) -> ParseJobResponse:
    repository = _repository(request)
    version = await repository.get_source_version(principal=principal, version_id=version_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=version["space_id"],
        action="source.parse",
        classification=version["classification"],
    )
    result = await repository.create_reparse(
        principal=principal,
        version_id=version_id,
        expected_version=_version_from_etag(if_match),
        payload=body.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    run_id = await _start_parse_workflow(
        request,
        parse_job_id=UUID(result["id"]),
        workflow_id=result["workflow_id"],
        trace_id=_trace_id(request),
    )
    result["temporal_run_id"] = run_id
    response.headers["ETag"] = f'"v{result["version"]}"'
    return ParseJobResponse.model_validate(_fields(ParseJobResponse, result))


@router.post(
    "/parse-jobs/{parse_job_id}/retry",
    response_model=ParseJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def retry_parse_job(
    request: Request,
    parse_job_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    response: Response,
) -> ParseJobResponse:
    repository = _repository(request)
    current = await repository.get_parse_job(principal=principal, parse_job_id=parse_job_id)
    version = await repository.get_source_version(
        principal=principal, version_id=UUID(current["source_version_id"])
    )
    await _authorize_resource(
        request,
        principal=principal,
        space_id=version["space_id"],
        action="source.parse",
        classification=version["classification"],
    )
    result = await repository.prepare_parse_retry(
        principal=principal,
        parse_job_id=parse_job_id,
        expected_version=_version_from_etag(if_match),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    run_id = await _start_parse_workflow(
        request,
        parse_job_id=parse_job_id,
        workflow_id=result["workflow_id"],
        trace_id=_trace_id(request),
        retry=True,
    )
    result["temporal_run_id"] = run_id
    response.headers["ETag"] = f'"v{result["version"]}"'
    return ParseJobResponse.model_validate(_fields(ParseJobResponse, result))


@router.post(
    "/parse-jobs/{parse_job_id}/cancel",
    response_model=ParseJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def cancel_parse_job(
    request: Request,
    parse_job_id: UUID,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
    response: Response,
) -> ParseJobResponse:
    repository = _repository(request)
    current = await repository.get_parse_job(principal=principal, parse_job_id=parse_job_id)
    version = await repository.get_source_version(
        principal=principal, version_id=UUID(current["source_version_id"])
    )
    await _authorize_resource(
        request,
        principal=principal,
        space_id=version["space_id"],
        action="source.parse",
        classification=version["classification"],
    )
    result = await repository.cancel_parse_job(
        principal=principal,
        parse_job_id=parse_job_id,
        expected_version=_version_from_etag(if_match),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    await _workflow(request).cancel(workflow_id=result["workflow_id"])
    response.headers["ETag"] = f'"v{result["version"]}"'
    return ParseJobResponse.model_validate(_fields(ParseJobResponse, result))


@router.get("/parse-jobs/{parse_job_id}", response_model=ParseJobResponse)
async def get_parse_job(
    request: Request,
    parse_job_id: UUID,
    principal: PrincipalDependency,
    response: Response,
) -> ParseJobResponse:
    result = await _repository(request).get_parse_job(
        principal=principal, parse_job_id=parse_job_id
    )
    version = await _repository(request).get_source_version(
        principal=principal, version_id=UUID(result["source_version_id"])
    )
    await _authorize_resource(
        request,
        principal=principal,
        space_id=version["space_id"],
        action="source.read",
        classification=version["classification"],
    )
    response.headers["ETag"] = f'"v{result["version"]}"'
    return ParseJobResponse.model_validate(_fields(ParseJobResponse, result))


@router.get("/source-versions/{version_id}/segments", response_model=SegmentListResponse)
async def list_source_segments(
    request: Request,
    version_id: UUID,
    principal: PrincipalDependency,
    limit: PageLimit = 50,
    cursor: PageCursor = None,
    parse_job_id: ParseJobFilter = None,
) -> SegmentListResponse:
    repository = _repository(request)
    version = await repository.get_source_version(principal=principal, version_id=version_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=version["space_id"],
        action="source.read",
        classification=version["classification"],
    )
    if await repository.is_source_version_invalidated(principal=principal, version_id=version_id):
        raise ApiProblem(
            409,
            "SOURCE_VERSION_INVALIDATED",
            "Source version invalidated",
            "Invalidated derived content cannot be displayed.",
        )
    items = await repository.list_segments(
        principal=principal, version_id=version_id, parse_job_id=parse_job_id
    )
    return SegmentListResponse.model_validate(_paginate(items, limit, cursor))


@router.get("/source-versions/{version_id}/preview", response_model=PreviewResponse)
async def preview_source_version(
    request: Request,
    version_id: UUID,
    principal: PrincipalDependency,
    anchor_id: AnchorFilter = None,
) -> PreviewResponse:
    repository = _repository(request)
    version = await repository.get_source_version(principal=principal, version_id=version_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=version["space_id"],
        action="source.read",
        classification=version["classification"],
    )
    invalidated = await repository.is_source_version_invalidated(
        principal=principal, version_id=version_id
    )
    anchor = None
    if anchor_id:
        anchor = await repository.get_anchor(principal=principal, anchor_id=anchor_id)
        if UUID(anchor["source_version_id"]) != version_id:
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Anchor not found",
                "The Anchor is unavailable for this SourceVersion.",
            )
    if invalidated:
        selected_job_id = anchor["parse_job_id"] if anchor else version["active_parse_job_id"]
        if selected_job_id is None:
            raise ApiProblem(
                409,
                "STATE_TRANSITION_NOT_ALLOWED",
                "Preview unavailable",
                "The SourceVersion has no active parse result to revoke.",
            )
        return PreviewResponse(
            source_version_id=version_id,
            parse_job_id=UUID(str(selected_job_id)),
            anchor_id=anchor_id,
            anchor_status="REVOKED" if anchor_id else None,
            content_type="text/plain",
            sanitized_content="",
            locator_results=(),
        )
    selected_job = (
        UUID(anchor["parse_job_id"] if anchor else version["active_parse_job_id"])
        if (anchor or version["active_parse_job_id"])
        else None
    )
    if selected_job is None:
        raise ApiProblem(
            409,
            "STATE_TRANSITION_NOT_ALLOWED",
            "Preview unavailable",
            "The SourceVersion has no active usable parse result.",
        )
    segments = await repository.list_segments(
        principal=principal, version_id=version_id, parse_job_id=selected_job
    )
    sanitized = "\n\n".join(
        str(segment["normalized_text"]) for segment in segments if segment.get("normalized_text")
    )[:500_000]
    locator_results: tuple[PreviewLocatorResult, ...] = ()
    if anchor:
        segment_locators = [locator for segment in segments for locator in segment["locators"]]
        locator_results = tuple(
            PreviewLocatorResult(
                locator=locator,
                matched=locator in segment_locators,
                safe_detail="matched" if locator in segment_locators else "not found",
            )
            for locator in anchor["locators"]
        )
    return PreviewResponse(
        source_version_id=version_id,
        parse_job_id=selected_job,
        anchor_id=anchor_id,
        anchor_status=anchor["status"] if anchor else None,
        content_type="text/plain",
        sanitized_content=sanitized,
        locator_results=locator_results,
    )


@router.post(
    "/source-versions/{version_id}/invalidate",
    response_model=SourceInvalidationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invalidate_source_version(
    request: Request,
    version_id: UUID,
    body: SourceInvalidationCreate,
    principal: PrincipalDependency,
    idempotency_key: IdempotencyKey,
    if_match: IfMatch,
) -> SourceInvalidationResponse:
    repository = _repository(request)
    version = await repository.get_source_version(principal=principal, version_id=version_id)
    await _authorize_resource(
        request,
        principal=principal,
        space_id=version["space_id"],
        action="source.invalidate",
        classification=version["classification"],
    )
    result = await repository.invalidate_source_version(
        principal=principal,
        version_id=version_id,
        expected_version=_version_from_etag(if_match),
        payload=body.model_dump(mode="json"),
        idempotency_key=idempotency_key,
        trace_id=_trace_id(request),
    )
    return SourceInvalidationResponse.model_validate(result)
