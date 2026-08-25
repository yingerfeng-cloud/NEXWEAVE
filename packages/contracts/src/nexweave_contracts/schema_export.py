"""Generate committed JSON Schemas from canonical contract models."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from nexweave_contracts import (
    ConnectorDefinitionResponse,
    EventEnvelope,
    KnowledgeSpaceResponse,
    ManagedObjectResponse,
    MembershipChangedEventData,
    ModelProfileResponse,
    PlatformEntityChangedEventData,
    ProblemDetails,
    PromptVersionResponse,
    ResourceMetadata,
    SourceAnchor,
    SpaceChangedEventData,
    WorkflowTaskEventData,
    WorkflowTaskResponse,
)

SCHEMAS: dict[str, type[BaseModel]] = {
    "event-envelope.schema.json": EventEnvelope,
    "membership-changed-event-data.schema.json": MembershipChangedEventData,
    "platform-entity-changed-event-data.schema.json": PlatformEntityChangedEventData,
    "space-changed-event-data.schema.json": SpaceChangedEventData,
    "problem.schema.json": ProblemDetails,
    "resource-metadata.schema.json": ResourceMetadata,
    "source-anchor.schema.json": SourceAnchor,
    "knowledge-space.schema.json": KnowledgeSpaceResponse,
    "managed-object.schema.json": ManagedObjectResponse,
    "model-profile.schema.json": ModelProfileResponse,
    "prompt-version.schema.json": PromptVersionResponse,
    "connector-definition.schema.json": ConnectorDefinitionResponse,
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
