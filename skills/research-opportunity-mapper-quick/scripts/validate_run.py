#!/usr/bin/env python3
"""Validate completeness and traceability of a research opportunity mapping run."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


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

SUPPORTED_SKILL_IDS = {
    "research-opportunity-mapper-quick",
    "simple-ro-mapper",
    "research-opportunity-mapper",
}

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


def validate(run_dir: Path) -> Report:
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
                manifest.get("skill") in SUPPORTED_SKILL_IDS,
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
        reader_report_path = run_dir / declared_reports[0]
        report.check(
            reader_report_path.is_file(),
            f"Human-facing report exists: {declared_reports[0]}",
            f"Manifest-declared human-facing report is missing: {declared_reports[0]}",
        )
        if reader_report_path.is_file():
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
        path = run_dir / filename
        if not path.is_file():
            report.errors.append(f"Missing required artifact: {filename}")
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
    report = validate(args.run_directory.expanduser().resolve())
    emit(report, as_json=args.json)
    if report.errors or (args.strict and report.warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
