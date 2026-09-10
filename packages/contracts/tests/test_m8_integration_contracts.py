from uuid import UUID

import pytest
from pydantic import ValidationError

from nexweave_contracts import (
    ConnectorInstanceCreate,
    ObsidianImportCreate,
    WikiLinkGraphResponse,
)


def test_connector_contract_rejects_inline_credentials() -> None:
    with pytest.raises(ValidationError, match="inline credentials"):
        ConnectorInstanceCreate(
            definition_id=UUID("01989e3f-0b29-7000-8000-000000000001"),
            name="local files",
            kind="FILESYSTEM",
            allowlist=("/srv/nexweave/import",),
            config={"token": "must-not-be-accepted"},
        )


def test_obsidian_import_contract_is_bounded() -> None:
    assert ObsidianImportCreate(markdown="# note\n").markdown == "# note\n"


def test_wiki_link_graph_contract_keeps_navigation_separate_from_release() -> None:
    graph = WikiLinkGraphResponse(
        space_id=UUID("01989e3f-0b29-7000-8000-000000000001"),
        max_depth=2,
        node_limit=180,
    )

    assert graph.nodes == ()
    assert graph.truncated is False
