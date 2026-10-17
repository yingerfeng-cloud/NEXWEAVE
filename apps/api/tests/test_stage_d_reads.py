from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from nexweave_api.errors import ApiProblem
from nexweave_api.release_graph import traverse
from nexweave_api.release_repository import (
    ReleaseRepository,
    _answer_reason,
    _keyword_query_text,
)
from nexweave_domain import DataClassification, new_uuid7


def edge(a, b, identity=None):
    return {
        "id": identity or a + b,
        "source_entity_id": a,
        "target_entity_id": b,
        "relation_type_key": "test/relates",
        "evidence_ids": ["evidence"],
    }


def test_graph_membership_and_hidden_target_fail_closed():
    for start, target in [("outside", None), ("a", "outside")]:
        with pytest.raises(ApiProblem) as error:
            traverse({"a": {"id": "a"}}, [], start, target, "TRAVERSE", 3)
        assert error.value.status == 404


def test_graph_shortest_cycle_depth_and_frozen_nodes():
    nodes = {i: {"id": i, "display_name": "frozen " + i} for i in "abcd"}
    edges = [edge("a", "b"), edge("a", "c"), edge("b", "a"), edge("b", "c"), edge("c", "d")]
    shortest = traverse(nodes, edges, "a", "d", "SHORTEST", 3)
    assert [e["relation_id"] for e in shortest["edges"]] == ["ac", "cd"]
    one = traverse(nodes, edges, "a", None, "TRAVERSE", 1)
    assert len(one["edges"]) == 2 and not one["truncated"]
    assert all(n["display_name"].startswith("frozen") for n in one["nodes"])
    assert not traverse(nodes, edges, "a", "d", "SHORTEST", 1)["edges"]


def test_graph_output_limit_is_explicit_and_hides_unavailable_nodes():
    nodes = {str(i): {"id": str(i)} for i in range(503)}
    edges = [edge("0", str(i)) for i in range(1, 503)] + [edge("0", "hidden")]
    result = traverse(nodes, edges, "0", None, "TRAVERSE", 2)
    assert len(result["edges"]) == 500 and result["truncated"]
    assert "hidden" not in str(result)


def test_state_question_focus_keeps_entity_terms_for_keyword_retrieval():
    assert _keyword_query_text("What is the state of Pump A?") == "Pump A"
    assert _keyword_query_text("Pump A operational") == "Pump A operational"
    assert _keyword_query_text("  What is the status for Pump A?!  ") == "Pump A"


@pytest.mark.parametrize(
    ("candidate_count", "citation_count", "expected"),
    [
        (0, 0, "NO_MATCHING_KNOWLEDGE"),
        (3, 0, "EVIDENCE_UNAVAILABLE"),
        (3, 1, "SUPPORTED_EVIDENCE"),
    ],
)
def test_answer_reason_explains_fresh_query_without_leaking_hidden_objects(
    candidate_count: int, citation_count: int, expected: str
):
    assert (
        _answer_reason(
            candidate_count=candidate_count,
            citation_count=citation_count,
        )
        == expected
    )


def test_answer_reason_marks_historical_recheck_that_lost_all_citations():
    assert (
        _answer_reason(
            candidate_count=1,
            citation_count=0,
            historical=True,
            read_filtered=True,
        )
        == "HISTORICAL_RECHECK_UNAVAILABLE"
    )


@pytest.mark.asyncio
async def test_source_list_includes_only_versions_within_clearance():
    from types import SimpleNamespace

    from nexweave_api.source_repository import SourceRepository

    source_id, visible_id, hidden_id = new_uuid7(), new_uuid7(), new_uuid7()
    source_rows = [{"id": source_id, "classification": "INTERNAL"}]
    version_rows = [
        {
            "id": visible_id,
            "source_document_id": source_id,
            "classification": "INTERNAL",
            "status": "PARSED",
        },
        {
            "id": hidden_id,
            "source_document_id": source_id,
            "classification": "CONFIDENTIAL",
            "status": "PARSED",
        },
    ]
    source_result = MagicMock()
    source_result.mappings.return_value.all.return_value = source_rows
    version_result = MagicMock()
    version_result.mappings.return_value.all.return_value = version_rows
    connection = MagicMock()
    connection.__aenter__ = AsyncMock(return_value=connection)
    connection.__aexit__ = AsyncMock(return_value=None)

    async def execute(statement, _params):
        return version_result if "source_versions" in str(statement) else source_result

    connection.execute = AsyncMock(side_effect=execute)
    database = SimpleNamespace(engine=MagicMock())
    database.engine.connect.return_value = connection
    repository = SourceRepository(database)
    principal = SimpleNamespace(
        tenant_id=new_uuid7(),
        clearance=DataClassification.INTERNAL,
    )

    repository.principal_for_space = AsyncMock(return_value=principal)
    result = await repository.list_sources(principal=principal, space_id=new_uuid7())

    assert [version["id"] for version in result[0]["versions"]] == [str(visible_id)]
    assert str(hidden_id) not in str(result)
    assert connection.execute.await_count == 2


@pytest.mark.asyncio
async def test_only_cited_frozen_claims_can_become_answer_text():
    cid = new_uuid7()
    result = MagicMock()
    result.mappings.return_value.all.return_value = [
        {"object_id": cid, "snapshot": {"statement": "frozen supported statement"}}
    ]
    connection = MagicMock(execute=AsyncMock(return_value=result))
    hits = [
        {"object_type": "CLAIM", "object_id": str(cid), "text": "changed index text"},
        {"object_type": "CLAIM", "object_id": str(new_uuid7()), "text": "unsupported"},
    ]
    supported = await ReleaseRepository._supported_hits(
        None, connection, new_uuid7(), hits, [{"claim_id": str(cid)}]
    )
    assert [h["text"] for h in supported] == ["frozen supported statement"]
    assert await ReleaseRepository._supported_hits(None, connection, new_uuid7(), hits, []) == []


@pytest.mark.asyncio
async def test_query_replay_rejects_other_release_before_returning_answer():
    rid, answer_id = new_uuid7(), new_uuid7()
    connection = MagicMock()
    connection.__aenter__ = AsyncMock(return_value=connection)
    connection.__aexit__ = AsyncMock(return_value=None)
    query = MagicMock()
    query.scalar_one_or_none.return_value = answer_id
    connection.execute = AsyncMock(return_value=query)
    repo = MagicMock()
    repo._database.engine.connect.return_value = connection
    repo.principal_for_space = AsyncMock(return_value=MagicMock())
    repo.get_release = AsyncMock(return_value={"space_id": str(new_uuid7())})
    repo.get_query_answer = AsyncMock(
        return_value={
            "release_id": str(new_uuid7()),
            "question": "q",
            "retrieval_strategy": "HYBRID",
            "retrieval_config": {"top_k": 5, "filters": {}},
        }
    )
    with pytest.raises(ApiProblem) as error:
        await ReleaseRepository.query_release(
            repo,
            principal=MagicMock(),
            release_id=rid,
            payload={
                "client_request_id": "same",
                "question": "q",
                "strategy": "HYBRID",
                "top_k": 5,
            },
            trace_id="test",
        )
    assert error.value.status == 409
    repo.get_query_answer.assert_awaited_once_with(
        principal=repo.get_query_answer.call_args.kwargs["principal"],
        answer_id=UUID(str(answer_id)),
    )
