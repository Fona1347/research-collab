#!/usr/bin/env python3
"""Create a non-destructive research-opportunity-map run from bundled templates."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path


TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^\w.-]+", "-", value, flags=re.UNICODE)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value or "research-map"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize a research opportunity mapping run."
    )
    parser.add_argument("--domain", required=True, help="Domain or decision topic.")
    parser.add_argument(
        "--output", required=True, type=Path, help="Parent directory for the new run."
    )
    parser.add_argument(
        "--run-name",
        help="Optional directory name. Default: YYYY-MM-DD-<domain-slug>.",
    )
    parser.add_argument(
        "--short-task-name",
        help=(
            "Short name used in the reader report filename. "
            "Default: a shortened domain slug."
        ),
    )
    parser.add_argument(
        "--language", default="zh-CN", help="Working language metadata (default: zh-CN)."
    )
    parser.add_argument("--date", dest="run_date", type=date.fromisoformat,
                        help="Run date in YYYY-MM-DD; defaults to the local date read once.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not TEMPLATE_DIR.is_dir():
        print(f"Template directory not found: {TEMPLATE_DIR}", file=sys.stderr)
        return 2

    run_date = args.run_date or date.today()
    run_name = slugify(args.run_name or f"{run_date.isoformat()}-{args.domain}")
    short_task_name = slugify(args.short_task_name or args.domain)[:48].rstrip("-._")
    short_task_name = short_task_name or "research-map"
    report_filename = (
        f"map_report_{short_task_name}_{run_date.isoformat()}.md"
    )
    target = args.output.expanduser().resolve() / run_name

    if target.exists():
        print(
            f"Refusing to overwrite existing run directory: {target}", file=sys.stderr
        )
        return 2

    replacements = {
        "{{DOMAIN}}": args.domain.strip(),
        "{{DATE}}": run_date.isoformat(),
        "{{LANGUAGE}}": args.language.strip(),
        "{{RUN_ID}}": run_name,
        "{{SHORT_TASK_NAME}}": short_task_name,
    }

    template_files = sorted(TEMPLATE_DIR.glob("*.md"))
    if not template_files:
        print(f"No Markdown templates found in: {TEMPLATE_DIR}", file=sys.stderr)
        return 2

    target.mkdir(parents=True)

    artifact_files: list[str] = []
    for source in template_files:
        content = source.read_text(encoding="utf-8")
        for token, value in replacements.items():
            content = content.replace(token, value)
        output_name = report_filename if source.name == "map_report.md" else source.name
        (target / output_name).write_text(content, encoding="utf-8", newline="\n")
        artifact_files.append(output_name)

    manifest = {
        "schema_version": "1.2",
        "skill": "research-opportunity-mapper-quick",
        "run_id": run_name,
        "domain": args.domain.strip(),
        "short_task_name": short_task_name,
        "language": args.language.strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "primary_artifact": report_filename,
        "artifact_files": artifact_files,
    }
    (target / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
