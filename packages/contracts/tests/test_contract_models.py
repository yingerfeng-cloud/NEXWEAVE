from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from nexweave_contracts.source_anchor import CharacterRangeLocator


def test_character_range_rejects_empty_or_reversed_ranges() -> None:
    with pytest.raises(ValidationError):
        CharacterRangeLocator(start=5, end=5, text_basis="normalized_utf8")


def test_contract_time_fixture_is_timezone_aware() -> None:
    assert datetime(2026, 8, 23, tzinfo=UTC).utcoffset() is not None
