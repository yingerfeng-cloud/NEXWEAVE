"""Real self-service binding APIs and Chronos conditions on explicitly synthetic data."""

from __future__ import annotations

import copy
import csv
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
from verify_m95 import _login, upload

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    state = json.loads((ROOT / ".nexweave-data/m95-e2e.json").read_text())
    sid = state["space_id"]
    with httpx.Client(
        base_url="http://127.0.0.1:8080/api/v1", timeout=120, trust_env=False
    ) as client:
        api = _login(client, "local-admin")
        bindings = api.request("GET", f"/spaces/{sid}/signal-bindings").json()["items"]
        original = next(b for b in bindings if b["id"] == state["binding_id"])
        assert original["data_kind"] == "SYNTHETIC"
        run = api.request("GET", f"/forecast-runs/{state['runs'][0]['run_id']}").json()
        artifact = api.request("GET", f"/forecast-artifacts/{run['artifact_id']}").json()
        points = artifact["content"]["context"]["observations"]
        body = {
            k: original[k]
            for k in [
                "name",
                "entity_id",
                "schema_version_id",
                "profile_key",
                "timestamp_column",
                "columns",
                "quality_column",
                "data_kind",
                "operating_context",
            ]
        }
        stream = io.StringIO()
        fields = [body["timestamp_column"], *[c["column"] for c in body["columns"]]]
        if body["quality_column"]:
            fields.append(body["quality_column"])
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for p in points:
            row = {
                body["timestamp_column"]: p["timestamp"],
                **{c["column"]: p["values"][c["signal_key"]] for c in body["columns"]},
            }
            if body["quality_column"]:
                row[body["quality_column"]] = "GOOD"
            writer.writerow(row)
        raw = stream.getvalue().encode()
        source = upload(api, sid, "stage-b-synthetic-binding.csv", "text/csv", raw)
        body.update(
            source_version_id=source,
            name="阶段 B 自主绑定验证 · 合成数据",
            operating_context="从既有合成开发窗口复制的受控 CSV；非现场观测。",
        )
        prefix = f"/spaces/{sid}/signal-bindings"
        preview = api.request("GET", f"/spaces/{sid}/time-series-sources/{source}/preview").json()
        assert preview["row_count"] == len(points) and len(preview["sample_rows"]) == 5
        assert "object_key" not in preview
        entities = api.request("GET", f"/spaces/{sid}/binding-entities").json()["items"]
        assert any(e["id"] == body["entity_id"] for e in entities)
        before = len(api.request("GET", prefix).json()["items"])
        validation = api.request("POST", prefix + "/validate", json=body).json()
        assert validation["point_count"] == len(points)
        assert len(api.request("GET", prefix).json()["items"]) == before
        for alteration, code in [
            ("unit", "UNIT_OR_TYPE_MISMATCH"),
            ("column", "DATA_QUALITY_INSUFFICIENT"),
        ]:
            bad = copy.deepcopy(body)
            bad["columns"][0][alteration] = (
                "invalid-unit" if alteration == "unit" else "missing-column"
            )
            for endpoint in [prefix + "/validate", prefix]:
                response = api.request(
                    "POST", endpoint, expected=422, idempotency_key=str(uuid4()), json=bad
                ).json()
                assert response["code"] == code, response
        assert len(api.request("GET", prefix).json()["items"]) == before
        key = str(uuid4())
        saved = api.request("POST", prefix, expected=201, idempotency_key=key, json=body).json()
        replay = api.request("POST", prefix, expected=201, idempotency_key=key, json=body).json()
        assert saved["id"] == replay["id"]
        different = {**body, "name": "different payload"}
        api.request("POST", prefix, expected=409, idempotency_key=key, json=different)
        outputs = []
        for scenario, increase in [("持续工况", 0), ("上升工况", 25)]:
            request = copy.deepcopy(run["request"])
            request.update(binding_id=saved["id"], scenario_name="阶段 B 合成条件 · " + scenario)
            for path in request["future_paths"]:
                initial = validation["latest_values"][path["signal_key"]]
                path["values"] = [
                    initial + increase * (i + 1) / request["horizon"]
                    for i in range(request["horizon"])
                ]
            created = api.request(
                "POST",
                f"/spaces/{sid}/forecast-runs",
                expected=202,
                idempotency_key=str(uuid4()),
                json=request,
            ).json()
            finished = api.wait(
                f"/forecast-runs/{created['id']}", {"SUCCEEDED", "FAILED"}, timeout=120
            )
            assert finished["status"] == "SUCCEEDED", finished["error_code"]
            result = api.request("GET", f"/forecast-artifacts/{finished['artifact_id']}").json()
            assert result["epistemic_kind"] == "FORECAST" and result["data_kind"] == "SYNTHETIC"
            assert result["content"]["released_knowledge"]["status"] == "NO_RELEASE_SELECTED"
            outputs.append(result)
        assert (
            outputs[0]["content"]["context"]["observations"]
            == outputs[1]["content"]["context"]["observations"]
        )
        subject = "stage-b-outsider-" + uuid4().hex[:8]
        api.request(
            "POST",
            "/users",
            idempotency_key=str(uuid4()),
            json={
                "issuer": "https://identity.nexweave.local/dev",
                "subject": subject,
                "display_name": "Stage B synthetic outsider",
                "clearance": "INTERNAL",
                "tenant_roles": [],
            },
        )
        outsider = _login(client, subject)
        outsider.request("GET", f"/spaces/{sid}/time-series-sources/{source}/preview", expected=403)
        outsider.request("GET", f"/spaces/{sid}/binding-entities", expected=403)
        outsider.request("POST", prefix + "/validate", expected=403, json=body)
        outsider.request("POST", prefix, expected=403, idempotency_key=str(uuid4()), json=body)
        report = {
            "completed_at": datetime.now(UTC).isoformat(),
            "space_id": sid,
            "binding_id": saved["id"],
            "source_version_id": source,
            "data_kind": "SYNTHETIC",
            "row_count": preview["row_count"],
            "preview_sample_rows": len(preview["sample_rows"]),
            "validation": validation,
            "invalid_mapping_rejections": 4,
            "direct_save_rejections": 2,
            "outsider_denials": 4,
            "binding_idempotency": True,
            "same_history": True,
            "outputs": [
                {
                    "artifact_id": a["id"],
                    "run_id": a["run_id"],
                    "checksum": a["content_checksum"],
                    "p50_end": a["content"]["result"]["quantiles"]["0.5"][-1],
                    "provider": a["content"]["result"]["provider_id"],
                    "model_revision": a["content"]["result"]["model_revision"],
                }
                for a in outputs
            ],
            "industrial_acceptance": False,
        }
        (ROOT / ".nexweave-data/stage-b-e2e.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False)
        )
        print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
