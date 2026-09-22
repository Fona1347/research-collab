from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("collection", ROOT / "scripts" / "skills.py")
collection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collection)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="research collab ")
        self.root = Path(self.temp.name) / "repo"
        self.skill = self.root / "skills" / "sample-skill"
        (self.skill / "agents").mkdir(parents=True)
        (self.skill / "SKILL.md").write_text("---\nname: sample-skill\ndescription: Synthetic test skill.\n---\n# Sample\n", encoding="utf-8")
        (self.skill / "agents/openai.yaml").write_text('interface:\n  display_name: "Sample"\n', encoding="utf-8")
        (self.skill / "LICENSE").write_text("Synthetic fixture license\n", encoding="utf-8")
        (self.skill / "script.py").write_text("print('v1')\n", encoding="utf-8")
        self.target = Path(self.temp.name) / "installed skills"
        self.backups = Path(self.temp.name) / "backups"
        self.dest = self.target / "sample-skill"

    def tearDown(self):
        self.temp.cleanup()

    def install(self, **kwargs):
        return collection.install("sample-skill", self.target, self.backups, root=self.root, **kwargs)

    def test_preview_writes_nothing(self):
        result = self.install(dry_run=True)
        self.assertEqual(result["status"], "preview")
        self.assertFalse(self.target.exists())
        self.assertFalse(self.backups.exists())
        out = Path(self.temp.name) / "missing output" / "package.zip"
        collection.package(["sample-skill"], out, self.root, dry_run=True)
        self.assertFalse(out.parent.exists())

    def test_repeat_install_and_unknown_files_preserved(self):
        self.install()
        local = self.dest / "config/local.json"
        local.parent.mkdir()
        local.write_text('{"user": "preserve"}', encoding="utf-8")
        note = self.dest / "my-note.txt"
        note.write_text("not managed", encoding="utf-8")
        result = self.install()
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(local.read_text(), '{"user": "preserve"}')
        self.assertEqual(note.read_text(), "not managed")

    def test_managed_drift_blocks_without_overwriting(self):
        self.install()
        (self.dest / "script.py").write_text("my edit", encoding="utf-8")
        (self.skill / "script.py").write_text("upstream edit", encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "drift"):
            self.install()
        self.assertEqual((self.dest / "script.py").read_text(), "my edit")

    def test_unmanaged_collision_requires_reviewed_target_bound_baseline(self):
        self.dest.mkdir(parents=True)
        p = self.dest / "script.py"
        p.write_text("installed version", encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "conflicting"):
            self.install()
        baseline = {"path": str(self.dest), "files": {"script.py": collection.digest(p.read_bytes())}}
        wrong = {**baseline, "path": str(self.target / "another-skill")}
        with self.assertRaisesRegex(collection.GuardError, "another target"):
            self.install(baseline=wrong)
        p.write_text("changed after review", encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "baseline changed"):
            self.install(baseline=baseline)
        p.write_text("installed version", encoding="utf-8")
        self.install(baseline=baseline)
        self.assertEqual(p.read_text(), "print('v1')\n")

    def test_failure_rolls_back_files_and_receipt(self):
        self.install()
        receipt = (self.dest / collection.RECEIPT).read_bytes()
        original = (self.dest / "script.py").read_bytes()
        (self.skill / "script.py").write_text("print('v2')\n", encoding="utf-8")
        (self.skill / "second.py").write_text("new file\n", encoding="utf-8")
        real_write = collection.atomic_write
        calls = 0
        def flaky(path, data):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("simulated write failure")
            return real_write(path, data)
        with patch.object(collection, "atomic_write", side_effect=flaky):
            with self.assertRaisesRegex(OSError, "simulated"):
                self.install()
        self.assertEqual((self.dest / "script.py").read_bytes(), original)
        self.assertFalse((self.dest / "second.py").exists())
        self.assertEqual((self.dest / collection.RECEIPT).read_bytes(), receipt)

    def test_only_previously_managed_stale_files_removed_and_restorable(self):
        self.install()
        (self.dest / "extra.txt").write_text("keep", encoding="utf-8")
        (self.skill / "script.py").unlink()
        update = self.install()
        self.assertFalse((self.dest / "script.py").exists())
        self.assertTrue((self.dest / "extra.txt").exists())
        collection.restore(Path(update["backup"]), root=self.root)
        self.assertEqual((self.dest / "script.py").read_text(), "print('v1')\n")

    def test_restore_rejects_newer_local_edit(self):
        first = self.install()
        (self.dest / "script.py").write_text("newer", encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "changed since"):
            collection.restore(Path(first["backup"]), root=self.root)

    def test_package_reproducible_and_excludes_local_config(self):
        (self.skill / "config").mkdir()
        (self.skill / "config/local.json").write_text('{"private":"local"}', encoding="utf-8")
        out = Path(self.temp.name) / "first.zip"
        other = Path(self.temp.name) / "second.zip"
        collection.package(["sample-skill"], out, self.root)
        collection.package(["sample-skill"], other, self.root)
        self.assertEqual(out.read_bytes(), other.read_bytes())
        manifest = collection.check_archive(out)
        self.assertEqual(set(manifest["skills"]), {"sample-skill"})
        with zipfile.ZipFile(out) as z:
            self.assertIn("sample-skill/LICENSE", z.namelist())
            self.assertNotIn("sample-skill/config/local.json", z.namelist())

    def test_secret_like_file_blocks_package(self):
        (self.skill / ".env").write_text("NOT_A_REAL_SECRET=fixture", encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "Non-distributable"):
            collection.package(["sample-skill"], Path(self.temp.name) / "bad.zip", self.root)

    def test_traversal_and_bad_archive_rejected(self):
        for rel in ("../outside", "/absolute", "C:/outside", "dir\\outside"):
            with self.subTest(path=rel), self.assertRaises(collection.GuardError):
                collection.member(self.dest, rel)
        out = Path(self.temp.name) / "bad.zip"
        with zipfile.ZipFile(out, "w") as z:
            z.writestr("../outside", "bad")
            z.writestr("manifest.json", "{}")
        with self.assertRaises(collection.GuardError):
            collection.check_archive(out)

    def test_install_cannot_target_source(self):
        with self.assertRaisesRegex(collection.GuardError, "canonical"):
            collection.install("sample-skill", self.root / "skills", self.backups, root=self.root)

    def test_source_symlink_rejected(self):
        link = self.skill / "linked.txt"
        try:
            link.symlink_to(self.skill / "SKILL.md")
        except OSError:
            self.skipTest("This Windows account cannot create file symlinks")
        with self.assertRaises(collection.GuardError):
            collection.source_files(self.skill)


if __name__ == "__main__":
    unittest.main()
