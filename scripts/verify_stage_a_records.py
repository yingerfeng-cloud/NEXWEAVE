"""Read-only audit of Stage A recovery records, immutable results and Temporal history."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path

from dotenv import dotenv_values
from run_m95_worker import host_url
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from temporalio.api.enums.v1 import EventType, TimeoutType
from temporalio.client import Client

ROOT = Path(__file__).resolve().parents[1]
for relative in (
    "apps/api/src",
    "packages/domain/src",
    "packages/contracts/src",
    "packages/application/src",
):
    sys.path.insert(0, str(ROOT / relative))


async def main() -> None:
    from nexweave_api.object_storage import S3ObjectStorage
    from nexweave_api.settings import Settings

    for key, value in dotenv_values(ROOT / ".env").items():
        if value is not None:
            os.environ.setdefault(key, value)
    for key in ("NEXWEAVE_DATABASE_URL", "NEXWEAVE_OBJECT_STORE_ENDPOINT"):
        os.environ[key] = host_url(os.environ[key])
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    settings = Settings()
    db = create_async_engine(settings.database_url)
    storage = S3ObjectStorage(settings)
    records = json.loads((ROOT / ".nexweave-data/stage-a-recovery.json").read_text())
    temporal = await Client.connect("127.0.0.1:7233", namespace=settings.temporal_namespace)
    checks = []
    try:
        async with db.connect() as c:
            for record in records:
                if "run_id" not in record:
                    continue
                run = (
                    (
                        await c.execute(
                            text("SELECT * FROM forecast_runs WHERE id=:id"),
                            {"id": record["run_id"]},
                        )
                    )
                    .mappings()
                    .one()
                )
                rid = record.get("retry_id", record["run_id"])
                artifacts = (
                    (
                        await c.execute(
                            text("SELECT * FROM forecast_artifacts WHERE run_id=:id"), {"id": rid}
                        )
                    )
                    .mappings()
                    .all()
                )
                assert len(artifacts) == 1
                artifact = artifacts[0]
                raw = await storage.get(key=artifact["object_key"])
                assert "sha256:" + hashlib.sha256(raw).hexdigest() == artifact["content_checksum"]
                item = {
                    "drill": record["drill"],
                    "run_id": run["id"],
                    "artifact_count": 1,
                    "checksum_matches": True,
                }
                if record["drill"] == "cancel":
                    assert run["status"] == "CANCELLED" and run["artifact_id"] is None
                    assert (
                        await c.scalar(
                            text("SELECT count(*) FROM forecast_artifacts WHERE run_id=:id"),
                            {"id": run["id"]},
                        )
                        == 0
                    )
                    retry = (
                        (
                            await c.execute(
                                text("SELECT * FROM forecast_runs WHERE id=:id"), {"id": rid}
                            )
                        )
                        .mappings()
                        .one()
                    )
                    assert run["context"] is not None and run["context"] == retry["context"]
                    assert (
                        run["request"] == retry["request"]
                        and run["model_revision"] == retry["model_revision"]
                    )
                    item["frozen_retry_equal"] = True
                if record["drill"] == "crash":
                    history = await temporal.get_workflow_handle(run["workflow_id"]).fetch_history()
                    # Temporal records intermediate retries on the eventual started event;
                    # a standalone timeout event is emitted only when attempts are exhausted.
                    starts = [
                        e.activity_task_started_event_attributes
                        for e in history.events
                        if e.event_type == EventType.EVENT_TYPE_ACTIVITY_TASK_STARTED
                    ]
                    recovered = [
                        a
                        for a in starts
                        if a.attempt >= 2
                        and a.last_failure.timeout_failure_info.timeout_type
                        == TimeoutType.TIMEOUT_TYPE_HEARTBEAT
                    ]
                    assert recovered, "No heartbeat retry in committed history"
                    item["recovered_attempt"] = recovered[0].attempt
                    item["previous_failure"] = "TIMEOUT_TYPE_HEARTBEAT"
                checks.append(item)
    finally:
        await db.dispose()
    output = ROOT / ".nexweave-data/stage-a-record-checks.json"
    output.write_text(json.dumps(checks, default=str, ensure_ascii=False, indent=2))
    print(output.name, "passed", len(checks))


if __name__ == "__main__":
    asyncio.run(main())
