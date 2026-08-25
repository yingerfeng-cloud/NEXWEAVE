"""Provision the deterministic second local tenant used only by M1 E2E isolation checks."""

from __future__ import annotations

import asyncio
import json

from nexweave_api.database import Database
from nexweave_api.repository import PlatformRepository
from nexweave_api.settings import Settings


async def provision() -> None:
    settings = Settings()
    database = Database(settings)
    try:
        principal = await PlatformRepository(database).bootstrap_local_development(
            tenant_slug="m1-e2e-foreign",
            subject="m1-e2e-foreign-admin",
        )
        print(
            json.dumps(
                {"tenant_id": str(principal.tenant_id), "subject": principal.subject},
                sort_keys=True,
            )
        )
    finally:
        await database.close()


if __name__ == "__main__":
    asyncio.run(provision())
