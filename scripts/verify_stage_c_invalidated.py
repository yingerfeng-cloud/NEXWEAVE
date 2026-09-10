"""Invalidate only a new synthetic reference; active Stage C demo references stay usable."""

import json
from uuid import uuid4

import httpx
from verify_stage_c import BASE, ROOT, _login, reference


def main():
    state = json.loads((ROOT / ".nexweave-data/stage-c-e2e.json").read_text())
    with httpx.Client(base_url=BASE, timeout=120, trust_env=False) as client:
        api = _login(client, "local-admin")
        ref = reference(
            api, client, state["space_id"], ROOT / ".nexweave-data/stage-c-negative-reference.json"
        )
        path = f"/forecast-artifacts/{state['artifact_id']}/knowledge-context"
        body = {"release_id": ref["releases"][0]["id"], "question": ref["claim"]["statement"]}
        before = api.request("POST", path, json=body).json()
        assert before["status"] == "CITED_CONTEXT"
        item = before["items"][0]
        source = api.request("GET", f"/sources/{item['source_document_id']}").json()
        version = next(v for v in source["versions"] if v["id"] == ref["source_version_id"])
        api.request(
            "POST",
            f"/source-versions/{version['id']}/invalidate",
            expected=201,
            idempotency_key=str(uuid4()),
            version=version["version"],
            json={
                "reason_code": "SYNTHETIC_TEST",
                "reason": "Stage C isolated invalidation test.",
                "policy_version": "stage-c-test/1",
            },
        )
        after = api.request("POST", path, json=body).json()
        assert after["status"] == "INSUFFICIENT_EVIDENCE" and after["items"] == []
        assert after["artifact_checksum"] == state["artifact_checksum_unchanged"]
        original = api.request(
            "POST",
            path,
            json={
                "release_id": state["context"]["release_id"],
                "question": state["context"]["question"],
            },
        ).json()
        assert original["status"] == "CITED_CONTEXT"
        report = {
            "source_version_id": version["id"],
            "release_id": body["release_id"],
            "before": before["status"],
            "after": after["status"],
            "active_reference_still_cited": True,
            "artifact_unchanged": True,
            "data_kind": "SYNTHETIC",
            "industrial_acceptance": False,
        }
        (ROOT / ".nexweave-data/stage-c-invalidated.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report))


if __name__ == "__main__":
    main()
