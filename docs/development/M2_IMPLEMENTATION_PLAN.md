# NEXWEAVE M2 Implementation Plan

> Status: IMPLEMENTED — AWAITING USER ACCEPTANCE. User formally accepted M1 and dispatched M2 on 2026-08-24. Implementation is stopped at the M2 boundary and does not authorize M3 work.

| Workstream | M2 outcome | Verification |
|---|---|---|
| Workflow contracts | Stable task/workflow/run IDs, seven workflow types, states, commands, steps and events | domain + contract tests |
| Temporal runtime | Dedicated namespace, workflow/activity queues and non-root kernel Worker | real Compose health/E2E |
| Determinism | Workflow code contains no DB/network/file/model I/O; I/O isolated in Activities | architecture + replay tests |
| Reliability | timeout/retry/non-retryable policy, heartbeat, pause/resume/cancel, compensation and duplicate command handling | time skipping + fault/restart E2E |
| Projection | PostgreSQL task/step/event projection, audit/outbox, lag/reconciliation and repair | migration + DB/E2E |
| Task API/SDK | create/list/detail/command/reconcile with authorization, idempotency, ETag and stable errors | OpenAPI/event/SDK tests |
| Task center Web | real task list/detail/steps/logs/actions, deep-link recovery, empty/loading/error/retry states | UI + E2E |

## Completion note

- The seven Workflow types, dedicated queues/Worker, PostgreSQL projections, authorization, audit/Outbox, reconciliation, OpenAPI/events/SDK and real task center are implemented.
- Real Temporal E2E covers all seven types, Activity retry, duplicate Update, approval, pause/resume, cancel/compensation, projection repair, Worker restart and event-history replay.
- The official SDK time-skipping test passed locally and as an independent Linux x64 gate in GitHub Actions run `32808198635`; the former external test-server initialization condition is closed.

## Explicit exclusions

- Workflow Activities in M2 are kernel stubs/projection facts only; they do not create SourceVersion, compiled knowledge, ReviewAction, Release, Pack installation or GridCrew intake business objects.
- No parser, model, Connector, publication, Evidence or Domain Pack execution is introduced.
- Database projections do not advance Temporal execution state independently.
