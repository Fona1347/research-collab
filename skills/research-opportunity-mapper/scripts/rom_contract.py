#!/usr/bin/env python3
"""Shared schema-2 contract helpers for research-opportunity-mapper scripts.

This module deliberately uses only the Python standard library so the skill's
initialization, migration, and validation entry points can share one deterministic
contract without adding a runtime dependency.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence


SCHEMA_VERSION = "2.0"
SKILL_ID = "research-opportunity-mapper"
SKILL_VERSION = "2.2.0"
VALIDATOR_VERSION = "2.2.0"

WORKFLOW_CONTRACTS_BY_MODE: Mapping[str, tuple[str, ...]] = {
    "landscape": (
        "deep-reading-handoff-v2",
        "opportunity-gates-v2",
        "coverage-tension-v2",
        "route-fast-pilot-v2",
    ),
    "focus": (
        "deep-reading-handoff-v2",
        "opportunity-gates-v2",
        "coverage-tension-v2",
        "route-fast-pilot-v2",
    ),
    "evidence-audit": (
        "deep-reading-handoff-v2",
        "coverage-tension-v2",
    ),
    "run-audit": (),
}

RUN_TYPES = ("landscape", "focus", "evidence-audit", "run-audit")
DISCOVERY_LENSES = ("frontier-led", "gray-space-led", "balanced")
DOMAIN_LENSES = (
    "generic-physical-engineering",
    "materials-ferroelectric",
    "multiphysics-modeling",
    "semiconductor-device",
    "integrated-circuit",
    "neuromorphic-system",
    "wave-metasurface",
    "custom",
)

CUSTOM_DOMAIN_LENS_SLOT_ALIASES: Mapping[str, tuple[str, ...]] = {
    "decision object": ("decision object", "决策对象"),
    "state variables": ("state variables", "状态变量"),
    "persistent bottleneck": ("persistent bottleneck", "持久性瓶颈"),
    "causal chain": ("causal chain", "因果链"),
    "alternative explanations": (
        "alternative explanations",
        "alternatives/confounds",
        "alternative explanations/confounds",
        "替代解释",
        "替代解释与混杂因素",
    ),
    "budgets and constraints": (
        "budgets and constraints",
        "budgets/constraints",
        "预算与约束",
    ),
    "baseline ladder": ("baseline ladder", "基线阶梯"),
    "validation hierarchy": ("validation hierarchy", "验证层级"),
    "capability interface": ("capability interface", "能力接口"),
    "decisive test": ("decisive test", "决定性实验", "决定性测试"),
}
REQUESTED_MODES = ("auto",) + RUN_TYPES
ROUTING_CONFIDENCE = ("low", "moderate", "high")
COMPLETION_STATUSES = (
    "initialized",
    "in-progress",
    "ready-for-validation",
    "complete",
    "migrated-needs-review",
    "superseded",
)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"

MODE_OVERRIDE_INDICES: Mapping[str, frozenset[int]] = {
    "landscape": frozenset(),
    "focus": frozenset({1, 4, 5}),
    "evidence-audit": frozenset({0, 1, 4, 5}),
    "run-audit": frozenset({0, 1, 2, 3, 4, 5}),
}

MODE_ROLES: Mapping[str, Mapping[int, str]] = {
    "landscape": {
        0: "intake",
        1: "breadth_ledger",
        2: "search_log",
        3: "evidence_matrix",
        4: "research_map",
        5: "candidate_portfolio",
        6: "red_team",
        7: "decision_log",
    },
    "focus": {
        0: "intake",
        1: "focus_scope",
        2: "search_log",
        3: "evidence_matrix",
        4: "claim_mechanism_map",
        5: "route_protocol",
        6: "red_team",
        7: "decision_log",
    },
    "evidence-audit": {
        0: "audit_scope",
        1: "claim_register",
        2: "search_log",
        3: "evidence_matrix",
        4: "confidence_assessment",
        5: "gap_plan",
        6: "red_team",
        7: "decision_log",
    },
    "run-audit": {
        0: "audit_scope",
        1: "artifact_inventory",
        2: "traceability_audit",
        3: "evidence_audit",
        4: "reasoning_audit",
        5: "route_verdicts",
        6: "red_team",
        7: "decision_log",
    },
}

REPORT_PREFIX: Mapping[str, str] = {
    "landscape": "map_report",
    "focus": "focus_report",
    "evidence-audit": "evidence_audit_report",
    "run-audit": "run_audit_report",
}

LEGACY_REQUIRED_ARTIFACTS = tuple(f"{index:02d}_{name}.md" for index, name in (
    (0, "intake"),
    (1, "breadth-ledger"),
    (2, "search-log"),
    (3, "evidence-matrix"),
    (4, "research-map"),
    (5, "candidate-portfolio"),
    (6, "red-team"),
    (7, "decision-log"),
))

SCHEMA_PATTERN = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)$")
TEMPLATE_TOKEN_PATTERN = re.compile(r"\{\{[A-Z][A-Z0-9_]*\}\}")
NUMBERED_TEMPLATE_PATTERN = re.compile(r"^(\d{2})_.+\.md$")
ROLE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]*$")
BRANCH_ID_PATTERN = re.compile(r"^BR-\d{3}$")
FOCUS_TARGET_ID_PATTERN = re.compile(r"^(?:BR|C|I)-\d{3}$")
CLAIM_ID_PATTERN = re.compile(r"^(?:B|M|S|CL)-\d{3}$")
ROUTE_ID_PATTERN = re.compile(r"^C-\d{3}$")
EVIDENCE_ID_PATTERN = re.compile(r"^E-\d{3}$")
CAPABILITY_ID_PATTERN = re.compile(r"^CAP-\d{3}$")
ANY_ID_PATTERN = re.compile(
    r"\b(?:ART|BR|CAP|CTX|CL|DR|GS|B|M|S|C|E|Q|A|D|I|H|G|F|R)-\d{3}\b"
)
ROM_MARKER_PATTERN = re.compile(
    r"^<!--\s*rom-(?:section|table):\s*([a-z0-9-]+)\s*-->$",
    re.IGNORECASE,
)
ID_DEFINITION_SPECS: Mapping[str, tuple[str, re.Pattern[str]]] = {
    "atomic-claims": ("Claim ID", CLAIM_ID_PATTERN),
    "breadth-branches": ("Branch ID", BRANCH_ID_PATTERN),
    "candidate-routes": ("Candidate ID", ROUTE_ID_PATTERN),
    "rejected-routes": ("Candidate ID", ROUTE_ID_PATTERN),
    "local-alternatives": ("Alternative ID", ROUTE_ID_PATTERN),
    "evidence-records": ("Evidence ID", EVIDENCE_ID_PATTERN),
    "deep-reading-handoff": ("Deep-read request ID", re.compile(r"^DR-\d{3}$")),
    "search-queries": ("Query ID", re.compile(r"^Q-\d{3}$")),
    "capability-passport": ("Capability ID", CAPABILITY_ID_PATTERN),
    "attack-register": ("Attack ID", re.compile(r"^A-\d{3}$")),
    "decisions": ("Decision ID", re.compile(r"^D-\d{3}$")),
    "open-interfaces": ("Interface ID", re.compile(r"^I-\d{3}$")),
    "gray-space-mismatch": ("Mismatch ID", re.compile(r"^GS-\d{3}$")),
    "competing-hypotheses": ("Hypothesis ID", re.compile(r"^H-\d{3}$")),
    "evidence-gaps": ("Gap ID", re.compile(r"^G-\d{3}$")),
    "artifact-inventory": ("Artifact ID", re.compile(r"^ART-\d{3}$")),
    "dangling-references": ("Finding ID", re.compile(r"^F-\d{3}$")),
    "confidence-violations": ("Finding ID", re.compile(r"^F-\d{3}$")),
    "remediation-plan": ("Repair ID", re.compile(r"^R-\d{3}$")),
}

# A schema-2 marker is authoritative only in the artifact role that owns that
# table.  Keeping this registry beside ``ID_DEFINITION_SPECS`` gives every
# caller one shared role-aware definition contract instead of letting a marker
# copied into a reader report (or another working artifact) mint inheritable
# IDs.
ID_DEFINITION_MARKER_ROLES: Mapping[str, frozenset[str]] = {
    "atomic-claims": frozenset({"evidence_matrix"}),
    "breadth-branches": frozenset({"breadth_ledger"}),
    "candidate-routes": frozenset({"candidate_portfolio"}),
    "rejected-routes": frozenset({"candidate_portfolio"}),
    "local-alternatives": frozenset({"focus_scope"}),
    "evidence-records": frozenset({"evidence_matrix"}),
    "deep-reading-handoff": frozenset({"evidence_matrix"}),
    "search-queries": frozenset({"search_log"}),
    "capability-passport": frozenset({"intake"}),
    "attack-register": frozenset({"red_team"}),
    "decisions": frozenset({"decision_log"}),
    "open-interfaces": frozenset({"research_map"}),
    "gray-space-mismatch": frozenset({"breadth_ledger"}),
    "competing-hypotheses": frozenset({"claim_mechanism_map"}),
    "evidence-gaps": frozenset({"gap_plan"}),
    "artifact-inventory": frozenset({"artifact_inventory"}),
    "dangling-references": frozenset({"traceability_audit"}),
    "confidence-violations": frozenset({"evidence_audit"}),
    "remediation-plan": frozenset({"route_verdicts"}),
}


class ContractError(ValueError):
    """Raised when an input violates the persisted-run contract."""

def _strip_unicode_format_controls(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    return "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Cf"
    )


def _custom_value_key(value: str) -> str:
    """Normalize a custom-lens slot value for placeholder/duplication checks."""

    normalized = _strip_unicode_format_controls(value)
    return re.sub(r"[\W_]+", " ", normalized, flags=re.UNICODE).strip().casefold()

def _custom_placeholder_key(value: str) -> str:
    """Squash punctuation only for exact placeholder-vocabulary matching."""

    normalized = _strip_unicode_format_controls(value)
    return re.sub(r"[\W_]+", "", normalized, flags=re.UNICODE).casefold()


def parse_custom_domain_lens_notes(value: object) -> dict[str, str]:
    """Parse one substantive value for each of the ten Common Lens slots."""

    if not isinstance(value, str) or not value.strip():
        raise ContractError(
            "custom domain_lens_notes must define all ten labeled Common Lens "
            "Interface slots"
        )
    notes = _strip_unicode_format_controls(value.strip())
    alias_to_slot = {
        unicodedata.normalize("NFKC", alias).casefold(): slot
        for slot, aliases in CUSTOM_DOMAIN_LENS_SLOT_ALIASES.items()
        for alias in aliases
    }
    labels = "|".join(
        re.escape(alias)
        for alias in sorted(alias_to_slot, key=len, reverse=True)
    )
    marker = re.compile(
        rf"(?:^|[;；\n])\s*(?:[-*]|\d+[.)])?\s*"
        rf"(?P<label>{labels})\s*[:：]\s*",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = list(marker.finditer(notes))
    unlabeled_prefix = notes[:matches[0].start()] if matches else notes
    if _custom_value_key(unlabeled_prefix):
        raise ContractError(
            "custom domain_lens_notes contains substantive text before the "
            "first labeled Common Lens Interface slot"
        )
    values: dict[str, list[str]] = {
        slot: [] for slot in CUSTOM_DOMAIN_LENS_SLOT_ALIASES
    }
    for index, match in enumerate(matches):
        slot = alias_to_slot[match.group("label").casefold()]
        end = matches[index + 1].start() if index + 1 < len(matches) else len(notes)
        raw_value = notes[match.end():end].strip(" \t\r\n;；")
        values[slot].append(_strip_unicode_format_controls(raw_value).strip())

    placeholder_keys = {
        "none", "n a", "na", "unknown", "tbd", "not supplied",
        "not applicable", "same as above", "same as previous", "see above",
        "as above", "ditto", "无", "未知", "待定", "未提供", "不适用",
        "同上", "见上", "如上", "同前", "见前",
    }
    label_keys = {
        _custom_value_key(alias)
        for aliases in CUSTOM_DOMAIN_LENS_SLOT_ALIASES.values()
        for alias in aliases
    }
    placeholder_only = re.compile(
        r"^(?:none|na|unknown|tbd|notsupplied|notapplicable|"
        r"sameasabove|sameasprevious|seeabove|asabove|ditto|"
        r"(?:todo|tbd|tbc|fixme|placeholder)(?:later|content|entry|item|text|here)?|"
        r"tobe(?:determined|filled|completed)|notyetdetermined|"
        r"pending(?:confirmation)?|informationunavailable|unavailable|"
        r"notrelevant|nodatayet|"
        r"(?:referto|see)(?:the)?(?:previous|preceding|above)(?:entry|section)?|"
        r"无|未知|待定|未提供|不适用|同上|见上|如上|同前|见前|"
        r"(?:待补|待完善|待填写|占位|待确认|暂缺)(?:内容|信息|条目|文本|此处)?|"
        r"暂无数据|信息不可用|请见上文|见上文|参见上文|见前文|不相关"
        r")(?:(?:\d+)|(?:第\d+(?:项|条|个)?))?$",
        re.IGNORECASE,
    )
    generic_label_tail = {
        "value", "values", "detail", "details", "description", "information",
        "content", "entry", "text", "data", "here",
        "值", "详情", "描述", "信息", "内容", "条目", "文本", "数据", "此处",
    }

    def label_echo_placeholder(key: str) -> bool:
        for label_key in label_keys:
            if not key.startswith(label_key + " "):
                continue
            tail_tokens = key[len(label_key):].strip().split()
            meaningful = [
                token
                for token in tail_tokens
                if token not in generic_label_tail and not token.isdigit()
            ]
            if len(meaningful) < 2:
                return True
        return False


    def substantive(text: str) -> bool:
        compact = text.strip()
        key = _custom_value_key(compact)
        return (
            len(compact) >= 3
            and key not in placeholder_keys
            and key not in label_keys
            and placeholder_only.fullmatch(_custom_placeholder_key(compact)) is None
            and not label_echo_placeholder(key)
            and re.search(r"[A-Za-z0-9\u4e00-\u9fff]", compact) is not None
        )

    missing = [
        slot
        for slot, slot_values in values.items()
        if len(slot_values) != 1 or not substantive(slot_values[0])
    ]
    duplicates = [
        slot for slot, slot_values in values.items() if len(slot_values) > 1
    ]
    normalized_slot_values = {
        slot: _custom_value_key(slot_values[0])
        for slot, slot_values in values.items()
        if len(slot_values) == 1 and substantive(slot_values[0])
    }
    value_counts: dict[str, int] = {}
    for key in normalized_slot_values.values():
        value_counts[key] = value_counts.get(key, 0) + 1
    repeated_values = sorted(
        key for key, count in value_counts.items() if count > 1
    )
    if missing or duplicates or repeated_values:
        details: list[str] = []
        if missing:
            details.append("missing or empty: " + ", ".join(missing))
        if duplicates:
            details.append("duplicated labels: " + ", ".join(duplicates))
        if repeated_values:
            details.append(
                "repeated cross-slot values: " + ", ".join(repeated_values)
            )
        raise ContractError(
            "custom domain_lens_notes must define each labeled Common Lens "
            "Interface slot exactly once as 'Slot: substantive value'; "
            + "; ".join(details)
        )
    return {
        slot: slot_values[0]
        for slot, slot_values in values.items()
    }


def validate_custom_domain_lens_notes(value: object) -> str:
    """Return normalized notes only when all ten labeled interface slots exist."""

    parsed = parse_custom_domain_lens_notes(value)
    return "\n".join(
        f"{slot.title()}: {parsed[slot]}"
        for slot in CUSTOM_DOMAIN_LENS_SLOT_ALIASES
    )


@dataclass(frozen=True, order=True)
class SchemaVersion:
    major: int
    minor: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}"


@dataclass(frozen=True)
class ArtifactTemplate:
    index: int | None
    role: str
    source: Path
    output_name: str | None = None


@dataclass(frozen=True)
class ParentSnapshot:
    run_id: str
    relation: str
    workspace_relpath: str
    source_manifest_sha256: str
    source_artifact_sha256: Mapping[str, str]
    available_ids: frozenset[str]


def parse_schema_version(value: object) -> SchemaVersion:
    if not isinstance(value, str):
        raise ContractError("schema_version must be a string in MAJOR.MINOR form")
    match = SCHEMA_PATTERN.fullmatch(value)
    if not match:
        raise ContractError(f"Invalid schema_version: {value!r}")
    return SchemaVersion(int(match.group(1)), int(match.group(2)))


def require_supported_legacy_version(value: object) -> SchemaVersion:
    version = parse_schema_version(value)
    if version not in {SchemaVersion(1, 0), SchemaVersion(1, 1), SchemaVersion(1, 2)}:
        raise ContractError(
            f"upgrade_run supports only schema 1.0, 1.1, and 1.2; got {version}"
        )
    return version


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w.-]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value or "research-map"


def parse_iso_date(value: str, *, label: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ContractError(f"{label} must use YYYY-MM-DD: {value!r}") from exc


def parse_iso_datetime(value: str, *, label: str = "created-at") -> datetime:
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ContractError(f"{label} must be an ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise ContractError(f"{label} must include a UTC offset or Z suffix")
    return parsed


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def language_bucket(language: str) -> str:
    normalized = language.strip().lower()
    if normalized.startswith("zh"):
        return "zh-CN"
    if normalized.startswith("en"):
        return "en"
    raise ContractError(
        f"Unsupported template language {language!r}; use a zh-* or en-* language tag"
    )


def parse_evidence_window(value: str | None, *, as_of: date) -> dict[str, object]:
    end_was_as_of_year = False
    if value is None or not value.strip():
        start = date(max(1, as_of.year - 5), 1, 1)
        end = as_of
    else:
        raw = value.strip()
        separator = ".." if ".." in raw else ":" if ":" in raw else None
        if separator is None:
            start = _parse_window_endpoint(raw, label="evidence-window start", end=False)
            end = as_of
        else:
            start_raw, end_raw = raw.split(separator, 1)
            start = (
                _parse_window_endpoint(start_raw, label="evidence-window start", end=False)
                if start_raw.strip()
                else date(max(1, as_of.year - 5), 1, 1)
            )
            end = (
                _parse_window_endpoint(end_raw, label="evidence-window end", end=True)
                if end_raw.strip()
                else as_of
            )
            end_was_as_of_year = bool(
                re.fullmatch(r"\d{4}", end_raw.strip())
                and int(end_raw.strip()) == as_of.year
            )
    if end > as_of and end_was_as_of_year:
        end = as_of
    if start > end:
        raise ContractError("evidence-window start must not be after its end")
    if end > as_of:
        raise ContractError("evidence-window end must not be after as-of-date")
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "as_of": as_of.isoformat(),
        "canonical_pre_window_allowed": True,
    }


def _parse_window_endpoint(value: str, *, label: str, end: bool) -> date:
    value = value.strip()
    if re.fullmatch(r"\d{4}", value):
        year = int(value)
        return date(year, 12 if end else 1, 31 if end else 1)
    return parse_iso_date(value, label=label)


def report_filename(mode: str, short_task_name: str, run_date: date) -> str:
    try:
        prefix = REPORT_PREFIX[mode]
    except KeyError as exc:
        raise ContractError(f"Unsupported run type: {mode!r}") from exc
    return f"{prefix}_{short_task_name}_{run_date.isoformat()}.md"


def artifact_profile(mode: str) -> str:
    if mode not in RUN_TYPES:
        raise ContractError(f"Unsupported run type: {mode!r}")
    return f"{mode}-v2"


def resolve_template_plan(
    template_dir: Path,
    *,
    mode: str,
    language: str,
) -> tuple[list[ArtifactTemplate], Path]:
    """Resolve common templates, mode overrides, and the localized report.

    Flat numbered templates are the common/landscape base. A mode subdirectory
    replaces the required numbered positions. This permits semantic filenames in
    mode directories without duplicating unchanged templates.
    """

    if mode not in RUN_TYPES:
        raise ContractError(f"Unsupported run type: {mode!r}")
    if not template_dir.is_dir():
        raise ContractError(f"Template directory not found: {template_dir}")

    common = _numbered_templates(template_dir)
    missing_common = [index for index in range(8) if index not in common]
    if missing_common:
        rendered = ", ".join(f"{index:02d}" for index in missing_common)
        raise ContractError(f"Missing common numbered template(s): {rendered}")

    selected = dict(common)
    required_overrides = MODE_OVERRIDE_INDICES[mode]
    if required_overrides:
        override_dir = template_dir / mode
        if not override_dir.is_dir():
            raise ContractError(f"Mode template directory not found: {override_dir}")
        overrides = _numbered_templates(override_dir)
        missing = sorted(required_overrides - overrides.keys())
        unexpected = sorted(overrides.keys() - required_overrides)
        if missing:
            rendered = ", ".join(f"{index:02d}" for index in missing)
            raise ContractError(f"Missing {mode} override template(s): {rendered}")
        if unexpected:
            rendered = ", ".join(f"{index:02d}" for index in unexpected)
            raise ContractError(f"Unexpected {mode} override template(s): {rendered}")
        selected.update(overrides)

    entries = [
        ArtifactTemplate(
            index=index,
            role=MODE_ROLES[mode][index],
            source=selected[index],
            output_name=selected[index].name,
        )
        for index in range(8)
    ]

    bucket = language_bucket(language)
    report = template_dir / "reports" / bucket / f"{mode}.md"
    if not report.is_file() and mode == "landscape" and bucket == "zh-CN":
        # Transitional compatibility with the pre-v2 template tree. Once the
        # localized report tree exists it is always preferred.
        legacy_report = template_dir / "map_report.md"
        if legacy_report.is_file():
            report = legacy_report
    if not report.is_file():
        raise ContractError(f"Localized report template not found: {report}")
    return entries, report


def _numbered_templates(directory: Path) -> dict[int, Path]:
    result: dict[int, Path] = {}
    for path in sorted(directory.glob("[0-9][0-9]_*.md")):
        match = NUMBERED_TEMPLATE_PATTERN.fullmatch(path.name)
        if not match:
            continue
        index = int(match.group(1))
        if index in result:
            raise ContractError(
                f"Multiple templates use numbered position {index:02d} in {directory}"
            )
        result[index] = path
    return result


def render_template(source: Path, replacements: Mapping[str, str]) -> str:
    try:
        content = source.read_text(encoding="utf-8")
    except OSError as exc:
        raise ContractError(f"Cannot read template {source}: {exc}") from exc
    for token, value in replacements.items():
        content = content.replace(token, value)
    unresolved = sorted(set(TEMPLATE_TOKEN_PATTERN.findall(content)))
    if unresolved:
        raise ContractError(
            f"Template {source} contains unresolved token(s): {', '.join(unresolved)}"
        )
    return content


def load_json_object(path: Path, *, label: str) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ContractError(f"Cannot read {label} {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ContractError(f"Invalid JSON in {label} {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{label} must contain a JSON object: {path}")
    return value


def load_run_manifest(run_dir: Path) -> tuple[Path, dict[str, object]]:
    resolved = run_dir.expanduser().resolve()
    if not resolved.is_dir():
        raise ContractError(f"Run directory not found: {resolved}")
    try:
        manifest_path = resolve_contained_file(
            resolved, Path("run-manifest.json"), label="run manifest"
        )
    except ContractError as exc:
        raise ContractError(f"Missing or unsafe run-manifest.json in {resolved}: {exc}") from exc
    manifest = load_json_object(manifest_path, label="run manifest")
    if manifest.get("skill") != SKILL_ID:
        raise ContractError(f"Unexpected or missing skill identifier in {manifest_path}")
    return manifest_path, manifest


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ContractError(f"Cannot hash {path}: {exc}") from exc
    return digest.hexdigest()


def workspace_relative(
    path: Path,
    workspace_root: Path,
    *,
    must_exist: bool = True,
    label: str = "path",
) -> str:
    root = workspace_root.expanduser().resolve()
    candidate = path.expanduser().resolve()
    if must_exist and not candidate.exists():
        raise ContractError(f"{label} not found: {candidate}")
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ContractError(f"{label} must stay inside workspace root {root}: {candidate}") from exc
    if not relative.parts:
        raise ContractError(f"{label} cannot be the workspace root itself")
    return relative.as_posix()


def safe_manifest_relpath(value: object, *, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{label} must be a non-empty relative path")
    if value != value.strip():
        raise ContractError(f"Unsafe {label}: {value!r}")
    segments = value.replace("\\", "/").split("/")
    if any(segment in {"", ".", ".."} or ":" in segment for segment in segments):
        raise ContractError(f"Unsafe {label}: {value!r}")
    candidate = Path(value)
    if (
        candidate.is_absolute()
        or bool(candidate.drive)
        or bool(candidate.root)
        or bool(candidate.anchor)
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise ContractError(f"Unsafe {label}: {value!r}")
    return candidate


def resolve_contained_file(root: Path, relative: Path, *, label: str) -> Path:
    """Resolve an existing file without permitting a symlink/junction escape."""

    resolved_root = root.expanduser().resolve(strict=True)
    candidate = relative if relative.is_absolute() else resolved_root / relative
    try:
        resolved = candidate.expanduser().resolve(strict=True)
        resolved.relative_to(resolved_root)
    except (OSError, RuntimeError, ValueError) as exc:
        raise ContractError(
            f"{label} must resolve to a file inside {resolved_root}: {candidate}"
        ) from exc
    if not resolved.is_file():
        raise ContractError(f"{label} is not a file: {candidate}")
    return resolved


def parent_relation(mode: str) -> str:
    return {
        "landscape": "extends-landscape",
        "focus": "focuses-branch",
        "evidence-audit": "supplements-evidence",
        "run-audit": "audits-run",
    }[mode]


def _artifact_texts_by_declared_role(
    manifest: Mapping[str, object],
    texts_by_relpath: Mapping[str, str],
) -> dict[str, str]:
    """Project readable artifacts onto their manifest-declared schema-2 roles.

    Invalid or unresolved role entries are deliberately omitted here.  A
    run-audit can snapshot a malformed parent, so manifest-shape findings are
    left to validation/audit while malformed entries receive no authority to
    define inheritable IDs.
    """

    raw_roles = manifest.get("artifact_roles")
    if not isinstance(raw_roles, dict):
        return {}
    result: dict[str, str] = {}
    for role, raw_path in raw_roles.items():
        if not isinstance(role, str) or not ROLE_PATTERN.fullmatch(role):
            continue
        try:
            relpath = safe_manifest_relpath(
                raw_path, label=f"parent artifact role {role!r}"
            ).as_posix()
        except ContractError:
            continue
        text = texts_by_relpath.get(relpath)
        if text is not None:
            result[role] = text
    return result


def snapshot_parent_run(
    parent_run: Path,
    *,
    workspace_root: Path,
    relation: str,
) -> ParentSnapshot:
    parent_dir = parent_run.expanduser().resolve()
    manifest_path, manifest = load_run_manifest(parent_dir)
    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        raise ContractError(f"Parent manifest has no valid run_id: {manifest_path}")
    relpath = workspace_relative(
        parent_dir, workspace_root, must_exist=True, label="parent run"
    )

    artifact_hashes: dict[str, str] = {}
    parent_texts_by_path: dict[str, str] = {}
    artifact_files = manifest.get("artifact_files", [])
    if artifact_files is None:
        artifact_files = []
    if not isinstance(artifact_files, list):
        raise ContractError("Parent manifest artifact_files must be a list")
    if relation == "audits-run":
        # A run-audit must be able to snapshot a parent that is already
        # incomplete.  Its snapshot therefore covers the complete observed
        # file tree, while declared-but-missing paths are reported later by
        # the audit inventory instead of preventing initialization.
        observed: list[tuple[str, Path]] = []
        for artifact in parent_dir.rglob("*"):
            if not artifact.is_file() or artifact == manifest_path:
                continue
            try:
                resolved = artifact.resolve(strict=True)
                resolved.relative_to(parent_dir)
            except (OSError, ValueError) as exc:
                raise ContractError(
                    f"Parent audit snapshot contains an unsafe file target: {artifact}"
                ) from exc
            rel = artifact.relative_to(parent_dir).as_posix()
            observed.append((rel, artifact))
        for rel, artifact in sorted(observed):
            artifact_hashes[rel] = sha256_file(artifact)
            if artifact.suffix.lower() in {".md", ".json"}:
                try:
                    parent_texts_by_path[rel] = artifact.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    raise ContractError(
                        f"Cannot inspect parent artifact IDs in {artifact}: {exc}"
                    ) from exc
    else:
        for raw_name in artifact_files:
            rel = safe_manifest_relpath(raw_name, label="parent artifact path")
            artifact = resolve_contained_file(
                parent_dir, rel, label="parent artifact"
            )
            artifact_hashes[rel.as_posix()] = sha256_file(artifact)
            if artifact.suffix.lower() in {".md", ".json"}:
                try:
                    text = artifact.read_text(encoding="utf-8")
                except (OSError, UnicodeError) as exc:
                    raise ContractError(
                        f"Cannot inspect parent artifact IDs in {artifact}: {exc}"
                    ) from exc
                parent_texts_by_path[rel.as_posix()] = text

    parent_version = parse_schema_version(manifest.get("schema_version"))
    definition_sources: Iterable[str] | Mapping[str, str]
    if parent_version.major >= 2:
        definition_sources = _artifact_texts_by_declared_role(
            manifest, parent_texts_by_path
        )
    else:
        # Frozen schema-1 behavior scans every readable declared/observed text
        # artifact because legacy manifests do not carry authoritative roles.
        definition_sources = parent_texts_by_path.values()
    available_ids = collect_parent_definition_ids(
        definition_sources,
        schema_version=str(parent_version),
    )

    return ParentSnapshot(
        run_id=run_id.strip(),
        relation=relation,
        workspace_relpath=relpath,
        source_manifest_sha256=sha256_file(manifest_path),
        source_artifact_sha256=artifact_hashes,
        available_ids=frozenset(available_ids),
    )


def validate_inherited_ids(
    values: Sequence[str],
    *,
    pattern: re.Pattern[str],
    label: str,
    parent: ParentSnapshot | None,
) -> list[str]:
    normalized = dedupe_preserving_order(value.strip() for value in values if value.strip())
    for value in normalized:
        if not pattern.fullmatch(value):
            raise ContractError(f"Invalid {label}: {value!r}")
        if parent is None:
            raise ContractError(f"{label} requires --parent-run: {value}")
        if value not in parent.available_ids:
            raise ContractError(f"{label} is not present in the parent run: {value}")
    return normalized


def dedupe_preserving_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def build_context_sources(
    raw_sources: Sequence[str],
    *,
    capability_profile: Path | None,
    workspace_root: Path,
) -> list[dict[str, object]]:
    parsed: list[tuple[str, Path]] = []
    for raw in raw_sources:
        if "=" not in raw:
            raise ContractError(
                f"--context-source must use ROLE=PATH syntax: {raw!r}"
            )
        role, raw_path = raw.split("=", 1)
        role = role.strip().lower()
        if not ROLE_PATTERN.fullmatch(role):
            raise ContractError(f"Invalid context-source role: {role!r}")
        if not raw_path.strip():
            raise ContractError(f"Context-source path is empty for role {role!r}")
        parsed.append((role, Path(raw_path.strip())))
    if capability_profile is not None:
        parsed.append(("capability-profile", capability_profile))

    seen: set[tuple[str, str]] = set()
    result: list[dict[str, object]] = []
    for role, path in parsed:
        resolved = path.expanduser().resolve()
        relative = workspace_relative(
            resolved, workspace_root, must_exist=True, label=f"context source ({role})"
        )
        key = (role, relative)
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "source_id": f"CTX-{len(result) + 1:03d}",
                "workspace_relpath": relative,
                "role": role,
                "access": "read-only",
                "kind": "file" if resolved.is_file() else "directory",
                "snapshot_sha256": sha256_file(resolved) if resolved.is_file() else None,
            }
        )
    return result


def parent_snapshot_dict(snapshot: ParentSnapshot) -> dict[str, object]:
    return {
        "run_id": snapshot.run_id,
        "relation": snapshot.relation,
        "workspace_relpath": snapshot.workspace_relpath,
        "source_manifest_sha256": snapshot.source_manifest_sha256,
        "source_artifact_sha256": dict(snapshot.source_artifact_sha256),
    }


def json_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def validate_branch_selection(
    value: str | None,
    *,
    parent: ParentSnapshot | None,
) -> dict[str, object] | None:
    if value is None or not value.strip():
        return None
    normalized = value.strip()
    is_id = bool(FOCUS_TARGET_ID_PATTERN.fullmatch(normalized))
    if parent is not None:
        if not is_id:
            raise ContractError(
                "Parent-backed focus requires a stable BR-###, C-###, or I-### "
                f"selected target; got label {normalized!r}"
            )
        if normalized not in parent.available_ids:
            raise ContractError(
                f"Selected branch/route/interface is not present in the parent run: {normalized}"
            )
    return {
        "id": normalized if is_id else None,
        "label": None if is_id else normalized,
        "source": "parent" if parent is not None else "standalone",
    }


def legacy_artifact_sources(
    source_dir: Path,
    manifest: Mapping[str, object],
) -> tuple[list[Path], Path | None]:
    """Return text contract artifacts without touching unlisted binary files."""

    names: list[str] = []
    declared = manifest.get("artifact_files", [])
    if declared is not None and not isinstance(declared, list):
        raise ContractError("Legacy manifest artifact_files must be a list")
    for raw_name in declared or []:
        rel = safe_manifest_relpath(raw_name, label="legacy artifact path")
        if rel.suffix.lower() not in {".md", ".json"}:
            continue
        names.append(rel.as_posix())
    for name in LEGACY_REQUIRED_ARTIFACTS:
        if (source_dir / name).is_file():
            names.append(name)

    reports = sorted(source_dir.glob("map_report_*.md"))
    if len(reports) > 1:
        raise ContractError(
            f"Legacy run contains multiple map reports; select cannot be inferred: {source_dir}"
        )
    report = reports[0] if reports else None
    if report is not None:
        names.append(report.name)

    result: list[Path] = []
    for name in dedupe_preserving_order(names):
        rel = safe_manifest_relpath(name, label="legacy artifact path")
        path = resolve_contained_file(source_dir, rel, label="legacy artifact")
        result.append(path)
    return result, report


def collect_ids_from_texts(texts: Iterable[str]) -> dict[str, list[str]]:
    all_ids: set[str] = set()
    for text in texts:
        all_ids.update(ANY_ID_PATTERN.findall(text))
    return {
        "claims": sorted(value for value in all_ids if CLAIM_ID_PATTERN.fullmatch(value)),
        "evidence": sorted(value for value in all_ids if EVIDENCE_ID_PATTERN.fullmatch(value)),
        "capabilities": sorted(
            value for value in all_ids if CAPABILITY_ID_PATTERN.fullmatch(value)
        ),
    }


def _strip_html_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    """Return visible text while carrying multi-line HTML-comment state."""

    visible: list[str] = []
    cursor = 0
    while cursor < len(line):
        if in_comment:
            end = line.find("-->", cursor)
            if end < 0:
                return "".join(visible), True
            cursor = end + 3
            in_comment = False
            continue
        start = line.find("<!--", cursor)
        if start < 0:
            visible.append(line[cursor:])
            break
        visible.append(line[cursor:start])
        end = line.find("-->", start + 4)
        if end < 0:
            in_comment = True
            break
        cursor = end + 3
    return "".join(visible), in_comment


def collect_authoritative_ids_from_markdown(
    text: str,
    *,
    artifact_role: str | None = None,
) -> set[str]:
    """Collect schema-2 IDs only from authoritative definition tables.

    Ordinary prose references, HTML comments, and fenced examples are excluded.
    The schema-2 table contract places each authoritative definition ID in the
    first column of a marked table.  When ``artifact_role`` is provided, the
    marker must also belong to that manifest-declared role.
    """

    result: set[str] = set()
    active_marker: str | None = None
    table_lines: list[str] = []
    in_comment = False
    fence_char: str | None = None
    fence_length = 0

    def finalize_table() -> None:
        nonlocal table_lines
        spec = ID_DEFINITION_SPECS.get(active_marker or "")
        if spec is not None and len(table_lines) >= 3:
            expected_header, id_pattern = spec
            header = table_lines[0].strip().strip("|").split("|", 1)[0].strip()
            if header != expected_header:
                table_lines = []
                return
            for line in table_lines[2:]:
                stripped = line.strip().strip("|")
                first_cell = stripped.split("|", 1)[0].strip()
                if id_pattern.fullmatch(first_cell):
                    result.add(first_cell)
        table_lines = []

    for raw_line in text.splitlines():
        stripped_raw = raw_line.strip()
        if fence_char is not None:
            fence = re.match(r"^\s*(`{3,}|~{3,})", raw_line)
            if (
                fence
                and fence.group(1)[0] == fence_char
                and len(fence.group(1)) >= fence_length
            ):
                fence_char = None
                fence_length = 0
            continue

        if not in_comment:
            marker = ROM_MARKER_PATTERN.fullmatch(stripped_raw)
            if marker:
                finalize_table()
                name = marker.group(1).lower()
                allowed_roles = ID_DEFINITION_MARKER_ROLES.get(name, frozenset())
                active_marker = (
                    name
                    if name in ID_DEFINITION_SPECS
                    and (artifact_role is None or artifact_role in allowed_roles)
                    else None
                )
                continue

        visible, in_comment = _strip_html_comments(raw_line, in_comment)
        fence = re.match(r"^\s*(`{3,}|~{3,})", visible)
        if fence:
            fence_char = fence.group(1)[0]
            fence_length = len(fence.group(1))
            continue

        stripped = visible.strip()
        if active_marker is None:
            continue
        if stripped.startswith("|"):
            table_lines.append(stripped)
            continue
        if table_lines:
            finalize_table()
            active_marker = None

    finalize_table()
    return result


def collect_authoritative_ids_from_role_texts(
    texts_by_role: Mapping[str, str],
) -> set[str]:
    """Collect schema-2 definitions from manifest role-to-text projections."""

    result: set[str] = set()
    for role, text in texts_by_role.items():
        if not isinstance(role, str) or not isinstance(text, str):
            raise ContractError(
                "Role-aware definition sources must map strings to strings"
            )
        result.update(
            collect_authoritative_ids_from_markdown(text, artifact_role=role)
        )
    return result


def collect_parent_definition_ids(
    texts: Iterable[str] | Mapping[str, str],
    *,
    schema_version: object,
) -> set[str]:
    """Collect inheritable IDs with role-aware schema-2 and frozen legacy behavior.

    A mapping is interpreted as ``artifact role -> text`` for schema 2.  The
    iterable form remains supported for existing callers, but parent snapshots
    use the mapping form so misplaced markers cannot become definitions.
    """

    version = parse_schema_version(schema_version)
    text_values: Iterable[str] = (
        texts.values() if isinstance(texts, Mapping) else texts
    )
    if version.major < 2:
        return {
            value
            for text in text_values
            for value in ANY_ID_PATTERN.findall(text)
        }
    if isinstance(texts, Mapping):
        return collect_authoritative_ids_from_role_texts(texts)
    result: set[str] = set()
    for text in text_values:
        result.update(collect_authoritative_ids_from_markdown(text))
    return result


def artifact_roles_for_legacy_copy(
    artifacts: Sequence[Path],
    *,
    report_name: str,
) -> dict[str, str]:
    roles: dict[str, str] = {}
    roles_by_name = {
        "00_intake.md": "intake",
        "01_breadth-ledger.md": "breadth_ledger",
        "02_search-log.md": "search_log",
        "03_evidence-matrix.md": "evidence_matrix",
        "04_research-map.md": "research_map",
        "05_candidate-portfolio.md": "candidate_portfolio",
        "06_red-team.md": "red_team",
        "07_decision-log.md": "decision_log",
    }
    for path in artifacts:
        role = roles_by_name.get(path.name)
        if role is not None:
            roles[role] = path.name
    roles["reader_report"] = report_name
    return roles
