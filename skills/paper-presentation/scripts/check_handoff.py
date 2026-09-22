#!/usr/bin/env python3
"""Read-only mechanical V1.1 handoff checks; never judges scientific truth or writes slides."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import re

GATE_STATES = {
    "G0": {"pass", "blocked"}, "G1": {"pass", "pass-with-downgrade", "blocked"},
    "G2": {"pass", "pass-with-downgrade", "blocked"},
    "G3": {"pass", "pass-with-downgrade", "blocked", "not-applicable"},
    "G4": {"pass", "pass-with-downgrade", "blocked"}, "G5": {"pass", "blocked"},
}
DEFAULT_CHECKER = Path(__file__).resolve().parents[2] / "paper-deep-reading/scripts/check_canonical.py"


def load_checker(path: Path):
    if not path.is_file():
        raise ValueError("Supply --canonical-checker from the matching paper-deep-reading installation")
    spec = importlib.util.spec_from_file_location("presentation_canonical", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(run_dir: Path, checker_path: Path = DEFAULT_CHECKER) -> dict:
    """Return existing readiness states and retained limits, without creating a new ledger."""
    errors, limits = [], []
    result = {"readiness": "not presentation-ready", "errors": errors, "limits": limits,
              "manual_review_required": True,
              "scope": "Mechanical gate and canonical trace checks only; inspect scientific wording, figures and cited support before planning."}
    root = run_dir.resolve()
    try:
        package = (root / "paper-package.md").read_text(encoding="utf-8")
        checker = load_checker(checker_path)
        fields = {}
        for table in checker.parse_tables(package):
            if table["headers"] == ["Field", "Value"]:
                fields.update({r["Field"]: r["Value"] for r in table["rows"]})
        contract = fields.get("evidence_contract")
        marker = re.search(r"(?m)^\s*evidence_contract:\s*(\S+)", package)
        contract = contract or (marker.group(1).strip(chr(96)) if marker else None)
        if not contract:
            result.update(readiness=None, contract="legacy-v1.0.x")
            limits.append("Use the Skill's legacy file-and-content review; no V1.1 gates or IDs are invented.")
            return result
        if contract != "v1.1":
            errors.append("Unsupported explicit evidence_contract; resolve it with paper-deep-reading")
            return result
        result["contract"] = contract
        canonical = checker.validate_run(root)
        errors.extend(f"canonical {d['code']}: {d['message']}" for d in canonical["errors"])
        report = (root / "view-report.md").read_text(encoding="utf-8")
        if not report.strip():
            errors.append("Empty reader report")
        audit = (root / "view-report-audit.md").read_text(encoding="utf-8")
        tables = checker.parse_tables(audit)
        gates = {}
        for table in tables:
            if {"Gate", "Status"} <= set(table["headers"]):
                if table["malformed_rows"]:
                    errors.append("Malformed gate table")
                for row in table["rows"]:
                    match = re.match(r"^(G[0-5])(?:\s|$)", row["Gate"], re.I)
                    if not match:
                        errors.append("Unrecognized gate row")
                        continue
                    gate = match.group(1).upper()
                    if gate in gates:
                        errors.append(f"Duplicate {gate} gate")
                    state = row["Status"]
                    gates[gate] = state
                    if state not in GATE_STATES[gate] or state == "blocked":
                        errors.append(f"{gate}: {state}")
                    elif state != "pass":
                        limits.append({k: v for k, v in row.items() if k != "_line"})
        if set(gates) != set(GATE_STATES):
            errors.append("Audit must record G0-G5, including a passing G5")
        result["gates"] = gates
        known = set().union(*(canonical[name].keys() for name in ("claims", "ideas", "designs", "evidence")))
        maps = [t for t in tables if "Report claim or judgment" in t["headers"]]
        if not maps or not any(t["rows"] for t in maps):
            errors.append("Missing Report Claim Map; complete the canonical trace before handoff")
        for table in maps:
            if table["malformed_rows"]:
                errors.append("Malformed Report Claim Map")
            for row in table["rows"]:
                if row.get("Sync status") != "in-sync":
                    errors.append("Stale or missing Report Claim Map sync status")
                references = " ".join(v for k, v in row.items() if k.startswith("Canonical ") or k == "Main-paper locator or Evidence IDs")
                ids = set(re.findall(r"\b[CNDE]-\d+\b", references))
                if not any(re.fullmatch(r"[CND]-\d+", value) for value in ids):
                    errors.append("Report Claim Map row lacks a canonical claim/judgment")
                if ids - known:
                    errors.append("Unknown canonical IDs: " + ", ".join(sorted(ids - known)))
        if not errors:
            result["readiness"] = "presentation-ready with evidence gaps" if limits else "presentation-ready"
    except (OSError, UnicodeError, ValueError) as exc:
        errors.append(str(exc))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--canonical-checker", type=Path, default=DEFAULT_CHECKER)
    args = parser.parse_args(argv)
    result = check(args.run_dir, args.canonical_checker)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["readiness"] is None:
        return 2  # A legacy content review cannot be replaced by mechanical checks.
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
