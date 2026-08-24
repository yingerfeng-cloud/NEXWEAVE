"""Run the provider-neutral RustFS/S3 compatibility and recovery spike."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import Iterable
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse

import boto3  # type: ignore[import-untyped]
from botocore.client import Config  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[1]
RUSTFS_IMAGE = (
    "quay.io/rustfs/rustfs:1.0.0-rc.3@"
    "sha256:800cf3f352a0a27e3275ca854a51f0027975d7acc7a0d52089a35bcc9fcbf0b5"
)


def bypass_proxy_for_local_endpoint(endpoint: str) -> None:
    hostname = urlparse(endpoint).hostname
    if hostname not in {"127.0.0.1", "localhost", "::1"}:
        return
    for variable in ("NO_PROXY", "no_proxy"):
        entries = [item.strip() for item in os.getenv(variable, "").split(",") if item.strip()]
        if hostname not in entries:
            entries.append(hostname)
        os.environ[variable] = ",".join(entries)


def load_local_credentials() -> tuple[str, str]:
    values: dict[str, str] = {}
    env_path = ROOT / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", maxsplit=1)
            values[key] = value

    access_key = os.getenv("NEXWEAVE_OBJECT_STORE_ACCESS_KEY") or values.get(
        "NEXWEAVE_OBJECT_STORE_ACCESS_KEY"
    )
    secret_key = os.getenv("NEXWEAVE_OBJECT_STORE_SECRET_KEY") or values.get(
        "NEXWEAVE_OBJECT_STORE_SECRET_KEY"
    )
    if not access_key or not secret_key:
        raise RuntimeError(
            "Run `make env` before SPK-004; local object-store credentials are missing"
        )
    return access_key, secret_key


def create_client(endpoint: str, access_key: str, secret_key: str) -> Any:
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 4, "mode": "standard"},
        ),
    )


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def checksum_b64(payload: bytes) -> str:
    return base64.b64encode(hashlib.sha256(payload).digest()).decode("ascii")


def md5_b64(payload: bytes) -> str:
    digest = hashlib.md5(payload, usedforsecurity=False).digest()
    return base64.b64encode(digest).decode("ascii")


def read_body(response: dict[str, Any]) -> bytes:
    return bytes(response["Body"].read())


def expect_http_denied(url: str) -> None:
    try:
        urllib.request.urlopen(url, timeout=5)  # noqa: S310
    except urllib.error.HTTPError as exc:
        if exc.code not in {401, 403}:
            raise RuntimeError(f"Expected authorization denial, received HTTP {exc.code}") from exc
    else:
        raise RuntimeError("Anonymous or expired request unexpectedly accessed a private object")


def wait_until_available(client: Any, bucket: str, key: str, timeout_seconds: int = 90) -> None:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            client.head_object(Bucket=bucket, Key=key)
            return
        except Exception as exc:  # retry across restart transport and service errors
            last_error = exc
            time.sleep(1)
    raise RuntimeError("RustFS did not recover before the timeout") from last_error


def delete_bucket_and_versions(client: Any, bucket: str) -> None:
    try:
        paginator = client.get_paginator("list_object_versions")
        for page in paginator.paginate(Bucket=bucket):
            objects = [
                {"Key": item["Key"], "VersionId": item["VersionId"]}
                for item in [*page.get("Versions", []), *page.get("DeleteMarkers", [])]
            ]
            if objects:
                client.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True})
        client.delete_bucket(Bucket=bucket)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") not in {"NoSuchBucket", "NoSuchKey"}:
            raise


def verify_basic_object_operations(client: Any, endpoint: str, bucket: str) -> dict[str, str]:
    key = "raw/tenant/space/source/version/source.bin"
    payload = (b"NEXWEAVE-SPK-004-RAW-FIRST\n" * 65536)[:1_048_576]
    payload_hash = sha256_hex(payload)
    response = client.put_object(
        Bucket=bucket,
        Key=key,
        Body=payload,
        ContentMD5=md5_b64(payload),
        ChecksumSHA256=checksum_b64(payload),
        Metadata={"sha256": payload_hash, "classification": "public-synthetic"},
    )
    first_version = str(response.get("VersionId", ""))
    head = client.head_object(Bucket=bucket, Key=key)
    if head["ContentLength"] != len(payload) or head["Metadata"].get("sha256") != payload_hash:
        raise RuntimeError("Object metadata or length changed after upload")
    if read_body(client.get_object(Bucket=bucket, Key=key)) != payload:
        raise RuntimeError("Downloaded object checksum differs from the uploaded payload")
    ranged = read_body(client.get_object(Bucket=bucket, Key=key, Range="bytes=1024-4095"))
    if ranged != payload[1024:4096]:
        raise RuntimeError("Range download returned unexpected bytes")

    listed = client.list_objects_v2(Bucket=bucket, Prefix="raw/tenant/space/source/version/")
    if [item["Key"] for item in listed.get("Contents", [])] != [key]:
        raise RuntimeError("Prefix listing did not return the uploaded immutable object key")

    try:
        client.put_object(Bucket=bucket, Key=key, Body=b"forbidden-overwrite", IfNoneMatch="*")
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        http_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if error_code not in {
            "PreconditionFailed",
            "ConditionalRequestConflict",
        } and http_code not in {
            409,
            412,
        }:
            raise
    else:
        raise RuntimeError("RustFS silently overwrote an existing key despite If-None-Match: *")

    version_payload = b"explicit-version-transition"
    version_response = client.put_object(Bucket=bucket, Key=key, Body=version_payload)
    second_version = str(version_response.get("VersionId", ""))
    if not first_version or not second_version or first_version == second_version:
        raise RuntimeError("Bucket versioning did not create distinct object versions")
    if read_body(client.get_object(Bucket=bucket, Key=key, VersionId=first_version)) != payload:
        raise RuntimeError("The original object version was not preserved")

    object_url = f"{endpoint.rstrip('/')}/{quote(bucket)}/{quote(key)}"
    expect_http_denied(object_url)
    presigned_url = client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=30
    )
    with urllib.request.urlopen(presigned_url, timeout=5) as response_stream:  # noqa: S310
        if response_stream.read() != version_payload:
            raise RuntimeError("Presigned download returned unexpected content")

    expired_url = client.generate_presigned_url(
        "get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=1
    )
    time.sleep(2)
    expect_http_denied(expired_url)

    wrong_client = create_client(endpoint, "invalid-access", "invalid-secret")
    try:
        wrong_client.head_object(Bucket=bucket, Key=key)
    except ClientError:
        pass
    else:
        raise RuntimeError("Invalid credentials unexpectedly accessed a private object")

    return {"key": key, "first_version": first_version, "sha256": payload_hash}


def verify_multipart(client: Any, bucket: str) -> dict[str, str | int]:
    key = "raw/tenant/space/source/version/multipart.bin"
    part_one = b"A" * (5 * 1024 * 1024)
    part_two = b"B" * (1024 * 1024)
    expected = part_one + part_two
    upload = client.create_multipart_upload(Bucket=bucket, Key=key)
    upload_id = upload["UploadId"]
    try:
        first = client.upload_part(
            Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=1, Body=part_one
        )
        retried = client.upload_part(
            Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=1, Body=part_one
        )
        if first["ETag"] != retried["ETag"]:
            raise RuntimeError("Retrying the same multipart part changed its ETag")
        second = client.upload_part(
            Bucket=bucket, Key=key, UploadId=upload_id, PartNumber=2, Body=part_two
        )
        client.complete_multipart_upload(
            Bucket=bucket,
            Key=key,
            UploadId=upload_id,
            MultipartUpload={
                "Parts": [
                    {"PartNumber": 1, "ETag": retried["ETag"]},
                    {"PartNumber": 2, "ETag": second["ETag"]},
                ]
            },
        )
    except Exception:
        client.abort_multipart_upload(Bucket=bucket, Key=key, UploadId=upload_id)
        raise
    downloaded = read_body(client.get_object(Bucket=bucket, Key=key))
    if sha256_hex(downloaded) != sha256_hex(expected):
        raise RuntimeError("Completed multipart object checksum differs from uploaded parts")

    abandoned_key = f"{key}.abandoned"
    abandoned = client.create_multipart_upload(Bucket=bucket, Key=abandoned_key)
    client.abort_multipart_upload(Bucket=bucket, Key=abandoned_key, UploadId=abandoned["UploadId"])
    uploads = client.list_multipart_uploads(Bucket=bucket)
    if any(item["Key"] == abandoned_key for item in uploads.get("Uploads", [])):
        raise RuntimeError("Aborted multipart upload remained visible")
    return {"key": key, "size": len(expected), "sha256": sha256_hex(expected)}


def verify_lifecycle(client: Any, bucket: str) -> None:
    configuration = {
        "Rules": [
            {
                "ID": "abort-incomplete-spk004",
                "Status": "Enabled",
                "Filter": {"Prefix": "raw/"},
                "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 7},
            }
        ]
    }
    client.put_bucket_lifecycle_configuration(Bucket=bucket, LifecycleConfiguration=configuration)
    actual = client.get_bucket_lifecycle_configuration(Bucket=bucket)
    rules = actual.get("Rules", [])
    if len(rules) != 1 or rules[0].get("ID") != "abort-incomplete-spk004":
        raise RuntimeError("Lifecycle configuration did not round-trip")


def verify_restart_recovery(client: Any, bucket: str) -> dict[str, str]:
    key = "recovery/restart-proof.bin"
    payload = b"restart-proof-" + uuid.uuid4().bytes
    client.put_object(
        Bucket=bucket, Key=key, Body=payload, Metadata={"sha256": sha256_hex(payload)}
    )
    subprocess.run(
        ("docker", "compose", "restart", "rustfs"),
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
    )  # noqa: S603
    wait_until_available(client, bucket, key)
    recovered = read_body(client.get_object(Bucket=bucket, Key=key))
    if recovered != payload:
        raise RuntimeError("Object changed across RustFS restart")
    return {"key": key, "sha256": sha256_hex(payload)}


def verify_logical_backup_restore(client: Any, source_bucket: str, restore_bucket: str) -> None:
    client.create_bucket(Bucket=restore_bucket)
    manifest: list[tuple[str, bytes, str]] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=source_bucket):
        for item in page.get("Contents", []):
            key = item["Key"]
            payload = read_body(client.get_object(Bucket=source_bucket, Key=key))
            manifest.append((key, payload, sha256_hex(payload)))
            client.put_object(
                Bucket=restore_bucket,
                Key=key,
                Body=payload,
                Metadata={"restored-sha256": sha256_hex(payload)},
            )
    if not manifest:
        raise RuntimeError("Logical backup manifest was empty")
    for key, _, expected_hash in manifest:
        restored = read_body(client.get_object(Bucket=restore_bucket, Key=key))
        if sha256_hex(restored) != expected_hash:
            raise RuntimeError(f"Restored object checksum mismatch: {key}")


def write_report(path: Path, report: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cleanup_buckets(client: Any, buckets: Iterable[str]) -> None:
    for bucket in buckets:
        delete_bucket_and_versions(client, bucket)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", default="http://127.0.0.1:9000")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    bypass_proxy_for_local_endpoint(args.endpoint)
    access_key, secret_key = load_local_credentials()
    client = create_client(args.endpoint, access_key, secret_key)
    run_id = uuid.uuid4().hex[:12]
    source_bucket = f"nexweave-spk004-{run_id}"
    restore_bucket = f"nexweave-spk004-restore-{run_id}"
    report: dict[str, Any] = {
        "spike": "SPK-004",
        "rustfs_image": RUSTFS_IMAGE,
        "endpoint_kind": "local-compose",
        "credentials_logged": False,
        "checks": {},
    }
    try:
        client.create_bucket(Bucket=source_bucket)
        client.put_bucket_versioning(
            Bucket=source_bucket, VersioningConfiguration={"Status": "Enabled"}
        )
        versioning = client.get_bucket_versioning(Bucket=source_bucket)
        if versioning.get("Status") != "Enabled":
            raise RuntimeError("Bucket versioning was not enabled")
        report["checks"]["object_operations"] = verify_basic_object_operations(
            client, args.endpoint, source_bucket
        )
        report["checks"]["multipart"] = verify_multipart(client, source_bucket)
        verify_lifecycle(client, source_bucket)
        report["checks"]["lifecycle"] = "passed"
        report["checks"]["restart_recovery"] = verify_restart_recovery(client, source_bucket)
        verify_logical_backup_restore(client, source_bucket, restore_bucket)
        report["checks"]["logical_backup_restore"] = "passed"
        report["result"] = "passed"
        if args.output:
            write_report(args.output, report)
        print("SPK-004 RustFS/S3 compatibility and recovery checks passed")
    finally:
        cleanup_buckets(client, (restore_bucket, source_bucket))


if __name__ == "__main__":
    main()
