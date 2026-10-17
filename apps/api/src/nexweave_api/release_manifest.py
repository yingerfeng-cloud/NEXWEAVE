"""Freeze only selected content's entity versions and Wiki source context."""

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_api.repository import _json_value


async def wiki_manifest_refs(
    connection: AsyncConnection, tenant: UUID, space: UUID, versions: list[Any]
) -> tuple[set[UUID], list[dict[str, str]]]:
    if not versions:
        return set(), []
    rows = (
        (
            await connection.execute(
                text(
                    "SELECT DISTINCT wp.primary_entity_id,pv.id AS page_version_id,sa.id "
                    "AS anchor_id,"
                    "sa.source_version_id,sv.checksum FROM wiki_page_versions pv "
                    "JOIN wiki_pages wp ON wp.id=pv.wiki_page_id "
                    "JOIN wiki_page_versions previous ON previous.wiki_page_id=pv.wiki_page_id "
                    "AND previous.revision<=pv.revision "
                    "JOIN compile_job_sources cs ON cs.compile_job_id=previous.compile_job_id "
                    "JOIN source_versions sv ON sv.id=cs.source_version_id "
                    "JOIN source_anchors sa ON sa.source_version_id=sv.id AND "
                    "sa.parse_job_id=sv.active_parse_job_id "
                    "WHERE pv.tenant_id=:tenant AND pv.space_id=:space AND pv.id=ANY(:ids)"
                ),
                {"tenant": tenant, "space": space, "ids": [UUID(str(v)) for v in versions]},
            )
        )
        .mappings()
        .all()
    )
    return (
        {UUID(str(r["primary_entity_id"])) for r in rows},
        [
            {
                "source_version_id": str(r["source_version_id"]),
                "source_anchor_id": str(r["anchor_id"]),
                "source_checksum": str(r["checksum"]),
                "wiki_page_version_id": str(r["page_version_id"]),
            }
            for r in rows
        ],
    )


async def freeze_selected_entities(
    connection: AsyncConnection,
    tenant: UUID,
    space: UUID,
    entity_ids: set[UUID],
    groups: dict[str, list[Any]],
) -> dict[str, Any]:
    # The mutable current_version_id may point to an unselected subsequent compile.
    # All selected objects remain individually subject to the shared read gate.
    jobs = (
        (
            await connection.execute(
                text(
                    "SELECT cc.compile_job_id FROM claims c JOIN claim_candidates cc ON "
                    "cc.id=c.candidate_id "
                    "WHERE c.tenant_id=:tenant AND c.space_id=:space AND c.id=ANY(:claims) "
                    "UNION SELECT cr.compile_job_id FROM relations r JOIN "
                    "candidate_relations cr ON cr.id=r.candidate_id "
                    "WHERE r.tenant_id=:tenant AND r.space_id=:space AND r.id=ANY(:relations) "
                    "UNION SELECT previous.compile_job_id FROM wiki_page_versions pv "
                    "JOIN wiki_page_versions previous ON "
                    "previous.wiki_page_id=pv.wiki_page_id AND "
                    "previous.revision<=pv.revision "
                    "WHERE pv.tenant_id=:tenant AND pv.space_id=:space AND pv.id=ANY(:pages) "
                    "AND previous.compile_job_id IS NOT NULL"
                ),
                {
                    "tenant": tenant,
                    "space": space,
                    "claims": [UUID(str(v)) for v in groups["CLAIM"]],
                    "relations": [UUID(str(v)) for v in groups["RELATION"]],
                    "pages": [UUID(str(v)) for v in groups["WIKI_PAGE_VERSION"]],
                },
            )
        )
        .scalars()
        .all()
    )
    snapshots = {}
    for entity_id in sorted(entity_ids, key=str):
        row = (
            (
                await connection.execute(
                    text(
                        "SELECT e.*,ev.id AS selected_version_id FROM knowledge_entities e "
                        "JOIN knowledge_entity_versions ev ON ev.entity_id=e.id "
                        "AND ev.tenant_id=e.tenant_id AND ev.space_id=e.space_id "
                        "WHERE e.tenant_id=:tenant AND e.space_id=:space AND e.id=:id "
                        "AND ev.compile_job_id=ANY(:jobs) ORDER BY ev.revision DESC,ev.id"
                        " DESC LIMIT 1"
                    ),
                    {"tenant": tenant, "space": space, "id": entity_id, "jobs": list(jobs)},
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            raise ApiProblem(
                409,
                "RELEASE_ENTITY_VERSION_UNAVAILABLE",
                "Entity version unavailable",
                "Each released entity must have a version from selected content's compilation.",
            )
        snapshot = _json_value(row)
        snapshot["current_version_id"] = snapshot.pop("selected_version_id")
        snapshots[str(entity_id)] = snapshot
    return snapshots
