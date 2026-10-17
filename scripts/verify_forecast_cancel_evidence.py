"""Read separate DB, S3, Temporal and frozen-input facts for a synthetic cancel drill."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID

from run_m95_worker import host_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from temporalio.api.enums.v1 import EventType
from temporalio.client import Client

from nexweave_api.object_storage import S3ObjectStorage
from nexweave_api.settings import Settings


async def main(state: Path, output: Path) -> None:
    record = json.loads(state.read_text())[-1]
    assert record["drill"] == "cancel" and record["data_kind"] == "SYNTHETIC"
    settings = Settings()
    if any(
        urlsplit(host_url(u)).hostname not in {"127.0.0.1", "localhost"}
        for u in (settings.database_url, settings.object_store_endpoint)
    ):
        raise ValueError("This synthetic diagnostic is loopback-only")
    engine = create_async_engine(host_url(settings.database_url))
    try:
        async with engine.connect() as c:
            await c.execute(text("SET TRANSACTION READ ONLY"))
            rows = (
                (
                    await c.execute(
                        text("SELECT * FROM forecast_runs WHERE id=ANY(:ids)"),
                        {"ids": [UUID(record["run_id"]), UUID(record["retry_id"])]},
                    )
                )
                .mappings()
                .all()
            )
            by_id = {str(r["id"]): r for r in rows}
            cancelled, retry = by_id[record["run_id"]], by_id[record["retry_id"]]
            artifact_count = await c.scalar(
                text("SELECT count(*) FROM forecast_artifacts WHERE run_id=:id"),
                {"id": cancelled["id"]},
            )
        assert cancelled["context"]["data_kind"] == "SYNTHETIC"
        assert cancelled["status"] == "CANCELLED" and cancelled["artifact_id"] is None
        assert artifact_count == 0 and retry["status"] == "SUCCEEDED"
        assert cancelled["context"] == retry["context"]
        assert cancelled["request"] == retry["request"]
        assert cancelled["model_revision"] == retry["model_revision"]
        storage = S3ObjectStorage(
            settings.model_copy(
                update={"object_store_endpoint": host_url(settings.object_store_endpoint)}
            )
        )
        prefix = (
            f"tenants/{cancelled['tenant_id']}/spaces/{cancelled['space_id']}/"
            f"forecasts/{cancelled['id']}/"
        )
        objects = await asyncio.to_thread(
            storage._client.list_object_versions, Bucket=storage._bucket, Prefix=prefix
        )
        assert not objects.get("Versions") and not objects.get("DeleteMarkers")
        temporal = await Client.connect("127.0.0.1:7233", namespace=settings.temporal_namespace)
        handle = temporal.get_workflow_handle(cancelled["workflow_id"])
        description, history = await asyncio.gather(handle.describe(), handle.fetch_history())
        cancellation_events = [
            EventType.Name(e.event_type)
            for e in history.events
            if "CANCEL" in EventType.Name(e.event_type)
        ]
        acknowledged = (
            description.status.name == "CANCELED"
            and "EVENT_TYPE_WORKFLOW_EXECUTION_CANCELED" in cancellation_events
        )
        result = {
            "scope": "REAL_HTTP_DRILL_READ_ONLY_DB_S3_TEMPORAL_SYNTHETIC",
            "run_id": record["run_id"],
            "retry_id": record["retry_id"],
            "database": {"cancelled_status": cancelled["status"], "artifact_rows": artifact_count},
            "object_storage": {
                "versions": len(objects.get("Versions", [])),
                "delete_markers": len(objects.get("DeleteMarkers", [])),
            },
            "temporal": {
                "status": description.status.name,
                "events": cancellation_events,
                "cancellation_acknowledged": acknowledged,
                "activity_cancellation_ack_in_closed_history": "EVENT_TYPE_ACTIVITY_TASK_CANCELED"
                in cancellation_events,
            },
            "frozen_input": {
                "request_equal": True,
                "context_equal": True,
                "revision_equal": True,
                "context_sha256": hashlib.sha256(
                    json.dumps(cancelled["context"], sort_keys=True, separators=(",", ":")).encode()
                ).hexdigest(),
            },
            "numerical_model_ready_at_workflow_cancel": "NOT_OBSERVED_SEE_DIRECT_MODEL_TEST",
            "hard_crash_after_object_put": "NOT_TESTED",
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result))
        if not acknowledged:
            raise SystemExit("Temporal cancellation acknowledgement was not observed")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.state, args.output))
