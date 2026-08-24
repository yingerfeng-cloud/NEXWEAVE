"""Create ignored local Compose credentials without overwriting an existing environment."""

from __future__ import annotations

from pathlib import Path
from secrets import token_urlsafe
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"


def main() -> None:
    if ENV_FILE.exists():
        print(".env already exists; leaving it unchanged")
        return

    postgres_password = token_urlsafe(32)
    object_store_secret = token_urlsafe(32)
    encoded_password = quote(postgres_password, safe="")
    content = "\n".join(
        [
            "# Generated for local M0 Compose only. This file is ignored by Git.",
            "NEXWEAVE_ENV=development",
            "NEXWEAVE_LOG_LEVEL=INFO",
            "NEXWEAVE_BUILD_VERSION=0.1.0-m0",
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
            "NEXWEAVE_TEMPORAL_NAMESPACE=default",
            "NEXWEAVE_TEMPORAL_TASK_QUEUE=nexweave-m0-health",
            "NEXWEAVE_OIDC_ISSUER=",
            "NEXWEAVE_MODEL_GATEWAY_ENDPOINT=",
            "NEXWEAVE_SECRET_PROVIDER=local-env-m0-only",
            "",
        ]
    )
    ENV_FILE.write_text(content, encoding="utf-8")
    ENV_FILE.chmod(0o600)
    print("created .env with mode 0600")


if __name__ == "__main__":
    main()
