from __future__ import annotations

import os

import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SKILL_DIR / "scripts"), str(SKILL_DIR / "tests")]

from fixture_factory import (  # noqa: E402
    cleanup_work,
    load_manifest,
    make_run,
    reset_work,
    save_manifest,
    workspace_root,
)
from parent_audit import (  # noqa: E402
    MANIFEST_FAILURE_REPAIRS,
    _normalize_source as normalize_parent_source,
    canonical_manifest_repair,
    inspect_parent_for_audit,
)
from rom_contract import (  # noqa: E402
    ContractError,
    load_run_manifest,
    safe_manifest_relpath,
    snapshot_parent_run,
)
from validate_run import _normalize_source_link, validate  # noqa: E402


def set_table_cell(
    path: Path,
    marker: str,
    row_id: str,
    header: str,
    value: str,
) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    marker_line = f"<!-- rom-table: {marker} -->"
    if marker_line not in lines:
        marker_line = f"<!-- rom-section: {marker} -->"
    start = lines.index(marker_line)
    header_index = next(
        index for index in range(start + 1, len(lines)) if lines[index].startswith("|")
    )
    headers = [cell.strip() for cell in lines[header_index].strip().strip("|").split("|")]
    column = headers.index(header)
    for index in range(header_index + 2, len(lines)):
        if not lines[index].startswith("|"):
            break
        cells = [cell.strip() for cell in lines[index].strip().strip("|").split("|")]
        if cells and cells[0] == row_id:
            cells[column] = value
            lines[index] = "| " + " | ".join(cells) + " |"
            path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
            return
    raise AssertionError(f"row {row_id!r} not found in {marker!r}")


def append_table_row(path: Path, marker: str, cells: list[str]) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    marker_lines = (
        f"<!-- rom-table: {marker} -->",
        f"<!-- rom-section: {marker} -->",
    )
    start = next((lines.index(item) for item in marker_lines if item in lines), None)
    if start is None:
        raise AssertionError(f"marker {marker!r} not found")
    header_index = next(
        index for index in range(start + 1, len(lines)) if lines[index].startswith("|")
    )
    headers = [cell.strip() for cell in lines[header_index].strip().strip("|").split("|")]
    if len(cells) != len(headers):
        raise AssertionError(
            f"row for {marker!r} has {len(cells)} cells; expected {len(headers)}"
        )
    insert_at = header_index + 2
    while insert_at < len(lines) and lines[insert_at].startswith("|"):
        insert_at += 1
    lines.insert(insert_at, "| " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def duplicate_table_row(path: Path, marker: str, row_id: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    marker_lines = (
        f"<!-- rom-table: {marker} -->",
        f"<!-- rom-section: {marker} -->",
    )
    start = next((lines.index(item) for item in marker_lines if item in lines), None)
    if start is None:
        raise AssertionError(f"marker {marker!r} not found")
    header_index = next(
        index for index in range(start + 1, len(lines))
        if lines[index].startswith("|")
    )
    for index in range(header_index + 2, len(lines)):
        if not lines[index].startswith("|"):
            break
        cells = [
            cell.strip()
            for cell in lines[index].strip().strip("|").split("|")
        ]
        if cells and cells[0] == row_id:
            lines.insert(index + 1, lines[index])
            path.write_text(
                "\n".join(lines) + "\n", encoding="utf-8", newline="\n"
            )
            return
    raise AssertionError(f"row {row_id!r} not found in {marker!r}")


class ValidatorV2Tests(unittest.TestCase):
    work_name = "validator-v2"

    def setUp(self) -> None:
        self.work = reset_work(self.work_name)
        self.workspace = workspace_root()

    def tearDown(self) -> None:
        cleanup_work(self.work_name)

    def assertValid(self, run_dir: Path) -> None:  # noqa: N802
        report = validate(run_dir, workspace_root=self.workspace)
        self.assertEqual(report.errors, [], "\n".join(report.errors))
        self.assertEqual(report.warnings, [], "\n".join(report.warnings))

    def assertInvalidContains(self, run_dir: Path, fragment: str) -> None:  # noqa: N802
        report = validate(run_dir, workspace_root=self.workspace)
        self.assertTrue(
            any(fragment.lower() in error.lower() for error in report.errors),
            f"Expected {fragment!r} in errors:\n" + "\n".join(report.errors),
        )

    def test_all_four_mode_contracts_pass_and_focus_has_no_landscape_gate(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        runs = [
            make_run(self.work, mode="landscape", run_id="landscape"),
            make_run(self.work, mode="focus", parent=parent, run_id="focus"),
            make_run(
                self.work,
                mode="evidence-audit",
                lens="gray-space-led",
                run_id="evidence",
            ),
            make_run(self.work, mode="run-audit", parent=parent, run_id="run-audit"),
        ]
        for run_dir in runs:
            with self.subTest(mode=load_manifest(run_dir)["run_type"]):
                self.assertValid(run_dir)
        focus_manifest = load_manifest(runs[1])
        self.assertNotIn("breadth_ledger", focus_manifest["artifact_roles"])

    def test_enhanced_workflow_contracts_pass_in_applicable_modes(self) -> None:
        parent = make_run(
            self.work,
            mode="landscape",
            run_id="enhanced-parent",
            enhanced_contracts=True,
        )
        runs = [
            parent,
            make_run(
                self.work,
                mode="focus",
                parent=parent,
                run_id="enhanced-focus",
                enhanced_contracts=True,
            ),
            make_run(
                self.work,
                mode="evidence-audit",
                parent=parent,
                run_id="enhanced-evidence",
                enhanced_contracts=True,
            ),
        ]
        for run_dir in runs:
            with self.subTest(mode=load_manifest(run_dir)["run_type"]):
                self.assertValid(run_dir)

    def test_enhanced_workflow_semantic_gates_fail_closed(self) -> None:
        derived = make_run(
            self.work,
            run_id="enhanced-derived-report",
            enhanced_contracts=True,
        )
        set_table_cell(
            derived / "03_evidence-matrix.md",
            "evidence-records",
            "E-002",
            "Canonical cross-run ref",
            "research-runs/deep-reading/sample-001/view-report.md#evidence=E%2D002",
        )
        self.assertInvalidContains(derived, "derived or unknown file")

        gate_math = make_run(
            self.work,
            run_id="enhanced-gate-math",
            enhanced_contracts=True,
        )
        set_table_cell(
            gate_math / "05_candidate-portfolio.md",
            "opportunity-gates",
            "C-001",
            "Overall: go/conditional-go/defer/no-go",
            "defer",
        )
        self.assertInvalidContains(gate_math, "Overall must be 'go'")

        zero_hit = make_run(
            self.work,
            run_id="enhanced-zero-hit",
            enhanced_contracts=True,
        )
        set_table_cell(
            zero_hit / "02_search-log.md",
            "coverage-audit",
            "direct-neighbor",
            "Coverage status: covered/thin/query-failed/out-of-scope",
            "covered",
        )
        self.assertInvalidContains(zero_hit, "cannot be covered")

        conditionless = make_run(
            self.work,
            run_id="enhanced-conditionless",
            enhanced_contracts=True,
        )
        set_table_cell(
            conditionless / "03_evidence-matrix.md",
            "contradictions",
            "B-001",
            "Condition delta",
            "TBD",
        )
        self.assertInvalidContains(conditionless, "must state the regime")

        slow = make_run(
            self.work,
            run_id="enhanced-slow-pilot",
            enhanced_contracts=True,
        )
        set_table_cell(
            slow / "05_candidate-portfolio.md",
            "route-fast-pilots",
            "C-001",
            "Horizon days: 1-14",
            "15",
        )
        self.assertInvalidContains(slow, "integer from 1 to 14")

        same_hypothesis = make_run(
            self.work,
            run_id="enhanced-same-hypothesis",
            enhanced_contracts=True,
        )
        set_table_cell(
            same_hypothesis / "05_candidate-portfolio.md",
            "route-fast-pilots",
            "C-001",
            "Hypothesis B",
            "independent field control changes the intrinsic state timescale",
        )
        self.assertInvalidContains(same_hypothesis, "distinct hypotheses")

    def test_schema_dispatch_accepts_only_exact_supported_versions(self) -> None:
        for index, version in enumerate(("1.3", "2.1", "3.0", "99.0", "banana", "1", "1.-1")):
            with self.subTest(version=version):
                run_dir = make_run(self.work, run_id=f"bad-schema-{index}")
                manifest = load_manifest(run_dir)
                manifest["schema_version"] = version
                save_manifest(run_dir, manifest)
                report = validate(run_dir, workspace_root=self.workspace)
                self.assertTrue(report.errors)
                self.assertTrue(
                    any("schema" in error.lower() for error in report.errors),
                    report.errors,
                )

    def test_manifest_routing_dates_policy_and_selected_branch_are_enforced(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        mutations = {
            "mode-mismatch": lambda m: m.update({"task_mode": "focus"}),
            "bad-requested": lambda m: m["routing"].update({"requested": "magic"}),
            "empty-reason": lambda m: m["routing"].update({"reason": []}),
            "bad-confidence": lambda m: m["routing"].update({"confidence": "certain"}),
            "bad-created": lambda m: m.update({"created_at": "2026-07-31"}),
            "bad-window": lambda m: m["evidence_window"].update({"start": "2027-01-01"}),
            "bad-policy": lambda m: m.update({"parent_mutation_policy": "in-place"}),
            "custom-without-notes": lambda m: m.update(
                {"primary_domain_lens": "custom", "domain_lens_notes": None}
            ),
            "malformed-secondary-lens": lambda m: m.update(
                {"secondary_domain_lenses": [["semiconductor-device"]]}
            ),
        }
        for name, mutate in mutations.items():
            with self.subTest(case=name):
                run_dir = make_run(self.work, run_id=name)
                manifest = load_manifest(run_dir)
                mutate(manifest)
                save_manifest(run_dir, manifest)
                self.assertTrue(validate(run_dir, workspace_root=self.workspace).errors)

        focus = make_run(self.work, mode="focus", parent=parent, run_id="bad-branch")
        manifest = load_manifest(focus)
        manifest["selected_branch"] = {"id": "BR-999", "label": None, "source": "parent"}
        save_manifest(focus, manifest)
        self.assertInvalidContains(focus, "selected_branch")

    def test_manifest_paths_reject_traversal_and_absolute_paths(self) -> None:
        for name, bad_path in (
            ("traversal", "../escape.md"),
            ("absolute", "C:/escape.md"),
            ("drive-relative", "C:escape.md"),
        ):
            with self.subTest(case=name):
                run_dir = make_run(self.work, run_id=name)
                manifest = load_manifest(run_dir)
                manifest["artifact_roles"]["intake"] = bad_path
                save_manifest(run_dir, manifest)
                self.assertInvalidContains(run_dir, "artifact role intake")

    def test_parent_hash_map_hashes_and_inherited_id_types_are_enforced(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        focus = make_run(self.work, mode="focus", parent=parent, run_id="focus")
        manifest = load_manifest(focus)
        manifest["lineage"]["parents"][0]["source_artifact_sha256"].pop("00_intake.md")
        manifest["inherited_ids"]["claims"] = ["E-001"]
        save_manifest(focus, manifest)
        report = validate(focus, workspace_root=self.workspace)
        self.assertTrue(any("cover all" in error for error in report.errors), report.errors)
        self.assertTrue(any("invalid ID type" in error for error in report.errors), report.errors)

    def test_parent_ids_in_comments_fences_or_plain_references_are_not_inheritable(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        parent_manifest = load_manifest(parent)
        report_path = parent / parent_manifest["primary_artifact"]
        report_path.write_text(
            report_path.read_text(encoding="utf-8")
            + "\n<!-- BR-999 -->\n```text\nBR-999\n```\nOrdinary reference BR-999.\n",
            encoding="utf-8",
            newline="\n",
        )
        focus = make_run(self.work, mode="focus", parent=parent, run_id="focus")
        manifest = load_manifest(focus)
        manifest["selected_branch"] = {"id": "BR-999", "label": None, "source": "parent"}
        save_manifest(focus, manifest)
        self.assertInvalidContains(focus, "selected_branch")

    def test_markers_inside_fences_and_html_comments_do_not_count(self) -> None:
        run_dir = make_run(self.work, run_id="fake-markers")
        red_path = run_dir / "06_red-team.md"
        red_path.write_text(
            "# Fake red team\n\n```md\n<!-- rom-table: attack-register -->\n"
            "| Attack ID | Target claim/route | Attack surface | Strongest objection | Evidence IDs or test | Severity | Required repair or discriminating test | Verdict | Decision ID | Status |\n"
            "|---|---|---|---|---|---|---|---|---|---|\n"
            "| A-999 | C-001 | mechanism evidence capability baseline | objection | E-001 | high | test | Revise | D-001 | open |\n"
            "```\n\n<!-- <!-- rom-table: baseline-ladder --> -->\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(run_dir, "missing rom-table marker attack-register")

    def test_attack_register_resists_single_row_keyword_stuffing(self) -> None:
        run_dir = make_run(self.work, run_id="keyword-stuffing")
        path = run_dir / "06_red-team.md"
        text = path.read_text(encoding="utf-8")
        start = text.index("<!-- rom-table: attack-register -->")
        end = text.index("<!-- rom-table: baseline-ladder -->")
        stuffed = """<!-- rom-table: attack-register -->
## Attack Register
| Attack ID | Target claim/route | Attack surface | Strongest objection | Evidence IDs or test | Severity | Required repair or discriminating test | Verdict | Decision ID | Status |
|---|---|---|---|---|---|---|---|---|---|
| A-001 | C-001 | problem mechanism evidence open-position capability cross-scale baseline bio | all keywords | E-001 | high | one generic test | Keep | D-001 | closed |

"""
        path.write_text(text[:start] + stuffed + text[end:], encoding="utf-8", newline="\n")
        self.assertInvalidContains(run_dir, "at least eight structured attack rows")
        self.assertInvalidContains(run_dir, "exactly the eight registered attack surfaces")

    def test_evidence_enums_and_confidence_hard_caps(self) -> None:
        cases = {
            "source-role": ("canonical-anchor", "famous-paper", "invalid Source role"),
            "directness": ("| direct | review plus", "| suggestive | review plus", "invalid Directness"),
            "context-cap": ("full-context-verified", "metadata-only", "Low cap"),
            "indirect-cap": ("| direct |", "| indirect |", "Indirect-only"),
            "claim-type": ("| existence |", "| vibes |", "invalid claim type"),
        }
        for name, (old, new, expected) in cases.items():
            with self.subTest(case=name):
                run_dir = make_run(self.work, run_id=f"evidence-{name}")
                path = run_dir / "03_evidence-matrix.md"
                text = path.read_text(encoding="utf-8")
                self.assertIn(old, text)
                path.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
                self.assertInvalidContains(run_dir, expected)

        conflict = make_run(self.work, run_id="unresolved-conflict")
        path = conflict / "03_evidence-matrix.md"
        set_table_cell(path, "claim-confidence", "B-001", "Consistency/conflict status", "type=direct-conflict; status=unresolved; basis=matched direct tests")
        set_table_cell(path, "evidence-records", "E-003", "Stance", "contradicts")
        set_table_cell(path, "contradictions", "B-001", "Tension type: direct-conflict/evidence-gap/condition-difference", "direct-conflict")
        set_table_cell(path, "contradictions", "B-001", "Adjudication: support-dominant/limit-dominant/condition-split/unresolved", "unresolved")
        self.assertInvalidContains(conflict, "unresolved-conflict cap")

        unsupported = make_run(self.work, run_id="unsupported-moderate")
        matrix = unsupported / "03_evidence-matrix.md"
        set_table_cell(
            matrix, "claim-confidence", "B-001", "Supporting Evidence IDs", "none"
        )
        set_table_cell(
            matrix,
            "claim-confidence",
            "B-001",
            "Confidence: High/Moderate/Low/Insufficient",
            "Moderate",
        )
        set_table_cell(
            matrix,
            "claim-confidence",
            "B-001",
            "Active cap codes",
            "single-chain-broad-claim",
        )
        self.assertInvalidContains(unsupported, "no valid supporting evidence")

        epistemic = make_run(self.work, run_id="invalid-epistemic-label")
        set_table_cell(
            epistemic / "03_evidence-matrix.md",
            "atomic-claims",
            "B-001",
            "Epistemic label",
            "Fact",
        )
        self.assertInvalidContains(epistemic, "invalid Epistemic label")

        capability = make_run(self.work, run_id="invalid-capability-state")
        set_table_cell(
            capability / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Epistemic state: Observed/Reported/Assumed/Unknown",
            "Learning",
        )
        self.assertInvalidContains(capability, "invalid epistemic state")

        readiness = make_run(self.work, run_id="invalid-capability-readiness")
        set_table_cell(
            readiness / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Readiness: Ready/Adaptable/Collaborator/Unavailable",
            "AlmostReady",
        )
        self.assertInvalidContains(readiness, "invalid readiness")

        inflated = make_run(self.work, run_id="inflated-unknown-capability")
        set_table_cell(
            inflated / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Epistemic state: Observed/Reported/Assumed/Unknown",
            "Unknown",
        )
        set_table_cell(
            inflated / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Readiness: Ready/Adaptable/Collaborator/Unavailable",
            "Ready",
        )
        self.assertInvalidContains(inflated, "cannot be Ready")

        unsupported_observed = make_run(
            self.work, run_id="unsupported-observed-capability"
        )
        set_table_cell(
            unsupported_observed / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Readiness: Ready/Adaptable/Collaborator/Unavailable",
            "Ready",
        )
        set_table_cell(
            unsupported_observed / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Source or evidence",
            "not yet verified",
        )
        self.assertInvalidContains(
            unsupported_observed,
            "requires a non-uncertain Source or evidence basis",
        )

        unsupported_reported = make_run(
            self.work, run_id="unsupported-reported-capability"
        )
        set_table_cell(
            unsupported_reported / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Epistemic state: Observed/Reported/Assumed/Unknown",
            "Reported",
        )
        set_table_cell(
            unsupported_reported / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Source or evidence",
            "not yet verified",
        )
        self.assertInvalidContains(
            unsupported_reported,
            "requires a non-uncertain Source or evidence basis",
        )

    def test_confidence_evidence_must_link_the_claim_with_semantic_stance(self) -> None:
        wrong_stance = make_run(self.work, run_id="support-wrong-stance")
        set_table_cell(
            wrong_stance / "03_evidence-matrix.md",
            "evidence-records",
            "E-001",
            "Stance",
            "contradicts",
        )
        self.assertInvalidContains(
            wrong_stance, "invalid supporting evidence association/stance"
        )

        unrelated = make_run(self.work, run_id="support-unrelated-claim")
        set_table_cell(
            unrelated / "03_evidence-matrix.md",
            "evidence-records",
            "E-001",
            "Claim IDs",
            "M-001,S-001,CL-001",
        )
        self.assertInvalidContains(
            unrelated, "invalid supporting evidence association/stance"
        )

        invalid_enum = make_run(self.work, run_id="invalid-stance-enum")
        set_table_cell(
            invalid_enum / "03_evidence-matrix.md",
            "evidence-records",
            "E-001",
            "Stance",
            "endorses",
        )
        self.assertInvalidContains(invalid_enum, "invalid Stance")

        mixed_only_support = make_run(self.work, run_id="mixed-only-support")
        set_table_cell(
            mixed_only_support / "03_evidence-matrix.md",
            "evidence-records",
            "E-001",
            "Stance",
            "mixed",
        )
        self.assertInvalidContains(
            mixed_only_support,
            "mixed supporting evidence omitted from limiting IDs",
        )

    def test_duplicate_claim_projection_rows_are_rejected(self) -> None:
        landscape = make_run(self.work, run_id="duplicate-claim-confidence")
        duplicate_table_row(
            landscape / "03_evidence-matrix.md",
            "claim-confidence",
            "B-001",
        )
        self.assertInvalidContains(
            landscape, "Claim-confidence contains duplicate Claim IDs"
        )

        cases = (
            ("claim-register", "claim_register"),
            ("claim-confidence", "evidence_matrix"),
            ("confidence-assessment", "confidence_assessment"),
            ("allowed-wording", "confidence_assessment"),
            ("claim-verdicts", "reader_report"),
        )
        for marker, role in cases:
            with self.subTest(marker=marker):
                audit = make_run(
                    self.work,
                    mode="evidence-audit",
                    run_id=f"duplicate-audit-{marker}",
                )
                manifest = load_manifest(audit)
                target = (
                    audit / manifest["primary_artifact"]
                    if role == "reader_report"
                    else audit / manifest["artifact_roles"][role]
                )
                duplicate_table_row(target, marker, "B-001")
                self.assertInvalidContains(audit, "exactly once")

    def test_gray_zero_hit_cannot_become_global_novelty_claim(self) -> None:
        run_dir = make_run(
            self.work, lens="gray-space-led", run_id="gray-zero-hit"
        )
        path = run_dir / "02_search-log.md"
        text = path.read_text(encoding="utf-8").replace(
            "bounded sparse evidence; not a novelty claim",
            "zero proves this interface is completely unexplored and first ever",
        )
        path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(run_dir, "unbounded novelty")

    def test_reader_reference_ranges_bracket_refs_duplicate_numbers_and_doi_closure(self) -> None:
        ranged = make_run(self.work, run_id="ranged-citations")
        manifest = load_manifest(ranged)
        report_path = ranged / manifest["primary_artifact"]
        text = report_path.read_text(encoding="utf-8").replace(
            "[1], [2], and [3]", "[1-3]"
        )
        report_path.write_text(text, encoding="utf-8", newline="\n")
        self.assertValid(ranged)

        duplicate = make_run(self.work, run_id="duplicate-citation")
        manifest = load_manifest(duplicate)
        report_path = duplicate / manifest["primary_artifact"]
        text = report_path.read_text(encoding="utf-8").replace("2. Beta", "1. Beta")
        report_path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(duplicate, "duplicate number")

        mismatch = make_run(self.work, run_id="doi-mismatch")
        manifest = load_manifest(mismatch)
        report_path = mismatch / manifest["primary_artifact"]
        text = report_path.read_text(encoding="utf-8").replace(
            "https://doi.org/10.1234/rom.001", "https://doi.org/10.1234/wrong"
        )
        report_path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(mismatch, "does not match E-001")

        missing_entry = make_run(self.work, run_id="missing-reference-entry")
        manifest = load_manifest(missing_entry)
        report_path = missing_entry / manifest["primary_artifact"]
        report_path.write_text(
            report_path.read_text(encoding="utf-8").replace(
                "bounded state/readout interface [1]",
                "bounded state/readout interface [1] and unsupported reference [99]",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(missing_entry, "missing reference number")

        orphan_mapping = make_run(self.work, run_id="orphan-reader-ref")
        set_table_cell(
            orphan_mapping / "03_evidence-matrix.md",
            "evidence-records",
            "E-003",
            "Reader ref",
            "99",
        )
        self.assertInvalidContains(
            orphan_mapping, "no reader reference entry: 99"
        )

    def test_cross_artifact_dangling_id_and_nonkeep_report_propagation_fail(self) -> None:
        for namespace, identifier in (
            ("evidence", "E-999"),
            ("claim", "B-999"),
            ("query", "Q-999"),
            ("candidate", "C-999"),
            ("decision", "D-999"),
        ):
            with self.subTest(dangling_namespace=namespace):
                dangling = make_run(
                    self.work, run_id=f"dangling-{namespace}"
                )
                path = dangling / "07_decision-log.md"
                path.write_text(
                    path.read_text(encoding="utf-8")
                    + f"\nVisible unsupported reference {identifier}.\n",
                    encoding="utf-8",
                    newline="\n",
                )
                self.assertInvalidContains(dangling, "Dangling cross-artifact IDs")

        declared_context = make_run(
            self.work, mode="evidence-audit", run_id="declared-context-id"
        )
        context_log = declared_context / "07_decision-log.md"
        context_log.write_text(
            context_log.read_text(encoding="utf-8")
            + "\nDeclared read-only input CTX-001.\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertValid(declared_context)

        undeclared_context = make_run(
            self.work, mode="evidence-audit", run_id="undeclared-context-id"
        )
        context_log = undeclared_context / "07_decision-log.md"
        context_log.write_text(
            context_log.read_text(encoding="utf-8")
            + "\nUndeclared read-only input CTX-999.\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(
            undeclared_context, "Dangling cross-artifact IDs"
        )

        propagation = make_run(self.work, run_id="missing-propagation")
        manifest = load_manifest(propagation)
        report_path = propagation / manifest["primary_artifact"]
        set_table_cell(
            report_path,
            "red-team-impact",
            "A-002",
            "Verdict",
            "Keep",
        )
        report_path.write_text(
            report_path.read_text(encoding="utf-8")
            + "\nC-001 Revise D-002 appears here only as unstructured prose.\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(
            propagation,
            "red-team-impact projection must exactly match every attack-register row and field",
        )

    def test_red_team_full_reader_projection_and_binding_decision_are_exact(self) -> None:
        objection = make_run(self.work, run_id="reader-objection-drift")
        manifest = load_manifest(objection)
        set_table_cell(
            objection / manifest["primary_artifact"],
            "red-team-impact",
            "A-002",
            "Strongest objection",
            "A softened objection that no longer matches the audit",
        )
        self.assertInvalidContains(
            objection,
            "red-team-impact projection must exactly match every attack-register row and field",
        )

        stale = make_run(self.work, run_id="stale-route-disposition")
        manifest = load_manifest(stale)
        set_table_cell(
            stale / manifest["primary_artifact"],
            "decision-summary",
            "low",
            "Disposition",
            "Keep",
        )
        self.assertInvalidContains(
            stale,
            "understates or mislinks the strongest red-team verdict",
        )

    def test_clean_all_keep_red_team_is_allowed(self) -> None:
        run_dir = make_run(self.work, run_id="all-keep")
        red_team = run_dir / "06_red-team.md"
        decision_log = run_dir / "07_decision-log.md"
        manifest = load_manifest(run_dir)
        reader = run_dir / manifest["primary_artifact"]

        set_table_cell(red_team, "attack-register", "A-002", "Severity: low/medium/high/blocking", "low")
        set_table_cell(red_team, "attack-register", "A-002", "Verdict: Keep/Downgrade/Revise/Kill", "Keep")
        set_table_cell(red_team, "attack-register", "A-002", "Status", "closed")
        set_table_cell(decision_log, "decisions", "D-002", "Status: Keep/Downgrade/Revise/Kill", "Keep")
        set_table_cell(reader, "red-team-impact", "A-002", "Severity", "low")
        set_table_cell(reader, "red-team-impact", "A-002", "Verdict", "Keep")
        set_table_cell(reader, "red-team-impact", "A-002", "Status", "closed")
        set_table_cell(reader, "decision-summary", "low", "Disposition", "Keep")

        self.assertValid(run_dir)

    def test_claim_level_attack_must_change_its_affected_route_decision(self) -> None:
        run_dir = make_run(self.work, run_id="claim-level-attack")
        manifest = load_manifest(run_dir)
        set_table_cell(
            run_dir / "06_red-team.md",
            "attack-register",
            "A-001",
            "Target claim/route",
            "B-001",
        )
        set_table_cell(
            run_dir / "06_red-team.md",
            "attack-register",
            "A-001",
            "Verdict: Keep/Downgrade/Revise/Kill",
            "Kill",
        )
        set_table_cell(
            run_dir / "07_decision-log.md",
            "decisions",
            "D-001",
            "Target ID",
            "B-001",
        )
        set_table_cell(
            run_dir / "07_decision-log.md",
            "decisions",
            "D-001",
            "Status: Keep/Downgrade/Revise/Kill",
            "Kill",
        )
        set_table_cell(
            run_dir / manifest["primary_artifact"],
            "red-team-impact",
            "A-001",
            "Target ID",
            "B-001",
        )
        set_table_cell(
            run_dir / manifest["primary_artifact"],
            "red-team-impact",
            "A-001",
            "Verdict",
            "Kill",
        )
        self.assertInvalidContains(
            run_dir,
            "understates or mislinks the strongest red-team verdict kill",
        )
        set_table_cell(
            run_dir / manifest["primary_artifact"],
            "decision-summary",
            "low",
            "Disposition",
            "Kill",
        )
        set_table_cell(
            run_dir / manifest["primary_artifact"],
            "decision-summary",
            "low",
            "Decision ID",
            "D-001",
        )
        self.assertValid(run_dir)

    def test_short_attack_row_reports_structure_error_without_crashing(self) -> None:
        run_dir = make_run(self.work, run_id="short-attack-row")
        path = run_dir / "06_red-team.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        row_index = next(
            index for index, line in enumerate(lines) if line.startswith("| A-001 |")
        )
        lines[row_index] = "| A-001 |"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

        try:
            report = validate(run_dir, workspace_root=self.workspace)
        except Exception as exc:  # pragma: no cover - regression must return a Report
            self.fail(f"Malformed table input escaped validation as {type(exc).__name__}: {exc}")
        self.assertTrue(report.errors)
        self.assertTrue(
            any(
                "row width" in error.lower() or "cells; expected" in error.lower()
                for error in report.errors
            ),
            report.errors,
        )

    def test_landscape_rejects_non_route_affected_decision_target(self) -> None:
        run_dir = make_run(self.work, run_id="fake-affected-decision-target")
        manifest = load_manifest(run_dir)
        red_team = run_dir / "06_red-team.md"
        decisions = run_dir / "07_decision-log.md"
        reader = run_dir / manifest["primary_artifact"]

        set_table_cell(red_team, "attack-register", "A-001", "Target claim/route", "B-001")
        set_table_cell(
            red_team,
            "attack-register",
            "A-001",
            "Verdict: Keep/Downgrade/Revise/Kill",
            "Kill",
        )
        set_table_cell(decisions, "decisions", "D-001", "Target ID", "B-001")
        set_table_cell(
            decisions,
            "decisions",
            "D-001",
            "Affected decision target IDs",
            "D-001",
        )
        set_table_cell(
            decisions,
            "decisions",
            "D-001",
            "Status: Keep/Downgrade/Revise/Kill",
            "Kill",
        )
        set_table_cell(reader, "red-team-impact", "A-001", "Target ID", "B-001")
        set_table_cell(reader, "red-team-impact", "A-001", "Verdict", "Kill")
        append_table_row(
            reader,
            "decision-summary",
            [
                "audit-shadow",
                "D-001",
                "not a research route",
                "attack is hidden from the real route",
                "no platform value",
                "Kill",
                "D-001",
            ],
        )

        report = validate(run_dir, workspace_root=self.workspace)
        self.assertTrue(report.errors)
        self.assertTrue(
            any("affected" in error.lower() and "D-001" in error for error in report.errors),
            report.errors,
        )

    def test_bio_attack_a008_is_bound_to_bio_surface(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="bio-surface-parent")
        run_dir = make_run(
            self.work,
            mode="focus",
            parent=parent,
            bio=True,
            run_id="bio-surface-swap",
        )
        manifest = load_manifest(run_dir)
        for path, marker in (
            (run_dir / "06_red-team.md", "attack-register"),
            (run_dir / manifest["primary_artifact"], "red-team-impact"),
        ):
            set_table_cell(path, marker, "A-007", "Attack surface", "bio-inspired-translation")
            set_table_cell(path, marker, "A-008", "Attack surface", "baseline-system-cost")

        report = validate(run_dir, workspace_root=self.workspace)
        self.assertTrue(report.errors)
        self.assertTrue(
            any("A-008" in error and "surface" in error.lower() for error in report.errors),
            report.errors,
        )

        nonbio = make_run(
            self.work, mode="landscape", run_id="nonbio-surface-swap"
        )
        nonbio_manifest = load_manifest(nonbio)
        for path, marker in (
            (nonbio / "06_red-team.md", "attack-register"),
            (nonbio / nonbio_manifest["primary_artifact"], "red-team-impact"),
        ):
            set_table_cell(path, marker, "A-007", "Attack surface", "bio-inspired-translation")
            set_table_cell(path, marker, "A-008", "Attack surface", "baseline-system-cost")
        report = validate(nonbio, workspace_root=self.workspace)
        self.assertTrue(
            any("A-008" in error and "surface" in error.lower() for error in report.errors),
            report.errors,
        )

        nonbio_alignment = make_run(
            self.work, mode="landscape", run_id="nonbio-a008-alignment"
        )
        set_table_cell(
            nonbio_alignment / "06_red-team.md",
            "bio-inspired-audit",
            "C-001",
            "Target",
            "C-002",
        )
        self.assertInvalidContains(
            nonbio_alignment,
            "red_team bio-inspired audit must match A-008 target",
        )

    def test_a008_match_and_complete_bio_chain_must_be_the_same_row(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="bio-row-parent")
        run_dir = make_run(
            self.work,
            mode="focus",
            parent=parent,
            bio=True,
            run_id="bio-detached-a008-row",
        )
        manifest = load_manifest(run_dir)
        detached_row = [
            "C-001",
            "not applicable: detached A-008 row",
            "not applicable: detached principle",
            "not applicable: detached operator",
            "not applicable: detached algorithm",
            "not applicable: detached primitive",
            "not applicable: detached scientific question",
            "not applicable: detached baseline",
            "not applicable: detached ablation",
            "not applicable: detached gain boundary",
            "Revise",
            "D-008",
        ]
        path = run_dir / "06_red-team.md"
        set_table_cell(path, "bio-inspired-audit", "C-001", "Verdict", "Keep")
        set_table_cell(path, "bio-inspired-audit", "C-001", "Decision ID", "D-001")
        append_table_row(path, "bio-inspired-audit", detached_row)

        report = validate(run_dir, workspace_root=self.workspace)
        self.assertTrue(report.errors)
        self.assertTrue(
            any("A-008" in error and "bio" in error.lower() for error in report.errors),
            report.errors,
        )

    def test_visible_bio_claim_triggers_gate_even_when_manifest_is_generic(self) -> None:
        run_dir = make_run(self.work, run_id="visible-bio-claim")
        manifest = load_manifest(run_dir)
        reader = run_dir / manifest["primary_artifact"]
        text = reader.read_text(encoding="utf-8")
        marker = "<!-- rom-section: background-question -->"
        self.assertIn(marker, text)
        reader.write_text(
            text.replace(
                marker,
                marker
                + "\nThis bio-inspired neuromorphic route claims principle-specific "
                + "continual-learning value.",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )

        report = validate(run_dir, workspace_root=self.workspace)
        self.assertTrue(report.errors)
        self.assertTrue(
            any(
                "bio" in error.lower()
                and ("translation" in error.lower() or "n/a" in error.lower())
                for error in report.errors
            ),
            report.errors,
        )

    def test_common_bio_claim_synonyms_trigger_gate_with_generic_manifest(self) -> None:
        phrases = (
            "biologically inspired",
            "neuron-inspired",
            "synapse-inspired",
            "brain-like",
            "biological superiority",
            "类脑",
            "Neuronal computation is superior to conventional hardware algorithms.",
            "Synaptic plasticity provides intrinsic continual-learning capability.",
            "Cortical computation outperforms the same-budget digital baseline.",
            "Brain computation is inherently more efficient than hardware learning.",
            "biology-inspired",
            "Astrocyte-inspired homeostatic plasticity regulates adaptation.",
            "Dendritic computation provides a nonlinear hardware primitive.",
            "Axonal delay learning improves temporal credit assignment.",
            "Metaplasticity stabilizes continual learning.",
            "neuromorphic computing",
            "artificial synapse hardware",
            "synapse-mimicking device",
            "neuron-mimicking circuit",
            "brain-mimicking architecture",
            "人工突触器件",
            "人工神经元电路",
            "neuro-inspired adaptation",
            "neural-inspired learning",
            "immune-inspired control",
            "retina-inspired sensing",
            "nature-inspired optimization",
            "bio‑inspired hardware",
            "bio–inspired hardware",
            "neuron‑inspired circuit",
            "neuro inspired mechanism",
        )
        for index, phrase in enumerate(phrases):
            with self.subTest(phrase=phrase):
                run_dir = make_run(
                    self.work, run_id=f"bio-synonym-{index}"
                )
                manifest = load_manifest(run_dir)
                reader = run_dir / manifest["primary_artifact"]
                text = reader.read_text(encoding="utf-8")
                marker = "<!-- rom-section: background-question -->"
                reader.write_text(
                    text.replace(
                        marker,
                        marker
                        + f"\nThis {phrase} route claims principle-specific value.",
                        1,
                    ),
                    encoding="utf-8",
                    newline="\n",
                )
                self.assertInvalidContains(
                    run_dir,
                    "requires bio/neuromorphic manifest metadata",
                )

        retrieval_only = make_run(
            self.work, mode="landscape", run_id="bio-retrieval-only-mention"
        )
        search_log = retrieval_only / "02_search-log.md"
        text = search_log.read_text(encoding="utf-8")
        marker = "<!-- rom-section: search-policy -->"
        self.assertIn(marker, text)
        search_log.write_text(
            text.replace(
                marker,
                marker + "\nRejected adjacent terminology: synaptic and cortical analogies.",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )
        set_table_cell(
            retrieval_only / "00_intake.md",
            "capability-passport",
            "CAP-001",
            "Capability module",
            "reported synaptic-device characterization capability",
        )
        self.assertValid(retrieval_only)

        audit_parent = make_run(
            self.work, mode="landscape", run_id="bio-capability-audit-parent"
        )
        capability_audit = make_run(
            self.work,
            mode="run-audit",
            parent=audit_parent,
            run_id="bio-capability-audit-mention",
        )
        capability_text = "reported synaptic-device characterization capability"
        set_table_cell(
            capability_audit / "04_reasoning-audit.md",
            "cross-scale-audit",
            "B-001",
            "Capability state",
            capability_text,
        )
        audit_manifest = load_manifest(capability_audit)
        audit_reader = capability_audit / audit_manifest["primary_artifact"]
        reader_text = audit_reader.read_text(encoding="utf-8")
        marker = "<!-- rom-section: capability-cross-scale -->"
        self.assertIn(marker, reader_text)
        audit_reader.write_text(
            reader_text.replace(marker, marker + "\n" + capability_text, 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assertValid(capability_audit)

        metadata_capability = make_run(
            self.work,
            mode="landscape",
            run_id="bio-capability-only-request",
            routing_request=(
                "Lab neuromorphic-device characterization capability is "
                "capability context only, not a scientific premise."
            ),
        )
        self.assertValid(metadata_capability)

        custom_capability_notes = "\n".join(
            [
                "Decision object: choose a bounded active thermal-control route",
                "State variables: heater power, temperature, and heat flux",
                "Persistent bottleneck: convection-limited stability in the target regime",
                "Causal chain: heater power -> temperature field -> heat flux",
                "Alternative explanations: contact resistance, convection, and sensor drift",
                "Budgets and constraints: energy, latency, area, and uncertainty",
                "Baseline ladder: passive, controlled, optimized, and system references",
                "Validation hierarchy: simulation -> coupon -> component -> system",
                (
                    "Capability interface: neuromorphic-device characterization "
                    "capability context only, not a scientific premise"
                ),
                "Decisive test: randomized heater control with a five-sigma threshold",
            ]
        )
        custom_capability = make_run(
            self.work,
            mode="landscape",
            run_id="bio-custom-capability-only",
        )
        custom_manifest = load_manifest(custom_capability)
        custom_manifest.update(
            {
                "primary_domain_lens": "custom",
                "secondary_domain_lenses": [],
                "domain_lens_notes": custom_capability_notes,
            }
        )
        save_manifest(custom_capability, custom_manifest)
        self.assertValid(custom_capability)

        custom_premise = make_run(
            self.work,
            mode="landscape",
            run_id="bio-custom-real-premise",
        )
        premise_manifest = load_manifest(custom_premise)
        premise_manifest.update(
            {
                "primary_domain_lens": "custom",
                "secondary_domain_lenses": [],
                "domain_lens_notes": custom_capability_notes.replace(
                    "choose a bounded active thermal-control route",
                    "choose a neuro-inspired adaptive route",
                ),
            }
        )
        save_manifest(custom_premise, premise_manifest)
        self.assertInvalidContains(
            custom_premise,
            "Bio translation chain must be non-N/A",
        )

    def test_bio_translation_cannot_be_satisfied_by_wrong_role_decoy(self) -> None:
        parent = make_run(
            self.work,
            mode="landscape",
            run_id="bio-translation-owner-parent",
        )
        run_dir = make_run(
            self.work,
            mode="focus",
            parent=parent,
            bio=True,
            run_id="bio-translation-owner-decoy",
        )
        owner = run_dir / "04_claim-mechanism-map.md"
        owner_text = owner.read_text(encoding="utf-8")
        marker = "<!-- rom-section: bio-inspired-translation -->"
        start = owner_text.index(marker)
        tail = owner_text[start:]
        next_marker = tail.find("<!-- rom-", len(marker))
        decoy = tail if next_marker < 0 else tail[:next_marker]
        intake = run_dir / "00_intake.md"
        intake.write_text(
            intake.read_text(encoding="utf-8") + "\n" + decoy.rstrip() + "\n",
            encoding="utf-8",
            newline="\n",
        )
        set_table_cell(
            owner,
            "bio-inspired-translation",
            "adaptive forgetting under nonstationarity",
            "Biological observation",
            "not applicable: omitted from authoritative owner",
        )
        self.assertInvalidContains(
            run_dir, "translation chain must be non-N/A in claim_mechanism_map"
        )

    def test_evidence_audit_rejects_coherent_decision_id_claim_impersonation(self) -> None:
        run_dir = make_run(
            self.work,
            mode="evidence-audit",
            run_id="evidence-fake-decision-claim",
        )
        set_table_cell(
            run_dir / "01_claim-register.md",
            "claim-register",
            "B-001",
            "Claim ID",
            "D-001",
        )
        matrix = run_dir / "03_evidence-matrix.md"
        set_table_cell(
            matrix,
            "atomic-claims",
            "B-001",
            "Decision critical: yes/no",
            "no",
        )
        set_table_cell(matrix, "claim-confidence", "B-001", "Claim ID", "D-001")
        set_table_cell(
            matrix,
            "claim-confidence",
            "D-001",
            "Supporting Evidence IDs",
            "not applicable: none",
        )
        set_table_cell(
            matrix,
            "claim-confidence",
            "D-001",
            "Limiting Evidence IDs",
            "not applicable: none",
        )
        set_table_cell(
            matrix,
            "claim-confidence",
            "D-001",
            "Confidence: High/Moderate/Low/Insufficient",
            "Insufficient",
        )
        assessment = run_dir / "04_confidence-assessment.md"
        set_table_cell(
            assessment,
            "confidence-assessment",
            "B-001",
            "Claim ID",
            "D-001",
        )
        set_table_cell(
            assessment,
            "confidence-assessment",
            "D-001",
            "Supporting Evidence IDs",
            "not applicable: none",
        )
        set_table_cell(
            assessment,
            "confidence-assessment",
            "D-001",
            "Limiting Evidence IDs",
            "not applicable: none",
        )
        set_table_cell(
            assessment,
            "confidence-assessment",
            "D-001",
            "Confidence: High/Moderate/Low/Insufficient",
            "Insufficient",
        )
        set_table_cell(
            assessment,
            "allowed-wording",
            "B-001",
            "Claim ID",
            "D-001",
        )
        set_table_cell(
            run_dir / "05_gap-plan.md",
            "evidence-gaps",
            "G-001",
            "Claim ID",
            "D-001",
        )
        manifest = load_manifest(run_dir)
        reader = run_dir / manifest["primary_artifact"]
        for path in (
            run_dir / "06_red-team.md",
            run_dir / "07_decision-log.md",
            reader,
        ):
            path.write_text(
                path.read_text(encoding="utf-8").replace("B-001", "D-001"),
                encoding="utf-8",
                newline="\n",
            )
        set_table_cell(
            reader,
            "claim-verdicts",
            "D-001",
            "Confidence",
            "Insufficient",
        )

        report = validate(run_dir, workspace_root=self.workspace)
        self.assertTrue(report.errors)
        self.assertTrue(
            any(
                "evidence-audit main targets have invalid ID types: D-001"
                in error
                for error in report.errors
            ),
            report.errors,
        )
        self.assertTrue(
            any(
                "outside the authoritative claim/parent source" in error
                and "D-001" in error
                for error in report.errors
            ),
            report.errors,
        )

    def test_evidence_audit_cannot_switch_away_from_declared_target_claims(self) -> None:
        run_dir = make_run(
            self.work,
            mode="evidence-audit",
            run_id="evidence-declared-target-switch",
        )
        for path in run_dir.glob("*.md"):
            if path.name == "00_audit-scope.md":
                continue
            path.write_text(
                path.read_text(encoding="utf-8").replace("B-001", "M-001"),
                encoding="utf-8",
                newline="\n",
            )
        scope = run_dir / "00_audit-scope.md"
        scope.write_text(
            scope.read_text(encoding="utf-8")
            + "\n\n<!-- rom-table: claim-register -->\n"
            + "## Wrong-role decoy\n\n| Claim ID |\n|---|\n| B-001 |\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(
            run_dir, "claim-register Claim IDs must exactly match target-claims Claim IDs"
        )

    def test_run_audit_targets_must_be_unique_parent_claims_or_routes(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="audit-target-parent")
        forged = make_run(
            self.work,
            mode="run-audit",
            parent=parent,
            run_id="run-audit-fake-decision-target",
        )
        forged_manifest = load_manifest(forged)
        for path in (
            forged / "05_route-verdicts.md",
            forged / "06_red-team.md",
            forged / "07_decision-log.md",
            forged / forged_manifest["primary_artifact"],
        ):
            path.write_text(
                path.read_text(encoding="utf-8").replace("B-001", "D-001"),
                encoding="utf-8",
                newline="\n",
            )
        forged_report = validate(forged, workspace_root=self.workspace)
        self.assertTrue(
            any(
                "run-audit main targets have invalid ID types: D-001" in error
                for error in forged_report.errors
            ),
            forged_report.errors,
        )
        self.assertTrue(
            any(
                "outside the authoritative claim/parent source" in error
                and "D-001" in error
                for error in forged_report.errors
            ),
            forged_report.errors,
        )

        duplicate = make_run(
            self.work,
            mode="run-audit",
            parent=parent,
            run_id="run-audit-duplicate-target",
        )
        append_table_row(
            duplicate / "05_route-verdicts.md",
            "route-verdicts",
            [
                "B-001", "Advance", "applicability gap remains", "high",
                "Revise", "bounded mechanism candidate only",
                "matched local test", "D-002",
            ],
        )
        duplicate_manifest = load_manifest(duplicate)
        append_table_row(
            duplicate / duplicate_manifest["primary_artifact"],
            "route-verdicts",
            [
                "B-001", "Advance", "applicability gap remains", "Revise",
                "bounded mechanism candidate only", "matched local test",
                "stop if matched test shows no effect", "D-002",
            ],
        )
        self.assertInvalidContains(
            duplicate,
            "run-audit main decision target table has duplicate targets: B-001",
        )

        claim_only = make_run(
            self.work,
            mode="run-audit",
            parent=parent,
            run_id="run-audit-claim-only-route-id",
            audit_target="C-001",
        )
        set_table_cell(
            claim_only / "03_evidence-audit.md",
            "audited-claims",
            "B-001",
            "Claim ID",
            "C-001",
        )
        scope = claim_only / "00_audit-scope.md"
        scope.write_text(
            scope.read_text(encoding="utf-8")
            + "\n\n<!-- rom-table: audited-claims -->\n"
            + "## Wrong-role decoy\n\n| Claim ID |\n|---|\n| B-001 |\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(
            claim_only,
            "audited-claims Claim ID must be exactly one parent-authoritative claim ID",
        )

        reader_claim = make_run(
            self.work,
            mode="run-audit",
            parent=parent,
            run_id="run-audit-reader-claim-route-id",
            audit_target="C-001",
        )
        reader_manifest = load_manifest(reader_claim)
        set_table_cell(
            reader_claim / reader_manifest["primary_artifact"],
            "scientific-red-team",
            "F-002",
            "Claim",
            "C-001 [1]",
        )
        self.assertInvalidContains(
            reader_claim,
            "scientific-red-team Claim must contain exactly one parent-authoritative claim ID",
        )

        legacy_parent = (
            self.workspace
            / "Projects"
            / "research_map"
            / "validation-runs"
            / "ai-hardware-session-case"
        )
        legacy_route = make_run(
            self.work,
            mode="run-audit",
            parent=legacy_parent,
            run_id="run-audit-legacy-c-l01",
            audit_target="C-L01",
        )
        self.assertValid(legacy_route)

    def test_run_audit_bio_owners_cannot_substitute_for_red_team_a008(self) -> None:
        parent = make_run(
            self.work,
            mode="landscape",
            bio=True,
            run_id="bio-owner-parent",
        )
        run_dir = make_run(
            self.work,
            mode="run-audit",
            parent=parent,
            bio=True,
            run_id="bio-owner-a008-mismatch",
        )
        set_table_cell(
            run_dir / "06_red-team.md",
            "bio-inspired-audit",
            "B-001",
            "Verdict",
            "Keep",
        )
        self.assertInvalidContains(
            run_dir,
            "red_team bio-inspired audit must match A-008 target",
        )

    def test_registered_zh_cn_reader_headers_are_accepted(self) -> None:
        run_dir = make_run(self.work, language="zh-CN", run_id="localized-headers")
        manifest = load_manifest(run_dir)
        reader = run_dir / manifest["primary_artifact"]
        text = reader.read_text(encoding="utf-8")
        replacements = {
            "| Risk tier | Recommended route | Causal interface | Three-month decisive evidence | One-year platform value | Disposition | Decision ID |": "| 风险层级 | 推荐路线 | 核心因果接口 | 三个月决定性证据 | 一年平台价值 | 当前处置 | Decision ID |",
            "| Scope item | Declared boundary |": "| 范围项 | 明确边界 |",
            "| Dimension | Bounded favorable argument | Strongest counterargument | Evidence or capability basis | Decision implication |": "| 维度 | 有边界的正面论证 | 最强反方观点 | 证据或能力依据 | 对决策的影响 |",
            "| State/structure | Causal mechanism | Scale/regime | Readout/metric | Evidence boundary |": "| 状态/结构 | 因果机制 | 尺度/工作区间 | 读出与指标 | 证据边界 |",
            "| Approach family | What it solves | Best demonstrated regime | Enabling assumption | Strongest evidence | Residual failure mode | Why the root bottleneck remains |": "| Approach family | 已解决什么 | 最佳证明区间 | 关键假设 | 最强证据 | 残余失败模式 | 为什么根瓶颈仍存在 |",
            "| Route | What | Why | Need to know | How: existing base→new control→measurement | What we learn | Strongest baseline | Competing hypotheses | Positive outcome | Negative outcome | Ambiguous outcome | Kill criterion | Retained value after failure | Reversal condition |": "| 路线 | What：大白话做什么 | Why：为什么做 | Need to know | How：已有基础→新控制→测量 | What we learn | 最强基线 | 竞争假设 | Positive 结果 | Negative 结果 | Ambiguous 结果 | Kill criterion | 失败后保留价值 | 反转条件 |",
            "| Route | Horizon | Method, controls, and parameter boundary | Pass threshold | Kill/Revise condition | Retained asset |": "| Route | 阶段 | 方法、对照和参数边界 | 通过阈值 | Kill/Revise 条件 | 失败后保留资产 |",
            "| Route | Outcome | Observable | Allowed conclusion | Forbidden extrapolation | Next action |": "| Route | 结果类型 | 可观测结果 | 允许结论 | 禁止外推 | 下一步 |",
            "| Claim | Confidence | Active cap codes | Downgrade reason | Allowed wording | Upgrade/overturn condition |": "| Claim | Confidence | Active cap codes | 降级原因 | 允许措辞 | 升级/推翻条件 |",
        }
        for source, localized in replacements.items():
            self.assertIn(source, text)
            text = text.replace(source, localized, 1)
        reader.write_text(text, encoding="utf-8", newline="\n")
        self.assertValid(run_dir)

    def test_source_normalization_preserves_case_sensitive_url_paths(self) -> None:
        for normalize in (_normalize_source_link, normalize_parent_source):
            with self.subTest(normalize=normalize.__module__):
                self.assertNotEqual(
                    normalize("https://Example.org/Data/A?Token=X"),
                    normalize("https://example.org/data/a?Token=X"),
                )
                self.assertEqual(
                    normalize("HTTPS://DOI.ORG/10.1234/ROM.001"),
                    normalize("https://doi.org/10.1234/rom.001"),
                )

    def test_manifest_paths_reject_noncanonical_and_drive_relative_forms(self) -> None:
        for value in (
            ".", "./artifact.md", "dir//artifact.md", "artifact.md:stream",
            "C:escape.md", "../artifact.md", "dir/../artifact.md",
        ):
            with self.subTest(value=value):
                with self.assertRaises(ContractError):
                    safe_manifest_relpath(value, label="test artifact")
        self.assertEqual(
            safe_manifest_relpath("dir/artifact.md", label="test artifact").as_posix(),
            "dir/artifact.md",
        )

    def test_manifest_and_artifact_symlink_escapes_are_rejected(self) -> None:
        manifest_run = make_run(self.work, run_id="manifest-link")
        manifest_path = manifest_run / "run-manifest.json"
        outside_manifest = self.work / "outside-manifest.json"
        outside_manifest.write_text(
            manifest_path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
        )
        manifest_path.unlink()
        try:
            manifest_path.symlink_to(outside_manifest)
        except OSError as exc:
            self.skipTest(f"symbolic links unavailable: {exc}")
        with self.assertRaises(ContractError):
            load_run_manifest(manifest_run)
        self.assertInvalidContains(manifest_run, "Missing or unsafe run-manifest.json")

        artifact_run = make_run(self.work, run_id="artifact-link")
        artifact_path = artifact_run / "00_intake.md"
        outside_artifact = self.work / "outside-intake.md"
        outside_artifact.write_text(
            artifact_path.read_text(encoding="utf-8"), encoding="utf-8", newline="\n"
        )
        artifact_path.unlink()
        artifact_path.symlink_to(outside_artifact)
        self.assertInvalidContains(artifact_run, "must resolve to a file inside")
        with self.assertRaises(ContractError):
            snapshot_parent_run(
                artifact_run,
                workspace_root=self.workspace,
                relation="focuses-branch",
            )

    def test_bio_translation_chain_requires_baseline_and_ablation(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        valid = make_run(
            self.work, mode="focus", parent=parent, bio=True, run_id="bio-valid"
        )
        self.assertValid(valid)

        invalid = make_run(
            self.work, mode="focus", parent=parent, bio=True, run_id="bio-invalid"
        )
        path = invalid / "04_claim-mechanism-map.md"
        set_table_cell(
            path,
            "bio-inspired-translation",
            "adaptive forgetting under nonstationarity",
            "Principle-specific ablation",
            "not applicable: omitted",
        )
        self.assertInvalidContains(invalid, "translation chain must be non-N/A")

        audit_na = make_run(
            self.work, mode="focus", parent=parent, bio=True, run_id="bio-audit-na"
        )
        set_table_cell(
            audit_na / "06_red-team.md",
            "bio-inspired-audit",
            "C-001",
            "Biological observation",
            "not applicable: no biological observation",
        )
        self.assertInvalidContains(audit_na, "cannot satisfy bio-inspired audit")

        audit_mismatch = make_run(
            self.work, mode="focus", parent=parent, bio=True,
            run_id="bio-audit-mismatch",
        )
        set_table_cell(
            audit_mismatch / "06_red-team.md",
            "bio-inspired-audit",
            "C-001",
            "Verdict",
            "Keep",
        )
        self.assertInvalidContains(
            audit_mismatch, "must match A-008 target, verdict, and Decision ID"
        )

    def test_every_route_owns_reader_execution_and_three_outcomes(self) -> None:
        landscape = make_run(self.work, run_id="landscape-reader-ownership")
        manifest = load_manifest(landscape)
        set_table_cell(
            landscape / manifest["primary_artifact"],
            "execution",
            "C-002",
            "Route",
            "C-001",
        )
        set_table_cell(
            landscape / manifest["primary_artifact"],
            "execution",
            "C-002",
            "Route",
            "C-001",
        )
        self.assertInvalidContains(
            landscape, "Reader execution table is missing landscape routes"
        )

        parent = make_run(self.work, mode="landscape", run_id="ownership-parent")
        focus = make_run(
            self.work, mode="focus", parent=parent, run_id="focus-reader-ownership"
        )
        manifest = load_manifest(focus)
        set_table_cell(
            focus / manifest["primary_artifact"],
            "outcome-interpretation",
            "C-002",
            "Route",
            "C-001",
        )
        self.assertInvalidContains(
            focus, "Reader outcome-interpretation is incomplete by focus route"
        )

        working = make_run(
            self.work, mode="focus", parent=parent, run_id="focus-working-ownership"
        )
        path = working / "05_route-protocol.md"
        text = path.read_text(encoding="utf-8")
        self.assertIn("| one | C-002 | same-budget", text)
        path.write_text(
            text.replace("| one | C-002 | same-budget", "| one | C-001 | same-budget", 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(working, "staged-execution is missing routes")

    def test_each_route_has_a_complete_reader_card_and_focus_boundary_card(self) -> None:
        landscape = make_run(self.work, run_id="landscape-route-card")
        manifest = load_manifest(landscape)
        set_table_cell(
            landscape / manifest["primary_artifact"],
            "recommended-routes",
            "C-002",
            "Strongest baseline",
            "TBD",
        )
        self.assertInvalidContains(
            landscape, "reader route card is missing substantive Strongest baseline"
        )

        parent = make_run(self.work, mode="landscape", run_id="route-card-parent")
        focus = make_run(
            self.work, mode="focus", parent=parent, run_id="focus-boundary-card"
        )
        set_table_cell(
            focus / "05_route-protocol.md",
            "route-boundaries",
            "C-002",
            "Retained value after failure",
            "TBD",
        )
        self.assertInvalidContains(
            focus,
            "route-boundary row has an incomplete kill/reversal/retained-value/activation card",
        )

    def test_mode_specific_cross_artifact_projections_are_exact(self) -> None:
        landscape = make_run(
            self.work, mode="landscape", run_id="landscape-reader-risk-drift"
        )
        landscape_manifest = load_manifest(landscape)
        set_table_cell(
            landscape / landscape_manifest["primary_artifact"],
            "decision-summary",
            "low",
            "Risk tier",
            "high",
        )
        self.assertInvalidContains(
            landscape, "C-ID to risk mapping must exactly match"
        )

        parent = make_run(self.work, mode="landscape", run_id="parent")

        focus = make_run(self.work, mode="focus", parent=parent, run_id="focus")
        path = focus / "05_route-protocol.md"
        text = path.read_text(encoding="utf-8").replace(
            "| C-001 | primary |", "| C-001 | comparator |", 1
        )
        path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(focus, "identical C-ID to role mappings")

        reader_role_drift = make_run(
            self.work,
            mode="focus",
            parent=parent,
            run_id="focus-reader-role-drift",
        )
        reader_role_manifest = load_manifest(reader_role_drift)
        set_table_cell(
            reader_role_drift / reader_role_manifest["primary_artifact"],
            "recommended-routes",
            "primary",
            "Role",
            "comparator",
        )
        self.assertInvalidContains(
            reader_role_drift, "C-ID to role mapping must exactly match"
        )

        local_neighbor = make_run(
            self.work,
            mode="focus",
            parent=parent,
            run_id="focus-local-neighbor",
        )
        append_table_row(
            local_neighbor / "01_focus-scope.md",
            "local-alternatives",
            [
                "C-004",
                "neighbor",
                "adjacent mechanism",
                "same readout",
                "different state variable",
                "matched adjacent baseline",
                "E-001",
                "local only",
            ],
        )
        self.assertValid(local_neighbor)

        extra_focus = make_run(
            self.work,
            mode="focus",
            parent=parent,
            run_id="focus-extra-route-role",
        )
        append_table_row(
            extra_focus / "01_focus-scope.md",
            "local-alternatives",
            [
                "C-004",
                "neighbor",
                "adjacent mechanism",
                "same readout",
                "different state variable",
                "matched adjacent baseline",
                "E-001",
                "local only",
            ],
        )
        append_table_row(
            extra_focus / "05_route-protocol.md",
            "focus-routes",
            [
                "C-004",
                "neighbor",
                "adjacent route",
                "coverage only",
                "causal difference",
                "local comparison",
                "whether it remains adjacent",
                "matched baseline",
                "alternative state",
                "E-001",
            ],
        )
        self.assertInvalidContains(extra_focus, "other candidates use comparator/fallback")

        evidence = make_run(self.work, mode="evidence-audit", run_id="evidence")
        manifest = load_manifest(evidence)
        report_path = evidence / manifest["primary_artifact"]
        text = report_path.read_text(encoding="utf-8").replace(
            "Evidence supports a durable bottleneck in the target regime",
            "The claim might be true",
            1,
        )
        report_path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(evidence, "allowed wording mismatch")

        run_audit = make_run(
            self.work, mode="run-audit", parent=parent, run_id="run-audit"
        )
        manifest = load_manifest(run_audit)
        report_path = run_audit / manifest["primary_artifact"]
        text = report_path.read_text(encoding="utf-8").replace(
            "| B-001 | Advance | applicability gap remains | Revise |",
            "| B-001 | Advance | applicability gap remains | Keep |",
            1,
        )
        report_path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(run_audit, "must match working target")

    def test_run_audit_recomputes_parent_not_child_integrity(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")

        child_source_differs = make_run(
            self.work, mode="run-audit", parent=parent, run_id="audit-source-differs"
        )
        manifest = load_manifest(child_source_differs)
        report_path = child_source_differs / manifest["primary_artifact"]
        report_path.write_text(
            report_path.read_text(encoding="utf-8").replace(
                "https://doi.org/10.1234/rom.001",
                "https://doi.org/10.1234/audit.999",
            ),
            encoding="utf-8",
            newline="\n",
        )
        self.assertValid(child_source_differs)

        bad_artifact = make_run(
            self.work, mode="run-audit", parent=parent, run_id="bad-artifact-projection"
        )
        set_table_cell(
            bad_artifact / "01_artifact-inventory.md",
            "artifact-inventory",
            "ART-001",
            "SHA-256",
            "0" * 64,
        )
        self.assertInvalidContains(bad_artifact, "parent artifact inventory projection")

        bad_citation = make_run(
            self.work, mode="run-audit", parent=parent, run_id="bad-citation-projection"
        )
        set_table_cell(
            bad_citation / "02_traceability-audit.md",
            "citation-closure",
            "[1]",
            "Report DOI/stable URL",
            "https://doi.org/10.1234/audit.999",
        )
        self.assertInvalidContains(bad_citation, "parent citation closure projection")

        bad_manifest = make_run(
            self.work, mode="run-audit", parent=parent, run_id="bad-manifest-projection"
        )
        set_table_cell(
            bad_manifest / "01_artifact-inventory.md",
            "manifest-lineage-audit",
            "schema-supported",
            "Result: pass/fail/uncertain",
            "fail",
        )
        self.assertInvalidContains(bad_manifest, "parent manifest audit projection")

        drifted_parent = make_run(self.work, mode="landscape", run_id="drift-parent")
        drift_audit = make_run(
            self.work, mode="run-audit", parent=drifted_parent, run_id="drift-audit"
        )
        (drifted_parent / "undeclared-after-snapshot.md").write_text(
            "parent changed after audit initialization\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(drift_audit, "observed parent file tree")

    def test_parent_citation_anomaly_binds_the_strongest_final_disposition(self) -> None:
        parent = make_run(
            self.work, mode="landscape", run_id="citation-anomaly-parent"
        )
        parent_manifest = load_manifest(parent)
        parent_reader = parent / parent_manifest["primary_artifact"]
        parent_text = parent_reader.read_text(encoding="utf-8")
        original = "control-to-state interface [3]"
        self.assertIn(original, parent_text)
        parent_reader.write_text(
            parent_text.replace(
                original,
                "control-to-state interface",
                1,
            ),
            encoding="utf-8",
            newline="\n",
        )

        audit = make_run(
            self.work,
            mode="run-audit",
            parent=parent,
            run_id="citation-anomaly-audit",
        )
        self.assertValid(audit)
        repair = "repair parent citation closure"
        source = "parent citation-closure anomaly [3:reference-unused]"
        set_table_cell(
            audit / "02_traceability-audit.md",
            "citation-closure",
            "[3]",
            "Decision ID",
            "D-009",
        )
        append_table_row(
            audit / "07_decision-log.md",
            "decisions",
            [
                "D-009",
                "2026-07-31",
                "B-001",
                "B-001",
                "Kill",
                "Parent citation-closure anomaly [3:reference-unused]",
                "E-003",
                "the parent reference is unused in the report body",
                "repair only in a separate parent revision",
                "not-applicable: deterministic parent anomaly",
                "the parent report cites reference 3 again",
                repair,
            ],
        )
        self.assertInvalidContains(
            audit, "strongest red-team verdict kill"
        )

        audit_manifest = load_manifest(audit)
        working_verdicts = (
            audit / audit_manifest["artifact_roles"]["route_verdicts"]
        )
        reader_verdicts = audit / audit_manifest["primary_artifact"]
        for path, finding_header, verdict_header in (
            (
                working_verdicts,
                "Strongest finding",
                "Verdict: Keep/Downgrade/Revise/Kill",
            ),
            (reader_verdicts, "Strongest objection", "Verdict"),
        ):
            set_table_cell(
                path, "route-verdicts", "B-001", finding_header, source
            )
            set_table_cell(
                path, "route-verdicts", "B-001", verdict_header, "Kill"
            )
            set_table_cell(
                path,
                "route-verdicts",
                "B-001",
                "Required repair",
                repair,
            )
            set_table_cell(
                path, "route-verdicts", "B-001", "Decision ID", "D-009"
            )
        self.assertValid(audit)

    def test_run_audit_projects_legacy_10_and_12_parents(self) -> None:
        baseline = json.loads(
            (SKILL_DIR / "tests" / "baselines" / "legacy-runs.json").read_text(
                encoding="utf-8"
            )
        )
        for item in baseline["runs"]:
            with self.subTest(schema=item["schema_version"]):
                parent = self.workspace / Path(item["workspace_relpath"])
                parent_manifest = load_manifest(parent)
                parent_facts = inspect_parent_for_audit(
                    parent, parent_manifest, {"run_id": parent_manifest["run_id"]}
                )
                self.assertFalse(
                    any(row[4] == "duplicate-definition" for row in parent_facts.id_projection),
                    parent_facts.id_projection,
                )
                audit = make_run(
                    self.work,
                    mode="run-audit",
                    parent=parent,
                    run_id=f"audit-legacy-{item['schema_version'].replace('.', '-')}",
                )
                self.assertValid(audit)
                trace = (audit / "02_traceability-audit.md").read_text(
                    encoding="utf-8"
                )
                if item["schema_version"] == "1.0":
                    self.assertIn("not-applicable-no-declared-reader", trace)
                else:
                    self.assertIn("| [1] |", trace)
                    self.assertIn("| yes | match |", trace)
    @unittest.skipUnless(os.environ.get("MAPPER_LEGACY_WORKSPACE"), "Exact historical fixture assertions require MAPPER_LEGACY_WORKSPACE")
    def test_run_audit_projects_legal_schema_11_without_primary_artifact(self) -> None:
        legacy_12 = (
            self.workspace
            / "Doc/Typora/note_2025_S2SPR/周工作/W22/sciver mapper/"
            "self-regulating-learning-hardware"
        )
        parent = self.work / "legal-schema-1.1-parent"
        shutil.copytree(legacy_12, parent)
        parent_manifest = load_manifest(parent)
        parent_manifest["schema_version"] = "1.1"
        parent_manifest.pop("primary_artifact", None)
        parent_manifest.pop("artifact_roles", None)
        save_manifest(parent, parent_manifest)

        self.assertValid(parent)
        parent_facts = inspect_parent_for_audit(
            parent, parent_manifest, {"run_id": parent_manifest["run_id"]}
        )
        manifest_rows = {
            row[0]: row for row in parent_facts.manifest_projection
        }
        self.assertEqual(manifest_rows["primary-artifact"][2], "pass")
        self.assertIn(
            "primary_artifact=not-required",
            manifest_rows["primary-artifact"][1],
        )
        reader_rel = next(
            value for value in parent_manifest["artifact_files"]
            if value.startswith("map_report_")
        )
        reader_rows = [
            row for row in parent_facts.artifact_projection
            if row[2] == reader_rel
        ]
        self.assertEqual(len(reader_rows), 1)
        self.assertIn("reader_report", reader_rows[0][1])
        self.assertTrue(
            any(row[4:] == ("yes", "match") for row in parent_facts.citation_projection),
            parent_facts.citation_projection,
        )

        audit = make_run(
            self.work,
            mode="run-audit",
            parent=parent,
            run_id="audit-legal-schema-1-1",
        )
        self.assertValid(audit)
        trace = (audit / "02_traceability-audit.md").read_text(encoding="utf-8")
        self.assertIn("| [1] |", trace)
        self.assertIn("| yes | match |", trace)

        strict_12 = dict(parent_manifest)
        strict_12["schema_version"] = "1.2"
        strict_facts = inspect_parent_for_audit(
            parent, strict_12, {"run_id": strict_12["run_id"]}
        )
        strict_manifest_rows = {
            row[0]: row for row in strict_facts.manifest_projection
        }
        self.assertEqual(strict_manifest_rows["primary-artifact"][2], "fail")
        self.assertTrue(
            any(row[-1] == "missing-reader-artifact" for row in strict_facts.citation_projection),
            strict_facts.citation_projection,
        )

    def test_run_audit_can_truthfully_audit_an_incomplete_parent(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="incomplete-parent")
        parent_manifest = load_manifest(parent)
        (parent / parent_manifest["primary_artifact"]).unlink()

        audit = make_run(
            self.work,
            mode="run-audit",
            parent=parent,
            run_id="audit-incomplete-parent",
        )
        self.assertValid(audit)
        inventory = (audit / "01_artifact-inventory.md").read_text(encoding="utf-8")
        trace = (audit / "02_traceability-audit.md").read_text(encoding="utf-8")
        self.assertIn("declared-missing", inventory)
        self.assertIn("missing-reader-artifact", trace)
        set_table_cell(
            audit / "01_artifact-inventory.md",
            "manifest-lineage-audit",
            "declared-vs-observed",
            "Decision ID",
            "D-001",
        )
        self.assertInvalidContains(audit, "must propagate to a Downgrade/Revise/Kill")

        custom_parent = make_run(
            self.work, mode="landscape", run_id="incomplete-custom-parent"
        )
        custom_manifest = load_manifest(custom_parent)
        custom_manifest.update(
            {
                "primary_domain_lens": "custom",
                "secondary_domain_lenses": [],
                "domain_lens_notes": "Decision object: only one populated slot",
            }
        )
        save_manifest(custom_parent, custom_manifest)
        custom_audit = make_run(
            self.work,
            mode="run-audit",
            parent=custom_parent,
            run_id="audit-incomplete-custom-parent",
        )
        self.assertValid(custom_audit)
        custom_inventory = (custom_audit / "01_artifact-inventory.md").read_text(
            encoding="utf-8"
        )
        canonical_repair = canonical_manifest_repair("domain-lenses", "fail")
        manifest_failure = (
            "| domain-lenses | primary=custom; secondary=; custom-notes=present | "
            f"fail | high | {canonical_repair} | D-009 |"
        )
        self.assertIn(manifest_failure, custom_inventory)
        custom_audit_manifest = load_manifest(custom_audit)
        custom_reader = custom_audit / custom_audit_manifest["primary_artifact"]
        reader_projection = (
            "| parent manifest failure [domain-lenses] | "
            "primary=custom; secondary=; custom-notes=present | "
            f"high | Revise | {canonical_repair} | D-009 |"
        )
        self.assertIn(reader_projection, custom_reader.read_text(encoding="utf-8"))
        set_table_cell(
            custom_reader,
            "integrity",
            "parent manifest failure [domain-lenses]",
            "Verdict",
            "Keep",
        )
        self.assertInvalidContains(custom_audit, "reader integrity")

    def test_manifest_failures_have_adversarially_closed_dispositions(self) -> None:
        def build_audit(
            case: str,
            *,
            two_failures: bool = False,
        ) -> tuple[Path, Path]:
            parent = make_run(
                self.work,
                mode="landscape",
                run_id=f"{case}-parent",
            )
            parent_manifest = load_manifest(parent)
            parent_manifest.update(
                {
                    "primary_domain_lens": "custom",
                    "secondary_domain_lenses": [],
                    "domain_lens_notes": "Decision object: only one populated slot",
                }
            )
            if two_failures:
                parent_manifest["created_at"] = "not-a-date"
            save_manifest(parent, parent_manifest)
            audit = make_run(
                self.work,
                mode="run-audit",
                parent=parent,
                run_id=f"{case}-audit",
            )
            self.assertValid(audit)
            audit_manifest = load_manifest(audit)
            reader = audit / audit_manifest["primary_artifact"]
            return audit, reader

        collusion, collusion_reader = build_audit("manifest-repair-collusion")
        set_table_cell(
            collusion / "01_artifact-inventory.md",
            "manifest-lineage-audit",
            "domain-lenses",
            "Required repair",
            "generic repair accepted by both files",
        )
        set_table_cell(
            collusion_reader,
            "integrity",
            "parent manifest failure [domain-lenses]",
            "Repair",
            "generic repair accepted by both files",
        )
        self.assertInvalidContains(collusion, "canonical repair")

        reused, reused_reader = build_audit(
            "manifest-decision-reuse",
            two_failures=True,
        )
        set_table_cell(
            reused / "01_artifact-inventory.md",
            "manifest-lineage-audit",
            "created-at",
            "Decision ID",
            "D-009",
        )
        set_table_cell(
            reused_reader,
            "integrity",
            "parent manifest failure [created-at]",
            "Decision ID",
            "D-009",
        )
        self.assertInvalidContains(
            reused,
            "reuses manifest decision D-009",
        )

        attack_reuse, attack_reuse_reader = build_audit(
            "manifest-attack-reuse"
        )
        set_table_cell(
            attack_reuse / "01_artifact-inventory.md",
            "manifest-lineage-audit",
            "domain-lenses",
            "Decision ID",
            "D-002",
        )
        set_table_cell(
            attack_reuse_reader,
            "integrity",
            "parent manifest failure [domain-lenses]",
            "Decision ID",
            "D-002",
        )
        self.assertInvalidContains(
            attack_reuse,
            "reuses attack decision D-002",
        )

        duplicate_finding, duplicate_reader = build_audit(
            "manifest-reader-duplicate-finding"
        )
        canonical_repair = canonical_manifest_repair("domain-lenses", "fail")
        append_table_row(
            duplicate_reader,
            "integrity",
            [
                "parent manifest failure [domain-lenses]",
                "primary=custom; secondary=; custom-notes=present",
                "high",
                "Keep",
                canonical_repair,
                "D-001",
            ],
        )
        self.assertInvalidContains(
            duplicate_finding,
            "exactly one reader integrity row",
        )

        duplicate_decision, duplicate_decision_reader = build_audit(
            "manifest-reader-duplicate-decision"
        )
        append_table_row(
            duplicate_decision_reader,
            "integrity",
            [
                "parent manifest failure [fabricated-check]",
                "fabricated evidence",
                "high",
                "Keep",
                canonical_repair,
                "D-009",
            ],
        )
        self.assertInvalidContains(
            duplicate_decision,
            "exactly one reader integrity row",
        )

        unrelated_row, unrelated_reader = build_audit(
            "manifest-reader-unrelated-row"
        )
        append_table_row(
            unrelated_reader,
            "integrity",
            [
                "unrelated integrity observation",
                "plausible but unbound evidence",
                "low",
                "Keep",
                "retain plausible observation",
                "D-001",
            ],
        )
        self.assertInvalidContains(
            unrelated_row,
            "extra, missing, reordered, or altered rows",
        )

        passed_reuse, _ = build_audit("manifest-passed-row-reuse")
        set_table_cell(
            passed_reuse / "01_artifact-inventory.md",
            "manifest-lineage-audit",
            "schema-supported",
            "Decision ID",
            "D-009",
        )
        self.assertInvalidContains(
            passed_reuse,
            "reused by another passed or failed manifest check",
        )

        for case, decision_id in (
            ("manifest-invalid-pass-id", "plausible-decision"),
            ("manifest-composite-pass-id", "D-001,D-009"),
        ):
            with self.subTest(case=case):
                malformed_pass, _ = build_audit(case)
                set_table_cell(
                    malformed_pass / "01_artifact-inventory.md",
                    "manifest-lineage-audit",
                    "schema-supported",
                    "Decision ID",
                    decision_id,
                )
                self.assertInvalidContains(
                    malformed_pass,
                    "must use exactly one valid Decision ID",
                )

        nonkeep_pass, _ = build_audit("manifest-pass-nonkeep-decision")
        set_table_cell(
            nonkeep_pass / "01_artifact-inventory.md",
            "manifest-lineage-audit",
            "schema-supported",
            "Decision ID",
            "D-002",
        )
        self.assertInvalidContains(
            nonkeep_pass, "pass row must bind a Keep decision"
        )

        registry_drift, _ = build_audit("manifest-repair-registry-drift")
        drifted_repairs = dict(MANIFEST_FAILURE_REPAIRS)
        drifted_repairs.pop("domain-lenses")
        with patch.dict(
            MANIFEST_FAILURE_REPAIRS, drifted_repairs, clear=True
        ):
            drift_report = validate(
                registry_drift, workspace_root=self.workspace
            )
        self.assertTrue(drift_report.errors)
        self.assertTrue(
            any(
                "canonical manifest repair registry is incomplete" in error
                for error in drift_report.errors
            ),
            drift_report.errors,
        )

        clean_parent = make_run(
            self.work,
            mode="landscape",
            run_id="manifest-clean-sentinel-parent",
        )
        clean_audit = make_run(
            self.work,
            mode="run-audit",
            parent=clean_parent,
            run_id="manifest-clean-sentinel-audit",
        )
        self.assertValid(clean_audit)
        clean_manifest = load_manifest(clean_audit)
        clean_reader = clean_audit / clean_manifest["primary_artifact"]
        set_table_cell(
            clean_reader,
            "integrity",
            "manifest, artifact, ID, and citation projections match recomputation",
            "Finding",
            "plausible clean snapshot",
        )
        self.assertInvalidContains(
            clean_audit,
            "canonical clean-parent sentinel",
        )

        route_reader_drift, route_reader = build_audit(
            "manifest-route-reader-repair-drift"
        )
        set_table_cell(
            route_reader,
            "route-verdicts",
            "B-001",
            "Required repair",
            "plausible reader-only repair",
        )
        self.assertInvalidContains(
            route_reader_drift,
            "must match working target, strongest finding",
        )

        route_collusion, route_collusion_reader = build_audit(
            "manifest-route-repair-collusion"
        )
        route_collusion_manifest = load_manifest(route_collusion)
        route_collusion_working = (
            route_collusion
            / route_collusion_manifest["artifact_roles"]["route_verdicts"]
        )
        for path in (route_collusion_working, route_collusion_reader):
            set_table_cell(
                path,
                "route-verdicts",
                "B-001",
                "Required repair",
                "same plausible but noncanonical final repair",
            )
        self.assertInvalidContains(
            route_collusion,
            "Required repair must equal the canonical manifest repair",
        )

        finding_collusion, finding_collusion_reader = build_audit(
            "manifest-route-finding-collusion"
        )
        finding_manifest = load_manifest(finding_collusion)
        finding_working = (
            finding_collusion
            / finding_manifest["artifact_roles"]["route_verdicts"]
        )
        set_table_cell(
            finding_working,
            "route-verdicts",
            "B-001",
            "Strongest finding",
            "plausible but detached integrity finding",
        )
        set_table_cell(
            finding_collusion_reader,
            "route-verdicts",
            "B-001",
            "Strongest objection",
            "plausible but detached integrity finding",
        )
        self.assertInvalidContains(
            finding_collusion,
            "Strongest finding must equal",
        )

        integrity_only, integrity_only_reader = build_audit(
            "manifest-integrity-only-binding"
        )
        integrity_manifest = load_manifest(integrity_only)
        red_team = integrity_only / integrity_manifest["artifact_roles"]["red_team"]
        decisions = (
            integrity_only
            / integrity_manifest["artifact_roles"]["decision_log"]
        )
        for index in range(1, 9):
            attack_id = f"A-{index:03d}"
            decision_id = f"D-{index:03d}"
            set_table_cell(
                red_team,
                "attack-register",
                attack_id,
                "Severity: low/medium/high/blocking",
                "low",
            )
            set_table_cell(
                red_team,
                "attack-register",
                attack_id,
                "Verdict: Keep/Downgrade/Revise/Kill",
                "Keep",
            )
            set_table_cell(
                red_team,
                "attack-register",
                attack_id,
                "Status",
                "closed",
            )
            set_table_cell(
                decisions,
                "decisions",
                decision_id,
                "Status: Keep/Downgrade/Revise/Kill",
                "Keep",
            )
            set_table_cell(
                integrity_only_reader,
                "red-team-impact",
                attack_id,
                "Severity",
                "low",
            )
            set_table_cell(
                integrity_only_reader,
                "red-team-impact",
                attack_id,
                "Verdict",
                "Keep",
            )
            set_table_cell(
                integrity_only_reader,
                "red-team-impact",
                attack_id,
                "Status",
                "closed",
            )
        self.assertValid(integrity_only)
        route_verdicts = (
            integrity_only
            / integrity_manifest["artifact_roles"]["route_verdicts"]
        )
        set_table_cell(
            route_verdicts,
            "route-verdicts",
            "B-001",
            "Verdict: Keep/Downgrade/Revise/Kill",
            "Keep",
        )
        set_table_cell(
            route_verdicts,
            "route-verdicts",
            "B-001",
            "Decision ID",
            "D-001",
        )
        set_table_cell(
            integrity_only_reader,
            "route-verdicts",
            "B-001",
            "Verdict",
            "Keep",
        )
        set_table_cell(
            integrity_only_reader,
            "route-verdicts",
            "B-001",
            "Decision ID",
            "D-001",
        )
        self.assertInvalidContains(
            integrity_only,
            "strongest red-team verdict revise",
        )

        kill_binding, kill_reader = build_audit("manifest-kill-binding")
        kill_manifest = load_manifest(kill_binding)
        kill_decisions = (
            kill_binding / kill_manifest["artifact_roles"]["decision_log"]
        )
        kill_routes = (
            kill_binding / kill_manifest["artifact_roles"]["route_verdicts"]
        )
        set_table_cell(
            kill_decisions,
            "decisions",
            "D-009",
            "Status: Keep/Downgrade/Revise/Kill",
            "Kill",
        )
        set_table_cell(
            kill_reader,
            "integrity",
            "parent manifest failure [domain-lenses]",
            "Verdict",
            "Kill",
        )
        set_table_cell(
            kill_routes,
            "route-verdicts",
            "B-001",
            "Verdict: Keep/Downgrade/Revise/Kill",
            "Kill",
        )
        set_table_cell(
            kill_reader,
            "route-verdicts",
            "B-001",
            "Verdict",
            "Kill",
        )
        self.assertValid(kill_binding)

    def test_red_team_enums_targets_resolution_and_coverage_are_hard_gates(self) -> None:
        cases = {
            "surface": ("Attack surface", "vague-surface", "invalid attack surface"),
            "severity": ("Severity: low/medium/high/blocking", "urgent", "invalid severity"),
            "status": ("Status", "waiting", "invalid resolution status"),
            "target": ("Target claim/route", "C-999", "not a valid defined/external ID"),
            "evidence": ("Evidence IDs or test", "-", "substantive Evidence/test"),
            "repair": ("Required repair or discriminating test", "-", "substantive Evidence/test"),
        }
        for name, (header, value, expected) in cases.items():
            with self.subTest(case=name):
                run_dir = make_run(self.work, run_id=f"attack-{name}")
                set_table_cell(run_dir / "06_red-team.md", "attack-register", "A-001", header, value)
                self.assertInvalidContains(run_dir, expected)

        unresolved_keep = make_run(self.work, run_id="attack-unresolved-keep")
        set_table_cell(
            unresolved_keep / "06_red-team.md",
            "attack-register",
            "A-002",
            "Verdict: Keep/Downgrade/Revise/Kill",
            "Keep",
        )
        self.assertInvalidContains(unresolved_keep, "cannot Keep a high/blocking")

        uncovered = make_run(self.work, run_id="attack-uncovered")
        path = uncovered / "06_red-team.md"
        lines = path.read_text(encoding="utf-8").splitlines()
        path.write_text(
            "\n".join(line for line in lines if not line.startswith("| A-006 |")) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(uncovered, "missing major landscape targets: C-003")
        self.assertInvalidContains(uncovered, "exactly the eight registered attack surfaces")

        surface_gap = make_run(self.work, run_id="attack-surface-gap")
        manifest = load_manifest(surface_gap)
        set_table_cell(
            surface_gap / "06_red-team.md",
            "attack-register",
            "A-006",
            "Attack surface",
            "capability",
        )
        set_table_cell(
            surface_gap / manifest["primary_artifact"],
            "red-team-impact",
            "A-006",
            "Attack surface",
            "capability",
        )
        self.assertInvalidContains(
            surface_gap, "exactly the eight registered attack surfaces"
        )

    def test_reader_exact_structure_callouts_and_public_id_boundary(self) -> None:
        extra = make_run(self.work, run_id="reader-extra-marker")
        manifest = load_manifest(extra)
        path = extra / manifest["primary_artifact"]
        text = path.read_text(encoding="utf-8").replace(
            "<!-- rom-section: references -->",
            "<!-- rom-section: extra -->\n## Extra\nUnregistered reader section.\n\n<!-- rom-section: references -->",
        )
        path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(extra, "marker set/order mismatch")

        reordered = make_run(self.work, run_id="reader-reordered")
        manifest = load_manifest(reordered)
        path = reordered / manifest["primary_artifact"]
        text = path.read_text(encoding="utf-8")
        text = text.replace("rom-section: scope", "rom-section: swap-marker", 1)
        text = text.replace("rom-section: background-question", "rom-section: scope", 1)
        text = text.replace("rom-section: swap-marker", "rom-section: background-question", 1)
        path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(reordered, "marker set/order mismatch")

        no_table = make_run(self.work, run_id="reader-no-table")
        manifest = load_manifest(no_table)
        path = no_table / manifest["primary_artifact"]
        lines = path.read_text(encoding="utf-8").splitlines()
        start = lines.index("<!-- rom-section: outcome-interpretation -->")
        end = next(
            index for index in range(start + 1, len(lines))
            if lines[index].startswith("<!-- rom-section:")
        )
        lines[start + 1:end] = ["## Outcome Interpretation", "No structured outcome table."]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        self.assertInvalidContains(no_table, "required structured table")

        no_callout = make_run(self.work, run_id="reader-no-callout")
        manifest = load_manifest(no_callout)
        path = no_callout / manifest["primary_artifact"]
        path.write_text(
            path.read_text(encoding="utf-8").replace("> [!NOTE]", "> [!TIP]", 1),
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(no_callout, "missing required callouts: NOTE")

        internal = make_run(self.work, run_id="reader-internal-id")
        manifest = load_manifest(internal)
        path = internal / manifest["primary_artifact"]
        path.write_text(
            path.read_text(encoding="utf-8") + "\nInternal trace doc_id=opaque-123.\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(internal, "exposes internal retrieval IDs")

    def test_new_machine_confidence_caps_are_enforced(self) -> None:
        cases = {
            "method": (
                [("claim-confidence", "B-001", "Method validity", "cannot distinguish the preferred mechanism from an unresolved alternative")],
                "method-nondiscriminating",
            ),
            "regime": (
                [("claim-confidence", "B-001", "Applicability", "different regime with unvalidated transfer")],
                "regime-transfer-unvalidated",
            ),
            "salience": (
                [
                    ("evidence-records", "E-001", "Source role", "frontier-signal"),
                    ("evidence-records", "E-002", "Source role", "frontier-signal"),
                ],
                "salience-only",
            ),
            "search-miss": (
                [
                    ("atomic-claims", "B-001", "Claim type", "open-position"),
                    ("claim-confidence", "B-001", "Cap/downgrade reason", "zero hits imply novelty priority"),
                ],
                "search-miss-novelty",
            ),
            "proxy-system": (
                [
                    ("atomic-claims", "B-001", "Claim type", "system-value"),
                    ("claim-confidence", "B-001", "Applicability", "device proxy to system value has a missing bridge and remains unvalidated"),
                ],
                "proxy-to-system-unvalidated",
            ),
            "assumed-capability": (
                [("claim-confidence", "B-001", "Applicability", "capability is assumed and unverified")],
                "assumed-capability",
            ),
        }
        for name, (mutations, cap_code) in cases.items():
            with self.subTest(cap=name):
                run_dir = make_run(self.work, run_id=f"cap-{name}")
                path = run_dir / "03_evidence-matrix.md"
                for marker, row_id, header, value in mutations:
                    set_table_cell(path, marker, row_id, header, value)
                set_table_cell(
                    path,
                    "claim-confidence",
                    "B-001",
                    "Active cap codes",
                    cap_code,
                )
                self.assertInvalidContains(run_dir, f"imposed by {cap_code}")

        missing = make_run(self.work, run_id="cap-missing-declaration")
        path = missing / "03_evidence-matrix.md"
        set_table_cell(
            path,
            "claim-confidence",
            "B-001",
            "Method validity",
            "cannot distinguish the preferred mechanism from an alternative",
        )
        self.assertInvalidContains(missing, "missing required Active cap codes")

        unknown = make_run(self.work, run_id="cap-unknown")
        set_table_cell(
            unknown / "03_evidence-matrix.md",
            "claim-confidence",
            "B-001",
            "Active cap codes",
            "famous-paper",
        )
        self.assertInvalidContains(unknown, "unknown Active cap codes")

    def test_exact_header_registry_complete_roles_and_id_types_resist_impersonation(self) -> None:
        fuzzy = make_run(self.work, run_id="fuzzy-header")
        path = fuzzy / "03_evidence-matrix.md"
        text = path.read_text(encoding="utf-8").replace(
            "Confidence: High/Moderate/Low/Insufficient",
            "Confidence narrative",
            1,
        )
        path.write_text(text, encoding="utf-8", newline="\n")
        self.assertInvalidContains(fuzzy, "header must exactly match a registered schema")

        missing_role = make_run(self.work, run_id="missing-role-marker")
        path = missing_role / "00_intake.md"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "<!-- rom-section: controllable-actions -->\n", "", 1
            ),
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(missing_role, "missing rom-section marker controllable-actions")

        type_leak = make_run(self.work, run_id="candidate-type-leak")
        set_table_cell(
            type_leak / "05_candidate-portfolio.md",
            "candidate-routes",
            "C-001",
            "Candidate ID",
            "B-999",
        )
        self.assertInvalidContains(type_leak, "invalid definition ID")

        wrong_role = make_run(self.work, run_id="wrong-role-definition")
        intake = wrong_role / "00_intake.md"
        intake.write_text(
            intake.read_text(encoding="utf-8")
            + "\n<!-- rom-table: breadth-branches -->\n"
            + "| Branch ID | Branch |\n|---|---|\n"
            + "| BR-999 | misplaced definition |\n",
            encoding="utf-8",
            newline="\n",
        )
        self.assertInvalidContains(wrong_role, "appears in wrong artifact role")


if __name__ == "__main__":
    unittest.main()
