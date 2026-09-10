"""Stage A isolated software R1 chain. Synthetic data/roles, no expert acceptance."""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import verify_m6
import verify_m7
from verify_m5 import _compile, _create_published_schema, _create_source, _login
from verify_m95 import upload

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8080/api/v1"
OUTPUT = ROOT / ".nexweave-data/stage-a-r1.json"


def main() -> None:
    suffix = uuid4().hex[:10]
    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as client:
        api = _login(client, "local-admin")
        org = api.request("GET", "/organizations").json()["items"][0]
        space = api.request(
            "POST",
            "/spaces",
            expected=201,
            idempotency_key=str(uuid4()),
            json={
                "organization_id": org["id"],
                "slug": f"stage-a-test-{suffix}",
                "display_name": f"阶段 A 软件回归 · 合成数据 {suffix}",
                "description": "Synthetic scripted software test; no industrial/expert acceptance.",
                "default_classification": "INTERNAL",
            },
        ).json()
        sid = space["id"]
        source = _create_source(api, sid, suffix)
        # Multi-chunk request followed by upload completion/polling on the same keep-alive client.
        csv = b"timestamp,value\n" + b"2026-09-01T00:00:00Z,70\n" * 12000
        trace_source = upload(api, sid, "stage-a-synthetic-trace.csv", "text/csv", csv)
        schema = _create_published_schema(api, client, space, suffix)
        prompt = api.request(
            "POST",
            "/prompt-versions",
            idempotency_key=str(uuid4()),
            json={
                "space_id": sid,
                "prompt_key": f"stage-a.synthetic.{suffix}",
                "content": "Extract governed entities and claims using only the supplied schema.",
                "output_contract": {"kind": "nexweave.structured-compile/v1"},
            },
        ).json()
        model = api.request(
            "POST",
            "/model-profiles",
            idempotency_key=str(uuid4()),
            json={
                "space_id": sid,
                "name": f"Stage A synthetic structured provider {suffix}",
                "provider": "nexweave.local",
                "model_name": "structured-compile-v1",
                "externally_hosted": False,
                "maximum_classification": "INTERNAL",
                "config": {"max_input_units": 200000},
            },
        ).json()
        compiled = _compile(
            api,
            space_id=sid,
            schema_id=schema["id"],
            source_id=source,
            prompt_id=prompt["id"],
            profile_id=model["id"],
            suffix=suffix,
            mode="FULL",
        )
        pages = api.request("GET", f"/spaces/{sid}/wiki/pages").json()["items"]
        page = next(p for p in pages if "Pump A" in p["title"])
        detail = api.request("GET", f"/wiki/pages/{page['id']}").json()
        candidate = {
            "id": next(
                e["claim_candidate_id"]
                for e in detail["evidence_candidates"]
                if e["claim_candidate_id"]
            )
        }
        record = {
            "space_id": sid,
            "source_version_id": source,
            "trace_source_version_id": trace_source,
            "schema_id": schema["id"],
            "compile_job_id": compiled["id"],
            "candidate_id": candidate["id"],
            "data_kind": "SYNTHETIC",
            "review_actor_kind": "SCRIPTED_TEST_ROLES",
        }
        OUTPUT.write_text(json.dumps(record, indent=2))
        print("Source, large-upload trace isolation, Schema and Compile passed.", flush=True)
        sys.argv = [
            "verify_m6",
            "--base-url",
            BASE,
            "--space-id",
            sid,
            "--candidate-id",
            candidate["id"],
        ]
        verify_m6.main()
        claim = next(
            c
            for c in api.request("GET", f"/spaces/{sid}/claims").json()["items"]
            if c["candidate_id"] == candidate["id"]
        )
        sys.argv = ["verify_m7", "--base-url", BASE, "--space-id", sid, "--claim-id", claim["id"]]
        verify_m7.main()
        record.update(
            {
                "claim_id": claim["id"],
                "evidence": api.request("GET", f"/claims/{claim['id']}/evidence").json(),
                "releases": api.request("GET", f"/spaces/{sid}/releases").json()["items"],
                "pointer": api.request(
                    "GET", f"/spaces/{sid}/release-pointer?channel=stable"
                ).json(),
                "completed_at": datetime.now(UTC).isoformat(),
                "checks": [
                    "SOURCE_PARSE",
                    "KEEPALIVE_TRACE",
                    "COMPILE",
                    "REVIEW_DUTY_SEPARATION",
                    "ACCEPTED_EVIDENCE",
                    "QUALITY_GATE",
                    "IMMUTABLE_RELEASES",
                    "CITED_QUERY",
                    "QUERY_IDEMPOTENCY",
                    "REFUSAL",
                    "EXPORT",
                    "REBUILD",
                    "POINTER_ROLLBACK",
                ],
            }
        )
        OUTPUT.write_text(json.dumps(record, ensure_ascii=False, indent=2))
        print(f"Stage A R1 software E2E passed: {sid}; synthetic only.")


if __name__ == "__main__":
    main()
