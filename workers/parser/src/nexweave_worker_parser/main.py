"""Isolated M3 parser and malware-scan Activity worker entry point."""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.worker import Worker

from nexweave_api.database import Database
from nexweave_api.object_storage import ClamAvInstreamMalwareScanner, S3ObjectStorage
from nexweave_api.settings import Settings
from nexweave_api.source_repository import SourceRepository
from nexweave_worker_parser.activities import SourceActivities
from nexweave_worker_parser.sandbox_client import SandboxParserClient

LOGGER = logging.getLogger("nexweave.worker.parser")


async def run() -> None:
    settings = Settings(otel_service_name="nexweave-worker-parser")
    logging.basicConfig(level=settings.log_level)
    client = await Client.connect(
        settings.temporal_endpoint,
        namespace=settings.temporal_namespace,
    )
    database = Database(settings)
    activities = SourceActivities(
        repository=SourceRepository(database),
        storage=S3ObjectStorage(settings),
        scanner=ClamAvInstreamMalwareScanner(settings),
        parser=SandboxParserClient(
            settings.parser_sandbox_host,
            settings.parser_sandbox_port,
        ),
    )
    worker = Worker(
        client,
        task_queue=settings.temporal_parser_activity_task_queue,
        activities=[
            activities.verify_raw,
            activities.scan_raw,
            activities.parse_and_persist,
            activities.fail,
        ],
        max_concurrent_activities=2,
    )
    LOGGER.info(
        "M3 parser Activity worker ready",
        extra={
            "namespace": settings.temporal_namespace,
            "activity_task_queue": settings.temporal_parser_activity_task_queue,
            "parser_provider": "nexweave.parser.builtin/1.0.0",
            "malware_scanner": "clamav",
        },
    )
    try:
        await worker.run()
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(run())
