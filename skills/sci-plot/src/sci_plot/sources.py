from __future__ import annotations

import importlib.metadata
import json
import os
import re
import tempfile
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import REPOSITORY_ROOT
from .errors import SourceError

_DEVELOPMENT_MANIFEST = REPOSITORY_ROOT / "upstream" / "sources.toml"
_PACKAGED_MANIFEST = Path(__file__).resolve().parent / "resources" / "sources.toml"
DEFAULT_MANIFEST_PATH = (
    _DEVELOPMENT_MANIFEST if _DEVELOPMENT_MANIFEST.is_file() else _PACKAGED_MANIFEST
)


def _require_mutable_manifest(path: Path) -> None:
    if path.resolve() == _PACKAGED_MANIFEST.resolve():
        raise SourceError(
            "The packaged source manifest is an immutable baseline. Copy it to a "
            "writable review location and pass --manifest explicitly."
        )


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            manifest = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise SourceError(f"Source manifest not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise SourceError(f"Invalid source manifest {path}: {exc}") from exc
    if manifest.get("schema_version") != 1:
        raise SourceError("Source manifest schema_version must be 1")
    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        raise SourceError("Source manifest must contain at least one [[sources]] entry")
    seen: set[str] = set()
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise SourceError(f"sources[{index}] must be a table")
        for key in ("id", "url", "github", "branch", "role"):
            if not isinstance(source.get(key), str) or not source[key]:
                raise SourceError(f"sources[{index}].{key} must be a non-empty string")
        if source["id"] in seen:
            raise SourceError(f"Duplicate source id: {source['id']}")
        seen.add(source["id"])
        if "/" not in source["github"]:
            raise SourceError(f"Invalid GitHub repository: {source['github']}")
    return manifest


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return "[" + ", ".join(json.dumps(item, ensure_ascii=False) for item in value) + "]"
    raise SourceError(f"Unsupported manifest value type: {type(value).__name__}")


def serialize_manifest(manifest: dict[str, Any]) -> str:
    lines = [f"schema_version = {int(manifest['schema_version'])}", ""]
    for source in manifest["sources"]:
        lines.append("[[sources]]")
        preferred = [
            "id",
            "url",
            "github",
            "branch",
            "role",
            "release_tracking",
            "last_checked",
            "last_approved_ref",
            "last_approved_tag",
            "last_approved_version",
            "latest_seen_ref",
            "latest_seen_tag",
            "latest_seen_tag_ref",
            "latest_seen_version",
            "latest_compare_status",
            "latest_change_count",
            "latest_watched_changes",
            "latest_risks",
            "previous_approved_ref",
            "last_approval_time",
            "approval_history",
            "adapter_status",
            "watch_paths",
            "notes",
        ]
        emitted: set[str] = set()
        for key in preferred:
            if key in source:
                lines.append(f"{key} = {_toml_value(source[key])}")
                emitted.add(key)
        for key in sorted(set(source) - emitted):
            lines.append(f"{key} = {_toml_value(source[key])}")
        lines.append("")
    return "\n".join(lines)


def write_manifest_atomic(path: Path, manifest: dict[str, Any]) -> None:
    load_manifest_data = serialize_manifest(manifest)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    temp = Path(raw_temp)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(load_manifest_data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    except Exception:
        temp.unlink(missing_ok=True)
        raise


class GitHubClient:
    def __init__(self, *, timeout: float = 15.0):
        self.timeout = timeout

    def get_json(self, endpoint: str, *, allow_not_found: bool = False) -> Any:
        url = "https://api.github.com" + endpoint
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "sci-plot/0.1 source-check",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as exc:
            if allow_not_found and exc.code == 404:
                return None
            raise SourceError(f"GitHub returned HTTP {exc.code} for {url}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise SourceError(f"GitHub request failed for {url}: {exc}") from exc


def _installed_pubfig() -> str:
    try:
        return importlib.metadata.version("pubfig")
    except importlib.metadata.PackageNotFoundError:
        return ""


def _changed_risks(paths: list[str]) -> list[str]:
    risks: set[str] = set()
    for path in paths:
        lowered = path.lower()
        if "pyproject" in lowered or "requirements" in lowered or "lock" in lowered:
            risks.add("dependencies")
        if "cli" in lowered or "spec" in lowered or "api" in lowered:
            risks.add("api-or-spec")
        if "export" in lowered or "save" in lowered:
            risks.add("output-behavior")
        if "skill.md" in lowered or "readme" in lowered or "routing" in lowered:
            risks.add("routing-or-guidance")
    return sorted(risks)


def _watch_hits(changed: list[str], watched: list[str]) -> list[str]:
    hits: list[str] = []
    for path in changed:
        if any(path == item or path.startswith(item.rstrip("/") + "/") for item in watched):
            hits.append(path)
    return hits


def check_source(source: dict[str, Any], client: GitHubClient) -> dict[str, Any]:
    repo = source["github"]
    branch = urllib.parse.quote(source["branch"], safe="")
    commit = client.get_json(f"/repos/{repo}/commits/{branch}")
    latest_ref = commit["sha"]
    latest_date = commit.get("commit", {}).get("committer", {}).get("date", "")
    latest_version = ""
    release_url = ""
    if source.get("release_tracking", False):
        release = client.get_json(f"/repos/{repo}/releases/latest", allow_not_found=True)
        if release:
            latest_version = str(release.get("tag_name", "")).removeprefix("v")
            release_url = str(release.get("html_url", ""))
    tags = client.get_json(f"/repos/{repo}/tags?per_page=1", allow_not_found=True)
    latest_tag = ""
    latest_tag_ref = ""
    if isinstance(tags, list) and tags:
        latest_tag = str(tags[0].get("name", ""))
        latest_tag_ref = str(tags[0].get("commit", {}).get("sha", ""))

    changed_files: list[str] = []
    approved = source.get("last_approved_ref", "")
    compare_status = "unbaselined"
    if approved:
        base = urllib.parse.quote(approved, safe="")
        head = urllib.parse.quote(latest_ref, safe="")
        comparison = client.get_json(
            f"/repos/{repo}/compare/{base}...{head}",
            allow_not_found=True,
        )
        if comparison:
            compare_status = str(comparison.get("status", "unknown"))
            changed_files = [
                str(item.get("filename", ""))
                for item in comparison.get("files", [])
                if item.get("filename")
            ]
        else:
            compare_status = "comparison-unavailable"

    watched = [str(item) for item in source.get("watch_paths", [])]
    hits = _watch_hits(changed_files, watched)
    risks = _changed_risks(hits or changed_files)
    pending = compare_status not in {"identical"} if approved else True
    return {
        "id": source["id"],
        "role": source["role"],
        "approved_ref": approved,
        "approved_tag": source.get("last_approved_tag", ""),
        "approved_version": source.get("last_approved_version", ""),
        "latest_ref": latest_ref,
        "latest_tag": latest_tag,
        "latest_tag_ref": latest_tag_ref,
        "latest_version": latest_version,
        "latest_date": latest_date,
        "release_url": release_url,
        "compare_status": compare_status,
        "pending_update": pending,
        "changed_files": changed_files,
        "watched_changes": hits,
        "risks": risks,
        "installed_pubfig_version": _installed_pubfig() if source["id"] == "pubfig" else "",
        "adapter_status": source.get("adapter_status", ""),
    }


def check_sources(
    path: Path = DEFAULT_MANIFEST_PATH,
    *,
    record: bool = False,
    client: GitHubClient | None = None,
) -> dict[str, Any]:
    if record:
        _require_mutable_manifest(path)
    manifest = load_manifest(path)
    client = client or GitHubClient()
    checked_at = datetime.now(timezone.utc).isoformat()
    reports: list[dict[str, Any]] = []
    source_by_id = {source["id"]: source for source in manifest["sources"]}
    for source in manifest["sources"]:
        try:
            report = check_source(source, client)
        except SourceError as exc:
            report = {
                "id": source["id"],
                "role": source["role"],
                "error": str(exc),
                "pending_update": False,
            }
        reports.append(report)
        if record and "error" not in report:
            target = source_by_id[source["id"]]
            target["last_checked"] = checked_at
            target["latest_seen_ref"] = report["latest_ref"]
            target["latest_seen_tag"] = report["latest_tag"]
            target["latest_seen_tag_ref"] = report["latest_tag_ref"]
            target["latest_seen_version"] = report["latest_version"]
            target["latest_compare_status"] = report["compare_status"]
            target["latest_change_count"] = len(report["changed_files"])
            target["latest_watched_changes"] = report["watched_changes"]
            target["latest_risks"] = report["risks"]
    if record:
        write_manifest_atomic(path, manifest)
    return {
        "checked_at": checked_at,
        "recorded": record,
        "environment_modified": False,
        "sources": reports,
    }


def source_status(path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    manifest = load_manifest(path)
    status: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        approved = source.get("last_approved_ref", "")
        latest = source.get("latest_seen_ref", "")
        compare_status = source.get("latest_compare_status", "")
        if approved and latest == approved:
            pending = False
        elif compare_status == "identical":
            pending = False
        elif compare_status in {"ahead", "behind", "diverged"}:
            pending = True
        else:
            pending = bool(latest and latest != approved)
        status.append(
            {
                "id": source["id"],
                "role": source["role"],
                "approved_ref": approved,
                "approved_tag": source.get("last_approved_tag", ""),
                "approved_version": source.get("last_approved_version", ""),
                "last_checked": source.get("last_checked", ""),
                "latest_seen_ref": latest,
                "latest_seen_tag": source.get("latest_seen_tag", ""),
                "latest_seen_tag_ref": source.get("latest_seen_tag_ref", ""),
                "latest_seen_version": source.get("latest_seen_version", ""),
                "pending_update": pending,
                "impact": source.get("adapter_status", ""),
                "latest_change_count": source.get("latest_change_count", 0),
                "latest_watched_changes": source.get("latest_watched_changes", []),
                "latest_risks": source.get("latest_risks", []),
                "notes": source.get("notes", ""),
            }
        )
    return {"manifest": str(path.resolve()), "sources": status}


def _append_audit(path: Path, record: dict[str, Any]) -> Path:
    audit_dir = path.parent.parent / ".sci-plot"
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_path = audit_dir / "source-updates.jsonl"
    with audit_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return audit_path


def approve_source(
    path: Path,
    *,
    source_id: str,
    ref: str,
    approve: bool,
    tests_passed: bool,
) -> dict[str, Any]:
    if not approve:
        raise SourceError("Ref approval requires the explicit --approve flag")
    if not tests_passed:
        raise SourceError(
            "Ref approval requires --tests-passed after isolated compatibility and smoke tests"
        )
    if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
        raise SourceError("Only an immutable 40-character Git commit SHA can be approved")
    _require_mutable_manifest(path)

    manifest = load_manifest(path)
    source = next(
        (item for item in manifest["sources"] if item["id"] == source_id),
        None,
    )
    if source is None:
        raise SourceError(f"Unknown source id: {source_id}")
    latest = source.get("latest_seen_ref", "")
    if latest != ref:
        raise SourceError(
            "Requested ref does not match the recorded latest ref. "
            "Run source check --record and review the result first."
        )

    previous = source.get("last_approved_ref", "")
    approved_at = datetime.now(timezone.utc).isoformat()
    approved_tag = (
        source.get("latest_seen_tag", "")
        if source.get("latest_seen_tag_ref", "") == ref
        else ""
    )
    latest_version = source.get("latest_seen_version", "")
    approved_version = (
        latest_version
        if approved_tag and approved_tag.removeprefix("v") == latest_version
        else ""
    )
    change_summary = {
        "compare_status": source.get("latest_compare_status", ""),
        "changed_file_count": source.get("latest_change_count", 0),
        "watched_changes": source.get("latest_watched_changes", []),
        "risks": source.get("latest_risks", []),
    }
    history_record = {
        "timestamp": approved_at,
        "source": source_id,
        "previous_ref": previous,
        "approved_ref": ref,
        "approved_tag": approved_tag,
        "approved_version": approved_version,
        "tests_passed": True,
        "runtime_modified": False,
        "adapter_modified": False,
        "change_summary": change_summary,
    }
    history = list(source.get("approval_history", []))
    history.append(json.dumps(history_record, ensure_ascii=False, sort_keys=True))
    source["approval_history"] = history[-100:]
    source["previous_approved_ref"] = previous
    source["last_approved_ref"] = ref
    source["last_approved_tag"] = approved_tag
    source["last_approved_version"] = approved_version
    source["last_approval_time"] = approved_at
    source["latest_compare_status"] = "identical"
    source["latest_change_count"] = 0
    source["latest_watched_changes"] = []
    source["latest_risks"] = []
    write_manifest_atomic(path, manifest)

    record = history_record
    try:
        audit_path = _append_audit(path, record)
    except OSError as exc:
        return {
            **record,
            "audit_log": "",
            "audit_warning": (
                "Secondary JSONL audit copy failed; the authoritative audit entry "
                f"is embedded atomically in the manifest: {exc}"
            ),
        }
    return {**record, "audit_log": str(audit_path), "audit_warning": ""}
