#!/usr/bin/env python3
"""Report Sci Plot dependencies without installing or changing anything."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import sys

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
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if args.require and result["missing_required"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
