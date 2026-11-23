from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
BASELINE_FILE = SKILL_DIR / "tests" / "baselines" / "legacy-runs.json"
VALIDATOR = SKILL_DIR / "scripts" / "validate_run.py"


def find_workspace_root() -> Path:
    value = os.environ.get("MAPPER_LEGACY_WORKSPACE")
    if not value:
        raise unittest.SkipTest("Set MAPPER_LEGACY_WORKSPACE for local immutable historical fixtures")
    root = Path(value).resolve()
    if not root.is_dir():
        raise AssertionError(f"Configured legacy workspace does not exist: {root}")
    return root


def tree_snapshot(root: Path) -> tuple[str, int, int]:
    rows: list[str] = []
    total_bytes = 0
    files = sorted(path for path in root.rglob("*") if path.is_file())
    for path in files:
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        size = len(payload)
        total_bytes += size
        relpath = path.relative_to(root).as_posix()
        rows.append(f"{relpath}\t{digest}\t{size}\n")
    tree_hash = hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()
    return tree_hash, len(files), total_bytes


class LegacyRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.workspace_root = find_workspace_root()
        cls.baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))

    def test_legacy_runs_are_immutable_and_keep_validation_contract(self) -> None:
        for expected in self.baseline["runs"]:
            with self.subTest(run=expected["name"]):
                run_dir = self.workspace_root / Path(expected["workspace_relpath"])
                before = tree_snapshot(run_dir)
                self.assertEqual(before[0], expected["tree_sha256"])
                self.assertEqual(before[1], expected["file_count"])
                self.assertEqual(before[2], expected["byte_count"])

                completed = subprocess.run(
                    [sys.executable, str(VALIDATOR), str(run_dir), "--strict", "--json"],
                    cwd=SKILL_DIR,
                    check=False,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                self.assertEqual(completed.returncode, expected["strict_validation"]["exit_code"], completed.stderr)
                payload = json.loads(completed.stdout)
                self.assertEqual(payload["summary"]["errors"], expected["strict_validation"]["errors"])
                self.assertEqual(payload["summary"]["warnings"], expected["strict_validation"]["warnings"])
                self.assertEqual(payload["summary"]["passed"], expected["strict_validation"]["passed"])

                after = tree_snapshot(run_dir)
                self.assertEqual(after, before, "Legacy validator must not mutate the run")


if __name__ == "__main__":
    unittest.main()
