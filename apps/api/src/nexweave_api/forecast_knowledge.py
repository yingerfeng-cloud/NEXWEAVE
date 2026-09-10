"""Read-time composition of immutable forecasts and currently visible released evidence."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import bindparam, text

from nexweave_api.errors import ApiProblem
from nexweave_api.forecast_repository import ForecastRepository
from nexweave_contracts.forecast import ForecastKnowledgeRequest
from nexweave_domain import DataClassification, Principal
from nexweave_domain.access import CLASSIFICATION_LEVEL


class ForecastKnowledgeService:
    def __init__(self, repository: ForecastRepository):
        self.repo = repository

    async def visible_items(
        self, principal: Principal, release_id: UUID, citations: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        candidates = {
            str(c["evidence_id"]): c
            for c in citations
            if str(c["release_id"]) == str(release_id) and c.get("claim_id")
        }
        if not candidates:
            return []
        # Both Claim and Evidence must be in this release; mutable text is never returned.
        query = text("""
            SELECT rc.object_id AS claim_id,rc.snapshot->>'statement' AS statement,
                   er.id AS evidence_id,sa.id AS anchor_id,sv.id AS source_id,
                   sd.id AS source_document_id,
                   sa.locators,sv.classification,sd.classification AS document_classification,
                   rs.classification AS claim_classification
            FROM release_items re
            JOIN evidence_records er ON er.id=re.object_id AND er.status='ACCEPTED'
            JOIN release_items rc ON rc.release_id=re.release_id AND rc.object_type='CLAIM'
                AND rc.object_id=er.claim_id
            JOIN release_search_documents rs ON rs.release_id=rc.release_id
                AND rs.object_type='CLAIM' AND rs.object_id=rc.object_id
            JOIN source_anchors sa ON sa.id=er.source_anchor_id AND sa.status='VALID'
            JOIN source_versions sv ON sv.id=sa.source_version_id
            JOIN source_documents sd ON sd.id=sv.source_document_id AND sd.status<>'ARCHIVED'
            WHERE re.release_id=:release AND re.tenant_id=:tenant AND re.object_type='EVIDENCE'
                AND er.id IN :ids
                AND re.snapshot->>'claim_id'=CAST(rc.object_id AS text)
                AND re.snapshot->>'source_anchor_id'=CAST(sa.id AS text)
                AND NOT EXISTS (SELECT 1 FROM source_invalidations si
                    WHERE si.source_version_id=sv.id AND si.tenant_id=:tenant)
            ORDER BY rc.object_id,er.id LIMIT 20
        """).bindparams(bindparam("ids", expanding=True))
        async with self.repo.database.engine.connect() as connection:
            rows = (
                (
                    await connection.execute(
                        query,
                        {
                            "release": release_id,
                            "tenant": principal.tenant_id,
                            "ids": [UUID(i) for i in candidates],
                        },
                    )
                )
                .mappings()
                .all()
            )
        result = []
        for row in rows:
            if any(
                CLASSIFICATION_LEVEL[DataClassification(row[k])]
                > CLASSIFICATION_LEVEL[principal.clearance]
                for k in ("classification", "document_classification", "claim_classification")
            ):
                continue
            candidate = candidates[str(row["evidence_id"])]
            if str(candidate["claim_id"]) != str(row["claim_id"]):
                continue
            result.append(
                {
                    "claim_id": str(row["claim_id"]),
                    "source_document_id": str(row["source_document_id"]),
                    "statement": row["statement"],
                    "citation": {
                        **candidate,
                        "source_anchor_id": str(row["anchor_id"]),
                        "source_version_id": str(row["source_id"]),
                        "excerpt": None,
                        "locator": {"locators": row["locators"]},
                        "status": "VALID",
                    },
                }
            )
        return result

    async def build(
        self,
        principal: Principal,
        artifact_id: UUID,
        body: ForecastKnowledgeRequest,
        trace_id: str,
    ) -> dict[str, Any]:
        artifact = await self.repo.get_artifact(principal, artifact_id)
        space_id = UUID(str(artifact["space_id"]))
        await self.repo.authorize(principal, space_id, "query.release")
        release = await self.repo.platform.get_release(
            principal=principal, release_id=body.release_id
        )
        if str(release["space_id"]) != str(space_id):
            raise ApiProblem(
                404,
                "RESOURCE_NOT_FOUND",
                "Release unavailable",
                "Select a Release from the forecast's space.",
            )
        answer = await self.repo.platform.query_release(
            principal=principal,
            release_id=body.release_id,
            payload={
                "question": body.question,
                "strategy": "HYBRID",
                "top_k": 5,
                "filters": {},
                "client_request_id": "forecast-context:" + uuid4().hex,
            },
            trace_id=trace_id,
        )
        items = await self.visible_items(principal, body.release_id, answer["citations"])
        # Recheck membership/clearance after retrieval; no cached evidence crosses requests.
        await self.repo.get_artifact(principal, artifact_id)
        await self.repo.authorize(principal, space_id, "query.release")
        async with self.repo.database.engine.begin() as connection:
            await self.repo.platform._insert_audit(
                connection,
                principal=principal,
                space_id=space_id,
                action="forecast.knowledge-context",
                resource_type="ForecastArtifact",
                resource_id=artifact_id,
                trace_id=trace_id,
                outcome="SUCCEEDED",
                metadata={
                    "release_id": str(body.release_id),
                    "query_answer_id": answer["id"],
                    "citation_count": len(items),
                },
            )
        return {
            "artifact_id": str(artifact_id),
            "artifact_checksum": artifact["content_checksum"],
            "release_id": str(body.release_id),
            "release_checksum": release["manifest_checksum"],
            "release_deprecated": bool(release.get("deprecated_at")),
            "query_answer_id": answer["id"],
            "question": body.question,
            "checked_at": datetime.now(UTC).isoformat(),
            "status": "CITED_CONTEXT" if items else "INSUFFICIENT_EVIDENCE",
            "items": items,
            "explanation": (
                "已找到当前可见的固定版本支持材料；请结合适用工况核实，不能据此确认当前对象的故障原因。"
                if items
                else "当前固定版本中没有足够的可见有效证据；预测不能补足知识依据。"
            ),
            "limitations": [
                "本次引用回接独立于历史预测制品，不改变其内容。",
                "条件预测不等于因果推断；相关材料不证明当前对象适用性。",
                "Potential Event 不是已发生事实或故障概率；Hypothesis 仍待核实。",
            ],
        }
