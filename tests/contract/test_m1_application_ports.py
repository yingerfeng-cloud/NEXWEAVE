import asyncio
from datetime import UTC, datetime

from nexweave_api.object_storage import PolicyStubMalwareScanner
from nexweave_application import canonical_request_hash
from nexweave_domain import DataClassification, ScanStatus, new_uuid7


def test_canonical_request_hash_is_order_independent_and_sensitive_to_values() -> None:
    first = canonical_request_hash({"space_id": "one", "roles": ["consumer"]})
    reordered = canonical_request_hash({"roles": ["consumer"], "space_id": "one"})
    changed = canonical_request_hash({"roles": ["reviewer"], "space_id": "one"})

    assert first == reordered
    assert first.startswith("sha256:")
    assert first != changed


def test_canonical_request_hash_normalizes_domain_uuid_enum_and_timestamp_values() -> None:
    identifier = new_uuid7()
    timestamp = datetime(2026, 8, 24, tzinfo=UTC)
    typed = canonical_request_hash(
        {
            "id": identifier,
            "classification": DataClassification.INTERNAL,
            "occurred_at": timestamp,
        }
    )
    serialized = canonical_request_hash(
        {
            "id": str(identifier),
            "classification": "INTERNAL",
            "occurred_at": timestamp.isoformat(),
        }
    )

    assert typed == serialized


def test_scanner_stub_preserves_clean_and_infected_gate_states() -> None:
    scanner = PolicyStubMalwareScanner()
    clean = asyncio.run(scanner.scan(content=b"trusted", content_type="text/plain"))
    infected = asyncio.run(
        scanner.scan(
            content=b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE",
            content_type="text/plain",
        )
    )

    assert clean is ScanStatus.CLEAN
    assert infected is ScanStatus.INFECTED
