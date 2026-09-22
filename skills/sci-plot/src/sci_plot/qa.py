from __future__ import annotations

from pathlib import Path
from typing import Any

from .errors import SafetyError


def audit_outputs(
    paths: list[Path],
    formats: list[str],
    *,
    expected_dpi: int,
    expected_size_mm: tuple[float, float] | None = None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    for path, output_format in zip(paths, formats, strict=True):
        if not path.is_file() or path.stat().st_size == 0:
            raise SafetyError(f"Missing or empty exported file: {path}")
        check: dict[str, Any] = {
            "path": str(path),
            "format": output_format,
            "bytes": path.stat().st_size,
            "valid": True,
        }
        if output_format == "svg":
            text = path.read_text(encoding="utf-8", errors="replace")
            if "<svg" not in text:
                raise SafetyError(f"Invalid SVG output: {path}")
            check["editable_text"] = "<text" in text
            if not check["editable_text"]:
                raise SafetyError(f"SVG contains no editable text nodes: {path}")
        elif output_format == "pdf":
            if not path.read_bytes().startswith(b"%PDF"):
                raise SafetyError(f"Invalid PDF output: {path}")
        elif output_format in {"png", "tiff"}:
            try:
                from PIL import Image
            except ImportError as exc:
                raise SafetyError("Pillow is required for raster QA") from exc
            with Image.open(path) as image:
                image.verify()
            with Image.open(path) as image:
                check["mode"] = image.mode
                check["size_px"] = list(image.size)
                if expected_size_mm is not None:
                    expected_size = [
                        round(float(value) / 25.4 * expected_dpi)
                        for value in expected_size_mm
                    ]
                    check["expected_size_px"] = expected_size
                    if any(
                        abs(actual - expected) > 2
                        for actual, expected in zip(image.size, expected_size, strict=True)
                    ):
                        raise SafetyError(
                            f"Raster dimensions do not match the configured physical size: "
                            f"{path} ({image.size} vs {tuple(expected_size)} px)"
                        )
                dpi = image.info.get("dpi")
                if dpi:
                    check["dpi"] = [round(float(value), 2) for value in dpi]
                if output_format == "tiff" and image.mode != "RGBA":
                    raise SafetyError(f"TIFF is not RGBA: {path} ({image.mode})")
                if dpi and min(float(value) for value in dpi) < expected_dpi * 0.95:
                    warnings.append(
                        f"Raster DPI is below the requested value {expected_dpi}: {path} ({dpi})"
                    )
        checks.append(check)
    return {"checks": checks, "warnings": warnings}
