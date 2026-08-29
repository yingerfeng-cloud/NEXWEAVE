"""Idempotent M3 Source Activities behind the isolated parser-worker boundary."""

from __future__ import annotations

import asyncio
import hashlib
from typing import Any
from uuid import UUID

from temporalio import activity
from temporalio.exceptions import ApplicationError

from nexweave_api.errors import ApiProblem
from nexweave_api.object_storage import ClamAvInstreamMalwareScanner, S3ObjectStorage
from nexweave_api.source_repository import SourceRepository
from nexweave_application import ParserPort
from nexweave_contracts import ControlledObjectRef, ParserConfig, ParseRequest
from nexweave_domain import ScanStatus
from nexweave_worker_parser.protocol import (
    PARSER_ID,
    PARSER_VERSION,
    ParserPolicyError,
)


class SourceActivities:
    def __init__(
        self,
        *,
        repository: SourceRepository,
        storage: S3ObjectStorage,
        scanner: ClamAvInstreamMalwareScanner,
        parser: ParserPort,
    ) -> None:
        self._repository = repository
        self._storage = storage
        self._scanner = scanner
        self._parser = parser

    @activity.defn(name="m3_source_verify_raw")
    async def verify_raw(self, payload: dict[str, Any]) -> dict[str, Any]:
        parse_job_id = UUID(str(payload["parse_job_id"]))
        run_id = str(payload["run_id"])
        activity.heartbeat({"parse_job_id": str(parse_job_id), "step": "load-context"})
        await self._repository.mark_parse_running(parse_job_id, run_id)
        context = await self._repository.load_parse_context(parse_job_id)
        if (
            context["status"] != "RUNNING"
            or context["source_document_status"] == "ARCHIVED"
            or context["invalidated"]
        ):
            _raise_activity_error(
                "SOURCE_SECURITY_POLICY_FAILED",
                "The Source was archived or invalidated before parsing.",
                retryable=False,
            )
        if context["source_version_status"] == "SUPERSEDED":
            _raise_activity_error(
                "SOURCE_SECURITY_POLICY_FAILED",
                "A superseded SourceVersion cannot start a new parse.",
                retryable=False,
            )
        content = await self._storage.get(
            key=context["object_key"], version_id=context["object_version_id"]
        )
        head = await self._storage.head(
            key=context["object_key"], version_id=context["object_version_id"]
        )
        checksum = f"sha256:{hashlib.sha256(content).hexdigest()}"
        if (
            len(content) != context["size"]
            or checksum != context["checksum"]
            or head.size != context["size"]
            or head.content_type != context["content_type"]
            or head.version_id != context["object_version_id"]
        ):
            _raise_activity_error(
                "SOURCE_CHECKSUM_MISMATCH",
                "The server-read Raw metadata or checksum no longer matches registration.",
                retryable=False,
            )
        try:
            capability = self._parser.probe(
                filename=context["filename"],
                content_type=context["content_type"],
                content=content,
            )
        except ParserPolicyError as exc:
            _raise_activity_error(exc.code, exc.detail, retryable=False)
        if (
            context["parser_id"] != PARSER_ID
            or context["parser_version"] != PARSER_VERSION
            or capability.provider_id != PARSER_ID
            or capability.provider_version != PARSER_VERSION
        ):
            _raise_activity_error(
                "PARSER_CAPABILITY_UNAVAILABLE",
                "The immutable ParseJob requests an unregistered parser capability.",
                retryable=False,
            )
        return {
            "parse_job_id": str(parse_job_id),
            "source_version_id": context["source_version_id"],
            "checksum": checksum,
            "verified": True,
        }

    @activity.defn(name="m3_source_scan_raw")
    async def scan_raw(self, payload: dict[str, Any]) -> dict[str, Any]:
        parse_job_id = UUID(str(payload["parse_job_id"]))
        run_id = str(payload["run_id"])
        context = await self._repository.load_parse_context(parse_job_id)
        if context["status"] != "RUNNING":
            _raise_activity_error(
                "SOURCE_SECURITY_POLICY_FAILED",
                "A terminal or non-current ParseJob cannot run a malware scan.",
                retryable=False,
            )
        if context["malware_scan_status"] == "CLEAN":
            return {"parse_job_id": str(parse_job_id), "scan_status": "CLEAN", "duplicate": True}
        content = await self._storage.get(
            key=context["object_key"], version_id=context["object_version_id"]
        )
        activity.heartbeat(
            {"parse_job_id": str(parse_job_id), "step": "clamav-instream", "bytes": len(content)}
        )
        try:
            result = await self._scanner.scan(content=content, content_type=context["content_type"])
        except ApiProblem as exc:
            _raise_activity_error(
                exc.code,
                exc.detail,
                retryable=bool(exc.extensions.get("retryable", False)),
            )
        if result is ScanStatus.INFECTED:
            _raise_activity_error(
                "SOURCE_MALWARE_DETECTED",
                "ClamAV detected malicious content; parsing is denied.",
                retryable=False,
            )
        if result is not ScanStatus.CLEAN:
            _raise_activity_error(
                "SOURCE_MALWARE_SCAN_FAILED",
                "ClamAV did not return an approved clean result.",
                retryable=False,
            )
        await self._repository.mark_malware_scan_clean(parse_job_id, run_id)
        return {"parse_job_id": str(parse_job_id), "scan_status": "CLEAN", "duplicate": False}

    @activity.defn(name="m3_source_parse_and_persist")
    async def parse_and_persist(self, payload: dict[str, Any]) -> dict[str, Any]:
        parse_job_id = UUID(str(payload["parse_job_id"]))
        run_id = str(payload["run_id"])
        context = await self._repository.load_parse_context(parse_job_id)
        if (
            context["status"] != "RUNNING"
            or context["source_document_status"] == "ARCHIVED"
            or context["source_version_status"] == "SUPERSEDED"
            or context["invalidated"]
            or context["latest_parse_job_id"] != str(parse_job_id)
        ):
            _raise_activity_error(
                "SOURCE_SECURITY_POLICY_FAILED",
                "Archived, invalidated, superseded or stale parse work cannot continue.",
                retryable=False,
            )
        if context["malware_scan_status"] != "CLEAN":
            _raise_activity_error(
                "SOURCE_SECURITY_POLICY_FAILED",
                "The parser Activity is fail-closed until ClamAV records CLEAN.",
                retryable=False,
            )
        content = await self._storage.get(
            key=context["object_key"], version_id=context["object_version_id"]
        )
        config = ParserConfig.model_validate(context["config"])
        request = ParseRequest(
            parse_job_id=parse_job_id,
            source=ControlledObjectRef(
                source_version_id=UUID(context["source_version_id"]),
                object_key=context["object_key"],
                object_version_id=context["object_version_id"],
                checksum_sha256=context["checksum"],
                content_type=context["content_type"],
                size=context["size"],
            ),
            filename=context["filename"],
            parser_id=context["parser_id"],
            parser_version=context["parser_version"],
            config_checksum=context["config_checksum"],
            document_model_version=context["document_model_version"],
            locator_version=context["locator_version"],
            budget=config.budget,
        )
        activity.heartbeat(
            {"parse_job_id": str(parse_job_id), "step": "parse", "bytes": len(content)}
        )
        try:
            parse_task = asyncio.create_task(self._parser.parse(request=request, content=content))
            deadline = asyncio.get_running_loop().time() + request.budget.timeout_seconds
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    parse_task.cancel()
                    raise ParserPolicyError(
                        "PARSER_RESOURCE_LIMIT_EXCEEDED",
                        "The parser exceeded its configured wall-clock budget.",
                    )
                try:
                    manifest = await asyncio.wait_for(
                        asyncio.shield(parse_task), timeout=min(5.0, remaining)
                    )
                    break
                except TimeoutError:
                    activity.heartbeat(
                        {
                            "parse_job_id": str(parse_job_id),
                            "step": "parse",
                            "bytes": len(content),
                        }
                    )
            persisted = await self._repository.persist_parse_result(manifest, run_id)
        except asyncio.CancelledError:
            if "parse_task" in locals():
                parse_task.cancel()
            raise
        except ParserPolicyError as exc:
            _raise_activity_error(exc.code, exc.detail, retryable=False)
        except ApiProblem as exc:
            _raise_activity_error(
                exc.code,
                exc.detail,
                retryable=bool(exc.extensions.get("retryable", False)),
            )
        return {
            "parse_job_id": str(parse_job_id),
            "status": persisted["status"],
            "result_checksum": persisted["result_checksum"],
            "segment_count": len(manifest.segments),
            "failure_count": len(manifest.failure_units),
            "business_features_implemented": True,
            "knowledge_or_evidence_created": False,
        }

    @activity.defn(name="m3_source_fail")
    async def fail(self, payload: dict[str, Any]) -> None:
        parse_job_id = UUID(str(payload["parse_job_id"]))
        activity.heartbeat({"parse_job_id": str(parse_job_id), "step": "finalize-failure"})
        await self._repository.fail_parse_job(
            parse_job_id,
            str(payload["run_id"]),
            str(payload["code"]),
            str(payload["detail"]),
        )


def _raise_activity_error(code: str, detail: str, *, retryable: bool) -> None:
    raise ApplicationError(detail, type=code, non_retryable=not retryable)
