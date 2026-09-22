from __future__ import annotations

import math
import os
import tempfile
import warnings
from collections.abc import Iterator
from contextlib import contextmanager, nullcontext
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .backends import Backend, resolve_backend
from .config import load_effective_config
from .data import load_plot_data
from .errors import ConfigurationError, DataError, DependencyError
from .spec import iter_plot_specs

DEFAULT_PALETTE = [
    "#0072B2",
    "#E69F00",
    "#009E73",
    "#CC79A7",
    "#56B4E9",
    "#D55E00",
    "#F0E442",
    "#000000",
]
THEME_PALETTES = {
    "paper": DEFAULT_PALETTE,
    "nature": ["#3C5488", "#E64B35", "#00A087", "#4DBBD5", "#F39B7F", "#8491B4"],
    "science": ["#3B4992", "#EE0000", "#008B45", "#631879", "#008280", "#BB0021"],
    "cell": ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4"],
}
THEME_RC = {
    "paper": {},
    "nature": {"lines.linewidth": 1.1, "axes.linewidth": 0.8},
    "science": {
        "lines.linewidth": 1.3,
        "axes.linewidth": 0.9,
        "axes.titleweight": "bold",
    },
    "cell": {
        "lines.linewidth": 1.4,
        "axes.linewidth": 1.0,
        "axes.titleweight": "bold",
    },
    "custom": {},
}
STYLE_RC = {
    "general-paper": {},
    "minimal": {
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "xtick.major.size": 0.0,
        "ytick.major.size": 0.0,
    },
    "custom": {},
}


@dataclass
class RenderedFigure:
    figure: Any
    backend: Backend
    inputs: list[Path]
    data_formats: list[str]
    warnings: list[str]
    rc_params: dict[str, Any]


@dataclass(frozen=True)
class AppliedStyle:
    config_path: Path | None
    palette: tuple[str, ...]
    width_mm: float
    height_mm: float
    dpi: int
    formats: tuple[str, ...]


def publication_rc(config: dict[str, Any]) -> dict[str, Any]:
    render = config["render"]
    font_stack = ["Arial"]
    if render.get("chinese_font"):
        font_stack.append(render["chinese_font"])
    font_stack.extend(["Helvetica", "DejaVu Sans", "sans-serif"])
    rc: dict[str, Any] = {
        "font.family": "sans-serif",
        "font.sans-serif": font_stack,
        "font.size": render["font_size"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "axes.spines.right": False,
        "axes.spines.top": False,
        "axes.linewidth": 0.8,
        "lines.linewidth": 1.2,
        "lines.markersize": 4.0,
        "legend.frameon": False,
        "axes.grid": render.get("grid", False),
        "grid.alpha": 0.25,
    }
    rc.update(THEME_RC[render["theme"]])
    rc.update(STYLE_RC[render["style"]])
    custom = render.get("rcparams")
    if isinstance(custom, dict):
        rc.update(custom)
    return rc


def resolved_palette(config: dict[str, Any]) -> list[str]:
    render = config["render"]
    if render.get("palette"):
        return list(render["palette"])
    return list(THEME_PALETTES.get(render["theme"], DEFAULT_PALETTE))


def _validate_requested_font(config: dict[str, Any]) -> None:
    requested = config["render"].get("chinese_font")
    if not requested:
        return
    from matplotlib import font_manager

    try:
        font_manager.findfont(str(requested), fallback_to_default=False)
    except ValueError as exc:
        raise ConfigurationError(
            f"Configured render.chinese_font is not installed: {requested}"
        ) from exc


def _validate_matplotlib_settings(
    matplotlib: Any,
    rc: dict[str, Any],
    palette: list[str],
) -> None:
    for key, value in rc.items():
        validator = matplotlib.rcParams.validate.get(key)
        if validator is None:
            raise ConfigurationError(f"Unknown Matplotlib rcParam: {key}")
        try:
            validator(value)
        except (TypeError, ValueError) as exc:
            raise ConfigurationError(
                f"Invalid Matplotlib rcParam value for {key}: {value!r}"
            ) from exc
    from matplotlib.colors import is_color_like

    invalid = [color for color in palette if not is_color_like(color)]
    if invalid:
        raise ConfigurationError(
            "Invalid render.palette color(s): " + ", ".join(repr(item) for item in invalid)
        )


@contextmanager
def _style_context(
    matplotlib: Any,
    plt: Any,
    config: dict[str, Any],
) -> Iterator[tuple[dict[str, Any], list[str]]]:
    render = config["render"]
    palette = resolved_palette(config)
    rc = publication_rc(config)
    rc.update(
        {
            "figure.dpi": render["dpi"],
            "figure.figsize": [
                render["width_mm"] / 25.4,
                render["height_mm"] / 25.4,
            ],
            "savefig.dpi": render["dpi"],
        }
    )
    _validate_matplotlib_settings(matplotlib, rc, palette)
    rc["axes.prop_cycle"] = matplotlib.cycler(color=palette)
    _validate_requested_font(config)

    if render.get("scienceplots"):
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    category=matplotlib.MatplotlibDeprecationWarning,
                    module=r"scienceplots(?:\.|$)",
                )
                import scienceplots  # noqa: F401
        except ImportError as exc:
            raise DependencyError(
                "SciencePlots is enabled but not installed; install the declared project dependencies"
            ) from exc
        optional_style = plt.style.context(["science", "no-latex"])
    else:
        optional_style = nullcontext()

    with optional_style:
        with matplotlib.rc_context(rc=rc):
            yield rc, palette


@contextmanager
def project_style(project_root: str | Path) -> Iterator[AppliedStyle]:
    root = Path(project_root).expanduser().resolve()
    if not root.is_dir():
        raise ConfigurationError(f"Project root is not a directory: {root}")
    config, config_path = load_effective_config(project_root=root)
    try:
        import matplotlib
        import matplotlib.pyplot as plt
    except ImportError as exc:
        raise DependencyError(
            "Matplotlib is required to apply a Sci Plot project style"
        ) from exc

    with _style_context(matplotlib, plt, config) as (_, palette):
        render = config["render"]
        yield AppliedStyle(
            config_path=config_path,
            palette=tuple(palette),
            width_mm=render["width_mm"],
            height_mm=render["height_mm"],
            dpi=render["dpi"],
            formats=tuple(render["formats"]),
        )


def _matplotlib():
    if "MPLCONFIGDIR" not in os.environ:
        cache = Path(tempfile.gettempdir()) / "sci-plot-matplotlib"
        cache.mkdir(parents=True, exist_ok=True)
        os.environ["MPLCONFIGDIR"] = str(cache)
    try:
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError as exc:
        raise DependencyError(
            "Matplotlib and NumPy are required for rendering; install the declared dependencies"
        ) from exc
    return matplotlib, plt, np


def _axis_label(labels: dict[str, Any], key: str) -> str:
    label = str(labels.get(key, ""))
    unit = labels.get(f"{key}_unit")
    if unit is None and isinstance(labels.get("units"), dict):
        unit = labels["units"].get(key)
    return f"{label} ({unit})" if label and unit else label


def _finish_axis(ax: Any, labels: dict[str, Any], has_group: bool) -> None:
    if labels.get("title"):
        ax.set_title(str(labels["title"]))
    x_label = _axis_label(labels, "x")
    y_label = _axis_label(labels, "y")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    if has_group:
        ax.legend()


def _plot_line(ax: Any, frame: Any, mapping: dict[str, str], labels: dict[str, Any], palette: list[str]) -> None:
    group = mapping.get("group")
    if group:
        for index, (name, subset) in enumerate(frame.groupby(group, sort=False)):
            ax.plot(
                subset[mapping["x"]],
                subset[mapping["y"]],
                marker="o",
                color=palette[index % len(palette)],
                label=str(name),
            )
    else:
        ax.plot(frame[mapping["x"]], frame[mapping["y"]], marker="o", color=palette[0])
    _finish_axis(ax, labels, bool(group))


def _plot_errorbar(
    ax: Any,
    frame: Any,
    mapping: dict[str, str],
    labels: dict[str, Any],
    palette: list[str],
    np: Any,
) -> None:
    group = mapping.get("group")
    grouped = frame.groupby(group, sort=False) if group else [(None, frame)]
    for index, (name, subset) in enumerate(grouped):
        y = subset[mapping["y"]].to_numpy(dtype=float)
        if "yerr" in mapping:
            yerr: Any = subset[mapping["yerr"]].to_numpy(dtype=float)
        else:
            ymin = subset[mapping["ymin"]].to_numpy(dtype=float)
            ymax = subset[mapping["ymax"]].to_numpy(dtype=float)
            yerr = np.vstack((y - ymin, ymax - y))
        color = palette[index % len(palette)]
        ax.errorbar(
            subset[mapping["x"]],
            y,
            yerr=yerr,
            marker="o",
            capsize=2.5,
            color=color,
            ecolor=color,
            elinewidth=1.0,
            label=str(name) if group else None,
        )
    _finish_axis(ax, labels, bool(group))


def _plot_scatter(ax: Any, frame: Any, mapping: dict[str, str], labels: dict[str, Any], palette: list[str]) -> None:
    group = mapping.get("group")
    if group:
        for index, (name, subset) in enumerate(frame.groupby(group, sort=False)):
            ax.scatter(
                subset[mapping["x"]],
                subset[mapping["y"]],
                color=palette[index % len(palette)],
                label=str(name),
                s=20,
            )
    else:
        ax.scatter(frame[mapping["x"]], frame[mapping["y"]], color=palette[0], s=20)
    _finish_axis(ax, labels, bool(group))


def _plot_bar(ax: Any, frame: Any, mapping: dict[str, str], labels: dict[str, Any], palette: list[str], np: Any) -> None:
    x_column, y_column = mapping["x"], mapping["y"]
    group = mapping.get("group")
    if group:
        if frame.duplicated([x_column, group]).any():
            raise DataError("Bar data contains duplicate x/group combinations; aggregate explicitly")
        pivot = frame.pivot(index=x_column, columns=group, values=y_column)
        if pivot.isna().any().any():
            raise DataError("Grouped bar data has incomplete x/group combinations")
        positions = np.arange(len(pivot.index), dtype=float)
        width = 0.8 / max(len(pivot.columns), 1)
        for index, column in enumerate(pivot.columns):
            offset = (index - (len(pivot.columns) - 1) / 2) * width
            ax.bar(
                positions + offset,
                pivot[column].to_numpy(),
                width=width,
                color=palette[index % len(palette)],
                label=str(column),
            )
        ax.set_xticks(positions, [str(value) for value in pivot.index])
    else:
        if frame.duplicated([x_column]).any():
            raise DataError("Bar data contains duplicate x values; aggregate explicitly")
        ax.bar(
            [str(value) for value in frame[x_column]],
            frame[y_column],
            color=palette[0],
        )
    _finish_axis(ax, labels, bool(group))


def _plot_heatmap(ax: Any, frame: Any, mapping: dict[str, str], labels: dict[str, Any], figure: Any) -> None:
    x_column, y_column, value_column = mapping["x"], mapping["y"], mapping["value"]
    if frame.duplicated([x_column, y_column]).any():
        raise DataError("Heatmap data contains duplicate x/y cells; aggregate explicitly")
    pivot = frame.pivot(index=y_column, columns=x_column, values=value_column)
    if pivot.isna().any().any():
        raise DataError("Heatmap data does not form a complete rectangular matrix")
    image = ax.imshow(pivot.to_numpy(), aspect="auto", cmap="viridis")
    ax.set_xticks(range(len(pivot.columns)), [str(value) for value in pivot.columns])
    ax.set_yticks(range(len(pivot.index)), [str(value) for value in pivot.index])
    figure.colorbar(image, ax=ax, fraction=0.046, pad=0.04, label=str(labels.get("color", value_column)))
    _finish_axis(ax, labels, False)


def _plot_on_axis(
    ax: Any,
    figure: Any,
    plot: dict[str, Any],
    frame: Any,
    palette: list[str],
    np: Any,
) -> None:
    kind = plot["kind"]
    mapping = plot["mapping"]
    labels = plot.get("labels", {})
    if kind == "line":
        _plot_line(ax, frame, mapping, labels, palette)
    elif kind == "errorbar":
        _plot_errorbar(ax, frame, mapping, labels, palette, np)
    elif kind == "scatter":
        _plot_scatter(ax, frame, mapping, labels, palette)
    elif kind == "bar":
        _plot_bar(ax, frame, mapping, labels, palette, np)
    elif kind == "heatmap":
        _plot_heatmap(ax, frame, mapping, labels, figure)
    else:
        raise DataError(f"Unsupported plot kind: {kind}")


def render_figure(spec: dict[str, Any], spec_path: Path, config: dict[str, Any]) -> RenderedFigure:
    matplotlib, plt, np = _matplotlib()
    backend = resolve_backend(config["render"]["backend"])
    warnings = [backend.warning] if backend.warning else []
    width = config["render"]["width_mm"] / 25.4
    height = config["render"]["height_mm"] / 25.4

    figure = None
    input_files: list[Path] = []
    formats: list[str] = []
    with _style_context(matplotlib, plt, config) as (rc, palette):
        plots = list(iter_plot_specs(spec))
        if spec["kind"] == "multi_panel":
            layout = spec.get("layout", {})
            count = len(plots)
            cols = int(layout.get("cols", min(2, count)))
            rows = int(layout.get("rows", math.ceil(count / cols)))
            if rows * cols < count:
                raise DataError("layout.rows * layout.cols is smaller than the panel count")
            figure, axes = plt.subplots(
                rows,
                cols,
                figsize=(width, height),
                squeeze=False,
                constrained_layout=True,
            )
            flat_axes = list(axes.flat)
        else:
            figure, axis = plt.subplots(figsize=(width, height), constrained_layout=True)
            flat_axes = [axis]

        try:
            for index, plot in enumerate(plots):
                frame, path, data_format = load_plot_data(plot, spec_path)
                if path not in input_files:
                    input_files.append(path)
                    formats.append(data_format)
                _plot_on_axis(flat_axes[index], figure, plot, frame, palette, np)
            for axis in flat_axes[len(plots) :]:
                axis.set_visible(False)
        except Exception:
            plt.close(figure)
            raise

    return RenderedFigure(
        figure=figure,
        backend=backend,
        inputs=input_files,
        data_formats=formats,
        warnings=warnings,
        rc_params=rc,
    )
