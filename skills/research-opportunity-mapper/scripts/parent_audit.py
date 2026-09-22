#!/usr/bin/env python3
"""Deterministic, read-only facts for a schema-2 run-audit child.

The audit child is allowed to judge a flawed parent.  This module therefore
does not validate the parent as a prerequisite; it reconstructs observable
artifact, manifest, identifier, and citation facts that the child audit must
report faithfully.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from rom_contract import (
    CAPABILITY_ID_PATTERN,
    CLAIM_ID_PATTERN,
    COMPLETION_STATUSES,
    ContractError,
    DISCOVERY_LENSES,
    DOMAIN_LENSES,
    EVIDENCE_ID_PATTERN,
    FOCUS_TARGET_ID_PATTERN,
    ID_DEFINITION_MARKER_ROLES as DEFINITION_MARKER_ROLES,
    ID_DEFINITION_SPECS,
    MODE_ROLES,
    REQUESTED_MODES,
    ROUTING_CONFIDENCE,
    RUN_TYPES,
    SKILL_ID,
    SKILL_VERSION,
    VALIDATOR_VERSION,
    artifact_profile,
    parse_schema_version,
    resolve_contained_file,
    safe_manifest_relpath,
    sha256_file,
    validate_custom_domain_lens_notes,
)


SUPPORTED_PARENT_SCHEMAS = {"1.0", "1.1", "1.2", "2.0"}
PARENT_ID_PATTERN = re.compile(
    r"\b(?:ART|BR|CAP|CTX|CL|GS|B|M|S|C|E|Q|A|D|I|H|G|F|R)-\d{3}\b"
    r"|\bC-[LMH]\d{2}\b"
)
MARKER_PATTERN = re.compile(
    r"^<!--\s*rom-(?:section|table):\s*([a-z0-9-]+)\s*-->$",
    re.IGNORECASE,
)
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
CONTEXT_ID_PATTERN = re.compile(r"^CTX-\d{3}$")
ROLE_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
LEGACY_READER_REPORT_PATTERN = re.compile(
    r"^map_report_.+_\d{4}-\d{2}-\d{2}\.md$",
    re.IGNORECASE,
)
MANIFEST_FAILURE_REPAIRS: Mapping[str, str] = {
    "schema-supported": (
        "Create a separate revision copy with an explicitly supported schema; "
        "do not edit the audited parent."
    ),
    "skill-identifier": (
        "In a separate revision copy, restore skill=research-opportunity-mapper "
        "and refresh lineage hashes without editing the audited parent."
    ),
    "run-id-lineage": (
        "Correct the audit child lineage to bind the parent's actual run_id and "
        "exact source manifest SHA-256."
    ),
    "package-versions": (
        "In a separate revision copy, set the current skill and validator versions "
        "and refresh the manifest hash."
    ),
    "identity-metadata": (
        "In a separate revision copy, restore substantive run_id, domain, "
        "short_task_name, and language fields."
    ),
    "domain-lenses": (
        "In a separate revision copy, use one registered primary lens and unique "
        "registered secondary lenses; for custom, supply all ten labeled Common "
        "Lens Interface slots exactly once with substantive values."
    ),
    "created-at": (
        "In a separate revision copy, write a timezone-aware ISO-8601 created_at value."
    ),
    "evidence-window": (
        "In a separate revision copy, restore ordered start, end, and as-of dates "
        "with start no later than end and end no later than as-of."
    ),
    "frontier-policy": (
        "In a separate revision copy, restore the complete frontier policy and "
        "keep frontier salience separate from claim confidence."
    ),
    "routing-contract": (
        "In a separate revision copy, align routing request, requested mode, "
        "selected mode, reasons, and confidence with the persisted run type."
    ),
    "parent-mutation-policy": (
        "In a separate revision copy, restore the mode-appropriate immutable-parent "
        "mutation policy."
    ),
    "lineage-structure": (
        "In a separate revision copy, rebuild unique typed workspace-relative "
        "parent records with exact source manifest and artifact hashes."
    ),
    "context-sources": (
        "In a separate revision copy, rebuild unique read-only context records "
        "with safe workspace-relative paths and exact snapshot hashes."
    ),
    "selected-branch": (
        "In a separate revision copy, bind selected_branch to the declared mode "
        "and a resolvable parent branch or bounded standalone label."
    ),
    "inherited-ids": (
        "In a separate revision copy, retain only unique typed IDs that resolve "
        "in the declared immutable parent snapshot."
    ),
    "artifact-files-list": (
        "In a separate revision copy, rebuild artifact_files as a list of strings."
    ),
    "artifact-files-safe": (
        "In a separate revision copy, replace unsafe artifact paths with canonical "
        "workspace-contained relative paths."
    ),
    "artifact-files-unique": (
        "In a separate revision copy, remove duplicate artifact paths after "
        "canonical normalization."
    ),
    "declared-vs-observed": (
        "In a separate revision copy, restore each declared artifact or remove its "
        "stale declaration, and declare every observed in-scope artifact."
    ),
    "primary-artifact": (
        "In a separate revision copy, bind the schema-authorized reader artifact "
        "to one declared, observed report; preserve the schema 1.1 declaration rule."
    ),
    "artifact-roles": (
        "In a separate revision copy, rebuild the complete mode-specific artifact "
        "role map with unique existing paths and the correct artifact profile."
    ),
    "mode-routing": (
        "In a separate revision copy, align task_mode, run_type, routing.selected, "
        "and discovery_lens to registered values."
    ),
    "completion-status": (
        "In a separate revision copy, rerun the applicable completion gates and "
        "persist only a registered completion status."
    ),
}


def canonical_manifest_repair(check: str, result: str) -> str:
    """Return the deterministic repair authorized by a recomputed manifest check."""

    normalized_result = result.strip().lower()
    if check not in MANIFEST_FAILURE_REPAIRS:
        raise ContractError(
            f"No canonical manifest repair is registered for check {check!r}"
        )
    if normalized_result in {"pass", "not-applicable"}:
        return "retain observed state"
    if normalized_result != "fail":
        raise ContractError(
            f"No canonical manifest repair is registered for {check!r}={result!r}"
        )
    return MANIFEST_FAILURE_REPAIRS[check]


@dataclass(frozen=True)
class MarkdownTable:
    headers: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]
    row_lines: tuple[int, ...]
    marker: str | None = None


@dataclass(frozen=True)
class ParentAuditFacts:
    schema_version: str
    run_id: str
    artifact_projection: tuple[tuple[str, ...], ...]
    manifest_projection: tuple[tuple[str, ...], ...]
    id_projection: tuple[tuple[str, ...], ...]
    citation_projection: tuple[tuple[str, ...], ...]
    observed_ids: frozenset[str]


def _normalize_header(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value.lower(), flags=re.UNICODE)


def _split_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]
    cells: list[str] = []
    buffer: list[str] = []
    escaped = False
    code_ticks = 0
    index = 0
    while index < len(stripped):
        char = stripped[index]
        if escaped:
            buffer.append(char)
            escaped = False
            index += 1
            continue
        if char == "\\":
            escaped = True
            buffer.append(char)
            index += 1
            continue
        if char == "`":
            end = index
            while end < len(stripped) and stripped[end] == "`":
                end += 1
            ticks = end - index
            code_ticks = 0 if code_ticks == ticks else ticks if code_ticks == 0 else code_ticks
            buffer.append(stripped[index:end])
            index = end
            continue
        if char == "|" and code_ticks == 0:
            cells.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(char)
        index += 1
    cells.append("".join(buffer).strip())
    return cells


def _strip_visible_lines(text: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    in_comment = False
    fence_char: str | None = None
    fence_length = 0
    for number, raw in enumerate(text.splitlines(), 1):
        fence = re.match(r"^\s*(`{3,}|~{3,})", raw)
        if fence_char is not None:
            if fence and fence.group(1)[0] == fence_char and len(fence.group(1)) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        if fence and not in_comment:
            fence_char = fence.group(1)[0]
            fence_length = len(fence.group(1))
            continue
        output: list[str] = []
        cursor = 0
        while cursor < len(raw):
            if in_comment:
                end = raw.find("-->", cursor)
                if end < 0:
                    cursor = len(raw)
                    break
                cursor = end + 3
                in_comment = False
                continue
            start = raw.find("<!--", cursor)
            if start < 0:
                output.append(raw[cursor:])
                break
            output.append(raw[cursor:start])
            cursor = start + 4
            in_comment = True
        visible = "".join(output)
        if visible.strip():
            result.append((number, visible.rstrip()))
    return result


def _tables(text: str) -> list[MarkdownTable]:
    raw_lines = text.splitlines()
    visible_by_index = {
        number - 1: line for number, line in _strip_visible_lines(text)
    }
    marker_for_line: dict[int, str] = {}
    active_marker: str | None = None
    in_comment = False
    fence_char: str | None = None
    fence_length = 0
    for index, raw in enumerate(raw_lines):
        fence = re.match(r"^\s*(`{3,}|~{3,})", raw)
        if fence_char is not None:
            if fence and fence.group(1)[0] == fence_char and len(fence.group(1)) >= fence_length:
                fence_char = None
                fence_length = 0
            continue
        if fence and not in_comment:
            fence_char = fence.group(1)[0]
            fence_length = len(fence.group(1))
            continue
        if not in_comment:
            marker = MARKER_PATTERN.fullmatch(raw.strip())
            if marker:
                active_marker = marker.group(1).lower()
                continue
        cursor = 0
        visible_parts: list[str] = []
        while cursor < len(raw):
            if in_comment:
                end = raw.find("-->", cursor)
                if end < 0:
                    cursor = len(raw)
                    break
                cursor = end + 3
                in_comment = False
                continue
            start = raw.find("<!--", cursor)
            if start < 0:
                visible_parts.append(raw[cursor:])
                break
            visible_parts.append(raw[cursor:start])
            cursor = start + 4
            in_comment = True
        visible = "".join(visible_parts)
        if visible.lstrip().startswith("|") and active_marker is not None:
            marker_for_line[index] = active_marker
        elif visible.strip() and not visible.lstrip().startswith("#"):
            active_marker = None

    result: list[MarkdownTable] = []
    used_markers: set[str] = set()
    index = 0
    while index < len(raw_lines):
        visible = visible_by_index.get(index, "")
        if not visible.lstrip().startswith("|"):
            index += 1
            continue
        start = index
        block: list[str] = []
        while index < len(raw_lines) and visible_by_index.get(index, "").lstrip().startswith("|"):
            block.append(visible_by_index[index])
            index += 1
        if len(block) < 2:
            continue
        headers = _split_row(block[0])
        separator = _split_row(block[1])
        if len(headers) != len(separator) or not all(
            re.fullmatch(r":?-{3,}:?", cell) for cell in separator
        ):
            continue
        rows: list[tuple[str, ...]] = []
        row_lines: list[int] = []
        for offset, raw in enumerate(block[2:], 2):
            cells = _split_row(raw)
            if len(cells) == len(headers):
                rows.append(tuple(cells))
                row_lines.append(start + offset + 1)
        marker = marker_for_line.get(start)
        if marker in used_markers:
            marker = None
        elif marker is not None:
            used_markers.add(marker)
        result.append(
            MarkdownTable(
                tuple(headers), tuple(rows), tuple(row_lines), marker
            )
        )
    return result


def _exact_column(table: MarkdownTable, name: str) -> int | None:
    wanted = _normalize_header(name)
    normalized = [_normalize_header(value) for value in table.headers]
    try:
        return normalized.index(wanted)
    except ValueError:
        return None


def _safe_relpath(value: object) -> str | None:
    try:
        return safe_manifest_relpath(value, label="parent manifest path").as_posix()
    except ContractError:
        return None

def _legacy_reader_rel(
    manifest: Mapping[str, object], schema: str
) -> str | None:
    """Resolve only the reader declaration authorized by each legacy schema."""

    if schema == "1.0":
        return None
    if schema == "1.1":
        raw_files = manifest.get("artifact_files")
        candidates = [
            rel
            for item in raw_files if isinstance(raw_files, list) and isinstance(item, str)
            if LEGACY_READER_REPORT_PATTERN.fullmatch(item)
            if (rel := _safe_relpath(item)) is not None
        ] if isinstance(raw_files, list) else []
        return candidates[0] if len(candidates) == 1 else None
    if schema == "1.2":
        return _safe_relpath(manifest.get("primary_artifact"))
    return None


def _observed_files(parent_dir: Path) -> dict[str, Path]:
    observed: dict[str, Path] = {}
    root = parent_dir.resolve()
    for path in parent_dir.rglob("*"):
        if not path.is_file() or path == parent_dir / "run-manifest.json":
            continue
        resolved = path.resolve(strict=True)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ValueError(f"unsafe parent audit file target: {path}") from exc
        observed[path.relative_to(parent_dir).as_posix()] = resolved
    return observed


def _roles_by_path(manifest: Mapping[str, object], schema: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = defaultdict(list)
    roles = manifest.get("artifact_roles")
    if isinstance(roles, dict):
        for role, raw_path in roles.items():
            rel = _safe_relpath(raw_path)
            if isinstance(role, str) and rel is not None:
                result[rel].append(role)
    legacy = {
        "00_intake.md": "intake",
        "01_breadth-ledger.md": "breadth_ledger",
        "02_search-log.md": "search_log",
        "03_evidence-matrix.md": "evidence_matrix",
        "04_research-map.md": "research_map",
        "05_candidate-portfolio.md": "candidate_portfolio",
        "06_red-team.md": "red_team",
        "07_decision-log.md": "decision_log",
    }
    if schema.startswith("1."):
        for path, role in legacy.items():
            result[path].append(role)
        reader_rel = _legacy_reader_rel(manifest, schema)
        if reader_rel is not None:
            result[reader_rel].append("reader_report")
    return result


def _timezone_aware_iso_datetime(value: object) -> bool:
    if not isinstance(value, str):
        return False
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return False
    return parsed.tzinfo is not None and parsed.utcoffset() is not None


def _historical_parent_verified(parent_dir: Path) -> bool:
    """Ask the workspace's existing verifier about frozen pre-upgrade history.

    Standalone/unsealed parents are still auditable, but cannot self-declare
    historical compatibility merely by changing their manifest version.
    """
    parent = parent_dir.resolve()
    if parent.parent.name != "runs":
        return False
    workspace = parent.parent.parent
    script = workspace / "tools/workspace/seal_mapper_run.py"
    if not script.is_file() or script.is_symlink():
        return False
    module_name = "_rom_historical_seal_verifier"
    previous = sys.modules.get(module_name)
    try:
        script.resolve(strict=True).relative_to(workspace)
        spec = importlib.util.spec_from_file_location(module_name, script)
        if spec is None or spec.loader is None:
            return False
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        result = module.verify_seal(parent, workspace_root=workspace)
        return bool(result.valid and result.status == "historical-sealed")
    except (OSError, ValueError, ImportError, AttributeError, RuntimeError):
        return False
    finally:
        if previous is None:
            sys.modules.pop(module_name, None)
        else:
            sys.modules[module_name] = previous


def _schema2_manifest_structure(
    manifest: Mapping[str, object],
    *,
    mode: object,
    historical_verified: bool = False,
) -> tuple[tuple[str, str, str], ...]:
    """Return structural schema-2 manifest checks without trusting the parent.

    These checks deliberately avoid resolving the parent's own lineage or
    context sources because this audit helper receives only the parent run
    directory, not an authoritative workspace root.  Paths and snapshot hashes
    are still checked for canonical, typed structure; live target identity is a
    separate lineage-resolution concern.
    """

    def row(name: str, evidence: str, condition: bool) -> tuple[str, str, str]:
        return (name, evidence, "pass" if condition else "fail")

    normalized_mode = mode if isinstance(mode, str) else None
    package_ok = (
        manifest.get("skill_version") == SKILL_VERSION
        and manifest.get("validator_version") == VALIDATOR_VERSION
    ) or historical_verified
    identity_fields = ("run_id", "domain", "short_task_name", "language")
    identity_ok = all(
        isinstance(manifest.get(name), str) and bool(str(manifest.get(name)).strip())
        for name in identity_fields
    )
    primary_domain_lens = manifest.get("primary_domain_lens")
    secondary_domain_lenses = manifest.get("secondary_domain_lenses")
    domain_lens_notes = manifest.get("domain_lens_notes")
    custom_domain_lens_ok = True
    if primary_domain_lens == "custom":
        try:
            validate_custom_domain_lens_notes(domain_lens_notes)
        except ContractError:
            custom_domain_lens_ok = False
    domain_lenses_ok = (
        primary_domain_lens in DOMAIN_LENSES
        and isinstance(secondary_domain_lenses, list)
        and all(isinstance(value, str) for value in secondary_domain_lenses)
        and len(secondary_domain_lenses) == len(set(secondary_domain_lenses))
        and all(value in DOMAIN_LENSES for value in secondary_domain_lenses)
        and primary_domain_lens not in secondary_domain_lenses
        and custom_domain_lens_ok
    )
    domain_lenses_evidence = (
        f"primary={primary_domain_lens}; secondary="
        f"{','.join(secondary_domain_lenses) if isinstance(secondary_domain_lenses, list) and all(isinstance(value, str) for value in secondary_domain_lenses) else 'invalid'}; "
        f"custom-notes={'present' if isinstance(domain_lens_notes, str) and domain_lens_notes.strip() else 'absent'}"
    )

    created_at = manifest.get("created_at")
    created_ok = _timezone_aware_iso_datetime(created_at)

    as_of_raw = manifest.get("as_of_date")
    try:
        as_of = date.fromisoformat(as_of_raw) if isinstance(as_of_raw, str) else None
    except ValueError:
        as_of = None
    window = manifest.get("evidence_window")
    window_ok = False
    window_evidence = type(window).__name__
    if isinstance(window, dict):
        try:
            start_raw = window.get("start")
            end_raw = window.get("end")
            window_as_of_raw = window.get("as_of")
            start = date.fromisoformat(start_raw) if isinstance(start_raw, str) else None
            end = date.fromisoformat(end_raw) if isinstance(end_raw, str) else None
            window_as_of = (
                date.fromisoformat(window_as_of_raw)
                if isinstance(window_as_of_raw, str)
                else None
            )
        except ValueError:
            start = end = window_as_of = None
        window_ok = (
            start is not None
            and end is not None
            and window_as_of is not None
            and as_of is not None
            and start <= end <= window_as_of
            and window_as_of == as_of
            and window.get("canonical_pre_window_allowed") is True
        )
        window_evidence = (
            f"start={start_raw}; end={end_raw}; window-as-of={window_as_of_raw}; "
            f"manifest-as-of={as_of_raw}; canonical="
            f"{window.get('canonical_pre_window_allowed')}"
        )

    policy = manifest.get("frontier_policy")
    frontier_ok = (
        isinstance(policy, dict)
        and isinstance(policy.get("recent_years_default"), int)
        and not isinstance(policy.get("recent_years_default"), bool)
        and 1 <= policy.get("recent_years_default", 0) <= 10
        and policy.get("canonical_pre_window_allowed") is True
        and policy.get("citation_signal")
        == "field-year-normalized-when-available"
        and policy.get("citation_source_and_as_of_required") is True
        and policy.get("salience_is_not_claim_confidence") is True
    )
    frontier_evidence = (
        f"recent={policy.get('recent_years_default')}; "
        f"canonical={policy.get('canonical_pre_window_allowed')}; "
        f"citation={policy.get('citation_signal')}; "
        f"source-as-of={policy.get('citation_source_and_as_of_required')}; "
        f"salience-separate={policy.get('salience_is_not_claim_confidence')}"
        if isinstance(policy, dict)
        else type(policy).__name__
    )

    routing = manifest.get("routing")
    routing_reason = routing.get("reason") if isinstance(routing, dict) else None
    routing_ok = (
        isinstance(routing, dict)
        and routing.get("requested") in REQUESTED_MODES
        and routing.get("selected") == normalized_mode
        and isinstance(routing_reason, list)
        and bool(routing_reason)
        and all(isinstance(item, str) and bool(item.strip()) for item in routing_reason)
        and routing.get("confidence") in ROUTING_CONFIDENCE
        and (
            routing.get("request") is None
            or isinstance(routing.get("request"), str)
        )
    )
    routing_evidence = (
        f"requested={routing.get('requested')}; selected={routing.get('selected')}; "
        f"reasons={len(routing_reason) if isinstance(routing_reason, list) else 'invalid'}; "
        f"confidence={routing.get('confidence')}"
        if isinstance(routing, dict)
        else type(routing).__name__
    )

    expected_policy = (
        "supplement-only"
        if normalized_mode in ("evidence-audit", "run-audit")
        else "child-run-only"
    )
    mutation_ok = manifest.get("parent_mutation_policy") == expected_policy

    manifest_lineage = manifest.get("lineage")
    parents = (
        manifest_lineage.get("parents", [])
        if isinstance(manifest_lineage, dict)
        else None
    )
    expected_relation = {
        "landscape": "extends-landscape",
        "focus": "focuses-branch",
        "evidence-audit": "supplements-evidence",
        "run-audit": "audits-run",
    }.get(normalized_mode)
    if normalized_mode == "landscape" and manifest.get("completion_status") == "migrated-needs-review":
        expected_relation = "migrated-copy"
    parent_rows_ok = isinstance(parents, list)
    parent_keys: list[tuple[str, str]] = []
    if isinstance(parents, list):
        if normalized_mode == "run-audit" and len(parents) != 1:
            parent_rows_ok = False
        for parent in parents:
            if not isinstance(parent, dict):
                parent_rows_ok = False
                continue
            rel = _safe_relpath(parent.get("workspace_relpath"))
            raw_hashes = parent.get("source_artifact_sha256")
            hashes_ok = isinstance(raw_hashes, dict)
            if isinstance(raw_hashes, dict):
                normalized_hash_paths: list[str] = []
                for raw_path, raw_hash in raw_hashes.items():
                    safe_path = _safe_relpath(raw_path)
                    if safe_path is None or not isinstance(raw_hash, str) or not SHA256_PATTERN.fullmatch(raw_hash):
                        hashes_ok = False
                    elif safe_path in normalized_hash_paths:
                        hashes_ok = False
                    else:
                        normalized_hash_paths.append(safe_path)
            run_id = parent.get("run_id")
            manifest_hash = parent.get("source_manifest_sha256")
            item_ok = (
                isinstance(run_id, str)
                and bool(run_id.strip())
                and parent.get("relation") == expected_relation
                and rel is not None
                and isinstance(manifest_hash, str)
                and bool(SHA256_PATTERN.fullmatch(manifest_hash))
                and hashes_ok
            )
            parent_rows_ok = parent_rows_ok and item_ok
            if isinstance(run_id, str) and rel is not None:
                parent_keys.append((run_id, rel))
        if len(parent_keys) != len(set(parent_keys)):
            parent_rows_ok = False
    lineage_ok = isinstance(manifest_lineage, dict) and parent_rows_ok
    lineage_evidence = (
        f"parents={len(parents)}; expected-relation={expected_relation}"
        if isinstance(parents, list)
        else f"parents={type(parents).__name__}"
    )

    contexts = manifest.get("context_sources")
    contexts_ok = isinstance(contexts, list)
    context_ids: list[str] = []
    if isinstance(contexts, list):
        for source in contexts:
            if not isinstance(source, dict):
                contexts_ok = False
                continue
            source_id = source.get("source_id")
            rel = _safe_relpath(source.get("workspace_relpath"))
            role = source.get("role")
            kind = source.get("kind")
            snapshot_hash = source.get("snapshot_sha256")
            source_ok = (
                isinstance(source_id, str)
                and bool(CONTEXT_ID_PATTERN.fullmatch(source_id))
                and rel is not None
                and isinstance(role, str)
                and bool(ROLE_NAME_PATTERN.fullmatch(role))
                and source.get("access") == "read-only"
                and kind in ("file", "directory")
                and (
                    isinstance(snapshot_hash, str)
                    and bool(SHA256_PATTERN.fullmatch(snapshot_hash))
                    if kind == "file"
                    else snapshot_hash is None
                )
            )
            contexts_ok = contexts_ok and source_ok
            if isinstance(source_id, str):
                context_ids.append(source_id)
        if len(context_ids) != len(set(context_ids)):
            contexts_ok = False
    if normalized_mode == "evidence-audit" and not (
        isinstance(parents, list)
        and bool(parents)
        or isinstance(contexts, list)
        and bool(contexts)
    ):
        contexts_ok = False
    context_evidence = (
        f"contexts={len(contexts)}; unique-ids={len(set(context_ids))}"
        if isinstance(contexts, list)
        else type(contexts).__name__
    )

    selected = manifest.get("selected_branch")
    has_parents = isinstance(parents, list) and bool(parents)
    if normalized_mode != "focus":
        selected_ok = selected is None
    elif selected is None:
        selected_ok = not has_parents
    elif isinstance(selected, dict):
        branch_id = selected.get("id")
        label = selected.get("label")
        has_id = isinstance(branch_id, str) and bool(branch_id.strip())
        has_label = isinstance(label, str) and bool(label.strip())
        exactly_one = has_id != has_label
        selected_ok = exactly_one and (
            has_parents
            and selected.get("source") == "parent"
            and has_id
            and bool(FOCUS_TARGET_ID_PATTERN.fullmatch(branch_id))
            or not has_parents
            and selected.get("source") == "standalone"
            and (
                has_label
                or has_id
                and bool(FOCUS_TARGET_ID_PATTERN.fullmatch(branch_id))
            )
        )
    else:
        selected_ok = False
    selected_evidence = (
        "none"
        if selected is None
        else (
            f"id={selected.get('id')}; label={selected.get('label')}; "
            f"source={selected.get('source')}"
            if isinstance(selected, dict)
            else type(selected).__name__
        )
    )

    inherited = manifest.get("inherited_ids")
    inherited_ok = isinstance(inherited, dict)
    inherited_counts: list[str] = []
    inherited_specs = {
        "claims": CLAIM_ID_PATTERN,
        "evidence": EVIDENCE_ID_PATTERN,
        "capabilities": CAPABILITY_ID_PATTERN,
    }
    if isinstance(inherited, dict):
        for name, pattern in inherited_specs.items():
            values = inherited.get(name)
            values_ok = (
                isinstance(values, list)
                and all(isinstance(value, str) and bool(pattern.fullmatch(value)) for value in values)
                and len(values) == len(set(values))
            )
            inherited_ok = inherited_ok and values_ok
            inherited_counts.append(
                f"{name}={len(values) if isinstance(values, list) else 'invalid'}"
            )
    inherited_evidence = ", ".join(inherited_counts) or type(inherited).__name__

    return (
        row(
            "package-versions",
            f"skill={manifest.get('skill_version')}; validator={manifest.get('validator_version')}; "
            f"basis={'historical-seal-integrity' if historical_verified else 'current-package'}",
            package_ok,
        ),
        row(
            "identity-metadata",
            "; ".join(f"{name}={manifest.get(name) or 'missing'}" for name in identity_fields),
            identity_ok,
        ),
        row("domain-lenses", domain_lenses_evidence, domain_lenses_ok),
        row("created-at", str(created_at or "missing"), created_ok),
        row("evidence-window", window_evidence, window_ok),
        row("frontier-policy", frontier_evidence, frontier_ok),
        row("routing-contract", routing_evidence, routing_ok),
        row(
            "parent-mutation-policy",
            f"actual={manifest.get('parent_mutation_policy')}; expected={expected_policy}",
            mutation_ok,
        ),
        row("lineage-structure", lineage_evidence, lineage_ok),
        row("context-sources", context_evidence, contexts_ok),
        row("selected-branch", selected_evidence, selected_ok),
        row("inherited-ids", inherited_evidence, inherited_ok),
    )


def _artifact_projection(
    parent_dir: Path,
    manifest: Mapping[str, object],
    lineage: Mapping[str, object],
    schema: str,
    observed: Mapping[str, Path] | None = None,
) -> tuple[tuple[str, ...], ...]:
    observed = dict(observed) if observed is not None else _observed_files(parent_dir)
    manifest_path = resolve_contained_file(
        parent_dir, Path("run-manifest.json"), label="parent run manifest"
    )
    raw_declared = manifest.get("artifact_files")
    declared = {
        rel
        for value in raw_declared if (rel := _safe_relpath(value)) is not None
    } if isinstance(raw_declared, list) else set()
    roles = _roles_by_path(manifest, schema)
    rows: list[tuple[str, ...]] = [
        (
            "ART-001",
            "manifest",
            "run-manifest.json",
            "yes",
            "yes",
            sha256_file(manifest_path),
            f"schema {schema} manifest",
            "manifest",
        )
    ]
    for index, rel in enumerate(sorted(declared | set(observed)), 2):
        present = rel in observed
        is_declared = rel in declared
        if is_declared and present:
            status = "declared-present"
        elif is_declared:
            status = "declared-missing"
        else:
            status = "observed-undeclared"
        role = ",".join(sorted(set(roles.get(rel, [])))) or "unassigned"
        rows.append(
            (
                f"ART-{index:03d}",
                role,
                rel,
                "yes" if is_declared else "no",
                "yes" if present else "no",
                sha256_file(observed[rel]) if present else "unavailable",
                f"schema {schema} artifact",
                status,
            )
        )
    return tuple(rows)


def _manifest_projection(
    manifest: Mapping[str, object],
    lineage: Mapping[str, object],
    parent_dir: Path,
    schema: str,
    observed: Mapping[str, Path] | None = None,
) -> tuple[tuple[str, ...], ...]:
    raw_files = manifest.get("artifact_files")
    list_ok = isinstance(raw_files, list) and all(isinstance(value, str) for value in raw_files)
    safe_values = [_safe_relpath(value) for value in raw_files] if isinstance(raw_files, list) else []
    safe_ok = list_ok and all(value is not None for value in safe_values)
    normalized = [value for value in safe_values if value is not None]
    unique_ok = safe_ok and len(normalized) == len(set(normalized))
    observed_map = dict(observed) if observed is not None else _observed_files(parent_dir)
    observed = set(observed_map)
    declared = set(normalized)
    missing = sorted(declared - observed)
    extra = sorted(observed - declared)
    primary = _safe_relpath(manifest.get("primary_artifact"))
    legacy_reader = _legacy_reader_rel(manifest, schema)
    if schema == "1.0":
        primary_evidence, primary_result = "not-applicable", "not-applicable"
    elif schema == "1.1":
        primary_ok = (
            legacy_reader is not None
            and legacy_reader in declared
            and legacy_reader in observed
        )
        primary_evidence = (
            "schema-1.1 reader inferred from artifact_files="
            f"{legacy_reader or 'missing-or-ambiguous'}; primary_artifact=not-required"
        )
        primary_result = "pass" if primary_ok else "fail"
    else:
        primary_ok = primary is not None and primary in declared and primary in observed
        primary_evidence = primary or "missing-or-unsafe"
        primary_result = "pass" if primary_ok else "fail"
    roles = manifest.get("artifact_roles")
    if schema.startswith("1."):
        roles_evidence, roles_result = "not-applicable", "not-applicable"
        mode_evidence, mode_result = "not-applicable", "not-applicable"
        completion_evidence, completion_result = "not-applicable", "not-applicable"
        schema2_structure = tuple(
            (name, "not-applicable", "not-applicable")
            for name in (
                "package-versions",
                "identity-metadata",
                "domain-lenses",
                "created-at",
                "evidence-window",
                "frontier-policy",
                "routing-contract",
                "parent-mutation-policy",
                "lineage-structure",
                "context-sources",
                "selected-branch",
                "inherited-ids",
            )
        )
    else:
        mode = manifest.get("task_mode")
        expected_roles = (
            set(MODE_ROLES[mode].values()) | {"reader_report"}
            if isinstance(mode, str) and mode in RUN_TYPES
            else set()
        )
        allowed_roles = expected_roles | {"migration_report"}
        role_paths = {
            key: _safe_relpath(value)
            for key, value in roles.items()
        } if isinstance(roles, dict) else {}
        roles_ok = (
            bool(expected_roles)
            and expected_roles <= set(role_paths) <= allowed_roles
            and all(path is not None for path in role_paths.values())
            and len(set(role_paths.values())) == len(role_paths)
            and all(path in declared and path in observed for path in role_paths.values())
            and len({observed_map[path] for path in role_paths.values() if path in observed_map})
            == len(role_paths)
            and manifest.get("artifact_profile") == artifact_profile(mode)
        )
        reader_role = role_paths.get("reader_report")
        primary_ok = primary is not None and primary == reader_role and primary in declared and primary in observed
        primary_evidence = (
            f"primary={primary or 'missing-or-unsafe'}; reader-role={reader_role or 'missing-or-unsafe'}"
        )
        primary_result = "pass" if primary_ok else "fail"
        roles_evidence = (
            f"actual={','.join(sorted(role_paths)) or 'none'}; "
            f"required={','.join(sorted(expected_roles)) or 'unknown-mode'}; "
            f"optional=migration_report; "
            f"profile={manifest.get('artifact_profile') or 'missing'}"
        )
        roles_result = "pass" if roles_ok else "fail"
        routing = manifest.get("routing")
        selected = routing.get("selected") if isinstance(routing, dict) else None
        lens = manifest.get("discovery_lens")
        mode_ok = (
            isinstance(mode, str)
            and mode in RUN_TYPES
            and mode == manifest.get("run_type")
            and selected == mode
            and lens in DISCOVERY_LENSES
        )
        mode_evidence = (
            f"task_mode={mode or 'missing'}; run_type={manifest.get('run_type') or 'missing'}; "
            f"routing.selected={selected or 'missing'}; lens={lens or 'missing'}"
        )
        mode_result = "pass" if mode_ok else "fail"
        completion = manifest.get("completion_status")
        completion_ok = completion in COMPLETION_STATUSES
        completion_evidence, completion_result = str(completion or "missing"), ("pass" if completion_ok else "fail")
        schema2_structure = _schema2_manifest_structure(
            manifest, mode=mode, historical_verified=_historical_parent_verified(parent_dir)
        )
    expected_run_id = lineage.get("run_id")
    actual_run_id = manifest.get("run_id")
    declared_observed = (
        f"declared={len(declared)}; observed={len(observed)}; "
        f"missing={','.join(missing) or 'none'}; extra={','.join(extra) or 'none'}"
    )
    rows = (
        ("schema-supported", schema, "pass" if schema in SUPPORTED_PARENT_SCHEMAS else "fail"),
        ("skill-identifier", str(manifest.get("skill") or "missing"), "pass" if manifest.get("skill") == SKILL_ID else "fail"),
        ("run-id-lineage", f"expected={expected_run_id}; actual={actual_run_id}", "pass" if actual_run_id == expected_run_id else "fail"),
        *schema2_structure,
        ("artifact-files-list", f"list[{len(raw_files)}]" if isinstance(raw_files, list) else type(raw_files).__name__, "pass" if list_ok else "fail"),
        ("artifact-files-safe", "all-safe" if safe_ok else "unsafe-or-invalid", "pass" if safe_ok else "fail"),
        ("artifact-files-unique", "unique" if unique_ok else "duplicate-or-invalid", "pass" if unique_ok else "fail"),
        ("declared-vs-observed", declared_observed, "pass" if not missing and not extra else "fail"),
        ("primary-artifact", primary_evidence, primary_result),
        ("artifact-roles", roles_evidence, roles_result),
        ("mode-routing", mode_evidence, mode_result),
        ("completion-status", completion_evidence, completion_result),
    )
    return rows


def _definition_occurrences(
    files: Mapping[str, Path], schema: str, manifest: Mapping[str, object]
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    definitions: dict[str, list[str]] = defaultdict(list)
    occurrences: dict[str, list[str]] = defaultdict(list)
    legacy_headers: dict[str, set[str]] = {
        "01_breadth-ledger.md": {"Branch ID"},
        "02_search-log.md": {"Query ID"},
        "03_evidence-matrix.md": {"Claim ID", "Evidence ID"},
        "06_red-team.md": {"Attack ID"},
        "07_decision-log.md": {"Decision ID"},
    }
    roles_by_file: dict[str, set[str]] = defaultdict(set)
    raw_roles = manifest.get("artifact_roles")
    if isinstance(raw_roles, dict):
        for role, raw_path in raw_roles.items():
            rel = _safe_relpath(raw_path)
            if isinstance(role, str) and rel is not None:
                roles_by_file[rel].add(role)
    for rel, path in sorted(files.items()):
        if path.suffix.lower() != ".md":
            continue
        text = path.read_text(encoding="utf-8")
        for line_number, line in _strip_visible_lines(text):
            for match in PARENT_ID_PATTERN.finditer(line):
                occurrences[match.group(0)].append(f"{rel}:L{line_number}")
        for table in _tables(text):
            if schema == "2.0":
                spec = ID_DEFINITION_SPECS.get(table.marker or "")
                if spec is None:
                    continue
                header, pattern = spec
                allowed_roles = DEFINITION_MARKER_ROLES.get(table.marker or "", frozenset())
                if not (roles_by_file.get(rel, set()) & allowed_roles):
                    continue
                try:
                    column = table.headers.index(header)
                except ValueError:
                    continue
                for row, line_number in zip(table.rows, table.row_lines):
                    value = row[column].strip()
                    if pattern.fullmatch(value):
                        definitions[value].append(f"{rel}:L{line_number}")
            else:
                legacy_name = Path(rel).name
                allowed = legacy_headers.get(legacy_name, set())
                for header in allowed:
                    if header == "Claim ID" and not (
                        _exact_column(table, "Epistemic label") is not None
                        and _exact_column(table, "Atomic claim") is not None
                    ):
                        # In legacy Evidence Records and contradiction tables
                        # this column references a claim. Only Atomic Claims
                        # defines it.
                        continue
                    column = _exact_column(table, header)
                    if column is None:
                        continue
                    for row, line_number in zip(table.rows, table.row_lines):
                        value = row[column].strip()
                        if PARENT_ID_PATTERN.fullmatch(value):
                            definitions[value].append(f"{rel}:L{line_number}")
                if legacy_name == "04_research-map.md":
                    # Schema 1.x had no rom markers, so definition authority is
                    # recovered from a header plus a companion column.  This
                    # distinguishes the defining bottleneck/mechanism tables
                    # from the Missing Primitives and Material/Process tables,
                    # where the same ID column is only a reference.
                    legacy_map_definitions = (
                        ("Bottleneck ID", "Bottleneck"),
                        ("Mechanism ID", "Physical state variable"),
                        ("Interface ID", "Layers joined"),
                    )
                    for id_header, companion_header in legacy_map_definitions:
                        column = _exact_column(table, id_header)
                        companion = _exact_column(table, companion_header)
                        if column is None or companion is None:
                            continue
                        # Atomic Claims, when present, remains the primary
                        # definition source.  The research-map definition is a
                        # fallback for legacy B/M/I IDs absent from that table.
                        preexisting = set(definitions)
                        for row, line_number in zip(table.rows, table.row_lines):
                            value = row[column].strip()
                            if (
                                PARENT_ID_PATTERN.fullmatch(value)
                                and value not in preexisting
                            ):
                                definitions[value].append(
                                    f"{rel}:L{line_number}"
                                )
        if schema.startswith("1.") and Path(rel).name == "05_candidate-portfolio.md":
            for line_number, line in _strip_visible_lines(text):
                match = re.match(r"^\s*-\s*Candidate ID:\s*(C-[LMH]\d{2}|C-\d{3})\s*$", line)
                if match:
                    definitions[match.group(1)].append(f"{rel}:L{line_number}")
    return definitions, occurrences


def _namespace(identifier: str) -> str:
    prefix = identifier.split("-", 1)[0]
    return {
        "ART": "artifact",
        "BR": "branch",
        "CAP": "capability",
        "CTX": "context",
        "DR": "deep-read-request",
        "CL": "claim",
        "B": "claim",
        "M": "claim",
        "S": "claim",
        "C": "candidate",
        "E": "evidence",
        "Q": "query",
        "A": "attack",
        "D": "decision",
        "I": "interface",
        "GS": "gray-space",
        "H": "hypothesis",
        "G": "gap",
        "F": "finding",
        "R": "repair",
    }.get(prefix, "unknown")


def _id_projection(
    files: Mapping[str, Path], schema: str, manifest: Mapping[str, object]
) -> tuple[tuple[str, ...], ...]:
    definitions, occurrences = _definition_occurrences(files, schema, manifest)
    rows: list[tuple[str, ...]] = []
    for identifier in sorted(set(definitions) | set(occurrences)):
        defs = list(definitions.get(identifier, []))
        refs = list(occurrences.get(identifier, []))
        for location in defs:
            if location in refs:
                refs.remove(location)
        if len(defs) > 1:
            status = "duplicate-definition"
        elif not defs:
            status = "dangling-reference"
        elif not refs:
            status = "unreferenced-definition"
        else:
            status = "closed"
        rows.append(
            (
                identifier,
                _namespace(identifier),
                "; ".join(defs) or "unavailable",
                "; ".join(refs) or "unavailable",
                status,
            )
        )
    if not rows:
        rows.append(("unavailable", "unavailable", "unavailable", "unavailable", "no-identifiers-observed"))
    return tuple(rows)


def _normalize_source(value: str) -> str:
    doi = re.search(
        r"(?:(?:https?://(?:dx\.)?doi\.org/)|(?:doi:\s*))?"
        r"(10\.\d{4,9}/[^\s)>]+)", value, re.IGNORECASE
    )
    if doi:
        return "https://doi.org/" + doi.group(1).rstrip(".,;]").lower()
    match = re.search(r"https?://[^\s)>]+", value, re.IGNORECASE)
    raw = (match.group(0) if match else value.strip()).rstrip(".,;]")
    parsed = urlsplit(raw)
    if parsed.scheme and parsed.netloc:
        return urlunsplit(
            (parsed.scheme.lower(), parsed.netloc.lower(), parsed.path, parsed.query, parsed.fragment)
        )
    return raw


def _reference_lines(text: str) -> list[str]:
    lines = text.splitlines()
    marker_index = next(
        (index for index, line in enumerate(lines) if re.fullmatch(r"<!--\s*rom-section:\s*references\s*-->", line.strip(), re.IGNORECASE)),
        None,
    )
    if marker_index is not None:
        result: list[str] = []
        for line in lines[marker_index + 1 :]:
            if MARKER_PATTERN.fullmatch(line.strip()):
                break
            result.append(line)
        return [line for _, line in _strip_visible_lines("\n".join(result))]
    for index, line in enumerate(lines):
        heading = re.match(r"^(#{1,3})\s+(?:参考文献|References)(?:\s|$|（|\()", line.strip(), re.IGNORECASE)
        if not heading:
            continue
        level = len(heading.group(1))
        result = []
        for candidate in lines[index + 1 :]:
            next_heading = re.match(r"^(#{1,6})\s+", candidate.strip())
            if next_heading and len(next_heading.group(1)) <= level:
                break
            result.append(candidate)
        return [line for _, line in _strip_visible_lines("\n".join(result))]
    return []


def _body_cited_numbers(text: str) -> set[int]:
    lines = text.splitlines()
    start = next(
        (
            index
            for index, line in enumerate(lines)
            if re.fullmatch(
                r"<!--\s*rom-section:\s*references\s*-->",
                line.strip(),
                re.IGNORECASE,
            )
            or re.match(
                r"^#{1,3}\s+(?:参考文献|References)(?:\s|$|（|\()",
                line.strip(),
                re.IGNORECASE,
            )
        ),
        len(lines),
    )
    visible = "\n".join(
        line for _, line in _strip_visible_lines("\n".join(lines[:start]))
    )
    cited: set[int] = set()
    for match in re.finditer(r"\[([0-9][0-9,;\s\-–—]*)\]", visible):
        for token in re.split(r"[,;]", match.group(1)):
            token = token.strip()
            range_match = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", token)
            if range_match:
                first, last = map(int, range_match.groups())
                if first <= last and last - first <= 1000:
                    cited.update(range(first, last + 1))
            elif token.isdigit():
                cited.add(int(token))
    return cited


def _reader_references_raw(text: str) -> tuple[list[tuple[int, str]], set[int]]:
    entries: list[tuple[int, str]] = []
    seen: set[int] = set()
    duplicates: set[int] = set()
    for line in _reference_lines(text):
        match = re.match(r"^\s*(?:\[(\d+)\]|(\d+)\.)\s+", line)
        if not match:
            continue
        number = int(match.group(1) or match.group(2))
        if number in seen:
            duplicates.add(number)
        seen.add(number)
        url_match = re.search(r"https?://[^\s)>]+", line, re.IGNORECASE)
        if url_match is None:
            doi_match = re.search(r"(?:doi:\s*)?(10\.\d{4,9}/[^\s)>]+)", line, re.IGNORECASE)
            url = f"https://doi.org/{doi_match.group(1)}" if doi_match else "unavailable"
        else:
            url = _normalize_source(url_match.group(0))
        entries.append((number, url))
    return entries, duplicates


def _evidence_records(path: Path | None) -> list[tuple[str, str, str | None]]:
    if path is None or not path.is_file():
        return []
    result: list[tuple[str, str, str | None]] = []
    for table in _tables(path.read_text(encoding="utf-8")):
        id_col = _exact_column(table, "Evidence ID")
        url_col = _exact_column(table, "DOI or stable URL")
        if url_col is None:
            url_col = _exact_column(table, "DOI or URL")
        if id_col is None or url_col is None:
            continue
        ref_col = _exact_column(table, "Reader ref")
        for row in table.rows:
            result.append(
                (
                    row[id_col].strip(),
                    _normalize_source(row[url_col]),
                    row[ref_col].strip() if ref_col is not None else None,
                )
            )
    return result


def _citation_projection(
    parent_dir: Path,
    manifest: Mapping[str, object],
    schema: str,
    observed: Mapping[str, Path] | None = None,
) -> tuple[tuple[str, ...], ...]:
    if schema == "1.0":
        return (("unavailable", "unavailable", "unavailable", "unavailable", "not-applicable", "not-applicable-no-declared-reader"),)
    if schema == "2.0":
        roles = manifest.get("artifact_roles")
        reader_rel = _safe_relpath(roles.get("reader_report")) if isinstance(roles, dict) else None
        evidence_rel = _safe_relpath(roles.get("evidence_matrix")) if isinstance(roles, dict) else None
    elif schema == "1.1":
        reader_rel = _legacy_reader_rel(manifest, schema)
        evidence_rel = "03_evidence-matrix.md"
    else:
        reader_rel = _safe_relpath(manifest.get("primary_artifact"))
        evidence_rel = "03_evidence-matrix.md"
    safe_observed = dict(observed) if observed is not None else _observed_files(parent_dir)
    reader_path = safe_observed.get(reader_rel) if reader_rel is not None else None
    if reader_path is None:
        return (("unavailable", "unavailable", "unavailable", "unavailable", "no", "missing-reader-artifact"),)
    evidence_path = safe_observed.get(evidence_rel) if evidence_rel is not None else None
    reader_text = reader_path.read_text(encoding="utf-8")
    references, duplicates = _reader_references_raw(reader_text)
    body_cited = _body_cited_numbers(reader_text)
    records = _evidence_records(evidence_path)
    if not references:
        return (("unavailable", "unavailable", "unavailable", "unavailable", "no", "no-reader-references"),)
    rows: list[tuple[str, ...]] = []
    for number, report_url in references:
        if number in duplicates:
            matches: list[tuple[str, str, str | None]] = []
            status = "duplicate-reader-number"
        elif report_url == "unavailable":
            matches = []
            status = "missing-report-url"
        elif evidence_path is None:
            matches = []
            status = "missing-evidence-matrix"
        elif schema == "2.0":
            matches = [record for record in records if record[2] is not None and re.fullmatch(r"\s*\[?%d\]?\s*" % number, record[2])]
            if not matches:
                status = "no-evidence-record"
            elif len(matches) > 1:
                status = "ambiguous-evidence-record"
            elif matches[0][1] != report_url:
                status = "url-mismatch"
            else:
                status = "match"
        else:
            matches = [record for record in records if record[1] == report_url]
            if not matches:
                status = "no-evidence-record"
            elif len(matches) > 1:
                status = "ambiguous-evidence-record"
            else:
                status = "match"
        if status == "match" and number not in body_cited:
            status = "reference-unused"
        evidence_ids = ",".join(sorted(record[0] for record in matches)) or "unavailable"
        evidence_urls = "; ".join(sorted({record[1] for record in matches})) or "unavailable"
        rows.append(
            (
                f"[{number}]",
                report_url,
                evidence_ids,
                evidence_urls,
                "yes" if status == "match" else "no",
                status,
            )
        )
    reference_numbers = {number for number, _ in references}
    for number in sorted(body_cited - reference_numbers):
        rows.append(
            (
                f"[{number}]",
                "unavailable",
                "unavailable",
                "unavailable",
                "no",
                "body-reference-missing",
            )
        )
    return tuple(sorted(rows, key=lambda row: int(row[0].strip("[]")) if row[0].strip("[]").isdigit() else 10**9))


def inspect_parent_for_audit(
    parent_dir: Path,
    manifest: Mapping[str, object],
    lineage: Mapping[str, object],
) -> ParentAuditFacts:
    """Recompute the exact local parent facts a run-audit must project."""

    schema = str(parse_schema_version(manifest.get("schema_version")))
    observed = _observed_files(parent_dir)
    run_id = str(manifest.get("run_id") or "")
    id_projection = _id_projection(observed, schema, manifest)
    return ParentAuditFacts(
        schema_version=schema,
        run_id=run_id,
        artifact_projection=_artifact_projection(parent_dir, manifest, lineage, schema, observed),
        manifest_projection=_manifest_projection(manifest, lineage, parent_dir, schema, observed),
        id_projection=id_projection,
        citation_projection=_citation_projection(parent_dir, manifest, schema, observed),
        observed_ids=frozenset(
            row[0] for row in id_projection if PARENT_ID_PATTERN.fullmatch(row[0])
        ),
    )


def _cli() -> int:
    parser = argparse.ArgumentParser(
        description="Print deterministic parent projections for a run-audit child."
    )
    parser.add_argument("parent_run", type=Path)
    parser.add_argument("--lineage-run-id")
    args = parser.parse_args()
    parent = args.parent_run.expanduser().resolve()
    try:
        manifest_path = resolve_contained_file(
            parent, Path("run-manifest.json"), label="parent run manifest"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("parent manifest must be a JSON object")
        expected_run_id = args.lineage_run_id or manifest.get("run_id")
        facts = inspect_parent_for_audit(
            parent, manifest, {"run_id": expected_run_id}
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    payload = {
        "schema_version": facts.schema_version,
        "run_id": facts.run_id,
        "artifact_projection": facts.artifact_projection,
        "manifest_projection": facts.manifest_projection,
        "id_projection": facts.id_projection,
        "citation_projection": facts.citation_projection,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_cli())
