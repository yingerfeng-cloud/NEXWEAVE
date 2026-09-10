"""Verify the M9 declarative Equipment RCA Pack without claiming a real pilot."""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "packages" / "contracts" / "src"),
    str(ROOT / "packages" / "domain" / "src"),
]

from nexweave_contracts import DomainPackManifestV1Alpha1, SemanticDeclarations  # noqa: E402
from nexweave_domain import canonical_json, compose_declarations, verify_pack  # noqa: E402

PACK = ROOT / "domain-packs" / "equipment-rca"
FIXTURES = ROOT / "domain-packs" / "fixtures"
CONTENT_FILES = ("semantic.json", "authoring.json", "evaluation.json")


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"{path} must contain a JSON object")
    return value


def main() -> None:
    manifest = DomainPackManifestV1Alpha1.model_validate(load(PACK / "manifest.json"))
    key = load(PACK / "publisher-public-key.json")
    contents = {name: load(PACK / name) for name in CONTENT_FILES}
    for content in contents.values():
        SemanticDeclarations.model_validate(content)
    files = {name: canonical_json(content) for name, content in contents.items()}
    verified = verify_pack(
        manifest=manifest.model_dump(mode="json", by_alias=True),
        files=files,
        public_key=base64.urlsafe_b64decode(str(key["publicKeyBase64Url"]) + "="),
    )

    merged: dict[str, list[Any]] = {}
    for content in contents.values():
        for section, values in content.items():
            merged.setdefault(section, []).extend(values)
    core = load(FIXTURES / "core-pack" / "semantic.json")
    maintenance = load(FIXTURES / "maintenance-pack" / "semantic.json")
    composed = compose_declarations(
        packs={"core-pack": core, "equipment-rca-pack": merged, "maintenance-pack": maintenance},
        dependencies={
            "core-pack": (),
            "equipment-rca-pack": ("core-pack",),
            "maintenance-pack": ("core-pack",),
        },
    )
    causal = [item for item in composed.normalized_snapshot["relations"] if item.get("causal")]
    cases = composed.normalized_snapshot["evaluationSuites"][0]["definition"]["cases"]
    if not causal or not all(item.get("evidenceRequired") for item in causal):
        raise RuntimeError("Every M9 causal relation must require Evidence")
    if len({item["caseType"] for item in cases}) != 6:
        raise RuntimeError("The M9 standard questions do not cover all required behaviors")

    print(
        json.dumps(
            {
                "pack": f"{manifest.metadata.id}@{manifest.metadata.version}",
                "signatureKeyId": verified.key_id,
                "contentChecksum": verified.content_checksum,
                "compositionChecksum": composed.composition_checksum,
                "packOrder": composed.pack_order,
                "typeCount": len(composed.normalized_snapshot["types"]),
                "causalRelationCount": len(causal),
                "standardQuestionCount": len(cases),
                "fixtureClassification": "SYNTHETIC",
                "realPilotClaimed": False,
                "gridCrewDemoClaimed": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
