"""Offline behavioral regression for canonical integrity and capability preflight."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import check_canonical as canonical
import check_dependencies as dependencies


def table(headers, rows):
    return "\n".join(["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |", *["| " + " | ".join(row) + " |" for row in rows]]) + "\n"


def fixture(root, *, external=True):
    package = {"evidence_contract": "v1.1", "paper_identity": "Target paper; DOI 10.1234/main", "task": "focused-analysis", "validation": "custom", "DOI or canonical identifier": "10.1234/main", "Canonical title": "Target paper", "candidate_count": "1" if external else "0", "verified_external_source_count": "1" if external else "0", "cited_external_source_count": "0"}
    claims = ["C-001", "State changes under one pulse", "high", "direct measurement", "p. 2 Fig. 1", "one device, 300 K, fixed pulse", "none", "none", "mechanism: downgraded; method/provenance: closed", "supported"]
    (root / "paper-package.md").write_text(table(["Field", "Value"], list(package.items())), encoding="utf-8")
    (root / "reading-report.md").write_text(table([canonical.TABLES["claims"][1], *canonical.TABLES["claims"][3]], [claims]), encoding="utf-8")
    if external:
        source = ["S-001", "https://doi.org/10.1234/other", "Other / 2020", "query Q1", "C-001", "mechanism", "A", "direct", "unknown; same dataset not excluded", "same temperature", "boundary", "available", "not-needed", "not-needed", "full", "verified", "not-cited", "not-cited", "not-cited", "Used publisher full text"]
        evidence = ["E-001", "C-001", "S-001", "contextualizes", "direct measurement", "p. 3 Fig. 2", "300 K; other stack", "An independently reported observation bounds transfer", "not a matched replication", "moderate", "supported", "audit-only"]
        (root / "auxiliary-literature-table.md").write_text(table([canonical.TABLES["sources"][1], *canonical.TABLES["sources"][3]], [source]), encoding="utf-8")
        (root / "external-evidence-matrix.md").write_text(table([canonical.TABLES["evidence"][1], *canonical.TABLES["evidence"][3]], [evidence]), encoding="utf-8")


class CanonicalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def change(self, filename, before, after):
        path = self.root / filename
        text = path.read_text(encoding="utf-8")
        self.assertIn(before, text)
        path.write_text(text.replace(before, after), encoding="utf-8")

    def codes(self):
        return {x["code"] for x in canonical.validate_run(self.root)["errors"]}

    def test_valid_auxiliary_doi_can_differ_from_main(self):
        report = canonical.validate_run(self.root)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["main_identity"]["normalized_identifier"], "doi:10.1234/main")
        self.assertEqual(report["sources"]["S-001"]["normalized_identifier"], "doi:10.1234/other")
        self.assertEqual(report["evidence"]["E-001"]["Source ID"], "S-001")

    def test_main_only_needs_no_external_files(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            fixture(root, external=False)
            self.assertTrue(canonical.validate_run(root)["valid"])

    def test_missing_run(self):
        self.assertFalse(canonical.validate_run(self.root / "absent")["valid"])

    def test_invalid_claim_enum(self):
        self.change("reading-report.md", "| supported |", "| supported under conditions |")
        self.assertIn("invalid-enum", self.codes())

    def test_joint_text_is_not_claim_link(self):
        self.change("reading-report.md", "| none | none |", "| two devices, not simultaneous | none |")
        self.assertIn("invalid-reference-cell", self.codes())

    def test_role_needs_state(self):
        self.change("reading-report.md", "mechanism: downgraded", "mechanism")
        self.assertIn("role-state-missing", self.codes())

    def test_one_claim_per_evidence_row(self):
        self.change("external-evidence-matrix.md", "| E-001 | C-001 |", "| E-001 | C-001,C-999 |")
        self.assertIn("invalid-reference-cell", self.codes())

    def test_one_source_per_evidence_row(self):
        self.change("external-evidence-matrix.md", "| S-001 |", "| S-001,S-002 |")
        self.assertIn("invalid-reference-cell", self.codes())

    def test_dangling_id(self):
        self.change("external-evidence-matrix.md", "| S-001 |", "| S-999 |")
        self.assertIn("dangling-reference", self.codes())

    def test_duplicate_id(self):
        path = self.root / "external-evidence-matrix.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text + text.splitlines()[-1] + "\n", encoding="utf-8")
        self.assertIn("duplicate-id", self.codes())

    def test_duplicate_doi_is_not_independent_source(self):
        path = self.root / "auxiliary-literature-table.md"
        text = path.read_text(encoding="utf-8")
        duplicate = text.splitlines()[-1].replace("S-001", "S-002").replace("https://doi.org/10.1234/other", "DOI 10.1234/OTHER")
        path.write_text(text + duplicate + "\n", encoding="utf-8")
        report = canonical.validate_run(self.root)
        self.assertIn("duplicate-source-identity", {e["code"] for e in report["errors"]})
        self.assertEqual(report["counts"]["distinct_external_sources"], 1)

    def test_multiple_claims_same_source_still_one_source(self):
        path = self.root / "reading-report.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text + text.splitlines()[-1].replace("C-001", "C-002").replace("one pulse", "two pulses") + "\n", encoding="utf-8")
        path = self.root / "external-evidence-matrix.md"
        text = path.read_text(encoding="utf-8")
        path.write_text(text + text.splitlines()[-1].replace("E-001", "E-002").replace("C-001", "C-002") + "\n", encoding="utf-8")
        report = canonical.validate_run(self.root)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["counts"]["evidence"], 2)
        self.assertEqual(report["counts"]["verified_external_sources"], 1)

    def test_unread_source_cannot_be_verified(self):
        self.change("auxiliary-literature-table.md", "| full | verified |", "| unread | verified |")
        self.assertIn("verified-without-full-read", self.codes())

    def test_strong_needs_locator(self):
        self.change("external-evidence-matrix.md", "p. 3 Fig. 2", "unknown")
        self.change("external-evidence-matrix.md", "| moderate |", "| strong |")
        self.assertIn("strong-without-locator", self.codes())

    def test_counter_does_not_count_rows(self):
        self.change("paper-package.md", "| verified_external_source_count | 1 |", "| verified_external_source_count | 2 |")
        self.assertIn("source-count-mismatch", self.codes())

    def test_identity_conflict(self):
        self.change("paper-package.md", "| DOI or canonical identifier | 10.1234/main |", "| DOI or canonical identifier | 10.1234/wrong |")
        self.assertIn("main-identity-conflict", self.codes())

    def test_empty_claims_fail(self):
        path = self.root / "reading-report.md"
        path.write_text("\n".join(path.read_text(encoding="utf-8").splitlines()[:2]), encoding="utf-8")
        self.assertIn("empty-claim-registry", self.codes())

    def test_historical_output_directory_does_not_redirect_reading(self):
        path = self.root / "paper-package.md"
        path.write_text(path.read_text(encoding="utf-8") + "| output_directory | E:/missing/old-run |\n", encoding="utf-8")
        self.assertTrue(canonical.validate_run(self.root)["valid"])

    def test_parser_ignores_code_examples_and_accepts_escaped_pipe(self):
        text = "```md\n| Claim ID | Value |\n| --- | --- |\n| C-999 | fake |\n```\n" + table(["Field", "Value"], [["a", r"value\|two"]])
        parsed = canonical.parse_tables(text)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["rows"][0]["Value"], "value|two")

    def test_balanced_parenthesis_in_doi_is_preserved(self):
        self.assertEqual(canonical.normalize_identifier("DOI 10.1234/abc(2020)"), "doi:10.1234/abc(2020)")
        self.assertEqual(canonical.normalize_identifier("(https://doi.org/10.1234/ABC(2020))."), "doi:10.1234/abc(2020)")

    def test_main_source_row_does_not_increment_external_counts(self):
        self.change("auxiliary-literature-table.md", "10.1234/other", "10.1234/main")
        self.change("paper-package.md", "| candidate_count | 1 |", "| candidate_count | 0 |")
        self.change("paper-package.md", "| verified_external_source_count | 1 |", "| verified_external_source_count | 0 |")
        report = canonical.validate_run(self.root)
        self.assertTrue(report["valid"], report["errors"])
        self.assertEqual(report["counts"]["distinct_external_sources"], 0)

    def test_cited_source_requires_verified_state_and_key(self):
        self.change("auxiliary-literature-table.md", "| full | verified | not-cited |", "| full | blocked | cited |")
        self.assertTrue({"cited-unverified-source", "cited-without-key"} <= self.codes())

    def test_evidence_scoped_prose_is_not_enum(self):
        self.change("external-evidence-matrix.md", "| supported |", "| supported within fabricated structures |")
        self.assertIn("invalid-enum", self.codes())


@unittest.skipUnless(os.environ.get("DEEP_READING_FROZEN_ROOT"), "optional read-only frozen artifact regression")
class FrozenArtifactTests(unittest.TestCase):
    def run_result(self, name):
        return canonical.validate_run(Path(os.environ["DEEP_READING_FROZEN_ROOT"]) / name)

    def test_bfo_original_fails_joint_role_and_enum_checks(self):
        result = self.run_result("Zhiwei Chen-2023-Nat Commun-All-ferroelectric-implementation-reservoir-computing")
        codes = {r["code"] for r in result["errors"]}
        self.assertTrue({"invalid-reference-cell", "role-state-missing", "invalid-enum", "missing-table"} <= codes)
        self.assertEqual(result["counts"]["distinct_external_sources"], 3)
        self.assertEqual(result["counts"]["verified_external_sources"], 2)

    def test_lancaster_original_fails_multi_claim_rows(self):
        result = self.run_result("Suzanne Lancaster-2022-Front Nanotechnol-Investigating-charge-trapping-transient-measurements")
        broken = {r["record_id"] for r in result["errors"] if r["code"] == "invalid-reference-cell"}
        self.assertEqual(broken, {"E-001", "E-002", "E-004"})
        self.assertEqual(result["counts"]["verified_external_sources"], 1)

    def test_mpb_original_role_and_reference_issues_are_visible(self):
        result = self.run_result("Jangsaeng Kim-2024-Nat Commun-Analog-reservoir-computing-mixed-phase-boundary")
        self.assertEqual({r["code"] for r in result["errors"]}, {"role-state-missing", "invalid-reference-cell"})
        self.assertEqual(result["counts"]["verified_external_sources"], 2)


class DependencyTests(unittest.TestCase):
    def report(self, *args):
        parsed = dependencies.parse_args(list(args))
        with patch.object(dependencies, "env_present", return_value=False), patch.object(dependencies, "find_skill", return_value=None), patch.object(dependencies, "command_present", return_value=False), patch.object(dependencies, "module_present", return_value=True):
            return dependencies.build_report(parsed)

    def test_standard_without_sciverse_with_equivalent_routes_passes(self):
        report = self.report("--mode", "standard", "--input-kind", "pdf", "--agent-check", "external-discovery.route", "--agent-check", "external-fulltext.route")
        self.assertEqual(report["summary"]["exit_code"], 0)
        sciverse = [r for r in report["results"] if "sciverse" in r["name"].lower()]
        self.assertTrue(all(not r["required"] for r in sciverse))

    def test_standard_requires_capabilities_not_provider(self):
        report = self.report("--mode", "standard", "--input-kind", "full-text")
        self.assertEqual(set(report["summary"]["required_blockers"]), {"external-discovery.route", "external-fulltext.route"})

    def test_existing_lookup_flags_remain_compatible(self):
        report = self.report("--mode", "standard", "--input-kind", "full-text", "--agent-check", "research-lookup-enhanced.skill", "--agent-check", "research-lookup-enhanced.http-fetch")
        self.assertEqual(report["summary"]["exit_code"], 0)

    def test_custom_retains_mode_and_disables_upload(self):
        report = self.report("--mode", "custom", "--custom-scope", "standard", "--input-kind", "pdf", "--agent-check", "external-discovery.route", "--agent-check", "external-fulltext.route")
        self.assertEqual(report["mode"], "custom")
        self.assertEqual(report["effective_mode"], "standard")
        self.assertFalse(report["permissions_granted_by_preflight"])
        self.assertFalse(report["remote_parsing_applicable"])
        self.assertEqual(report["summary"]["exit_code"], 0)

    def test_custom_local_does_not_activate_network(self):
        report = self.report("--mode", "custom", "--custom-scope", "fully-local", "--input-kind", "pdf", "--agent-check", "external-discovery.route")
        self.assertEqual(report["summary"]["exit_code"], 0)
        self.assertTrue(all(r["status"] == "NOT-APPLICABLE" for r in report["results"] if r["name"].startswith("external-")))

    def test_custom_cannot_guess_projection_or_override_local(self):
        for args in (["--mode", "custom"], ["--mode", "custom", "--custom-scope", "fully-local", "--allow-remote-parsing"]):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                dependencies.parse_args(args)


if __name__ == "__main__":
    unittest.main()
