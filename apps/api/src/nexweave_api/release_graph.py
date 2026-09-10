"""Bounded graph from frozen release snapshots and current source visibility."""

from collections import deque
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_domain import Principal

LEVEL = {"PUBLIC": 0, "INTERNAL": 1, "CONFIDENTIAL": 2, "HIGHLY_RESTRICTED": 3}


def traverse(
    nodes: dict[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    start: str,
    target: str | None,
    mode: str,
    max_depth: int,
) -> dict[str, Any]:
    if start not in nodes or (target is not None and target not in nodes):
        raise ApiProblem(
            404,
            "RESOURCE_NOT_FOUND",
            "Graph object unavailable",
            "The requested object is not visible in this Release.",
        )
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        if edge["source_entity_id"] in nodes and edge["target_entity_id"] in nodes:
            adjacency.setdefault(edge["source_entity_id"], []).append(edge)
    queue: deque[tuple[str, list[dict[str, Any]]]] = deque([(start, [])])
    visited = {start}
    selected: list[tuple[dict[str, Any], int]] = []
    found: list[dict[str, Any]] = []
    truncated = False
    while queue:
        node, path = queue.popleft()
        if mode == "SHORTEST" and node == target:
            found = path
            break
        if len(path) >= max_depth:
            continue
        for edge in adjacency.get(node, []):
            if mode != "SHORTEST":
                if len(selected) == 500:
                    truncated = True
                    queue.clear()
                    break
                selected.append((edge, len(path) + 1))
            destination = edge["target_entity_id"]
            if destination not in visited:
                visited.add(destination)
                queue.append((destination, [*path, edge]))
    if mode == "SHORTEST":
        selected = [(edge, depth + 1) for depth, edge in enumerate(found)]
    payload = [
        {
            "relation_id": e["id"],
            "relation_type_key": e["relation_type_key"],
            "source_entity_id": e["source_entity_id"],
            "target_entity_id": e["target_entity_id"],
            "evidence_ids": e["evidence_ids"],
            "depth": depth,
        }
        for e, depth in selected
    ]
    included = {start} | {e[k] for e in payload for k in ("source_entity_id", "target_entity_id")}
    return {"nodes": [nodes[i] for i in sorted(included)], "edges": payload, "truncated": truncated}


async def read_graph(
    connection: AsyncConnection,
    principal: Principal,
    release_id: UUID,
    start: UUID,
    target: UUID | None,
    mode: str,
    depth: int,
    causal: bool,
    as_of: datetime | None,
) -> dict[str, Any]:
    params = {
        "release": release_id,
        "tenant": principal.tenant_id,
        "clearance": LEVEL[principal.clearance.value],
        "causal": causal or mode == "CAUSAL",
        "as_of": as_of,
    }
    nodes_query = text("""
        SELECT ri.object_id,ri.snapshot FROM release_items ri
        JOIN knowledge_entity_versions ev ON CAST(ev.id AS text)=ri.snapshot->>'current_version_id'
        JOIN compile_job_sources cs ON cs.compile_job_id=ev.compile_job_id
        JOIN source_versions sv ON sv.id=cs.source_version_id
        JOIN source_documents sd ON sd.id=sv.source_document_id
        LEFT JOIN source_invalidations si ON si.source_version_id=sv.id AND si.tenant_id=:tenant
        WHERE ri.release_id=:release AND ri.tenant_id=:tenant AND ri.object_type='ENTITY'
        GROUP BY ri.id
        HAVING bool_and(sd.status<>'ARCHIVED')
           AND max(CASE sv.classification WHEN 'PUBLIC' THEN 0 WHEN 'INTERNAL' THEN 1
                   WHEN 'CONFIDENTIAL' THEN 2 ELSE 3 END)<=:clearance
           AND max(CASE sd.classification WHEN 'PUBLIC' THEN 0 WHEN 'INTERNAL' THEN 1
                   WHEN 'CONFIDENTIAL' THEN 2 ELSE 3 END)<=:clearance
           AND bool_and(si.source_version_id IS NULL)
        ORDER BY ri.object_id LIMIT 4001
    """)
    node_rows = (await connection.execute(nodes_query, params)).mappings().all()
    if len(node_rows) > 4000:
        raise ApiProblem(
            422,
            "GRAPH_BUDGET_EXCEEDED",
            "Graph budget exceeded",
            "This Release exceeds the bounded graph budget.",
        )
    nodes = {
        str(r["object_id"]): {
            k: dict(r["snapshot"])[k] for k in ("id", "type_key", "normalized_key", "display_name")
        }
        for r in node_rows
    }
    if str(start) not in nodes or (target is not None and str(target) not in nodes):
        raise ApiProblem(
            404,
            "RESOURCE_NOT_FOUND",
            "Graph object unavailable",
            "The requested object is not visible in this Release.",
        )
    edges_query = text("""
        SELECT ri.object_id,ri.snapshot,array_agg(er.id ORDER BY er.id) AS evidence_ids
        FROM release_items ri
        JOIN evidence_records er ON CAST(er.relation_id AS text)=CAST(ri.object_id AS text)
            AND er.status='ACCEPTED'
        JOIN release_items re ON re.release_id=ri.release_id AND re.object_type='EVIDENCE'
            AND re.object_id=er.id
        JOIN source_anchors sa ON sa.id=er.source_anchor_id AND sa.status='VALID'
        JOIN source_versions sv ON sv.id=sa.source_version_id
        JOIN source_documents sd ON sd.id=sv.source_document_id AND sd.status<>'ARCHIVED'
        WHERE ri.release_id=:release AND ri.tenant_id=:tenant AND ri.object_type='RELATION'
            AND re.snapshot->>'relation_id'=CAST(ri.object_id AS text)
            AND re.snapshot->>'source_anchor_id'=CAST(sa.id AS text)
            AND (NOT :causal OR CAST(ri.snapshot->>'is_causal' AS boolean))
            AND (CAST(:as_of AS timestamptz) IS NULL OR (
                (ri.snapshot->>'valid_from' IS NULL OR
                    CAST(ri.snapshot->>'valid_from' AS timestamptz)<=CAST(:as_of AS timestamptz))
                AND (ri.snapshot->>'valid_until' IS NULL OR
                    CAST(ri.snapshot->>'valid_until' AS timestamptz)>CAST(:as_of AS timestamptz))))
            AND NOT EXISTS (SELECT 1 FROM source_invalidations si
                            WHERE si.source_version_id=sv.id AND si.tenant_id=:tenant)
        GROUP BY ri.id
        HAVING max(CASE sv.classification WHEN 'PUBLIC' THEN 0 WHEN 'INTERNAL' THEN 1
                   WHEN 'CONFIDENTIAL' THEN 2 ELSE 3 END)<=:clearance
           AND max(CASE sd.classification WHEN 'PUBLIC' THEN 0 WHEN 'INTERNAL' THEN 1
                   WHEN 'CONFIDENTIAL' THEN 2 ELSE 3 END)<=:clearance
        ORDER BY ri.object_id LIMIT 2001
    """)
    rows = (await connection.execute(edges_query, params)).mappings().all()
    if len(rows) > 2000:
        raise ApiProblem(
            422,
            "GRAPH_BUDGET_EXCEEDED",
            "Graph budget exceeded",
            "This Release exceeds the bounded graph budget.",
        )
    edges = [
        {**dict(r["snapshot"]), "evidence_ids": [str(i) for i in r["evidence_ids"]]} for r in rows
    ]
    return traverse(nodes, edges, str(start), str(target) if target else None, mode, depth)
