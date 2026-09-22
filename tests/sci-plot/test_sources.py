from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sci_plot.errors import SourceError
from sci_plot.sources import (
    approve_source,
    check_sources,
    load_manifest,
    source_status,
)

SHA = "a" * 40
APPROVED = "b" * 40

MANIFEST = """schema_version = 1

[[sources]]
id = "pubfig"
url = "https://github.com/Galaxy-Dawn/pubfig"
github = "Galaxy-Dawn/pubfig"
branch = "main"
role = "optional-preferred-runtime"
release_tracking = true
last_checked = ""
last_approved_ref = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
last_approved_version = "0.3.0"
latest_seen_ref = ""
latest_seen_version = ""
adapter_status = "adapter"
watch_paths = ["pyproject.toml", "src/pubfig/export"]
notes = "safe"
"""


class FakeClient:
    def get_json(self, endpoint: str, *, allow_not_found: bool = False):
        if "/commits/" in endpoint:
            return {
                "sha": SHA,
                "commit": {"committer": {"date": "2026-07-22T00:00:00Z"}},
            }
        if endpoint.endswith("/releases/latest"):
            return {"tag_name": "v0.3.1", "html_url": "https://example.invalid/release"}
        if endpoint.endswith("/tags?per_page=1"):
            return [{"name": "v0.3.1", "commit": {"sha": SHA}}]
        if "/compare/" in endpoint:
            return {
                "status": "ahead",
                "files": [
                    {"filename": "pyproject.toml"},
                    {"filename": "src/pubfig/export/save.py"},
                ],
            }
        raise AssertionError(endpoint)


class SourceTests(unittest.TestCase):
    def _manifest(self, root: Path) -> Path:
        path = root / "upstream" / "sources.toml"
        path.parent.mkdir()
        path.write_text(MANIFEST, encoding="utf-8")
        return path

    def test_status_is_local_and_check_is_read_only_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = self._manifest(Path(raw))
            before = path.read_bytes()
            status = source_status(path)
            self.assertFalse(status["sources"][0]["pending_update"])
            report = check_sources(path, record=False, client=FakeClient())
            self.assertEqual(path.read_bytes(), before)
            checked = report["sources"][0]
            self.assertTrue(checked["pending_update"])
            self.assertEqual(checked["latest_ref"], SHA)
            self.assertEqual(checked["latest_tag"], "v0.3.1")
            self.assertIn("dependencies", checked["risks"])
            self.assertIn("output-behavior", checked["risks"])
            self.assertFalse(report["environment_modified"])

    def test_record_and_approve_require_all_gates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = self._manifest(root)
            check_sources(path, record=True, client=FakeClient())
            recorded = load_manifest(path)["sources"][0]
            self.assertEqual(recorded["latest_seen_ref"], SHA)
            self.assertEqual(recorded["latest_seen_tag"], "v0.3.1")
            self.assertEqual(recorded["latest_seen_tag_ref"], SHA)
            self.assertEqual(recorded["latest_seen_version"], "0.3.1")
            self.assertEqual(recorded["latest_change_count"], 2)
            self.assertEqual(
                recorded["latest_risks"],
                ["dependencies", "output-behavior"],
            )

            with self.assertRaisesRegex(SourceError, "--approve"):
                approve_source(
                    path,
                    source_id="pubfig",
                    ref=SHA,
                    approve=False,
                    tests_passed=True,
                )
            with self.assertRaisesRegex(SourceError, "--tests-passed"):
                approve_source(
                    path,
                    source_id="pubfig",
                    ref=SHA,
                    approve=True,
                    tests_passed=False,
                )
            result = approve_source(
                path,
                source_id="pubfig",
                ref=SHA,
                approve=True,
                tests_passed=True,
            )
            approved = load_manifest(path)["sources"][0]
            self.assertEqual(approved["last_approved_ref"], SHA)
            self.assertEqual(approved["last_approved_tag"], "v0.3.1")
            self.assertEqual(approved["previous_approved_ref"], APPROVED)
            self.assertEqual(approved["last_approved_version"], "0.3.1")
            self.assertFalse(result["runtime_modified"])
            self.assertEqual(result["change_summary"]["changed_file_count"], 2)
            self.assertTrue(Path(result["audit_log"]).is_file())
            self.assertEqual(len(approved["approval_history"]), 1)
            self.assertFalse(source_status(path)["sources"][0]["pending_update"])
            self.assertEqual(approved["latest_compare_status"], "identical")
            self.assertEqual(approved["latest_change_count"], 0)

    def test_manifest_embeds_audit_if_secondary_log_fails(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = self._manifest(root)
            check_sources(path, record=True, client=FakeClient())
            with patch("sci_plot.sources._append_audit", side_effect=OSError("denied")):
                result = approve_source(
                    path,
                    source_id="pubfig",
                    ref=SHA,
                    approve=True,
                    tests_passed=True,
                )
            approved = load_manifest(path)["sources"][0]
            self.assertEqual(approved["last_approved_ref"], SHA)
            self.assertEqual(len(approved["approval_history"]), 1)
            self.assertIn("embedded atomically", result["audit_warning"])

    def test_untagged_head_is_not_labeled_as_a_release(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = self._manifest(root)
            check_sources(path, record=True, client=FakeClient())
            manifest = load_manifest(path)
            source = manifest["sources"][0]
            source["latest_seen_tag_ref"] = APPROVED
            from sci_plot.sources import write_manifest_atomic

            write_manifest_atomic(path, manifest)
            result = approve_source(
                path,
                source_id="pubfig",
                ref=SHA,
                approve=True,
                tests_passed=True,
            )
            approved = load_manifest(path)["sources"][0]
            self.assertEqual(approved["last_approved_tag"], "")
            self.assertEqual(approved["last_approved_version"], "")
            self.assertEqual(result["approved_version"], "")
            self.assertFalse(source_status(path)["sources"][0]["pending_update"])

    def test_identical_comparison_is_not_reported_as_pending(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = self._manifest(Path(raw))
            manifest = load_manifest(path)
            source = manifest["sources"][0]
            source["latest_seen_ref"] = SHA
            source["latest_compare_status"] = "identical"
            from sci_plot.sources import write_manifest_atomic

            write_manifest_atomic(path, manifest)
            self.assertFalse(source_status(path)["sources"][0]["pending_update"])

    def test_non_sha_cannot_be_approved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = self._manifest(Path(raw))
            with self.assertRaisesRegex(SourceError, "immutable"):
                approve_source(
                    path,
                    source_id="pubfig",
                    ref="main",
                    approve=True,
                    tests_passed=True,
                )

    def test_packaged_manifest_cannot_be_recorded_or_approved(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = self._manifest(Path(raw))
            before = path.read_bytes()
            with patch("sci_plot.sources._PACKAGED_MANIFEST", path):
                with self.assertRaisesRegex(SourceError, "immutable baseline"):
                    check_sources(path, record=True, client=FakeClient())
                with self.assertRaisesRegex(SourceError, "immutable baseline"):
                    approve_source(
                        path,
                        source_id="pubfig",
                        ref=SHA,
                        approve=True,
                        tests_passed=True,
                    )
            self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
