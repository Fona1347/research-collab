"""Adapters for open scholarly APIs and Easy Scholar journal enrichment."""

from __future__ import annotations

import html
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable
from urllib.parse import quote

from .http_client import HttpClient, HttpResult
from .models import (
    EvidenceChunk,
    FullTextLocation,
    PaperRecord,
    Provenance,
    canonicalize_url,
    normalize_doi,
    openalex_short_id,
    reconstruct_abstract,
    utc_now,
)


METADATA_FIELDS = (
    "title",
    "authors",
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
    "publication_types",
    "fields_of_study",
    "keywords",
    "citation_count",
    "reference_count",
    "is_retracted",
    "is_open_access",
)
NON_RETRACTION_FIELDS = tuple(
    name for name in METADATA_FIELDS if name != "is_retracted"
)


def _first(value: Any, default: str = "") -> str:
    if isinstance(value, list):
        return str(value[0]) if value else default
    return str(value) if value not in (None, "") else default


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError, OverflowError):
        return None


def _float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _year(value: Any) -> int | None:
    match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
    return int(match.group(1)) if match else None


def _strip_markup(value: Any) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _request_provenance(
    provider: str,
    result: HttpResult | None,
    *,
    record_id: str = "",
    operation: str = "search",
    notes: Iterable[str] = (),
) -> Provenance:
    return Provenance(
        provider=provider,
        retrieved_at=result.retrieved_at if result and result.retrieved_at else utc_now(),
        request_url=result.url if result else "",
        provider_record_id=record_id,
        cache_path=result.cache_path if result else "",
        operation=operation,
        notes=list(notes),
    )


@dataclass(slots=True)
class ProviderStatus:
    name: str
    enabled: bool
    reason: str = ""
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Provider-neutral filters; adapters apply only fields their API supports."""

    after_date: str | None = None
    before_date: str | None = None
    fields_of_study: tuple[str, ...] = ()
    publication_types: tuple[str, ...] = ()
    open_access_only: bool = False
    min_citation_count: int | None = None


@dataclass(slots=True)
class SearchBatch:
    """One response page; normalization completeness is not search recall."""

    records: list[PaperRecord]
    diagnostics: dict[str, Any]


class Provider:
    name = "provider"
    capabilities = ("search", "get_paper", "resolve_fulltext", "provenance")
    min_interval = 0.0
    serialize_requests = False

    def __init__(
        self,
        *,
        cache_dir: str | Path,
        client: HttpClient | None = None,
    ) -> None:
        self.client = client or HttpClient(
            self.name,
            cache_dir=cache_dir,
            min_interval=self.min_interval,
            user_agent=self.user_agent(),
            serialize_requests=self.serialize_requests,
            serialization_key=self.name if self.serialize_requests else None,
        )

    def user_agent(self) -> str:
        return "research-lookup-enhanced/0.1"

    def status(self) -> ProviderStatus:
        return ProviderStatus(self.name, True, capabilities=self.capabilities)

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        after_date: str | None = None,
        facet: str = "general",
        filters: SearchFilters | None = None,
        semantic: bool = False,
    ) -> list[PaperRecord]:
        raise NotImplementedError

    def get_paper(self, identifier: str) -> PaperRecord | None:
        raise NotImplementedError

    def search_batch(self, query: str, **kwargs: Any) -> SearchBatch:
        """Diagnostic companion to the backwards-compatible list API."""
        self._last_search_batch = None
        records = self.search(query, **kwargs)
        batch = self._last_search_batch
        if batch is not None:
            return batch
        return SearchBatch(records, {
            "received_count": None, "normalized_count": len(records),
            "discarded_count": None, "provider_total": None, "has_more": None,
            "stop_reason": "pagination-unknown", "status": "ok",
            "row_errors": [], "diagnostics_available": False,
        })

    def _normalize_search_page(
        self, items: Any, normalize: Callable[[dict[str, Any]], PaperRecord],
        *, provider_total: Any = None, has_more: bool | None = None,
    ) -> list[PaperRecord]:
        if not isinstance(items, list):
            raise ValueError("Provider response record collection is not a list")
        records: list[PaperRecord] = []
        errors: list[dict[str, Any]] = []
        for index, item in enumerate(items):
            try:
                if not isinstance(item, dict):
                    raise TypeError("Record is not an object")
                record = normalize(item)
                if not (record.title or record.doi or record.pmid or record.openalex_id or record.semantic_scholar_id or record.pmcid):
                    raise ValueError("Record has neither a title nor a stable identifier")
                records.append(record)
            except (TypeError, ValueError, OverflowError, AttributeError, KeyError, IndexError) as exc:
                # Avoid retaining source payloads or arbitrary exception strings.
                identifier = ""
                if isinstance(item, dict):
                    identifier = str(item.get("id") or item.get("DOI") or item.get("doi") or item.get("paperId") or "")[:256]
                errors.append({"row_index": index, "record_id": identifier,
                               "error_type": type(exc).__name__})
        total = _integer(provider_total)
        if total is not None and total < 0:
            total = None
        if has_more is None and total is not None:
            has_more = total > len(items)
        self._last_search_batch = SearchBatch(records, {
            "received_count": len(items), "normalized_count": len(records),
            "discarded_count": len(errors), "provider_total": total,
            "has_more": has_more,
            "stop_reason": "single-page-limit" if has_more else (
                "source-exhausted" if has_more is False else "pagination-unknown"),
            "status": "partial" if errors else "ok", "row_errors": errors,
            "diagnostics_available": True,
        })
        return records

    def get_papers(self, identifiers: Iterable[str]) -> list[PaperRecord]:
        records: list[PaperRecord] = []
        for identifier in identifiers:
            record = self.get_paper(identifier)
            if record:
                records.append(record)
        return records

    def get_citations(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        return []

    def get_references(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        return []

    def resolve_fulltext(self, record: PaperRecord) -> list[FullTextLocation]:
        return list(record.fulltext_locations)


class OpenAlexProvider(Provider):
    name = "openalex"
    capabilities = (
        "search",
        "get_paper",
        "get_citations",
        "get_references",
        "filtered_search",
        "semantic_search",
        "resolve_fulltext",
        "provenance",
    )
    base_url = "https://api.openalex.org"
    fields = (
        "id,doi,title,publication_year,publication_date,type,is_retracted,"
        "cited_by_count,open_access,authorships,primary_location,"
        "best_oa_location,abstract_inverted_index,referenced_works,ids,"
        "topics,keywords"
    )
    search_fields = fields + ",relevance_score"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.api_key = os.getenv("OPENALEX_API_KEY", "").strip()
        self.mailto = os.getenv("OPENALEX_MAILTO", "").strip()

    def _params(self, **values: Any) -> dict[str, Any]:
        params = {key: value for key, value in values.items() if value not in (None, "")}
        if self.api_key:
            params["api_key"] = self.api_key
        if self.mailto:
            params["mailto"] = self.mailto
        return params

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            self.name,
            bool(self.api_key),
            "OPENALEX_API_KEY is not configured"
            if not self.api_key
            else "",
            self.capabilities,
        )

    @staticmethod
    def normalize(
        item: dict[str, Any],
        result: HttpResult | None = None,
        *,
        facet: str = "general",
        operation: str = "search",
    ) -> PaperRecord:
        openalex_id = openalex_short_id(item.get("id"))
        ids = item.get("ids") or {}
        authors = [
            str((authorship.get("author") or {}).get("display_name") or "")
            for authorship in item.get("authorships") or []
        ]
        primary = item.get("primary_location") or {}
        source = primary.get("source") or {}
        best = item.get("best_oa_location") or {}
        access = item.get("open_access") or {}
        topics = item.get("topics") or []
        fields_of_study: list[str] = []
        for topic in topics:
            for value in (
                topic.get("display_name"),
                (topic.get("field") or {}).get("display_name"),
                (topic.get("domain") or {}).get("display_name"),
            ):
                if value:
                    fields_of_study.append(str(value))
        keywords = [
            str(value.get("display_name") or value.get("keyword") or "")
            for value in item.get("keywords") or []
        ]
        locations: list[FullTextLocation] = []
        for url, kind in (
            (best.get("pdf_url"), "pdf"),
            (best.get("landing_page_url"), "html"),
            (access.get("oa_url"), "landing"),
        ):
            if url:
                locations.append(
                    FullTextLocation(
                        url=str(url),
                        kind=kind,
                        source="openalex",
                        license=str(best.get("license") or ""),
                        host_type=str((best.get("source") or {}).get("host_organization_name") or ""),
                        version=str(best.get("version") or ""),
                        is_oa=True,
                    )
                )
        record = PaperRecord(
            title=str(item.get("title") or ""),
            authors=authors,
            publication_date=str(item.get("publication_date") or ""),
            year=_integer(item.get("publication_year")),
            venue=str(source.get("display_name") or ""),
            doi=normalize_doi(item.get("doi") or ids.get("doi")),
            pmid=str(ids.get("pmid") or "").rsplit("/", 1)[-1],
            pmcid=str(ids.get("pmcid") or "").rsplit("/", 1)[-1],
            openalex_id=openalex_id,
            arxiv_id=str(ids.get("arxiv") or "").rstrip("/").rsplit("/", 1)[-1],
            url=str(primary.get("landing_page_url") or item.get("doi") or item.get("id") or ""),
            abstract=reconstruct_abstract(item.get("abstract_inverted_index")),
            publication_types=[str(item.get("type") or "")],
            fields_of_study=fields_of_study,
            keywords=keywords,
            citation_count=_integer(item.get("cited_by_count")),
            is_retracted=bool(item.get("is_retracted")),
            is_open_access=bool(access.get("is_oa")) if "is_oa" in access else None,
            fulltext_locations=locations,
            facets=[facet],
            provenance=[
                _request_provenance(
                    "openalex",
                    result,
                    record_id=openalex_id,
                    operation=operation,
                )
            ],
            metrics_by_provider={
                "openalex": {
                    "citation_count": _integer(item.get("cited_by_count")),
                    "relevance_score": _float(item.get("relevance_score")),
                    "search_mode": (
                        "semantic" if operation == "semantic_search" else "keyword"
                    ),
                }
            },
        )
        fields = NON_RETRACTION_FIELDS + (("is_retracted",) if "is_retracted" in item else ())
        record.mark_fields("openalex", fields)
        return record

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        after_date: str | None = None,
        facet: str = "general",
        filters: SearchFilters | None = None,
        semantic: bool = False,
    ) -> list[PaperRecord]:
        options = filters or SearchFilters()
        filter_values: list[str] = []
        start = options.after_date or after_date
        if start:
            filter_values.append(f"from_publication_date:{start}")
        if options.before_date:
            filter_values.append(f"to_publication_date:{options.before_date}")
        if options.publication_types:
            filter_values.append("type:" + "|".join(options.publication_types))
        if options.open_access_only:
            filter_values.append("is_oa:true")
        if options.min_citation_count is not None:
            filter_values.append(f"cited_by_count:>{max(-1, options.min_citation_count - 1)}")
        topic_ids = [
            value
            for value in options.fields_of_study
            if re.fullmatch(r"T\d+", value.strip(), flags=re.I)
        ]
        if topic_ids:
            filter_values.append("topics.id:" + "|".join(topic_ids))
        search_key = "search.semantic" if semantic else "search"
        payload, result = self.client.get_json(
            f"{self.base_url}/works",
            params=self._params(
                **{
                    search_key: query,
                    "per_page": min(max(1, limit), 50 if semantic else 100),
                    "filter": ",".join(filter_values),
                    "select": self.search_fields,
                }
            ),
        )
        operation = "semantic_search" if semantic else "search"
        return self._normalize_search_page(
            payload.get("results", []),
            lambda item: self.normalize(item, result, facet=facet, operation=operation),
            provider_total=(payload.get("meta") or {}).get("count"),
        )

    def get_paper(self, identifier: str) -> PaperRecord | None:
        doi = normalize_doi(identifier)
        lookup = f"doi:{doi}" if doi else openalex_short_id(identifier)
        payload, result = self.client.get_json(
            f"{self.base_url}/works/{quote(lookup, safe=':')}",
            params=self._params(select=self.fields),
        )
        return self.normalize(payload, result, facet="identifier", operation="get_paper")

    def get_citations(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        seed = self.get_paper(identifier)
        if not seed or not seed.openalex_id:
            return []
        payload, result = self.client.get_json(
            f"{self.base_url}/works",
            params=self._params(
                filter=f"cites:{seed.openalex_id}",
                per_page=min(max(1, limit), 100),
                select=self.fields,
            ),
        )
        return [
            self.normalize(item, result, facet="citation", operation="get_citations")
            for item in payload.get("results") or []
        ]

    def get_references(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        doi = normalize_doi(identifier)
        lookup = f"doi:{doi}" if doi else openalex_short_id(identifier)
        payload, first_result = self.client.get_json(
            f"{self.base_url}/works/{quote(lookup, safe=':')}",
            params=self._params(select="id,referenced_works"),
        )
        ids = [openalex_short_id(value) for value in payload.get("referenced_works") or []]
        ids = [value for value in ids if value][: min(limit, 100)]
        if not ids:
            return []
        references, result = self.client.get_json(
            f"{self.base_url}/works",
            params=self._params(
                filter="openalex_id:" + "|".join(ids),
                per_page=len(ids),
                select=self.fields,
            ),
        )
        del first_result
        return [
            self.normalize(item, result, facet="reference", operation="get_references")
            for item in references.get("results") or []
        ]


class SemanticScholarProvider(Provider):
    name = "semantic_scholar"
    min_interval = 1.2
    serialize_requests = True
    capabilities = (
        "search",
        "get_paper",
        "get_papers",
        "get_citations",
        "get_references",
        "filtered_search",
        "recommend",
        "resolve_fulltext",
        "provenance",
    )
    base_url = "https://api.semanticscholar.org/graph/v1"
    fields = (
        "paperId,externalIds,url,title,abstract,venue,year,referenceCount,"
        "citationCount,isOpenAccess,openAccessPdf,publicationTypes,publicationDate,authors"
        ",fieldsOfStudy,s2FieldsOfStudy"
    )
    recommendations_url = "https://api.semanticscholar.org/recommendations/v1"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.api_key = (
            os.getenv("SEMANTIC_SCHOLAR_API_KEY") or os.getenv("S2_API_KEY") or ""
        ).strip()

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key} if self.api_key else {}

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            self.name,
            bool(self.api_key),
            "SEMANTIC_SCHOLAR_API_KEY is not configured"
            if not self.api_key
            else "",
            self.capabilities,
        )

    @staticmethod
    def normalize(
        item: dict[str, Any],
        result: HttpResult | None = None,
        *,
        facet: str = "general",
        operation: str = "search",
    ) -> PaperRecord:
        external = item.get("externalIds") or {}
        oa = item.get("openAccessPdf") or {}
        fields_of_study = [str(value) for value in item.get("fieldsOfStudy") or []]
        fields_of_study.extend(
            str(value.get("category") or "")
            for value in item.get("s2FieldsOfStudy") or []
        )
        locations = []
        if oa.get("url"):
            locations.append(
                FullTextLocation(
                    url=str(oa["url"]),
                    kind="pdf",
                    source="semantic_scholar",
                    license=str(oa.get("license") or ""),
                    is_oa=True,
                )
            )
        record = PaperRecord(
            title=str(item.get("title") or ""),
            authors=[str(author.get("name") or "") for author in item.get("authors") or []],
            publication_date=str(item.get("publicationDate") or ""),
            year=_integer(item.get("year")),
            venue=str(item.get("venue") or ""),
            doi=normalize_doi(external.get("DOI")),
            pmid=str(external.get("PubMed") or ""),
            pmcid=str(external.get("PubMedCentral") or ""),
            openalex_id=str(external.get("OpenAlex") or ""),
            semantic_scholar_id=str(item.get("paperId") or ""),
            arxiv_id=str(external.get("ArXiv") or ""),
            url=str(item.get("url") or ""),
            abstract=str(item.get("abstract") or ""),
            publication_types=[str(value) for value in item.get("publicationTypes") or []],
            fields_of_study=fields_of_study,
            citation_count=_integer(item.get("citationCount")),
            reference_count=_integer(item.get("referenceCount")),
            is_open_access=bool(item.get("isOpenAccess")) if "isOpenAccess" in item else None,
            fulltext_locations=locations,
            facets=[facet],
            provenance=[
                _request_provenance(
                    "semantic_scholar",
                    result,
                    record_id=str(item.get("paperId") or ""),
                    operation=operation,
                )
            ],
            metrics_by_provider={
                "semantic_scholar": {
                    "citation_count": _integer(item.get("citationCount")),
                    "reference_count": _integer(item.get("referenceCount")),
                }
            },
        )
        record.mark_fields("semantic_scholar", NON_RETRACTION_FIELDS)
        return record

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        after_date: str | None = None,
        facet: str = "general",
        filters: SearchFilters | None = None,
        semantic: bool = False,
    ) -> list[PaperRecord]:
        del semantic
        options = filters or SearchFilters()
        params: dict[str, Any] = {
            "query": query,
            "limit": min(max(1, limit), 100),
            "fields": self.fields,
        }
        start = options.after_date or after_date
        if start or options.before_date:
            params["publicationDateOrYear"] = (
                f"{start or ''}:{options.before_date or ''}"
            )
        if options.fields_of_study:
            params["fieldsOfStudy"] = ",".join(options.fields_of_study)
        if options.publication_types:
            params["publicationTypes"] = ",".join(options.publication_types)
        if options.open_access_only:
            params["openAccessPdf"] = "true"
        if options.min_citation_count is not None:
            params["minCitationCount"] = max(0, options.min_citation_count)
        payload, result = self.client.get_json(
            f"{self.base_url}/paper/search", params=params, headers=self._headers()
        )
        return self._normalize_search_page(
            payload.get("data", []), lambda item: self.normalize(item, result, facet=facet),
            provider_total=payload.get("total"),
            has_more=True if payload.get("next") is not None else None,
        )

    def recommendation_status(self) -> ProviderStatus:
        return ProviderStatus(
            self.name,
            bool(self.api_key),
            "SEMANTIC_SCHOLAR_API_KEY is required for recommendations"
            if not self.api_key
            else "",
            ("recommend", "provenance"),
        )

    def recommend(
        self,
        positive_identifiers: Iterable[str],
        *,
        negative_identifiers: Iterable[str] = (),
        limit: int = 100,
    ) -> list[PaperRecord]:
        if not self.api_key:
            raise RuntimeError("Semantic Scholar recommendations require an API key.")
        positive = [
            self._paper_id(value)
            for value in positive_identifiers
            if str(value).strip()
        ]
        negative = [
            self._paper_id(value)
            for value in negative_identifiers
            if str(value).strip()
        ]
        if not positive:
            raise ValueError("At least one positive seed paper is required.")
        payload, result = self.client.post_json(
            f"{self.recommendations_url}/papers/",
            params={"fields": self.fields, "limit": min(max(1, limit), 500)},
            headers=self._headers(),
            json_body={
                "positivePaperIds": positive,
                "negativePaperIds": negative,
            },
        )
        records: list[PaperRecord] = []
        values = payload.get("recommendedPapers") or []
        for rank, item in enumerate(values, start=1):
            record = self.normalize(
                item,
                result,
                facet="seed-recommendation",
                operation="recommend",
            )
            record.metrics_by_provider.setdefault("semantic_scholar", {}).update(
                {
                    "recommendation_rank": rank,
                    "recommendation_count": len(values),
                    "recommendation_score": None,
                }
            )
            record.provenance[-1].notes.append(
                "The API returns an ordered list, not a numeric relevance score."
            )
            records.append(record)
        return records

    @staticmethod
    def _paper_id(identifier: str) -> str:
        doi = normalize_doi(identifier)
        if doi:
            return f"DOI:{doi}"
        text = str(identifier).strip()
        if text.upper().startswith(("PMID:", "PMCID:", "ARXIV:", "CORPUSID:")):
            return text
        if text.upper().startswith("PMC"):
            return f"PMCID:{text[3:]}"
        return text

    def get_paper(self, identifier: str) -> PaperRecord | None:
        paper_id = quote(self._paper_id(identifier), safe=":")
        payload, result = self.client.get_json(
            f"{self.base_url}/paper/{paper_id}",
            params={"fields": self.fields},
            headers=self._headers(),
        )
        return self.normalize(payload, result, facet="identifier", operation="get_paper")

    def get_papers(self, identifiers: Iterable[str]) -> list[PaperRecord]:
        paper_ids = [self._paper_id(value) for value in identifiers if str(value).strip()]
        records: list[PaperRecord] = []
        for offset in range(0, len(paper_ids), 500):
            batch = paper_ids[offset : offset + 500]
            payload, result = self.client.post_json(
                f"{self.base_url}/paper/batch",
                params={"fields": self.fields},
                headers=self._headers(),
                json_body={"ids": batch},
            )
            records.extend(
                self.normalize(item, result, facet="identifier", operation="get_papers")
                for item in payload or []
                if item
            )
        return records

    def _edges(self, identifier: str, edge: str, limit: int) -> list[PaperRecord]:
        paper_id = quote(self._paper_id(identifier), safe=":")
        payload, result = self.client.get_json(
            f"{self.base_url}/paper/{paper_id}/{edge}",
            params={"fields": self.fields, "limit": min(max(1, limit), 1000)},
            headers=self._headers(),
        )
        key = "citingPaper" if edge == "citations" else "citedPaper"
        facet = "citation" if edge == "citations" else "reference"
        records: list[PaperRecord] = []
        for item in payload.get("data") or []:
            paper = item.get(key) or {}
            record = self.normalize(paper, result, facet=facet, operation=f"get_{edge}")
            for index, context in enumerate(item.get("contexts") or []):
                record.evidence_chunks.append(
                    EvidenceChunk(
                        text=str(context),
                        source_type="citation-context",
                        locator=f"context-{index + 1}",
                        url=record.url,
                        extraction_method="semantic-scholar-context",
                    )
                )
            records.append(record)
        return records

    def get_citations(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        return self._edges(identifier, "citations", limit)

    def get_references(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        return self._edges(identifier, "references", limit)


class CrossrefProvider(Provider):
    name = "crossref"
    min_interval = 0.2
    capabilities = (
        "search",
        "filtered_search",
        "get_paper",
        "get_references",
        "resolve_fulltext",
        "provenance",
    )
    base_url = "https://api.crossref.org"

    def __init__(self, **kwargs: Any) -> None:
        self.mailto = os.getenv("CROSSREF_MAILTO", "").strip()
        super().__init__(**kwargs)

    def user_agent(self) -> str:
        suffix = f" (mailto:{self.mailto})" if getattr(self, "mailto", "") else ""
        return f"research-lookup-enhanced/0.1{suffix}"

    def _params(self, **values: Any) -> dict[str, Any]:
        params = {key: value for key, value in values.items() if value not in (None, "")}
        if self.mailto:
            params["mailto"] = self.mailto
        return params

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            self.name,
            True,
            "CROSSREF_MAILTO is not configured; polite identification is recommended"
            if not self.mailto
            else "",
            self.capabilities,
        )

    @staticmethod
    def _date(item: dict[str, Any]) -> str:
        for key in ("published", "published-online", "published-print", "issued"):
            parts = (item.get(key) or {}).get("date-parts") or []
            if parts and parts[0]:
                return "-".join(str(value).zfill(2) for value in parts[0])
        return ""

    @staticmethod
    def normalize(
        item: dict[str, Any],
        result: HttpResult | None = None,
        *,
        facet: str = "general",
        operation: str = "search",
    ) -> PaperRecord:
        authors = [
            " ".join(
                part for part in (str(author.get("given") or ""), str(author.get("family") or "")) if part
            )
            for author in item.get("author") or []
        ]
        licenses = [str(value.get("URL") or "") for value in item.get("license") or []]
        open_license = next(
            (value for value in licenses if "creativecommons.org" in value.lower()), ""
        )
        locations: list[FullTextLocation] = []
        for link in item.get("link") or []:
            url = str(link.get("URL") or "")
            if not url:
                continue
            content_type = str(link.get("content-type") or "").lower()
            locations.append(
                FullTextLocation(
                    url=url,
                    kind="pdf" if "pdf" in content_type else "html",
                    source="crossref",
                    license=open_license,
                    version=str(link.get("content-version") or ""),
                    is_oa=True if open_license else None,
                )
            )
        date = CrossrefProvider._date(item)
        doi = normalize_doi(item.get("DOI"))
        record = PaperRecord(
            title=_first(item.get("title")),
            authors=authors,
            publication_date=date,
            year=_year(date),
            venue=_first(item.get("container-title")),
            doi=doi,
            url=str(item.get("URL") or (f"https://doi.org/{doi}" if doi else "")),
            abstract=_strip_markup(item.get("abstract")),
            publication_types=[str(item.get("type") or "")],
            citation_count=_integer(item.get("is-referenced-by-count")),
            reference_count=_integer(item.get("references-count")),
            fulltext_locations=locations,
            facets=[facet],
            provenance=[
                _request_provenance(
                    "crossref", result, record_id=doi, operation=operation
                )
            ],
            metrics_by_provider={
                "crossref": {
                    "citation_count": _integer(item.get("is-referenced-by-count")),
                    "reference_count": _integer(item.get("references-count")),
                }
            },
        )
        record.mark_fields("crossref", NON_RETRACTION_FIELDS)
        record.metrics_by_provider["crossref"]["references"] = item.get("reference") or []
        return record

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        after_date: str | None = None,
        facet: str = "general",
        filters: SearchFilters | None = None,
        semantic: bool = False,
    ) -> list[PaperRecord]:
        del semantic
        options = filters or SearchFilters()
        filter_values: list[str] = []
        start = options.after_date or after_date
        if start:
            filter_values.append(f"from-pub-date:{start}")
        if options.before_date:
            filter_values.append(f"until-pub-date:{options.before_date}")
        if options.publication_types:
            filter_values.append("type:" + options.publication_types[0])
        payload, result = self.client.get_json(
            f"{self.base_url}/works",
            params=self._params(
                **{
                    "query.bibliographic": query,
                    "rows": min(max(1, limit), 1000),
                    "filter": ",".join(filter_values),
                }
            ),
        )
        message = payload.get("message") or {}
        return self._normalize_search_page(
            message.get("items", []), lambda item: self.normalize(item, result, facet=facet),
            provider_total=message.get("total-results"),
        )

    def get_paper(self, identifier: str) -> PaperRecord | None:
        doi = normalize_doi(identifier)
        if not doi:
            return None
        payload, result = self.client.get_json(
            f"{self.base_url}/works/{quote(doi, safe='')}",
            params=self._params(),
        )
        return self.normalize(
            payload.get("message") or {}, result, facet="identifier", operation="get_paper"
        )

    def get_references(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        seed = self.get_paper(identifier)
        if not seed:
            return []
        raw = seed.metrics_by_provider.get("crossref", {}).get("references") or []
        records: list[PaperRecord] = []
        for item in raw[:limit]:
            doi = normalize_doi(item.get("DOI"))
            title = str(item.get("article-title") or item.get("unstructured") or "")
            record = PaperRecord(
                title=title,
                doi=doi,
                year=_year(item.get("year")),
                venue=str(item.get("journal-title") or ""),
                url=f"https://doi.org/{doi}" if doi else "",
                facets=["reference"],
                provenance=[
                    Provenance(
                        provider="crossref",
                        operation="get_references",
                        provider_record_id=doi,
                        notes=["Reference metadata is limited to the depositing member's record."],
                    )
                ],
            )
            record.mark_fields("crossref", NON_RETRACTION_FIELDS)
            records.append(record)
        return records


class EuropePmcProvider(Provider):
    name = "europe_pmc"
    min_interval = 1.0
    capabilities = (
        "search",
        "get_paper",
        "get_citations",
        "get_references",
        "filtered_search",
        "resolve_fulltext",
        "provenance",
    )
    base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"

    @staticmethod
    def normalize(
        item: dict[str, Any],
        result: HttpResult | None = None,
        *,
        facet: str = "general",
        operation: str = "search",
    ) -> PaperRecord:
        authors = [
            str(author.get("fullName") or author.get("lastName") or "")
            for author in (item.get("authorList") or {}).get("author") or []
        ]
        if not authors and item.get("authorString"):
            authors = [part.strip() for part in str(item["authorString"]).split(",")]
        pmcid = str(item.get("pmcid") or "")
        is_oa = str(item.get("isOpenAccess") or "").upper() == "Y"
        locations: list[FullTextLocation] = []
        for value in (item.get("fullTextUrlList") or {}).get("fullTextUrl") or []:
            url = str(value.get("url") or "")
            if url:
                style = str(value.get("documentStyle") or "").lower()
                locations.append(
                    FullTextLocation(
                        url=url,
                        kind="pdf" if "pdf" in style else "html",
                        source="europe_pmc",
                        license=str(value.get("availability") or ""),
                        is_oa=is_oa,
                    )
                )
        if pmcid and is_oa:
            locations.append(
                FullTextLocation(
                    url=f"{EuropePmcProvider.base_url}/{quote(pmcid)}/fullTextXML",
                    kind="jats",
                    source="europe_pmc",
                    is_oa=True,
                )
            )
        provider_id = str(item.get("id") or item.get("pmid") or pmcid)
        record = PaperRecord(
            title=str(item.get("title") or ""),
            authors=authors,
            publication_date=str(item.get("firstPublicationDate") or ""),
            year=_integer(item.get("pubYear")),
            venue=str(item.get("journalTitle") or ""),
            doi=normalize_doi(item.get("doi")),
            pmid=str(item.get("pmid") or ""),
            pmcid=pmcid,
            url=(f"https://europepmc.org/article/{item.get('source') or 'MED'}/{provider_id}" if provider_id else ""),
            abstract=str(item.get("abstractText") or ""),
            publication_types=[
                str(value)
                for value in (item.get("pubTypeList") or {}).get("pubType") or []
            ],
            citation_count=_integer(item.get("citedByCount")),
            is_open_access=is_oa if "isOpenAccess" in item else None,
            fulltext_locations=locations,
            facets=[facet],
            provenance=[
                _request_provenance(
                    "europe_pmc", result, record_id=provider_id, operation=operation
                )
            ],
            metrics_by_provider={
                "europe_pmc": {"citation_count": _integer(item.get("citedByCount"))}
            },
        )
        record.mark_fields("europe_pmc", NON_RETRACTION_FIELDS)
        return record

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        after_date: str | None = None,
        facet: str = "general",
        filters: SearchFilters | None = None,
        semantic: bool = False,
    ) -> list[PaperRecord]:
        del semantic
        options = filters or SearchFilters()
        search_query = query
        start = options.after_date or after_date
        clauses = [f"({query})"]
        if start or options.before_date:
            clauses.append(
                f"FIRST_PDATE:[{start or '1000-01-01'} TO "
                f"{options.before_date or '3000-12-31'}]"
            )
        if options.open_access_only:
            clauses.append("OPEN_ACCESS:Y")
        search_query = " AND ".join(clauses)
        payload, result = self.client.get_json(
            f"{self.base_url}/search",
            params={
                "query": search_query,
                "format": "json",
                "resultType": "core",
                "pageSize": min(max(1, limit), 1000),
            },
        )
        return self._normalize_search_page(
            (payload.get("resultList") or {}).get("result", []),
            lambda item: self.normalize(item, result, facet=facet),
            provider_total=payload.get("hitCount"),
        )

    @staticmethod
    def _query_for_identifier(identifier: str) -> str:
        doi = normalize_doi(identifier)
        if doi:
            return f'DOI:"{doi}"'
        text = str(identifier).strip()
        if text.upper().startswith("PMC"):
            return f"PMCID:{text.upper()}"
        if text.upper().startswith("PMID:"):
            text = text.split(":", 1)[1]
        return f"EXT_ID:{text}"

    def get_paper(self, identifier: str) -> PaperRecord | None:
        records = self.search(
            self._query_for_identifier(identifier), limit=1, facet="identifier"
        )
        if records:
            records[0].provenance[-1].operation = "get_paper"
        return records[0] if records else None

    def _edges(self, identifier: str, edge: str, limit: int) -> list[PaperRecord]:
        seed = self.get_paper(identifier)
        if not seed:
            return []
        source = "MED" if seed.pmid else "PMC"
        item_id = seed.pmid or seed.pmcid
        if not item_id:
            return []
        payload, result = self.client.get_json(
            f"{self.base_url}/{source}/{quote(item_id)}/{edge}",
            params={"format": "json", "pageSize": min(max(1, limit), 1000)},
        )
        list_key = "citationList" if edge == "citations" else "referenceList"
        item_key = "citation" if edge == "citations" else "reference"
        values = (payload.get(list_key) or {}).get(item_key) or []
        facet = "citation" if edge == "citations" else "reference"
        return [
            self.normalize(item, result, facet=facet, operation=f"get_{edge}")
            for item in values
        ]

    def get_citations(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        return self._edges(identifier, "citations", limit)

    def get_references(self, identifier: str, *, limit: int = 100) -> list[PaperRecord]:
        return self._edges(identifier, "references", limit)


class UnpaywallProvider(Provider):
    name = "unpaywall"
    min_interval = 0.05
    capabilities = ("get_paper", "resolve_fulltext", "provenance")
    base_url = "https://api.unpaywall.org/v2"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.email = os.getenv("UNPAYWALL_EMAIL", "").strip()

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            self.name,
            bool(self.email),
            "UNPAYWALL_EMAIL is not configured" if not self.email else "",
            self.capabilities,
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 20,
        after_date: str | None = None,
        facet: str = "general",
        filters: SearchFilters | None = None,
        semantic: bool = False,
    ) -> list[PaperRecord]:
        del query, limit, after_date, facet, filters, semantic
        return []

    @staticmethod
    def normalize(
        item: dict[str, Any], result: HttpResult | None = None
    ) -> PaperRecord:
        location = item.get("best_oa_location") or {}
        locations: list[FullTextLocation] = []
        for url, kind in (
            (location.get("url_for_pdf"), "pdf"),
            (location.get("url_for_landing_page"), "html"),
            (location.get("url"), "landing"),
        ):
            if url:
                locations.append(
                    FullTextLocation(
                        url=str(url),
                        kind=kind,
                        source="unpaywall",
                        license=str(location.get("license") or ""),
                        host_type=str(location.get("host_type") or ""),
                        version=str(location.get("version") or ""),
                        is_oa=bool(item.get("is_oa")),
                    )
                )
        authors = [
            str(author.get("raw_author_name") or "")
            for author in item.get("z_authors") or []
        ]
        record = PaperRecord(
            title=str(item.get("title") or ""),
            authors=authors,
            publication_date=str(item.get("published_date") or ""),
            year=_integer(item.get("year")),
            venue=str(item.get("journal_name") or ""),
            doi=normalize_doi(item.get("doi")),
            url=str(item.get("doi_url") or ""),
            publication_types=[str(item.get("genre") or "")],
            is_open_access=bool(item.get("is_oa")),
            fulltext_locations=locations,
            facets=["oa-resolution"],
            provenance=[
                _request_provenance(
                    "unpaywall",
                    result,
                    record_id=normalize_doi(item.get("doi")),
                    operation="resolve_fulltext",
                    notes=[f"oa_status={item.get('oa_status') or 'unknown'}"],
                )
            ],
        )
        fields = tuple(
            name for name in NON_RETRACTION_FIELDS if name != "is_open_access"
        ) + (("is_open_access",) if "is_oa" in item else ())
        record.mark_fields("unpaywall", fields)
        return record

    def get_paper(self, identifier: str) -> PaperRecord | None:
        if not self.email:
            return None
        doi = normalize_doi(identifier)
        if not doi:
            return None
        payload, result = self.client.get_json(
            f"{self.base_url}/{quote(doi, safe='')}", params={"email": self.email}
        )
        return self.normalize(payload, result)

    def resolve_fulltext(self, record: PaperRecord) -> list[FullTextLocation]:
        enriched = self.get_paper(record.doi) if record.doi else None
        return enriched.fulltext_locations if enriched else []


class EasyScholarEnricher:
    """Optional venue-level rank enrichment; never used for paper discovery."""

    name = "easy_scholar"
    endpoint = "https://www.easyscholar.cc/open/getPublicationRank"

    def __init__(
        self,
        *,
        cache_dir: str | Path,
        client: HttpClient | None = None,
    ) -> None:
        self.secret_key = (
            os.getenv("EASYSCHOLAR_SECRET_KEY")
            or os.getenv("EASYSCHOLAR_API_KEY")
            or ""
        ).strip()
        self.client = client or HttpClient(
            self.name,
            cache_dir=cache_dir,
            min_interval=1.0,
            user_agent="research-lookup-enhanced/0.1",
            serialize_requests=True,
            serialization_key=self.name,
        )

    def status(self) -> ProviderStatus:
        return ProviderStatus(
            self.name,
            bool(self.secret_key),
            "EASYSCHOLAR_SECRET_KEY is not configured" if not self.secret_key else "",
            ("journal_enrichment", "provenance"),
        )

    def lookup_venue(self, venue: str) -> tuple[dict[str, Any], Provenance] | None:
        if not self.secret_key or not venue.strip():
            return None
        payload, result = self.client.get_json(
            self.endpoint,
            params={"secretKey": self.secret_key, "publicationName": venue.strip()},
            use_cache=False,
        )
        try:
            code = int(payload.get("code") or 0)
        except (TypeError, ValueError):
            code = 0
        if code != 200:
            return None
        data = payload.get("data") or {}
        official = data.get("officialRank") or {}
        metrics = {
            "selected": official.get("select") or {},
            "all": official.get("all") or {},
            "custom_rank": data.get("customRank") or {},
        }
        provenance = _request_provenance(
            self.name,
            result,
            record_id=venue,
            operation="journal_enrichment",
            notes=["Venue-level metrics only; not evidence of paper quality."],
        )
        return metrics, provenance

    def enrich(self, records: list[PaperRecord]) -> list[PaperRecord]:
        cache: dict[str, tuple[dict[str, Any], Provenance] | None] = {}
        for record in records:
            key = record.venue.casefold().strip()
            if not key:
                continue
            if key not in cache:
                cache[key] = self.lookup_venue(record.venue)
            result = cache[key]
            if not result:
                continue
            metrics, provenance = result
            record.journal_metrics[self.name] = metrics
            record.provenance.append(provenance)
        return records


PROVIDER_TYPES: dict[str, type[Provider]] = {
    "openalex": OpenAlexProvider,
    "semantic_scholar": SemanticScholarProvider,
    "semantic-scholar": SemanticScholarProvider,
    "crossref": CrossrefProvider,
    "europe_pmc": EuropePmcProvider,
    "europe-pmc": EuropePmcProvider,
    "unpaywall": UnpaywallProvider,
}


def build_provider(name: str, *, cache_dir: str | Path) -> Provider:
    normalized = name.strip().lower()
    provider_type = PROVIDER_TYPES.get(normalized)
    if not provider_type:
        raise ValueError(f"Unknown provider: {name}")
    return provider_type(cache_dir=cache_dir)


def unique_locations(locations: Iterable[FullTextLocation]) -> list[FullTextLocation]:
    output: list[FullTextLocation] = []
    seen: set[str] = set()
    for location in locations:
        key = canonicalize_url(location.url)
        if key and key not in seen:
            seen.add(key)
            output.append(location)
    return output
