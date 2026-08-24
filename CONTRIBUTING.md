# Contributing to NEXWEAVE

## Before changing the repository

1. Read `AGENTS.md`, `docs/INDEX.md`, the current Milestone, accepted ADRs, and the previous execution report.
2. Confirm that the requested work is inside the current Milestone.
3. Inspect the working tree and preserve user changes.
4. Update requirement traceability before implementation planning.

## Change requirements

- Core objects, states, versions, API, events, Workflow, SourceAnchor and Release semantics require an ADR.
- Domain and contracts remain independent of frameworks and vendors.
- Product behavior requires tests, documentation, audit/error handling, and migration impact analysis.
- New dependencies require purpose, locked version, license, security risk, and alternative.
- Never commit credentials or real sensitive pilot data.

## Review gates

Changes must satisfy `docs/governance/QUALITY_GATES.md` and `docs/governance/SECURITY_BASELINE.md`. A Milestone is not complete until its requirement rows, test evidence, migrations, documentation, and execution report agree with the repository.

## Git

- Use the contributor's real configured Git identity.
- Do not rewrite history, reset user changes, auto-push, or create remotes without explicit approval.
- Keep commits scoped to one reviewable concern when commits are authorized.
