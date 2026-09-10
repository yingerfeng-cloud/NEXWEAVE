from unittest.mock import AsyncMock

import pytest

from nexweave_api.errors import ApiProblem
from nexweave_api.semantic_repository import SemanticRepository
from nexweave_domain import ActorType, DataClassification, Principal, Role, new_uuid7


@pytest.mark.parametrize(
    "definition",
    [
        {"script": "alert(1)"},
        {"helpText": "javascript:alert(1)"},
        {"icon": "https://untrusted.example/icon.svg"},
        {"form": {"onClick": "run"}},
    ],
)
def test_declarative_pack_values_reject_code_and_remote_content(
    definition: dict[str, object],
) -> None:
    with pytest.raises(ApiProblem) as raised:
        SemanticRepository._validate_declarative_value(definition)
    assert raised.value.code == "PACK_ARTIFACT_INVALID"


def test_ui_declaration_rejects_fields_outside_allowlist() -> None:
    with pytest.raises(ApiProblem) as raised:
        SemanticRepository._validate_pack_owned_keys(
            {
                "semantic.json": {
                    "ui": [
                        {
                            "key": "example.org/equipment-form",
                            "definition": {"customComponent": "EquipmentEditor"},
                        }
                    ]
                }
            },
            "example.org",
        )
    assert raised.value.code == "PACK_ARTIFACT_INVALID"


@pytest.mark.asyncio
async def test_pack_evaluation_suite_persists_m7_required_creator() -> None:
    connection = AsyncMock()
    principal = Principal(
        actor_type=ActorType.USER,
        actor_id=new_uuid7(),
        tenant_id=new_uuid7(),
        subject="pack-installer",
        audience=("nexweave-api",),
        tenant_roles=frozenset({Role.SPACE_ADMIN}),
        clearance=DataClassification.INTERNAL,
        token_id=str(new_uuid7()),
    )
    repository = object.__new__(SemanticRepository)

    await repository._persist_semantic_snapshot(
        connection,
        principal=principal,
        space_id=new_uuid7(),
        schema_version_id=new_uuid7(),
        snapshot={
            "evaluationSuites": [
                {
                    "key": "equipment.rca/standard-questions-v1",
                    "definition": {"name": "Equipment RCA standard questions"},
                }
            ]
        },
    )

    connection.execute.assert_awaited_once()
    statement, parameters = connection.execute.await_args.args
    assert "definition,created_by" in str(statement)
    assert ":actor" in str(statement)
    assert parameters["actor"] == principal.actor_id
