from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from nexweave_api.settings import get_settings
from nexweave_worker_health.workflows import PlatformHealthWorkflow


async def run_worker() -> None:
    settings = get_settings()
    client = await Client.connect(
        settings.temporal_endpoint,
        namespace=settings.temporal_namespace,
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[PlatformHealthWorkflow],
    )
    logging.getLogger(__name__).info(
        "M0 health worker started",
        extra={"task_queue": settings.temporal_task_queue},
    )
    await worker.run()


def main() -> None:
    logging.basicConfig(level=get_settings().log_level)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
