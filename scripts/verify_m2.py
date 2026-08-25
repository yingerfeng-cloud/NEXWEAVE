"""Exercise the real M2 API, PostgreSQL projection and Temporal runtime."""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
from temporalio.client import Client
from temporalio.worker import Replayer

ROOT = Path(__file__).resolve().parents[1]
for source_root in (ROOT / "workers/kernel/src", ROOT / "packages/domain/src"):
    sys.path.insert(0, str(source_root))

from nexweave_worker_kernel.workflows import WORKFLOW_CLASSES  # noqa: E402

TERMINAL = {"SUCCEEDED", "FAILED", "TIMED_OUT", "CANCELLED", "REJECTED"}
APPROVAL_TYPES = {"HUMAN_REVIEW", "KNOWLEDGE_RELEASE", "DOMAIN_PACK_INSTALL"}
WORKFLOW_TYPES = [
    "SOURCE_INGESTION",
    "KNOWLEDGE_COMPILE",
    "HUMAN_REVIEW",
    "QUALITY_EVALUATION",
    "KNOWLEDGE_RELEASE",
    "DOMAIN_PACK_INSTALL",
    "GRIDCREW_FEEDBACK_INGESTION",
]


@dataclass
class Api:
    client: httpx.Client
    base_url: str
    headers: dict[str, str]
    space_id: str

    def create(
        self,
        workflow_type: str,
        business_key: str,
        *,
        start_paused: bool = False,
        idempotency_key: str | None = None,
        display_name: str | None = None,
    ) -> httpx.Response:
        return self.client.post(
            f"{self.base_url}/spaces/{self.space_id}/workflow-tasks",
            headers={
                **self.headers,
                "Idempotency-Key": idempotency_key or str(uuid4()),
            },
            json={
                "workflow_type": workflow_type,
                "business_key": business_key,
                "display_name": display_name or f"M2 verification {workflow_type}",
                "input_refs": {},
                "start_paused": start_paused,
            },
        )

    def detail(self, task_id: str) -> dict[str, Any]:
        response = self.client.get(
            f"{self.base_url}/workflow-tasks/{task_id}", headers=self.headers
        )
        response.raise_for_status()
        return dict(response.json())

    def wait_for(self, task_id: str, statuses: set[str], timeout: float = 30) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            detail = self.detail(task_id)
            if detail["task"]["status"] in statuses:
                return detail
            time.sleep(0.25)
        raise AssertionError(
            f"task {task_id} did not reach {sorted(statuses)}; last={self.detail(task_id)}"
        )

    def command(
        self,
        detail: dict[str, Any],
        action: str,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> httpx.Response:
        task = detail["task"]
        return self.client.post(
            f"{self.base_url}/workflow-tasks/{task['id']}/commands",
            headers={
                **self.headers,
                "Idempotency-Key": key or str(uuid4()),
                "If-Match": f'"v{version or task["version"]}"',
            },
            json={"action": action, "reason": f"M2 verification {action}"},
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api/v1")
    parser.add_argument("--skip-worker-restart", action="store_true")
    args = parser.parse_args()
    suffix = uuid4().hex[:12]
    with httpx.Client(timeout=45) as client:
        session = client.post(f"{args.base_url}/auth/dev/session", json={"subject": "local-admin"})
        session.raise_for_status()
        headers = {"Authorization": f"Bearer {session.json()['access_token']}"}
        spaces = client.get(f"{args.base_url}/spaces", headers=headers)
        spaces.raise_for_status()
        space_id = next(item["id"] for item in spaces.json()["items"] if item["status"] == "ACTIVE")
        api = Api(client, args.base_url, headers, space_id)

        completed: list[dict[str, Any]] = []
        for workflow_type in WORKFLOW_TYPES:
            response = api.create(workflow_type, f"verify-{suffix}-{workflow_type.lower()}")
            assert response.status_code == 202, response.text
            detail = api.wait_for(
                response.json()["id"],
                {"WAITING"} if workflow_type in APPROVAL_TYPES else {"SUCCEEDED"},
            )
            if workflow_type in APPROVAL_TYPES:
                approval = api.command(detail, "APPROVE")
                assert approval.status_code == 202, approval.text
                detail = api.wait_for(response.json()["id"], {"SUCCEEDED"})
            assert detail["task"]["result_summary"]["business_features_implemented"] is False
            completed.append(detail)

        retry_detail = next(
            detail for detail in completed if detail["task"]["workflow_type"] == "SOURCE_INGESTION"
        )
        assert [step["attempt"] for step in retry_detail["steps"]] == [1, 2, 1]

        duplicate_key = str(uuid4())
        duplicate_business_key = f"verify-{suffix}-duplicate"
        first = api.create(
            "SOURCE_INGESTION", duplicate_business_key, idempotency_key=duplicate_key
        )
        second = api.create(
            "SOURCE_INGESTION", duplicate_business_key, idempotency_key=duplicate_key
        )
        third = api.create("SOURCE_INGESTION", duplicate_business_key)
        assert first.status_code == second.status_code == third.status_code == 202
        assert first.json()["id"] == second.json()["id"] == third.json()["id"]
        conflict = api.create(
            "SOURCE_INGESTION",
            duplicate_business_key,
            display_name="Different request with same business key",
        )
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "BUSINESS_KEY_CONFLICT"

        paused = api.create("SOURCE_INGESTION", f"verify-{suffix}-paused", start_paused=True)
        paused_detail = api.wait_for(paused.json()["id"], {"PAUSED"})
        command_key = str(uuid4())
        original_version = paused_detail["task"]["version"]
        resume = api.command(paused_detail, "RESUME", key=command_key)
        repeated_resume = api.command(
            paused_detail, "RESUME", key=command_key, version=original_version
        )
        assert resume.status_code == repeated_resume.status_code == 202
        assert resume.json() == repeated_resume.json()
        api.wait_for(paused.json()["id"], {"SUCCEEDED"})

        cancellable = api.create("SOURCE_INGESTION", f"verify-{suffix}-cancel")
        cancel_detail = api.wait_for(cancellable.json()["id"], {"RUNNING"})
        while cancel_detail["task"]["progress"] < 33:
            time.sleep(0.1)
            cancel_detail = api.detail(cancellable.json()["id"])
        cancel = api.command(cancel_detail, "CANCEL")
        assert cancel.status_code == 202, cancel.text
        cancelled = api.wait_for(cancellable.json()["id"], {"CANCELLED"})
        assert any(step["status"] == "COMPENSATED" for step in cancelled["steps"])

        for workflow_type in WORKFLOW_TYPES:
            cancelled_response = api.create(
                workflow_type,
                f"verify-{suffix}-cancel-{workflow_type.lower()}",
                start_paused=True,
            )
            cancelled_detail = api.wait_for(cancelled_response.json()["id"], {"PAUSED"})
            cancel_response = api.command(cancelled_detail, "CANCEL")
            assert cancel_response.status_code == 202, cancel_response.text
            api.wait_for(cancelled_response.json()["id"], {"CANCELLED"})

        retry_response = api.create("SOURCE_INGESTION", f"verify-{suffix}-retry", start_paused=True)
        retry_paused = api.wait_for(retry_response.json()["id"], {"PAUSED"})
        asyncio.run(_terminate_workflow(retry_paused["task"]["workflow_id"]))
        retry_reconcile = client.post(
            f"{args.base_url}/workflow-tasks/{retry_paused['task']['id']}/reconcile",
            headers=headers,
        )
        assert retry_reconcile.status_code == 200, retry_reconcile.text
        assert retry_reconcile.json()["task"]["status"] == "FAILED"
        retry_failed = api.detail(retry_paused["task"]["id"])
        retry_command = api.command(retry_failed, "RETRY")
        assert retry_command.status_code == 202, retry_command.text
        retried_paused = api.wait_for(retry_paused["task"]["id"], {"PAUSED"})
        retry_resume = api.command(retried_paused, "RESUME")
        assert retry_resume.status_code == 202, retry_resume.text
        api.wait_for(retry_paused["task"]["id"], {"SUCCEEDED"})

        reconcile_target = completed[1]
        _corrupt_projection(reconcile_target["task"]["id"])
        reconcile = client.post(
            f"{args.base_url}/workflow-tasks/{reconcile_target['task']['id']}/reconcile",
            headers=headers,
        )
        assert reconcile.status_code == 200, reconcile.text
        assert reconcile.json()["repaired"] is True
        assert reconcile.json()["task"]["status"] == "SUCCEEDED"

        if not args.skip_worker_restart:
            _compose("stop", "worker-kernel")
            interrupted = api.create("QUALITY_EVALUATION", f"verify-{suffix}-worker-restart")
            assert interrupted.status_code == 202, interrupted.text
            time.sleep(1)
            assert api.detail(interrupted.json()["id"])["task"]["status"] == "STARTING"
            _compose("start", "worker-kernel")
            recovered = api.wait_for(interrupted.json()["id"], {"SUCCEEDED"}, timeout=45)
            assert recovered["task"]["status"] == "SUCCEEDED"

        _assert_security_evidence()
        asyncio.run(_replay_history(retry_detail["task"]["workflow_id"]))
        print(
            "M2 real verification passed: seven workflows, all-type cancellation, Update "
            "idempotency, Activity and failed-run retries, approval, pause/resume, "
            "compensation, reconciliation, worker restart and replay"
        )


def _compose(*arguments: str) -> None:
    subprocess.run(  # noqa: S603
        ["docker", "compose", *arguments],  # noqa: S607
        check=True,
        cwd=ROOT,  # noqa: S607
    )


def _corrupt_projection(task_id: str) -> None:
    task_id = str(UUID(task_id))
    subprocess.run(  # noqa: S603
        [  # noqa: S607
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "nexweave",
            "-d",
            "nexweave",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            (
                "UPDATE workflow_tasks SET status = 'PAUSED', projection_in_sync = false "  # noqa: S608 - validated UUID fault target
                f"WHERE id = '{task_id}'"
            ),
        ],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )


def _assert_security_evidence() -> None:
    counts = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "nexweave",
            "-d",
            "nexweave",
            "-At",
            "-c",
            (
                "SELECT (SELECT COUNT(*) FROM audit_logs WHERE action LIKE 'workflow.%'), "
                "(SELECT COUNT(*) FROM outbox_events WHERE event_type LIKE "
                "'io.nexweave.workflow.%')"
            ),
        ],
        check=True,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    audit_count, outbox_count = (int(value) for value in counts.stdout.strip().split("|"))
    assert audit_count > 0 and outbox_count > 0
    immutable = subprocess.run(  # noqa: S603
        [  # noqa: S607
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            "nexweave",
            "-d",
            "nexweave",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            (
                "UPDATE workflow_task_events SET message = message WHERE id = "
                "(SELECT id FROM workflow_task_events LIMIT 1)"
            ),
        ],
        check=False,
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert immutable.returncode != 0
    assert "append-only" in immutable.stderr


async def _replay_history(workflow_id: str) -> None:
    client = await Client.connect("127.0.0.1:7233", namespace="nexweave-dev")
    history = await client.get_workflow_handle(workflow_id).fetch_history()
    result = await Replayer(workflows=WORKFLOW_CLASSES).replay_workflow(history)
    assert result.replay_failure is None


async def _terminate_workflow(workflow_id: str) -> None:
    client = await Client.connect("127.0.0.1:7233", namespace="nexweave-dev")
    await client.get_workflow_handle(workflow_id).terminate("M2 retry-path verification")


if __name__ == "__main__":
    main()
