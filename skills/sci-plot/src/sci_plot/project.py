from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ConfigurationError


def resolve_project_root(spec_path: Path, explicit_root: str | Path | None) -> Path | None:
    if explicit_root is not None:
        root = Path(explicit_root).expanduser().resolve()
        if not root.is_dir():
            raise ConfigurationError(f"Project root is not a directory: {root}")
        return root
    candidate = spec_path.parent / "sci-plot.toml"
    return spec_path.parent.resolve() if candidate.is_file() else None


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def init_project(
    project_root: Path,
    *,
    project_name: str,
    output_dir: str,
    theme: str,
    style: str,
    scienceplots: bool,
) -> Path:
    root = project_root.expanduser().resolve()
    if not root.is_dir():
        raise ConfigurationError(
            f"Project root must already exist; refusing to create an ambiguous path: {root}"
        )
    path = root / "sci-plot.toml"
    if path.exists():
        raise ConfigurationError(f"Project configuration already exists: {path}")
    content = (
        "[project]\n"
        f"name = {_toml_string(project_name)}\n"
        f"output_dir = {_toml_string(output_dir)}\n\n"
        "[render]\n"
        f"theme = {_toml_string(theme)}\n"
        f"style = {_toml_string(style)}\n"
        f"scienceplots = {'true' if scienceplots else 'false'}\n"
    )
    try:
        with path.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except FileExistsError as exc:
        raise ConfigurationError(f"Project configuration already exists: {path}") from exc
    return path


def resolve_output_base(
    *,
    spec: dict[str, Any],
    spec_path: Path,
    config: dict[str, Any],
    project_root: Path | None,
    cli_output: str | None,
    cwd: Path | None = None,
) -> tuple[Path, str]:
    if cli_output:
        raw = Path(cli_output).expanduser()
        base = raw if raw.is_absolute() else (cwd or Path.cwd()) / raw
        return base.resolve(), "cli"

    spec_output = spec.get("export", {}).get("path")
    if spec_output:
        raw = Path(spec_output).expanduser()
        base = raw if raw.is_absolute() else spec_path.parent / raw
        return base.resolve(), "figure-spec"

    project = config.get("project", {})
    if project_root is not None and isinstance(project, dict) and project.get("output_dir"):
        raw = Path(str(project["output_dir"])).expanduser()
        directory = raw if raw.is_absolute() else project_root / raw
        return (directory / spec_path.stem).resolve(), "project-config"

    if project_root is not None:
        return (project_root / "figures" / spec_path.stem).resolve(), "project-fallback"

    raise ConfigurationError(
        "No output path and no explicit project root. Provide --output or --project-root."
    )
