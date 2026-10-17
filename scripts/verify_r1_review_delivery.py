"""Real HTTP/Temporal outage drill; synthetic technical roles, never Web acceptance.

Run prepare with Temporal available, queue-start with it stopped, verify-start
after recovery, queue-decision with it stopped again, then verify-decision after
recovery. The operator controls only the isolated Compose Temporal service.
"""

import argparse
import json
import time
from pathlib import Path
from uuid import uuid4

import httpx
from verify_m5 import _compile, _create_source, _login
from verify_m6 import login


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "phase",
        choices=["prepare", "queue-start", "verify-start", "queue-decision", "verify-decision"],
    )
    parser.add_argument("--source-state", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    args = parser.parse_args()
    with httpx.Client(
        base_url="http://127.0.0.1:8080/api/v1", timeout=30, trust_env=False
    ) as client:
        admin = login(client, "local-admin")
        if args.phase == "prepare":
            original = json.loads(args.source_state.read_text())
            sid, suffix = original["space_id"], uuid4().hex[:10]
            sdk = _login(client, "local-admin")
            job = admin.request("GET", f"/compile-jobs/{original['compile_job_id']}")
            source_id = _create_source(sdk, sid, suffix)
            before = {
                e["claim_candidate_id"]
                for p in admin.request("GET", f"/spaces/{sid}/wiki/pages")["items"]
                for e in admin.request("GET", f"/wiki/pages/{p['id']}")["evidence_candidates"]
                if e["claim_candidate_id"]
            }
            _compile(
                sdk,
                space_id=sid,
                schema_id=job["schema_version_id"],
                source_id=source_id,
                prompt_id=job["prompt_version_id"],
                profile_id=job["model_profile_id"],
                suffix=suffix,
                mode="FULL",
            )
            after = {
                e["claim_candidate_id"]
                for p in admin.request("GET", f"/spaces/{sid}/wiki/pages")["items"]
                for e in admin.request("GET", f"/wiki/pages/{p['id']}")["evidence_candidates"]
                if e["claim_candidate_id"]
            }
            target = sorted(after - before)[0]
            subjects = {}
            for role in ("knowledge_engineer", "reviewer", "publisher"):
                subject = f"review-outage-{role}-{suffix}"
                user = admin.request(
                    "POST",
                    "/users",
                    json={
                        "issuer": "https://identity.nexweave.local/dev",
                        "subject": subject,
                        "display_name": "Synthetic outage role",
                        "clearance": "INTERNAL",
                        "tenant_roles": [],
                    },
                )
                admin.request(
                    "PUT",
                    f"/spaces/{sid}/members/{user['id']}",
                    json={"subject_type": "USER", "roles": [role], "clearance": "INTERNAL"},
                )
                subjects[role] = subject
            policy = admin.request(
                "POST",
                f"/spaces/{sid}/review-policies",
                expected=201,
                json={
                    "risk_level": "HIGH",
                    "stages": ["ENGINEERING", "EXPERT", "APPROVAL"],
                    "timeout_seconds": 3600,
                },
            )
            state = {
                "space_id": sid,
                "target_id": target,
                "policy_id": policy["id"],
                "subjects": subjects,
                "evidence_kind": "REAL_HTTP_TEMPORAL_SYNTHETIC_ROLES",
                "completed_phases": ["prepare"],
            }
        else:
            state = json.loads(args.state.read_text())
            sid = state["space_id"]
            actors = {role: login(client, subject) for role, subject in state["subjects"].items()}
            if args.phase == "queue-start":
                case = actors["knowledge_engineer"].request(
                    "POST",
                    f"/spaces/{sid}/review-cases",
                    expected=202,
                    json={
                        "target_type": "CLAIM_CANDIDATE",
                        "target_id": state["target_id"],
                        "policy_id": state["policy_id"],
                        "risk_level": "HIGH",
                        "reason": "Synthetic real Temporal outage drill",
                    },
                )
                assert case["workflow_delivery_status"] == "PENDING"
                state["case_id"], state["workflow_task_id"] = case["id"], case["workflow_task_id"]
            elif args.phase in {"verify-start", "verify-decision"}:
                deadline = time.monotonic() + 45
                while True:
                    case = next(
                        c
                        for c in admin.request("GET", f"/spaces/{sid}/review-cases")["items"]
                        if c["id"] == state["case_id"]
                    )
                    task = admin.request("GET", f"/workflow-tasks/{state['workflow_task_id']}")[
                        "task"
                    ]
                    final = args.phase == "verify-decision"
                    if case["workflow_delivery_status"] == "DELIVERED" and (
                        task["status"] == "SUCCEEDED"
                        if final
                        else task["status"] == "WAITING"
                        and task.get("current_step") == "wait-for-audited-final-decision"
                    ):
                        break
                    if time.monotonic() > deadline:
                        raise RuntimeError(
                            "Review delivery did not recover to the expected Temporal state"
                        )
                    time.sleep(1)
                if not final:
                    for role in ("knowledge_engineer", "reviewer"):
                        active = next(
                            t for t in case["tasks"] if t["stage"] == case["current_stage"]
                        )
                        case = actors[role].request(
                            "POST",
                            f"/review-cases/{case['id']}/tasks/{active['id']}/actions",
                            json={
                                "decision": "ACCEPT",
                                "reason": "Synthetic technical examination of source support",
                            },
                        )
                state["last_workflow_status"] = task["status"]
            else:
                case = next(
                    c
                    for c in admin.request("GET", f"/spaces/{sid}/review-cases")["items"]
                    if c["id"] == state["case_id"]
                )
                active = next(t for t in case["tasks"] if t["stage"] == "APPROVAL")
                case = actors["publisher"].request(
                    "POST",
                    f"/review-cases/{case['id']}/tasks/{active['id']}/actions",
                    json={
                        "decision": "ACCEPT",
                        "reason": "Independent synthetic technical approval during outage",
                    },
                )
                assert (
                    case["status"] == "APPROVED" and case["workflow_delivery_status"] == "PENDING"
                )
            state["completed_phases"].append(args.phase)
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps(state, indent=2) + "\n")
        print(
            f"Real HTTP/Temporal review delivery: {args.phase} passed; synthetic technical roles."
        )


if __name__ == "__main__":
    main()
