from __future__ import annotations

import importlib.metadata
import json
import sys
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .safety import redact_cli_args


def _version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return ""


def version_report() -> dict[str, str]:
    from . import __version__

    return {
        "sci_plot": __version__,
        "pubfig": _version("pubfig"),
        "matplotlib": _version("matplotlib"),
        "scienceplots": _version("SciencePlots"),
        "numpy": _version("numpy"),
        "pandas": _version("pandas"),
    }


def approved_sources(manifest_path: Path | None = None) -> dict[str, str]:
    if manifest_path is None:
        from .sources import DEFAULT_MANIFEST_PATH

        path = DEFAULT_MANIFEST_PATH
    else:
        path = manifest_path
    if not path.is_file():
        return {}
    with path.open("rb") as handle:
        manifest = tomllib.load(handle)
    return {
        source["id"]: source.get("last_approved_ref", "")
        for source in manifest.get("sources", [])
        if isinstance(source, dict) and source.get("id")
    }


def write_run_log(
    *,
    root: Path,
    status: str,
    spec_path: Path,
    project_root: Path | None,
    inputs: list[Path],
    outputs: list[Path],
    kind: str,
    theme: str,
    backend: str,
    formats: list[str],
    error: str | None = None,
    command: list[str] | None = None,
) -> Path:
    log_dir = root / ".sci-plot"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "runs.jsonl"
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": redact_cli_args(command if command is not None else sys.argv),
        "spec": str(spec_path),
        "project_root": str(project_root) if project_root else "",
        "inputs": [str(path) for path in inputs],
        "outputs": [str(path) for path in outputs],
        "kind": kind,
        "theme": theme,
        "backend": backend,
        "formats": formats,
        "status": status,
        "error": error or "",
        "versions": version_report(),
        "approved_sources": approved_sources(),
    }
    with log_path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return log_path
