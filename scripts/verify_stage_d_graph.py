"""PostgreSQL temporary-table adapter fixtures; no writes to business tables."""
# ruff: noqa: E501

import asyncio
import json
import sys
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from nexweave_api.errors import ApiProblem
from nexweave_api.release_graph import read_graph
from nexweave_api.release_repository import ReleaseRepository
from nexweave_api.settings import Settings
from nexweave_domain import DataClassification


async def main():
    engine = create_async_engine(Settings().database_url)
    async with engine.connect() as c:
        # Read existing synthetic history before creating session-local fixtures.
        history = (
            await c.execute(
                text(
                    "SELECT id FROM query_answers WHERE release_id=:id ORDER BY created_at LIMIT 1"
                ),
                {"id": sys.argv[1]},
            )
        ).scalar_one()
        for statement in [
            "CREATE TEMP TABLE release_items (id uuid PRIMARY KEY,object_id uuid,tenant_id uuid,release_id uuid,object_type text,snapshot jsonb)",
            "CREATE TEMP TABLE knowledge_entity_versions (id uuid,compile_job_id uuid)",
            "CREATE TEMP TABLE compile_job_sources (compile_job_id uuid,source_version_id uuid)",
            "CREATE TEMP TABLE source_versions (id uuid,source_document_id uuid,classification text)",
            "CREATE TEMP TABLE source_documents (id uuid,status text,classification text)",
            "CREATE TEMP TABLE source_invalidations (tenant_id uuid,source_version_id uuid)",
            "CREATE TEMP TABLE evidence_records (id uuid,relation_id uuid,status text,source_anchor_id uuid)",
            "CREATE TEMP TABLE source_anchors (id uuid,status text,source_version_id uuid)",
        ]:
            await c.execute(text(statement))
        (
            tenant,
            release,
            doc,
            node_source,
            edge_source,
            job,
            version,
            a,
            b,
            relation,
            evidence,
            anchor,
        ) = [uuid4() for _ in range(12)]
        principal = SimpleNamespace(tenant_id=tenant, clearance=DataClassification.INTERNAL)
        await c.execute(
            text("INSERT INTO source_documents VALUES (:id,'ACTIVE','INTERNAL')"), {"id": doc}
        )
        for sid in [node_source, edge_source]:
            await c.execute(
                text("INSERT INTO source_versions VALUES (:id,:doc,'INTERNAL')"),
                {"id": sid, "doc": doc},
            )
        await c.execute(
            text("INSERT INTO knowledge_entity_versions VALUES (:v,:j)"), {"v": version, "j": job}
        )
        await c.execute(
            text("INSERT INTO compile_job_sources VALUES (:j,:s)"), {"j": job, "s": node_source}
        )

        async def item(kind, identity, snapshot):
            await c.execute(
                text(
                    "INSERT INTO release_items VALUES (:id,:obj,:tenant,:release,:kind,CAST(:snapshot AS jsonb))"
                ),
                {
                    "id": uuid4(),
                    "obj": identity,
                    "tenant": tenant,
                    "release": release,
                    "kind": kind,
                    "snapshot": json.dumps(snapshot),
                },
            )

        for identity in [a, b]:
            await item(
                "ENTITY",
                identity,
                {
                    "id": str(identity),
                    "current_version_id": str(version),
                    "type_key": "test/entity",
                    "normalized_key": str(identity),
                    "display_name": "Frozen name",
                },
            )
        await item(
            "RELATION",
            relation,
            {
                "id": str(relation),
                "relation_type_key": "test/link",
                "source_entity_id": str(a),
                "target_entity_id": str(b),
                "is_causal": True,
                "valid_from": None,
                "valid_until": None,
            },
        )
        await item(
            "EVIDENCE", evidence, {"relation_id": str(relation), "source_anchor_id": str(anchor)}
        )
        await c.execute(
            text("INSERT INTO evidence_records VALUES (:id,:r,'ACCEPTED',:a)"),
            {"id": evidence, "r": relation, "a": anchor},
        )
        await c.execute(
            text("INSERT INTO source_anchors VALUES (:a,'VALID',:s)"),
            {"a": anchor, "s": edge_source},
        )

        async def read(start=a, end=None):
            return await read_graph(c, principal, release, start, end, "TRAVERSE", 3, True, None)

        positive = await read()
        assert len(positive["edges"]) == 1 and len(positive["nodes"]) == 2
        assert all(n["display_name"] == "Frozen name" for n in positive["nodes"])
        for start, end in [(uuid4(), None), (a, uuid4())]:
            try:
                await read(start, end)
                raise AssertionError("nonmember leaked")
            except ApiProblem as exc:
                assert exc.status == 404
        await c.execute(
            text("UPDATE release_items SET release_id=:other WHERE object_type='EVIDENCE'"),
            {"other": uuid4()},
        )
        assert not (await read())["edges"]
        await c.execute(
            text("UPDATE release_items SET release_id=:r WHERE object_type='EVIDENCE'"),
            {"r": release},
        )
        await c.execute(
            text("INSERT INTO source_invalidations VALUES (:t,:s)"), {"t": tenant, "s": edge_source}
        )
        assert not (await read())["edges"]
        await c.execute(
            text("UPDATE source_versions SET classification='HIGHLY_RESTRICTED' WHERE id=:s"),
            {"s": node_source},
        )
        try:
            await read()
            raise AssertionError("high clearance node leaked")
        except ApiProblem as exc:
            assert exc.status == 404
        # A surviving low-classification citation cannot expose a claim whose other
        # frozen source was reclassified, even when that source is now invalidated.
        await c.execute(
            text(
                "ALTER TABLE evidence_records ADD COLUMN claim_id uuid, ADD COLUMN created_at timestamptz DEFAULT now()"
            )
        )
        await c.execute(text("ALTER TABLE source_anchors ADD COLUMN locators jsonb DEFAULT '[]'"))
        await c.execute(
            text(
                "CREATE TEMP TABLE release_search_documents (release_id uuid, object_type text, object_id uuid, classification text)"
            )
        )
        await c.execute(text("UPDATE source_versions SET classification='INTERNAL'"))
        claim = uuid4()
        await item("CLAIM", claim, {"id": str(claim), "statement": "Frozen synthetic claim"})
        await c.execute(
            text("INSERT INTO release_search_documents VALUES (:r,'CLAIM',:c,'INTERNAL')"),
            {"r": release, "c": claim},
        )
        for sid in [node_source, edge_source]:
            eid, aid = uuid4(), uuid4()
            await c.execute(
                text(
                    "INSERT INTO source_anchors(id,status,source_version_id) VALUES (:a,'VALID',:s)"
                ),
                {"a": aid, "s": sid},
            )
            await c.execute(
                text(
                    "INSERT INTO evidence_records(id,status,source_anchor_id,claim_id) VALUES (:e,'ACCEPTED',:a,:c)"
                ),
                {"e": eid, "a": aid, "c": claim},
            )
            await item("EVIDENCE", eid, {"claim_id": str(claim), "source_anchor_id": str(aid)})
        hits = [{"object_id": str(claim), "object_type": "CLAIM"}]
        assert (
            len(await ReleaseRepository._visible_citations(None, c, principal, release, hits)) == 1
        )
        await c.execute(
            text("UPDATE source_versions SET classification='HIGHLY_RESTRICTED' WHERE id=:s"),
            {"s": edge_source},
        )
        assert not await ReleaseRepository._visible_citations(None, c, principal, release, hits)
        await c.rollback()  # Includes all temporary DDL/data; business tables were read only.
    await engine.dispose()
    print(
        json.dumps(
            {
                "postgres_graph_checks": 6,
                "positive_edges": 1,
                "nonmember_denials": 2,
                "fixed_release_evidence": True,
                "invalid_source_hidden": True,
                "node_clearance_denied": True,
                "query_mixed_source_reclassification_checks": 2,
                "fixture_scope": "SESSION_LOCAL_TEMP_TABLES_ROLLED_BACK",
                "historical_answer_id": str(history),
            }
        )
    )


asyncio.run(main())
