"""Export the reviewed OpenAPI snapshot used by contract tests and SDK generation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from nexweave_api.app import create_app
from nexweave_api.settings import Settings


def render_openapi() -> dict[str, Any]:
    return create_app(Settings()).openapi()


def render_openapi_text() -> str:
    return json.dumps(render_openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    output = (
        Path(__file__).resolve().parents[4]
        / "packages/contracts/openapi/nexweave-platform-v1.openapi.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_openapi_text(), encoding="utf-8")
