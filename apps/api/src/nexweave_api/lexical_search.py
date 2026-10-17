"""Deterministic lexical retrieval, explicitly not an embedding/LLM substitute."""

import re
import unicodedata
from typing import Any

_STOP = frozenset(
    (
        "a an the is are was were what which who how do does did please tell me about "
        "of for in on at to from with and or this that current state status can could "
        "would should it its i we you 的 是 吗 呢 请 问 多少 什么 哪些 如何 当前 告诉 我"
    ).split()
)


def normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def tokens(value: str) -> set[str]:
    value = normalized(value)
    found = {t for t in re.findall(r"[a-z0-9]+(?:[-_][a-z0-9]+)*", value) if t not in _STOP}
    for run in re.findall(r"[\u3400-\u9fff]+", value):
        found.update(run[i : i + 2] for i in range(len(run) - 1) if run[i : i + 2] not in _STOP)
        if len(run) == 1 and run not in _STOP:
            found.add(run)
    return found


def object_scope(documents: list[dict[str, Any]], question: str) -> list[dict[str, Any]]:
    query = normalized(question)
    # A verbatim approved statement may mention a second entity without a
    # separate Claim in this release. Its complete quote is a valid exact hit;
    # object-qualified questions still pass through the stricter scope checks.
    exact = [
        d for d in documents if d["object_type"] == "CLAIM" and normalized(str(d["body"])) == query
    ]
    if exact:
        return exact
    names = {normalized(str(d["title"])) for d in documents if d["object_type"] == "CLAIM"}

    def mentioned(name: str) -> bool:
        if not name:
            return False
        left = r"(?<![a-z0-9])" if name[0].isascii() else ""
        right = r"(?![a-z0-9])" if name[-1].isascii() else ""
        return bool(re.search(left + re.escape(name) + right, query))

    chosen = {n for n in names if mentioned(n)}
    # Explicit IDs and qualified object phrases cannot be satisfied by an
    # unrelated object merely sharing words such as 'temperature'.
    ids = re.findall(r"(?<![a-z0-9])[a-z]+[-_]?[0-9]+(?:[-_][a-z0-9]+)*", query)
    if any(not any(i in n for n in names) for i in ids):
        return []
    if not chosen and ids:
        chosen = {n for n in names if any(i in n for i in ids)}
    scope = re.search(r"\b(?:of|for|about)\s+(.+?)(?:\s+(?:in|at|on|under)\b|[?？.!]|$)", query)
    if scope and not chosen:
        return []
    designators = re.findall(r"\b([a-z][a-z-]+\s+(?:[a-z]|[0-9]+))\b", query)
    if any(
        not any(normalized(v) == n for n in names) for v in designators if v.split()[0] not in _STOP
    ):
        return []
    return [d for d in documents if not chosen or normalized(str(d["title"])) in chosen]


def keyword_ranking(documents: list[dict[str, Any]], question: str) -> list[str]:
    documents = object_scope(documents, question)
    q = tokens(question)
    results = []
    for d in documents:
        dt = tokens(
            str(d["title"])
            + " "
            + str(d["body"])
            + " "
            + str(d.get("attributes", {}).get("schema_terms", ""))
        )
        overlap = q & dt
        content = q - tokens(str(d["title"]))
        if not overlap or (content and not (content & dt)):
            continue
        score = sum(2 if t in tokens(str(d["title"])) else 1 for t in overlap)
        results.append((-score, str(d["object_id"])))
    return [i for _, i in sorted(results)]
