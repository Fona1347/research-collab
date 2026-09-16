#!/usr/bin/env python3
"""Read-only validation of Deep Reading canonical Markdown records.

Use validate_run(run_dir) from Python, or --run-dir DIR --json from the CLI.
This validates record integrity, not scientific truth, bibliographic authority,
actual reading, statistical power, or semantic atomicity of a claim sentence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import unquote

SCHEMA_VERSION = "1"
EVIDENCE_MODES = {"direct measurement", "derived", "model fit", "simulation", "extrapolation", "author interpretation"}
CLAIM_STATES = {"supported", "weakened", "contradicted", "not established within scope", "blocked"}
ROLE_STATES = {"open", "closed", "downgraded", "blocked", "not-applicable"}
SOURCE_STATES = {
    "Full-text status": {"available", "unavailable", "access-blocked", "unknown"},
    "PDF status": {"not-needed", "not-materialized", "materialized", "failed", "not-authorized"},
    "Parse status": {"not-needed", "not-submitted", "parsed", "partial", "failed", "not-authorized"},
    "Read status": {"unread", "partial", "full"},
    "Verification status": {"not-started", "verified", "conflicted", "rejected", "blocked"},
    "Citation status": {"not-cited", "planned", "cited"},
}
IDEA_VERDICTS = {"high-conceptual", "high-mechanistic", "high-architectural", "high-integrative", "incremental", "performance-only", "internally-distinctive; external-priority-not-established", "not-established-within-scope"}
DESIGN_VERDICTS = {"demonstrated-feasible", "sufficient-under-stated-joint-conditions", "necessary-within-stated-architecture", "practically-preferred-under-stated-constraints", "not-shown-necessary", "one-implementation-among-alternatives", "superiority-not-established", "not-established-within-scope"}
NO_VALUE = {"none", "not-applicable", "unknown", "not available", "unavailable", "not-cited", "pending"}
TABLES = {
    "claims": ("reading-report.md", "Claim ID", "C", ["Atomic claim", "Priority", "Evidence mode", "Main-paper locator", "Conditions", "Jointly demonstrated", "Supplementary dependency", "Validation roles", "Status"]),
    "sources": ("auxiliary-literature-table.md", "Source ID", "S", ["Canonical identifier", "Title / year", "Discovery route", "Related Claim IDs", "Evidence role", "Relevance grade", "Directness", "Independence", "Comparability", "Counter-evidence value", *SOURCE_STATES, "Reader-facing footnote key", "Backlink anchor IDs", "Include/exclude reason"]),
    "evidence": ("external-evidence-matrix.md", "Evidence ID", "E", ["Claim ID", "Source ID", "Relation", "Evidence mode", "Locator", "Conditions", "Evidence summary", "Limitations/conflict", "Evidence strength", "Final assessment", "Report target"]),
    "ideas": ("reading-report.md", "Idea ID", "N", ["Candidate idea", "Closest baseline or prior art", "Atomic delta", "Novelty type", "Claim IDs", "Evidence IDs", "Transferable abstraction", "Generative direction and decisive test", "Perspective shift", "Boundary", "Judgment"]),
    "designs": ("reading-report.md", "Design ID", "D", ["Named design choice", "Target function and constraints", "Minimum baseline", "Baseline failure mode", "Necessity judgment", "Sufficiency scope", "Joint dependencies", "Alternatives and counterexamples", "Discriminating control or matched comparison", "Claim IDs", "Evidence IDs", "Verdict"]),
}


def scalar(value: str) -> str:
    return value.strip().strip("`").strip()


def normalize_identifier(value: str) -> str:
    """Normalize stable source identity; a DOI wins over attached metadata."""
    value = unquote(scalar(value))
    doi = re.search(r"10\.\d{4,9}/[^\s<>\"|;,]+", value, re.I)
    if doi:
        suffix = doi.group(0).rstrip(".]}")
        while suffix.endswith(")") and suffix.count(")") > suffix.count("("):
            suffix = suffix[:-1]
        return "doi:" + suffix.casefold()
    arxiv = re.search(r"(?:arxiv\s*:\s*|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5}(?:v\d+)?)", value, re.I)
    if arxiv:
        return "arxiv:" + arxiv.group(1).casefold()
    pmid = re.search(r"pmid\s*:?\s*(\d+)", value, re.I)
    if pmid:
        return "pmid:" + pmid.group(1)
    return re.sub(r"\s+", " ", value).rstrip("/").casefold()


def parse_tables(text: str) -> list[dict[str, Any]]:
    """Parse actual Markdown tables (outside fenced examples), retaining lines."""
    lines = text.splitlines()
    result: list[dict[str, Any]] = []
    fence_char = ""
    fence_length = 0
    i = 0
    while i < len(lines):
        if fence_char:
            if re.fullmatch(r" {0,3}" + re.escape(fence_char) + "{" + str(fence_length) + r",}\s*", lines[i]):
                fence_char = ""
            i += 1
            continue
        opener = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", lines[i])
        if opener and (opener[1][0] != "`" or "`" not in opener[2]):
            fence_char, fence_length = opener[1][0], len(opener[1])
            i += 1
            continue
        if not lines[i].lstrip().startswith("|") or i + 1 >= len(lines):
            i += 1
            continue
        def cells(line: str) -> list[str]:
            return [scalar(v.replace(r"\|", "|")) for v in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        headers = cells(lines[i])
        separator = cells(lines[i + 1])
        if len(headers) != len(separator) or not all(re.fullmatch(r":?-{3,}:?", v.replace(" ", "")) for v in separator):
            i += 1
            continue
        table = {"headers": headers, "line": i + 1, "rows": [], "malformed_rows": []}
        i += 2
        while i < len(lines) and lines[i].lstrip().startswith("|"):
            values = cells(lines[i])
            if len(values) != len(headers):
                table["malformed_rows"].append(i + 1)
            else:
                table["rows"].append({**dict(zip(headers, values)), "_line": i + 1})
            i += 1
        result.append(table)
    return result


def _native_path(path: Path) -> Path:
    """Use extended Windows paths for IO, without changing public owner IDs."""
    raw = str(path.absolute())
    if os.name == "nt" and not raw.startswith("\\\\?\\"):
        raw = "\\\\?\\UNC\\" + raw[2:] if raw.startswith("\\\\") else "\\\\?\\" + raw
    return Path(raw)


def validate_run(run_dir: str | Path) -> dict[str, Any]:
    """Return diagnostics, indexed canonical rows and deduplicated source counts.

    Paths are resolved from the actual run directory, never its historical
    output_directory. Return data can be consumed by Mapper without copying it
    into a second scientific ledger. No file/network/environment mutation occurs.
    """
    root = Path(run_dir).resolve()
    io_root = _native_path(root).resolve()
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    texts: dict[str, str] = {}
    tables: dict[str, list[dict[str, Any]]] = {}
    hashes: dict[str, str] = {}

    def diag(code: str, message: str, file: str, row: dict[str, Any] | None = None, *, warning: bool = False) -> None:
        row = row or {}
        entry = {"code": code, "file": file, "line": row.get("_line", row.get("line", 1)), "record_id": next((row[k] for k in ("Evidence ID", "Idea ID", "Design ID", "Claim ID", "Source ID") if k in row), ""), "message": message}
        (warnings if warning else errors).append(entry)

    for name in ("paper-package.md", "reading-report.md", "auxiliary-literature-table.md", "external-evidence-matrix.md", "view-report-audit.md"):
        path = io_root / name
        if path.is_symlink():
            diag("canonical-owner-mismatch", "Canonical owners must be the named run files, not aliases to other artifacts", name)
            continue
        if path.is_file():
            try:
                if path.resolve(strict=True).relative_to(io_root) != Path(name):
                    diag("canonical-owner-mismatch", "Canonical owner resolves outside its named run location", name)
                    continue
                raw = path.read_bytes()
                texts[name] = raw.decode("utf-8-sig")
                hashes[name] = hashlib.sha256(raw).hexdigest()
                tables[name] = parse_tables(texts[name])
            except (OSError, UnicodeError, ValueError, RuntimeError) as exc:
                diag("file-unreadable", f"Cannot read canonical file: {type(exc).__name__}", name)

    def fields(name: str) -> dict[str, str]:
        result: dict[str, str] = {}
        for table in tables.get(name, []):
            if table["headers"][:2] != ["Field", "Value"]:
                continue
            if len(table["headers"]) != len(set(table["headers"])):
                diag("table-columns", "Duplicate Run Contract columns", name, table)
                continue
            for line in table["malformed_rows"]:
                diag("malformed-row", "Run Contract row has a different number of cells than its header", name, {"_line": line})
            for row in table["rows"]:
                key = row["Field"]
                if key in result:
                    diag("duplicate-field", f"Duplicate canonical field {key}", name, row)
                result[key] = row["Value"]
        return result

    package = fields("paper-package.md")
    if "paper-package.md" not in texts:
        diag("missing-file", "Run Contract owner is required", "paper-package.md")
    for field in ("evidence_contract", "paper_identity", "task", "validation"):
        if not package.get(field):
            diag("missing-run-field", f"Run Contract requires {field}", "paper-package.md")
    for field, allowed in {"evidence_contract": {"v1.1"}, "task": {"full-report", "focused-analysis", "plan-only"}, "validation": {"standard", "main-paper-only", "fully-local", "custom"}, "presentation_handoff": {"yes", "no"}, "candidate_policy": {"soft-target", "hard-limit"}}.items():
        if field in package and package[field] not in allowed:
            diag("invalid-enum", f"{field} must be one of {sorted(allowed)}", "paper-package.md")
    if package.get("Parse status") and package["Parse status"] not in {"not-required", "not-submitted", "parsed", "partial", "failed", "blocked"}:
        diag("invalid-enum", "Main Parse status must use the canonical enum; place explanations in limitations", "paper-package.md")
    identity = package.get("DOI or canonical identifier", package.get("paper_identity", ""))
    main_identity = {"canonical_identifier": identity, "normalized_identifier": normalize_identifier(identity), "title": package.get("Canonical title", "")}
    if identity in NO_VALUE:
        diag("identity-limited", "Main paper has no stable identifier; identity must be checked manually", "paper-package.md", warning=True)
    if package.get("DOI or canonical identifier"):
        in_contract = normalize_identifier(package.get("paper_identity", ""))
        if in_contract.startswith(("doi:", "arxiv:", "pmid:")) and in_contract != main_identity["normalized_identifier"]:
            diag("main-identity-conflict", "Run Contract and main-source identity disagree", "paper-package.md")

    entities: dict[str, dict[str, dict[str, Any]]] = {}
    for kind, (file, key, prefix, required) in TABLES.items():
        indexed: dict[str, dict[str, Any]] = {}
        recognized = [t for t in tables.get(file, []) if t["headers"] and t["headers"][0] == key]
        if kind == "claims" and package.get("task") != "plan-only" and not recognized:
            diag("missing-table", "Claim and Condition Registry is required", file)
        if kind in ("sources", "evidence") and file in texts and not recognized:
            diag("missing-table", f"{kind} owner must contain its canonical table, including an honest empty table", file)
        for table in recognized:
            missing = set(required) - set(table["headers"])
            if missing or len(table["headers"]) != len(set(table["headers"])):
                diag("table-columns", f"Missing or duplicate columns; missing={sorted(missing)}", file, table)
                continue
            for line in table["malformed_rows"]:
                diag("malformed-row", "Table row has a different number of cells than its header", file, {"_line": line})
            for row in table["rows"]:
                ident = row[key]
                if not re.fullmatch(prefix + r"-\d{3,}", ident):
                    diag("invalid-id", f"Expected stable {prefix}-001 style ID", file, row)
                if ident in indexed:
                    diag("duplicate-id", f"Duplicate {ident}", file, row)
                else:
                    indexed[ident] = row
                for column in required:
                    if not row.get(column):
                        diag("blank-cell", f"{column} is blank; record an explicit scoped state", file, row)
        entities[kind] = indexed

    if package.get("task") != "plan-only" and not entities["claims"]:
        diag("empty-claim-registry", "A reading result requires at least one atomic claim", "reading-report.md")

    def enum(row: dict[str, Any], field: str, allowed: set[str], file: str, allow_blocked_reason: bool = False) -> None:
        value = row.get(field, "")
        if value not in allowed and not (allow_blocked_reason and re.fullmatch(r"blocked:\s*\S.*", value)):
            diag("invalid-enum", f"{field}={value!r} is outside its controlled vocabulary", file, row)

    def references(row: dict[str, Any], field: str, kind: str, file: str, *, single: bool = False, optional: bool = False) -> list[str]:
        value = row.get(field, "")
        if optional and value in {"none", "not-applicable"}:
            return []
        prefix = TABLES[kind][2]
        ids = re.findall(r"(?<![A-Za-z0-9-])" + prefix + r"-\d{3,}(?!\d)", value)
        remainder = re.sub(r"(?<![A-Za-z0-9-])" + prefix + r"-\d{3,}(?!\d)", "", value)
        if not ids or remainder.strip(" ,;；、\t") or (single and len(ids) != 1):
            diag("invalid-reference-cell", f"{field} must contain {'exactly one ID' if single else 'IDs only'}" + (" or none" if optional else ""), file, row)
        if len(ids) != len(set(ids)):
            diag("duplicate-reference", f"{field} repeats the same ID", file, row)
        for ident in ids:
            if ident not in entities[kind]:
                diag("dangling-reference", f"{field} references absent {ident}", file, row)
        return ids

    for row in entities["claims"].values():
        file = "reading-report.md"
        enum(row, "Priority", {"high", "medium", "low"}, file)
        enum(row, "Evidence mode", EVIDENCE_MODES, file)
        enum(row, "Status", CLAIM_STATES, file)
        joint = references(row, "Jointly demonstrated", "claims", file, optional=True)
        if row["Claim ID"] in joint:
            diag("self-joint-reference", "Jointly demonstrated lists other claims, not itself", file, row)
        role_text = row["Validation roles"]
        if role_text != "not-applicable":
            for role in re.split(r"[;；]", role_text):
                # Existing valid runs use either 'role: closed' or 'role closed'.
                state = re.search(r"(?<![\w-])(open|closed|downgraded|blocked|not-applicable)(?![\w-])", role)
                if not state or not role[:state.start()].strip(" :："):
                    diag("role-state-missing", "Each Validation role needs a role name and explicit state", file, row)

    identities: dict[str, str] = {}
    external_ids: set[str] = set()
    for sid, row in entities["sources"].items():
        file = "auxiliary-literature-table.md"
        norm = normalize_identifier(row["Canonical identifier"])
        row["normalized_identifier"] = norm
        if norm in identities:
            diag("duplicate-source-identity", f"Same canonical source already has ID {identities[norm]}; evidence rows do not create independent sources", file, row)
        identities[norm] = sid
        if norm != main_identity["normalized_identifier"]:
            external_ids.add(sid)
        references(row, "Related Claim IDs", "claims", file, optional=True)
        enum(row, "Relevance grade", {"S", "A", "B", "C", "D"}, file)
        for field, allowed in SOURCE_STATES.items():
            enum(row, field, allowed, file)
        if row["Verification status"] == "verified" and (row["Full-text status"] != "available" or row["Read status"] != "full"):
            diag("verified-without-full-read", "Verified evidence requires available, full-read text; relevance and parsing cannot substitute", file, row)
        if row["Citation status"] == "cited" and row["Verification status"] != "verified":
            diag("cited-unverified-source", "Reader citation requires verified full text", file, row)
        key = row["Reader-facing footnote key"]
        if row["Citation status"] == "cited" and (key in NO_VALUE or key.startswith("blocked:")):
            diag("cited-without-key", "A cited source requires its semantic reader-facing key", file, row)
        if key not in NO_VALUE and not key.startswith("blocked:") and row["Citation status"] != "cited":
            diag("citation-key-without-citation", "A semantic key requires Citation status=cited", file, row)

    relation_keys: dict[tuple[str, ...], str] = {}
    external_evidence_sources: set[str] = set()
    for eid, row in entities["evidence"].items():
        file = "external-evidence-matrix.md"
        claims = references(row, "Claim ID", "claims", file, single=True)
        source_ids = references(row, "Source ID", "sources", file, single=True)
        enum(row, "Relation", {"supports", "weakens", "contradicts", "contextualizes"}, file)
        enum(row, "Evidence mode", EVIDENCE_MODES, file)
        enum(row, "Evidence strength", {"strong", "moderate", "weak", "unusable"}, file)
        enum(row, "Final assessment", CLAIM_STATES, file)
        if row["Evidence strength"] == "strong" and (row["Locator"] in NO_VALUE or row["Locator"].startswith("blocked:")):
            diag("strong-without-locator", "Strong evidence requires a usable locator", file, row)
        for sid in source_ids:
            source = entities["sources"].get(sid)
            if sid in external_ids:
                external_evidence_sources.add(sid)
            if source and row["Evidence strength"] == "strong" and (source["Read status"] != "full" or source["Verification status"] != "verified"):
                diag("strong-unverified-source", "Strong evidence cannot come from an unread or unverified source", file, row)
        if len(claims) == len(source_ids) == 1:
            key = (claims[0], source_ids[0], row["Relation"], row["Evidence mode"], row["Locator"], row["Conditions"], row["Evidence summary"])
            if key in relation_keys:
                diag("duplicate-evidence-relation", f"Same source/claim/relation/conditions already recorded as {relation_keys[key]}; merge duplicate votes", file, row)
            relation_keys[key] = eid

    for kind in ("ideas", "designs"):
        for row in entities[kind].values():
            references(row, "Claim IDs", "claims", "reading-report.md")
            references(row, "Evidence IDs", "evidence", "reading-report.md", optional=True)
            enum(row, "Judgment" if kind == "ideas" else "Verdict", IDEA_VERDICTS if kind == "ideas" else DESIGN_VERDICTS, "reading-report.md", allow_blocked_reason=True)

    distinct = {entities["sources"][s]["normalized_identifier"] for s in external_ids}
    verified = {entities["sources"][s]["normalized_identifier"] for s in external_ids if entities["sources"][s]["Read status"] == "full" and entities["sources"][s]["Verification status"] == "verified"}
    cited = {entities["sources"][s]["normalized_identifier"] for s in external_ids if entities["sources"][s]["Citation status"] == "cited"}
    counts = {kind: len(rows) for kind, rows in entities.items()}
    counts.update(distinct_external_sources=len(distinct), verified_external_sources=len(verified), cited_external_sources=len(cited), evidence_external_sources=len(external_evidence_sources))
    for field, actual in (("candidate_count", len(distinct)), ("verified_external_source_count", len(verified)), ("cited_external_source_count", len(cited))):
        if field in package:
            try:
                stated = int(package[field])
            except ValueError:
                diag("invalid-counter", f"{field} must be an integer", "paper-package.md")
            else:
                if stated != actual:
                    diag("source-count-mismatch", f"{field}={stated}, but distinct external source identities give {actual}", "paper-package.md")

    return {"schema_version": SCHEMA_VERSION, "valid": not errors, "run_directory": str(root), "errors": errors, "warnings": warnings, "main_identity": main_identity, **entities, "counts": counts, "artifacts": hashes, "run_contract": package, "scientific_independence": "Not inferred from row, source, or agent counts; review authorship, datasets, and conditions separately."}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args(argv)
    try:
        result = validate_run(args.run_dir)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"Canonical validation failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"canonical validation: {'PASS' if result['valid'] else 'FAIL'}; {len(result['errors'])} errors, {len(result['warnings'])} warnings")
        for item in result["errors"] + result["warnings"]:
            print(f"{item['file']}:{item['line']} [{item['code']}] {item['record_id']}: {item['message']}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
