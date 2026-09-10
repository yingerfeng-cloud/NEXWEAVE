from nexweave_api.model_gateway import LocalModelGateway
from nexweave_application import ModelGatewayRequest


async def test_local_model_gateway_accepts_replayable_tuple_inputs() -> None:
    request = ModelGatewayRequest(
        model_profile_id="model-v1",
        prompt_version_id="prompt-v1",
        classification="INTERNAL",
        schema_snapshot={
            "types": [{"key": "example.org/equipment", "abstract": False}],
            "properties": [],
            "terms": [],
            "relations": [],
        },
        segments=(
            {
                "id": "segment-v1",
                "normalized_text": "Pump A is operational.",
                "text_checksum": "sha256:" + "a" * 64,
                "locators": {"paragraph": 1},
                "anchor_id": "anchor-v1",
            },
        ),
        budget_units=10_000,
    )

    result = await LocalModelGateway().structured_output(request)

    assert result.provider_request_id.startswith("local:")
    assert result.estimated_cost_microunits == 0
    assert result.structured_output["entities"][0]["type_key"] == "example.org/equipment"
