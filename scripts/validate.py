#!/usr/bin/env python3
"""Run the existing component checks offline; never installs dependencies or launches research."""
from pathlib import Path
import argparse
import json
import os
import subprocess
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--component", action="append", choices=("collection", "reading", "presentation", "mapper", "quick", "lookup", "sciverse", "plot", "zotero", "acquisition"))
    parser.add_argument("--plot-python", default=sys.executable)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--quick-validator", type=Path)
    args = parser.parse_args()
    output = args.output_dir or ROOT / ".local" / "checks" / uuid.uuid4().hex
    output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    env["MPLBACKEND"] = "Agg"
    env["MPLCONFIGDIR"] = str(output / "matplotlib")
    env.setdefault("ROM_CANONICAL_CHECKER", str(ROOT / "skills/paper-deep-reading/scripts/check_canonical.py"))
    mapper = ROOT / "skills/research-opportunity-mapper"
    tests = ROOT / "tests"
    selected = args.component or ["collection", "reading", "presentation", "mapper", "quick", "lookup", "sciverse", "plot", "zotero", "acquisition"]
    if "mapper" in selected:
        sys.path.insert(0, str(tests))
        from mapper_synthetic_workspace import seed
        legacy_workspace = env.get("MAPPER_LEGACY_WORKSPACE")
        if legacy_workspace:
            env["ROM_TEST_WORKSPACE"] = str(Path(legacy_workspace).resolve())
            env["ROM_TEST_ROOT"] = str(output / "mapper-work")
        else:
            seed(output / "synthetic workspace", mapper)
            env["ROM_TEST_WORKSPACE"] = str(output / "synthetic workspace")
            env["ROM_TEST_ROOT"] = str(output / "synthetic workspace" / "mapper-work")
    pwsh = "pwsh"
    steps = [
        ("collection", "packages", [sys.executable, str(ROOT / "scripts/skills.py"), "validate"]),
        ("collection", "distribution", [sys.executable, "-m", "unittest", "discover", "-s", str(tests), "-p", "test_distribution.py", "-v"]),
        ("reading", "canonical", [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "skills/paper-deep-reading/scripts"), "-p", "test_*.py", "-v"]),
        ("reading", "footnotes", [sys.executable, "-m", "unittest", "discover", "-s", str(tests), "-p", "test_check_report_footnotes.py", "-v"]),
        ("mapper", "mapper", [sys.executable, "-m", "unittest", "discover", "-s", str(mapper / "tests"), "-v"]),
        ("quick", "quick", [sys.executable, "-m", "unittest", "discover", "-s", str(tests), "-p", "test_mapper_quick.py", "-v"]),
        ("presentation", "presentation", [sys.executable, "-m", "unittest", "discover", "-s", str(tests / "paper-presentation"), "-v"]),
        ("collection", "validation-runner", [sys.executable, "-m", "unittest", "discover", "-s", str(tests), "-p", "test_validation_runner.py", "-v"]),
        ("lookup", "lookup", [sys.executable, "-m", "unittest", "discover", "-s", str(tests / "research-lookup-enhanced"), "-v"]),
        ("lookup", "lookup-offline", [sys.executable, str(tests / "research-lookup-enhanced/offline_smoke.py")]),
        ("plot", "plot", [args.plot_python, "-m", "unittest", "discover", "-s", str(tests / "sci-plot"), "-v"]),
        ("zotero", "zotero", [pwsh, "-NoProfile", "-File", str(tests / "zotero-literature-note/validate-skill.ps1")]),
        ("acquisition", "acquisition-guards", [sys.executable, "-m", "unittest", "discover", "-s", str(tests / "literature-fulltext-acquisition"), "-p", "test_guards.py", "-v"]),
        ("acquisition", "acquisition-runtime", [pwsh, "-NoProfile", "-File", str(tests / "literature-fulltext-acquisition/smoke.ps1")]),
    ]
    quick = args.quick_validator or Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py"
    if quick.is_file():
        if "collection" in selected:
            for skill in sorted((ROOT / "skills").iterdir()):
                if (skill / "SKILL.md").is_file():
                    steps.append(("collection", f"skill-{skill.name}", [sys.executable, str(quick), str(skill)]))
        steps.append(("sciverse", "sciverse", [pwsh, "-NoProfile", "-File", str(tests / "sciverse-research/validate.ps1"), "-PythonCommand", sys.executable, "-QuickValidatePath", str(quick)]))
    else:
        # The collection validation does not require host-specific Skill tooling.
        steps.append(("sciverse", "sciverse-contracts", [sys.executable, str(tests / "sciverse-research/check_contracts.py")]))
    results = []
    for group, label, command in steps:
        if group not in selected:
            continue
        step_env = env.copy()
        if group == "plot":
            step_env["PYTHONPATH"] = str(ROOT / "skills/sci-plot/src")
        if group == "acquisition":
            settings = ROOT / "skills/literature-fulltext-acquisition/config/local.json"
            if settings.is_file():
                data = json.loads(settings.read_text(encoding="utf-8"))
                step_env["LITERATURE_TOOLS_ROOT"] = data["tools_root"]
                step_env["LITERATURE_PROTECTED_ROOT"] = data["protected_root"]
        if label == "acquisition-runtime" and not (step_env.get("LITERATURE_TOOLS_ROOT") and step_env.get("LITERATURE_PROTECTED_ROOT")):
            results.append({"component": group, "check": label, "exit_code": 0, "status": "skipped", "reason": "External runtime smoke requires explicit local tool configuration"})
            print(f"{label}: SKIP (no external runtime configured)", flush=True)
            continue
        if command[0] == pwsh and shutil.which(pwsh) is None:
            log = "PowerShell 7 (pwsh) is required for this selected component. Use an existing environment with pwsh on PATH; validation never installs it.\n"
            (output / f"{label}.log").write_text(log, encoding="utf-8")
            results.append({"component": group, "check": label, "exit_code": 127, "status": "blocked", "reason": log.strip()})
            print(f"{label}: BLOCKED (PowerShell 7 missing)", flush=True)
            continue
        try:
            run = subprocess.run(command, cwd=ROOT, env=step_env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=240)
            code, log = run.returncode, run.stdout + run.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, log = 1, str(exc)
        (output / f"{label}.log").write_text(log, encoding="utf-8")
        results.append({"component": group, "check": label, "exit_code": code})
        print(f"{label}: {'PASS' if code == 0 else 'FAIL'}", flush=True)
    (output / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"Logs: {output}", flush=True)
    return 1 if any(x["exit_code"] for x in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
