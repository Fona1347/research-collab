from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
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
        self.set_distribution("SKILL.md", "agents/openai.yaml", "LICENSE", "script.py")
        self.target = Path(self.temp.name) / "installed skills"
        self.backups = Path(self.temp.name) / "backups"
        self.dest = self.target / "sample-skill"

    def set_distribution(self, *paths):
        (self.skill / collection.DISTRIBUTION).write_text(
            json.dumps({"format": 1, "files": list(paths)}) + "\n", encoding="utf-8")

    def update_distribution(self, add=(), remove=()):
        current = json.loads((self.skill / collection.DISTRIBUTION).read_text())["files"]
        self.set_distribution(*sorted((set(current) | set(add)) - set(remove)))

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
        self.update_distribution(add=["second.py"])
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
        self.update_distribution(remove=["script.py"])
        update = self.install()
        self.assertFalse((self.dest / "script.py").exists())
        self.assertTrue((self.dest / "extra.txt").exists())
        collection.restore(Path(update["backup"]), skills_root=self.target, root=self.root)
        self.assertEqual((self.dest / "script.py").read_text(), "print('v1')\n")

    def test_restore_rejects_newer_local_edit(self):
        first = self.install()
        (self.dest / "script.py").write_text("newer", encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "changed since"):
            collection.restore(Path(first["backup"]), skills_root=self.target, root=self.root)

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

    def test_unlisted_source_cannot_be_published(self):
        (self.skill / "private-note.md").write_text("synthetic personal note", encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "Unlisted"):
            self.install()
        self.assertFalse(self.target.exists())

    def test_missing_declared_resource_rejected(self):
        self.update_distribution(add=["assets/required.dat"])
        with self.assertRaisesRegex(collection.GuardError, "missing distribution"):
            collection.package(["sample-skill"], Path(self.temp.name) / "missing.zip", self.root)

    def test_sensitive_formats_rejected_even_when_declared(self):
        for name in ("private.sqlite3", "private.p12", "private.tar.gz"):
            with self.subTest(name=name):
                p = self.skill / name
                p.write_bytes(b"SYNTHETIC, NOT A SECRET")
                self.update_distribution(add=[name])
                with self.assertRaisesRegex(collection.GuardError, "Non-distributable"):
                    collection.package(["sample-skill"], Path(self.temp.name) / "bad.zip", self.root)
                self.update_distribution(remove=[name])
                p.unlink()

    def test_legacy_archive_without_distribution_list_remains_readable(self):
        out = Path(self.temp.name) / "legacy.zip"
        payloads = {name: (self.skill / name).read_bytes()
                    for name in ("SKILL.md", "agents/openai.yaml", "LICENSE")}
        record = {"files": {name: collection.digest(data) for name, data in payloads.items()}}
        with zipfile.ZipFile(out, "w") as archive:
            archive.writestr("manifest.json", json.dumps({"format": 1, "skills": {"sample-skill": record}}))
            for name, data in payloads.items():
                archive.writestr(f"sample-skill/{name}", data)
        self.assertEqual(collection.check_archive(out)["format"], 1)

    def test_restore_binding_and_manifest_closure_fail_before_mutation(self):
        first = self.install()
        backup = Path(first["backup"])
        current = {p.name: p.read_bytes() for p in self.dest.iterdir() if p.is_file()}
        with self.assertRaisesRegex(collection.GuardError, "another target"):
            collection.restore(backup, skills_root=self.target / "different", root=self.root)
        info = json.loads((backup / "restore.json").read_text())
        info["after"].pop("script.py")
        (backup / "restore.json").write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "file set"):
            collection.restore(backup, skills_root=self.target, root=self.root)
        self.assertEqual(current, {p.name: p.read_bytes() for p in self.dest.iterdir() if p.is_file()})

    def test_restore_rejects_unowned_file_even_with_matching_after_hash(self):
        first = self.install()
        backup = Path(first["backup"])
        victim = self.dest / "personal-note.txt"
        victim.write_text("preserve", encoding="utf-8")
        info = json.loads((backup / "restore.json").read_text())
        info["before"]["personal-note.txt"] = None
        info["after"]["personal-note.txt"] = collection.digest(victim.read_bytes())
        (backup / "restore.json").write_text(json.dumps(info), encoding="utf-8")
        with self.assertRaisesRegex(collection.GuardError, "not owned"):
            collection.restore(backup, skills_root=self.target, root=self.root)
        self.assertEqual(victim.read_text(), "preserve")

    def test_revision_does_not_borrow_an_ancestor_commit(self):
        with patch.object(collection.subprocess, "run", return_value=SimpleNamespace(stdout=str(self.root.parent))) as run:
            self.assertEqual(collection.revision(self.root, ["sample-skill"]), "source-snapshot")
        self.assertEqual(run.call_count, 1)

    def test_revision_requires_all_managed_files_tracked(self):
        tracked = [f"skills/sample-skill/{p}" for p in collection.source_files(self.skill)]
        def git_result(command, **_):
            if "--show-toplevel" in command:
                return SimpleNamespace(stdout=str(self.root))
            if "rev-parse" in command:
                return SimpleNamespace(stdout="a" * 40)
            if "status" in command:
                return SimpleNamespace(stdout="")
            return SimpleNamespace(stdout=chr(0).join(tracked))
        with patch.object(collection.subprocess, "run", side_effect=git_result):
            self.assertEqual(collection.revision(self.root, ["sample-skill"]), "a" * 40)
            tracked.remove("skills/sample-skill/script.py")
            self.assertEqual(collection.revision(self.root, ["sample-skill"]), "working-tree")

    def test_invalid_other_component_does_not_block_selected_source(self):
        other = self.root / "skills/other-skill"
        other.mkdir()
        (other / "SKILL.md").write_text("not publishable", encoding="utf-8")
        tracked = [f"skills/sample-skill/{p}" for p in collection.source_files(self.skill)]
        replies = [SimpleNamespace(stdout=str(self.root)), SimpleNamespace(stdout="a" * 40),
                   SimpleNamespace(stdout=""), SimpleNamespace(stdout=chr(0).join(tracked))]
        with patch.object(collection.subprocess, "run", side_effect=replies):
            self.assertEqual(collection.revision(self.root, ["sample-skill"]), "a" * 40)

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
