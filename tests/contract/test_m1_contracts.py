from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from nexweave_contracts import PlatformEntityChangedEventData, ServiceIdentityCreate, SpaceCreate
from nexweave_domain import DataClassification, Role, new_uuid7


def test_platform_entity_event_data_is_versioned_and_forbids_unknown_fields() -> None:
    event = PlatformEntityChangedEventData(
        entity_kind="MANAGED_OBJECT",
        entity_id=new_uuid7(),
        space_id=new_uuid7(),
        version=1,
        status="CLEAN",
        change="STORED",
        checksum="sha256:" + "a" * 64,
    )
    assert event.version == 1
    with pytest.raises(ValidationError):
        PlatformEntityChangedEventData.model_validate(
            {**event.model_dump(), "created_at": datetime.now(UTC)}
        )


def test_service_identity_requires_api_audience_and_least_privilege_role() -> None:
    valid = ServiceIdentityCreate(client_id="compiler", display_name="Compiler")
    assert valid.audiences == ("nexweave-api",)

    with pytest.raises(ValidationError, match="nexweave-api"):
        ServiceIdentityCreate(
            client_id="compiler",
            display_name="Compiler",
            audiences=("wrong-audience",),
        )
    with pytest.raises(ValidationError, match="service role"):
        ServiceIdentityCreate(
            client_id="compiler",
            display_name="Compiler",
            tenant_roles=(Role.TENANT_ADMIN,),
        )


def test_contracts_keep_domain_enums_in_memory_and_serialize_values_at_the_boundary() -> None:
    command = SpaceCreate(
        organization_id=new_uuid7(),
        slug="quality",
        display_name="Quality",
        default_classification=DataClassification.INTERNAL,
    )

    assert command.default_classification is DataClassification.INTERNAL
    assert command.model_dump(mode="json")["default_classification"] == "INTERNAL"
