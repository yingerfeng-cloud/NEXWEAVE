from pathlib import Path

import pytest

from nexweave_api.connector_provider import ReadOnlyConnectorProvider
from nexweave_api.errors import ApiProblem


class Storage:
    async def get(self, *, key: str, version_id: str | None = None) -> bytes:
        assert version_id is None
        return {"allowed/a.md": b"# trusted raw\n"}[key]


@pytest.mark.asyncio
async def test_filesystem_connector_requires_an_allowlisted_regular_file(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    source = allowed / "note.md"
    source.write_text("# raw\n", encoding="utf-8")
    provider = ReadOnlyConnectorProvider(Storage(), 1024)

    filename, content_type, content, locator = await provider.read(
        {"kind": "FILESYSTEM", "config": {"path": str(source)}, "allowlist": [str(allowed)]}
    )

    assert (filename, content_type, content, locator["path"]) == (
        "note.md",
        "text/markdown",
        b"# raw\n",
        str(source),
    )


@pytest.mark.asyncio
async def test_s3_connector_rejects_a_key_outside_its_explicit_prefix() -> None:
    provider = ReadOnlyConnectorProvider(Storage(), 1024)

    with pytest.raises(ApiProblem, match="allowlisted") as error:
        await provider.read(
            {
                "kind": "S3",
                "config": {"bucket": "nexweave-dev", "object_key": "denied/a.md"},
                "allowlist": ["s3://nexweave-dev/allowed"],
            }
        )

    assert error.value.code == "CONNECTOR_ALLOWLIST_DENIED"
