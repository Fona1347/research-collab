"""Read-only validation of explicitly linked Deep Reading canonical records."""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from urllib.parse import unquote


CANONICAL_FILES = frozenset({"paper-package.md", "reading-report.md", "auxiliary-literature-table.md", "external-evidence-matrix.md", "view-report-audit.md"})
CHECKER_PATH: Path | None = None


def normalize_identity(value: str) -> str:
    value = unquote(str(value)).strip().casefold()
    doi = re.search(r"10\.\d{4,9}/[^\s<>|#;]+", value)
    if doi:
        suffix = doi.group(0).rstrip(".,]}\"")
        while suffix.endswith(")") and suffix.count(")") > suffix.count("("):
            suffix = suffix[:-1]
        return "doi:" + suffix
    arxiv = re.search(r"(?:arxiv[:/]|arxiv\.org/(?:abs|pdf)/)(\d{4}\.\d{4,5})(?:v\d+)?", value)
    if arxiv:
        return "arxiv:" + arxiv.group(1)
    return value.rstrip("/")


def load_checker():
    path = CHECKER_PATH or Path(__file__).resolve().parents[2] / "paper-deep-reading" / "scripts" / "check_canonical.py"
    if not path.is_file():
        raise ValueError(f"Deep Reading canonical checker unavailable: {path}; use --canonical-checker for an explicit maintenance-source path")
    spec = importlib.util.spec_from_file_location("_rom_canonical_checker", path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Cannot load canonical checker: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.validate_run


def parse_refs(value: str, base: Path, owner: Path) -> list[tuple[Path, str, str]]:
    refs = []
    for token in value.split(";"):
        token = token.strip().strip("<>")
        if not token or token.lower() in {"none", "not applicable"}:
            continue
        raw_path, _, fragment = token.partition("#")
        path = Path(unquote(raw_path))
        if path.name not in CANONICAL_FILES or (not path.is_absolute() and path.parent == Path(".")):
            raise ValueError(f"Canonical ref must name an explicit run path and canonical artifact: {token}")
        candidate = path if path.is_absolute() else base / path
        if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
            raise ValueError(f"Canonical ref cannot be a linked file: {token}")
        try:
            resolved = candidate.resolve(strict=True)
        except FileNotFoundError as exc:
            raise ValueError(f"Canonical artifact does not exist: {token}") from exc
        if not resolved.is_file() or resolved.parent != owner:
            raise ValueError(f"Canonical ref has the wrong run owner: {token}")
        kind, _, record_id = unquote(fragment).partition("=")
        if fragment and kind not in {"claim", "source", "evidence"}:
            raise ValueError(f"Canonical ref requires a typed claim/source/evidence fragment: {token}")
        refs.append((resolved, kind, record_id))
    if not refs:
        raise ValueError("No canonical artifact refs")
    return refs


def record_identity(payload: dict, kind: str, record_id: str, filename: str, *, for_import: bool = False) -> str:
    expected_file = {"claim": "reading-report.md", "source": "auxiliary-literature-table.md", "evidence": "external-evidence-matrix.md"}
    if filename != expected_file[kind]:
        raise ValueError(f"{kind} {record_id} is not owned by {filename}")
    records = payload[{"claim": "claims", "source": "sources", "evidence": "evidence"}[kind]]
    if record_id not in records:
        raise ValueError(f"Canonical {kind} does not exist: {record_id}")
    record = records[record_id]
    if kind == "claim":
        locator = record.get("Main-paper locator", "").strip().lower()
        if for_import and (not locator or locator in {"none", "unknown", "not available", "unavailable", "pending", "not-applicable"} or locator.startswith("blocked:")):
            raise ValueError(f"Canonical claim {record_id} lacks a verified main-paper locator")
        return normalize_identity(payload["main_identity"].get("normalized_identifier", ""))
    if kind == "evidence":
        source_id = record.get("Source ID", "")
        record = payload["sources"].get(source_id, {})
        if not record and str(source_id).strip().lower() in {"main", "main-paper", "s-000"}:
            return normalize_identity(payload["main_identity"].get("normalized_identifier", ""))
    if for_import and not all(record.get(field, "").strip().lower() == required for field, required in (
        ("Full-text status", "available"), ("Read status", "full"), ("Verification status", "verified"),
    )):
        raise ValueError(f"Canonical {kind} {record_id} requires an available, fully read and verified source before canonical-deep-read import")
    return normalize_identity(record.get("normalized_identifier", record.get("DOI or URL", "")))


def check_import(run_text: str, queue_refs: str, evidence_refs: list[tuple[str, str]], *, base: Path, paper_key: str, cache: dict) -> None:
    raw_owner = Path(run_text)
    candidate = raw_owner if raw_owner.is_absolute() else base / raw_owner
    if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
        raise ValueError("Deep Reading run cannot be a linked directory")
    owner = candidate.resolve(strict=True)
    if not owner.is_dir():
        raise ValueError("Deep Reading run is not a directory")
    if owner not in cache:
        cache[owner] = load_checker()(owner)
    payload = cache[owner]
    if not payload.get("valid"):
        raise ValueError(f"Deep Reading canonical structure invalid: {payload.get('errors', [])}")
    main_id = normalize_identity(payload["main_identity"].get("normalized_identifier", ""))
    if not main_id or main_id != normalize_identity(paper_key):
        raise ValueError("Deep Reading handoff paper identity differs from canonical main paper")
    for path, kind, record_id in parse_refs(queue_refs, base, owner):
        if kind:
            record_identity(payload, kind, record_id, path.name)
    for identity, text in evidence_refs:
        refs = parse_refs(text, base, owner)
        identities = {record_identity(payload, kind, record_id, path.name, for_import=True)
                      for path, kind, record_id in refs if kind}
        if normalize_identity(identity) not in identities:
            raise ValueError(f"Canonical evidence requires a real typed locator for its own source identity: {identity}")
