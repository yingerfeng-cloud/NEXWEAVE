from nexweave_domain import new_uuid7


def test_uuid7_has_expected_version_variant_and_timestamp() -> None:
    timestamp_ms = 1_756_000_000_123
    value = new_uuid7(timestamp_ms)

    assert value.version == 7
    assert value.variant == "specified in RFC 4122"
    assert value.int >> 80 == timestamp_ms


def test_uuid7_rejects_invalid_timestamp() -> None:
    try:
        new_uuid7(-1)
    except ValueError as exc:
        assert "48 unsigned bits" in str(exc)
    else:
        raise AssertionError("negative UUIDv7 timestamp was accepted")
