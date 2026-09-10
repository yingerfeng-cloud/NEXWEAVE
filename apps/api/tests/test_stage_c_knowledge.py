from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from nexweave_api.errors import ApiProblem
from nexweave_api.forecast_knowledge import ForecastKnowledgeService
from nexweave_contracts.forecast import ForecastKnowledgeRequest
from nexweave_domain import DataClassification, new_uuid7


def setup_service():
    space, release, artifact = new_uuid7(), new_uuid7(), new_uuid7()
    connection = MagicMock()
    connection.__aenter__ = AsyncMock(return_value=connection)
    connection.__aexit__ = AsyncMock(return_value=None)
    repo = SimpleNamespace(
        get_artifact=AsyncMock(return_value={"space_id": str(space), "content_checksum": "fixed"}),
        authorize=AsyncMock(),
        database=SimpleNamespace(engine=MagicMock()),
        platform=SimpleNamespace(
            get_release=AsyncMock(
                return_value={"space_id": str(space), "manifest_checksum": "release"}
            ),
            query_release=AsyncMock(
                return_value={
                    "id": str(new_uuid7()),
                    "citations": [],
                    "direct_answer": "DO NOT TRUST UNGROUNDED TEXT",
                }
            ),
            _insert_audit=AsyncMock(),
        ),
    )
    repo.database.engine.begin.return_value = connection
    repo.database.engine.connect.return_value = connection
    return ForecastKnowledgeService(repo), repo, artifact, release, connection


@pytest.mark.asyncio
async def test_cross_space_release_fails_before_retrieval():
    service, repo, artifact, release, _ = setup_service()
    repo.platform.get_release.return_value["space_id"] = str(new_uuid7())
    with pytest.raises(ApiProblem) as error:
        await service.build(
            object(), artifact, ForecastKnowledgeRequest(release_id=release, question="q"), "trace"
        )
    assert error.value.status == 404
    repo.platform.query_release.assert_not_awaited()


@pytest.mark.asyncio
async def test_no_citations_never_uses_generated_answer_or_writes_forecast():
    service, repo, artifact, release, _ = setup_service()
    result = await service.build(
        object(), artifact, ForecastKnowledgeRequest(release_id=release, question="q"), "trace"
    )
    assert result["status"] == "INSUFFICIENT_EVIDENCE" and result["items"] == []
    assert "DO NOT TRUST" not in str(result)
    assert repo.get_artifact.await_count == 2
    repo.platform._insert_audit.assert_awaited_once()


@pytest.mark.asyncio
async def test_query_permission_denial_prevents_release_read_and_retrieval():
    service, repo, artifact, release, _ = setup_service()
    repo.authorize.side_effect = ApiProblem(403, "ACCESS_DENIED", "Denied", "Denied")
    with pytest.raises(ApiProblem):
        await service.build(
            object(), artifact, ForecastKnowledgeRequest(release_id=release, question="q"), "trace"
        )
    repo.platform.get_release.assert_not_awaited()
    repo.platform.query_release.assert_not_awaited()


@pytest.mark.asyncio
async def test_visible_items_exclude_other_release_high_clearance_and_wrong_claim():
    service, _, _, release, connection = setup_service()
    eid, claim = new_uuid7(), new_uuid7()
    citation = {
        "id": str(new_uuid7()),
        "evidence_id": str(eid),
        "claim_id": str(claim),
        "release_id": str(release),
    }
    row = {
        "evidence_id": eid,
        "claim_id": claim,
        "statement": "frozen statement",
        "source_document_id": new_uuid7(),
        "anchor_id": new_uuid7(),
        "source_id": new_uuid7(),
        "locators": [],
        "classification": "PUBLIC",
        "document_classification": "PUBLIC",
        "claim_classification": "CONFIDENTIAL",
    }
    query_result = MagicMock()
    query_result.mappings.return_value.all.return_value = [row]
    connection.execute = AsyncMock(return_value=query_result)
    principal = SimpleNamespace(tenant_id=new_uuid7(), clearance=DataClassification.INTERNAL)
    assert (
        await service.visible_items(
            principal, release, [{**citation, "release_id": str(new_uuid7())}]
        )
        == []
    )
    connection.execute.assert_not_awaited()
    assert await service.visible_items(principal, release, [citation]) == []
    row["claim_classification"] = "PUBLIC"
    assert (
        await service.visible_items(
            principal, release, [{**citation, "claim_id": str(new_uuid7())}]
        )
        == []
    )
    items = await service.visible_items(principal, release, [citation])
    assert items[0]["statement"] == "frozen statement"
    assert items[0]["citation"]["source_anchor_id"] == str(row["anchor_id"])


def test_blank_question_rejected():
    with pytest.raises(ValidationError):
        ForecastKnowledgeRequest(release_id=new_uuid7(), question="   ")
