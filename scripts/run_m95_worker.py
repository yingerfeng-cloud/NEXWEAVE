"""Run one supervised optional forecast worker against local Compose infrastructure."""

from __future__ import annotations

import asyncio
import fcntl
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".nexweave-data"
for relative in (
    "apps/api/src",
    "packages/domain/src",
    "packages/contracts/src",
    "packages/application/src",
    "workers/kernel/src",
):
    sys.path.insert(0, str(ROOT / relative))


def host_url(value: str) -> str:
    p = urlsplit(value)
    if p.hostname not in {"postgres", "rustfs", "redis"}:
        return value
    credentials, separator, _ = p.netloc.rpartition("@")
    authority = (credentials + separator if separator else "") + "127.0.0.1"
    if p.port:
        authority += f":{p.port}"
    return urlunsplit((p.scheme, authority, p.path, p.query, p.fragment))


def write_status(ready: bool, error: str | None = None) -> None:
    from nexweave_contracts.runtime import IMPLEMENTATION_VERSION

    temp = DATA / "m95-worker-status.tmp"
    temp.write_text(
        json.dumps(
            {
                "pid": os.getpid(),
                "ready": ready,
                "updated_at": time.time(),
                "implementation_version": IMPLEMENTATION_VERSION,
                "error": error,
            }
        )
    )
    temp.replace(DATA / "m95-worker-status.json")


async def supervise() -> None:
    from nexweave_worker_kernel.forecast_main import main as run

    task = asyncio.current_task()
    assert task is not None
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, task.cancel)
    try:
        while True:
            try:
                await run(on_ready=lambda: write_status(True))
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                write_status(False, type(exc).__name__)
                logging.warning("Forecast worker reconnecting: %s", type(exc).__name__)
            await asyncio.sleep(5)
    finally:
        write_status(False)


def main() -> None:
    DATA.mkdir(exist_ok=True)
    with (DATA / "m95-worker.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Forecast worker is already running.")
            return
        (DATA / "m95-worker.pid").write_text(str(os.getpid()))
        write_status(False)
        for key, value in dotenv_values(ROOT / ".env").items():
            if value is not None:
                os.environ.setdefault(key, value)
        for key in (
            "NEXWEAVE_DATABASE_URL",
            "NEXWEAVE_OBJECT_STORE_ENDPOINT",
            "NEXWEAVE_REDIS_URL",
        ):
            if value := os.environ.get(key):
                os.environ[key] = host_url(value)
        os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ",localhost,127.0.0.1"
        os.environ["no_proxy"] = os.environ["NO_PROXY"]
        if os.environ.get("NEXWEAVE_TEMPORAL_ENDPOINT", "temporal:7233") == "temporal:7233":
            os.environ["NEXWEAVE_TEMPORAL_ENDPOINT"] = "127.0.0.1:7233"
        os.environ["NEXWEAVE_FORECAST_MODEL_PATH"] = str(DATA / "models/chronos-2")
        try:
            asyncio.run(supervise())
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    main()
