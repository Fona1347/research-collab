"""Provider-neutral scholarly records and deterministic merge helpers."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


DOI_RE = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonicalize_url(url: str) -> str:
    """Normalize a URL for comparison while preserving meaningful query fields."""
    if not url:
        return ""
    parts = urlsplit(str(url).strip())
    query = [
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_")
        and key.lower() not in {"campaign", "ref"}
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(query), "")
    )


def normalize_doi(value: str | None) -> str:
    if not value:
        return ""
    text = str(value).strip()
    text = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", text, flags=re.I)
    match = DOI_RE.search(text)
    return match.group(0).rstrip(".,;:)]}").lower() if match else ""


def normalize_title(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def openalex_short_id(value: str | None) -> str:
    text = str(value or "").strip().rstrip("/")
    return text.rsplit("/", 1)[-1] if text else ""


def reconstruct_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for word, indices in inverted_index.items():
        for index in indices or []:
            if isinstance(index, int):
                positions[index] = str(word)
    return " ".join(positions[index] for index in sorted(positions))


@dataclass(slots=True)
class Provenance:
    provider: str
    retrieved_at: str = field(default_factory=utc_now)
    request_url: str = ""
    provider_record_id: str = ""
    cache_path: str = ""
    operation: str = "search"
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class FullTextLocation:
    url: str
    kind: str = "landing"
    source: str = ""
    license: str = ""
    host_type: str = ""
    version: str = ""
    is_oa: bool | None = None

    def __post_init__(self) -> None:
        self.url = canonicalize_url(self.url)


@dataclass(slots=True)
class EvidenceChunk:
    text: str
    source_type: str = "abstract"
    locator: str = ""
    url: str = ""
    extraction_method: str = "provider-metadata"
    content_hash: str = ""


@dataclass(slots=True)
class PaperRecord:
    title: str = ""
    authors: list[str] = field(default_factory=list)
    publication_date: str = ""
    year: int | None = None
    venue: str = ""
    doi: str = ""
    pmid: str = ""
    pmcid: str = ""
    openalex_id: str = ""
    semantic_scholar_id: str = ""
    arxiv_id: str = ""
    url: str = ""
    abstract: str = ""
    publication_types: list[str] = field(default_factory=list)
    fields_of_study: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    citation_count: int | None = None
    reference_count: int | None = None
    is_retracted: bool = False
    is_open_access: bool | None = None
    fulltext_locations: list[FullTextLocation] = field(default_factory=list)
    evidence_chunks: list[EvidenceChunk] = field(default_factory=list)
    facets: list[str] = field(default_factory=list)
    provenance: list[Provenance] = field(default_factory=list)
    field_sources: dict[str, list[str]] = field(default_factory=dict)
    conflicts: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    metrics_by_provider: dict[str, dict[str, Any]] = field(default_factory=dict)
    journal_metrics: dict[str, dict[str, Any]] = field(default_factory=dict)
    ranking: dict[str, Any] = field(default_factory=dict)
    retrieval_routes: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.doi = normalize_doi(self.doi)
        self.openalex_id = openalex_short_id(self.openalex_id)
        self.url = canonicalize_url(self.url)
        self.authors = _unique_strings(self.authors)
        self.publication_types = _unique_strings(self.publication_types)
        self.fields_of_study = _unique_strings(self.fields_of_study)
        self.keywords = _unique_strings(self.keywords)
        self.facets = _unique_strings(self.facets)

    @property
    def providers(self) -> list[str]:
        return _unique_strings(item.provider for item in self.provenance)

    def mark_fields(self, provider: str, fields: Iterable[str]) -> None:
        for name in fields:
            value = getattr(self, name, None)
            if value not in (None, "", [], {}):
                self.field_sources.setdefault(name, [])
                if provider not in self.field_sources[name]:
                    self.field_sources[name].append(provider)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["providers"] = self.providers
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PaperRecord":
        data = dict(payload)
        data.pop("providers", None)
        data["fulltext_locations"] = [
            item if isinstance(item, FullTextLocation) else FullTextLocation(**item)
            for item in data.get("fulltext_locations") or []
        ]
        data["evidence_chunks"] = [
            item if isinstance(item, EvidenceChunk) else EvidenceChunk(**item)
            for item in data.get("evidence_chunks") or []
        ]
        data["provenance"] = [
            item if isinstance(item, Provenance) else Provenance(**item)
            for item in data.get("provenance") or []
        ]
        accepted = cls.__dataclass_fields__.keys()
        return cls(**{key: value for key, value in data.items() if key in accepted})


SCALAR_FIELDS = (
    "title",
    "publication_date",
    "year",
    "venue",
    "doi",
    "pmid",
    "pmcid",
    "openalex_id",
    "semantic_scholar_id",
    "arxiv_id",
    "url",
    "abstract",
    "citation_count",
    "reference_count",
    "is_retracted",
    "is_open_access",
)

FIELD_PRIORITY: dict[str, tuple[str, ...]] = {
    "title": ("crossref", "europe_pmc", "semantic_scholar", "openalex"),
    "authors": ("crossref", "europe_pmc", "semantic_scholar", "openalex"),
    "publication_date": ("crossref", "europe_pmc", "openalex", "semantic_scholar"),
    "year": ("crossref", "europe_pmc", "openalex", "semantic_scholar"),
    "venue": ("crossref", "europe_pmc", "semantic_scholar", "openalex"),
    "abstract": ("europe_pmc", "semantic_scholar", "openalex", "crossref"),
    "citation_count": ("semantic_scholar", "openalex", "europe_pmc", "crossref"),
    "reference_count": ("semantic_scholar", "crossref", "openalex"),
    "is_open_access": ("unpaywall", "europe_pmc", "openalex", "semantic_scholar"),
}


def _unique_strings(values: Iterable[Any]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values or []:
        value = str(raw or "").strip()
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            output.append(value)
    return output


def source_text(record: PaperRecord | dict[str, Any]) -> str:
    item = record if isinstance(record, PaperRecord) else PaperRecord.from_dict(record)
    parts = [item.title, item.abstract]
    parts.extend(chunk.text for chunk in item.evidence_chunks)
    return "\n".join(part.strip() for part in parts if part and part.strip())


def identity_keys(record: PaperRecord) -> set[str]:
    keys: set[str] = set()
    for prefix, value in (
        ("doi", record.doi),
        ("pmid", record.pmid),
        ("pmcid", record.pmcid),
        ("openalex", record.openalex_id),
        ("s2", record.semantic_scholar_id),
        ("arxiv", record.arxiv_id),
        ("url", record.url),
    ):
        if value:
            keys.add(f"{prefix}:{str(value).casefold()}")
    title = normalize_title(record.title)
    if len(title) >= 20:
        if record.authors:
            lead_author = normalize_title(record.authors[0])
            if lead_author:
                keys.add(f"title-author:{title}:{lead_author}")
        else:
            keys.add(f"title-only:{title}")
    return keys


def _field_provider(record: PaperRecord, name: str) -> str:
    sources = record.field_sources.get(name) or []
    return sources[0] if sources else (record.providers[0] if record.providers else "")


def _priority(name: str, provider: str) -> int:
    order = FIELD_PRIORITY.get(name, ())
    try:
        return len(order) - order.index(provider)
    except ValueError:
        return 0


def _record_conflict(
    record: PaperRecord, name: str, value: Any, provider: str
) -> None:
    entry = {"value": value, "provider": provider}
    bucket = record.conflicts.setdefault(name, [])
    if entry not in bucket:
        bucket.append(entry)


def _promote_source(record: PaperRecord, name: str, provider: str) -> None:
    if not provider:
        return
    existing = record.field_sources.get(name) or []
    record.field_sources[name] = _unique_strings(
        [provider, *(value for value in existing if value != provider)]
    )


def merge_pair(base: PaperRecord, incoming: PaperRecord) -> PaperRecord:
    """Merge records without discarding conflicting provider values."""
    for name in SCALAR_FIELDS:
        current = getattr(base, name)
        candidate = getattr(incoming, name)
        if name == "is_retracted":
            current_provider = (base.field_sources.get(name) or [""])[0]
            candidate_provider = (incoming.field_sources.get(name) or [""])[0]
            if current != candidate and current_provider and candidate_provider:
                _record_conflict(base, name, current, current_provider)
                _record_conflict(base, name, candidate, candidate_provider)
            if candidate:
                base.is_retracted = True
                _promote_source(
                    base,
                    name,
                    candidate_provider or _field_provider(incoming, name),
                )
            continue
        if candidate in (None, ""):
            continue
        candidate_provider = _field_provider(incoming, name)
        if current in (None, ""):
            setattr(base, name, candidate)
            _promote_source(base, name, candidate_provider)
        elif current != candidate:
            current_provider = _field_provider(base, name)
            _record_conflict(base, name, current, current_provider)
            _record_conflict(base, name, candidate, candidate_provider)
            if _priority(name, candidate_provider) > _priority(name, current_provider):
                setattr(base, name, candidate)
                _promote_source(base, name, candidate_provider)

    if incoming.authors:
        if not base.authors:
            base.authors = list(incoming.authors)
            _promote_source(base, "authors", _field_provider(incoming, "authors"))
        elif [item.casefold() for item in base.authors] != [
            item.casefold() for item in incoming.authors
        ]:
            _record_conflict(base, "authors", list(base.authors), _field_provider(base, "authors"))
            _record_conflict(
                base, "authors", list(incoming.authors), _field_provider(incoming, "authors")
            )
            if _priority("authors", _field_provider(incoming, "authors")) > _priority(
                "authors", _field_provider(base, "authors")
            ):
                base.authors = list(incoming.authors)
                _promote_source(base, "authors", _field_provider(incoming, "authors"))

    base.publication_types = _unique_strings(
        [*base.publication_types, *incoming.publication_types]
    )
    base.fields_of_study = _unique_strings(
        [*base.fields_of_study, *incoming.fields_of_study]
    )
    base.keywords = _unique_strings([*base.keywords, *incoming.keywords])
    base.facets = _unique_strings([*base.facets, *incoming.facets])
    known_provenance = {
        json_key
        for json_key in (
            repr(sorted(asdict(item).items())) for item in base.provenance
        )
    }
    for item in incoming.provenance:
        key = repr(sorted(asdict(item).items()))
        if key not in known_provenance:
            base.provenance.append(item)
            known_provenance.add(key)

    known_locations = {canonicalize_url(item.url) for item in base.fulltext_locations}
    for item in incoming.fulltext_locations:
        if item.url and canonicalize_url(item.url) not in known_locations:
            base.fulltext_locations.append(item)
            known_locations.add(canonicalize_url(item.url))

    known_chunks = {
        (item.content_hash or item.text, item.locator, item.source_type)
        for item in base.evidence_chunks
    }
    for item in incoming.evidence_chunks:
        key = (item.content_hash or item.text, item.locator, item.source_type)
        if item.text and key not in known_chunks:
            base.evidence_chunks.append(item)
            known_chunks.add(key)

    for name, providers in incoming.field_sources.items():
        base.field_sources[name] = _unique_strings(
            [*(base.field_sources.get(name) or []), *providers]
        )
    for name, values in incoming.conflicts.items():
        for value in values:
            if value not in base.conflicts.setdefault(name, []):
                base.conflicts[name].append(value)
    for provider, metrics in incoming.metrics_by_provider.items():
        base.metrics_by_provider.setdefault(provider, {}).update(metrics)
    for provider, metrics in incoming.journal_metrics.items():
        base.journal_metrics.setdefault(provider, {}).update(metrics)
    for route in incoming.retrieval_routes:
        if route not in base.retrieval_routes:
            base.retrieval_routes.append(dict(route))
    if incoming.ranking and not base.ranking:
        base.ranking = dict(incoming.ranking)
    return base


def merge_records(records: Iterable[PaperRecord | dict[str, Any]]) -> list[PaperRecord]:
    merged: list[PaperRecord] = []
    for raw in records:
        record = raw if isinstance(raw, PaperRecord) else PaperRecord.from_dict(raw)
        keys = identity_keys(record)
        matches = [
            index
            for index, current in enumerate(merged)
            if keys and keys.intersection(identity_keys(current))
        ]
        if not matches:
            merged.append(record)
            continue
        target = matches[0]
        for duplicate in reversed(matches[1:]):
            merge_pair(merged[target], merged.pop(duplicate))
        merge_pair(merged[target], record)
    return merged


def record_score(record: PaperRecord) -> tuple[int, int, int, int]:
    verification = 2 if record.evidence_chunks else 1 if record.abstract else 0
    identifiers = sum(
        bool(value)
        for value in (record.doi, record.pmid, record.openalex_id, record.semantic_scholar_id)
    )
    citations = record.citation_count or 0
    year = record.year or 0
    return (0 if record.is_retracted else 1, verification, identifiers, citations + year)
