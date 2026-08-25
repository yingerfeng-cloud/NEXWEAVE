"""Verify the real M1 Web/API/PostgreSQL/RustFS/Temporal vertical chain."""

from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any
from uuid import uuid4

import boto3
import httpx
from botocore.client import Config
from botocore.exceptions import ClientError

ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "http://localhost:8080"
M1_COMPATIBLE_MILESTONES = {"M1", "M2"}


def environment() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


def docker(*arguments: str, capture: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603,S607 - fixed Docker CLI verification entrypoint
        ["docker", "compose", *arguments],  # noqa: S607
        cwd=ROOT,
        check=True,
        capture_output=capture,
        text=True,
    )


def psql(statement: str, *, expect_failure: bool = False) -> str:
    env = environment()
    result = subprocess.run(  # noqa: S603,S607 - fixed Docker CLI verification entrypoint
        [  # noqa: S607
            "docker",
            "compose",
            "exec",
            "-T",
            "postgres",
            "psql",
            "-U",
            env["NEXWEAVE_POSTGRES_USER"],
            "-d",
            env["NEXWEAVE_POSTGRES_DB"],
            "-At",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            statement,
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if expect_failure:
        if result.returncode == 0:
            raise RuntimeError("The append-only audit mutation unexpectedly succeeded")
        return ""
    if result.returncode != 0:
        raise RuntimeError("A PostgreSQL verification query failed")
    return result.stdout.strip()


def request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    token: str | None = None,
    expected: int = 200,
    headers: dict[str, str] | None = None,
    **kwargs: Any,
) -> httpx.Response:
    request_headers = dict(headers or {})
    if token:
        request_headers["Authorization"] = f"Bearer {token}"
    trace_id, span_id = uuid4().hex, uuid4().hex[:16]
    request_headers["traceparent"] = f"00-{trace_id}-{span_id}-01"
    response = client.request(method, path, headers=request_headers, **kwargs)
    if response.status_code != expected:
        raise RuntimeError(
            f"{method} {path} returned {response.status_code}, expected {expected}: "
            f"{response.text[:300]}"
        )
    if response.headers.get("X-Trace-Id") != trace_id:
        raise RuntimeError(f"{method} {path} did not preserve W3C trace context")
    return response


def login(client: httpx.Client, subject: str) -> tuple[str, dict[str, object]]:
    response = request(
        client,
        "POST",
        "/api/v1/auth/dev/session",
        expected=200,
        json={"subject": subject},
    )
    body = response.json()
    return str(body["access_token"]), body["principal"]


def create_space(
    client: httpx.Client,
    token: str,
    organization_id: str,
    suffix: str,
    key: str,
) -> tuple[dict[str, object], httpx.Response]:
    response = request(
        client,
        "POST",
        "/api/v1/spaces",
        token=token,
        expected=201,
        headers={"Idempotency-Key": key},
        json={
            "organization_id": organization_id,
            "slug": f"m1-e2e-{suffix}",
            "display_name": f"M1 E2E {suffix}",
            "description": "Real M1 verification space",
            "default_classification": "INTERNAL",
        },
    )
    return response.json(), response


def assert_object_storage_immutable(metadata: dict[str, object], content: bytes) -> None:
    env = environment()
    client = boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id=env["NEXWEAVE_OBJECT_STORE_ACCESS_KEY"],
        aws_secret_access_key=env["NEXWEAVE_OBJECT_STORE_SECRET_KEY"],
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            proxies={},
            s3={"addressing_style": "path"},
        ),
    )
    versioning = client.get_bucket_versioning(Bucket=env["NEXWEAVE_OBJECT_STORE_BUCKET"])
    if versioning.get("Status") != "Enabled":
        raise RuntimeError("RustFS bucket versioning is not enabled")
    try:
        client.put_object(
            Bucket=env["NEXWEAVE_OBJECT_STORE_BUCKET"],
            Key=str(metadata["object_key"]),
            Body=b"different-content",
            ContentType="text/plain",
            IfNoneMatch="*",
        )
    except ClientError as exc:
        if str(exc.response.get("Error", {}).get("Code")) not in {
            "PreconditionFailed",
            "412",
            "ConditionalRequestConflict",
        }:
            raise
    else:
        raise RuntimeError("RustFS allowed an immutable object key to be overwritten")
    if len(content) != int(metadata["size"]):
        raise RuntimeError("Managed object size metadata is incorrect")


def verify_database_head() -> None:
    heads = docker("exec", "-T", "api", "alembic", "heads", capture=True).stdout.split()
    current = docker("exec", "-T", "api", "alembic", "current", capture=True).stdout.split()
    if not heads or heads[0] not in current:
        raise RuntimeError("PostgreSQL is not at the single Alembic head")


def main() -> None:
    suffix = uuid4().hex[:10]
    client = httpx.Client(base_url=BASE_URL, timeout=20)
    try:
        readiness = request(client, "GET", "/api/v1/health/ready").json()
        if readiness.get("status") != "ready" or set(readiness.get("components", {})) != {
            "postgresql",
            "redis",
            "object_storage",
            "temporal",
        }:
            raise RuntimeError("M1 infrastructure readiness is incomplete")
        milestone = request(client, "GET", "/api/v1/version").json().get("milestone")
        if milestone not in M1_COMPATIBLE_MILESTONES:
            raise RuntimeError("The deployed API is not reporting an M1-compatible milestone")
        for route in ("/", "/spaces", "/sources", "/admin"):
            page = client.get(route)
            if page.status_code != 200 or "NEXWEAVE" not in page.text:
                raise RuntimeError(f"Web deep link {route} did not restore the M1 application")

        admin_token, admin = login(client, "local-admin")
        organizations = request(client, "GET", "/api/v1/organizations", token=admin_token).json()[
            "items"
        ]
        organization_id = str(organizations[0]["id"])

        idempotency_key = f"space-{suffix}"
        first_space, create_response = create_space(
            client, admin_token, organization_id, suffix, idempotency_key
        )
        replayed_space, _ = create_space(
            client, admin_token, organization_id, suffix, idempotency_key
        )
        if first_space["id"] != replayed_space["id"]:
            raise RuntimeError("Idempotency replay created a second space")
        request(
            client,
            "POST",
            "/api/v1/spaces",
            token=admin_token,
            expected=409,
            headers={"Idempotency-Key": idempotency_key},
            json={
                "organization_id": organization_id,
                "slug": f"m1-e2e-different-{suffix}",
                "display_name": "Different request",
                "description": "",
                "default_classification": "INTERNAL",
            },
        )

        second_space, _ = create_space(
            client, admin_token, organization_id, f"isolated-{suffix}", f"space-two-{suffix}"
        )
        first_space_id = str(first_space["id"])
        second_space_id = str(second_space["id"])

        updated = request(
            client,
            "PATCH",
            f"/api/v1/spaces/{first_space_id}",
            token=admin_token,
            headers={
                "Idempotency-Key": f"edit-{suffix}",
                "If-Match": '"v1"',
            },
            json={"description": "Updated with optimistic locking"},
        ).json()
        request(
            client,
            "PATCH",
            f"/api/v1/spaces/{first_space_id}",
            token=admin_token,
            expected=412,
            headers={
                "Idempotency-Key": f"stale-{suffix}",
                "If-Match": '"v1"',
            },
            json={"description": "Stale write"},
        )

        guest_subject = f"m1-e2e-user-{suffix}"
        guest = request(
            client,
            "POST",
            "/api/v1/users",
            token=admin_token,
            headers={"Idempotency-Key": f"user-{suffix}"},
            json={
                "issuer": "https://identity.nexweave.local/dev",
                "subject": guest_subject,
                "display_name": "M1 E2E Member",
                "clearance": "CONFIDENTIAL",
                "tenant_roles": [],
            },
        ).json()
        guest_id = str(guest["id"])
        request(
            client,
            "PUT",
            f"/api/v1/spaces/{first_space_id}/members/{guest_id}",
            token=admin_token,
            headers={"Idempotency-Key": f"grant-{suffix}"},
            json={
                "subject_type": "USER",
                "roles": ["consumer"],
                "clearance": "CONFIDENTIAL",
            },
        )
        guest_token, _ = login(client, guest_subject)
        request(client, "GET", f"/api/v1/spaces/{first_space_id}", token=guest_token)
        request(
            client,
            "GET",
            f"/api/v1/spaces/{second_space_id}",
            token=guest_token,
            expected=403,
        )

        request(
            client,
            "DELETE",
            f"/api/v1/spaces/{first_space_id}/members/{guest_id}",
            token=admin_token,
            headers={"Idempotency-Key": f"revoke-{suffix}"},
        )
        request(
            client,
            "GET",
            f"/api/v1/spaces/{first_space_id}",
            token=guest_token,
            expected=403,
        )

        provisioned = docker(
            "exec", "-T", "api", "python", "scripts/provision_m1_e2e_tenant.py", capture=True
        )
        foreign = json.loads(provisioned.stdout.splitlines()[-1])
        foreign_token, foreign_principal = login(client, str(foreign["subject"]))
        if foreign_principal["tenant_id"] == admin["tenant_id"]:
            raise RuntimeError("The cross-tenant test identity was provisioned in the wrong tenant")
        request(
            client,
            "GET",
            f"/api/v1/spaces/{first_space_id}",
            token=foreign_token,
            expected=404,
        )
        foreign_audits = request(
            client, "GET", "/api/v1/audit-logs?limit=100", token=foreign_token
        ).json()["items"]
        if not any(
            item["outcome"] == "DENIED" and item["metadata"].get("reason") == "TENANT_MISMATCH"
            for item in foreign_audits
        ):
            raise RuntimeError("Cross-tenant denial did not leave an audit record")

        content = b"NEXWEAVE M1 immutable managed object"
        upload = request(
            client,
            "POST",
            f"/api/v1/spaces/{first_space_id}/object-uploads",
            token=admin_token,
            expected=201,
            headers={"Idempotency-Key": f"upload-{suffix}"},
            json={
                "filename": "evidence.txt",
                "content_type": "text/plain",
                "expected_size": len(content),
                "classification": "INTERNAL",
            },
        ).json()
        stored = request(
            client,
            "PUT",
            str(upload["upload_url"]),
            token=admin_token,
            headers={"Content-Type": "text/plain"},
            content=content,
        ).json()
        checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
        if stored["checksum"] != checksum or stored["scan_status"] != "CLEAN":
            raise RuntimeError("Managed object checksum or scan result is incorrect")
        metadata = request(
            client, "GET", f"/api/v1/objects/{stored['id']}", token=admin_token
        ).json()
        assert_object_storage_immutable(metadata, content)
        downloaded = request(
            client,
            "GET",
            f"/api/v1/objects/{stored['id']}/content",
            token=admin_token,
        )
        if downloaded.content != content or downloaded.headers["X-Content-Checksum"] != checksum:
            raise RuntimeError("Authorized object download did not preserve bytes and checksum")

        eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE"
        infected_upload = request(
            client,
            "POST",
            f"/api/v1/spaces/{first_space_id}/object-uploads",
            token=admin_token,
            expected=201,
            headers={"Idempotency-Key": f"infected-{suffix}"},
            json={
                "filename": "scan-test.txt",
                "content_type": "text/plain",
                "expected_size": len(eicar),
                "classification": "INTERNAL",
            },
        ).json()
        infected = request(
            client,
            "PUT",
            str(infected_upload["upload_url"]),
            token=admin_token,
            headers={"Content-Type": "text/plain"},
            content=eicar,
        ).json()
        if infected["scan_status"] != "INFECTED":
            raise RuntimeError("The M1 scanner extension point did not preserve INFECTED state")
        request(
            client,
            "GET",
            f"/api/v1/objects/{infected['id']}/content",
            token=admin_token,
            expected=409,
        )

        archived = request(
            client,
            "POST",
            f"/api/v1/spaces/{first_space_id}/archive",
            token=admin_token,
            headers={
                "Idempotency-Key": f"archive-{suffix}",
                "If-Match": f'"v{updated["version"]}"',
            },
        ).json()
        if archived["status"] != "ARCHIVED":
            raise RuntimeError("Knowledge space did not enter the archived state")
        request(
            client,
            "PATCH",
            f"/api/v1/spaces/{first_space_id}",
            token=admin_token,
            expected=403,
            headers={
                "Idempotency-Key": f"post-archive-{suffix}",
                "If-Match": f'"v{archived["version"]}"',
            },
            json={"description": "Must not mutate"},
        )

        audits = request(client, "GET", "/api/v1/audit-logs?limit=100", token=admin_token).json()[
            "items"
        ]
        create_trace_id = create_response.headers["X-Trace-Id"]
        if not any(
            item["resource_id"] == first_space_id
            and item["action"] == "space.create"
            and item["trace_id"] == create_trace_id
            for item in audits
        ):
            raise RuntimeError("Core operation trace_id did not reach the audit record")
        if not any(item["outcome"] == "DENIED" for item in audits):
            raise RuntimeError("Permission denials were not visible to the tenant auditor")

        if (
            int(
                psql(
                    "SELECT count(*) FROM outbox_events "  # noqa: S608 - UUID from trusted API
                    f"WHERE aggregate_id = '{first_space_id}'::uuid "
                    "AND event_type IN ('io.nexweave.space.created.v1', "
                    "'io.nexweave.space.updated.v1', 'io.nexweave.space.archived.v1')"
                )
            )
            < 3
        ):
            raise RuntimeError("Space mutations were not transactionally represented in Outbox")
        psql(
            "UPDATE audit_logs SET outcome = 'FAILED' "
            "WHERE id = (SELECT id FROM audit_logs LIMIT 1)",
            expect_failure=True,
        )

        verify_database_head()
        docker(
            "exec",
            "-T",
            "worker-health",
            "python",
            "-m",
            "nexweave_worker_health.verify",
        )
    finally:
        client.close()

    print(
        "M1 E2E passed: Web deep links -> authenticated API -> tenant/space policy -> "
        "PostgreSQL audit/outbox -> immutable RustFS object -> Temporal worker"
    )


if __name__ == "__main__":
    main()
