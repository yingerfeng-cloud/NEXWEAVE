from __future__ import annotations

import asyncio

from temporalio.client import Client

from nexweave_api.settings import get_settings
from nexweave_domain import new_uuid7
from nexweave_worker_health.workflows import PlatformHealthWorkflow


async def verify() -> None:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_endpoint,
        namespace=settings.temporal_namespace,
    )
    result = await client.execute_workflow(
        PlatformHealthWorkflow.run,
        id=f"nexweave-m0-health-{new_uuid7()}",
        task_queue=settings.temporal_task_queue,
    )
    if result != {"status": "worker-ready", "milestone": "M0"}:
        raise RuntimeError(f"Unexpected health workflow result: {result!r}")
    print("Temporal worker health workflow passed")


if __name__ == "__main__":
    asyncio.run(verify())
