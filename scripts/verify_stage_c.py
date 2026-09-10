"""Actual fixed-Release context on an existing Chronos artifact; synthetic test roles only."""

import json
import sys
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import verify_m6
import verify_m7
from verify_m5 import _compile, _create_published_schema, _login
from verify_m95 import upload

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8080/api/v1"
CHECKPOINT = ROOT / ".nexweave-data/stage-c-reference.json"


@contextmanager
def preserve_pointer(api, client, sid):
    path = f"/spaces/{sid}/release-pointer"
    response = client.get(
        path, params={"channel": "stable"}, headers={"Authorization": f"Bearer {api.token}"}
    )
    if response.status_code != 404:
        response.raise_for_status()
    previous = response.json() if response.status_code == 200 else None
    try:
        yield
    finally:
        if previous:
            current = api.request("GET", path, params={"channel": "stable"}).json()
            if current["release_id"] != previous["release_id"]:
                api.request(
                    "POST",
                    path,
                    version=current["version"],
                    idempotency_key=str(uuid4()),
                    json={
                        "release_id": previous["release_id"],
                        "channel": "stable",
                        "reason": "Restore pre-test pointer after synthetic Stage C verification.",
                    },
                )


def reference(api, client, sid, checkpoint=CHECKPOINT):
    if checkpoint.exists():
        return json.loads(checkpoint.read_text())
    suffix = uuid4().hex[:10]
    space = api.request("GET", f"/spaces/{sid}").json()
    source = upload(
        api,
        sid,
        "stage-c-synthetic-reference-" + suffix + ".txt",
        "text/plain",
        (
            b"Pump A is a synthetic reference for knowledge retrieval alongside P-101 forecasts. "
            b"Check lubrication records and vibration history when reviewing temperature changes. "
            b"This fictional example is not an approved procedure or industrial case.\n\n"
            b"Pump B is a synthetic standby reference."
        ),
    )
    schema = _create_published_schema(api, client, space, suffix)
    prompt = api.request(
        "POST",
        "/prompt-versions",
        idempotency_key=str(uuid4()),
        json={
            "space_id": sid,
            "prompt_key": f"stage-c.synthetic.{suffix}",
            "content": "Extract entities and claims using the supplied schema and sources only.",
            "output_contract": {"kind": "nexweave.structured-compile/v1"},
        },
    ).json()
    model = api.request(
        "POST",
        "/model-profiles",
        idempotency_key=str(uuid4()),
        json={
            "space_id": sid,
            "name": "Stage C synthetic structured provider " + suffix,
            "provider": "nexweave.local",
            "model_name": "structured-compile-v1",
            "externally_hosted": False,
            "maximum_classification": "INTERNAL",
            "config": {"max_input_units": 200000},
        },
    ).json()
    _compile(
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
    page = next(
        p for p in pages if "Pump A" in p["title"] and p["schema_version_id"] == schema["id"]
    )
    detail = api.request("GET", f"/wiki/pages/{page['id']}").json()
    candidate = next(
        e["claim_candidate_id"] for e in detail["evidence_candidates"] if e["claim_candidate_id"]
    )
    sys.argv = ["verify_m6", "--base-url", BASE, "--space-id", sid, "--candidate-id", candidate]
    verify_m6.main()
    claim = next(
        c
        for c in api.request("GET", f"/spaces/{sid}/claims").json()["items"]
        if c["candidate_id"] == candidate
    )
    sys.argv = ["verify_m7", "--base-url", BASE, "--space-id", sid, "--claim-id", claim["id"]]
    with preserve_pointer(api, client, sid):
        verify_m7.main()
    releases = [
        r
        for r in api.request("GET", f"/spaces/{sid}/releases").json()["items"]
        if r["schema_version_id"] == schema["id"]
    ]
    result = {
        "source_version_id": source,
        "claim": claim,
        "releases": releases,
        "data_kind": "SYNTHETIC",
        "review_actor_kind": "SCRIPTED_TEST_ROLES",
    }
    checkpoint.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main():
    previous = json.loads((ROOT / ".nexweave-data/stage-b-e2e.json").read_text())
    aid, sid = previous["outputs"][0]["artifact_id"], previous["space_id"]
    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as client:
        api = _login(client, "local-admin")
        artifact = api.request("GET", f"/forecast-artifacts/{aid}").json()
        assert artifact["content"]["result"]["provider_id"] == "chronos2"
        ref = reference(api, client, sid)
        path = f"/forecast-artifacts/{aid}/knowledge-context"
        body = {"release_id": ref["releases"][0]["id"], "question": ref["claim"]["statement"]}
        result = api.request("POST", path, json=body).json()
        assert result["status"] == "CITED_CONTEXT" and result["items"]
        assert all(i["statement"] == ref["claim"]["statement"] for i in result["items"])
        assert all(i["citation"]["release_id"] == body["release_id"] for i in result["items"])
        for item in result["items"]:
            citation = item["citation"]
            api.request(
                "GET",
                f"/source-versions/{citation['source_version_id']}/preview",
                params={"anchor_id": citation["source_anchor_id"]},
            )
        insufficient = api.request(
            "POST", path, json={**body, "question": "unrelated satellite launch code"}
        ).json()
        assert insufficient["status"] == "INSUFFICIENT_EVIDENCE" and not insufficient["items"]
        other = json.loads((ROOT / ".nexweave-data/stage-a-r1.json").read_text())["releases"][0][
            "id"
        ]
        api.request("POST", path, expected=404, json={**body, "release_id": other})
        # Existing non-member identity from the M9.5 guard verifier.
        outsider_subject = "stage-c-outsider-" + uuid4().hex[:10]
        api.request(
            "POST",
            "/users",
            idempotency_key=str(uuid4()),
            json={
                "issuer": "https://identity.nexweave.local/dev",
                "subject": outsider_subject,
                "display_name": "Stage C synthetic outsider",
                "clearance": "INTERNAL",
                "tenant_roles": [],
            },
        )
        outsider = _login(client, outsider_subject)
        outsider.request("POST", path, expected=403, json=body)
        second = api.request(
            "POST", path, json={**body, "release_id": ref["releases"][1]["id"]}
        ).json()
        assert second["release_id"] != result["release_id"] and second["items"]
        assert api.request("GET", f"/forecast-artifacts/{aid}").json() == artifact
        report = {
            "completed_at": datetime.now(UTC).isoformat(),
            "space_id": sid,
            "artifact_id": aid,
            "artifact_checksum_unchanged": artifact["content_checksum"],
            "context": result,
            "second_release_id": second["release_id"],
            "refusal": True,
            "cross_space_denied": True,
            "outsider_denied": True,
            "anchor_preview": "PASSED",
            "data_kind": "SYNTHETIC",
            "review_actor_kind": "SCRIPTED_TEST_ROLES",
            "industrial_acceptance": False,
        }
        (ROOT / ".nexweave-data/stage-c-e2e.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2)
        )
        print(
            json.dumps(
                {"status": "PASSED", "citations": len(result["items"]), "artifact_unchanged": True}
            )
        )


if __name__ == "__main__":
    main()
