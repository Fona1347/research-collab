#!/usr/bin/env python3
"""Validate completeness and traceability of a research opportunity mapping run."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from urllib.parse import urlsplit, urlunsplit
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from rom_contract import (
    COMPLETION_STATUSES,
    DISCOVERY_LENSES,
    DOMAIN_LENSES,
    FOCUS_TARGET_ID_PATTERN,
    ID_DEFINITION_MARKER_ROLES,
    ID_DEFINITION_SPECS as CONTRACT_ID_DEFINITION_SPECS,
    MODE_ROLES,
    REQUESTED_MODES,
    ROUTING_CONFIDENCE,
    RUN_TYPES,
    SKILL_ID,
    SKILL_VERSION,
    VALIDATOR_VERSION,
    WORKFLOW_CONTRACTS_BY_MODE,
    ContractError,
    artifact_profile,
    collect_parent_definition_ids,
    load_json_object,
    parse_custom_domain_lens_notes,
    parse_schema_version,
    resolve_contained_file,
    safe_manifest_relpath,
    sha256_file,
    validate_custom_domain_lens_notes,
)
from parent_audit import (
    ParentAuditFacts,
    canonical_manifest_repair,
    inspect_parent_for_audit,
)
from evidence_chains import CHAIN_PREFIX, assess_chains, independently_reviewed
import canonical_links


REQUIRED_FILES = {
    "00_intake.md": ["## Decision", "## Capability Passport", "## Constraints"],
    "01_breadth-ledger.md": ["## Anchor Audit", "## Branches", "## Breadth-Gate Decision"],
    "02_search-log.md": ["## Queries", "## Bounded Negative Evidence"],
    "03_evidence-matrix.md": ["## Atomic Claims", "## Evidence Records"],
    "04_research-map.md": ["### Evidence", "### Inference", "### Recommendation", "## Mapping Lattice"],
    "05_candidate-portfolio.md": ["## Shared Platform", "## Low-Risk Candidate", "## Medium-Risk Candidate", "## High-Risk Candidate"],
    "06_red-team.md": ["## Strongest Baseline Ladder", "## Alternative-Explanation Tests", "## Candidate Kill Criteria"],
    "07_decision-log.md": ["## Decisions", "## Revisions and Rejections", "## Next Actions"],
}

COUNT_GATES = {
    "Bottleneck families covered": 4,
    "Mechanism families covered": 4,
    "Application contexts covered": 2,
    "Counterexample searches completed": 3,
    "Outside-favorite-material routes": 1,
}

PLACEHOLDER_PATTERNS = [
    re.compile(r"\bTBD\b", re.IGNORECASE),
    re.compile(r"\{\{[^}]+\}\}"),
    re.compile(r"\[TODO[^]]*\]", re.IGNORECASE),
    re.compile(r"待填|待补|待定"),
]

DISCONFIRM_PATTERN = re.compile(
    r"counter|disconfirm|failure|negative|alternative|baseline|"
    r"反例|反证|失败|负面|替代|基线",
    re.IGNORECASE,
)

UNBOUNDED_CLAIM_PATTERN = re.compile(
    r"\b(nobody has|no one has|first ever|completely unexplored)\b|"
    r"无人做|没有人做|尚无人|从未有人|世界首创|国内外首次|完全空白",
    re.IGNORECASE,
)

HUMAN_REPORT_PATTERN = re.compile(
    r"^map_report_.+_\d{4}-\d{2}-\d{2}\.md$",
    re.IGNORECASE,
)

HUMAN_REPORT_SECTIONS = (
    (
        "one-page conclusion",
        re.compile(
            r"^##\s+(?:\d+\.\s*)?(?:一页结论|One-Page Conclusion|Executive Summary|Decision Summary)\s*$",
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "research map",
        re.compile(r"^##\s+.*(?:研究地图|Research Map).*$", re.MULTILINE | re.IGNORECASE),
    ),
    (
        "recommendation portfolio",
        re.compile(
            r"^##\s+.*(?:推荐(?:路线|组合)|Recommended Routes|Recommendations|Portfolio).*$",
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
    (
        "references",
        re.compile(
            r"^##\s+(?:\d+\.\s*)?(?:参考文献|References)\s*$",
            re.MULTILINE | re.IGNORECASE,
        ),
    ),
)


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    passed: list[str] = field(default_factory=list)

    def check(self, condition: bool, success: str, failure: str, *, warning: bool = False) -> None:
        if condition:
            self.passed.append(success)
        elif warning:
            self.warnings.append(failure)
        else:
            self.errors.append(failure)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a research-map run directory.")
    parser.add_argument("run_directory", type=Path)
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat quality-gate warnings as a failing exit status.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument("--canonical-checker", type=Path, help="Explicit Deep Reading check_canonical.py for maintenance-source testing; installed skills use the sibling checker.")
    parser.add_argument(
        "--workspace-root",
        type=Path,
        help="Workspace root used to resolve schema-2 parent/context references.",
    )
    return parser.parse_args()


def table_rows(text: str, marker: str) -> list[list[str]]:
    lines = text.splitlines()
    start = next((i for i, line in enumerate(lines) if marker in line and line.lstrip().startswith("|")), None)
    if start is None:
        return []
    rows: list[list[str]] = []
    for line in lines[start + 2 :]:
        if not line.lstrip().startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and not all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells):
            rows.append(cells)
    return rows


def schema_at_least(value: object, major: int, minor: int) -> bool:
    try:
        parts = str(value).split(".")
        parsed = (int(parts[0]), int(parts[1]) if len(parts) > 1 else 0)
    except (TypeError, ValueError):
        return False
    return parsed >= (major, minor)


def validate_v1_legacy(run_dir: Path) -> Report:
    report = Report()
    contents: dict[str, str] = {}
    manifest: dict[str, object] = {}
    reader_report_text = ""

    report.check(run_dir.is_dir(), "Run directory exists", f"Run directory not found: {run_dir}")
    if not run_dir.is_dir():
        return report

    manifest_path = run_dir / "run-manifest.json"
    report.check(manifest_path.is_file(), "Manifest exists", "Missing run-manifest.json")
    if manifest_path.is_file():
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            report.check(
                manifest.get("skill") == "research-opportunity-mapper",
                "Manifest identifies the skill",
                "Manifest has an unexpected or missing skill identifier",
            )
        except (OSError, json.JSONDecodeError) as exc:
            report.errors.append(f"Invalid manifest: {exc}")

    artifact_files = manifest.get("artifact_files", [])
    declared_reports = [
        name
        for name in artifact_files
        if isinstance(name, str) and HUMAN_REPORT_PATTERN.fullmatch(name)
    ] if isinstance(artifact_files, list) else []
    schema_version = manifest.get("schema_version", "1.0")
    requires_reader_report = schema_at_least(schema_version, 1, 1)
    requires_full_reader_contract = schema_at_least(schema_version, 1, 2)

    if requires_reader_report:
        report.check(
            len(declared_reports) == 1,
            "Manifest declares one human-facing map report",
            "Current-schema runs must declare exactly one map_report_<short_task_name>_<YYYY-MM-DD>.md",
        )
    if requires_full_reader_contract and declared_reports:
        report.check(
            manifest.get("primary_artifact") == declared_reports[0],
            "Manifest identifies the map report as the primary artifact",
            "Schema 1.2+ manifest must set primary_artifact to the declared map_report",
        )

    if declared_reports:
        try:
            reader_report_path = resolve_contained_file(
                run_dir, Path(declared_reports[0]), label="legacy reader report"
            )
        except ContractError as exc:
            report.errors.append(str(exc))
            reader_report_path = None
        if reader_report_path is not None:
            report.passed.append(f"Human-facing report exists inside run: {declared_reports[0]}")
            reader_report_text = reader_report_path.read_text(encoding="utf-8")
            for label, section_pattern in HUMAN_REPORT_SECTIONS:
                report.check(
                    bool(section_pattern.search(reader_report_text)),
                    f"Human-facing report contains {label}",
                    f"Human-facing report is missing required section: {label}",
                )
            report.check(
                bool(re.search(r"^> \[!(?:NOTE|TIP|CAUTION|IMPORTANT|WARNING)\]", reader_report_text, re.MULTILINE | re.IGNORECASE)),
                "Human-facing report uses GitHub-style callouts",
                "Human-facing report has no GitHub-style callout",
            )
            report.check(
                "doi.org/" in reader_report_text or "https://" in reader_report_text,
                "Human-facing report contains reader-facing citation links",
                "Human-facing report contains no DOI or stable citation link",
            )
            report.check(
                not re.search(r"\b(?:doc_id|chunk_id|offset)\b", reader_report_text, re.IGNORECASE),
                "Human-facing report omits internal provenance identifiers",
                "Human-facing report exposes doc/chunk/offset provenance; keep it in 03_evidence-matrix.md",
                warning=True,
            )

            if requires_full_reader_contract:
                callout_types = {
                    match.upper()
                    for match in re.findall(
                        r"^> \[!(NOTE|TIP|CAUTION|IMPORTANT|WARNING)\]",
                        reader_report_text,
                        re.MULTILINE | re.IGNORECASE,
                    )
                }
                report.check(
                    "IMPORTANT" in callout_types,
                    "Reader report contains a decision-level IMPORTANT callout",
                    "Reader report needs an IMPORTANT callout for the primary decision or epistemic contract",
                )
                report.check(
                    "NOTE" in callout_types,
                    "Reader report contains evidence or concept NOTE callouts",
                    "Reader report needs a NOTE callout for important literature evidence or a concept boundary",
                )
                report.check(
                    bool(callout_types & {"CAUTION", "WARNING"}),
                    "Reader report contains a limitation or risk callout",
                    "Reader report needs a CAUTION or WARNING callout for a material limitation or risk",
                )

                source_labels = {
                    "core contribution": re.compile(r"核心贡献|Core contribution", re.IGNORECASE),
                    "supported viewpoint": re.compile(
                        r"印证观点|支持(?:观点|判断|主张)|Supports?", re.IGNORECASE
                    ),
                    "boundary": re.compile(r"边界|局限|Limits?|Boundary", re.IGNORECASE),
                }
                for label, pattern in source_labels.items():
                    report.check(
                        bool(pattern.search(reader_report_text)),
                        f"Reader-facing source annotations include {label}",
                        f"Reader-facing source annotations are missing {label}",
                    )

                risk_patterns = {
                    "low risk": re.compile(r"低风险|low[- ]risk", re.IGNORECASE),
                    "medium risk": re.compile(r"中风险|medium[- ]risk", re.IGNORECASE),
                    "high risk": re.compile(r"高风险|high[- ]risk", re.IGNORECASE),
                }
                for label, pattern in risk_patterns.items():
                    report.check(
                        bool(pattern.search(reader_report_text)),
                        f"Reader report covers {label}",
                        f"Reader report does not cover a {label} route",
                    )

                report.check(
                    bool(re.search(r"三个月|3[- ]month", reader_report_text, re.IGNORECASE)),
                    "Reader report states a three-month horizon",
                    "Reader report is missing the three-month decisive-data horizon",
                )
                report.check(
                    bool(re.search(r"一年|one[- ]year|12[- ]month", reader_report_text, re.IGNORECASE)),
                    "Reader report states a one-year horizon",
                    "Reader report is missing the one-year platform horizon",
                )

                decision_terms = {
                    "strongest baseline": re.compile(r"最强基线|strongest baseline", re.IGNORECASE),
                    "kill criterion": re.compile(
                        r"kill criteri(?:on|a)|终止条件|停止条件", re.IGNORECASE
                    ),
                    "reversal condition": re.compile(r"反转条件|reversal condition", re.IGNORECASE),
                }
                for label, pattern in decision_terms.items():
                    report.check(
                        bool(pattern.search(reader_report_text)),
                        f"Reader report contains {label}",
                        f"Reader report is missing {label}",
                    )

                reference_entries = re.findall(
                    r"^\s*\d+\.\s+.*(?:https?://|doi\b).*$",
                    reader_report_text,
                    re.MULTILINE | re.IGNORECASE,
                )
                report.check(
                    len(reference_entries) >= 4,
                    f"Reader report contains {len(reference_entries)} linked numbered references",
                    f"Reader report has only {len(reference_entries)} linked numbered references; a full map normally requires at least four",
                    warning=True,
                )
                report.check(
                    len(reader_report_text) >= 2500,
                    "Reader report has enough substance for an independent reading surface",
                    "Reader report is unusually short for a full research map; verify that it is not a skeletal summary",
                    warning=True,
                )

                internal_claim_ids = re.findall(r"\bE-\d{3}\b", reader_report_text)
                report.check(
                    len(internal_claim_ids) <= 3,
                    "Reader report does not depend on internal evidence IDs",
                    f"Reader report contains {len(internal_claim_ids)} internal E-### references; convert them to ordinary numbered citations",
                    warning=True,
                )

                if str(manifest.get("language", "")).lower().startswith("zh"):
                    cjk_count = len(re.findall(r"[\u4e00-\u9fff]", reader_report_text))
                    report.check(
                        cjk_count >= 200,
                        f"Chinese-first reader report contains {cjk_count} CJK characters",
                        "Reader report is marked zh-CN but does not appear to be Chinese-dominant",
                        warning=True,
                    )

    for filename, headings in REQUIRED_FILES.items():
        try:
            path = resolve_contained_file(
                run_dir, Path(filename), label="legacy required artifact"
            )
        except ContractError as exc:
            report.errors.append(f"Missing or unsafe required artifact {filename}: {exc}")
            continue
        text = path.read_text(encoding="utf-8")
        contents[filename] = text
        for heading in headings:
            report.check(
                heading in text,
                f"{filename}: contains {heading}",
                f"{filename}: missing required section {heading}",
            )

    if len(contents) != len(REQUIRED_FILES):
        return report

    all_text = "\n".join(contents.values())
    if reader_report_text:
        all_text = f"{all_text}\n{reader_report_text}"
    placeholders = sum(len(pattern.findall(all_text)) for pattern in PLACEHOLDER_PATTERNS)
    report.check(
        placeholders == 0,
        "No unresolved template placeholders",
        f"Found {placeholders} unresolved template placeholders",
    )

    breadth = contents["01_breadth-ledger.md"]
    for label, minimum in COUNT_GATES.items():
        match = re.search(rf"^{re.escape(label)}:\s*(\d+)\s*$", breadth, re.MULTILINE)
        actual = int(match.group(1)) if match else -1
        report.check(
            actual >= minimum,
            f"Breadth gate: {label} = {actual}",
            f"Breadth gate not met: {label} is {actual if actual >= 0 else 'missing'}, requires at least {minimum}",
            warning=True,
        )

    search_log = contents["02_search-log.md"]
    query_rows = table_rows(search_log, "| Query ID |")
    report.check(
        len(query_rows) >= 4,
        f"Search log contains {len(query_rows)} query records",
        f"Search log has only {len(query_rows)} query records; use at least four distinct query purposes",
        warning=True,
    )
    disconfirm_rows = [row for row in query_rows if DISCONFIRM_PATTERN.search(" ".join(row))]
    report.check(
        bool(disconfirm_rows),
        f"Search log contains {len(disconfirm_rows)} disconfirmation or baseline query record(s)",
        "Search rows do not show a counterexample, failure, alternative, or baseline search",
        warning=True,
    )

    evidence = contents["03_evidence-matrix.md"]
    evidence_rows = table_rows(evidence, "| Evidence ID |")
    report.check(
        len(evidence_rows) >= 4,
        f"Evidence matrix contains {len(evidence_rows)} records",
        f"Evidence matrix has only {len(evidence_rows)} records; coverage is too thin for comparison",
        warning=True,
    )
    well_formed_rows = [
        row
        for row in evidence_rows
        if len(row) >= 12 and row[8] and row[9] and row[10] and row[11]
    ]
    report.check(
        len(well_formed_rows) == len(evidence_rows),
        "All evidence records include DOI/URL, provenance, depth, and verification",
        f"{len(evidence_rows) - len(well_formed_rows)} evidence record(s) have incomplete traceability fields",
    )
    verified_rows = [
        row
        for row in evidence_rows
        if len(row) >= 12 and row[11].strip().lower() in {"verified", "已核验"}
    ]
    report.check(
        len(verified_rows) >= 2,
        f"Evidence matrix contains {len(verified_rows)} verified records",
        "Fewer than two evidence records are marked verified",
        warning=True,
    )
    report.check(
        "> **E-" in evidence or "> **E-" in contents["04_research-map.md"],
        "Important evidence uses blockquote annotations",
        "No GitHub blockquote-style evidence annotation was found",
    )
    limiting_rows = [
        row
        for row in evidence_rows
        if len(row) >= 3
        and row[2].strip().lower() in {"contradicts", "mixed", "反驳", "混合"}
    ]
    report.check(
        bool(limiting_rows),
        f"Evidence matrix contains {len(limiting_rows)} contradicting or mixed record(s)",
        "No evidence record is labeled contradicting or mixed",
        warning=True,
    )
    full_context_rows = [
        row
        for row in evidence_rows
        if len(row) >= 11 and row[10].strip().lower() in {"full context", "全文语境"}
    ]
    report.check(
        bool(full_context_rows),
        f"Evidence matrix contains {len(full_context_rows)} full-context record(s)",
        "No evidence record is marked as checked in full context",
        warning=True,
    )

    research_map = contents["04_research-map.md"]
    for label in ("Evidence", "Inference", "Recommendation"):
        report.check(
            bool(re.search(rf"^###\s+{label}\s*$", research_map, re.MULTILINE)),
            f"Research map separates {label}",
            f"Research map does not separate {label}",
        )

    portfolio = contents["05_candidate-portfolio.md"]
    for phrase in (
        "Three-month minimal decisive experiment",
        "Kill criterion",
        "One-year platform path",
        "Strongest baseline",
        "Recommendation reversal condition",
    ):
        count = portfolio.count(phrase)
        report.check(
            count >= 3,
            f"All candidate cards contain {phrase}",
            f"Candidate portfolio contains {phrase} only {count} time(s); expected three",
        )
    report.check(
        "## Rejected Routes" in portfolio and bool(re.search(r"rejected|reject", portfolio, re.IGNORECASE)),
        "Portfolio retains rejected routes",
        "Portfolio does not retain an explicitly rejected route",
        warning=True,
    )

    red_team = contents["06_red-team.md"]
    report.check(
        all(token in red_team for token in ("Circuit/digital baseline", "Alternative explanation", "Kill criterion")),
        "Red team covers baselines, alternative explanations, and kill criteria",
        "Red team is missing a baseline, alternative-explanation, or kill-criterion field",
    )

    decision_log = contents["07_decision-log.md"]
    report.check(
        "Reversal condition" in decision_log,
        "Decision log records reversal conditions",
        "Decision log is missing reversal conditions",
    )

    absence_claims = UNBOUNDED_CLAIM_PATTERN.findall(all_text)
    report.check(
        not absence_claims,
        "No unbounded absence or priority claims detected",
        f"Detected {len(absence_claims)} unbounded absence or priority claim(s)",
        warning=True,
    )
    return report


# ---------------------------------------------------------------------------
# Schema 2.0 validation. The legacy validator above is intentionally frozen:
# schema-1 fixtures must retain their exact 53/81 pass-count contract.

SUPPORTED_SCHEMA_VERSIONS = {"1.0", "1.1", "1.2", "2.0"}
V2_ID_PATTERN = re.compile(
    r"\b(?:ART|BR|CAP|CTX|CL|DR|GS|B|M|S|C|E|Q|A|D|I|H|G|F|R)-\d{3}\b"
)
RUN_AUDIT_TARGET_PATTERN = re.compile(
    r"(?<![A-Za-z0-9])(?:(?:B|M|S|CL)-\d{3}|C-(?:\d{3}|[LMH]\d{2}))(?![A-Za-z0-9])"
)
V2_ID_TYPE_PATTERNS = {
    "artifact": re.compile(r"^ART-\d{3}$"),
    "branch": re.compile(r"^BR-\d{3}$"),
    "capability": re.compile(r"^CAP-\d{3}$"),
    "context": re.compile(r"^CTX-\d{3}$"),
    "deep_read_request": re.compile(r"^DR-\d{3}$"),
    "claim": re.compile(r"^(?:B|M|S|CL)-\d{3}$"),
    "candidate": re.compile(r"^C-\d{3}$"),
    "evidence": re.compile(r"^E-\d{3}$"),
    "query": re.compile(r"^Q-\d{3}$"),
    "attack": re.compile(r"^A-\d{3}$"),
    "decision": re.compile(r"^D-\d{3}$"),
    "interface": re.compile(r"^I-\d{3}$"),
    "gray_space": re.compile(r"^GS-\d{3}$"),
    "hypothesis": re.compile(r"^H-\d{3}$"),
    "gap": re.compile(r"^G-\d{3}$"),
    "finding": re.compile(r"^F-\d{3}$"),
    "repair": re.compile(r"^R-\d{3}$"),
}
V2_PLACEHOLDER = re.compile(
    r"\b(?:TBD|TODO|TBC|FIXME)\b|\{\{[^}]+\}\}|待填|待补|待定|占位",
    re.IGNORECASE,
)
UNBOUNDED_PRIORITY = re.compile(
    r"\b(?:nobody has|no one has|no prior work|first ever|completely unexplored|"
    r"unexplored|novel because zero|first because zero)\b|"
    r"无人做|没有人做|尚无人|尚无报道|未见报道|从未有人|世界首创|国内外首次|"
    r"完全空白|研究空白|零命中.*(?:首创|空白)",
    re.IGNORECASE,
)
MARKER_PATTERN = re.compile(
    r"^<!--\s*rom-(section|table):\s*([a-z0-9-]+)\s*-->$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class VisibleLine:
    number: int
    text: str


@dataclass(frozen=True)
class DispositionBinding:
    target_id: str
    verdict: str
    decision_id: str
    source: str
    repair: str
    exact_final_projection: bool = True


@dataclass
class V2Block:
    kind: str
    name: str
    marker_line: int
    lines: list[VisibleLine] = field(default_factory=list)


@dataclass
class V2Table:
    name: str
    headers: list[str]
    rows: list[list[str]]
    row_lines: list[int]
    errors: list[str] = field(default_factory=list)


@dataclass
class V2Document:
    path: Path
    text: str
    blocks: dict[str, V2Block]
    errors: list[str]
    projections: dict[str, V2Block] = field(default_factory=dict)
    route_blocks: dict[str, V2Block] = field(default_factory=dict)

    @property
    def narrative_layout(self) -> bool:
        return "audit-appendix" in self.blocks

    @classmethod
    def parse(cls, path: Path, text: str) -> "V2Document":
        blocks: dict[str, V2Block] = {}
        errors: list[str] = []
        current: V2Block | None = None
        projections: dict[str, V2Block] = {}
        route_blocks: dict[str, V2Block] = {}
        current_route: V2Block | None = None
        section_name: str | None = None
        fence_char: str | None = None
        fence_length = 0
        in_comment = False

        for line_number, raw_line in enumerate(text.splitlines(), 1):
            stripped = raw_line.strip()
            fence_match = re.match(r"^\s*(`{3,}|~{3,})", raw_line)
            if fence_char is not None:
                if (
                    fence_match
                    and fence_match.group(1)[0] == fence_char
                    and len(fence_match.group(1)) >= fence_length
                ):
                    fence_char = None
                    fence_length = 0
                continue
            if fence_match and not in_comment:
                fence_char = fence_match.group(1)[0]
                fence_length = len(fence_match.group(1))
                continue

            if not in_comment:
                projection = re.fullmatch(r"<!--\s*rom-projection:\s*([a-z0-9-]+)\s*-->", stripped)
                route = re.fullmatch(r"<!--\s*rom-route:\s*(C-\d{3})\s*-->", stripped)
                if projection:
                    name = projection.group(1)
                    if section_name != "audit-appendix":
                        errors.append(f"rom-projection {name!r} must be in audit-appendix")
                    if name in projections:
                        errors.append(f"duplicate rom-projection {name!r}")
                    current = V2Block("projection", name, line_number)
                    projections.setdefault(name, current)
                    current_route = None
                    continue
                if route:
                    name = route.group(1)
                    if section_name != "scientific-argument":
                        errors.append(f"rom-route {name!r} must be in scientific-argument")
                    if name in route_blocks:
                        errors.append(f"duplicate rom-route {name!r}")
                    current_route = V2Block("route", name, line_number)
                    route_blocks.setdefault(name, current_route)
                    continue
                marker = MARKER_PATTERN.fullmatch(stripped)
                if marker:
                    name = marker.group(2).lower()
                    section_name = name
                    current_route = None
                    if name in blocks:
                        errors.append(
                            f"duplicate rom marker {name!r} at line {line_number}"
                        )
                    else:
                        current = V2Block(
                            kind=marker.group(1).lower(),
                            name=name,
                            marker_line=line_number,
                        )
                        blocks[name] = current
                    continue

            visible, in_comment = _strip_html_comments(raw_line, in_comment)
            if current is not None and visible.strip():
                current.lines.append(VisibleLine(line_number, visible.rstrip()))
                if current_route is not None:
                    current_route.lines.append(VisibleLine(line_number, visible.rstrip()))

        if fence_char is not None:
            errors.append("unterminated fenced code block")
        if in_comment:
            errors.append("unterminated HTML comment")
        return cls(path=path, text=text, blocks=blocks, errors=errors,
                   projections=projections, route_blocks=route_blocks)

    def table(self, name: str) -> V2Table | None:
        block = self.projections.get(name) or self.blocks.get(name)
        if block is None:
            return None
        return _parse_v2_table(block)

    def visible_text(self) -> str:
        return "\n".join(
            line.text for block in (*self.blocks.values(), *self.projections.values()) for line in block.lines
        )


def _strip_html_comments(line: str, in_comment: bool) -> tuple[str, bool]:
    output: list[str] = []
    cursor = 0
    while cursor < len(line):
        if in_comment:
            end = line.find("-->", cursor)
            if end < 0:
                return "".join(output), True
            cursor = end + 3
            in_comment = False
            continue
        start = line.find("<!--", cursor)
        if start < 0:
            output.append(line[cursor:])
            break
        output.append(line[cursor:start])
        cursor = start + 4
        in_comment = True
    return "".join(output), in_comment


def _split_markdown_row(line: str) -> list[str]:
    stripped = line.strip()
    if stripped.startswith("|"):
        stripped = stripped[1:]
    if stripped.endswith("|") and not stripped.endswith(r"\|"):
        stripped = stripped[:-1]
    cells: list[str] = []
    buffer: list[str] = []
    escaped = False
    code_delimiter = 0
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
            if code_delimiter == 0:
                code_delimiter = ticks
            elif code_delimiter == ticks:
                code_delimiter = 0
            buffer.append(stripped[index:end])
            index = end
            continue
        if char == "|" and code_delimiter == 0:
            cells.append("".join(buffer).strip())
            buffer = []
        else:
            buffer.append(char)
        index += 1
    cells.append("".join(buffer).strip())
    return cells


def _parse_v2_table(block: V2Block) -> V2Table:
    errors: list[str] = []
    table_lines = [line for line in block.lines if line.text.lstrip().startswith("|")]
    if len(table_lines) < 2:
        return V2Table(block.name, [], [], [], ["missing header or separator"])
    first_index = next(
        index for index, line in enumerate(block.lines) if line.text.lstrip().startswith("|")
    )
    contiguous: list[VisibleLine] = []
    for line in block.lines[first_index:]:
        if not line.text.lstrip().startswith("|"):
            if contiguous:
                break
            continue
        contiguous.append(line)
    if len(contiguous) < 2:
        return V2Table(block.name, [], [], [], ["table must have a header and separator"])
    headers = _split_markdown_row(contiguous[0].text)
    separator = _split_markdown_row(contiguous[1].text)
    if len(headers) != len(separator) or not all(
        re.fullmatch(r":?-{3,}:?", cell) for cell in separator
    ):
        errors.append(f"invalid Markdown separator at line {contiguous[1].number}")
    if not headers or any(not cell for cell in headers):
        errors.append("table contains an empty header")
    normalized_headers = [_normalize_header(value) for value in headers]
    if len(set(normalized_headers)) != len(normalized_headers):
        errors.append("table contains duplicate headers")
    rows: list[list[str]] = []
    row_lines: list[int] = []
    for line in contiguous[2:]:
        cells = _split_markdown_row(line.text)
        if len(cells) != len(headers):
            errors.append(
                f"row at line {line.number} has {len(cells)} cells; expected {len(headers)}"
            )
            # Preserve the structural error but do not expose malformed rows to
            # semantic validators that index an exact registered schema.
            continue
        rows.append(cells)
        row_lines.append(line.number)
    return V2Table(block.name, headers, rows, row_lines, errors)


def _normalize_header(value: str) -> str:
    return re.sub(r"[^\w\u4e00-\u9fff]+", "", value.lower(), flags=re.UNICODE)


EXACT_COLUMN_VARIANTS: Mapping[str, frozenset[str]] = {
    "decisioncritical": frozenset({"decisioncritical", "decisioncriticalyesno"}),
    "outsidefavoritefamily": frozenset({"outsidefavoritefamily", "outsidefavoritefamilyyesno"}),
    "fieldyearnormalized": frozenset({"fieldyearnormalized", "fieldyearnormalizedyesnounavailable"}),
    "confidence": frozenset({"confidence", "confidencehighmoderatelowinsufficient"}),
    "risk": frozenset({"risk", "risklowmediumhigh"}),
    "why": frozenset({"why", "whysufficiencynecessitytiming"}),
    "severity": frozenset({"severity", "severitylowmediumhighblocking"}),
    "verdict": frozenset({"verdict", "verdictkeepdowngraderevisekill"}),
    "status": frozenset({"status", "statuskeepdowngraderevisekill"}),
    "role": frozenset({"role", "roleprimarycomparatorfallbackneighbor"}),
    "routerole": frozenset({"routerole", "routeroleprimarycomparatorfallback"}),
    "outcomeclass": frozenset({"outcomeclass", "outcomeclasspositivenegativeambiguous"}),
    "sameinterface": frozenset({"sameinterface", "sameinterfaceyesno"}),
    "parentleftunchanged": frozenset({"parentleftunchanged", "parentleftunchangedyesno"}),
    "declared": frozenset({"declared", "declaredyesno"}),
    "exists": frozenset({"exists", "existsyesno"}),
    "result": frozenset({"result", "resultpassfailuncertain"}),
    "match": frozenset({"match", "matchyesno"}),
    "metadataverified": frozenset({"metadataverified", "metadataverifiedyesno"}),
    "discriminatingcontrolpresent": frozenset({"discriminatingcontrolpresent", "discriminatingcontrolpresentyesno"}),
    "thresholdpresent": frozenset({"thresholdpresent", "thresholdpresentyesno"}),
    "type": frozenset({"type", "typesearchexperimentmodelcollaboration"}),
}


def _column(table: V2Table, *aliases: str) -> int:
    normalized = [_normalize_header(header) for header in table.headers]
    wanted: set[str] = set()
    for alias in aliases:
        normalized_alias = _normalize_header(alias)
        wanted.add(normalized_alias)
        wanted.update(EXACT_COLUMN_VARIANTS.get(normalized_alias, ()))
    for alias in wanted:
        for index, header in enumerate(normalized):
            if header == alias:
                return index
    raise ContractError(
        f"rom-table {table.name!r} is missing an exact registered column matching {aliases!r}; "
        f"headers are {table.headers!r}"
    )


def _meaningful(value: str) -> bool:
    stripped = re.sub(r"[*_`]", "", value).strip()
    if not stripped or V2_PLACEHOLDER.search(stripped):
        return False
    return stripped.lower() not in {"-", "...", "x", "value", "placeholder"}


def _scope_rationale(value: str) -> bool:
    # Sentinels are legal in other tables, but cannot explain a scope exclusion.
    normalized = "".join(char for char in unicodedata.normalize("NFKC", value).casefold() if char.isalnum())
    return _meaningful(value) and bool(normalized) and normalized not in {
        "na", "none", "unknown", "notapplicable", "outofscope", "sameasabove",
        "无", "未知", "不适用", "范围外", "同上",
    }


def _unbounded_priority_assertions(text: str) -> list[str]:
    prohibition = re.compile(
        r"\b(?:do not|don't|must not|never)\s+(?:claim|infer|treat|state|say)\b|"
        r"\b(?:forbidden|prohibited)\b|禁止|不得|不可|不要(?:声称|推断)|不能(?:声称|推断)",
        re.IGNORECASE,
    )
    return [
        line.strip()
        for line in text.splitlines()
        if UNBOUNDED_PRIORITY.search(line) and not prohibition.search(line)
    ]


def _cell_ids(value: str, pattern: re.Pattern[str] | None = None) -> list[str]:
    values = V2_ID_PATTERN.findall(value)
    if pattern is not None:
        values = [item for item in values if pattern.fullmatch(item)]
    return values


def _split_multi(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[,;/]+", value) if item.strip()]


def _discover_workspace_root(run_dir: Path, explicit: Path | None) -> Path:
    if explicit is not None:
        root = explicit.expanduser().resolve()
        if not root.is_dir():
            raise ContractError(f"Workspace root not found: {root}")
        return root
    for candidate in (run_dir, *run_dir.parents):
        if (candidate / "AGENTS.md").is_file():
            return candidate
    raise ContractError("Cannot infer workspace root; pass --workspace-root")


def _resolve_workspace_path(root: Path, value: object, *, label: str) -> Path:
    relative = safe_manifest_relpath(value, label=label)
    target = (root / relative).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ContractError(f"{label} escapes workspace root: {value!r}") from exc
    return target


ROLE_MARKERS: Mapping[str, tuple[tuple[str, str], ...]] = {
    "intake": (
        ("section", "decision"),
        ("section", "problem-adequacy"),
        ("section", "capability-passport"),
        ("section", "constraints"),
        ("section", "scale-boundary"),
        ("section", "controllable-actions"),
        ("section", "unknowns"),
        ("section", "scope"),
    ),
    "breadth_ledger": (
        ("section", "anchor-audit"),
        ("table", "breadth-branches"),
        ("table", "breadth-summary"),
        ("section", "frontier-radar"),
        ("section", "gray-space-mismatch"),
        ("section", "breadth-gate"),
    ),
    "search_log": (
        ("section", "search-policy"),
        ("table", "search-queries"),
        ("table", "frontier-signals"),
        ("section", "seed-expansion"),
        ("section", "bounded-negative-evidence"),
    ),
    "evidence_matrix": (
        ("table", "atomic-claims"),
        ("table", "evidence-records"),
        ("table", "claim-confidence"),
        ("section", "source-annotations"),
        ("table", "contradictions"),
    ),
    "research_map": (
        ("section", "decision-summary"),
        ("section", "background-question"),
        ("table", "persistent-bottlenecks"),
        ("table", "sota-families"),
        ("table", "mapping-lattice"),
        ("table", "mechanism-definitions"),
        ("table", "open-interfaces"),
        ("section", "bio-inspired-translation"),
        ("table", "uncertainty-register"),
    ),
    "candidate_portfolio": (
        ("section", "shared-platform"),
        ("table", "candidate-routes"),
        ("table", "scorecard"),
        ("section", "sensitivity"),
        ("table", "rejected-routes"),
    ),
    "red_team": (
        ("table", "attack-register"),
        ("table", "baseline-ladder"),
        ("table", "alternative-explanations"),
        ("table", "evidence-independence"),
        ("table", "capability-scale"),
        ("table", "bio-inspired-audit"),
        ("table", "kill-criteria"),
        ("section", "decision-impact"),
    ),
    "decision_log": (
        ("table", "decisions"),
        ("table", "revisions"),
        ("table", "open-uncertainty"),
        ("table", "next-actions"),
    ),
    "focus_scope": (
        ("section", "parent-lineage"),
        ("section", "exact-question"),
        ("table", "local-alternatives"),
        ("table", "direct-neighbors"),
        ("section", "local-coverage-gate"),
    ),
    "claim_mechanism_map": (
        ("section", "focus-synthesis"),
        ("table", "claim-null-test-threshold"),
        ("table", "competing-hypotheses"),
        ("table", "causal-chain"),
        ("section", "sota-families"),
        ("section", "bio-inspired-translation"),
    ),
    "route_protocol": (
        ("table", "focus-routes"),
        ("table", "staged-execution"),
        ("table", "outcome-interpretation"),
        ("section", "route-boundaries"),
    ),
    "audit_scope": (
        ("section", "audit-decision"),
    ),
    "claim_register": (
        ("table", "claim-register"),
        ("table", "claim-dependencies"),
        ("section", "audit-priority"),
    ),
    "confidence_assessment": (
        ("table", "confidence-assessment"),
        ("section", "confidence-caps"),
        ("table", "allowed-wording"),
    ),
    "gap_plan": (
        ("table", "evidence-gaps"),
        ("table", "supplementary-plan"),
        ("section", "parent-implications"),
        ("section", "residual-uncertainty"),
    ),
    "artifact_inventory": (
        ("table", "artifact-inventory"),
        ("section", "manifest-lineage-audit"),
        ("section", "missing-extra-artifacts"),
    ),
    "traceability_audit": (
        ("table", "id-closure"),
        ("table", "citation-closure"),
        ("section", "dangling-references"),
    ),
    "evidence_audit": (
        ("table", "audited-claims"),
        ("table", "confidence-violations"),
        ("table", "contradictions"),
    ),
    "reasoning_audit": (
        ("section", "problem-timing-audit"),
        ("section", "causal-audit"),
        ("section", "cross-scale-audit"),
        ("section", "open-position-audit"),
        ("section", "bio-inspired-audit"),
    ),
    "route_verdicts": (
        ("table", "route-verdicts"),
        ("table", "remediation-plan"),
        ("section", "stop-conditions"),
        ("section", "report-impact"),
    ),
}

MODE_ROLE_MARKERS: Mapping[tuple[str, str], tuple[tuple[str, str], ...]] = {
    ("evidence-audit", "audit_scope"): (
        ("section", "parent-mutation-policy"),
        ("section", "target-claims"),
        ("section", "evidence-requirements"),
    ),
    ("run-audit", "audit_scope"): (
        ("section", "parent-snapshot"),
        ("section", "mutation-policy"),
    ),
}

WORKFLOW_ROLE_MARKERS: Mapping[
    str, Mapping[str, tuple[tuple[str, str], ...]]
] = {
    "deep-reading-handoff-v2": {
        "evidence_matrix": (("table", "deep-reading-handoff"),),
    },
    "opportunity-gates-v2": {
        "candidate_portfolio": (("table", "opportunity-gates"),),
        "route_protocol": (("table", "opportunity-gates"),),
    },
    "coverage-tension-v2": {
        "search_log": (("table", "coverage-audit"),),
    },
    "route-fast-pilot-v2": {
        "candidate_portfolio": (("table", "route-fast-pilots"),),
        "route_protocol": (("table", "route-fast-pilots"),),
    },
}


# Exact, ordered working-artifact table schemas.  A marker may be rom-section
# when it owns a table, but its header contract is still exact.
EXACT_TABLE_HEADERS: Mapping[str, tuple[tuple[str, ...], ...]] = {
    "problem-adequacy": (("Dimension", "Bounded statement", "Evidence or observation", "Counterargument", "Decision implication"),),
    "capability-passport": (("Capability ID", "Capability module", "Epistemic state: Observed/Reported/Assumed/Unknown", "Readiness: Ready/Adaptable/Collaborator/Unavailable", "Source or evidence", "Lead time/dependency"),),
    "constraints": (("Constraint", "Value/regime", "Hard or soft", "Consequence"),),
    "scale-boundary": (("Starting evidence level", "Highest currently justified conclusion", "Forbidden extrapolation", "Required bridge"),),
    "unknowns": (("Unknown", "Why it matters", "Resolution action", "Deadline"),),
    "breadth-branches": (("Branch ID", "Bottleneck family", "Desired function/state", "Application context", "Missing primitive/knowledge", "Mechanism families", "Outside favorite family: yes/no", "Representative Evidence IDs", "Disconfirm Query ID", "Disposition"),),
    "breadth-summary": (("Metric", "Declared count", "Minimum", "Status"),),
    "frontier-radar": (("Frontier cluster", "Recent authoritative synthesis Evidence ID", "Representative primary Evidence ID", "Salience signal/source/as-of", "Why it matters now", "Credibility caveat"),),
    "gray-space-mismatch": (("Mismatch ID", "Mature need positive Evidence IDs", "Candidate mechanism positive Evidence IDs", "Bounded neighbor-miss Query ID", "Adjacent terminology checked", "Falsifiable interface", "Status"),),
    "search-queries": (("Query ID", "Date", "Task mode", "Discovery lens", "Search lane", "Source/database", "Exact query and filters", "Purpose", "Results", "Screened/selected", "Evidence IDs", "Miss/limitation", "Stop or next-query decision"),),
    "frontier-signals": (("Evidence ID", "Signal type", "Value or unavailable", "Source", "As-of date", "Field/year normalized: yes/no/unavailable", "Use in decision"),),
    "seed-expansion": (("Seed Evidence ID", "Relation explored", "Records selected", "New Evidence IDs", "Coverage note"),),
    "atomic-claims": (("Claim ID", "Claim type", "Atomic bounded claim", "Scope/regime", "Epistemic label", "Decision critical: yes/no", "Status", "Parent Claim ID"),),
    "evidence-records": (
        ("Evidence ID", "Claim IDs", "Source role", "Stance", "Directness", "Study/source type", "Publication status", "Core contribution", "Exact supported/limited claim", "Scope/regime", "Method-validity note", "Independence/replication", "Source metadata", "DOI or stable URL", "Provenance locator", "Full-context status", "Verification", "Frontier signal", "Citation signal/source/as-of", "Reader ref"),
        ("Evidence ID", "Claim IDs", "Source role", "Stance", "Directness", "Study/source type", "Publication status", "Core contribution", "Exact supported/limited claim", "Scope/regime", "Method-validity note", "Independence/replication", "Source metadata", "DOI or stable URL", "Provenance locator", "Full-context status", "verification_depth", "Verification", "Canonical cross-run ref", "Frontier signal", "Citation signal/source/as-of", "Reader ref"),
    ),
    "deep-reading-handoff": (("Deep-read request ID", "Paper key", "Target Claim/Route IDs", "Decision-changing question", "Priority: high/medium/low", "Status: queued/in-progress/imported/blocked/skipped", "Deep Reading run", "Canonical refs", "Imported Evidence IDs", "Blocker or import decision"),),
    "claim-confidence": (("Claim ID", "Required evidence roles", "Supporting Evidence IDs", "Limiting Evidence IDs", "Directness summary", "Full-context status", "Method validity", "Independence/replication", "Consistency/conflict status", "Applicability", "Confidence: High/Moderate/Low/Insufficient", "Active cap codes", "Cap/downgrade reason", "Allowed wording", "Upgrade evidence/action", "Overturn condition"),),
    "contradictions": (
        ("Claim ID", "Supporting Evidence IDs", "Contradicting/limiting Evidence IDs", "Independence", "Tension type: direct-conflict/evidence-gap/condition-difference", "Condition delta", "Adjudication: support-dominant/limit-dominant/condition-split/unresolved", "Current interpretation", "Resolution action", "Decision ID"),
        ("Claim ID", "Supporting Evidence IDs", "Contradicting/limiting Evidence IDs", "Independence", "Current interpretation", "Resolution action", "Decision ID"),
        ("Claim ID", "Supporting Evidence IDs", "Contradicting/limiting Evidence IDs", "Independence", "Condition delta", "Adjudication: support-dominant/limit-dominant/condition-split/unresolved", "Current interpretation", "Resolution action", "Decision ID"),
        ("Claim ID", "Direct conflict", "Same-team dependence", "Unresolved applicability gap", "Consequence", "Resolution action", "Decision ID"),
    ),
    "persistent-bottlenecks": (("Bottleneck Claim ID", "Desired function/state", "Regime", "Why it persists", "Strongest current baseline", "Supporting Evidence IDs", "Confidence"),),
    "sota-families": (
        ("Approach family", "Core idea", "Best demonstrated regime", "Enabling assumption", "Strongest Evidence IDs", "Unresolved failure mode", "Why the persistent bottleneck remains"),
        ("Approach family", "Best demonstrated regime", "Enabling assumption", "Strongest Evidence IDs", "Failure mode", "Why the bottleneck remains"),
    ),
    "mapping-lattice": (("Decision context", "Desired function/observable", "Persistent bottleneck", "Missing controllable primitive/knowledge", "Falsifiable mechanism", "Implementation/process route", "Discriminating test", "Bounded conclusion", "Evidence IDs"),),
    "mechanism-definitions": (("Mechanism ID", "Physical/causal state variable", "Control", "Readout", "Governing dynamics", "Timescale/regime", "Failure modes", "Evidence IDs"),),
    "open-interfaces": (("Interface ID", "Layers joined", "Unresolved falsifiable question", "Two-sided positive Evidence IDs", "Direct-neighbor Query ID", "Bounded miss Query ID", "Crowding class", "Candidate ID"),),
    "bio-inspired-translation": (("Biological observation", "Abstract computational principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological strong baseline", "Principle-specific ablation", "Measurable intrinsic gain and boundary"),),
    "uncertainty-register": (("Uncertainty", "Affected claim/route", "Current bound", "Resolution search/experiment", "Reversal condition", "Decision ID"),),
    "shared-platform": (("Platform module", "Reused by Candidate IDs", "Current capability state", "New dependency", "Retained value if flagship fails"),),
    "candidate-routes": (("Candidate ID", "Risk: low/medium/high", "What", "Why: sufficiency/necessity/timing", "Need to know", "How", "What we learn", "Strongest baseline", "Competing hypotheses", "Positive outcome", "Negative outcome", "Ambiguous outcome", "Three-month decisive test", "Quantitative threshold", "Kill criterion", "One-year platform path", "Retained value", "Evidence IDs", "Reversal condition"),),
    "scorecard": (("Candidate ID", "Persistence", "Mechanism depth", "Capability transfer", "First-data feasibility", "Platform leverage", "Open-interface evidence", "System value", "Dependency penalty", "Written rationale"),),
    "rejected-routes": (("Candidate ID", "Why initially attractive", "Decisive objection", "Evidence IDs", "Verdict: Downgrade/Revise/Kill", "Decision ID", "Reconsideration condition"),),
    "opportunity-gates": (("Candidate ID", "Openness gate: pass/conditional/fail/unknown", "Contribution gate: pass/conditional/fail/unknown", "Feasibility gate: pass/conditional/fail/unknown", "Overall: go/conditional-go/defer/no-go", "Recall caveat", "Gate Evidence IDs", "Binding condition or next check"),),
    "route-fast-pilots": (("Candidate ID", "Rank: 1-3", "Hypothesis A", "Hypothesis B", "Discriminating test", "Observable", "Horizon days: 1-14", "Resource cap", "Advance threshold", "Kill or revise threshold"),),
    "coverage-audit": (("Lane", "Query IDs", "Relevant Evidence IDs", "Coverage status: covered/thin/query-failed/out-of-scope", "Blind spot or failure mode", "Next query or stop rationale"),),
    "attack-register": (("Attack ID", "Target claim/route", "Attack surface", "Strongest objection", "Evidence IDs or test", "Severity: low/medium/high/blocking", "Required repair or discriminating test", "Verdict: Keep/Downgrade/Revise/Kill", "Decision ID", "Status"),),
    "baseline-ladder": (("Target claim/route", "Material/device baseline", "Control-disabled baseline", "Alternative mechanism", "Circuit/digital or conventional baseline", "End-to-end baseline", "Missing comparison", "Decision impact"),),
    "alternative-explanations": (("Target claim/route", "Observable", "Preferred mechanism", "Alternative explanation", "Discriminating control", "Expected signatures", "Decision rule", "Threshold"),),
    "evidence-independence": (("Claim ID", "Single-source/team risk", "Full-context gap", "Replication gap", "Direct conflict", "Confidence cap", "Required evidence", "Decision ID"),),
    "capability-scale": (("Target claim/route", "Starting evidence scale", "Claimed destination scale", "Missing bridge", "Capability ID/state", "PVT/variation/yield/reliability or analogous cost", "Verdict", "Decision ID"),),
    "bio-inspired-audit": (
        ("Target", "Biological observation", "Abstract principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological baseline", "Principle-specific ablation", "Intrinsic gain/boundary", "Verdict", "Decision ID"),
    ),
    "kill-criteria": (("Target claim/route", "Kill criterion", "Quantitative threshold", "Earliest test", "Consequence", "Fallback/retained asset", "Decision ID"),),
    "decisions": (("Decision ID", "Date", "Target ID", "Affected decision target IDs", "Status: Keep/Downgrade/Revise/Kill", "Decision", "Evidence IDs", "Inference", "Alternative", "Trigger Attack IDs", "Reversal condition", "Owner/next action"),),
    "revisions": (("Target ID", "Previous position", "Trigger Evidence/Attack IDs", "Revised position", "Report section changed", "Knowledge retained"),),
    "open-uncertainty": (("Uncertainty", "Priority", "Affected IDs", "Resolution action", "Owner", "Due date"),),
    "next-actions": (("Action", "Type: search/experiment/model/collaboration", "Dependency", "Deliverable", "Decision enabled"),),
    "target-claims": (("Claim ID", "Claim type", "Atomic bounded claim", "Scope/regime", "Decision critical: yes/no", "Existing confidence", "Parent source"),),
    "evidence-requirements": (("Claim ID", "Required evidence roles", "Required directness/context", "Independence need", "Critical missing role", "Completion rule"),),
    "claim-register": (("Claim ID", "Claim type", "Atomic bounded claim", "Scope/regime", "Decision importance", "Required evidence roles", "Current Evidence IDs", "Missing role", "Audit priority", "Parent Claim ID"),),
    "claim-dependencies": (("Upstream Claim ID", "Downstream Claim ID", "Dependency type", "Failure consequence", "Test/search to break dependency"),),
    "confidence-assessment": (("Claim ID", "Supporting Evidence IDs", "Limiting Evidence IDs", "Directness", "Full-context status", "Method/design validity", "Independence/replication", "Consistency/conflict", "Applicability", "Confidence: High/Moderate/Low/Insufficient", "Active cap codes", "Cap/downgrade reason", "Allowed wording", "Upgrade action/evidence", "Overturn condition", "Parent impact"),),
    "allowed-wording": (("Claim ID", "Allowed wording", "Forbidden wording", "Evidence boundary", "Required report change", "Decision ID"),),
    "evidence-gaps": (("Gap ID", "Claim ID", "Missing evidence role", "Why decision-critical", "Cheapest resolving search/test", "Priority", "Stop rule"),),
    "supplementary-plan": (("Gap ID", "Query IDs", "Source priority", "Direct neighbor/baseline/negative target", "Expected upgrade or downgrade", "Completion state"),),
    "parent-implications": (("Parent claim/route", "Previous wording/status", "Audited wording/status", "Verdict: Keep/Downgrade/Revise/Kill", "Decision ID", "Parent left unchanged: yes/no"),),
    "parent-lineage": (("Parent run ID", "Selected branch/node", "Inherited Claim IDs", "Inherited Evidence IDs", "Inherited Capability IDs", "Snapshot limitation"),),
    "local-alternatives": (("Alternative ID", "Role: primary/comparator/fallback/neighbor", "Mechanism or approach", "What it shares", "What differs causally", "Strongest baseline", "Evidence IDs", "Disposition"),),
    "direct-neighbors": (("Neighbor", "Overlap", "Causal difference", "Same interface: yes/no", "Evidence ID", "Crowding class", "Implication"),),
    "claim-null-test-threshold": (("Candidate ID", "Claim ID", "Falsifiable claim", "Null hypothesis", "Manipulated control", "Observable/readout", "Strongest baseline", "Test", "Quantitative threshold", "Kill consequence", "Evidence IDs"),),
    "competing-hypotheses": (("Hypothesis ID", "Mechanism", "Predicted signature", "Alternative signature", "Discriminating control", "Ambiguity remaining", "Decision rule"),),
    "causal-chain": (("Step", "State/quantity", "Control", "Readout", "Governing relation", "Evidence level", "Required bridge", "Forbidden inference"),),
    "focus-routes": (("Candidate ID", "Route role: primary/comparator/fallback", "What", "Why", "Need to know", "How", "What we learn", "Strongest baseline", "Competing hypotheses", "Evidence IDs"),),
    "staged-execution": (("Stage", "Route", "Action", "Required evidence", "Quantitative pass threshold", "Kill/revise threshold", "Dependency", "Retained asset"),),
    "outcome-interpretation": (("Candidate ID", "Outcome class: positive/negative/ambiguous", "Observable pattern", "Allowed conclusion", "Forbidden conclusion", "Next action", "Decision ID"),),
    "route-boundaries": (("Candidate ID", "Kill criterion", "Reversal condition", "Retained value after failure", "Comparator/fallback activation rule"),),
    "parent-snapshot": (("Parent run ID", "Workspace-relative manifest reference", "Manifest SHA-256", "Selected artifacts/hashes", "Schema", "Audit boundary"),),
    "artifact-inventory": (("Artifact ID", "Manifest role", "Workspace-relative file", "Declared: yes/no", "Exists: yes/no", "SHA-256", "Schema/contract", "Status"),),
    "manifest-lineage-audit": (("Check", "Evidence", "Result: pass/fail/uncertain", "Severity", "Required repair", "Decision ID"),),
    "missing-extra-artifacts": (("File/role", "Missing/extra/undeclared", "Why it matters", "Exact repair", "Decision ID"),),
    "id-closure": (("ID", "Type", "Defined in", "Referenced in", "Dangling/duplicate/mismatch", "Severity", "Repair", "Decision ID"),),
    "citation-closure": (("Reader reference", "Report DOI/stable URL", "Evidence ID", "Evidence-matrix DOI/stable URL", "Match: yes/no", "Computed status", "Repair", "Decision ID"),),
    "dangling-references": (("Finding ID", "Claim/report location", "Missing definition/source/locator", "Decision consequence", "Repair", "Decision ID"),),
    "audited-claims": (("Claim ID", "Claim type", "Parent wording", "Supporting Evidence IDs", "Limiting Evidence IDs", "Full-context direct support", "Independent replication", "Current justified confidence", "Audit verdict"),),
    "confidence-violations": (("Finding ID", "Claim ID", "Claimed confidence", "Active cap codes", "Evidence basis", "Exact allowed wording", "Decision ID"),),
    "problem-timing-audit": (("Dimension", "Parent claim", "Strongest objection", "Evidence/test", "Verdict", "Decision ID"),),
    "causal-audit": (("Claim/route ID", "Preferred mechanism", "Strongest alternative", "Discriminating control present: yes/no", "Threshold present: yes/no", "Verdict", "Decision ID"),),
    "cross-scale-audit": (("Claim/route ID", "Starting evidence scale", "Claimed scale", "Missing bridge", "Capability state", "System/manufacturing cost omitted", "Verdict", "Decision ID"),),
    "open-position-audit": (("Claim ID", "Two-sided positive evidence", "Bounded neighbor search", "Zero-hit overclaim", "Adjacent terminology", "Justified class", "Verdict", "Decision ID"),),
    "route-verdicts": (("Route/claim ID", "Parent status", "Strongest finding", "Severity", "Verdict: Keep/Downgrade/Revise/Kill", "Allowed current conclusion", "Required repair", "Decision ID"),),
    "remediation-plan": (("Repair ID", "Affected artifact/section", "Exact change", "Dependency", "Verification command/gate", "Owner", "Status"),),
    "stop-conditions": (("Route/claim ID", "Stop condition", "Re-entry evidence", "Retained knowledge/asset", "Next decision date"),),
}


READER_TABLE_HEADERS: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "landscape": {
        "decision-summary": ("Risk tier", "Recommended route", "Causal interface", "Three-month decisive evidence", "One-year platform value", "Disposition", "Decision ID"),
        "scope": ("Scope item", "Declared boundary"),
        "necessity-timing": ("Dimension", "Bounded favorable argument", "Strongest counterargument", "Evidence or capability basis", "Decision implication"),
        "need-to-know": ("State/structure", "Causal mechanism", "Scale/regime", "Readout/metric", "Evidence boundary"),
        "sota-families": ("Approach family", "What it solves", "Best demonstrated regime", "Enabling assumption", "Strongest evidence", "Residual failure mode", "Why the root bottleneck remains"),
        "bio-inspired-translation": ("Biological observation", "Abstract computational principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological strong baseline", "Principle-specific ablation", "Measurable intrinsic gain and boundary"),
        "recommended-routes": ("Route", "What", "Why", "Need to know", "How: existing base→new control→measurement", "What we learn", "Strongest baseline", "Competing hypotheses", "Positive outcome", "Negative outcome", "Ambiguous outcome", "Kill criterion", "Retained value after failure", "Reversal condition"),
        "execution": ("Route", "Horizon", "Method, controls, and parameter boundary", "Pass threshold", "Kill/Revise condition", "Retained asset"),
        "outcome-interpretation": ("Route", "Outcome", "Observable", "Allowed conclusion", "Forbidden extrapolation", "Next action"),
        "evidence-confidence": ("Claim", "Confidence", "Active cap codes", "Downgrade reason", "Allowed wording", "Upgrade/overturn condition"),
        "red-team-impact": ("Attack ID", "Target ID", "Attack surface", "Strongest objection", "Severity", "Verdict", "Status", "Exact repair", "Decision ID"),
    },
    "focus": {
        "lineage": ("Scope item", "Declared boundary"),
        "necessity-timing": ("Dimension", "Bounded favorable argument", "Strongest counterargument", "Evidence or capability basis", "Decision implication"),
        "sota-families": ("Approach family", "What it solves", "Best demonstrated regime", "Strongest evidence", "Enabling assumption", "What remains", "Why the bottleneck persists"),
        "bounded-open-position": ("Positive evidence on both sides", "Closest direct neighbors", "Adjacent terminology/modules", "Database/date/access boundary", "Unclosed falsifiable interface", "Allowed wording"),
        "bio-inspired-translation": ("Biological observation", "Abstract computational principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological strong baseline", "Principle-specific ablation", "Measurable intrinsic gain and boundary"),
        "recommended-routes": ("Role", "Route", "What", "Why", "Need to know", "How", "What we learn", "Strongest baseline", "Competing hypotheses", "Positive outcome", "Negative outcome", "Ambiguous outcome", "Kill criterion", "Retained value after failure", "Reversal condition", "Disposition", "Decision ID"),
        "execution": ("Route", "Stage", "Action/method", "Baseline/controls", "Pass threshold", "Kill/Revise", "Retained value"),
        "outcome-interpretation": ("Route", "Outcome", "Signal", "Allowed conclusion", "Forbidden conclusion", "Next action"),
        "evidence-confidence": ("Claim", "Confidence", "Active cap codes", "Cap reason", "Allowed wording", "Upgrade/overturn"),
        "red-team-impact": ("Attack ID", "Target ID", "Attack surface", "Strongest objection", "Severity", "Verdict", "Status", "Exact repair", "Decision ID"),
    },
    "evidence-audit": {
        "audit-scope": ("Scope item", "Declared boundary"),
        "claim-verdicts": ("Claim", "Previous wording", "Evidence found", "Limiting/contradicting evidence", "Confidence", "Active cap codes", "Allowed wording", "Parent impact", "Decision ID"),
        "evidence-confidence": ("Claim", "Directness", "Full context", "Method validity", "Independence", "Applicability", "Conflict", "Cap reason"),
        "bio-inspired-audit": ("Target", "Biological observation", "Abstract principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological baseline", "Principle-specific ablation", "Intrinsic gain/boundary", "Verdict", "Decision ID"),
        "gap-plan": ("Claim", "Missing role", "Cheapest next search/test", "Upgrade condition", "Overturn condition", "Stop rule"),
        "red-team-impact": ("Attack ID", "Target ID", "Attack surface", "Strongest objection", "Severity", "Verdict", "Status", "Exact repair", "Decision ID"),
    },
    "run-audit": {
        "audited-snapshot": ("Scope item", "Declared boundary"),
        "integrity": ("Finding", "Evidence", "Severity", "Verdict", "Repair", "Decision ID"),
        "scientific-red-team": ("Finding ID", "Claim", "Parent confidence", "Active cap codes", "Justified confidence", "Verdict", "Decision ID"),
        "bio-inspired-audit": ("Target", "Biological observation", "Abstract principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological baseline", "Principle-specific ablation", "Intrinsic gain/boundary", "Verdict", "Decision ID"),
        "route-verdicts": ("Route/claim", "Parent status", "Strongest objection", "Verdict", "Allowed conclusion", "Required repair", "Stop/re-entry condition", "Decision ID"),
        "red-team-impact": ("Attack ID", "Target ID", "Attack surface", "Strongest objection", "Severity", "Verdict", "Status", "Exact repair", "Decision ID"),
    },
}

ZH_READER_TABLE_HEADER_OVERRIDES: Mapping[str, Mapping[str, tuple[str, ...]]] = {
    "landscape": {
        "decision-summary": ("风险层级", "推荐路线", "核心因果接口", "三个月决定性证据", "一年平台价值", "当前处置", "Decision ID"),
        "scope": ("范围项", "明确边界"),
        "necessity-timing": ("维度", "有边界的正面论证", "最强反方观点", "证据或能力依据", "对决策的影响"),
        "need-to-know": ("状态/结构", "因果机制", "尺度/工作区间", "读出与指标", "证据边界"),
        "sota-families": ("Approach family", "已解决什么", "最佳证明区间", "关键假设", "最强证据", "残余失败模式", "为什么根瓶颈仍存在"),
        "recommended-routes": ("路线", "What：大白话做什么", "Why：为什么做", "Need to know", "How：已有基础→新控制→测量", "What we learn", "最强基线", "竞争假设", "Positive 结果", "Negative 结果", "Ambiguous 结果", "Kill criterion", "失败后保留价值", "反转条件"),
        "execution": ("Route", "阶段", "方法、对照和参数边界", "通过阈值", "Kill/Revise 条件", "失败后保留资产"),
        "outcome-interpretation": ("Route", "结果类型", "可观测结果", "允许结论", "禁止外推", "下一步"),
        "evidence-confidence": ("Claim", "Confidence", "Active cap codes", "降级原因", "允许措辞", "升级/推翻条件"),
    },
    "focus": {
        "lineage": ("范围项", "明确边界"),
        "necessity-timing": ("维度", "有边界的正面论证", "最强反方观点", "证据或能力依据", "对决策的影响"),
        "sota-families": ("方法族", "已解决什么", "最佳证明区间", "最强证据", "关键假设", "尚未解决什么", "根瓶颈为何持续"),
        "bounded-open-position": ("两侧正证据", "最近直接近邻", "相邻术语与模块", "数据库/日期/访问边界", "尚未闭合的可证伪接口", "允许措辞"),
        "recommended-routes": ("角色", "路线", "What", "Why", "Need to know", "How", "What we learn", "最强基线", "竞争假设", "Positive 结果", "Negative 结果", "Ambiguous 结果", "Kill criterion", "失败后保留价值", "反转条件", "当前处置", "Decision ID"),
        "execution": ("Route", "阶段", "操作与方法", "Baseline/controls", "通过阈值", "Kill/Revise", "保留价值"),
        "outcome-interpretation": ("Route", "结果", "信号", "允许结论", "禁止结论", "下一动作"),
    },
    "evidence-audit": {
        "audit-scope": ("范围项", "明确边界"),
        "claim-verdicts": ("Claim", "原表述", "Evidence found", "Limiting/contradicting evidence", "Confidence", "Active cap codes", "Allowed wording", "Parent impact", "Decision ID"),
    },
    "run-audit": {
        "audited-snapshot": ("范围项", "明确边界"),
    },
}

REPORT_MARKERS: Mapping[str, tuple[str, ...]] = {
    "landscape": (
        "decision-summary", "scope", "background-question", "necessity-timing",
        "need-to-know", "persistent-bottleneck", "sota-families",
        "bounded-open-position", "bio-inspired-translation", "recommended-routes",
        "baseline-hypotheses", "execution", "outcome-interpretation",
        "evidence-confidence", "red-team-impact", "reversal",
        "references",
    ),
    "focus": (
        "decision-summary", "lineage", "background-question", "necessity-timing",
        "need-to-know", "sota-families", "bounded-open-position",
        "bio-inspired-translation", "recommended-routes", "baseline-hypotheses",
        "execution", "outcome-interpretation", "evidence-confidence",
        "red-team-impact", "references",
    ),
    "evidence-audit": (
        "decision-summary", "audit-scope", "claim-verdicts", "evidence-confidence",
        "supplemental-search", "bio-inspired-audit", "allowed-wording", "gap-plan",
        "decisions", "red-team-impact", "references",
    ),
    "run-audit": (
        "decision-summary", "audited-snapshot", "integrity", "scientific-red-team",
        "capability-cross-scale", "open-position-bio", "bio-inspired-audit",
        "route-verdicts", "red-team-impact", "remediation",
        "residual-uncertainty", "references",
    ),
}


# An additive reader presentation, not a scientific schema or release dispatcher.
# Human headings inside scientific-argument / audit-findings are unconstrained.
NARRATIVE_REPORT_MARKERS = {
    mode: ("decision-summary",
           "scientific-argument" if mode in {"landscape", "focus"} else "audit-findings",
           "audit-appendix", "references")
    for mode in REPORT_MARKERS
}
NARRATIVE_PROJECTION_NAMES = {
    "landscape": ("decision-summary", "recommended-routes", "execution",
                  "outcome-interpretation", "evidence-confidence",
                  "bio-inspired-translation", "red-team-impact"),
    "focus": ("recommended-routes", "execution", "outcome-interpretation",
              "evidence-confidence", "bio-inspired-translation", "red-team-impact"),
    "evidence-audit": ("claim-verdicts", "evidence-confidence", "gap-plan",
                       "bio-inspired-audit", "red-team-impact"),
    "run-audit": ("integrity", "scientific-red-team", "route-verdicts",
                  "bio-inspired-audit", "red-team-impact"),
}


def _reader_markers(reader: V2Document, mode: str) -> tuple[str, ...]:
    return (NARRATIVE_REPORT_MARKERS if reader.narrative_layout else REPORT_MARKERS)[mode]


def _has_reader_prose(block: V2Block) -> bool:
    # Presence/ownership guard, never a quality score, word quota or truth test.
    return any(
        _meaningful(line.text.strip())
        for line in block.lines
        if not line.text.lstrip().startswith(("#", "|", "<", "> [!"))
    )


def _block_has_substance(block: V2Block) -> bool:
    for line in block.lines:
        stripped = line.text.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("|") and re.fullmatch(r"[|:\-\s]+", stripped):
            continue
        if _meaningful(stripped):
            return True
    return False


EMPTY_COLLECTION_TABLES = frozenset({
    "candidate-routes", "shared-platform", "scorecard", "rejected-routes",
    "opportunity-gates", "route-fast-pilots", "deep-reading-handoff",
    "recommended-routes", "execution", "outcome-interpretation",
    "decision-summary", "local-alternatives", "focus-routes", "staged-execution",
    "route-boundaries", "claim-null-test-threshold",
})


def _validate_document_contract(
    report: Report,
    document: V2Document,
    markers: Iterable[tuple[str, str]],
    *,
    header_registry: Mapping[str, tuple[tuple[str, ...], ...]] | None = EXACT_TABLE_HEADERS,
) -> None:
    for error in document.errors:
        report.errors.append(f"{document.path.name}: {error}")
    for expected_kind, name in markers:
        block = document.blocks.get(name)
        report.check(
            block is not None,
            f"{document.path.name}: rom marker {name} exists",
            f"{document.path.name}: missing rom-{expected_kind} marker {name}",
        )
        if block is None:
            continue
        report.check(
            block.kind == expected_kind,
            f"{document.path.name}: marker {name} has type {expected_kind}",
            f"{document.path.name}: marker {name} must be rom-{expected_kind}, got rom-{block.kind}",
        )
        report.check(
            _block_has_substance(block),
            f"{document.path.name}: marker {name} has substantive visible content",
            f"{document.path.name}: marker {name} has no substantive visible content",
        )
        table_is_required = expected_kind == "table" or (
            header_registry is not None and name in header_registry
        )
        if table_is_required:
            table = document.table(name)
            assert table is not None
            for error in table.errors:
                report.errors.append(f"{document.path.name}: {name}: {error}")
            report.check(
                bool(table.rows) or name in EMPTY_COLLECTION_TABLES,
                f"{document.path.name}: table {name} has data rows",
                f"{document.path.name}: table {name} has no data rows",
            )
            if header_registry is not None and name in header_registry:
                allowed_headers = header_registry[name]
                report.check(
                    tuple(table.headers) in allowed_headers,
                    f"{document.path.name}: table {name} uses the exact registered header",
                    f"{document.path.name}: table {name} header must exactly match a registered schema; "
                    f"got {tuple(table.headers)!r}",
                )
            for row_number, row in zip(table.row_lines, table.rows):
                report.check(
                    len(row) == len(table.headers),
                    f"{document.path.name}:{row_number}: table width is valid",
                    f"{document.path.name}:{row_number}: table row width does not match header",
                )
                if len(row) == len(table.headers):
                    empty = [
                        table.headers[index]
                        for index, value in enumerate(row)
                        if not _meaningful(value)
                    ]
                    report.check(
                        not empty,
                        f"{document.path.name}:{row_number}: table row has substantive values",
                        f"{document.path.name}:{row_number}: non-substantive cells: {', '.join(empty)}",
                    )


INTERNAL_RETRIEVAL_ID = re.compile(
    r"\b(?:doc_id|chunk_id|retrieval_id|retrieval_trace|source_node_id|"
    r"item_key|attachment_key)\b\s*[:=]|"
    r"\bturn\d+(?:search|fetch|view)\d+\b|"
    r"\bzotero\s+(?:item|attachment)\s+key\b|"
    r"\boffset\s*[:=]\s*\d+\b",
    re.IGNORECASE,
)


def _validate_reader_contract(
    report: Report,
    reader: V2Document,
    *,
    mode: str,
) -> None:
    expected_markers = _reader_markers(reader, mode)
    actual_markers = tuple(reader.blocks)
    report.check(
        actual_markers == expected_markers,
        "Reader markers use the exact required set and order",
        "Reader marker set/order mismatch; expected "
        f"{expected_markers!r}, got {actual_markers!r}",
    )

    table_headers = READER_TABLE_HEADERS[mode]
    if reader.narrative_layout:
        expected_projections = set(NARRATIVE_PROJECTION_NAMES[mode])
        report.check(
            set(reader.projections) == expected_projections,
            "Narrative reader retains all required audit projections",
            f"Reader audit projection set mismatch; expected {sorted(expected_projections)!r}, "
            f"got {sorted(reader.projections)!r}",
        )
        table_headers = {name: table_headers[name] for name in NARRATIVE_PROJECTION_NAMES[mode]}
        argument = reader.blocks.get(expected_markers[1])
        report.check(
            argument is not None and _has_reader_prose(argument),
            "Reader contains argument prose outside tables",
            "Reader argument needs visible prose; tables, headings and comments cannot replace explanation",
        )
        for name, projection in reader.projections.items():
            separators = sum(
                bool(re.fullmatch(r"\s*\|[|:\-\s]+\|\s*", line.text))
                for line in projection.lines
            )
            report.check(
                separators == 1,
                f"Reader projection {name} contains one unambiguous table",
                f"Reader projection {name} must contain exactly one table; put comparison tables in the argument",
            )
        if mode not in {"landscape", "focus"}:
            report.check(not reader.route_blocks, "Audit findings do not invent route ownership",
                         "Audit report must use verdict findings, not rom-route blocks")
    else:
        report.check(not reader.projections and not reader.route_blocks,
                     "Legacy reader uses its original section/table contract",
                     "rom-projection/rom-route requires the narrative reader envelope")

    for name, expected_headers in table_headers.items():
        table = reader.table(name)
        table_present = table is not None and bool(table.headers)
        report.check(
            table_present,
            f"Reader contains required structured table {name}",
            f"Reader marker {name} must contain its required structured table",
        )
        if table is None or not table.headers:
            continue
        for error in table.errors:
            report.errors.append(f"{reader.path.name}: {name}: {error}")
        registered_headers = {expected_headers}
        if mode == "landscape" and name == "decision-summary":
            registered_headers.add(("Claim", "Disposition", "Decision ID"))
        if name == "recommended-routes" and mode in {"landscape", "focus"}:
            registered_headers.add(("Route", "Summary", "Disposition", "Decision ID") if mode == "landscape"
                                   else ("Role", "Route", "Summary", "Disposition", "Decision ID"))
        localized = ZH_READER_TABLE_HEADER_OVERRIDES.get(mode, {}).get(name)
        if localized is not None:
            registered_headers.add(localized)
        report.check(
            tuple(table.headers) in registered_headers,
            f"Reader table {name} uses the exact registered header",
            f"Reader table {name} header must exactly match a registered English or zh-CN schema {sorted(registered_headers)!r}; "
            f"got {tuple(table.headers)!r}",
        )
        report.check(
            bool(table.rows) or name in EMPTY_COLLECTION_TABLES,
            f"Reader table {name} has data rows",
            f"Reader table {name} has no data rows",
        )
        for row_number, row in zip(table.row_lines, table.rows):
            report.check(
                len(row) == len(table.headers)
                and all(_meaningful(value) for value in row),
                f"{reader.path.name}:{row_number}: reader table row is substantive",
                f"{reader.path.name}:{row_number}: reader table row is incomplete or non-substantive",
            )

    callouts = {
        item.upper()
        for item in re.findall(
            r"^\s*>\s*\[!(IMPORTANT|NOTE|CAUTION|WARNING)\]",
            reader.text,
            re.MULTILINE | re.IGNORECASE,
        )
    }
    expected_callouts = (
        {"IMPORTANT", "WARNING"}
        if mode == "run-audit"
        else {"IMPORTANT", "NOTE", "CAUTION"}
    )
    report.check(
        expected_callouts <= callouts,
        "Reader contains the required decision and boundary callouts",
        "Reader is missing required callouts: "
        + ", ".join(sorted(expected_callouts - callouts)),
    )
    internal_ids = sorted(set(match.group(0) for match in INTERNAL_RETRIEVAL_ID.finditer(reader.text)))
    report.check(
        not internal_ids,
        "Reader contains no internal retrieval IDs",
        "Reader exposes internal retrieval IDs: " + ", ".join(internal_ids),
    )


def _table_from_documents(
    documents: Mapping[str, V2Document], name: str
) -> V2Table | None:
    for document in documents.values():
        if name in document.blocks:
            return document.table(name)
    return None

def _table_from_role(
    documents: Mapping[str, V2Document], role: str, name: str
) -> V2Table | None:
    document = documents.get(role)
    if document is None or name not in document.blocks:
        return None
    return document.table(name)


def _tables_from_documents(
    documents: Mapping[str, V2Document], name: str
) -> list[V2Table]:
    result: list[V2Table] = []
    for document in documents.values():
        if name in document.blocks:
            table = document.table(name)
            if table is not None:
                result.append(table)
    return result


def _validate_frontier_policy(report: Report, manifest: Mapping[str, object]) -> None:
    policy = manifest.get("frontier_policy")
    report.check(
        isinstance(policy, dict),
        "Manifest declares frontier policy",
        "Schema 2.0 manifest requires a frontier_policy object",
    )
    if not isinstance(policy, dict):
        return
    recent_years = policy.get("recent_years_default")
    report.check(
        isinstance(recent_years, int) and 1 <= recent_years <= 10,
        f"Frontier policy recent window is {recent_years} years",
        "frontier_policy.recent_years_default must be an integer from 1 to 10",
    )
    report.check(
        policy.get("canonical_pre_window_allowed") is True,
        "Frontier policy permits justified canonical anchors",
        "frontier_policy must explicitly allow justified canonical pre-window anchors",
    )
    report.check(
        policy.get("citation_signal") == "field-year-normalized-when-available",
        "Citation signals are field/year normalized when available",
        "frontier_policy.citation_signal must be field-year-normalized-when-available",
    )
    report.check(
        policy.get("citation_source_and_as_of_required") is True,
        "Citation signals require source and as-of date",
        "frontier_policy must require citation-signal source and as-of date",
    )
    report.check(
        policy.get("salience_is_not_claim_confidence") is True,
        "Frontier salience is explicitly separated from claim confidence",
        "frontier_policy must state salience_is_not_claim_confidence=true",
        )


def _active_workflow_contracts(
    report: Report,
    manifest: Mapping[str, object],
    *,
    mode: str,
) -> frozenset[str]:
    raw = manifest.get("workflow_contracts")
    expected = WORKFLOW_CONTRACTS_BY_MODE[mode]
    valid_shape = (
        isinstance(raw, list)
        and all(isinstance(item, str) for item in raw)
        and len(raw) == len(set(raw))
    )
    report.check(
        valid_shape,
        "Manifest workflow_contracts is a unique string list",
        "workflow_contracts must be a unique string list",
    )
    if not valid_shape:
        return frozenset(expected)
    actual = tuple(raw)
    report.check(
        actual == expected,
        f"Manifest workflow contracts match {mode}",
        f"workflow_contracts for {mode} must be {list(expected)!r}; got {list(actual)!r}",
    )
    # A malformed declaration is an error, never permission to skip checks.
    return frozenset(expected)


def _validate_v2_manifest_metadata(
    report: Report,
    manifest: Mapping[str, object],
    *,
    mode: str,
) -> None:
    report.check(
        manifest.get("skill_version") == SKILL_VERSION,
        f"Manifest skill_version is {SKILL_VERSION}",
        f"skill_version must be {SKILL_VERSION}",
    )
    report.check(
        manifest.get("validator_version") == VALIDATOR_VERSION,
        f"Manifest validator_version is {VALIDATOR_VERSION}",
        f"validator_version must be {VALIDATOR_VERSION}",
    )
    for field_name in ("run_id", "domain", "short_task_name", "language"):
        value = manifest.get(field_name)
        report.check(
            isinstance(value, str) and bool(value.strip()),
            f"Manifest {field_name} is substantive",
            f"Manifest {field_name} must be a non-empty string",
        )

    primary_domain_lens = manifest.get("primary_domain_lens")
    secondary_domain_lenses = manifest.get("secondary_domain_lenses")
    domain_lens_notes = manifest.get("domain_lens_notes")
    report.check(
        primary_domain_lens in DOMAIN_LENSES,
        f"Primary domain lens is {primary_domain_lens}",
        f"primary_domain_lens must be one of {', '.join(DOMAIN_LENSES)}",
    )
    secondary_strings = (
        secondary_domain_lenses
        if isinstance(secondary_domain_lenses, list)
        and all(isinstance(value, str) for value in secondary_domain_lenses)
        else None
    )
    secondary_valid = (
        secondary_strings is not None
        and len(secondary_strings) == len(set(secondary_strings))
        and all(value in DOMAIN_LENSES for value in secondary_strings)
        and primary_domain_lens not in secondary_strings
    )
    report.check(
        secondary_valid,
        "Secondary domain lenses are unique registered interface lenses",
        "secondary_domain_lenses must be a unique registered list excluding the primary lens",
    )
    custom_notes_error: str | None = None
    if primary_domain_lens == "custom":
        try:
            validate_custom_domain_lens_notes(domain_lens_notes)
        except ContractError as exc:
            custom_notes_error = str(exc)
    report.check(
        primary_domain_lens != "custom" or custom_notes_error is None,
        "Custom domain lens instantiates all ten Common Lens Interface slots",
        "primary_domain_lens=custom has invalid domain_lens_notes: "
        + (custom_notes_error or "unknown error"),
    )

    created_at = manifest.get("created_at")
    try:
        parsed_created = datetime.fromisoformat(
            created_at[:-1] + "+00:00"
            if isinstance(created_at, str) and created_at.endswith("Z")
            else str(created_at)
        )
        created_valid = parsed_created.tzinfo is not None
    except ValueError:
        created_valid = False
    report.check(
        created_valid,
        "Manifest created_at is timezone-aware ISO-8601",
        "Manifest created_at must be a timezone-aware ISO-8601 timestamp",
    )

    as_of_raw = manifest.get("as_of_date")
    try:
        as_of = date.fromisoformat(str(as_of_raw))
        as_of_valid = isinstance(as_of_raw, str)
    except ValueError:
        as_of = None
        as_of_valid = False
    report.check(
        as_of_valid,
        "Manifest as_of_date uses YYYY-MM-DD",
        "Manifest as_of_date must use YYYY-MM-DD",
    )

    window = manifest.get("evidence_window")
    report.check(
        isinstance(window, dict),
        "Manifest evidence_window is an object",
        "Manifest evidence_window must be an object",
    )
    if isinstance(window, dict):
        try:
            start = date.fromisoformat(str(window.get("start")))
            end = date.fromisoformat(str(window.get("end")))
            window_as_of = date.fromisoformat(str(window.get("as_of")))
            window_valid = (
                all(isinstance(window.get(key), str) for key in ("start", "end", "as_of"))
                and start <= end <= window_as_of
                and as_of is not None
                and window_as_of == as_of
            )
        except ValueError:
            window_valid = False
        report.check(
            window_valid,
            "Evidence window dates are ordered and match as_of_date",
            "evidence_window requires ordered YYYY-MM-DD start/end/as_of matching as_of_date",
        )
        report.check(
            window.get("canonical_pre_window_allowed") is True,
            "Evidence window permits declared canonical pre-window anchors",
            "evidence_window.canonical_pre_window_allowed must be true",
        )

    routing = manifest.get("routing")
    report.check(
        isinstance(routing, dict),
        "Manifest routing is an object",
        "Manifest routing must be an object",
    )
    if isinstance(routing, dict):
        requested = routing.get("requested")
        reasons = routing.get("reason")
        confidence = routing.get("confidence")
        report.check(
            requested in REQUESTED_MODES,
            f"Routing requested mode is {requested}",
            f"routing.requested must be one of {', '.join(REQUESTED_MODES)}",
        )
        report.check(
            isinstance(reasons, list)
            and bool(reasons)
            and all(isinstance(item, str) and bool(item.strip()) for item in reasons),
            "Routing records at least one substantive reason",
            "routing.reason must be a non-empty list of substantive strings",
        )
        report.check(
            confidence in ROUTING_CONFIDENCE,
            f"Routing confidence is {confidence}",
            f"routing.confidence must be one of {', '.join(ROUTING_CONFIDENCE)}",
        )

    expected_policy = (
        "supplement-only" if mode in {"evidence-audit", "run-audit"} else "child-run-only"
    )
    report.check(
        manifest.get("parent_mutation_policy") == expected_policy,
        f"Parent mutation policy is {expected_policy}",
        f"parent_mutation_policy must be {expected_policy} for {mode}",
    )


def _validate_selected_branch(
    report: Report,
    manifest: Mapping[str, object],
    *,
    mode: str,
    external_ids: set[str],
) -> None:
    selected = manifest.get("selected_branch")
    parents = manifest.get("lineage", {}).get("parents", []) if isinstance(manifest.get("lineage"), dict) else []
    if mode != "focus":
        report.check(
            selected is None,
            "Non-focus run has no selected_branch",
            "selected_branch is reserved for focus mode",
        )
        return
    if selected is None:
        report.check(
            not parents,
            "Standalone focus may use its exact-question artifact without a selected_branch",
            "Focus with a parent run requires selected_branch",
        )
        return
    if not isinstance(selected, dict):
        report.errors.append("selected_branch must be null or an object")
        return
    branch_id = selected.get("id")
    label = selected.get("label")
    source = selected.get("source")
    exactly_one_target = (
        isinstance(branch_id, str) and bool(branch_id.strip())
    ) != (
        isinstance(label, str) and bool(label.strip())
    )
    report.check(
        exactly_one_target,
        "selected_branch defines exactly one ID or label",
        "selected_branch must define exactly one of id or label",
    )
    if parents:
        report.check(
            source == "parent"
            and isinstance(branch_id, str)
            and bool(FOCUS_TARGET_ID_PATTERN.fullmatch(branch_id))
            and branch_id in external_ids,
            "Parent focus selects a BR/C/I target present in the parent snapshot",
            "Parent focus selected_branch must be a parent BR/C/I ID with source=parent",
        )
    else:
        report.check(
            source == "standalone"
            and (
                (isinstance(branch_id, str) and bool(FOCUS_TARGET_ID_PATTERN.fullmatch(branch_id)))
                or (isinstance(label, str) and bool(label.strip()))
            ),
            "Standalone focus selected_branch has a valid ID or label",
            "Standalone focus selected_branch must have source=standalone and a valid ID or label",
        )


def _collect_authoritative_v2_ids(
    documents: Mapping[str, V2Document],
    *,
    report: Report | None = None,
    source_label: str = "run",
) -> dict[str, str]:
    definitions: dict[str, str] = {}
    for marker, (definition_header, pattern) in CONTRACT_ID_DEFINITION_SPECS.items():
        allowed_roles = ID_DEFINITION_MARKER_ROLES.get(marker, frozenset())
        for role, document in documents.items():
            if marker not in document.blocks:
                continue
            table = document.table(marker)
            if table is None or not table.headers:
                continue
            normalized_headers = {_normalize_header(header) for header in table.headers}
            if _normalize_header(definition_header) not in normalized_headers:
                continue
            if role not in allowed_roles:
                if report is not None:
                    report.errors.append(
                        f"{source_label}: authoritative marker {marker!r} appears in wrong "
                        f"artifact role {role!r}; allowed roles are {sorted(allowed_roles)!r}"
                    )
                continue
            try:
                column = _column(table, definition_header)
            except ContractError as exc:
                if report is not None:
                    report.errors.append(f"{source_label}: {exc}")
                continue
            seen_local: set[str] = set()
            for row in table.rows:
                if len(row) <= column:
                    continue
                value = row[column].strip()
                if report is not None:
                    report.check(
                        bool(pattern.fullmatch(value)),
                        f"{marker} defines valid ID {value}",
                        f"{marker} has invalid definition ID: {value!r}",
                    )
                if not pattern.fullmatch(value):
                    continue
                if report is not None:
                    report.check(
                        value not in seen_local and value not in definitions,
                        f"ID definition is unique: {value}",
                        f"Duplicate ID definition: {value}",
                    )
                if value not in seen_local and value not in definitions:
                    definitions[value] = marker
                seen_local.add(value)
    return definitions


def _validate_v2_lineage_and_context(
    report: Report,
    manifest: Mapping[str, object],
    *,
    run_dir: Path,
    workspace_root: Path,
    mode: str,
) -> set[str]:
    external_ids: set[str] = set()
    lineage = manifest.get("lineage")
    parents = lineage.get("parents", []) if isinstance(lineage, dict) else []
    report.check(
        isinstance(lineage, dict) and isinstance(parents, list),
        "Manifest lineage structure is valid",
        "Manifest lineage must contain a parents list",
    )
    if not isinstance(parents, list):
        parents = []
    if mode == "run-audit":
        report.check(
            len(parents) == 1,
            "Run-audit declares exactly one parent run",
            "run-audit requires exactly one parent run",
        )

    expected_relation = {
        "landscape": "extends-landscape",
        "focus": "focuses-branch",
        "evidence-audit": "supplements-evidence",
        "run-audit": "audits-run",
    }[mode]
    if mode == "landscape" and manifest.get("completion_status") == "migrated-needs-review":
        expected_relation = "migrated-copy"

    for index, raw_parent in enumerate(parents, 1):
        if not isinstance(raw_parent, dict):
            report.errors.append(f"lineage parent {index} must be an object")
            continue
        report.check(
            raw_parent.get("relation") == expected_relation,
            f"Lineage parent {index} uses relation {expected_relation}",
            f"Lineage parent {index} must use relation={expected_relation}",
        )
        try:
            parent_dir = _resolve_workspace_path(
                workspace_root,
                raw_parent.get("workspace_relpath"),
                label=f"lineage parent {index} path",
            )
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        try:
            manifest_path = resolve_contained_file(
                parent_dir, Path("run-manifest.json"), label="parent manifest"
            )
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        report.passed.append(
            f"Parent manifest exists inside run: {raw_parent.get('workspace_relpath')}"
        )
        expected_hash = raw_parent.get("source_manifest_sha256")
        actual_hash = sha256_file(manifest_path)
        report.check(
            isinstance(expected_hash, str) and expected_hash == actual_hash,
            "Parent manifest SHA-256 matches the recorded snapshot",
            "Parent manifest SHA-256 does not match the recorded snapshot",
        )
        try:
            parent_manifest = load_json_object(manifest_path, label="parent manifest")
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        report.check(
            parent_manifest.get("run_id") == raw_parent.get("run_id"),
            "Parent run ID matches lineage",
            "Parent run ID does not match lineage",
        )
        report.check(
            parent_manifest.get("skill") == SKILL_ID,
            "Parent manifest identifies the same skill",
            "Parent manifest has an incompatible skill identifier",
        )
        parent_version = ""
        try:
            parent_version = str(parse_schema_version(parent_manifest.get("schema_version")))
        except ContractError as exc:
            report.errors.append(f"Invalid parent schema: {exc}")
        else:
            report.check(
                parent_version in SUPPORTED_SCHEMA_VERSIONS,
                f"Parent schema {parent_version} is supported",
                f"Parent schema {parent_version} is unsupported",
            )
        parent_texts: list[str] = []
        parent_texts_by_role: dict[str, str] = {}
        parent_roles_by_path: dict[str, list[str]] = defaultdict(list)
        raw_parent_roles = parent_manifest.get("artifact_roles")
        if isinstance(raw_parent_roles, dict):
            for parent_role, raw_role_path in raw_parent_roles.items():
                if not isinstance(parent_role, str):
                    continue
                try:
                    role_relpath = safe_manifest_relpath(
                        raw_role_path,
                        label=f"parent artifact role {parent_role}",
                    ).as_posix()
                except ContractError as exc:
                    report.errors.append(str(exc))
                    continue
                parent_roles_by_path[role_relpath].append(parent_role)
        artifact_hashes = raw_parent.get("source_artifact_sha256", {})
        if not isinstance(artifact_hashes, dict):
            report.errors.append("Parent source_artifact_sha256 must be an object")
            artifact_hashes = {}
        parent_files = parent_manifest.get("artifact_files")
        if isinstance(parent_files, list) and all(isinstance(item, str) for item in parent_files):
            declared_parent_files: set[str] = set()
            for item in parent_files:
                try:
                    declared_parent_files.add(
                        safe_manifest_relpath(item, label="parent artifact path").as_posix()
                    )
                except ContractError as exc:
                    report.errors.append(str(exc))
            hash_paths = set(artifact_hashes)
            if mode == "run-audit":
                observed_parent_files: set[str] = set()
                for observed_path in parent_dir.rglob("*"):
                    if not observed_path.is_file() or observed_path == manifest_path:
                        continue
                    try:
                        observed_path.resolve(strict=True).relative_to(parent_dir.resolve())
                    except (OSError, ValueError):
                        report.errors.append(
                            f"Parent audit snapshot contains an unsafe file target: {observed_path}"
                        )
                        continue
                    observed_parent_files.add(
                        observed_path.relative_to(parent_dir).as_posix()
                    )
                complete_snapshot = hash_paths == observed_parent_files
            else:
                complete_snapshot = (
                    hash_paths == declared_parent_files
                    if parent_version == "2.0"
                    else declared_parent_files <= hash_paths
                )
            report.check(
                complete_snapshot,
                "Parent artifact hash map covers the complete declared snapshot",
                (
                    "Parent source_artifact_sha256 must exactly cover the observed parent file tree"
                    if mode == "run-audit"
                    else "Parent source_artifact_sha256 must cover all parent artifact_files"
                    + (" exactly for schema 2.0" if parent_version == "2.0" else "")
                ),
            )
        else:
            report.errors.append("Parent manifest artifact_files must be a string list")
        for raw_path, expected in artifact_hashes.items():
            try:
                rel = safe_manifest_relpath(raw_path, label="parent artifact hash path")
            except ContractError as exc:
                report.errors.append(str(exc))
                continue
            try:
                artifact = resolve_contained_file(
                    parent_dir, rel, label="parent snapshot artifact"
                )
            except ContractError as exc:
                report.errors.append(str(exc))
                continue
            report.passed.append(f"Parent snapshot artifact exists inside run: {raw_path}")
            report.check(
                isinstance(expected, str) and sha256_file(artifact) == expected,
                f"Parent artifact hash matches: {raw_path}",
                f"Parent artifact hash mismatch: {raw_path}",
            )
            if artifact.suffix.lower() in {".md", ".json"}:
                try:
                    artifact_text = artifact.read_text(encoding="utf-8")
                    parent_texts.append(artifact_text)
                    for parent_role in parent_roles_by_path.get(rel.as_posix(), []):
                        parent_texts_by_role[parent_role] = artifact_text
                except (OSError, UnicodeError) as exc:
                    report.errors.append(f"Cannot inspect parent artifact {artifact}: {exc}")
        if parent_version:
            try:
                external_ids.update(
                    collect_parent_definition_ids(
                        parent_texts_by_role if parent_version == "2.0" else parent_texts,
                        schema_version=parent_version,
                    )
                )
            except ContractError as exc:
                report.errors.append(f"Cannot collect parent definition IDs: {exc}")

    contexts = manifest.get("context_sources", [])
    report.check(
        isinstance(contexts, list),
        "Manifest context_sources is a list",
        "Manifest context_sources must be a list",
    )
    if not isinstance(contexts, list):
        contexts = []
    seen_context_ids: set[str] = set()
    for index, source in enumerate(contexts, 1):
        if not isinstance(source, dict):
            report.errors.append(f"context source {index} must be an object")
            continue
        source_id = source.get("source_id")
        valid_source_id = (
            isinstance(source_id, str)
            and bool(V2_ID_TYPE_PATTERNS["context"].fullmatch(source_id))
            and source_id not in seen_context_ids
        )
        report.check(
            valid_source_id,
            f"Context source {index} has a unique CTX ID",
            f"Context source {index} has an invalid or duplicate source_id: {source_id!r}",
        )
        if isinstance(source_id, str):
            seen_context_ids.add(source_id)
        if valid_source_id:
            external_ids.add(source_id)
        role = source.get("role")
        report.check(
            isinstance(role, str) and bool(re.fullmatch(r"[a-z][a-z0-9_-]*", role)),
            f"Context source {index} has a valid role",
            f"Context source {index} has an invalid role: {role!r}",
        )
        report.check(
            source.get("access") == "read-only",
            f"Context source {index} is read-only",
            f"Context source {index} must declare access=read-only",
        )
        try:
            path = _resolve_workspace_path(
                workspace_root,
                source.get("workspace_relpath"),
                label=f"context source {index} path",
            )
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        report.check(
            path.exists(),
            f"Context source exists: {source.get('workspace_relpath')}",
            f"Context source is missing: {path}",
        )
        expected_kind = "file" if path.is_file() else "directory" if path.is_dir() else None
        report.check(
            source.get("kind") == expected_kind,
            f"Context source {index} kind matches the snapshot",
            f"Context source {index} kind does not match the resolved path",
        )
        expected_hash = source.get("snapshot_sha256")
        if path.is_file():
            report.check(
                isinstance(expected_hash, str) and sha256_file(path) == expected_hash,
                f"Context source hash matches: {source.get('workspace_relpath')}",
                f"Context source hash is missing or mismatched: {source.get('workspace_relpath')}",
            )
        elif path.is_dir():
            report.check(
                expected_hash is None,
                f"Directory context source {index} declares no file hash",
                f"Directory context source {index} must use snapshot_sha256=null",
            )
    if mode == "evidence-audit":
        report.check(
            bool(parents) or bool(contexts),
            "Evidence-audit has a parent or explicit context source",
            "evidence-audit requires a parent run or context source",
        )

    inherited = manifest.get("inherited_ids", {})
    if not isinstance(inherited, dict):
        report.errors.append("Manifest inherited_ids must be an object")
    else:
        inherited_patterns = {
            "claims": V2_ID_TYPE_PATTERNS["claim"],
            "evidence": V2_ID_TYPE_PATTERNS["evidence"],
            "capabilities": V2_ID_TYPE_PATTERNS["capability"],
        }
        for key, pattern in inherited_patterns.items():
            values = inherited.get(key, [])
            if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
                report.errors.append(f"inherited_ids.{key} must be a string list")
                continue
            report.check(
                len(values) == len(set(values)),
                f"inherited_ids.{key} contains unique IDs",
                f"inherited_ids.{key} contains duplicate IDs",
            )
            for value in values:
                report.check(
                    bool(pattern.fullmatch(value)),
                    f"Inherited {key} ID has the correct type: {value}",
                    f"inherited_ids.{key} has an invalid ID type: {value}",
                )
                report.check(
                    value in external_ids,
                    f"Inherited ID exists in parent snapshot: {value}",
                    f"Inherited ID is not present in a parent snapshot: {value}",
                )
                external_ids.add(value)
    return external_ids


def _validate_id_closure(
    report: Report,
    documents: Mapping[str, V2Document],
    *,
    external_ids: set[str],
) -> set[str]:
    definitions = _collect_authoritative_v2_ids(documents, report=report)

    visible_text = "\n".join(document.visible_text() for document in documents.values())
    referenced = set(V2_ID_PATTERN.findall(visible_text))
    dangling = sorted(referenced - definitions.keys() - external_ids)
    report.check(
        not dangling,
        "Cross-artifact IDs are closed",
        f"Dangling cross-artifact IDs: {', '.join(dangling)}",
    )
    return set(definitions)


def _normalize_source_link(value: str) -> str:
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


def _reader_references(document: V2Document) -> tuple[dict[int, str], list[int]]:
    block = document.blocks.get("references")
    if block is None:
        return {}, []
    result: dict[int, str] = {}
    duplicates: list[int] = []
    for line in block.lines:
        match = re.match(r"^\s*(\d+)\.\s+", line.text)
        if not match:
            continue
        link = re.search(r"\((https?://[^)]+)\)", line.text, re.IGNORECASE)
        if link is None:
            link = re.search(r"(https?://\S+)", line.text, re.IGNORECASE)
        if link is not None:
            number = int(match.group(1))
            if number in result:
                duplicates.append(number)
            else:
                result[number] = _normalize_source_link(link.group(1))
    return result, duplicates


def _parse_reader_ref(value: str) -> int | None:
    match = re.fullmatch(r"\s*\[?\s*(\d+)\s*\]?\s*", value)
    return int(match.group(1)) if match else None


def _reader_cited_numbers(text: str) -> set[int]:
    cited: set[int] = set()
    for match in re.finditer(r"\[([0-9][0-9,;\s\-–—]*)\]", text):
        content = match.group(1)
        for token in re.split(r"[,;]", content):
            token = token.strip()
            if not token:
                continue
            range_match = re.fullmatch(r"(\d+)\s*[-–—]\s*(\d+)", token)
            if range_match:
                start, end = map(int, range_match.groups())
                if start <= end and end - start <= 1000:
                    cited.update(range(start, end + 1))
                continue
            if token.isdigit():
                cited.add(int(token))
    return cited


def _validate_reader_citations(
    report: Report,
    documents: Mapping[str, V2Document],
    reader: V2Document,
    *,
    mode: str,
) -> None:
    references, duplicates = _reader_references(reader)
    report.check(
        not duplicates,
        "Reader reference numbers are unique",
        "Reader reference list contains duplicate number(s): "
        + ", ".join(str(item) for item in sorted(set(duplicates))),
    )
    report.check(
        bool(references),
        "Reader report has linked numbered references",
        "Reader report has no linked numbered references",
    )
    if references:
        report.check(
            sorted(references) == list(range(1, len(references) + 1)),
            "Reader references are contiguous and unique",
            "Reader reference numbers must be contiguous from 1",
        )
    visible = reader.visible_text()
    cited_numbers = _reader_cited_numbers(visible)
    missing_reference_entries = sorted(cited_numbers - references.keys())
    report.check(
        not missing_reference_entries,
        "Every reader body citation has a numbered reference entry",
        "Reader body cites missing reference number(s): "
        + ", ".join(str(item) for item in missing_reference_entries),
    )
    for number in references:
        report.check(
            number in cited_numbers,
            f"Reader reference [{number}] is cited in report body",
            f"Reader reference [{number}] is not cited in report body",
        )

    if mode == "run-audit":
        # The audit report's own bibliography is validated above.  The
        # citation-closure table is a projection of the parent run and is
        # checked separately against recomputed parent facts.
        return

    evidence = _table_from_documents(documents, "evidence-records")
    if evidence is None:
        return
    try:
        ref_col = _column(evidence, "Reader ref")
        url_col = _column(evidence, "DOI or stable URL")
        evidence_id_col = _column(evidence, "Evidence ID")
    except ContractError as exc:
        report.errors.append(str(exc))
        return
    mappings: dict[int, tuple[str, str]] = {}
    for row in evidence.rows:
        raw_ref = row[ref_col].strip()
        if raw_ref.lower() in {"unavailable", "not applicable", "none"}:
            continue
        number = _parse_reader_ref(raw_ref)
        if number is None:
            report.errors.append(f"Evidence {row[evidence_id_col]} has invalid Reader ref {raw_ref!r}")
            continue
        if number in mappings:
            report.errors.append(f"Reader ref {number} maps to multiple evidence records")
        mappings[number] = (row[evidence_id_col], _normalize_source_link(row[url_col]))
    orphan_mappings = sorted(set(mappings) - set(references))
    report.check(
        not orphan_mappings,
        "Every evidence Reader ref has a reader reference entry",
        "Evidence Reader ref mappings have no reader reference entry: "
        + ", ".join(str(number) for number in orphan_mappings),
    )
    for number, link in references.items():
        report.check(
            number in mappings,
            f"Reader reference {number} maps to an evidence record",
            f"Reader reference {number} has no evidence-record mapping",
        )
        if number in mappings:
            evidence_id, evidence_link = mappings[number]
            report.check(
                evidence_link == link,
                f"Reader reference {number} DOI/URL matches {evidence_id}",
                f"Reader reference {number} DOI/URL does not match {evidence_id}",
            )


CONFIDENCE_CAP_MAX: Mapping[str, str] = {
    "context-unverified": "low",
    "indirect-only": "low",
    "unresolved-direct-conflict": "moderate",
    "single-chain-broad-claim": "moderate",
    "method-nondiscriminating": "low",
    "regime-transfer-unvalidated": "low",
    "salience-only": "insufficient",
    "search-miss-novelty": "insufficient",
    "proxy-to-system-unvalidated": "low",
    "assumed-capability": "moderate",
}

CAPABILITY_UNCERTAIN_BASIS_PATTERN = re.compile(
    r"\b(?:not\s+yet\s+verified|unverified|unknown|assumed|learning\s+only|"
    r"planned\s+only|not\s+documented)\b|未核验|未经核验|未知|假设|仅学习|仅计划|未记录",
    re.IGNORECASE,
)


def _active_cap_codes(value: str) -> tuple[set[str], bool]:
    raw = value.strip().lower()
    if raw == "none":
        return set(), True
    codes = {item.strip() for item in re.split(r"[,;]+", raw) if item.strip()}
    return codes, False


def _validate_evidence_confidence(
    report: Report,
    documents: Mapping[str, V2Document],
) -> None:
    capabilities = _table_from_documents(documents, "capability-passport")
    if capabilities is not None:
        try:
            capability_id_col = _column(capabilities, "Capability ID")
            capability_state_col = _column(
                capabilities,
                "Epistemic state",
                "Epistemic state: Observed/Reported/Assumed/Unknown",
            )
            readiness_col = _column(
                capabilities,
                "Readiness",
                "Readiness: Ready/Adaptable/Collaborator/Unavailable",
            )
            capability_source_col = _column(capabilities, "Source or evidence")
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            allowed_states = {"observed", "reported", "assumed", "unknown"}
            allowed_readiness = {
                "ready", "adaptable", "collaborator", "unavailable"
            }
            for row in capabilities.rows:
                capability_id = row[capability_id_col].strip()
                state = row[capability_state_col].strip().lower()
                readiness = row[readiness_col].strip().lower()
                source_or_evidence = row[capability_source_col].strip()
                report.check(
                    state in allowed_states,
                    f"Capability {capability_id} uses a valid epistemic state",
                    f"Capability {capability_id} has invalid epistemic state "
                    f"{row[capability_state_col]!r}",
                )
                report.check(
                    readiness in allowed_readiness,
                    f"Capability {capability_id} uses a valid readiness state",
                    f"Capability {capability_id} has invalid readiness "
                    f"{row[readiness_col]!r}",
                )
                report.check(
                    not (
                        state in {"assumed", "unknown"}
                        and readiness == "ready"
                    ),
                    f"Capability {capability_id} does not inflate an assumed/unknown capability to Ready",
                    f"Capability {capability_id} cannot be Ready while its epistemic state is {state!r}",
                )
                report.check(
                    _meaningful(source_or_evidence),
                    f"Capability {capability_id} records a source or evidence basis",
                    f"Capability {capability_id} must record a meaningful Source or evidence basis",
                )
                if state in {"observed", "reported"}:
                    report.check(
                        not CAPABILITY_UNCERTAIN_BASIS_PATTERN.search(
                            source_or_evidence
                        ),
                        f"{state.title()} capability {capability_id} has a non-uncertain source or evidence basis",
                        f"{state.title()} capability {capability_id} requires a non-uncertain Source or evidence basis",
                    )
    claims = _table_from_documents(documents, "atomic-claims")
    evidence = _table_from_documents(documents, "evidence-records")
    confidence = _table_from_documents(documents, "claim-confidence")
    if claims is None or evidence is None or confidence is None:
        return
    try:
        claim_id_col = _column(claims, "Claim ID")
        claim_type_col = _column(claims, "Claim type")
        epistemic_col = _column(claims, "Epistemic label")
        critical_col = _column(claims, "Decision critical")
        evidence_id_col = _column(evidence, "Evidence ID")
        evidence_claim_ids_col = _column(evidence, "Claim IDs")
        source_role_col = _column(evidence, "Source role")
        directness_col = _column(evidence, "Directness")
        context_col = _column(evidence, "Full-context status")
        verification_col = _column(evidence, "Verification")
        independence_col = _column(evidence, "Independence/replication")
        source_identity_col = _column(evidence, "DOI or stable URL")
        stance_col = _column(evidence, "Stance")
        confidence_claim_col = _column(confidence, "Claim ID")
        supports_col = _column(confidence, "Supporting Evidence IDs")
        limits_col = _column(confidence, "Limiting Evidence IDs")
        consistency_col = _column(confidence, "Consistency/conflict status")
        method_col = _column(confidence, "Method validity", "Method/design validity")
        applicability_col = _column(confidence, "Applicability")
        level_col = _column(confidence, "Confidence")
        active_caps_col = _column(confidence, "Active cap codes")
        cap_col = _column(confidence, "Cap/downgrade reason")
        wording_col = _column(confidence, "Allowed wording")
        confidence_independence_col = _column(confidence, "Independence/replication")
    except ContractError as exc:
        report.errors.append(str(exc))
        return

    allowed_claim_types = {
        "existence", "mechanism", "comparative", "persistence", "generalization",
        "system-value", "open-position", "forecast",
    }
    allowed_epistemic_labels = {"evidence", "inference", "recommendation", "speculation"}
    claim_types = {row[claim_id_col]: row[claim_type_col].strip().lower() for row in claims.rows}
    for row in claims.rows:
        epistemic_label = row[epistemic_col].strip().lower()
        report.check(
            epistemic_label in allowed_epistemic_labels,
            f"Claim {row[claim_id_col]} uses a valid epistemic label",
            f"Claim {row[claim_id_col]} has invalid Epistemic label "
            f"{row[epistemic_col]!r}",
        )
        critical_value = row[critical_col].strip().lower()
        report.check(
            critical_value in {"yes", "no"},
            f"Claim {row[claim_id_col]} uses a valid decision-critical enum",
            f"Claim {row[claim_id_col]} has invalid Decision critical value {row[critical_col]!r}",
        )
    for claim_id, claim_type in claim_types.items():
        report.check(
            claim_type in allowed_claim_types,
            f"Claim {claim_id} uses a valid claim type",
            f"Claim {claim_id} has invalid claim type {claim_type!r}",
        )
    critical_claims = {
        row[claim_id_col]
        for row in claims.rows
        if row[critical_col].strip().lower() == "yes"
    }
    evidence_records = {row[evidence_id_col]: row for row in evidence.rows}
    allowed_source_roles = {
        "canonical-anchor", "frontier-signal", "direct-support", "direct-neighbor",
        "strongest-baseline", "limitation-negative", "independent-replication",
        "translation",
    }
    allowed_directness = {"direct", "supporting", "indirect", "none"}
    allowed_context = {
        "full-context-verified", "abstract-only", "metadata-only", "not-accessed",
    }
    allowed_stances = {"supports", "limits", "contradicts", "mixed", "context"}
    for evidence_id, evidence_row in evidence_records.items():
        report.check(
            bool(CHAIN_PREFIX.match(evidence_row[independence_col])),
            f"Evidence {evidence_id} declares a parseable chain identity or unknown",
            f"Evidence {evidence_id} independence is unresolved and requires review; use chains=EC-001; basis=... or chains=unknown; basis=...",
            warning=True,
        )
        roles = {item.lower() for item in _split_multi(evidence_row[source_role_col])}
        report.check(
            bool(roles) and roles <= allowed_source_roles,
            f"Evidence {evidence_id} uses valid source role(s)",
            f"Evidence {evidence_id} has invalid Source role {evidence_row[source_role_col]!r}",
        )
        directness = evidence_row[directness_col].strip().lower()
        report.check(
            directness in allowed_directness,
            f"Evidence {evidence_id} uses valid Directness",
            f"Evidence {evidence_id} has invalid Directness {evidence_row[directness_col]!r}",
        )
        context_status = evidence_row[context_col].strip().lower()
        report.check(
            context_status in allowed_context,
            f"Evidence {evidence_id} uses valid Full-context status",
            f"Evidence {evidence_id} has invalid Full-context status {evidence_row[context_col]!r}",
        )
        stance = evidence_row[stance_col].strip().lower()
        report.check(
            stance in allowed_stances,
            f"Evidence {evidence_id} uses a valid exact stance",
            f"Evidence {evidence_id} has invalid Stance {evidence_row[stance_col]!r}",
        )
    confidence_counts: dict[str, int] = defaultdict(int)
    for row in confidence.rows:
        confidence_claim_id = row[confidence_claim_col].strip()
        confidence_counts[confidence_claim_id] += 1
        report.check(
            bool(V2_ID_TYPE_PATTERNS["claim"].fullmatch(confidence_claim_id))
            and confidence_claim_id in claim_types,
            f"Claim-confidence row targets authoritative claim {confidence_claim_id}",
            f"Claim-confidence row has invalid or non-authoritative Claim ID {confidence_claim_id!r}",
        )
    duplicate_confidence = {
        claim_id: count
        for claim_id, count in confidence_counts.items()
        if count > 1
    }
    report.check(
        not duplicate_confidence,
        "Claim-confidence has at most one row per claim",
        f"Claim-confidence contains duplicate Claim IDs: {duplicate_confidence}",
    )
    confidence_rows = {
        row[confidence_claim_col].strip(): row for row in confidence.rows
    }
    report.check(
        all(confidence_counts.get(claim_id, 0) == 1 for claim_id in critical_claims),
        "Every decision-critical claim has exactly one confidence row",
        "Decision-critical claims must have exactly one confidence row: "
        + ", ".join(
            f"{claim_id}={confidence_counts.get(claim_id, 0)}"
            for claim_id in sorted(critical_claims)
            if confidence_counts.get(claim_id, 0) != 1
        ),
    )

    levels = {"high": 3, "moderate": 2, "low": 1, "insufficient": 0}
    broad_types = {
        "mechanism", "generalization", "comparative", "system-value", "persistence",
        "open-position",
    }
    for claim_id, row in confidence_rows.items():
        level = row[level_col].strip().lower()
        report.check(
            level in levels,
            f"Claim {claim_id} uses a valid confidence level",
            f"Claim {claim_id} has invalid confidence level {row[level_col]!r}",
        )
        if level not in levels:
            continue
        report.check(
            _meaningful(row[cap_col]) and _meaningful(row[wording_col]),
            f"Claim {claim_id} records cap reason and allowed wording",
            f"Claim {claim_id} must record cap/downgrade reason and allowed wording",
        )
        supports = _cell_ids(row[supports_col], V2_ID_TYPE_PATTERNS["evidence"])
        limits = _cell_ids(row[limits_col], V2_ID_TYPE_PATTERNS["evidence"])
        support_records = [evidence_records[item] for item in supports if item in evidence_records]
        limit_records = [evidence_records[item] for item in limits if item in evidence_records]
        invalid_support_links = [
            evidence_id
            for evidence_id in supports
            if evidence_id in evidence_records
            and (
                claim_id not in _cell_ids(
                    evidence_records[evidence_id][evidence_claim_ids_col],
                    V2_ID_TYPE_PATTERNS["claim"],
                )
                or evidence_records[evidence_id][stance_col].strip().lower()
                not in {"supports", "mixed"}
            )
        ]
        invalid_limit_links = [
            evidence_id
            for evidence_id in limits
            if evidence_id in evidence_records
            and (
                claim_id not in _cell_ids(
                    evidence_records[evidence_id][evidence_claim_ids_col],
                    V2_ID_TYPE_PATTERNS["claim"],
                )
                or evidence_records[evidence_id][stance_col].strip().lower()
                not in {"limits", "contradicts", "mixed"}
            )
        ]
        mixed_supports_missing_limit = [
            evidence_id
            for evidence_id in supports
            if evidence_id in evidence_records
            and evidence_records[evidence_id][stance_col].strip().lower() == "mixed"
            and evidence_id not in limits
        ]
        report.check(
            not invalid_support_links,
            f"Claim {claim_id} support IDs are claim-linked with supporting stance",
            f"Claim {claim_id} has invalid supporting evidence association/stance: "
            + ", ".join(invalid_support_links),
        )
        report.check(
            not invalid_limit_links,
            f"Claim {claim_id} limiting IDs are claim-linked with limiting stance",
            f"Claim {claim_id} has invalid limiting evidence association/stance: "
            + ", ".join(invalid_limit_links),
        )
        report.check(
            not mixed_supports_missing_limit,
            f"Claim {claim_id} mixed support is also carried as limiting evidence",
            f"Claim {claim_id} has mixed supporting evidence omitted from limiting IDs: "
            + ", ".join(mixed_supports_missing_limit),
        )
        report.check(
            bool(support_records) or level == "insufficient",
            f"Claim {claim_id} has support evidence or is Insufficient",
            f"Claim {claim_id} has no valid supporting evidence record and must be Insufficient",
        )
        direct_full_verified = [
            item
            for item in support_records
            if item[directness_col].strip().lower() == "direct"
            and item[context_col].strip().lower() == "full-context-verified"
            and item[verification_col].strip().lower() in {"verified", "已核验"}
        ]
        shallow_support = any(
            item[context_col].strip().lower()
            in {"metadata-only", "abstract-only", "not-accessed"}
            for item in support_records
        )
        indirect_only = bool(support_records) and all(
            item[directness_col].strip().lower() == "indirect" for item in support_records
        )
        declared_unresolved_conflict = bool(re.search(
            r"(?:^|;)\s*type=direct-conflict\s*;\s*status=unresolved(?:;|$)",
            row[consistency_col], re.I,
        ))
        tension_table = _table_from_role(documents, "evidence_matrix", "contradictions")
        unresolved_conflict = declared_unresolved_conflict
        if tension_table is not None:
            tension_header = "Tension type: direct-conflict/evidence-gap/condition-difference"
            adjudication_header = "Adjudication: support-dominant/limit-dominant/condition-split/unresolved"
            if all(name in tension_table.headers for name in ("Claim ID", tension_header, adjudication_header)):
                unresolved_conflict = unresolved_conflict or any(
                    tension_row[_column(tension_table, "Claim ID")] == claim_id
                    and tension_row[_column(tension_table, tension_header)].lower() == "direct-conflict"
                    and tension_row[_column(tension_table, adjudication_header)].lower() == "unresolved"
                    for tension_row in tension_table.rows
                )
        direct_conflict = any(
            item[directness_col].strip().lower() == "direct"
            and item[stance_col].strip().lower() == "contradicts"
            for item in limit_records
        )
        report.check(
            not declared_unresolved_conflict or direct_conflict,
            f"Claim {claim_id} explicit conflict diagnosis has direct contradicting evidence",
            f"Claim {claim_id} cannot label a limitation or gap as unresolved direct conflict",
        )
        chains = assess_chains(
            (_normalize_source_link(item[source_identity_col]), item[independence_col])
            for item in support_records
        )
        direct_chains = assess_chains(
            (_normalize_source_link(item[source_identity_col]), item[independence_col])
            for item in direct_full_verified
        )
        independence_review = row[confidence_independence_col]
        reviewed = independently_reviewed(independence_review)
        strong_design = reviewed and bool(re.search(
            r"(?:^|;)\s*design=strong-multimethod\s*(?:;|$)", independence_review, re.I,
        )) and bool(direct_full_verified)
        active_codes, declared_none = _active_cap_codes(row[active_caps_col])
        unknown_codes = active_codes - CONFIDENCE_CAP_MAX.keys()
        report.check(
            not unknown_codes,
            f"Claim {claim_id} uses only registered active cap codes",
            f"Claim {claim_id} has unknown Active cap codes: {', '.join(sorted(unknown_codes))}",
        )
        report.check(
            declared_none or bool(active_codes),
            f"Claim {claim_id} declares none or one or more cap codes",
            f"Claim {claim_id} Active cap codes must be exact 'none' or registered comma-separated codes",
        )
        report.check(
            not (declared_none and "," in row[active_caps_col]),
            f"Claim {claim_id} uses exact none only when no cap is declared",
            f"Claim {claim_id} cannot combine none with another Active cap code",
        )

        method_text = row[method_col].casefold()
        applicability_text = row[applicability_col].casefold()
        assessment_text = " ".join(
            (method_text, applicability_text, row[cap_col].casefold(), row[wording_col].casefold())
        )
        detected_codes: set[str] = set()
        if shallow_support and not direct_full_verified:
            detected_codes.add("context-unverified")
        if indirect_only:
            detected_codes.add("indirect-only")
        if unresolved_conflict and direct_conflict:
            detected_codes.add("unresolved-direct-conflict")
        if claim_types.get(claim_id) in broad_types and support_records and (
            chains.count == 1 and not chains.unresolved and not strong_design
        ):
            detected_codes.add("single-chain-broad-claim")
        report.check(
            "single-chain-broad-claim" not in active_codes or (
                bool(support_records) and chains.count == 1 and not chains.unresolved
            ),
            f"Claim {claim_id} single-chain diagnosis has a known supporting chain",
            f"Claim {claim_id} cannot label zero support or unknown independence as single-chain-broad-claim",
        )
        if re.search(
            r"cannot distinguish|cannot discriminate|non[- ]?discriminat|"
            r"alternative (?:is |remains )?(?:unresolved|plausible)|association only|"
            r"无法区分|不能区分|替代.*未解决",
            method_text,
        ):
            detected_codes.add("method-nondiscriminating")
        if re.search(
            r"different regime|regime mismatch|unvalidated (?:regime )?transfer|"
            r"transfer (?:is )?(?:unvalidated|unknown)|transfer model missing|"
            r"跨域未验证|跨尺度未验证|迁移.*未验证",
            applicability_text,
        ):
            detected_codes.add("regime-transfer-unvalidated")
        support_role_sets = [
            {item.lower() for item in _split_multi(record[source_role_col])}
            for record in support_records
        ]
        if (
            support_role_sets
            and all(roles == {"frontier-signal"} for roles in support_role_sets)
        ) or re.search(
            r"salience[- ]only|citation count only|venue prestige only|"
            r"only (?:a )?(?:salience|citation|venue) signal|仅.*(?:热度|引文|期刊)",
            assessment_text,
        ):
            detected_codes.add("salience-only")
        if claim_types.get(claim_id) == "open-position" and (
            UNBOUNDED_PRIORITY.search(assessment_text)
            or (
                re.search(r"zero hits?|search miss|no matches|零命中|未命中", assessment_text)
                and re.search(r"novel|priority|first|unexplored|空白|首创|优先", assessment_text)
            )
        ):
            detected_codes.add("search-miss-novelty")
        if claim_types.get(claim_id) == "system-value" and (
            re.search(r"device|material|proxy|器件|材料|代理", assessment_text)
            and re.search(r"system|array|workload|系统|阵列|负载", assessment_text)
            and re.search(r"unvalidated|missing bridge|no bridge|unknown|未验证|缺少.*桥", assessment_text)
        ):
            detected_codes.add("proxy-to-system-unvalidated")
        if re.search(
            r"assumed capability|capability (?:is )?(?:assumed|unknown|unverified)|"
            r"unverified capability dependency|能力.*(?:假设|未知|未验证)",
            assessment_text,
        ):
            detected_codes.add("assumed-capability")

        missing_codes = detected_codes - active_codes
        report.check(
            not missing_codes,
            f"Claim {claim_id} declares every machine-detected confidence cap",
            f"Claim {claim_id} is missing required Active cap codes: {', '.join(sorted(missing_codes))}",
        )
        report.check(
            not (declared_none and detected_codes),
            f"Claim {claim_id} uses none only when no cap applies",
            f"Claim {claim_id} declares none although cap(s) apply: {', '.join(sorted(detected_codes))}",
        )
        applicable_declared = active_codes & CONFIDENCE_CAP_MAX.keys()
        if applicable_declared:
            strictest = min(
                applicable_declared,
                key=lambda code: levels[CONFIDENCE_CAP_MAX[code]],
            )
            maximum = CONFIDENCE_CAP_MAX[strictest]
            report.check(
                levels[level] <= levels[maximum],
                f"Claim {claim_id} respects declared confidence cap(s)",
                f"Claim {claim_id} exceeds the {maximum.title()} cap imposed by {strictest}",
            )
        if level == "high":
            report.check(
                bool(direct_full_verified),
                f"High-confidence claim {claim_id} has direct verified full-context support",
                f"High-confidence claim {claim_id} lacks direct verified full-context support",
            )
            report.check(
                not (unresolved_conflict and direct_conflict),
                f"High-confidence claim {claim_id} has no unresolved direct conflict",
                f"High-confidence claim {claim_id} exceeds the unresolved-conflict cap",
            )
            if claim_types.get(claim_id) in broad_types:
                report.check(
                    reviewed and (strong_design or (
                        direct_chains.count >= 2 and not direct_chains.unresolved
                        and not direct_chains.source_conflicts
                    )),
                    f"Broad High-confidence claim {claim_id} records reviewed independent chains or a strong-design exception",
                    f"Broad High-confidence claim {claim_id} requires source-aware independent chains and an attributable independent review, or a reviewed strong-multimethod design",
                )
        if indirect_only:
            report.check(
                levels[level] <= levels["low"],
                f"Indirect-only claim {claim_id} respects the Low cap",
                f"Indirect-only claim {claim_id} exceeds the Low confidence cap",
            )
        if shallow_support and not direct_full_verified:
            report.check(
                levels[level] <= levels["low"],
                f"Unverified-context claim {claim_id} respects the Low cap",
                f"Claim {claim_id} exceeds the Low cap for metadata/abstract/not-accessed support",
            )


def _validate_reader_route_ownership(
    report: Report,
    reader: V2Document,
    route_ids: set[str],
    *,
    mode: str,
) -> None:
    """Require one complete decision card, execution, and outcomes per route."""
    cards = reader.table("recommended-routes")
    execution = reader.table("execution")
    outcomes = reader.table("outcome-interpretation")
    if cards is None or execution is None or outcomes is None:
        return
    if reader.narrative_layout:
        report.check(
            set(reader.route_blocks) == route_ids,
            "Every authoritative route owns one narrative explanation",
            f"Reader narrative route ownership mismatch: expected {sorted(route_ids)!r}, "
            f"got {sorted(reader.route_blocks)!r}",
        )
        for route_id, block in reader.route_blocks.items():
            report.check(
                _has_reader_prose(block),
                f"Route {route_id} has explanation outside its summary/projection",
                f"Route {route_id} needs visible explanation outside tables, headings and comments",
            )
    if not route_ids:
        report.check(
            not cards.rows and not execution.rows and not outcomes.rows,
            "A no-candidate result has no fabricated route cards or experiments",
            "A no-candidate result must leave route cards, execution and outcomes empty",
        )
        return
    try:
        card_route_col = _column(cards, "Route", "路线")
        card_field_columns = {"Summary": _column(cards, "Summary")} if "Summary" in cards.headers else {
            "What": _column(cards, "What", "What：大白话做什么"),
            "Why": _column(cards, "Why", "Why：为什么做"),
            "Need to know": _column(cards, "Need to know"),
            "How": _column(
                cards,
                "How",
                "How: existing base→new control→measurement",
                "How：已有基础→新控制→测量",
            ),
            "What we learn": _column(cards, "What we learn"),
            "Strongest baseline": _column(cards, "Strongest baseline", "最强基线"),
            "Competing hypotheses": _column(cards, "Competing hypotheses", "竞争假设"),
            "Positive outcome": _column(cards, "Positive outcome", "Positive 结果"),
            "Negative outcome": _column(cards, "Negative outcome", "Negative 结果"),
            "Ambiguous outcome": _column(cards, "Ambiguous outcome", "Ambiguous 结果"),
            "Kill criterion": _column(cards, "Kill criterion"),
            "Retained value after failure": _column(
                cards, "Retained value after failure", "失败后保留价值"
            ),
            "Reversal condition": _column(cards, "Reversal condition", "反转条件"),
        }
        execution_route_col = _column(execution, "Route", "路线")
        outcome_route_col = _column(outcomes, "Route", "路线")
        outcome_class_col = _column(
            outcomes, "Outcome", "结果类型", "结果"
        )
    except ContractError as exc:
        report.errors.append(str(exc))
        return

    card_counts: dict[str, int] = defaultdict(int)
    for row in cards.rows:
        row_routes = set(
            _cell_ids(row[card_route_col], V2_ID_TYPE_PATTERNS["candidate"])
        )
        report.check(
            len(row_routes) == 1,
            f"{mode} reader route card owns exactly one route",
            f"{mode} reader route cards must each own exactly one C-ID; "
            f"found {sorted(row_routes)!r}",
        )
        for route_id in row_routes:
            card_counts[route_id] += 1
            report.check(
                route_id in route_ids,
                f"{mode} reader route card targets an authoritative route",
                f"{mode} reader route card targets unknown route {route_id}",
            )
        for label, column in card_field_columns.items():
            report.check(
                _meaningful(row[column]),
                f"{mode} reader route card has substantive {label}",
                f"{mode} reader route card is missing substantive {label}",
            )
    report.check(
        set(card_counts) == route_ids
        and all(card_counts[route_id] == 1 for route_id in route_ids),
        f"Every {mode} route owns exactly one complete reader decision card",
        f"{mode} reader decision-card ownership mismatch: "
        f"expected {sorted(route_ids)!r}, counts={dict(sorted(card_counts.items()))!r}",
    )

    execution_routes: set[str] = set()
    for row in execution.rows:
        row_routes = set(
            _cell_ids(
                row[execution_route_col], V2_ID_TYPE_PATTERNS["candidate"]
            )
        )
        report.check(
            len(row_routes) == 1,
            f"{mode} reader execution row owns exactly one route",
            f"{mode} reader execution rows must each own exactly one C-ID; "
            f"found {sorted(row_routes)!r}",
        )
        execution_routes.update(row_routes)
    report.check(
        route_ids == execution_routes,
        f"Every {mode} reader route owns an execution row",
        f"Reader execution table is missing {mode} routes: "
        + ", ".join(sorted(route_ids - execution_routes)),
    )

    outcomes_by_route: dict[str, set[str]] = defaultdict(set)
    for row in outcomes.rows:
        row_routes = set(
            _cell_ids(
                row[outcome_route_col], V2_ID_TYPE_PATTERNS["candidate"]
            )
        )
        report.check(
            len(row_routes) == 1,
            f"{mode} reader outcome row owns exactly one route",
            f"{mode} reader outcome rows must each own exactly one C-ID; "
            f"found {sorted(row_routes)!r}",
        )
        outcome_class = row[outcome_class_col].strip().lower()
        report.check(
            outcome_class in {"positive", "negative", "ambiguous"},
            f"{mode} reader outcome uses an exact registered class",
            f"{mode} reader outcome has invalid class {row[outcome_class_col]!r}",
        )
        for route_id in row_routes:
            outcomes_by_route[route_id].add(outcome_class)
    required = {"positive", "negative", "ambiguous"}
    missing = {
        route_id: sorted(required - outcomes_by_route.get(route_id, set()))
        for route_id in route_ids
        if not required <= outcomes_by_route.get(route_id, set())
    }
    report.check(
        not missing and set(outcomes_by_route) == route_ids,
        f"Every {mode} reader route owns positive, negative, and ambiguous outcomes",
        f"Reader outcome-interpretation is incomplete by {mode} route: {missing}",
    )


def _validate_landscape(
    report: Report,
    documents: Mapping[str, V2Document],
    reader: V2Document,
) -> None:
    branches = _table_from_documents(documents, "breadth-branches")
    summary = _table_from_documents(documents, "breadth-summary")
    routes = _table_from_documents(documents, "candidate-routes")
    platform = _table_from_documents(documents, "shared-platform")
    if not all((branches, summary, routes, platform)):
        return
    assert branches is not None and summary is not None and routes is not None and platform is not None
    try:
        bottleneck_col = _column(branches, "Bottleneck family")
        mechanism_col = _column(branches, "Mechanism families")
        application_col = _column(branches, "Application context")
        counter_col = _column(branches, "Disconfirm Query ID")
        outside_col = _column(branches, "Outside favorite family")
        metric_col = _column(summary, "Metric")
        declared_col = _column(summary, "Declared count")
        candidate_col = _column(routes, "Candidate ID")
        risk_col = _column(routes, "Risk")
        reused_col = _column(platform, "Reused by Candidate IDs")
        candidate_detail_cols = {label: _column(routes, label) for label in (
            "Strongest baseline", "Competing hypotheses", "Three-month decisive test",
            "Quantitative threshold", "Kill criterion", "One-year platform path", "Retained value",
        )}
    except ContractError as exc:
        report.errors.append(str(exc))
        return
    counts = {
        "Unique bottleneck families": len({row[bottleneck_col] for row in branches.rows}),
        "Unique mechanism families": len({item for row in branches.rows for item in _split_multi(row[mechanism_col])}),
        "Unique application contexts": len({row[application_col] for row in branches.rows}),
        "Branches with disconfirming queries": sum(
            bool(_cell_ids(row[counter_col], V2_ID_TYPE_PATTERNS["query"]))
            for row in branches.rows
        ),
        "Outside-favorite-family branches": sum(row[outside_col].strip().lower() == "yes" for row in branches.rows),
    }
    minima = {
        "Unique bottleneck families": 4,
        "Unique mechanism families": 4,
        "Unique application contexts": 2,
        "Branches with disconfirming queries": 3,
        "Outside-favorite-family branches": 1,
    }
    summary_values: dict[str, int] = {}
    for row in summary.rows:
        try:
            summary_values[row[metric_col]] = int(row[declared_col])
        except ValueError:
            report.errors.append(f"breadth-summary count is not an integer: {row[declared_col]!r}")
    for metric, actual in counts.items():
        report.check(
            actual >= minima[metric],
            f"Recomputed breadth gate: {metric} = {actual}",
            f"Recomputed breadth gate failed: {metric} = {actual}, requires {minima[metric]}",
        )
        report.check(
            summary_values.get(metric) == actual,
            f"Declared breadth count matches recomputed value for {metric}",
            f"Declared breadth count for {metric} does not match recomputed value {actual}",
        )
    risk_by_candidate = {
        row[candidate_col].strip(): row[risk_col].strip().lower()
        for row in routes.rows
    }
    for row in routes.rows:
        for label, column in candidate_detail_cols.items():
            value = row[column].strip().casefold()
            report.check(
                value not in {"none", "unknown", "not applicable", "n/a", "no"},
                f"Candidate {row[candidate_col]} retains substantive {label}",
                f"Candidate {row[candidate_col]} requires substantive {label}; unknown access belongs in its dependency/gate",
            )
    risk_values = set(risk_by_candidate.values())
    invalid_risks = risk_values - {"low", "medium", "high"}
    report.check(
        not invalid_risks,
        "Landscape routes use only exact low/medium/high risk labels",
        f"Landscape routes contain invalid risk labels: {sorted(invalid_risks)}",
    )
    candidate_ids = set(risk_by_candidate)
    scorecard = _table_from_documents(documents, "scorecard")
    if scorecard is not None:
        try:
            score_id_col = _column(scorecard, "Candidate ID")
            report.check(
                {row[score_id_col].strip() for row in scorecard.rows} == candidate_ids,
                "Scorecard contains exactly the selected candidates",
                "Scorecard candidate set must exactly match candidate-routes",
            )
        except ContractError as exc:
            report.errors.append(str(exc))
    if not candidate_ids:
        portfolio = documents.get("candidate_portfolio")
        report.check(
            portfolio is not None and bool(re.search(
                r"(?im)^\s*(?:-\s*)?Selection outcome:\s*no-candidate\s*$",
                portfolio.visible_text(),
            )),
            "Empty candidate set is an explicit no-candidate disposition",
            "Zero candidates require 'Selection outcome: no-candidate' and claim-owned decisions; unfinished templates are not a result",
        )
        _validate_reader_route_ownership(report, reader, candidate_ids, mode="landscape")
        return
    shared = any(candidate_ids <= set(_cell_ids(row[reused_col])) for row in platform.rows)
    report.check(
        len(candidate_ids) < 2 or shared,
        "Landscape risk routes share a declared platform module",
        "Landscape low/medium/high routes do not share a platform module",
    )
    reader_summary = reader.table("decision-summary")
    if reader_summary is not None:
        try:
            reader_route_col = _column(
                reader_summary, "Recommended route", "推荐路线"
            )
            reader_risk_col = _column(
                reader_summary, "Risk tier", "风险层级"
            )
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            reader_risk_counts: dict[str, int] = defaultdict(int)
            reader_risk_by_candidate: dict[str, str] = {}
            for row in reader_summary.rows:
                row_routes = set(
                    _cell_ids(
                        row[reader_route_col],
                        V2_ID_TYPE_PATTERNS["candidate"],
                    )
                )
                report.check(
                    len(row_routes) == 1,
                    "Landscape reader risk row owns exactly one route",
                    "Landscape reader decision-summary risk rows must each own exactly one C-ID",
                )
                risk = row[reader_risk_col].strip().lower()
                report.check(
                    risk in {"low", "medium", "high"},
                    "Landscape reader uses an exact low/medium/high risk label",
                    f"Landscape reader has invalid risk label {row[reader_risk_col]!r}",
                )
                for candidate_id in row_routes:
                    reader_risk_counts[candidate_id] += 1
                    reader_risk_by_candidate[candidate_id] = risk
            report.check(
                reader_risk_by_candidate == risk_by_candidate
                and all(count == 1 for count in reader_risk_counts.values()),
                "Landscape reader risk tiers exactly project the candidate portfolio",
                "Landscape reader C-ID to risk mapping must exactly match candidate-routes",
            )
    _validate_reader_route_ownership(report, reader, candidate_ids, mode="landscape")


def _validate_focus(
    report: Report,
    documents: Mapping[str, V2Document],
    reader: V2Document,
) -> None:
    alternatives = _table_from_documents(documents, "local-alternatives")
    routes = _table_from_documents(documents, "focus-routes")
    claim_test = _table_from_documents(documents, "claim-null-test-threshold")
    execution = _table_from_documents(documents, "staged-execution")
    outcomes = _table_from_documents(documents, "outcome-interpretation")
    boundaries = _table_from_documents(documents, "route-boundaries")
    if not all((alternatives, routes, claim_test, execution, outcomes, boundaries)):
        return
    assert alternatives is not None and routes is not None and claim_test is not None and execution is not None and outcomes is not None and boundaries is not None
    try:
        alt_id = _column(alternatives, "Alternative ID", "Candidate ID")
        alt_role = _column(alternatives, "Role")
        route_id = _column(routes, "Candidate ID")
        route_role = _column(routes, "Route role")
        route_design_cols = [_column(routes, label) for label in ("Strongest baseline", "Competing hypotheses")]
        execution_route = _column(execution, "Route")
        outcome_route = _column(outcomes, "Candidate ID")
        outcome_class = _column(outcomes, "Outcome class")
        boundary_route = _column(boundaries, "Candidate ID")
        boundary_field_columns = [
            _column(boundaries, "Kill criterion"),
            _column(boundaries, "Reversal condition"),
            _column(boundaries, "Retained value after failure"),
            _column(boundaries, "Comparator/fallback activation rule"),
        ]
        claim_test_detail_cols = {}
        for required in (
            "Claim ID", "Falsifiable claim", "Null hypothesis", "Test",
            "Quantitative threshold", "Strongest baseline",
        ):
            claim_test_detail_cols[required] = _column(claim_test, required)
    except ContractError as exc:
        report.errors.append(str(exc))
        return
    required_roles = {"primary", "comparator", "fallback"}
    if not routes.rows:
        report.check(
            bool(re.search(r"(?im)^\s*(?:-\s*)?Selection outcome:\s*no-candidate\s*$", documents["route_protocol"].visible_text())),
            "Focus explicitly concludes with no candidate",
            "A zero-candidate focus requires Selection outcome: no-candidate",
        )
        report.check(
            not alternatives.rows and not claim_test.rows and not execution.rows and not outcomes.rows and not boundaries.rows,
            "Zero-candidate focus leaves route-owned collections empty",
            "A zero-candidate focus cannot retain fabricated alternatives, route claim tests, stages, outcomes or boundaries",
        )
        _validate_reader_route_ownership(report, reader, set(), mode="focus")
        return
    for row in claim_test.rows:
        for label, column in claim_test_detail_cols.items():
            report.check(
                _meaningful(row[column]) and row[column].strip().lower() not in {"none", "unknown", "not applicable", "n/a"},
                f"Focus claim test retains substantive {label}",
                f"Focus claim test requires substantive {label}; unknown resources belong in the dependency/gate",
            )
    alternative_role_counts: dict[str, int] = defaultdict(int)
    for row in alternatives.rows:
        alternative_role_counts[row[alt_role].strip().lower()] += 1
    route_role_counts: dict[str, int] = defaultdict(int)
    for row in routes.rows:
        report.check(
            all(_meaningful(row[c]) and row[c].strip().lower() not in {"none", "unknown", "n/a", "not applicable"} for c in route_design_cols),
            "Focus candidate retains baseline and competing hypotheses without role quotas",
            "Every focus candidate requires a substantive baseline and competing hypotheses",
        )
        route_role_counts[row[route_role].strip().lower()] += 1
    report.check(
        set(alternative_role_counts) <= required_roles | {"neighbor"}
        and alternative_role_counts["primary"] == 1,
        "Focus local alternatives contain one primary with optional substantive comparators/fallbacks and neighbors",
        "Focus local alternatives must contain exactly one primary; comparator/fallback candidate roles are optional; "
        f"counts={dict(alternative_role_counts)!r}",
    )
    report.check(
        set(route_role_counts) <= required_roles
        and route_role_counts["primary"] == 1,
        "Focus route protocol contains one primary and optional substantive comparator/fallback candidates",
        "Focus route protocol must contain exactly one primary; other candidates use comparator/fallback, "
        f"not a quota; counts={dict(route_role_counts)!r}",
    )
    alternative_route_roles = {
        row[alt_id].strip(): row[alt_role].strip().lower()
        for row in alternatives.rows
        if row[alt_role].strip().lower() in required_roles
    }
    route_roles = {
        row[route_id].strip(): row[route_role].strip().lower() for row in routes.rows
    }
    report.check(
        alternative_route_roles == route_roles,
        "Focus alternative IDs and roles project exactly into the route protocol",
        "Focus primary/comparator/fallback alternatives and focus-routes must have "
        "identical C-ID to role mappings; neighbor alternatives stay local",
    )
    reader_routes = reader.table("recommended-routes")
    if reader_routes is not None:
        try:
            reader_route_id_col = _column(reader_routes, "Route", "路线")
            reader_route_role_col = _column(reader_routes, "Role", "角色")
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            reader_role_counts: dict[str, int] = defaultdict(int)
            reader_route_roles: dict[str, str] = {}
            for row in reader_routes.rows:
                row_routes = set(
                    _cell_ids(
                        row[reader_route_id_col],
                        V2_ID_TYPE_PATTERNS["candidate"],
                    )
                )
                report.check(
                    len(row_routes) == 1,
                    "Focus reader role row owns exactly one route",
                    "Focus reader recommended-routes rows must each own exactly one C-ID",
                )
                role = row[reader_route_role_col].strip().lower()
                report.check(
                    role in required_roles,
                    "Focus reader uses an exact primary/comparator/fallback role",
                    f"Focus reader has invalid route role {row[reader_route_role_col]!r}",
                )
                for candidate_id in row_routes:
                    reader_role_counts[candidate_id] += 1
                    reader_route_roles[candidate_id] = role
            report.check(
                reader_route_roles == route_roles
                and all(count == 1 for count in reader_role_counts.values()),
                "Focus reader roles exactly project the route protocol",
                "Focus reader C-ID to role mapping must exactly match focus-routes",
            )
    report.check(
        {"positive", "negative", "ambiguous"}
        <= {row[outcome_class].strip().lower() for row in outcomes.rows},
        "Focus protocol interprets positive, negative, and ambiguous outcomes",
        "Focus protocol must interpret positive, negative, and ambiguous outcomes",
    )
    invalid_outcome_classes = {
        row[outcome_class].strip().lower()
        for row in outcomes.rows
        if row[outcome_class].strip().lower()
        not in {"positive", "negative", "ambiguous"}
    }
    report.check(
        not invalid_outcome_classes,
        "Focus protocol uses only exact outcome classes",
        f"Focus protocol has invalid outcome classes: {sorted(invalid_outcome_classes)}",
    )
    report.check(
        bool(claim_test.rows),
        "Focus protocol contains claim-null-test-threshold rows",
        "Focus protocol has no claim-null-test-threshold row",
    )
    route_ids = set(route_roles)
    boundary_counts: dict[str, int] = defaultdict(int)
    for row in boundaries.rows:
        row_routes = set(
            _cell_ids(row[boundary_route], V2_ID_TYPE_PATTERNS["candidate"])
        )
        report.check(
            len(row_routes) == 1,
            "Focus route-boundary row owns exactly one route",
            "Focus route-boundary rows must each own exactly one C-ID",
        )
        for bounded_route in row_routes:
            boundary_counts[bounded_route] += 1
            report.check(
                bounded_route in route_ids,
                "Focus route-boundary row targets an authoritative route",
                f"Focus route-boundary row targets unknown route {bounded_route}",
            )
        report.check(
            all(_meaningful(row[column]) and row[column].strip().lower() not in {"none", "unknown", "n/a", "not applicable"} for column in boundary_field_columns),
            "Focus route-boundary row has kill, reversal, retained value, and activation rule",
            "Focus route-boundary row has an incomplete kill/reversal/retained-value/activation card",
        )
    report.check(
        set(boundary_counts) == route_ids
        and all(boundary_counts[route] == 1 for route in route_ids),
        "Every focus route owns exactly one working route-boundary card",
        "Focus route-boundary ownership mismatch: "
        f"expected {sorted(route_ids)!r}, counts={dict(sorted(boundary_counts.items()))!r}",
    )
    execution_ids = {row[execution_route].strip() for row in execution.rows}
    report.check(
        route_ids <= execution_ids,
        "Every focus route owns a staged-execution row",
        "Focus staged-execution is missing routes: "
        + ", ".join(sorted(route_ids - execution_ids)),
    )
    outcome_classes_by_route: dict[str, set[str]] = defaultdict(set)
    for row in outcomes.rows:
        outcome_classes_by_route[row[outcome_route].strip()].add(
            row[outcome_class].strip().lower()
        )
    required_outcomes = {"positive", "negative", "ambiguous"}
    missing_outcomes = {
        route: sorted(required_outcomes - outcome_classes_by_route.get(route, set()))
        for route in route_ids
        if not required_outcomes <= outcome_classes_by_route.get(route, set())
    }
    report.check(
        not missing_outcomes,
        "Every focus route owns positive, negative, and ambiguous outcome rows",
        f"Focus outcome-interpretation is incomplete by route: {missing_outcomes}",
    )
    _validate_reader_route_ownership(report, reader, route_ids, mode="focus")


def _projection_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).casefold()


def _validate_evidence_audit(
    report: Report,
    documents: Mapping[str, V2Document],
    reader: V2Document,
) -> None:
    register = _table_from_role(documents, "claim_register", "claim-register")
    targets = _table_from_role(documents, "audit_scope", "target-claims")
    canonical = _table_from_role(documents, "evidence_matrix", "claim-confidence")
    assessment = _table_from_role(
        documents, "confidence_assessment", "confidence-assessment"
    )
    wording = _table_from_role(documents, "confidence_assessment", "allowed-wording")
    gaps = _table_from_role(documents, "gap_plan", "evidence-gaps")
    implications = _table_from_role(documents, "gap_plan", "parent-implications")
    reader_verdicts = reader.table("claim-verdicts")
    if not all((targets, register, canonical, assessment, wording, gaps, implications, reader_verdicts)):
        return
    assert targets is not None and register is not None and canonical is not None and assessment is not None and wording is not None and gaps is not None and implications is not None and reader_verdicts is not None
    try:
        register_id = _column(register, "Claim ID")
        target_id = _column(targets, "Claim ID")
        canonical_id = _column(canonical, "Claim ID")
        canonical_confidence = _column(canonical, "Confidence")
        canonical_caps = _column(canonical, "Active cap codes")
        canonical_allowed = _column(canonical, "Allowed wording")
        assessment_id = _column(assessment, "Claim ID")
        assessment_confidence = _column(assessment, "Confidence")
        assessment_caps = _column(assessment, "Active cap codes")
        allowed_col = _column(assessment, "Allowed wording")
        cap_col = _column(assessment, "Cap/downgrade reason")
        assessment_parent = _column(assessment, "Parent impact")
        wording_id = _column(wording, "Claim ID")
        wording_allowed = _column(wording, "Allowed wording")
        gap_claim = _column(gaps, "Claim ID")
        unchanged_col = _column(implications, "Parent left unchanged")
        reader_id = _column(reader_verdicts, "Claim", "Claim ID")
        reader_confidence = _column(reader_verdicts, "Confidence")
        reader_caps = _column(reader_verdicts, "Active cap codes")
        reader_allowed = _column(reader_verdicts, "Allowed wording")
        reader_parent = _column(reader_verdicts, "Parent impact")
    except ContractError as exc:
        report.errors.append(str(exc))
        return
    def audited_claim_counts(
        table: V2Table,
        column: int,
        label: str,
    ) -> dict[str, int]:
        counts: dict[str, int] = defaultdict(int)
        for table_row in table.rows:
            claim_id = table_row[column].strip()
            counts[claim_id] += 1
            report.check(
                bool(V2_ID_TYPE_PATTERNS["claim"].fullmatch(claim_id)),
                f"{label} row uses valid Claim ID {claim_id}",
                f"{label} row has invalid Claim ID {claim_id!r}",
            )
        return counts

    target_counts = audited_claim_counts(targets, target_id, "target-claims")
    declared_targets = set(target_counts)
    report.check(
        all(count == 1 for count in target_counts.values()),
        "Evidence-audit target-claims are unique",
        "Evidence-audit target-claims contains duplicate Claim IDs",
    )
    register_counts = audited_claim_counts(
        register, register_id, "claim-register"
    )
    claims = set(register_counts)
    report.check(
        claims == declared_targets
        and all(count == 1 for count in register_counts.values()),
        "Evidence-audit claim-register exactly matches declared target-claims",
        "Evidence-audit claim-register Claim IDs must exactly match target-claims Claim IDs and occur exactly once; "
        f"missing={sorted(declared_targets - claims)!r}, "
        f"extra={sorted(claims - declared_targets)!r}, "
        f"counts={dict(sorted(register_counts.items()))!r}",
    )
    projection_counts = {
        "claim-confidence": audited_claim_counts(
            canonical, canonical_id, "claim-confidence"
        ),
        "confidence-assessment": audited_claim_counts(
            assessment, assessment_id, "confidence-assessment"
        ),
        "allowed-wording": audited_claim_counts(
            wording, wording_id, "allowed-wording"
        ),
        "reader claim-verdicts": audited_claim_counts(
            reader_verdicts, reader_id, "reader claim-verdicts"
        ),
    }
    for label, counts in projection_counts.items():
        report.check(
            set(counts) == declared_targets
            and all(count == 1 for count in counts.values()),
            f"Evidence-audit {label} contains each target claim exactly once",
            f"Evidence-audit {label} must contain each target claim exactly once; "
            f"counts={dict(sorted(counts.items()))!r}",
        )
    assessed = set(projection_counts["confidence-assessment"])
    worded = set(projection_counts["allowed-wording"])
    gap_counts = audited_claim_counts(gaps, gap_claim, "evidence-gaps")
    gapped = set(gap_counts)
    report.check(
        gapped <= declared_targets,
        "Evidence-audit gap rows target only declared claims",
        "Evidence-audit evidence-gaps contains undeclared Claim IDs: "
        + ", ".join(sorted(gapped - declared_targets)),
    )
    report.check(
        claims <= assessed and claims <= worded and claims <= gapped,
        "Evidence-audit claims have assessment, allowed wording, and gap plans",
        "Every evidence-audit claim needs assessment, allowed wording, and a gap plan",
    )
    report.check(
        all(_meaningful(row[allowed_col]) and _meaningful(row[cap_col]) for row in assessment.rows),
        "Evidence-audit assessments include allowed wording and cap reasons",
        "Evidence-audit assessments have missing allowed wording or cap reasons",
    )
    canonical_rows = {row[canonical_id]: row for row in canonical.rows}
    assessment_rows = {row[assessment_id]: row for row in assessment.rows}
    wording_rows = {row[wording_id]: row for row in wording.rows}
    reader_rows = {row[reader_id]: row for row in reader_verdicts.rows}
    report.check(
        claims == set(canonical_rows) == set(assessment_rows) == set(wording_rows) == set(reader_rows),
        "Evidence-audit claim projections have identical claim sets",
        "claim-confidence, confidence-assessment, allowed-wording, and reader claim-verdicts must project the same claims",
    )
    for claim_id in sorted(claims & canonical_rows.keys() & assessment_rows.keys() & wording_rows.keys() & reader_rows.keys()):
        canonical_row = canonical_rows[claim_id]
        assessment_row = assessment_rows[claim_id]
        wording_row = wording_rows[claim_id]
        reader_row = reader_rows[claim_id]
        confidence_values = {
            _projection_text(canonical_row[canonical_confidence]),
            _projection_text(assessment_row[assessment_confidence]),
            _projection_text(reader_row[reader_confidence]),
        }
        cap_values = {
            _projection_text(canonical_row[canonical_caps]),
            _projection_text(assessment_row[assessment_caps]),
            _projection_text(reader_row[reader_caps]),
        }
        allowed_values = {
            _projection_text(canonical_row[canonical_allowed]),
            _projection_text(assessment_row[allowed_col]),
            _projection_text(wording_row[wording_allowed]),
            _projection_text(reader_row[reader_allowed]),
        }
        report.check(
            len(confidence_values) == 1,
            f"Evidence-audit confidence projects consistently for {claim_id}",
            f"Evidence-audit confidence mismatch across artifacts for {claim_id}",
        )
        report.check(
            len(cap_values) == 1,
            f"Evidence-audit Active cap codes project consistently for {claim_id}",
            f"Evidence-audit Active cap code mismatch across artifacts for {claim_id}",
        )
        report.check(
            len(allowed_values) == 1,
            f"Evidence-audit allowed wording projects consistently for {claim_id}",
            f"Evidence-audit allowed wording mismatch across artifacts for {claim_id}",
        )
        report.check(
            _projection_text(assessment_row[assessment_parent])
            == _projection_text(reader_row[reader_parent]),
            f"Evidence-audit parent impact projects consistently for {claim_id}",
            f"Evidence-audit parent impact mismatch for {claim_id}",
        )
    report.check(
        all(row[unchanged_col].strip().lower() == "yes" for row in implications.rows),
        "Evidence-audit preserves the supplement-only parent policy",
        "Evidence-audit must leave parent artifacts unchanged and record yes",
    )


def _validate_attack_propagation(
    report: Report,
    documents: Mapping[str, V2Document],
    reader: V2Document,
    *,
    mode: str,
    valid_ids: set[str],
    authoritative_major_targets: set[str] | None = None,
    additional_bindings: Sequence[DispositionBinding] = (),
) -> None:
    attacks = _table_from_role(documents, "red_team", "attack-register")
    decisions = _table_from_role(documents, "decision_log", "decisions")
    if attacks is None or decisions is None:
        return

    def mode_target_ids(value: str) -> list[str]:
        if mode == "run-audit":
            return RUN_AUDIT_TARGET_PATTERN.findall(value)
        return _cell_ids(value)
    target_role, target_table_name, target_aliases = {
        "landscape": ("candidate_portfolio", "candidate-routes", ("Candidate ID",)),
        "focus": ("route_protocol", "focus-routes", ("Candidate ID",)),
        "evidence-audit": ("claim_register", "claim-register", ("Claim ID",)),
        "run-audit": ("route_verdicts", "route-verdicts", ("Route/claim ID",)),
    }[mode]
    major_targets_table = _table_from_role(
        documents, target_role, target_table_name
    )
    major_target_values: list[str] = []
    if major_targets_table is not None:
        try:
            major_target_col = _column(major_targets_table, *target_aliases)
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            major_target_values = [
                row[major_target_col].strip() for row in major_targets_table.rows
            ]
    major_targets = set(major_target_values)
    no_candidates = mode in {"landscape", "focus"} and not major_targets
    if no_candidates:
        # A concluded search can reject every route. Atomic decision-critical
        # claims then carry the existing decision/red-team contract.
        atomic = _table_from_role(documents, "evidence_matrix", "atomic-claims")
        if atomic is not None:
            try:
                atomic_id = _column(atomic, "Claim ID")
                critical = _column(atomic, "Decision critical")
                major_target_values = [row[atomic_id].strip() for row in atomic.rows
                                       if row[critical].strip().lower() == "yes"]
                major_targets = set(major_target_values)
            except ContractError as exc:
                report.errors.append(str(exc))
        actions = _table_from_role(documents, "decision_log", "next-actions")
        if actions is not None:
            try:
                action_columns = [_column(actions, label) for label in ("Action", "Dependency", "Deliverable", "Decision enabled")]
                action_type = _column(actions, "Type")
                enabled = _column(actions, "Decision enabled")
                report.check(
                    any(row[action_type].strip().lower() in {"search", "model"}
                        and set(_cell_ids(row[enabled])) & major_targets
                        and all(_meaningful(row[c]) and row[c].strip().lower() not in {"none", "unknown", "not applicable", "n/a"}
                                for c in action_columns) for row in actions.rows),
                    "Zero-candidate conclusion provides a concrete information check or bounded stop",
                    "Zero-candidate conclusion needs a claim-linked information check or bounded stop in next-actions, with inputs and deliverable",
                )
            except ContractError as exc:
                report.errors.append(str(exc))
    target_counts: dict[str, int] = defaultdict(int)
    for target in major_target_values:
        target_counts[target] += 1
    duplicate_targets = sorted(
        target for target, count in target_counts.items() if count != 1
    )
    report.check(
        not duplicate_targets,
        f"{mode} main decision targets are unique",
        f"{mode} main decision target table has duplicate targets: "
        + ", ".join(duplicate_targets),
    )
    invalid_target_types = {
        target
        for target in major_targets
        if (
            mode in {"landscape", "focus"} and not no_candidates
            and not V2_ID_TYPE_PATTERNS["candidate"].fullmatch(target)
        )
        or (
            (mode == "evidence-audit" or no_candidates)
            and not V2_ID_TYPE_PATTERNS["claim"].fullmatch(target)
        )
        or (
            mode == "run-audit"
            and not RUN_AUDIT_TARGET_PATTERN.fullmatch(target)
        )
    }
    report.check(
        not invalid_target_types,
        f"{mode} main targets use valid route/claim ID types",
        f"{mode} main targets have invalid ID types: "
        + ", ".join(sorted(invalid_target_types)),
    )
    if authoritative_major_targets is not None:
        unauthorized_targets = major_targets - authoritative_major_targets
        report.check(
            not unauthorized_targets,
            f"{mode} main targets come from its authoritative claim/parent source",
            f"{mode} main targets are outside the authoritative claim/parent source: "
            + ", ".join(sorted(unauthorized_targets)),
        )
    report.check(
        bool(major_targets),
        f"{mode} defines its main decision targets",
        f"{mode} has no valid main decision targets in {target_table_name}",
    )
    try:
        attack_id_col = _column(attacks, "Attack ID")
        target_col = _column(attacks, "Target claim/route")
        surface_col = _column(attacks, "Attack surface")
        objection_col = _column(attacks, "Strongest objection")
        evidence_test_col = _column(attacks, "Evidence IDs or test")
        severity_col = _column(attacks, "Severity")
        repair_col = _column(attacks, "Required repair or discriminating test")
        verdict_col = _column(attacks, "Verdict")
        attack_decision_col = _column(attacks, "Decision ID")
        attack_status_col = _column(attacks, "Status")
        decision_id_col = _column(decisions, "Decision ID")
        decision_target_col = _column(decisions, "Target ID")
        decision_affected_col = _column(decisions, "Affected decision target IDs")
        decision_status_col = _column(decisions, "Status")
        trigger_col = _column(decisions, "Trigger Attack IDs")
    except ContractError as exc:
        report.errors.append(str(exc))
        return
    report.check(
        len(attacks.rows) >= 8,
        f"Attack register has {len(attacks.rows)} structured attacks",
        "Attack register requires at least eight structured attack rows",
    )
    allowed_surfaces = {
        "problem-adequacy", "mechanism", "evidence", "open-position",
        "capability", "cross-scale", "baseline-system-cost",
        "bio-inspired-translation",
    }
    allowed_severities = {"low", "medium", "high", "blocking"}
    unresolved_statuses = {"open", "unresolved", "accepted"}
    handled_statuses = {"resolved", "mitigated", "closed"}
    allowed_statuses = unresolved_statuses | handled_statuses
    allowed_verdicts = {"keep", "downgrade", "revise", "kill"}
    surfaces = {row[surface_col].strip().lower() for row in attacks.rows}
    report.check(
        surfaces == allowed_surfaces,
        "Attack register covers exactly the eight registered attack surfaces",
        "Attack register must cover exactly the eight registered attack surfaces; "
        f"missing={sorted(allowed_surfaces - surfaces)!r}, extra={sorted(surfaces - allowed_surfaces)!r}",
    )
    decision_map = {row[decision_id_col]: row for row in decisions.rows}
    decision_affected_targets: dict[str, set[str]] = {}
    for decision_id, decision in decision_map.items():
        status_value = decision[decision_status_col].strip().lower()
        report.check(
            status_value in allowed_verdicts,
            f"Decision {decision_id} uses a valid exact status enum",
            f"Decision {decision_id} has invalid status {decision[decision_status_col]!r}",
        )
        affected_targets = set(mode_target_ids(decision[decision_affected_col]))
        decision_affected_targets[decision_id] = affected_targets
        report.check(
            bool(affected_targets),
            f"Decision {decision_id} declares an affected main-decision target",
            f"Decision {decision_id} must declare at least one Affected decision target ID",
        )
        invalid_affected = affected_targets - major_targets
        report.check(
            not invalid_affected,
            f"Decision {decision_id} affects only authoritative {mode} decision targets",
            f"Decision {decision_id} has affected targets outside the authoritative {mode} target set: "
            + ", ".join(sorted(invalid_affected)),
        )

    impact_projection: list[tuple[str, ...]] = []
    impact_table = reader.table("red-team-impact")
    if impact_table is not None:
        try:
            impact_columns = {
                "attack": _column(impact_table, "Attack ID"),
                "target": _column(impact_table, "Target ID"),
                "surface": _column(impact_table, "Attack surface"),
                "objection": _column(impact_table, "Strongest objection"),
                "severity": _column(impact_table, "Severity"),
                "verdict": _column(impact_table, "Verdict"),
                "status": _column(impact_table, "Status"),
                "repair": _column(impact_table, "Exact repair"),
                "decision": _column(impact_table, "Decision ID"),
            }
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            impact_projection = [
                (
                    row[impact_columns["attack"]].strip(),
                    row[impact_columns["target"]].strip(),
                    row[impact_columns["surface"]].strip().lower(),
                    _projection_text(row[impact_columns["objection"]]),
                    row[impact_columns["severity"]].strip().lower(),
                    row[impact_columns["verdict"]].strip().lower(),
                    row[impact_columns["status"]].strip().lower(),
                    _projection_text(row[impact_columns["repair"]]),
                    row[impact_columns["decision"]].strip(),
                )
                for row in impact_table.rows
            ]

    working_projection = [
        (
            row[attack_id_col].strip(),
            row[target_col].strip(),
            row[surface_col].strip().lower(),
            _projection_text(row[objection_col]),
            row[severity_col].strip().lower(),
            row[verdict_col].strip().lower(),
            row[attack_status_col].strip().lower(),
            _projection_text(row[repair_col]),
            row[attack_decision_col].strip(),
        )
        for row in attacks.rows
    ]
    report.check(
        impact_projection == working_projection,
        "Reader red-team-impact projection exactly matches the complete attack register",
        "Reader red-team-impact projection must exactly match every attack-register row and field",
    )

    attacked_targets: set[str] = set()
    for row in attacks.rows:
        attack_id = row[attack_id_col]
        verdict = row[verdict_col].strip().lower()
        target = row[target_col].strip()
        surface = row[surface_col].strip().lower()
        severity = row[severity_col].strip().lower()
        attack_status = row[attack_status_col].strip().lower()
        decision_id = row[attack_decision_col].strip()
        attacked_targets.add(target)
        if mode == "run-audit":
            target_type_ok = bool(RUN_AUDIT_TARGET_PATTERN.fullmatch(target))
        else:
            target_type_ok = bool(V2_ID_TYPE_PATTERNS["claim"].fullmatch(target))
        if mode in {"landscape", "focus"}:
            target_type_ok = target_type_ok or bool(
                V2_ID_TYPE_PATTERNS["candidate"].fullmatch(target)
            )
        report.check(
            target_type_ok and target in valid_ids,
            f"Attack {attack_id} targets a defined or inherited ID",
            f"Attack {attack_id} target {target!r} is not a valid defined/external ID of claim or route type",
        )
        report.check(
            surface in allowed_surfaces,
            f"Attack {attack_id} uses a valid exact attack surface",
            f"Attack {attack_id} has invalid attack surface {row[surface_col]!r}",
        )
        report.check(
            severity in allowed_severities,
            f"Attack {attack_id} uses a valid exact severity",
            f"Attack {attack_id} has invalid severity {row[severity_col]!r}",
        )
        report.check(
            attack_status in allowed_statuses,
            f"Attack {attack_id} uses a valid exact resolution status",
            f"Attack {attack_id} has invalid resolution status {row[attack_status_col]!r}",
        )
        report.check(
            _meaningful(row[evidence_test_col]) and _meaningful(row[repair_col]),
            f"Attack {attack_id} records substantive evidence/test and repair cells",
            f"Attack {attack_id} requires substantive Evidence/test and repair cells",
        )
        report.check(
            not (
                severity in {"high", "blocking"}
                and attack_status in unresolved_statuses
                and verdict == "keep"
            ),
            f"Attack {attack_id} does not Keep an unresolved high-severity finding",
            f"Attack {attack_id} cannot Keep a high/blocking finding with unresolved status {attack_status!r}",
        )
        report.check(
            verdict in allowed_verdicts,
            f"Attack {attack_id} has a valid verdict",
            f"Attack {attack_id} has invalid verdict {row[verdict_col]!r}",
        )
        decision = decision_map.get(decision_id)
        report.check(
            decision is not None,
            f"Attack {attack_id} links to decision {decision_id}",
            f"Attack {attack_id} has no linked decision {decision_id}",
        )
        if decision is not None:
            report.check(
                decision[decision_target_col].strip() == target,
                f"Decision {decision_id} targets the same ID as attack {attack_id}",
                f"Decision {decision_id} target does not match attack {attack_id} target {target}",
            )
            report.check(
                attack_id in _cell_ids(decision[trigger_col], V2_ID_TYPE_PATTERNS["attack"]),
                f"Decision {decision_id} links back to attack {attack_id}",
                f"Decision {decision_id} does not link back to attack {attack_id}",
            )
            report.check(
                decision[decision_status_col].strip().lower() == verdict,
                f"Decision {decision_id} propagates verdict {verdict}",
                f"Decision {decision_id} status does not match attack verdict {verdict}",
            )

    verdict_rank = {"keep": 0, "downgrade": 1, "revise": 2, "kill": 3}
    strongest_by_target: dict[str, tuple[str, set[str]]] = {}
    for row in attacks.rows:
        verdict = row[verdict_col].strip().lower()
        decision_id = row[attack_decision_col].strip()
        if verdict not in verdict_rank:
            continue
        for affected_target in decision_affected_targets.get(decision_id, set()):
            current = strongest_by_target.get(affected_target)
            if current is None or verdict_rank[verdict] > verdict_rank[current[0]]:
                strongest_by_target[affected_target] = (verdict, {decision_id})
            elif verdict == current[0]:
                current[1].add(decision_id)

    integrity_strongest_by_target: dict[str, tuple[str, set[str]]] = {}
    for binding in additional_bindings:
        report.check(
            binding.target_id in major_targets,
            f"Integrity disposition {binding.decision_id} targets an authoritative main route/claim",
            f"Integrity disposition {binding.decision_id} targets non-main ID "
            f"{binding.target_id!r}",
        )
        report.check(
            binding.verdict in verdict_rank,
            f"Integrity disposition {binding.decision_id} uses a valid verdict",
            f"Integrity disposition {binding.decision_id} has invalid verdict "
            f"{binding.verdict!r}",
        )
        if (
            binding.target_id not in major_targets
            or binding.verdict not in verdict_rank
        ):
            continue
        integrity_current = integrity_strongest_by_target.get(
            binding.target_id
        )
        if (
            integrity_current is None
            or verdict_rank[binding.verdict]
            > verdict_rank[integrity_current[0]]
        ):
            integrity_strongest_by_target[binding.target_id] = (
                binding.verdict,
                {binding.decision_id},
            )
        elif binding.verdict == integrity_current[0]:
            integrity_current[1].add(binding.decision_id)
        current = strongest_by_target.get(binding.target_id)
        if (
            current is None
            or verdict_rank[binding.verdict] > verdict_rank[current[0]]
        ):
            strongest_by_target[binding.target_id] = (
                binding.verdict,
                {binding.decision_id},
            )
        elif binding.verdict == current[0]:
            current[1].add(binding.decision_id)

    summary_name, summary_target_aliases, summary_verdict_aliases = {
        "landscape": (
            "decision-summary", ("Recommended route", "推荐路线"),
            ("Disposition", "当前处置"),
        ),
        "focus": (
            "recommended-routes", ("Route", "路线"),
            ("Disposition", "当前处置"),
        ),
        "evidence-audit": (
            "claim-verdicts", ("Claim",), ("Parent impact",),
        ),
        "run-audit": (
            "route-verdicts", ("Route/claim",), ("Verdict",),
        ),
    }[mode]
    if no_candidates:
        summary_name, summary_target_aliases, summary_verdict_aliases = (
            "decision-summary", ("Claim",), ("Disposition",),
        )
    summary_table = reader.table(summary_name)
    reader_decision_targets: set[str] = set()
    if summary_table is not None:
        try:
            summary_target_col = _column(summary_table, *summary_target_aliases)
            summary_verdict_col = _column(summary_table, *summary_verdict_aliases)
            summary_decision_col = _column(summary_table, "Decision ID")
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            target_row_counts: dict[str, int] = defaultdict(int)
            for summary_row in summary_table.rows:
                row_targets = set(mode_target_ids(summary_row[summary_target_col]))
                non_main_targets = row_targets - major_targets
                report.check(
                    not non_main_targets,
                    f"{summary_name} row names only authoritative {mode} targets",
                    f"{summary_name} row contains non-main targets: {sorted(non_main_targets)!r}",
                )
                report.check(
                    len(row_targets) == 1,
                    f"{summary_name} row owns exactly one main decision target",
                    f"{summary_name} rows must each own exactly one main decision target; "
                    f"found {sorted(row_targets)!r}",
                )
                for target_id in row_targets:
                    target_row_counts[target_id] += 1
            reader_decision_targets = set(target_row_counts)
            duplicate_summary_targets = {
                target_id: count
                for target_id, count in target_row_counts.items()
                if count != 1
            }
            report.check(
                not duplicate_summary_targets,
                f"{summary_name} contains one row per main decision target",
                f"{summary_name} has duplicate main decision target rows: "
                f"{duplicate_summary_targets}",
            )
            for target, (binding_verdict, binding_decisions) in strongest_by_target.items():
                preferred_decisions = binding_decisions
                integrity_binding = integrity_strongest_by_target.get(target)
                if (
                    integrity_binding is not None
                    and integrity_binding[0] == binding_verdict
                ):
                    preferred_decisions = integrity_binding[1]
                represented = target in reader_decision_targets
                report.check(
                    represented,
                    f"Affected target {target} appears in the main mode-decision table",
                    f"Affected target {target} is missing from the main mode-decision table",
                )
                if not represented:
                    continue
                aligned = False
                for summary_row in summary_table.rows:
                    if target not in mode_target_ids(summary_row[summary_target_col]):
                        continue
                    verdict_matches = {
                        value
                        for value in allowed_verdicts
                        if re.search(
                            rf"\b{re.escape(value)}\b",
                            summary_row[summary_verdict_col],
                            re.IGNORECASE,
                        )
                    }
                    if (
                        verdict_matches == {binding_verdict}
                        and summary_row[summary_decision_col].strip()
                        in preferred_decisions
                    ):
                        aligned = True
                        break
                report.check(
                    aligned,
                    f"Mode decision for {target} adopts the strongest red-team verdict {binding_verdict} and any equally strong integrity binding",
                    f"Mode decision for {target} understates or mislinks the strongest red-team verdict {binding_verdict} or an equally strong integrity binding",
                )

    report.check(
        major_targets <= attacked_targets,
        f"Red team covers every major {mode} target",
        f"Red team is missing major {mode} targets: "
        + ", ".join(sorted(major_targets - attacked_targets)),
    )
    report.check(
        major_targets <= reader_decision_targets,
        f"Reader mode decision table covers every major {mode} target",
        f"Reader mode decision table is missing major {mode} targets: "
        + ", ".join(sorted(major_targets - reader_decision_targets)),
    )


def _load_parent_audit_facts(
    report: Report,
    manifest: Mapping[str, object],
    *,
    workspace_root: Path,
) -> ParentAuditFacts | None:
    lineage = manifest.get("lineage")
    parents = lineage.get("parents", []) if isinstance(lineage, dict) else []
    if not isinstance(parents, list) or len(parents) != 1 or not isinstance(parents[0], dict):
        return None
    raw_parent = parents[0]
    try:
        parent_dir = _resolve_workspace_path(
            workspace_root,
            raw_parent.get("workspace_relpath"),
            label="run-audit parent path",
        )
        parent_manifest_path = resolve_contained_file(
            parent_dir,
            Path("run-manifest.json"),
            label="run-audit parent manifest",
        )
        parent_manifest = load_json_object(
            parent_manifest_path, label="run-audit parent manifest"
        )
        return inspect_parent_for_audit(parent_dir, parent_manifest, raw_parent)
    except (ContractError, OSError, UnicodeError, ValueError) as exc:
        report.errors.append(f"Cannot inspect run-audit parent: {exc}")
        return None


def _projection_from_table(
    table: V2Table,
    columns: Sequence[str],
) -> tuple[tuple[str, ...], ...]:
    indices = [_column(table, name) for name in columns]
    return tuple(
        tuple(row[index].strip() for index in indices)
        for row in table.rows
    )


def _validate_parent_audit_projections(
    report: Report,
    documents: Mapping[str, V2Document],
    reader: V2Document,
    facts: ParentAuditFacts | None,
) -> tuple[DispositionBinding, ...]:
    if facts is None:
        report.errors.append("Run-audit parent facts could not be reconstructed")
        return ()
    try:
        canonical_manifest_projection = tuple(
            (*row, canonical_manifest_repair(row[0], row[2]))
            for row in facts.manifest_projection
        )
    except ContractError as exc:
        report.errors.append(
            f"Run-audit canonical manifest repair registry is incomplete: {exc}"
        )
        canonical_manifest_projection = ()
    specifications: tuple[
        tuple[str, tuple[str, ...], tuple[tuple[str, ...], ...], str], ...
    ] = (
        (
            "artifact-inventory",
            (
                "Artifact ID", "Manifest role", "Workspace-relative file",
                "Declared", "Exists", "SHA-256", "Schema/contract", "Status",
            ),
            facts.artifact_projection,
            "parent artifact inventory",
        ),
        (
            "manifest-lineage-audit",
            ("Check", "Evidence", "Result", "Required repair"),
            canonical_manifest_projection,
            "parent manifest audit",
        ),
        (
            "id-closure",
            ("ID", "Type", "Defined in", "Referenced in", "Dangling/duplicate/mismatch"),
            facts.id_projection,
            "parent identifier closure",
        ),
        (
            "citation-closure",
            (
                "Reader reference", "Report DOI/stable URL", "Evidence ID",
                "Evidence-matrix DOI/stable URL", "Match", "Computed status",
            ),
            facts.citation_projection,
            "parent citation closure",
        ),
    )
    for marker, columns, expected, label in specifications:
        table = _table_from_documents(documents, marker)
        if table is None:
            continue
        try:
            actual = _projection_from_table(table, columns)
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        report.check(
            actual == expected,
            f"Run-audit exactly projects the recomputed {label}",
            f"Run-audit {label} projection differs from the recomputed parent facts",
        )

    decisions = _table_from_role(documents, "decision_log", "decisions")
    if decisions is None:
        return ()
    try:
        decision_id_col = _column(decisions, "Decision ID")
        decision_status_col = _column(decisions, "Status")
        decision_target_col = _column(decisions, "Target ID")
        decision_affected_col = _column(
            decisions, "Affected decision target IDs"
        )
        decision_text_col = _column(decisions, "Decision")
        decision_trigger_col = _column(decisions, "Trigger Attack IDs")
        decision_owner_col = _column(decisions, "Owner/next action")
    except ContractError as exc:
        report.errors.append(str(exc))
        return ()
    decision_rows_by_id: dict[str, list[list[str]]] = defaultdict(list)
    for decision_row in decisions.rows:
        decision_rows_by_id[
            decision_row[decision_id_col].strip()
        ].append(decision_row)
    attacks = _table_from_role(documents, "red_team", "attack-register")
    attack_decision_ids: set[str] = set()
    if attacks is not None:
        try:
            attack_decision_col = _column(attacks, "Decision ID")
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            attack_decision_ids = {
                row[attack_decision_col].strip() for row in attacks.rows
            }
    route_verdicts = _table_from_role(
        documents, "route_verdicts", "route-verdicts"
    )
    major_targets: set[str] = set()
    if route_verdicts is not None:
        try:
            major_target_col = _column(route_verdicts, "Route/claim ID")
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            major_targets = {
                row[major_target_col].strip() for row in route_verdicts.rows
            }
    bindings: list[DispositionBinding] = []
    manifest_decision_ids: set[str] = set()
    reader_integrity = reader.table("integrity")
    reader_integrity_columns: dict[str, int] | None = None
    if reader_integrity is not None:
        try:
            reader_integrity_columns = {
                name: _column(reader_integrity, name)
                for name in (
                    "Finding",
                    "Evidence",
                    "Severity",
                    "Verdict",
                    "Repair",
                    "Decision ID",
                )
            }
        except ContractError as exc:
            report.errors.append(str(exc))
    manifest_audit = _table_from_documents(
        documents, "manifest-lineage-audit"
    )
    expected_reader_projection: list[tuple[str, ...]] = []
    if manifest_audit is not None:
        try:
            manifest_columns = {
                "check": _column(manifest_audit, "Check"),
                "evidence": _column(manifest_audit, "Evidence"),
                "result": _column(manifest_audit, "Result"),
                "severity": _column(manifest_audit, "Severity"),
                "repair": _column(manifest_audit, "Required repair"),
                "decision": _column(manifest_audit, "Decision ID"),
            }
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            manifest_decision_counts: dict[str, int] = defaultdict(int)
            for manifest_row in manifest_audit.rows:
                manifest_decision_id = manifest_row[
                    manifest_columns["decision"]
                ].strip()
                manifest_result = manifest_row[
                    manifest_columns["result"]
                ].strip().lower()
                valid_manifest_decision_id = bool(
                    V2_ID_TYPE_PATTERNS["decision"].fullmatch(
                        manifest_decision_id
                    )
                )
                report.check(
                    valid_manifest_decision_id,
                    f"Manifest check uses one valid Decision ID {manifest_decision_id}",
                    "Every manifest-lineage-audit row must use exactly one valid "
                    f"Decision ID; got {manifest_decision_id!r}",
                )
                manifest_decision_counts[manifest_decision_id] += 1
                bound_manifest_rows = decision_rows_by_id.get(
                    manifest_decision_id, []
                )
                report.check(
                    len(bound_manifest_rows) == 1,
                    f"Manifest check decision {manifest_decision_id} binds exactly one decision row",
                    f"Manifest check decision {manifest_decision_id} must bind exactly one decision row; "
                    f"found {len(bound_manifest_rows)}",
                )
                if (
                    valid_manifest_decision_id
                    and len(bound_manifest_rows) == 1
                    and manifest_result in {"pass", "not-applicable"}
                ):
                    manifest_decision_status = bound_manifest_rows[0][
                        decision_status_col
                    ].strip().lower()
                    report.check(
                        manifest_decision_status == "keep",
                        f"Manifest {manifest_result} row binds a Keep decision",
                        f"Manifest {manifest_result} row must bind a Keep decision; "
                        f"{manifest_decision_id} is {manifest_decision_status}",
                    )
            for row in manifest_audit.rows:
                result = row[manifest_columns["result"]].strip().lower()
                if result != "fail":
                    continue
                check = row[manifest_columns["check"]].strip()
                evidence = row[manifest_columns["evidence"]].strip()
                severity = row[manifest_columns["severity"]].strip().lower()
                repair = row[manifest_columns["repair"]].strip()
                decision_id = row[manifest_columns["decision"]].strip()
                source = f"parent manifest failure [{check}]"
                try:
                    canonical_repair = canonical_manifest_repair(check, result)
                except ContractError as exc:
                    report.errors.append(
                        "Run-audit canonical manifest repair registry is incomplete: "
                        f"{exc}"
                    )
                    continue
                report.check(
                    repair == canonical_repair,
                    f"Parent manifest failure {check} uses its canonical repair",
                    f"Parent manifest failure {check} must use the canonical repair",
                )
                report.check(
                    severity in {"high", "blocking"},
                    f"Parent manifest failure {check} retains high or blocking severity",
                    f"Parent manifest failure {check} cannot be downgraded below high severity",
                )
                report.check(
                    manifest_decision_counts[decision_id] == 1,
                    f"Parent manifest failure {check} exclusively owns its manifest-table decision",
                    f"Parent manifest failure {check} decision {decision_id} is reused by "
                    "another passed or failed manifest check",
                )
                report.check(
                    decision_id not in manifest_decision_ids,
                    f"Parent manifest failure {check} owns a distinct decision ID",
                    f"Parent manifest failure {check} reuses manifest decision {decision_id}",
                )
                manifest_decision_ids.add(decision_id)
                report.check(
                    decision_id not in attack_decision_ids,
                    f"Parent manifest failure {check} does not reuse an attack decision",
                    f"Parent manifest failure {check} reuses attack decision {decision_id}",
                )
                bound_rows = decision_rows_by_id.get(decision_id, [])
                report.check(
                    len(bound_rows) == 1,
                    f"Parent manifest failure {check} binds exactly one decision row",
                    f"Parent manifest failure {check} must bind exactly one decision row; "
                    f"found {len(bound_rows)} for {decision_id}",
                )
                expected_verdict = ""
                if len(bound_rows) == 1:
                    decision_row = bound_rows[0]
                    expected_verdict = decision_row[
                        decision_status_col
                    ].strip().lower()
                    target = decision_row[decision_target_col].strip()
                    affected = decision_row[decision_affected_col].strip()
                    report.check(
                        expected_verdict in {"downgrade", "revise", "kill"},
                        f"Parent manifest failure {check} has a non-Keep disposition",
                        f"Parent manifest failure {check} must propagate to a "
                        "Downgrade/Revise/Kill decision",
                    )
                    report.check(
                        target in major_targets and affected == target,
                        f"Parent manifest failure {check} binds one authoritative main target",
                        f"Parent manifest failure {check} must target and affect exactly one "
                        "authoritative main route/claim",
                    )
                    report.check(
                        decision_row[decision_text_col].strip()
                        == f"Parent manifest failure [{check}]",
                        f"Decision {decision_id} names manifest check {check} exactly",
                        f"Decision {decision_id} must be named "
                        f"'Parent manifest failure [{check}]'",
                    )
                    report.check(
                        decision_row[decision_trigger_col].strip()
                        == "not-applicable: deterministic manifest check",
                        f"Decision {decision_id} uses the deterministic manifest trigger sentinel",
                        f"Decision {decision_id} must not masquerade as or reuse a red-team attack",
                    )
                    report.check(
                        decision_row[decision_owner_col].strip()
                        == canonical_repair,
                        f"Decision {decision_id} carries the canonical repair",
                        f"Decision {decision_id} Owner/next action must equal the canonical repair",
                    )
                    if (
                        expected_verdict in {"downgrade", "revise", "kill"}
                        and target in major_targets
                        and affected == target
                    ):
                        bindings.append(
                            DispositionBinding(
                                target_id=target,
                                verdict=expected_verdict,
                                decision_id=decision_id,
                                source=source,
                                repair=canonical_repair,
                            )
                        )
                expected_reader_projection.append(
                    (
                        source,
                        evidence,
                        severity,
                        expected_verdict,
                        canonical_repair,
                        decision_id,
                    )
                )
                reader_candidates: list[list[str]] = []
                if (
                    reader_integrity is not None
                    and reader_integrity_columns is not None
                ):
                    reader_candidates = [
                        reader_row
                        for reader_row in reader_integrity.rows
                        if len(reader_row)
                        > max(reader_integrity_columns.values())
                        and (
                            reader_row[
                                reader_integrity_columns["Finding"]
                            ].strip()
                            == source
                            or reader_row[
                                reader_integrity_columns["Decision ID"]
                            ].strip()
                            == decision_id
                        )
                    ]
                reader_matches = [
                    reader_row
                    for reader_row in reader_candidates
                    if reader_row[
                        reader_integrity_columns["Finding"]
                    ].strip()
                    == source
                    and reader_row[
                        reader_integrity_columns["Evidence"]
                    ].strip()
                    == evidence
                    and reader_row[
                        reader_integrity_columns["Severity"]
                    ].strip().lower()
                    == severity
                    and reader_row[
                        reader_integrity_columns["Verdict"]
                    ].strip().lower()
                    == expected_verdict
                    and reader_row[
                        reader_integrity_columns["Repair"]
                    ].strip()
                    == canonical_repair
                    and reader_row[
                        reader_integrity_columns["Decision ID"]
                    ].strip()
                    == decision_id
                ] if reader_integrity_columns is not None else []
                report.check(
                    len(reader_candidates) == 1 and len(reader_matches) == 1,
                    f"Parent manifest failure {check} projects exactly once into reader integrity",
                    f"Parent manifest failure {check} must have exactly one reader integrity row "
                    "selected by Finding or Decision ID with identical evidence, severity, verdict, "
                    "canonical repair, and decision",
                )
    actual_reader_projection: tuple[tuple[str, ...], ...] = ()
    if reader_integrity is not None and reader_integrity_columns is not None:
        actual_reader_projection = tuple(
            (
                row[reader_integrity_columns["Finding"]].strip(),
                row[reader_integrity_columns["Evidence"]].strip(),
                row[reader_integrity_columns["Severity"]].strip().lower(),
                row[reader_integrity_columns["Verdict"]].strip().lower(),
                row[reader_integrity_columns["Repair"]].strip(),
                row[reader_integrity_columns["Decision ID"]].strip(),
            )
            for row in reader_integrity.rows
            if len(row) > max(reader_integrity_columns.values())
        )
    if expected_reader_projection:
        required_reader_projection = tuple(expected_reader_projection)
        projection_label = "all and only recomputed parent manifest failures"
    else:
        required_reader_projection = (
            (
                "manifest, artifact, ID, and citation projections match recomputation",
                "parent-audit deterministic projections",
                "low",
                "keep",
                "retain the immutable snapshot and rerun after parent change",
                "D-001",
            ),
        )
        projection_label = "the canonical clean-parent sentinel"
    report.check(
        actual_reader_projection == required_reader_projection,
        f"Reader integrity contains exactly {projection_label}",
        f"Reader integrity must contain exactly {projection_label}; "
        "extra, missing, reordered, or altered rows are not allowed",
    )

    anomaly_specs = (
        (
            "id-closure",
            "ID",
            "Dangling/duplicate/mismatch",
            {"dangling-reference", "duplicate-definition"},
        ),
        (
            "citation-closure",
            "Reader reference",
            "Computed status",
            {
                "missing-reader-artifact", "missing-evidence-matrix",
                "missing-report-url", "invalid-reader-reference",
                "duplicate-reader-number", "no-reader-references",
                "no-evidence-record", "ambiguous-evidence-record", "url-mismatch",
                "body-reference-missing", "reference-unused",
            },
        ),
    )
    anomaly_records: list[tuple[str, str, str, str, str]] = []
    for marker, key_header, status_header, abnormal_values in anomaly_specs:
        table = _table_from_documents(documents, marker)
        if table is None:
            continue
        try:
            key_col = _column(table, key_header)
            status_col = _column(table, status_header)
            row_repair_col = _column(table, "Repair")
            row_decision_col = _column(table, "Decision ID")
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        for row in table.rows:
            status = row[status_col].strip().lower()
            if status not in abnormal_values:
                continue
            raw_key = row[key_col].strip()
            stable_key = (
                raw_key[1:-1]
                if marker == "citation-closure"
                and raw_key.startswith("[")
                and raw_key.endswith("]")
                else raw_key
            )
            decision_id = row[row_decision_col].strip()
            repair = row[row_repair_col].strip()
            anomaly_records.append(
                (marker, stable_key, status, repair, decision_id)
            )

    anomaly_decision_counts: dict[str, int] = defaultdict(int)
    for _, _, _, _, decision_id in anomaly_records:
        anomaly_decision_counts[decision_id] += 1
    for marker, stable_key, status, repair, decision_id in anomaly_records:
        source = f"parent {marker} anomaly [{stable_key}:{status}]"
        expected_decision_text = (
            f"Parent {marker} anomaly [{stable_key}:{status}]"
        )
        valid_decision_id = bool(
            V2_ID_TYPE_PATTERNS["decision"].fullmatch(decision_id)
        )
        report.check(
            valid_decision_id,
            f"Parent anomaly {source} uses one valid Decision ID",
            f"Parent anomaly {source} must use exactly one valid Decision ID",
        )
        report.check(
            _meaningful(repair),
            f"Parent anomaly {source} records a substantive repair",
            f"Parent anomaly {source} must record a substantive repair",
        )
        shared_attack = decision_id in attack_decision_ids
        report.check(
            shared_attack or anomaly_decision_counts[decision_id] == 1,
            f"Parent anomaly {source} owns a dedicated decision or shares a non-Keep attack decision",
            f"Parent anomaly decision {decision_id} is reused by multiple anomaly rows without an attack binding",
        )
        report.check(
            decision_id not in manifest_decision_ids,
            f"Parent anomaly {source} does not reuse a manifest-failure decision",
            f"Parent anomaly {source} reuses manifest-failure decision {decision_id}",
        )
        bound_rows = decision_rows_by_id.get(decision_id, [])
        report.check(
            len(bound_rows) == 1,
            f"Parent anomaly {source} binds exactly one decision row",
            f"Parent anomaly {source} must bind exactly one decision row; found {len(bound_rows)}",
        )
        if len(bound_rows) != 1:
            continue
        decision_row = bound_rows[0]
        anomaly_verdict = decision_row[decision_status_col].strip().lower()
        target = decision_row[decision_target_col].strip()
        affected = decision_row[decision_affected_col].strip()
        report.check(
            anomaly_verdict in {"downgrade", "revise", "kill"},
            f"Parent anomaly {status} propagates to non-Keep decision {decision_id}",
            f"Parent anomaly {status} must propagate to a Downgrade/Revise/Kill decision",
        )
        report.check(
            target in major_targets and affected == target,
            f"Parent anomaly {source} binds one authoritative main target",
            f"Parent anomaly {source} must target and affect the same authoritative route/claim",
        )
        if not shared_attack:
            report.check(
                decision_row[decision_text_col].strip()
                == expected_decision_text,
                f"Decision {decision_id} names parent anomaly {source} exactly",
                f"Decision {decision_id} must be named {expected_decision_text!r}",
            )
            report.check(
                decision_row[decision_trigger_col].strip()
                == "not-applicable: deterministic parent anomaly",
                f"Decision {decision_id} uses the deterministic parent-anomaly trigger sentinel",
                f"Decision {decision_id} must use the deterministic parent-anomaly trigger sentinel",
            )
            report.check(
                decision_row[decision_owner_col].strip() == repair,
                f"Decision {decision_id} carries the anomaly repair",
                f"Decision {decision_id} Owner/next action must equal the anomaly repair",
            )
        if (
            valid_decision_id
            and anomaly_verdict in {"downgrade", "revise", "kill"}
            and target in major_targets
            and affected == target
        ):
            bindings.append(
                DispositionBinding(
                    target_id=target,
                    verdict=anomaly_verdict,
                    decision_id=decision_id,
                    source=source,
                    repair=repair,
                    exact_final_projection=not shared_attack,
                )
            )
    return tuple(bindings)


def _validate_run_audit(
    report: Report,
    documents: Mapping[str, V2Document],
    reader: V2Document,
    parent_facts: ParentAuditFacts | None,
) -> tuple[DispositionBinding, ...]:
    integrity_bindings = _validate_parent_audit_projections(
        report, documents, reader, parent_facts
    )
    if parent_facts is not None:
        parent_claim_ids = {
            row[0]
            for row in parent_facts.id_projection
            if len(row) >= 2
            and row[1] == "claim"
            and V2_ID_TYPE_PATTERNS["claim"].fullmatch(row[0])
        }
        claim_only_specs = (
            ("evidence_audit", "audited-claims", "Claim ID"),
            ("evidence_audit", "confidence-violations", "Claim ID"),
            ("evidence_audit", "contradictions", "Claim ID"),
            ("reasoning_audit", "open-position-audit", "Claim ID"),
            ("red_team", "evidence-independence", "Claim ID"),
        )
        for role, marker, header in claim_only_specs:
            owner = documents.get(role)
            table = owner.table(marker) if owner is not None else None
            if table is None:
                continue
            try:
                claim_col = _column(table, header)
            except ContractError as exc:
                report.errors.append(str(exc))
                continue
            for row in table.rows:
                claim_id = row[claim_col].strip()
                report.check(
                    bool(V2_ID_TYPE_PATTERNS["claim"].fullmatch(claim_id))
                    and claim_id in parent_claim_ids,
                    f"Run-audit {marker} row targets a parent-authoritative claim",
                    f"Run-audit {marker} Claim ID must be exactly one "
                    f"parent-authoritative claim ID; found {claim_id!r}",
                )

        scientific_red_team = reader.table("scientific-red-team")
        if scientific_red_team is not None:
            try:
                reader_claim_col = _column(scientific_red_team, "Claim")
            except ContractError as exc:
                report.errors.append(str(exc))
            else:
                for row in scientific_red_team.rows:
                    value = row[reader_claim_col]
                    claim_ids = _cell_ids(
                        value, V2_ID_TYPE_PATTERNS["claim"]
                    )
                    audit_target_ids = RUN_AUDIT_TARGET_PATTERN.findall(value)
                    report.check(
                        len(claim_ids) == 1
                        and len(audit_target_ids) == 1
                        and claim_ids[0] in parent_claim_ids,
                        "Reader scientific-red-team row owns exactly one "
                        "parent-authoritative claim",
                        "Reader scientific-red-team Claim must contain exactly one "
                        f"parent-authoritative claim ID; found {value!r}",
                    )
    verdicts = _table_from_role(documents, "route_verdicts", "route-verdicts")
    reader_verdicts = reader.table("route-verdicts")
    if verdicts is None or reader_verdicts is None:
        return integrity_bindings
    try:
        target_col = _column(verdicts, "Route/claim ID")
        finding_col = _column(verdicts, "Strongest finding")
        verdict_col = _column(verdicts, "Verdict")
        decision_col = _column(verdicts, "Decision ID")
        allowed_col = _column(verdicts, "Allowed current conclusion", "Allowed conclusion")
        repair_col = _column(verdicts, "Required repair")
        reader_target_col = _column(reader_verdicts, "Route/claim ID", "Route/claim")
        reader_finding_col = _column(
            reader_verdicts, "Strongest objection", "Strongest finding"
        )
        reader_verdict_col = _column(reader_verdicts, "Verdict")
        reader_decision_col = _column(reader_verdicts, "Decision ID")
        reader_allowed_col = _column(reader_verdicts, "Allowed conclusion", "Allowed current conclusion")
        reader_repair_col = _column(reader_verdicts, "Required repair")
    except ContractError as exc:
        report.errors.append(str(exc))
        return integrity_bindings
    working_projection = {
        row[target_col].strip(): (
            row[finding_col].strip(),
            row[verdict_col].strip().lower(),
            row[allowed_col].strip(),
            row[repair_col].strip(),
            row[decision_col].strip(),
        )
        for row in verdicts.rows
    }
    reader_projection = {
        row[reader_target_col].strip(): (
            row[reader_finding_col].strip(),
            row[reader_verdict_col].strip().lower(),
            row[reader_allowed_col].strip(),
            row[reader_repair_col].strip(),
            row[reader_decision_col].strip(),
        )
        for row in reader_verdicts.rows
    }
    report.check(
        working_projection == reader_projection,
        "Run-audit working and reader verdict projections are identical",
        "Run-audit reader route-verdicts must match working target, strongest finding, "
        "verdict, allowed conclusion, required repair, and Decision ID",
    )
    binding_by_target_decision = {
        (binding.target_id, binding.decision_id): binding
        for binding in integrity_bindings
        if binding.exact_final_projection
    }
    for row in verdicts.rows:
        target = row[target_col].strip()
        decision_id = row[decision_col].strip()
        binding = binding_by_target_decision.get((target, decision_id))
        if binding is None:
            continue
        report.check(
            row[finding_col].strip() == binding.source,
            f"Final route verdict {decision_id} preserves its canonical integrity finding",
            f"Final route verdict {decision_id} Strongest finding must equal "
            f"{binding.source!r}",
        )
        report.check(
            row[repair_col].strip() == binding.repair,
            f"Final route verdict {decision_id} preserves its canonical integrity repair",
            f"Final route verdict {decision_id} Required repair must equal the "
            "canonical manifest repair",
        )
    report.check(
        all(_meaningful(row[allowed_col]) and _meaningful(row[repair_col]) for row in verdicts.rows)
        and all(
            _meaningful(row[reader_allowed_col]) and _meaningful(row[reader_repair_col])
            for row in reader_verdicts.rows
        ),
        "Run-audit verdicts contain allowed conclusions and exact repairs",
        "Run-audit working and reader verdicts require substantive allowed conclusions and repairs",
    )
    return integrity_bindings


def _validate_lens(
    report: Report,
    documents: Mapping[str, V2Document],
    *,
    mode: str,
    lens: str,
) -> None:
    if mode == "run-audit":
        return
    queries = _table_from_documents(documents, "search-queries")
    signals = _table_from_documents(documents, "frontier-signals")
    if queries is None or signals is None:
        return
    try:
        query_id_col = _column(queries, "Query ID")
        lane_col = _column(queries, "Search lane")
        query_text_col = _column(queries, "Exact query and filters")
        purpose_col = _column(queries, "Purpose")
        result_col = _column(queries, "Results")
        evidence_col = _column(queries, "Evidence IDs")
        miss_col = _column(queries, "Miss/limitation")
        signal_type_col = _column(signals, "Signal type")
        signal_value_col = _column(signals, "Value or unavailable")
        signal_source_col = _column(signals, "Source")
        signal_date_col = _column(signals, "As-of date")
    except ContractError as exc:
        report.errors.append(str(exc))
        return
    lanes = {row[lane_col].strip().lower() for row in queries.rows}
    if lens in {"frontier-led", "balanced"}:
        report.check(
            any("canonical" in lane for lane in lanes)
            and any("frontier" in lane for lane in lanes),
            "Frontier lens includes canonical-anchor and frontier-radar lanes",
            "Frontier lens requires canonical-anchor and frontier-radar search lanes",
        )
        signal_types = {row[signal_type_col].strip().lower() for row in signals.rows}
        report.check(
            any("synthesis" in value for value in signal_types)
            and any("primary" in value for value in signal_types),
            "Frontier radar includes synthesis and representative-primary signals",
            "Frontier radar requires authoritative-synthesis and representative-primary signals",
        )
        for row in signals.rows:
            if row[signal_value_col].strip().lower() != "unavailable":
                report.check(
                    _meaningful(row[signal_source_col])
                    and bool(re.fullmatch(r"\d{4}-\d{2}-\d{2}", row[signal_date_col].strip())),
                    "Frontier citation/venue signal records source and as-of date",
                    "Available frontier signals require source and YYYY-MM-DD as-of date",
                )
    if lens in {"gray-space-led", "balanced"}:
        mismatch_table = _table_from_documents(documents, "gray-space-mismatch")
        searchable_rows = [
            (row, " ".join((row[lane_col], row[query_text_col], row[purpose_col])).lower())
            for row in queries.rows
        ]
        mismatch_rows = [
            row for row, text in searchable_rows
            if re.search(r"mismatch|cross[- ]domain|two[- ]sided|analogy|translation|错配|跨域|双侧", text)
        ]
        neighbor_rows = [
            row for row, text in searchable_rows
            if re.search(r"neighbor|bounded[- ]negative|direct[- ]adjacent|crowding|邻近|相邻|有界负", text)
        ]
        if mismatch_table is not None:
            try:
                mature_col = _column(mismatch_table, "Mature need positive Evidence IDs")
                mechanism_col = _column(mismatch_table, "Candidate mechanism positive Evidence IDs")
                bounded_query_col = _column(mismatch_table, "Bounded neighbor-miss Query ID")
            except ContractError as exc:
                report.errors.append(str(exc))
            else:
                query_rows = {row[query_id_col]: row for row in queries.rows}
                valid_mismatches = 0
                for row in mismatch_table.rows:
                    mature_ids = _cell_ids(row[mature_col], V2_ID_TYPE_PATTERNS["evidence"])
                    mechanism_ids = _cell_ids(row[mechanism_col], V2_ID_TYPE_PATTERNS["evidence"])
                    bounded_ids = _cell_ids(row[bounded_query_col], V2_ID_TYPE_PATTERNS["query"])
                    bounded_ok = any(
                        query_id in query_rows
                        and bool(re.search(
                            r"sparse|bounded|neighbor|未命中|稀疏|边界|邻近",
                            query_rows[query_id][miss_col],
                            re.IGNORECASE,
                        ))
                        for query_id in bounded_ids
                    )
                    if mature_ids and mechanism_ids and bounded_ok:
                        valid_mismatches += 1
                report.check(
                    valid_mismatches >= 1,
                    "Gray-space mismatch has two-sided positive evidence and a bounded neighbor check",
                    "Gray-space mismatch requires mature-need evidence, mechanism evidence, and a bounded neighbor query",
                )
        else:
            report.check(
                bool(mismatch_rows) and bool(neighbor_rows),
                "Gray-space lens includes mismatch and bounded-neighbor searches",
                "Gray-space lens requires mismatch and bounded-neighbor searches",
            )
            report.check(
                any(len(set(_cell_ids(row[evidence_col], V2_ID_TYPE_PATTERNS["evidence"]))) >= 2 for row in mismatch_rows),
                "Gray-space mismatch has two-sided positive evidence",
                "Gray-space mismatch requires at least two positive Evidence IDs",
            )
        for row in queries.rows:
            if re.fullmatch(r"(?:0|zero)", row[result_col].strip(), re.IGNORECASE):
                miss = row[miss_col]
                report.check(
                    not UNBOUNDED_PRIORITY.search(miss)
                    and bool(re.search(r"sparse|bounded|未命中|稀疏|边界", miss, re.IGNORECASE)),
                    "Zero-hit query is recorded only as bounded sparse evidence",
                    "Zero-hit query is converted into an unbounded novelty/absence claim",
                )



_BIO_DASH_PATTERN = re.compile(
    r"[\u058a\u05be\u1400\u1806\u2010-\u2015\u2212\u2e3a-\u2e3b\ufe58\ufe63\uff0d]"
)
_CAPABILITY_CONTEXT_PATTERN = re.compile(
    r"\b(?:capabilit(?:y|ies)|expertise|skills?|instrument(?:ation)?|"
    r"facilit(?:y|ies)|characteri[sz]ation|measurement\s+access|"
    r"fabrication\s+access|simulation\s+access)\b|"
    r"能力|经验|技能|仪器|设施|表征条件|制备条件|仿真条件",
    re.IGNORECASE,
)
_NON_PREMISE_DISCLAIMER_PATTERN = re.compile(
    r"\b(?:capability|inventory|context)(?:\s+context)?\s+only\b|"
    r"\bnot\s+(?:an?\s+)?(?:scientific|research)\s+"
    r"(?:premise|claim|hypothesis)\b|"
    r"仅(?:为|作)?(?:能力|条件|清单|背景)|"
    r"(?:不是|并非|非)(?:科学|研究)?(?:前提|主张|假设)",
    re.IGNORECASE,
)
_CAPABILITY_SUBJECT_PATTERN = re.compile(
    r"^(?:(?:the|our)\s+)?(?:lab(?:oratory)?|group|team|facility|we)\s+"
    r"(?:has|have|possess(?:es)?|reports?|lists?|maintains?|provides?|"
    r"offers?|can\s+(?:perform|access|characterize|measure|fabricate|simulate))\b|"
    r"^(?:本|我们)?(?:实验室|课题组|团队|平台)(?:具备|拥有|可进行|可访问|已报告)",
    re.IGNORECASE,
)
_CAPABILITY_END_PATTERN = re.compile(
    r"(?:capabilit(?:y|ies)|expertise|skills?|instrument(?:ation)?|"
    r"facilit(?:y|ies)|characteri[sz]ation\s+(?:capability|access)|"
    r"measurement\s+access|fabrication\s+access|simulation\s+access|"
    r"能力|经验|技能|仪器|设施|表征条件|制备条件|仿真条件)"
    r"(?:\s+(?:is|are))?$",
    re.IGNORECASE,
)
_CAPABILITY_DESCRIPTOR_END_PATTERN = re.compile(
    r"(?:characteri[sz]ation|measurement|fabrication|simulation|"
    r"modeling|modelling|testing|instrumentation|表征|测量|制备|仿真)$",
    re.IGNORECASE,
)
_DISCLAIMER_ONLY_PATTERN = re.compile(
    r"^(?:(?:this|that|it)\s+(?:is|was)\s+)?"
    r"(?:capability|inventory|context)(?:\s+context)?\s+only"
    r"(?:\s*,?\s*(?:and\s+)?not\s+(?:an?\s+)?"
    r"(?:scientific|research)\s+(?:premise|claim|hypothesis))?$|"
    r"^(?:这|此)?(?:仅(?:为|作)?(?:能力|条件|清单|背景)"
    r"(?:，?(?:不是|并非|非)(?:科学|研究)?(?:前提|主张|假设))?)$",
    re.IGNORECASE,
)

_TRAILING_NON_PREMISE_PATTERN = re.compile(
    r"^(?:and\s+)?not\s+(?:an?\s+)?(?:scientific|research)\s+"
    r"(?:premise|claim|hypothesis)$|"
    r"^(?:而且|并且)?(?:不是|并非|非)(?:科学|研究)?(?:前提|主张|假设)$",
    re.IGNORECASE,
)

def _normalize_bio_scan_text(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    text = "".join(
        character for character in text
        if unicodedata.category(character) != "Cf"
    )
    text = _BIO_DASH_PATTERN.sub("-", text)
    return re.sub(r"[\u00a0\u202f]", " ", text)


def _clean_metadata_clause(value: str) -> str:
    return value.strip().strip(".!?;。！？；").strip()


def _inline_capability_only_clause(clause: str) -> bool:
    disclaimer = _NON_PREMISE_DISCLAIMER_PATTERN.search(clause)
    if disclaimer is None or not _CAPABILITY_CONTEXT_PATTERN.search(clause):
        return False
    trailing = clause[disclaimer.end():].strip(" \t,，")
    if trailing and _TRAILING_NON_PREMISE_PATTERN.fullmatch(trailing) is None:
        return False
    prefix = clause[:disclaimer.start()].strip(" \t,，")
    return bool(
        _CAPABILITY_END_PATTERN.search(prefix)
        or (
            disclaimer.group(0).casefold().startswith("capability")
            and _CAPABILITY_DESCRIPTOR_END_PATTERN.search(prefix)
        )
    )


def _paired_capability_inventory_clause(clause: str) -> bool:
    return bool(
        _CAPABILITY_SUBJECT_PATTERN.search(clause)
        and _CAPABILITY_CONTEXT_PATTERN.search(clause)
        and _CAPABILITY_END_PATTERN.search(clause)
    )


def _bare_structured_capability_clause(clause: str) -> bool:
    return bool(
        _CAPABILITY_CONTEXT_PATTERN.search(clause)
        and _CAPABILITY_END_PATTERN.search(clause)
    )


def _manifest_bio_premise_text(
    value: object,
    *,
    structured_capability: bool = False,
) -> str:
    """Remove only narrow, explicit capability-inventory clauses."""

    normalized = _normalize_bio_scan_text(value)
    clauses = [
        _clean_metadata_clause(clause)
        for clause in re.split(r"(?<=[.!?;。！？；\n])", normalized)
        if _clean_metadata_clause(clause)
    ]
    kept: list[str] = []
    index = 0
    while index < len(clauses):
        clause = clauses[index]
        if _inline_capability_only_clause(clause):
            index += 1
            continue
        if (
            index + 1 < len(clauses)
            and _paired_capability_inventory_clause(clause)
            and _DISCLAIMER_ONLY_PATTERN.fullmatch(clauses[index + 1])
        ):
            index += 2
            continue
        if structured_capability and _bare_structured_capability_clause(clause):
            index += 1
            continue
        kept.append(clause)
        index += 1
    return " ".join(kept)


def _validate_bio_translation(
    report: Report,
    documents: Mapping[str, V2Document],
    reader: V2Document,
    manifest: Mapping[str, object],
) -> None:
    routing = manifest.get("routing", {})
    request = routing.get("request", "") if isinstance(routing, dict) else ""
    secondary_lenses = manifest.get("secondary_domain_lenses", [])
    if not isinstance(secondary_lenses, list):
        secondary_lenses = []
    metadata_fragments = [
        _manifest_bio_premise_text(manifest.get("domain", "")),
        _manifest_bio_premise_text(request),
    ]
    domain_lens_notes = manifest.get("domain_lens_notes")
    if manifest.get("primary_domain_lens") == "custom":
        try:
            custom_slots = parse_custom_domain_lens_notes(domain_lens_notes)
        except ContractError:
            custom_slots = {}
        metadata_fragments.extend(
            _manifest_bio_premise_text(
                value,
                structured_capability=(slot == "capability interface"),
            )
            for slot, value in custom_slots.items()
        )
    else:
        metadata_fragments.append(_manifest_bio_premise_text(domain_lens_notes or ""))
    claim_trigger_text = "\n".join(metadata_fragments)
    lens_text = _normalize_bio_scan_text("\n".join([
        str(manifest.get("primary_domain_lens", "")),
        " ".join(str(item) for item in secondary_lenses if isinstance(item, str)),
    ]))
    biological_source = (
        r"(?:biolog(?:y|ical)|nature|brain|neur(?:on|onal)|synap(?:se|tic)|"
        r"retina|immune\s+system|cort(?:ex|ical)|astrocyt(?:e|ic)|"
        r"glia(?:l)?|dendrit(?:e|ic)|axon(?:al)?)"
    )
    bio_pattern = re.compile(
        r"bio(?:logical(?:ly)?)?(?:-|\s)*inspired|"
        r"biology(?:-|\s)*inspired|biomim|neuromorph|"
        r"(?:neuro|neural|brain|neuron(?:al)?|synap(?:se|tic)|"
        r"immune|retina|nature)(?:-|\s)*(?:inspired|like|mimic(?:king)?|mimetic)|"
        r"artificial(?:-|\s)+(?:neuron(?:al)?|synap(?:se|tic))|"
        r"(?:inspired|derived|modeled|modelled)(?:-|\s)+(?:by|from|after)"
        r"(?:-|\s)+(?:the(?:-|\s)+)?" + biological_source + r"|"
        r"(?:draw(?:s|n|ing)?|drew)(?:-|\s)+inspiration(?:-|\s)+from"
        r"(?:-|\s)+(?:the(?:-|\s)+)?" + biological_source + r"|"
        r"borrow(?:s|ed|ing)?(?:-|\s)+(?:from(?:-|\s)+)?"
        r"(?:the(?:-|\s)+)?" + biological_source + r"(?:['’]s)?|"
        r"(?:based|grounded)(?:-|\s)+on(?:-|\s)+(?:the(?:-|\s)+)?"
        + biological_source + r"|"
        r"brain\s+function|biological\s+(?:observation|analogy|function|superiority|computation)|"
        r"\b(?:neuronal|synaptic|cortical)\b|"
        r"\bbrain\s+(?:computation|computing|plasticity|memory|learning|efficien(?:cy|t)|superiority)\b|"
        r"\b(?:astrocyt(?:e|ic)|dendrit(?:e|ic)|axon(?:al)?|glia(?:l)?|metaplasticity|homeostatic(?:-|\s)+plasticity)\b|"
        r"spiking(?:-|\s)*neural|hebbian|"
        r"仿生|生物启发|生物(?:观察|类比|功能|优势|优越性|计算)|"
        r"神经形态|大脑|类脑|脑启发|人工(?:神经元|突触)|"
        r"(?:神经元|突触)(?:启发|仿生|类|模拟|拟态)|"
        r"(?:受|从|借鉴|源自|仿照|模拟).{0,24}"
        r"(?:视网膜|免疫系统|自然|生物|大脑|神经元|突触).{0,24}"
        r"(?:启发|借鉴|原理|机制|编码|记忆)?|赫布",
        re.IGNORECASE,
    )
    claim_metadata_trigger = bool(bio_pattern.search(claim_trigger_text))
    metadata_declared = claim_metadata_trigger or bool(bio_pattern.search(lens_text))
    mode = str(manifest.get("run_type", ""))
    premise_roles = {
        "landscape": {"intake", "research_map", "candidate_portfolio", "reader_report"},
        "focus": {"intake", "focus_scope", "claim_mechanism_map", "route_protocol", "reader_report"},
        "evidence-audit": {"audit_scope", "claim_register", "confidence_assessment", "reader_report"},
        "run-audit": {"audit_scope", "reasoning_audit", "route_verdicts", "reader_report"},
    }.get(mode, {"reader_report"})
    raw_content_text = "\n".join(
        line.text
        for role, document in documents.items()
        if role in premise_roles
        for block_name, block in (*document.blocks.items(), *document.projections.items())
        if block_name not in {
            "bio-inspired-translation",
            "bio-inspired-audit",
            "attack-register",
            "red-team-impact",
            "capability-passport",
            "cross-scale-audit",
            "capability-cross-scale",
            "direct-neighbors",
            "frontier-radar",
            "sota-families",
            "supplemental-search",
            "evidence-confidence",
            "references",
        }
        for line in block.lines
    )
    content_text = _normalize_bio_scan_text(re.sub(
        r"bio(?:-|\s)?inspired(?:-|\s)(?:translation|audit)",
        "",
        raw_content_text,
        flags=re.IGNORECASE,
    ))
    content_trigger = bool(bio_pattern.search(content_text))
    bio_triggered = claim_metadata_trigger or content_trigger
    report.check(
        not content_trigger or metadata_declared,
        "Bio-related artifact content is declared in manifest routing/domain metadata",
        "Bio-related artifact content requires bio/neuromorphic manifest metadata",
    )
    working_documents = {
        role: document
        for role, document in documents.items()
        if role != "reader_report"
    }
    red_team_document = working_documents.get("red_team")
    attacks = (
        red_team_document.table("attack-register")
        if red_team_document is not None
        else None
    )
    bio_attacks = []
    if attacks is not None:
        try:
            attack_id_col = _column(attacks, "Attack ID")
            attack_target_col = _column(attacks, "Target claim/route")
            attack_surface_col = _column(attacks, "Attack surface")
            attack_verdict_col = _column(attacks, "Verdict")
            attack_decision_col = _column(attacks, "Decision ID")
        except ContractError as exc:
            report.errors.append(str(exc))
        else:
            bio_attacks = [
                row for row in attacks.rows if row[attack_id_col].strip() == "A-008"
            ]
            report.check(
                len(bio_attacks) == 1,
                "Bio translation attack A-008 is unique",
                "Every run requires exactly one A-008 attack",
            )
            if len(bio_attacks) == 1:
                report.check(
                    bio_attacks[0][attack_surface_col].strip().lower()
                    == "bio-inspired-translation",
                    "A-008 owns the bio-inspired-translation attack surface",
                    "A-008 must use attack surface bio-inspired-translation",
                )

    translation_owner_role = {
        "landscape": "research_map",
        "focus": "claim_mechanism_map",
    }.get(mode)
    translation_owner_document = (
        working_documents.get(translation_owner_role)
        if translation_owner_role is not None
        else None
    )
    translation_table = (
        translation_owner_document.table("bio-inspired-translation")
        if translation_owner_document is not None
        else None
    )
    audit_owner_roles = (
        ("red_team", "reasoning_audit")
        if mode == "run-audit"
        else ("red_team",)
    )
    owned_audit_tables: list[tuple[str, V2Table]] = []
    for role in audit_owner_roles:
        owner_document = working_documents.get(role)
        owner_table = (
            owner_document.table("bio-inspired-audit")
            if owner_document is not None
            else None
        )
        report.check(
            owner_table is not None,
            f"{role} owns its required bio-inspired audit table",
            f"{role} is missing its required bio-inspired audit table",
        )
        if owner_table is not None:
            owned_audit_tables.append((role, owner_table))
    reader_translation = reader.table("bio-inspired-translation")
    reader_audit = reader.table("bio-inspired-audit")

    not_applicable = re.compile(
        r"\b(?:not\s+applicable|n\s*/?\s*a)\b|不适用|无(?:生物|仿生)",
        re.IGNORECASE,
    )

    def complete_non_na_row(table: V2Table, headers: Sequence[str]) -> bool:
        try:
            columns = [_column(table, header) for header in headers]
        except ContractError as exc:
            report.errors.append(str(exc))
            return False
        return any(
            all(
                _meaningful(row[column])
                and not not_applicable.search(row[column])
                for column in columns
            )
            for row in table.rows
        )

    audit_chain_headers = (
        "Biological observation",
        "Abstract principle",
        "Mathematical operator/state-update rule",
        "Algorithm",
        "Hardware primitive",
        "De-biologized scientific question",
        "Non-biological baseline",
        "Principle-specific ablation",
        "Intrinsic gain/boundary",
    )
    if bio_triggered:
        for role, table in owned_audit_tables:
            report.check(
                bool(table.rows) and complete_non_na_row(table, audit_chain_headers),
                f"{role} bio-inspired audit contains a complete non-N/A translation chain",
                f"{role} cannot satisfy bio-inspired audit with an incomplete or all-N/A chain",
            )
        if reader_audit is not None:
            report.check(
                complete_non_na_row(reader_audit, audit_chain_headers),
                "Bio-related reader audit contains a complete non-N/A translation chain",
                "Bio-related reader bio-inspired audit cannot be all N/A",
            )

    if len(bio_attacks) == 1:
        expected = (
            bio_attacks[0][attack_target_col].strip(),
            bio_attacks[0][attack_verdict_col].strip().lower(),
            bio_attacks[0][attack_decision_col].strip(),
        )

        def audit_matches_attack(table: V2Table) -> bool:
            try:
                target_col = _column(table, "Target")
                verdict_col = _column(table, "Verdict")
                decision_col = _column(table, "Decision ID")
                chain_columns = [
                    _column(table, header) for header in audit_chain_headers
                ]
            except ContractError as exc:
                report.errors.append(str(exc))
                return False
            return any(
                (
                    row[target_col].strip(),
                    row[verdict_col].strip().lower(),
                    row[decision_col].strip(),
                ) == expected
                and (
                    not bio_triggered
                    or all(
                        _meaningful(row[column])
                        and not not_applicable.search(row[column])
                        for column in chain_columns
                    )
                )
                for row in table.rows
            )

        alignment_detail = " on one complete row" if bio_triggered else ""
        for role, table in owned_audit_tables:
            report.check(
                audit_matches_attack(table),
                f"{role} bio-inspired audit verdict and decision match A-008",
                f"{role} bio-inspired audit must match A-008 target, verdict, and Decision ID{alignment_detail}",
            )
        if reader_audit is not None:
            report.check(
                audit_matches_attack(reader_audit),
                "Reader bio-inspired audit verdict and decision match A-008",
                "Reader bio-inspired audit must match A-008 target, verdict, and Decision ID"
                + alignment_detail,
            )

    if not bio_triggered:
        return

    if mode not in {"landscape", "focus"}:
        return
    report.check(
        translation_table is not None and bool(translation_table.rows),
        f"Bio-related {mode} run contains its owner-bound translation-chain table",
        f"Bio-related {mode} run requires the biological-observation-to-hardware translation table in {translation_owner_role}",
    )
    if translation_table is None:
        return
    translation_headers = (
        "Biological observation",
        "Abstract computational principle",
        "Mathematical operator/state-update rule",
        "Algorithm",
        "Hardware primitive",
        "De-biologized scientific question",
        "Non-biological strong baseline",
        "Principle-specific ablation",
        "Measurable intrinsic gain and boundary",
    )
    report.check(
        complete_non_na_row(translation_table, translation_headers),
        "Bio working translation chain is complete and non-N/A",
        f"Bio translation chain must be non-N/A in {translation_owner_role} and include observation, principle, mathematical operator/state update, algorithm, primitive, de-biologized question, non-bio baseline, principle-specific ablation, and bounded gain",
    )
    report.check(
        reader_translation is not None
        and complete_non_na_row(reader_translation, translation_headers),
        "Bio reader translation chain is complete and non-N/A",
        "Bio-related reader report requires a complete non-N/A translation chain",
    )


DEEP_READING_CANONICAL_FILES = frozenset(
    {
        "paper-package.md",
        "reading-report.md",
        "auxiliary-literature-table.md",
        "external-evidence-matrix.md",
        "view-report-audit.md",
    }
)
SIX_SEARCH_LANES = (
    "canonical-anchor",
    "frontier-radar",
    "sota-family",
    "direct-neighbor",
    "baseline-negative",
    "translation",
)
RECALL_BOUNDARY_PATTERN = re.compile(
    r"\b(?:database|corpus|query|queries|date|window|language|term(?:inology)?|"
    r"access|coverage|bounded)\b|数据库|语料|检索|查询|日期|时间窗|语种|术语|访问|覆盖|有界",
    re.IGNORECASE,
)


def _canonical_deep_read_refs(value: str) -> tuple[set[str], bool]:
    files = {
        match.group(1).lower()
        for match in re.finditer(r"(?i)([a-z0-9_-]+\.md)", value)
    }
    return files, bool(files) and files <= DEEP_READING_CANONICAL_FILES


def _validate_deep_reading_handoff(
    report: Report,
    documents: Mapping[str, V2Document],
    *, workspace_root: Path | None = None,
) -> None:
    evidence = _table_from_role(documents, "evidence_matrix", "evidence-records")
    queue = _table_from_role(documents, "evidence_matrix", "deep-reading-handoff")
    if evidence is None or queue is None:
        return
    try:
        evidence_id_col = _column(evidence, "Evidence ID")
        context_col = _column(evidence, "Full-context status")
        depth_col = _column(evidence, "verification_depth")
        verification_col = _column(evidence, "Verification")
        evidence_ref_col = _column(evidence, "Canonical cross-run ref")
        source_col = _column(evidence, "DOI or stable URL")
        request_id_col = _column(queue, "Deep-read request ID")
        paper_col = _column(queue, "Paper key")
        target_col = _column(queue, "Target Claim/Route IDs")
        question_col = _column(queue, "Decision-changing question")
        priority_col = _column(queue, "Priority: high/medium/low")
        status_col = _column(
            queue, "Status: queued/in-progress/imported/blocked/skipped"
        )
        run_col = _column(queue, "Deep Reading run")
        refs_col = _column(queue, "Canonical refs")
        imported_col = _column(queue, "Imported Evidence IDs")
        decision_col = _column(queue, "Blocker or import decision")
    except ContractError as exc:
        report.errors.append(str(exc))
        return

    evidence_rows = {row[evidence_id_col].strip(): row for row in evidence.rows}
    allowed_depths = {"metadata", "abstract", "full-text", "canonical-deep-read"}
    compatible_context = {
        "metadata": {"metadata-only", "not-accessed"},
        "abstract": {"abstract-only"},
        "full-text": {"full-context-verified"},
        "canonical-deep-read": {"full-context-verified"},
    }
    for evidence_id, row in evidence_rows.items():
        depth = row[depth_col].strip().lower()
        context = row[context_col].strip().lower()
        report.check(
            depth in allowed_depths,
            f"Evidence {evidence_id} uses a valid verification_depth",
            f"Evidence {evidence_id} has invalid verification_depth {row[depth_col]!r}",
        )
        if depth in compatible_context:
            report.check(
                context in compatible_context[depth],
                f"Evidence {evidence_id} verification_depth matches Full-context status",
                f"Evidence {evidence_id} verification_depth {depth!r} is incompatible "
                f"with Full-context status {context!r}",
            )
        canonical_ref = row[evidence_ref_col].strip()
        if depth == "canonical-deep-read":
            _, refs_valid = _canonical_deep_read_refs(canonical_ref)
            report.check(
                refs_valid,
                f"Evidence {evidence_id} points to Deep Reading canonical evidence",
                f"Evidence {evidence_id} canonical-deep-read must reference only "
                "Deep Reading canonical artifacts, never view-report.md",
            )
            report.check(
                row[verification_col].strip().lower() in {"verified", "已核验"},
                f"Evidence {evidence_id} canonical deep read is verified",
                f"Evidence {evidence_id} canonical-deep-read requires Verification=verified",
            )
        elif canonical_ref.lower() not in {"none", "not applicable"}:
            _, refs_valid = _canonical_deep_read_refs(canonical_ref)
            report.check(
                refs_valid,
                f"Evidence {evidence_id} optional cross-run ref is canonical",
                f"Evidence {evidence_id} Canonical cross-run ref names a derived or unknown file",
            )

    allowed_priorities = {"high", "medium", "low"}
    allowed_statuses = {"queued", "in-progress", "imported", "blocked", "skipped"}
    paper_requests: dict[str, str] = {}
    import_owners: dict[str, list[str]] = defaultdict(list)
    canonical_cache: dict = {}
    for row in queue.rows:
        request_id = row[request_id_col].strip()
        priority = row[priority_col].strip().lower()
        status = row[status_col].strip().lower()
        targets = set(_cell_ids(row[target_col])) & {
            identifier
            for identifier in _cell_ids(row[target_col])
            if V2_ID_TYPE_PATTERNS["claim"].fullmatch(identifier)
            or V2_ID_TYPE_PATTERNS["candidate"].fullmatch(identifier)
        }
        imported_ids = set(
            _cell_ids(row[imported_col], V2_ID_TYPE_PATTERNS["evidence"])
        )
        paper_identity = canonical_links.normalize_identity(row[paper_col])
        report.check(
            paper_identity not in paper_requests,
            f"Deep Reading request {request_id} owns a unique paper",
            f"Duplicate Deep Reading request for the same paper: {request_id} and {paper_requests.get(paper_identity)}",
        )
        paper_requests[paper_identity] = request_id
        if status != "imported":
            report.check(
                not imported_ids,
                f"Non-imported request {request_id} has no imported evidence",
                f"Request {request_id} is {status} but lists Imported Evidence IDs",
            )
        report.check(
            bool(V2_ID_TYPE_PATTERNS["deep_read_request"].fullmatch(request_id)),
            f"Deep Reading request uses valid ID {request_id}",
            f"Deep Reading request has invalid ID {request_id!r}",
        )
        report.check(
            priority in allowed_priorities,
            f"Deep Reading request {request_id} uses a valid priority",
            f"Deep Reading request {request_id} has invalid priority {row[priority_col]!r}",
        )
        report.check(
            status in allowed_statuses,
            f"Deep Reading request {request_id} uses a valid status",
            f"Deep Reading request {request_id} has invalid status {row[status_col]!r}",
        )
        report.check(
            bool(targets) and _meaningful(row[paper_col]) and _meaningful(row[question_col]),
            f"Deep Reading request {request_id} is decision-linked",
            f"Deep Reading request {request_id} requires a paper key, Claim/Route target, "
            "and decision-changing question",
        )
        if status == "imported":
            _, refs_valid = _canonical_deep_read_refs(row[refs_col])
            report.check(
                _meaningful(row[run_col])
                and row[run_col].strip().lower() not in {"none", "not applicable"}
                and refs_valid,
                f"Imported request {request_id} records its run and canonical refs",
                f"Imported request {request_id} requires a Deep Reading run and only "
                "canonical artifact refs",
            )
            report.check(
                bool(imported_ids) and imported_ids <= evidence_rows.keys(),
                f"Imported request {request_id} resolves to evidence rows",
                f"Imported request {request_id} has missing or unknown Imported Evidence IDs",
            )
            for evidence_id in imported_ids & evidence_rows.keys():
                import_owners[evidence_id].append(request_id)
                report.check(
                    evidence_rows[evidence_id][depth_col].strip().lower()
                    == "canonical-deep-read",
                    f"Imported evidence {evidence_id} records canonical-deep-read depth",
                    f"Imported evidence {evidence_id} must use verification_depth "
                    "canonical-deep-read",
                )
            try:
                canonical_links.check_import(
                    row[run_col], row[refs_col],
                    [(evidence_rows[eid][source_col], evidence_rows[eid][evidence_ref_col])
                     for eid in sorted(imported_ids & evidence_rows.keys())],
                    base=workspace_root or documents["evidence_matrix"].path.parent,
                    paper_key=row[paper_col], cache=canonical_cache,
                )
            except (OSError, ValueError, KeyError, ImportError) as exc:
                report.errors.append(f"Imported request {request_id}: {exc}")
        if status in {"blocked", "skipped"}:
            report.check(
                _meaningful(row[decision_col]),
                f"Deep Reading request {request_id} records its blocker/disposition",
                f"Deep Reading request {request_id} must explain its blocker/disposition",
            )
    for evidence_id, evidence_row in evidence_rows.items():
        if evidence_row[depth_col].strip().lower() == "canonical-deep-read":
            report.check(
                len(import_owners[evidence_id]) == 1,
                f"Canonical evidence {evidence_id} has exactly one imported handoff owner",
                f"Canonical evidence {evidence_id} must be linked by exactly one imported handoff; found {import_owners[evidence_id]}",
            )


def _validate_coverage_and_tensions(
    report: Report,
    documents: Mapping[str, V2Document],
) -> None:
    queries = _table_from_role(documents, "search_log", "search-queries")
    coverage = _table_from_role(documents, "search_log", "coverage-audit")
    tensions = _table_from_role(documents, "evidence_matrix", "contradictions")
    evidence = _table_from_role(documents, "evidence_matrix", "evidence-records")
    if queries is None or coverage is None or tensions is None or evidence is None:
        return
    try:
        query_id_col = _column(queries, "Query ID")
        query_lane_col = _column(queries, "Search lane")
        query_results_col = _column(queries, "Results")
        selected_evidence_col = _column(queries, "Evidence IDs")
        lane_col = _column(coverage, "Lane")
        coverage_queries_col = _column(coverage, "Query IDs")
        coverage_evidence_col = _column(coverage, "Relevant Evidence IDs")
        coverage_status_col = _column(
            coverage,
            "Coverage status: covered/thin/query-failed/out-of-scope",
        )
        blind_col = _column(coverage, "Blind spot or failure mode")
        next_col = _column(coverage, "Next query or stop rationale")
        tension_support_col = _column(tensions, "Supporting Evidence IDs")
        tension_limit_col = _column(tensions, "Contradicting/limiting Evidence IDs")
        condition_col = _column(tensions, "Condition delta")
        tension_type_col = _column(tensions, "Tension type: direct-conflict/evidence-gap/condition-difference")
        tension_claim_col = _column(tensions, "Claim ID")
        resolution_col = _column(tensions, "Resolution action")
        adjudication_col = _column(
            tensions,
            "Adjudication: support-dominant/limit-dominant/condition-split/unresolved",
        )
        evidence_id_col = _column(evidence, "Evidence ID")
        evidence_claim_col = _column(evidence, "Claim IDs")
        evidence_stance_col = _column(evidence, "Stance")
        evidence_direct_col = _column(evidence, "Directness")
    except ContractError as exc:
        report.errors.append(str(exc))
        return

    query_rows = {row[query_id_col].strip(): row for row in queries.rows}
    evidence_ids = {row[evidence_id_col].strip() for row in evidence.rows}
    evidence_rows = {row[evidence_id_col].strip(): row for row in evidence.rows}
    lane_counts: dict[str, int] = defaultdict(int)
    allowed_statuses = {"covered", "thin", "query-failed", "out-of-scope"}
    for row in coverage.rows:
        lane = row[lane_col].strip().lower()
        status = row[coverage_status_col].strip().lower()
        lane_counts[lane] += 1
        query_ids = set(
            _cell_ids(row[coverage_queries_col], V2_ID_TYPE_PATTERNS["query"])
        )
        row_evidence_ids = set(
            _cell_ids(row[coverage_evidence_col], V2_ID_TYPE_PATTERNS["evidence"])
        )
        report.check(
            status in allowed_statuses,
            f"Coverage lane {lane} uses a valid status",
            f"Coverage lane {lane} has invalid status {row[coverage_status_col]!r}",
        )
        if status == "out-of-scope":
            report.check(
                _scope_rationale(row[blind_col]) and _scope_rationale(row[next_col]),
                f"Out-of-scope lane {lane} has an explicit boundary",
                f"Out-of-scope lane {lane} requires a boundary and stop rationale",
            )
        else:
            report.check(
                bool(query_ids)
                and query_ids <= query_rows.keys()
                and all(
                    query_rows[query_id][query_lane_col].strip().lower() == lane
                    for query_id in query_ids
                ),
                f"Coverage lane {lane} resolves to a same-lane query",
                f"Coverage lane {lane} must reference an existing query with the same lane",
            )
        report.check(
            row_evidence_ids <= evidence_ids,
            f"Coverage lane {lane} Evidence IDs resolve",
            f"Coverage lane {lane} references unknown Evidence IDs",
        )
        selected_ids = {
            evidence_id
            for query_id in query_ids if query_id in query_rows
            for evidence_id in _cell_ids(query_rows[query_id][selected_evidence_col], V2_ID_TYPE_PATTERNS["evidence"])
        }
        report.check(
            row_evidence_ids <= selected_ids,
            f"Coverage lane {lane} evidence was selected by its cited queries",
            f"Coverage lane {lane} cites evidence not selected by its Query IDs",
        )
        if status == "covered":
            responsive = any(
                query_id in query_rows
                and query_rows[query_id][query_lane_col].strip().lower() == lane
                and bool(re.fullmatch(r"[1-9]\d*", query_rows[query_id][query_results_col].strip()))
                for query_id in query_ids
            )
            report.check(
                bool(row_evidence_ids) and responsive,
                f"Covered lane {lane} has responsive evidence",
                f"Coverage lane {lane} cannot be covered without a positive same-lane "
                "query and relevant evidence",
            )
    report.check(
        set(lane_counts) == set(SIX_SEARCH_LANES)
        and all(lane_counts[lane] == 1 for lane in SIX_SEARCH_LANES),
        "Coverage audit contains each of the six search lanes exactly once",
        "Coverage audit must contain exactly one row for each lane: "
        + ", ".join(SIX_SEARCH_LANES),
    )

    allowed_adjudications = {
        "support-dominant",
        "limit-dominant",
        "condition-split",
        "unresolved",
    }
    for row in tensions.rows:
        support_ids = set(
            _cell_ids(row[tension_support_col], V2_ID_TYPE_PATTERNS["evidence"])
        )
        limit_ids = set(
            _cell_ids(row[tension_limit_col], V2_ID_TYPE_PATTERNS["evidence"])
        )
        adjudication = row[adjudication_col].strip().lower()
        tension_type = row[tension_type_col].strip().lower()
        claim_id = row[tension_claim_col].strip()
        report.check(
            tension_type in {"direct-conflict", "evidence-gap", "condition-difference"},
            f"Tension for {claim_id} has an explicit type",
            f"Tension for {claim_id} has an invalid or missing Tension type",
        )
        for identifiers, stances in ((support_ids, {"supports", "mixed"}), (limit_ids, {"limits", "contradicts", "mixed"})):
            report.check(
                all(eid in evidence_rows and claim_id in _cell_ids(evidence_rows[eid][evidence_claim_col])
                    and evidence_rows[eid][evidence_stance_col].strip().lower() in stances
                    for eid in identifiers),
                f"Tension for {claim_id} preserves evidence-to-claim stance",
                f"Tension for {claim_id} has an unbound source or incompatible stance",
            )
        if tension_type == "direct-conflict":
            report.check(
                bool(support_ids) and bool(limit_ids)
                and any(eid in evidence_rows and evidence_rows[eid][evidence_direct_col].lower() == "direct"
                        for eid in support_ids)
                and any(eid in evidence_rows and evidence_rows[eid][evidence_direct_col].lower() == "direct"
                        and evidence_rows[eid][evidence_stance_col].lower() == "contradicts" for eid in limit_ids),
                f"Direct conflict for {claim_id} has both direct sides",
                f"Direct conflict for {claim_id} requires direct support and direct contradicting evidence; a limitation or missing comparison is not a conflict",
            )
        report.check(
            row[resolution_col].strip().lower() not in {"none", "not applicable", "unknown"},
            f"Tension for {claim_id} has a decision-changing resolution",
            f"Tension for {claim_id} requires a substantive resolution action",
        )
        report.check(
            adjudication in allowed_adjudications,
            "Evidence tension uses a condition-aware adjudication",
            f"Evidence tension has invalid adjudication {row[adjudication_col]!r}",
        )
        report.check(
            _meaningful(row[condition_col]),
            "Evidence tension states the condition delta",
            "Every evidence tension must state the regime, method, population, "
            "or boundary condition that changes interpretation",
        )
        report.check(
            (support_ids | limit_ids) <= evidence_ids,
            "Evidence tension references known evidence",
            "Evidence tension references unknown supporting or limiting evidence",
        )


def _route_ids_for_mode(
    documents: Mapping[str, V2Document],
    *,
    mode: str,
) -> set[str]:
    marker = "candidate-routes" if mode == "landscape" else "focus-routes"
    routes = _table_from_documents(documents, marker)
    if routes is None:
        return set()
    try:
        candidate_col = _column(routes, "Candidate ID")
    except ContractError:
        return set()
    return {
        row[candidate_col].strip()
        for row in routes.rows
        if V2_ID_TYPE_PATTERNS["candidate"].fullmatch(row[candidate_col].strip())
    }


def _validate_opportunity_gates(
    report: Report,
    documents: Mapping[str, V2Document],
    *,
    mode: str,
) -> None:
    gates = _table_from_documents(documents, "opportunity-gates")
    evidence = _table_from_documents(documents, "evidence-records")
    if gates is None or evidence is None:
        return
    try:
        candidate_col = _column(gates, "Candidate ID")
        openness_col = _column(
            gates, "Openness gate: pass/conditional/fail/unknown"
        )
        contribution_col = _column(
            gates, "Contribution gate: pass/conditional/fail/unknown"
        )
        feasibility_col = _column(
            gates, "Feasibility gate: pass/conditional/fail/unknown"
        )
        overall_col = _column(
            gates, "Overall: go/conditional-go/defer/no-go"
        )
        recall_col = _column(gates, "Recall caveat")
        gate_evidence_col = _column(gates, "Gate Evidence IDs")
        next_col = _column(gates, "Binding condition or next check")
        evidence_id_col = _column(evidence, "Evidence ID")
    except ContractError as exc:
        report.errors.append(str(exc))
        return
    route_ids = _route_ids_for_mode(documents, mode=mode)
    evidence_ids = {row[evidence_id_col].strip() for row in evidence.rows}
    counts: dict[str, int] = defaultdict(int)
    allowed_gates = {"pass", "conditional", "fail", "unknown"}
    overall_by_candidate: dict[str, str] = {}
    for row in gates.rows:
        candidate_id = row[candidate_col].strip()
        counts[candidate_id] += 1
        values = [
            row[openness_col].strip().lower(),
            row[contribution_col].strip().lower(),
            row[feasibility_col].strip().lower(),
        ]
        overall = row[overall_col].strip().lower()
        expected_overall = (
            "no-go"
            if "fail" in values
            else "defer"
            if "unknown" in values
            else "conditional-go"
            if "conditional" in values
            else "go"
        )
        overall_by_candidate[candidate_id] = overall
        report.check(
            all(value in allowed_gates for value in values),
            f"Opportunity {candidate_id} uses valid three-gate values",
            f"Opportunity {candidate_id} must use pass/conditional/fail/unknown "
            "for openness, contribution, and feasibility",
        )
        report.check(
            overall == expected_overall,
            f"Opportunity {candidate_id} overall is deterministic",
            f"Opportunity {candidate_id} Overall must be {expected_overall!r} "
            f"from its three gates, got {overall!r}",
        )
        recall = row[recall_col]
        report.check(
            bool(RECALL_BOUNDARY_PATTERN.search(recall))
            and not UNBOUNDED_PRIORITY.search(recall),
            f"Opportunity {candidate_id} carries a bounded recall caveat",
            f"Opportunity {candidate_id} Recall caveat must state bounded search "
            "coverage and must not turn a miss into an absence/priority claim",
        )
        gate_evidence_ids = set(
            _cell_ids(row[gate_evidence_col], V2_ID_TYPE_PATTERNS["evidence"])
        )
        report.check(
            bool(gate_evidence_ids) and gate_evidence_ids <= evidence_ids,
            f"Opportunity {candidate_id} gate evidence resolves",
            f"Opportunity {candidate_id} requires one or more known Gate Evidence IDs",
        )
        report.check(
            _meaningful(row[next_col]),
            f"Opportunity {candidate_id} records its binding condition",
            f"Opportunity {candidate_id} requires a binding condition or next check",
        )
    report.check(
        set(counts) == route_ids
        and all(counts[candidate_id] == 1 for candidate_id in route_ids),
        f"{mode.title()} opportunities have exactly one gate row per route",
        f"Opportunity-gates must contain exactly the authoritative {mode} route set",
    )
    deferred = {candidate for candidate, overall in overall_by_candidate.items() if overall == "defer"}
    if deferred:
        actions = _table_from_role(documents, "decision_log", "next-actions")
        if actions is not None:
            try:
                action_col = _column(actions, "Action")
                dependency_col = _column(actions, "Dependency")
                deliverable_col = _column(actions, "Deliverable")
                enabled_col = _column(actions, "Decision enabled")
                for candidate in deferred:
                    report.check(
                        any(candidate in _cell_ids(row[enabled_col])
                            and re.search(r"openness|contribution|feasibility|开放|贡献|可行", row[enabled_col], re.I)
                            and all(_meaningful(row[c]) and row[c].strip().lower() not in {"none", "unknown", "not applicable"}
                                    for c in (action_col, dependency_col, deliverable_col))
                            for row in actions.rows),
                        f"Deferred route {candidate} has a handoff-ready gate-changing check",
                        f"Deferred route {candidate} needs a next-actions row with exact inputs, deliverable and named gate change",
                    )
            except ContractError as exc:
                report.errors.append(str(exc))


def _validate_route_fast_pilots(
    report: Report,
    documents: Mapping[str, V2Document],
    *,
    mode: str,
) -> None:
    pilots = _table_from_documents(documents, "route-fast-pilots")
    gates = _table_from_documents(documents, "opportunity-gates")
    if pilots is None or gates is None:
        return
    try:
        candidate_col = _column(pilots, "Candidate ID")
        rank_col = _column(pilots, "Rank: 1-3")
        hypothesis_a_col = _column(pilots, "Hypothesis A")
        hypothesis_b_col = _column(pilots, "Hypothesis B")
        test_col = _column(pilots, "Discriminating test")
        observable_col = _column(pilots, "Observable")
        horizon_col = _column(pilots, "Horizon days: 1-14")
        resource_col = _column(pilots, "Resource cap")
        advance_col = _column(pilots, "Advance threshold")
        kill_col = _column(pilots, "Kill or revise threshold")
        gate_candidate_col = _column(gates, "Candidate ID")
        gate_overall_col = _column(
            gates, "Overall: go/conditional-go/defer/no-go"
        )
    except ContractError as exc:
        report.errors.append(str(exc))
        return
    route_ids = _route_ids_for_mode(documents, mode=mode)
    gate_overall = {
        row[gate_candidate_col].strip(): row[gate_overall_col].strip().lower()
        for row in gates.rows
    }
    seen_candidates: set[str] = set()
    ranks: list[int] = []
    report.check(
        (1 <= len(pilots.rows) <= 3) if any(
            value in {"go", "conditional-go"} for value in gate_overall.values()
        ) else not pilots.rows,
        "Fast-pilot count agrees with the gate-eligible route set",
        "route-fast-pilots must be empty with zero eligible routes; otherwise select one to three rows",
    )
    for row in pilots.rows:
        candidate_id = row[candidate_col].strip()
        try:
            rank = int(row[rank_col].strip())
        except ValueError:
            rank = 0
        try:
            horizon = int(row[horizon_col].strip())
        except ValueError:
            horizon = 0
        ranks.append(rank)
        report.check(
            candidate_id in route_ids and candidate_id not in seen_candidates,
            f"Fast pilot owns one authoritative route {candidate_id}",
            f"Fast pilot candidate {candidate_id!r} must be authoritative and unique",
        )
        seen_candidates.add(candidate_id)
        report.check(
            gate_overall.get(candidate_id) in {"go", "conditional-go"},
            f"Fast pilot {candidate_id} passed or conditionally passed the three gates",
            f"Fast pilot {candidate_id} cannot be selected while Overall is "
            f"{gate_overall.get(candidate_id)!r}",
        )
        hypothesis_a = re.sub(
            r"\W+", " ", row[hypothesis_a_col].casefold(), flags=re.UNICODE
        ).strip()
        hypothesis_b = re.sub(
            r"\W+", " ", row[hypothesis_b_col].casefold(), flags=re.UNICODE
        ).strip()
        report.check(
            _meaningful(row[hypothesis_a_col])
            and _meaningful(row[hypothesis_b_col])
            and hypothesis_a != hypothesis_b,
            f"Fast pilot {candidate_id} compares distinct hypotheses",
            f"Fast pilot {candidate_id} requires two substantive, distinct hypotheses",
        )
        report.check(
            1 <= horizon <= 14,
            f"Fast pilot {candidate_id} is bounded to {horizon} day(s)",
            f"Fast pilot {candidate_id} Horizon days must be an integer from 1 to 14",
        )
        report.check(
            all(
                _meaningful(row[index]) and row[index].strip().lower() not in {"none", "unknown", "n/a", "not applicable"}
                for index in (
                    test_col,
                    observable_col,
                    resource_col,
                    advance_col,
                    kill_col,
                )
            ),
            f"Fast pilot {candidate_id} is discriminating and resource-bounded",
            f"Fast pilot {candidate_id} requires test, observable, resource cap, "
            "advance threshold, and kill/revise threshold",
        )
    report.check(
        sorted(ranks) == list(range(1, len(pilots.rows) + 1)),
        "Fast-pilot ranks are contiguous from one",
        "Fast-pilot ranks must be unique and contiguous from 1",
    )


def validate_v2(
    run_dir: Path,
    manifest: Mapping[str, object],
    *,
    workspace_root: Path | None,
) -> Report:
    report = Report()
    report.check(run_dir.is_dir(), "Run directory exists", f"Run directory not found: {run_dir}")
    report.check(manifest.get("skill") == SKILL_ID, "Manifest identifies the skill", "Manifest has an unexpected skill identifier")

    run_type = manifest.get("run_type")
    task_mode = manifest.get("task_mode")
    lens = manifest.get("discovery_lens")
    routing = manifest.get("routing")
    selected = routing.get("selected") if isinstance(routing, dict) else None
    report.check(
        run_type in RUN_TYPES,
        f"Manifest run_type is {run_type}",
        f"Invalid or missing run_type: {run_type!r}",
    )
    report.check(
        task_mode == run_type == selected,
        "Manifest task_mode, run_type, and routing.selected agree",
        "Schema 2.0 requires task_mode == run_type == routing.selected",
    )
    report.check(
        selected != "auto",
        "Persisted selected mode is concrete",
        "auto cannot be persisted as run_type/routing.selected",
    )
    report.check(
        lens in DISCOVERY_LENSES,
        f"Manifest discovery_lens is {lens}",
        f"Invalid or missing discovery_lens: {lens!r}",
    )
    if run_type not in RUN_TYPES or lens not in DISCOVERY_LENSES:
        return report
    assert isinstance(run_type, str) and isinstance(lens, str)
    _validate_v2_manifest_metadata(report, manifest, mode=run_type)
    active_workflow_contracts = _active_workflow_contracts(
        report, manifest, mode=run_type
    )
    report.check(
        manifest.get("artifact_profile") == artifact_profile(run_type),
        "Manifest artifact_profile matches run type",
        f"artifact_profile must be {artifact_profile(run_type)}",
    )
    status = manifest.get("completion_status")
    allowed_statuses = set(COMPLETION_STATUSES)
    report.check(
        status in allowed_statuses,
        f"Manifest completion status is {status}",
        f"Invalid completion_status: {status!r}",
    )
    report.check(
        status == "complete",
        "Run declares completion_status=complete",
        f"Run is not ready for delivery: completion_status={status!r}",
        warning=True,
    )
    _validate_frontier_policy(report, manifest)

    roles = manifest.get("artifact_roles")
    files = manifest.get("artifact_files")
    report.check(isinstance(roles, dict), "Manifest artifact_roles is an object", "artifact_roles must be an object")
    report.check(isinstance(files, list), "Manifest artifact_files is a list", "artifact_files must be a list")
    if not isinstance(roles, dict) or not isinstance(files, list):
        return report
    expected_roles = set(MODE_ROLES[run_type].values()) | {"reader_report"}
    actual_roles = set(roles)
    optional_roles = {"migration_report"}
    report.check(
        expected_roles <= actual_roles and actual_roles <= expected_roles | optional_roles,
        "Manifest artifact roles match the mode profile",
        f"Artifact-role mismatch; expected {sorted(expected_roles)}, got {sorted(actual_roles)}",
    )
    report.check(
        len(files) == len(set(item for item in files if isinstance(item, str)))
        and all(isinstance(item, str) for item in files),
        "Manifest artifact_files are unique strings",
        "artifact_files must contain unique string paths",
    )

    safe_files: set[str] = set()
    safe_file_paths: dict[str, Path] = {}
    for raw_name in files:
        try:
            rel = safe_manifest_relpath(raw_name, label="artifact path")
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        safe_files.add(rel.as_posix())
        try:
            path = resolve_contained_file(run_dir, rel, label="declared artifact")
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        safe_file_paths[rel.as_posix()] = path
        report.passed.append(f"Declared artifact exists inside run: {rel.as_posix()}")
    role_paths: dict[str, Path] = {}
    for role, raw_name in roles.items():
        try:
            rel = safe_manifest_relpath(raw_name, label=f"artifact role {role}")
        except ContractError as exc:
            report.errors.append(str(exc))
            continue
        report.check(rel.as_posix() in safe_files, f"Artifact role {role} is declared", f"Artifact role {role} points to an undeclared file")
        path = safe_file_paths.get(rel.as_posix())
        report.check(
            path is not None,
            f"Artifact role {role} resolves to a contained file",
            f"Artifact role {role} points to a missing or unsafe file",
        )
        if path is not None:
            role_paths[role] = path
    report.check(
        len({str(path) for path in role_paths.values()}) == len(role_paths),
        "Artifact roles map to unique files",
        "Two artifact roles map to the same file",
    )
    report.check(
        manifest.get("primary_artifact") == roles.get("reader_report"),
        "Primary artifact is the reader report",
        "primary_artifact must equal artifact_roles.reader_report",
    )

    documents: dict[str, V2Document] = {}
    for role, path in role_paths.items():
        if role == "migration_report" or path.suffix.lower() != ".md" or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            report.errors.append(f"Cannot read {path}: {exc}")
            continue
        document = V2Document.parse(path, text)
        documents[role] = document
        placeholders = V2_PLACEHOLDER.findall(document.visible_text())
        report.check(
            not placeholders,
            f"{path.name}: no visible placeholders",
            f"{path.name}: unresolved visible placeholders: {len(placeholders)}",
        )
        marker_contract = (
            ROLE_MARKERS.get(role, ())
            + MODE_ROLE_MARKERS.get((run_type, role), ())
            + tuple(
                marker
                for contract_name in WORKFLOW_CONTRACTS_BY_MODE[run_type]
                if contract_name in active_workflow_contracts
                for marker in WORKFLOW_ROLE_MARKERS.get(contract_name, {}).get(
                    role, ()
                )
            )
        )
        _validate_document_contract(report, document, marker_contract)


    marker_owner_roles: dict[str, set[str]] = defaultdict(set)
    for owner_role, markers in ROLE_MARKERS.items():
        for _, marker_name in markers:
            marker_owner_roles[marker_name].add(owner_role)
    for (_, owner_role), markers in MODE_ROLE_MARKERS.items():
        for _, marker_name in markers:
            marker_owner_roles[marker_name].add(owner_role)
    for role_markers in WORKFLOW_ROLE_MARKERS.values():
        for owner_role, markers in role_markers.items():
            for _, marker_name in markers:
                marker_owner_roles[marker_name].add(owner_role)
    for role, document in documents.items():
        if role in {"reader_report", "migration_report"}:
            continue
        report.check(
            not document.projections and not document.route_blocks,
            "Reader-only presentation markers stay in the reader artifact",
            f"{role}: rom-projection/rom-route cannot define working artifacts",
        )
        for marker_name in document.blocks:
            allowed_roles = marker_owner_roles.get(marker_name)
            if not allowed_roles:
                continue
            report.check(
                role in allowed_roles,
                f"Registered marker {marker_name!r} appears in an owning artifact role",
                f"Registered marker {marker_name!r} appears in wrong artifact role "
                f"{role!r}; allowed roles are {sorted(allowed_roles)!r}",
            )
    reader = documents.get("reader_report")
    report.check(reader is not None, "Reader report was parsed", "Reader report is missing or unreadable")
    if reader is None:
        return report
    _validate_document_contract(
        report,
        reader,
        (("section", name) for name in _reader_markers(reader, run_type)),
        header_registry=None,
    )
    _validate_reader_contract(report, reader, mode=run_type)

    try:
        root = _discover_workspace_root(run_dir, workspace_root)
    except ContractError as exc:
        report.errors.append(str(exc))
        return report
    external_ids = _validate_v2_lineage_and_context(
        report, manifest, run_dir=run_dir, workspace_root=root, mode=run_type
    )
    parent_audit_facts = None
    if run_type == "run-audit":
        parent_audit_facts = _load_parent_audit_facts(
            report, manifest, workspace_root=root
        )
        if parent_audit_facts is not None:
            # A run-audit may name a dangling parent identifier in order to
            # report it.  That observation is not an inherited claim.
            external_ids.update(parent_audit_facts.observed_ids)
    _validate_selected_branch(
        report, manifest, mode=run_type, external_ids=external_ids
    )
    local_ids = _validate_id_closure(report, documents, external_ids=external_ids)
    _validate_reader_citations(report, documents, reader, mode=run_type)
    if run_type != "run-audit":
        _validate_evidence_confidence(report, documents)
    if "deep-reading-handoff-v2" in active_workflow_contracts:
        _validate_deep_reading_handoff(report, documents, workspace_root=workspace_root)
    if "coverage-tension-v2" in active_workflow_contracts:
        _validate_coverage_and_tensions(report, documents)
    if "opportunity-gates-v2" in active_workflow_contracts:
        _validate_opportunity_gates(report, documents, mode=run_type)
    if "route-fast-pilot-v2" in active_workflow_contracts:
        _validate_route_fast_pilots(report, documents, mode=run_type)
    integrity_bindings: tuple[DispositionBinding, ...] = ()
    if run_type == "landscape":
        _validate_landscape(report, documents, reader)
    elif run_type == "focus":
        _validate_focus(report, documents, reader)
    elif run_type == "evidence-audit":
        _validate_evidence_audit(report, documents, reader)
    elif run_type == "run-audit":
        integrity_bindings = _validate_run_audit(
            report, documents, reader, parent_audit_facts
        )
    _validate_lens(report, documents, mode=run_type, lens=lens)
    authoritative_major_targets: set[str] | None = None
    if run_type == "evidence-audit":
        inherited = manifest.get("inherited_ids", {})
        inherited_claims = (
            inherited.get("claims", []) if isinstance(inherited, dict) else []
        )
        authoritative_major_targets = {
            identifier
            for identifier in local_ids
            if V2_ID_TYPE_PATTERNS["claim"].fullmatch(identifier)
        }
        if isinstance(inherited_claims, list):
            authoritative_major_targets.update(
                identifier
                for identifier in inherited_claims
                if isinstance(identifier, str)
                and V2_ID_TYPE_PATTERNS["claim"].fullmatch(identifier)
            )
        target_claims = _table_from_documents(documents, "target-claims")
        if target_claims is not None:
            try:
                target_claim_col = _column(target_claims, "Claim ID")
            except ContractError:
                authoritative_major_targets = set()
            else:
                authoritative_major_targets &= {
                    row[target_claim_col].strip()
                    for row in target_claims.rows
                }
    elif run_type == "run-audit":
        authoritative_major_targets = (
            {
                row[0]
                for row in parent_audit_facts.id_projection
                if len(row) >= 2
                and row[1] in {"claim", "candidate"}
                and RUN_AUDIT_TARGET_PATTERN.fullmatch(row[0])
            }
            if parent_audit_facts is not None
            else set()
        )
    _validate_attack_propagation(
        report,
        documents,
        reader,
        mode=run_type,
        valid_ids=local_ids | external_ids,
        authoritative_major_targets=authoritative_major_targets,
        additional_bindings=integrity_bindings,
    )
    _validate_bio_translation(report, documents, reader, manifest)

    all_visible = "\n".join(document.visible_text() for document in documents.values())
    priority_claims = _unbounded_priority_assertions(all_visible)
    report.check(
        not priority_claims,
        "No unbounded absence/priority claims appear in visible content",
        f"Detected {len(priority_claims)} unbounded absence/priority claim(s)",
    )
    return report


def validate(run_dir: Path, *, workspace_root: Path | None = None) -> Report:
    if not run_dir.is_dir():
        report = Report()
        report.errors.append(f"Run directory not found: {run_dir}")
        return report
    try:
        manifest_path = resolve_contained_file(
            run_dir, Path("run-manifest.json"), label="run manifest"
        )
    except ContractError as exc:
        report = Report()
        report.errors.append(f"Missing or unsafe run-manifest.json: {exc}")
        return report
    try:
        manifest = load_json_object(manifest_path, label="run manifest")
        version = parse_schema_version(manifest.get("schema_version"))
    except ContractError as exc:
        report = Report()
        report.errors.append(str(exc))
        return report
    version_text = str(version)
    if version_text not in SUPPORTED_SCHEMA_VERSIONS:
        report = Report()
        report.errors.append(
            f"Unsupported schema_version {version_text}; supported versions are 1.0, 1.1, 1.2, and 2.0"
        )
        return report
    if version_text in {"1.0", "1.1", "1.2"}:
        return validate_v1_legacy(run_dir)
    return validate_v2(run_dir, manifest, workspace_root=workspace_root)


def emit(report: Report, *, as_json: bool) -> None:
    payload = {
        "errors": report.errors,
        "warnings": report.warnings,
        "passed": report.passed,
        "summary": {
            "errors": len(report.errors),
            "warnings": len(report.warnings),
            "passed": len(report.passed),
        },
    }
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(
        f"Validation: {len(report.errors)} error(s), "
        f"{len(report.warnings)} warning(s), {len(report.passed)} passed check(s)"
    )
    for label, items in (("ERROR", report.errors), ("WARN", report.warnings)):
        for item in items:
            print(f"[{label}] {item}")


def main() -> int:
    args = parse_args()
    canonical_links.CHECKER_PATH = args.canonical_checker
    report = validate(
        args.run_directory.expanduser().resolve(),
        workspace_root=args.workspace_root,
    )
    emit(report, as_json=args.json)
    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
