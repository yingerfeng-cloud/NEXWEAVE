"""Provider-neutral M5 Model Gateway with a replayable local structured provider."""

from __future__ import annotations

import time
from dataclasses import asdict
from hashlib import sha256

from nexweave_api.errors import ApiProblem
from nexweave_application import ModelGatewayRequest, ModelGatewayResult
from nexweave_domain import canonical_json, local_structured_compile, sha256_checksum


def _json_ready(value: object) -> object:
    if isinstance(value, tuple):
        return [_json_ready(item) for item in value]
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    return value


class LocalModelGateway:
    """No-network provider for local acceptance; never claims an external LLM call."""

    async def structured_output(self, request: ModelGatewayRequest) -> ModelGatewayResult:
        started = time.monotonic()
        input_document = {
            "model_profile_id": request.model_profile_id,
            "prompt_version_id": request.prompt_version_id,
            "classification": request.classification,
            "schema_snapshot": request.schema_snapshot,
            "segments": list(request.segments),
        }
        input_bytes = canonical_json(input_document)
        input_units = max(1, len(input_bytes) // 4)
        if input_units > request.budget_units:
            raise ApiProblem(
                422,
                "MODEL_BUDGET_EXCEEDED",
                "Model budget exceeded",
                "The structured compile request exceeds its configured unit budget.",
            )
        compiled = local_structured_compile(
            schema_snapshot=request.schema_snapshot, segments=request.segments
        )
        output = {
            "entities": [_json_ready(asdict(value)) for value in compiled.entities],
            "claims": [_json_ready(asdict(value)) for value in compiled.claims],
            "relations": [_json_ready(asdict(value)) for value in compiled.relations],
            "semantic_proposals": [
                _json_ready(asdict(value)) for value in compiled.semantic_proposals
            ],
            "provider": "nexweave.local-structured/1",
        }
        output_bytes = canonical_json(output)
        return ModelGatewayResult(
            provider_request_id="local:" + sha256(input_bytes).hexdigest()[:24],
            structured_output=output,
            input_checksum=sha256_checksum(input_bytes),
            output_checksum=sha256_checksum(output_bytes),
            input_units=input_units,
            output_units=max(1, len(output_bytes) // 4),
            latency_ms=max(0, int((time.monotonic() - started) * 1000)),
            estimated_cost_microunits=0,
        )

    async def embedding(
        self, *, model_profile_id: str, texts: tuple[str, ...]
    ) -> tuple[tuple[float, ...], ...]:
        vectors: list[tuple[float, ...]] = []
        for text in texts:
            digest = sha256(f"{model_profile_id}\0{text}".encode()).digest()
            vectors.append(tuple((byte - 127.5) / 127.5 for byte in digest[:16]))
        return tuple(vectors)
