#!/usr/bin/env python3
"""Read-only preflight for paper-deep-reading external dependencies.

The script deliberately does not install packages, access the network, upload
files, modify the environment, or inspect secret values. Agent-side Skill and
MCP discovery must be merged with this report by the calling agent.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, List, Optional, Tuple


MODES = ("standard", "fully-local", "main-paper-only", "plan-only")
INPUT_KINDS = ("unknown", "pdf", "full-text")
STATUS = ("PASS", "MISSING", "BLOCKED", "OPTIONAL", "NOT-APPLICABLE")
AGENT_CHECKS = (
    "paper-lookup.skill",
    "paper-lookup.http-fetch",
    "sciverse-research.skill",
    "sciverse.mcp-tools",
    "mineru-pdf.skill",
    "pdf.skill",
    "skill.parallel-web",
    "skill.research-lookup",
    "skill.paper-presentation",
)


def add_result(
    results: list[dict[str, Any]],
    *,
    name: str,
    category: str,
    status: str,
    details: str,
    required: bool = False,
    source: str = "local",
    priority: Optional[str] = None,
) -> None:
    if status not in STATUS:
        raise ValueError(f"unsupported dependency status: {status}")
    if priority is None:
        priority = "must" if required else (
            "strongly-recommended"
            if category in ("preferred-pdf-route", "local-pdf-route", "pdf-route")
            else "optional"
        )
    results.append(
        {
            "name": name,
            "category": category,
            "priority": priority,
            "status": status,
            "required": required,
            "source": source,
            "details": details,
        }
    )


def env_present(name: str) -> bool:
    """Return only whether an environment variable has a non-empty value."""

    return bool(os.environ.get(name, "").strip())


def command_present(name: str) -> bool:
    return shutil.which(name) is not None


def module_present(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def infer_skill_root() -> Path:
    # .../skills/paper-deep-reading/scripts/check_dependencies.py
    return Path(__file__).resolve().parents[1]


def resolve_skill_roots(skill_root: Path, explicit_roots: List[str]) -> List[Path]:
    roots: list[Path] = []

    def add(path: Path) -> None:
        path = path.expanduser().resolve()
        if path not in roots:
            roots.append(path)

    for value in explicit_roots:
        add(Path(value))

    env_root = os.environ.get("CODEX_SKILLS_ROOT", "").strip()
    if env_root:
        add(Path(env_root))

    codex_home = os.environ.get("CODEX_HOME", "").strip()
    if codex_home:
        add(Path(codex_home) / "skills")

    # This also makes the script useful in a repository checkout containing
    # sibling skills, without embedding any machine-specific path.
    if skill_root.parent.name == "skills":
        add(skill_root.parent)

    return roots


SKILL_ALIASES = {
    "paper-deep-reading": ("paper-deep-reading",),
    "paper-lookup": ("paper-lookup", "sa.paper-lookup"),
    "sciverse-research": ("sciverse-research",),
    "mineru-pdf": ("mineru-pdf",),
    "pdf": ("pdf",),
    "parallel-web": ("parallel-web", "sa.parallel-web"),
    "research-lookup": ("research-lookup", "sa.research-lookup"),
    "paper-presentation": ("paper-presentation",),
}


def find_skill(skill_name: str, roots: List[Path]) -> Optional[Path]:
    for root in roots:
        for alias in SKILL_ALIASES.get(skill_name, (skill_name,)):
            marker = root / alias / "SKILL.md"
            if marker.is_file():
                return marker
    return None


def skill_status(
    skill_name: str,
    roots: List[Path],
    *,
    applicable: bool,
) -> Tuple[str, str]:
    if not applicable:
        return "NOT-APPLICABLE", "not used by the selected validation mode"
    found = find_skill(skill_name, roots)
    if found is not None:
        return "PASS", "Skill file is locally discoverable"
    if roots:
        return "MISSING", "Skill file was not found in the inspected Skill roots"
    return "BLOCKED", "Skill roots were not supplied; agent Skill catalog check is required"


def path_candidates(skill_root: Path, wrapper_arg: Optional[str]) -> List[Path]:
    candidates: List[Path] = []
    values = [
        wrapper_arg,
        os.environ.get("MINERU_WRAPPER", ""),
        os.environ.get("MINERU_WRAPPER_PATH", ""),
    ]
    for value in values:
        if value:
            candidates.append(Path(value).expanduser())

    # These are conventional names only; an explicit argument or environment
    # variable remains the portable way to point at a wrapper elsewhere.
    for relative in (
        "scripts/mineru_parse.py",
        "scripts/mineru_parser.py",
        "mineru_parse.py",
        "mineru_parser.py",
    ):
        candidates.append(skill_root / relative)
    return candidates


def wrapper_present(skill_root: Path, wrapper_arg: Optional[str]) -> bool:
    return any(candidate.is_file() for candidate in path_candidates(skill_root, wrapper_arg))


def agent_confirmed(args: argparse.Namespace, name: str) -> bool:
    return name in args.agent_check


def agent_skill_override(
    args: argparse.Namespace, name: str, status: str, details: str
) -> Tuple[str, str]:
    if status != "NOT-APPLICABLE" and agent_confirmed(args, name):
        return "PASS", "confirmed by the agent Skill/tool catalog"
    return status, details


def local_component_status(ok: bool, applicable: bool, required: bool) -> str:
    if not applicable:
        return "NOT-APPLICABLE"
    if ok:
        return "PASS"
    return "MISSING" if required else "OPTIONAL"


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    mode = args.mode
    input_kind = args.input_kind
    skill_root = Path(args.skill_root).expanduser().resolve() if args.skill_root else infer_skill_root()
    roots = resolve_skill_roots(skill_root, args.skills_root)
    results: List[dict[str, Any]] = []
    agent_checks_required: List[str] = []

    add_result(
        results,
        name="paper-deep-reading",
        category="skill",
        status="PASS" if (skill_root / "SKILL.md").is_file() else "MISSING",
        details="Current Skill file is present" if (skill_root / "SKILL.md").is_file() else "Current Skill file is missing",
        required=mode != "plan-only",
    )

    external_mode = mode == "standard"
    pdf_checks_applicable = mode == "standard" or (
        mode in ("main-paper-only", "fully-local") and input_kind != "full-text"
    )
    pdf_route_required = mode == "standard" or (
        mode in ("main-paper-only", "fully-local") and input_kind == "pdf"
    )
    paper_lookup_status, paper_lookup_details = skill_status(
        "paper-lookup", roots, applicable=external_mode
    )
    paper_lookup_status, paper_lookup_details = agent_skill_override(
        args, "paper-lookup.skill", paper_lookup_status, paper_lookup_details
    )
    add_result(
        results,
        name="paper-lookup.skill",
        category="required" if external_mode else "conditional",
        status=paper_lookup_status,
        details=paper_lookup_details,
        required=external_mode,
    )

    if external_mode:
        http_confirmed = agent_confirmed(args, "paper-lookup.http-fetch")
        add_result(
            results,
            name="paper-lookup.http-fetch",
            category="required",
            status="PASS" if http_confirmed else "BLOCKED",
            details=(
                "confirmed by the agent HTTP/tool catalog"
                if http_confirmed
                else "HTTP capability must be confirmed from the agent tool catalog; this script does not access the network"
            ),
            required=True,
            source="agent",
        )
        if not http_confirmed:
            agent_checks_required.append("paper-lookup.http-fetch")
    else:
        add_result(
            results,
            name="paper-lookup.http-fetch",
            category="conditional",
            status="NOT-APPLICABLE",
            details="external paper lookup is disabled by the selected validation mode",
            source="agent",
        )

    sciverse_status, sciverse_details = skill_status(
        "sciverse-research", roots, applicable=external_mode
    )
    sciverse_status, sciverse_details = agent_skill_override(
        args, "sciverse-research.skill", sciverse_status, sciverse_details
    )
    add_result(
        results,
        name="sciverse-research.skill",
        category="required" if external_mode else "conditional",
        status=sciverse_status,
        details=sciverse_details,
        required=external_mode,
    )
    add_result(
        results,
        name="SCIVERSE_API_TOKEN",
        category="required" if external_mode else "conditional",
        status=(
            "PASS"
            if external_mode and env_present("SCIVERSE_API_TOKEN")
            else "MISSING"
            if external_mode
            else "NOT-APPLICABLE"
        ),
        details=(
            "environment variable is present"
            if external_mode and env_present("SCIVERSE_API_TOKEN")
            else "environment variable is not set; value was not inspected"
            if external_mode
            else "Sciverse is not used by the selected validation mode"
        ),
        required=external_mode,
    )
    if external_mode:
        mcp_confirmed = agent_confirmed(args, "sciverse.mcp-tools")
        add_result(
            results,
            name="sciverse.mcp-tools",
            category="required",
            status="PASS" if mcp_confirmed else "BLOCKED",
            details=(
                "required Sciverse MCP tools confirmed by the agent tool catalog"
                if mcp_confirmed
                else "MCP exposure must be confirmed from the agent tool catalog; filesystem checks cannot prove server availability"
            ),
            required=True,
            source="agent",
        )
        if not mcp_confirmed:
            agent_checks_required.append("sciverse.mcp-tools")
    else:
        add_result(
            results,
            name="sciverse.mcp-tools",
            category="conditional",
            status="NOT-APPLICABLE",
            details="Sciverse is not required by the selected validation mode",
            source="agent",
        )

    python_ok = bool(sys.executable) and sys.version_info >= (3, 9)
    add_result(
        results,
        name="python.runtime",
        category="required" if pdf_route_required else "conditional",
        status="PASS" if python_ok else ("MISSING" if pdf_route_required else "OPTIONAL"),
        details="current Python runtime is usable" if python_ok else "Python 3.9 or newer is required",
        required=pdf_route_required,
    )

    mineru_applicable = mode == "standard" or (
        mode == "main-paper-only" and input_kind != "full-text"
    )
    mineru_skill_status, mineru_skill_details = skill_status(
        "mineru-pdf", roots, applicable=mineru_applicable
    )
    mineru_skill_status, mineru_skill_details = agent_skill_override(
        args, "mineru-pdf.skill", mineru_skill_status, mineru_skill_details
    )
    add_result(
        results,
        name="mineru-pdf.skill",
        category="preferred-pdf-route" if mineru_applicable else "conditional",
        status=mineru_skill_status,
        details=mineru_skill_details,
        required=False,
    )
    mineru_wrapper_ok = wrapper_present(skill_root, args.mineru_wrapper)
    add_result(
        results,
        name="mineru.wrapper",
        category="preferred-pdf-route" if mineru_applicable else "conditional",
        status=(
            "PASS"
            if mineru_applicable and mineru_wrapper_ok
            else "MISSING"
            if mineru_applicable
            else "NOT-APPLICABLE"
        ),
        details=(
            "MinerU wrapper is discoverable"
            if mineru_applicable and mineru_wrapper_ok
            else "MinerU wrapper was not found; pass --mineru-wrapper or set MINERU_WRAPPER when needed"
            if mineru_applicable
            else "remote MinerU is not used by the selected validation mode"
        ),
        required=False,
    )
    mineru_key_ok = env_present("MINERU_API_KEY")
    add_result(
        results,
        name="MINERU_API_KEY",
        category="preferred-pdf-route" if mineru_applicable else "conditional",
        status=(
            "PASS"
            if mineru_applicable and mineru_key_ok
            else "MISSING"
            if mineru_applicable
            else "NOT-APPLICABLE"
        ),
        details=(
            "environment variable is present"
            if mineru_applicable and mineru_key_ok
            else "environment variable is not set; value was not inspected"
            if mineru_applicable
            else "remote MinerU is not used by the selected validation mode"
        ),
        required=False,
    )
    mineru_ready = mineru_applicable and all(
        (
            mineru_skill_status == "PASS",
            mineru_wrapper_ok,
            python_ok,
            mineru_key_ok,
        )
    )
    add_result(
        results,
        name="mineru-pdf.route",
        category="pdf-route",
        status=("PASS" if mineru_ready else ("OPTIONAL" if mineru_applicable else "NOT-APPLICABLE")),
        details=(
            "preferred MinerU PDF route is ready"
            if mineru_ready
            else "preferred route is incomplete; use local PDF fallback when available"
            if mineru_applicable
            else "remote MinerU is not used by the selected validation mode"
        ),
        required=False,
    )

    pdf_skill_status, pdf_skill_details = skill_status("pdf", roots, applicable=pdf_checks_applicable)
    pdf_skill_status, pdf_skill_details = agent_skill_override(
        args, "pdf.skill", pdf_skill_status, pdf_skill_details
    )
    if pdf_checks_applicable and not pdf_route_required and pdf_skill_status in ("MISSING", "BLOCKED"):
        pdf_skill_status = "OPTIONAL"
        pdf_skill_details = "local PDF Skill is not confirmed; it becomes required when input-kind=pdf"
    add_result(
        results,
        name="pdf.skill",
        category="local-pdf-route" if pdf_checks_applicable else "conditional",
        status=pdf_skill_status,
        details=pdf_skill_details,
        required=False,
    )
    for command in ("pdfinfo", "pdftoppm"):
        ok = command_present(command)
        add_result(
            results,
            name=f"command.{command}",
            category="local-pdf-route" if pdf_checks_applicable else "conditional",
            status=local_component_status(ok, pdf_checks_applicable, pdf_route_required),
            details=(
                f"{command} is executable"
                if pdf_checks_applicable and ok
                else f"{command} is not executable"
                if pdf_checks_applicable
                else "local PDF tooling is not used by the selected input/mode"
            ),
            required=False,
        )
    pypdf_ok = module_present("pypdf")
    fitz_ok = module_present("fitz")
    add_result(
        results,
        name="python.pypdf",
        category="local-pdf-route" if pdf_checks_applicable else "conditional",
        status=local_component_status(pypdf_ok, pdf_checks_applicable, pdf_route_required),
        details=(
            "pypdf can be imported"
            if pdf_checks_applicable and pypdf_ok
            else "pypdf cannot be imported"
            if pdf_checks_applicable
            else "pypdf is not used by the selected input/mode"
        ),
        required=False,
    )
    add_result(
        results,
        name="python.PyMuPDF",
        category="local-pdf-route" if pdf_checks_applicable else "conditional",
        status=(
            "PASS"
            if pdf_checks_applicable and fitz_ok
            else "OPTIONAL"
            if pdf_checks_applicable
            else "NOT-APPLICABLE"
        ),
        details=(
            "fitz/PyMuPDF can be imported"
            if pdf_checks_applicable and fitz_ok
            else "fitz/PyMuPDF is unavailable; visual or extraction coverage may be reduced"
            if pdf_checks_applicable
            else "PyMuPDF is not used by the selected input/mode"
        ),
        required=False,
    )
    local_parser_ok = pypdf_ok or fitz_ok
    local_visual_ok = command_present("pdfinfo") and command_present("pdftoppm")
    local_route_ok = pdf_checks_applicable and local_parser_ok
    add_result(
        results,
        name="pdf.local-route",
        category="pdf-route",
        status=(
            "PASS"
            if local_route_ok
            else "MISSING"
            if pdf_route_required
            else "OPTIONAL"
            if pdf_checks_applicable
            else "NOT-APPLICABLE"
        ),
        details=(
            "local PDF parser is available"
            + (" and Poppler visual QA tools are available" if local_visual_ok else "; visual QA tools are incomplete")
            if local_route_ok
            else "no local PDF parser (pypdf or PyMuPDF) is available"
            if pdf_checks_applicable
            else "local PDF parsing is not used by the selected input/mode"
        ),
        required=False,
    )
    add_result(
        results,
        name="pdf.route",
        category="required-pdf-route" if mode == "standard" else "pdf-route",
        status=(
            "NOT-APPLICABLE"
            if not pdf_checks_applicable
            else "PASS"
            if mineru_ready or local_route_ok
            else "MISSING"
            if pdf_route_required
            else "OPTIONAL"
        ),
        details=(
            "at least one PDF route is usable"
            if mineru_ready or local_route_ok
            else "MinerU and local PDF fallback are both unavailable"
            if pdf_route_required
            else "PDF route will be required if the supplied main source is a PDF"
            if pdf_checks_applicable
            else "PDF parsing is not needed for the selected input/mode"
        ),
        required=pdf_route_required,
    )

    parallel_cli_ok = command_present("parallel-cli")
    parallel_key_ok = env_present("PARALLEL_API_KEY")
    openrouter_key_ok = env_present("OPENROUTER_API_KEY")
    parallel_applicable = mode == "standard"
    parallel_status = "PASS" if parallel_cli_ok and parallel_key_ok else "OPTIONAL"
    add_result(
        results,
        name="parallel-web.research-lookup",
        category="optional-enhancement",
        status=parallel_status if parallel_applicable else "NOT-APPLICABLE",
        details=(
            "parallel-cli and PARALLEL_API_KEY are available"
            if parallel_status == "PASS"
            else "parallel-cli or PARALLEL_API_KEY is unavailable; open-ended web/deep research is optional"
            if parallel_applicable
            else "open-ended web/deep research is disabled by the selected validation mode"
        ),
        required=False,
    )
    add_result(
        results,
        name="OPENROUTER_API_KEY",
        category="optional-enhancement",
        status="PASS" if openrouter_key_ok and parallel_applicable else ("OPTIONAL" if parallel_applicable else "NOT-APPLICABLE"),
        details=(
            "environment variable is present"
            if openrouter_key_ok and parallel_applicable
            else "environment variable is not set; value was not inspected"
            if parallel_applicable
            else "OpenRouter is not used by the selected validation mode"
        ),
        required=False,
    )

    # These are useful to the agent but are not runtime checks performed here.
    for name in ("paper-lookup", "sciverse-research", "mineru-pdf", "pdf", "parallel-web", "research-lookup", "paper-presentation"):
        if name in ("paper-lookup", "sciverse-research", "mineru-pdf", "pdf"):
            continue
        status, details = skill_status(name, roots, applicable=parallel_applicable if name in ("parallel-web", "research-lookup") else mode != "plan-only")
        status, details = agent_skill_override(args, f"skill.{name}", status, details)
        add_result(
            results,
            name=f"skill.{name}",
            category="agent-discovery",
            status=status,
            details=details,
            required=False,
            source="local",
        )

    required_blockers = [
        item["name"]
        for item in results
        if item["required"] and item["status"] in ("MISSING", "BLOCKED")
    ]
    return {
        "schema_version": "1",
        "mode": mode,
        "input_kind": input_kind,
        "script": "check_dependencies.py",
        "read_only": True,
        "secrets_checked_by_presence_only": True,
        "skill_roots_inspected": len(roots),
        "agent_checks_required": agent_checks_required,
        "results": results,
        "summary": {
            "required_blockers": required_blockers,
            "status_counts": {
                status: sum(item["status"] == status for item in results) for status in STATUS
            },
            "exit_code": 1 if required_blockers else 0,
        },
    }


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=MODES, default="standard")
    parser.add_argument(
        "--input-kind",
        choices=INPUT_KINDS,
        default="unknown",
        help="main source kind; use pdf to make the local parser route required in local modes",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--skill-root", help="path to this paper-deep-reading Skill directory")
    parser.add_argument(
        "--skills-root",
        action="append",
        default=[],
        help="additional directory containing installed Skill directories; may be repeated",
    )
    parser.add_argument(
        "--mineru-wrapper",
        help="optional path to the local MinerU wrapper; never read or uploaded by this check",
    )
    parser.add_argument(
        "--agent-check",
        action="append",
        choices=AGENT_CHECKS,
        default=[],
        metavar="NAME",
        help="repeat for capabilities already confirmed by the agent Skill/tool catalog",
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    try:
        args = parse_args(argv)
        report = build_report(args)
        if args.as_json:
            print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
        else:
            print(f"paper-deep-reading dependency preflight: mode={report['mode']}")
            for item in report["results"]:
                marker = item["priority"]
                print(f"[{item['status']}] {item['name']} ({marker}) - {item['details']}")
            if report["agent_checks_required"]:
                print("Agent-side checks required: " + ", ".join(report["agent_checks_required"]))
            blockers = report["summary"]["required_blockers"]
            if blockers:
                print("Required dependencies not ready: " + ", ".join(blockers))
            else:
                print("All script-visible required dependencies are ready.")
        return int(report["summary"]["exit_code"])
    except Exception as exc:  # pragma: no cover - defensive CLI boundary
        print(f"dependency preflight failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
