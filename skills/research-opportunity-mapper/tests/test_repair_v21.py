from __future__ import annotations

import importlib.util
import os
import re
import sys
import unittest
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SKILL_DIR / "scripts"), str(SKILL_DIR / "tests")]
import canonical_links
from evidence_chains import assess_chains, independently_reviewed
from fixture_factory import cleanup_work, load_manifest, make_run, reset_work, save_manifest, workspace_root
from test_validator_v2 import set_table_cell
from validate_run import validate


def edit_table(path, marker, transform):
    document_lines = path.read_text(encoding="utf-8").splitlines()
    marker_index = next(i for i, line in enumerate(document_lines) if line in
                        (f"<!-- rom-table: {marker} -->", f"<!-- rom-section: {marker} -->"))
    start = next(i for i in range(marker_index + 1, len(document_lines)) if document_lines[i].startswith("|"))
    end = start
    while end < len(document_lines) and document_lines[end].startswith("|"):
        end += 1
    lines = document_lines[start:end]
    headers = [cell.strip() for cell in lines[0].strip("|").split("|")]
    rows = [[cell.strip() for cell in line.strip("|").split("|")] for line in lines[2:]]
    headers, rows = transform(headers, rows)
    replacement = "\n".join(["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers),
                              *["| " + " | ".join(row) + " |" for row in rows]]) + "\n"
    path.write_text("\n".join(document_lines[:start]) + "\n" + replacement + "\n".join(document_lines[end:]) + "\n", encoding="utf-8", newline="\n")


def filter_routes(run, keep):
    portfolio = run / "05_candidate-portfolio.md"
    reader = run / load_manifest(run)["primary_artifact"]
    for marker in ("candidate-routes", "scorecard", "opportunity-gates", "route-fast-pilots"):
        edit_table(portfolio, marker, lambda h, rows: (h, [r for r in rows if r[0] in keep]))
    for marker in ("recommended-routes", "execution", "outcome-interpretation"):
        edit_table(reader, marker, lambda h, rows: (h, [r for r in rows if r[0] in keep]))
    edit_table(reader, "decision-summary", lambda h, rows: (h, [r for r in rows if any(c in r[1] for c in keep)]))
    if not keep:
        for marker in ("shared-platform", "rejected-routes"):
            edit_table(portfolio, marker, lambda h, rows: (h, []))
        edit_table(reader, "decision-summary", lambda h, rows: (["Claim", "Disposition", "Decision ID"], [["B-001", "Revise", "D-002"]]))
        set_table_cell(run / "04_research-map.md", "open-interfaces", "I-001", "Candidate ID", "none")
    for path in run.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for identifier in ("C-001", "C-002", "C-003", "C-004"):
            if identifier not in keep and (not keep or identifier != "C-004"):
                text = text.replace(identifier, "C-001" if keep else "B-001")
        path.write_text(text, encoding="utf-8", newline="\n")
    if not keep:
        portfolio.write_text(portfolio.read_text(encoding="utf-8") + "\nSelection outcome: no-candidate\n", encoding="utf-8")
        edit_table(run / "07_decision-log.md", "next-actions", lambda h, rows: (h, [["audit the existing evidence and resource inventory", "search", "frozen evidence matrix and inventory records", "bounded no-candidate decision with explicit reopening conditions", "B-001: retain stop unless the missing evidence or capability becomes documented"]]))
    text = reader.read_text(encoding="utf-8")
    reader.write_text(text.replace("<!-- rom-section: scope -->", "The bounded bottleneck evidence [1], mechanism context [2], and limiting regime [3] remain relevant to the decision.\n\n<!-- rom-section: scope -->"), encoding="utf-8")


def filter_focus_routes(run, keep):
    reader = run / load_manifest(run)["primary_artifact"]
    for file, marker, column in (
        ("01_focus-scope.md", "local-alternatives", 0),
        ("04_claim-mechanism-map.md", "claim-null-test-threshold", 0),
        ("05_route-protocol.md", "focus-routes", 0),
        ("05_route-protocol.md", "staged-execution", 1),
        ("05_route-protocol.md", "outcome-interpretation", 0),
        ("05_route-protocol.md", "route-boundaries", 0),
        ("05_route-protocol.md", "opportunity-gates", 0),
        ("05_route-protocol.md", "route-fast-pilots", 0),
        (reader.name, "recommended-routes", 1),
        (reader.name, "execution", 0),
        (reader.name, "outcome-interpretation", 0),
    ):
        edit_table(run / file, marker, lambda h, rows: (h, [row for row in rows if row[column] in keep]))
    for path in run.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        for identifier in ("C-001", "C-002", "C-003", "C-004"):
            if identifier not in keep:
                text = text.replace(identifier, "C-001" if keep else "B-001")
        path.write_text(text, encoding="utf-8")
    if keep:
        set_table_cell(run / "05_route-protocol.md", "route-boundaries", "C-001", "Comparator/fallback activation rule", "Use the matched digital comparator; if causal signatures fail retain static calibration and the measurement dataset, without inventing a new candidate")
    else:
        path = run / "05_route-protocol.md"
        path.write_text(path.read_text(encoding="utf-8") + "\nSelection outcome: no-candidate\n", encoding="utf-8")
        text = reader.read_text(encoding="utf-8")
        text = re.sub(r"(<!-- rom-section: decision-summary -->).*?(?=<!-- rom-section:)", r"\1\n## Decision Summary\n\n| Claim | Disposition | Decision ID |\n|---|---|---|\n| B-001 | Revise | D-002 |\n\n", text, count=1, flags=re.S)
        reader.write_text(text, encoding="utf-8")
        edit_table(run / "07_decision-log.md", "next-actions", lambda h, rows: (h, [["check frozen evidence for a bounded reopening condition", "search", "existing full-text evidence and resource inventory", "claim-level stop decision and missing-evidence specification", "B-001: remain stopped unless the specified evidence becomes available"]]))


class RepairV21Tests(unittest.TestCase):
    work_name = "repair-v21"

    def setUp(self):
        self.work = reset_work(self.work_name)
        self.workspace = workspace_root()

    def tearDown(self):
        cleanup_work(self.work_name)

    def errors(self, run):
        return validate(run, workspace_root=self.workspace).errors

    def assertValid(self, run):
        self.assertEqual(self.errors(run), [])

    def assertError(self, run, fragment):
        errors = self.errors(run)
        self.assertTrue(any(fragment.lower() in error.lower() for error in errors), "\n".join(errors))

    def test_missing_partial_unknown_contracts_cannot_disable_checks(self):
        for value in (None, [], ["deep-reading-handoff-v2"], ["unknown-contract"]):
            with self.subTest(value=value):
                run = make_run(self.work, run_id="contract-" + str(len(list(self.work.iterdir()))))
                manifest = load_manifest(run)
                if value is None:
                    manifest.pop("workflow_contracts")
                else:
                    manifest["workflow_contracts"] = value
                save_manifest(run, manifest)
                set_table_cell(run / "05_candidate-portfolio.md", "route-fast-pilots", "C-001", "Horizon days: 1-14", "90")
                self.assertError(run, "workflow_contracts")
                self.assertError(run, "integer from 1 to 14")

    def test_zero_candidates_close_on_atomic_claims(self):
        run = make_run(self.work, run_id="zero-candidates")
        filter_routes(run, set())
        self.assertValid(run)
        path = run / "05_candidate-portfolio.md"
        path.write_text(path.read_text(encoding="utf-8").replace("Selection outcome: no-candidate", ""), encoding="utf-8")
        self.assertError(run, "Selection outcome: no-candidate")

    def test_single_candidate_does_not_require_shared_or_three_risks(self):
        run = make_run(self.work, run_id="single")
        filter_routes(run, {"C-001"})
        edit_table(run / "05_candidate-portfolio.md", "shared-platform", lambda h, rows: (h, []))
        self.assertValid(run)

    def test_multiple_candidates_may_share_one_risk(self):
        run = make_run(self.work, run_id="same-risk")
        for candidate in ("C-002", "C-003"):
            set_table_cell(run / "05_candidate-portfolio.md", "candidate-routes", candidate, "Risk: low/medium/high", "low")
        reader = run / load_manifest(run)["primary_artifact"]
        edit_table(reader, "decision-summary", lambda h, rows: (h, [["low", *r[1:]] for r in rows]))
        self.assertValid(run)

    def test_nonzero_candidates_zero_eligible_pilots_and_useful_defer(self):
        run = make_run(self.work, run_id="all-defer")
        portfolio = run / "05_candidate-portfolio.md"
        for candidate in ("C-001", "C-002", "C-003"):
            for header in ("Openness gate: pass/conditional/fail/unknown", "Contribution gate: pass/conditional/fail/unknown", "Feasibility gate: pass/conditional/fail/unknown"):
                set_table_cell(portfolio, "opportunity-gates", candidate, header, "unknown")
            set_table_cell(portfolio, "opportunity-gates", candidate, "Overall: go/conditional-go/defer/no-go", "defer")
        edit_table(portfolio, "route-fast-pilots", lambda h, rows: (h, []))
        self.assertError(run, "next-actions")
        edit_table(run / "07_decision-log.md", "next-actions", lambda h, rows: (h, [
            ["audit existing equipment records", "search", "existing instrument inventory and acceptance sheets",
             "capability matrix with unavailable resources marked", f"{candidate} feasibility: observed access permits pilot; absent access retains defer"]
            for candidate in ("C-001", "C-002", "C-003")]))
        self.assertValid(run)

    def test_compact_reader_cards_preserve_route_ownership(self):
        run = make_run(self.work, run_id="compact")
        reader = run / load_manifest(run)["primary_artifact"]
        edit_table(reader, "recommended-routes", lambda h, rows: (
            ["Route", "Summary", "Disposition", "Decision ID"],
            [[r[0], "Bounded route; matched baseline, staged test, kill rule and retained dataset described below.",
              "Revise" if r[0] == "C-001" else "Keep", {"C-001": "D-002", "C-002": "D-005", "C-003": "D-006"}[r[0]]] for r in rows]))
        self.assertValid(run)
        edit_table(reader, "recommended-routes", lambda h, rows: (h, rows[:-1]))
        self.assertError(run, "decision-card ownership")

    def test_empty_pilot_resources_and_candidate_baseline_fail(self):
        for marker, column, fragment in (("route-fast-pilots", "Resource cap", "resource cap"), ("candidate-routes", "Strongest baseline", "Strongest baseline")):
            run = make_run(self.work, run_id=marker)
            set_table_cell(run / "05_candidate-portfolio.md", marker, "C-001", column, "none")
            self.assertError(run, fragment)

    def test_coverage_requires_selected_evidence_and_positive_known_count(self):
        run = make_run(self.work, run_id="coverage-unselected")
        set_table_cell(run / "02_search-log.md", "search-queries", "Q-001", "Evidence IDs", "none")
        self.assertError(run, "not selected by")
        run = make_run(self.work, run_id="coverage-unknown")
        set_table_cell(run / "02_search-log.md", "search-queries", "Q-001", "Results", "unknown")
        self.assertError(run, "cannot be covered")

    def test_out_of_scope_requires_a_real_boundary_and_stop_reason(self):
        for column in ("Blind spot or failure mode", "Next query or stop rationale"):
            for value in ("not applicable", "**N/A**", "not-applicable", "不适用", "none", "未知"):
                with self.subTest(column=column, value=value):
                    run = make_run(self.work, run_id="scope-" + str(len(list(self.work.iterdir()))))
                    path = run / "02_search-log.md"
                    for header, text in (
                        ("Query IDs", "none"), ("Relevant Evidence IDs", "none"),
                        ("Coverage status: covered/thin/query-failed/out-of-scope", "out-of-scope"),
                        ("Blind spot or failure mode", "Biological mechanisms are excluded from this inorganic device decision"),
                        ("Next query or stop rationale", "Stop this lane because no biological-to-hardware claim is being evaluated"),
                    ):
                        set_table_cell(path, "coverage-audit", "translation", header, text)
                    set_table_cell(path, "coverage-audit", "translation", column, value)
                    self.assertError(run, "requires a boundary and stop rationale")

    def test_explained_out_of_scope_remains_valid(self):
        run = make_run(self.work, run_id="explained-scope")
        path = run / "02_search-log.md"
        for header, text in (
            ("Query IDs", "none"), ("Relevant Evidence IDs", "none"),
            ("Coverage status: covered/thin/query-failed/out-of-scope", "out-of-scope"),
            ("Blind spot or failure mode", "Not applicable: this run tests an inorganic device, not a biological translation claim"),
            ("Next query or stop rationale", "No biological analogy is used; retain the electronic control and do not expand this lane"),
        ):
            set_table_cell(path, "coverage-audit", "translation", header, text)
        self.assertValid(run)

    def test_limit_with_unresolved_wording_does_not_become_direct_conflict(self):
        run = make_run(self.work, run_id="unresolved-limit")
        matrix = run / "03_evidence-matrix.md"
        set_table_cell(matrix, "claim-confidence", "B-001", "Consistency/conflict status", "unresolved evidence gap; adjacent limitation remains")
        set_table_cell(matrix, "contradictions", "B-001", "Tension type: direct-conflict/evidence-gap/condition-difference", "evidence-gap")
        set_table_cell(matrix, "contradictions", "B-001", "Adjudication: support-dominant/limit-dominant/condition-split/unresolved", "unresolved")
        self.assertValid(run)

    def test_typed_unresolved_conflict_cannot_hide_behind_claim_prose(self):
        run = make_run(self.work, run_id="typed-conflict")
        matrix = run / "03_evidence-matrix.md"
        set_table_cell(matrix, "evidence-records", "E-003", "Stance", "contradicts")
        set_table_cell(matrix, "contradictions", "B-001", "Tension type: direct-conflict/evidence-gap/condition-difference", "direct-conflict")
        set_table_cell(matrix, "contradictions", "B-001", "Adjudication: support-dominant/limit-dominant/condition-split/unresolved", "unresolved")
        self.assertError(run, "unresolved-direct-conflict")

    def test_source_chains_merge_prose_aliases_and_shared_data(self):
        for records in (
            [("doi:one", "chains=EC-001; sample A"), ("doi:one", "chains=EC-001; totally different prose")],
            [("doi:one", "chains=EC-001; sample A"), ("doi:one", "chains=EC-002; sample B")],
            [("doi:one", "chains=EC-001; study A"), ("doi:two", "chains=EC-001; shared dataset")],
        ):
            self.assertEqual(assess_chains(records).count, 1)
        self.assertEqual(assess_chains([]).count, 0)
        self.assertFalse(assess_chains([]).unresolved)
        self.assertTrue(assess_chains([("doi:one", "different words")]).unresolved)
        self.assertTrue(assess_chains([("doi:one", "chains=unknown; needs review")]).unresolved)
        self.assertEqual(assess_chains([("doi:one", "chains=EC-001; separate data"), ("doi:two", "chains=EC-002; separate data")]).count, 2)

    def test_chain_labels_without_source_or_basis_are_unresolved(self):
        for source in ("", "none", "unknown"):
            result = assess_chains([(source, "chains=EC-001; independently collected data")])
            self.assertTrue(result.unresolved)
            self.assertEqual(result.count, 0)
        for basis in ("", "basis=", "basis=unknown", "pending inspection"):
            self.assertTrue(assess_chains([("doi:one", "chains=EC-001; " + basis)]).unresolved)

    def test_canonical_doi_identity_keeps_valid_balanced_parentheses(self):
        self.assertEqual(canonical_links.normalize_identity("(https://doi.org/10.1234/ABC(2020))."), "doi:10.1234/abc(2020)")

    def test_strong_single_study_needs_attributable_independent_review(self):
        run = make_run(self.work, run_id="strong-single-study")
        matrix = run / "03_evidence-matrix.md"
        set_table_cell(matrix, "atomic-claims", "B-001", "Claim type", "mechanism")
        set_table_cell(matrix, "evidence-records", "E-002", "Independence/replication", "chains=EC-001; shared upstream data")
        self.assertError(run, "single-chain-broad-claim")
        set_table_cell(matrix, "claim-confidence", "B-001", "Independence/replication", "review=independent; reviewer=review-agent; basis=full methods and separate sample controls p4 Fig3; design=strong-multimethod")
        self.assertValid(run)
        self.assertFalse(independently_reviewed("review=independent; reviewer=unknown; basis=unreviewed"))
        self.assertFalse(independently_reviewed("design=strong-multimethod; persuasive design prose"))

    def test_zero_support_and_unknown_independence_are_not_single_chain(self):
        run = make_run(self.work, run_id="zero-support")
        matrix = run / "03_evidence-matrix.md"
        set_table_cell(matrix, "claim-confidence", "B-001", "Supporting Evidence IDs", "none")
        set_table_cell(matrix, "claim-confidence", "B-001", "Active cap codes", "single-chain-broad-claim")
        self.assertError(run, "must be Insufficient")
        self.assertError(run, "zero support or unknown independence")
        run = make_run(self.work, run_id="unknown-independence")
        matrix = run / "03_evidence-matrix.md"
        set_table_cell(matrix, "atomic-claims", "B-001", "Claim type", "mechanism")
        for eid in ("E-001", "E-002"):
            set_table_cell(matrix, "evidence-records", eid, "Independence/replication", "chains=unknown; data provenance requires review")
        self.assertError(run, "Broad High-confidence claim")
        self.assertFalse(any("must declare detected cap codes: single-chain" in e for e in self.errors(run)))

    def test_fulltext_depth_does_not_set_directness_or_independence(self):
        run = make_run(self.work, run_id="fulltext-supporting")
        matrix = run / "03_evidence-matrix.md"
        for eid in ("E-001", "E-002"):
            set_table_cell(matrix, "evidence-records", eid, "Directness", "supporting")
        errors = self.errors(run)
        self.assertTrue(any("High" in error for error in errors))
        self.assertFalse(any("indirect-only" in error for error in errors))

    def test_focus_single_candidate_keeps_baseline_and_fallback_design(self):
        parent = make_run(self.work, run_id="focus-parent")
        run = make_run(self.work, run_id="one-focus", mode="focus", parent=parent)
        filter_focus_routes(run, {"C-001"})
        self.assertValid(run)
        set_table_cell(run / "04_claim-mechanism-map.md", "claim-null-test-threshold", "C-001", "Strongest baseline", "none")
        self.assertError(run, "requires substantive Strongest baseline")

        run = make_run(self.work, run_id="one-focus-no-fallback", mode="focus", parent=parent)
        filter_focus_routes(run, {"C-001"})
        set_table_cell(run / "05_route-protocol.md", "route-boundaries", "C-001", "Comparator/fallback activation rule", "none")
        self.assertError(run, "incomplete kill/reversal/retained-value/activation card")

    def test_focus_zero_candidates_needs_atomic_decisions_and_information_check(self):
        parent = make_run(self.work, run_id="focus-parent")
        run = make_run(self.work, run_id="zero-focus", mode="focus", parent=parent)
        filter_focus_routes(run, set())
        self.assertValid(run)
        edit_table(run / "07_decision-log.md", "next-actions", lambda h, rows: (h, [["none"] * len(h)]))
        self.assertError(run, "claim-linked information check")

    def test_missing_chain_identity_requires_review_not_prose_independence(self):
        run = make_run(self.work, run_id="missing-chain")
        set_table_cell(run / "03_evidence-matrix.md", "evidence-records", "E-001", "Independence/replication", "independent group alpha")
        report = validate(run, workspace_root=self.workspace)
        self.assertTrue(any("requires review" in warning for warning in report.warnings))

    def test_malformed_candidate_header_is_diagnostic_not_exception(self):
        run = make_run(self.work, run_id="malformed-candidate")
        edit_table(run / "05_candidate-portfolio.md", "candidate-routes", lambda h, rows: (["Wrong baseline" if x == "Strongest baseline" else x for x in h], rows))
        self.assertError(run, "Strongest baseline")



@unittest.skipUnless(os.environ.get("ROM_CANONICAL_CHECKER"), "set ROM_CANONICAL_CHECKER for actual Deep Reading API integration")
class CanonicalIntegrationTests(unittest.TestCase):
    work_name = "canonical-integration"

    def setUp(self):
        self.work = reset_work(self.work_name)
        self.workspace = workspace_root()
        self.previous_checker = canonical_links.CHECKER_PATH
        checker = Path(os.environ["ROM_CANONICAL_CHECKER"])
        canonical_links.CHECKER_PATH = checker
        sys.path.insert(0, str(checker.parent))
        spec = importlib.util.spec_from_file_location("_rom_deepreading_fixture", checker.parent / "test_canonical_and_dependencies.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.canonical = self.work / "canonical"
        self.canonical.mkdir()
        module.fixture(self.canonical)
        self.main_ref = (self.canonical / "reading-report.md").as_posix() + "#claim=C%2D001"
        self.aux_ref = (self.canonical / "external-evidence-matrix.md").as_posix() + "#evidence=E%2D001"
        self.queue_refs = self.main_ref + "; " + self.aux_ref

    def tearDown(self):
        canonical_links.CHECKER_PATH = self.previous_checker
        cleanup_work(self.work_name)

    def make_imported(self, run_id):
        run = make_run(self.work, run_id=run_id)
        for path in run.glob("*.md"):
            text = path.read_text(encoding="utf-8").replace("10.1234/rom.001", "10.1234/main").replace("10.1234/rom.002", "10.1234/other")
            path.write_text(text, encoding="utf-8")
        matrix = run / "03_evidence-matrix.md"
        for eid, reference in (("E-001", self.main_ref), ("E-002", self.aux_ref)):
            set_table_cell(matrix, "evidence-records", eid, "verification_depth", "canonical-deep-read")
            set_table_cell(matrix, "evidence-records", eid, "Canonical cross-run ref", reference)
        for column, value in {
            "Paper key": "doi:10.1234/main",
            "Status: queued/in-progress/imported/blocked/skipped": "imported",
            "Deep Reading run": self.canonical.as_posix(),
            "Canonical refs": self.queue_refs,
            "Imported Evidence IDs": "E-001,E-002",
        }.items():
            set_table_cell(matrix, "deep-reading-handoff", "DR-001", column, value)
        return run

    def errors(self, run):
        return validate(run, workspace_root=self.workspace).errors

    def test_actual_main_and_auxiliary_import_and_workspace_relative_refs(self):
        before = {p.name: p.read_bytes() for p in self.canonical.iterdir()}
        run = self.make_imported("actual-import")
        self.assertEqual(self.errors(run), [])
        matrix = run / "03_evidence-matrix.md"
        text = matrix.read_text(encoding="utf-8")
        text = text.replace(self.canonical.as_posix(), self.canonical.relative_to(self.workspace).as_posix())
        matrix.write_text(text, encoding="utf-8")
        self.assertEqual(self.errors(run), [])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.canonical.iterdir()})

    def test_nonexistent_wrong_owner_record_and_identity_fail(self):
        other = self.work / "other"
        other.mkdir()
        (other / "reading-report.md").write_text("not canonical", encoding="utf-8")
        cases = [
            ("missing-file", "E-001", (self.canonical / "view-report-audit.md").as_posix(), "No such file"),
            ("wrong-owner", "E-001", (other / "reading-report.md").as_posix() + "#claim=C%2D001", "wrong run owner"),
            ("missing-record", "E-001", self.main_ref.replace("C%2D001", "C%2D999"), "does not exist"),
            ("wrong-record-owner", "E-001", self.main_ref.replace("reading-report", "paper-package"), "not owned by"),
            ("wrong-source", "E-002", self.main_ref, "own source identity"),
            ("bare-basename", "E-001", "reading-report.md#claim=C%2D001", "explicit run path"),
        ]
        for name, eid, reference, fragment in cases:
            with self.subTest(name=name):
                run = self.make_imported(name)
                set_table_cell(run / "03_evidence-matrix.md", "evidence-records", eid, "Canonical cross-run ref", reference)
                errors = self.errors(run)
                if name == "missing-file":
                    self.assertTrue(any("Canonical artifact does not exist" in e for e in errors), errors)
                else:
                    self.assertTrue(any(fragment in e for e in errors), errors)

    def test_handoff_status_is_bidirectionally_closed_and_duplicate_paper_rejected(self):
        run = self.make_imported("queued-import")
        matrix = run / "03_evidence-matrix.md"
        set_table_cell(matrix, "deep-reading-handoff", "DR-001", "Status: queued/in-progress/imported/blocked/skipped", "queued")
        errors = self.errors(run)
        self.assertTrue(any("queued but lists Imported" in e for e in errors), errors)
        self.assertTrue(any("exactly one imported handoff" in e for e in errors), errors)
        run = self.make_imported("duplicate-request")
        matrix = run / "03_evidence-matrix.md"
        edit_table(matrix, "deep-reading-handoff", lambda h, rows: (h, [*rows, ["DR-002", *rows[0][1:]]]))
        self.assertTrue(any("Duplicate Deep Reading request" in e for e in self.errors(run)))

    def test_real_checker_rejects_broken_canonical_structure(self):
        run = self.make_imported("broken-canonical")
        path = self.canonical / "external-evidence-matrix.md"
        path.write_text(path.read_text(encoding="utf-8").replace("| S-001 |", "| S-999 |"), encoding="utf-8")
        self.assertTrue(any("canonical structure invalid" in e for e in self.errors(run)))

    def test_valid_unread_auxiliary_is_not_full_depth_import(self):
        run = self.make_imported("unread-auxiliary")
        path = self.canonical / "auxiliary-literature-table.md"
        path.write_text(path.read_text(encoding="utf-8").replace("| full | verified |", "| unread | not-started |"), encoding="utf-8")
        path = self.canonical / "paper-package.md"
        path.write_text(path.read_text(encoding="utf-8").replace("| verified_external_source_count | 1 |", "| verified_external_source_count | 0 |"), encoding="utf-8")
        payload = canonical_links.load_checker()(self.canonical)
        self.assertTrue(payload["valid"], payload["errors"])
        self.assertTrue(any("fully read and verified source" in e for e in self.errors(run)))

        # Queue references may document an unread candidate without importing it.
        canonical_links.check_import(str(self.canonical), self.queue_refs,
                                    [("doi:10.1234/main", self.main_ref)],
                                    base=self.workspace, paper_key="doi:10.1234/main", cache={})

    def test_main_claim_without_locator_cannot_claim_canonical_full_depth(self):
        run = self.make_imported("main-no-locator")
        path = self.canonical / "reading-report.md"
        path.write_text(path.read_text(encoding="utf-8").replace("p. 2 Fig. 1", "blocked: full text not available"), encoding="utf-8")
        payload = canonical_links.load_checker()(self.canonical)
        self.assertTrue(payload["valid"], payload["errors"])
        self.assertTrue(any("verified main-paper locator" in e for e in self.errors(run)))


if __name__ == "__main__":
    unittest.main()
