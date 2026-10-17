"""Authoritative review revisions and material edits, within the review transaction."""

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from nexweave_api.errors import ApiProblem
from nexweave_api.repository import _json_value
from nexweave_domain import new_uuid7

TABLES = {
    "CLAIM_CANDIDATE": "claim_candidates",
    "RELATION_CANDIDATE": "candidate_relations",
    "SEMANTIC_PROPOSAL": "semantic_change_proposals",
}


def content(row: Any) -> dict[str, Any]:
    # Status is lifecycle metadata, never the reviewed content version.
    return {
        k: v for k, v in _json_value(row).items() if k not in {"status", "updated_at", "updated_by"}
    }


def checksum(value: dict[str, Any]) -> str:
    return (
        "sha256:"
        + hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
    )


async def load_target(connection: AsyncConnection, case: Any) -> dict[str, Any]:
    row = (
        (
            await connection.execute(
                text(
                    f"SELECT * FROM {TABLES[case['target_type']]} "  # noqa: S608
                    "WHERE tenant_id=:tenant AND space_id=:space AND id=:id FOR UPDATE"
                ),
                {"id": case["target_id"], "tenant": case["tenant_id"], "space": case["space_id"]},
            )
        )
        .mappings()
        .first()
    )
    if row is None:
        raise ApiProblem(
            404, "REVIEW_TARGET_NOT_FOUND", "Target unavailable", "Target unavailable."
        )
    return content(row)


async def record_revision(
    connection: AsyncConnection,
    case_id: UUID,
    value: dict[str, Any],
    revision: int,
    original_author: UUID,
    editor: UUID | None,
    now: datetime,
) -> None:
    await connection.execute(
        text(
            "INSERT INTO review_target_revisions "
            "(id,review_case_id,revision,content_snapshot,content_checksum,"
            "original_author_id,edited_by,created_at) "
            "VALUES (:id,:case,:revision,CAST(:snapshot AS jsonb),:checksum,:author,:editor,:now)"
        ),
        {
            "id": new_uuid7(),
            "case": case_id,
            "revision": revision,
            "snapshot": json.dumps(value),
            "checksum": checksum(value),
            "author": original_author,
            "editor": editor,
            "now": now,
        },
    )


async def checked_revision(connection: AsyncConnection, case: Any) -> dict[str, Any]:
    revision = (
        (
            await connection.execute(
                text(
                    "SELECT * FROM review_target_revisions WHERE "
                    "review_case_id=:id ORDER BY revision DESC LIMIT 1"
                ),
                {"id": case["id"]},
            )
        )
        .mappings()
        .first()
    )
    if revision is None:
        raise ApiProblem(
            409,
            "REVIEW_VERSION_REQUIRED",
            "Review must restart",
            "This legacy case requires an explicit restart against current content.",
        )
    target = await load_target(connection, case)
    if checksum(target) != revision["content_checksum"]:
        raise ApiProblem(
            409,
            "REVIEW_VERSION_CHANGED",
            "Review content changed",
            "The target changed outside the reviewed revision. Restart review.",
        )
    return dict(revision)


async def modify_target(
    connection: AsyncConnection, case: Any, changes: dict[str, Any], actor_id: UUID, now: datetime
) -> dict[str, Any]:
    current = await checked_revision(connection, case)
    # Other candidate kinds explicitly reject unsupported edits rather than
    # recording a MODIFY which never changes knowledge.
    if (
        case["target_type"] != "CLAIM_CANDIDATE"
        or not changes
        or set(changes) - {"statement", "object_value"}
    ):
        raise ApiProblem(
            422,
            "REVIEW_CHANGE_SET_INVALID",
            "Invalid content edit",
            "Claim edits support statement and object_value; a material change is required.",
        )
    if "statement" in changes and (
        not isinstance(changes["statement"], str)
        or not changes["statement"].strip()
        or len(changes["statement"]) > 16000
    ):
        raise ApiProblem(
            422, "REVIEW_CHANGE_SET_INVALID", "Invalid statement", "Provide nonblank text."
        )
    if "object_value" in changes and not isinstance(changes["object_value"], dict):
        raise ApiProblem(
            422, "REVIEW_CHANGE_SET_INVALID", "Invalid value", "object_value must be an object."
        )
    updated = {**current["content_snapshot"], **changes}
    if checksum(updated) == current["content_checksum"]:
        raise ApiProblem(
            422, "REVIEW_CHANGE_SET_EMPTY", "No content change", "Edit the reviewed content."
        )
    for key, value in changes.items():
        expression = "CAST(:value AS jsonb)" if key == "object_value" else ":value"
        await connection.execute(
            text(
                f"UPDATE claim_candidates SET {key}={expression} WHERE id=:id"  # noqa: S608
            ),
            {
                "value": json.dumps(value) if key == "object_value" else value,
                "id": case["target_id"],
            },
        )
    await record_revision(
        connection,
        case["id"],
        updated,
        int(current["revision"]) + 1,
        current["original_author_id"],
        actor_id,
        now,
    )
    return updated
