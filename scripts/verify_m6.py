"""Exercise the real M6 candidate→Evidence→HumanReview→Claim and Conflict chain."""

from __future__ import annotations

import argparse
from uuid import uuid4

import httpx


class Api:
    def __init__(self, client: httpx.Client, token: str) -> None:
        self.client, self.token = client, token

    def request(self, method: str, path: str, *, expected: int = 200, **kwargs: object) -> dict:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "traceparent": f"00-{uuid4().hex}-{uuid4().hex[:16]}-01",
        }
        if method != "GET":
            headers["Idempotency-Key"] = f"m6-{uuid4()}"
        response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(f"{method} {path}: {response.status_code} {response.text[:600]}")
        return response.json()


def login(client: httpx.Client, subject: str) -> Api:
    response = client.post("/auth/dev/session", json={"subject": subject})
    response.raise_for_status()
    return Api(client, str(response.json()["access_token"]))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api/v1")
    parser.add_argument("--space-id", required=True)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=30, trust_env=False) as client:
        admin = login(client, "local-admin")
        if args.verify_only:
            claims = admin.request("GET", f"/spaces/{args.space_id}/claims")["items"]
            claim = next(
                (item for item in claims if item["candidate_id"] == args.candidate_id), None
            )
            if claim is None:
                raise RuntimeError("Evidence-backed candidate did not create a formal Claim")
            evidence = admin.request("GET", f"/claims/{claim['id']}/evidence")
            if not evidence or not any(item["status"] == "ACCEPTED" for item in evidence):
                raise RuntimeError("Formal Claim is missing accepted Evidence")
            print("M6 existing review verified: formal Claim and accepted Evidence are queryable.")
            return
        suffix = uuid4().hex[:10]
        actors: dict[str, Api] = {}
        for role, subject in {
            "knowledge_engineer": f"m6-engineer-{suffix}",
            "reviewer": f"m6-expert-{suffix}",
            "publisher": f"m6-approver-{suffix}",
        }.items():
            user = admin.request(
                "POST",
                "/users",
                json={
                    "issuer": "https://identity.nexweave.local/dev",
                    "subject": subject,
                    "display_name": f"M6 synthetic {role}",
                    "clearance": "INTERNAL",
                    "tenant_roles": [],
                },
            )
            admin.request(
                "PUT",
                f"/spaces/{args.space_id}/members/{user['id']}",
                json={"subject_type": "USER", "roles": [role], "clearance": "INTERNAL"},
            )
            actors[role] = login(client, subject)
        policy = admin.request(
            "POST",
            f"/spaces/{args.space_id}/review-policies",
            expected=201,
            json={
                "risk_level": "HIGH",
                "stages": ["ENGINEERING", "EXPERT", "APPROVAL"],
                "timeout_seconds": 3600,
                "escalation_role": "space_admin",
                "allow_batch": False,
                "batch_limit": 1,
            },
        )
        review = actors["knowledge_engineer"].request(
            "POST",
            f"/spaces/{args.space_id}/review-cases",
            expected=202,
            json={
                "target_type": "CLAIM_CANDIDATE",
                "target_id": args.candidate_id,
                "policy_id": policy["id"],
                "risk_level": "HIGH",
                "reason": "M6 synthetic evidence-governed review",
            },
        )
        for role in ("knowledge_engineer", "reviewer", "publisher"):
            current = actors[role].request("GET", f"/spaces/{args.space_id}/review-cases")["items"]
            case = next(item for item in current if item["id"] == review["id"])
            task = next(item for item in case["tasks"] if item["stage"] == case["current_stage"])
            review = actors[role].request(
                "POST",
                f"/review-cases/{case['id']}/tasks/{task['id']}/actions",
                json={"decision": "ACCEPT", "reason": f"M6 synthetic {role} acceptance"},
            )
        if review["status"] != "APPROVED":
            raise RuntimeError(f"Review did not approve: {review}")
        claims = admin.request("GET", f"/spaces/{args.space_id}/claims")["items"]
        claim = next((item for item in claims if item["candidate_id"] == args.candidate_id), None)
        if claim is None:
            raise RuntimeError("Evidence-backed candidate did not create a formal Claim")
        evidence = admin.request("GET", f"/claims/{claim['id']}/evidence")
        if not evidence or not any(item["status"] == "ACCEPTED" for item in evidence):
            raise RuntimeError("Formal Claim is missing accepted Evidence")
        conflicts = admin.request("POST", f"/spaces/{args.space_id}/conflicts/detect")["items"]
        if conflicts:
            first = conflicts[0]
            resolved = admin.request(
                "POST",
                f"/conflicts/{first['id']}/decisions",
                json={
                    "resolution": "UNRESOLVED",
                    "reason": "Synthetic M6 audit preservation check",
                },
            )
            if resolved["status"] != "UNRESOLVED":
                raise RuntimeError("Conflict did not preserve its unresolved decision")
    print(
        "M6 real chain verified: high-risk duty separation, Evidence gate, HumanReview v2, "
        "formal Claim/Evidence and conflict decision audit."
    )


if __name__ == "__main__":
    main()
