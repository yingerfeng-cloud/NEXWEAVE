"""Direct keep-alive upload and concurrent HTTP trace isolation against the actual API."""

import asyncio
import json
from pathlib import Path
from uuid import uuid4

import httpx
from verify_m95 import _login, upload

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:8000/api/v1"


async def concurrent_traces() -> None:
    async with httpx.AsyncClient(base_url=BASE, trust_env=False) as client:

        async def request() -> None:
            trace_id = uuid4().hex
            response = await client.get(
                "/version",
                headers={
                    "traceparent": f"00-{trace_id}-{uuid4().hex[:16]}-01",
                },
            )
            assert response.status_code == 200 and response.headers["x-trace-id"] == trace_id

        await asyncio.gather(*(request() for _ in range(24)))


def main() -> None:
    sid = json.loads((ROOT / ".nexweave-data/stage-a-r1.json").read_text())["space_id"]
    with httpx.Client(
        base_url=BASE,
        timeout=120,
        trust_env=False,
        limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
    ) as client:
        api = _login(client, "local-admin")
        content = b"timestamp,value\n" + b"2026-09-01T00:00:00Z,70\n" * 12000
        source = upload(api, sid, "stage-a-synthetic-direct-trace.csv", "text/csv", content)
        for _ in range(12):
            api.request("GET", "/version")
    asyncio.run(concurrent_traces())
    result = {
        "direct_http_keepalive": True,
        "upload_bytes": len(content),
        "source_version_id": source,
        "sequential_after_upload": 12,
        "concurrent_requests": 24,
        "trace_mismatches": 0,
        "data_kind": "SYNTHETIC",
    }
    (ROOT / ".nexweave-data/stage-a-trace.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))


if __name__ == "__main__":
    main()
