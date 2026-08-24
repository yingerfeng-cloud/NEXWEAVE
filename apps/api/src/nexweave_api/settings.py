from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NEXWEAVE_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = "development"
    log_level: str = "INFO"
    build_version: str = "0.1.0-m0"
    database_url: str = "postgresql+asyncpg://nexweave:local@localhost:5432/nexweave"
    object_store_endpoint: str = "http://localhost:9000"
    object_store_health_url: str = "http://localhost:9000/health"
    object_store_bucket: str = "nexweave-dev"
    redis_url: str = "redis://localhost:6379/0"
    temporal_endpoint: str = "localhost:7233"
    temporal_namespace: str = "nexweave-dev"
    temporal_task_queue: str = "nexweave-m0-health"
    oidc_issuer: str = ""
    model_gateway_endpoint: str = ""
    secret_provider: str = Field(default="local-env-m0-only")
    health_timeout_seconds: float = Field(default=3.0, gt=0, le=30)

    def diagnostics(self) -> dict[str, str]:
        return {
            "environment": self.env,
            "build_version": self.build_version,
            "database": _redact_url(self.database_url),
            "object_store": self.object_store_endpoint,
            "object_store_bucket": self.object_store_bucket,
            "redis": _redact_url(self.redis_url),
            "temporal": self.temporal_endpoint,
            "temporal_namespace": self.temporal_namespace,
            "oidc_configured": str(bool(self.oidc_issuer)).lower(),
            "model_gateway_configured": str(bool(self.model_gateway_endpoint)).lower(),
            "secret_provider": self.secret_provider,
        }


def _redact_url(value: str) -> str:
    parts = urlsplit(value)
    if parts.username is None and parts.password is None:
        return value
    host = parts.hostname or ""
    if parts.port is not None:
        host = f"{host}:{parts.port}"
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))


@lru_cache
def get_settings() -> Settings:
    return Settings()
