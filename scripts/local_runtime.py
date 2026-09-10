"""Control the optional host forecast worker without disturbing Compose or other processes."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / ".nexweave-data"
LOCK = DATA / "m95-worker.lock"
STATUS = DATA / "m95-worker-status.json"
RUNNER = ROOT / "scripts/run_m95_worker.py"
PYTHON = DATA / "forecast-venv/bin/python"


def locked() -> bool:
    DATA.mkdir(exist_ok=True)
    with LOCK.open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(f, fcntl.LOCK_UN)
        return False


def status() -> dict:
    try:
        result = json.loads(STATUS.read_text())
    except (FileNotFoundError, ValueError):
        result = {}
    result["process_running"] = locked()
    result["ready"] = bool(
        result["process_running"]
        and result.get("ready")
        and time.time() - result.get("updated_at", 0) < 20
    )
    return result


def start() -> None:
    if locked():
        print(json.dumps(status()))
        return
    if not PYTHON.is_file() or not (DATA / "models/chronos-2/model.safetensors").is_file():
        print("Forecast worker unavailable: install the pinned optional runtime and model first.")
        return
    with (DATA / "m95-worker.log").open("ab") as log:
        subprocess.Popen(  # noqa: S603 - fixed workspace interpreter and runner
            [str(PYTHON), str(RUNNER)],
            cwd=ROOT,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    for _ in range(20):
        if locked():
            print(json.dumps(status()))
            return
        time.sleep(0.2)
    raise RuntimeError("Forecast worker did not start; inspect .nexweave-data/m95-worker.log")


def stop() -> None:
    if not locked():
        print("Forecast worker already stopped.")
        return
    pid = int(status().get("pid", 0))
    if pid <= 1:
        raise RuntimeError("Worker owner is unknown; refusing to signal an unverified process.")
    command = subprocess.run(  # noqa: S603 - numeric PID, no shell
        ["/bin/ps", "-p", str(pid), "-o", "command="],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    if command.split() != [str(PYTHON), str(RUNNER)]:
        raise RuntimeError("Worker PID does not match the managed command.")
    os.kill(pid, signal.SIGTERM)
    for _ in range(100):
        if not locked():
            print("Forecast worker stopped.")
            return
        time.sleep(0.2)
    raise RuntimeError("Worker is still draining; no force kill was sent.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["worker-start", "worker-stop", "status"])
    action = parser.parse_args().action
    if action == "worker-start":
        start()
    elif action == "worker-stop":
        stop()
    else:
        print(json.dumps(status()))


if __name__ == "__main__":
    main()
