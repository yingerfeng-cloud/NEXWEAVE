"""Pure M4 semantic-model and declarative Pack validation primitives."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

STABLE_KEY_PATTERN = re.compile(r"^[a-z][a-z0-9.-]{1,62}/[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?$")
PACK_PATH_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._/-]{0,191}$")
PACK_ID_PATTERN = re.compile(r"^[a-z][a-z0-9-]{1,62}-pack$")
SEMVER_PATTERN = re.compile(
    r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$"
)
RESERVED_NAMESPACES = frozenset({"nexweave.io", "local.nexweave.io", "test.nexweave.io"})
MAX_PACK_FILE_BYTES = 262_144
MAX_PACK_TOTAL_BYTES = 2 * 1024 * 1024
MAX_PACK_FILES = 64
MAX_JSON_DEPTH = 32


class SemanticRuleViolation(ValueError):
    """A stable public semantic/Pack validation failure."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


class SchemaVersionStatus(StrEnum):
    DRAFT = "DRAFT"
    TESTING = "TESTING"
    PUBLISHED = "PUBLISHED"
    DEPRECATED = "DEPRECATED"


def validate_stable_key(value: str, *, namespace: str | None = None) -> str:
    if not STABLE_KEY_PATTERN.fullmatch(value):
        raise SemanticRuleViolation("SEMANTIC_MODEL_INVALID", "Stable key has an invalid v1 form.")
    key_namespace, _ = value.split("/", maxsplit=1)
    if namespace is not None and key_namespace != namespace:
        raise SemanticRuleViolation(
            "PACK_COMPOSITION_CONFLICT", "A Pack may only define keys in its registered namespace."
        )
    return value


def validate_pack_path(value: str) -> str:
    if (
        not PACK_PATH_PATTERN.fullmatch(value)
        or value.startswith("/")
        or "//" in value
        or any(part in {"", ".", ".."} for part in value.split("/"))
    ):
        raise SemanticRuleViolation(
            "PACK_ARTIFACT_INVALID", "Pack content path is not a safe relative path."
        )
    return value


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SemanticRuleViolation(
                "PACK_ARTIFACT_INVALID", "JSON object contains a duplicate key."
            )
        result[key] = value
    return result


def _check_json_value(value: Any, *, depth: int = 0) -> None:
    if depth > MAX_JSON_DEPTH:
        raise SemanticRuleViolation(
            "PACK_RESOURCE_LIMIT_EXCEEDED", "JSON nesting exceeds Pack limits."
        )
    if isinstance(value, float):
        raise SemanticRuleViolation(
            "PACK_ARTIFACT_INVALID", "Pack JSON cannot contain floating values."
        )
    if value is None or isinstance(value, str | bool | int):
        return
    if isinstance(value, list):
        for item in value:
            _check_json_value(item, depth=depth + 1)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise SemanticRuleViolation(
                    "PACK_ARTIFACT_INVALID", "Pack JSON keys must be strings."
                )
            _check_json_value(item, depth=depth + 1)
        return
    raise SemanticRuleViolation("PACK_ARTIFACT_INVALID", "Pack JSON contains an unsupported value.")


def parse_pack_json(raw: bytes) -> Any:
    if len(raw) > MAX_PACK_FILE_BYTES:
        raise SemanticRuleViolation("PACK_RESOURCE_LIMIT_EXCEEDED", "Pack file exceeds 256 KiB.")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise SemanticRuleViolation("PACK_ARTIFACT_INVALID", "Pack JSON must not have a UTF-8 BOM.")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_float=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as exc:
        raise SemanticRuleViolation(
            "PACK_ARTIFACT_INVALID", "Pack content must be valid restricted JSON."
        ) from exc
    _check_json_value(value)
    return value


def canonical_json(value: Any) -> bytes:
    """RFC8785-JCS/1 for the deliberately integer-only Pack JSON subset."""

    _check_json_value(value)
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")


def sha256_checksum(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _semver_key(value: str) -> tuple[int, int, int, tuple[tuple[int, int | str], ...]]:
    match = SEMVER_PATTERN.fullmatch(value)
    if match is None:
        raise SemanticRuleViolation("PACK_ARTIFACT_INVALID", "Pack version is not SemVer 2.0.0.")
    prerelease = match.group(4)
    identifiers: tuple[tuple[int, int | str], ...]
    if prerelease is None:
        identifiers = ((2, ""),)
    else:
        identifiers = tuple(
            (0, int(item)) if item.isdigit() else (1, item) for item in prerelease.split(".")
        )
    return int(match.group(1)), int(match.group(2)), int(match.group(3)), identifiers


def semver_satisfies(version: str, version_range: str) -> bool:
    """Evaluate the frozen M4 whitespace-AND comparator range subset."""

    current = _semver_key(version)
    comparators = version_range.split()
    if not comparators:
        raise SemanticRuleViolation("PACK_DEPENDENCY_CONFLICT", "Pack version range is empty.")
    for comparator in comparators:
        operator = next(
            (item for item in (">=", "<=", ">", "<", "=") if comparator.startswith(item)), "="
        )
        expected_text = (
            comparator[len(operator) :] if comparator.startswith(operator) else comparator
        )
        expected = _semver_key(expected_text)
        if operator == ">=" and not current >= expected:
            return False
        if operator == "<=" and not current <= expected:
            return False
        if operator == ">" and not current > expected:
            return False
        if operator == "<" and not current < expected:
            return False
        if operator == "=" and not current == expected:
            return False
    return True


def pack_descriptor(manifest: Mapping[str, Any]) -> bytes:
    descriptor = dict(manifest)
    security = dict(descriptor.get("security", {}))
    signature = dict(security.get("signature", {}))
    signature.pop("value", None)
    security["signature"] = signature
    descriptor["security"] = security
    return canonical_json(descriptor)


@dataclass(frozen=True, slots=True)
class PackVerification:
    content_checksum: str
    key_id: str


def verify_signed_revocation_list(
    *, document: Mapping[str, Any], public_key: bytes
) -> PackVerification:
    """Verify the frozen offline revocation-list envelope without applying it."""

    _check_json_value(document)
    if (
        document.get("apiVersion") != "nexweave.io/pack-revocation/v1alpha1"
        or document.get("kind") != "NexweavePackRevocationList"
        or document.get("canonicalizationAlgorithm") != "RFC8785-JCS/1"
    ):
        raise SemanticRuleViolation(
            "PACK_ARTIFACT_INVALID", "Pack revocation-list identity is invalid."
        )
    revoked = document.get("revoked")
    security = document.get("security")
    if not isinstance(revoked, list) or not 1 <= len(revoked) <= 1000:
        raise SemanticRuleViolation(
            "PACK_RESOURCE_LIMIT_EXCEEDED", "Pack revocation-list size is invalid."
        )
    if not isinstance(security, Mapping) or not isinstance(security.get("signature"), Mapping):
        raise SemanticRuleViolation(
            "PACK_SIGNATURE_INVALID", "Pack revocation-list signature is missing."
        )
    signature = security["signature"]
    if signature.get("algorithm") != "Ed25519" or not isinstance(signature.get("keyId"), str):
        raise SemanticRuleViolation(
            "PACK_SIGNATURE_INVALID", "Pack revocation-list signature metadata is invalid."
        )
    for entry in revoked:
        if not isinstance(entry, Mapping) or not isinstance(entry.get("reasonCode"), str):
            raise SemanticRuleViolation(
                "PACK_ARTIFACT_INVALID", "Pack revocation target is invalid."
            )
        by_key = isinstance(entry.get("keyId"), str)
        by_artifact = all(
            isinstance(entry.get(name), str) for name in ("packId", "version", "contentChecksum")
        )
        if by_key == by_artifact:
            raise SemanticRuleViolation(
                "PACK_ARTIFACT_INVALID",
                "Revocation must target exactly one key or exact Pack artifact.",
            )
    try:
        encoded = str(signature["value"])
        raw_signature = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            raw_signature, pack_descriptor(document)
        )
    except (ValueError, InvalidSignature, KeyError) as exc:
        raise SemanticRuleViolation(
            "PACK_SIGNATURE_INVALID", "Pack revocation-list signature verification failed."
        ) from exc
    return PackVerification(sha256_checksum(pack_descriptor(document)), str(signature["keyId"]))


def verify_pack(
    *, manifest: Mapping[str, Any], files: Mapping[str, bytes], public_key: bytes
) -> PackVerification:
    """Verify an untrusted Pack without filesystem traversal or implicit I/O."""

    metadata = manifest.get("metadata")
    security = manifest.get("security")
    content = manifest.get("content")
    if (
        not isinstance(metadata, Mapping)
        or not isinstance(security, Mapping)
        or not isinstance(content, Mapping)
    ):
        raise SemanticRuleViolation("PACK_ARTIFACT_INVALID", "Manifest sections are incomplete.")
    pack_id = metadata.get("id")
    namespace = metadata.get("keyNamespace")
    if (
        not isinstance(pack_id, str)
        or not PACK_ID_PATTERN.fullmatch(pack_id)
        or not isinstance(namespace, str)
    ):
        raise SemanticRuleViolation(
            "PACK_ARTIFACT_INVALID", "Pack identity or namespace is invalid."
        )
    if (
        len(files) > MAX_PACK_FILES
        or sum(len(item) for item in files.values()) > MAX_PACK_TOTAL_BYTES
    ):
        raise SemanticRuleViolation(
            "PACK_RESOURCE_LIMIT_EXCEEDED", "Pack exceeds total resource limits."
        )
    declared_paths: set[str] = set()
    for name, descriptor in content.items():
        if not isinstance(name, str) or not isinstance(descriptor, Mapping):
            raise SemanticRuleViolation(
                "PACK_ARTIFACT_INVALID", "Pack content descriptor is invalid."
            )
        path, checksum = descriptor.get("path"), descriptor.get("sha256")
        if not isinstance(path, str) or not isinstance(checksum, str):
            raise SemanticRuleViolation(
                "PACK_ARTIFACT_INVALID", "Pack content checksum is missing."
            )
        validate_pack_path(path)
        declared_paths.add(path)
        file_content = files.get(path)
        if file_content is None or len(file_content) > MAX_PACK_FILE_BYTES:
            raise SemanticRuleViolation(
                "PACK_ARTIFACT_INVALID", "Declared Pack content is unavailable or oversized."
            )
        parse_pack_json(file_content)
        if sha256_checksum(canonical_json(parse_pack_json(file_content))) != checksum:
            raise SemanticRuleViolation(
                "PACK_SIGNATURE_INVALID", "Pack content checksum does not match."
            )
    if set(files) != declared_paths:
        raise SemanticRuleViolation(
            "PACK_ARTIFACT_INVALID", "Pack has undeclared or missing content files."
        )
    signature = security.get("signature")
    if security.get("executableContent") is not False or not isinstance(signature, Mapping):
        raise SemanticRuleViolation(
            "PACK_ARTIFACT_INVALID", "Pack must explicitly prohibit executable content."
        )
    if signature.get("algorithm") != "Ed25519" or not isinstance(signature.get("keyId"), str):
        raise SemanticRuleViolation("PACK_SIGNATURE_INVALID", "Pack signature metadata is invalid.")
    try:
        raw_signature = base64.urlsafe_b64decode(str(signature["value"]) + "==")
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            raw_signature, pack_descriptor(manifest)
        )
    except (ValueError, InvalidSignature, KeyError) as exc:
        raise SemanticRuleViolation(
            "PACK_SIGNATURE_INVALID", "Pack signature verification failed."
        ) from exc
    return PackVerification(sha256_checksum(pack_descriptor(manifest)), str(signature["keyId"]))


@dataclass(frozen=True, slots=True)
class CompositionResult:
    normalized_snapshot: dict[str, Any]
    composition_checksum: str
    pack_order: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompatibilityReport:
    classification: str
    changes: tuple[dict[str, Any], ...]
    migration_operations: tuple[dict[str, Any], ...]
    breaking: bool


def compose_declarations(
    *, packs: Mapping[str, Mapping[str, Any]], dependencies: Mapping[str, Iterable[str]]
) -> CompositionResult:
    """Compose declarations with no installation-order precedence or silent overwrite."""

    pack_order = deterministic_topological_order(dependencies)
    if set(pack_order) != set(packs):
        raise SemanticRuleViolation(
            "PACK_DEPENDENCY_CONFLICT", "Pack inputs and dependency graph differ."
        )
    types: dict[str, dict[str, Any]] = {}
    properties: dict[tuple[str, str], dict[str, Any]] = {}
    relations: dict[str, dict[str, Any]] = {}
    hierarchy: set[tuple[str, str]] = set()
    exact_mappings: dict[str, str] = {}
    exact_mapping_targets: dict[str, str] = {}
    mappings: list[dict[str, Any]] = []
    terms: list[dict[str, Any]] = []
    preferred_terms: set[tuple[str, str, str]] = set()
    templates: dict[str, dict[str, Any]] = {}
    lint_rules: dict[str, dict[str, Any]] = {}
    evaluation_suites: dict[str, dict[str, Any]] = {}
    ui_declarations: dict[str, dict[str, Any]] = {}
    signals: dict[str, dict[str, Any]] = {}
    forecast_profiles: dict[str, dict[str, Any]] = {}
    for pack_id in pack_order:
        declaration = packs[pack_id]
        for item in sorted(
            declaration.get("types", ()), key=lambda entry: str(entry.get("key", ""))
        ):
            key = validate_stable_key(str(item.get("key", "")))
            normalized = {key: item[key] for key in sorted(item)}
            existing = types.get(key)
            if existing is not None and existing != normalized:
                raise SemanticRuleViolation(
                    "PACK_COMPOSITION_CONFLICT", "Type key has incompatible definitions."
                )
            types[key] = normalized
        for item in sorted(
            declaration.get("properties", ()),
            key=lambda entry: (str(entry.get("typeKey", "")), str(entry.get("key", ""))),
        ):
            type_key = validate_stable_key(str(item.get("typeKey", "")))
            key = validate_stable_key(str(item.get("key", "")))
            if type_key not in types:
                raise SemanticRuleViolation(
                    "SEMANTIC_MODEL_INVALID", "Property references an unavailable type."
                )
            normalized = {key: item[key] for key in sorted(item)}
            identity = (type_key, key)
            existing = properties.get(identity)
            if existing is not None and existing != normalized:
                raise SemanticRuleViolation(
                    "PACK_COMPOSITION_CONFLICT", "Property has incompatible inherited constraints."
                )
            properties[identity] = normalized
        for item in sorted(
            declaration.get("hierarchy", ()),
            key=lambda entry: (str(entry.get("child", "")), str(entry.get("parent", ""))),
        ):
            child = validate_stable_key(str(item.get("child", "")))
            parent = validate_stable_key(str(item.get("parent", "")))
            if child == parent or child not in types or parent not in types:
                raise SemanticRuleViolation(
                    "SEMANTIC_MODEL_INVALID", "Type hierarchy endpoint is invalid."
                )
            hierarchy.add((child, parent))
        for item in sorted(
            declaration.get("relations", ()), key=lambda entry: str(entry.get("key", ""))
        ):
            key = validate_stable_key(str(item.get("key", "")))
            domain, range_ = str(item.get("domain", "")), str(item.get("range", ""))
            if domain not in types or range_ not in types:
                raise SemanticRuleViolation(
                    "SEMANTIC_MODEL_INVALID", "Relation endpoint is unavailable."
                )
            normalized = {key: item[key] for key in sorted(item)}
            existing = relations.get(key)
            if existing is not None and existing != normalized:
                raise SemanticRuleViolation(
                    "PACK_COMPOSITION_CONFLICT", "Relation key has incompatible definitions."
                )
            relations[key] = normalized
        for item in sorted(
            declaration.get("mappings", ()),
            key=lambda entry: (str(entry.get("source", "")), str(entry.get("target", ""))),
        ):
            source, target, kind = (
                str(item.get("source", "")),
                str(item.get("target", "")),
                item.get("kind"),
            )
            if (
                source not in types
                or target not in types
                or kind not in {"EXACT", "BROADER", "NARROWER", "RELATED"}
            ):
                raise SemanticRuleViolation("SEMANTIC_MODEL_INVALID", "Concept mapping is invalid.")
            if kind == "EXACT" and source in exact_mappings and exact_mappings[source] != target:
                raise SemanticRuleViolation(
                    "SEMANTIC_MAPPING_AMBIGUOUS", "EXACT mapping has multiple targets."
                )
            if (
                kind == "EXACT"
                and target in exact_mapping_targets
                and exact_mapping_targets[target] != source
            ):
                raise SemanticRuleViolation(
                    "SEMANTIC_MAPPING_AMBIGUOUS", "EXACT mapping has multiple sources."
                )
            if kind == "EXACT":
                exact_mappings[source] = target
                exact_mapping_targets[target] = source
            mappings.append({key: item[key] for key in sorted(item)})
        for item in sorted(
            declaration.get("terms", ()),
            key=lambda entry: (
                str(entry.get("targetKey", "")),
                str(entry.get("language", "")),
                str(entry.get("scope", "GLOBAL")),
                str(entry.get("term", "")),
            ),
        ):
            target = validate_stable_key(str(item.get("targetKey", "")))
            if target not in types and target not in relations:
                raise SemanticRuleViolation(
                    "SEMANTIC_MODEL_INVALID", "TypeTerm target is unavailable."
                )
            normalized = {key: item[key] for key in sorted(item)}
            if item.get("kind") == "PREFERRED":
                term_identity = (
                    target,
                    str(item.get("language", "")),
                    str(item.get("scope", "GLOBAL")),
                )
                if term_identity in preferred_terms:
                    raise SemanticRuleViolation(
                        "PACK_COMPOSITION_CONFLICT",
                        "A target has multiple preferred terms in the same language and scope.",
                    )
                preferred_terms.add(term_identity)
            terms.append(normalized)
        _merge_keyed_declarations(templates, declaration.get("templates", ()), "template")
        _merge_keyed_declarations(lint_rules, declaration.get("lintRules", ()), "lint rule")
        _merge_keyed_declarations(
            evaluation_suites, declaration.get("evaluationSuites", ()), "evaluation suite"
        )
        _merge_keyed_declarations(ui_declarations, declaration.get("ui", ()), "UI declaration")
        _merge_keyed_declarations(signals, declaration.get("signalDefinitions", ()), "signal")
        _merge_keyed_declarations(
            forecast_profiles, declaration.get("forecastProfiles", ()), "forecast profile"
        )
    _assert_acyclic_hierarchy(hierarchy)
    _assert_inheritance_compatible(hierarchy, properties)
    for relation in relations.values():
        inverse = relation.get("inverseOf")
        if inverse is not None and inverse not in relations:
            raise SemanticRuleViolation(
                "SEMANTIC_MODEL_INVALID", "Relation inverse candidate is unavailable."
            )
    snapshot = {
        "algorithm": "nexweave.semantic-compose/1",
        "packs": list(pack_order),
        "types": [types[key] for key in sorted(types)],
        "properties": [properties[key] for key in sorted(properties)],
        "hierarchy": [{"child": child, "parent": parent} for child, parent in sorted(hierarchy)],
        "relations": [relations[key] for key in sorted(relations)],
        "mappings": sorted(mappings, key=canonical_json),
        "terms": sorted(terms, key=canonical_json),
        "templates": [templates[key] for key in sorted(templates)],
        "lintRules": [lint_rules[key] for key in sorted(lint_rules)],
        "evaluationSuites": [evaluation_suites[key] for key in sorted(evaluation_suites)],
        "ui": [ui_declarations[key] for key in sorted(ui_declarations)],
    }
    if signals or forecast_profiles:
        from nexweave_domain.forecast import validate_temporal_declarations

        snapshot["temporalContractVersion"] = "nexweave.timeseries/1"
        snapshot["signalDefinitions"] = [signals[key] for key in sorted(signals)]
        snapshot["forecastProfiles"] = [forecast_profiles[key] for key in sorted(forecast_profiles)]
        validate_temporal_declarations(snapshot)
    return CompositionResult(snapshot, sha256_checksum(canonical_json(snapshot)), pack_order)


def _merge_keyed_declarations(
    target: dict[str, dict[str, Any]], values: Iterable[Mapping[str, Any]], label: str
) -> None:
    for item in values:
        key = validate_stable_key(str(item.get("key", "")))
        normalized = {name: item[name] for name in sorted(item)}
        existing = target.get(key)
        if existing is not None and existing != normalized:
            raise SemanticRuleViolation(
                "PACK_COMPOSITION_CONFLICT", f"{label.capitalize()} key is incompatible."
            )
        target[key] = normalized


def _assert_inheritance_compatible(
    edges: Iterable[tuple[str, str]],
    properties: Mapping[tuple[str, str], Mapping[str, Any]],
) -> None:
    parents: dict[str, set[str]] = {}
    for child, parent in edges:
        parents.setdefault(child, set()).add(parent)
    direct: dict[str, dict[str, Mapping[str, Any]]] = {}
    for (type_key, property_key), definition in properties.items():
        direct.setdefault(type_key, {})[property_key] = definition

    def inherited(
        type_key: str, seen: frozenset[str] = frozenset()
    ) -> dict[str, Mapping[str, Any]]:
        if type_key in seen:
            return {}
        result: dict[str, Mapping[str, Any]] = {}
        for parent in sorted(parents.get(type_key, ())):
            for key, definition in inherited(parent, seen | {type_key}).items():
                if key in result and result[key] != definition:
                    raise SemanticRuleViolation(
                        "PACK_COMPOSITION_CONFLICT",
                        "Multiple parents contribute incompatible property constraints.",
                    )
                result[key] = definition
            for key, definition in direct.get(parent, {}).items():
                if key in result and result[key] != definition:
                    raise SemanticRuleViolation(
                        "PACK_COMPOSITION_CONFLICT",
                        "Multiple parents contribute incompatible property constraints.",
                    )
                result[key] = definition
        return result

    for child in sorted(parents):
        inherited(child)


def analyze_compatibility(
    previous: Mapping[str, Any] | None, current: Mapping[str, Any]
) -> CompatibilityReport:
    """Classify M4 semantic changes and produce the bounded preview DSL."""

    if previous is None:
        return CompatibilityReport("COMPATIBLE", (), (), False)
    changes: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    breaking = False
    conditional = False

    def keyed(snapshot: Mapping[str, Any], section: str) -> dict[str, Mapping[str, Any]]:
        return {
            str(item["key"]): item
            for item in snapshot.get(section, ())
            if isinstance(item, Mapping) and "key" in item
        }

    for section, add_operation in (("types", "addType"), ("relations", "addRelation")):
        before, after = keyed(previous, section), keyed(current, section)
        for key in sorted(before.keys() - after.keys()):
            changes.append({"section": section, "key": key, "kind": "REMOVED"})
            breaking = True
        for key in sorted(after.keys() - before.keys()):
            changes.append({"section": section, "key": key, "kind": "ADDED"})
            operations.append(
                {"operationId": f"{add_operation}:{key}", "operation": add_operation, "key": key}
            )
        for key in sorted(before.keys() & after.keys()):
            if before[key] != after[key]:
                changes.append({"section": section, "key": key, "kind": "CHANGED"})
                breaking = True

    for section in ("signalDefinitions", "forecastProfiles"):
        before, after = keyed(previous, section), keyed(current, section)
        for key in sorted(before.keys() | after.keys()):
            if before.get(key) != after.get(key):
                changes.append(
                    {
                        "section": section,
                        "key": key,
                        "kind": "ADDED"
                        if key not in before
                        else "CHANGED"
                        if key in after
                        else "REMOVED",
                    }
                )
                if key in before:
                    breaking = True

    for section in ("templates", "lintRules", "evaluationSuites", "ui"):
        before, after = keyed(previous, section), keyed(current, section)
        for key in sorted(before.keys() - after.keys()):
            changes.append({"section": section, "key": key, "kind": "REMOVED"})
            breaking = True
        for key in sorted(after.keys() - before.keys()):
            changes.append({"section": section, "key": key, "kind": "ADDED"})
        for key in sorted(before.keys() & after.keys()):
            if before[key] != after[key]:
                changes.append({"section": section, "key": key, "kind": "CHANGED"})
                conditional = True

    before_properties = {
        (str(item.get("typeKey")), str(item.get("key"))): item
        for item in previous.get("properties", ())
    }
    after_properties = {
        (str(item.get("typeKey")), str(item.get("key"))): item
        for item in current.get("properties", ())
    }
    for identity in sorted(before_properties.keys() - after_properties.keys()):
        changes.append({"section": "properties", "key": list(identity), "kind": "REMOVED"})
        breaking = True
    for identity in sorted(after_properties.keys() - before_properties.keys()):
        definition = after_properties[identity]
        required = bool(definition.get("required", False))
        changes.append({"section": "properties", "key": list(identity), "kind": "ADDED"})
        if required:
            breaking = True
        else:
            operations.append(
                {
                    "operationId": f"addOptionalProperty:{identity[0]}:{identity[1]}",
                    "operation": "addOptionalProperty",
                    "typeKey": identity[0],
                    "propertyKey": identity[1],
                }
            )
    for identity in sorted(before_properties.keys() & after_properties.keys()):
        if before_properties[identity] != after_properties[identity]:
            changes.append({"section": "properties", "key": list(identity), "kind": "CHANGED"})
            breaking = True

    before_hierarchy = {
        (str(item.get("child")), str(item.get("parent"))) for item in previous.get("hierarchy", ())
    }
    after_hierarchy = {
        (str(item.get("child")), str(item.get("parent"))) for item in current.get("hierarchy", ())
    }
    if before_hierarchy - after_hierarchy:
        breaking = True
    if after_hierarchy - before_hierarchy:
        conditional = True
    for child, parent in sorted(after_hierarchy - before_hierarchy):
        changes.append({"section": "hierarchy", "key": [child, parent], "kind": "ADDED"})
        operations.append(
            {
                "operationId": f"addSubtype:{child}:{parent}",
                "operation": "addSubtype",
                "child": child,
                "parent": parent,
            }
        )

    before_mappings = {canonical_json(item) for item in previous.get("mappings", ())}
    after_mapping_items = list(current.get("mappings", ()))
    after_mappings = {canonical_json(item) for item in after_mapping_items}
    if before_mappings - after_mappings:
        breaking = True
    for item in after_mapping_items:
        encoded = canonical_json(item)
        if encoded not in before_mappings:
            kind = item.get("kind")
            conditional = conditional or kind in {"EXACT", "BROADER", "NARROWER"}
            if kind == "RELATED":
                operations.append(
                    {
                        "operationId": (
                            f"addRelatedMapping:{item.get('source')}:{item.get('target')}"
                        ),
                        "operation": "addRelatedMapping",
                        "source": item.get("source"),
                        "target": item.get("target"),
                    }
                )
            changes.append(
                {
                    "section": "mappings",
                    "key": [item.get("source"), item.get("target"), kind],
                    "kind": "ADDED",
                }
            )

    classification = "BREAKING" if breaking else ("CONDITIONAL" if conditional else "COMPATIBLE")
    if len(operations) > 100:
        raise SemanticRuleViolation(
            "PACK_RESOURCE_LIMIT_EXCEEDED", "Migration preview exceeds 100 operations."
        )
    return CompatibilityReport(classification, tuple(changes), tuple(operations), breaking)


def _assert_acyclic_hierarchy(edges: Iterable[tuple[str, str]]) -> None:
    parents: dict[str, set[str]] = {}
    for child, parent in edges:
        parents.setdefault(child, set()).add(parent)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise SemanticRuleViolation(
                "PACK_COMPOSITION_CONFLICT", "Type hierarchy contains a cycle."
            )
        if node in visited:
            return
        visiting.add(node)
        for parent in sorted(parents.get(node, ())):
            visit(parent)
        visiting.remove(node)
        visited.add(node)

    for key in sorted(parents):
        visit(key)


def deterministic_topological_order(nodes: Mapping[str, Iterable[str]]) -> tuple[str, ...]:
    """Return a stable dependency-first order and reject missing/cyclic dependencies."""

    pending = {name: set(dependencies) for name, dependencies in nodes.items()}
    if any(
        dependency not in pending
        for dependencies in pending.values()
        for dependency in dependencies
    ):
        raise SemanticRuleViolation("PACK_DEPENDENCY_CONFLICT", "Pack dependency is not available.")
    ordered: list[str] = []
    while pending:
        ready = sorted(name for name, dependencies in pending.items() if not dependencies)
        if not ready:
            raise SemanticRuleViolation(
                "PACK_DEPENDENCY_CONFLICT", "Pack dependency graph contains a cycle."
            )
        ordered.extend(ready)
        completed = set(ready)
        pending = {
            name: dependencies - completed
            for name, dependencies in pending.items()
            if name not in completed
        }
    return tuple(ordered)
