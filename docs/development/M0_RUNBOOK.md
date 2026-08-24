# M0 Local Runbook

## Prerequisites

- Docker Desktop with Compose support.
- Python 3 for the credential bootstrap; Python 3.12 for local Python checks.
- Node 22.12+ and pnpm 11.19 for local Web checks.

## Start the complete M0 baseline

```bash
make dev-up
```

The command creates an ignored `.env` with random local credentials (mode `0600`) if one does not exist, builds the API/Worker/Web images, applies Alembic migrations and waits for healthy services. It never overwrites an existing `.env`.

Open:

- Web status shell: `http://localhost:8080`
- API readiness: `http://localhost:8000/api/v1/health/ready`
- API docs: `http://localhost:8000/api/docs`
- RustFS console: `http://localhost:9001` (local generated credentials are in the ignored `.env`)

M0 deliberately does not run the optional Temporal UI container. Temporal is verified through its
health command and a real Workflow execution, which keeps the minimum environment smaller and avoids
making an administrative UI part of the platform acceptance surface.

RustFS runs as non-root UID/GID `10001:10001` and writes its image-declared `/data` volume. The runtime
is fixed to the verified official Quay multi-architecture index for `1.0.0-rc.3`; do not replace it
with `latest`. Production promotion remains blocked until SPK-004 verifies the required S3 subset,
recovery, image signatures/SBOM and both target architectures.

## Verify

```bash
make verify
make migration-check
```

`make verify` performs a real Web/API/PostgreSQL/Redis/RustFS/Temporal/Worker chain and verifies the database is at migration head. `make migration-check` destroys and rebuilds M0 tables in the disposable local database; do not use it against shared data. `make PYTHON=.venv/bin/python rustfs-spike` runs the synthetic SPK-004 S3/restart/backup matrix, writes an ignored local receipt and removes its temporary buckets.

## Stop

```bash
make dev-down
```

This preserves local named volumes. `docker compose down --volumes` intentionally destroys the disposable M0 data and must only be used when that result is desired.

## Diagnostics

- `docker compose ps`: container health.
- `make dev-logs`: API, Worker and Web logs.
- The public `/api/v1/config/diagnostics` response is sanitized and never returns passwords, tokens or credentials.
- If a host port is already in use, stop the conflicting local service or explicitly revise the development port mapping; do not silently point M0 at an unapproved remote system.
- If image pulls stall, verify the relevant official registry. RustFS is pinned to its official Quay multi-architecture digest; PostgreSQL/pgvector, Redis, Temporal, Python, Node and Nginx remain pinned to their official image sources. Do not substitute an unreviewed mirror.

## M0 boundary

The Web shell and health workflow are engineering verification only. No Source, Schema, Compile, Review, Release, Query, GridCrew or RCA business capability is implemented by this runbook.
