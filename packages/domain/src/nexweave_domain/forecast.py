"""Pure time-series semantics, temporal validation and interpretation rules."""

from __future__ import annotations

import csv
import io
import math
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from nexweave_domain.semantic import SemanticRuleViolation, validate_stable_key


def validate_temporal_declarations(snapshot: Mapping[str, Any]) -> None:
    signals = {s["key"]: s for s in snapshot.get("signalDefinitions", [])}
    if len(signals) != len(snapshot.get("signalDefinitions", [])):
        raise SemanticRuleViolation("SEMANTIC_MODEL_INVALID", "Duplicate signal key.")
    types = {t["key"] for t in snapshot["types"]}
    for key, signal in signals.items():
        validate_stable_key(key)
        if signal["typeKey"] not in types or not signal.get("unit"):
            raise SemanticRuleViolation("SEMANTIC_MODEL_INVALID", "Signal type or unit invalid.")
    for profile in snapshot.get("forecastProfiles", []):
        keys = [profile["target"], *profile["pastCovariates"], *profile["futureCovariates"]]
        if len(keys) != len(set(keys)) or not set(keys) <= signals.keys():
            raise SemanticRuleViolation("SEMANTIC_MODEL_INVALID", "Forecast roles are invalid.")
        if len({signals[k]["typeKey"] for k in keys}) != 1:
            raise SemanticRuleViolation("SEMANTIC_MODEL_INVALID", "Slice signals need one type.")


def read_csv_table(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    if len(raw) > 2_000_000:
        raise SemanticRuleViolation("INPUT_RESOURCE_EXCEEDED", "CSV exceeds the slice budget.")
    try:
        reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        fields = reader.fieldnames or []
        if (
            not 1 <= len(fields) <= 32
            or len(fields) != len(set(fields))
            or any(not f.strip() or len(f) > 128 for f in fields)
        ):
            raise ValueError("columns")
        rows = list(reader)
        if not 32 <= len(rows) <= 20_000 or any(
            set(row) != set(fields) or any(v is None for v in row.values()) for row in rows
        ):
            raise ValueError("rows")
        return list(fields), rows
    except (ValueError, TypeError, UnicodeError, csv.Error) as exc:
        raise SemanticRuleViolation(
            "DATA_QUALITY_INSUFFICIENT", "CSV structure is invalid."
        ) from exc


def read_observations(
    raw: bytes,
    binding: Mapping[str, Any],
    *,
    cutoff_value: str | None = None,
    history_points: int = 8192,
) -> list[dict[str, Any]]:
    """Reject missing/duplicate/irregular data instead of silently interpolating it."""
    if len(raw) > 2_000_000:
        raise SemanticRuleViolation("INPUT_RESOURCE_EXCEEDED", "CSV exceeds the slice budget.")
    try:
        _, rows = read_csv_table(raw)
        points: list[dict[str, Any]] = []
        columns = binding["columns"]
        cutoff = datetime.fromisoformat(cutoff_value) if cutoff_value else None
        previous: datetime | None = None
        frequency = binding["snapshot"]["profile"]["frequencySeconds"]
        for row_index, row in enumerate(rows, start=2):
            stamp = datetime.fromisoformat(row[binding["timestamp_column"]].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timezone")
            stamp = stamp.astimezone(UTC)
            if previous is not None and (stamp - previous).total_seconds() != frequency:
                raise ValueError("irregular time grid")
            previous = stamp
            if cutoff is not None and stamp > cutoff:
                continue
            quality_column = binding.get("quality_column")
            if quality_column and row.get(quality_column) != "GOOD":
                raise ValueError("quality")
            values = {c["signal_key"]: float(row[c["column"]]) for c in columns}
            if not all(math.isfinite(v) for v in values.values()):
                raise ValueError("finite values")
            points.append(
                {"timestamp": stamp.isoformat(), "values": values, "source_row": row_index}
            )
        points = points[-history_points:]
        if len(points) < 32:
            raise ValueError("history")
    except (ValueError, KeyError, TypeError, UnicodeError, csv.Error) as exc:
        raise SemanticRuleViolation(
            "DATA_QUALITY_INSUFFICIENT",
            "CSV needs a regular UTC-aware grid and finite GOOD values.",
        ) from exc
    return points


def build_observation_window(
    raw: bytes, binding: Mapping[str, Any], request: Mapping[str, Any]
) -> dict[str, Any]:
    points = read_observations(
        raw,
        binding,
        cutoff_value=request.get("cutoff"),
        history_points=int(request["history_points"]),
    )
    columns = binding["columns"]
    profile = binding["snapshot"]["profile"]
    frequency = profile["frequencySeconds"]
    paths = {p["signal_key"]: p for p in request["future_paths"]}
    expected = set(profile["futureCovariates"])
    if len(paths) != len(request["future_paths"]) or set(paths) != expected:
        raise SemanticRuleViolation("FUTURE_COVARIATE_INCOMPLETE", "Future signal roles mismatch.")
    units = {c["signal_key"]: c["unit"] for c in columns}
    for key, path in paths.items():
        if path["unit"] != units[key]:
            raise SemanticRuleViolation("UNIT_MISMATCH", "Future path unit differs from binding.")
        if len(path["values"]) != request["horizon"] or not all(
            math.isfinite(v) for v in path["values"]
        ):
            raise SemanticRuleViolation("FUTURE_COVARIATE_INCOMPLETE", "Future horizon incomplete.")
    target = profile["target"]
    if request.get("event_rule") and request["event_rule"]["unit"] != units[target]:
        raise SemanticRuleViolation("UNIT_MISMATCH", "Event threshold must use target units.")
    origin = datetime.fromisoformat(points[-1]["timestamp"])
    return {
        "observations": points,
        "target": target,
        "unit": units[target],
        "profile": profile,
        "origin": origin.isoformat(),
        "prediction_timestamps": [
            (origin + timedelta(seconds=frequency * (i + 1))).isoformat()
            for i in range(request["horizon"])
        ],
        "future_paths": list(paths.values()),
        "quality": {"status": "VALID", "interpolated": False, "points": len(points)},
        "operating_context": binding["operating_context"],
        "scenario_kind": "USER_ASSUMPTION",
        "scenario_name": request["scenario_name"],
        "data_kind": binding["data_kind"],
        "source_version_id": binding["source_version_id"],
        "source_checksum": binding["snapshot"]["source_checksum"],
        "schema_version_id": binding["schema_version_id"],
        "schema_checksum": binding["snapshot"]["schema_checksum"],
        "entity_id": binding["entity_id"],
        "entity_snapshot": binding["snapshot"]["entity"],
        "release_id": request.get("release_id"),
        "available_at": binding["created_at"],
        "temporal_mode": "HISTORICAL_REPLAY_UNVERIFIED_AVAILABILITY",
    }


def validate_forecast_result(result: Mapping[str, Any], horizon: int) -> None:
    quantiles = result["quantiles"]
    if not quantiles or "0.5" not in quantiles:
        raise SemanticRuleViolation("FORECAST_OUTPUT_INVALID", "Median output is missing.")
    ordered = sorted(quantiles, key=float)
    if any(len(quantiles[q]) != horizon for q in ordered):
        raise SemanticRuleViolation("FORECAST_OUTPUT_INVALID", "Output horizon is invalid.")
    for i in range(horizon):
        values = [quantiles[q][i] for q in ordered]
        if not all(math.isfinite(v) for v in values) or values != sorted(values):
            raise SemanticRuleViolation(
                "FORECAST_OUTPUT_INVALID", "Nonfinite or crossed quantiles."
            )


def interpret_forecast(
    context: Mapping[str, Any], result: Mapping[str, Any], rule: Mapping[str, Any] | None
) -> dict[str, Any]:
    """An unverified rule condition is never a fault probability or a diagnosis."""
    median = result["quantiles"]["0.5"]
    upper = result["quantiles"].get("0.9")
    event: dict[str, Any] | None = None
    if rule and upper:
        matched = [i for i, value in enumerate(upper) if value >= rule["threshold"]]
        if matched:
            event = {
                "epistemic_kind": "FORECAST",
                "status": "OPEN",
                "label": rule["label"],
                "first_timestamp": context["prediction_timestamps"][matched[0]],
                "matched_steps": len(matched),
                "rule": dict(rule),
                "event_probability": None,
                "explanation": "P90 曲线达到配置阈值；不表示故障概率，阈值未经现场批准。",
            }
    status = (
        "NOT_EVALUATED" if not rule or not upper else ("MATCHED" if event else "EVALUATED_NO_MATCH")
    )
    return {
        "potential_events": [event] if event else [],
        "event_evaluation": status,
        "hypotheses": [
            {
                "epistemic_kind": "HYPOTHESIS",
                "status": "INCONCLUSIVE",
                "statement": "预测变化的原因尚未确定，需结合工况、有效规程与现场证据核实。",
                "support": "条件预测曲线，不是因果证据",
                "counter_evidence": [],
                "verification": "核验测点质量、未来输入路径与设备适用知识。",
            }
        ],
        "risk_narrative": {
            "observed": (
                f"窗口包含 {len(context['observations'])} 个记录点，截止 {context['origin']}。"
            ),
            "forecast": (
                f"在“{context['scenario_name']}”假设下，"
                f"末端 P50 为 {median[-1]:.3f} {context['unit']}。"
            ),
            "knowledge": "未使用已发布知识依据；此结果不是 RCA 诊断。",
            "limitations": [
                "条件预测不等于因果推断",
                "区间尚未以现场数据校准",
                "历史可获得性尚未验证",
            ],
        },
    }
