"""Shared SQL retrieval and evidence-bound answer execution for Query and Evaluation."""

import json
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.derived_reads import DerivedReadGate
from nexweave_api.errors import ApiProblem
from nexweave_domain import Principal, new_uuid7, reciprocal_rank_fusion
from nexweave_domain.access import CLASSIFICATION_LEVEL

DOCS = """WITH documents AS (
    SELECT object_id,object_type,title,body,attributes,classification,
           to_tsvector('simple',title || ' ' || body) AS search_vector,
           CAST(embedding AS vector) AS embedding
    FROM jsonb_to_recordset(CAST(:documents AS jsonb)) AS d(
        object_id text,object_type text,title text,body text,attributes jsonb,
        classification integer,embedding text)
) """


async def retrieve(
    connection: AsyncConnection,
    documents: list[dict[str, Any]],
    payload: dict[str, Any],
    keyword_query: str,
    query_vector: Any,
    principal: Principal,
) -> list[dict[str, Any]]:
    filters = payload.get("filters", {})
    supported = {"predicate_key", "subject_entity_id"}
    if (
        not isinstance(filters, dict)
        or set(filters) - supported
        or any(not isinstance(v, str) or not v.strip() for v in filters.values())
    ):
        raise ApiProblem(
            422,
            "QUERY_FILTER_INVALID",
            "Invalid filter",
            "Supported string filters: predicate_key, subject_entity_id.",
        )
    if payload["strategy"] == "ATTRIBUTE" and not filters:
        raise ApiProblem(
            422,
            "QUERY_FILTER_REQUIRED",
            "Attribute filter required",
            "ATTRIBUTE requires an explicit supported filter.",
        )
    params = {
        "documents": json.dumps(documents),
        "query": keyword_query,
        "clearance": CLASSIFICATION_LEVEL[principal.clearance],
        "embedding": "[" + ",".join(str(float(v)) for v in query_vector) + "]",
        "limit": int(payload["top_k"]) * 4,
        "predicate": filters.get("predicate_key"),
        "subject": filters.get("subject_entity_id"),
    }
    base = """classification<=:clearance
        AND (CAST(:predicate AS text) IS NULL OR attributes->>'predicate_key'=:predicate)
        AND (CAST(:subject AS text) IS NULL OR attributes->>'subject_entity_id'=:subject)"""
    keyword = (
        (
            await connection.execute(
                text(  # noqa: S608
                    DOCS  # noqa: S608
                    + """
        SELECT object_id,ROW_NUMBER() OVER (
            ORDER BY ts_rank(search_vector,plainto_tsquery('simple',:query)) DESC,object_id) AS rank
        FROM documents WHERE """
                    + base
                    + (
                        ""
                        if payload["strategy"] == "ATTRIBUTE"
                        else " AND search_vector @@ plainto_tsquery('simple',:query)"
                    )
                    + " ORDER BY rank LIMIT :limit"
                ),
                params,
            )
        )
        .mappings()
        .all()
    )
    semantic = (
        (
            await connection.execute(
                text(  # noqa: S608
                    DOCS  # noqa: S608
                    + """
        SELECT object_id,1-(embedding <=> CAST(:embedding AS vector)) AS similarity,
            ROW_NUMBER() OVER (ORDER BY embedding <=> CAST(:embedding AS vector),object_id) AS rank
        FROM documents WHERE """
                    + base
                    + " ORDER BY embedding <=> CAST(:embedding AS vector),object_id LIMIT :limit"
                ),
                params,
            )
        )
        .mappings()
        .all()
    )
    rankings = {}
    if payload["strategy"] in {"KEYWORD", "ATTRIBUTE", "HYBRID"}:
        rankings["keyword"] = [str(item["object_id"]) for item in keyword]
    if payload["strategy"] in {"SEMANTIC", "HYBRID"}:
        rankings["semantic"] = [str(item["object_id"]) for item in semantic]
    keywords = {str(item["object_id"]) for item in keyword}
    similarities = {str(item["object_id"]): float(item["similarity"]) for item in semantic}
    fused = [
        item
        for item in reciprocal_rank_fusion(rankings)
        if item[0] in keywords or similarities.get(item[0], -1) >= 0.9
    ][: payload["top_k"]]
    by_id = {str(d["object_id"]): d for d in documents}
    return [
        {
            "object_type": by_id[i]["object_type"],
            "object_id": i,
            "title": by_id[i]["title"],
            "text": by_id[i]["body"],
            "ranks": ranks,
            "fusion_score": score,
        }
        for i, score, ranks in fused
    ]


async def ground(
    connection: AsyncConnection,
    principal: Principal,
    space_id: UUID,
    scope_id: UUID,
    scope_type: str,
    hits: list[dict[str, Any]],
    items: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    gate = DerivedReadGate(connection, principal, space_id)
    claims = {str(i["object_id"]): i["snapshot"] for i in items if i["object_type"] == "CLAIM"}
    evidence = [i for i in items if i["object_type"] == "EVIDENCE"]
    kept, citations = [], []
    for hit in hits:
        cid = str(hit["object_id"])
        if (
            hit["object_type"] != "CLAIM"
            or cid not in claims
            or not await gate.can_read("CLAIM", cid)
        ):
            continue
        supported = []
        for item in evidence:
            frozen = item["snapshot"]
            if str(frozen.get("claim_id")) != cid or frozen.get("stance") != "SUPPORTS":
                continue
            row = (
                (
                    await connection.execute(
                        text(
                            "SELECT er.*,sa.source_version_id,sa.locators FROM evidence_records er "
                            "JOIN source_anchors sa ON sa.id=er.source_anchor_id "
                            "WHERE er.id=:id AND er.claim_id=:claim AND er.status='ACCEPTED' "
                            "AND er.stance='SUPPORTS' AND sa.status='VALID'"
                        ),
                        {"id": UUID(str(item["object_id"])), "claim": UUID(cid)},
                    )
                )
                .mappings()
                .first()
            )
            if row is None or str(row["source_anchor_id"]) != str(frozen["source_anchor_id"]):
                continue
            if not await gate.can_read("EVIDENCE", row["id"], frozen):
                continue
            supported.append(
                {
                    "id": str(new_uuid7()),
                    "release_id": str(scope_id) if scope_type == "RELEASE" else None,
                    "evidence_id": str(row["id"]),
                    "source_version_id": str(row["source_version_id"]),
                    "source_anchor_id": str(row["source_anchor_id"]),
                    "claim_id": cid,
                    "relation_id": None,
                    "excerpt": None,
                    "locator": {"locators": row["locators"]},
                    "status": "VALID",
                }
            )
        if supported:
            kept.append({**hit, "text": claims[cid]["statement"], "title": "已审核主张"})
            citations.extend(supported)
    return kept[:3], [c for c in citations if c["claim_id"] in {h["object_id"] for h in kept[:3]}]


def compose(hits: list[dict[str, Any]], citations: list[dict[str, Any]]) -> dict[str, Any]:
    statements = [str(h["text"]) for h in hits]
    return {
        "status": "COMPLETED" if statements and citations else "REFUSED",
        "direct_answer": "；".join(statements)
        if statements and citations
        else "当前固定知识范围中没有足够的可见有效证据，无法下结论。",
        "key_basis": statements if citations else [],
    }
