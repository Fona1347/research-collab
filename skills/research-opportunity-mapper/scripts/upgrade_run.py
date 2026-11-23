#!/usr/bin/env python3
"""Non-destructively copy a legacy 1.x landscape run into schema 2.0."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Mapping, Sequence

from rom_contract import (
    DISCOVERY_LENSES,
    DOMAIN_LENSES,
    SCHEMA_VERSION,
    SKILL_ID,
    SKILL_VERSION,
    TEMPLATE_DIR,
    VALIDATOR_VERSION,
    ContractError,
    artifact_profile,
    artifact_roles_for_legacy_copy,
    collect_ids_from_texts,
    dedupe_preserving_order,
    json_text,
    language_bucket,
    legacy_artifact_sources,
    load_run_manifest,
    parent_snapshot_dict,
    parse_evidence_window,
    parse_iso_date,
    parse_iso_datetime,
    render_template,
    report_filename,
    require_supported_legacy_version,
    resolve_template_plan,
    sha256_file,
    slugify,
    snapshot_parent_run,
    utc_now,
    validate_custom_domain_lens_notes,
    workspace_relative,
)


@dataclass(frozen=True)
class ClockValues:
    run_date: date
    as_of_date: date
    created_at: datetime


@dataclass(frozen=True)
class UpgradePlan:
    source_dir: Path
    target_dir: Path
    source_schema: str
    source_manifest_sha256: str
    source_hashes: Mapping[str, str]
    copied_files: Mapping[str, bytes]
    primary_artifact: str
    generated_report: tuple[str, str] | None
    manifest: Mapping[str, object]
    migration_report: Mapping[str, object]

    def dry_run_payload(self) -> dict[str, object]:
        created = ["run-manifest.json", "migration-report.json"]
        if self.generated_report is not None:
            created.append(self.generated_report[0])
        return {
            "operation": "legacy-copy-upgrade",
            "dry_run": True,
            "source_run": str(self.source_dir),
            "source_schema": self.source_schema,
            "target_run": str(self.target_dir),
            "target_schema": SCHEMA_VERSION,
            "run_type": "landscape",
            "discovery_lens": self.manifest["discovery_lens"],
            "primary_domain_lens": self.manifest["primary_domain_lens"],
            "completion_status": "migrated-needs-review",
            "would_copy": list(self.copied_files),
            "would_create": created,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_artifact_sha256": {
                key: value
                for key, value in self.source_hashes.items()
                if key != "run-manifest.json"
            },
            "source_will_be_modified": False,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Copy a schema 1.0/1.1/1.2 landscape run into a new schema-2 directory. "
            "In-place migration is never supported."
        )
    )
    parser.add_argument("source_run", type=Path)
    parser.add_argument(
        "--copy-to",
        required=True,
        type=Path,
        help=(
            "Exact new run directory; it must not already exist and must be "
            "disjoint from the source (neither directory may contain the other)."
        ),
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path.cwd(),
        help="Root used for persisted workspace-relative lineage.",
    )
    parser.add_argument(
        "--mode",
        choices=("landscape",),
        default="landscape",
        help="Legacy runs can only be migrated as landscape; derive other modes separately.",
    )
    parser.add_argument(
        "--lens", choices=DISCOVERY_LENSES, default="balanced"
    )
    parser.add_argument(
        "--domain-lens",
        choices=DOMAIN_LENSES,
        default="generic-physical-engineering",
    )
    parser.add_argument("--domain-lens-notes")
    parser.add_argument("--run-name", help="Optional new run ID.")
    parser.add_argument("--short-task-name", help="Optional report short task name.")
    parser.add_argument("--language", help="Optional zh-* or en-* language override.")
    parser.add_argument(
        "--evidence-window",
        help="START:END, START..END, or START; endpoints may be YYYY or YYYY-MM-DD.",
    )
    parser.add_argument("--as-of-date", help="Evidence cutoff in YYYY-MM-DD.")
    parser.add_argument(
        "--date", dest="run_date", help="Migration/report date in YYYY-MM-DD."
    )
    parser.add_argument(
        "--created-at", help="Timezone-aware ISO-8601 timestamp for deterministic replay."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Print the migration plan without writing."
    )
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    return build_parser().parse_args(argv)


def resolve_clock(
    args: argparse.Namespace,
    *,
    today: date | None = None,
    now: datetime | None = None,
) -> ClockValues:
    default_date = today or date.today()
    run_date = (
        parse_iso_date(args.run_date, label="date") if args.run_date else default_date
    )
    as_of_date = (
        parse_iso_date(args.as_of_date, label="as-of-date")
        if args.as_of_date
        else run_date
    )
    if as_of_date > run_date:
        raise ContractError("as-of-date must not be after the migration date")
    created_at = (
        parse_iso_datetime(args.created_at)
        if args.created_at
        else (now or utc_now())
    )
    return ClockValues(run_date=run_date, as_of_date=as_of_date, created_at=created_at)


def build_upgrade_plan(
    args: argparse.Namespace,
    *,
    today: date | None = None,
    now: datetime | None = None,
) -> UpgradePlan:
    clock = resolve_clock(args, today=today, now=now)
    domain_lens_notes = (
        args.domain_lens_notes.strip()
        if args.domain_lens_notes and args.domain_lens_notes.strip()
        else None
    )
    if args.domain_lens == "custom":
        if domain_lens_notes is None:
            raise ContractError("--domain-lens custom requires --domain-lens-notes")
        try:
            domain_lens_notes = validate_custom_domain_lens_notes(domain_lens_notes)
        except ContractError as exc:
            raise ContractError(
                "--domain-lens custom requires --domain-lens-notes with all ten "
                f"labeled Common Lens Interface slots: {exc}"
            ) from exc
    source_dir = args.source_run.expanduser().resolve()
    target_dir = args.copy_to.expanduser().resolve()
    workspace_root = args.workspace_root.expanduser().resolve()
    if not workspace_root.is_dir():
        raise ContractError(f"Workspace root not found: {workspace_root}")
    paths_overlap = (
        source_dir == target_dir
        or target_dir.is_relative_to(source_dir)
        or source_dir.is_relative_to(target_dir)
    )
    if paths_overlap:
        raise ContractError(
            "Source and --copy-to target must be disjoint directories; "
            "neither may contain the other"
        )
    if target_dir.exists():
        raise ContractError(f"Refusing to overwrite existing target: {target_dir}")
    workspace_relative(source_dir, workspace_root, label="source run")
    workspace_relative(
        target_dir, workspace_root, must_exist=False, label="copy target"
    )

    manifest_path, source_manifest = load_run_manifest(source_dir)
    source_version = require_supported_legacy_version(
        source_manifest.get("schema_version")
    )
    source_artifacts, discovered_report = legacy_artifact_sources(
        source_dir, source_manifest
    )
    source_by_name = {path.name: path for path in source_artifacts}
    required_names = {
        "00_intake.md",
        "01_breadth-ledger.md",
        "02_search-log.md",
        "03_evidence-matrix.md",
        "04_research-map.md",
        "05_candidate-portfolio.md",
        "06_red-team.md",
        "07_decision-log.md",
    }
    missing = sorted(required_names - source_by_name.keys())
    if missing:
        raise ContractError(
            f"Legacy run is missing required landscape artifact(s): {', '.join(missing)}"
        )

    copied_files: dict[str, bytes] = {}
    source_hashes: dict[str, str] = {}
    text_contents: list[str] = []
    for artifact in source_artifacts:
        if artifact.name == "run-manifest.json":
            continue
        if artifact.parent != source_dir:
            raise ContractError(
                f"Nested legacy artifacts are not migrated implicitly: {artifact}"
            )
        try:
            data = artifact.read_bytes()
        except OSError as exc:
            raise ContractError(f"Cannot preflight legacy artifact {artifact}: {exc}") from exc
        copied_files[artifact.name] = data
        source_hashes[artifact.name] = sha256_file(artifact)
        if artifact.suffix.lower() in {".md", ".json"}:
            try:
                text_contents.append(data.decode("utf-8"))
            except UnicodeDecodeError as exc:
                raise ContractError(f"Legacy text artifact is not UTF-8: {artifact}") from exc

    source_manifest_sha256 = sha256_file(manifest_path)
    source_hashes["run-manifest.json"] = source_manifest_sha256

    domain = source_manifest.get("domain")
    if not isinstance(domain, str) or not domain.strip():
        raise ContractError("Legacy manifest has no valid domain")
    domain = domain.strip()
    source_language = source_manifest.get("language", "zh-CN")
    language = args.language or (source_language if isinstance(source_language, str) else "zh-CN")
    language_bucket(language)
    run_id = slugify(args.run_name or target_dir.name)
    source_short_name = source_manifest.get("short_task_name")
    report_short_name = None
    if discovered_report is not None:
        match = re.fullmatch(
            r"map_report_(.+)_\d{4}-\d{2}-\d{2}\.md", discovered_report.name
        )
        if match:
            report_short_name = match.group(1)
    short_task_name = slugify(
        args.short_task_name
        or (source_short_name if isinstance(source_short_name, str) else None)
        or report_short_name
        or domain
    )[:48].rstrip("-._")
    short_task_name = short_task_name or "research-map"

    evidence_window = parse_evidence_window(
        args.evidence_window, as_of=clock.as_of_date
    )
    generated_report: tuple[str, str] | None = None
    if discovered_report is not None:
        primary_artifact = discovered_report.name
    else:
        primary_artifact = report_filename("landscape", short_task_name, clock.run_date)
        _, report_template = resolve_template_plan(
            TEMPLATE_DIR, mode="landscape", language=language
        )
        replacements = {
            "{{DOMAIN}}": domain,
            "{{DATE}}": clock.run_date.isoformat(),
            "{{AS_OF_DATE}}": clock.as_of_date.isoformat(),
            "{{LANGUAGE}}": language.strip(),
            "{{RUN_ID}}": run_id,
            "{{SHORT_TASK_NAME}}": short_task_name,
            "{{RUN_TYPE}}": "landscape",
            "{{TASK_MODE}}": "landscape",
            "{{MODE}}": "landscape",
            "{{DISCOVERY_LENS}}": args.lens,
            "{{EVIDENCE_WINDOW}}": (
                f"{evidence_window['start']}..{evidence_window['end']}"
            ),
            "{{EVIDENCE_WINDOW_START}}": str(evidence_window["start"]),
            "{{EVIDENCE_WINDOW_END}}": str(evidence_window["end"]),
            "{{PRIMARY_ARTIFACT}}": primary_artifact,
            "{{PARENT_RUN_ID}}": str(source_manifest.get("run_id", "legacy-run")),
            "{{PARENT_RUN}}": str(source_manifest.get("run_id", "legacy-run")),
            "{{SELECTED_BRANCH}}": "none",
            "{{ROUTING_REQUEST}}": "non-destructive legacy schema migration",
        }
        generated_report = (
            primary_artifact,
            render_template(report_template, replacements),
        )

    if primary_artifact in copied_files and generated_report is not None:
        raise ContractError(f"Generated report would overwrite a copied artifact: {primary_artifact}")
    if "migration-report.json" in copied_files:
        raise ContractError("Legacy artifacts already contain migration-report.json")

    parent = snapshot_parent_run(
        source_dir,
        workspace_root=workspace_root,
        relation="migrated-copy",
    )
    parent_dict = parent_snapshot_dict(parent)
    parent_dict["source_artifact_sha256"] = {
        key: value for key, value in source_hashes.items() if key != "run-manifest.json"
    }

    roles = artifact_roles_for_legacy_copy(
        source_artifacts, report_name=primary_artifact
    )
    inherited_ids = collect_ids_from_texts(text_contents)
    artifact_files = dedupe_preserving_order(
        [*copied_files, primary_artifact, "migration-report.json"]
    )
    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "skill": SKILL_ID,
        "skill_version": SKILL_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "run_id": run_id,
        "domain": domain,
        "short_task_name": short_task_name,
        "language": language.strip(),
        "created_at": clock.created_at.isoformat(),
        "as_of_date": clock.as_of_date.isoformat(),
        "task_mode": "landscape",
        "run_type": "landscape",
        "discovery_lens": args.lens,
        "primary_domain_lens": args.domain_lens,
        "secondary_domain_lenses": [],
        "domain_lens_notes": domain_lens_notes,
        "artifact_profile": artifact_profile("landscape"),
        "completion_status": "migrated-needs-review",
        "parent_mutation_policy": "child-run-only",
        "routing": {
            "request": "non-destructive legacy schema migration",
            "requested": "landscape",
            "selected": "landscape",
            "reason": [f"schema {source_version} legacy contract is a landscape run"],
            "confidence": "high",
        },
        "evidence_window": evidence_window,
        "frontier_policy": {
            "recent_years_default": 3,
            "canonical_pre_window_allowed": True,
            "citation_signal": "field-year-normalized-when-available",
            "citation_source_and_as_of_required": True,
            "salience_is_not_claim_confidence": True,
        },
        "selected_branch": None,
        "lineage": {"parents": [parent_dict]},
        "inherited_ids": inherited_ids,
        "context_sources": [],
        "primary_artifact": primary_artifact,
        "artifact_files": artifact_files,
        "artifact_roles": {**roles, "migration_report": "migration-report.json"},
    }

    migration_report: dict[str, object] = {
        "operation": "legacy-copy-upgrade",
        "source_schema": str(source_version),
        "target_schema": SCHEMA_VERSION,
        "source_run_id": source_manifest.get("run_id"),
        "source_workspace_relpath": workspace_relative(
            source_dir, workspace_root, label="source run"
        ),
        "source_manifest_sha256": source_manifest_sha256,
        "source_artifact_sha256": {
            key: value for key, value in source_hashes.items() if key != "run-manifest.json"
        },
        "copied_files": list(copied_files),
        "generated_report": generated_report[0] if generated_report else None,
        "inferred_fields": {
            "run_type": "landscape",
            "discovery_lens": args.lens,
        },
        "manual_review_required": [
            "Populate all schema-2-only landscape/report sections.",
            "Re-audit evidence confidence and cross-artifact identifiers.",
            "Set completion_status only after schema-2 strict validation.",
        ],
        "source_modified": False,
    }

    return UpgradePlan(
        source_dir=source_dir,
        target_dir=target_dir,
        source_schema=str(source_version),
        source_manifest_sha256=source_manifest_sha256,
        source_hashes=source_hashes,
        copied_files=copied_files,
        primary_artifact=primary_artifact,
        generated_report=generated_report,
        manifest=manifest,
        migration_report=migration_report,
    )


def verify_source_unchanged(plan: UpgradePlan) -> None:
    current_manifest = sha256_file(plan.source_dir / "run-manifest.json")
    if current_manifest != plan.source_manifest_sha256:
        raise ContractError("Source manifest changed while the migration was running")
    for name, expected in plan.source_hashes.items():
        if name == "run-manifest.json":
            continue
        current = sha256_file(plan.source_dir / name)
        if current != expected:
            raise ContractError(f"Source artifact changed while migrating: {name}")


def execute_upgrade(plan: UpgradePlan) -> Path:
    if plan.target_dir.exists():
        raise ContractError(f"Refusing to overwrite existing target: {plan.target_dir}")
    # All source files and generated text were preflighted in memory before this point.
    try:
        plan.target_dir.mkdir(parents=True)
        for name, data in plan.copied_files.items():
            (plan.target_dir / name).write_bytes(data)
        if plan.generated_report is not None:
            name, content = plan.generated_report
            (plan.target_dir / name).write_text(
                content, encoding="utf-8", newline="\n"
            )
        (plan.target_dir / "migration-report.json").write_text(
            json_text(plan.migration_report), encoding="utf-8", newline="\n"
        )
        (plan.target_dir / "run-manifest.json").write_text(
            json_text(plan.manifest), encoding="utf-8", newline="\n"
        )
    except OSError as exc:
        raise ContractError(
            f"Failed while writing migrated run {plan.target_dir}; it may be incomplete: {exc}"
        ) from exc
    verify_source_unchanged(plan)
    return plan.target_dir


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        plan = build_upgrade_plan(args)
        if args.dry_run:
            print(json.dumps(plan.dry_run_payload(), ensure_ascii=False, indent=2))
            return 0
        target = execute_upgrade(plan)
    except ContractError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
