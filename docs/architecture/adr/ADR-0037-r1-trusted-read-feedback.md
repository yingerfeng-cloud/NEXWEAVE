# ADR-0037：R1 可信读取与流程反馈

Status: Accepted for the R1 follow-up UX and contract hardening.
Date: 2026-09-14.

## Context

The supervised R1 walkthrough exposed three different classes of outcome that
the Web surface collapsed into the same message: a committed mutation followed
by a refresh failure, a still-loading compile resource list, and a query that
had either no matching published knowledge or no evidence that passed the
fixed-Release read gates. The resulting UI could make a successful operation
look like a network failure and required users to infer governance meaning from
technical fields.

## Decision

1. Space creation acknowledges the committed `POST` immediately, selects the
   returned space, and reports a subsequent directory refresh failure as a
   separate recoverable condition. The UI must not invite a duplicate create.
2. Compile resource reads are independently projected. A temporary failure in
   jobs, schemas, sources, prompts, or model profiles must not hide resources
   that were read successfully. Until the first response completes, the UI
   shows a loading state instead of an empty-state claim.
3. `QueryAnswerResponse` receives the additive response-only `answer_reason`
   code. It distinguishes supported evidence, no matching published
   knowledge, an evidence/anchor gate failure, and historical revalidation
   outcomes. The code never confirms the existence of objects hidden by
   permissions. Existing `query_answers` rows and Release/Evidence semantics
   remain unchanged; historical reads derive the code at read time.
4. Ask displays a plain-language explanation and next action for every answer,
   and citation cards retain a direct, server-authorized source-preview route.
   Compile and governance pages expose the next human step and gate meaning in
   the normal view while keeping raw IDs and trace details expandable.

## Consequences

- No database migration, new dependency, model-provider change, or new domain
  object is introduced.
- The additive response field is optional for older clients; generated JSON
  Schema, OpenAPI, and typed SDK projections are updated together.
- `answer_reason` is an explanation of the read result, not a confidence score,
  causal statement, Evidence record, or Release mutation.
- The changes improve local R1 software usability and observability. They do
  not establish M9 expert approval, industrial accuracy, or a general natural
  language retrieval benchmark.

## Follow-up verification · 2026-09-14

- Reset Compile resource/selection state when the workspace changes; clear
  resources whose refresh fails and block submission while loading.
- Clear source previews before reauthorization and ignore superseded responses.
- Reject whitespace-only QueryCreate.question at the contract boundary (422).
  Preserve nonblank question text and existing idempotency comparison semantics.
- These corrections do not alter Release/Evidence authority or persisted answers.
