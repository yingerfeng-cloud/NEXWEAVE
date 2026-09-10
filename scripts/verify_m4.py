"""Exercise the real M4 API→PostgreSQL→Temporal→Pack→Schema chain."""

from __future__ import annotations

import base64
import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "domain" / "src"))

from nexweave_domain import canonical_json, pack_descriptor, sha256_checksum  # noqa: E402

FIXTURES = ROOT / "domain-packs" / "fixtures"
BASE_URL = "http://127.0.0.1:8080/api/v1"
TERMINAL_INSTALLATION = {"ACTIVE", "FAILED", "DISABLED", "ROLLED_BACK"}
FIXTURE_KEYS = {
    "core-pack": ("nexweave.io", 0),
    "equipment-rca-pack": ("industry.example", 1),
    "maintenance-pack": ("maintenance.example", 2),
}


def _private_key(last_byte: int) -> Ed25519PrivateKey:
    seed = bytearray(
        bytes.fromhex("4e455857454156452d4d342d464958545552452d4b45592d4f4e4c5921000000")
    )
    seed[-1] = last_byte
    return Ed25519PrivateKey.from_private_bytes(bytes(seed))


class Api:
    def __init__(self, client: httpx.Client, token: str) -> None:
        self.client = client
        self.token = token

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: int = 200,
        idempotency_key: str | None = None,
        version: int | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        trace_id = uuid4().hex
        headers = {
            "Authorization": f"Bearer {self.token}",
            "traceparent": f"00-{trace_id}-{uuid4().hex[:16]}-01",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if version is not None:
            headers["If-Match"] = f'"v{version}"'
        response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(
                f"{method} {path} returned {response.status_code}, expected {expected}: "
                f"{response.text[:500]}"
            )
        if response.headers.get("X-Trace-Id") != trace_id:
            raise RuntimeError(f"{method} {path} did not preserve W3C trace context")
        return response

    def wait_installation(self, installation_id: str, timeout: float = 60) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        latest: dict[str, Any] = {}
        while time.monotonic() < deadline:
            latest = self.request("GET", f"/domain-pack-installations/{installation_id}").json()
            if latest["status"] in TERMINAL_INSTALLATION:
                if latest["status"] == "FAILED":
                    raise RuntimeError(f"Pack installation failed: {latest}")
                return latest
            time.sleep(0.25)
        raise RuntimeError(f"Pack installation did not finish: {latest}")


def _login(client: httpx.Client, subject: str) -> tuple[str, dict[str, Any]]:
    response = client.post("/auth/dev/session", json={"subject": subject})
    response.raise_for_status()
    return str(response.json()["access_token"]), dict(response.json()["principal"])


def _register_fixture(api: Api, pack_id: str, suffix: str) -> dict[str, Any]:
    for existing in api.request("GET", "/domain-packs").json()["items"]:
        if existing["pack_key"] == pack_id and existing["pack_version"] == "1.0.0":
            return dict(existing)
    if pack_id == "maintenance-pack":
        return _register_dynamic_maintenance(api, suffix, "runtime")
    namespace, last_byte = FIXTURE_KEYS[pack_id]
    private_key = _private_key(last_byte)
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    api.request(
        "POST",
        "/domain-pack-trust-keys",
        expected=201,
        idempotency_key=f"m4-trust-{suffix}-{pack_id}",
        json={
            "key_id": f"m4-fixture-{pack_id}",
            "key_namespace": namespace,
            "public_key_base64url": base64.urlsafe_b64encode(public_key).decode().rstrip("="),
            "valid_from": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
            "valid_until": None,
        },
    )
    manifest = json.loads((FIXTURES / pack_id / "manifest.json").read_text(encoding="utf-8"))
    content = json.loads((FIXTURES / pack_id / "semantic.json").read_text(encoding="utf-8"))
    return dict(
        api.request(
            "POST",
            "/domain-packs",
            expected=201,
            idempotency_key=f"m4-pack-{suffix}-{pack_id}",
            json={"manifest": manifest, "contents": {"semantic.json": content}},
        ).json()
    )


def _register_dynamic_maintenance(api: Api, suffix: str, label: str) -> dict[str, Any]:
    key_id = f"m4-{label}-{suffix}-maintenance"
    pack_key = f"maintenance-{label}-{suffix}-pack"
    private_key = _private_key(2)
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    api.request(
        "POST",
        "/domain-pack-trust-keys",
        expected=201,
        idempotency_key=f"m4-{label}-trust-{suffix}",
        json={
            "key_id": key_id,
            "key_namespace": "maintenance.example",
            "public_key_base64url": base64.urlsafe_b64encode(public_key).decode().rstrip("="),
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_until": None,
        },
    )
    manifest = json.loads(
        (FIXTURES / "maintenance-pack" / "manifest.json").read_text(encoding="utf-8")
    )
    content = json.loads(
        (FIXTURES / "maintenance-pack" / "semantic.json").read_text(encoding="utf-8")
    )
    manifest["metadata"]["id"] = pack_key
    manifest["security"]["signature"] = {
        "algorithm": "Ed25519",
        "keyId": key_id,
        "value": "",
    }
    manifest["security"]["signature"]["value"] = (
        base64.urlsafe_b64encode(private_key.sign(pack_descriptor(manifest))).decode().rstrip("=")
    )
    return dict(
        api.request(
            "POST",
            "/domain-packs",
            expected=201,
            idempotency_key=f"m4-{label}-pack-{suffix}",
            json={"manifest": manifest, "contents": {"semantic.json": content}},
        ).json()
    )


def _register_upgrade(api: Api, suffix: str) -> dict[str, Any]:
    for existing in api.request("GET", "/domain-packs").json()["items"]:
        if existing["pack_key"] == "equipment-rca-pack" and existing["pack_version"] == "1.1.0":
            return dict(existing)
    manifest = json.loads(
        (FIXTURES / "equipment-rca-pack" / "manifest.json").read_text(encoding="utf-8")
    )
    content = json.loads(
        (FIXTURES / "equipment-rca-pack" / "semantic.json").read_text(encoding="utf-8")
    )
    manifest["metadata"]["version"] = "1.1.0"
    manifest["security"]["signature"]["value"] = ""
    signature = _private_key(1).sign(pack_descriptor(manifest))
    manifest["security"]["signature"]["value"] = (
        base64.urlsafe_b64encode(signature).decode().rstrip("=")
    )
    return dict(
        api.request(
            "POST",
            "/domain-packs",
            expected=201,
            idempotency_key=f"m4-pack-{suffix}-equipment-upgrade",
            json={"manifest": manifest, "contents": {"semantic.json": content}},
        ).json()
    )


def _import_revocation(api: Api, target: dict[str, Any], suffix: str) -> None:
    document: dict[str, Any] = {
        "apiVersion": "nexweave.io/pack-revocation/v1alpha1",
        "kind": "NexweavePackRevocationList",
        "canonicalizationAlgorithm": "RFC8785-JCS/1",
        "revoked": [
            {
                "keyId": None,
                "packId": target["pack_key"],
                "version": target["pack_version"],
                "contentChecksum": target["content_checksum"],
                "reasonCode": "M4_SYNTHETIC_REVOCATION",
                "revokedAt": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            }
        ],
        "security": {
            "executableContent": False,
            "signature": {
                "algorithm": "Ed25519",
                "keyId": "m4-fixture-core-pack",
                "value": "",
            },
        },
    }
    signature = _private_key(0).sign(pack_descriptor(document))
    document["security"]["signature"]["value"] = (
        base64.urlsafe_b64encode(signature).decode().rstrip("=")
    )
    api.request(
        "POST",
        "/domain-pack-revocations/import",
        expected=202,
        idempotency_key=f"m4-revocation-{suffix}",
        json=document,
    )


def _verify_failure_audit(api: Api, organization_id: str, suffix: str) -> None:
    namespace = f"failure-{suffix}.example"
    pack_key = f"failure-{suffix}-pack"
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    space = api.request(
        "POST",
        "/spaces",
        expected=201,
        idempotency_key=f"m4-failure-space-{suffix}",
        json={
            "organization_id": organization_id,
            "slug": f"m4-failure-{suffix}",
            "display_name": f"M4 failure audit {suffix}",
            "description": "Synthetic dependency failure verification",
            "default_classification": "INTERNAL",
        },
    ).json()
    schema = api.request(
        "POST",
        f"/spaces/{space['id']}/schemas",
        expected=201,
        idempotency_key=f"m4-failure-schema-{suffix}",
        json={
            "schema_key": f"{namespace}/schema",
            "display_name": "M4 failure schema",
            "semantic_version": "0.1.0",
            "snapshot": {},
        },
    ).json()
    api.request(
        "POST",
        "/domain-pack-trust-keys",
        expected=201,
        idempotency_key=f"m4-failure-trust-{suffix}",
        json={
            "key_id": f"m4-failure-{suffix}",
            "key_namespace": namespace,
            "public_key_base64url": base64.urlsafe_b64encode(public_key).decode().rstrip("="),
            "valid_from": "2026-01-01T00:00:00Z",
            "valid_until": None,
        },
    )
    declaration = {"types": [{"key": f"{namespace}/item", "displayName": "Item"}]}
    declaration_bytes = canonical_json(declaration)
    manifest: dict[str, Any] = {
        "apiVersion": "nexweave.io/domain-pack/v1alpha1",
        "kind": "NexweaveDomainPack",
        "canonicalizationAlgorithm": "RFC8785-JCS/1",
        "metadata": {
            "id": pack_key,
            "version": "1.0.0",
            "publisher": "M4 failure fixture",
            "keyNamespace": namespace,
            "description": "Dependency failure fixture",
        },
        "compatibility": {
            "platform": ">=1.0.0 <2.0.0",
            "semanticContract": ">=1.0.0 <2.0.0",
            "dependencies": [{"id": f"absent-{suffix}-pack", "versionRange": ">=1.0.0 <2.0.0"}],
        },
        "content": {
            "semantic": {"path": "semantic.json", "sha256": sha256_checksum(declaration_bytes)}
        },
        "security": {
            "executableContent": False,
            "signature": {
                "algorithm": "Ed25519",
                "keyId": f"m4-failure-{suffix}",
                "value": "",
            },
        },
    }
    manifest["security"]["signature"]["value"] = (
        base64.urlsafe_b64encode(private_key.sign(pack_descriptor(manifest))).decode().rstrip("=")
    )
    pack = api.request(
        "POST",
        "/domain-packs",
        expected=201,
        idempotency_key=f"m4-failure-pack-{suffix}",
        json={"manifest": manifest, "contents": {"semantic.json": declaration}},
    ).json()
    installation = api.request(
        "POST",
        f"/spaces/{space['id']}/domain-pack-installations",
        expected=202,
        idempotency_key=f"m4-failure-install-{suffix}",
        json={
            "domain_pack_version_id": pack["id"],
            "schema_definition_id": schema["schema_definition_id"],
            "semantic_version": "0.2.0",
        },
    ).json()
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        installation = api.request("GET", f"/domain-pack-installations/{installation['id']}").json()
        if installation["status"] == "FAILED":
            break
        time.sleep(0.25)
    if installation["status"] != "FAILED":
        raise RuntimeError(f"Dependency failure did not reach FAILED: {installation}")
    audits = api.request("GET", "/audit-logs?limit=100").json()["items"]
    if not any(
        item["resource_id"] == installation["id"]
        and item["outcome"] == "FAILED"
        and item["metadata"].get("error_code") == "PACK_DEPENDENCY_CONFLICT"
        for item in audits
    ):
        raise RuntimeError("Pack dependency failure was not captured by sanitized audit evidence")


def main(*, failure_only: bool = False) -> None:
    suffix = uuid4().hex[:10]
    with httpx.Client(base_url=BASE_URL, timeout=120) as client:
        admin_token, _ = _login(client, "local-admin")
        admin = Api(client, admin_token)
        organization = admin.request("GET", "/organizations").json()["items"][0]
        _verify_failure_audit(admin, str(organization["id"]), suffix)
        if failure_only:
            print("M4 failure path verified: dependency rejection, FAILED projection and audit.")
            return
        space = admin.request(
            "POST",
            "/spaces",
            expected=201,
            idempotency_key=f"m4-space-{suffix}",
            json={
                "organization_id": organization["id"],
                "slug": f"m4-e2e-{suffix}",
                "display_name": f"M4 E2E {suffix}",
                "description": "Synthetic M4 verification space",
                "default_classification": "INTERNAL",
            },
        ).json()
        schema = admin.request(
            "POST",
            f"/spaces/{space['id']}/schemas",
            expected=201,
            idempotency_key=f"m4-schema-{suffix}",
            json={
                "schema_key": f"test.{suffix}.nexweave.io/schema",
                "display_name": "M4 synthetic schema",
                "semantic_version": "0.1.0",
                "snapshot": {},
            },
        ).json()
        core = _register_fixture(admin, "core-pack", suffix)
        equipment = _register_fixture(admin, "equipment-rca-pack", suffix)
        maintenance = _register_fixture(admin, "maintenance-pack", suffix)
        if not core["content_checksum"].startswith("sha256:"):
            raise RuntimeError("Core Pack checksum was not persisted")

        tampered = json.loads(
            (FIXTURES / "maintenance-pack" / "semantic.json").read_text(encoding="utf-8")
        )
        tampered["types"][0]["displayName"] = "Tampered"
        manifest = json.loads(
            (FIXTURES / "maintenance-pack" / "manifest.json").read_text(encoding="utf-8")
        )
        admin.request(
            "POST",
            "/domain-packs",
            expected=403,
            idempotency_key=f"m4-tamper-{suffix}",
            json={"manifest": manifest, "contents": {"semantic.json": tampered}},
        )

        first = admin.request(
            "POST",
            f"/spaces/{space['id']}/domain-pack-installations",
            expected=202,
            idempotency_key=f"m4-install-equipment-{suffix}",
            json={
                "domain_pack_version_id": equipment["id"],
                "schema_definition_id": schema["schema_definition_id"],
                "semantic_version": "0.2.0",
                "operation": "INSTALL",
            },
        ).json()
        first = admin.wait_installation(first["id"])
        candidate = admin.request(
            "GET",
            f"/schemas/{schema['schema_definition_id']}/versions/0.2.0/semantic-model",
        ).json()
        type_keys = {item["key"] for item in candidate["normalized_snapshot"]["types"]}
        if type_keys != {"nexweave.io/equipment", "industry.example/failure"}:
            raise RuntimeError(f"Equipment Pack composition is incomplete: {sorted(type_keys)}")
        if candidate["status"] != "DRAFT":
            raise RuntimeError("Pack installation implicitly published a SchemaVersion")

        report = admin.request(
            "POST",
            f"/schemas/{schema['schema_definition_id']}/versions/0.2.0/validate",
        ).json()
        candidate = admin.request(
            "GET", f"/schemas/{schema['schema_definition_id']}/versions/0.2.0"
        ).json()
        publisher_subject = f"m4-publisher-{suffix}"
        publisher_user = admin.request(
            "POST",
            "/users",
            idempotency_key=f"m4-publisher-user-{suffix}",
            json={
                "issuer": "https://identity.nexweave.local/dev",
                "subject": publisher_subject,
                "display_name": "M4 independent publisher",
                "clearance": "INTERNAL",
                "tenant_roles": [],
            },
        ).json()
        admin.request(
            "PUT",
            f"/spaces/{space['id']}/members/{publisher_user['id']}",
            idempotency_key=f"m4-publisher-member-{suffix}",
            json={"subject_type": "USER", "roles": ["publisher"], "clearance": "INTERNAL"},
        )
        publisher_token, _ = _login(client, publisher_subject)
        publisher = Api(client, publisher_token)
        published = publisher.request(
            "POST",
            f"/schemas/{schema['schema_definition_id']}/versions/0.2.0/publish",
            idempotency_key=f"m4-publish-{suffix}",
            version=candidate["version"],
        ).json()
        if published["status"] != "PUBLISHED" or report["report"]["compatible"] is not True:
            raise RuntimeError("Independent Schema validation/publication failed")

        second = admin.request(
            "POST",
            f"/spaces/{space['id']}/domain-pack-installations",
            expected=202,
            idempotency_key=f"m4-install-maintenance-{suffix}",
            json={
                "domain_pack_version_id": maintenance["id"],
                "schema_definition_id": schema["schema_definition_id"],
                "semantic_version": "0.3.0",
            },
        ).json()
        second = admin.wait_installation(second["id"])
        upgrade_pack = _register_upgrade(admin, suffix)
        upgrade = admin.request(
            "POST",
            f"/spaces/{space['id']}/domain-pack-installations",
            expected=202,
            idempotency_key=f"m4-upgrade-{suffix}",
            json={
                "domain_pack_version_id": upgrade_pack["id"],
                "schema_definition_id": schema["schema_definition_id"],
                "semantic_version": "0.4.0",
                "operation": "UPGRADE",
                "previous_installation_id": first["id"],
            },
        ).json()
        upgrade = admin.wait_installation(upgrade["id"])
        disabled = admin.request(
            "POST",
            f"/spaces/{space['id']}/domain-pack-installations/{second['id']}/disable",
            expected=202,
            idempotency_key=f"m4-disable-{suffix}",
        ).json()
        disabled = admin.wait_installation(disabled["id"])
        rolled_back = admin.request(
            "POST",
            f"/spaces/{space['id']}/domain-pack-installations/rollback",
            expected=202,
            idempotency_key=f"m4-rollback-{suffix}",
            json={"target_installation_id": first["id"]},
        ).json()
        rolled_back = admin.wait_installation(rolled_back["id"])
        if disabled["status"] != "DISABLED" or rolled_back["status"] != "ROLLED_BACK":
            raise RuntimeError("Disable/rollback did not preserve explicit historical states")

        revocation_target = _register_dynamic_maintenance(admin, suffix, "revoke")
        _import_revocation(admin, revocation_target, suffix)
        available_ids = {
            item["id"] for item in admin.request("GET", "/domain-packs").json()["items"]
        }
        if revocation_target["id"] in available_ids:
            raise RuntimeError("Revoked PackVersion remained installable")
        other_space = admin.request(
            "POST",
            "/spaces",
            expected=201,
            idempotency_key=f"m4-other-space-{suffix}",
            json={
                "organization_id": organization["id"],
                "slug": f"m4-other-{suffix}",
                "display_name": f"M4 isolation {suffix}",
                "description": "Synthetic cross-space isolation target",
                "default_classification": "INTERNAL",
            },
        ).json()
        admin.request(
            "POST",
            f"/spaces/{other_space['id']}/domain-pack-installations",
            expected=404,
            idempotency_key=f"m4-cross-space-{suffix}",
            json={
                "domain_pack_version_id": equipment["id"],
                "schema_definition_id": schema["schema_definition_id"],
                "semantic_version": "0.5.0",
            },
        )

    print(
        "M4 real chain verified: signed registry, dependency composition, deterministic candidate, "
        "separate validation/publication, upgrade, disable, rollback, revocation and isolation."
    )


if __name__ == "__main__":
    main(failure_only="--failure-only" in sys.argv[1:])
