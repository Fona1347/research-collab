from __future__ import annotations

import copy
import json
from collections.abc import Iterator, Mapping
from pathlib import Path
from typing import Any

from .config import ALLOWED_FORMATS
from .errors import SpecError

TEMPLATE_CATALOG: dict[str, dict[str, Any]] = {
    "line": {
        "description": "Exact trends, optionally grouped",
        "required_mapping": ("x", "y"),
        "optional_mapping": ("group",),
    },
    "bar": {
        "description": "Exact categorical values, optionally grouped",
        "required_mapping": ("x", "y"),
        "optional_mapping": ("group",),
    },
    "scatter": {
        "description": "Exact x/y observations, optionally grouped",
        "required_mapping": ("x", "y"),
        "optional_mapping": ("group",),
    },
    "heatmap": {
        "description": "Complete long-form x/y/value matrix",
        "required_mapping": ("x", "y", "value"),
        "optional_mapping": (),
    },
    "errorbar": {
        "description": "Explicit symmetric errors or absolute lower/upper bounds",
        "required_mapping": ("x", "y"),
        "optional_mapping": ("group", "yerr", "ymin", "ymax"),
    },
    "multi_panel": {
        "description": "Simple grid of supported plot kinds",
        "required_mapping": (),
        "optional_mapping": (),
    },
}
ALLOWED_KINDS = set(TEMPLATE_CATALOG)
ALLOWED_DATA_FORMATS = {"csv", "tsv", "json", "xlsx", "npy", "npz"}
TOP_LEVEL_KEYS = {
    "schema_version",
    "kind",
    "conclusion",
    "data",
    "mapping",
    "labels",
    "style",
    "export",
    "panels",
    "layout",
}
PLOT_KEYS = {"kind", "data", "mapping", "labels", "style"}


def template_catalog() -> list[dict[str, Any]]:
    return [
        {
            "kind": kind,
            "description": descriptor["description"],
            "required_mapping": list(descriptor["required_mapping"]),
            "optional_mapping": list(descriptor["optional_mapping"]),
        }
        for kind, descriptor in TEMPLATE_CATALOG.items()
    ]


def _object_without_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SpecError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_spec(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise SpecError(f"Figure spec not found: {path}") from exc
    try:
        data = json.loads(text, object_pairs_hook=_object_without_duplicates)
    except json.JSONDecodeError as exc:
        raise SpecError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise SpecError("Figure spec root must be an object")
    return validate_spec(data)


def _require_mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SpecError(f"{name} must be an object")
    return value


def _validate_plot(plot: Mapping[str, Any], context: str) -> None:
    unknown = set(plot) - PLOT_KEYS
    if unknown:
        raise SpecError(f"Unknown key(s) in {context}: {', '.join(sorted(unknown))}")
    kind = plot.get("kind")
    if kind not in ALLOWED_KINDS - {"multi_panel"}:
        raise SpecError(f"Unsupported plot kind in {context}: {kind}")

    data = _require_mapping(plot.get("data"), f"{context}.data")
    path = data.get("path")
    if not isinstance(path, str) or not path.strip():
        raise SpecError(f"{context}.data.path must be a non-empty string")
    data_format = data.get("format")
    if data_format is not None and str(data_format).lower() not in ALLOWED_DATA_FORMATS:
        raise SpecError(f"Unsupported data format in {context}: {data_format}")
    if "key" in data and not isinstance(data["key"], str):
        raise SpecError(f"{context}.data.key must be a string")

    mapping = _require_mapping(plot.get("mapping"), f"{context}.mapping")
    descriptor = TEMPLATE_CATALOG[str(kind)]
    required = descriptor["required_mapping"]
    for key in required:
        if not isinstance(mapping.get(key), str) or not mapping[key]:
            raise SpecError(f"{context}.mapping.{key} must be a column name")
    for key in descriptor["optional_mapping"]:
        if key in mapping and (
            not isinstance(mapping[key], str) or not mapping[key]
        ):
            raise SpecError(f"{context}.mapping.{key} must be a non-empty column name")

    for name in ("labels", "style"):
        value = plot.get(name, {})
        if not isinstance(value, dict):
            raise SpecError(f"{context}.{name} must be an object")

    if kind == "errorbar":
        has_yerr = "yerr" in mapping
        has_ymin = "ymin" in mapping
        has_ymax = "ymax" in mapping
        if has_ymin != has_ymax:
            raise SpecError(
                f"{context}.mapping must provide both ymin and ymax"
            )
        if has_yerr == (has_ymin and has_ymax):
            raise SpecError(
                f"{context}.mapping must provide exactly one uncertainty form: "
                "yerr or ymin+ymax"
            )
        uncertainty = plot.get("labels", {}).get("uncertainty")
        if not isinstance(uncertainty, str) or not uncertainty.strip():
            raise SpecError(
                f"{context}.labels.uncertainty must name the interval, such as SD, SEM, or 95% CI"
            )


def validate_spec(spec: Mapping[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(dict(spec))
    unknown = set(normalized) - TOP_LEVEL_KEYS
    if unknown:
        raise SpecError(f"Unknown top-level key(s): {', '.join(sorted(unknown))}")
    if normalized.get("schema_version") != 1:
        raise SpecError("schema_version must be 1")
    kind = normalized.get("kind")
    if kind not in ALLOWED_KINDS:
        raise SpecError(f"kind must be one of: {', '.join(sorted(ALLOWED_KINDS))}")

    export = normalized.get("export", {})
    if not isinstance(export, dict):
        raise SpecError("export must be an object")
    if "overwrite" in export:
        raise SpecError("export.overwrite is forbidden; use the explicit CLI --overwrite flag")
    if "path" in export and (not isinstance(export["path"], str) or not export["path"]):
        raise SpecError("export.path must be a non-empty string")
    if "formats" in export:
        formats = export["formats"]
        if not isinstance(formats, list) or not formats:
            raise SpecError("export.formats must be a non-empty array")
        cleaned: list[str] = []
        for item in formats:
            value = str(item).lower()
            if value == "tif":
                value = "tiff"
            if value not in ALLOWED_FORMATS:
                raise SpecError(f"Unsupported export format: {item}")
            if value not in cleaned:
                cleaned.append(value)
        export["formats"] = cleaned

    if not isinstance(normalized.get("style", {}), dict):
        raise SpecError("style must be an object")
    if not isinstance(normalized.get("labels", {}), dict):
        raise SpecError("labels must be an object")

    if kind == "multi_panel":
        panels = normalized.get("panels")
        if not isinstance(panels, list) or not panels:
            raise SpecError("multi_panel requires a non-empty panels array")
        inherited = {
            key: normalized[key]
            for key in ("data", "mapping", "labels", "style")
            if key in normalized
        }
        for index, panel in enumerate(panels):
            if not isinstance(panel, dict):
                raise SpecError(f"panels[{index}] must be an object")
            merged = _merge_plot(inherited, panel)
            _validate_plot(merged, f"panels[{index}]")
        layout = normalized.get("layout", {})
        if not isinstance(layout, dict):
            raise SpecError("layout must be an object")
        for key in ("rows", "cols"):
            if key in layout and (
                isinstance(layout[key], bool)
                or not isinstance(layout[key], int)
                or layout[key] <= 0
            ):
                raise SpecError(f"layout.{key} must be a positive integer")
    else:
        _validate_plot(
            {key: normalized[key] for key in PLOT_KEYS if key in normalized},
            "figure",
        )
    return normalized


def _merge_plot(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(base))
    for key, value in override.items():
        if key in {"labels", "style", "mapping", "data"} and isinstance(value, Mapping):
            current = result.get(key, {})
            result[key] = {**current, **copy.deepcopy(dict(value))}
        else:
            result[key] = copy.deepcopy(value)
    return result


def iter_plot_specs(spec: Mapping[str, Any]) -> Iterator[dict[str, Any]]:
    if spec["kind"] != "multi_panel":
        yield {key: copy.deepcopy(spec[key]) for key in PLOT_KEYS if key in spec}
        return
    base = {
        key: copy.deepcopy(spec[key])
        for key in ("data", "mapping", "labels", "style")
        if key in spec
    }
    for panel in spec["panels"]:
        yield _merge_plot(base, panel)


def resolve_data_path(plot: Mapping[str, Any], spec_path: Path) -> Path:
    raw = Path(plot["data"]["path"]).expanduser()
    return raw.resolve() if raw.is_absolute() else (spec_path.parent / raw).resolve()


def input_paths(spec: Mapping[str, Any], spec_path: Path) -> list[Path]:
    paths: list[Path] = []
    for plot in iter_plot_specs(spec):
        path = resolve_data_path(plot, spec_path)
        if path not in paths:
            paths.append(path)
    return paths
