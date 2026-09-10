# NEXWEAVE M7 Runbook

## 1. Scope and boundary

This runbook operates the M7 Quality Center, immutable Release, PostgreSQL FTS/pgvector projection, graph traversal and trusted query capabilities. It does not authorize M8 Connector/GridCrew work. Production promotion still requires the normal CI, image, secret-provider, OIDC and deployment approvals.

## 2. Start and health

```bash
make dev-up
docker compose ps
curl --fail http://127.0.0.1:8000/api/v1/health/ready
curl --fail http://127.0.0.1:8000/api/v1/version
```

The API reports milestone `M7`. Temporal must have kernel Workflow and Activity workers. PostgreSQL must be at Alembic head `0008_m7_quality_release_query` with the vector extension available.

## 3. Quality and publication procedure

1. Create an EvaluationSuite bound to a PUBLISHED SchemaVersion. Include answerable, unanswerable/counterfactual, conflict, multi-source and insufficient-evidence cases as appropriate.
2. Create a ReleaseCandidate with explicit Claim/Relation/WikiPageVersion IDs and fixed SchemaVersion, composition checksum, PromptVersion, ModelProfile, Suite and index configuration.
3. Wait for KnowledgeRelease v2 validation. `PENDING_APPROVAL` requires 100% traceability, 100% Schema compliance, no blocking lint, no unresolved blocking conflict and a passed EvaluationRun.
4. A different user holding `publisher` approves. The candidate creator cannot approve their own Release.
5. Publication atomically creates the immutable Release/Items, projection, pointer history, audit and Outbox facts.

Failed or rejected candidates remain historical. Fixes create a new candidate and SemVer; published Release rows/items are never edited.

## 4. Query and graph operation

- Every query URL contains an explicit Release ID. Reusing the same actor/client-request ID returns the recorded answer.
- Completed answers require visible accepted Evidence and a VALID SourceAnchor. Otherwise the service returns `REFUSED` without citations.
- Keyword and semantic ranks are fused with RRF. Vector similarity is retrieval evidence only, never factual confidence.
- Graph traversal is bounded to depth 1—5 and filters relation Evidence, Anchor status, classification, causal flag and optional time slice.

## 5. Export, projection rebuild and rollback

- `GET /releases/{release_id}/export?format=json|markdown` exports immutable metadata and item snapshots.
- `POST /releases/{release_id}/projections/rebuild` rebuilds FTS/vector projection from the fixed Release; it does not change the manifest checksum.
- Rollback reads the channel pointer version and posts the historical target with `If-Match: "vN"`. It appends pointer history and never mutates either Release.
- Deprecation appends a reason and optional replacement; it does not delete history.

## 6. Verification

```bash
export PYTHONPATH="apps/api/src:packages/domain/src:packages/contracts/src:packages/application/src:workers/kernel/src"
.venv/bin/ruff check .
.venv/bin/mypy apps/api/src packages/domain/src packages/contracts/src packages/application/src workers/kernel/src
.venv/bin/pytest -q
pnpm --filter @nexweave/web test
pnpm --filter @nexweave/web build
.venv/bin/python scripts/check_migrations.py
```

The true M7 E2E verifier accepts `--base-url`, `--space-id` and `--claim-id`. Run it only in an isolated database/task queue or a purpose-created disposable acceptance space; it deliberately publishes two immutable versions and moves a Release pointer.

## 7. Diagnosis and recovery

- Candidate `FAILED`: inspect gate summary, lint findings, EvaluationRun results, conflicts and Evidence/Anchor status; create a corrected candidate.
- Approval rejected: confirm the candidate is `PENDING_APPROVAL`, the actor is a Publisher and differs from the creator.
- Empty/refused query: verify the requested Release contains both Claim and accepted Evidence, Anchor is VALID and caller clearance covers the source classification.
- Projection issue: rebuild from Release and compare manifest checksum before/after. Do not repair by editing ReleaseItem.
- Pointer conflict: reload the current pointer and retry with its strong ETag. Never force an update.

## 8. Stop boundary

M7 completion does not authorize M8. Do not add Connector execution, GridCrew integration or feedback intake until the user explicitly dispatches M8.
