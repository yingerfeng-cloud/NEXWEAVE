from functools import lru_cache
from urllib.parse import urlsplit, urlunsplit

from pydantic import Field, model_validator
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
    build_version: str = "0.4.0-m3"
    database_url: str = "postgresql+asyncpg://nexweave:local@localhost:5432/nexweave"
    object_store_endpoint: str = "http://localhost:9000"
    object_store_health_url: str = "http://localhost:9000/health"
    object_store_bucket: str = "nexweave-dev"
    object_store_access_key: str = ""
    object_store_secret_key: str = ""
    redis_url: str = "redis://localhost:6379/0"
    temporal_endpoint: str = "localhost:7233"
    temporal_namespace: str = "nexweave-dev"
    temporal_task_queue: str = "nexweave-m0-health"
    temporal_workflow_task_queue: str = "nexweave-m2-workflows"
    temporal_activity_task_queue: str = "nexweave-m2-activities"
    temporal_parser_activity_task_queue: str = "nexweave-m3-parser-activities"
    parser_sandbox_host: str = "localhost"
    parser_sandbox_port: int = Field(default=7001, ge=1, le=65535)
    identity_provider: str = "local"
    oidc_issuer: str = ""
    oidc_jwks_url: str = ""
    oidc_audience: str = "nexweave-api"
    oidc_algorithms: str = "RS256,ES256"
    local_dev_identity_enabled: bool = False
    local_dev_signing_key: str = ""
    local_dev_subject: str = "local-admin"
    local_dev_tenant_slug: str = "local"
    local_dev_session_seconds: int = Field(default=3600, ge=300, le=86_400)
    model_gateway_endpoint: str = ""
    secret_provider: str = Field(default="local-env-m1-only")
    health_timeout_seconds: float = Field(default=3.0, gt=0, le=30)
    object_upload_max_bytes: int = Field(default=104_857_600, gt=0)
    object_upload_session_seconds: int = Field(default=900, ge=60, le=86_400)
    malware_scanner_provider: str = "clamav"
    clamav_host: str = "localhost"
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    clamav_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    otel_service_name: str = "nexweave-api"
    otel_exporter_otlp_endpoint: str = ""

    @model_validator(mode="after")
    def production_identity_must_be_oidc(self) -> "Settings":
        if self.identity_provider not in {"local", "oidc"}:
            raise ValueError("identity provider must be local or oidc")
        if self.malware_scanner_provider != "clamav":
            raise ValueError("M3 requires the approved ClamAV malware scanner provider")
        if self.env != "development" and self.identity_provider != "oidc":
            raise ValueError("non-development environments require the OIDC identity provider")
        if self.identity_provider == "oidc" and not (
            self.oidc_issuer and self.oidc_jwks_url and self.oidc_audience
        ):
            raise ValueError("OIDC issuer, JWKS URL and audience are required")
        if self.local_dev_identity_enabled and not self.local_dev_signing_key:
            raise ValueError("local development identity requires a signing key")
        if self.local_dev_identity_enabled and len(self.local_dev_signing_key) < 32:
            raise ValueError("local development signing keys must contain at least 32 characters")
        allowed_algorithms = {
            "RS256",
            "RS384",
            "RS512",
            "ES256",
            "ES384",
            "ES512",
            "PS256",
            "PS384",
            "PS512",
        }
        configured_algorithms = {item.strip() for item in self.oidc_algorithms.split(",")}
        if not configured_algorithms or not configured_algorithms.issubset(allowed_algorithms):
            raise ValueError("OIDC algorithms must use the approved asymmetric allowlist")
        if self.env != "development":
            if not self.oidc_issuer.startswith("https://") or not self.oidc_jwks_url.startswith(
                "https://"
            ):
                raise ValueError("non-development OIDC endpoints must use HTTPS")
            if self.secret_provider == "local-env-m1-only":  # noqa: S105 - provider mode label
                raise ValueError("non-development environments require an external Secret Provider")
        return self

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
            "temporal_workflow_task_queue": self.temporal_workflow_task_queue,
            "temporal_activity_task_queue": self.temporal_activity_task_queue,
            "temporal_parser_activity_task_queue": self.temporal_parser_activity_task_queue,
            "parser_sandbox": f"{self.parser_sandbox_host}:{self.parser_sandbox_port}",
            "oidc_configured": str(bool(self.oidc_issuer)).lower(),
            "identity_provider": self.identity_provider,
            "local_dev_identity_enabled": str(self.local_dev_identity_enabled).lower(),
            "model_gateway_configured": str(bool(self.model_gateway_endpoint)).lower(),
            "secret_provider": self.secret_provider,
            "telemetry_export_configured": str(bool(self.otel_exporter_otlp_endpoint)).lower(),
            "malware_scanner": self.malware_scanner_provider,
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
