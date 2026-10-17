import pytest

from nexweave_domain import local_structured_compile


@pytest.mark.parametrize(
    ("clause", "count"),
    [
        ("Pump A feeds Pump B", 1),
        ("Pump A does not feed Pump B", 0),
        ("Pump A may feed Pump B", 0),
        ("Pump A and Pump B are listed independently", 0),
        ("Pump A feeds Pump C", 0),
        ("Pump B feeds Pump A", 1),
        ("Pump A不供给Pump B", 0),
        ("Pump A供给Pump B", 1),
    ],
)
def test_rule_provider_needs_affirmative_source_direction_not_just_schema(clause, count):
    schema = {
        "types": [{"key": "example.io/equipment"}],
        "properties": [],
        "relations": [
            {
                "key": "example.io/feeds",
                "domain": "example.io/equipment",
                "range": "example.io/equipment",
            }
        ],
        "terms": [{"targetKey": "example.io/feeds", "term": "供给"}],
    }
    segments = [
        {"id": "a", "anchor_id": "anchor-a", "normalized_text": "Pump A. " + clause + "."},
        {"id": "b", "anchor_id": "anchor-b", "normalized_text": "Pump B. Independent listing."},
    ]
    result = local_structured_compile(schema_snapshot=schema, segments=segments)
    assert len(result.relations) == count
    if count:
        edge = result.relations[0]
        assert edge.anchor_id == "anchor-a"
        assert ("pump-b" in edge.source_entity_key) == clause.startswith("Pump B")
