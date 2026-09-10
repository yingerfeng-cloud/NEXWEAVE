"""Exercise the real M7 quality gate, immutable Release, query and rollback chain."""

from __future__ import annotations

import argparse
import time
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx


class Api:
    def __init__(self, client: httpx.Client, token: str) -> None:
        self.client, self.token = client, token

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: int = 200,
        headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        request_headers = {
            "Authorization": f"Bearer {self.token}",
            "traceparent": f"00-{uuid4().hex}-{uuid4().hex[:16]}-01",
        }
        if method != "GET":
            request_headers["Idempotency-Key"] = f"m7-{uuid4()}"
        request_headers.update(headers or {})
        response = self.client.request(method, path, headers=request_headers, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(f"{method} {path}: {response.status_code} {response.text[:800]}")
        value = response.json()
        if not isinstance(value, dict):
            raise RuntimeError(f"{method} {path}: expected a JSON object")
        return value


def all_items(api: Api, path: str) -> list[dict[str, Any]]:
    items = []
    cursor = None
    while True:
        page = api.request(
            "GET", path, params={"limit": 100, **({"cursor": cursor} if cursor else {})}
        )
        items.extend(page["items"])
        cursor = page.get("next_cursor")
        if not cursor:
            return items


def login(client: httpx.Client, subject: str) -> Api:
    response = client.post("/auth/dev/session", json={"subject": subject})
    response.raise_for_status()
    return Api(client, str(response.json()["access_token"]))


def wait_candidate(api: Api, candidate_id: str, wanted: set[str]) -> dict[str, Any]:
    for _ in range(100):
        candidate = api.request("GET", f"/release-candidates/{candidate_id}")
        if candidate["status"] in wanted:
            return candidate
        if candidate["status"] in {"FAILED", "REJECTED", "CANCELLED"}:
            raise RuntimeError(f"Release candidate failed: {candidate}")
        time.sleep(0.2)
    raise RuntimeError("Timed out waiting for ReleaseCandidate")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api/v1")
    parser.add_argument("--space-id", required=True)
    parser.add_argument("--claim-id", required=True)
    args = parser.parse_args()
    with httpx.Client(base_url=args.base_url, timeout=30, trust_env=False) as client:
        admin = login(client, "local-admin")
        claims = admin.request("GET", f"/spaces/{args.space_id}/claims")["items"]
        claim = next(item for item in claims if item["id"] == args.claim_id)
        prompts = [
            item
            for item in all_items(admin, "/prompt-versions")
            if item.get("space_id") == args.space_id
        ]
        models = [
            item
            for item in all_items(admin, "/model-profiles")
            if item.get("space_id") == args.space_id
        ]
        if not prompts or not models:
            raise RuntimeError("The selected M6 space has no fixed PromptVersion or ModelProfile")

        suffix = uuid4().hex[:10]
        publisher_subject = f"m7-publisher-{suffix}"
        publisher_user = admin.request(
            "POST",
            "/users",
            json={
                "issuer": "https://identity.nexweave.local/dev",
                "subject": publisher_subject,
                "display_name": "M7 independent publisher",
                "clearance": "INTERNAL",
                "tenant_roles": [],
            },
        )
        admin.request(
            "PUT",
            f"/spaces/{args.space_id}/members/{publisher_user['id']}",
            json={"subject_type": "USER", "roles": ["publisher"], "clearance": "INTERNAL"},
        )
        publisher = login(client, publisher_subject)

        suite = admin.request(
            "POST",
            f"/spaces/{args.space_id}/evaluation-suites",
            expected=201,
            json={
                "schema_version_id": claim["schema_version_id"],
                "suite_key": f"m7/acceptance-{suffix}",
                "version": 1,
                "name": "M7 fixed Release acceptance suite",
                "minimum_pass_rate": 100,
                "cases": [
                    {
                        "case_key": "approved-claim",
                        "case_type": "ANSWERABLE",
                        "question": claim["statement"],
                        "expected_claim_ids": [claim["id"]],
                        "expected_terms": ["Pump A"],
                        "expect_refusal": False,
                    },
                    {
                        "case_key": "insufficient-evidence",
                        "case_type": "INSUFFICIENT_EVIDENCE",
                        "question": "What is the launch code for an unrelated satellite?",
                        "expected_claim_ids": [],
                        "expected_terms": [],
                        "expect_refusal": True,
                    },
                ],
            },
        )

        base_patch = int(datetime.now(UTC).timestamp())
        releases: list[dict[str, Any]] = []
        for patch in (base_patch, base_patch + 1):
            candidate = admin.request(
                "POST",
                f"/spaces/{args.space_id}/release-candidates",
                expected=202,
                json={
                    "version": f"7.0.{patch}",
                    "schema_version_id": claim["schema_version_id"],
                    "prompt_version_id": prompts[0]["id"],
                    "model_profile_id": models[0]["id"],
                    "evaluation_suite_id": suite["id"],
                    "claim_ids": [claim["id"]],
                    "relation_ids": [],
                    "wiki_page_version_ids": [],
                    "index_config": {"version": "m7-r1", "fusion": "rrf", "vector_dimensions": 16},
                    "notes": "M7 real acceptance chain",
                },
            )
            candidate = wait_candidate(admin, candidate["id"], {"PENDING_APPROVAL"})
            gate = candidate["gate_summary"]
            if (
                gate.get("traceability_percent") != 100
                or gate.get("schema_compliance_percent") != 100
                or not gate.get("evaluation_passed")
            ):
                raise RuntimeError(f"Release gate was not complete: {gate}")
            publisher.request(
                "POST",
                f"/release-candidates/{candidate['id']}/publish",
                expected=202,
                json={"reason": "Independent M7 acceptance approval", "channel": "stable"},
            )
            wait_candidate(admin, candidate["id"], {"PUBLISHED"})
            published = admin.request("GET", f"/spaces/{args.space_id}/releases")["items"]
            releases.append(
                next(item for item in published if item["candidate_id"] == candidate["id"])
            )

        first, second = releases
        answer = admin.request(
            "POST",
            f"/releases/{first['id']}/queries",
            json={
                "question": claim["statement"],
                "strategy": "HYBRID",
                "top_k": 5,
                "client_request_id": f"m7-answer-{suffix}",
            },
        )
        replay = admin.request(
            "POST",
            f"/releases/{first['id']}/queries",
            json={
                "question": claim["statement"],
                "strategy": "HYBRID",
                "top_k": 5,
                "client_request_id": f"m7-answer-{suffix}",
            },
        )
        if (
            answer["status"] != "COMPLETED"
            or not answer["citations"]
            or replay["id"] != answer["id"]
        ):
            raise RuntimeError(
                "Fixed-Release query was not evidence-backed and idempotently reproducible"
            )
        refused = admin.request(
            "POST",
            f"/releases/{first['id']}/queries",
            json={
                "question": "What is the launch code for an unrelated satellite?",
                "strategy": "HYBRID",
                "top_k": 5,
                "client_request_id": f"m7-refusal-{suffix}",
            },
        )
        if refused["status"] != "REFUSED" or refused["citations"]:
            raise RuntimeError("Insufficient evidence did not trigger a citation-free refusal")

        current_pointer = admin.request(
            "GET", f"/spaces/{args.space_id}/release-pointer?channel=stable"
        )
        rollback = admin.request(
            "POST",
            f"/spaces/{args.space_id}/release-pointer",
            headers={"If-Match": f'"v{current_pointer["version"]}"'},
            json={
                "release_id": first["id"],
                "channel": "stable",
                "reason": "M7 rollback acceptance",
            },
        )
        if (
            rollback["version"] != current_pointer["version"] + 1
            or rollback["release_id"] != first["id"]
        ):
            raise RuntimeError("Release pointer rollback did not advance exactly one version")
        exported = admin.request("GET", f"/releases/{first['id']}/export?format=json")
        if (
            exported["release"]["manifest_checksum"] != first["manifest_checksum"]
            or not exported["items"]
        ):
            raise RuntimeError("Immutable Release export is incomplete")
        rebuilt = publisher.request("POST", f"/releases/{first['id']}/projections/rebuild")
        if not rebuilt["rebuilt"] or rebuilt["document_count"] < 1:
            raise RuntimeError("Release projection rebuild failed")
        after = admin.request("GET", f"/releases/{first['id']}")
        if after["manifest_checksum"] != first["manifest_checksum"] or second["id"] == first["id"]:
            raise RuntimeError("Rollback or projection rebuild mutated Release history")
    print(
        "M7 real chain verified: fixed quality gate, independent approval, two immutable "
        "Releases, evidence-backed reproducible query, refusal, export, projection rebuild "
        "and pointer-only rollback."
    )


if __name__ == "__main__":
    main()
