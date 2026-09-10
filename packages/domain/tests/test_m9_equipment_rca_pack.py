import base64
import json
from pathlib import Path
from typing import Any

from nexweave_contracts import DomainPackManifestV1Alpha1, SemanticDeclarations
from nexweave_domain import canonical_json, compose_declarations, verify_pack

ROOT = Path(__file__).resolve().parents[3]
PACK = ROOT / "domain-packs" / "equipment-rca"
FIXTURES = ROOT / "domain-packs" / "fixtures"
CONTENT_FILES = ("semantic.json", "authoring.json", "evaluation.json")


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def _pack_files() -> dict[str, bytes]:
    return {name: canonical_json(_json(PACK / name)) for name in CONTENT_FILES}


def _merged_declarations() -> dict[str, list[Any]]:
    merged: dict[str, list[Any]] = {}
    for name in CONTENT_FILES:
        for section, values in _json(PACK / name).items():
            assert isinstance(values, list)
            merged.setdefault(section, []).extend(values)
    return merged


def test_m9_pack_signature_contract_and_content_checksums_are_valid() -> None:
    manifest = _json(PACK / "manifest.json")
    key = _json(PACK / "publisher-public-key.json")

    DomainPackManifestV1Alpha1.model_validate(manifest)
    for name in CONTENT_FILES:
        SemanticDeclarations.model_validate(_json(PACK / name))

    verification = verify_pack(
        manifest=manifest,
        files=_pack_files(),
        public_key=base64.urlsafe_b64decode(str(key["publicKeyBase64Url"]) + "="),
    )

    assert verification.key_id == "nexweave-m9-equipment-rca-2026"
    assert manifest["security"]["executableContent"] is False


def test_m9_pack_composes_with_core_and_maintenance_without_duplicate_equipment() -> None:
    core = _json(FIXTURES / "core-pack" / "semantic.json")
    maintenance = _json(FIXTURES / "maintenance-pack" / "semantic.json")
    rca = _merged_declarations()

    composition = compose_declarations(
        packs={"core-pack": core, "equipment-rca-pack": rca, "maintenance-pack": maintenance},
        dependencies={
            "core-pack": (),
            "equipment-rca-pack": ("core-pack",),
            "maintenance-pack": ("core-pack",),
        },
    )
    type_keys = [item["key"] for item in composition.normalized_snapshot["types"]]

    assert composition.pack_order == (
        "core-pack",
        "equipment-rca-pack",
        "maintenance-pack",
    )
    assert type_keys.count("nexweave.io/equipment") == 1
    assert "equipment.rca/component" in type_keys
    assert "maintenance.example/work-order" in type_keys


def test_m9_pack_causal_relations_and_standard_questions_enforce_safe_assistance() -> None:
    declarations = _merged_declarations()
    causal = [item for item in declarations["relations"] if item["causal"]]
    suites = declarations["evaluationSuites"]
    assert causal
    assert all(item["evidenceRequired"] for item in causal)
    assert len(suites) == 1

    cases = suites[0]["definition"]["cases"]
    assert {item["caseType"] for item in cases} == {
        "ANSWERABLE",
        "UNANSWERABLE",
        "COUNTERFACTUAL",
        "CONFLICT",
        "MULTI_SOURCE",
        "INSUFFICIENT_EVIDENCE",
    }
    unanswerable = next(item for item in cases if item["caseType"] == "UNANSWERABLE")
    insufficient = next(item for item in cases if item["caseType"] == "INSUFFICIENT_EVIDENCE")
    assert "refusalRequired" in unanswerable["assertions"]
    assert "noAutomaticDisposition" in insufficient["assertions"]


def test_m9_synthetic_fixture_cannot_be_mistaken_for_pilot_evidence() -> None:
    fixture = _json(PACK / "examples" / "synthetic-rca-case.json")
    assert fixture["fixtureClassification"] == "SYNTHETIC"
    assert fixture["pilotEvidence"] is False
    assert "not operating guidance" in str(fixture["safetyNotice"])


def test_platform_runtime_has_no_equipment_rca_stable_keys_or_kks_branch() -> None:
    runtime_roots = (
        ROOT / "apps" / "api" / "src",
        ROOT / "packages" / "application" / "src",
        ROOT / "packages" / "contracts" / "src",
        ROOT / "packages" / "domain" / "src",
        ROOT / "workers",
    )
    offenders: list[str] = []
    for runtime_root in runtime_roots:
        for path in runtime_root.rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            if "equipment.rca/" in text or "kks-code" in text:
                offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


def test_platform_still_composes_when_equipment_rca_pack_is_absent() -> None:
    core = _json(FIXTURES / "core-pack" / "semantic.json")
    maintenance = _json(FIXTURES / "maintenance-pack" / "semantic.json")
    composition = compose_declarations(
        packs={"core-pack": core, "maintenance-pack": maintenance},
        dependencies={"core-pack": (), "maintenance-pack": ("core-pack",)},
    )
    assert composition.pack_order == ("core-pack", "maintenance-pack")
    assert all(
        not str(item["key"]).startswith("equipment.rca/")
        for item in composition.normalized_snapshot["types"]
    )
