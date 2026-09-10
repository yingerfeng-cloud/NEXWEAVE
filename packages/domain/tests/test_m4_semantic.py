import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from nexweave_domain import (
    SemanticRuleViolation,
    analyze_compatibility,
    canonical_json,
    compose_declarations,
    deterministic_topological_order,
    pack_descriptor,
    semver_satisfies,
    sha256_checksum,
    validate_pack_path,
    validate_stable_key,
    verify_pack,
    verify_signed_revocation_list,
)

FIXTURES = Path(__file__).resolve().parents[3] / "domain-packs" / "fixtures"
FIXTURE_PUBLIC_KEYS = {
    "core-pack": "kR92cVpXQ0xGseuVRArtgySaHOzib5Gxraxo1XrCnBU",
    "equipment-rca-pack": "JIA189zUUCfQHxqtl-R9DHECoTj9Wwjhtxt5oH5xXLQ",
    "maintenance-pack": "CBurpx8h6iVjTLhYUfrA9QsTY2slCT8c_0zuHLT_GGQ",
}


def _manifest_and_files() -> tuple[dict[str, object], dict[str, bytes], bytes]:
    content = {"types": [{"key": "example.org/equipment", "displayName": "Equipment"}]}
    content_bytes = canonical_json(content)
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    manifest: dict[str, object] = {
        "apiVersion": "nexweave.io/domain-pack/v1alpha1",
        "kind": "NexweaveDomainPack",
        "canonicalizationAlgorithm": "RFC8785-JCS/1",
        "metadata": {
            "id": "example-pack",
            "version": "1.0.0",
            "publisher": "Example",
            "keyNamespace": "example.org",
            "description": "Fixture",
        },
        "compatibility": {
            "platform": ">=1.0.0 <2.0.0",
            "semanticContract": ">=1.0.0 <2.0.0",
            "dependencies": [],
        },
        "content": {
            "entities": {"path": "schema/entities.json", "sha256": sha256_checksum(content_bytes)}
        },
        "security": {
            "executableContent": False,
            "signature": {"algorithm": "Ed25519", "keyId": "fixture-key", "value": ""},
        },
    }
    signature = private_key.sign(pack_descriptor(manifest))
    manifest["security"] = {
        "executableContent": False,
        "signature": {
            "algorithm": "Ed25519",
            "keyId": "fixture-key",
            "value": base64.urlsafe_b64encode(signature).decode().rstrip("="),
        },
    }
    return manifest, {"schema/entities.json": content_bytes}, public_key


def test_stable_key_is_namespaced_and_lowercase() -> None:
    assert (
        validate_stable_key("example.org/equipment", namespace="example.org")
        == "example.org/equipment"
    )
    with pytest.raises(SemanticRuleViolation, match="invalid"):
        validate_stable_key("Example.org/Equipment")
    with pytest.raises(SemanticRuleViolation, match="invalid"):
        validate_stable_key("example.org/equipment-")


def test_pack_signature_and_content_are_verified() -> None:
    manifest, files, public_key = _manifest_and_files()
    result = verify_pack(manifest=manifest, files=files, public_key=public_key)
    assert result.key_id == "fixture-key"
    assert result.content_checksum.startswith("sha256:")


def test_undeclared_pack_content_is_rejected() -> None:
    manifest, files, public_key = _manifest_and_files()
    files["schema/extra.json"] = canonical_json({"ignored": False})
    with pytest.raises(SemanticRuleViolation, match="undeclared"):
        verify_pack(manifest=manifest, files=files, public_key=public_key)


@pytest.mark.parametrize(
    "path",
    ["../escape.json", "/absolute.json", "schema//types.json", "schema/./types.json"],
)
def test_pack_paths_cannot_escape_or_alias(path: str) -> None:
    with pytest.raises(SemanticRuleViolation, match="safe relative"):
        validate_pack_path(path)


def test_pack_rejects_floating_point_and_oversized_content() -> None:
    manifest, files, public_key = _manifest_and_files()
    files["schema/entities.json"] = canonical_json({"ratio": 1}) + b" " * 262_145
    with pytest.raises(SemanticRuleViolation, match="oversized"):
        verify_pack(manifest=manifest, files=files, public_key=public_key)

    with pytest.raises(SemanticRuleViolation, match="floating"):
        canonical_json({"ratio": 0.5})


def test_topological_order_is_stable_and_cycles_are_rejected() -> None:
    assert deterministic_topological_order(
        {"maintenance-pack": ("core-pack",), "core-pack": ()}
    ) == (
        "core-pack",
        "maintenance-pack",
    )
    with pytest.raises(SemanticRuleViolation, match="cycle"):
        deterministic_topological_order({"a-pack": ("b-pack",), "b-pack": ("a-pack",)})


def test_composition_is_deterministic_and_reuses_identical_type() -> None:
    core = {"types": [{"key": "example.org/equipment", "displayName": "Equipment"}]}
    maintenance = {
        "types": [{"key": "example.org/equipment", "displayName": "Equipment"}],
        "relations": [
            {
                "key": "example.org/maintains",
                "domain": "example.org/equipment",
                "range": "example.org/equipment",
            }
        ],
    }
    first = compose_declarations(
        packs={"core-pack": core, "maintenance-pack": maintenance},
        dependencies={"maintenance-pack": ("core-pack",), "core-pack": ()},
    )
    second = compose_declarations(
        packs={"maintenance-pack": maintenance, "core-pack": core},
        dependencies={"core-pack": (), "maintenance-pack": ("core-pack",)},
    )
    assert first.composition_checksum == second.composition_checksum


def test_composition_rejects_hierarchy_cycle_and_ambiguous_exact_mapping() -> None:
    cyclic = {
        "types": [{"key": "example.org/a"}, {"key": "example.org/b"}],
        "hierarchy": [
            {"child": "example.org/a", "parent": "example.org/b"},
            {"child": "example.org/b", "parent": "example.org/a"},
        ],
    }
    with pytest.raises(SemanticRuleViolation, match="cycle"):
        compose_declarations(packs={"core-pack": cyclic}, dependencies={"core-pack": ()})
    ambiguous = {
        "types": [{"key": "example.org/a"}, {"key": "example.org/b"}, {"key": "example.org/c"}],
        "mappings": [
            {"source": "example.org/a", "target": "example.org/b", "kind": "EXACT"},
            {"source": "example.org/a", "target": "example.org/c", "kind": "EXACT"},
        ],
    }
    with pytest.raises(SemanticRuleViolation, match="multiple"):
        compose_declarations(packs={"core-pack": ambiguous}, dependencies={"core-pack": ()})


@pytest.mark.parametrize("pack_id", ["core-pack", "equipment-rca-pack", "maintenance-pack"])
def test_committed_fixture_signature_and_checksum_are_valid(pack_id: str) -> None:
    fixture = FIXTURES / pack_id
    manifest = json.loads((fixture / "manifest.json").read_text(encoding="utf-8"))
    content = (fixture / "semantic.json").read_bytes()

    result = verify_pack(
        manifest=manifest,
        files={"semantic.json": content},
        public_key=base64.urlsafe_b64decode(FIXTURE_PUBLIC_KEYS[pack_id] + "="),
    )

    assert result.key_id == f"m4-fixture-{pack_id}"


def test_fixture_pack_order_and_checksum_are_repeatable() -> None:
    declarations = {
        pack_id: json.loads((FIXTURES / pack_id / "semantic.json").read_text(encoding="utf-8"))
        for pack_id in ("core-pack", "equipment-rca-pack", "maintenance-pack")
    }
    dependencies = {
        "core-pack": (),
        "equipment-rca-pack": ("core-pack",),
        "maintenance-pack": ("core-pack",),
    }

    first = compose_declarations(packs=declarations, dependencies=dependencies)
    second = compose_declarations(
        packs=dict(reversed(declarations.items())),
        dependencies=dict(reversed(dependencies.items())),
    )

    assert first.pack_order == ("core-pack", "equipment-rca-pack", "maintenance-pack")
    assert first.composition_checksum == second.composition_checksum
    assert [item["key"] for item in first.normalized_snapshot["types"]] == [
        "industry.example/failure",
        "maintenance.example/work-order",
        "nexweave.io/equipment",
    ]
    assert first.normalized_snapshot["mappings"] == []


def test_inheritance_relation_and_preferred_term_conflicts_are_blocked() -> None:
    declarations = {
        "types": [
            {"key": "example.org/a"},
            {"key": "example.org/b"},
            {"key": "example.org/c"},
        ],
        "properties": [
            {"key": "example.org/name", "typeKey": "example.org/a", "required": False},
            {"key": "example.org/name", "typeKey": "example.org/b", "required": True},
        ],
        "hierarchy": [
            {"child": "example.org/c", "parent": "example.org/a"},
            {"child": "example.org/c", "parent": "example.org/b"},
        ],
    }
    with pytest.raises(SemanticRuleViolation, match="Multiple parents"):
        compose_declarations(packs={"x": declarations}, dependencies={"x": ()})

    with pytest.raises(SemanticRuleViolation, match="endpoint"):
        compose_declarations(
            packs={
                "x": {
                    "types": [{"key": "example.org/a"}],
                    "relations": [
                        {
                            "key": "example.org/bad",
                            "domain": "example.org/a",
                            "range": "example.org/missing",
                        }
                    ],
                }
            },
            dependencies={"x": ()},
        )

    with pytest.raises(SemanticRuleViolation, match="preferred"):
        compose_declarations(
            packs={
                "x": {
                    "types": [{"key": "example.org/a"}],
                    "terms": [
                        {
                            "targetKey": "example.org/a",
                            "language": "en",
                            "term": "A",
                            "kind": "PREFERRED",
                        },
                        {
                            "targetKey": "example.org/a",
                            "language": "en",
                            "term": "Alpha",
                            "kind": "PREFERRED",
                        },
                    ],
                }
            },
            dependencies={"x": ()},
        )


def test_breaking_change_is_classified_and_optional_addition_has_preview() -> None:
    previous = compose_declarations(
        packs={"x": {"types": [{"key": "example.org/a"}]}}, dependencies={"x": ()}
    ).normalized_snapshot
    optional = compose_declarations(
        packs={
            "x": {
                "types": [{"key": "example.org/a"}],
                "properties": [
                    {
                        "key": "example.org/name",
                        "typeKey": "example.org/a",
                        "required": False,
                    }
                ],
            }
        },
        dependencies={"x": ()},
    ).normalized_snapshot
    removed = compose_declarations(packs={"x": {}}, dependencies={"x": ()}).normalized_snapshot

    compatible = analyze_compatibility(previous, optional)
    breaking = analyze_compatibility(previous, removed)

    assert compatible.classification == "COMPATIBLE"
    assert compatible.migration_operations[0]["operation"] == "addOptionalProperty"
    assert breaking.classification == "BREAKING"
    assert breaking.breaking is True


def test_semver_range_subset_and_tampering_security_boundary() -> None:
    assert semver_satisfies("1.4.2", ">=1.0.0 <2.0.0")
    assert not semver_satisfies("2.0.0", ">=1.0.0 <2.0.0")
    manifest, files, public_key = _manifest_and_files()
    manifest["security"] = {
        "executableContent": True,
        "signature": manifest["security"]["signature"],  # type: ignore[index]
    }
    with pytest.raises(SemanticRuleViolation, match="prohibit executable"):
        verify_pack(manifest=manifest, files=files, public_key=public_key)


def test_signed_revocation_list_requires_exactly_one_target_kind() -> None:
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    document: dict[str, object] = {
        "apiVersion": "nexweave.io/pack-revocation/v1alpha1",
        "kind": "NexweavePackRevocationList",
        "canonicalizationAlgorithm": "RFC8785-JCS/1",
        "revoked": [
            {
                "keyId": "compromised-key",
                "reasonCode": "KEY_COMPROMISE",
                "revokedAt": "2026-08-30T00:00:00Z",
            }
        ],
        "security": {
            "executableContent": False,
            "signature": {"algorithm": "Ed25519", "keyId": "root-key", "value": ""},
        },
    }
    signature = private_key.sign(pack_descriptor(document))
    document["security"]["signature"]["value"] = (  # type: ignore[index]
        base64.urlsafe_b64encode(signature).decode().rstrip("=")
    )

    result = verify_signed_revocation_list(document=document, public_key=public_key)

    assert result.key_id == "root-key"
    document["revoked"] = [
        {
            "keyId": "also-key",
            "packId": "example-pack",
            "version": "1.0.0",
            "contentChecksum": "sha256:" + "0" * 64,
            "reasonCode": "INVALID",
            "revokedAt": "2026-08-30T00:00:00Z",
        }
    ]
    with pytest.raises(SemanticRuleViolation, match="exactly one"):
        verify_signed_revocation_list(document=document, public_key=public_key)
