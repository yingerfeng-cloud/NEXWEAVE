"""Generate committed JSON Schemas from canonical contract models."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from nexweave_contracts import EventEnvelope, ProblemDetails, ResourceMetadata, SourceAnchor

SCHEMAS: dict[str, type[BaseModel]] = {
    "event-envelope.schema.json": EventEnvelope,
    "problem.schema.json": ProblemDetails,
    "resource-metadata.schema.json": ResourceMetadata,
    "source-anchor.schema.json": SourceAnchor,
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
