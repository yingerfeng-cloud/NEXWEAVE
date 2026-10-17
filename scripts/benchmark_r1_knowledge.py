"""Independent synthetic business baseline using real ingestion/review/evaluation APIs.

This is a scripted technical dataset, never Web or industrial acceptance.
A failing benchmark remains failed; no release is published by this runner.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import uuid4

import httpx
from verify_m5 import _compile, _create_published_schema, _login
from verify_m95 import upload

ROOT = Path(__file__).resolve().parents[1]


async def inspect_admission_counts(space_id: str) -> dict:
    """Privileged read-only diagnostic, separate from the protected business API."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine
    from verify_m1 import environment

    configured = urlsplit(environment()["NEXWEAVE_DATABASE_URL"])
    local = configured._replace(netloc=configured.netloc.replace("@postgres:", "@127.0.0.1:"))
    if local.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Benchmark database inspection must be loopback-only")
    engine = create_async_engine(urlunsplit(local))
    try:
        async with engine.connect() as c:
            await c.execute(text("SET TRANSACTION READ ONLY"))
            return {
                "quality_tasks": await c.scalar(
                    text(
                        "SELECT count(*) FROM workflow_tasks "
                        "WHERE space_id=:id AND workflow_type='QUALITY_EVALUATION'"
                    ),
                    {"id": space_id},
                ),
                "evaluation_runs": await c.scalar(
                    text("SELECT count(*) FROM evaluation_runs WHERE space_id=:id"),
                    {"id": space_id},
                ),
            }
    finally:
        await engine.dispose()


CORPUS = """Device P101. Device P101 temperature is 70 degC during operation.
Device P101 feeds Device P102.

Device P102. Device P102 is the standby equipment.

设备P201。设备P201的运行温度为65摄氏度。

设备P202。设备P202未向设备P201供给介质。

Device P301. Device P301 does not feed Device P302.

Device P302. Device P302 is listed independently; no connection is asserted.
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8080/api/v1")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strategy", choices=("KEYWORD", "SEMANTIC", "HYBRID"), default="KEYWORD")
    parser.add_argument(
        "--embedding-model-profile-id", help="A tenant/global fixed embedding profile"
    )
    parser.add_argument(
        "--text-model-profile-id",
        help="A tenant/global fixed text profile; default is development rules",
    )
    args = parser.parse_args()
    if (args.strategy != "KEYWORD") != bool(args.embedding_model_profile_id):
        parser.error("SEMANTIC/HYBRID requires a fixed embedding profile; KEYWORD does not use one")
    if not args.base_url.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise ValueError("This development fixture runner is loopback-only")
    cases = json.loads((ROOT / "tests/benchmarks/r1_knowledge_baseline.json").read_text())["cases"]
    suffix = uuid4().hex[:10]
    with httpx.Client(base_url=args.base_url, timeout=120, trust_env=False) as client:
        admin = _login(client, "local-admin")
        org = admin.request("GET", "/organizations").json()["items"][0]
        space = admin.request(
            "POST",
            "/spaces",
            expected=201,
            idempotency_key=str(uuid4()),
            json={
                "organization_id": org["id"],
                "slug": "independent-benchmark-" + suffix,
                "display_name": "Independent synthetic benchmark " + suffix,
                "description": "Scripted technical baseline; not Web/expert/industrial acceptance",
                "default_classification": "INTERNAL",
            },
        ).json()
        sid = space["id"]
        schema = _create_published_schema(admin, client, space, suffix, relation_verb="feeds")
        source = upload(
            admin, sid, "independent-business-baseline.txt", "text/plain", CORPUS.encode()
        )
        prompt = admin.request(
            "POST",
            "/prompt-versions",
            idempotency_key=str(uuid4()),
            json={
                "space_id": sid,
                "prompt_key": "benchmark/" + suffix,
                "content": "Extract source statements with anchors. Human review required.",
            },
        ).json()
        model = (
            {"id": args.text_model_profile_id}
            if args.text_model_profile_id
            else admin.request(
                "POST",
                "/model-profiles",
                idempotency_key=str(uuid4()),
                json={
                    "space_id": sid,
                    "name": "Development rule baseline, not a semantic model",
                    "provider": "nexweave.local",
                    "model_name": "structured-compile-v2",
                    "maximum_classification": "INTERNAL",
                    "config": {"development_only": True},
                },
            ).json()
        )
        compiled = _compile(
            admin,
            space_id=sid,
            schema_id=schema["id"],
            source_id=source,
            prompt_id=prompt["id"],
            profile_id=model["id"],
            suffix=suffix,
            mode="FULL",
        )
        roles = {}
        for role in ("knowledge_engineer", "reviewer", "publisher"):
            subject = f"benchmark-{role}-{suffix}"
            user = admin.request(
                "POST",
                "/users",
                idempotency_key=str(uuid4()),
                json={
                    "issuer": "https://identity.nexweave.local/dev",
                    "subject": subject,
                    "display_name": "Synthetic benchmark technical " + role,
                    "clearance": "INTERNAL",
                    "tenant_roles": [],
                },
            ).json()
            admin.request(
                "PUT",
                f"/spaces/{sid}/members/{user['id']}",
                idempotency_key=str(uuid4()),
                json={"subject_type": "USER", "roles": [role], "clearance": "INTERNAL"},
            )
            roles[role] = _login(client, subject)
        policy = admin.request(
            "POST",
            f"/spaces/{sid}/review-policies",
            expected=201,
            idempotency_key=str(uuid4()),
            json={
                "risk_level": "HIGH",
                "stages": ["ENGINEERING", "EXPERT", "APPROVAL"],
                "timeout_seconds": 3600,
            },
        ).json()
        targets = admin.request("GET", f"/spaces/{sid}/review-targets?limit=500").json()["items"]
        entities = {
            e["id"]: e["display_name"]
            for e in admin.request("GET", f"/spaces/{sid}/entities").json()["items"]
        }
        edges = [t["content"] for t in targets if t["target_type"] == "RELATION_CANDIDATE"]
        assert len(edges) == 1, (
            "Negation/independent listing must not generate affirmative relations"
        )
        assert entities[edges[0]["source_entity_id"]] == "Device P101"
        assert entities[edges[0]["target_entity_id"]] == "Device P102"
        review_cases = []
        for target in targets:
            if target["target_type"] not in {"CLAIM_CANDIDATE", "RELATION_CANDIDATE"}:
                continue
            case = (
                roles["knowledge_engineer"]
                .request(
                    "POST",
                    f"/spaces/{sid}/review-cases",
                    expected=202,
                    idempotency_key=str(uuid4()),
                    json={
                        "target_type": target["target_type"],
                        "target_id": target["id"],
                        "policy_id": policy["id"],
                        "risk_level": "HIGH",
                        "reason": "Scripted corpus review of source quotes; technical only.",
                    },
                )
                .json()
            )
            for stage, role in [
                ("ENGINEERING", "knowledge_engineer"),
                ("EXPERT", "reviewer"),
                ("APPROVAL", "publisher"),
            ]:
                task = next(t for t in case["tasks"] if t["stage"] == stage)
                case = (
                    roles[role]
                    .request(
                        "POST",
                        f"/review-cases/{case['id']}/tasks/{task['id']}/actions",
                        idempotency_key=str(uuid4()),
                        json={
                            "decision": "ACCEPT",
                            "reason": "Technical role checks source quotes; not industrial.",
                        },
                    )
                    .json()
                )
            if case["status"] != "APPROVED":
                raise RuntimeError("corpus review failed")
            review_cases.append(case["id"])
        claims = admin.request("GET", f"/spaces/{sid}/claims").json()["items"]
        mapped = []
        for case in cases:
            claim = next(
                (
                    c
                    for c in claims
                    if case.get("entity") and c["statement"].startswith(case["entity"])
                ),
                None,
            )
            mapped.append(
                {
                    "case_key": case["key"],
                    "case_type": "INSUFFICIENT_EVIDENCE" if case.get("refuse") else "ANSWERABLE",
                    "question": case["question"],
                    "expected_claim_ids": [claim["id"]] if claim else [],
                    "expected_terms": case.get("terms", []),
                    "expect_refusal": case.get("refuse", False),
                    "metadata": {"requirement": case.get("requires", "lexical/evidence baseline")},
                }
            )
        suite = admin.request(
            "POST",
            f"/spaces/{sid}/evaluation-suites",
            expected=201,
            idempotency_key=str(uuid4()),
            json={
                "schema_version_id": schema["id"],
                "suite_key": "independent/q-" + suffix,
                "version": 1,
                "name": "Independent 20-question business baseline",
                "minimum_pass_rate": 100,
                "cases": mapped,
            },
        ).json()
        candidate = admin.request(
            "POST",
            f"/spaces/{sid}/release-candidates",
            expected=202,
            idempotency_key=str(uuid4()),
            json={
                "version": "1.0.0",
                "schema_version_id": schema["id"],
                "prompt_version_id": prompt["id"],
                "model_profile_id": model["id"],
                "evaluation_suite_id": suite["id"],
                "claim_ids": [c["id"] for c in claims],
                "relation_ids": [],
                "wiki_page_version_ids": [],
                "index_config": {
                    "version": "r1-query-v3",
                    "retrieval_strategy": args.strategy,
                    **(
                        {"embedding_model_profile_id": args.embedding_model_profile_id}
                        if args.embedding_model_profile_id
                        else {}
                    ),
                },
                "notes": "Independent 100% benchmark; no release or model accuracy claim.",
            },
        ).json()
        candidate = admin.wait(
            f"/release-candidates/{candidate['id']}", {"FAILED", "PENDING_APPROVAL"}
        )
        if not candidate["gate_summary"].get("evaluation_run_id"):
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(
                    {"status": "MODEL_OR_GATE_UNAVAILABLE", "candidate": candidate},
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n"
            )
            raise SystemExit(
                "No scored evaluation: model or gate unavailable; see candidate details"
            )
        run = admin.request(
            "GET", f"/evaluations/runs/{candidate['gate_summary']['evaluation_run_id']}"
        ).json()
        expected = [r for r in run["results"] if not r["details"]["scoring"]["expected_refusal"]]
        refusals = [r for r in run["results"] if r["details"]["scoring"]["expected_refusal"]]
        metrics = {
            "recall": sum(r["details"]["scoring"]["expected_claims_retrieved"] for r in expected)
            / len(expected),
            "answer": sum(
                r["details"]["scoring"]["terms_in_answer"] and r["answer_status"] == "COMPLETED"
                for r in expected
            )
            / len(expected),
            "citation": sum(r["details"]["scoring"]["expected_claims_cited"] for r in expected)
            / len(expected),
            "refusal": sum(r["answer_status"] == "REFUSED" for r in refusals) / len(refusals),
        }
        result = {
            "scope": "REAL_HTTP_SOURCE_REVIEW_EVALUATION_SYNTHETIC_SCRIPTED_NOT_WEB_OR_INDUSTRIAL",
            "strategy": args.strategy,
            "real_semantic_model": "UNAVAILABLE_NOT_TESTED"
            if args.strategy == "KEYWORD"
            else "CONFIGURED_PROVIDER_EXECUTED_NOT_INDUSTRIAL_ACCEPTANCE",
            "embedding_model_profile_id": args.embedding_model_profile_id,
            "text_model_profile_id": model["id"],
            "text_extraction": "CONFIGURED_PROVIDER"
            if args.text_model_profile_id
            else "DEVELOPMENT_RULES",
            "space_id": sid,
            "source_version_id": source,
            "compile_job_id": compiled["id"],
            "extraction_control": {
                "affirmative_relations": [
                    {
                        "source": entities[e["source_entity_id"]],
                        "target": entities[e["target_entity_id"]],
                        "relation_type": e["relation_type_key"],
                    }
                    for e in edges
                ],
                "negation_and_independent_listing": "NO_AFFIRMATIVE_EDGE_GENERATED",
            },
            "review_case_ids": review_cases,
            "candidate_id": candidate["id"],
            "candidate_status": candidate["status"],
            "dimension_metrics": metrics,
            "evaluation": run,
        }
        # Preserve the original answer expectations; loss of the source must
        # make them fail, while ordinary users cannot read stale answer details.
        sources = admin.request("GET", f"/spaces/{sid}/sources").json()["items"]
        source_row = next(v for d in sources for v in d["versions"] if v["id"] == source)
        admin.request(
            "POST",
            f"/source-versions/{source}/invalidate",
            expected=201,
            version=source_row["version"],
            idempotency_key=str(uuid4()),
            json={
                "reason_code": "SYNTHETIC_BENCHMARK",
                "reason": "Independent lost-source regression; synthetic fixture only",
                "policy_version": "r1-review-c/1",
            },
        )
        historical = admin.request("GET", f"/evaluations/runs/{run['id']}").json()
        assert historical["result_visibility"] == "METADATA_ONLY" and not historical["results"]
        counts_before = asyncio.run(inspect_admission_counts(sid))
        invalidated = admin.request(
            "POST",
            f"/spaces/{sid}/evaluations/runs",
            expected=404,
            idempotency_key=str(uuid4()),
            json={
                "suite_id": suite["id"],
                "target_type": "RELEASE_CANDIDATE",
                "target_id": candidate["id"],
                "retrieval_strategy": args.strategy,
            },
        )
        counts_after = asyncio.run(inspect_admission_counts(sid))
        assert counts_after == counts_before
        result["source_invalidation_control"] = {
            "new_evaluation_http_status": invalidated.status_code,
            "new_execution": "REJECTED_BEFORE_EXECUTION_NOT_A_SCORED_PASS",
            "public_visibility": historical["result_visibility"],
            "historical_answer_hidden": True,
            "historical_gate_passed": historical["gate_passed"],
            "database_evidence_layer": "PRIVILEGED_READ_ONLY_COUNTS_NOT_BUSINESS_API",
            "counts_before": counts_before,
            "counts_after": counts_after,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(
            json.dumps(
                {
                    "status": "PASS" if run["gate_passed"] else "FAIL",
                    "metrics": metrics,
                    "cases": run["metrics"],
                    "published": False,
                },
                ensure_ascii=False,
            )
        )
        if not run["gate_passed"]:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
