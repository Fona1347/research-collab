from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import DataError, DependencyError
from .spec import TEMPLATE_CATALOG, resolve_data_path

SUPPORTED_FORMATS = ("csv", "tsv", "json", "xlsx", "npy", "npz")


def _pandas():
    try:
        import pandas as pd
    except ImportError as exc:
        raise DependencyError(
            "pandas is required for data inspection and rendering; install the declared project dependencies"
        ) from exc
    return pd


def _numpy():
    try:
        import numpy as np
    except ImportError as exc:
        raise DependencyError(
            "NumPy is required for array data and rendering; install the declared project dependencies"
        ) from exc
    return np


def infer_format(path: Path, explicit: str | None = None) -> str:
    value = explicit.lower() if explicit else path.suffix.lower().lstrip(".")
    if value == "xls":
        raise DataError("Legacy .xls is not supported; save as .xlsx")
    if value not in SUPPORTED_FORMATS:
        raise DataError(
            f"Unsupported data format '{value or '(none)'}'; expected one of: "
            + ", ".join(SUPPORTED_FORMATS)
        )
    return value


def _array_frame(array: Any):
    pd = _pandas()
    np = _numpy()
    if getattr(array.dtype, "names", None):
        return pd.DataFrame.from_records(array)
    if array.ndim == 1:
        return pd.DataFrame({"value": array})
    if array.ndim == 2:
        return pd.DataFrame(array, columns=[f"col_{index}" for index in range(array.shape[1])])
    raise DataError(f"NPY/NPZ arrays must be one- or two-dimensional, got shape {array.shape}")


def load_table(data_spec: dict[str, Any], spec_path: Path):
    pd = _pandas()
    path = resolve_data_path({"data": data_spec}, spec_path)
    if not path.is_file():
        raise DataError(f"Input data file not found: {path}")
    data_format = infer_format(path, data_spec.get("format"))
    try:
        if data_format == "csv":
            frame = pd.read_csv(path)
        elif data_format == "tsv":
            frame = pd.read_csv(path, sep="\t")
        elif data_format == "json":
            frame = pd.read_json(path)
        elif data_format == "xlsx":
            frame = pd.read_excel(path, engine="openpyxl")
        elif data_format == "npy":
            np = _numpy()
            frame = _array_frame(np.load(path, allow_pickle=False))
        else:
            np = _numpy()
            with np.load(path, allow_pickle=False) as archive:
                key = data_spec.get("key")
                if key is None:
                    if len(archive.files) != 1:
                        raise DataError(
                            "NPZ contains multiple arrays; set data.key explicitly"
                        )
                    key = archive.files[0]
                if key not in archive.files:
                    raise DataError(f"NPZ key not found: {key}")
                frame = _array_frame(archive[key])
    except DependencyError:
        raise
    except DataError:
        raise
    except ImportError as exc:
        raise DependencyError(
            f"A declared dependency is missing while reading {data_format}: {exc}"
        ) from exc
    except Exception as exc:
        raise DataError(f"Failed to read {path}: {exc}") from exc

    if frame.empty:
        raise DataError(f"Input data is empty: {path}")
    columns = [str(column) for column in frame.columns]
    if len(set(columns)) != len(columns):
        raise DataError("Column names become ambiguous when converted to strings")
    frame = frame.copy()
    frame.columns = columns
    return frame, path, data_format


def validate_plot_data(frame: Any, plot: dict[str, Any]) -> None:
    pd = _pandas()
    mapping = plot["mapping"]
    kind = plot["kind"]
    descriptor = TEMPLATE_CATALOG[kind]
    keys = list(descriptor["required_mapping"])
    keys.extend(
        key for key in descriptor["optional_mapping"] if key in mapping
    )
    columns = [mapping[key] for key in keys]
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise DataError(
            "Mapped column(s) not found: "
            + ", ".join(missing)
            + ". Available columns: "
            + ", ".join(frame.columns)
        )
    null_counts = {column: int(frame[column].isna().sum()) for column in columns}
    null_counts = {column: count for column, count in null_counts.items() if count}
    if null_counts:
        details = ", ".join(f"{column}={count}" for column, count in null_counts.items())
        raise DataError(f"Mapped columns contain missing values: {details}")

    numeric_geometry = {mapping["value"] if kind == "heatmap" else mapping["y"]}
    if kind == "errorbar":
        if "yerr" in mapping:
            numeric_geometry.add(mapping["yerr"])
        else:
            numeric_geometry.update((mapping["ymin"], mapping["ymax"]))
    x_column = mapping["x"]
    if pd.api.types.is_numeric_dtype(frame[x_column]):
        numeric_geometry.add(x_column)
    np = _numpy()
    for column in numeric_geometry:
        if not pd.api.types.is_numeric_dtype(frame[column]):
            raise DataError(f"Mapped numeric column is not numeric: {column}")
        values = frame[column].to_numpy(dtype=float)
        if not np.isfinite(values).all():
            raise DataError(f"Mapped numeric column contains non-finite values: {column}")
    if kind == "errorbar":
        y = frame[mapping["y"]].to_numpy(dtype=float)
        if "yerr" in mapping:
            yerr = frame[mapping["yerr"]].to_numpy(dtype=float)
            if (yerr < 0).any():
                raise DataError("Errorbar yerr values must be non-negative")
        else:
            ymin = frame[mapping["ymin"]].to_numpy(dtype=float)
            ymax = frame[mapping["ymax"]].to_numpy(dtype=float)
            if (ymin > y).any() or (y > ymax).any():
                raise DataError("Errorbar bounds must satisfy ymin <= y <= ymax")
    if len(frame.index) < 1:
        raise DataError("Plot data must contain at least one row")


def load_plot_data(plot: dict[str, Any], spec_path: Path):
    frame, path, data_format = load_table(plot["data"], spec_path)
    validate_plot_data(frame, plot)
    return frame, path, data_format


def inspect_table(path: Path, *, data_format: str | None = None, key: str | None = None) -> dict[str, Any]:
    fake_spec = path.parent / "inspect.spec.json"
    frame, resolved, resolved_format = load_table(
        {"path": str(path), "format": data_format, "key": key},
        fake_spec,
    )
    return {
        "path": str(resolved),
        "format": resolved_format,
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "column_names": list(frame.columns),
        "dtypes": {column: str(dtype) for column, dtype in frame.dtypes.items()},
        "missing": {column: int(count) for column, count in frame.isna().sum().items()},
    }
