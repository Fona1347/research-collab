from __future__ import annotations

import importlib
import importlib.metadata
import inspect
from dataclasses import dataclass
from types import ModuleType

from .errors import DependencyError


@dataclass(frozen=True)
class Backend:
    name: str
    version: str
    module: ModuleType | None
    warning: str | None = None


def installed_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _compatible_pubfig(version: str) -> bool:
    parts = version.split(".", 2)
    try:
        return int(parts[0]) == 0 and int(parts[1]) == 3
    except (ValueError, IndexError):
        return False


def _load_pubfig(version: str) -> ModuleType:
    try:
        return importlib.import_module("pubfig")
    except ImportError as exc:
        missing = getattr(exc, "name", None) or str(exc)
        raise DependencyError(
            f"pubfig {version} is installed but could not be imported because "
            f"'{missing}' is unavailable; repair the explicitly managed plotting "
            "environment before selecting this backend"
        ) from exc


def validate_pubfig_api(module: ModuleType, version: str) -> None:
    save = getattr(module, "save_figure", None)
    figure_spec = getattr(module, "FigureSpec", None)
    if not callable(save) or not callable(figure_spec):
        raise DependencyError(
            f"pubfig {version} lacks the save_figure/FigureSpec API required by "
            "the Sci Plot 0.3 adapter"
        )
    try:
        parameters = inspect.signature(save).parameters
    except (TypeError, ValueError) as exc:
        raise DependencyError(
            f"pubfig {version} save_figure has no inspectable signature"
        ) from exc
    required = {"spec", "width", "height_mm", "raster_dpi", "trim", "svg_fonttype"}
    missing = sorted(required - set(parameters))
    if missing:
        raise DependencyError(
            f"pubfig {version} export API is incompatible with the Sci Plot 0.3 "
            "adapter; missing save_figure parameter(s): " + ", ".join(missing)
        )
    try:
        spec_parameters = inspect.signature(figure_spec).parameters
    except (TypeError, ValueError) as exc:
        raise DependencyError(
            f"pubfig {version} FigureSpec has no inspectable constructor signature"
        ) from exc
    required_spec = {
        "name",
        "font_family",
        "single_column_mm",
        "double_column_mm",
        "default_raster_dpi",
        "background_color",
    }
    missing_spec = sorted(required_spec - set(spec_parameters))
    if missing_spec:
        raise DependencyError(
            f"pubfig {version} FigureSpec API is incompatible with the Sci Plot 0.3 "
            "adapter; missing constructor parameter(s): " + ", ".join(missing_spec)
        )


def _load_compatible_pubfig(version: str) -> ModuleType:
    module = _load_pubfig(version)
    validate_pubfig_api(module, version)
    return module


def resolve_backend(requested: str) -> Backend:
    requested = requested.lower()
    if requested == "matplotlib":
        version = installed_version("matplotlib")
        if version is None:
            raise DependencyError("Matplotlib is not installed")
        return Backend("matplotlib", version, None)

    pubfig_version = installed_version("pubfig")
    if requested == "pubfig":
        if pubfig_version is None:
            raise DependencyError(
                "pubfig was explicitly requested but is not installed; Sci Plot will not install it automatically"
            )
        if not _compatible_pubfig(pubfig_version):
            raise DependencyError(
                f"Unsupported pubfig version {pubfig_version}; expected >=0.3,<0.4"
            )
        return Backend("pubfig", pubfig_version, _load_compatible_pubfig(pubfig_version))

    if requested != "auto":
        raise DependencyError(f"Unknown backend: {requested}")
    if pubfig_version is not None and _compatible_pubfig(pubfig_version):
        try:
            return Backend(
                "pubfig",
                pubfig_version,
                _load_compatible_pubfig(pubfig_version),
            )
        except DependencyError as exc:
            matplotlib_version = installed_version("matplotlib")
            if matplotlib_version is None:
                raise
            return Backend(
                "matplotlib",
                matplotlib_version,
                None,
                f"Ignored unusable pubfig {pubfig_version}; used Matplotlib: {exc}",
            )

    matplotlib_version = installed_version("matplotlib")
    if matplotlib_version is None:
        raise DependencyError("Neither compatible pubfig nor Matplotlib is installed")
    warning = (
        "Compatible pubfig 0.3.x is not installed; used the deterministic Matplotlib fallback"
        if pubfig_version is None
        else f"Ignored incompatible pubfig {pubfig_version}; used Matplotlib"
    )
    return Backend("matplotlib", matplotlib_version, None, warning)
