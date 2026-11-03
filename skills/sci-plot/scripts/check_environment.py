#!/usr/bin/env python3
"""Report Sci Plot dependencies without installing or changing anything."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys
import shutil

REQUIRED = ("matplotlib", "numpy", "openpyxl", "pandas", "Pillow", "SciencePlots")
OPTIONAL = ("pubfig", "scipy")


def version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require",
        action="store_true",
        help="Return a failure status when a required dependency is absent",
    )
    parser.add_argument("--require-pdf", action="store_true", help="Also require existing Poppler PDF checks/previews")
    args = parser.parse_args(argv)
    required = {name: version(name) for name in REQUIRED}
    optional = {name: version(name) for name in OPTIONAL}
    result = {
        "python": sys.version.split()[0],
        "executable": sys.executable,
        "required": required,
        "optional": optional,
        "missing_required": [name for name, value in required.items() if not value],
        "environment_modified": False,
        "pdf_tools": {name: shutil.which(name) for name in ("pdfinfo", "pdffonts", "pdftoppm")},
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    missing_pdf = any(not value for value in result["pdf_tools"].values())
    return 1 if (args.require and result["missing_required"]) or (args.require_pdf and missing_pdf) else 0


if __name__ == "__main__":
    raise SystemExit(main())
