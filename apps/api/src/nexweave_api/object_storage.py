"""RustFS/S3 adapter behind the provider-neutral ObjectStoragePort."""

from __future__ import annotations

import asyncio
import struct
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
from opentelemetry import metrics, trace

from nexweave_api.errors import ApiProblem
from nexweave_api.settings import Settings
from nexweave_application import StoredObjectInfo
from nexweave_domain import ScanStatus

TRACER = trace.get_tracer("nexweave.object-storage")
METER = metrics.get_meter("nexweave.object-storage")
OBJECT_OPERATIONS = METER.create_counter("nexweave.object_storage.operations")
OBJECT_BYTES = METER.create_histogram("nexweave.object_storage.bytes")


class S3ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        self._bucket = settings.object_store_bucket
        self._client: Any = boto3.client(
            "s3",
            endpoint_url=settings.object_store_endpoint,
            aws_access_key_id=settings.object_store_access_key,
            aws_secret_access_key=settings.object_store_secret_key,
            region_name="us-east-1",
            config=Config(
                signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"}
            ),
        )

    async def ensure_bucket(self) -> None:
        def ensure() -> None:
            try:
                self._client.head_bucket(Bucket=self._bucket)
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                if code not in {"404", "NoSuchBucket", "NotFound"}:
                    raise
                self._client.create_bucket(Bucket=self._bucket)
                self._client.put_bucket_versioning(
                    Bucket=self._bucket, VersioningConfiguration={"Status": "Enabled"}
                )

        with TRACER.start_as_current_span("object_storage.ensure_bucket"):
            await asyncio.to_thread(ensure)

    async def put_if_absent(
        self, *, key: str, content: bytes, content_type: str, checksum_sha256: str
    ) -> StoredObjectInfo:
        def put() -> StoredObjectInfo:
            try:
                response = self._client.put_object(
                    Bucket=self._bucket,
                    Key=key,
                    Body=content,
                    ContentType=content_type,
                    Metadata={"sha256": checksum_sha256.removeprefix("sha256:")},
                    IfNoneMatch="*",
                )
            except ClientError as exc:
                code = str(exc.response.get("Error", {}).get("Code", ""))
                if code in {"PreconditionFailed", "412", "ConditionalRequestConflict"}:
                    existing = self._client.head_object(Bucket=self._bucket, Key=key)
                    existing_checksum = str(existing.get("Metadata", {}).get("sha256", ""))
                    if (
                        existing_checksum == checksum_sha256.removeprefix("sha256:")
                        and int(existing.get("ContentLength", -1)) == len(content)
                        and str(existing.get("ContentType", "")) == content_type
                    ):
                        return StoredObjectInfo(
                            key=key,
                            version_id=existing.get("VersionId"),
                            size=len(content),
                            checksum_sha256=checksum_sha256,
                            content_type=content_type,
                        )
                    raise ApiProblem(
                        409,
                        "VERSION_CONFLICT",
                        "Object already exists",
                        "The immutable object key already exists and was not overwritten.",
                    ) from exc
                raise ApiProblem(
                    503,
                    "DEPENDENCY_UNAVAILABLE",
                    "Object storage unavailable",
                    "The object storage write could not be completed.",
                ) from exc
            return StoredObjectInfo(
                key=key,
                version_id=response.get("VersionId"),
                size=len(content),
                checksum_sha256=checksum_sha256,
                content_type=content_type,
            )

        with TRACER.start_as_current_span("object_storage.put") as span:
            span.set_attribute("object.key", key)
            span.set_attribute("object.size", len(content))
            result = await asyncio.to_thread(put)
            OBJECT_OPERATIONS.add(1, {"operation": "put"})
            OBJECT_BYTES.record(len(content), {"operation": "put"})
            return result

    async def create_download_url(self, *, key: str, expires_seconds: int) -> str:
        return str(
            await asyncio.to_thread(
                self._client.generate_presigned_url,
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_seconds,
            )
        )

    async def get(self, *, key: str, version_id: str | None = None) -> bytes:
        def read() -> bytes:
            try:
                params = {"Bucket": self._bucket, "Key": key}
                if version_id is not None:
                    params["VersionId"] = version_id
                response = self._client.get_object(**params)
                return bytes(response["Body"].read())
            except ClientError as exc:
                raise ApiProblem(
                    503,
                    "DEPENDENCY_UNAVAILABLE",
                    "Object storage unavailable",
                    "The authorized object could not be read.",
                ) from exc

        with TRACER.start_as_current_span("object_storage.get") as span:
            span.set_attribute("object.key", key)
            result = await asyncio.to_thread(read)
            OBJECT_OPERATIONS.add(1, {"operation": "get"})
            OBJECT_BYTES.record(len(result), {"operation": "get"})
            return result

    async def head(self, *, key: str, version_id: str | None = None) -> StoredObjectInfo:
        def inspect() -> StoredObjectInfo:
            try:
                params = {"Bucket": self._bucket, "Key": key}
                if version_id is not None:
                    params["VersionId"] = version_id
                response = self._client.head_object(**params)
            except ClientError as exc:
                raise ApiProblem(
                    503,
                    "DEPENDENCY_UNAVAILABLE",
                    "Object storage unavailable",
                    "The authorized object metadata could not be read.",
                ) from exc
            checksum = str(response.get("Metadata", {}).get("sha256", ""))
            return StoredObjectInfo(
                key=key,
                version_id=response.get("VersionId"),
                size=int(response.get("ContentLength", 0)),
                checksum_sha256=f"sha256:{checksum}",
                content_type=str(response.get("ContentType", "application/octet-stream")),
            )

        with TRACER.start_as_current_span("object_storage.head"):
            return await asyncio.to_thread(inspect)


class PolicyStubMalwareScanner:
    """M1 scanner extension point; explicit policy stub with an EICAR denial path."""

    async def scan(self, *, content: bytes, content_type: str) -> ScanStatus:
        del content_type
        if b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE" in content:
            return ScanStatus.INFECTED
        return ScanStatus.CLEAN


class ClamAvInstreamMalwareScanner:
    """Real ClamAV clamd INSTREAM adapter; dependency failure is fail-closed."""

    def __init__(self, settings: Settings) -> None:
        self._host = settings.clamav_host
        self._port = settings.clamav_port
        self._timeout = settings.clamav_timeout_seconds

    async def scan(self, *, content: bytes, content_type: str) -> ScanStatus:
        del content_type
        try:
            async with asyncio.timeout(self._timeout):
                reader, writer = await asyncio.open_connection(self._host, self._port)
                try:
                    writer.write(b"zINSTREAM\0")
                    for offset in range(0, len(content), 65_536):
                        chunk = content[offset : offset + 65_536]
                        writer.write(struct.pack("!I", len(chunk)))
                        writer.write(chunk)
                    writer.write(struct.pack("!I", 0))
                    await writer.drain()
                    response = (
                        (await reader.readuntil(b"\0"))
                        .rstrip(b"\0")
                        .decode("utf-8", errors="replace")
                    )
                finally:
                    writer.close()
                    await writer.wait_closed()
        except (TimeoutError, OSError, asyncio.IncompleteReadError) as exc:
            raise ApiProblem(
                503,
                "SOURCE_MALWARE_SCANNER_UNAVAILABLE",
                "Malware scanner unavailable",
                "The Raw object was retained but cannot enter parsing until the scanner recovers.",
                extensions={"provider": "clamav", "retryable": True},
            ) from exc
        if response.endswith(" OK"):
            return ScanStatus.CLEAN
        if response.endswith(" FOUND"):
            return ScanStatus.INFECTED
        raise ApiProblem(
            422,
            "SOURCE_MALWARE_SCAN_FAILED",
            "Malware scan failed",
            "The scanner rejected or could not safely inspect this Raw object.",
            extensions={"provider": "clamav", "retryable": False},
        )
