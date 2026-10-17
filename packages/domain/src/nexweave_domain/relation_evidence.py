"""Conservative evidence-span check shared by rule and HTTP extraction adapters."""

import re
from collections.abc import Mapping, Sequence
from typing import Any


def explicit_relation_span(
    raw: str,
    source: str,
    target: str,
    relation: Mapping[str, Any],
    terms: Sequence[Mapping[str, Any]],
) -> bool:
    words = {str(relation["key"]).rsplit("/", 1)[-1].replace("-", " ")}
    words.update(str(t["term"]) for t in terms if t.get("targetKey") == relation["key"])
    words |= {w[:-1] for w in tuple(words) if w.endswith("s") and len(w) > 3}

    def name(value: str) -> str:
        return (
            (r"(?<![a-z0-9_])" if value[:1].isascii() else "")
            + re.escape(value)
            + (r"(?![a-z0-9_])" if value[-1:].isascii() else "")
        )

    for clause in re.split(r"[。.!?;；\n]", raw):
        if re.search(
            r"\b(?:not|no|never|without|may|might|could)\b|不|未|无|没有|可能|假设", clause, re.I
        ):
            continue
        if re.search(
            name(source)
            + r"\s*(?:"
            + "|".join(re.escape(w) for w in sorted(words))
            + r")\s*"
            + name(target),
            clause,
            re.I,
        ):
            return True
    return False
