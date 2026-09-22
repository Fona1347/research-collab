"""Small, source-aware evidence-chain accounting; never infer scientific independence."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


CHAIN_PREFIX = re.compile(r"^\s*chains\s*=\s*(unknown|EC-\d{3}(?:\s*,\s*EC-\d{3})*)\s*;", re.I)


def chain_ids(value: str) -> frozenset[str] | None:
    match = CHAIN_PREFIX.match(value)
    if not match or match.group(1).lower() == "unknown":
        return None
    basis = re.sub(r"^\s*basis\s*=\s*", "", value[match.end():], flags=re.I).strip()
    if not basis or re.match(r"^(?:unknown|none|pending|tbd|not[- ](?:known|available|documented))\b", basis, re.I):
        return None
    return frozenset(item.upper() for item in re.findall(r"EC-\d{3}", match.group(1), re.I))


def independently_reviewed(value: str) -> bool:
    """Require an attributable review declaration, not a vote over row text."""
    tokens = {}
    for item in value.split(";"):
        key, separator, content = item.partition("=")
        if separator:
            tokens[key.strip().lower()] = content.strip()
    return tokens.get("review", "").lower() == "independent" and all(
        tokens.get(key, "") and not re.match(r"^(?:unknown|none|pending|tbd)\b", tokens[key], re.I)
        for key in ("reviewer", "basis")
    )


@dataclass(frozen=True)
class ChainAssessment:
    count: int
    unresolved: bool
    source_conflicts: tuple[str, ...]


def assess_chains(records: Iterable[tuple[str, str]]) -> ChainAssessment:
    """Merge a paper's split rows and all explicit shared upstream chains.

    ``records`` contains normalized source identity and the existing
    Independence/replication cell. Different prose never creates a new chain.
    Multiple IDs in one source are merged; strong single-study designs use the
    separately reviewed design exception instead of manufacturing replication.
    """
    sources: dict[str, set[str]] = {}
    unknown_sources: set[str] = set()
    conflicts: set[str] = set()
    for source, cell in records:
        identifiers = chain_ids(cell)
        if not source or source.strip().lower() in {"none", "unknown", "not available", "unavailable", "n/a"}:
            unknown_sources.add("missing-source")
            continue
        if identifiers is None:
            unknown_sources.add(source)
            sources.setdefault(source, set())
        else:
            previous = sources.setdefault(source, set())
            if previous and previous != set(identifiers):
                conflicts.add(source)
            previous.update(identifiers)
    groups: list[set[str]] = []
    for source, identifiers in sources.items():
        if not identifiers:
            continue
        group = set(identifiers)
        overlaps = [existing for existing in groups if existing & group]
        for existing in overlaps:
            group.update(existing)
            groups.remove(existing)
        groups.append(group)
        unknown_sources.discard(source)
    return ChainAssessment(len(groups), bool(unknown_sources), tuple(sorted(conflicts)))
