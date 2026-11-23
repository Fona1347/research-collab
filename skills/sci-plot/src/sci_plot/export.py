from __future__ import annotations

import inspect
import os
import shutil
import tempfile
import warnings
from datetime import datetime
from pathlib import Path
from typing import Any

from .backends import Backend, validate_pubfig_api
from .errors import DependencyError, SafetyError

FORMAT_SUFFIX = {"svg": ".svg", "pdf": ".pdf", "png": ".png", "tiff": ".tiff"}


def _available_font_family(value: Any) -> str:
    try:
        from matplotlib import font_manager
    except ImportError as exc:
        raise DependencyError("Matplotlib font discovery is unavailable") from exc

    candidates = [value] if isinstance(value, str) else list(value or [])
    for candidate in candidates:
        name = str(candidate).strip()
        if not name or name.lower() in {
            "serif",
            "sans-serif",
            "cursive",
            "fantasy",
            "monospace",
        }:
            continue
        try:
            font_manager.findfont(
                font_manager.FontProperties(family=[name]),
                fallback_to_default=False,
            )
        except ValueError:
            continue
        return name
    return "DejaVu Sans"


def _base_without_known_suffix(base: Path) -> Path:
    if base.suffix.lower() in {".svg", ".pdf", ".png", ".tif", ".tiff"}:
        return base.with_suffix("")
    return base


def output_paths(base: Path, formats: list[str]) -> list[Path]:
    if len(formats) == 1:
        expected = FORMAT_SUFFIX[formats[0]]
        if base.suffix.lower() in {expected, ".tif" if formats[0] == "tiff" else expected}:
            return [base.with_suffix(expected)]
    root = _base_without_known_suffix(base)
    return [Path(str(root) + FORMAT_SUFFIX[item]) for item in formats]


def choose_output_paths(
    base: Path,
    formats: list[str],
    *,
    conflict: str,
    overwrite: bool,
    timestamp: str | None = None,
) -> tuple[list[Path], bool]:
    candidates = output_paths(base, formats)
    if overwrite or not any(path.exists() for path in candidates):
        return candidates, False
    if conflict == "error":
        existing = ", ".join(str(path) for path in candidates if path.exists())
        raise SafetyError(f"Output already exists: {existing}")
    if conflict != "timestamp":
        raise SafetyError(f"Unknown output conflict policy: {conflict}")

    stamp = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S")
    root = _base_without_known_suffix(base)
    attempt = root.with_name(f"{root.name}_{stamp}")
    counter = 1
    stamped = output_paths(attempt, formats)
    while any(path.exists() for path in stamped):
        attempt = root.with_name(f"{root.name}_{stamp}_{counter}")
        stamped = output_paths(attempt, formats)
        counter += 1
    return stamped, True


def _temp_path(directory: Path, final: Path, suffix: str | None = None) -> Path:
    handle = tempfile.NamedTemporaryFile(
        dir=directory,
        prefix=f".{final.stem}.",
        suffix=suffix or final.suffix,
        delete=False,
    )
    handle.close()
    path = Path(handle.name)
    path.unlink()
    return path


def _save_pubfig(
    backend: Backend,
    figure: Any,
    path: Path,
    dpi: int,
    *,
    theme: str,
    rc_params: dict[str, Any],
) -> None:
    if backend.module is None:
        raise DependencyError("pubfig backend module is unavailable")
    validate_pubfig_api(backend.module, backend.version)
    save = getattr(backend.module, "save_figure", None)
    assert callable(save)
    parameters = inspect.signature(save).parameters
    figure_spec = getattr(backend.module, "FigureSpec", None)
    assert callable(figure_spec)

    width_mm = float(figure.get_figwidth()) * 25.4
    height_mm = float(figure.get_figheight()) * 25.4
    font_family = _available_font_family(
        rc_params.get("font.sans-serif", ["Arial", "Helvetica", "DejaVu Sans"])
    )
    try:
        from matplotlib.colors import to_hex

        background = to_hex(figure.get_facecolor(), keep_alpha=False)
        spec = figure_spec(
            name=f"sci-plot-{theme}",
            font_family=font_family,
            single_column_mm=width_mm,
            double_column_mm=width_mm,
            default_raster_dpi=dpi,
            background_color=background,
        )
    except (ImportError, TypeError, ValueError) as exc:
        raise DependencyError(
            "Installed pubfig FigureSpec is incompatible with the Sci Plot 0.3 adapter"
        ) from exc

    kwargs: dict[str, Any] = {
        "spec": spec,
        "width": width_mm,
        "height_mm": height_mm,
        "raster_dpi": dpi,
        "trim": False,
        "svg_fonttype": "none",
    }
    if "transparent" in parameters:
        kwargs["transparent"] = False
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="The figure layout has changed to tight",
            category=UserWarning,
        )
        save(figure, str(path), **kwargs)


def _save_tiff_rgba(figure: Any, path: Path, dpi: int) -> None:
    try:
        from PIL import Image
    except ImportError as exc:
        raise DependencyError("Pillow is required for RGBA TIFF export") from exc
    raw_png = _temp_path(path.parent, path, ".png")
    try:
        figure.savefig(
            raw_png,
            format="png",
            dpi=dpi,
            transparent=True,
        )
        with Image.open(raw_png) as image:
            rgba = image.convert("RGBA")
            rgba.save(path, format="TIFF", compression="tiff_lzw", dpi=(dpi, dpi))
    finally:
        raw_png.unlink(missing_ok=True)


def _save_one(
    figure: Any,
    path: Path,
    output_format: str,
    *,
    dpi: int,
    backend: Backend,
    theme: str,
    rc_params: dict[str, Any],
) -> list[str]:
    if output_format == "tiff":
        _save_tiff_rgba(figure, path, dpi)
    elif backend.name == "pubfig":
        _save_pubfig(
            backend,
            figure,
            path,
            dpi,
            theme=theme,
            rc_params=rc_params,
        )
    else:
        figure.savefig(
            path,
            format=output_format,
            dpi=dpi if output_format == "png" else None,
        )
    if not path.is_file() or path.stat().st_size == 0:
        raise SafetyError(f"Exporter did not create a non-empty file: {path}")


def export_figure(
    figure: Any,
    paths: list[Path],
    formats: list[str],
    *,
    dpi: int,
    backend: Backend,
    rc_params: dict[str, Any],
    theme: str,
    overwrite: bool,
) -> None:
    if len(paths) != len(formats):
        raise SafetyError("Output path and format counts do not match")
    try:
        import matplotlib as mpl
    except ImportError as exc:
        raise DependencyError("Matplotlib is required for export") from exc

    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)

    temporary: list[Path] = []
    reserved: list[Path] = []
    committed: list[Path] = []
    backups: dict[Path, Path] = {}
    try:
        with mpl.rc_context(rc=rc_params):
            for final, output_format in zip(paths, formats, strict=True):
                temp = _temp_path(final.parent, final)
                temporary.append(temp)
                _save_one(
                    figure,
                    temp,
                    output_format,
                    dpi=dpi,
                    backend=backend,
                    theme=theme,
                    rc_params=rc_params,
                )

        if overwrite:
            for final in paths:
                if final.is_file():
                    backup = _temp_path(final.parent, final, final.suffix + ".bak")
                    shutil.copy2(final, backup)
                    backups[final] = backup
        else:
            for final in paths:
                try:
                    with final.open("xb"):
                        pass
                except FileExistsError as exc:
                    raise SafetyError(
                        f"Output appeared during export and was not overwritten: {final}"
                    ) from exc
                reserved.append(final)

        for temp, final in zip(temporary, paths, strict=True):
            os.replace(temp, final)
            committed.append(final)
        temporary.clear()
    except Exception as exc:
        for temp in temporary:
            temp.unlink(missing_ok=True)
        rollback_errors: list[str] = []
        if overwrite:
            for final in reversed(committed):
                backup = backups.get(final)
                try:
                    if backup is None:
                        final.unlink(missing_ok=True)
                    else:
                        os.replace(backup, final)
                        backups.pop(final, None)
                except OSError as rollback_exc:
                    recovery = f"; recovery copy: {backup}" if backup else ""
                    rollback_errors.append(f"{final}: {rollback_exc}{recovery}")
            committed_set = set(committed)
            for final, backup in list(backups.items()):
                if final not in committed_set:
                    try:
                        backup.unlink(missing_ok=True)
                    except OSError:
                        pass
        else:
            for path in reserved:
                path.unlink(missing_ok=True)
        if rollback_errors:
            raise SafetyError(
                "Export failed and overwrite rollback was incomplete: "
                + "; ".join(rollback_errors)
            ) from exc
        raise

    cleanup_warnings: list[str] = []
    for backup in backups.values():
        try:
            backup.unlink(missing_ok=True)
        except OSError as exc:
            cleanup_warnings.append(
                f"Committed outputs are valid, but an overwrite recovery copy "
                f"could not be removed: {backup} ({exc})"
            )
    return cleanup_warnings
