"""Real Stage A recovery drills against local synthetic P-101. Restores stopped services."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from verify_m5 import _login

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".nexweave-data/stage-a-recovery.json"


def command(*args: str) -> None:
    subprocess.run(args, cwd=ROOT, check=True, stdout=subprocess.DEVNULL)  # noqa: S603


def worker(action: str) -> None:
    command(sys.executable, str(ROOT / "scripts/local_runtime.py"), action)


def wait(api, path, predicate, timeout=90):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        value = api.request("GET", path).json()
        if predicate(value):
            return value
        time.sleep(0.2)
    raise RuntimeError(f"Timed out: {path}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("drill", choices=["delivery", "crash", "cancel", "guards"])
    drill = parser.parse_args().drill
    state = json.loads((ROOT / ".nexweave-data/m95-e2e.json").read_text())
    sid = state["space_id"]
    path = f"/spaces/{sid}/forecast-runs"
    with httpx.Client(
        base_url="http://127.0.0.1:8080/api/v1", timeout=30, trust_env=False
    ) as client:
        api = _login(client, "local-admin")
        template = api.request("GET", f"/forecast-runs/{state['runs'][0]['run_id']}").json()[
            "request"
        ]
        template["scenario_name"] = f"Stage A synthetic {drill} {uuid4().hex[:6]}"
        result = {"drill": drill, "data_kind": "SYNTHETIC"}

        def create():
            key = str(uuid4())
            r = api.request("POST", path, expected=202, idempotency_key=key, json=template).json()
            replay = api.request(
                "POST", path, expected=202, idempotency_key=key, json=template
            ).json()
            assert replay["id"] == r["id"]
            result["run_id"] = r["id"]
            return r

        if drill == "delivery":
            try:
                command("docker", "compose", "stop", "temporal")
                run = create()
                observed = wait(
                    api,
                    f"/forecast-runs/{run['id']}",
                    lambda r: r["delivery_status"] == "RETRYING",
                    45,
                )
                assert observed["status"] == "QUEUED" and observed["artifact_id"] is None
                result["outage_status"] = observed
            finally:
                command("docker", "compose", "up", "--detach", "--wait", "temporal")
            final = wait(
                api, f"/forecast-runs/{run['id']}", lambda r: r["status"] in {"SUCCEEDED", "FAILED"}
            )
            assert final["status"] == "SUCCEEDED", final
            result["artifact_id"] = final["artifact_id"]
        elif drill in {"crash", "cancel"}:
            worker("worker-stop")
            try:
                run = create()
                # Cold worker opens a reproducible window before loading the model.
                worker("worker-start")
                wait(api, f"/forecast-runs/{run['id']}", lambda r: r["status"] == "RUNNING", 40)
                if drill == "crash":
                    pid = int((ROOT / ".nexweave-data/m95-worker.pid").read_text())
                    cmd = subprocess.run(  # noqa: S603 - verified numeric PID
                        ["/bin/ps", "-p", str(pid), "-o", "command="],
                        capture_output=True,
                        text=True,
                        check=True,
                    ).stdout.strip()  # noqa: S603
                    assert cmd.split() == [
                        str(ROOT / ".nexweave-data/forecast-venv/bin/python"),
                        str(ROOT / "scripts/run_m95_worker.py"),
                    ]
                    os.kill(pid, signal.SIGKILL)
                    result["killed_own_worker_pid"] = pid
                    time.sleep(1)
                    worker("worker-start")
                    final = wait(
                        api,
                        f"/forecast-runs/{run['id']}",
                        lambda r: r["status"] in {"SUCCEEDED", "FAILED"},
                    )
                    assert final["status"] == "SUCCEEDED", final
                    result["artifact_id"] = final["artifact_id"]
                else:
                    cancelled = api.request(
                        "POST",
                        f"/forecast-runs/{run['id']}/cancel",
                        idempotency_key=str(uuid4()),
                        json={"reason": "Synthetic Stage A cancellation drill"},
                    ).json()
                    assert cancelled["status"] == "CANCELLED" and cancelled["artifact_id"] is None
                    time.sleep(8)
                    final = api.request("GET", f"/forecast-runs/{run['id']}").json()
                    assert final["status"] == "CANCELLED" and final["artifact_id"] is None
                    key = str(uuid4())
                    body = {"reason": "Synthetic Stage A frozen-input retry"}
                    retry = api.request(
                        "POST",
                        f"/forecast-runs/{run['id']}/retry",
                        expected=202,
                        idempotency_key=key,
                        json=body,
                    ).json()
                    replay = api.request(
                        "POST",
                        f"/forecast-runs/{run['id']}/retry",
                        expected=202,
                        idempotency_key=key,
                        json=body,
                    ).json()
                    assert (
                        retry["id"] == replay["id"]
                        and retry["retry_of"] == run["id"]
                        and retry["id"] != run["id"]
                    )
                    final = wait(
                        api,
                        f"/forecast-runs/{retry['id']}",
                        lambda r: r["status"] in {"SUCCEEDED", "FAILED"},
                    )
                    assert final["status"] == "SUCCEEDED", final
                    result.update({"retry_id": retry["id"], "artifact_id": final["artifact_id"]})
            finally:
                worker("worker-start")
        else:
            subject = f"stage-a-outsider-{uuid4().hex[:8]}"
            api.request(
                "POST",
                "/users",
                idempotency_key=str(uuid4()),
                json={
                    "issuer": "https://identity.nexweave.local/dev",
                    "subject": subject,
                    "display_name": "Stage A synthetic outsider",
                    "clearance": "INTERNAL",
                    "tenant_roles": [],
                },
            )
            outsider = _login(client, subject)
            run_id = state["runs"][0]["run_id"]
            for action in ("cancel", "retry"):
                outsider.request(
                    "POST",
                    f"/forecast-runs/{run_id}/{action}",
                    expected=403,
                    idempotency_key=str(uuid4()),
                    json={"reason": "Unauthorized synthetic test"},
                )
            outsider.request("GET", f"/spaces/{sid}/forecast-runtime", expected=403)
            result["permission_denials"] = 3
            worker("worker-stop")
            try:
                queued = api.request(
                    "POST", path, expected=202, idempotency_key=str(uuid4()), json=template
                ).json()
                offline = wait(
                    api,
                    f"/spaces/{sid}/forecast-runtime",
                    lambda r: r["worker_status"] == "UNAVAILABLE",
                    30,
                )
                assert offline["queued"] >= 1
                cancelled = api.request(
                    "POST",
                    f"/forecast-runs/{queued['id']}/cancel",
                    idempotency_key=str(uuid4()),
                    json={"reason": "Synthetic queued cancellation"},
                ).json()
                assert cancelled["status"] == "CANCELLED"
                result["queued_cancel_id"] = queued["id"]
            finally:
                worker("worker-start")
            template["future_paths"] = []
            bad = api.request(
                "POST", path, expected=202, idempotency_key=str(uuid4()), json=template
            ).json()
            failed = wait(api, f"/forecast-runs/{bad['id']}", lambda r: r["status"] == "FAILED")
            assert (
                failed["error_code"] == "FUTURE_COVARIATE_INCOMPLETE"
                and failed["artifact_id"] is None
            )
            retry = api.request(
                "POST",
                f"/forecast-runs/{bad['id']}/retry",
                expected=202,
                idempotency_key=str(uuid4()),
                json={"reason": "Synthetic failed-input preservation"},
            ).json()
            retried = wait(api, f"/forecast-runs/{retry['id']}", lambda r: r["status"] == "FAILED")
            assert retried["retry_of"] == bad["id"] and retried["request"] == failed["request"]
            assert retried["error_code"] == failed["error_code"] and retried["artifact_id"] is None
            result["failed_retry_ids"] = [bad["id"], retry["id"]]
            final = api.request("GET", f"/forecast-runs/{queued['id']}").json()
            assert final["status"] == "CANCELLED" and final["artifact_id"] is None
        result["completed_at"] = datetime.now(UTC).isoformat()
        results = json.loads(OUTPUT.read_text()) if OUTPUT.exists() else []
        results.append(result)
        OUTPUT.write_text(json.dumps(results, ensure_ascii=False, indent=2))
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
