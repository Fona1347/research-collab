from __future__ import annotations

import copy
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .errors import ConfigurationError

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
_DEVELOPMENT_DEFAULTS = REPOSITORY_ROOT / "config" / "defaults.toml"
_PACKAGED_DEFAULTS = Path(__file__).resolve().parent / "resources" / "defaults.toml"
DEFAULTS_PATH = _DEVELOPMENT_DEFAULTS if _DEVELOPMENT_DEFAULTS.is_file() else _PACKAGED_DEFAULTS
ALLOWED_FORMATS = {"svg", "pdf", "png", "tiff"}
ALLOWED_BACKENDS = {"auto", "matplotlib", "pubfig"}
ALLOWED_THEMES = {"paper", "nature", "science", "cell", "custom"}
ALLOWED_STYLES = {"general-paper", "minimal", "custom"}

FALLBACK_DEFAULTS: dict[str, Any] = {
    "render": {
        "backend": "auto",
        "theme": "paper",
        "style": "general-paper",
        "scienceplots": True,
        "chinese_font": "",
        "font_size": 7.0,
        "width_mm": 89.0,
        "height_mm": 60.0,
        "dpi": 300,
        "formats": ["svg"],
        "grid": False,
    },
    "output": {"conflict": "timestamp"},
    "updates": {"check_before_render": False},
    "logging": {"enabled": True},
}


def deep_merge(*layers: Mapping[str, Any] | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for layer in layers:
        if not layer:
            continue
        for key, value in layer.items():
            if isinstance(value, Mapping) and isinstance(result.get(key), Mapping):
                result[key] = deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
    return result


def load_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise ConfigurationError(f"Configuration file not found: {path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ConfigurationError(f"Invalid TOML in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigurationError(f"Configuration must be a TOML table: {path}")
    return data


def load_defaults(path: Path = DEFAULTS_PATH) -> dict[str, Any]:
    defaults = load_toml(path) if path.is_file() else copy.deepcopy(FALLBACK_DEFAULTS)
    return validate_config(deep_merge(FALLBACK_DEFAULTS, defaults))


def figure_config_layer(spec: Mapping[str, Any]) -> dict[str, Any]:
    layer: dict[str, Any] = {"render": {}}
    style = spec.get("style", {})
    export = spec.get("export", {})
    if isinstance(style, Mapping):
        layer["render"].update(style)
    if isinstance(export, Mapping):
        for key in ("dpi", "formats"):
            if key in export:
                layer["render"][key] = export[key]
    return layer


def load_effective_config(
    *,
    project_root: Path | None,
    figure_spec: Mapping[str, Any] | None = None,
    cli_overrides: Mapping[str, Any] | None = None,
    defaults_path: Path = DEFAULTS_PATH,
) -> tuple[dict[str, Any], Path | None]:
    defaults = load_defaults(defaults_path)
    project_path = project_root / "sci-plot.toml" if project_root else None
    project_config = (
        load_toml(project_path)
        if project_path is not None and project_path.is_file()
        else {}
    )
    config = deep_merge(
        defaults,
        project_config,
        figure_config_layer(figure_spec or {}),
        cli_overrides,
    )
    return validate_config(config), project_path if project_path and project_path.is_file() else None


def _positive_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise ConfigurationError(f"{name} must be a positive number")
    return float(value)


def validate_config(config: Mapping[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(dict(config))
    render = normalized.get("render")
    if not isinstance(render, dict):
        raise ConfigurationError("The [render] configuration must be a table")

    backend = str(render.get("backend", "auto")).lower()
    if backend not in ALLOWED_BACKENDS:
        raise ConfigurationError(
            f"render.backend must be one of: {', '.join(sorted(ALLOWED_BACKENDS))}"
        )
    render["backend"] = backend

    theme = str(render.get("theme", "paper")).lower()
    if theme not in ALLOWED_THEMES:
        raise ConfigurationError(
            f"render.theme must be one of: {', '.join(sorted(ALLOWED_THEMES))}"
        )
    style = str(render.get("style", "general-paper")).lower()
    if style not in ALLOWED_STYLES:
        raise ConfigurationError(
            f"render.style must be one of: {', '.join(sorted(ALLOWED_STYLES))}"
        )
    render["theme"] = theme
    render["style"] = style

    formats = render.get("formats", ["svg"])
    if not isinstance(formats, list) or not formats:
        raise ConfigurationError("render.formats must be a non-empty array")
    normalized_formats: list[str] = []
    for item in formats:
        value = str(item).lower()
        if value == "tif":
            value = "tiff"
        if value not in ALLOWED_FORMATS:
            raise ConfigurationError(f"Unsupported export format: {item}")
        if value not in normalized_formats:
            normalized_formats.append(value)
    render["formats"] = normalized_formats

    dpi = int(_positive_number(render.get("dpi", 300), "render.dpi"))
    if dpi < 72 or dpi > 2400:
        raise ConfigurationError("render.dpi must be between 72 and 2400")
    render["dpi"] = dpi
    for key in ("width_mm", "height_mm", "font_size"):
        render[key] = _positive_number(render.get(key, FALLBACK_DEFAULTS["render"][key]), f"render.{key}")

    for key in ("scienceplots", "grid"):
        if not isinstance(render.get(key, False), bool):
            raise ConfigurationError(f"render.{key} must be true or false")

    palette = render.get("palette")
    if palette is not None:
        if not isinstance(palette, list) or not palette or not all(
            isinstance(item, str) and item for item in palette
        ):
            raise ConfigurationError("render.palette must be a non-empty array of colors")
    custom_rc = render.get("rcparams")
    if custom_rc is not None and not isinstance(custom_rc, dict):
        raise ConfigurationError("render.rcparams must be a table")
    if theme == "custom" and palette is None and not custom_rc:
        raise ConfigurationError(
            "render.theme='custom' requires render.palette or render.rcparams"
        )
    if style == "custom" and not custom_rc:
        raise ConfigurationError(
            "render.style='custom' requires render.rcparams"
        )

    output = normalized.setdefault("output", {})
    if not isinstance(output, dict):
        raise ConfigurationError("The [output] configuration must be a table")
    if output.get("conflict", "timestamp") not in {"timestamp", "error"}:
        raise ConfigurationError("output.conflict must be 'timestamp' or 'error'")

    updates = normalized.setdefault("updates", {})
    logging = normalized.setdefault("logging", {})
    for section, key in ((updates, "check_before_render"), (logging, "enabled")):
        if not isinstance(section, dict) or not isinstance(section.get(key, False), bool):
            raise ConfigurationError(f"{key} must be true or false")
    return normalized
