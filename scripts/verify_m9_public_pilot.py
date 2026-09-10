"""Run the M9 public-source pilot through Pack→Source→Compile without expert sign-off.

This verification intentionally stops before Review approval, Release and Query. It uses the
deterministic no-network local provider and must not be represented as an RCA expert result.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "domain-packs" / "equipment-rca"
CORE_DIR = ROOT / "domain-packs" / "fixtures" / "core-pack"
SOURCE_DIR = ROOT / ".nexweave-data" / "m9-public-sources"
ACCESSION = ROOT / "docs" / "reference" / "domain" / "rca" / "public-source-accession-manifest.json"
TERMINAL_PARSE = {"SUCCEEDED", "PARTIAL_FAILED", "FAILED", "CANCELED"}
TERMINAL_COMPILE = {"SUCCEEDED", "PARTIAL_FAILED", "FAILED", "CANCELED"}
TERMINAL_INSTALL = {"ACTIVE", "FAILED", "DISABLED", "ROLLED_BACK"}
PILOT_SOURCE_IDS = (
    "NTSB-MIR-22-06",
    "NTSB-AAR-18-01",
    "NTSB-PIR-22-02",
    "NTSB-RIR-24-05",
)


def _sha(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


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
            raise RuntimeError(
                f"{method} {path} returned {response.status_code}, expected {expected}: "
                f"{response.text[:800]}"
            )
        if response.headers.get("X-Trace-Id") != trace_id:
            raise RuntimeError(f"{method} {path} did not preserve W3C trace context")
        return response

    def wait(self, path: str, terminal: set[str], timeout: float = 180) -> dict[str, Any]:
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


def _register_real_pack(admin: Api, suffix: str) -> dict[str, Any] | None:
    existing = [
        item
        for item in admin.request("GET", "/domain-packs").json()["items"]
        if item["pack_key"] == "equipment-rca-pack"
        and item["pack_version"] == "1.0.0"
        and item["key_namespace"] == "equipment.rca"
    ]
    if existing:
        return dict(existing[0])

    trust = json.loads((PACK_DIR / "publisher-public-key.json").read_text(encoding="utf-8"))
    try:
        admin.request(
            "POST",
            "/domain-pack-trust-keys",
            expected=201,
            idempotency_key=f"m9-public-trust-{suffix}",
            json={
                "key_id": trust["keyId"],
                "key_namespace": trust["keyNamespace"],
                "public_key_base64url": trust["publicKeyBase64Url"],
                "valid_from": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
                "valid_until": None,
            },
        )
    except RuntimeError as error:
        if "409" not in str(error):
            raise
    manifest = json.loads((PACK_DIR / "manifest.json").read_text(encoding="utf-8"))
    contents = {
        name: json.loads((PACK_DIR / name).read_text(encoding="utf-8"))
        for name in ("semantic.json", "authoring.json", "evaluation.json")
    }
    try:
        return dict(
            admin.request(
                "POST",
                "/domain-packs",
                expected=201,
                idempotency_key=f"m9-public-pack-{suffix}",
                json={"manifest": manifest, "contents": contents},
            ).json()
        )
    except RuntimeError as error:
        if "PACK_NAMESPACE_CONFLICT" not in str(error):
            raise
        return None


def _direct_composed_snapshot() -> dict[str, Any]:
    """Compose signed source declarations when fixture registry pollution blocks Pack identity."""

    core = json.loads((CORE_DIR / "semantic.json").read_text(encoding="utf-8"))
    rca = json.loads((PACK_DIR / "semantic.json").read_text(encoding="utf-8"))
    keys = (
        "types",
        "properties",
        "hierarchy",
        "relations",
        "terms",
        "mappings",
        "templates",
        "lintRules",
        "evaluationSuites",
        "ui",
    )
    return {key: [*core.get(key, []), *rca.get(key, [])] for key in keys}


def _core_fixture_private_key() -> Ed25519PrivateKey:
    seed = bytearray(
        bytes.fromhex("4e455857454156452d4d342d464958545552452d4b45592d4f4e4c5921000000")
    )
    seed[-1] = 0
    return Ed25519PrivateKey.from_private_bytes(bytes(seed))


def _ensure_core_pack(admin: Api, suffix: str) -> dict[str, Any]:
    existing = [
        item
        for item in admin.request("GET", "/domain-packs").json()["items"]
        if item["pack_key"] == "core-pack" and item["pack_version"] == "1.0.0"
    ]
    if not existing:
        private_key = _core_fixture_private_key()
        public_key = private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        try:
            admin.request(
                "POST",
                "/domain-pack-trust-keys",
                expected=201,
                idempotency_key=f"m9-public-core-trust-{suffix}",
                json={
                    "key_id": "m4-fixture-core-pack",
                    "key_namespace": "nexweave.io",
                    "public_key_base64url": base64.urlsafe_b64encode(public_key)
                    .decode()
                    .rstrip("="),
                    "valid_from": (datetime.now(UTC) - timedelta(minutes=5)).isoformat(),
                    "valid_until": None,
                },
            )
        except RuntimeError as error:
            if "409" not in str(error):
                raise
        manifest = json.loads((CORE_DIR / "manifest.json").read_text(encoding="utf-8"))
        semantic = json.loads((CORE_DIR / "semantic.json").read_text(encoding="utf-8"))
        registered = admin.request(
            "POST",
            "/domain-packs",
            expected=201,
            idempotency_key=f"m9-public-core-pack-{suffix}",
            json={"manifest": manifest, "contents": {"semantic.json": semantic}},
        ).json()
        existing = [registered]
    manifest = json.loads((CORE_DIR / "manifest.json").read_text(encoding="utf-8"))
    if existing[0]["key_namespace"] != manifest["metadata"]["keyNamespace"]:
        raise RuntimeError("Registered core-pack namespace does not match the signed dependency.")
    return dict(existing[0])


def _upload_source(
    admin: Api, *, space_id: str, accession: dict[str, Any], suffix: str
) -> dict[str, Any]:
    source_path = SOURCE_DIR / str(accession["localFile"])
    content = source_path.read_bytes()
    checksum = _sha(content)
    if checksum.removeprefix("sha256:") != accession["sha256"]:
        raise RuntimeError(f"Accession checksum mismatch for {accession['sourceId']}")
    raw_session = admin.request(
        "POST",
        f"/spaces/{space_id}/sources/uploads",
        expected=201,
        idempotency_key=f"m9-public-upload-{suffix}-{accession['sourceId'].lower()}",
        json={
            "filename": accession["localFile"],
            "content_type": "application/pdf",
            "expected_size": len(content),
            "expected_checksum": checksum,
            "display_name": accession["title"],
            "description": (
                "Official NTSB public report; local text-only technical pilot. "
                "Third-party visual elements are excluded from evidence use."
            ),
            "classification": "PUBLIC",
            "tags": ["m9-public-pilot", "ntsb", "text-only", accession["sourceId"].lower()],
        },
    ).json()
    admin.request(
        "PUT",
        f"/sources/uploads/{raw_session['id']}/content",
        extra_headers={"Content-Type": "application/pdf"},
        content=content,
    )
    raw_completed = admin.request(
        "POST",
        f"/sources/uploads/{raw_session['id']}/complete",
        expected=202,
        idempotency_key=f"m9-public-complete-{suffix}-{accession['sourceId'].lower()}",
        json={"checksum": checksum, "size": len(content)},
    ).json()
    raw_parsed = admin.wait(f"/parse-jobs/{raw_completed['parse_job_id']}", TERMINAL_PARSE)
    if raw_parsed["status"] == "SUCCEEDED":
        return {
            "source_id": accession["sourceId"],
            "source_version_id": raw_completed["source_version_id"],
            "parse_job_id": raw_completed["parse_job_id"],
            "checksum": checksum,
            "bytes": len(content),
            "parse_status": raw_parsed["status"],
            "parse_summary": raw_parsed.get("result_summary", {}),
            "raw_preserved": True,
            "text_derivative_used": False,
        }

    reader = PdfReader(BytesIO(content))
    if not reader.is_encrypted:
        raise RuntimeError(
            f"Non-encrypted public source parse failed for {accession['sourceId']}: {raw_parsed}"
        )
    reader.decrypt("")
    excluded = {int(page) for page in accession["parseReview"]["excludedVisualPages"]}
    text_pages = []
    for page_number, page in enumerate(reader.pages, start=1):
        if page_number in excluded:
            continue
        extracted = (page.extract_text() or "").strip()
        if extracted:
            text_pages.append(f"[Source PDF page {page_number}]\n{extracted}")
    derivative = ("\n\n".join(text_pages) + "\n").encode("utf-8")
    derivative_checksum = _sha(derivative)
    derivative_name = str(accession["localFile"]).removesuffix(".pdf") + ".text-only.txt"
    derivative_session = admin.request(
        "POST",
        f"/spaces/{space_id}/sources/uploads",
        expected=201,
        idempotency_key=f"m9-public-derivative-upload-{suffix}-{accession['sourceId'].lower()}",
        json={
            "filename": derivative_name,
            "content_type": "text/plain",
            "expected_size": len(derivative),
            "expected_checksum": derivative_checksum,
            "display_name": f"{accession['title']} — admitted text derivative",
            "description": (
                f"Text-only derivative of SourceVersion {raw_completed['source_version_id']}; "
                "pages containing excluded third-party visual elements were omitted."
            ),
            "classification": "PUBLIC",
            "tags": [
                "m9-public-pilot",
                "ntsb",
                "text-only-derivative",
                "raw-first",
                accession["sourceId"].lower(),
            ],
        },
    ).json()
    admin.request(
        "PUT",
        f"/sources/uploads/{derivative_session['id']}/content",
        extra_headers={"Content-Type": "text/plain"},
        content=derivative,
    )
    derivative_completed = admin.request(
        "POST",
        f"/sources/uploads/{derivative_session['id']}/complete",
        expected=202,
        idempotency_key=f"m9-public-derivative-complete-{suffix}-{accession['sourceId'].lower()}",
        json={"checksum": derivative_checksum, "size": len(derivative)},
    ).json()
    derivative_parsed = admin.wait(
        f"/parse-jobs/{derivative_completed['parse_job_id']}", TERMINAL_PARSE
    )
    if derivative_parsed["status"] != "SUCCEEDED":
        raise RuntimeError(
            f"Text derivative parse failed for {accession['sourceId']}: {derivative_parsed}"
        )
    return {
        "source_id": accession["sourceId"],
        "source_version_id": derivative_completed["source_version_id"],
        "parse_job_id": derivative_completed["parse_job_id"],
        "checksum": derivative_checksum,
        "bytes": len(derivative),
        "parse_status": derivative_parsed["status"],
        "parse_summary": derivative_parsed.get("result_summary", {}),
        "raw_preserved": True,
        "raw_source_version_id": raw_completed["source_version_id"],
        "raw_parse_job_id": raw_completed["parse_job_id"],
        "raw_parse_status": raw_parsed["status"],
        "raw_checksum": checksum,
        "raw_bytes": len(content),
        "text_derivative_used": True,
        "omitted_pdf_pages": sorted(excluded),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api/v1")
    parser.add_argument("--admin-subject", default="local-admin")
    args = parser.parse_args()
    suffix = uuid4().hex[:10]
    accession_document = json.loads(ACCESSION.read_text(encoding="utf-8"))
    accession_by_id = {item["sourceId"]: item for item in accession_document["sources"]}
    selected = [accession_by_id[source_id] for source_id in PILOT_SOURCE_IDS]
    if any(
        item["admissionStatus"] != "ADMITTED_LOCAL_TEXT_ONLY_WITH_ELEMENT_EXCLUSIONS"
        for item in selected
    ):
        raise RuntimeError("All pilot sources must pass the recorded text-only admission review.")

    with httpx.Client(base_url=args.base_url, timeout=180) as client:
        admin = _login(client, args.admin_subject)
        organization = admin.request("GET", "/organizations").json()["items"][0]
        core_pack = _ensure_core_pack(admin, suffix)
        pack = _register_real_pack(admin, suffix)
        if pack is not None and pack["key_namespace"] != "equipment.rca":
            raise RuntimeError("The registered Pack is not the real M9 equipment.rca Pack.")
        runtime_pack_installed = pack is not None

        space = admin.request(
            "POST",
            "/spaces",
            expected=201,
            idempotency_key=f"m9-public-space-{suffix}",
            json={
                "organization_id": organization["id"],
                "slug": f"m9-public-pilot-{suffix}",
                "display_name": f"M9 public RCA technical pilot {suffix}",
                "description": (
                    "Public NTSB text-only technical pilot; not an expert-approved release."
                ),
                "default_classification": "PUBLIC",
            },
        ).json()
        schema = admin.request(
            "POST",
            f"/spaces/{space['id']}/schemas",
            expected=201,
            idempotency_key=f"m9-public-schema-{suffix}",
            json={
                "schema_key": f"m9-public-{suffix}.nexweave.io/equipment-rca",
                "display_name": "M9 public Equipment RCA pilot schema",
                "semantic_version": "0.1.0",
                "snapshot": {} if runtime_pack_installed else _direct_composed_snapshot(),
            },
        ).json()
        installation: dict[str, Any] | None = None
        schema_version = "0.1.0"
        if pack is not None:
            installation = admin.request(
                "POST",
                f"/spaces/{space['id']}/domain-pack-installations",
                expected=202,
                idempotency_key=f"m9-public-install-{suffix}",
                json={
                    "domain_pack_version_id": pack["id"],
                    "schema_definition_id": schema["schema_definition_id"],
                    "semantic_version": "0.2.0",
                    "operation": "INSTALL",
                },
            ).json()
            installation = admin.wait(
                f"/domain-pack-installations/{installation['id']}", TERMINAL_INSTALL
            )
            if installation["status"] != "ACTIVE":
                raise RuntimeError(f"Real M9 Pack installation failed: {installation}")
            schema_version = "0.2.0"
        validation = admin.request(
            "POST",
            f"/schemas/{schema['schema_definition_id']}/versions/{schema_version}/validate",
        ).json()
        if validation["report"]["compatible"] is not True:
            raise RuntimeError(f"Composed M9 schema is incompatible: {validation}")
        candidate = admin.request(
            "GET", f"/schemas/{schema['schema_definition_id']}/versions/{schema_version}"
        ).json()
        publisher_subject = f"m9-technical-publisher-{suffix}"
        publisher_user = admin.request(
            "POST",
            "/users",
            idempotency_key=f"m9-public-publisher-user-{suffix}",
            json={
                "issuer": "https://identity.nexweave.local/dev",
                "subject": publisher_subject,
                "display_name": "M9 schema technical publisher (not RCA expert)",
                "clearance": "PUBLIC",
                "tenant_roles": [],
            },
        ).json()
        admin.request(
            "PUT",
            f"/spaces/{space['id']}/members/{publisher_user['id']}",
            idempotency_key=f"m9-public-publisher-member-{suffix}",
            json={"subject_type": "USER", "roles": ["publisher"], "clearance": "PUBLIC"},
        )
        published_schema = (
            _login(client, publisher_subject)
            .request(
                "POST",
                f"/schemas/{schema['schema_definition_id']}/versions/{schema_version}/publish",
                idempotency_key=f"m9-public-schema-publish-{suffix}",
                version=int(candidate["version"]),
            )
            .json()
        )

        uploaded = [
            _upload_source(admin, space_id=str(space["id"]), accession=item, suffix=suffix)
            for item in selected
        ]
        prompt = admin.request(
            "POST",
            "/prompt-versions",
            idempotency_key=f"m9-public-prompt-{suffix}",
            json={
                "space_id": space["id"],
                "prompt_key": f"m9.public.rca.{suffix}",
                "content": (
                    "Create schema-bound draft candidates only from supplied report text. "
                    "Do not infer expert approval, do not use images, and preserve "
                    "SourceAnchor provenance."
                ),
                "output_contract": {"kind": "nexweave.structured-compile/v1"},
            },
        ).json()
        profile = admin.request(
            "POST",
            "/model-profiles",
            idempotency_key=f"m9-public-model-{suffix}",
            json={
                "space_id": space["id"],
                "name": f"M9 deterministic local provider {suffix}",
                "provider": "nexweave.local",
                "model_name": "structured-compile-v1",
                "externally_hosted": False,
                "maximum_classification": "PUBLIC",
                "config": {"max_input_units": 500000},
            },
        ).json()

        compiles: list[dict[str, Any]] = []
        for source in uploaded:
            created = admin.request(
                "POST",
                f"/spaces/{space['id']}/compile-jobs",
                expected=202,
                idempotency_key=f"m9-public-compile-{suffix}-{source['source_id'].lower()}",
                json={
                    "schema_version_id": published_schema["id"],
                    "source_version_ids": [source["source_version_id"]],
                    "prompt_version_id": prompt["id"],
                    "model_profile_id": profile["id"],
                    "mode": "SOURCE_SCOPED",
                    "scope": {
                        "pilot": "M9_PUBLIC_TEXT_ONLY",
                        "source_id": source["source_id"],
                        "expert_approved": False,
                    },
                },
            ).json()
            completed = admin.wait(f"/compile-jobs/{created['id']}", TERMINAL_COMPILE)
            if completed["status"] != "SUCCEEDED":
                raise RuntimeError(f"Compile failed for {source['source_id']}: {completed}")
            result = dict(completed["result_summary"])
            if result.get("external_llm_called") is not False:
                raise RuntimeError("Public pilot unexpectedly called an external model.")
            if result.get("stats", {}).get("evidence_candidates", 0) < 1:
                raise RuntimeError(f"No SourceAnchor-backed evidence for {source['source_id']}")
            compiles.append(
                {
                    "source_id": source["source_id"],
                    "compile_job_id": completed["id"],
                    "status": completed["status"],
                    "provider": result.get("provider"),
                    "external_llm_called": result.get("external_llm_called"),
                    "stats": result.get("stats", {}),
                    "cost_summary": completed.get("cost_summary", {}),
                }
            )

        formal_claims = admin.request("GET", f"/spaces/{space['id']}/claims").json()["items"]
        releases = admin.request("GET", f"/spaces/{space['id']}/releases").json()["items"]
        review_cases = admin.request("GET", f"/spaces/{space['id']}/review-cases").json()["items"]
        candidate_claim_count = sum(
            int(item.get("stats", {}).get("claims", 0)) for item in compiles
        )
        if releases:
            raise RuntimeError("The technical pilot must stop before creating a Release.")
        if review_cases:
            raise RuntimeError("The technical pilot must not fabricate an expert ReviewCase.")
        if formal_claims:
            raise RuntimeError("Compile candidates must not become formal Claims before review.")
        if candidate_claim_count < 1:
            raise RuntimeError("Public pilot did not produce any ClaimCandidate.")

        expected_compile_audits = {str(item["compile_job_id"]) for item in compiles}
        expected_raw_parse_audits = {str(item["raw_parse_job_id"]) for item in uploaded}
        expected_derivative_parse_audits = {str(item["parse_job_id"]) for item in uploaded}
        audit_items: list[dict[str, Any]] = []
        cursor: str | None = None
        for _ in range(20):
            params: dict[str, str | int] = {"limit": 100}
            if cursor:
                params["cursor"] = cursor
            page = admin.request("GET", "/audit-logs", params=params).json()
            audit_items.extend(page["items"])
            cursor = page.get("next_cursor")
            if not cursor:
                break
        successful_compile_audits = {
            str(item["resource_id"])
            for item in audit_items
            if item["action"] == "compile.execute" and item["outcome"] == "SUCCEEDED"
        }
        failed_raw_parse_audits = {
            str(item["resource_id"])
            for item in audit_items
            if item["action"] == "source.parse.finalize" and item["outcome"] == "FAILED"
        }
        successful_derivative_parse_audits = {
            str(item["resource_id"])
            for item in audit_items
            if item["action"] == "source.parse.finalize" and item["outcome"] == "SUCCEEDED"
        }
        if not expected_compile_audits <= successful_compile_audits:
            raise RuntimeError("Compile success audit evidence is incomplete.")
        if not expected_raw_parse_audits <= failed_raw_parse_audits:
            raise RuntimeError("Raw encrypted-PDF rejection audit evidence is incomplete.")
        if not expected_derivative_parse_audits <= successful_derivative_parse_audits:
            raise RuntimeError("Text-derivative parse success audit evidence is incomplete.")

        output = {
            "pilot": "M9_PUBLIC_TEXT_ONLY_TECHNICAL",
            "space_id": space["id"],
            "space_slug": space["slug"],
            "pack": (
                {
                    "id": pack["id"],
                    "pack_key": pack["pack_key"],
                    "pack_version": pack["pack_version"],
                    "key_namespace": pack["key_namespace"],
                    "content_checksum": pack["content_checksum"],
                    "runtime_status": "INSTALLED",
                }
                if pack is not None
                else {
                    "pack_key": "equipment-rca-pack",
                    "pack_version": "1.0.0",
                    "key_namespace": "equipment.rca",
                    "runtime_status": "BLOCKED_BY_EXISTING_M4_FIXTURE_IDENTITY",
                    "schema_fallback": "DIRECT_FROM_SIGNED_DECLARATIVE_CONTENT",
                }
            ),
            "core_pack": {
                "id": core_pack["id"],
                "pack_key": core_pack["pack_key"],
                "pack_version": core_pack["pack_version"],
                "key_namespace": core_pack["key_namespace"],
                "content_checksum": core_pack["content_checksum"],
            },
            "installation": (
                {
                    "id": installation["id"],
                    "status": installation["status"],
                    "composition_checksum": installation.get("composition_checksum"),
                }
                if installation is not None
                else None
            ),
            "schema_version": {
                "id": published_schema["id"],
                "status": published_schema["status"],
                "composition_checksum": published_schema.get("composition_checksum"),
            },
            "sources": uploaded,
            "compiles": compiles,
            "candidate_claim_count": candidate_claim_count,
            "formal_claim_count": len(formal_claims),
            "review_case_count": len(review_cases),
            "release_count": len(releases),
            "audit_evidence": {
                "compile_execute_succeeded": len(expected_compile_audits),
                "raw_parse_failed": len(expected_raw_parse_audits),
                "text_derivative_parse_succeeded": len(expected_derivative_parse_audits),
            },
            "expert_approved": False,
            "thresholds_approved": False,
            "gridcrew_in_scope": False,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
