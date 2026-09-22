#!/usr/bin/env python3
"""Small, dependency-free collection validator, packager and guarded installer."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RECEIPT = ".research-collab-install.json"
DISTRIBUTION = "distribution.json"
LOCAL_FILES = {"config/local.json", "profiles/local-capability-profile.md", ".paper-collab.yaml"}
EXCLUDED_DIRS = {".git", ".local", ".venv", "__pycache__", ".pytest_cache", ".work", "dist", "build"}
FORBIDDEN_SUFFIXES = {".pdf", ".zip", ".7z", ".tar", ".tar.gz", ".tar.bz2", ".tar.xz",
                      ".sqlite", ".sqlite3", ".db", ".pem", ".key", ".pfx", ".p12"}
EXCLUDED_FILES = {".DS_Store", "Thumbs.db"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class GuardError(ValueError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def no_links(path: Path) -> None:
    for part in (path, *path.parents):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise GuardError(f"Path traverses a link/reparse point: {part}")


def member(root: Path, relative: str) -> Path:
    part = PurePosixPath(relative)
    if not relative or "\\" in relative or ":" in relative or part.is_absolute() or any(x in ("..", ".") for x in relative.split("/")):
        raise GuardError(f"Unsafe relative path: {relative}")
    result = root.joinpath(*part.parts)
    if not result.resolve().is_relative_to(root.resolve()):
        raise GuardError("Path escapes target")
    no_links(result)
    return result


def distributable(relative: str) -> None:
    path = PurePosixPath(relative)
    if (relative in LOCAL_FILES or path.name == RECEIPT
            or any(p in EXCLUDED_DIRS or p.endswith(".egg-info") for p in path.parts)
            or any(path.name.lower().endswith(suffix) for suffix in FORBIDDEN_SUFFIXES)
            or (path.name.lower().startswith(".env") and path.name != ".env.example")):
        raise GuardError(f"Non-distributable file: {relative}")


def distribution_paths(value) -> set[str]:
    if (not isinstance(value, dict) or value.get("format") != 1
            or not isinstance(value.get("files"), list)
            or not all(isinstance(p, str) for p in value["files"])):
        raise GuardError("Invalid distribution.json; expected format 1 and a file list")
    paths = value["files"]
    if len(paths) != len(set(paths)) or DISTRIBUTION in paths:
        raise GuardError("Distribution list must contain distinct files, excluding itself")
    for rel in paths:
        # member() also checks path traversal when the listed file is read.
        distributable(rel)
    return {*paths, DISTRIBUTION}


def source_files(skill: Path) -> dict[str, bytes]:
    no_links(skill)
    inventory = member(skill, DISTRIBUTION)
    if not inventory.is_file():
        raise GuardError(f"{skill.name}: missing explicit {DISTRIBUTION}")
    declared = distribution_paths(load_json(inventory))
    for rel in declared:
        member(skill, rel)
    result = {}
    for folder, dirs, names in os.walk(skill, followlinks=False):
        folder = Path(folder)
        for name in list(dirs):
            if name in EXCLUDED_DIRS or name.endswith(".egg-info"):
                dirs.remove(name)
            else:
                no_links(folder / name)
        for name in names:
            p = folder / name
            rel = p.relative_to(skill).as_posix()
            if rel in LOCAL_FILES or name in (RECEIPT, *EXCLUDED_FILES) or p.suffix in (".pyc", ".pyo"):
                continue
            no_links(p)
            distributable(rel)
            if rel not in declared:
                raise GuardError(f"Unlisted source file: {skill.name}/{rel}; review it before adding to {DISTRIBUTION}")
            result[rel] = p.read_bytes()
    missing = declared - result.keys()
    if missing:
        raise GuardError(f"{skill.name}: missing distribution files {sorted(missing)}")
    return dict(sorted(result.items()))


def skill_names(root: Path = ROOT) -> list[str]:
    return sorted(p.name for p in (root / "skills").iterdir() if (p / "SKILL.md").is_file())


def select(names: list[str] | None, root: Path = ROOT) -> list[str]:
    available = skill_names(root)
    chosen = names or available
    if not chosen or len(chosen) != len(set(chosen)) or any(n not in available or not NAME_RE.fullmatch(n) for n in chosen):
        raise GuardError("Select distinct installed source names from: " + ", ".join(available))
    return sorted(chosen)


def validate_skill(name: str, root: Path = ROOT) -> dict:
    files = source_files(root / "skills" / name)
    required = {"SKILL.md", "agents/openai.yaml", "LICENSE"}
    if required - files.keys():
        raise GuardError(f"{name}: missing required files {sorted(required - files.keys())}")
    entry = files["SKILL.md"].decode("utf-8-sig")
    front = re.match(r"\A---\s*\n(.*?)\n---", entry, re.S)
    if not front or not re.search(rf"(?m)^name:\s*{re.escape(name)}\s*$", front[1]) or not re.search(r"(?m)^description:\s*\S", front[1]):
        raise GuardError(f"{name}: invalid Skill identity or description")
    for rel, payload in files.items():
        if not rel.endswith(".md"):
            continue
        text = payload.decode("utf-8-sig")
        for target in re.findall(r"\[[^\]]+\]\(([^)\s]+)\)", text):
            target = target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:") or "<" in target:
                continue
            if target.endswith(".md") and not ((root / "skills" / name / rel).parent / target).is_file():
                raise GuardError(f"{name}/{rel}: unresolved link {target}")
    hashes = {p: digest(v) for p, v in files.items()}
    return {"skill": name, "files": hashes, "tree_sha256": digest(json_bytes(hashes))}


def revision(root: Path = ROOT, names: list[str] | None = None) -> str:
    cmd = ["git", "-c", f"safe.directory={root}", "-C", str(root)]
    try:
        top = subprocess.run(cmd + ["rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True).stdout.strip()
        if Path(top).resolve() != root.resolve():
            return "source-snapshot"
        head = subprocess.run(cmd + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(cmd + ["status", "--porcelain"], capture_output=True, text=True, check=True).stdout
        tracked = set(subprocess.run(cmd + ["ls-files", "-z", "--", "skills"], capture_output=True, text=True, check=True).stdout.split("\0"))
        untracked = any(f"skills/{name}/{rel}" not in tracked
                        for name in (names if names is not None else skill_names(root))
                        for rel in source_files(root / "skills" / name))
        return "working-tree" if dirty.strip() or untracked else head
    except (OSError, subprocess.CalledProcessError):
        return "source-snapshot"


def archive_manifest(names: list[str], root: Path = ROOT) -> dict:
    return {"format": 1, "collection": "research-collab", "revision": revision(root, names),
            "skills": {n: validate_skill(n, root) for n in names}}


def check_archive(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or "manifest.json" not in names:
            raise GuardError("Duplicate entries or missing package manifest")
        for name in names:
            part = PurePosixPath(name)
            if part.is_absolute() or "\\" in name or ":" in name or any(x in ("..", ".", "") for x in name.split("/")):
                raise GuardError("Unsafe archive entry")
            if stat.S_ISLNK(archive.getinfo(name).external_attr >> 16):
                raise GuardError("Archive contains a symbolic link")
        manifest = json.loads(archive.read("manifest.json"))
        if manifest.get("format") != 1:
            raise GuardError("Unsupported archive format")
        expected = {"manifest.json"}
        for name, record in manifest["skills"].items():
            if not NAME_RE.fullmatch(name) or not {"SKILL.md", "agents/openai.yaml", "LICENSE"}.issubset(record["files"]):
                raise GuardError("Incomplete skill in archive")
            if DISTRIBUTION in record["files"]:
                declared = distribution_paths(json.loads(archive.read(f"{name}/{DISTRIBUTION}")))
                if declared != set(record["files"]):
                    raise GuardError(f"Archive distribution list mismatch: {name}")
            for rel, sha in record["files"].items():
                distributable(rel)
                filename = f"{name}/{rel}"
                expected.add(filename)
                if filename not in names or digest(archive.read(filename)) != sha:
                    raise GuardError(f"Archive hash mismatch: {filename}")
        if set(names) != expected:
            raise GuardError("Archive has undeclared entries")
    return manifest


def package(names: list[str], output: Path, root: Path = ROOT, dry_run: bool = False) -> dict:
    no_links(output)
    manifest = archive_manifest(names, root)
    if dry_run:
        return {"action": "package-preview", "output": str(output), "skills": names}
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=".package-", suffix=".zip", dir=output.parent)
    os.close(fd)
    temp = Path(raw)
    try:
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            entries = {"manifest.json": json_bytes(manifest)}
            for name in names:
                entries.update({f"{name}/{rel}": data for rel, data in source_files(root / "skills" / name).items()})
            for rel, data in sorted(entries.items()):
                entry = zipfile.ZipInfo(rel, date_time=(1980, 1, 1, 0, 0, 0))
                entry.compress_type = zipfile.ZIP_DEFLATED
                entry.external_attr = 0o100644 << 16
                archive.writestr(entry, data)
        check_archive(temp)
        if output.exists():
            if output.read_bytes() != temp.read_bytes():
                raise GuardError("Output exists with different content; select a new archive path")
        else:
            os.replace(temp, output)
        return {"action": "packaged", "path": str(output), "sha256": digest(output.read_bytes()), "skills": names}
    finally:
        temp.unlink(missing_ok=True)


def atomic_write(path: Path, data: bytes) -> None:
    no_links(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix=".collab-", dir=path.parent)
    temp = Path(raw)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def read_current(target: Path, paths) -> dict[str, str | None]:
    result = {}
    for rel in paths:
        p = member(target, rel)
        if p.exists() and not p.is_file():
            raise GuardError(f"Expected a file: {p}")
        result[rel] = digest(p.read_bytes()) if p.exists() else None
    return result


def ensure_target(target: Path, name: str, root: Path) -> None:
    no_links(target)
    if not NAME_RE.fullmatch(name) or target.name != name or target.parent == Path(target.anchor):
        raise GuardError("Install requires an explicit skills directory, not a drive root")
    if target.resolve().is_relative_to((root / "skills").resolve()):
        raise GuardError("Cannot install into the canonical source tree")


def check_install(name: str, skills_root: Path, root: Path = ROOT) -> dict:
    target = skills_root / name
    ensure_target(target, name, root)
    expected = validate_skill(name, root)["files"]
    actual = read_current(target, expected)
    differences = [p for p in expected if actual[p] != expected[p]]
    if differences:
        raise GuardError(f"{name}: managed files differ: {', '.join(differences)}")
    receipt_path = target / RECEIPT
    if receipt_path.exists():
        record = load_json(receipt_path)
        if record.get("skill") != name or record.get("files") != expected:
            raise GuardError(f"{name}: installation receipt does not match source")
    return {"skill": name, "status": "identical", "files": len(expected)}


def install(name: str, skills_root: Path, backup_root: Path, root: Path = ROOT,
            baseline: dict | None = None, dry_run: bool = False) -> dict:
    target = skills_root / name
    ensure_target(target, name, root)
    record = validate_skill(name, root)
    contents = source_files(root / "skills" / name)
    previous_receipt = target / RECEIPT
    previous = load_json(previous_receipt) if previous_receipt.exists() else None
    if previous is not None and (previous.get("format") != 1 or previous.get("skill") != name):
        raise GuardError("Invalid installation receipt")
    if previous and (set(previous["files"]) & (LOCAL_FILES | {RECEIPT})):
        raise GuardError("Receipt must not own local settings or itself")
    prior = previous["files"] if previous else {}
    if baseline and not previous:
        if Path(baseline["path"]).resolve() != target.resolve():
            raise GuardError("Adoption baseline belongs to another target")
        prior = baseline["files"]
    # Local files and unknown files are never owned merely because they were inventoried.
    managed_before = previous["files"] if previous else {}
    paths = set(contents) | set(managed_before)
    current = read_current(target, paths)
    for rel in paths:
        if rel in managed_before and current[rel] != managed_before[rel]:
            raise GuardError(f"{name}: installed drift at {rel}; preserve and review before updating")
        if rel in contents and rel not in managed_before and current[rel] is not None:
            if rel in prior:
                if current[rel] != prior[rel]:
                    raise GuardError(f"{name}: adoption baseline changed at {rel}")
            elif current[rel] != record["files"][rel]:
                raise GuardError(f"{name}: unowned conflicting file {rel}; supply a reviewed baseline")
    changed = [rel for rel in sorted(paths) if current[rel] != record["files"].get(rel)]
    new_receipt = {"format": 1, **record, "revision": revision(root, [name])}
    if not changed and previous == new_receipt:
        return {"skill": name, "status": "unchanged"}
    if dry_run:
        return {"skill": name, "status": "preview", "changed": changed, "target": str(target)}
    # Recheck immediately before the first mutation.
    if read_current(target, paths) != current:
        raise GuardError("Target changed during planning")
    no_links(backup_root)
    if backup_root.resolve().is_relative_to(target.resolve()):
        raise GuardError("Backups must be outside the installation")
    backup = backup_root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]) / name
    backup.mkdir(parents=True, exist_ok=False)
    touched = [*changed, RECEIPT]
    before = read_current(target, touched)
    for rel, sha in before.items():
        if sha is not None:
            p = member(backup / "files", rel)
            p.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(member(target, rel), p)
    after = {p: record["files"].get(p) for p in changed}
    after[RECEIPT] = digest(json_bytes(new_receipt))
    info = {"format": 1, "skill": name, "target": str(target.resolve()), "before": before, "after": after}
    (backup / "restore.json").write_bytes(json_bytes(info))
    try:
        for rel in changed:
            dest = member(target, rel)
            if rel in contents:
                atomic_write(dest, contents[rel])
            else:
                dest.unlink()
        atomic_write(previous_receipt, json_bytes(new_receipt))
        check_install(name, skills_root, root)
    except Exception:
        restore(backup, skills_root=skills_root, root=root, require_unchanged=False)
        raise
    return {"skill": name, "status": "installed", "changed": len(changed), "backup": str(backup)}


def restore(backup: Path, *, skills_root: Path, root: Path = ROOT,
            require_unchanged: bool = True, dry_run: bool = False) -> dict:
    no_links(backup)
    info = load_json(member(backup, "restore.json"))
    if (not isinstance(info, dict) or info.get("format") != 1
            or not isinstance(info.get("skill"), str) or not NAME_RE.fullmatch(info["skill"])
            or not isinstance(info.get("target"), str)):
        raise GuardError("Invalid restore manifest identity or format")
    target = skills_root / info["skill"]
    ensure_target(target, info["skill"], root)
    if not Path(info["target"]).is_absolute() or Path(info["target"]).resolve() != target.resolve():
        raise GuardError("Backup belongs to another target; supply its original --skills-root")
    before, after = info.get("before"), info.get("after")
    if (not isinstance(before, dict) or not isinstance(after, dict)
            or before.keys() != after.keys() or not all(isinstance(p, str) for p in before)
            or RECEIPT not in before
            or not isinstance(after[RECEIPT], str)):
        raise GuardError("Invalid restore file set; before/after and installation receipt must agree")
    saved_files = {}
    for rel in before:
        if rel in LOCAL_FILES:
            raise GuardError("Restore must not own local settings")
        member(target, rel)
        for sha in (before[rel], after[rel]):
            if sha is not None and (not isinstance(sha, str) or not SHA256_RE.fullmatch(sha)):
                raise GuardError("Invalid restore SHA-256")
        if before[rel] is not None:
            saved = member(backup / "files", rel).read_bytes()
            if digest(saved) != before[rel]:
                raise GuardError("Backup integrity check failed")
            saved_files[rel] = saved
    if require_unchanged:
        if read_current(target, after) != after:
            raise GuardError("Installation changed since this backup; refusing to overwrite newer work")
        receipt = load_json(member(target, RECEIPT))
        if (not isinstance(receipt, dict) or receipt.get("format") != 1 or receipt.get("skill") != info["skill"]
                or not isinstance(receipt.get("files"), dict)):
            raise GuardError("Restore target has no matching installation receipt")
        prior = json.loads(saved_files[RECEIPT]) if RECEIPT in saved_files else {}
        if prior and (not isinstance(prior, dict) or prior.get("format") != 1 or prior.get("skill") != info["skill"]
                      or not isinstance(prior.get("files"), dict)):
            raise GuardError("Backup contains an invalid previous receipt")
        owned = set(receipt["files"]) | set(prior.get("files", {})) | {RECEIPT}
        if not set(before).issubset(owned):
            raise GuardError("Restore manifest includes files not owned by this installation")
    if not dry_run:
        # All paths, hashes and target ownership have passed before the first write.
        for rel, sha in before.items():
            dest = member(target, rel)
            if sha is None:
                dest.unlink(missing_ok=True)
            else:
                atomic_write(dest, saved_files[rel])
    return {"skill": info["skill"], "status": "restore-preview" if dry_run else "restored"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "package", "install", "check", "restore"))
    parser.add_argument("--skill", action="append", help="Repeat to select multiple skills; default: all")
    parser.add_argument("--skills-root", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", type=Path, help="Reviewed local adoption baseline; never published")
    parser.add_argument("--backup-root", type=Path, default=ROOT / ".local" / "install-backups")
    parser.add_argument("--backup", type=Path, help="One backup directory containing restore.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "restore":
            if not args.backup or not args.skills_root:
                parser.error("restore requires --backup and the original --skills-root")
            print(json.dumps(restore(args.backup, skills_root=args.skills_root, dry_run=args.dry_run), ensure_ascii=False))
            return 0
        names = select(args.skill)
        if args.action == "package":
            if not args.output:
                parser.error("package requires --output")
            print(json.dumps(package(names, args.output, dry_run=args.dry_run), ensure_ascii=False))
            return 0
        if args.action in ("install", "check") and not args.skills_root:
            parser.error("install/check requires --skills-root")
        baselines = load_json(args.baseline) if args.baseline else {}
        failures = 0
        for name in names:
            try:
                if args.action == "validate":
                    result = validate_skill(name)
                    result = {"skill": name, "status": "valid", "files": len(result["files"])}
                elif args.action == "check":
                    result = check_install(name, args.skills_root)
                else:
                    result = install(name, args.skills_root, args.backup_root, baseline=baselines.get(name), dry_run=args.dry_run)
                print(json.dumps(result, ensure_ascii=False))
            except (GuardError, OSError, ValueError, KeyError) as exc:
                failures += 1
                print(json.dumps({"skill": name, "status": "blocked", "reason": str(exc)}, ensure_ascii=False))
        return 1 if failures else 0
    except (GuardError, OSError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
