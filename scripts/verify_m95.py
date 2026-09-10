"""Create labelled P-101 replay data through real R1 APIs, then run real providers.

No industrial data, expert sign-off, Evidence approval or Release is fabricated.
Re-running uses the saved binding; --fresh creates a separate demonstration space.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import httpx
from verify_m5 import Api as LegacyApi
from verify_m5 import _compile
from verify_m9_public_pilot import _direct_composed_snapshot

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".nexweave-data/m95-e2e.json"


class Api(LegacyApi):
    def request(
        self,
        method,
        path,
        *,
        expected=200,
        idempotency_key=None,
        version=None,
        extra_headers=None,
        **kwargs,
    ):
        trace_id = uuid4().hex
        headers = {
            "Authorization": f"Bearer {self.token}",
            "traceparent": f"00-{trace_id}-{uuid4().hex[:16]}-01",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if version is not None:
            headers["If-Match"] = f'"v{version}"'
        headers.update(extra_headers or {})
        response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(f"{method} {path}: {response.status_code}: {response.text[:800]}")
        if response.headers.get("X-Trace-Id") != trace_id:
            raise RuntimeError(f"{method} {path} did not preserve W3C trace context")
        return response


def _login(client, subject):
    response = client.post("/auth/dev/session", json={"subject": subject})
    response.raise_for_status()
    return Api(client, response.json()["access_token"])


def upload(api: Api, space_id: str, name: str, mime: str, content: bytes) -> str:
    checksum = "sha256:" + hashlib.sha256(content).hexdigest()
    item = api.request(
        "POST",
        f"/spaces/{space_id}/sources/uploads",
        expected=201,
        idempotency_key=str(uuid4()),
        json={
            "filename": name,
            "content_type": mime,
            "expected_size": len(content),
            "expected_checksum": checksum,
            "display_name": name,
            "description": "SYNTHETIC / M9.5 工程演示，非真实工业观测或专家知识。",
            "classification": "INTERNAL",
            "tags": ["synthetic", "m95-demo"],
        },
    ).json()
    api.request(
        "PUT",
        f"/sources/uploads/{item['id']}/content",
        content=content,
        extra_headers={"Content-Type": mime},
    )
    done = api.request(
        "POST",
        f"/sources/uploads/{item['id']}/complete",
        expected=202,
        idempotency_key=str(uuid4()),
        json={"checksum": checksum, "size": len(content)},
    ).json()
    result = api.wait(
        f"/parse-jobs/{done['parse_job_id']}", {"SUCCEEDED", "FAILED", "PARTIAL_FAILED"}
    )
    assert result["status"] == "SUCCEEDED", result
    return str(done["source_version_id"])


def setup(api: Api, client: httpx.Client, *, fresh: bool = False) -> dict:
    checkpoint = ROOT / ".nexweave-data/m95-binding-inputs.json"
    if checkpoint.exists() and not fresh:
        saved = json.loads(checkpoint.read_text())
        return bind(api, saved["sid"], saved["schema"], saved["entity"], saved["csv_source"])
    suffix = uuid4().hex[:8]
    org = api.request("GET", "/organizations").json()["items"][0]
    space = api.request(
        "POST",
        "/spaces",
        expected=201,
        idempotency_key=str(uuid4()),
        json={
            "organization_id": org["id"],
            "slug": f"living-p101-{suffix}",
            "display_name": "P-101 运行知识演示",
            "description": "SYNTHETIC 条件预测工程演示",
            "default_classification": "INTERNAL",
        },
    ).json()
    sid = space["id"]
    declarations = _direct_composed_snapshot()
    declarations.update(
        json.loads(
            (ROOT / "domain-packs/equipment-rca/living/temporal-declarations.json").read_text()
        )
    )
    schema = api.request(
        "POST",
        f"/spaces/{sid}/schemas",
        expected=201,
        idempotency_key=str(uuid4()),
        json={
            "schema_key": f"living-{suffix}.nexweave.io/equipment-rca",
            "display_name": "Equipment RCA · 运行语义",
            "semantic_version": "0.1.0",
            "snapshot": declarations,
        },
    ).json()
    path = f"/schemas/{schema['schema_definition_id']}/versions/0.1.0"
    api.request("POST", path + "/validate")
    schema = api.request("GET", path).json()
    subject = f"living-publisher-{suffix}"
    publisher = api.request(
        "POST",
        "/users",
        idempotency_key=str(uuid4()),
        json={
            "issuer": "https://identity.nexweave.local/dev",
            "subject": subject,
            "display_name": "运行演示 Schema 技术发布身份（非领域专家）",
            "clearance": "INTERNAL",
            "tenant_roles": [],
        },
    ).json()
    api.request(
        "PUT",
        f"/spaces/{sid}/members/{publisher['id']}",
        idempotency_key=str(uuid4()),
        json={"subject_type": "USER", "roles": ["publisher"], "clearance": "INTERNAL"},
    )
    schema = (
        _login(client, subject)
        .request("POST", path + "/publish", idempotency_key=str(uuid4()), version=schema["version"])
        .json()
    )
    source = upload(
        api,
        sid,
        "P-101-demo.txt",
        "text/plain",
        (
            "P-101. Pump equipment demonstration. Synthetic boiler feedwater pump.\n\n"
            "此设备卡片只用于 M9.5 技术演示，无真实检修和规程记录。"
        ).encode(),
    )
    prompt = api.request(
        "POST",
        "/prompt-versions",
        idempotency_key=str(uuid4()),
        json={
            "space_id": sid,
            "prompt_key": f"living.demo.{suffix}",
            "content": "Extract draft entities using supplied schema only.",
            "output_contract": {"kind": "nexweave.structured-compile/v1"},
        },
    ).json()
    profile = api.request(
        "POST",
        "/model-profiles",
        idempotency_key=str(uuid4()),
        json={
            "space_id": sid,
            "name": "本地规则编译（非 LLM）",
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
        profile_id=profile["id"],
        suffix=suffix,
        mode="FULL",
    )
    entities = api.request("GET", f"/spaces/{sid}/entities").json()["items"]
    entity = next(e for e in entities if e["display_name"] == "P-101")
    rows = ["timestamp,temperature,vibration,lube,load,quality"]
    temp = 57.0
    for i in range(1440):
        load = 70 + 14 * math.sin(i / 100)
        if i >= 1320:
            load = 70.0
        temp += 0.035 * ((42 + 0.23 * load) - temp) + 0.008 * math.sin(i / 9)
        timestamp = (datetime(2026, 9, 6, tzinfo=UTC) + timedelta(minutes=i)).isoformat()
        rows.append(
            f"{timestamp},{temp:.4f},{2.1 + 0.002 * load + 0.05 * math.sin(i / 31):.4f},"
            f"{0.25 + 0.002 * math.sin(i / 25):.4f},{load:.4f},GOOD"
        )
    csv_source = upload(
        api, sid, "P-101-synthetic-runtime.csv", "text/csv", "\n".join(rows).encode()
    )
    return bind(api, sid, schema, entity, csv_source)


def bind(api, sid, schema, entity, csv_source):
    declarations = json.loads(
        (ROOT / "domain-packs/equipment-rca/living/temporal-declarations.json").read_text()
    )
    temporal = declarations["signalDefinitions"]
    columns = ["temperature", "vibration", "lube", "load"]
    (ROOT / ".nexweave-data/m95-binding-inputs.json").write_text(
        json.dumps({"sid": sid, "schema": schema, "entity": entity, "csv_source": csv_source})
    )
    binding = api.request(
        "POST",
        f"/spaces/{sid}/signal-bindings",
        expected=201,
        idempotency_key=str(uuid4()),
        json={
            "name": "P-101 · 轴承运行窗口",
            "entity_id": entity["id"],
            "schema_version_id": schema["id"],
            "source_version_id": csv_source,
            "profile_key": declarations["forecastProfiles"][0]["key"],
            "quality_column": "quality",
            "columns": [
                {"signal_key": s["key"], "column": c, "unit": s["unit"]}
                for s, c in zip(temporal, columns, strict=True)
            ],
            "data_kind": "SYNTHETIC",
            "operating_context": "合成给水泵工况；末段负荷70%；仅验证软件链路。",
        },
    ).json()
    result = {
        "space_id": sid,
        "binding_id": binding["id"],
        "schema_id": schema["id"],
        "entity_id": entity["id"],
        "source_id": csv_source,
        "runs": [],
    }
    STATE.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fresh", action="store_true")
    args = parser.parse_args()
    with httpx.Client(
        base_url="http://localhost:8000/api/v1", timeout=30, trust_env=False
    ) as client:
        api = _login(client, "local-admin")
        state = (
            setup(api, client, fresh=args.fresh)
            if args.fresh or not STATE.exists()
            else json.loads(STATE.read_text())
        )
        for name, provider, values in (
            ("负荷保持70%", "chronos2", [70.0] * 120),
            ("两小时负荷70%升至95%", "chronos2", [70 + 25 * (i + 1) / 120 for i in range(120)]),
            ("持久性基准（忽略协变量）", "persistence", [70.0] * 120),
        ):
            body = {
                "binding_id": state["binding_id"],
                "provider_id": provider,
                "horizon": 120,
                "history_points": 720,
                "scenario_name": name,
                "future_paths": [
                    {"signal_key": "equipment.rca/unit-load", "unit": "%", "values": values}
                ],
                "event_rule": {
                    "threshold": 60.0,
                    "unit": "degC",
                    "label": "轴承温度进入演示关注区间",
                    "authority": "DEMONSTRATION_ONLY",
                },
            }
            key = str(uuid4())
            run = api.request(
                "POST",
                f"/spaces/{state['space_id']}/forecast-runs",
                expected=202,
                idempotency_key=key,
                json=body,
            ).json()
            replay = api.request(
                "POST",
                f"/spaces/{state['space_id']}/forecast-runs",
                expected=202,
                idempotency_key=key,
                json=body,
            ).json()
            assert run["id"] == replay["id"]
            run = api.wait(
                f"/forecast-runs/{run['id']}", {"SUCCEEDED", "FAILED", "CANCELLED"}, timeout=600
            )
            assert run["status"] == "SUCCEEDED", run
            artifact = api.request("GET", f"/forecast-artifacts/{run['artifact_id']}").json()
            state["runs"].append(
                {
                    "run_id": run["id"],
                    "artifact_id": artifact["id"],
                    "checksum": artifact["content_checksum"],
                    "scenario": name,
                    "provider": provider,
                    "p50_end": artifact["content"]["result"]["quantiles"]["0.5"][-1],
                    "events": artifact["content"]["event_evaluation"],
                }
            )
            STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2))
            print(json.dumps(state["runs"][-1], ensure_ascii=False), flush=True)
        print("M9.5 real execution succeeded with SYNTHETIC inputs; not an industrial benchmark.")


if __name__ == "__main__":
    main()
