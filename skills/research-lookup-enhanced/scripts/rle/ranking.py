"""Deterministic, explainable paper relevance ranking with optional backends."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Protocol

from .models import PaperRecord, normalize_title


TOKEN_RE = re.compile(r"[a-z0-9]+|[\u4e00-\u9fff]", re.IGNORECASE)
STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "do",
    "does",
    "for",
    "from",
    "how",
    "in",
    "is",
    "of",
    "on",
    "or",
    "paper",
    "papers",
    "research",
    "study",
    "the",
    "to",
    "using",
    "what",
    "which",
    "with",
}
METHOD_LEXICON = {
    "assay",
    "benchmark",
    "case control",
    "cohort",
    "cross sectional",
    "double blind",
    "flow cytometry",
    "in vivo",
    "in vitro",
    "meta analysis",
    "microscopy",
    "randomized",
    "randomised",
    "regression",
    "rna seq",
    "sequencing",
    "simulation",
    "systematic review",
    "transformer",
}
DEFAULT_WEIGHTS: dict[str, float] = {
    "title_match": 0.32,
    "abstract_match": 0.27,
    "method_match": 0.13,
    "field_match": 0.11,
    "year_fit": 0.06,
    "semantic_similarity": 0.05,
    "seed_graph_proximity": 0.02,
    "evidence_availability": 0.02,
    "normalized_citation_signal": 0.02,
}


def record_key(record: PaperRecord) -> str:
    """Return a deterministic identifier suitable for backend score maps."""
    for prefix, value in (
        ("doi", record.doi),
        ("pmid", record.pmid),
        ("pmcid", record.pmcid),
        ("openalex", record.openalex_id),
        ("s2", record.semantic_scholar_id),
        ("arxiv", record.arxiv_id),
    ):
        if value:
            return f"{prefix}:{str(value).casefold()}"
    authors = "|".join(value.casefold() for value in record.authors[:2])
    return f"title:{normalize_title(record.title)}|authors:{authors}"


def is_preprint(record: PaperRecord) -> bool:
    values = " ".join(
        [
            record.url,
            record.venue,
            *record.publication_types,
        ]
    ).casefold()
    return bool(record.arxiv_id) or any(
        marker in values
        for marker in ("preprint", "arxiv.org", "biorxiv.org", "medrxiv.org")
    )


def _tokens(value: str | Iterable[str]) -> set[str]:
    text = value if isinstance(value, str) else " ".join(str(item) for item in value)
    return {
        token.casefold()
        for token in TOKEN_RE.findall(text)
        if token.casefold() not in STOPWORDS
    }


def _text_match(needles: set[str], text: str) -> float:
    if not needles:
        return 0.5
    haystack = _tokens(text)
    if not haystack:
        return 0.0
    intersection = needles.intersection(haystack)
    coverage = len(intersection) / len(needles)
    precision = len(intersection) / len(haystack)
    return min(1.0, 0.85 * coverage + 0.15 * precision)


def _minmax(values: Mapping[str, float], *, reverse: bool = False) -> dict[str, float]:
    if not values:
        return {}
    low = min(values.values())
    high = max(values.values())
    if math.isclose(low, high):
        return {key: 1.0 for key in values}
    output = {
        key: (value - low) / (high - low)
        for key, value in values.items()
    }
    if reverse:
        return {key: 1.0 - value for key, value in output.items()}
    return output


def _context_values(
    context: Mapping[str, Any],
    *names: str,
) -> list[str]:
    values: list[str] = []
    for name in names:
        raw = context.get(name)
        if isinstance(raw, str):
            values.extend(value.strip() for value in re.split(r"[,;]", raw) if value.strip())
        elif isinstance(raw, (list, tuple, set)):
            values.extend(str(value).strip() for value in raw if str(value).strip())
    return values


@dataclass(frozen=True, slots=True)
class ResearchContext:
    question: str
    methods: tuple[str, ...] = ()
    fields: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    after_year: int | None = None
    before_year: int | None = None
    target_year: int | None = None

    @classmethod
    def from_input(
        cls,
        question: str | Mapping[str, Any],
        context: Mapping[str, Any] | None = None,
    ) -> "ResearchContext":
        if isinstance(question, Mapping):
            merged = dict(question)
            text = str(
                merged.get("question")
                or merged.get("research_question")
                or merged.get("query")
                or ""
            )
        else:
            merged = {}
            text = str(question)
        merged.update(context or {})
        methods = _context_values(merged, "methods", "method", "study_designs")
        lowered = text.casefold()
        methods.extend(term for term in METHOD_LEXICON if term in lowered)
        fields = _context_values(
            merged,
            "fields",
            "field",
            "fields_of_study",
            "domains",
        )
        keywords = _context_values(merged, "keywords", "concepts", "population", "outcomes")

        def year_value(*names: str) -> int | None:
            for name in names:
                value = merged.get(name)
                match = re.search(r"\b(19\d{2}|20\d{2})\b", str(value or ""))
                if match:
                    return int(match.group(1))
            return None

        after_year = year_value("after_year", "year_from", "after_date")
        before_year = year_value("before_year", "year_to", "before_date")
        target_year = year_value("target_year")
        if after_year is None:
            match = re.search(r"\b(?:since|after|from)\s+(19\d{2}|20\d{2})\b", text, re.I)
            after_year = int(match.group(1)) if match else None
        if before_year is None:
            match = re.search(r"\b(?:before|until|through)\s+(19\d{2}|20\d{2})\b", text, re.I)
            before_year = int(match.group(1)) if match else None
        return cls(
            question=text,
            methods=tuple(dict.fromkeys(methods)),
            fields=tuple(dict.fromkeys(fields)),
            keywords=tuple(dict.fromkeys(keywords)),
            after_year=after_year,
            before_year=before_year,
            target_year=target_year,
        )


class SemanticBackend(Protocol):
    """Optional semantic backend returning raw, backend-local scores."""

    name: str

    def score(
        self,
        context: ResearchContext,
        records: list[PaperRecord],
    ) -> Mapping[str, float]: ...


class Specter2Backend:
    """Lazy SPECTER2 adapter; never downloads models unless explicitly allowed."""

    name = "specter2"

    def __init__(
        self,
        *,
        base_model: str = "allenai/specter2_base",
        query_adapter: str = "allenai/specter2_adhoc_query",
        paper_adapter: str = "allenai/specter2",
        allow_model_download: bool = False,
    ) -> None:
        self.base_model = base_model
        self.query_adapter = query_adapter
        self.paper_adapter = paper_adapter
        self.allow_model_download = allow_model_download

    def score(
        self,
        context: ResearchContext,
        records: list[PaperRecord],
    ) -> Mapping[str, float]:
        try:
            import torch
            from adapters import AutoAdapterModel
            from transformers import AutoTokenizer
        except ImportError as exc:
            raise RuntimeError(
                "SPECTER2 requires optional torch, transformers, and adapters packages."
            ) from exc

        local_only = not self.allow_model_download
        tokenizer = AutoTokenizer.from_pretrained(
            self.base_model,
            local_files_only=local_only,
        )
        model = AutoAdapterModel.from_pretrained(
            self.base_model,
            local_files_only=local_only,
        )
        model.eval()

        def embed(texts: list[str], adapter: str, alias: str) -> Any:
            model.load_adapter(
                adapter,
                source="hf",
                load_as=alias,
                set_active=True,
                local_files_only=local_only,
            )
            encoded = tokenizer(
                texts,
                padding=True,
                truncation=True,
                return_tensors="pt",
                return_token_type_ids=False,
                max_length=512,
            )
            with torch.no_grad():
                values = model(**encoded).last_hidden_state[:, 0, :]
            return torch.nn.functional.normalize(values, p=2, dim=1)

        query_embedding = embed(
            [context.question],
            self.query_adapter,
            "rle_adhoc_query",
        )
        paper_texts = [
            f"{record.title}{tokenizer.sep_token}{record.abstract or ''}"
            for record in records
        ]
        paper_embeddings = embed(
            paper_texts,
            self.paper_adapter,
            "rle_proximity",
        )
        similarities = (paper_embeddings @ query_embedding.T).squeeze(1).tolist()
        return {
            record_key(record): float(value)
            for record, value in zip(records, similarities)
        }


@dataclass(slots=True)
class RankingComponent:
    score: float
    weight: float
    reason: str
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "score": round(self.score, 6),
            "weight": round(self.weight, 6),
            "reason": self.reason,
        }
        if self.details:
            payload["details"] = self.details
        return payload


@dataclass(slots=True)
class RankingResult:
    record: PaperRecord
    rank: int
    total_score: float
    components: dict[str, RankingComponent]
    preprint: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "total_score": round(self.total_score, 6),
            "preprint": self.preprint,
            "components": {
                name: component.to_dict()
                for name, component in self.components.items()
            },
        }


@dataclass(slots=True)
class RankingReport:
    ranked: list[RankingResult]
    excluded: list[dict[str, str]]
    backend_errors: list[dict[str, str]]


def _year_score(record: PaperRecord, context: ResearchContext) -> tuple[float, str]:
    constrained = any(
        value is not None
        for value in (context.after_year, context.before_year, context.target_year)
    )
    if not constrained:
        return 0.5, "No year preference was supplied; this component is neutral."
    if record.year is None:
        return 0.5, "Publication year is missing; used a neutral score."
    if context.target_year is not None:
        distance = abs(record.year - context.target_year)
        return 1.0 / (1.0 + distance), f"Year is {distance} from target {context.target_year}."
    lower = context.after_year if context.after_year is not None else record.year
    upper = context.before_year if context.before_year is not None else record.year
    if lower <= record.year <= upper:
        return 1.0, f"Year {record.year} is inside the requested range."
    distance = lower - record.year if record.year < lower else record.year - upper
    return 1.0 / (1.0 + distance), f"Year {record.year} is {distance} year(s) outside the requested range."


def _evidence_score(record: PaperRecord) -> tuple[float, str]:
    score = 0.0
    signals: list[str] = []
    if record.abstract:
        score += 0.45
        signals.append("abstract")
    if record.evidence_chunks:
        score += 0.35
        signals.append("extracted evidence")
    if any(
        (
            record.doi,
            record.pmid,
            record.pmcid,
            record.openalex_id,
            record.semantic_scholar_id,
            record.arxiv_id,
        )
    ):
        score += 0.10
        signals.append("stable identifier")
    if record.is_open_access is True or any(
        location.is_oa is True for location in record.fulltext_locations
    ):
        score += 0.10
        signals.append("open-access location")
    return min(1.0, score), (
        "Available: " + ", ".join(signals) + "."
        if signals
        else "No abstract, extracted evidence, stable identifier, or OA location is available."
    )


def _provider_signals(
    records: list[PaperRecord],
) -> tuple[
    dict[str, float],
    dict[str, dict[str, Any]],
    dict[str, float],
    dict[str, dict[str, Any]],
]:
    semantic_values: dict[str, dict[str, float]] = {}
    recommendation_values: dict[str, dict[str, float]] = {}
    raw_semantic: dict[str, dict[str, Any]] = {}
    raw_recommendation: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record_key(record)
        for provider, metrics in record.metrics_by_provider.items():
            raw_score = metrics.get("relevance_score")
            if (
                raw_score not in (None, "")
                and metrics.get("search_mode") == "semantic"
            ):
                semantic_values.setdefault(provider, {})[key] = float(raw_score)
                raw_semantic.setdefault(key, {})[provider] = {
                    "raw_score": float(raw_score),
                    "search_mode": metrics.get("search_mode") or "provider-search",
                }
            rank = metrics.get("recommendation_rank")
            if rank not in (None, ""):
                recommendation_values.setdefault(provider, {})[key] = float(rank)
                raw_recommendation.setdefault(key, {})[provider] = {
                    "raw_rank": int(rank),
                    "native_score": metrics.get("recommendation_score"),
                }

    semantic_normalized: dict[str, list[float]] = {}
    for provider, values in semantic_values.items():
        for key, value in _minmax(values).items():
            semantic_normalized.setdefault(key, []).append(value)
            raw_semantic[key][provider]["normalized"] = round(value, 6)
    recommendation_normalized: dict[str, list[float]] = {}
    for provider, values in recommendation_values.items():
        for key, value in _minmax(values, reverse=True).items():
            recommendation_normalized.setdefault(key, []).append(value)
            raw_recommendation[key][provider]["normalized"] = round(value, 6)
    return (
        {
            key: sum(values) / len(values)
            for key, values in semantic_normalized.items()
        },
        raw_semantic,
        {
            key: sum(values) / len(values)
            for key, values in recommendation_normalized.items()
        },
        raw_recommendation,
    )


def _citation_signals(
    records: list[PaperRecord],
) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    known_years = [record.year for record in records if record.year is not None]
    reference_year = max(known_years) if known_years else 0
    provider_values: dict[str, dict[str, float]] = {}
    details: dict[str, dict[str, Any]] = {}
    for record in records:
        key = record_key(record)
        age = max(0, reference_year - record.year) + 1 if record.year else 1
        for provider, metrics in record.metrics_by_provider.items():
            count = metrics.get("citation_count")
            if count in (None, ""):
                continue
            try:
                numeric = max(0.0, float(count))
            except (TypeError, ValueError):
                continue
            age_adjusted = math.log1p(numeric) / math.sqrt(age)
            provider_values.setdefault(provider, {})[key] = age_adjusted
            details.setdefault(key, {})[provider] = {
                "raw_count": int(numeric),
                "paper_age": age,
                "age_adjusted": round(age_adjusted, 6),
            }
    normalized: dict[str, list[float]] = {}
    for provider, values in provider_values.items():
        for key, value in _minmax(values).items():
            normalized.setdefault(key, []).append(value)
            details[key][provider]["normalized_within_provider"] = round(value, 6)
    return (
        {
            key: sum(values) / len(values)
            for key, values in normalized.items()
        },
        details,
    )


def rank_papers(
    question: str | Mapping[str, Any],
    records: Iterable[PaperRecord],
    *,
    context: Mapping[str, Any] | None = None,
    semantic_backends: Iterable[SemanticBackend] = (),
    weights: Mapping[str, float] | None = None,
) -> RankingReport:
    """Rank non-retracted records and attach deterministic explanations."""
    research = ResearchContext.from_input(question, context)
    configured = dict(DEFAULT_WEIGHTS)
    if weights:
        unknown = set(weights).difference(DEFAULT_WEIGHTS)
        if unknown:
            raise ValueError(f"Unknown ranking component(s): {', '.join(sorted(unknown))}")
        configured.update({name: max(0.0, float(value)) for name, value in weights.items()})
    total_weight = sum(configured.values())
    if total_weight <= 0:
        raise ValueError("At least one ranking weight must be positive.")
    configured = {name: value / total_weight for name, value in configured.items()}

    values = list(records)
    eligible = [record for record in values if not record.is_retracted]
    excluded = [
        {"record_key": record_key(record), "reason": "retracted_or_withdrawn"}
        for record in values
        if record.is_retracted
    ]
    backend_errors: list[dict[str, str]] = []

    provider_semantic, provider_semantic_raw, graph_scores, graph_raw = (
        _provider_signals(eligible)
    )
    backend_scores: dict[str, list[float]] = {}
    backend_raw: dict[str, dict[str, Any]] = {}
    for backend in semantic_backends:
        try:
            raw = {
                str(key): float(value)
                for key, value in backend.score(research, eligible).items()
            }
        except Exception as exc:
            backend_errors.append({"backend": backend.name, "error": str(exc)})
            continue
        for key, value in _minmax(raw).items():
            backend_scores.setdefault(key, []).append(value)
            backend_raw.setdefault(key, {})[backend.name] = {
                "raw_score": raw[key],
                "normalized": round(value, 6),
            }
    semantic_scores: dict[str, float] = {}
    semantic_details: dict[str, dict[str, Any]] = {}
    for record in eligible:
        key = record_key(record)
        candidates: list[float] = []
        details: dict[str, Any] = {}
        if key in provider_semantic:
            candidates.append(provider_semantic[key])
            details["provider_search"] = provider_semantic_raw[key]
        if key in backend_scores:
            candidates.extend(backend_scores[key])
            details["semantic_backends"] = backend_raw[key]
        if candidates:
            semantic_scores[key] = sum(candidates) / len(candidates)
            semantic_details[key] = details

    citation_scores, citation_details = _citation_signals(eligible)
    query_terms = _tokens(
        [
            research.question,
            *research.keywords,
        ]
    )
    method_terms = _tokens(research.methods)
    field_terms = _tokens(research.fields)

    provisional: list[RankingResult] = []
    for record in eligible:
        key = record_key(record)
        title_score = _text_match(query_terms, record.title)
        abstract_score = (
            _text_match(query_terms, record.abstract) if record.abstract else 0.5
        )
        method_text = " ".join(
            [record.title, record.abstract, *record.publication_types, *record.keywords]
        )
        method_score = _text_match(method_terms, method_text) if method_terms else 0.5
        field_text = " ".join(
            [*record.fields_of_study, *record.keywords, record.title, record.abstract]
        )
        field_score = _text_match(field_terms, field_text) if field_terms else 0.5
        year_score, year_reason = _year_score(record, research)
        evidence_score, evidence_reason = _evidence_score(record)
        semantic_score = semantic_scores.get(key, 0.5)
        graph_score = graph_scores.get(key, 0.5)
        citation_score = citation_scores.get(key, 0.0)

        components = {
            "title_match": RankingComponent(
                title_score,
                configured["title_match"],
                f"Matched {len(query_terms.intersection(_tokens(record.title)))} of "
                f"{len(query_terms)} query term(s) in the title.",
            ),
            "abstract_match": RankingComponent(
                abstract_score,
                configured["abstract_match"],
                (
                    f"Matched {len(query_terms.intersection(_tokens(record.abstract)))} of "
                    f"{len(query_terms)} query term(s) in the abstract."
                    if record.abstract
                    else "Abstract is missing; used a neutral score."
                ),
            ),
            "method_match": RankingComponent(
                method_score,
                configured["method_match"],
                (
                    f"Compared requested method terms ({', '.join(research.methods)}) "
                    "with title, abstract, type, and keywords."
                    if method_terms
                    else "No method constraint was supplied or detected; this component is neutral."
                ),
            ),
            "field_match": RankingComponent(
                field_score,
                configured["field_match"],
                (
                    f"Compared requested field terms ({', '.join(research.fields)}) "
                    "with provider field/topic metadata and paper text."
                    if field_terms
                    else "No structured field constraint was supplied; this component is neutral."
                ),
            ),
            "year_fit": RankingComponent(
                year_score,
                configured["year_fit"],
                year_reason,
            ),
            "semantic_similarity": RankingComponent(
                semantic_score,
                configured["semantic_similarity"],
                (
                    "Normalized semantic scores within each backend before combining."
                    if key in semantic_scores
                    else "No semantic backend score is available; used a neutral score."
                ),
                semantic_details.get(key, {}),
            ),
            "seed_graph_proximity": RankingComponent(
                graph_score,
                configured["seed_graph_proximity"],
                (
                    "Converted provider recommendation order to a provider-local normalized signal."
                    if key in graph_scores
                    else "No seed-paper recommendation signal is available; used a neutral score."
                ),
                graph_raw.get(key, {}),
            ),
            "evidence_availability": RankingComponent(
                evidence_score,
                configured["evidence_availability"],
                evidence_reason,
            ),
            "normalized_citation_signal": RankingComponent(
                citation_score,
                configured["normalized_citation_signal"],
                (
                    "Citation counts were age-adjusted and normalized separately within each provider."
                    if key in citation_scores
                    else "No provider-specific citation count is available."
                ),
                citation_details.get(key, {}),
            ),
        }
        total = sum(
            component.score * component.weight
            for component in components.values()
        )
        provisional.append(
            RankingResult(
                record=record,
                rank=0,
                total_score=total,
                components=components,
                preprint=is_preprint(record),
            )
        )

    provisional.sort(
        key=lambda item: (
            -round(item.total_score, 12),
            record_key(item.record),
        )
    )
    for rank, result in enumerate(provisional, start=1):
        result.rank = rank
        result.record.ranking = result.to_dict()
    return RankingReport(
        ranked=provisional,
        excluded=excluded,
        backend_errors=backend_errors,
    )
