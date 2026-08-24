# M0 Dependency and Supply-chain Baseline

All direct dependencies are exact-version pinned in `requirements/*.txt`, `package.json`, `pnpm-lock.yaml` and `compose.yaml`. Transitive JavaScript dependencies are integrity-locked by pnpm. Application Dockerfiles pin both the human-readable base-image version and the reviewed OCI index digest; production promotion consumes immutable multi-architecture digests rather than mutable tags.

## Python direct dependencies

| Package | Version | Purpose | License | Boundary / alternative |
|---|---:|---|---|---|
| FastAPI | 0.141.1 | HTTP platform shell | MIT | API adapter only; Starlette/custom ASGI alternative |
| Pydantic / pydantic-settings | 2.11.7 / 2.10.1 | Contract and validated config | MIT | contracts/config; dataclasses + jsonschema alternative |
| SQLAlchemy / Alembic | 2.0.43 / 1.16.4 | DB adapter and migrations | MIT | never imported by domain/contracts; SQL migration alternative |
| asyncpg | 0.30.0 | PostgreSQL async driver | Apache-2.0 | adapter only; psycopg alternative |
| temporalio | 1.31.0 | reliable Worker boundary | MIT | Worker only; replacement requires ADR; upgraded after container scanning found fixed HIGH advisories in the 1.17.0 embedded Rust bridge |
| redis | 6.4.0 | readiness and future cache adapter | MIT | adapter only; removable if cache is not needed |
| HTTPX | 0.28.1 | object-storage health and future controlled HTTP adapters | BSD-3-Clause | boundary only; aiohttp alternative |
| Uvicorn | 0.35.0 | ASGI runtime | BSD-3-Clause | deployment adapter; another ASGI server alternative |

Development-only packages are exact-pinned: boto3 1.43.78 (SPK-004 S3 compatibility client, Apache-2.0), jsonschema 4.25.1, mypy 1.17.1, pip-audit 2.9.0, pytest 8.4.1, pytest-asyncio 1.1.0 and Ruff 0.12.10. They do not ship in runtime images. Boto3 remains outside domain/contracts and is not the future `ObjectStoragePort` contract.

## JavaScript direct dependencies

| Package group | Version | Purpose | License / alternative |
|---|---:|---|---|
| React / React DOM | 19.1.1 | M0 status Web shell | MIT; standards-based Web Components are the removal alternative |
| Vite / React plugin | 7.3.6 / 5.2.0 | build tool | MIT; Rollup/custom build alternative |
| TypeScript | 5.9.2 | static typing | Apache-2.0 |
| Vitest / Testing Library / jsdom | 3.2.4 / 16.3.0 / 26.1.0 | UI tests | MIT; development only |
| ESLint / TypeScript ESLint | 9.34.0 / 8.41.0 | lint | MIT; development only |
| Prettier | 3.6.2 | formatting | MIT; development only |

pnpm 11 blocks lifecycle scripts by default. M0 explicitly allows only `esbuild`; additions require this file, lockfile and CI review to change together.

## Container dependencies

M0 Compose pins Python 3.12.13, Node 24.19.0, Nginx 1.31.4/Alpine 3.24, pgvector 0.8.6/PostgreSQL 17, Redis 7.4.11, RustFS `1.0.0-rc.3`, and Temporal 1.29.6. Python, Node and Nginx Dockerfiles additionally pin OCI indexes `sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2`, `sha256:244cc2b53f46f9e876304391d17682b0ddae9ac33491f4857e25e35a36ba7995` and `sha256:db35bfc6b2951e7f8a72db5db120288c127ffaeeb4a6d4b95a26fead017d5913`. RustFS is Apache-2.0 licensed. The optional Temporal UI is excluded from the M0 acceptance surface. These images process synthetic/local M0 state only.

RustFS `1.0.0-rc.3` is tied to official Git tag commit `1aae6803739a5bac67e0d702ac46d43f09fb06dd`. The official Quay OCI index was verified on 2026-08-24: index digest `sha256:800cf3f352a0a27e3275ca854a51f0027975d7acc7a0d52089a35bcc9fcbf0b5`, `linux/amd64` digest `sha256:1aba56126e19f6b0791560710251c946ef0674b6a5130ae9889c3b15208dd0fb`, and `linux/arm64` digest `sha256:97801eaeb7d22d9138230b273bff2e1539b81c42fa5be56d94ff0ce8ccfb59b3`. The native ARM64 image was pulled successfully and a disposable container verified non-root UID/GID `10001:10001` can write `/data`. Cosign found no upstream signature or SBOM artifacts on that index; attestation-shaped manifests alone are not treated as provenance. SPK-004 S3 compatibility/recovery passed and the ARM64 Trivy 0.74.0 gate found zero fixable HIGH/CRITICAL vulnerabilities. GitHub CI therefore copies only the exact index into GHCR, validates both architectures, generates per-architecture CycloneDX/CVE evidence and signs the digest as a NEXWEAVE internal approval. RustFS is still an RC; distributed/HA and production DR claims remain gated by later Milestones.

The container gate uses official Trivy `0.74.0` at index `sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969` and Cosign `3.0.2`. All third-party GitHub Actions are pinned to immutable commit SHAs. The policy rejects fixable HIGH/CRITICAL findings; exceptions require separate time-bounded approval and must not be implemented as an unreviewed global ignore.

## Update and removal rule

Renovation is deliberate, one dependency family per change. CI must pass format, lint, typecheck, unit, contract, migration, Web build, dependency audit and real Compose verification. Domain/contracts/Workflow code must never absorb a dependency merely because an adapter already uses it.
