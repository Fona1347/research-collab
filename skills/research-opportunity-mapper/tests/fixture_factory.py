from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Iterable, Sequence

from parent_audit import ParentAuditFacts, canonical_manifest_repair, inspect_parent_for_audit
from rom_contract import WORKFLOW_CONTRACTS_BY_MODE, SKILL_VERSION, VALIDATOR_VERSION


SKILL_DIR = Path(__file__).resolve().parents[1]
WORK_ROOT = Path(os.environ.get("ROM_TEST_ROOT", str(SKILL_DIR / "tests" / ".work")))


ROLE_FILES = {
    "landscape": {
        "intake": "00_intake.md",
        "breadth_ledger": "01_breadth-ledger.md",
        "search_log": "02_search-log.md",
        "evidence_matrix": "03_evidence-matrix.md",
        "research_map": "04_research-map.md",
        "candidate_portfolio": "05_candidate-portfolio.md",
        "red_team": "06_red-team.md",
        "decision_log": "07_decision-log.md",
    },
    "focus": {
        "intake": "00_intake.md",
        "focus_scope": "01_focus-scope.md",
        "search_log": "02_search-log.md",
        "evidence_matrix": "03_evidence-matrix.md",
        "claim_mechanism_map": "04_claim-mechanism-map.md",
        "route_protocol": "05_route-protocol.md",
        "red_team": "06_red-team.md",
        "decision_log": "07_decision-log.md",
    },
    "evidence-audit": {
        "audit_scope": "00_audit-scope.md",
        "claim_register": "01_claim-register.md",
        "search_log": "02_search-log.md",
        "evidence_matrix": "03_evidence-matrix.md",
        "confidence_assessment": "04_confidence-assessment.md",
        "gap_plan": "05_gap-plan.md",
        "red_team": "06_red-team.md",
        "decision_log": "07_decision-log.md",
    },
    "run-audit": {
        "audit_scope": "00_audit-scope.md",
        "artifact_inventory": "01_artifact-inventory.md",
        "traceability_audit": "02_traceability-audit.md",
        "evidence_audit": "03_evidence-audit.md",
        "reasoning_audit": "04_reasoning-audit.md",
        "route_verdicts": "05_route-verdicts.md",
        "red_team": "06_red-team.md",
        "decision_log": "07_decision-log.md",
    },
}


REPORT_PREFIX = {
    "landscape": "map_report",
    "focus": "focus_report",
    "evidence-audit": "evidence_audit_report",
    "run-audit": "run_audit_report",
}


def workspace_root() -> Path:
    if os.environ.get("ROM_TEST_WORKSPACE"):
        return Path(os.environ["ROM_TEST_WORKSPACE"]).resolve()
    raise AssertionError("Set ROM_TEST_WORKSPACE explicitly or use scripts/validate.py")


def reset_work(name: str) -> Path:
    WORK_ROOT.mkdir(parents=True, exist_ok=True)
    root = (WORK_ROOT / name).resolve()
    if root.parent != WORK_ROOT.resolve():
        raise AssertionError(f"unsafe test work path: {root}")
    if root.exists():
        shutil.rmtree(root)
    root.mkdir()
    return root


def cleanup_work(name: str) -> None:
    root = (WORK_ROOT / name).resolve()
    if root.parent != WORK_ROOT.resolve():
        raise AssertionError(f"unsafe test cleanup path: {root}")
    if root.exists():
        shutil.rmtree(root)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def marker_section(name: str, title: str, body: str) -> str:
    return f"<!-- rom-section: {name} -->\n## {title}\n{body.strip()}\n"


def marker_table(
    name: str,
    title: str,
    headers: Sequence[str],
    rows: Iterable[Sequence[str]],
    *,
    kind: str = "table",
) -> str:
    lines = [
        f"<!-- rom-{kind}: {name} -->",
        f"## {title}",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def _intake(
    mode: str,
    *,
    scenario_summary: str | None = None,
    capability_state: str = "Observed",
) -> str:
    scenario = scenario_summary or "bounded physical research opportunity"
    readiness = "Unavailable" if capability_state == "Unknown" else "Adaptable"
    capability_source = (
        "not yet verified" if capability_state == "Unknown" else "documented or reported workflow"
    )
    return "\n".join(
        [
            "# Intake",
            marker_section("decision", "Decision", f"Select a falsifiable route within a bounded regime and a three-month decision horizon. Scenario boundary: {scenario}"),
            marker_table(
                "problem-adequacy",
                "Problem Sufficiency, Necessity, and Timing",
                ["Dimension", "Bounded statement", "Evidence or observation", "Counterargument", "Decision implication"],
                [["Sufficiency", "The bottleneck recurs in the target regime", "E-001", "A stronger conventional control may close it", "Test before scaling"]],
                kind="section",
            ),
            marker_table(
                "capability-passport",
                "Capability Passport",
                ["Capability ID", "Capability module", "Epistemic state: Observed/Reported/Assumed/Unknown", "Readiness: Ready/Adaptable/Collaborator/Unavailable", "Source or evidence", "Lead time/dependency"],
                [["CAP-001", "multiphysics modeling, fabrication, and measurement", capability_state, readiness, capability_source, "dependency must be confirmed before commitment"]],
                kind="section",
            ),
            marker_table(
                "constraints",
                "Constraints",
                ["Constraint", "Value/regime", "Hard or soft", "Consequence"],
                [["first-data window", "three months", "hard", "prioritize discriminating proxy test"]],
                kind="section",
            ),
            marker_table(
                "scale-boundary",
                "Scale and Evidence Boundaries",
                ["Starting evidence level", "Highest currently justified conclusion", "Forbidden extrapolation", "Required bridge"],
                [["material/device proxy", "bounded mechanism claim", "array or workload advantage", "compact model and hardware-in-loop"]],
                kind="section",
            ),
            marker_section("controllable-actions", "Controllable Actions", "Run the bounded search, matched control, and capability verification tasks."),
            marker_table("unknowns", "Unknowns", ["Unknown", "Why it matters", "Resolution action", "Deadline"], [["local transfer behavior", "sets route applicability", "matched local test", "2026-08-31"]], kind="section"),
            marker_section("scope", "Scope and Exclusions", "Evidence is bounded to the declared window and target regime; patent opinion and exhaustive review are excluded."),
        ]
    )


def _search(mode: str, lens: str, *, enhanced: bool = False) -> str:
    headers = [
        "Query ID", "Date", "Task mode", "Discovery lens", "Search lane", "Source/database",
        "Exact query and filters", "Purpose", "Results", "Screened/selected", "Evidence IDs",
        "Miss/limitation", "Stop or next-query decision",
    ]
    rows = [
        ["Q-001", "2026-07-31", mode, lens, "canonical-anchor", "Crossref", "durable bottleneck review", "establish canonical frame", "24", "12/2", "E-001", "review may smooth disagreements", "expand to primary work"],
        ["Q-002", "2026-07-31", mode, lens, "frontier-radar", "OpenAlex", "recent primary mechanism", "frontier sensing", "31", "14/2", "E-001,E-002", "citation signal is salience only", "verify full context"],
        ["Q-003", "2026-07-31", mode, lens, "gray-space-mismatch", "Scholar", "mature need AND controllable primitive", "two-sided positive evidence", "18", "9/2", "E-001,E-002", "interface remains bounded", "search adjacent terms"],
        ["Q-004", "2026-07-31", mode, lens, "direct-neighbor", "Scholar", "exact interface neighbor", "crowding boundary", "0", "0/0", "E-001", "bounded sparse evidence; not a novelty claim", "search adjacent terminology"],
        ["Q-005", "2026-07-31", mode, lens, "bounded-negative", "IEEE", "failure alternative baseline", "disconfirm mechanism", "11", "7/1", "E-003", "one database omits materials venues", "repeat in Crossref"],
        ["Q-006", "2026-07-31", mode, lens, "baseline-negative", "Crossref", "strongest conventional baseline", "baseline fairness", "20", "10/2", "E-002,E-003", "system overhead incompletely reported", "retain as audit gap"],
    ]
    if enhanced:
        rows.extend(
            [
                ["Q-007", "2026-07-31", mode, lens, "SOTA-family", "Crossref", "best demonstrated family and full-budget baseline", "map SOTA families", "17", "8/2", "E-001,E-002", "specialist implementations remain thin", "stop after strongest baseline is responsive"],
                ["Q-008", "2026-07-31", mode, lens, "translation", "IEEE", "device to system bridge evidence", "test cross-layer transfer", "13", "6/1", "E-002,E-003", "manufacturing access is incomplete", "retain the bridge as conditional"],
            ]
        )
    parts = [
            "# Search Log",
            marker_section("search-policy", "Search Policy", "Frontier salience orders retrieval but does not determine claim confidence; direct and limiting evidence adjudicate claims."),
            marker_table("search-queries", "Queries", headers, rows),
            marker_table(
                "frontier-signals",
                "Frontier Signals",
                ["Evidence ID", "Signal type", "Value or unavailable", "Source", "As-of date", "Field/year normalized: yes/no/unavailable", "Use in decision"],
                [
                    ["E-001", "authoritative-synthesis", "120", "OpenAlex", "2026-07-31", "yes", "retrieval priority only"],
                    ["E-002", "representative-primary", "45", "OpenAlex", "2026-07-31", "yes", "retrieval priority only"],
                ],
            ),
            marker_table("seed-expansion", "Seed Expansion", ["Seed Evidence ID", "Relation explored", "Records selected", "New Evidence IDs", "Coverage note"], [["E-001", "cited and citing neighbors", "two independent records", "E-002,E-003", "closed canonical, primary, and limiting lanes"]], kind="section"),
            marker_section("bounded-negative-evidence", "Bounded Negative Evidence", "Q-004 returned zero exact matches in one bounded corpus; this means sparse evidence only and does not prove priority."),
    ]
    if enhanced:
        parts.append(
            marker_table(
                "coverage-audit",
                "Six-Lane Coverage and Blind Spots",
                ["Lane", "Query IDs", "Relevant Evidence IDs", "Coverage status: covered/thin/query-failed/out-of-scope", "Blind spot or failure mode", "Next query or stop rationale"],
                [
                    ["canonical-anchor", "Q-001", "E-001", "covered", "review synthesis can smooth disagreement", "stop after primary and limiting evidence are linked"],
                    ["frontier-radar", "Q-002", "E-001,E-002", "covered", "salience does not establish causality", "stop after representative primary work is verified"],
                    ["SOTA-family", "Q-007", "E-001,E-002", "covered", "specialist implementations remain thin", "stop after the full-budget comparator is responsive"],
                    ["direct-neighbor", "Q-004", "E-001", "thin", "one bounded corpus returned zero exact matches", "retain sparse-evidence wording and search adjacent terminology"],
                    ["baseline-negative", "Q-006", "E-002,E-003", "covered", "system overhead is incompletely reported", "carry overhead into the route gate"],
                    ["translation", "Q-008", "E-002,E-003", "thin", "manufacturing access evidence is incomplete", "treat the cross-layer bridge as conditional"],
                ],
            )
        )
    return "\n".join(parts)


def _evidence(*, enhanced: bool = False) -> str:
    claim_headers = ["Claim ID", "Claim type", "Atomic bounded claim", "Scope/regime", "Epistemic label", "Decision critical: yes/no", "Status", "Parent Claim ID"]
    evidence_headers = [
        "Evidence ID", "Claim IDs", "Source role", "Stance", "Directness", "Study/source type",
        "Publication status", "Core contribution", "Exact supported/limited claim", "Scope/regime",
        "Method-validity note", "Independence/replication", "Source metadata", "DOI or stable URL",
        "Provenance locator", "Full-context status", "Verification", "Frontier signal",
        "Citation signal/source/as-of", "Reader ref",
    ]
    evidence_rows = [
        ["E-001", "B-001,M-001,S-001,CL-001", "canonical-anchor", "supports", "direct", "review plus primary synthesis", "peer reviewed", "defines the durable bottleneck and measured regime", "B-001 within the target regime", "bounded operating regime", "methods address the observable", "independent group alpha", "Alpha et al. 2025", "https://doi.org/10.1234/rom.001", "full text section 3", "full-context-verified", "verified", "authoritative synthesis", "120/OpenAlex/2026-07-31", "1"],
        ["E-002", "B-001,M-001,S-001,CL-001", "direct-support", "supports", "direct", "controlled experiment", "peer reviewed", "demonstrates the controllable state operation", "M-001 under matched controls", "bounded device regime", "control disables the mechanism", "independent group beta", "Beta et al. 2026", "https://doi.org/10.1234/rom.002", "full text figure 4", "full-context-verified", "verified", "representative primary", "45/OpenAlex/2026-07-31", "2"],
        ["E-003", "B-001", "limitation-negative", "limits", "direct", "controlled counterexample", "peer reviewed", "shows an alternative mechanism in a neighboring regime", "limits broad extrapolation of B-001", "adjacent regime", "matched negative control", "independent group gamma", "Gamma et al. 2024", "https://doi.org/10.1234/rom.003", "full text supplement 2", "full-context-verified", "verified", "specialist negative result", "unavailable", "3"],
    ]
    if enhanced:
        evidence_headers.insert(16, "verification_depth")
        evidence_headers.insert(18, "Canonical cross-run ref")
        for row in evidence_rows:
            row.insert(16, "full-text")
            row.insert(18, "none")
        # Baseline fixtures do not pretend that a nonexistent Deep Reading run
        # has been imported. Cross-run tests create real canonical files.
    for index, row in enumerate(evidence_rows, 1):
        row[11] = f"chains=EC-{index:03d}; basis=independent source group {index} and separate devices"
    contradiction_headers = [
        "Claim ID", "Supporting Evidence IDs", "Contradicting/limiting Evidence IDs",
        "Independence", "Current interpretation", "Resolution action", "Decision ID",
    ]
    contradiction_row = [
        "B-001", "E-001,E-002", "E-003", "independent groups",
        "limitation applies only to an adjacent regime", "run matched boundary control",
        "D-002",
    ]
    if enhanced:
        contradiction_headers[4:4] = [
            "Tension type: direct-conflict/evidence-gap/condition-difference",
            "Condition delta",
            "Adjudication: support-dominant/limit-dominant/condition-split/unresolved",
        ]
        contradiction_row[4:4] = [
            "condition-difference",
            "the limiting study uses an adjacent temperature and control regime",
            "condition-split",
        ]
    parts = [
            "# Evidence Matrix",
            marker_table(
                "atomic-claims", "Atomic Claims", claim_headers,
                [
                    ["B-001", "existence", "A durable bottleneck exists in the bounded regime", "target regime only", "Evidence", "yes", "open", "not applicable: root claim"],
                    ["M-001", "mechanism", "Control changes the target state operation", "matched control regime", "Inference", "no", "open", "B-001"],
                    ["S-001", "system-value", "A bridge metric is needed before system value", "device-to-system boundary", "Inference", "no", "open", "B-001"],
                    ["CL-001", "comparative", "The route must beat a conventional baseline", "same budget", "Recommendation", "no", "open", "B-001"],
                ],
            ),
            marker_table("evidence-records", "Evidence Records", evidence_headers, evidence_rows),
    ]
    if enhanced:
        parts.append(
            marker_table(
                "deep-reading-handoff",
                "Deep Reading Handoff Queue",
                ["Deep-read request ID", "Paper key", "Target Claim/Route IDs", "Decision-changing question", "Priority: high/medium/low", "Status: queued/in-progress/imported/blocked/skipped", "Deep Reading run", "Canonical refs", "Imported Evidence IDs", "Blocker or import decision"],
                [[
                    "DR-001", "doi:10.1234/rom.002", "B-001",
                    "Does the full method distinguish controlled state change from thermal drift?",
                    "high", "queued", "none", "none",
                    "none", "full-text context exists; canonical adjudication remains queued",
                ]],
            )
        )
    parts.extend(
        [
            marker_table(
                "claim-confidence", "Claim Confidence",
                ["Claim ID", "Required evidence roles", "Supporting Evidence IDs", "Limiting Evidence IDs", "Directness summary", "Full-context status", "Method validity", "Independence/replication", "Consistency/conflict status", "Applicability", "Confidence: High/Moderate/Low/Insufficient", "Active cap codes", "Cap/downgrade reason", "Allowed wording", "Upgrade evidence/action", "Overturn condition"],
                [["B-001", "canonical and independent primary", "E-001,E-002", "E-003", "direct", "verified full context", "methods answer bounded claim", "two independent groups", "consistent; neighboring limitation resolved", "target regime only", "High", "none", "scope remains bounded", "Evidence supports a durable bottleneck in the target regime", "replicate under local stack", "matched local control eliminates the bottleneck"]],
            ),
            marker_section("source-annotations", "Important Source Annotations", "E-001 core contribution, exact support boundary, and full-context provenance were verified and retained in the evidence record."),
            marker_table(
                "contradictions", "Contradictions and Mixed Evidence",
                contradiction_headers,
                [contradiction_row],
            ),
        ]
    )
    return "\n".join(parts)


def _bio_table(name: str, *, bio: bool, kind: str = "section") -> str:
    headers = ["Biological observation", "Abstract computational principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological strong baseline", "Principle-specific ablation", "Measurable intrinsic gain and boundary"]
    if bio:
        row = ["adaptive forgetting under nonstationarity", "error-gated timescale adaptation", "r(t+1)=r(t)+eta(e)Delta r", "error-gated adaptive-forgetting update", "controllable relaxation state", "Can error-gated retention control lower regret under bounded drift without biological terminology?", "same-budget digital adaptive filter baseline", "disable error-gated timescale coupling", "lower regret at equal energy within the tested drift regime"]
    else:
        row = ["not applicable: non-biological problem", "not applicable: no biological analogy claimed", "not applicable: conventional state equation", "not applicable: conventional update", "not applicable: conventional primitive", "Can controlled physical retention improve the bounded target metric?", "conventional matched baseline", "control-disabled physical ablation", "bounded gain will be reported in the tested regime"]
    return marker_table(name, "Bio-Inspired Translation", headers, [row], kind=kind)


def _attack_rows(
    target: str,
    *,
    bio: bool,
    capability_id: str | None = "CAP-001",
    extra_targets: Sequence[str] = (),
    single_target: bool = False,
) -> list[list[str]]:
    secondary = target if single_target or len(extra_targets) < 1 else extra_targets[0]
    tertiary = target if single_target or len(extra_targets) < 2 else extra_targets[1]
    return [
        ["A-001", target, "problem-adequacy", "The metric may create a pseudo-bottleneck", "E-001 and an alternative-metric comparison", "medium", "compare the primary and alternative metric under identical controls", "Keep", "D-001", "closed"],
        ["A-002", target, "mechanism", "A neighboring mechanism can explain the observable", "E-003 and the control-disabled matched test", "high", "run the control-disabled matched test and narrow wording until it separates signatures", "Revise", "D-002", "open"],
        ["A-003", target, "evidence", "The direct evidence chain may be too shallow", "E-001,E-003 plus an independent full-context source", "medium", "verify independent full-context evidence for the bounded claim", "Keep", "D-003", "resolved"],
        ["A-004", target, "open-position", "Adjacent terminology may erase the claimed opening", "Q-004 and an adjacent-module neighbor search", "medium", "complete the bounded adjacent-terminology and close-neighbor search", "Keep", "D-004", "resolved"],
        ["A-005", secondary, "capability", "The route may rely on an unverified local capability", f"{capability_id} status plus a first-week capability gate" if capability_id else "declared capability status plus a first-week capability gate", "medium", "verify access, readiness, dependency, and lead time before commitment", "Keep", "D-005", "mitigated"],
        ["A-006", tertiary, "cross-scale", "Device evidence cannot establish workload value", "E-002 and a compact-model hardware-in-loop bridge", "high", "add compact-model and hardware-in-loop validation before any system claim", "Keep", "D-006", "mitigated"],
        ["A-007", target, "baseline-system-cost", "The conventional baseline may match the gain", "E-002,E-003 and a same-budget end-to-end comparison", "medium", "run the same-budget baseline including calibration and readout cost", "Keep", "D-007", "resolved"],
        [
            "A-008", target, "bio-inspired-translation",
            "Biological resemblance may add no principle-specific gain" if bio else "No biological claim is in scope, but the non-biological baseline still bounds interpretation",
            "same-budget non-biological baseline and principle-specific ablation",
            "medium", "run the non-biological baseline and ablation or retain an explicit not-applicable boundary",
            "Revise" if bio else "Keep", "D-008", "open" if bio else "closed",
        ],
    ]


def _red_team(
    target: str,
    *,
    bio: bool,
    capability_id: str | None = "CAP-001",
    extra_targets: Sequence[str] = (),
    single_target: bool = False,
) -> str:
    attacks = _attack_rows(
        target, bio=bio, capability_id=capability_id,
        extra_targets=extra_targets, single_target=single_target
    )
    bio_headers = ["Target", "Biological observation", "Abstract principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological baseline", "Principle-specific ablation", "Intrinsic gain/boundary", "Verdict", "Decision ID"]
    bio_row = (
        [target, "adaptive forgetting", "error-gated timescale adaptation", "r(t+1)=r(t)+eta(e)Delta r", "error-gated adaptive-forgetting update", "relaxation state", "Can error-gated retention control lower regret under bounded drift?", "same-budget adaptive filter", "disable timescale coupling", "lower regret in tested drift", "Revise", "D-008"]
        if bio
        else [target, "not applicable: no biological claim", "not applicable: physical principle", "not applicable: conventional state equation", "not applicable: conventional update", "conventional state primitive", "Can controlled physical retention improve the bounded target metric?", "same-budget conventional baseline", "disable target control", "bounded gain in target regime", "Keep", "D-008"]
    )
    return "\n".join(
        [
            "# Red Team",
            marker_table("attack-register", "Attack Register", ["Attack ID", "Target claim/route", "Attack surface", "Strongest objection", "Evidence IDs or test", "Severity: low/medium/high/blocking", "Required repair or discriminating test", "Verdict: Keep/Downgrade/Revise/Kill", "Decision ID", "Status"], attacks),
            marker_table("baseline-ladder", "Strongest Baseline Ladder", ["Target claim/route", "Material/device baseline", "Control-disabled baseline", "Alternative mechanism", "Circuit/digital or conventional baseline", "End-to-end baseline", "Missing comparison", "Decision impact"], [[target, "matched device", "control disabled", "neighboring mechanism", "same-budget conventional solver", "end-to-end reference", "local calibration", "Revise before claim"]]),
            marker_table("alternative-explanations", "Alternative Explanations", ["Target claim/route", "Observable", "Preferred mechanism", "Alternative explanation", "Discriminating control", "Expected signatures", "Decision rule", "Threshold"], [[target, "state readout", "controlled state transition", "thermal or trap drift", "control-disabled matched run", "opposite timescale signature", "prefer mechanism only after separation", "effect exceeds noise by five sigma"]]),
            marker_table("evidence-independence", "Evidence Independence", ["Claim ID", "Single-source/team risk", "Full-context gap", "Replication gap", "Direct conflict", "Confidence cap", "Required evidence", "Decision ID"], [["B-001", "two independent groups available", "full context checked", "local replication pending", "resolved adjacent conflict", "High within scope", "local matched replication", "D-002"]]),
            marker_table("capability-scale", "Capability and Scale", ["Target claim/route", "Starting evidence scale", "Claimed destination scale", "Missing bridge", "Capability ID/state", "PVT/variation/yield/reliability or analogous cost", "Verdict", "Decision ID"], [[target, "device proxy", "bounded device conclusion", "compact-model bridge", f"{capability_id}/Observed" if capability_id else "Observed capability; no inherited ID", "variation and reliability remain explicit", "Keep", "D-003"]]),
            marker_table("bio-inspired-audit", "Bio-Inspired Audit", bio_headers, [bio_row]),
            marker_table("kill-criteria", "Kill Criteria", ["Target claim/route", "Kill criterion", "Quantitative threshold", "Earliest test", "Consequence", "Fallback/retained asset", "Decision ID"], [[target, "control does not change state", "effect below five sigma", "stage one", "Kill mechanism claim", "retain measurement workflow", "D-002"]]),
            marker_section("decision-impact", "Decision Impact", f"{target} Revise under D-002: the report now limits the mechanism claim and adds a discriminating control."),
        ]
    )


def _decisions(
    target: str,
    *,
    bio: bool = False,
    capability_id: str | None = "CAP-001",
    extra_targets: Sequence[str] = (),
    single_target: bool = False,
    manifest_failures: Sequence[dict[str, str]] = (),
) -> str:
    attacks = _attack_rows(
        target, bio=bio, capability_id=capability_id,
        extra_targets=extra_targets, single_target=single_target
    )
    rows = []
    for attack in attacks:
        attack_id, attack_target, surface = attack[0], attack[1], attack[2]
        verdict, decision_id = attack[7], attack[8]
        rows.append([
            decision_id, "2026-07-31", attack_target, attack_target, verdict,
            f"Disposition after {surface} attack", "E-001,E-002,E-003",
            "bounded decision follows the recorded attack", "strongest alternative retained",
            attack_id, "new discriminating evidence reverses the finding",
            "execute the recorded repair and update the reader report",
        ])
    for failure in manifest_failures:
        rows.append([
            failure["decision_id"],
            "2026-07-31",
            target,
            target,
            failure["verdict"],
            f"Parent manifest failure [{failure['check']}]",
            "not-applicable: deterministic parent manifest recomputation",
            "the immutable parent fails the named schema check",
            "repair only in a separate revision copy or the audit child lineage",
            "not-applicable: deterministic manifest check",
            "a new audit of the separate revision copy recomputes this check as pass",
            failure["repair"],
        ])
    return "\n".join(
        [
            "# Decision Log",
            marker_table("decisions", "Decisions", ["Decision ID", "Date", "Target ID", "Affected decision target IDs", "Status: Keep/Downgrade/Revise/Kill", "Decision", "Evidence IDs", "Inference", "Alternative", "Trigger Attack IDs", "Reversal condition", "Owner/next action"], rows),
            marker_table("revisions", "Revisions", ["Target ID", "Previous position", "Trigger Evidence/Attack IDs", "Revised position", "Report section changed", "Knowledge retained"], [[target, "broad mechanism claim", "E-003,A-002", "bounded mechanism claim", "decision summary and route", "measurement protocol"]]),
            marker_table("open-uncertainty", "Open Uncertainty", ["Uncertainty", "Priority", "Affected IDs", "Resolution action", "Owner", "Due date"], [["local transfer behavior", "high", target, "run matched local control", "route owner", "2026-08-31"]]),
            marker_table("next-actions", "Next Actions", ["Action", "Type: search/experiment/model/collaboration", "Dependency", "Deliverable", "Decision enabled"], [["run discriminating control", "experiment", capability_id or "observed local capability", "matched comparison", "D-002"]]),
        ]
    )


def _landscape_artifacts(
    *,
    bio: bool,
    scenario_summary: str | None = None,
    capability_state: str = "Observed",
    enhanced: bool = False,
) -> dict[str, str]:
    branches = [
        ["BR-001", "retention bottleneck", "stable state", "adaptive computing", "controlled retention", "ferroelectric control", "no", "E-001", "Q-004", "advance"],
        ["BR-002", "energy bottleneck", "low-energy update", "sensing", "local update", "ionic control", "no", "E-002", "Q-005", "compare"],
        ["BR-003", "bandwidth bottleneck", "fast reconfiguration", "wave control", "low-loss tuning", "phase-change control", "yes", "E-001,E-002", "Q-006", "explore"],
        ["BR-004", "reliability bottleneck", "repeatable state", "memory", "variation tolerance", "electrostatic control", "no", "E-003", "Q-004", "fallback"],
    ]
    breadth = "\n".join(
        [
            "# Breadth",
            marker_section("anchor-audit", "Anchor Audit", "The anchor spans the requested domain but is not treated as the only valid mechanism family."),
            marker_table("breadth-branches", "Branches", ["Branch ID", "Bottleneck family", "Desired function/state", "Application context", "Missing primitive/knowledge", "Mechanism families", "Outside favorite family: yes/no", "Representative Evidence IDs", "Disconfirm Query ID", "Disposition"], branches),
            marker_table("breadth-summary", "Breadth Summary", ["Metric", "Declared count", "Minimum", "Status"], [["Unique bottleneck families", "4", "4", "pass"], ["Unique mechanism families", "4", "4", "pass"], ["Unique application contexts", "4", "2", "pass"], ["Branches with disconfirming queries", "4", "3", "pass"], ["Outside-favorite-family branches", "1", "1", "pass"]]),
            marker_table("frontier-radar", "Frontier Radar", ["Frontier cluster", "Recent authoritative synthesis Evidence ID", "Representative primary Evidence ID", "Salience signal/source/as-of", "Why it matters now", "Credibility caveat"], [["adaptive physical states", "E-001", "E-002", "OpenAlex normalized 2026-07-31", "recent control advances", "salience is not confidence"]], kind="section"),
            marker_table("gray-space-mismatch", "Gray Space", ["Mismatch ID", "Mature need positive Evidence IDs", "Candidate mechanism positive Evidence IDs", "Bounded neighbor-miss Query ID", "Adjacent terminology checked", "Falsifiable interface", "Status"], [["GS-001", "E-001", "E-002", "Q-004", "device physics and control terminology", "independent retention control", "bounded sparse evidence"]], kind="section"),
            marker_section("breadth-gate", "Breadth Gate", "The recomputed gate passes and ranking may begin; all exceptions remain explicit."),
        ]
    )
    research = "\n".join(
        [
            "# Research Map",
            marker_section("decision-summary", "Decision Summary", "Evidence supports a bounded opportunity; inference and recommendation remain separately labeled."),
            marker_section("background-question", "Background Question", "The scientific question asks whether independent control changes the state operation beyond the strongest baseline."),
            marker_table("persistent-bottlenecks", "Persistent Bottlenecks", ["Bottleneck Claim ID", "Desired function/state", "Regime", "Why it persists", "Strongest current baseline", "Supporting Evidence IDs", "Confidence"], [["B-001", "stable controllable state", "target regime", "coupled state variables", "same-budget conventional control", "E-001,E-002", "High"]]),
            marker_table("sota-families", "SOTA Families", ["Approach family", "Core idea", "Best demonstrated regime", "Enabling assumption", "Strongest Evidence IDs", "Unresolved failure mode", "Why the persistent bottleneck remains"], [["active compensation", "cancel drift", "small arrays", "stationary calibration", "E-001,E-002", "calibration overhead", "nonstationarity breaks the assumption"]]),
            marker_table("mapping-lattice", "Mapping Lattice", ["Decision context", "Desired function/observable", "Persistent bottleneck", "Missing controllable primitive/knowledge", "Falsifiable mechanism", "Implementation/process route", "Discriminating test", "Bounded conclusion", "Evidence IDs"], [["adaptive hardware", "controlled retention", "B-001", "independent timescale control", "M-001", "device proxy", "control-disabled comparison", "mechanism in target regime", "E-001,E-002"]]),
            marker_table("mechanism-definitions", "Mechanisms", ["Mechanism ID", "Physical/causal state variable", "Control", "Readout", "Governing dynamics", "Timescale/regime", "Failure modes", "Evidence IDs"], [["M-001", "bounded internal state", "independent field", "electrical proxy", "relaxation equation", "target timescale", "thermal drift", "E-002,E-003"]]),
            marker_table("open-interfaces", "Open Interfaces", ["Interface ID", "Layers joined", "Unresolved falsifiable question", "Two-sided positive Evidence IDs", "Direct-neighbor Query ID", "Bounded miss Query ID", "Crowding class", "Candidate ID"], [["I-001", "state and readout", "does independent control survive baseline", "E-001,E-002", "Q-004", "Q-004", "sparse direct matches", "C-001"]]),
            _bio_table("bio-inspired-translation", bio=bio, kind="section"),
            marker_table("uncertainty-register", "Uncertainty Register", ["Uncertainty", "Affected claim/route", "Current bound", "Resolution search/experiment", "Reversal condition", "Decision ID"], [["local transfer behavior", "C-001", "unknown beyond target regime", "matched local experiment", "baseline dominates", "D-002"]]),
        ]
    )
    route_headers = ["Candidate ID", "Risk: low/medium/high", "What", "Why: sufficiency/necessity/timing", "Need to know", "How", "What we learn", "Strongest baseline", "Competing hypotheses", "Positive outcome", "Negative outcome", "Ambiguous outcome", "Three-month decisive test", "Quantitative threshold", "Kill criterion", "One-year platform path", "Retained value", "Evidence IDs", "Reversal condition"]
    route_rows = [
        ["C-001", "low", "test independent state control", "persistent bounded bottleneck", "state and readout", "matched controlled proxy", "whether mechanism is causal", "same-budget controller", "thermal drift", "control separates states", "no separation", "mixed timescale", "matched control test", "five-sigma separation", "effect below threshold", "compact model", "measurement workflow", "E-001,E-002", "baseline dominates"],
        ["C-002", "medium", "couple device proxy to model", "tests cross-scale bridge", "variation and overhead", "compact model integration", "whether gain survives overhead", "digital reference", "calibration artifact", "system proxy improves", "overhead removes gain", "uncertain calibration", "hardware-in-loop", "ten percent gain", "no gain at equal budget", "array model", "compact model", "E-002,E-003", "overhead exceeds benefit"],
        ["C-003", "high", "explore new state operation", "could remove missing primitive", "fabrication boundary", "simulation then collaborator", "whether new primitive exists", "best conventional device", "unmodeled loss", "new controllable regime", "state unstable", "readout ambiguous", "decisive simulation", "robust across three seeds", "no stable regime", "shared platform", "parameter provenance", "E-001,E-003", "neighbor demonstrates same interface"],
    ]
    portfolio_parts = [
            "# Portfolio",
            marker_table("shared-platform", "Shared Platform", ["Platform module", "Reused by Candidate IDs", "Current capability state", "New dependency", "Retained value if flagship fails"], [["multiphysics and matched readout", "C-001,C-002,C-003", "CAP-001 Observed", "collaborator fabrication", "validated model and controls"]], kind="section"),
            marker_table("candidate-routes", "Candidate Routes", route_headers, route_rows),
            marker_table("scorecard", "Scorecard", ["Candidate ID", "Persistence", "Mechanism depth", "Capability transfer", "First-data feasibility", "Platform leverage", "Open-interface evidence", "System value", "Dependency penalty", "Written rationale"], [["C-001", "high", "high", "ready", "high", "high", "bounded", "conditional", "low", "best decisive first test"], ["C-002", "high", "medium", "adaptable", "medium", "high", "bounded", "conditional", "medium", "tests the scale bridge"], ["C-003", "medium", "high", "collaborator", "low", "medium", "sparse", "unknown", "high", "high-risk primitive exploration"]]),
            marker_section("sensitivity", "Sensitivity", "C-001 remains preferred unless local capability is unavailable; then C-002 becomes the primary bridge route."),
            marker_table("rejected-routes", "Rejected Routes", ["Candidate ID", "Why initially attractive", "Decisive objection", "Evidence IDs", "Verdict: Downgrade/Revise/Kill", "Decision ID", "Reconsideration condition"], [["C-004", "new physical freedom", "fabrication dependency dominates", "E-003", "Revise", "D-002", "collaborator validates process"]]),
    ]
    if enhanced:
        portfolio_parts.extend(
            [
                marker_table(
                    "opportunity-gates",
                    "Opportunity Gates",
                    ["Candidate ID", "Openness gate: pass/conditional/fail/unknown", "Contribution gate: pass/conditional/fail/unknown", "Feasibility gate: pass/conditional/fail/unknown", "Overall: go/conditional-go/defer/no-go", "Recall caveat", "Gate Evidence IDs", "Binding condition or next check"],
                    [
                        ["C-001", "pass", "pass", "pass", "go", "Coverage is bounded to Crossref, OpenAlex, Scholar, and IEEE queries through 2026-07-31 in English terminology with open-access limits.", "E-001,E-002,E-003", "advance after the matched local control confirms transfer"],
                        ["C-002", "pass", "conditional", "conditional", "conditional-go", "Coverage is bounded to Crossref and IEEE queries through 2026-07-31 in English terminology; proprietary system data were not accessible.", "E-001,E-002,E-003", "hold system claims until equal-budget overhead is measured"],
                        ["C-003", "unknown", "conditional", "fail", "no-go", "Coverage is bounded to Crossref and Scholar queries through 2026-07-31 in English device terminology; patent and fabrication records are incomplete.", "E-001,E-003", "do not advance without observed fabrication access"],
                    ],
                ),
                marker_table(
                    "route-fast-pilots",
                    "Top Route Fast Pilots",
                    ["Candidate ID", "Rank: 1-3", "Hypothesis A", "Hypothesis B", "Discriminating test", "Observable", "Horizon days: 1-14", "Resource cap", "Advance threshold", "Kill or revise threshold"],
                    [[
                        "C-001", "1",
                        "independent field control changes the intrinsic state timescale",
                        "the apparent change is thermal drift under the same readout",
                        "randomized control-enabled versus temperature-matched control-disabled sweep",
                        "difference in fitted state timescale with uncertainty",
                        "14", "one existing fixture and forty instrument-hours",
                        "five-sigma separation with stable sign across three repeats",
                        "revise if separation is below two sigma or flips sign",
                    ]],
                ),
            ]
        )
    portfolio = "\n".join(portfolio_parts)
    return {
        "intake": _intake(
            "landscape", scenario_summary=scenario_summary,
            capability_state=capability_state,
        ),
        "breadth_ledger": breadth,
        "search_log": _search("landscape", "balanced", enhanced=enhanced),
        "evidence_matrix": _evidence(enhanced=enhanced),
        "research_map": research,
        "candidate_portfolio": portfolio,
        "red_team": _red_team("C-001", bio=bio, extra_targets=("C-002", "C-003")),
        "decision_log": _decisions("C-001", bio=bio, extra_targets=("C-002", "C-003")),
    }


def _focus_artifacts(
    lens: str,
    *,
    bio: bool,
    parent_id: str | None,
    scenario_summary: str | None = None,
    capability_state: str = "Observed",
    enhanced: bool = False,
) -> dict[str, str]:
    parent_text = parent_id or "standalone focus"
    focus_scope = "\n".join(
        [
            "# Focus Scope",
            marker_table("parent-lineage", "Parent Lineage", ["Parent run ID", "Selected branch/node", "Inherited Claim IDs", "Inherited Evidence IDs", "Inherited Capability IDs", "Snapshot limitation"], [[parent_text, "BR-001" if parent_id else "standalone branch", "B-001", "E-001", "CAP-001", "snapshot fixes an as-of boundary"]], kind="section"),
            marker_section("exact-question", "Exact Question", "Can independent control change the target state operation beyond the same-budget baseline? Null: the control has no effect beyond drift."),
            marker_table("local-alternatives", "Local Alternatives", ["Alternative ID", "Role: primary/comparator/fallback/neighbor", "Mechanism or approach", "What it shares", "What differs causally", "Strongest baseline", "Evidence IDs", "Disposition"], [["C-001", "primary", "independent state control", "same readout", "new control variable", "matched controller", "E-001,E-002", "advance"], ["C-002", "comparator", "active compensation", "same metric", "algorithmic control", "digital reference", "E-001", "compare"], ["C-003", "fallback", "static calibrated state", "same device", "no dynamic control", "calibrated device", "E-003", "retain"]]),
            marker_table("direct-neighbors", "Direct Neighbors", ["Neighbor", "Overlap", "Causal difference", "Same interface: yes/no", "Evidence ID", "Crowding class", "Implication"], [["active compensation", "same output metric", "external rather than intrinsic control", "no", "E-002", "adjacent", "requires fair comparator"]]),
            marker_section("local-coverage-gate", "Local Coverage Gate", "Primary, comparator, fallback, direct-neighbor search, and alternative terminology are all present."),
        ]
    )
    mechanism = "\n".join(
        [
            "# Focus Mechanism",
            marker_section("focus-synthesis", "Focus Synthesis", "Evidence supports the bounded bottleneck; inference proposes independent control; recommendation is a matched discriminating test."),
            marker_table("claim-null-test-threshold", "Claim Null Test Threshold", ["Candidate ID", "Claim ID", "Falsifiable claim", "Null hypothesis", "Manipulated control", "Observable/readout", "Strongest baseline", "Test", "Quantitative threshold", "Kill consequence", "Evidence IDs"], [["C-001", "B-001", "independent control changes retention", "control has no effect beyond drift", "field amplitude", "state readout", "same-budget controller", "matched control-disabled experiment", "five-sigma separation", "Kill mechanism claim", "E-001,E-002"]]),
            marker_table("competing-hypotheses", "Competing Hypotheses", ["Hypothesis ID", "Mechanism", "Predicted signature", "Alternative signature", "Discriminating control", "Ambiguity remaining", "Decision rule"], [["H-001", "controlled state transition", "field-dependent timescale", "temperature-dependent drift", "matched temperature control", "readout noise", "advance only after signature separation"]]),
            marker_table("causal-chain", "Causal Chain", ["Step", "State/quantity", "Control", "Readout", "Governing relation", "Evidence level", "Required bridge", "Forbidden inference"], [["one", "internal state", "field", "electrical proxy", "bounded relaxation", "device proxy", "compact model", "no workload extrapolation"]]),
            marker_table("sota-families", "SOTA Families", ["Approach family", "Best demonstrated regime", "Enabling assumption", "Strongest Evidence IDs", "Failure mode", "Why the bottleneck remains"], [["active compensation", "small array", "stationary calibration", "E-001,E-002", "calibration overhead", "nonstationarity remains"]], kind="section"),
            _bio_table("bio-inspired-translation", bio=bio, kind="section"),
        ]
    )
    route_parts = [
            "# Focus Route",
            marker_table("focus-routes", "Focus Routes", ["Candidate ID", "Route role: primary/comparator/fallback", "What", "Why", "Need to know", "How", "What we learn", "Strongest baseline", "Competing hypotheses", "Evidence IDs"], [["C-001", "primary", "test independent state control", "causal bottleneck", "state timescale", "matched control test", "mechanism causality", "same-budget controller", "thermal drift", "E-001,E-002"], ["C-002", "comparator", "active compensation", "strongest alternative", "calibration overhead", "digital implementation", "whether physics adds value", "optimized digital controller", "algorithmic artifact", "E-001"], ["C-003", "fallback", "static calibrated state", "retains platform value", "drift boundary", "calibration protocol", "bounded device behavior", "commercial device", "trap drift", "E-003"]]),
            marker_table("staged-execution", "Staged Execution", ["Stage", "Route", "Action", "Required evidence", "Quantitative pass threshold", "Kill/revise threshold", "Dependency", "Retained asset"], [["one", "C-001", "matched control experiment", "readout curve", "five-sigma separation", "effect below threshold", "CAP-001", "measurement workflow"], ["one", "C-002", "same-budget active-compensation comparator", "matched cost ledger", "target route exceeds comparator within uncertainty", "comparator matches target", "CAP-001", "baseline harness"], ["one", "C-003", "static calibrated fallback", "bounded drift dataset", "state remains reproducible", "operating window collapses", "CAP-001", "calibration dataset"]]),
            marker_table("outcome-interpretation", "Outcome Interpretation", ["Candidate ID", "Outcome class: positive/negative/ambiguous", "Observable pattern", "Allowed conclusion", "Forbidden conclusion", "Next action", "Decision ID"], [[candidate, outcome, signal, allowed, forbidden, action, decision] for candidate, decision in (("C-001", "D-002"), ("C-002", "D-005"), ("C-003", "D-006")) for outcome, signal, allowed, forbidden, action in (("positive", "route-specific signal exceeds its threshold", "the route passes its bounded gate", "system advantage", "advance to the next bridge"), ("negative", "no separation from its strongest baseline", "the route fails its bounded gate", "all approaches fail", "activate the retained alternative"), ("ambiguous", "mixed dependence within uncertainty", "evidence remains insufficient", "mechanism proven", "tighten controls and repeat"))]),
            marker_table(
                "route-boundaries",
                "Route Boundaries",
                ["Candidate ID", "Kill criterion", "Reversal condition", "Retained value after failure", "Comparator/fallback activation rule"],
                [
                    ["C-001", "effect remains below five-sigma separation", "same-budget comparator dominates", "calibrated readout workflow", "activate C-002 on causal-test failure"],
                    ["C-002", "no equal-budget advantage remains", "target route beats the comparator after matched costing", "baseline harness", "activate C-003 if both dynamic routes fail"],
                    ["C-003", "bounded calibrated state is not reproducible", "a dynamic route becomes reliable within budget", "calibration dataset", "retain only measurement and calibration assets"],
                ],
                kind="section",
            ),
    ]
    if enhanced:
        route_parts.extend(
            [
                marker_table(
                    "opportunity-gates",
                    "Opportunity Gates",
                    ["Candidate ID", "Openness gate: pass/conditional/fail/unknown", "Contribution gate: pass/conditional/fail/unknown", "Feasibility gate: pass/conditional/fail/unknown", "Overall: go/conditional-go/defer/no-go", "Recall caveat", "Gate Evidence IDs", "Binding condition or next check"],
                    [
                        ["C-001", "pass", "pass", "pass", "go", "Coverage is bounded to Crossref, OpenAlex, Scholar, and IEEE queries through 2026-07-31 in English terminology with open-access limits.", "E-001,E-002,E-003", "advance after the matched local control confirms transfer"],
                        ["C-002", "pass", "conditional", "conditional", "conditional-go", "Coverage is bounded to Crossref and IEEE queries through 2026-07-31 in English terminology; proprietary system data were not accessible.", "E-001,E-002,E-003", "retain as comparator until equal-budget overhead is measured"],
                        ["C-003", "conditional", "conditional", "pass", "conditional-go", "Coverage is bounded to Scholar queries through 2026-07-31 in English calibration terminology; unpublished reliability data were not accessible.", "E-001,E-003", "activate only if the dynamic routes fail their thresholds"],
                    ],
                ),
                marker_table(
                    "route-fast-pilots",
                    "Top Route Fast Pilots",
                    ["Candidate ID", "Rank: 1-3", "Hypothesis A", "Hypothesis B", "Discriminating test", "Observable", "Horizon days: 1-14", "Resource cap", "Advance threshold", "Kill or revise threshold"],
                    [[
                        "C-001", "1",
                        "independent field control changes the intrinsic state timescale",
                        "the apparent change is thermal drift under the same readout",
                        "randomized control-enabled versus temperature-matched control-disabled sweep",
                        "difference in fitted state timescale with uncertainty",
                        "14", "one existing fixture and forty instrument-hours",
                        "five-sigma separation with stable sign across three repeats",
                        "revise if separation is below two sigma or flips sign",
                    ]],
                ),
            ]
        )
    routes = "\n".join(route_parts)
    return {
        "intake": _intake(
            "focus", scenario_summary=scenario_summary,
            capability_state=capability_state,
        ),
        "focus_scope": focus_scope,
        "search_log": _search("focus", lens, enhanced=enhanced),
        "evidence_matrix": _evidence(enhanced=enhanced),
        "claim_mechanism_map": mechanism,
        "route_protocol": routes,
        "red_team": _red_team("C-001", bio=bio, extra_targets=("C-002", "C-003")),
        "decision_log": _decisions("C-001", bio=bio, extra_targets=("C-002", "C-003")),
    }


def _evidence_audit_artifacts(
    lens: str,
    parent_id: str | None,
    *,
    enhanced: bool = False,
) -> dict[str, str]:
    scope = "\n".join(
        [
            "# Audit Scope",
            marker_section("audit-decision", "Audit Decision", "Audit B-001 credibility and its effect on the bounded route decision."),
            marker_section("parent-mutation-policy", "Parent Mutation Policy", "supplement-only: parent artifacts remain unchanged; changes are recorded as proposed decisions."),
            marker_table("target-claims", "Target Claims", ["Claim ID", "Claim type", "Atomic bounded claim", "Scope/regime", "Decision critical: yes/no", "Existing confidence", "Parent source"], [["B-001", "existence", "durable bottleneck exists", "target regime", "yes", "High", parent_id or "explicit context source"]], kind="section"),
            marker_table("evidence-requirements", "Evidence Requirements", ["Claim ID", "Required evidence roles", "Required directness/context", "Independence need", "Critical missing role", "Completion rule"], [["B-001", "canonical primary negative", "direct full context", "two independent groups", "local replication", "allowed wording and cap assigned"]], kind="section"),
        ]
    )
    register = "\n".join(
        [
            "# Claim Register",
            marker_table("claim-register", "Claim Register", ["Claim ID", "Claim type", "Atomic bounded claim", "Scope/regime", "Decision importance", "Required evidence roles", "Current Evidence IDs", "Missing role", "Audit priority", "Parent Claim ID"], [["B-001", "existence", "durable bottleneck exists", "target regime", "decision critical", "canonical primary negative", "E-001,E-002,E-003", "local replication", "high", "not applicable: root claim"]]),
            marker_table("claim-dependencies", "Claim Dependencies", ["Upstream Claim ID", "Downstream Claim ID", "Dependency type", "Failure consequence", "Test/search to break dependency"], [["B-001", "M-001", "mechanism depends on bottleneck", "route loses rationale", "matched control experiment"]]),
            marker_section("audit-priority", "Audit Priority", "Resolve directness and independent limiting evidence before widening any conclusion."),
        ]
    )
    assessment = "\n".join(
        [
            "# Confidence Assessment",
            marker_table("confidence-assessment", "Confidence Assessment", ["Claim ID", "Supporting Evidence IDs", "Limiting Evidence IDs", "Directness", "Full-context status", "Method/design validity", "Independence/replication", "Consistency/conflict", "Applicability", "Confidence: High/Moderate/Low/Insufficient", "Active cap codes", "Cap/downgrade reason", "Allowed wording", "Upgrade action/evidence", "Overturn condition", "Parent impact"], [["B-001", "E-001,E-002", "E-003", "direct", "full-context-verified", "methods answer bounded claim", "independent groups", "resolved neighboring conflict", "target regime", "High", "none", "scope remains bounded", "Evidence supports a durable bottleneck in the target regime", "local matched replication", "local control eliminates bottleneck", "Revise broad parent wording"]]),
            marker_section("confidence-caps", "Confidence Caps", "Metadata-only evidence cannot support High; indirect-only evidence is capped Low; unresolved direct conflict is capped Moderate."),
            marker_table("allowed-wording", "Allowed Wording", ["Claim ID", "Allowed wording", "Forbidden wording", "Evidence boundary", "Required report change", "Decision ID"], [["B-001", "Evidence supports a durable bottleneck in the target regime", "universal bottleneck", "two independent sources and one neighboring limitation", "narrow the decision summary", "D-002"]]),
        ]
    )
    gaps = "\n".join(
        [
            "# Gap Plan",
            marker_table("evidence-gaps", "Evidence Gaps", ["Gap ID", "Claim ID", "Missing evidence role", "Why decision-critical", "Cheapest resolving search/test", "Priority", "Stop rule"], [["G-001", "B-001", "local replication", "determines applicability", "matched local experiment", "high", "stop after decisive control"]]),
            marker_table("supplementary-plan", "Supplementary Plan", ["Gap ID", "Query IDs", "Source priority", "Direct neighbor/baseline/negative target", "Expected upgrade or downgrade", "Completion state"], [["G-001", "Q-004,Q-005", "specialist primary", "direct neighbor and negative evidence", "upgrade applicability or downgrade route", "planned"]]),
            marker_table("parent-implications", "Parent Implications", ["Parent claim/route", "Previous wording/status", "Audited wording/status", "Verdict: Keep/Downgrade/Revise/Kill", "Decision ID", "Parent left unchanged: yes/no"], [["B-001", "broad claim", "bounded claim", "Revise", "D-002", "yes"]], kind="section"),
            marker_section("residual-uncertainty", "Residual Uncertainty", "Literature cannot replace a local discriminating experiment; the unresolved applicability gap remains explicit."),
        ]
    )
    return {
        "audit_scope": scope,
        "claim_register": register,
        "search_log": _search("evidence-audit", lens, enhanced=enhanced),
        "evidence_matrix": _evidence(enhanced=enhanced),
        "confidence_assessment": assessment,
        "gap_plan": gaps,
        "red_team": _red_team("B-001", bio=False, capability_id="CAP-001" if parent_id else None),
        "decision_log": _decisions("B-001", capability_id="CAP-001" if parent_id else None),
    }


def _manifest_failure_specs(
    parent_facts: ParentAuditFacts,
) -> tuple[dict[str, str], ...]:
    failures = [
        row for row in parent_facts.manifest_projection if row[2] == "fail"
    ]
    return tuple(
        {
            "check": row[0],
            "evidence": row[1],
            "result": row[2],
            "severity": "high",
            "repair": canonical_manifest_repair(row[0], row[2]),
            "decision_id": f"D-{index:03d}",
            "verdict": "Revise",
        }
        for index, row in enumerate(failures, 9)
    )


def _strongest_manifest_failure(
    failures: Sequence[dict[str, str]],
) -> dict[str, str] | None:
    rank = {"Keep": 0, "Downgrade": 1, "Revise": 2, "Kill": 3}
    return (
        max(failures, key=lambda failure: rank[failure["verdict"]])
        if failures
        else None
    )


def _run_audit_artifacts(
    parent: Path,
    parent_id: str,
    *,
    bio: bool,
    manifest_failures: Sequence[dict[str, str]] | None = None,
    audit_target: str = "B-001",
) -> dict[str, str]:
    parent_manifest = json.loads(
        (parent / "run-manifest.json").read_text(encoding="utf-8")
    )
    parent_facts = inspect_parent_for_audit(
        parent, parent_manifest, {"run_id": parent_id}
    )
    failure_specs = (
        tuple(manifest_failures)
        if manifest_failures is not None
        else _manifest_failure_specs(parent_facts)
    )
    failure_by_check = {
        failure["check"]: failure for failure in failure_specs
    }
    manifest_rows: list[list[str]] = []
    for row in parent_facts.manifest_projection:
        failure = failure_by_check.get(row[0])
        manifest_rows.append([
            row[0],
            row[1],
            row[2],
            failure["severity"] if failure is not None else "low",
            canonical_manifest_repair(row[0], row[2]),
            failure["decision_id"] if failure is not None else "D-001",
        ])
    id_rows = [
        [
            *row,
            "high" if row[4] in {"dangling-reference", "duplicate-definition"} else "low",
            "repair parent ID closure" if row[4] in {"dangling-reference", "duplicate-definition"} else "retain trace",
            "D-002" if row[4] in {"dangling-reference", "duplicate-definition"} else "D-001",
        ]
        for row in parent_facts.id_projection
    ]
    citation_rows = [
        [
            *row,
            "repair parent citation closure" if row[5] not in {"match", "not-applicable-no-declared-reader"} else "retain mapping",
            "D-002" if row[5] not in {"match", "not-applicable-no-declared-reader"} else "D-001",
        ]
        for row in parent_facts.citation_projection
    ]
    binding_failure = _strongest_manifest_failure(failure_specs)
    binding_decision = (
        binding_failure["decision_id"] if binding_failure is not None else "D-002"
    )
    binding_finding = (
        f"parent manifest failure [{binding_failure['check']}]"
        if binding_failure is not None
        else "applicability gap remains"
    )
    binding_repair = (
        binding_failure["repair"]
        if binding_failure is not None
        else "matched local test"
    )
    binding_verdict = (
        binding_failure["verdict"] if binding_failure is not None else "Revise"
    )
    binding_severity = (
        binding_failure["severity"] if binding_failure is not None else "high"
    )
    scope = "\n".join(
        [
            "# Run Audit Scope",
            marker_section("audit-decision", "Audit Decision", f"Determine whether parent route {audit_target} should be kept, downgraded, revised, or killed."),
            marker_table("parent-snapshot", "Parent Snapshot", ["Parent run ID", "Workspace-relative manifest reference", "Manifest SHA-256", "Selected artifacts/hashes", "Schema", "Audit boundary"], [[parent_id, "recorded in manifest", "verified snapshot hash", "declared artifact hashes", "schema two", "read-only parent"]], kind="section"),
            marker_section("mutation-policy", "Mutation Policy", "supplement-only audit: the parent remains read-only and repair requires a separate revision run."),
        ]
    )
    inventory = "\n".join(
        [
            "# Artifact Inventory",
            marker_table("artifact-inventory", "Artifact Inventory", ["Artifact ID", "Manifest role", "Workspace-relative file", "Declared: yes/no", "Exists: yes/no", "SHA-256", "Schema/contract", "Status"], parent_facts.artifact_projection),
            marker_table("manifest-lineage-audit", "Manifest Lineage Audit", ["Check", "Evidence", "Result: pass/fail/uncertain", "Severity", "Required repair", "Decision ID"], manifest_rows, kind="section"),
            marker_table("missing-extra-artifacts", "Missing Extra Artifacts", ["File/role", "Missing/extra/undeclared", "Why it matters", "Exact repair", "Decision ID"], [["reader citation map", "declared and present", "supports closure", "retain mapping", "D-001"]], kind="section"),
        ]
    )
    trace = "\n".join(
        [
            "# Traceability Audit",
            marker_table("id-closure", "ID Closure", ["ID", "Type", "Defined in", "Referenced in", "Dangling/duplicate/mismatch", "Severity", "Repair", "Decision ID"], id_rows),
            marker_table("citation-closure", "Citation Closure", ["Reader reference", "Report DOI/stable URL", "Evidence ID", "Evidence-matrix DOI/stable URL", "Match: yes/no", "Computed status", "Repair", "Decision ID"], citation_rows),
            marker_table("dangling-references", "Dangling References", ["Finding ID", "Claim/report location", "Missing definition/source/locator", "Decision consequence", "Repair", "Decision ID"], [["F-001", "parent decision summary", "no missing locator", "retain citation", "none required", "D-001"]], kind="section"),
        ]
    )
    evidence = "\n".join(
        [
            "# Audited Evidence",
            marker_table("audited-claims", "Audited Claims", ["Claim ID", "Claim type", "Parent wording", "Supporting Evidence IDs", "Limiting Evidence IDs", "Full-context direct support", "Independent replication", "Current justified confidence", "Audit verdict"], [["B-001", "existence", "universal bottleneck", "E-001", "E-003", "yes", "partial local replication", "Moderate", "Revise"]]),
            marker_table("confidence-violations", "Confidence Violations", ["Finding ID", "Claim ID", "Claimed confidence", "Active cap codes", "Evidence basis", "Exact allowed wording", "Decision ID"], [["F-002", "B-001", "High", "regime-transfer-unvalidated", "one unresolved applicability gap", "supported in bounded parent regime", "D-002"]]),
            marker_table("contradictions", "Contradictions", ["Claim ID", "Direct conflict", "Same-team dependence", "Unresolved applicability gap", "Consequence", "Resolution action", "Decision ID"], [["B-001", "neighboring direct limitation", "independent teams", "local stack unknown", "Revise wording", "matched local test", "D-002"]]),
        ]
    )
    reasoning_parts = [
        "# Reasoning Audit",
        marker_table("problem-timing-audit", "Problem Timing", ["Dimension", "Parent claim", "Strongest objection", "Evidence/test", "Verdict", "Decision ID"], [["necessity", "urgent bottleneck", "baseline may bypass it", "E-001", "Revise", "D-002"]], kind="section"),
        marker_table("causal-audit", "Causal Audit", ["Claim/route ID", "Preferred mechanism", "Strongest alternative", "Discriminating control present: yes/no", "Threshold present: yes/no", "Verdict", "Decision ID"], [[audit_target, "controlled state", "thermal drift", "yes", "yes", "Revise", "D-002"]], kind="section"),
        marker_table("cross-scale-audit", "Cross Scale", ["Claim/route ID", "Starting evidence scale", "Claimed scale", "Missing bridge", "Capability state", "System/manufacturing cost omitted", "Verdict", "Decision ID"], [[audit_target, "device", "system", "compact model", "Observed capability; no inherited ID", "variation cost", "Revise", "D-002"]], kind="section"),
        marker_table("open-position-audit", "Open Position", ["Claim ID", "Two-sided positive evidence", "Bounded neighbor search", "Zero-hit overclaim", "Adjacent terminology", "Justified class", "Verdict", "Decision ID"], [["B-001", "E-001,E-003", "bounded parent query", "no", "checked", "sparse direct matches", "Keep", "D-001"]], kind="section"),
    ]
    bio_headers = ["Target", "Biological observation", "Abstract principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological baseline", "Principle-specific ablation", "Intrinsic gain/boundary", "Verdict", "Decision ID"]
    bio_row = [audit_target, "adaptive forgetting", "error-gated adaptation", "r(t+1)=r(t)+eta(e)Delta r", "error-gated adaptive-forgetting update", "relaxation state", "Can error-gated retention control lower regret under bounded drift?", "same-budget adaptive filter", "disable timescale coupling", "regret gain in tested drift", "Revise", "D-008"] if bio else [audit_target, "not applicable: no biological claim", "not applicable: physical principle", "not applicable: conventional state equation", "not applicable: conventional update", "conventional primitive", "Can controlled physical retention improve the bounded target metric?", "same-budget baseline", "disable target control", "bounded target-regime gain", "Keep", "D-008"]
    reasoning_parts.append(marker_table("bio-inspired-audit", "Bio Audit", bio_headers, [bio_row], kind="section"))
    verdicts = "\n".join(
        [
            "# Route Verdicts",
            marker_table("route-verdicts", "Route Verdicts", ["Route/claim ID", "Parent status", "Strongest finding", "Severity", "Verdict: Keep/Downgrade/Revise/Kill", "Allowed current conclusion", "Required repair", "Decision ID"], [[audit_target, "Advance", binding_finding, binding_severity, binding_verdict, "bounded mechanism candidate only", binding_repair, binding_decision]]),
            marker_table("remediation-plan", "Remediation", ["Repair ID", "Affected artifact/section", "Exact change", "Dependency", "Verification command/gate", "Owner", "Status"], [["R-001", "parent decision summary", "narrow universal wording", "D-002", "strict validator and matched test", "route owner", "proposed"]]),
            marker_table("stop-conditions", "Stop Conditions", ["Route/claim ID", "Stop condition", "Re-entry evidence", "Retained knowledge/asset", "Next decision date"], [[audit_target, "matched test shows no effect", "independent local replication", "audit and measurement workflow", "2026-10-31"]], kind="section"),
            marker_section("report-impact", "Report Impact", f"{audit_target} {binding_verdict} under {binding_decision}: {binding_finding}; required repair: {binding_repair}."),
        ]
    )
    return {
        "audit_scope": scope,
        "artifact_inventory": inventory,
        "traceability_audit": trace,
        "evidence_audit": evidence,
        "reasoning_audit": "\n".join(reasoning_parts),
        "route_verdicts": verdicts,
        "red_team": _red_team(
            audit_target, bio=bio, capability_id=None, single_target=True
        ),
        "decision_log": _decisions(
            audit_target,
            bio=bio,
            capability_id=None,
            single_target=True,
            manifest_failures=failure_specs,
        ),
    }


REPORT_MARKERS = {
    "landscape": ["decision-summary", "scope", "background-question", "necessity-timing", "need-to-know", "persistent-bottleneck", "sota-families", "bounded-open-position", "bio-inspired-translation", "recommended-routes", "baseline-hypotheses", "execution", "outcome-interpretation", "evidence-confidence", "red-team-impact", "reversal"],
    "focus": ["decision-summary", "lineage", "background-question", "necessity-timing", "need-to-know", "sota-families", "bounded-open-position", "bio-inspired-translation", "recommended-routes", "baseline-hypotheses", "execution", "outcome-interpretation", "evidence-confidence", "red-team-impact"],
    "evidence-audit": ["decision-summary", "audit-scope", "claim-verdicts", "evidence-confidence", "supplemental-search", "bio-inspired-audit", "allowed-wording", "gap-plan", "decisions", "red-team-impact"],
    "run-audit": ["decision-summary", "audited-snapshot", "integrity", "scientific-red-team", "capability-cross-scale", "open-position-bio", "bio-inspired-audit", "route-verdicts", "red-team-impact", "remediation", "residual-uncertainty"],
}


def _reader_report(
    mode: str,
    language: str,
    *,
    bio: bool,
    scenario_summary: str | None = None,
    run_audit_target: str | None = None,
    run_audit_manifest_failures: Sequence[dict[str, str]] = (),
) -> str:
    title = "可执行科研路线报告" if language.startswith("zh") else "Executable Research Route Report"
    callouts = [
        "> [!IMPORTANT]\n> The decision is bounded by the declared evidence, regime, and reversal conditions."
    ]
    if mode == "run-audit":
        callouts.append("> [!WARNING]\n> Unresolved high-severity findings constrain the parent conclusion.")
    else:
        callouts.extend([
            "> [!NOTE]\n> Salience prioritizes retrieval and never substitutes for direct evidence.",
            "> [!CAUTION]\n> Do not extrapolate a device proxy into array or workload value without a bridge.",
        ])
    scenario = scenario_summary or "bounded physical research opportunity"
    parts = [f"# {title}", f"Scenario boundary: {scenario}", *callouts]
    audit_target = run_audit_target or "B-001"
    attack_target = (
        "C-001"
        if mode in {"landscape", "focus"}
        else audit_target if mode == "run-audit" else "B-001"
    )
    attack_extra_targets: Sequence[str] = (
        ("C-002", "C-003") if mode in {"landscape", "focus"} else ()
    )
    attacks = _attack_rows(
        attack_target,
        bio=bio if mode != "evidence-audit" else False,
        capability_id=None if mode == "run-audit" else "CAP-001",
        extra_targets=attack_extra_targets,
        single_target=mode == "run-audit",
    )
    binding_failure = (
        _strongest_manifest_failure(run_audit_manifest_failures)
        if mode == "run-audit"
        else None
    )
    binding_decision = (
        binding_failure["decision_id"] if binding_failure is not None else "D-002"
    )
    binding_finding = (
        f"parent manifest failure [{binding_failure['check']}]"
        if binding_failure is not None
        else "applicability gap remains"
    )
    binding_repair = (
        binding_failure["repair"]
        if binding_failure is not None
        else "matched local test"
    )
    binding_verdict = (
        binding_failure["verdict"] if binding_failure is not None else "Revise"
    )
    for marker in REPORT_MARKERS[mode]:
        if marker == "red-team-impact":
            parts.append(marker_table(
                marker, "Red-Team Decision Impact",
                ["Attack ID", "Target ID", "Attack surface", "Strongest objection", "Severity", "Verdict", "Status", "Exact repair", "Decision ID"],
                [[row[0], row[1], row[2], row[3], row[5], row[7], row[9], row[6], row[8]] for row in attacks],
                kind="section",
            ))
            continue
        if mode == "landscape" and marker == "decision-summary":
            parts.append(marker_table(
                marker, "Decision Summary",
                ["Risk tier", "Recommended route", "Causal interface", "Three-month decisive evidence", "One-year platform value", "Disposition", "Decision ID"],
                [
                    ["low", "C-001 independent state control", "bounded state/readout interface [1]", "matched control test", "measurement and compact-model platform", "Revise", "D-002"],
                    ["medium", "C-002 model bridge", "device-to-model interface [2]", "hardware-in-loop result", "validated compact model", "Keep", "D-005"],
                    ["high", "C-003 new state operation", "control-to-state interface [3]", "robust simulation", "shared parameter provenance", "Keep", "D-006"],
                ], kind="section",
            ))
            continue
        if mode == "landscape" and marker == "scope":
            parts.append(marker_table(
                marker, "Scope",
                ["Scope item", "Declared boundary"],
                [["domain and scale", "target material/device regime; array and workload claims require an explicit bridge"], ["evidence window", "searches through 2026-07-31; inaccessible full text is confidence-capped"]],
                kind="section",
            ))
            continue
        if mode == "landscape" and marker == "necessity-timing":
            parts.append(marker_table(
                marker, "Necessity and Timing",
                ["Dimension", "Bounded favorable argument", "Strongest counterargument", "Evidence or capability basis", "Decision implication"],
                [
                    ["sufficiency", "a falsifiable state/readout interface exists", "the selected metric may create a pseudo-bottleneck", "E-001 plus an alternative-metric control", "retain only the bounded causal question"],
                    ["necessity", "the durable bottleneck blocks bounded transfer", "active compensation may already suffice", "E-002 plus the same-budget comparator", "keep the conventional route mandatory"],
                    ["timeliness", "recent direct evidence makes the control test feasible", "full-context evidence may remain too shallow", "E-003 and verified access status", "cap wording until verification"],
                    ["urgency", "a three-month test can prevent a year of misallocated work", "waiting may improve the fabrication window", "CAP-001 readiness and lead time", "run the capability gate before commitment"],
                ],
                kind="section",
            ))
            continue
        if mode == "landscape" and marker == "need-to-know":
            parts.append(marker_table(
                marker, "Need to Know",
                ["State/structure", "Causal mechanism", "Scale/regime", "Readout/metric", "Evidence boundary"],
                [["retention state", "independent control-to-state coupling", "single device in bounded drift regime", "matched state readout and energy", "direct full-context sources plus explicit transfer gaps"]],
                kind="section",
            ))
            continue
        if mode == "landscape" and marker == "sota-families":
            parts.append(marker_table(
                marker, "SOTA Families",
                ["Approach family", "What it solves", "Best demonstrated regime", "Enabling assumption", "Strongest evidence", "Residual failure mode", "Why the root bottleneck remains"],
                [["active compensation", "bounded drift", "small arrays", "stationary calibration", "E-001,E-002", "calibration overhead", "nonstationarity breaks the assumption"]], kind="section",
            ))
            continue
        if mode == "landscape" and marker == "bio-inspired-translation":
            parts.append(_bio_table(marker, bio=bio))
            continue
        if mode == "landscape" and marker == "recommended-routes":
            parts.append(marker_table(
                marker, "Recommended Routes",
                ["Route", "What", "Why", "Need to know", "How: existing base→new control→measurement", "What we learn", "Strongest baseline", "Competing hypotheses", "Positive outcome", "Negative outcome", "Ambiguous outcome", "Kill criterion", "Retained value after failure", "Reversal condition"],
                [
                    ["C-001", "test independent state control", "persistent bounded bottleneck", "causal state and readout", "existing model→independent control→matched readout", "whether the mechanism is causal", "same-budget controller", "causal control versus thermal drift", "control-separated signal exceeds threshold", "no separation from baseline", "mixed dependence within uncertainty", "effect below five-sigma separation", "measurement protocol and calibrated dataset", "same-budget comparator dominates"],
                    ["C-002", "build the scale bridge", "tests transfer", "overhead and variation", "device proxy→compact model→hardware-in-loop", "whether gain survives overhead", "optimized digital reference", "physical gain versus calibration artifact", "gain survives calibration and readout cost", "overhead removes the gain", "uncertain calibration transfer", "no gain at equal budget", "compact model and hardware-in-loop harness", "overhead exceeds benefit"],
                    ["C-003", "explore a new state operation", "could supply the missing primitive", "fabrication boundary", "simulation→collaborator→matched measurement", "whether the primitive exists", "best conventional device", "new state operation versus unmodeled loss", "stable controllable regime appears", "operating window collapses", "readout remains ambiguous", "no stable regime", "parameter provenance and shared process protocol", "a direct neighbor demonstrates the same interface"],
                ], kind="section",
            ))
            continue
        if mode == "landscape" and marker == "execution":
            parts.append(marker_table(
                marker, "Execution",
                ["Route", "Horizon", "Method, controls, and parameter boundary", "Pass threshold", "Kill/Revise condition", "Retained asset"],
                [
                    ["C-001", "three months", "matched independent-control experiment within the declared device regime", "control-separated effect exceeds five sigma", "Kill mechanism wording if no separation", "measurement protocol"],
                    ["C-001", "one year", "replication and variation study with fixed readout", "effect survives declared variation window", "Revise scope if transfer fails", "calibrated dataset"],
                    ["C-002", "three months", "compact model fitted to E-002 parameters", "held-out error below ten percent", "Revise bridge if error exceeds threshold", "compact-model scaffold"],
                    ["C-002", "one year", "hardware-in-loop same-budget comparison", "gain survives calibration and readout cost", "Kill system claim if baseline matches", "hardware-in-loop harness"],
                    ["C-003", "three months", "robust simulation over bounded fabrication parameters", "candidate operating window remains nonempty", "Kill primitive if window collapses", "parameter provenance"],
                    ["C-003", "one year", "collaborator fabrication and matched measurement", "predicted state operation is reproduced", "Revise mechanism if signature differs", "shared process protocol"],
                ],
                kind="section",
            ))
            continue
        if mode == "landscape" and marker == "outcome-interpretation":
            parts.append(marker_table(
                marker, "Outcome Interpretation",
                ["Route", "Outcome", "Observable", "Allowed conclusion", "Forbidden extrapolation", "Next action"],
                [
                    [route, outcome, observable, allowed, forbidden, action]
                    for route in ("C-001", "C-002", "C-003")
                    for outcome, observable, allowed, forbidden, action in (
                        ("positive", "control-separated bounded signal", "the tested route passes its local gate", "unvalidated workload advantage", "advance to the next bridge"),
                        ("negative", "no separation from the strongest baseline", "the tested route fails its stated mechanism or value gate", "all neighboring routes fail", "retain assets and use the fallback"),
                        ("ambiguous", "mixed dependence within uncertainty", "evidence remains insufficient", "the mechanism is proven", "tighten controls and repeat"),
                    )
                ], kind="section",
            ))
            continue
        if mode == "landscape" and marker == "evidence-confidence":
            parts.append(marker_table(marker, "Evidence Confidence", ["Claim", "Confidence", "Active cap codes", "Downgrade reason", "Allowed wording", "Upgrade/overturn condition"], [["B-001", "High", "none", "scope remains bounded", "Evidence supports a durable bottleneck in the target regime", "local control eliminates the bottleneck"]], kind="section"))
            continue
        if mode == "focus" and marker == "lineage":
            parts.append(marker_table(
                marker, "Lineage and Scope",
                ["Scope item", "Declared boundary"],
                [["parent selection", "selected parent branch C-001; inherited evidence remains source-attributed"], ["focus boundary", "single-device causal interface; system value requires a later bridge"]],
                kind="section",
            ))
            continue
        if mode == "focus" and marker == "necessity-timing":
            parts.append(marker_table(
                marker, "Necessity and Timing",
                ["Dimension", "Bounded favorable argument", "Strongest counterargument", "Evidence or capability basis", "Decision implication"],
                [
                    ["sufficiency", "the claim has a manipulable state and measurable readout", "the metric may manufacture the bottleneck", "E-001 plus an alternative-metric control", "retain only the bounded question"],
                    ["necessity", "the bottleneck blocks transfer in the target regime", "active compensation may already suffice", "E-002 and same-budget comparator", "keep the comparator mandatory"],
                    ["timeliness", "recent methods enable the discriminating control", "full-context evidence may still be shallow", "E-003 and source-access status", "cap wording until verification"],
                    ["urgency", "the cheapest test resolves a route choice within three months", "waiting could yield a better fabrication window", "CAP-001 readiness and lead time", "run capability gate before commitment"],
                ],
                kind="section",
            ))
            continue
        if mode == "focus" and marker == "sota-families":
            parts.append(marker_table(marker, "SOTA Families", ["Approach family", "What it solves", "Best demonstrated regime", "Strongest evidence", "Enabling assumption", "What remains", "Why the bottleneck persists"], [["active compensation", "bounded drift", "small arrays under stationary calibration", "E-001,E-002 [1-2]", "stationary calibration", "calibration overhead [3]", "nonstationarity remains"]], kind="section"))
            continue
        if mode == "focus" and marker == "bounded-open-position":
            parts.append(marker_table(
                marker, "Bounded Open Position",
                ["Positive evidence on both sides", "Closest direct neighbors", "Adjacent terminology/modules", "Database/date/access boundary", "Unclosed falsifiable interface", "Allowed wording"],
                [["E-001 supports the need; E-002 supports the mechanism", "E-003 and the active-compensation family", "adaptive retention; calibration; readout co-design", "declared databases through 2026-07-31; inaccessible full text capped", "independent control-to-state coupling under matched readout", "a bounded open interface remains under the declared search"]],
                kind="section",
            ))
            continue
        if mode == "focus" and marker == "bio-inspired-translation":
            parts.append(_bio_table(marker, bio=bio))
            continue
        if mode == "focus" and marker == "recommended-routes":
            parts.append(marker_table(
                marker, "Recommended Routes",
                ["Role", "Route", "What", "Why", "Need to know", "How", "What we learn", "Strongest baseline", "Competing hypotheses", "Positive outcome", "Negative outcome", "Ambiguous outcome", "Kill criterion", "Retained value after failure", "Reversal condition", "Disposition", "Decision ID"],
                [["primary", "C-001", "test independent state control", "causal bottleneck", "state timescale", "matched control test", "mechanism causality", "same-budget controller", "controlled transition versus thermal drift", "route-specific signal exceeds threshold", "no separation from the controller", "mixed dependence within uncertainty", "effect remains below five-sigma separation", "calibrated readout workflow", "same-budget comparator dominates", "Revise", "D-002"], ["comparator", "C-002", "active compensation", "strongest alternative", "calibration overhead", "digital implementation", "whether physics adds value", "optimized digital controller", "physical value versus algorithmic artifact", "target exceeds comparator at equal budget", "comparator matches target", "cost ledger remains uncertain", "no equal-budget advantage remains", "baseline harness", "target route beats the comparator after matched costing", "Keep", "D-005"], ["fallback", "C-003", "static calibrated state", "retains platform value", "drift boundary", "calibration protocol", "bounded behavior", "commercial calibrated device", "stable state versus trap drift", "bounded state remains reproducible", "operating window collapses", "drift dependence remains mixed", "calibrated state is not reproducible", "calibration dataset", "a dynamic route becomes reliable within budget", "Keep", "D-006"]], kind="section",
            ))
            continue
        if mode == "focus" and marker == "execution":
            parts.append(marker_table(
                marker, "Execution",
                ["Route", "Stage", "Action/method", "Baseline/controls", "Pass threshold", "Kill/Revise", "Retained value"],
                [
                    ["C-001", "one", "run matched control-to-state experiment", "control-disabled and alternative-mechanism controls", "effect exceeds five sigma", "Kill if signatures do not separate", "measurement protocol"],
                    ["C-002", "one", "run same-budget active-compensation comparator", "equal calibration and readout cost", "target route exceeds comparator within uncertainty", "Downgrade if comparator matches", "baseline harness"],
                    ["C-003", "one", "establish static calibrated fallback", "matched drift window", "bounded state remains reproducible", "Revise operating window if unstable", "calibration dataset"],
                ],
                kind="section",
            ))
            continue
        if mode == "focus" and marker == "outcome-interpretation":
            parts.append(marker_table(
                marker, "Outcome Interpretation",
                ["Route", "Outcome", "Signal", "Allowed conclusion", "Forbidden conclusion", "Next action"],
                [
                    [route, outcome, signal, allowed, forbidden, action]
                    for route in ("C-001", "C-002", "C-003")
                    for outcome, signal, allowed, forbidden, action in (
                        ("positive", "control-separated bounded signal", "the route passes its stated local gate", "system advantage", "advance to the next bridge"),
                        ("negative", "no separation from baseline", "the route fails its stated gate", "all routes fail", "use the retained fallback"),
                        ("ambiguous", "mixed dependence", "evidence remains insufficient", "the mechanism is proven", "improve controls"),
                    )
                ], kind="section",
            ))
            continue
        if mode == "focus" and marker == "evidence-confidence":
            parts.append(marker_table(marker, "Evidence Confidence", ["Claim", "Confidence", "Active cap codes", "Cap reason", "Allowed wording", "Upgrade/overturn"], [["B-001", "High", "none", "scope remains bounded", "Evidence supports the bounded claim", "local control eliminates the effect"]], kind="section"))
            continue
        if mode == "evidence-audit" and marker == "audit-scope":
            parts.append(marker_table(
                marker, "Audit Scope",
                ["Scope item", "Declared boundary"],
                [["target claim", "B-001 and its direct support, limitation, applicability, and parent-decision consequence"], ["mutation policy", "supplement-only; the parent remains unchanged"]],
                kind="section",
            ))
            continue
        if mode == "evidence-audit" and marker == "claim-verdicts":
            parts.append(
                marker_table(
                    "claim-verdicts",
                    "Claim Verdicts",
                    ["Claim", "Previous wording", "Evidence found", "Limiting/contradicting evidence", "Confidence", "Active cap codes", "Allowed wording", "Parent impact", "Decision ID"],
                    [["B-001", "universal bottleneck", "E-001 [1], E-002 [2]", "E-003 [3]", "High", "none", "Evidence supports a durable bottleneck in the target regime", "Revise broad parent wording", "D-002"]],
                    kind="section",
                )
            )
            continue
        if mode == "evidence-audit" and marker == "evidence-confidence":
            parts.append(marker_table(marker, "Evidence Confidence", ["Claim", "Directness", "Full context", "Method validity", "Independence", "Applicability", "Conflict", "Cap reason"], [["B-001", "direct", "verified", "bounded method valid", "two groups", "target regime", "resolved neighbor", "scope remains bounded"]], kind="section"))
            continue
        if mode == "evidence-audit" and marker == "bio-inspired-audit":
            parts.append(marker_table(
                marker, "Bio-Inspired Audit",
                ["Target", "Biological observation", "Abstract principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological baseline", "Principle-specific ablation", "Intrinsic gain/boundary", "Verdict", "Decision ID"],
                [["B-001", "not applicable: no biological claim", "not applicable: physical principle", "not applicable: conventional state equation", "not applicable: conventional update", "conventional primitive", "Can controlled physical retention improve the bounded target metric?", "same-budget conventional baseline", "disable target control", "bounded target-regime gain", "Keep", "D-008"]],
                kind="section",
            ))
            continue
        if mode == "evidence-audit" and marker == "gap-plan":
            parts.append(marker_table(
                marker, "Gap Plan",
                ["Claim", "Missing role", "Cheapest next search/test", "Upgrade condition", "Overturn condition", "Stop rule"],
                [["B-001", "local replication", "matched local control experiment", "independent replication preserves the bounded effect", "the matched control eliminates the bottleneck", "stop after a decisive discriminating result"]],
                kind="section",
            ))
            continue
        if mode == "run-audit" and marker == "audited-snapshot":
            parts.append(marker_table(
                marker, "Audited Snapshot",
                ["Scope item", "Declared boundary"],
                [["parent snapshot", "one immutable parent manifest plus every observed non-cache artifact hash"], ["audit authority", "deterministic recomputation controls integrity; scientific verdicts remain evidence-bounded"]],
                kind="section",
            ))
            continue
        if mode == "run-audit" and marker == "integrity":
            integrity_rows = (
                [
                    [
                        f"parent manifest failure [{row['check']}]",
                        row["evidence"],
                        row["severity"],
                        row["verdict"],
                        row["repair"],
                        row["decision_id"],
                    ]
                    for row in run_audit_manifest_failures
                ]
                if run_audit_manifest_failures
                else [[
                    "manifest, artifact, ID, and citation projections match recomputation",
                    "parent-audit deterministic projections", "low", "Keep",
                    "retain the immutable snapshot and rerun after parent change", "D-001",
                ]]
            )
            parts.append(marker_table(
                marker, "Integrity",
                ["Finding", "Evidence", "Severity", "Verdict", "Repair", "Decision ID"],
                integrity_rows,
                kind="section",
            ))
            continue
        if mode == "run-audit" and marker == "scientific-red-team":
            parts.append(marker_table(marker, "Scientific Red Team", ["Finding ID", "Claim", "Parent confidence", "Active cap codes", "Justified confidence", "Verdict", "Decision ID"], [["F-002", "B-001 [1]", "High", "regime-transfer-unvalidated", "Moderate", "Revise", "D-002"]], kind="section"))
            continue
        if mode == "run-audit" and marker == "bio-inspired-audit":
            if bio:
                bio_row = [audit_target, "adaptive forgetting", "error-gated timescale adaptation", "r(t+1)=r(t)+eta(e)Delta r", "error-gated adaptive-forgetting update", "relaxation state", "Can error-gated retention control lower regret under bounded drift?", "same-budget adaptive filter", "disable timescale coupling", "lower regret in the tested drift regime", "Revise", "D-008"]
            else:
                bio_row = [audit_target, "not applicable: no biological claim", "not applicable: physical principle", "not applicable: conventional state equation", "not applicable: conventional update", "conventional primitive", "Can controlled physical retention improve the bounded target metric?", "same-budget conventional baseline", "disable target control", "bounded target-regime gain", "Keep", "D-008"]
            parts.append(marker_table(
                marker, "Bio-Inspired Audit",
                ["Target", "Biological observation", "Abstract principle", "Mathematical operator/state-update rule", "Algorithm", "Hardware primitive", "De-biologized scientific question", "Non-biological baseline", "Principle-specific ablation", "Intrinsic gain/boundary", "Verdict", "Decision ID"],
                [bio_row],
                kind="section",
            ))
            continue
        if mode == "run-audit" and marker == "route-verdicts":
            parts.append(
                marker_table(
                    "route-verdicts",
                    "Route Verdicts",
                    ["Route/claim", "Parent status", "Strongest objection", "Verdict", "Allowed conclusion", "Required repair", "Stop/re-entry condition", "Decision ID"],
                    [[audit_target, "Advance", binding_finding, binding_verdict, "bounded mechanism candidate only", binding_repair, "stop if matched test shows no effect", binding_decision]],
                    kind="section",
                )
            )
            continue
        body = f"This section provides a bounded, decision-relevant explanation for {marker}."
        if marker == "decision-summary":
            target = attack_target
            refs = "Evidence [1] bounds the decision." if mode == "run-audit" else "Evidence [1], [2], and [3] bound the decision."
            body = (
                f"{target} {binding_verdict} under {binding_decision}: "
                f"{binding_finding}; required repair: {binding_repair}. {refs}"
                if mode == "run-audit"
                else f"{target} Revise under D-002 after the alternative-mechanism control. {refs}"
            )
        if marker == "outcome-interpretation":
            body = "Positive, negative, and ambiguous outcomes each have different allowed conclusions and next actions."
        if marker in {"route-verdicts", "decisions"}:
            body = f"{attack_target} Revise under D-002; exact repair and stop/re-entry conditions are recorded."
        if bio and marker in {"recommended-routes", "baseline-hypotheses", "open-position-bio", "scientific-red-team"}:
            body += " The non-biological baseline is a same-budget adaptive filter and the ablation disables error-gated timescale coupling."
        parts.append(marker_section(marker, marker.replace("-", " ").title(), body))
    references = [
        "1. Alpha source. [DOI](https://doi.org/10.1234/rom.001)",
        "2. Beta source. [DOI](https://doi.org/10.1234/rom.002)",
        "3. Gamma source. [DOI](https://doi.org/10.1234/rom.003)",
    ]
    if mode == "run-audit":
        references = [references[0]]
    parts.append(marker_section("references", "References", "\n".join(references)))
    return "\n".join(parts)


def make_run(
    root: Path,
    *,
    mode: str = "landscape",
    lens: str = "balanced",
    language: str = "zh-CN",
    parent: Path | None = None,
    bio: bool = False,
    run_id: str | None = None,
    domain: str | None = None,
    primary_domain_lens: str | None = None,
    secondary_domain_lenses: Sequence[str] | None = None,
    routing_request: str | None = None,
    scenario_summary: str | None = None,
    capability_state: str = "Observed",
    audit_target: str | None = None,
    enhanced_contracts: bool = True,
) -> Path:
    run_id = run_id or f"fixture-{mode}"
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    parent_id = None
    if parent is not None:
        parent_manifest = json.loads((parent / "run-manifest.json").read_text(encoding="utf-8"))
        parent_id = str(parent_manifest["run_id"])
    run_audit_manifest_failures: tuple[dict[str, str], ...] = ()

    if mode == "landscape":
        artifacts = _landscape_artifacts(
            bio=bio,
            scenario_summary=scenario_summary,
            capability_state=capability_state,
            enhanced=enhanced_contracts,
        )
        artifacts["search_log"] = _search(
            mode, lens, enhanced=enhanced_contracts
        )
    elif mode == "focus":
        artifacts = _focus_artifacts(
            lens,
            bio=bio,
            parent_id=parent_id,
            scenario_summary=scenario_summary,
            capability_state=capability_state,
            enhanced=enhanced_contracts,
        )
    elif mode == "evidence-audit":
        artifacts = _evidence_audit_artifacts(
            lens, parent_id, enhanced=enhanced_contracts
        )
    elif mode == "run-audit":
        if parent is None:
            raise AssertionError("run-audit fixture requires parent")
        parent_facts = inspect_parent_for_audit(
            parent, parent_manifest, {"run_id": parent_id or "parent"}
        )
        run_audit_manifest_failures = _manifest_failure_specs(parent_facts)
        artifacts = _run_audit_artifacts(
            parent,
            parent_id or "parent",
            bio=bio,
            manifest_failures=run_audit_manifest_failures,
            audit_target=audit_target or "B-001",
        )
    else:
        raise AssertionError(mode)

    role_files = dict(ROLE_FILES[mode])
    report_name = f"{REPORT_PREFIX[mode]}_fixture_2026-07-31.md"
    role_files["reader_report"] = report_name
    for role, content in artifacts.items():
        (run_dir / role_files[role]).write_text(content, encoding="utf-8", newline="\n")
    (run_dir / report_name).write_text(
        _reader_report(
            mode,
            language,
            bio=bio,
            scenario_summary=scenario_summary,
            run_audit_target=audit_target,
            run_audit_manifest_failures=run_audit_manifest_failures,
        ),
        encoding="utf-8", newline="\n",
    )

    root_workspace = workspace_root()
    parents: list[dict[str, object]] = []
    inherited = {"claims": [], "evidence": [], "capabilities": []}
    selected_branch = None
    if parent is not None:
        parent_manifest_path = parent / "run-manifest.json"
        parent_manifest = json.loads(parent_manifest_path.read_text(encoding="utf-8"))
        if mode == "run-audit":
            artifact_hashes = {
                path.relative_to(parent).as_posix(): sha256(path)
                for path in sorted(item for item in parent.rglob("*") if item.is_file())
                if path.name != "run-manifest.json"
            }
        else:
            artifact_hashes = {
                name: sha256(parent / name)
                for name in parent_manifest["artifact_files"]
                if (parent / name).is_file()
            }
        parents.append(
            {
                "run_id": parent_manifest["run_id"],
                "relation": "audits-run" if mode == "run-audit" else "focuses-branch" if mode == "focus" else "supplements-evidence",
                "workspace_relpath": parent.resolve().relative_to(root_workspace.resolve()).as_posix(),
                "source_manifest_sha256": sha256(parent_manifest_path),
                "source_artifact_sha256": artifact_hashes,
            }
        )
        if mode != "run-audit":
            inherited = {
                "claims": ["B-001", "M-001", "S-001", "CL-001"],
                "evidence": ["E-001", "E-002", "E-003"],
                "capabilities": ["CAP-001"],
            }
        selected_branch = {"id": "BR-001", "label": None, "source": "parent"} if mode == "focus" else None

    contexts: list[dict[str, object]] = []
    if mode == "evidence-audit" and parent is None:
        context = run_dir / "claim-context.md"
        context.write_text("Bounded claim context for B-001.\n", encoding="utf-8", newline="\n")
        contexts.append(
            {
                "source_id": "CTX-001",
                "workspace_relpath": context.resolve().relative_to(root_workspace.resolve()).as_posix(),
                "role": "claim-input",
                "access": "read-only",
                "kind": "file",
                "snapshot_sha256": sha256(context),
            }
        )

    manifest = {
        "schema_version": "2.0",
        "skill": "research-opportunity-mapper",
        "skill_version": SKILL_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "run_id": run_id,
        "domain": domain or ("bio-inspired continual-learning hardware" if bio else "bounded physical research opportunity"),
        "short_task_name": "fixture",
        "language": language,
        "created_at": "2026-07-31T00:00:00+00:00",
        "as_of_date": "2026-07-31",
        "task_mode": mode,
        "run_type": mode,
        "discovery_lens": lens,
        "primary_domain_lens": primary_domain_lens or ("neuromorphic-system" if bio else "generic-physical-engineering"),
        "secondary_domain_lenses": (
            list(secondary_domain_lenses)
            if secondary_domain_lenses is not None
            else (["semiconductor-device"] if bio else [])
        ),
        "domain_lens_notes": None,
        "artifact_profile": f"{mode}-v2",
        "completion_status": "complete",
        "parent_mutation_policy": "supplement-only" if mode in {"evidence-audit", "run-audit"} else "child-run-only",
        "routing": {
            "request": routing_request or f"execute {mode} with bounded evidence",
            "requested": mode,
            "selected": mode,
            "reason": ["fixture exercises the declared mode"],
            "confidence": "high",
        },
        "evidence_window": {
            "start": "2021-01-01",
            "end": "2026-07-31",
            "as_of": "2026-07-31",
            "canonical_pre_window_allowed": True,
        },
        "frontier_policy": {
            "recent_years_default": 3,
            "canonical_pre_window_allowed": True,
            "citation_signal": "field-year-normalized-when-available",
            "citation_source_and_as_of_required": True,
            "salience_is_not_claim_confidence": True,
        },
        "selected_branch": selected_branch,
        "lineage": {"parents": parents},
        "inherited_ids": inherited,
        "context_sources": contexts,
        "primary_artifact": report_name,
        "artifact_files": [*role_files.values()],
        "artifact_roles": role_files,
    }
    if enhanced_contracts:
        manifest["workflow_contracts"] = list(
            WORKFLOW_CONTRACTS_BY_MODE[mode]
        )
    (run_dir / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return run_dir


def load_manifest(run_dir: Path) -> dict[str, object]:
    return json.loads((run_dir / "run-manifest.json").read_text(encoding="utf-8"))


def save_manifest(run_dir: Path, manifest: dict[str, object]) -> None:
    (run_dir / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
