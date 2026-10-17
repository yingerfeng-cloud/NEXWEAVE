"""Protocol/provider boundary tests with substitute HTTP, never model accuracy evidence."""

import copy
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from nexweave_api.configured_model_gateway import (
    ConfiguredModelGateway,
    profile_fingerprint,
    validate_extraction,
)
from nexweave_api.errors import ApiProblem
from nexweave_api.model_gateway import LocalModelGateway
from nexweave_api.settings import Settings
from nexweave_application import ModelGatewayRequest


def test_verbatim_statement_with_secondary_entity_is_retrievable_without_wrong_object_answers():
    from nexweave_api.lexical_search import keyword_ranking

    statement = "Pump A. Pump A temperature is 70 degC. Pump A feeds Pump B."
    docs = [
        {"object_type": "CLAIM", "object_id": "approved-a", "title": "Pump A", "body": statement}
    ]
    assert keyword_ranking(docs, statement) == ["approved-a"]
    assert keyword_ranking(docs, "What is the temperature of Pump A?") == ["approved-a"]
    assert keyword_ranking(docs, "What is the temperature of Pump B?") == []
    assert keyword_ranking(docs, "What is the temperature of Pump A and Pump Z?") == []


def test_fixed_chronos_loader_rejects_untrusted_shard_indexes_before_loading(tmp_path):
    from nexweave_api.forecast_gateway import Chronos2Provider
    from nexweave_domain.semantic import SemanticRuleViolation

    (tmp_path / "model.safetensors").write_bytes(b"not loaded")
    (tmp_path / "config.json").write_text("{}")
    (tmp_path / "model.safetensors.index.json").write_text('{"weight_map":{"x":"../../outside"}}')
    provider = Chronos2Provider(Settings(_env_file=None, forecast_model_path=str(tmp_path)))
    with pytest.raises(SemanticRuleViolation) as error:
        provider.verify_model()
    assert error.value.code == "MODEL_LAYOUT_UNSUPPORTED"


class Gateway(ConfiguredModelGateway):
    def __init__(self, profile, handler):
        super().__init__(
            SimpleNamespace(
                settings=Settings(
                    _env_file=None, model_gateway_endpoint="http://127.0.0.1:19999/v1"
                )
            ),
            httpx.MockTransport(handler),
        )
        self.saved, self.calls = profile, []

    async def profile(self, profile_id):
        return self.saved

    async def _audit(self, *args):
        self.calls.append(args)


def profile():
    return {
        "id": str(uuid4()),
        "version": 1,
        "provider": "openai-compatible",
        "model_name": "pinned-embedding-model",
        "config": {"revision": "weights-sha256-test", "capability": "embedding", "dimensions": 3},
        "maximum_classification": "INTERNAL",
        "externally_hosted": False,
        "credential_ref": None,
    }


def test_gateway_configuration_fingerprint_and_actual_input_classification():
    p = profile()
    gateway = Gateway(p, lambda request: httpx.Response(500))
    assert gateway.configuration(p, "embedding")["dimensions"] == 3
    assert gateway._policy(p, "INTERNAL", "embedding")
    with pytest.raises(ApiProblem) as denied:
        gateway._policy(p, "HIGHLY_RESTRICTED", "embedding")
    assert denied.value.code == "MODEL_CLASSIFICATION_DENIED"
    assert profile_fingerprint(p, endpoint="https://one.example/v1") != profile_fingerprint(
        p, endpoint="https://two.example/v1"
    )


async def test_no_hash_or_production_rule_substitute():
    with pytest.raises(ApiProblem) as error:
        await LocalModelGateway(Settings(_env_file=None)).embedding(
            model_profile_id="unused", texts=("中文同义词",)
        )
    assert error.value.code == "MODEL_PROVIDER_UNAVAILABLE"
    gateway = LocalModelGateway(Settings(_env_file=None).model_copy(update={"env": "production"}))
    with pytest.raises(ApiProblem):
        await gateway.structured_output(
            ModelGatewayRequest("model", "prompt", "INTERNAL", {}, (), 100)
        )


@pytest.mark.parametrize(
    "fault", [None, "dimension", "nan", "duplicate", "wrong_model", "redirect"]
)
async def test_real_embedding_protocol_validates_order_dimensions_revision_and_no_redirect(fault):
    p = profile()

    def respond(request):
        assert request.url.path == "/v1/embeddings"
        if fault == "redirect":
            return httpx.Response(302, headers={"location": "https://untrusted.invalid"})
        data = [
            {"index": 1, "embedding": [0.0, 1.0, 0.0]},
            {"index": 0, "embedding": [1.0, 0.0, 0.0]},
        ]
        if fault == "dimension":
            data[0]["embedding"] = [1.0]
        if fault == "nan":
            data[0]["embedding"] = ["nan", 1, 0]
        if fault == "duplicate":
            data[0]["index"] = 0
        return httpx.Response(
            200,
            json={
                "data": data,
                "model": "other-model" if fault == "wrong_model" else p["model_name"],
            },
            headers={"x-request-id": "test-real-protocol"},
        )

    gateway = Gateway(p, respond)
    if fault:
        with pytest.raises(ApiProblem):
            await gateway.embedding(
                model_profile_id=p["id"], texts=("温度", "temperature"), classification="INTERNAL"
            )
        assert not gateway.calls
    else:
        vectors = await gateway.embedding(
            model_profile_id=p["id"], texts=("温度", "temperature"), classification="INTERNAL"
        )
        assert vectors == ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))
        assert gateway.calls and profile_fingerprint(p) != profile_fingerprint({**p, "version": 2})


async def test_classification_and_unimplemented_secret_reference_fail_before_network():
    def should_not_call(request):
        raise AssertionError("Network must not be called")

    p = profile()
    gateway = Gateway(p, should_not_call)
    with pytest.raises(ApiProblem) as denied:
        await gateway.embedding(
            model_profile_id=p["id"], texts=("restricted",), classification="CONFIDENTIAL"
        )
    assert denied.value.code == "MODEL_CLASSIFICATION_DENIED"
    p["credential_ref"] = "vault://uninstalled-resolver"
    with pytest.raises(ApiProblem):
        await gateway.embedding(
            model_profile_id=p["id"], texts=("allowed",), classification="INTERNAL"
        )


def test_text_provider_rejects_fabricated_claim_quotes_before_persistence():
    request = ModelGatewayRequest(
        "model",
        "prompt",
        "INTERNAL",
        {
            "types": [{"key": "example.io/device"}],
            "properties": [{"key": "example.io/state", "typeKey": "example.io/device"}],
        },
        ({"id": "s1", "anchor_id": "a1", "normalized_text": "Device P101 is operational."},),
        100,
    )
    from nexweave_domain import normalize_entity_key

    key = "example.io/device:" + normalize_entity_key("Device P101")
    output = {
        "entities": [
            {
                "type_key": "example.io/device",
                "normalized_key": normalize_entity_key("Device P101"),
                "display_name": "Device P101",
                "attributes": {},
                "aliases": [],
                "segment_id": "s1",
                "anchor_id": "a1",
                "quote": "Device P101 is operational.",
            }
        ],
        "claims": [
            {
                "entity_key": key,
                "predicate_key": "example.io/state",
                "statement": "Device P101 is operational.",
                "object_value": {},
                "segment_id": "s1",
                "anchor_id": "a1",
                "quote": "Device P101 is operational.",
            }
        ],
        "relations": [],
        "semantic_proposals": [],
    }
    validate_extraction(output, request)
    bad = copy.deepcopy(output)
    bad["claims"][0]["statement"] = "Device P101 has failed."
    with pytest.raises(ValueError):
        validate_extraction(bad, request)
    bad = copy.deepcopy(output)
    bad["entities"][0]["anchor_id"] = "other-anchor"
    with pytest.raises(ValueError):
        validate_extraction(bad, request)
    bad = copy.deepcopy(output)
    bad["claims"] = [None]
    with pytest.raises(ValueError):
        validate_extraction(bad, request)
    # A real quote about B must not become a claim about A.
    request.segments[0]["normalized_text"] += " Device P102 is stopped."
    bad = copy.deepcopy(output)
    bad["claims"][0].update(statement="Device P102 is stopped.", quote="Device P102 is stopped.")
    with pytest.raises(ValueError):
        validate_extraction(bad, request)
