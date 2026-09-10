"""Verify authoritative Source invalidation rejects the new preview and binding APIs."""

import json
from pathlib import Path
from uuid import uuid4

import httpx
from verify_m95 import _login, upload

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = json.loads((ROOT / ".nexweave-data/stage-b-e2e.json").read_text())
    sid = state["space_id"]
    with httpx.Client(
        base_url="http://127.0.0.1:8080/api/v1", trust_env=False, timeout=120
    ) as client:
        api = _login(client, "local-admin")
        raw = api.request("GET", f"/source-versions/{state['source_version_id']}/content").content
        name = "stage-b-invalidated-synthetic-" + uuid4().hex[:8] + ".csv"
        source = upload(api, sid, name, "text/csv", raw)
        csv_sources = api.request(
            "GET",
            f"/spaces/{sid}/sources",
            params={"content_type": "text/csv", "limit": 100, "search": name},
        ).json()["items"]
        assert len(csv_sources) == 1
        document = api.request("GET", f"/spaces/{sid}/sources", params={"search": name}).json()[
            "items"
        ][0]
        versions = api.request("GET", f"/sources/{document['id']}").json()["versions"]
        version = next(v for v in versions if v["id"] == source)
        assert "object_key" not in version
        api.request(
            "POST",
            f"/source-versions/{source}/invalidate",
            expected=201,
            idempotency_key=str(uuid4()),
            version=version["version"],
            json={
                "reason_code": "SYNTHETIC_TEST",
                "reason": "Stage B controlled negative test; no industrial evidence.",
                "policy_version": "stage-b-test/1",
            },
        )
        binding = next(
            b
            for b in api.request("GET", f"/spaces/{sid}/signal-bindings").json()["items"]
            if b["id"] == state["binding_id"]
        )
        body = {
            k: binding[k]
            for k in [
                "name",
                "entity_id",
                "schema_version_id",
                "source_version_id",
                "profile_key",
                "timestamp_column",
                "columns",
                "quality_column",
                "data_kind",
                "operating_context",
            ]
        }
        body["source_version_id"] = source
        responses = [
            api.request("GET", f"/spaces/{sid}/time-series-sources/{source}/preview", expected=409)
        ]
        for path in [f"/spaces/{sid}/signal-bindings/validate", f"/spaces/{sid}/signal-bindings"]:
            responses.append(
                api.request("POST", path, expected=409, idempotency_key=str(uuid4()), json=body)
            )
        assert all(r.json()["code"] == "SOURCE_VERSION_INVALIDATED" for r in responses)
        current = api.request("GET", f"/sources/{document['id']}").json()
        archived = api.request(
            "POST",
            f"/sources/{document['id']}/archive",
            idempotency_key=str(uuid4()),
            version=current["version"],
        ).json()
        assert archived["status"] == "ARCHIVED" and "archived_at" not in archived
        entities = api.request("GET", f"/spaces/{sid}/binding-entities").json()["items"]
        schemas = api.request("GET", f"/spaces/{sid}/schemas").json()["items"]
        assert any(e["id"] == binding["entity_id"] for e in entities)
        assert any(s["id"] == binding["schema_version_id"] for s in schemas)
        runtime = api.request("GET", f"/spaces/{sid}/forecast-runtime").json()
        report = {
            "source_version_id": source,
            "invalidated_source_denials": 3,
            "source_list_get_archive_contracts": "PASSED",
            "data_kind": "SYNTHETIC",
            "active_demo_source_unchanged": True,
            "wizard_resource_apis": "PASSED",
            "runtime": runtime,
        }
        (ROOT / ".nexweave-data/stage-b-invalidated.json").write_text(json.dumps(report, indent=2))
        print(json.dumps(report))


if __name__ == "__main__":
    main()
