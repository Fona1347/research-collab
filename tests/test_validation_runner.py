"""Check missing prerequisites without invoking services or installing anything."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("validation_runner", ROOT / "scripts/validate.py")
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class ValidationRunnerTests(unittest.TestCase):
    def test_missing_powershell_is_actionable_and_fails_requested_component(self):
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / "checks"
            argv = ["validate.py", "--component", "zotero", "--output-dir", str(output)]
            with patch.object(sys, "argv", argv), patch.object(runner.shutil, "which", return_value=None), \
                    patch.object(runner.subprocess, "run") as run, contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(), 1)
            run.assert_not_called()
            results = json.loads((output / "results.json").read_text())
            self.assertEqual(results[0]["status"], "blocked")
            self.assertIn("PowerShell 7", (output / "zotero.log").read_text())


if __name__ == "__main__":
    unittest.main()
