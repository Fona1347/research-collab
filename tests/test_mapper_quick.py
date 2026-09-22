"""Offline Quick initializer behavior, independent from Full Mapper's schema."""
import contextlib
from datetime import date
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/research-opportunity-mapper-quick"
spec = importlib.util.spec_from_file_location("quick_initializer", SKILL / "scripts/init_run.py")
initializer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initializer)


class QuickInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="quick fixture ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def invoke(self, *extra):
        argv = ["init_run.py", "--domain", "synthetic-interface", "--output", str(self.root), *extra]
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()):
            return initializer.main()

    def assert_coherent(self, day):
        run = self.root / f"{day}-synthetic-interface"
        manifest = json.loads((run / "run-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["schema_version"], "1.2")
        self.assertEqual(manifest["skill"], "research-opportunity-mapper-quick")
        self.assertEqual(manifest["primary_artifact"], f"map_report_synthetic-interface_{day}.md")
        self.assertEqual(manifest["run_id"], run.name)
        self.assertEqual(set(manifest["artifact_files"]),
                         {p.name for p in run.glob("*.md")})
        report = (run / manifest["primary_artifact"]).read_text(encoding="utf-8")
        self.assertIn(f"报告日期：{day}", report)
        self.assertNotIn("{{", report)
        return run

    def test_date_is_coherent_across_midnight(self):
        with patch.object(initializer, "date", wraps=date) as clock:
            clock.today.side_effect = [date(2026, 9, 22), date(2026, 9, 23), date(2026, 9, 24)]
            self.assertEqual(self.invoke(), 0)
        self.assert_coherent("2026-09-22")

    def test_explicit_date_and_existing_run_preserved(self):
        self.assertEqual(self.invoke("--date", "2026-01-02"), 0)
        run = self.assert_coherent("2026-01-02")
        original = {p.name: p.read_bytes() for p in run.iterdir()}
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.invoke("--date", "2026-01-02"), 2)
        self.assertEqual(original, {p.name: p.read_bytes() for p in run.iterdir()})

    def test_invalid_date_creates_nothing(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.invoke("--date", "2026-02-30")
        self.assertEqual(list(self.root.iterdir()), [])

    def test_missing_templates_create_nothing(self):
        empty = self.root / "empty templates"
        empty.mkdir()
        with patch.object(initializer, "TEMPLATE_DIR", empty), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(self.invoke("--date", "2026-01-02"), 2)
        self.assertEqual(list(self.root.iterdir()), [empty])

    def test_template_is_not_misreported_as_complete(self):
        self.invoke("--date", "2026-01-02")
        run = self.assert_coherent("2026-01-02")
        result = subprocess.run([sys.executable, str(SKILL / "scripts/validate_run.py"),
                                 str(run), "--strict", "--json"],
                                capture_output=True, text=True, encoding="utf-8", check=False)
        self.assertEqual(result.returncode, 1)
        self.assertTrue(json.loads(result.stdout)["errors"])


if __name__ == "__main__":
    unittest.main()
