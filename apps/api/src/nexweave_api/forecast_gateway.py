"""Allowlisted model gateway and immutable CSV connector for the M9.5 worker."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from collections.abc import Callable
from importlib.metadata import version
from pathlib import Path
from typing import Any

from nexweave_api.object_storage import S3ObjectStorage
from nexweave_api.settings import Settings
from nexweave_contracts.forecast import TimeSeriesCapabilities
from nexweave_domain.semantic import SemanticRuleViolation

CHRONOS_REVISION = "29ec3766d36d6f73f0696f85560a422f50e8498c"

CONFIG_SHA256 = "ef1143bfdc9c0376d9a056eefca46cb4b1ec3d0ffacd541ff56feb40fb708031"
MODEL_SHA256 = "ddcda3c7508bf2528087723e98a20707cc04b7f370ae275a9fd88078ddba4f42"


class CsvTimeSeriesConnector:
    def __init__(self, storage: S3ObjectStorage, version_id: str | None = None) -> None:
        self.storage, self.version_id = storage, version_id

    async def read_window(self, object_key: str, checksum: str) -> bytes:
        raw = await self.storage.get(key=object_key, version_id=self.version_id)
        if "sha256:" + hashlib.sha256(raw).hexdigest() != checksum:
            raise SemanticRuleViolation("SOURCE_CHECKSUM_MISMATCH", "Source content changed.")
        return raw


class PersistenceProvider:
    def capabilities(self) -> TimeSeriesCapabilities:
        return TimeSeriesCapabilities(
            provider_id="persistence",
            model_revision="persistence/1",
            past_covariates=False,
            known_future_covariates=False,
            quantiles=(0.5,),
        )

    async def forecast(self, context: dict[str, Any]) -> dict[str, Any]:
        value = context["observations"][-1]["values"][context["target"]]
        return {
            "quantiles": {"0.5": [value] * len(context["prediction_timestamps"])},
            "provider_id": "persistence",
            "model_revision": "persistence/1",
            "covariates_used": False,
            "calibration": "NOT_APPLICABLE",
        }


class Chronos2Provider:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.pipeline: Any = None
        self._lock = asyncio.Lock()
        self.last_process_pid: int | None = None
        self.last_process_exitcode: int | None = None
        self.last_process_interrupted = False
        self.last_model_ready = False
        self.model_ready_event = asyncio.Event()

    def capabilities(self) -> TimeSeriesCapabilities:
        return TimeSeriesCapabilities(
            provider_id="chronos2",
            model_revision=self.settings.forecast_model_revision,
            past_covariates=True,
            known_future_covariates=True,
            quantiles=(0.1, 0.5, 0.9),
        )

    def verify_model(self) -> None:
        if self.settings.forecast_model_revision != CHRONOS_REVISION:
            raise SemanticRuleViolation(
                "MODEL_REVISION_MISMATCH", "Only the verified fixed Chronos revision is enabled."
            )
        root = Path(self.settings.forecast_model_path)
        model = root / "model.safetensors"
        if not model.is_file() or model.is_symlink() or not (root / "config.json").is_file():
            raise SemanticRuleViolation("MODEL_UNAVAILABLE", "Pinned model is not installed.")
        # No sharded index is accepted by this fixed single-safetensors provider.
        # This narrows exposure to accelerate CVE-2026-69112; the dependency
        # advisory itself remains an audit blocker until upstream is fixed.
        if any(root.glob("*.index.json")) or any(root.glob("*.bin")):
            raise SemanticRuleViolation(
                "MODEL_LAYOUT_UNSUPPORTED", "Only the verified single-file model layout is enabled."
            )
        config_digest = hashlib.sha256((root / "config.json").read_bytes()).hexdigest()
        if config_digest != CONFIG_SHA256:
            raise SemanticRuleViolation("MODEL_CONFIG_MISMATCH", "Pinned config integrity failed.")
        with model.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != MODEL_SHA256:
            raise SemanticRuleViolation("MODEL_CHECKSUM_MISMATCH", "Model integrity failed.")

    def _forecast(
        self, context: dict[str, Any], on_ready: Callable[[], None] | None = None
    ) -> dict[str, Any]:
        import pandas as pd
        import torch
        from chronos import Chronos2Pipeline

        if self.pipeline is None:
            self.verify_model()
            root = Path(self.settings.forecast_model_path)
            torch.set_num_threads(4)
            self.pipeline = Chronos2Pipeline.from_pretrained(
                str(root),
                device_map="cpu",
                local_files_only=True,
                trust_remote_code=False,
                torch_dtype=torch.float32,
            )
        history = pd.DataFrame(
            [
                {"item_id": "target", "timestamp": p["timestamp"], **p["values"]}
                for p in context["observations"]
            ]
        )
        history["timestamp"] = pd.to_datetime(history["timestamp"], utc=True).dt.tz_localize(None)
        future = pd.DataFrame(
            {
                "item_id": "target",
                "timestamp": pd.to_datetime(context["prediction_timestamps"], utc=True).tz_localize(
                    None
                ),
            }
        )
        for path in context["future_paths"]:
            future[path["signal_key"]] = path["values"]
        if on_ready:
            on_ready()
        output = self.pipeline.predict_df(
            history,
            future_df=future if context["future_paths"] else None,
            prediction_length=len(future),
            quantile_levels=[0.1, 0.5, 0.9],
            id_column="item_id",
            timestamp_column="timestamp",
            target=context["target"],
            cross_learning=False,
        )
        return {
            "quantiles": {str(q): output[str(q)].astype(float).tolist() for q in (0.1, 0.5, 0.9)},
            "provider_id": "chronos2",
            "model_revision": self.settings.forecast_model_revision,
            "weights_sha256": MODEL_SHA256,
            "config_sha256": CONFIG_SHA256,
            "runtime_versions": {
                name: version(name) for name in ("chronos-forecasting", "torch", "transformers")
            },
            "covariates_used": bool(
                context["profile"]["pastCovariates"] or context["future_paths"]
            ),
            "calibration": "UNVERIFIED",
            "execution": "LOCAL_CPU",
        }

    async def forecast(self, context: dict[str, Any]) -> dict[str, Any]:
        # A thread cannot stop Torch computation. A dedicated offline process
        # makes Activity cancellation observable and actually interrupts the model.
        async with self._lock:
            environment = {
                k: v for k, v in os.environ.items() if k in {"PATH", "SYSTEMROOT", "TMPDIR"}
            }
            environment.update(
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                PYTHONPATH=os.pathsep.join(sys.path),
                OMP_NUM_THREADS="4",
            )
            self.model_ready_event.clear()
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "nexweave_api.forecast_model_process",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
                env=environment,
                limit=8_000_000,
            )
            self.last_process_pid = process.pid
            self.last_process_exitcode = None
            self.last_process_interrupted = False
            self.last_model_ready = False
            request = json.dumps(
                {
                    "model_path": self.settings.forecast_model_path,
                    "model_revision": self.settings.forecast_model_revision,
                    "context": context,
                },
                allow_nan=False,
            ).encode()
            try:
                assert process.stdin is not None and process.stdout is not None
                process.stdin.write(request)
                await process.stdin.drain()
                process.stdin.close()

                async def collect() -> bytes:
                    assert process.stdout is not None
                    first = await process.stdout.readline()
                    if first.strip() == b'{"event":"MODEL_READY"}':
                        self.last_model_ready = True
                        self.model_ready_event.set()
                        first = b""
                    output = first + await process.stdout.read(8_000_001)
                    await process.wait()
                    return output

                raw = await asyncio.wait_for(collect(), timeout=590)
                if process.returncode != 0 or len(raw) > 8_000_000:
                    raise SemanticRuleViolation(
                        "MODEL_EXECUTION_FAILED", "The fixed offline model process failed."
                    )
                result: dict[str, Any] = json.loads(raw)
                return result
            except (asyncio.CancelledError, TimeoutError):
                self.last_process_interrupted = True
                if process.returncode is None:
                    process.terminate()
                    try:
                        await asyncio.wait_for(process.wait(), timeout=3)
                    except TimeoutError:
                        process.kill()
                        await process.wait()
                raise
            finally:
                self.last_process_exitcode = process.returncode


class ForecastModelGateway:
    """No SDK dispatch or provider-selected endpoints in domain, UI or Workflow."""

    def __init__(self, settings: Settings) -> None:
        from nexweave_application.forecast_ports import TimeSeriesModelProvider

        self.providers: dict[str, TimeSeriesModelProvider] = {
            "chronos2": Chronos2Provider(settings),
            "persistence": PersistenceProvider(),
        }

    async def forecast(self, provider_id: str, context: dict[str, Any]) -> dict[str, Any]:
        provider = self.providers[provider_id]
        capabilities = provider.capabilities()
        # Persistence is explicitly a benchmark, never a silent scenario fallback.
        if (
            provider_id != "persistence"
            and context["future_paths"]
            and not capabilities.known_future_covariates
        ):
            raise SemanticRuleViolation("CAPABILITY_UNSUPPORTED", "Future covariates unsupported.")
        return await provider.forecast(context)
