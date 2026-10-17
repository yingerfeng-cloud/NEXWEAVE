"""Evaluation cannot silently accept filters/configuration which Query rejects."""

import pytest
from pydantic import ValidationError

from nexweave_contracts.release import EvaluationRunCreate, QueryCreate
from nexweave_domain import new_uuid7


@pytest.mark.parametrize(
    "config",
    [
        {"ignored_option": True},
        {"filters": {"unsupported": "value"}},
        {"filters": {"predicate_key": ["wrong-type"]}},
        {"filters": {"subject_entity_id": "not-a-uuid"}},
        {"top_k": True},
        {"top_k": 0},
    ],
)
def test_invalid_evaluation_retrieval_configuration_fails_before_execution(config):
    with pytest.raises(ValidationError):
        EvaluationRunCreate(
            suite_id=new_uuid7(),
            target_type="RELEASE",
            target_id=new_uuid7(),
            retrieval_config=config,
        )


def test_query_and_evaluation_share_uuid_filter_normalization_and_attribute_requirement():
    uid = str(new_uuid7()).upper()
    query = QueryCreate(
        question="Pump",
        strategy="ATTRIBUTE",
        filters={"subject_entity_id": uid},
        client_request_id="config",
    )
    run = EvaluationRunCreate(
        suite_id=new_uuid7(),
        target_type="RELEASE",
        target_id=new_uuid7(),
        retrieval_strategy="ATTRIBUTE",
        retrieval_config={"filters": {"subject_entity_id": uid}},
    )
    assert run.retrieval_config["filters"] == query.filters == {"subject_entity_id": uid.lower()}
    with pytest.raises(ValidationError):
        EvaluationRunCreate(
            suite_id=new_uuid7(),
            target_type="RELEASE",
            target_id=new_uuid7(),
            retrieval_strategy="ATTRIBUTE",
        )
