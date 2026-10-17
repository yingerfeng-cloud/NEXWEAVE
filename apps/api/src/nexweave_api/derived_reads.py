"""One current-dependency gate for draft and frozen derived content.

Callers authorize the space and supply its effective (membership-capped) principal.
All source inputs are checked, including invalid inputs and opposing evidence, so
a surviving low-classification source cannot declassify a compound statement.
Snapshots select historical entity/page versions; returned content stays frozen.
"""

from collections.abc import Awaitable, Callable
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_domain import Principal
from nexweave_domain.access import CLASSIFICATION_LEVEL

_TABLES = {
    "CLAIM": "claims",
    "CLAIM_CANDIDATE": "claim_candidates",
    "RELATION": "relations",
    "RELATION_CANDIDATE": "candidate_relations",
    "SEMANTIC_PROPOSAL": "semantic_change_proposals",
    "ENTITY": "knowledge_entities",
    "WIKI_PAGE": "wiki_pages",
    "WIKI_PAGE_VERSION": "wiki_page_versions",
    "EVIDENCE": "evidence_records",
    "EVIDENCE_CANDIDATE": "evidence_candidates",
    "COMPILE_JOB": "compile_jobs",
}


class DerivedReadGate:
    def __init__(
        self,
        connection: AsyncConnection,
        principal: Principal,
        space_id: UUID,
        denial_recorder: Callable[..., Awaitable[None]] | None = None,
    ):
        self.connection = connection
        self.principal = principal
        self.space_id = space_id
        self.denial_recorder = denial_recorder

    async def can_read(
        self, kind: str, object_id: UUID | str, snapshot: dict[str, Any] | None = None
    ) -> bool:
        table = _TABLES.get(kind)
        if table is None:
            return False
        row = (
            (
                await self.connection.execute(
                    text(
                        f"SELECT * FROM {table} WHERE id=:id AND tenant_id=:tenant "  # noqa: S608
                        "AND space_id=:space"
                    ),
                    {
                        "id": UUID(str(object_id)),
                        "tenant": self.principal.tenant_id,
                        "space": self.space_id,
                    },
                )
            )
            .mappings()
            .first()
        )
        if row is None:
            return False
        value = dict(snapshot or row)
        if kind == "WIKI_PAGE":
            version = value.get("current_version_id")
            return version is not None and await self.can_read("WIKI_PAGE_VERSION", version)
        if kind == "ENTITY":
            version = value.get("current_version_id")
            query = "SELECT compile_job_id FROM knowledge_entity_versions WHERE id=:id"
            dependency_id = version
        elif kind == "WIKI_PAGE_VERSION":
            # Manual versions copy previous generated sections, but have NULL job.
            # Conservatively retain every earlier compilation dependency of the page.
            query = (
                "SELECT compile_job_id FROM wiki_page_versions WHERE wiki_page_id=:id "
                "AND revision<=:revision AND compile_job_id IS NOT NULL"
            )
            dependency_id = value["wiki_page_id"]
        elif kind in {"CLAIM", "RELATION"}:
            candidate = "claim_candidates" if kind == "CLAIM" else "candidate_relations"
            query = f"SELECT compile_job_id FROM {candidate} WHERE id=:id"  # noqa: S608
            dependency_id = value["candidate_id"]
        elif kind in {"EVIDENCE", "EVIDENCE_CANDIDATE"}:
            query = "SELECT source_version_id FROM source_anchors WHERE id=:id AND status='VALID'"
            dependency_id = value["source_anchor_id"]
        else:
            query = "SELECT CAST(:id AS uuid) AS compile_job_id"
            dependency_id = object_id if kind == "COMPILE_JOB" else value["compile_job_id"]
        ids = (
            list(
                (
                    await self.connection.execute(
                        text(query),
                        {"id": UUID(str(dependency_id)), "revision": value.get("revision", 0)},
                    )
                )
                .scalars()
                .all()
            )
            if dependency_id
            else []
        )
        if kind not in {"EVIDENCE", "EVIDENCE_CANDIDATE"} and ids:
            ids = list(
                (
                    await self.connection.execute(
                        text(
                            "SELECT source_version_id FROM compile_job_sources WHERE "
                            "compile_job_id IN :ids"
                        ).bindparams(bindparam("ids", expanding=True)),
                        {"ids": ids},
                    )
                )
                .scalars()
                .all()
            )
        if kind in {"CLAIM", "RELATION"}:
            column = "claim_id" if kind == "CLAIM" else "relation_id"
            evidence = (
                (
                    await self.connection.execute(
                        text(
                            f"SELECT er.status,er.stance,sa.status AS "  # noqa: S608
                            f"anchor_status,sa.source_version_id "  # noqa: S608
                            f"FROM evidence_records er JOIN source_anchors sa ON "
                            f"sa.id=er.source_anchor_id "
                            f"WHERE er.{column}=:id"
                        ),
                        {"id": UUID(str(object_id))},
                    )
                )
                .mappings()
                .all()
            )
            ids.extend(e["source_version_id"] for e in evidence)
            if not any(
                e["status"] == "ACCEPTED"
                and e["stance"] == "SUPPORTS"
                and e["anchor_status"] == "VALID"
                for e in evidence
            ):
                return False
        if kind == "EVIDENCE" and value.get("status") != "ACCEPTED":
            return False
        if not ids:
            return False
        rows = (
            (
                await self.connection.execute(
                    text(
                        "SELECT sv.id,sv.classification,sd.classification AS "
                        "document_classification,"
                        "sd.status,EXISTS (SELECT 1 FROM source_invalidations si "
                        "WHERE si.source_version_id=sv.id) AS invalidated "
                        "FROM source_versions sv JOIN source_documents sd ON "
                        "sd.id=sv.source_document_id "
                        "WHERE sv.tenant_id=:tenant AND sv.space_id=:space AND sv.id IN :ids"
                    ).bindparams(bindparam("ids", expanding=True)),
                    {
                        "tenant": self.principal.tenant_id,
                        "space": self.space_id,
                        "ids": list(set(ids)),
                    },
                )
            )
            .mappings()
            .all()
        )
        clearance = CLASSIFICATION_LEVEL[self.principal.clearance]
        from nexweave_domain import DataClassification

        return len(rows) == len(set(ids)) and all(
            r["status"] != "ARCHIVED"
            and not r["invalidated"]
            and max(
                CLASSIFICATION_LEVEL[DataClassification(r[k])]
                for k in ("classification", "document_classification")
            )
            <= clearance
            for r in rows
        )

    async def require(
        self, kind: str, object_id: UUID | str, snapshot: dict[str, Any] | None = None
    ) -> None:
        if not await self.can_read(kind, object_id, snapshot):
            if self.denial_recorder is not None:
                from nexweave_domain import new_uuid7

                await self.denial_recorder(
                    principal=self.principal,
                    action="derived.read",
                    resource_type=kind,
                    resource_id=UUID(str(object_id)),
                    space_id=self.space_id,
                    trace_id=str(new_uuid7()),
                    reason="CURRENT_DEPENDENCY_UNAVAILABLE",
                )
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Content unavailable",
                "The requested content is not currently readable.",
            )
