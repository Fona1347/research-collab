"""Regression for canonical owner files and Markdown record boundaries."""

import os
import tempfile
import shutil
import unittest
from pathlib import Path

import check_canonical as canonical
from test_canonical_and_dependencies import fixture, table


def windows_io(path):
    raw = str(path.absolute())
    if os.name == "nt" and not raw.startswith("\\\\?\\"):
        raw = "\\\\?\\UNC\\" + raw[2:] if raw.startswith("\\\\") else "\\\\?\\" + raw
    return Path(raw)


class CanonicalBoundaryTests(unittest.TestCase):
    def test_nested_fence_does_not_create_canonical_records(self):
        sample = table(["Claim ID", "Value"], [["C-999", "example only"]])
        markdown = "````markdown\n```\n" + sample + "```\n````\n" + table(["Field", "Value"], [["real", "value"]])
        parsed = canonical.parse_tables(markdown)
        self.assertEqual([t["headers"][0] for t in parsed], ["Field"])

    def test_unmatched_fence_kind_does_not_end_example(self):
        sample = table(["Claim ID", "Value"], [["C-999", "example only"]])
        self.assertEqual(canonical.parse_tables("```markdown\n~~~\n" + sample + "```\n"), [])

    def test_duplicate_field_value_headers_are_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            fixture(root)
            owner = root / "paper-package.md"
            owner.write_text(owner.read_text(encoding="utf-8") + "\n" + table(["Field", "Value", "Value"], [["extra", "one", "two"]]), encoding="utf-8")
            result = canonical.validate_run(root)
            self.assertFalse(result["valid"])
            self.assertIn("table-columns", {e["code"] for e in result["errors"]})

    def test_malformed_run_field_is_not_silently_discarded(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            fixture(root)
            owner = root / "paper-package.md"
            owner.write_text(owner.read_text(encoding="utf-8") + "| materialized_aux_pdf_count | 1 | broken extra cell |\n", encoding="utf-8")
            result = canonical.validate_run(root)
            self.assertFalse(result["valid"])
            self.assertIn("malformed-row", {e["code"] for e in result["errors"]})

    def test_canonical_owner_cannot_alias_another_runs_file(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name) / "run"
            root.mkdir()
            fixture(root)
            owner = root / "reading-report.md"
            target = Path(name) / "outside-reading-report.md"
            owner.replace(target)
            try:
                owner.symlink_to(target)
            except OSError as exc:
                self.skipTest(f"File symlink unavailable: {exc}")
            result = canonical.validate_run(root)
            self.assertFalse(result["valid"])
            self.assertIn("canonical-owner-mismatch", {e["code"] for e in result["errors"]})
            self.assertNotIn("reading-report.md", result["artifacts"])

    @unittest.skipUnless(os.name == "nt", "Windows MAX_PATH regression")
    def test_existing_long_path_is_read_without_changing_record_identity(self):
        name = tempfile.mkdtemp(prefix="deep-canonical-long-")
        try:
            root = Path(name) / ("a" * 80) / ("b" * 80) / ("c" * 80)
            io_root = windows_io(root)
            io_root.mkdir(parents=True)
            fixture(io_root)
            result = canonical.validate_run(root)
            self.assertTrue(result["valid"], result["errors"])
            self.assertEqual(result["main_identity"]["normalized_identifier"], "doi:10.1234/main")
            self.assertEqual(len(result["artifacts"]), 4)
        finally:
            # Remove only this test-owned, resolved temporary directory.
            target = windows_io(Path(name)).resolve()
            self.assertEqual(target.parent, windows_io(Path(tempfile.gettempdir())).resolve())
            self.assertTrue(target.name.startswith("deep-canonical-long-"))
            shutil.rmtree(target)


if __name__ == "__main__":
    unittest.main()
