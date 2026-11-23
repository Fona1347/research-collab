#!/usr/bin/env python3
"""Create a non-destructive schema-2 research-opportunity-mapper run."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Sequence

from rom_contract import (
    CAPABILITY_ID_PATTERN,
    CLAIM_ID_PATTERN,
    DISCOVERY_LENSES,
    DOMAIN_LENSES,
    EVIDENCE_ID_PATTERN,
    REQUESTED_MODES,
    ROUTING_CONFIDENCE,
    RUN_TYPES,
    SCHEMA_VERSION,
    SKILL_ID,
    SKILL_VERSION,
    TEMPLATE_DIR,
    VALIDATOR_VERSION,
    WORKFLOW_CONTRACTS_BY_MODE,
    ContractError,
    artifact_profile,
    build_context_sources,
    json_text,
    language_bucket,
    parent_relation,
    parent_snapshot_dict,
    parse_evidence_window,
    parse_iso_date,
    parse_iso_datetime,
    render_template,
    report_filename,
    resolve_template_plan,
    slugify,
    snapshot_parent_run,
    utc_now,
    validate_custom_domain_lens_notes,
    validate_branch_selection,
    validate_inherited_ids,
)


@dataclass(frozen=True)
class ClockValues:
    run_date: date
    as_of_date: date
    created_at: datetime


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Initialize a schema-2 research opportunity mapping run."
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
        help="Short name used in the reader report filename.",
    )
    parser.add_argument(
        "--language", default="zh-CN", help="Template language tag (zh-* or en-*)."
    )

    parser.add_argument(
        "--mode",
        choices=RUN_TYPES,
        default="landscape",
        help="Persisted run type. 'auto' is intentionally not a valid persisted mode.",
    )
    parser.add_argument(
        "--lens",
        choices=DISCOVERY_LENSES,
        default="balanced",
        help="Discovery lens, orthogonal to run type (default: balanced).",
    )
    parser.add_argument(
        "--domain-lens",
        choices=DOMAIN_LENSES,
        default="generic-physical-engineering",
        help="Primary causal/domain contract; use custom with --domain-lens-notes.",
    )
    parser.add_argument(
        "--secondary-domain-lens",
        action="append",
        choices=DOMAIN_LENSES,
        default=[],
        help="Optional interface-crossing secondary lens; repeatable.",
    )
    parser.add_argument(
        "--domain-lens-notes",
        help="For custom: all ten labeled Common Lens Interface slots from references/domain-lenses.md.",
    )
    parser.add_argument(
        "--requested-mode",
        choices=REQUESTED_MODES,
        help="Requested mode before routing; may be auto. Default: the selected --mode.",
    )
    parser.add_argument(
        "--request",
        help="Optional original natural-language request stored in routing metadata.",
    )
    parser.add_argument(
        "--routing-reason",
        action="append",
        default=[],
        help="Routing reason; repeat to preserve multiple reasons.",
    )
    parser.add_argument(
        "--routing-confidence",
        choices=ROUTING_CONFIDENCE,
        help="Confidence in the deterministic routing decision.",
    )

    parser.add_argument(
        "--parent-run", type=Path, help="Existing parent run; it is read but never modified."
    )
    parser.add_argument(
        "--workspace-root",
        type=Path,
        default=Path.cwd(),
        help="Root used to persist safe workspace-relative lineage/context paths.",
    )
    parser.add_argument(
        "--selected-branch",
        help=(
            "Parent BR-### branch, C-### route, or I-### interface ID; "
            "a standalone focus label is also accepted."
        ),
    )
    parser.add_argument(
        "--inherit-claim", action="append", default=[], help="Inherited claim ID; repeatable."
    )
    parser.add_argument(
        "--inherit-evidence",
        action="append",
        default=[],
        help="Inherited evidence ID; repeatable.",
    )
    parser.add_argument(
        "--inherit-capability",
        action="append",
        default=[],
        help="Inherited capability ID; repeatable.",
    )
    parser.add_argument(
        "--context-source",
        action="append",
        default=[],
        metavar="ROLE=PATH",
        help="Read-only workspace context source; repeatable.",
    )
    parser.add_argument(
        "--capability-profile",
        type=Path,
        help="Read-only external capability profile inside the workspace.",
    )

    parser.add_argument(
        "--evidence-window",
        help="START:END, START..END, or START; endpoints may be YYYY or YYYY-MM-DD.",
    )
    parser.add_argument(
        "--as-of-date",
        help="Evidence cutoff in YYYY-MM-DD; default: --date/current date.",
    )
    parser.add_argument(
        "--date",
        dest="run_date",
        help="Run/report date in YYYY-MM-DD for deterministic replay.",
    )
    parser.add_argument(
        "--created-at",
        help="Timezone-aware ISO-8601 creation timestamp for deterministic replay/testing.",
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
        raise ContractError("as-of-date must not be after the run date")
    created_at = (
        parse_iso_datetime(args.created_at)
        if args.created_at
        else (now or utc_now())
    )
    return ClockValues(run_date=run_date, as_of_date=as_of_date, created_at=created_at)


def initialize_run(
    args: argparse.Namespace,
    *,
    today: date | None = None,
    now: datetime | None = None,
) -> Path:
    clock = resolve_clock(args, today=today, now=now)
    domain = args.domain.strip()
    if not domain:
        raise ContractError("--domain cannot be empty")
    language_bucket(args.language)
    secondary_domain_lenses = list(dict.fromkeys(args.secondary_domain_lens))
    if len(secondary_domain_lenses) != len(args.secondary_domain_lens):
        raise ContractError("--secondary-domain-lens values must be unique")
    if args.domain_lens in secondary_domain_lenses:
        raise ContractError("The primary domain lens cannot also be secondary")
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

    workspace_root = args.workspace_root.expanduser().resolve()
    if not workspace_root.is_dir():
        raise ContractError(f"Workspace root not found: {workspace_root}")

    requested_mode = args.requested_mode or args.mode
    routing_reasons = [value.strip() for value in args.routing_reason if value.strip()]
    if requested_mode == "auto" and not (args.request and args.request.strip()) and not routing_reasons:
        raise ContractError(
            "--requested-mode auto requires --request or at least one --routing-reason"
        )
    if not routing_reasons:
        routing_reasons = [
            "explicit persisted mode" if requested_mode == args.mode else "deterministic mode routing"
        ]
    routing_confidence = args.routing_confidence or (
        "high" if requested_mode == args.mode else "moderate"
    )

    parent = None
    if args.parent_run is not None:
        parent = snapshot_parent_run(
            args.parent_run,
            workspace_root=workspace_root,
            relation=parent_relation(args.mode),
        )
    if args.mode == "run-audit" and parent is None:
        raise ContractError("run-audit requires --parent-run")

    context_sources = build_context_sources(
        args.context_source,
        capability_profile=args.capability_profile,
        workspace_root=workspace_root,
    )
    if args.mode == "evidence-audit" and parent is None and not context_sources:
        raise ContractError(
            "evidence-audit requires --parent-run, --context-source, or --capability-profile"
        )

    selected_branch = validate_branch_selection(args.selected_branch, parent=parent)
    if args.mode == "focus" and parent is not None and selected_branch is None:
        raise ContractError("focus with --parent-run requires --selected-branch")

    inherited_ids = {
        "claims": validate_inherited_ids(
            args.inherit_claim,
            pattern=CLAIM_ID_PATTERN,
            label="inherited claim ID",
            parent=parent,
        ),
        "evidence": validate_inherited_ids(
            args.inherit_evidence,
            pattern=EVIDENCE_ID_PATTERN,
            label="inherited evidence ID",
            parent=parent,
        ),
        "capabilities": validate_inherited_ids(
            args.inherit_capability,
            pattern=CAPABILITY_ID_PATTERN,
            label="inherited capability ID",
            parent=parent,
        ),
    }

    evidence_window = parse_evidence_window(
        args.evidence_window, as_of=clock.as_of_date
    )
    run_name = slugify(args.run_name or f"{clock.run_date.isoformat()}-{domain}")
    short_task_name = slugify(args.short_task_name or domain)[:48].rstrip("-._")
    short_task_name = short_task_name or "research-map"
    primary_artifact = report_filename(args.mode, short_task_name, clock.run_date)
    target = args.output.expanduser().resolve() / run_name
    if target.exists():
        raise ContractError(f"Refusing to overwrite existing run directory: {target}")

    # Resolve and read every template before creating the output directory.
    artifact_templates, report_template = resolve_template_plan(
        TEMPLATE_DIR, mode=args.mode, language=args.language
    )
    artifact_roles = {entry.role: entry.output_name for entry in artifact_templates}
    artifact_roles["reader_report"] = primary_artifact
    if any(value is None for value in artifact_roles.values()):
        raise ContractError("Template plan contains an artifact without an output filename")
    output_names = [str(value) for value in artifact_roles.values()]
    if len(set(output_names)) != len(output_names):
        raise ContractError("Template plan would create duplicate output filenames")

    branch_display = "none"
    if selected_branch is not None:
        branch_display = str(selected_branch.get("id") or selected_branch.get("label"))
    replacements = {
        "{{DOMAIN}}": domain,
        "{{DATE}}": clock.run_date.isoformat(),
        "{{AS_OF_DATE}}": clock.as_of_date.isoformat(),
        "{{LANGUAGE}}": args.language.strip(),
        "{{RUN_ID}}": run_name,
        "{{SHORT_TASK_NAME}}": short_task_name,
        "{{RUN_TYPE}}": args.mode,
        "{{TASK_MODE}}": args.mode,
        "{{MODE}}": args.mode,
        "{{DISCOVERY_LENS}}": args.lens,
        "{{PRIMARY_DOMAIN_LENS}}": args.domain_lens,
        "{{SECONDARY_DOMAIN_LENSES}}": ", ".join(secondary_domain_lenses) or "none",
        "{{DOMAIN_LENS_NOTES}}": domain_lens_notes or "none",
        "{{EVIDENCE_WINDOW}}": (
            f"{evidence_window['start']}..{evidence_window['end']}"
        ),
        "{{EVIDENCE_WINDOW_START}}": str(evidence_window["start"]),
        "{{EVIDENCE_WINDOW_END}}": str(evidence_window["end"]),
        "{{PRIMARY_ARTIFACT}}": primary_artifact,
        "{{PARENT_RUN_ID}}": parent.run_id if parent is not None else "none",
        "{{PARENT_RUN}}": parent.run_id if parent is not None else "none",
        "{{SELECTED_BRANCH}}": branch_display,
        "{{ROUTING_REQUEST}}": (
            args.request.strip() if args.request and args.request.strip() else "not supplied"
        ),
    }
    rendered_files: dict[str, str] = {}
    for entry in artifact_templates:
        assert entry.output_name is not None
        rendered_files[entry.output_name] = render_template(entry.source, replacements)
    rendered_files[primary_artifact] = render_template(report_template, replacements)

    manifest: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "skill": SKILL_ID,
        "skill_version": SKILL_VERSION,
        "validator_version": VALIDATOR_VERSION,
        "run_id": run_name,
        "domain": domain,
        "short_task_name": short_task_name,
        "language": args.language.strip(),
        "created_at": clock.created_at.isoformat(),
        "as_of_date": clock.as_of_date.isoformat(),
        "task_mode": args.mode,
        "run_type": args.mode,
        "discovery_lens": args.lens,
        "primary_domain_lens": args.domain_lens,
        "secondary_domain_lenses": secondary_domain_lenses,
        "domain_lens_notes": domain_lens_notes,
        "artifact_profile": artifact_profile(args.mode),
        "completion_status": "initialized",
        "workflow_contracts": list(WORKFLOW_CONTRACTS_BY_MODE[args.mode]),
        "parent_mutation_policy": (
            "supplement-only" if args.mode in {"evidence-audit", "run-audit"} else "child-run-only"
        ),
        "routing": {
            "request": args.request.strip() if args.request and args.request.strip() else None,
            "requested": requested_mode,
            "selected": args.mode,
            "reason": routing_reasons,
            "confidence": routing_confidence,
        },
        "evidence_window": evidence_window,
        "frontier_policy": {
            "recent_years_default": 3,
            "canonical_pre_window_allowed": True,
            "citation_signal": "field-year-normalized-when-available",
            "citation_source_and_as_of_required": True,
            "salience_is_not_claim_confidence": True,
        },
        "selected_branch": selected_branch,
        "lineage": {
            "parents": [parent_snapshot_dict(parent)] if parent is not None else []
        },
        "inherited_ids": inherited_ids,
        "context_sources": context_sources,
        "primary_artifact": primary_artifact,
        "artifact_files": list(rendered_files),
        "artifact_roles": artifact_roles,
    }
    manifest_text = json_text(manifest)

    try:
        target.mkdir(parents=True)
        for output_name, content in rendered_files.items():
            (target / output_name).write_text(content, encoding="utf-8", newline="\n")
        (target / "run-manifest.json").write_text(
            manifest_text, encoding="utf-8", newline="\n"
        )
    except OSError as exc:
        raise ContractError(
            f"Failed while writing run {target}; the directory may be incomplete: {exc}"
        ) from exc
    return target


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        target = initialize_run(args)
    except ContractError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    print(target)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
