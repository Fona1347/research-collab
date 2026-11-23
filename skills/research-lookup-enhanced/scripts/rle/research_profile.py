"""Deterministic research-depth profiles and per-run configuration resolution.

The resolver operates only after a request has already been accepted as a scholarly
research task.  It does not decide whether the Skill should be invoked, call an LLM,
or authorize remote parsing/model downloads.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


PROFILE_SCHEMA_VERSION = 1
MAX_QUERY_VARIANTS = 6

RESEARCH_LEVELS = frozenset({"quick", "standard", "deep"})
REQUESTED_LEVELS = frozenset({"auto", *RESEARCH_LEVELS})
EXPLICIT_SOURCES = frozenset(
    {"explicit-user-intent", "explicit-cli", "agent-inference"}
)
PROVIDER_ORDER = (
    "openalex",
    "crossref",
    "semantic_scholar",
    "europe_pmc",
)
PROVIDER_ALIASES = {
    "open_alex": "openalex",
    "s2": "semantic_scholar",
    "semantic-scholar": "semantic_scholar",
    "semanticscholar": "semantic_scholar",
    "europe-pmc": "europe_pmc",
    "europepmc": "europe_pmc",
}

OVERRIDE_ALIASES = {
    "global_request_budget": "request_budget",
    "max_results_per_provider": "max_results",
    "extract_limit_records": "extract_limit",
}
OVERRIDABLE_FIELDS = frozenset(
    {
        "target_references",
        "max_results",
        "request_budget",
        "provider_budgets",
        "fallback_threshold",
        "stable_identifier_threshold",
        "max_query_variants",
        "resolve_oa",
        "easy_scholar",
        "extract_fulltext",
        "extract_limit",
        "graph_limit",
    }
)


def _empty_mapping() -> Mapping[str, Any]:
    return MappingProxyType({})


def _plain(value: Any) -> Any:
    """Return a deterministic JSON-compatible copy of profile data."""
    if isinstance(value, Mapping):
        return {
            str(key): _plain(value[key])
            for key in sorted(value, key=lambda item: str(item))
        }
    if isinstance(value, tuple):
        return [_plain(item) for item in value]
    if isinstance(value, list):
        return [_plain(item) for item in value]
    return value


def _freeze_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any]:
    return MappingProxyType(dict(_plain(value or {})))


def _canonical_provider(value: str) -> str:
    name = str(value or "").strip().casefold().replace(" ", "_")
    name = PROVIDER_ALIASES.get(name, name.replace("-", "_"))
    if not name:
        raise ValueError("Provider budget names cannot be empty.")
    return name


def _ordered_provider_budgets(
    value: Mapping[str, Any],
) -> Mapping[str, int]:
    parsed: dict[str, int] = {}
    for raw_name, raw_limit in value.items():
        name = _canonical_provider(str(raw_name))
        try:
            limit = int(raw_limit)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Provider budget for {raw_name!r} must be an integer."
            ) from exc
        parsed[name] = limit
    ordered: dict[str, int] = {}
    for name in PROVIDER_ORDER:
        if name in parsed:
            ordered[name] = parsed.pop(name)
    for name in sorted(parsed):
        ordered[name] = parsed[name]
    return MappingProxyType(ordered)


def _sanitize_reason(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:512]


def _normalize_query(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value or ""))
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


@dataclass(frozen=True, slots=True)
class ResearchLevelDecision:
    """Auditable selection of a named profile."""

    requested_level: str | None
    effective_level: str
    source: str
    reason_code: str
    reason: str
    matched_signals: tuple[str, ...] = ()
    ambiguous: bool = False
    schema_version: int = PROFILE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "requested_level": self.requested_level,
            "effective_level": self.effective_level,
            "source": self.source,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "matched_signals": list(self.matched_signals),
            "ambiguous": self.ambiguous,
        }


@dataclass(frozen=True, slots=True)
class ResearchProfile:
    """Named defaults; explicit run options are merged by the resolver."""

    level: str
    target_references: int
    max_results: int
    request_budget: int
    provider_budgets: Mapping[str, int]
    fallback_threshold: int
    stable_identifier_threshold: float
    max_query_variants: int
    resolve_oa: bool
    easy_scholar: bool
    extract_fulltext: bool
    extract_limit: int
    graph_limit: int
    schema_version: int = PROFILE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "level": self.level,
            "target_references": self.target_references,
            "max_results": self.max_results,
            "request_budget": self.request_budget,
            "provider_budgets": _plain(self.provider_budgets),
            "fallback_threshold": self.fallback_threshold,
            "stable_identifier_threshold": self.stable_identifier_threshold,
            "max_query_variants": self.max_query_variants,
            "resolve_oa": self.resolve_oa,
            "easy_scholar": self.easy_scholar,
            "extract_fulltext": self.extract_fulltext,
            "extract_limit": self.extract_limit,
            "graph_limit": self.graph_limit,
        }

    def parameter_dict(self) -> dict[str, Any]:
        payload = self.to_dict()
        payload.pop("schema_version")
        payload.pop("level")
        return payload


@dataclass(frozen=True, slots=True)
class EffectiveRunConfig:
    """Immutable, per-query runtime snapshot after all override layers."""

    decision: ResearchLevelDecision
    base_profile: ResearchProfile
    target_references: int
    max_results: int
    request_budget: int
    provider_budgets: Mapping[str, int]
    fallback_threshold: int
    stable_identifier_threshold: float
    max_query_variants: int
    resolve_oa: bool
    easy_scholar: bool
    extract_fulltext: bool
    extract_limit: int
    graph_limit: int
    inferred_overrides: Mapping[str, Any] = field(default_factory=_empty_mapping)
    explicit_overrides: Mapping[str, Any] = field(default_factory=_empty_mapping)
    constraints_applied: tuple[str, ...] = ()
    schema_version: int = PROFILE_SCHEMA_VERSION

    def effective_parameters(self) -> dict[str, Any]:
        return {
            "target_references": self.target_references,
            "max_results": self.max_results,
            "routed_request_budget": self.request_budget,
            "provider_budgets": _plain(self.provider_budgets),
            "fallback_threshold": self.fallback_threshold,
            "stable_identifier_threshold": self.stable_identifier_threshold,
            "max_query_variants": self.max_query_variants,
            "resolve_oa": self.resolve_oa,
            "easy_scholar": self.easy_scholar,
            "extract_fulltext": self.extract_fulltext,
            "extract_limit": self.extract_limit,
            "graph_limit": self.graph_limit,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "decision": self.decision.to_dict(),
            "profile_defaults": self.base_profile.parameter_dict(),
            "inferred_overrides": _plain(self.inferred_overrides),
            "explicit_overrides": _plain(self.explicit_overrides),
            "constraints_applied": list(self.constraints_applied),
            "effective_settings": self.effective_parameters(),
        }

    def research_profile_payload(self) -> dict[str, Any]:
        """Return the nested payload intended for QueryPlan and packet output."""
        return self.to_dict()

    def to_research_profile_payload(self) -> dict[str, Any]:
        """Compatibility spelling for callers that prefer a ``to_*`` helper."""
        return self.research_profile_payload()


def _profile(
    level: str,
    *,
    target_references: int,
    max_results: int,
    request_budget: int,
    provider_budgets: Mapping[str, int],
    fallback_threshold: int,
    stable_identifier_threshold: float,
    max_query_variants: int,
    resolve_oa: bool,
    easy_scholar: bool,
    extract_fulltext: bool,
    extract_limit: int,
    graph_limit: int,
) -> ResearchProfile:
    return ResearchProfile(
        level=level,
        target_references=target_references,
        max_results=max_results,
        request_budget=request_budget,
        provider_budgets=_ordered_provider_budgets(provider_budgets),
        fallback_threshold=fallback_threshold,
        stable_identifier_threshold=stable_identifier_threshold,
        max_query_variants=max_query_variants,
        resolve_oa=resolve_oa,
        easy_scholar=easy_scholar,
        extract_fulltext=extract_fulltext,
        extract_limit=extract_limit,
        graph_limit=graph_limit,
    )


RESEARCH_PROFILES: Mapping[str, ResearchProfile] = MappingProxyType(
    {
        "quick": _profile(
            "quick",
            target_references=12,
            max_results=5,
            request_budget=6,
            provider_budgets={
                "openalex": 2,
                "crossref": 2,
                "semantic_scholar": 1,
                "europe_pmc": 2,
            },
            fallback_threshold=5,
            stable_identifier_threshold=0.5,
            max_query_variants=3,
            resolve_oa=True,
            easy_scholar=False,
            extract_fulltext=False,
            extract_limit=5,
            graph_limit=20,
        ),
        "standard": _profile(
            "standard",
            target_references=60,
            max_results=10,
            request_budget=12,
            provider_budgets={
                "openalex": 4,
                "crossref": 3,
                "semantic_scholar": 2,
                "europe_pmc": 3,
            },
            fallback_threshold=12,
            stable_identifier_threshold=0.5,
            max_query_variants=6,
            resolve_oa=True,
            easy_scholar=True,
            extract_fulltext=False,
            extract_limit=20,
            graph_limit=50,
        ),
        "deep": _profile(
            "deep",
            target_references=100,
            max_results=20,
            request_budget=24,
            provider_budgets={
                "openalex": 8,
                "crossref": 6,
                "semantic_scholar": 4,
                "europe_pmc": 6,
            },
            fallback_threshold=24,
            stable_identifier_threshold=0.65,
            max_query_variants=6,
            resolve_oa=True,
            easy_scholar=True,
            extract_fulltext=False,
            extract_limit=40,
            graph_limit=100,
        ),
    }
)


IDENTIFIER_PATTERNS = (
    re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I),
    re.compile(r"\bPMID\s*[:#-]?\s*\d+\b", re.I),
    re.compile(r"\bPMC(?:ID)?\s*[:#-]?\s*\d+\b", re.I),
    re.compile(
        r"\barXiv\s*:\s*(?:\d{4}\.\d{4,5}|[a-z-]+/\d{7})\b",
        re.I,
    ),
)

QUICK_PATTERNS = (
    re.compile(
        r"\b(?:quick|brief|rapid)\s+"
        r"(?:(?:comprehensive|systematic)\s+)?"
        r"(?:paper\s+)?(?:search|lookup|scan)\b",
        re.I,
    ),
    re.compile(r"\bfind\s+(?:me\s+)?(?:a\s+)?few\s+(?:core\s+|key\s+)?papers?\b", re.I),
    re.compile(r"(?:快速|简要|简单).{0,4}(?:找|查|检索|看)(?:一下)?(?:几篇|少量)?(?:相关|核心)?(?:论文|文献)?"),
    re.compile(r"(?:找|查|检索)(?:一下)?(?:几篇|少量)(?:相关|核心)?(?:论文|文献)"),
)

DEEP_PATTERNS: Mapping[str, tuple[re.Pattern[str], ...]] = MappingProxyType(
    {
        "operation:deep-research": (
            re.compile(
                r"\b(?:(?:conduct|perform|undertake|do|provide)\s+)?"
                r"deep\s+(?:research|investigation|literature\s+search)\b",
                re.I,
            ),
            re.compile(
                r"(?:开展|进行|执行|做)?(?:一次|一项)?深度(?:调研|检索|研究)"
            ),
        ),
        "operation:fulltext": (
            re.compile(
                r"\b(?:read|review|analyse|analyze|parse|extract)\s+"
                r"(?:the\s+)?full[- ]texts?\b",
                re.I,
            ),
            re.compile(r"(?:逐篇)?(?:阅读|精读|解析|分析)(?:相关|这些|论文)?全文"),
            re.compile(r"全文(?:阅读|精读|解析|证据分析)"),
        ),
        "operation:citation-network": (
            re.compile(
                r"\b(?:trace|expand|analyse|analyze|map|build|follow)\s+"
                r"(?:the\s+)?(?:citation|reference)\s+(?:network|graph)\b",
                re.I,
            ),
            re.compile(r"(?:追踪|扩展|分析|构建|绘制).{0,6}(?:引用|引文)(?:网络|图谱|关系)"),
        ),
        "operation:conflict-analysis": (
            re.compile(
                r"\b(?:analyse|analyze|compare|reconcile|identify)\s+"
                r"(?:the\s+)?(?:contradictory|conflicting)\s+"
                r"(?:evidence|findings|results)\b",
                re.I,
            ),
            re.compile(r"(?:分析|比较|协调|识别).{0,6}(?:矛盾|冲突|不一致)(?:证据|结论|结果)"),
        ),
        "operation:systematic-review": (
            re.compile(
                r"\bcomprehensive\s+"
                r"(?:literature\s+|academic\s+|evidence\s+)?search\b",
                re.I,
            ),
            re.compile(
                r"\b(?:conduct|perform|prepare|provide|write|produce)\s+"
                r"(?:a\s+)?(?:comprehensive|systematic)\s+"
                r"(?:literature\s+|evidence\s+)?review\b",
                re.I,
            ),
            re.compile(r"(?:全面|系统性|系统地)(?:文献|学术|证据)?(?:检索|调研)"),
            re.compile(r"(?:开展|进行|完成|撰写|生成|提供).{0,4}(?:全面|系统性|系统的)(?:文献)?(?:检索|调研|综述)"),
        ),
        "operation:complete-report": (
            re.compile(
                r"\b(?:complete|full|comprehensive)\s+"
                r"(?:research|evidence|literature)\s+report\b",
                re.I,
            ),
            re.compile(r"完整(?:的)?(?:研究|调研|证据|文献)报告"),
        ),
    }
)

NEGATION_PATTERNS: Mapping[str, tuple[re.Pattern[str], ...]] = MappingProxyType(
    {
        "operation:deep-research": (
            re.compile(
                r"\b(?:do\s+not|don't|without|no\s+need\s+to)\s+"
                r"(?:conduct|perform|undertake|do|provide)?\s*"
                r"deep\s+(?:research|investigation|literature\s+search)\b",
                re.I,
            ),
            re.compile(
                r"(?:不要|无需|不需要)(?:开展|进行|执行|做)?"
                r"(?:一次|一项)?深度(?:调研|检索|研究)"
            ),
        ),
        "operation:fulltext": (
            re.compile(
                r"\b(?:do\s+not|don't|without|no\s+need\s+to)\s+"
                r"(?:read|review|analyse|analyze|parse|extract)\s+"
                r"(?:the\s+)?full[- ]texts?\b",
                re.I,
            ),
            re.compile(r"(?:不要|无需|不需要)(?:阅读|精读|解析|分析)?(?:论文)?全文"),
        ),
        "operation:citation-network": (
            re.compile(
                r"\b(?:do\s+not|don't|without|no\s+need\s+to)\s+"
                r"(?:trace|expand|analyse|analyze|map|build|follow)\s+"
                r"(?:the\s+)?(?:citation|reference)\s+(?:network|graph)\b",
                re.I,
            ),
            re.compile(r"(?:不要|无需|不需要).{0,6}(?:引用|引文)(?:网络|图谱|扩展)"),
        ),
        "operation:conflict-analysis": (
            re.compile(
                r"\b(?:do\s+not|don't|without|no\s+need\s+to)\s+"
                r"(?:analyse|analyze|compare|reconcile|identify)\s+"
                r"(?:the\s+)?(?:contradictory|conflicting)\s+"
                r"(?:evidence|findings|results)\b",
                re.I,
            ),
            re.compile(r"(?:不要|无需|不需要).{0,6}(?:矛盾|冲突|不一致)(?:证据|结论|结果)"),
        ),
        "operation:systematic-review": (
            re.compile(
                r"\b(?:do\s+not|don't|without|no\s+need\s+to)\s+"
                r"(?:(?:conduct|perform|prepare|provide|write|produce)\s+)?"
                r"(?:a\s+)?(?:comprehensive|systematic)\s+"
                r"(?:(?:literature|academic|evidence)\s+)?(?:search|review)\b",
                re.I,
            ),
            re.compile(
                r"(?:不要|无需|不需要)(?:开展|进行|完成|撰写|生成|提供)?"
                r".{0,4}(?:全面|系统性|系统的)(?:文献|学术|证据)?"
                r"(?:检索|调研|综述)"
            ),
        ),
        "operation:complete-report": (
            re.compile(
                r"\b(?:do\s+not|don't|without|no\s+need\s+for)\s+"
                r"(?:a\s+)?(?:complete|full|comprehensive)\s+"
                r"(?:research|evidence|literature)\s+report\b",
                re.I,
            ),
            re.compile(
                r"(?:不要|无需|不需要).{0,4}完整(?:的)?"
                r"(?:研究|调研|证据|文献)报告"
            ),
        ),
    }
)


class ResearchLevelResolver:
    """Resolve one query to a profile without network, time, or model inputs."""

    def __init__(
        self,
        profiles: Mapping[str, ResearchProfile] | None = None,
    ) -> None:
        selected = dict(profiles or RESEARCH_PROFILES)
        missing = RESEARCH_LEVELS.difference(selected)
        if missing:
            raise ValueError(f"Missing research profiles: {sorted(missing)!r}")
        self._profiles: Mapping[str, ResearchProfile] = MappingProxyType(selected)

    @property
    def profiles(self) -> Mapping[str, ResearchProfile]:
        return self._profiles

    def _auto_decision(
        self,
        query: str,
        explicit_overrides: Mapping[str, Any],
    ) -> ResearchLevelDecision:
        normalized = _normalize_query(query)
        signals: list[str] = []
        negated: list[str] = []

        for signal, patterns in DEEP_PATTERNS.items():
            is_negated = any(
                pattern.search(normalized)
                for pattern in NEGATION_PATTERNS.get(signal, ())
            )
            if is_negated:
                negated.append(f"negated:{signal.removeprefix('operation:')}")
                continue
            if any(pattern.search(normalized) for pattern in patterns):
                signals.append(signal)

        extract_override = explicit_overrides.get("extract_fulltext")
        if extract_override is True and "operation:fulltext" not in signals:
            signals.append("option:extract-fulltext")

        quick_signals = [
            "request:quick"
            for pattern in QUICK_PATTERNS
            if pattern.search(normalized)
        ]
        if quick_signals:
            quick_signals = ["request:quick"]

        has_identifier = any(pattern.search(normalized) for pattern in IDENTIFIER_PATTERNS)
        if has_identifier:
            quick_signals.append("query:stable-identifier")

        matched = tuple(dict.fromkeys([*signals, *quick_signals, *negated]))
        # An identifier is a quick default, not a conflict with an explicit
        # full-text/graph/conflict operation concerning that known paper.
        if signals and "request:quick" in quick_signals:
            return ResearchLevelDecision(
                requested_level="auto",
                effective_level="standard",
                source="auto-rule",
                reason_code="auto-ambiguous-standard",
                reason=(
                    "Quick and deep-operation signals conflict; using the "
                    "conservative standard profile."
                ),
                matched_signals=matched,
                ambiguous=True,
            )
        if signals:
            return ResearchLevelDecision(
                requested_level="auto",
                effective_level="deep",
                source="auto-rule",
                reason_code="deep-explicit-operations",
                reason="High-confidence research operations require the deep profile.",
                matched_signals=matched,
            )
        if quick_signals:
            code = (
                "quick-stable-identifier"
                if quick_signals == ["query:stable-identifier"]
                else "quick-explicit-request"
            )
            return ResearchLevelDecision(
                requested_level="auto",
                effective_level="quick",
                source="auto-rule",
                reason_code=code,
                reason="A bounded quick lookup is sufficient for the detected request.",
                matched_signals=matched,
            )
        return ResearchLevelDecision(
            requested_level="auto",
            effective_level="standard",
            source="auto-rule",
            reason_code="auto-default-standard",
            reason="No high-confidence quick or deep signal was detected.",
            matched_signals=matched,
        )

    def _explicit_decision(
        self,
        requested_level: str,
        source: str | None,
        reason: str | None,
    ) -> ResearchLevelDecision:
        resolved_source = str(source or "explicit-cli").strip().casefold()
        if resolved_source not in EXPLICIT_SOURCES:
            raise ValueError(
                "A non-auto research level requires source explicit-user-intent, "
                "explicit-cli, or agent-inference."
            )
        sanitized = _sanitize_reason(reason)
        if not sanitized:
            descriptions = {
                "explicit-user-intent": "The user explicitly requested this research level.",
                "explicit-cli": "The research level was explicitly selected on the CLI.",
                "agent-inference": "The agent selected this level from the research request.",
            }
            sanitized = descriptions[resolved_source]
        return ResearchLevelDecision(
            requested_level=requested_level,
            effective_level=requested_level,
            source=resolved_source,
            reason_code=f"{resolved_source}-selection",
            reason=sanitized,
        )

    @staticmethod
    def _default_decision() -> ResearchLevelDecision:
        return ResearchLevelDecision(
            requested_level=None,
            effective_level="standard",
            source="default-standard",
            reason_code="default-standard",
            reason="No research level was requested; using the standard profile.",
        )

    @staticmethod
    def _normalize_overrides(
        overrides: Mapping[str, Any] | None,
    ) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for raw_name, value in (overrides or {}).items():
            name = OVERRIDE_ALIASES.get(str(raw_name), str(raw_name))
            if name not in OVERRIDABLE_FIELDS:
                raise ValueError(f"Unsupported research-profile override: {raw_name!r}")
            if value is None:
                continue
            if name == "provider_budgets":
                if not isinstance(value, Mapping):
                    raise ValueError("provider_budgets must be a mapping.")
                normalized[name] = dict(_ordered_provider_budgets(value))
            else:
                normalized[name] = value
        return normalized

    @staticmethod
    def _boolean(value: Any, name: str) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{name} must be a boolean.")
        return value

    @staticmethod
    def _integer(value: Any, name: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be an integer.")
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be an integer.") from exc

    def resolve(
        self,
        query: str,
        *,
        requested_level: str | None = None,
        source: str | None = None,
        reason: str | None = None,
        explicit_overrides: Mapping[str, Any] | None = None,
    ) -> EffectiveRunConfig:
        """Resolve one query; explicit concrete options override profile defaults."""
        requested = (
            None
            if requested_level is None
            else str(requested_level).strip().casefold()
        )
        if requested is not None and requested not in REQUESTED_LEVELS:
            raise ValueError(
                "research level must be auto, quick, standard, or deep."
            )
        overrides = self._normalize_overrides(explicit_overrides)
        if requested is None:
            if source is not None or reason is not None:
                raise ValueError(
                    "source and reason require an explicit non-auto research level."
                )
            decision = self._default_decision()
        elif requested == "auto":
            if source is not None or reason is not None:
                raise ValueError(
                    "auto generates its own source and reason; source and reason "
                    "require an explicit non-auto research level."
                )
            decision = self._auto_decision(query, overrides)
        else:
            decision = self._explicit_decision(requested, source, reason)

        profile = self._profiles[decision.effective_level]
        values = profile.parameter_dict()
        inferred: dict[str, Any] = {}
        if (
            requested == "auto"
            and "operation:fulltext" in decision.matched_signals
        ):
            inferred["extract_fulltext"] = True
            values["extract_fulltext"] = True

        provider_override = overrides.get("provider_budgets", {})
        for name, value in overrides.items():
            if name != "provider_budgets":
                values[name] = value
        if provider_override:
            merged = dict(values["provider_budgets"])
            merged.update(provider_override)
            values["provider_budgets"] = merged

        constraints: list[str] = []

        def bounded_int(name: str, minimum: int, maximum: int | None = None) -> int:
            parsed = self._integer(values[name], name)
            if parsed < minimum:
                parsed = minimum
                constraints.append(f"{name}:minimum:{minimum}")
            if maximum is not None and parsed > maximum:
                parsed = maximum
                constraints.append(f"{name}:maximum:{maximum}")
            return parsed

        target_references = bounded_int("target_references", 1)
        max_results = bounded_int("max_results", 1)
        request_budget = bounded_int("request_budget", 1)
        fallback_threshold = bounded_int(
            "fallback_threshold", 1, target_references
        )
        max_query_variants = bounded_int(
            "max_query_variants", 1, MAX_QUERY_VARIANTS
        )
        extract_limit = bounded_int("extract_limit", 0)
        graph_limit = bounded_int("graph_limit", 1)

        try:
            stable_identifier_threshold = float(values["stable_identifier_threshold"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "stable_identifier_threshold must be a number."
            ) from exc
        if stable_identifier_threshold < 0.0:
            stable_identifier_threshold = 0.0
            constraints.append("stable_identifier_threshold:minimum:0.0")
        if stable_identifier_threshold > 1.0:
            stable_identifier_threshold = 1.0
            constraints.append("stable_identifier_threshold:maximum:1.0")

        provider_values: dict[str, int] = {}
        for name, raw_limit in values["provider_budgets"].items():
            limit = self._integer(raw_limit, f"provider_budgets.{name}")
            if limit < 0:
                limit = 0
                constraints.append(f"provider_budgets.{name}:minimum:0")
            if limit > request_budget:
                limit = request_budget
                constraints.append(
                    f"provider_budgets.{name}:maximum-request-budget:{request_budget}"
                )
            provider_values[_canonical_provider(name)] = limit

        return EffectiveRunConfig(
            decision=decision,
            base_profile=profile,
            target_references=target_references,
            max_results=max_results,
            request_budget=request_budget,
            provider_budgets=_ordered_provider_budgets(provider_values),
            fallback_threshold=fallback_threshold,
            stable_identifier_threshold=stable_identifier_threshold,
            max_query_variants=max_query_variants,
            resolve_oa=self._boolean(values["resolve_oa"], "resolve_oa"),
            easy_scholar=self._boolean(values["easy_scholar"], "easy_scholar"),
            extract_fulltext=self._boolean(
                values["extract_fulltext"], "extract_fulltext"
            ),
            extract_limit=extract_limit,
            graph_limit=graph_limit,
            inferred_overrides=_freeze_mapping(inferred),
            explicit_overrides=_freeze_mapping(overrides),
            constraints_applied=tuple(constraints),
        )


__all__ = [
    "PROFILE_SCHEMA_VERSION",
    "RESEARCH_PROFILES",
    "EffectiveRunConfig",
    "ResearchLevelDecision",
    "ResearchLevelResolver",
    "ResearchProfile",
]
