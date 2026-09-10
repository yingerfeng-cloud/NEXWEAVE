"""Exercise scoped access, immutable rows and checksums against the running slice."""

import asyncio
import hashlib
import json
import os
import sys
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import httpx
from dotenv import dotenv_values
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine
from verify_m95 import ROOT, STATE, _login

for relative in (
    "apps/api/src",
    "packages/domain/src",
    "packages/contracts/src",
    "packages/application/src",
):
    sys.path.insert(0, str(ROOT / relative))


async def main():
    state = json.loads(STATE.read_text())
    with httpx.Client(
        base_url="http://127.0.0.1:8000/api/v1", timeout=30, trust_env=False
    ) as client:
        admin = _login(client, "local-admin")
        subject = "living-outsider-" + uuid4().hex[:8]
        admin.request(
            "POST",
            "/users",
            idempotency_key=str(uuid4()),
            json={
                "issuer": "https://identity.nexweave.local/dev",
                "subject": subject,
                "display_name": "M9.5 access-denial test",
                "clearance": "INTERNAL",
                "tenant_roles": [],
            },
        )
        outsider = _login(client, subject)
        outsider.request("GET", f"/spaces/{state['space_id']}/signal-bindings", expected=403)
        outsider.request("GET", f"/forecast-runs/{state['runs'][0]['run_id']}", expected=403)
        outsider.request(
            "GET", f"/forecast-artifacts/{state['runs'][0]['artifact_id']}", expected=403
        )
        run = admin.request("GET", f"/forecast-runs/{state['runs'][0]['run_id']}").json()
        body = run["request"]
        body["future_paths"] = []
        key = str(uuid4())
        bad = admin.request(
            "POST",
            f"/spaces/{state['space_id']}/forecast-runs",
            expected=202,
            idempotency_key=key,
            json=body,
        ).json()
        bad = admin.wait(f"/forecast-runs/{bad['id']}", {"SUCCEEDED", "FAILED"}, timeout=60)
        assert (
            bad["status"] == "FAILED"
            and bad["error_code"] == "FUTURE_COVARIATE_INCOMPLETE"
            and bad["artifact_id"] is None
        )
        body["horizon"] = 119
        admin.request(
            "POST",
            f"/spaces/{state['space_id']}/forecast-runs",
            expected=409,
            idempotency_key=key,
            json=body,
        )
        artifact = admin.request(
            "GET", f"/forecast-artifacts/{state['runs'][0]['artifact_id']}"
        ).json()
    for k, v in dotenv_values(ROOT / ".env").items():
        if v is not None:
            os.environ.setdefault(k, v)
    from nexweave_api.object_storage import S3ObjectStorage
    from nexweave_api.settings import Settings

    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    p = urlsplit(os.environ["NEXWEAVE_DATABASE_URL"])
    url = urlunsplit(
        (p.scheme, p.netloc.replace(p.hostname, "127.0.0.1"), p.path, p.query, p.fragment)
    )
    engine = create_async_engine(url)
    async with engine.connect() as c:
        row = (
            (
                await c.execute(
                    text("SELECT object_key,content_checksum FROM forecast_artifacts WHERE id=:id"),
                    {"id": artifact["id"]},
                )
            )
            .mappings()
            .one()
        )
    storage = S3ObjectStorage(Settings(object_store_endpoint="http://127.0.0.1:9000"))
    raw = await storage.get(key=row["object_key"])
    assert (
        "sha256:" + hashlib.sha256(raw).hexdigest()
        == row["content_checksum"]
        == artifact["content_checksum"]
    )
    assert json.loads(raw) == artifact["content"]
    for table, identifier in (
        ("signal_bindings", state["binding_id"]),
        ("forecast_runs", state["runs"][0]["run_id"]),
        ("forecast_artifacts", artifact["id"]),
    ):
        async with engine.connect() as c:
            try:
                # Static table allowlist; deliberate no-op UPDATE must still be rejected.
                statement = text(f"UPDATE {table} SET id=id WHERE id=:id")  # noqa: S608
                await c.execute(statement, {"id": identifier})
            except DBAPIError as exc:
                assert "immutable" in str(exc).lower()
            else:
                raise AssertionError(f"Immutable guard missing: {table}")
            finally:
                await c.rollback()
    await engine.dispose()
    report = {
        "outsider_binding_run_artifact": "DENIED",
        "future_input_failure": "FAILED_WITHOUT_ARTIFACT",
        "idempotency_payload_conflict": "409",
        "object_storage_checksum": "MATCH",
        "immutable_tables": 3,
        "industrial_benchmark": False,
    }
    (ROOT / ".nexweave-data/m95-guards.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report))


if __name__ == "__main__":
    asyncio.run(main())
