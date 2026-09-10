"""Allowlisted model gateway and immutable CSV connector for the M9.5 worker."""

from __future__ import annotations

import asyncio
import hashlib
from importlib.metadata import version
from pathlib import Path
from typing import Any

from nexweave_api.object_storage import S3ObjectStorage
from nexweave_api.settings import Settings
from nexweave_contracts.forecast import TimeSeriesCapabilities
from nexweave_domain.semantic import SemanticRuleViolation

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

    def capabilities(self) -> TimeSeriesCapabilities:
        return TimeSeriesCapabilities(
            provider_id="chronos2",
            model_revision=self.settings.forecast_model_revision,
            past_covariates=True,
            known_future_covariates=True,
            quantiles=(0.1, 0.5, 0.9),
        )

    def verify_model(self) -> None:
        root = Path(self.settings.forecast_model_path)
        model = root / "model.safetensors"
        if not model.is_file():
            raise SemanticRuleViolation("MODEL_UNAVAILABLE", "Pinned model is not installed.")
        config_digest = hashlib.sha256((root / "config.json").read_bytes()).hexdigest()
        if config_digest != CONFIG_SHA256:
            raise SemanticRuleViolation("MODEL_CONFIG_MISMATCH", "Pinned config integrity failed.")
        with model.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if digest != MODEL_SHA256:
            raise SemanticRuleViolation("MODEL_CHECKSUM_MISMATCH", "Model integrity failed.")

    def _forecast(self, context: dict[str, Any]) -> dict[str, Any]:
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
            "covariates_used": True,
            "calibration": "UNVERIFIED",
            "execution": "LOCAL_CPU",
        }

    async def forecast(self, context: dict[str, Any]) -> dict[str, Any]:
        # Cancellation cannot interrupt a CPU thread. Keep its slot until it exits,
        # then propagate cancellation; the run's terminal guard forbids publication.
        async with self._lock:
            task = asyncio.create_task(asyncio.to_thread(self._forecast, context))
            try:
                return await asyncio.shield(task)
            except asyncio.CancelledError:
                try:
                    await task
                finally:
                    raise


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
