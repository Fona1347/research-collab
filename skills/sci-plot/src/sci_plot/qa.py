from __future__ import annotations

from pathlib import Path
from typing import Any
import re
import shutil
import subprocess
import warnings as warning_capture
import xml.etree.ElementTree as ET

from .errors import SafetyError


def pdf_tools() -> dict[str, str | None]:
    return {name: shutil.which(name) for name in ("pdfinfo", "pdffonts", "pdftoppm")}


def _inspect_pdf(path: Path, expected_size_mm) -> tuple[dict, list[str]]:
    tools = pdf_tools()
    result, notes = {}, []
    if not tools["pdfinfo"] or not tools["pdffonts"]:
        return {"metadata_status": "not_checked"}, ["PDF metadata/fonts need existing Poppler pdfinfo and pdffonts; request installation if unavailable."]
    def run(tool):
        completed = subprocess.run([tools[tool], str(path)], capture_output=True, text=True,
                                   encoding="utf-8", errors="replace", timeout=30)
        if completed.returncode:
            raise SafetyError(f"{tool} failed for {path}: {completed.stderr.strip()}")
        return completed.stdout
    info = run("pdfinfo")
    pages = re.search(r"^Pages:\s+(\d+)", info, re.M)
    size = re.search(r"^Page size:\s+([\d.]+) x ([\d.]+) pts", info, re.M)
    if not pages or not size:
        raise SafetyError("Could not parse PDF page metadata from Poppler")
    result.update(metadata_status="checked", pages=int(pages[1]),
                  size_mm=[float(size[i]) * 25.4 / 72 for i in (1, 2)])
    if result["pages"] != 1:
        raise SafetyError("A figure export must have exactly one PDF page")
    if expected_size_mm and any(abs(a-b) > .1 for a, b in zip(result["size_mm"], expected_size_mm)):
        raise SafetyError("PDF physical dimensions do not match the figure")
    fonts = []
    for line in run("pdffonts").splitlines()[2:]:
        match = re.search(r"\s+(yes|no)\s+(yes|no)\s+(yes|no)\s+\d+\s+\d+\s*$", line)
        if line.strip() and not match:
            raise SafetyError("Could not parse PDF font evidence from Poppler")
        if match:
            fonts.append({"name": line.split()[0], "embedded": match[1] == "yes",
                          "unicode_map": match[3] == "yes", "type3": "Type 3" in line})
    result["fonts"] = fonts
    if any(not f["embedded"] for f in fonts):
        notes.append("PDF contains a font that is not embedded")
    if any(f["type3"] for f in fonts):
        notes.append("PDF contains Type 3 fonts; text editing/search may be limited")
    return result, notes


def audit_figure(figure) -> dict:
    """Advisory canvas/font checks; these do not certify absence of overlap."""
    from matplotlib.text import Text
    with warning_capture.catch_warnings(record=True) as caught:
        warning_capture.simplefilter("always")
        figure.canvas.draw()
    notes = list(dict.fromkeys(str(w.message) for w in caught))
    renderer = figure.canvas.get_renderer()
    box = figure.bbox
    outside, fonts = [], set()
    # Locators retain ticks beyond view limits; Matplotlib does not draw them.
    undrawn_ticks = set()
    for axes in figure.axes:
        for axis in (axes.xaxis, axes.yaxis):
            low, high = sorted(axis.get_view_interval())
            for tick in [*axis.get_major_ticks(), *axis.get_minor_ticks()]:
                if not low <= tick.get_loc() <= high:
                    undrawn_ticks.update((id(tick.label1), id(tick.label2)))
    for text in figure.findobj(match=Text):
        if id(text) in undrawn_ticks or not text.get_visible() or not text.get_text().strip():
            continue
        fonts.add((tuple(text.get_fontfamily()), float(text.get_fontsize())))
        extent = text.get_window_extent(renderer)
        if extent.width and extent.height and (extent.x0 < box.x0-2 or extent.y0 < box.y0-2
                                               or extent.x1 > box.x1+2 or extent.y1 > box.y1+2):
            outside.append(text.get_text()[:100])
    if outside:
        notes.append("Possible text outside canvas: " + ", ".join(dict.fromkeys(outside)))
    return {"fonts": [{"families": list(f), "size_pt": s} for f, s in sorted(fonts)],
            "outside_canvas": list(dict.fromkeys(outside)), "warnings": notes,
            "overlap_detection": "requires visual review"}


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
            try:
                svg = ET.fromstring(text)
            except ET.ParseError as exc:
                raise SafetyError(f"Invalid SVG output: {path}") from exc
            if not svg.tag.endswith("svg"):
                raise SafetyError(f"Invalid SVG output: {path}")
            check["editable_text"] = "<text" in text
            if not check["editable_text"]:
                raise SafetyError(f"SVG contains no editable text nodes: {path}")
            if expected_size_mm:
                dimensions = []
                for key in ("width", "height"):
                    match = re.fullmatch(r"([\d.]+)(pt|mm|in|px)", svg.get(key, ""))
                    if not match:
                        raise SafetyError(f"SVG has no supported physical {key}")
                    dimensions.append(float(match[1]) * {"pt": 25.4/72, "mm": 1, "in": 25.4, "px": 25.4/96}[match[2]])
                check["size_mm"] = dimensions
                if any(abs(a-b) > .1 for a, b in zip(dimensions, expected_size_mm)):
                    raise SafetyError("SVG physical dimensions do not match the figure")
        elif output_format == "pdf":
            if not path.read_bytes().startswith(b"%PDF"):
                raise SafetyError(f"Invalid PDF output: {path}")
            metadata, notes = _inspect_pdf(path, expected_size_mm)
            check.update(metadata)
            warnings.extend(notes)
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
                else:
                    warnings.append(f"Raster has no DPI metadata: {path.name}")
                if output_format == "tiff" and image.mode != "RGBA":
                    raise SafetyError(f"TIFF is not RGBA: {path} ({image.mode})")
                if dpi and min(float(value) for value in dpi) < expected_dpi * 0.95:
                    warnings.append(
                        f"Raster DPI is below the requested value {expected_dpi}: {path} ({dpi})"
                    )
        checks.append(check)
    return {"checks": checks, "warnings": warnings}
