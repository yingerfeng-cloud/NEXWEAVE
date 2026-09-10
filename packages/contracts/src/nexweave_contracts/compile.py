"""M5 Compile, Model Gateway trace and Wiki draft contracts."""

from datetime import datetime
from typing import Any, Literal

from pydantic import UUID7, Field, model_validator

from nexweave_contracts.base import ContractModel


class CompileJobCreate(ContractModel):
    schema_version_id: UUID7
    source_version_ids: tuple[UUID7, ...] = Field(min_length=1, max_length=100)
    prompt_version_id: UUID7
    model_profile_id: UUID7
    mode: Literal["FULL", "INCREMENTAL", "SOURCE_SCOPED", "RECOMPILE"] = "FULL"
    scope: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique_sources(self) -> "CompileJobCreate":
        if len(set(self.source_version_ids)) != len(self.source_version_ids):
            raise ValueError("source_version_ids must be unique")
        return self


class CompileSourceRef(ContractModel):
    source_version_id: UUID7
    source_checksum: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    parse_job_id: UUID7
    input_order: int = Field(ge=0)


class CompileStepResponse(ContractModel):
    id: UUID7
    step_key: str
    input_checksum: str
    status: str
    attempt: int
    output_summary: dict[str, Any]
    error_code: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class CompileJobResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    schema_version_id: UUID7
    composition_checksum: str
    prompt_version_id: UUID7
    model_profile_id: UUID7
    workflow_task_id: UUID7
    workflow_id: str
    run_id: str | None = None
    mode: str
    status: str
    input_fingerprint: str
    normalization_version: str
    scope: dict[str, Any]
    progress: int
    cost_summary: dict[str, Any]
    result_summary: dict[str, Any]
    error_code: str | None = None
    error_detail: str | None = None
    version: int
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7
    sources: tuple[CompileSourceRef, ...] = ()
    steps: tuple[CompileStepResponse, ...] = ()


class CompileJobListResponse(ContractModel):
    items: tuple[CompileJobResponse, ...]


class ModelInvocationResponse(ContractModel):
    id: UUID7
    compile_job_id: UUID7
    compile_step_id: UUID7 | None = None
    model_profile_id: UUID7
    prompt_version_id: UUID7
    capability: str
    status: str
    input_checksum: str
    output_checksum: str | None = None
    input_units: int
    output_units: int
    latency_ms: int
    estimated_cost_microunits: int
    error_code: str | None = None
    created_at: datetime


class KnowledgeEntityResponse(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    schema_version_id: UUID7
    type_key: str
    normalized_key: str
    display_name: str
    status: str
    current_version_id: UUID7 | None = None
    version: int
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class KnowledgeEntityListResponse(ContractModel):
    items: tuple[KnowledgeEntityResponse, ...]


class WikiPageSummary(ContractModel):
    id: UUID7
    tenant_id: UUID7
    space_id: UUID7
    schema_version_id: UUID7
    primary_entity_id: UUID7
    template_key: str
    slug: str
    title: str
    status: str
    current_version_id: UUID7 | None = None
    version: int
    created_at: datetime
    created_by: UUID7
    updated_at: datetime
    updated_by: UUID7


class WikiPageVersionResponse(ContractModel):
    id: UUID7
    wiki_page_id: UUID7
    compile_job_id: UUID7 | None = None
    revision: int
    generated_sections: dict[str, str]
    protected_sections: dict[str, str]
    properties: dict[str, Any]
    markdown: str
    content_checksum: str
    status: str
    edit_reason: str | None = None
    created_at: datetime
    created_by: UUID7


class WikiPageVersionListResponse(ContractModel):
    items: tuple[WikiPageVersionResponse, ...]


class WikiPageResponse(WikiPageSummary):
    current_version: WikiPageVersionResponse | None = None
    outbound_links: tuple[dict[str, Any], ...] = ()
    backlinks: tuple[dict[str, Any], ...] = ()
    comments: tuple[dict[str, Any], ...] = ()
    evidence_candidates: tuple[dict[str, Any], ...] = ()
    followed: bool = False


class WikiPageListResponse(ContractModel):
    items: tuple[WikiPageSummary, ...]


class WikiLinkGraphNode(ContractModel):
    id: UUID7
    title: str
    template_key: str
    status: str
    version: int
    updated_at: datetime
    outbound_count: int = Field(ge=0)
    backlink_count: int = Field(ge=0)


class WikiLinkGraphEdge(ContractModel):
    id: UUID7
    source_page_id: UUID7
    target_page_id: UUID7
    link_kind: str


class WikiLinkGraphResponse(ContractModel):
    space_id: UUID7
    focus_page_id: UUID7 | None = None
    max_depth: int = Field(ge=1, le=3)
    node_limit: int = Field(ge=10, le=500)
    truncated: bool = False
    nodes: tuple[WikiLinkGraphNode, ...] = ()
    edges: tuple[WikiLinkGraphEdge, ...] = ()


class WikiPageEdit(ContractModel):
    protected_sections: dict[str, str] = Field(default_factory=dict)
    properties: dict[str, Any] = Field(default_factory=dict)
    title: str | None = Field(default=None, min_length=1, max_length=512)
    reason: str = Field(min_length=1, max_length=1024)


class WikiDiffResponse(ContractModel):
    page_id: UUID7
    from_version_id: UUID7
    to_version_id: UUID7
    markdown_diff: str
    generated_changed: tuple[str, ...]
    protected_changed: tuple[str, ...]
    properties_changed: tuple[str, ...]


class WikiCommentCreate(ContractModel):
    body: str = Field(min_length=1, max_length=5000)


class WikiCommentResponse(ContractModel):
    id: UUID7
    wiki_page_id: UUID7
    body: str
    status: str
    created_at: datetime
    created_by: UUID7


class CompileCompletedEventData(ContractModel):
    compile_job_id: UUID7
    schema_version_id: UUID7
    composition_checksum: str
    prompt_version_id: UUID7
    model_profile_id: UUID7
    source_version_ids: tuple[UUID7, ...]
    output_versions: dict[str, tuple[UUID7, ...]]
    stats: dict[str, int]
