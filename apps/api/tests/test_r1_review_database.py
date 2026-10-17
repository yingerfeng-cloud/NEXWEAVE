"""R1 repair regressions on migrated PostgreSQL tables and authenticated ASGI routes.

Synthetic fixtures are inserted explicitly; this is not a Web authoring or
Temporal/S3/model acceptance test. No SQL or authorization implementation is mocked.
"""

import os
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from sqlalchemy import MetaData, insert, text

from nexweave_api.app import create_app
from nexweave_api.database import Database
from nexweave_api.identity import LocalDevIdentityProvider
from nexweave_api.integration_repository import IntegrationRepository
from nexweave_api.settings import Settings
from nexweave_domain import DataClassification, new_uuid7

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
CHECKSUM = "sha256:" + "a" * 64


@pytest.fixture
async def system():
    url = os.environ.get("NEXWEAVE_REVIEW_DATABASE_URL")
    if not url:
        pytest.skip("Set NEXWEAVE_REVIEW_DATABASE_URL to an isolated migrated PostgreSQL database")
    settings = Settings(
        database_url=url,
        # Explicit unavailable dependency; not real Temporal acceptance.
        temporal_endpoint="127.0.0.1:1",
        local_dev_identity_enabled=True,
        local_dev_signing_key="synthetic-r1-regression-signing-key-20261017",
    )
    database = Database(settings)
    repo = IntegrationRepository(database)
    suffix = str(new_uuid7())
    admin = await repo.bootstrap_local_development(
        tenant_slug="review-" + suffix, subject="review-admin-" + suffix
    )
    async with database.engine.begin() as c:
        org = (
            await c.execute(
                text("SELECT id FROM organizations WHERE tenant_id=:t"), {"t": admin.tenant_id}
            )
        ).scalar_one()
        metadata = MetaData()
        await c.run_sync(metadata.reflect)
    space = await repo.create_space(
        principal=admin,
        organization_id=org,
        slug="review-" + suffix,
        display_name="Synthetic R1 regression",
        description="Test only",
        default_classification=DataClassification.INTERNAL,
        idempotency_key=suffix,
        trace_id="test",
    )
    sid = UUID(space["id"])

    async def put(table, **values):
        t = metadata.tables[table]
        common = {
            "id": new_uuid7(),
            "tenant_id": admin.tenant_id,
            "space_id": sid,
            "created_by": admin.actor_id,
            "updated_by": admin.actor_id,
        }
        row = {k: v for k, v in {**common, **values}.items() if k in t.c}
        async with database.engine.begin() as c:
            await c.execute(insert(t).values(**row))
        return row.get("id", common["id"])

    async def user(roles, clearance="HIGHLY_RESTRICTED", member_clearance=None):
        actor = await put(
            "user_identities",
            issuer=LocalDevIdentityProvider.issuer,
            subject="role-" + str(new_uuid7()),
            display_name="Synthetic role",
            clearance=clearance,
        )
        member = await put(
            "space_members",
            subject_type="USER",
            user_identity_id=actor,
            clearance=member_clearance or clearance,
        )
        for role in roles:
            await put("space_member_roles", space_member_id=member, role=role)
        async with database.engine.connect() as c:
            subject = (
                await c.execute(
                    text("SELECT subject FROM user_identities WHERE id=:id"), {"id": actor}
                )
            ).scalar_one()
        return await repo.get_local_principal(subject)

    engineer = await user(["knowledge_engineer"])
    definition = await put("schema_definitions", schema_key="review.io/schema", display_name="Test")
    schema = await put(
        "schema_versions",
        schema_definition_id=definition,
        semantic_version="1.0.0",
        normalized_snapshot={},
        content_checksum=CHECKSUM,
        composition_checksum=CHECKSUM,
        canonicalization_algorithm="nxw-canonical-json-v1",
        status="PUBLISHED",
    )
    prompt = await put(
        "prompt_versions",
        prompt_key="review.test",
        revision=1,
        content="Synthetic",
        checksum=CHECKSUM,
    )
    model = await put(
        "model_profiles",
        name="Synthetic local provider",
        provider="nexweave.local",
        model_name="structured-compile-v1",
    )
    workflow = await put(
        "workflow_tasks",
        workflow_type="KNOWLEDGE_COMPILE",
        business_key=suffix,
        display_name="Synthetic",
        workflow_id="review-" + suffix,
    )
    objects = []
    for label, classification in [("public", "INTERNAL"), ("secret", "CONFIDENTIAL")]:
        doc = await put("source_documents", display_name=label, classification=classification)
        source = new_uuid7()
        upload = await put(
            "source_upload_sessions",
            source_document_id=doc,
            source_version_id=source,
            filename=label + ".md",
            content_type="text/markdown",
            expected_size=10,
            expected_checksum=CHECKSUM,
            object_key="raw/v1/" + label + suffix,
            display_name=label,
            classification=classification,
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        await put(
            "source_versions",
            id=source,
            source_document_id=doc,
            upload_session_id=upload,
            filename=label + ".md",
            content_type="text/markdown",
            size=10,
            checksum=CHECKSUM,
            object_key="raw/v1/" + label + suffix,
            classification=classification,
        )
        parse = await put(
            "parse_jobs",
            source_version_id=source,
            workflow_id="parse-" + label + suffix,
            parser_id="markdown",
            parser_version="1",
            config_checksum=CHECKSUM,
            document_model_version="1",
            locator_version="1",
            correlation_id=new_uuid7(),
            requested_by_actor_type="USER",
        )
        anchor = await put(
            "source_anchors",
            source_version_id=source,
            source_checksum=CHECKSUM,
            parse_job_id=parse,
            locator_version="1",
            excerpt_hash=CHECKSUM,
            locators=[{"kind": "text", "start": 0, "end": 10}],
            status="VALID",
        )
        compile_workflow = await put(
            "workflow_tasks",
            workflow_type="KNOWLEDGE_COMPILE",
            business_key=label + suffix,
            display_name="Synthetic compilation",
            workflow_id="compile-workflow-" + label + suffix,
        )
        job = await put(
            "compile_jobs",
            schema_version_id=schema,
            composition_checksum=CHECKSUM,
            prompt_version_id=prompt,
            model_profile_id=model,
            workflow_task_id=compile_workflow,
            workflow_id="compile-" + label + suffix,
            mode="FULL",
            input_fingerprint="sha256:" + ("b" if label == "public" else "c") * 64,
            normalization_version="m5-v1",
        )
        await put(
            "compile_job_sources",
            compile_job_id=job,
            source_version_id=source,
            source_checksum=CHECKSUM,
            parse_job_id=parse,
            input_order=0,
        )
        entity = await put(
            "knowledge_entities",
            schema_version_id=schema,
            type_key="review.io/pump",
            normalized_key=label,
            display_name="Pump " + label,
        )
        version = await put(
            "knowledge_entity_versions",
            entity_id=entity,
            compile_job_id=job,
            revision=1,
            provenance={},
            content_checksum=CHECKSUM,
        )
        async with database.engine.begin() as c:
            await c.execute(
                text("UPDATE knowledge_entities SET current_version_id=:v WHERE id=:id"),
                {"v": version, "id": entity},
            )
        candidate = await put(
            "claim_candidates",
            compile_job_id=job,
            schema_version_id=schema,
            subject_entity_id=entity,
            predicate_key="review.io/temperature",
            object_value={"value": 70},
            statement="Pump " + label + " temperature is 70 degC.",
            provenance={},
            created_by=engineer.actor_id,
        )
        await put(
            "evidence_candidates",
            claim_candidate_id=candidate,
            source_anchor_id=anchor,
            stance="SUPPORTS",
            excerpt_hash=CHECKSUM,
            compile_job_id=job,
        )
        claim = await put(
            "claims",
            candidate_id=candidate,
            subject_entity_id=entity,
            predicate_key="review.io/temperature",
            object_value={"value": 70},
            statement="Pump " + label + " temperature is 70 degC.",
            confidence_level="HIGH",
            provenance={},
        )
        evidence = await put(
            "evidence_records",
            claim_id=claim,
            source_anchor_id=anchor,
            stance="SUPPORTS",
            excerpt_hash=CHECKSUM,
        )
        page = await put(
            "wiki_pages",
            schema_version_id=schema,
            primary_entity_id=entity,
            template_key="review.io/pump",
            slug=label,
            title="Pump " + label,
        )
        page_version = await put(
            "wiki_page_versions",
            wiki_page_id=page,
            compile_job_id=job,
            revision=1,
            markdown="Pump " + label,
            content_checksum=CHECKSUM,
            status="APPROVED",
        )
        async with database.engine.begin() as c:
            await c.execute(
                text("UPDATE wiki_pages SET current_version_id=:v WHERE id=:id"),
                {"v": page_version, "id": page},
            )
        objects.append(
            dict(
                doc=doc,
                source=source,
                job=job,
                candidate=candidate,
                claim=claim,
                evidence=evidence,
                entity=entity,
                page=page,
                page_version=page_version,
            )
        )
    suite = await repo.create_evaluation_suite(
        principal=admin,
        space_id=sid,
        payload={
            "schema_version_id": str(schema),
            "suite_key": "review.io/questions",
            "version": 1,
            "name": "Synthetic regression",
            "minimum_pass_rate": 100,
            "cases": [
                {
                    "case_key": "temperature",
                    "case_type": "ANSWERABLE",
                    "question": "How hot is Pump public?",
                    "expected_claim_ids": [str(objects[0]["claim"])],
                    "expected_terms": ["70"],
                }
            ],
        },
        idempotency_key=suffix,
        trace_id="test",
    )
    # Frozen fixture release: explicit setup only, never counted as a Web or review acceptance.
    manifest = {
        "objects": {
            "claim": [str(o["claim"]) for o in objects],
            "relation": [],
            "wiki_page_version": [str(o["page_version"]) for o in objects],
        },
        "evidence_ids": [str(o["evidence"]) for o in objects],
        "entity_ids": [str(o["entity"]) for o in objects],
    }
    rc = await put(
        "release_candidates",
        version="1.0.0",
        schema_version_id=schema,
        composition_checksum=CHECKSUM,
        prompt_version_id=prompt,
        model_profile_id=model,
        evaluation_suite_id=UUID(suite["id"]),
        workflow_task_id=workflow,
        workflow_id="release-" + suffix,
        manifest=manifest,
        manifest_checksum=CHECKSUM,
        index_config={},
    )
    release = await put(
        "releases",
        candidate_id=rc,
        version="1.0.0",
        manifest=manifest,
        manifest_checksum=CHECKSUM,
        schema_version_id=schema,
        composition_checksum=CHECKSUM,
        prompt_version_id=prompt,
        model_profile_id=model,
        index_config={},
        published_by=admin.actor_id,
    )
    async with database.engine.begin() as c:
        candidate_row = (
            (await c.execute(text("SELECT * FROM release_candidates WHERE id=:id"), {"id": rc}))
            .mappings()
            .one()
        )
        await repo._persist_release_items(c, release, candidate_row)
        docs = await repo._projection_documents(c, candidate_row)
        vectors = await repo._model_gateway.embedding(
            model_profile_id=str(model), texts=tuple(d["body"] for d in docs)
        )
        await repo._persist_projection(c, release, candidate_row, docs, vectors)
    app = create_app(settings, database=database, repository=repo)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://regression.test"
    ) as client:

        def headers(actor):
            token, _ = LocalDevIdentityProvider(settings).issue(actor)
            return {"Authorization": "Bearer " + token, "Idempotency-Key": str(new_uuid7())}

        yield SimpleNamespace(
            repo=repo,
            database=database,
            admin=admin,
            engineer=engineer,
            space=sid,
            objects=objects,
            release=release,
            candidate=rc,
            suite=UUID(suite["id"]),
            user=user,
            put=put,
            client=client,
            headers=headers,
        )
    await database.close()


async def test_current_permission_and_dependency_gates_across_routes(system):
    s = system
    low = await s.user(["consumer", "knowledge_engineer"], member_clearance="INTERNAL")
    high = await s.user(["consumer", "knowledge_engineer"])
    for actor, count in [(low, 1), (high, 2)]:
        response = await s.client.get(f"/api/v1/spaces/{s.space}/claims", headers=s.headers(actor))
        assert response.status_code == 200, response.text
        assert len(response.json()["items"]) == count
        entities = await s.client.get(
            f"/api/v1/releases/{s.release}/graph/entities", headers=s.headers(actor)
        )
        assert entities.status_code == 200 and len(entities.json()["items"]) == count
        response = await s.client.get(
            f"/api/v1/spaces/{s.space}/wiki/pages", headers=s.headers(actor)
        )
        assert len(response.json()["items"]) == count
    response = await s.client.get(f"/api/v1/releases/{s.release}/export", headers=s.headers(low))
    assert response.status_code == 404 and "Pump secret" not in response.text
    response = await s.client.get(f"/api/v1/releases/{s.release}/export", headers=s.headers(high))
    assert response.status_code == 200, response.text
    assert "Pump secret" in response.text
    metadata = await s.client.get(f"/api/v1/releases/{s.release}", headers=s.headers(low))
    assert metadata.status_code == 200
    assert metadata.json()["manifest_visibility"] == "METADATA_ONLY"
    assert str(s.objects[1]["claim"]) not in metadata.text
    for actor, expected in [(low, 404), (high, 200)]:
        graph = await s.client.get(
            f"/api/v1/releases/{s.release}/graph/traverse",
            params={"start_entity_id": str(s.objects[1]["entity"])},
            headers=s.headers(actor),
        )
        assert graph.status_code == expected, graph.text
        exported = await s.client.post(
            f"/api/v1/wiki/pages/{s.objects[1]['page']}/obsidian-exports", headers=s.headers(actor)
        )
        assert exported.status_code == (404 if actor is low else 201), exported.text
    for path in [
        f"/wiki/pages/{s.objects[1]['page']}",
        f"/claims/{s.objects[1]['claim']}/evidence",
    ]:
        response = await s.client.get("/api/v1" + path, headers=s.headers(low))
        assert response.status_code == 404
    async with s.database.engine.begin() as c:
        await c.execute(
            text("UPDATE space_members SET status='REVOKED' WHERE user_identity_id=:id"),
            {"id": low.actor_id},
        )
    response = await s.client.get(f"/api/v1/releases/{s.release}/export", headers=s.headers(low))
    assert response.status_code == 403
    archive = await s.client.post(
        f"/api/v1/sources/{s.objects[1]['doc']}/archive",
        headers={**s.headers(s.admin), "If-Match": '"v1"'},
        json={"reason": "Synthetic archival regression"},
    )
    assert archive.status_code == 200, archive.text
    graph = await s.client.get(
        f"/api/v1/releases/{s.release}/graph/traverse",
        params={"start_entity_id": str(s.objects[1]["entity"])},
        headers=s.headers(high),
    )
    assert graph.status_code == 404
    exported = await s.client.get(f"/api/v1/releases/{s.release}/export", headers=s.headers(high))
    assert exported.status_code == 404


async def test_web_review_context_conflict_decision_and_candidate_metadata_are_guarded(system):
    s = system
    low = await s.user(["knowledge_engineer", "reviewer"], member_clearance="INTERNAL")
    high = await s.user(["knowledge_engineer", "reviewer", "space_admin"])
    for actor, count in [(low, 1), (high, 2)]:
        result = await s.client.get(
            f"/api/v1/spaces/{s.space}/review-targets", headers=s.headers(actor)
        )
        assert result.status_code == 200, result.text
        assert len(result.json()["items"]) == count
        assert all(
            item["content"]["statement"] and item["evidence"][0]["source_version_id"]
            for item in result.json()["items"]
        )
    hidden = await s.client.get(f"/api/v1/release-candidates/{s.candidate}", headers=s.headers(low))
    assert hidden.status_code == 200 and hidden.json()["manifest_visibility"] == "METADATA_ONLY"
    assert "Pump secret" not in hidden.text and str(s.objects[1]["claim"]) not in hidden.text
    visible = await s.client.get(
        f"/api/v1/release-candidates/{s.candidate}", headers=s.headers(high)
    )
    assert visible.status_code == 200 and visible.json()["manifest_visibility"] == "FULL"
    conflict = await s.put(
        "conflict_cases",
        cluster_key="synthetic-web-case",
        kind="CONTRADICTORY_CLAIM",
        severity="BLOCKING",
        blocking=True,
        status="OPEN",
        details={},
    )
    for side, target in zip(("A", "B"), s.objects, strict=True):
        await s.put(
            "conflict_items",
            conflict_case_id=conflict,
            side=side,
            object_type="CLAIM_CANDIDATE",
            object_id=target["candidate"],
            evidence_snapshot={},
        )
    low_list = await s.client.get(f"/api/v1/spaces/{s.space}/conflicts", headers=s.headers(low))
    assert low_list.status_code == 200 and not low_list.json()["items"]
    high_list = await s.client.get(f"/api/v1/spaces/{s.space}/conflicts", headers=s.headers(high))
    assert high_list.status_code == 200, high_list.text
    sides = high_list.json()["items"][0]["items"]
    assert [item["side"] for item in sides] == ["A", "B"] and all(
        item["evidence"] for item in sides
    )
    path = f"/api/v1/conflicts/{conflict}/decisions"
    bad = await s.client.post(
        path,
        headers=s.headers(high),
        json={"resolution": "CONDITIONAL", "reason": "Reviewed", "conditions": {}},
    )
    assert bad.status_code == 422
    reader = await s.user(["knowledge_engineer", "reviewer"])
    unauthorized = await s.client.post(
        path,
        headers=s.headers(reader),
        json={"resolution": "RETAIN_BOTH", "reason": "Reader cannot decide"},
    )
    assert unauthorized.status_code == 403
    resolved = await s.client.post(
        path,
        headers=s.headers(high),
        json={
            "resolution": "CONDITIONAL",
            "reason": "Different operating windows explain both values",
            "conditions": {"applicability": "Use the matching operating window"},
        },
    )
    assert resolved.status_code == 200 and resolved.json()["status"] == "RESOLVED", resolved.text
    final = await s.client.get(f"/api/v1/spaces/{s.space}/conflicts", headers=s.headers(high))
    assert final.json()["items"][0]["decisions"][0]["conditions"]["applicability"]


async def test_expected_refusal_reason_is_executed_and_failed_workflow_is_terminal(system):
    s = system
    original = await s.repo.get_evaluation_suite(principal=s.admin, suite_id=s.suite)
    suite = await s.repo.create_evaluation_suite(
        principal=s.admin,
        space_id=s.space,
        payload={
            "schema_version_id": original["schema_version_id"],
            "suite_key": "review.io/refusal",
            "version": 1,
            "name": "Refusal reason contract",
            "minimum_pass_rate": 100,
            "cases": [
                {
                    "case_key": key,
                    "case_type": "COUNTERFACTUAL",
                    "question": "Absent Z999",
                    "expect_refusal": True,
                    "expected_refusal_reason": reason,
                }
                for key, reason in [
                    ("missing-object", "NO_MATCHING_KNOWLEDGE"),
                    ("wrong-condition", "EVIDENCE_UNAVAILABLE"),
                ]
            ],
        },
        idempotency_key=str(new_uuid7()),
        trace_id="test",
    )
    assert suite["cases"][0]["expected_refusal_reason"] == "NO_MATCHING_KNOWLEDGE"
    async with s.database.engine.begin() as c:
        run = await s.repo._evaluate(
            c,
            tenant_id=s.admin.tenant_id,
            space_id=s.space,
            suite_id=UUID(suite["id"]),
            target_type="RELEASE",
            target_id=s.release,
            strategy="KEYWORD",
            config={},
            actor_id=s.admin.actor_id,
        )
    assert run["metrics"]["pass_rate"] == 50 and run["gate_passed"] is False
    detail = await s.client.get(f"/api/v1/evaluations/runs/{run['id']}", headers=s.headers(s.admin))
    assert detail.status_code == 200
    assert [r["passed"] for r in detail.json()["results"]] == [True, False]
    task = await s.put(
        "workflow_tasks",
        workflow_type="QUALITY_EVALUATION",
        business_key=str(new_uuid7()),
        display_name="Synthetic failure",
        workflow_id="failure-" + str(new_uuid7()),
    )
    failed = await s.put(
        "evaluation_runs",
        suite_id=s.suite,
        suite_version=1,
        target_type="RELEASE",
        target_id=s.release,
        workflow_task_id=task,
        retrieval_strategy="KEYWORD",
        retrieval_config={},
        status="CREATED",
    )
    await s.repo.apply_projection_event(
        {
            "task_id": str(task),
            "actor_id": str(s.admin.actor_id),
            "run_id": "synthetic-failure-run",
            "trace_id": "test",
            "event_type": "RUN_FAILED",
            "event_key": "failure",
            "status": "FAILED",
            "error_code": "SYNTHETIC_PROVIDER_UNAVAILABLE",
            "message": "Synthetic terminal projection",
        }
    )
    response = await s.client.get(f"/api/v1/evaluations/runs/{failed}", headers=s.headers(s.admin))
    assert response.status_code == 200 and response.json()["status"] == "FAILED", response.text
    assert response.json()["gate_passed"] is False
    assert response.json()["metrics"]["execution_error_code"] == "SYNTHETIC_PROVIDER_UNAVAILABLE"
    listing = await s.client.get(
        f"/api/v1/spaces/{s.space}/evaluations/runs", headers=s.headers(s.admin)
    )
    assert listing.status_code == 200 and str(failed) in listing.text


async def test_oidc_subject_requires_the_provisioned_issuer(system):
    from nexweave_api.errors import AuthenticationFailed

    s = system
    with pytest.raises(AuthenticationFailed):
        await s.repo.resolve_principal(s.engineer, issuer="https://external-iam.example.test")
    verified = await s.repo.resolve_principal(s.engineer, issuer=LocalDevIdentityProvider.issuer)
    assert verified.actor_id == s.engineer.actor_id


async def test_browser_user_issuer_configuration_allows_real_development_login(system):
    s = system
    config = await s.client.get("/api/v1/auth/config")
    assert config.status_code == 200 and config.json()["issuer"] == LocalDevIdentityProvider.issuer
    for issuer, expected in [("local", 401), (config.json()["issuer"], 200)]:
        subject = "browser-identity-" + str(new_uuid7())
        created = await s.client.post(
            "/api/v1/users",
            headers=s.headers(s.admin),
            json={
                "issuer": issuer,
                "subject": subject,
                "display_name": "Synthetic UI identity regression",
                "clearance": "INTERNAL",
                "tenant_roles": [],
            },
        )
        assert created.status_code == 200, created.text
        logged_in = await s.client.post("/api/v1/auth/dev/session", json={"subject": subject})
        assert logged_in.status_code == expected
        if expected == 200:
            assert logged_in.json()["principal"]["actor_id"] == created.json()["id"]


async def test_evaluation_executes_same_question_and_source_gate_as_query(system):
    s = system

    async def ask(question):
        response = await s.client.post(
            f"/api/v1/releases/{s.release}/queries",
            headers=s.headers(s.admin),
            json={
                "question": question,
                "strategy": "KEYWORD",
                "top_k": 5,
                "client_request_id": str(new_uuid7()),
            },
        )
        assert response.status_code == 200, response.text
        return response.json()

    async def evaluate():
        async with s.database.engine.begin() as c:
            return await s.repo._evaluate(
                c,
                tenant_id=s.admin.tenant_id,
                space_id=s.space,
                suite_id=s.suite,
                target_type="RELEASE",
                target_id=s.release,
                strategy="KEYWORD",
                config={},
                actor_id=s.admin.actor_id,
            )

    assert (await ask("How hot is Pump public?"))["status"] == "REFUSED"
    run = await evaluate()
    assert not run["gate_passed"] and run["metrics"]["pass_rate"] == 0
    control = await ask("Pump public")
    assert control["status"] == "COMPLETED" and control["citations"]
    # Positive evaluation checks the identical retrieval/answer, not corpus presence.
    async with s.database.engine.begin() as c:
        suite_row = (
            (
                await c.execute(
                    text("SELECT schema_version_id FROM evaluation_suites WHERE id=:id"),
                    {"id": s.suite},
                )
            )
            .mappings()
            .one()
        )
    positive = await s.repo.create_evaluation_suite(
        principal=s.admin,
        space_id=s.space,
        payload={
            "schema_version_id": str(suite_row["schema_version_id"]),
            "suite_key": "review.io/control",
            "version": 1,
            "name": "Positive control",
            "minimum_pass_rate": 100,
            "cases": [
                {
                    "case_key": "temperature",
                    "case_type": "ANSWERABLE",
                    "question": "Pump public",
                    "expected_claim_ids": [str(s.objects[0]["claim"])],
                    "expected_terms": ["70"],
                }
            ],
        },
        idempotency_key=str(new_uuid7()),
        trace_id="test",
    )
    s.suite = UUID(positive["id"])
    positive_run = await evaluate()
    assert positive_run["gate_passed"]
    async with s.database.engine.connect() as c:
        trace = (
            await c.execute(
                text("SELECT details FROM evaluation_results WHERE run_id=:id"),
                {"id": UUID(positive_run["id"])},
            )
        ).scalar_one()
    assert trace["actual"]["retrieval_trace"] and trace["actual"]["citations"]
    assert (
        trace["scoring"]["expected_claims_retrieved"] and trace["scoring"]["expected_claims_cited"]
    )
    response = await s.client.post(
        f"/api/v1/source-versions/{s.objects[0]['source']}/invalidate",
        headers={**s.headers(s.admin), "If-Match": '"v1"'},
        json={
            "reason_code": "TEST_WITHDRAWN",
            "reason": "Synthetic regression",
            "policy_version": "test-v1",
        },
    )
    assert response.status_code == 201, response.text
    assert (await ask("Pump public"))["status"] == "REFUSED"
    assert not (await evaluate())["gate_passed"]
    historical_evaluation = await s.client.get(
        f"/api/v1/evaluations/runs/{positive_run['id']}", headers=s.headers(s.admin)
    )
    assert historical_evaluation.status_code == 200, historical_evaluation.text
    assert historical_evaluation.json()["result_visibility"] == "METADATA_ONLY"
    assert (
        not historical_evaluation.json()["results"]
        and historical_evaluation.json()["gate_passed"] is None
    )
    assert "Pump public" not in historical_evaluation.text
    response = await s.client.get(
        f"/api/v1/query-answers/{control['id']}", headers=s.headers(s.admin)
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "REFUSED" and not response.json()["citations"]
    response = await s.client.get(
        f"/api/v1/releases/{s.release}/export", headers=s.headers(s.admin)
    )
    assert response.status_code == 404


async def test_attribute_filters_execute_and_unknown_fields_fail(system):
    s = system

    async def ask(filters, strategy="ATTRIBUTE"):
        return await s.client.post(
            f"/api/v1/releases/{s.release}/queries",
            headers=s.headers(s.admin),
            json={
                "question": "Pump public",
                "strategy": strategy,
                "filters": filters,
                "top_k": 5,
                "client_request_id": str(new_uuid7()),
            },
        )

    matched = await ask(
        {"predicate_key": "review.io/temperature", "subject_entity_id": str(s.objects[0]["entity"])}
    )
    assert matched.status_code == 200, matched.text
    assert matched.json()["status"] == "COMPLETED"
    mismatch = await ask({"predicate_key": "review.io/vibration"})
    assert mismatch.status_code == 200 and mismatch.json()["status"] == "REFUSED"
    assert (await ask({"unknown": "ignored"})).status_code == 422
    assert (await ask({"predicate_key": 42})).status_code == 422
    assert (await ask({})).status_code == 422


async def test_high_risk_real_author_stage_roles_material_edit_and_delivery(system):
    from nexweave_api.errors import ApiProblem
    from nexweave_api.review_delivery import ReviewDelivery
    from nexweave_application import WorkflowExecutionInfo

    s = system

    class UnavailableTemporal:
        async def start(self, **kwargs):
            raise ApiProblem(
                503, "WORKFLOW_DEPENDENCY_UNAVAILABLE", "Unavailable", "Injected outage"
            )

        async def command(self, **kwargs):
            raise ApiProblem(
                503, "WORKFLOW_DEPENDENCY_UNAVAILABLE", "Unavailable", "Injected outage"
            )

        async def completed_review_result(self, workflow_id):
            return None

    s.client._transport.app.state.workflow_gateway = UnavailableTemporal()
    async with s.database.engine.connect() as c:
        original = dict(
            (
                await c.execute(
                    text("SELECT * FROM claim_candidates WHERE id=:id"),
                    {"id": s.objects[0]["candidate"]},
                )
            )
            .mappings()
            .one()
        )
        evidence = dict(
            (
                await c.execute(
                    text("SELECT * FROM evidence_candidates WHERE claim_candidate_id=:id"),
                    {"id": original["id"]},
                )
            )
            .mappings()
            .one()
        )
    original["id"] = new_uuid7()
    original["statement"] = "Pump public temperature observed at 70 degC."
    target = await s.put("claim_candidates", **original)
    evidence["id"], evidence["claim_candidate_id"] = new_uuid7(), target
    await s.put("evidence_candidates", **evidence)
    initiator = await s.user(["knowledge_engineer", "publisher"])
    independent_engineer = await s.user(["knowledge_engineer"])
    expert = await s.user(["reviewer"])
    author = s.engineer
    # Give the content author explicit approval qualification: duty separation,
    # not a missing role, must be what rejects their final approval.
    async with s.database.engine.begin() as c:
        member = (
            await c.execute(
                text("SELECT id FROM space_members WHERE user_identity_id=:id"),
                {"id": author.actor_id},
            )
        ).scalar_one()
    await s.put("space_member_roles", space_member_id=member, role="publisher")
    approver = await s.user(["publisher"])
    response = await s.client.post(
        f"/api/v1/spaces/{s.space}/review-policies",
        headers=s.headers(s.admin),
        json={
            "risk_level": "HIGH",
            "stages": ["ENGINEERING", "EXPERT", "APPROVAL"],
            "timeout_seconds": 3600,
        },
    )
    assert response.status_code == 201, response.text
    policy = response.json()
    response = await s.client.post(
        f"/api/v1/spaces/{s.space}/review-cases",
        headers=s.headers(initiator),
        json={
            "target_type": "CLAIM_CANDIDATE",
            "target_id": str(target),
            "policy_id": policy["id"],
            "risk_level": "HIGH",
            "reason": "Independent review of source-supported content",
        },
    )
    assert response.status_code == 202, response.text
    case = response.json()
    assert case["workflow_delivery_status"] == "PENDING"
    assert case["created_by"] == str(initiator.actor_id)
    assert case["content_revisions"][0]["original_author_id"] == str(author.actor_id)

    async def act(actor, decision="ACCEPT", changes=None):
        nonlocal case
        task = next(t for t in case["tasks"] if t["stage"] == case["current_stage"])
        r = await s.client.post(
            f"/api/v1/review-cases/{case['id']}/tasks/{task['id']}/actions",
            headers=s.headers(actor),
            json={
                "decision": decision,
                "reason": "Examined original support span",
                "change_set": changes or {},
            },
        )
        if r.status_code == 200:
            case = r.json()
        return r

    assert (await act(expert)).status_code == 403
    assert (await act(initiator, "MODIFY")).status_code == 422
    edited = await act(
        initiator, "MODIFY", {"statement": "Pump public temperature is measured at 70 degC."}
    )
    assert edited.status_code == 200, edited.text
    assert case["current_stage"] == "ENGINEERING" and len(case["content_revisions"]) == 2
    assert (await act(independent_engineer)).status_code == 200
    assert (await act(expert)).status_code == 200
    denied = await act(author)
    assert denied.status_code == 409 and denied.json()["code"] == "REVIEW_DUTY_SEPARATION", (
        denied.text
    )
    edited_approval = await act(initiator)
    assert (
        edited_approval.status_code == 409
        and edited_approval.json()["code"] == "REVIEW_DUTY_SEPARATION"
    )
    assert (await act(approver)).status_code == 200
    async with s.database.engine.connect() as c:
        claim = (
            await c.execute(
                text("SELECT statement FROM claims WHERE candidate_id=:id"), {"id": target}
            )
        ).scalar_one()
        denials = (
            (
                await c.execute(
                    text(
                        "SELECT metadata->>'reason' FROM audit_logs WHERE resource_id=:id "
                        "AND action='review.act' AND outcome='DENIED'"
                    ),
                    {"id": UUID(case["id"])},
                )
            )
            .scalars()
            .all()
        )
        assert denials.count("REVIEW_DUTY_SEPARATION") == 2
        pending = (
            await c.execute(
                text(
                    "SELECT count(*) FROM review_deliveries "
                    "WHERE review_case_id=:id AND delivered_at IS NULL"
                ),
                {"id": UUID(case["id"])},
            )
        ).scalar_one()
    assert claim == "Pump public temperature is measured at 70 degC." and pending == 2

    class RecoveredTemporal:
        def __init__(self):
            self.starts, self.commands = [], []

        async def start(self, **kwargs):
            self.starts.append(kwargs)
            return WorkflowExecutionInfo(kwargs["workflow_id"], "synthetic-temporal-run", "RUNNING")

        async def command(self, **kwargs):
            self.commands.append(kwargs)
            return {}

    recovered = RecoveredTemporal()
    await ReviewDelivery(s.repo, recovered).deliver(UUID(case["id"]))
    await ReviewDelivery(s.repo, recovered).deliver(UUID(case["id"]))
    assert len(recovered.starts) == len(recovered.commands) == 1
    assert recovered.commands[0]["action"] == "APPROVE"


@pytest.mark.parametrize("change", [None, "invalidate", "revoke", "archive", "conflict", "entity"])
async def test_final_publication_rechecks_changes_after_validation(system, change):
    from nexweave_api.errors import ApiProblem

    s = system
    async with s.database.engine.connect() as c:
        fixed = dict(
            (
                await c.execute(
                    text("SELECT * FROM release_candidates WHERE id=:id"), {"id": s.candidate}
                )
            )
            .mappings()
            .one()
        )
    suite = await s.repo.create_evaluation_suite(
        principal=s.admin,
        space_id=s.space,
        payload={
            "schema_version_id": str(fixed["schema_version_id"]),
            "suite_key": "review.io/final",
            "version": 1,
            "name": "Final gate regression",
            "minimum_pass_rate": 100,
            "cases": [
                {
                    "case_key": "control",
                    "case_type": "ANSWERABLE",
                    "question": "Pump public",
                    "expected_claim_ids": [str(s.objects[0]["claim"])],
                    "expected_terms": ["70"],
                }
            ],
        },
        idempotency_key=str(new_uuid7()),
        trace_id="test",
    )
    task = await s.put(
        "workflow_tasks",
        workflow_type="KNOWLEDGE_RELEASE",
        business_key=str(new_uuid7()),
        display_name="Synthetic publication",
        workflow_id="release-" + str(new_uuid7()),
    )
    candidate = await s.repo.create_release_candidate(
        principal=s.admin,
        space_id=s.space,
        payload={
            "version": "2.0.0",
            "schema_version_id": str(fixed["schema_version_id"]),
            "prompt_version_id": str(fixed["prompt_version_id"]),
            "model_profile_id": str(fixed["model_profile_id"]),
            "evaluation_suite_id": suite["id"],
            "claim_ids": [str(s.objects[0]["claim"])],
            "relation_ids": [],
            "wiki_page_version_ids": [],
            "index_config": {"version": "m7-r1"},
        },
        workflow_task_id=task,
        idempotency_key=str(new_uuid7()),
        trace_id="test",
    )
    cid = UUID(candidate["id"])
    summary = await s.repo.execute_release_validation(candidate_id=cid, trace_id="test")
    assert summary["evaluation_passed"], summary
    publisher = await s.user(["publisher"])
    await s.repo.record_release_approval(
        principal=publisher,
        candidate_id=cid,
        decision="APPROVED",
        reason="Checked actual question and source support",
        channel="stable",
        idempotency_key=str(new_uuid7()),
        trace_id="test",
    )
    if change == "invalidate":
        response = await s.client.post(
            f"/api/v1/source-versions/{s.objects[0]['source']}/invalidate",
            headers={**s.headers(s.admin), "If-Match": '"v1"'},
            json={
                "reason_code": "TEST",
                "reason": "Changed after approval",
                "policy_version": "test",
            },
        )
        assert response.status_code == 201, response.text
    elif change == "revoke":
        async with s.database.engine.begin() as c:
            await c.execute(
                text("UPDATE space_members SET status='REVOKED' WHERE user_identity_id=:id"),
                {"id": publisher.actor_id},
            )
    elif change == "archive":
        async with s.database.engine.begin() as c:
            await c.execute(
                text("UPDATE source_documents SET status='ARCHIVED' WHERE id=:id"),
                {"id": s.objects[0]["doc"]},
            )
    elif change == "conflict":
        await s.put(
            "conflict_cases",
            cluster_key="synthetic-late-conflict",
            kind="CONTRADICTION",
            severity="BLOCKING",
            blocking=True,
            details={},
        )

    elif change == "entity":
        new_version = await s.put(
            "knowledge_entity_versions",
            entity_id=s.objects[0]["entity"],
            compile_job_id=s.objects[1]["job"],
            revision=2,
            provenance={},
            content_checksum="sha256:" + "b" * 64,
        )
        async with s.database.engine.begin() as c:
            await c.execute(
                text(
                    "UPDATE knowledge_entities SET current_version_id=:version,"
                    "display_name='Changed confidential identity' WHERE id=:id"
                ),
                {"version": new_version, "id": s.objects[0]["entity"]},
            )

    async def publish():
        return await s.repo.publish_release(
            candidate_id=cid,
            approver_id=publisher.actor_id,
            channel="stable",
            reason="Synthetic regression",
            trace_id="test",
        )

    if change in {None, "entity"}:
        result = await publish()
        replay = await publish()
        assert result["id"] == replay["id"]
        if change == "entity":
            async with s.database.engine.connect() as c:
                frozen = (
                    await c.execute(
                        text(
                            "SELECT snapshot FROM release_items "
                            "WHERE release_id=:id AND object_type='ENTITY'"
                        ),
                        {"id": UUID(result["id"])},
                    )
                ).scalar_one()
                title = (
                    await c.execute(
                        text(
                            "SELECT title FROM release_search_documents "
                            "WHERE release_id=:id AND object_type='CLAIM'"
                        ),
                        {"id": UUID(result["id"])},
                    )
                ).scalar_one()
            assert frozen["display_name"] == title == "Pump public"
    else:
        with pytest.raises(ApiProblem) as error:
            await publish()
        assert error.value.status in {403, 404, 409}
        async with s.database.engine.connect() as c:
            count = (
                await c.execute(
                    text("SELECT count(*) FROM releases WHERE candidate_id=:id"), {"id": cid}
                )
            ).scalar_one()
        assert count == 0


async def test_late_workflow_command_and_stale_run_do_not_regress_projection(system):
    s = system
    task = await s.put(
        "workflow_tasks",
        workflow_type="HUMAN_REVIEW",
        business_key=str(new_uuid7()),
        display_name="Projection ordering regression",
        workflow_id=str(new_uuid7()),
    )
    base = {
        "task_id": str(task),
        "actor_id": str(s.admin.actor_id),
        "trace_id": "test",
        "run_id": "synthetic-run-1",
        "message": "Synthetic ordering test",
    }
    result = await s.repo.apply_projection_event(
        {
            **base,
            "event_key": "complete",
            "event_type": "RUN_SUCCEEDED",
            "status": "SUCCEEDED",
            "progress": 100,
            "step_key": "final",
            "result_summary": {"status": "APPROVED"},
        }
    )
    assert result["status"] == "SUCCEEDED"
    late = await s.repo.apply_projection_event(
        {
            **base,
            "event_key": "late-command",
            "event_type": "COMMAND_APPROVE",
            "status": "RUNNING",
            "progress": 25,
            "result_summary": {},
        }
    )
    assert late["status"] == "SUCCEEDED" and late["progress"] == 100
    assert late["result_summary"] == {"status": "APPROVED"}
    late_start = await s.repo.mark_workflow_started(
        task_id=task, run_id="synthetic-run-1", actor_id=s.admin.actor_id, trace_id="test"
    )
    assert late_start["status"] == "SUCCEEDED"
    await s.repo.mark_workflow_started(
        task_id=task,
        run_id="synthetic-run-2",
        restarted=True,
        actor_id=s.admin.actor_id,
        trace_id="test",
    )
    waiting = await s.repo.apply_projection_event(
        {
            **base,
            "run_id": "synthetic-run-2",
            "event_key": "new-wait",
            "event_type": "APPROVAL_WAITING",
            "status": "WAITING",
            "progress": 25,
        }
    )
    assert waiting["status"] == "WAITING"
    stale = await s.repo.apply_projection_event(
        {
            **base,
            "event_key": "old-complete",
            "event_type": "RUN_SUCCEEDED",
            "status": "SUCCEEDED",
            "progress": 100,
        }
    )
    assert stale["status"] == "WAITING" and stale["temporal_run_id"] == "synthetic-run-2"


async def test_legacy_open_review_requires_explicit_version_restart(system):
    from nexweave_api.errors import ApiProblem

    s = system
    policy = await s.repo.create_review_policy(
        principal=s.admin,
        space_id=s.space,
        payload={
            "risk_level": "HIGH",
            "stages": ["ENGINEERING", "EXPERT", "APPROVAL"],
            "timeout_seconds": 3600,
            "escalation_role": "space_admin",
            "allow_batch": False,
            "batch_limit": 1,
        },
        trace_id="test",
    )
    task = await s.put(
        "workflow_tasks",
        workflow_type="HUMAN_REVIEW",
        business_key=str(new_uuid7()),
        display_name="Legacy fixture",
        workflow_id=str(new_uuid7()),
    )
    case = await s.put(
        "review_cases",
        workflow_task_id=task,
        policy_id=UUID(policy["id"]),
        target_type="CLAIM_CANDIDATE",
        target_id=s.objects[0]["candidate"],
        risk_level="HIGH",
        current_stage="ENGINEERING",
        reason="Explicitly seeded pre-migration fixture",
    )
    task_ids = []
    for index, stage in enumerate(["ENGINEERING", "EXPERT", "APPROVAL"], 1):
        task_ids.append(
            await s.put(
                "review_tasks",
                review_case_id=case,
                stage=stage,
                sequence=index,
                due_at=datetime.now(UTC) + timedelta(hours=1),
            )
        )
    with pytest.raises(ApiProblem) as missing:
        await s.repo.act_on_review(
            principal=s.engineer,
            case_id=case,
            task_id=task_ids[0],
            payload={"decision": "ACCEPT", "reason": "Must not approve an unbound old version"},
            trace_id="test",
        )
    assert missing.value.code == "REVIEW_VERSION_REQUIRED"
    restarted = await s.repo.restart_review_case(
        principal=s.engineer,
        case_id=case,
        reason="Restart against the current server-side version",
        idempotency_key=str(new_uuid7()),
        trace_id="test",
    )
    assert restarted["current_stage"] == "ENGINEERING" and len(restarted["content_revisions"]) == 1
    assert restarted["content_revisions"][0]["original_author_id"] == str(s.engineer.actor_id)
    assert restarted["content_revisions"][0]["edited_by"] is None
    assert restarted["workflow_delivery_status"] == "PENDING"


async def test_graph_relation_keeps_all_source_dependencies_after_invalidation(system):
    s = system
    async with s.database.engine.connect() as c:
        fixed = dict(
            (
                await c.execute(
                    text("SELECT * FROM release_candidates WHERE id=:id"), {"id": s.candidate}
                )
            )
            .mappings()
            .one()
        )
        anchors = [
            (
                await c.execute(
                    text("SELECT source_anchor_id FROM evidence_records WHERE id=:id"),
                    {"id": o["evidence"]},
                )
            ).scalar_one()
            for o in s.objects
        ]
    target = await s.put(
        "knowledge_entities",
        schema_version_id=fixed["schema_version_id"],
        type_key="review.io/pump",
        normalized_key="public-target",
        display_name="Public downstream entity",
    )
    target_version = await s.put(
        "knowledge_entity_versions",
        entity_id=target,
        compile_job_id=s.objects[0]["job"],
        revision=1,
        provenance={},
        content_checksum=CHECKSUM,
    )
    async with s.database.engine.begin() as c:
        await c.execute(
            text("UPDATE knowledge_entities SET current_version_id=:version WHERE id=:id"),
            {"version": target_version, "id": target},
        )
    draft = await s.put(
        "candidate_relations",
        compile_job_id=s.objects[0]["job"],
        schema_version_id=fixed["schema_version_id"],
        relation_type_key="review.io/feeds",
        source_entity_id=s.objects[0]["entity"],
        target_entity_id=target,
        provenance={},
    )
    relation = await s.put(
        "relations",
        candidate_id=draft,
        schema_version_id=fixed["schema_version_id"],
        relation_type_key="review.io/feeds",
        source_entity_id=s.objects[0]["entity"],
        target_entity_id=target,
        is_causal=False,
        provenance={},
    )
    evidence = [
        await s.put(
            "evidence_records",
            relation_id=relation,
            source_anchor_id=anchor,
            stance=stance,
            excerpt_hash=CHECKSUM,
        )
        for anchor, stance in zip(anchors, ["SUPPORTS", "OPPOSES"], strict=True)
    ]
    manifest = dict(fixed["manifest"])
    listed_relations = await s.client.get(
        f"/api/v1/spaces/{s.space}/relations", headers=s.headers(s.admin)
    )
    assert listed_relations.status_code == 200, listed_relations.text
    assert listed_relations.json()["items"][0]["id"] == str(relation)
    assert "valid_until" in listed_relations.json()["items"][0]
    manifest["objects"]["relation"] = [str(relation)]
    manifest["entity_ids"].append(str(target))
    manifest["evidence_ids"] += [str(i) for i in evidence]
    task = await s.put(
        "workflow_tasks",
        workflow_type="KNOWLEDGE_RELEASE",
        business_key=str(new_uuid7()),
        display_name="Explicit graph fixture",
        workflow_id=str(new_uuid7()),
    )
    candidate = await s.put(
        "release_candidates",
        version="3.0.0",
        schema_version_id=fixed["schema_version_id"],
        composition_checksum=CHECKSUM,
        prompt_version_id=fixed["prompt_version_id"],
        model_profile_id=fixed["model_profile_id"],
        evaluation_suite_id=s.suite,
        workflow_task_id=task,
        workflow_id=str(new_uuid7()),
        manifest=manifest,
        manifest_checksum=CHECKSUM,
        index_config={},
    )
    release = await s.put(
        "releases",
        candidate_id=candidate,
        version="3.0.0",
        manifest=manifest,
        manifest_checksum=CHECKSUM,
        schema_version_id=fixed["schema_version_id"],
        composition_checksum=CHECKSUM,
        prompt_version_id=fixed["prompt_version_id"],
        model_profile_id=fixed["model_profile_id"],
        index_config={},
        published_by=s.admin.actor_id,
    )
    async with s.database.engine.begin() as c:
        candidate_row = (
            (
                await c.execute(
                    text("SELECT * FROM release_candidates WHERE id=:id"), {"id": candidate}
                )
            )
            .mappings()
            .one()
        )
        await s.repo._persist_release_items(c, release, candidate_row)
    low, high = await s.user(["consumer"], member_clearance="INTERNAL"), await s.user(["consumer"])

    async def graph(actor):
        r = await s.client.get(
            f"/api/v1/releases/{release}/graph/traverse",
            headers=s.headers(actor),
            params={"start_entity_id": str(s.objects[0]["entity"])},
        )
        assert r.status_code == 200, r.text
        return r.json()

    assert not (await graph(low))["edges"]
    assert len((await graph(high))["edges"]) == 1
    invalidated = await s.client.post(
        f"/api/v1/source-versions/{s.objects[1]['source']}/invalidate",
        headers={**s.headers(s.admin), "If-Match": '"v1"'},
        json={
            "reason_code": "TEST",
            "reason": "High opposing source withdrawn",
            "policy_version": "test",
        },
    )
    assert invalidated.status_code == 201, invalidated.text
    # The lower supporting source alone must not expose the compound relation.
    assert not (await graph(low))["edges"] and not (await graph(high))["edges"]


async def test_immutable_wiki_version_has_real_independent_review_and_release_gate(system):
    s = system
    original = s.objects[0]
    async with s.database.engine.connect() as c:
        row = dict(
            (
                await c.execute(
                    text("SELECT * FROM wiki_page_versions WHERE id=:id"),
                    {"id": original["page_version"]},
                )
            )
            .mappings()
            .one()
        )
    async with s.database.engine.begin() as c:
        await c.execute(
            text(
                "UPDATE source_versions SET active_parse_job_id=(SELECT parse_job_id "
                "FROM source_anchors WHERE source_version_id=:source LIMIT 1) "
                "WHERE id=:source"
            ),
            {"source": original["source"]},
        )
    author = await s.user(["knowledge_engineer", "publisher"])
    row.update(
        id=new_uuid7(),
        revision=2,
        status="AI_DRAFT",
        created_by=author.actor_id,
        markdown="# Pump public\n\nTemperature is 70 degC.",
        content_checksum="sha256:" + "c" * 64,
    )
    version_id = await s.put("wiki_page_versions", **row)
    engineer = await s.user(["knowledge_engineer"])
    expert = await s.user(["reviewer"])
    approver = await s.user(["publisher"])
    policy = await s.client.post(
        f"/api/v1/spaces/{s.space}/review-policies",
        headers=s.headers(s.admin),
        json={
            "risk_level": "HIGH",
            "stages": ["ENGINEERING", "EXPERT", "APPROVAL"],
            "timeout_seconds": 3600,
        },
    )
    assert policy.status_code == 201, policy.text
    response = await s.client.post(
        f"/api/v1/spaces/{s.space}/review-cases",
        headers=s.headers(engineer),
        json={
            "target_type": "WIKI_PAGE_VERSION",
            "target_id": str(version_id),
            "policy_id": policy.json()["id"],
            "risk_level": "HIGH",
            "reason": "Review complete immutable page against source context",
        },
    )
    assert response.status_code == 202, response.text
    case = response.json()
    assert case["target_context"]["content"]["markdown"] == row["markdown"]
    assert case["target_context"]["evidence"]

    async def act(actor):
        nonlocal case
        task = next(t for t in case["tasks"] if t["stage"] == case["current_stage"])
        r = await s.client.post(
            f"/api/v1/review-cases/{case['id']}/tasks/{task['id']}/actions",
            headers=s.headers(actor),
            json={"decision": "ACCEPT", "reason": "Checked all page sections and current anchors"},
        )
        if r.status_code == 200:
            case = r.json()
        return r

    assert (await act(expert)).status_code == 403
    assert (await act(engineer)).status_code == 200
    assert (await act(expert)).status_code == 200
    denied = await act(author)
    assert denied.status_code == 409 and denied.json()["code"] == "REVIEW_DUTY_SEPARATION"
    assert (await act(approver)).status_code == 200
    assert case["status"] == "APPROVED"
    async with s.database.engine.connect() as c:
        unchanged = (
            (
                await c.execute(
                    text(
                        "SELECT status,markdown,content_checksum FROM wiki_page_versions "
                        "WHERE id=:id"
                    ),
                    {"id": version_id},
                )
            )
            .mappings()
            .one()
        )
        assert unchanged["status"] == "AI_DRAFT" and unchanged["markdown"] == row["markdown"]
        fixed = dict(
            (
                await c.execute(
                    text("SELECT * FROM release_candidates WHERE id=:id"), {"id": s.candidate}
                )
            )
            .mappings()
            .one()
        )
    manifest = dict(fixed["manifest"])
    manifest["objects"] = {**manifest["objects"], "wiki_page_version": [str(version_id)]}
    manifest["source_refs"] = [{"source_version_id": str(original["source"])}]
    fixed["id"], fixed["manifest"] = s.candidate, manifest
    async with s.database.engine.begin() as c:
        findings = await s.repo._lint_candidate(c, fixed)
        assert not any(f["code"] == "PAGE_NOT_APPROVED" for f in findings)
    # A fresh version requires its own case, even when the previous version passed.
    unreviewed = await s.put(
        "wiki_page_versions",
        **{**row, "id": new_uuid7(), "revision": 3, "content_checksum": "sha256:" + "d" * 64},
    )
    fixed["id"] = s.candidate
    fixed["manifest"]["objects"]["wiki_page_version"] = [str(unreviewed)]
    async with s.database.engine.begin() as c:
        findings = await s.repo._lint_candidate(c, fixed)
        assert any(f["code"] == "PAGE_NOT_APPROVED" for f in findings)


async def test_manifest_entity_version_comes_from_selected_content_not_unselected_compile(system):
    from nexweave_api.derived_reads import DerivedReadGate
    from nexweave_api.release_manifest import freeze_selected_entities

    s = system
    selected, unselected = s.objects
    replacement = await s.put(
        "knowledge_entity_versions",
        entity_id=selected["entity"],
        compile_job_id=unselected["job"],
        revision=2,
        provenance={},
        content_checksum="sha256:" + "e" * 64,
    )
    async with s.database.engine.begin() as c:
        expected = await c.scalar(
            text("SELECT current_version_id FROM knowledge_entities WHERE id=:id"),
            {"id": selected["entity"]},
        )
        await c.execute(
            text("UPDATE knowledge_entities SET current_version_id=:v WHERE id=:id"),
            {"v": replacement, "id": selected["entity"]},
        )
    reader = await s.user(["consumer"], member_clearance="INTERNAL")
    reader = await s.repo.principal_for_space(
        principal=reader, space_id=s.space, action="query.release"
    )
    async with s.database.engine.connect() as c:
        frozen = await freeze_selected_entities(
            c,
            s.admin.tenant_id,
            s.space,
            {selected["entity"]},
            {"CLAIM": [selected["claim"]], "RELATION": [], "WIKI_PAGE_VERSION": []},
        )
        snapshot = frozen[str(selected["entity"])]
        assert snapshot["current_version_id"] == str(expected)
        gate = DerivedReadGate(c, reader, s.space)
        assert not await gate.can_read("ENTITY", selected["entity"])
        assert await gate.can_read("ENTITY", selected["entity"], snapshot)
