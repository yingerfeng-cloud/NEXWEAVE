"""Fixed-model rolling-origin benchmark; no forecast is a causal/fault conclusion."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import io
import json
import math
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from nexweave_api.forecast_gateway import CHRONOS_REVISION, Chronos2Provider, PersistenceProvider
from nexweave_api.settings import Settings
from nexweave_domain.forecast import build_observation_window, validate_forecast_result


def synthetic_csv() -> bytes:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["timestamp", "value"])
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for i in range(512):
        writer.writerow(
            [(start + timedelta(minutes=i)).isoformat(), 70 + 2 * math.sin(i / 18) + i / 500]
        )
    return out.getvalue().encode()


def pinball(values: list[float], actual: list[float], quantile: float) -> float:
    return sum(
        max(quantile * (a - v), (quantile - 1) * (a - v))
        for a, v in zip(actual, values, strict=True)
    ) / len(actual)


async def run(args: argparse.Namespace) -> dict:
    raw = args.csv.read_bytes() if args.csv else synthetic_csv()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    if not 0.5 <= args.train_fraction <= 0.8 or args.origins < 2:
        raise ValueError("Use a chronological holdout and multiple origins")
    settings = Settings(
        forecast_model_path=str(args.model_path.resolve()), forecast_model_revision=args.revision
    )
    model = Chronos2Provider(settings)
    model.verify_model()
    digest = "sha256:" + hashlib.sha256(raw).hexdigest()
    identifier = str(uuid4())
    binding = {
        "id": identifier,
        "entity_id": identifier,
        "schema_version_id": identifier,
        "source_version_id": identifier,
        "timestamp_column": "timestamp",
        "columns": [{"signal_key": "benchmark.io/value", "column": "value", "unit": args.unit}],
        "snapshot": {
            "source_checksum": digest,
            "schema_checksum": "benchmark-schema/1",
            "entity": {"id": identifier},
            "profile": {
                "target": "benchmark.io/value",
                "pastCovariates": [],
                "futureCovariates": [],
                "frequencySeconds": 60,
            },
        },
        "operating_context": "Offline backtest; input availability unverified",
        "data_kind": "IMPORTED_UNVERIFIED" if args.csv else "SYNTHETIC",
        "created_at": datetime.now(UTC).isoformat(),
    }
    request = {
        "history_points": args.history,
        "horizon": args.horizon,
        "future_paths": [],
        "scenario_name": "rolling-origin fixed-model baseline",
    }
    origins = []
    first = int(len(rows) * args.train_fraction)
    for index in range(args.origins):
        origin = first + index * args.step
        if origin + args.horizon >= len(rows):
            raise ValueError("Holdout too short for requested origins")
        context = build_observation_window(
            raw, binding, {**request, "cutoff": rows[origin]["timestamp"]}
        )
        truth = [float(r["value"]) for r in rows[origin + 1 : origin + 1 + args.horizon]]
        result = await model.forecast(context)
        baseline = await PersistenceProvider().forecast(context)
        validate_forecast_result(result, args.horizon)
        p50 = result["quantiles"]["0.5"]
        origins.append(
            {
                "origin": context["origin"],
                "last_input_timestamp": context["observations"][-1]["timestamp"],
                "first_scored_timestamp": context["prediction_timestamps"][0],
                "horizon": args.horizon,
                "mae": sum(abs(a - v) for a, v in zip(truth, p50, strict=True)) / args.horizon,
                "persistence_mae": sum(
                    abs(a - v) for a, v in zip(truth, baseline["quantiles"]["0.5"], strict=True)
                )
                / args.horizon,
                "pinball": {q: pinball(v, truth, float(q)) for q, v in result["quantiles"].items()},
                "coverage_10_90": sum(
                    lower <= actual <= upper
                    for actual, lower, upper in zip(
                        truth, result["quantiles"]["0.1"], result["quantiles"]["0.9"], strict=True
                    )
                )
                / args.horizon,
                "result_provenance": {k: v for k, v in result.items() if k != "quantiles"},
            }
        )
    cancellation = {
        "status": "NOT_RUN",
        "database_artifacts": "NOT_APPLICABLE_DIRECT_MODEL_ENTRY",
        "object_storage": "NOT_APPLICABLE_DIRECT_MODEL_ENTRY",
    }
    if args.cancel_check:
        long_context = build_observation_window(
            raw, binding, {**request, "horizon": 120, "cutoff": rows[first]["timestamp"]}
        )
        model.model_ready_event.clear()
        task = asyncio.create_task(model.forecast(long_context))
        readiness = asyncio.create_task(model.model_ready_event.wait())
        await asyncio.wait({task, readiness}, return_when=asyncio.FIRST_COMPLETED)
        readiness.cancel()
        if task.done():
            await task
            raise RuntimeError("Model finished before cancellation; interruption was not verified")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
        cancellation.update(
            status="PASS_PROCESS_INTERRUPTED",
            model_ready_before_cancel=model.last_model_ready,
            interrupted=model.last_process_interrupted,
            process_exitcode=model.last_process_exitcode,
        )
        if model.last_process_exitcode is None or not model.last_process_interrupted:
            raise RuntimeError("Model process not interrupted")
    return {
        "status": "EXECUTED_NOT_INDUSTRIAL_ACCEPTANCE",
        "data_kind": binding["data_kind"],
        "source_checksum": digest,
        "model_revision": CHRONOS_REVISION,
        "split": {
            "method": "chronological_rolling_origin",
            "train_fraction": args.train_fraction,
            "step": args.step,
            "history": args.history,
        },
        "origins": origins,
        "process_cancellation": cancellation,
        "claim": "Conditional numerical baseline; no causal or fault probability conclusion.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, default=Path(".nexweave-data/models/chronos-2"))
    parser.add_argument("--revision", default=CHRONOS_REVISION)
    parser.add_argument("--train-fraction", type=float, default=0.6)
    parser.add_argument("--origins", type=int, default=4)
    parser.add_argument("--history", type=int, default=96)
    parser.add_argument("--horizon", type=int, default=12)
    parser.add_argument("--step", type=int, default=24)
    parser.add_argument("--unit", default="unit")
    parser.add_argument("--cancel-check", action="store_true")
    args = parser.parse_args()
    result = asyncio.run(run(args))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": result["status"],
                "origins": len(result["origins"]),
                "cancellation": result["process_cancellation"],
            }
        )
    )


if __name__ == "__main__":
    main()
