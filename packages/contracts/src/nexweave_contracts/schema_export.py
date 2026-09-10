"""Generate committed JSON Schemas from canonical contract models."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from nexweave_contracts import (
    ClaimResponse,
    CompileCompletedEventData,
    CompileJobResponse,
    CompositionReportResponse,
    ConflictResponse,
    ConnectorDefinitionResponse,
    ConnectorInstanceResponse,
    ConnectorSyncRunResponse,
    DomainPackInstallationResponse,
    DomainPackManifestV1Alpha1,
    DomainPackRevocationListV1Alpha1,
    EvaluationCompletedEventData,
    EventEnvelope,
    KnowledgeSpaceResponse,
    ManagedObjectResponse,
    MembershipChangedEventData,
    ModelProfileResponse,
    ObsidianImportResponse,
    PackInstalledEventData,
    ParseEventData,
    PlatformEntityChangedEventData,
    ProblemDetails,
    PromptVersionResponse,
    QueryAnswerResponse,
    ReleaseCandidateResponse,
    ReleaseDeprecatedEventData,
    ReleasePointerChangedEventData,
    ReleasePublishedEventData,
    ReleaseResponse,
    ResourceMetadata,
    ReviewCaseResponse,
    ReviewPolicyResponse,
    SchemaPublishedEventData,
    SchemaVersionResponse,
    SourceAnchor,
    SourceInvalidatedEventData,
    SourceVersionReadyEventData,
    SourceVersionSupersededEventData,
    SpaceChangedEventData,
    WikiLinkGraphResponse,
    WikiPageResponse,
    WorkflowTaskEventData,
    WorkflowTaskResponse,
)
from nexweave_contracts.forecast import (
    BindingCreate,
    BindingResponse,
    BindingValidation,
    CsvBindingPreview,
    ForecastArtifactResponse,
    ForecastCommand,
    ForecastCreate,
    ForecastEventData,
    ForecastKnowledgeContext,
    ForecastKnowledgeRequest,
    ForecastRunResponse,
    ForecastRuntime,
    TimeSeriesCapabilities,
)

SCHEMAS: dict[str, type[BaseModel]] = {
    "forecast-knowledge-context.schema.json": ForecastKnowledgeContext,
    "forecast-knowledge-request.schema.json": ForecastKnowledgeRequest,
    "signal-binding-create.schema.json": BindingCreate,
    "signal-binding.schema.json": BindingResponse,
    "binding-validation.schema.json": BindingValidation,
    "csv-binding-preview.schema.json": CsvBindingPreview,
    "forecast-create.schema.json": ForecastCreate,
    "forecast-command.schema.json": ForecastCommand,
    "forecast-runtime.schema.json": ForecastRuntime,
    "forecast-event-data.schema.json": ForecastEventData,
    "forecast-run.schema.json": ForecastRunResponse,
    "forecast-artifact.schema.json": ForecastArtifactResponse,
    "timeseries-capabilities.schema.json": TimeSeriesCapabilities,
    "event-envelope.schema.json": EventEnvelope,
    "membership-changed-event-data.schema.json": MembershipChangedEventData,
    "platform-entity-changed-event-data.schema.json": PlatformEntityChangedEventData,
    "space-changed-event-data.schema.json": SpaceChangedEventData,
    "problem.schema.json": ProblemDetails,
    "resource-metadata.schema.json": ResourceMetadata,
    "source-anchor.schema.json": SourceAnchor,
    "source-version-ready-event-data.schema.json": SourceVersionReadyEventData,
    "source-version-superseded-event-data.schema.json": SourceVersionSupersededEventData,
    "source-invalidated-event-data.schema.json": SourceInvalidatedEventData,
    "parse-event-data.schema.json": ParseEventData,
    "knowledge-space.schema.json": KnowledgeSpaceResponse,
    "managed-object.schema.json": ManagedObjectResponse,
    "model-profile.schema.json": ModelProfileResponse,
    "prompt-version.schema.json": PromptVersionResponse,
    "connector-definition.schema.json": ConnectorDefinitionResponse,
    "connector-instance.schema.json": ConnectorInstanceResponse,
    "connector-sync-run.schema.json": ConnectorSyncRunResponse,
    "domain-pack-manifest-v1alpha1.schema.json": DomainPackManifestV1Alpha1,
    "domain-pack-revocation-list-v1alpha1.schema.json": DomainPackRevocationListV1Alpha1,
    "schema-version.schema.json": SchemaVersionResponse,
    "schema-composition-report.schema.json": CompositionReportResponse,
    "domain-pack-installation.schema.json": DomainPackInstallationResponse,
    "pack-installed-event-data.schema.json": PackInstalledEventData,
    "schema-published-event-data.schema.json": SchemaPublishedEventData,
    "compile-job.schema.json": CompileJobResponse,
    "compile-completed-event-data.schema.json": CompileCompletedEventData,
    "claim.schema.json": ClaimResponse,
    "conflict.schema.json": ConflictResponse,
    "review-case.schema.json": ReviewCaseResponse,
    "review-policy.schema.json": ReviewPolicyResponse,
    "evaluation-completed-event-data.schema.json": EvaluationCompletedEventData,
    "release-candidate.schema.json": ReleaseCandidateResponse,
    "release.schema.json": ReleaseResponse,
    "release-published-event-data.schema.json": ReleasePublishedEventData,
    "release-pointer-changed-event-data.schema.json": ReleasePointerChangedEventData,
    "release-deprecated-event-data.schema.json": ReleaseDeprecatedEventData,
    "query-answer.schema.json": QueryAnswerResponse,
    "obsidian-import.schema.json": ObsidianImportResponse,
    "wiki-page.schema.json": WikiPageResponse,
    "wiki-link-graph.schema.json": WikiLinkGraphResponse,
    "workflow-task.schema.json": WorkflowTaskResponse,
    "workflow-task-event-data.schema.json": WorkflowTaskEventData,
}


def render_schemas() -> dict[str, str]:
    return {
        filename: json.dumps(
            model.model_json_schema(mode="serialization"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
        for filename, model in SCHEMAS.items()
    }


def write_schemas(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, content in render_schemas().items():
        (output_dir / filename).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    write_schemas(Path(__file__).resolve().parents[2] / "schemas")
