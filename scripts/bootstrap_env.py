"""Create ignored local Compose credentials without overwriting an existing environment."""

from __future__ import annotations

from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def main() -> None:
    if ENV_FILE.exists():
        existing = ENV_FILE.read_text(encoding="utf-8")
        additions: list[str] = []
        if "NEXWEAVE_LOCAL_DEV_SIGNING_KEY=" not in existing:
            additions.extend(
                [
                    "# Added for the local-only M1 identity provider.",
                    "NEXWEAVE_IDENTITY_PROVIDER=local",
                    "NEXWEAVE_OIDC_AUDIENCE=nexweave-api",
                    "NEXWEAVE_LOCAL_DEV_IDENTITY_ENABLED=true",
                    f"NEXWEAVE_LOCAL_DEV_SIGNING_KEY={token_urlsafe(48)}",
                    "NEXWEAVE_LOCAL_DEV_SUBJECT=local-admin",
                    "NEXWEAVE_LOCAL_DEV_TENANT_SLUG=local",
                ]
            )
        if "NEXWEAVE_TEMPORAL_WORKFLOW_TASK_QUEUE=" not in existing:
            additions.extend(
                [
                    "# Added for the M2 reliable-workflow kernel.",
                    "NEXWEAVE_TEMPORAL_WORKFLOW_TASK_QUEUE=nexweave-m2-workflows",
                    "NEXWEAVE_TEMPORAL_ACTIVITY_TASK_QUEUE=nexweave-m2-activities",
                ]
            )
        if additions:
            separator = "" if existing.endswith("\n") else "\n"
            ENV_FILE.write_text(
                existing + separator + "\n".join(additions) + "\n", encoding="utf-8"
            )
            ENV_FILE.chmod(0o600)
            print("added missing M1 local identity settings to .env")
        else:
            print(".env already contains the required settings; leaving it unchanged")
        return

    postgres_password = token_urlsafe(32)
    object_store_secret = token_urlsafe(32)
    local_dev_signing_key = token_urlsafe(48)
    encoded_password = quote(postgres_password, safe="")
    content = "\n".join(
        [
            "# Generated for local M2 Compose only. This file is ignored by Git.",
            "NEXWEAVE_ENV=development",
            "NEXWEAVE_LOG_LEVEL=INFO",
            "NEXWEAVE_BUILD_VERSION=0.3.0-m2",
            "NEXWEAVE_POSTGRES_DB=nexweave",
            "NEXWEAVE_POSTGRES_USER=nexweave",
            f"NEXWEAVE_POSTGRES_PASSWORD={postgres_password}",
            "NEXWEAVE_DATABASE_URL="
            f"postgresql+asyncpg://nexweave:{encoded_password}@postgres:5432/nexweave",
            "NEXWEAVE_OBJECT_STORE_ENDPOINT=http://rustfs:9000",
            "NEXWEAVE_OBJECT_STORE_HEALTH_URL=http://rustfs:9000/health",
            "NEXWEAVE_OBJECT_STORE_BUCKET=nexweave-dev",
            "NEXWEAVE_OBJECT_STORE_ACCESS_KEY=nexweave",
            f"NEXWEAVE_OBJECT_STORE_SECRET_KEY={object_store_secret}",
            "NEXWEAVE_REDIS_URL=redis://redis:6379/0",
            "NEXWEAVE_TEMPORAL_ENDPOINT=temporal:7233",
            "NEXWEAVE_TEMPORAL_NAMESPACE=nexweave-dev",
            "NEXWEAVE_TEMPORAL_TASK_QUEUE=nexweave-m0-health",
            "NEXWEAVE_TEMPORAL_WORKFLOW_TASK_QUEUE=nexweave-m2-workflows",
            "NEXWEAVE_TEMPORAL_ACTIVITY_TASK_QUEUE=nexweave-m2-activities",
            "NEXWEAVE_IDENTITY_PROVIDER=local",
            "NEXWEAVE_OIDC_ISSUER=",
            "NEXWEAVE_OIDC_JWKS_URL=",
            "NEXWEAVE_OIDC_AUDIENCE=nexweave-api",
            "NEXWEAVE_LOCAL_DEV_IDENTITY_ENABLED=true",
            f"NEXWEAVE_LOCAL_DEV_SIGNING_KEY={local_dev_signing_key}",
            "NEXWEAVE_LOCAL_DEV_SUBJECT=local-admin",
            "NEXWEAVE_LOCAL_DEV_TENANT_SLUG=local",
            "NEXWEAVE_MODEL_GATEWAY_ENDPOINT=",
            "NEXWEAVE_SECRET_PROVIDER=local-env-m1-only",
            "NEXWEAVE_OTEL_EXPORTER_OTLP_ENDPOINT=",
            "",
        ]
    )
    ENV_FILE.write_text(content, encoding="utf-8")
    ENV_FILE.chmod(0o600)
    print("created .env with mode 0600")


if __name__ == "__main__":
    main()
