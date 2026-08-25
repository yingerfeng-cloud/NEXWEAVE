from __future__ import annotations

import ast
import asyncio
from pathlib import Path

from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner

from nexweave_worker_kernel.workflows import WORKFLOW_CLASSES


def test_seven_versioned_workflow_definitions_are_registered() -> None:
    names = {workflow.__temporal_workflow_definition.name for workflow in WORKFLOW_CLASSES}

    assert names == {
        "nexweave.source-ingestion.v1",
        "nexweave.knowledge-compile.v1",
        "nexweave.human-review.v1",
        "nexweave.quality-evaluation.v1",
        "nexweave.knowledge-release.v1",
        "nexweave.domain-pack-install.v1",
        "nexweave.gridcrew-feedback-ingestion.v1",
    }


def test_workflow_sandbox_can_prepare_every_definition() -> None:
    async def prepare() -> None:
        runner = SandboxedWorkflowRunner()
        for workflow in WORKFLOW_CLASSES:
            runner.prepare_workflow(workflow.__temporal_workflow_definition)

    asyncio.run(prepare())


def test_workflow_module_contains_no_direct_io_imports() -> None:
    path = Path(__file__).resolve().parents[1] / "src/nexweave_worker_kernel/workflows.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports = {
        node.module.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }

    assert imports.isdisjoint(
        {"sqlalchemy", "asyncpg", "redis", "boto3", "httpx", "fastapi", "socket", "os"}
    )
