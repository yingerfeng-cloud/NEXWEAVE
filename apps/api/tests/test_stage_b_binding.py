"""Binding validation uses governed preparation and rejects data before persistence."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from nexweave_api.binding_service import BindingService
from nexweave_api.errors import ApiProblem
from nexweave_contracts.forecast import BindingCreate
from nexweave_domain import new_uuid7
from nexweave_domain.forecast import read_csv_table, read_observations
from nexweave_domain.semantic import SemanticRuleViolation


def fixture():
    from datetime import UTC, datetime, timedelta

    raw = "time,value,quality\n" + "\n".join(
        f"{(datetime(2026, 9, 1, tzinfo=UTC) + timedelta(minutes=i)).isoformat()},{i},GOOD"
        for i in range(40)
    )
    binding = {
        "timestamp_column": "time",
        "quality_column": "quality",
        "columns": [{"signal_key": "demo/value", "column": "value", "unit": "degC"}],
        "snapshot": {"profile": {"frequencySeconds": 60}, "source_checksum": "sha256:test"},
    }
    return raw.encode(), binding


@pytest.mark.parametrize(
    "change", ["ragged", "duplicate", "blank", "badtime", "badquality", "nonfinite"]
)
def test_binding_data_rejects_invalid_structures_or_values(change):
    raw, binding = fixture()
    if change == "ragged":
        raw += b"\nextra,row,GOOD,overflow"
    if change == "duplicate":
        raw = raw.replace(b"time,value,quality", b"time,value,value")
    if change == "blank":
        raw = raw.replace(b"time,value,quality", b"time, ,quality")
    if change == "badtime":
        raw = raw.replace(b"00:01:00", b"00:01:01")
    if change == "badquality":
        raw = raw.replace(b"GOOD", b"BAD", 1)
    if change == "nonfinite":
        raw = raw.replace(b",0,GOOD", b",nan,GOOD")
    with pytest.raises(SemanticRuleViolation):
        read_observations(raw, binding)


def test_preview_and_forecast_reader_use_same_table_and_latest_values():
    raw, binding = fixture()
    fields, rows = read_csv_table(raw)
    points = read_observations(raw, binding, history_points=32)
    assert fields == ["time", "value", "quality"] and len(rows) == 40
    assert len(points) == 32 and points[-1]["values"]["demo/value"] == 39


@pytest.mark.asyncio
async def test_precheck_does_not_create_binding_or_forecast():
    raw, record = fixture()
    body = BindingCreate(
        name="synthetic",
        entity_id=new_uuid7(),
        schema_version_id=new_uuid7(),
        source_version_id=new_uuid7(),
        profile_key="demo/profile",
        timestamp_column="time",
        columns=record["columns"],
        quality_column="quality",
        data_kind="SYNTHETIC",
    )
    repo = SimpleNamespace(
        prepare_binding=AsyncMock(return_value=record), create_binding=AsyncMock()
    )
    service = BindingService(repo, None)
    service.source_bytes = AsyncMock(return_value=({}, raw))
    service.audit = AsyncMock()
    result = await service.validate(None, new_uuid7(), body, "a" * 32)
    assert result["point_count"] == 40 and result["latest_values"]["demo/value"] == 39
    repo.create_binding.assert_not_awaited()
    service.audit.assert_awaited_once()
    with pytest.raises(ApiProblem, match="distinct columns"):
        await service.validate(
            None, new_uuid7(), body.model_copy(update={"timestamp_column": "value"}), "a" * 32
        )


@pytest.mark.asyncio
async def test_invalidated_source_never_reaches_forecast_storage_or_model():
    from nexweave_api.forecast_execution import ForecastExecution

    source_id, space_id, binding_id = new_uuid7(), new_uuid7(), new_uuid7()
    principal = SimpleNamespace()
    repository = SimpleNamespace(
        worker_principal=AsyncMock(return_value=principal),
        get_binding=AsyncMock(
            return_value={"classification": "INTERNAL", "source_version_id": str(source_id)}
        ),
        authorize=AsyncMock(),
        platform=SimpleNamespace(is_source_version_invalidated=AsyncMock(return_value=True)),
    )
    service = ForecastExecution(repository, None, None)
    with pytest.raises(ApiProblem, match="Invalidated source"):
        await service.inputs({"space_id": str(space_id), "binding_id": str(binding_id)})
