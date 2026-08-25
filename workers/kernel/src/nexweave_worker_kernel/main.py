"""M2 Temporal workflow/activity worker entry point."""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from nexweave_api.database import Database
from nexweave_api.settings import Settings
from nexweave_api.workflow_repository import WorkflowRepository
from nexweave_worker_kernel.activities import KernelActivities
from nexweave_worker_kernel.workflows import WORKFLOW_CLASSES

LOGGER = logging.getLogger("nexweave.worker.kernel")


async def run() -> None:
    settings = Settings(otel_service_name="nexweave-worker-kernel")
    logging.basicConfig(level=settings.log_level)
    client = await Client.connect(
        settings.temporal_endpoint,
        namespace=settings.temporal_namespace,
    )
    database = Database(settings)
    activities = KernelActivities(WorkflowRepository(database))
    workflow_worker = Worker(
        client,
        task_queue=settings.temporal_workflow_task_queue,
        workflows=WORKFLOW_CLASSES,
    )
    activity_worker = Worker(
        client,
        task_queue=settings.temporal_activity_task_queue,
        activities=[
            activities.record_projection_transition,
            activities.execute_kernel_step,
            activities.compensate_kernel_step,
        ],
    )
    LOGGER.info(
        "M2 kernel workers ready",
        extra={
            "namespace": settings.temporal_namespace,
            "workflow_task_queue": settings.temporal_workflow_task_queue,
            "activity_task_queue": settings.temporal_activity_task_queue,
        },
    )
    try:
        await asyncio.gather(workflow_worker.run(), activity_worker.run())
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(run())
