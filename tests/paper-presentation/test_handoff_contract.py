"""Synthetic handoffs reuse the canonical fixture/API, never retrieve literature."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
READING = ROOT / "skills/paper-deep-reading/scripts"
sys.path.insert(0, str(READING))
from test_canonical_and_dependencies import fixture, table

spec = importlib.util.spec_from_file_location("handoff", ROOT / "skills/paper-presentation/scripts/check_handoff.py")
handoff = importlib.util.module_from_spec(spec)
spec.loader.exec_module(handoff)


class HandoffTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="synthetic handoff ")
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        fixture(self.root)
        (self.root / "view-report.md").write_text(
            "# Synthetic observation\nInternal Evidence: one pulse changes one device at 300 K. "
            "Transfer to other stacks and superiority are not established.\n", encoding="utf-8")
        self.states = dict.fromkeys(handoff.GATE_STATES, "pass")

    def audit(self, *, reference="C-001", sync="in-sync"):
        gates = table(["Gate", "Status", "Reader-facing limit and prohibited wording"],
            [[key, value, "No external priority claim" if value != "pass" else "none"]
             for key, value in self.states.items()])
        trace = table(["Report claim or judgment", "Report section or paragraph",
                       "Canonical C-*, N-*, or D-* IDs", "Main-paper locator or Evidence IDs",
                       "Intended wording strength", "Gate status", "Sync status"],
                      [["Pulse response", "Observation", reference, "p. 2 Fig. 1",
                        "Internal Evidence", "pass", sync]])
        (self.root / "view-report-audit.md").write_text(gates + "\n" + trace, encoding="utf-8")

    def check(self):
        before = {p.name: p.read_bytes() for p in self.root.iterdir()}
        result = handoff.check(self.root, READING / "check_canonical.py")
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.root.iterdir()})
        self.assertTrue(result["manual_review_required"])
        return result

    def test_all_pass_retains_manual_scientific_review(self):
        self.audit()
        result = self.check()
        self.assertEqual(result["readiness"], "presentation-ready", result["errors"])

    def test_scope_gaps_retained_without_requiring_zotero_or_download(self):
        for state in ("not-applicable", "pass-with-downgrade"):
            with self.subTest(state=state):
                self.states["G3"] = state
                self.audit()
                result = self.check()
                self.assertEqual(result["readiness"], "presentation-ready with evidence gaps", result["errors"])
                self.assertIn("No external priority claim", str(result["limits"]))

    def test_blocked_missing_or_unknown_gate_is_not_ready(self):
        self.states["G5"] = "pass-with-downgrade"
        self.audit()
        self.assertEqual(self.check()["readiness"], "not presentation-ready")
        self.states.pop("G5")
        self.audit()
        self.assertEqual(self.check()["readiness"], "not presentation-ready")
        (self.root / "view-report-audit.md").unlink()
        self.assertEqual(self.check()["readiness"], "not presentation-ready")

    def test_dangling_trace_and_stale_map_block(self):
        self.audit(reference="C-999")
        self.assertEqual(self.check()["readiness"], "not presentation-ready")
        self.audit(sync="stale")
        self.assertEqual(self.check()["readiness"], "not presentation-ready")

    def test_bad_canonical_does_not_pass_on_audit_claim_alone(self):
        self.audit()
        path = self.root / "external-evidence-matrix.md"
        path.write_text(path.read_text().replace("S-001", "S-999"), encoding="utf-8")
        self.assertEqual(self.check()["readiness"], "not presentation-ready")

    def test_legacy_requires_content_review_without_inventing_ids(self):
        (self.root / "paper-package.md").write_text("# Legacy package\n", encoding="utf-8")
        result = self.check()
        self.assertIsNone(result["readiness"])
        self.assertFalse(result["errors"])


if __name__ == "__main__":
    unittest.main()
