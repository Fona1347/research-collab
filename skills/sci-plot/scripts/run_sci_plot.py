#!/usr/bin/env python3
"""Run the bundled Sci Plot source tree without installing the package."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path


def main() -> None:
    skill_root = Path(__file__).resolve().parents[1]
    source_root = skill_root / "src"
    package_root = source_root / "sci_plot"
    if not package_root.is_dir():
        raise SystemExit(f"Bundled Sci Plot package not found: {package_root}")
    sys.path.insert(0, str(source_root))
    sys.argv[0] = "sci-plot"
    runpy.run_module("sci_plot", run_name="__main__")


if __name__ == "__main__":
    main()
