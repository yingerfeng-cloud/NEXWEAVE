"""Exercise the real M5 API→Temporal→Model Gateway→knowledge/Wiki chain."""

from __future__ import annotations

import argparse
import hashlib
import time
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx

TERMINAL_PARSE = {"SUCCEEDED", "PARTIAL_FAILED", "FAILED", "CANCELED"}
TERMINAL_COMPILE = {"SUCCEEDED", "PARTIAL_FAILED", "FAILED", "CANCELED"}


def _sha(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


@dataclass
class Api:
    client: httpx.Client
    token: str

    def request(
        self,
        method: str,
        path: str,
        *,
        expected: int = 200,
        idempotency_key: str | None = None,
        version: int | None = None,
        extra_headers: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        trace_id, span_id = uuid4().hex, uuid4().hex[:16]
        headers = {
            "Authorization": f"Bearer {self.token}",
            "traceparent": f"00-{trace_id}-{span_id}-01",
        }
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        if version is not None:
            headers["If-Match"] = f'"v{version}"'
        headers.update(extra_headers or {})
        response = self.client.request(method, path, headers=headers, **kwargs)
        if response.status_code != expected:
            raise RuntimeError(
                f"{method} {path} returned {response.status_code}, expected {expected}: "
                f"{response.text[:600]}"
            )
        if response.headers.get("X-Trace-Id") != trace_id:
            raise RuntimeError(f"{method} {path} did not preserve W3C trace context")
        return response

    def wait(self, path: str, terminal: set[str], timeout: float = 90) -> dict[str, Any]:
        deadline = time.monotonic() + timeout
        latest: dict[str, Any] = {}
        while time.monotonic() < deadline:
            latest = self.request("GET", path).json()
            if latest["status"] in terminal:
                return latest
            time.sleep(0.25)
        raise RuntimeError(f"Resource did not reach a terminal state: {latest}")


def _login(client: httpx.Client, subject: str) -> Api:
    response = client.post("/auth/dev/session", json={"subject": subject})
    response.raise_for_status()
    return Api(client, str(response.json()["access_token"]))


def _create_source(api: Api, space_id: str, suffix: str, *, state: str = "operational") -> str:
    content = (
        f"Pump A is the primary synthetic cooling pump. State: {state}.\n\n"
        "Pump B is the synthetic standby cooling pump."
    ).encode()
    checksum = _sha(content)
    session = api.request(
        "POST",
        f"/spaces/{space_id}/sources/uploads",
        expected=201,
        idempotency_key=f"m5-upload-{suffix}",
        json={
            "filename": "m5-synthetic.txt",
            "content_type": "text/plain",
            "expected_size": len(content),
            "expected_checksum": checksum,
            "display_name": "M5 synthetic cooling pumps",
            "description": "Synthetic, non-customer M5 verification fixture",
            "classification": "INTERNAL",
            "tags": ["synthetic", "m5-e2e"],
        },
    ).json()
    api.request(
        "PUT",
        f"/sources/uploads/{session['id']}/content",
        extra_headers={"Content-Type": "text/plain"},
        content=content,
    )
    completed = api.request(
        "POST",
        f"/sources/uploads/{session['id']}/complete",
        expected=202,
        idempotency_key=f"m5-complete-{suffix}",
        json={"checksum": checksum, "size": len(content)},
    ).json()
    parsed = api.wait(f"/parse-jobs/{completed['parse_job_id']}", TERMINAL_PARSE)
    if parsed["status"] != "SUCCEEDED":
        raise RuntimeError(f"Synthetic M5 source did not parse: {parsed}")
    return str(completed["source_version_id"])


def _create_published_schema(
    admin: Api, client: httpx.Client, space: dict[str, Any], suffix: str
) -> dict[str, Any]:
    namespace = f"m5-{suffix}.example"
    created = admin.request(
        "POST",
        f"/spaces/{space['id']}/schemas",
        expected=201,
        idempotency_key=f"m5-schema-{suffix}",
        json={
            "schema_key": f"{namespace}/knowledge",
            "display_name": "M5 synthetic compile schema",
            "semantic_version": "0.1.0",
            "snapshot": {
                "types": [
                    {
                        "key": f"{namespace}/equipment",
                        "displayName": "Equipment",
                        "abstract": False,
                    }
                ],
                "properties": [
                    {
                        "key": f"{namespace}/description",
                        "typeKey": f"{namespace}/equipment",
                        "dataType": "STRING",
                        "mergeStrategy": "MANUAL",
                    }
                ],
                "terms": [
                    {
                        "targetKey": f"{namespace}/equipment",
                        "language": "en",
                        "term": "Pump",
                        "kind": "PREFERRED",
                    }
                ],
                "relations": [
                    {
                        "key": f"{namespace}/backs-up",
                        "domain": f"{namespace}/equipment",
                        "range": f"{namespace}/equipment",
                        "direction": "DIRECTED",
                        "evidenceRequired": True,
                    }
                ],
            },
        },
    ).json()
    report = admin.request(
        "POST",
        f"/schemas/{created['schema_definition_id']}/versions/0.1.0/validate",
    ).json()
    if report["report"]["compatible"] is not True:
        raise RuntimeError(f"Synthetic M5 schema did not validate: {report}")
    validated = admin.request(
        "GET", f"/schemas/{created['schema_definition_id']}/versions/0.1.0"
    ).json()
    subject = f"m5-publisher-{suffix}"
    publisher = admin.request(
        "POST",
        "/users",
        idempotency_key=f"m5-publisher-user-{suffix}",
        json={
            "issuer": "https://identity.nexweave.local/dev",
            "subject": subject,
            "display_name": "M5 independent publisher",
            "clearance": "INTERNAL",
            "tenant_roles": [],
        },
    ).json()
    admin.request(
        "PUT",
        f"/spaces/{space['id']}/members/{publisher['id']}",
        idempotency_key=f"m5-publisher-member-{suffix}",
        json={"subject_type": "USER", "roles": ["publisher"], "clearance": "INTERNAL"},
    )
    published = (
        _login(client, subject)
        .request(
            "POST",
            f"/schemas/{created['schema_definition_id']}/versions/0.1.0/publish",
            idempotency_key=f"m5-publish-{suffix}",
            version=int(validated["version"]),
        )
        .json()
    )
    if published["status"] != "PUBLISHED":
        raise RuntimeError("SchemaVersion did not reach PUBLISHED")
    return published


def _compile(
    api: Api,
    *,
    space_id: str,
    schema_id: str,
    source_id: str,
    prompt_id: str,
    profile_id: str,
    suffix: str,
    mode: str,
) -> dict[str, Any]:
    job = api.request(
        "POST",
        f"/spaces/{space_id}/compile-jobs",
        expected=202,
        idempotency_key=f"m5-compile-{mode.lower()}-{suffix}",
        json={
            "schema_version_id": schema_id,
            "source_version_ids": [source_id],
            "prompt_version_id": prompt_id,
            "model_profile_id": profile_id,
            "mode": mode,
            "scope": {"fixture": "synthetic-m5"},
        },
    ).json()
    completed = api.wait(f"/compile-jobs/{job['id']}", TERMINAL_COMPILE)
    if completed["status"] != "SUCCEEDED":
        raise RuntimeError(f"CompileJob did not succeed: {completed}")
    return completed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api/v1")
    args = parser.parse_args()
    suffix = uuid4().hex[:10]
    with httpx.Client(base_url=args.base_url, timeout=120) as client:
        admin = _login(client, "local-admin")
        version = admin.request("GET", "/version").json()
        if version["milestone"] not in {"M5", "M6"}:
            raise RuntimeError(f"Expected M5 service, got {version}")
        organization = admin.request("GET", "/organizations").json()["items"][0]
        space = admin.request(
            "POST",
            "/spaces",
            expected=201,
            idempotency_key=f"m5-space-{suffix}",
            json={
                "organization_id": organization["id"],
                "slug": f"m5-e2e-{suffix}",
                "display_name": f"M5 E2E {suffix}",
                "description": "Synthetic M5 verification space",
                "default_classification": "INTERNAL",
            },
        ).json()
        source_id = _create_source(admin, str(space["id"]), suffix)
        schema = _create_published_schema(admin, client, space, suffix)
        prompt = admin.request(
            "POST",
            "/prompt-versions",
            idempotency_key=f"m5-prompt-{suffix}",
            json={
                "space_id": space["id"],
                "prompt_key": f"m5.synthetic.{suffix}",
                "content": "Extract governed entities and claims using only the supplied schema.",
                "output_contract": {"kind": "nexweave.structured-compile/v1"},
            },
        ).json()
        profile = admin.request(
            "POST",
            "/model-profiles",
            idempotency_key=f"m5-model-{suffix}",
            json={
                "space_id": space["id"],
                "name": f"M5 local structured provider {suffix}",
                "provider": "nexweave.local",
                "model_name": "structured-compile-v1",
                "externally_hosted": False,
                "maximum_classification": "INTERNAL",
                "config": {"max_input_units": 200000},
            },
        ).json()
        first = _compile(
            admin,
            space_id=str(space["id"]),
            schema_id=str(schema["id"]),
            source_id=source_id,
            prompt_id=str(prompt["id"]),
            profile_id=str(profile["id"]),
            suffix=suffix,
            mode="FULL",
        )
        if not first["result_summary"].get("page_ids"):
            raise RuntimeError("CompileJob did not materialize Wiki drafts")
        entities_before = admin.request("GET", f"/spaces/{space['id']}/entities").json()["items"]
        pages = admin.request("GET", f"/spaces/{space['id']}/wiki/pages").json()["items"]
        page = admin.request("GET", f"/wiki/pages/{pages[0]['id']}").json()
        if not page["outbound_links"]:
            raise RuntimeError("Schema relation did not create a governed Wiki link")
        first_version_id = str(page["current_version_id"])
        page = admin.request(
            "PATCH",
            f"/wiki/pages/{page['id']}/drafts/{first_version_id}",
            idempotency_key=f"m5-wiki-edit-{suffix}",
            version=int(page["version"]),
            json={
                "protected_sections": {"operator-notes": "Human-authored synthetic note."},
                "properties": page["current_version"]["properties"],
                "reason": "Verify protected section preservation",
            },
        ).json()
        edited_version_id = str(page["current_version_id"])
        admin.request(
            "POST",
            f"/wiki/pages/{page['id']}/comments",
            expected=201,
            json={"body": "Synthetic M5 review comment"},
        )
        admin.request("PUT", f"/wiki/pages/{page['id']}/follow")
        second = _compile(
            admin,
            space_id=str(space["id"]),
            schema_id=str(schema["id"]),
            source_id=source_id,
            prompt_id=str(prompt["id"]),
            profile_id=str(profile["id"]),
            suffix=f"{suffix}-recompile",
            mode="RECOMPILE",
        )
        entities_after = admin.request("GET", f"/spaces/{space['id']}/entities").json()["items"]
        recompiled = admin.request("GET", f"/wiki/pages/{page['id']}").json()
        if {item["id"] for item in entities_before} != {item["id"] for item in entities_after}:
            raise RuntimeError("Recompile changed stable entity identities")
        if recompiled["current_version"]["protected_sections"].get("operator-notes") != (
            "Human-authored synthetic note."
        ):
            raise RuntimeError("Recompile overwrote a human protected section")
        versions = admin.request("GET", f"/wiki/pages/{page['id']}/versions").json()["items"]
        if len(versions) < 2:
            raise RuntimeError("Wiki append-only version history is incomplete")
        if second["result_summary"]["stats"]["page_versions_created"] != 0:
            raise RuntimeError("Idempotent recompile created a duplicate Wiki page version")
        admin.request(
            "GET",
            f"/wiki/pages/{page['id']}/diff",
            params={
                "from_version_id": first_version_id,
                "to_version_id": edited_version_id,
            },
        )
        consumer_subject = f"m5-consumer-{suffix}"
        consumer = admin.request(
            "POST",
            "/users",
            idempotency_key=f"m5-consumer-user-{suffix}",
            json={
                "issuer": "https://identity.nexweave.local/dev",
                "subject": consumer_subject,
                "display_name": "M5 draft-denied consumer",
                "clearance": "INTERNAL",
                "tenant_roles": [],
            },
        ).json()
        admin.request(
            "PUT",
            f"/spaces/{space['id']}/members/{consumer['id']}",
            idempotency_key=f"m5-consumer-member-{suffix}",
            json={"subject_type": "USER", "roles": ["consumer"], "clearance": "INTERNAL"},
        )
        _login(client, consumer_subject).request("GET", f"/wiki/pages/{page['id']}", expected=403)
        audits = admin.request("GET", "/audit-logs?limit=100").json()["items"]
        if not any(
            item["resource_id"] == first["id"]
            and item["action"] == "compile.execute"
            and item["outcome"] == "SUCCEEDED"
            for item in audits
        ):
            raise RuntimeError("Compile success audit evidence is missing")
        if second["result_summary"]["stats"]["evidence_candidates"] < 1:
            raise RuntimeError("Compile output has no SourceAnchor-backed EvidenceCandidate")
        changed_source_id = _create_source(
            admin, str(space["id"]), f"{suffix}-changed", state="failed"
        )
        conflict_compile = _compile(
            admin,
            space_id=str(space["id"]),
            schema_id=str(schema["id"]),
            source_id=changed_source_id,
            prompt_id=str(prompt["id"]),
            profile_id=str(profile["id"]),
            suffix=f"{suffix}-conflict",
            mode="SOURCE_SCOPED",
        )
        if conflict_compile["result_summary"]["stats"]["conflicts"] < 1:
            raise RuntimeError("Changed source did not produce a ConflictCandidate")

    print(
        "M5 real chain verified: fixed published inputs, local Model Gateway invocation, stable "
        "entities, relations, claims, SourceAnchor-backed candidates, ConflictCandidate, governed "
        "Wiki links, append-only versions/protected sections, "
        "comments/follow, audit, trace context and consumer draft denial."
    )
    print(
        "No external LLM was called: nexweave.local is a deterministic no-network M5 provider; "
        "external provider adapters, review, release and query remain outside this verification."
    )


if __name__ == "__main__":
    main()
