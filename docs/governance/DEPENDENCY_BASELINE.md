# M3 Dependency and Supply-chain Baseline

> M3 implementation adds only the isolated Parser Worker document libraries and the real ClamAV service described below. Preview is plain text, so the unused `nh3` dependency was removed. No real OCR Provider is selected.

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
| PyJWT / cryptography | 2.13.0 / 50.0.0 | OIDC-compatible token verification and local development signing | MIT / Apache-2.0 or BSD | identity adapter only; Authlib alternative; production uses an asymmetric algorithm allowlist |
| boto3 / botocore | 1.43.78 / 1.43.78 | RustFS/S3 `ObjectStoragePort` adapter | Apache-2.0 | adapter only; MinIO SDK or controlled HTTP alternative |
| OpenTelemetry SDK/exporter | 1.44.0 | trace, metric and log export | Apache-2.0 | bootstrap/adapter only; structured logs and Prometheus/manual instrumentation alternatives |
| OpenTelemetry FastAPI/SQLAlchemy/logging instrumentation | 0.65b0 | Web/API/DB trace correlation | Apache-2.0 | pre-1.0 contrib family pinned and isolated; manual instrumentation fallback |
| greenlet | 3.5.5 | SQLAlchemy async bridge | MIT | persistence adapter transitive runtime requirement |
| protobuf | 7.36.0 | compatible OTel/Temporal wire lock | BSD-3-Clause | transitive version constrained for both dependency families |
| pypdf | 6.16.2 | PDF structure/page/text-layer and encryption detection | BSD-3-Clause | Parser Worker only; `pdfminer.six` is the review-required alternative |
| python-docx | 1.2.0 | DOCX paragraphs, styles and tables | MIT | Parser Worker only; a bounded direct OOXML adapter is the removal alternative |
| openpyxl | 3.1.5 | XLSX read-only/data-only sheet and cell parsing | MIT | Parser Worker only; a reviewed calamine adapter is the alternative |
| lxml | 6.1.2 | `python-docx` XML runtime | BSD-3-Clause | locked transitive dependency; direct bounded XML parsing is the alternative |
| et_xmlfile | 2.0.0 | `openpyxl` OpenXML support | MIT | locked transitive dependency; follows the XLSX adapter |

Development-only packages remain exact-pinned: jsonschema 4.25.1, mypy 1.17.1, pip-audit 2.9.0, pytest 8.4.1, pytest-asyncio 1.1.0 and Ruff 0.12.10. Boto3 moved to runtime in M1 because it now implements the real S3 adapter; it remains outside domain/contracts/application, which depend only on `ObjectStoragePort`.

M1 supply-chain controls remain in force: token algorithms are configured rather than inferred from untrusted headers; S3 credentials are runtime configuration and never business-row data; telemetry excludes tokens, credentials and object bodies; externally hosted model profiles store only `credential_ref`. M2 adds no new direct dependency: the already pinned Temporal Python SDK `1.31.0` now powers the dedicated kernel Worker, Workflow Replayer and official time-skipping test API. The SDK remains confined to the API/Worker adapters; `domain`, `contracts` and application Ports stay vendor-neutral. Replacement with another durable execution engine requires ADR and history/compatibility migration rather than a package swap.

M3 confines `pypdf`, `python-docx`, `openpyxl` and their transitive XML libraries to `workers/parser`. The credentialed coordinator does not import the parser implementation; actual third-party parsing is invoked through a bounded framed protocol in the credential-free `parser-sandbox` service, which has no DB/object-store/Temporal/ClamAV credentials and only a dedicated internal IPC network. The adapter never executes macros, scripts, external relationships or embedded executables. OOXML is bounded by path/encryption/compression policy, duplicate/entry count, per-entry and total expansion, compression ratio, rows/columns and output budgets. Target-platform amd64/arm64 wheel availability—especially `lxml`—must be proven by the image build gate; a development-machine install is not multi-architecture evidence. Offline deployment must pre-stage the exact locked wheels.

## JavaScript direct dependencies

| Package group | Version | Purpose | License / alternative |
|---|---:|---|---|
| React / React DOM | 19.1.1 | authenticated platform shell, administration UI and M2 task center | MIT; standards-based Web Components are the removal alternative |
| Vite / React plugin | 7.3.6 / 5.2.0 | build tool | MIT; Rollup/custom build alternative |
| TypeScript | 5.9.2 | static typing | Apache-2.0 |
| Vitest / Testing Library / jsdom | 3.2.4 / 16.3.0 / 26.1.0 | UI tests | MIT; development only |
| ESLint / TypeScript ESLint | 9.34.0 / 8.41.0 | lint | MIT; development only |
| Prettier | 3.6.2 | formatting | MIT; development only |

pnpm 11 blocks lifecycle scripts by default. M0 explicitly allows only `esbuild`; additions require this file, lockfile and CI review to change together.

## Container dependencies

M2 Compose retains the accepted pinned Python 3.12.13, Node 24.19.0, Nginx 1.31.4/Alpine 3.24, pgvector 0.8.6/PostgreSQL 17, Redis 7.4.11, RustFS `1.0.0-rc.4`, and Temporal 1.29.6 images. Python, Node and Nginx Dockerfiles additionally pin the accepted OCI indexes `sha256:4766d8b510c428e595d74b9cc5bbb2fae8e26316fffb4adc89908d79aacd58a2`, `sha256:244cc2b53f46f9e876304391d17682b0ddae9ac33491f4857e25e35a36ba7995` and `sha256:db35bfc6b2951e7f8a72db5db120288c127ffaeeb4a6d4b95a26fead017d5913`; the Web runtime also refreshes Alpine packages at build time to receive fixed security packages. RustFS is Apache-2.0 licensed. The optional Temporal UI remains outside the acceptance surface. The M2 kernel Worker uses the same reviewed Python base and locked runtime set. M3 uses real ClamAV `1.4.3`, GPL-2.0 licensed, through clamd INSTREAM; unavailable, ambiguous or failed scan results fail closed. Because the development network cannot connect to Docker Hub Registry or its authentication endpoint, Compose builds `nexweave-clamav:1.4.3-deb12u2` from the already approved Python 3.12.13/Debian 12 base digest and installs exact Debian security package versions `clamav-daemon=1.4.3+dfsg-1~deb12u2` and `clamav-freshclam=1.4.3+dfsg-1~deb12u2` from the official Debian repository. FreshClam must update the persistent signature volume before clamd starts. This changes packaging provenance, not the scanner Provider or policy; the upstream `clamav/clamav:1.4.3` image remains the removal alternative when Docker Hub is reachable. On 2026-08-29 the running service reported ClamAV 1.4.3 with daily 28106, main 63 and bytecode 339, and the local ARM64 image passed Trivy 0.74.0 with zero fixable HIGH/CRITICAL findings using the current GHCR database. FreshClam also reported that upstream 1.4.6 is available; 1.4.3 remains deliberately locked to the approved M3 taskbook and any upgrade requires an isolated dependency change. Multi-architecture build, SBOM and signature evidence remain production-promotion gates.

RustFS `1.0.0-rc.4` is tied to official Git tag commit `44f3f0e73ef4ced4dc6674df8c467071d67f324b`. The official Quay OCI index was verified on 2026-08-29: index digest `sha256:a9fbb5e5bfce09ccd0869ac9a7b0e39191c6868d75ec4c5d08ebbd5475db5d6b`, `linux/amd64` digest `sha256:6c063491cb01e6e8c0cc605c3806542f288dd3925519225d32c0bdd97630d834`, and `linux/arm64` digest `sha256:93684db5b4878907b46ca224a3c05c1aec7123b44dc89e29b369c6d77c3e28a5`. The official RC4 index was fetched and a local amd64 Trivy 0.74.0 scan found zero fixable HIGH/CRITICAL vulnerabilities; full SPK-004 and CI evidence remain required. Cosign found no upstream signature or SBOM artifacts on the index; NEXWEAVE signs the exact digest as internal approval only. RustFS is still an RC; distributed/HA and production DR claims remain gated by later Milestones.

The container gate uses official Trivy `0.74.0` at index `sha256:62b1e65e8869bc4b4c6aa4fa2b21595256c7c2f6018a9d9ad61caf87187c1969` and Cosign `3.0.2`. All third-party GitHub Actions are pinned to immutable commit SHAs. The policy rejects fixable HIGH/CRITICAL findings; exceptions require separate time-bounded approval and must not be implemented as an unreviewed global ignore.

The 2026-08-29 result above is a real local ARM64 image CVE scan, not multi-architecture promotion evidence. Acceptance must retain the actual `pip-audit`, CycloneDX/SBOM, container CVE and provenance outputs. Any fixable unapproved HIGH/CRITICAL result blocks M3. No OCR model, language pack or Provider may be claimed until its version, model origin, license, maintenance, CPU/memory, offline and replacement plan is added here and verified end-to-end.

## Update and removal rule

Renovation is deliberate, one dependency family per change. CI must pass format, lint, typecheck, unit, contract, migration, Web build, dependency audit and real Compose verification. Domain/contracts/Workflow code must never absorb a dependency merely because an adapter already uses it.
