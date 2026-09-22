from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .config import ALLOWED_STYLES, ALLOWED_THEMES, load_effective_config, panel_config
from .data import SUPPORTED_FORMATS, inspect_table, load_plot_data
from .errors import DataError, SciPlotError, SourceError
from .export import choose_output_paths, export_figure
from .project import init_project, resolve_output_base, resolve_project_root
from .qa import audit_outputs
from .render import render_figure
from .runlog import version_report, write_run_log
from .safety import (
    file_fingerprint,
    require_distinct_from_inputs,
    require_output_authorization,
    verify_fingerprints,
)
from .sources import (
    DEFAULT_MANIFEST_PATH,
    approve_source,
    check_sources,
    source_status,
)
from .spec import input_paths, iter_plot_specs, load_spec, template_catalog


def _json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sci-plot",
        description="Safe, deterministic scientific plotting",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="Create an explicit project configuration")
    init.add_argument("project_root", type=Path)
    init.add_argument("--project-name")
    init.add_argument("--output-dir", default="figures")
    init.add_argument("--theme", choices=sorted(ALLOWED_THEMES), default="paper")
    init.add_argument("--style", choices=sorted(ALLOWED_STYLES), default="general-paper")
    init.add_argument(
        "--scienceplots",
        action=argparse.BooleanOptionalAction,
        default=True,
    )
    init.set_defaults(handler=_cmd_init)

    render = subparsers.add_parser("render", help="Render and safely export a figure spec")
    render.add_argument("spec", type=Path)
    render.add_argument("--project-root", type=Path)
    render.add_argument("--output")
    render.add_argument("--format", dest="formats", action="append", choices=["svg", "pdf", "png", "tiff"])
    render.add_argument("--dpi", type=int)
    render.add_argument("--theme")
    render.add_argument("--style")
    render.add_argument("--backend", choices=["auto", "matplotlib", "pubfig"])
    render.add_argument("--scienceplots", action=argparse.BooleanOptionalAction, default=None)
    render.add_argument("--on-conflict", choices=["timestamp", "error"])
    render.add_argument("--overwrite", action="store_true")
    render.add_argument("--allow-external-output", action="store_true")
    render.add_argument("--no-log", action="store_true")
    render.set_defaults(handler=_cmd_render)

    validate = subparsers.add_parser("validate", help="Validate a figure spec and mapped data")
    validate.add_argument("spec", type=Path)
    validate.add_argument("--project-root", type=Path)
    validate.add_argument("--schema-only", action="store_true")
    validate.set_defaults(handler=_cmd_validate)

    inspect_data = subparsers.add_parser("inspect-data", help="Read-only data shape and missing-value report")
    inspect_data.add_argument("data", type=Path)
    inspect_data.add_argument("--format", choices=list(SUPPORTED_FORMATS))
    inspect_data.add_argument("--key")
    inspect_data.set_defaults(handler=_cmd_inspect_data)

    templates = subparsers.add_parser("list-templates", help="List built-in plot kinds and mappings")
    templates.set_defaults(handler=_cmd_list_templates)

    source = subparsers.add_parser("source", help="Inspect and approve upstream revisions")
    source.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    source_sub = source.add_subparsers(dest="source_command", required=True)
    status = source_sub.add_parser("status", help="Read local source state only")
    status.set_defaults(handler=_cmd_source_status)
    check = source_sub.add_parser("check", help="Read remote source state without applying changes")
    check.add_argument("--record", action="store_true", help="Record observation metadata only")
    check.set_defaults(handler=_cmd_source_check)
    update = source_sub.add_parser("update", help="Approve an already reviewed immutable ref")
    update.add_argument("--source", required=True, dest="source_id")
    update.add_argument("--ref", required=True)
    update.add_argument("--approve", action="store_true")
    update.add_argument("--tests-passed", action="store_true")
    update.set_defaults(handler=_cmd_source_update)
    return parser


def _cmd_init(args: argparse.Namespace) -> int:
    root = args.project_root.expanduser().resolve()
    path = init_project(
        root,
        project_name=args.project_name or root.name,
        output_dir=args.output_dir,
        theme=args.theme,
        style=args.style,
        scienceplots=args.scienceplots,
    )
    _json({"created": str(path), "project_root": str(root)})
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    spec_path = args.spec.expanduser().resolve()
    spec = load_spec(spec_path)
    project_root = resolve_project_root(spec_path, args.project_root)
    config, project_config_path = load_effective_config(
        project_root=project_root,
        figure_spec=spec,
    )
    if spec["kind"] == "multi_panel":
        for panel in spec["panels"]:
            panel_config(config, panel.get("style", {}))
    inputs: list[str] = []
    if not args.schema_only:
        for plot in iter_plot_specs(spec):
            _, path, _ = load_plot_data(plot, spec_path)
            if str(path) not in inputs:
                inputs.append(str(path))
    _json(
        {
            "valid": True,
            "schema_version": spec["schema_version"],
            "kind": spec["kind"],
            "inputs": inputs,
            "schema_only": args.schema_only,
            "project_root": str(project_root) if project_root else "",
            "project_config": str(project_config_path) if project_config_path else "",
            "effective_render": config["render"],
        }
    )
    return 0


def _cmd_inspect_data(args: argparse.Namespace) -> int:
    _json(inspect_table(args.data.expanduser().resolve(), data_format=args.format, key=args.key))
    return 0


def _cmd_list_templates(args: argparse.Namespace) -> int:
    _json({"templates": template_catalog()})
    return 0


def _cli_config_overrides(args: argparse.Namespace) -> dict[str, Any]:
    render: dict[str, Any] = {}
    for key in ("dpi", "theme", "style", "backend", "scienceplots"):
        value = getattr(args, key, None)
        if value is not None:
            render[key] = value
    if args.formats:
        render["formats"] = args.formats
    result: dict[str, Any] = {"render": render}
    if args.on_conflict:
        result["output"] = {"conflict": args.on_conflict}
    if args.no_log:
        result["logging"] = {"enabled": False}
    return result


def _output_formats(args: argparse.Namespace, config: dict[str, Any]) -> list[str]:
    if args.formats:
        return list(dict.fromkeys(args.formats))
    if args.output:
        suffix = Path(args.output).suffix.lower()
        inferred = {".svg": "svg", ".pdf": "pdf", ".png": "png", ".tif": "tiff", ".tiff": "tiff"}.get(suffix)
        if inferred:
            return [inferred]
    return list(config["render"]["formats"])


def _check_updates_before_render() -> None:
    report = check_sources(DEFAULT_MANIFEST_PATH, record=False)
    errors = [item for item in report["sources"] if item.get("error")]
    if errors:
        raise SourceError(
            "Pre-render source check failed: "
            + "; ".join(f"{item['id']}: {item['error']}" for item in errors)
        )
    pending = [item for item in report["sources"] if item.get("pending_update")]
    if pending:
        raise SourceError(
            "Upstream updates require review before rendering: "
            + ", ".join(item["id"] for item in pending)
        )


def _cmd_render(args: argparse.Namespace) -> int:
    spec_path = args.spec.expanduser().resolve()
    spec = load_spec(spec_path)
    project_root = resolve_project_root(spec_path, args.project_root)
    config, project_config_path = load_effective_config(
        project_root=project_root,
        figure_spec=spec,
        cli_overrides=_cli_config_overrides(args),
    )
    if config["updates"]["check_before_render"]:
        _check_updates_before_render()

    declared_inputs = input_paths(spec, spec_path)
    try:
        fingerprints = {path: file_fingerprint(path) for path in declared_inputs}
    except FileNotFoundError as exc:
        raise DataError(f"Input data file not found: {exc.filename}") from exc

    output_base, output_source = resolve_output_base(
        spec=spec,
        spec_path=spec_path,
        config=config,
        project_root=project_root,
        cli_output=args.output,
    )
    allowed_root = project_root or spec_path.parent
    require_output_authorization(
        output_base,
        allowed_root=allowed_root,
        allow_external=args.allow_external_output,
    )

    formats = _output_formats(args, config)
    paths, conflict_renamed = choose_output_paths(
        output_base,
        formats,
        conflict=config["output"]["conflict"],
        overwrite=args.overwrite,
    )
    require_distinct_from_inputs(paths, declared_inputs)

    rendered = None
    log_path = None
    log_root = project_root or spec_path.parent
    try:
        rendered = render_figure(spec, spec_path, config)
        export_warnings = export_figure(
            rendered.figure,
            paths,
            formats,
            dpi=config["render"]["dpi"],
            backend=rendered.backend,
            rc_params=rendered.rc_params,
            theme=config["render"]["theme"],
            overwrite=args.overwrite,
        )
        verify_fingerprints(fingerprints)
        qa = audit_outputs(
            paths,
            formats,
            expected_dpi=config["render"]["dpi"],
            expected_size_mm=(
                config["render"]["width_mm"],
                config["render"]["height_mm"],
            ),
        )
        warnings = rendered.warnings + export_warnings + qa["warnings"]
        if config["logging"]["enabled"]:
            log_path = write_run_log(
                root=log_root,
                status="success",
                spec_path=spec_path,
                project_root=project_root,
                inputs=rendered.inputs,
                outputs=paths,
                kind=spec["kind"],
                theme=config["render"]["theme"],
                backend=rendered.backend.name,
                formats=formats,
            )
        _json(
            {
                "status": "success",
                "spec": str(spec_path),
                "project_root": str(project_root) if project_root else "",
                "project_config": str(project_config_path) if project_config_path else "",
                "inputs": [str(path) for path in rendered.inputs],
                "outputs": [str(path) for path in paths],
                "output_source": output_source,
                "conflict_renamed": conflict_renamed,
                "theme": config["render"]["theme"],
                "backend": rendered.backend.name,
                "backend_version": rendered.backend.version,
                "formats": formats,
                "dpi": config["render"]["dpi"],
                "qa": qa["checks"],
                "warnings": warnings,
                "run_log": str(log_path) if log_path else "",
                "versions": version_report(),
            }
        )
        return 0
    except Exception as exc:
        if config["logging"]["enabled"]:
            try:
                write_run_log(
                    root=log_root,
                    status="error",
                    spec_path=spec_path,
                    project_root=project_root,
                    inputs=declared_inputs,
                    outputs=[],
                    kind=spec["kind"],
                    theme=config["render"]["theme"],
                    backend=rendered.backend.name if rendered else config["render"]["backend"],
                    formats=formats,
                    error=str(exc),
                )
            except Exception:
                pass
        raise
    finally:
        if rendered is not None:
            try:
                import matplotlib.pyplot as plt

                plt.close(rendered.figure)
            except ImportError:
                pass


def _cmd_source_status(args: argparse.Namespace) -> int:
    _json(source_status(args.manifest.expanduser().resolve()))
    return 0


def _cmd_source_check(args: argparse.Namespace) -> int:
    report = check_sources(
        args.manifest.expanduser().resolve(),
        record=args.record,
    )
    _json(report)
    return 3 if any(item.get("error") for item in report["sources"]) else 0


def _cmd_source_update(args: argparse.Namespace) -> int:
    result = approve_source(
        args.manifest.expanduser().resolve(),
        source_id=args.source_id,
        ref=args.ref,
        approve=args.approve,
        tests_passed=args.tests_passed,
    )
    _json(result)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.handler(args))
    except SciPlotError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: filesystem operation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
