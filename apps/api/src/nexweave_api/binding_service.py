"""Bounded, authorized CSV inspection through the existing time-series Connector."""

from typing import Any
from uuid import UUID

from sqlalchemy import text

from nexweave_api.errors import ApiProblem
from nexweave_api.forecast_gateway import CsvTimeSeriesConnector
from nexweave_api.forecast_repository import ForecastRepository
from nexweave_api.object_storage import S3ObjectStorage
from nexweave_contracts.forecast import BindingCreate
from nexweave_domain import Principal
from nexweave_domain.forecast import read_csv_table, read_observations


class BindingService:
    def __init__(self, repository: ForecastRepository, storage: S3ObjectStorage):
        self.repo, self.storage = repository, storage

    async def source_bytes(
        self, principal: Principal, space_id: UUID, source_id: UUID
    ) -> tuple[dict[str, Any], bytes]:
        await self.repo.authorize(principal, space_id, "source.read")
        source = await self.repo.platform.get_source_version(
            principal=principal, version_id=source_id
        )
        if str(source["space_id"]) != str(space_id):
            raise ApiProblem(
                404, "RESOURCE_NOT_FOUND", "Source unavailable", "Source not in space."
            )
        await self.repo.authorize(principal, space_id, "source.read", source["classification"])
        if await self.repo.platform.is_source_version_invalidated(
            principal=principal, version_id=source_id
        ):
            raise ApiProblem(
                409,
                "SOURCE_VERSION_INVALIDATED",
                "Source invalidated",
                "Invalidated sources cannot be bound or previewed.",
            )
        async with self.repo.database.engine.connect() as c:
            clean = await c.scalar(
                text(
                    "SELECT pj.malware_scan_status='CLEAN' AND sd.status<>'ARCHIVED' "
                    "FROM parse_jobs pj JOIN source_versions sv ON sv.active_parse_job_id=pj.id "
                    "JOIN source_documents sd ON sd.id=sv.source_document_id WHERE sv.id=:id"
                ),
                {"id": source_id},
            )
        if source["status"] != "PARSED" or not clean:
            raise ApiProblem(
                422,
                "SOURCE_UNAVAILABLE",
                "Source unavailable",
                "Use a clean fully parsed SourceVersion.",
            )
        if source["content_type"] != "text/csv" or source["size"] > 2_000_000:
            raise ApiProblem(
                422, "SOURCE_TYPE_UNSUPPORTED", "CSV required", "Use UTF-8 CSV under 2 MB."
            )
        raw = await CsvTimeSeriesConnector(self.storage, source["object_version_id"]).read_window(
            source["object_key"], source["checksum"]
        )
        return source, raw

    async def audit(
        self, principal: Principal, space_id: UUID, source_id: UUID, trace_id: str, action: str
    ) -> None:
        async with self.repo.database.engine.begin() as c:
            await self.repo.platform._insert_audit(
                c,
                principal=principal,
                space_id=space_id,
                action=action,
                resource_type="SourceVersion",
                resource_id=source_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={"purpose": "SIGNAL_BINDING"},
            )

    async def preview(
        self, principal: Principal, space_id: UUID, source_id: UUID, trace_id: str
    ) -> dict[str, Any]:
        source, raw = await self.source_bytes(principal, space_id, source_id)
        fields, rows = read_csv_table(raw)
        await self.audit(
            principal, space_id, source_id, trace_id, "signal-binding.source-previewed"
        )
        return {
            "source_version_id": str(source_id),
            "checksum": source["checksum"],
            "columns": fields,
            "sample_rows": [{k: v[:128] for k, v in r.items()} for r in rows[:5]],
            "row_count": len(rows),
        }

    async def validate(
        self, principal: Principal, space_id: UUID, body: BindingCreate, trace_id: str
    ) -> dict[str, Any]:
        binding = await self.repo.prepare_binding(principal, space_id, body)
        _, raw = await self.source_bytes(principal, space_id, body.source_version_id)
        # Reject timestamp/quality reuse as a numerical signal; units are explicit, never inferred.
        occupied = {c.column for c in body.columns}
        if body.timestamp_column in occupied or (
            body.quality_column
            and (body.quality_column in occupied or body.quality_column == body.timestamp_column)
        ):
            raise ApiProblem(
                422,
                "BINDING_AMBIGUOUS",
                "Mapping ambiguous",
                "Time, quality and values need distinct columns.",
            )
        points = read_observations(raw, binding)
        await self.audit(
            principal, space_id, body.source_version_id, trace_id, "signal-binding.validated"
        )
        return {
            "valid": True,
            "point_count": len(points),
            "start": points[0]["timestamp"],
            "end": points[-1]["timestamp"],
            "latest_values": points[-1]["values"],
            "source_checksum": binding["snapshot"]["source_checksum"],
        }
