"""Deterministic, auditable query planning without an LLM dependency."""

from __future__ import annotations

import re
import unicodedata
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Mapping

from .models import normalize_doi


DEFAULT_PROVIDER_BUDGETS: dict[str, int] = {
    "openalex": 4,
    "crossref": 3,
    "semantic_scholar": 2,
    "europe_pmc": 3,
}
MAX_QUERY_VARIANTS = 6
MAX_ENGLISH_QUERY_LENGTH = 512

ENGLISH_STOPWORDS = {
    "about",
    "after",
    "among",
    "and",
    "are",
    "before",
    "between",
    "does",
    "effect",
    "effects",
    "for",
    "from",
    "how",
    "into",
    "paper",
    "papers",
    "research",
    "study",
    "the",
    "their",
    "using",
    "what",
    "when",
    "where",
    "which",
    "with",
}
CHINESE_FUNCTION_WORDS = (
    "近年来",
    "近几年",
    "请问",
    "如何",
    "是否",
    "什么",
    "哪些",
    "为什么",
    "以及",
    "及其",
    "中的",
    "用于",
    "对于",
    "关于",
    "研究",
    "影响",
)

# This is term expansion, not general translation. Unmatched text is never discarded.
ZH_EN_TERMS: tuple[tuple[str, str], ...] = (
    ("人工智能", "artificial intelligence"),
    ("机器学习", "machine learning"),
    ("深度学习", "deep learning"),
    ("神经网络", "neural network"),
    ("大语言模型", "large language model"),
    ("生物医学", "biomedicine"),
    ("生命科学", "life science"),
    ("帕金森病", "Parkinson disease"),
    ("阿尔茨海默病", "Alzheimer disease"),
    ("心血管", "cardiovascular"),
    ("临床试验", "clinical trial"),
    ("随机对照试验", "randomized controlled trial"),
    ("系统综述", "systematic review"),
    ("荟萃分析", "meta-analysis"),
    ("石墨烯", "graphene"),
    ("二维材料", "two-dimensional materials"),
    ("柔性传感器", "flexible sensor"),
    ("传感器", "sensor"),
    ("步态监测", "gait monitoring"),
    ("癌症", "cancer"),
    ("肿瘤", "tumor"),
    ("诊断", "diagnosis"),
    ("治疗", "treatment"),
    ("预后", "prognosis"),
    ("预测", "prediction"),
    ("筛查", "screening"),
    ("机制", "mechanism"),
    ("方法", "method"),
    ("模型", "model"),
    ("蛋白质", "protein"),
    ("基因", "gene"),
    ("基因组", "genome"),
    ("药物", "drug"),
    ("材料", "materials"),
    ("电池", "battery"),
    ("能源", "energy"),
    ("环境", "environment"),
    ("气候", "climate"),
    ("综述", "review"),
    ("最新", "recent"),
    ("近期", "recent"),
    ("矛盾证据", "contradictory evidence"),
)

CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "methods": (
        "assay",
        "benchmark",
        "cohort",
        "deep learning",
        "machine learning",
        "meta-analysis",
        "microscopy",
        "randomized",
        "regression",
        "sequencing",
        "simulation",
        "systematic review",
        "transformer",
        "方法",
        "模型",
        "测量",
        "实验",
        "临床试验",
        "随机对照",
        "系统综述",
        "荟萃分析",
    ),
    "materials_objects": (
        "battery",
        "cell",
        "cohort",
        "graphene",
        "material",
        "patient",
        "polymer",
        "protein",
        "sensor",
        "tissue",
        "tumor",
        "石墨烯",
        "二维材料",
        "材料",
        "患者",
        "细胞",
        "蛋白质",
        "传感器",
        "肿瘤",
        "电池",
    ),
    "tasks": (
        "classification",
        "detection",
        "diagnosis",
        "forecasting",
        "generation",
        "monitoring",
        "prediction",
        "screening",
        "诊断",
        "检测",
        "分类",
        "监测",
        "生成",
        "筛查",
        "预测",
    ),
    "outcomes": (
        "accuracy",
        "adverse",
        "efficacy",
        "mortality",
        "outcome",
        "performance",
        "prognosis",
        "safety",
        "survival",
        "不良反应",
        "安全性",
        "疗效",
        "生存",
        "性能",
        "预后",
        "准确率",
        "结局",
    ),
}

BIOMEDICAL_TERMS = {
    "alzheimer",
    "biomedical",
    "cancer",
    "cardiovascular",
    "cell",
    "clinical",
    "disease",
    "drug",
    "gene",
    "genome",
    "health",
    "medicine",
    "patient",
    "parkinson",
    "protein",
    "therapy",
    "tumor",
    "临床",
    "医学",
    "帕金森病",
    "患者",
    "疾病",
    "癌症",
    "细胞",
    "肿瘤",
    "药物",
    "蛋白质",
    "诊断",
    "治疗",
}

INTENT_TERMS: dict[str, tuple[str, ...]] = {
    "recent": ("latest", "newest", "recent", "近年", "近期", "最新"),
    "review": (
        "evidence synthesis",
        "meta-analysis",
        "review",
        "systematic review",
        "综述",
        "荟萃分析",
        "系统评价",
        "系统综述",
    ),
    "seminal": (
        "classic",
        "foundational",
        "landmark",
        "seminal",
        "奠基",
        "经典",
        "里程碑",
    ),
    "methods": (
        "benchmark",
        "method",
        "methodology",
        "protocol",
        "validation",
        "方法",
        "方案",
        "验证",
    ),
    "contradictory-evidence": (
        "conflicting",
        "contradictory",
        "negative result",
        "null result",
        "replication",
        "不一致",
        "否定结果",
        "矛盾",
        "重复验证",
    ),
}


@dataclass(frozen=True, slots=True)
class QueryVariant:
    variant_id: str
    query: str
    intent: str
    language: str
    source: str
    provider_hints: tuple[str, ...] = ()
    preserves_original: bool = False


@dataclass(slots=True)
class QueryPlan:
    original_query: str
    query_language: str
    normalized_query: str
    identifiers: dict[str, str] = field(default_factory=dict)
    core_concepts: list[str] = field(default_factory=list)
    method_terms: list[str] = field(default_factory=list)
    materials_or_objects: list[str] = field(default_factory=list)
    task_terms: list[str] = field(default_factory=list)
    outcome_terms: list[str] = field(default_factory=list)
    filters: dict[str, Any] = field(default_factory=dict)
    intents: list[str] = field(default_factory=list)
    query_variants: list[QueryVariant] = field(default_factory=list)
    ranking_query_variant_id: str = "original"
    recommended_provider_route: list[dict[str, Any]] = field(default_factory=list)
    request_budget: dict[str, Any] = field(default_factory=dict)
    router_confidence: float = 0.0
    fallback_triggered: bool = False
    fallback_reasons: list[str] = field(default_factory=list)
    provenance: list[dict[str, Any]] = field(default_factory=list)
    research_profile: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def variant(self, variant_id: str) -> QueryVariant | None:
        return next(
            (
                variant
                for variant in self.query_variants
                if variant.variant_id == variant_id
            ),
            None,
        )

    def ranking_query(self) -> str:
        """Return the audited query variant used for relevance ranking."""

        selected = self.variant(self.ranking_query_variant_id)
        if selected and selected.query.strip():
            return selected.query
        return self.original_query

    def add_fallback_reason(self, reason: str) -> None:
        value = str(reason).strip()
        if value and value not in self.fallback_reasons:
            self.fallback_reasons.append(value)
        self.fallback_triggered = bool(self.fallback_reasons)


def _deterministic_copy(value: Any) -> Any:
    """Copy JSON-like profile data with stable mapping-key order."""

    if isinstance(value, Mapping):
        return {
            str(key): _deterministic_copy(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, list):
        return [_deterministic_copy(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_deterministic_copy(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return sorted(
            (_deterministic_copy(item) for item in value),
            key=repr,
        )
    return deepcopy(value)


def _research_profile_copy(
    research_profile: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if research_profile is None:
        return {}
    return _deterministic_copy(research_profile)


def _request_budget_payload(
    global_request_budget: int,
    provider_budgets: Mapping[str, int] | None,
    *,
    clamp_providers_to_global: bool,
) -> dict[str, Any]:
    global_limit = max(1, int(global_request_budget))
    budgets = dict(DEFAULT_PROVIDER_BUDGETS)
    for provider, value in (provider_budgets or {}).items():
        budgets[str(provider).replace("-", "_")] = max(0, int(value))
    if clamp_providers_to_global:
        budgets = {
            provider: min(global_limit, max(0, int(limit)))
            for provider, limit in budgets.items()
        }
    return {
        "global_limit": global_limit,
        "provider_limits": budgets,
    }


def _check_research_profile_budget(
    research_profile: Mapping[str, Any],
    request_budget: Mapping[str, Any],
    *,
    clamp_providers_to_global: bool,
) -> None:
    """Reject drift between an effective profile and the generated budget."""

    effective_settings = research_profile.get("effective_settings")
    if not isinstance(effective_settings, Mapping):
        return
    has_global = "routed_request_budget" in effective_settings
    has_providers = "provider_budgets" in effective_settings
    if not has_global and not has_providers:
        return

    actual_global = int(request_budget.get("global_limit", 0))
    expected_global = (
        max(1, int(effective_settings["routed_request_budget"]))
        if has_global
        else actual_global
    )
    if has_global and actual_global != expected_global:
        raise ValueError(
            "Research profile routed_request_budget does not match the "
            "generated QueryPlan request budget."
        )

    if not has_providers:
        return
    effective_provider_budgets = effective_settings["provider_budgets"]
    if not isinstance(effective_provider_budgets, Mapping):
        raise TypeError(
            "research_profile.effective_settings.provider_budgets must be a mapping."
        )
    expected_budget = _request_budget_payload(
        expected_global,
        effective_provider_budgets,
        clamp_providers_to_global=clamp_providers_to_global,
    )
    if dict(request_budget.get("provider_limits") or {}) != expected_budget[
        "provider_limits"
    ]:
        raise ValueError(
            "Research profile provider_budgets do not match the generated "
            "QueryPlan provider limits."
        )


def normalize_query(query: str) -> str:
    value = unicodedata.normalize("NFKC", str(query or ""))
    value = re.sub(r"[\u0000-\u001f\u007f]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def detect_query_language(query: str) -> str:
    cjk = len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", query))
    latin = len(re.findall(r"[A-Za-z]", query))
    if cjk and latin:
        return "zh-en-mixed"
    if cjk:
        return "zh"
    if latin:
        return "en"
    return "undetermined"


def _deduplicate(values: list[str], *, limit: int = 12) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for raw in values:
        value = re.sub(r"\s+", " ", str(raw or "")).strip(" ,.;:，。；：")
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            output.append(value)
        if len(output) >= limit:
            break
    return output


def _extract_identifiers(query: str) -> dict[str, str]:
    identifiers: dict[str, str] = {}
    doi = normalize_doi(query)
    if doi:
        identifiers["doi"] = doi
    pmcid = re.search(r"\bPMC(?:ID)?\s*[:#-]?\s*(\d+)\b", query, re.I)
    if pmcid:
        identifiers["pmcid"] = f"PMC{pmcid.group(1)}"
    pmid = re.search(r"\bPMID\s*[:#-]?\s*(\d+)\b", query, re.I)
    if pmid:
        identifiers["pmid"] = pmid.group(1)
    arxiv = re.search(
        r"\barXiv\s*:\s*((?:\d{4}\.\d{4,5})|(?:[a-z-]+/\d{7}))\b",
        query,
        re.I,
    )
    if arxiv:
        identifiers["arxiv"] = arxiv.group(1)
    return identifiers


def _english_terms(query: str) -> list[str]:
    return _deduplicate(
        [
            token.casefold()
            for token in re.findall(r"[A-Za-z][A-Za-z0-9-]{2,}", query)
            if token.casefold() not in ENGLISH_STOPWORDS
        ]
    )


def _chinese_terms(query: str) -> list[str]:
    working = query
    for word in CHINESE_FUNCTION_WORDS:
        working = working.replace(word, " ")
    candidates = [
        zh
        for zh, _ in ZH_EN_TERMS
        if zh in query and len(zh) >= 2
    ]
    candidates.extend(
        value
        for value in re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]{2,20}", working)
        if value not in CHINESE_FUNCTION_WORDS
    )
    return _deduplicate(candidates)


def _category_matches(query: str, category: str) -> list[str]:
    lowered = query.casefold()
    return _deduplicate(
        [term for term in CATEGORY_TERMS[category] if term.casefold() in lowered]
    )


def _english_expansion(query: str) -> tuple[str, list[str]]:
    matches: list[tuple[int, str, str]] = []
    for zh, english in ZH_EN_TERMS:
        position = query.find(zh)
        if position >= 0:
            matches.append((position, zh, english))
    matches.sort(key=lambda item: (item[0], -len(item[1]), item[2]))
    terms = _deduplicate([english for _, _, english in matches], limit=10)
    return " ".join(terms), [zh for _, zh, _ in matches]


def _useful_english_expansion(query: str) -> bool:
    """Reject one-token local matches that are too broad to route safely."""

    return len(_english_terms(query)) >= 2


def _validate_english_query(value: str | None) -> tuple[str, str, str]:
    """Validate an optional caller-supplied English scholarly query."""

    if value is None:
        return "", "not-supplied", ""
    normalized = normalize_query(value)
    if not normalized:
        return "", "rejected", "empty after normalization"
    if len(normalized) > MAX_ENGLISH_QUERY_LENGTH:
        return (
            "",
            "rejected",
            f"exceeds {MAX_ENGLISH_QUERY_LENGTH} characters",
        )
    if re.search(r"[\u3400-\u4dbf\u4e00-\u9fff]", normalized):
        return "", "rejected", "contains CJK text"
    if len(_english_terms(normalized)) < 2:
        return "", "rejected", "fewer than two English content terms"
    return normalized, "accepted", ""


def _intent_list(query: str, *, academic: bool) -> list[str]:
    lowered = query.casefold()
    values = ["broad-discovery"]
    for intent, terms in INTENT_TERMS.items():
        if any(term.casefold() in lowered for term in terms):
            values.append(intent)
    if academic:
        values.append("evidence-coverage")
    return _deduplicate(values, limit=8)


def _filter_dict(filters: Any) -> dict[str, Any]:
    if filters is None:
        return {
            "after_date": None,
            "before_date": None,
            "fields_of_study": [],
            "publication_types": [],
            "open_access_only": False,
            "min_citation_count": None,
        }
    if isinstance(filters, Mapping):
        source = dict(filters)
    else:
        source = {
            name: getattr(filters, name, None)
            for name in (
                "after_date",
                "before_date",
                "fields_of_study",
                "publication_types",
                "open_access_only",
                "min_citation_count",
            )
        }
    return {
        "after_date": source.get("after_date"),
        "before_date": source.get("before_date"),
        "fields_of_study": list(source.get("fields_of_study") or []),
        "publication_types": list(source.get("publication_types") or []),
        "open_access_only": bool(source.get("open_access_only")),
        "min_citation_count": source.get("min_citation_count"),
    }


def _provider_route(
    *,
    biomedical: bool,
    identifiers: Mapping[str, str],
    semantic_search: bool,
    provider_configuration: Mapping[str, bool],
) -> list[dict[str, Any]]:
    if identifiers:
        candidates = [
            ("crossref", "identifier and DOI metadata verification"),
            ("openalex", "cross-disciplinary identifier lookup"),
            ("semantic_scholar", "semantic metadata identifier lookup"),
            ("europe_pmc", "PMID/PMCID and biomedical identifier lookup"),
        ]
    elif biomedical:
        candidates = [
            ("europe_pmc", "biomedical discovery and JATS/PMID coverage"),
            ("openalex", "cross-disciplinary primary discovery"),
            ("crossref", "independent bibliographic companion"),
            ("semantic_scholar", "optional semantic metadata companion"),
        ]
    else:
        candidates = [
            (
                "openalex",
                "cross-disciplinary primary discovery"
                + (" with semantic capability" if semantic_search else ""),
            ),
            ("crossref", "independent bibliographic companion"),
            ("semantic_scholar", "optional semantic metadata companion"),
            ("europe_pmc", "coverage fallback when the query is biomedical or sparse"),
        ]
    return [
        {
            "provider": provider,
            "role": reason,
            "configuration": (
                "configured"
                if provider_configuration.get(provider, True)
                else "not configured"
            ),
        }
        for provider, reason in candidates
    ]


def build_query_plan(
    query: str,
    *,
    english_query: str | None = None,
    filters: Any = None,
    academic: bool = True,
    semantic_search: bool = False,
    max_variants: int = MAX_QUERY_VARIANTS,
    global_request_budget: int = 12,
    provider_budgets: Mapping[str, int] | None = None,
    provider_configuration: Mapping[str, bool] | None = None,
    research_profile: Mapping[str, Any] | None = None,
) -> QueryPlan:
    original = str(query or "")
    if not original.strip():
        raise ValueError("A non-empty research query is required.")
    normalized = normalize_query(original)
    language = detect_query_language(normalized)
    identifiers = _extract_identifiers(normalized)
    english_terms = _english_terms(normalized)
    chinese_terms = _chinese_terms(normalized)
    core_concepts = _deduplicate([*chinese_terms, *english_terms])
    methods = _category_matches(normalized, "methods")
    materials = _category_matches(normalized, "materials_objects")
    tasks = _category_matches(normalized, "tasks")
    outcomes = _category_matches(normalized, "outcomes")
    intents = _intent_list(normalized, academic=academic)
    filter_values = _filter_dict(filters)

    local_expansion, expanded_from = _english_expansion(normalized)
    local_expansion_useful = _useful_english_expansion(local_expansion)
    supplied_expansion, english_query_status, english_query_reason = (
        _validate_english_query(english_query)
    )
    if english_query_status == "accepted" and identifiers:
        supplied_expansion = ""
        english_query_status = "ignored-identifier"
        english_query_reason = "stable identifier lookup does not need translation"
    elif english_query_status == "accepted" and language not in {"zh", "zh-en-mixed"}:
        supplied_expansion = ""
        english_query_status = "ignored-non-chinese"
        english_query_reason = "English expansion is only used for Chinese or mixed queries"

    supplied_expansion_selected = bool(supplied_expansion)
    expansion = supplied_expansion or (
        local_expansion if local_expansion_useful else ""
    )
    expansion_source = (
        "caller-supplied-english-query"
        if supplied_expansion_selected
        else "local-bilingual-lexicon-v1"
    )
    variants: list[QueryVariant] = [
        QueryVariant(
            variant_id="original",
            query=original,
            intent="raw-original-fallback",
            language=language,
            source="user",
            provider_hints=("openalex", "crossref", "semantic_scholar", "europe_pmc"),
            preserves_original=True,
        )
    ]
    if supplied_expansion_selected:
        variants.append(
            QueryVariant(
                variant_id="english-term-expansion",
                query=expansion,
                intent="cross-language-term-expansion",
                language="en",
                source=expansion_source,
                provider_hints=(
                    "openalex",
                    "semantic_scholar",
                    "europe_pmc",
                    "crossref",
                ),
            )
        )
    if normalized != original:
        variants.append(
            QueryVariant(
                variant_id="normalized-wide",
                query=normalized,
                intent="broad-discovery",
                language=language,
                source="unicode-and-whitespace-normalization",
                provider_hints=("openalex", "crossref", "semantic_scholar", "europe_pmc"),
            )
        )
    if identifiers:
        identifier_value = (
            identifiers.get("doi")
            or identifiers.get("pmid")
            or identifiers.get("pmcid")
            or identifiers.get("arxiv")
            or normalized
        )
        variants.append(
            QueryVariant(
                variant_id="stable-identifier",
                query=identifier_value,
                intent="known-paper-lookup",
                language="identifier",
                source="deterministic-identifier-extraction",
                provider_hints=("crossref", "openalex", "semantic_scholar", "europe_pmc"),
            )
        )
    if (
        expansion
        and not supplied_expansion_selected
        and expansion.casefold() != normalized.casefold()
    ):
        variants.append(
            QueryVariant(
                variant_id="english-term-expansion",
                query=expansion,
                intent="cross-language-term-expansion",
                language="en",
                source=expansion_source,
                provider_hints=("openalex", "semantic_scholar", "europe_pmc", "crossref"),
            )
        )
    concept_wide = " ".join(
        value
        for value in [*english_terms, *methods, *materials, *tasks, *outcomes]
        if re.search(r"[A-Za-z]", value)
    )
    concept_wide = " ".join(_deduplicate(concept_wide.split(), limit=14))
    if (
        concept_wide
        and concept_wide.casefold() not in {variant.query.casefold() for variant in variants}
    ):
        variants.append(
            QueryVariant(
                variant_id="concept-wide",
                query=concept_wide,
                intent="conservative-broad-query",
                language="en",
                source="deterministic-concept-selection",
                provider_hints=("openalex", "crossref", "semantic_scholar", "europe_pmc"),
            )
        )

    variant_cap = max(1, min(int(max_variants), MAX_QUERY_VARIANTS))
    variants = variants[:variant_cap]
    if not any(variant.variant_id == "original" for variant in variants):
        variants[-1] = QueryVariant(
            variant_id="original",
            query=original,
            intent="raw-original-fallback",
            language=language,
            source="user",
            preserves_original=True,
        )

    english_variant_selected = any(
        variant.variant_id == "english-term-expansion" for variant in variants
    )
    if supplied_expansion_selected and not english_variant_selected:
        english_query_status = "accepted-not-selected"
        english_query_reason = "excluded by the configured query variant cap"
    ranking_query_variant_id = (
        "english-term-expansion"
        if english_variant_selected and not identifiers
        else "original"
    )

    lowered = normalized.casefold()
    biomedical = any(term.casefold() in lowered for term in BIOMEDICAL_TERMS)
    configured = dict(provider_configuration or {})
    profile_snapshot = _research_profile_copy(research_profile)
    request_budget = _request_budget_payload(
        global_request_budget,
        provider_budgets,
        clamp_providers_to_global=True,
    )
    _check_research_profile_budget(
        profile_snapshot,
        request_budget,
        clamp_providers_to_global=True,
    )

    if identifiers:
        confidence = 0.97
    elif biomedical:
        confidence = 0.9
    elif supplied_expansion_selected and english_variant_selected:
        confidence = 0.84
    elif language == "en":
        confidence = 0.78
    elif language == "zh-en-mixed" and len(english_terms) >= 2:
        confidence = 0.78
    elif english_variant_selected:
        confidence = 0.78
    else:
        confidence = 0.58

    return QueryPlan(
        original_query=original,
        query_language=language,
        normalized_query=normalized,
        identifiers=identifiers,
        core_concepts=core_concepts,
        method_terms=methods,
        materials_or_objects=materials,
        task_terms=tasks,
        outcome_terms=outcomes,
        filters=filter_values,
        intents=intents,
        query_variants=variants,
        ranking_query_variant_id=ranking_query_variant_id,
        recommended_provider_route=_provider_route(
            biomedical=biomedical,
            identifiers=identifiers,
            semantic_search=semantic_search,
            provider_configuration=configured,
        ),
        request_budget=request_budget,
        router_confidence=confidence,
        provenance=[
            {
                "sequence": 1,
                "operation": "capture-original-query",
                "source": "user",
                "details": {"preserved_verbatim": True},
            },
            {
                "sequence": 2,
                "operation": "deterministic-local-query-build",
                "source": "rle.query_plan",
                "details": {
                    "normalization": "Unicode NFKC, control removal, whitespace compaction",
                    "language_heuristic": language,
                    "bilingual_expansion_terms": expanded_from,
                    "local_english_expansion_useful": local_expansion_useful,
                    "english_query_status": english_query_status,
                    "english_query_reason": english_query_reason,
                    "ranking_query_variant_id": ranking_query_variant_id,
                    "variant_cap": variant_cap,
                    "llm_used": False,
                    "planner_llm_call_used": False,
                    "external_translation_supplied": english_query is not None,
                    "external_translation_used": bool(
                        supplied_expansion_selected and english_variant_selected
                    ),
                },
            },
        ],
        research_profile=profile_snapshot,
    )


def emergency_query_plan(
    query: str,
    *,
    filters: Any = None,
    error: str = "",
    global_request_budget: int = 12,
    provider_budgets: Mapping[str, int] | None = None,
    research_profile: Mapping[str, Any] | None = None,
) -> QueryPlan:
    """Return a minimal raw-query plan when normal query construction fails."""
    original = str(query or "")
    normalized = normalize_query(original) or original
    profile_snapshot = _research_profile_copy(research_profile)
    request_budget = _request_budget_payload(
        global_request_budget,
        provider_budgets,
        clamp_providers_to_global=False,
    )
    _check_research_profile_budget(
        profile_snapshot,
        request_budget,
        clamp_providers_to_global=False,
    )
    plan = QueryPlan(
        original_query=original,
        query_language=detect_query_language(normalized),
        normalized_query=normalized,
        identifiers=_extract_identifiers(original),
        filters=_filter_dict(filters),
        intents=["raw-original-fallback"],
        query_variants=[
            QueryVariant(
                variant_id="original",
                query=original,
                intent="raw-original-fallback",
                language=detect_query_language(normalized),
                source="user",
                provider_hints=("openalex", "crossref", "semantic_scholar", "europe_pmc"),
                preserves_original=True,
            )
        ],
        recommended_provider_route=[
            {"provider": "openalex", "role": "general fallback"},
            {"provider": "crossref", "role": "independent bibliographic fallback"},
            {"provider": "semantic_scholar", "role": "optional configured fallback"},
            {"provider": "europe_pmc", "role": "biomedical and shortage fallback"},
        ],
        request_budget=request_budget,
        router_confidence=0.0,
        fallback_triggered=True,
        fallback_reasons=[
            "query builder failed; preserved raw original query"
            + (f": {error}" if error else "")
        ],
        provenance=[
            {
                "sequence": 1,
                "operation": "emergency-query-plan",
                "source": "rle.query_plan",
                "details": {"error": error, "llm_used": False},
            }
        ],
        research_profile=profile_snapshot,
    )
    return plan
