"""Capability-aware scholarly source routing with bounded deterministic fallback."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable

from .models import PaperRecord, Provenance, merge_records, utc_now
from .providers import Provider, SearchFilters
from .query_plan import QueryPlan, QueryVariant


@dataclass(slots=True)
class RequestBudget:
    global_limit: int
    provider_limits: dict[str, int]
    global_used: int = 0
    provider_used: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_plan(cls, plan: QueryPlan) -> "RequestBudget":
        payload = plan.request_budget or {}
        return cls(
            global_limit=max(1, int(payload.get("global_limit") or 1)),
            provider_limits={
                str(name).replace("-", "_"): max(0, int(value))
                for name, value in (payload.get("provider_limits") or {}).items()
            },
        )

    def can_consume(self, provider: str) -> tuple[bool, str]:
        normalized = provider.replace("-", "_")
        if self.global_used >= self.global_limit:
            return False, "global request budget exhausted"
        provider_limit = self.provider_limits.get(normalized, self.global_limit)
        if self.provider_used.get(normalized, 0) >= provider_limit:
            return False, f"{normalized} request budget exhausted"
        return True, ""

    def consume(self, provider: str) -> None:
        allowed, reason = self.can_consume(provider)
        if not allowed:
            raise RuntimeError(reason)
        normalized = provider.replace("-", "_")
        self.global_used += 1
        self.provider_used[normalized] = self.provider_used.get(normalized, 0) + 1

    def snapshot(self) -> dict[str, Any]:
        return {
            "global": {
                "limit": self.global_limit,
                "used": self.global_used,
                "remaining": max(0, self.global_limit - self.global_used),
            },
            "providers": {
                provider: {
                    "limit": limit,
                    "used": self.provider_used.get(provider, 0),
                    "remaining": max(
                        0, limit - self.provider_used.get(provider, 0)
                    ),
                }
                for provider, limit in sorted(self.provider_limits.items())
            },
        }


@dataclass(slots=True)
class RoutingResult:
    records: list[PaperRecord]
    failed_providers: dict[str, str]
    provider_result_counts: dict[str, int]
    budget: dict[str, Any]
    request_budget: RequestBudget = field(repr=False)


class SourceRouter:
    """Run at most three finite retrieval stages using provider capabilities."""

    def __init__(
        self,
        providers: Iterable[Provider],
        *,
        query_plan: QueryPlan,
        filters: SearchFilters,
        max_results_per_request: int,
        fallback_threshold: int,
        stable_identifier_threshold: float = 0.5,
        after_date: str | None = None,
        semantic_search: bool = False,
    ) -> None:
        self.providers = list(providers)
        self.provider_map = {provider.name: provider for provider in self.providers}
        self.plan = query_plan
        self.filters = filters
        self.max_results = max(1, int(max_results_per_request))
        requested_threshold = max(1, int(fallback_threshold))
        self.fallback_threshold = (
            1 if self.plan.identifiers else requested_threshold
        )
        self.stable_identifier_threshold = min(
            1.0, max(0.0, float(stable_identifier_threshold))
        )
        self.after_date = after_date
        self.semantic_search = semantic_search
        self.budget = RequestBudget.from_plan(query_plan)
        self.failed_providers: dict[str, str] = {}
        self.provider_result_counts: dict[str, int] = {}
        self.executed: set[tuple[str, str, str, bool]] = set()
        self.completed: set[tuple[str, str, str, bool]] = set()

    @staticmethod
    def _timestamp() -> str:
        return utc_now()

    def _variant(self, *names: str) -> QueryVariant:
        for name in names:
            value = self.plan.variant(name)
            if value and value.query.strip():
                return value
        original = self.plan.variant("original")
        if original is None:
            raise RuntimeError("QueryPlan does not contain the required original variant.")
        return original

    def _unexecuted_variant(
        self,
        provider_name: str,
        *names: str,
        operation: str = "search",
        semantic: bool = False,
    ) -> QueryVariant:
        candidates: list[QueryVariant] = []
        for name in names:
            value = self.plan.variant(name)
            if value and value.query.strip() and value not in candidates:
                candidates.append(value)
        original = self._variant("original")
        if original not in candidates:
            candidates.append(original)
        for variant in candidates:
            key = (
                provider_name,
                operation,
                variant.query.casefold().strip(),
                bool(semantic),
            )
            if key not in self.executed:
                return variant
        return candidates[0]

    def _provider_available(
        self, provider_name: str, capability: str
    ) -> tuple[bool, str]:
        provider = self.provider_map.get(provider_name)
        if provider is None:
            return False, "provider was not included in this run"
        status = provider.status()
        if not status.enabled:
            return False, status.reason or "provider is not configured"
        if capability not in status.capabilities:
            return False, f"{capability} capability is unavailable"
        if provider_name in self.failed_providers:
            return False, self.failed_providers[provider_name]
        return True, ""

    def _record_decisions(
        self,
        ledger: list[dict[str, Any]],
        *,
        stage: str,
        selected: dict[str, str],
        capability: str,
    ) -> None:
        for provider in self.providers:
            available, unavailable_reason = self._provider_available(
                provider.name, capability
            )
            if provider.name not in selected:
                status = "skipped"
                reason = "not selected by the capability route for this stage"
            elif not available:
                status = "skipped"
                reason = unavailable_reason
            else:
                status = "selected"
                reason = selected[provider.name]
            ledger.append(
                {
                    "capability": "route_decision",
                    "route_stage": stage,
                    "provider": provider.name,
                    "timestamp": self._timestamp(),
                    "status": status,
                    "reason": reason,
                    "request_budget": self.budget.snapshot(),
                }
            )

    def _annotate_records(
        self,
        records: list[PaperRecord],
        *,
        provider: Provider,
        variant: QueryVariant,
        stage: str,
        route_reason: str,
        operation: str,
    ) -> None:
        fallback = stage != "targeted"
        route = {
            "provider": provider.name,
            "query_variant_id": variant.variant_id,
            "query": variant.query,
            "intent": variant.intent,
            "route_stage": stage,
            "route_reason": route_reason,
            "operation": operation,
            "fallback": fallback,
        }
        for record in records:
            if route not in record.retrieval_routes:
                record.retrieval_routes.append(dict(route))
            note_values = (
                f"query_variant={variant.variant_id}",
                f"route_stage={stage}",
                f"fallback={str(fallback).lower()}",
            )
            matching = [
                provenance
                for provenance in record.provenance
                if provenance.provider == provider.name
            ]
            if not matching:
                matching = [
                    Provenance(
                        provider=provider.name,
                        operation=operation,
                        provider_record_id=(
                            record.doi
                            or record.pmid
                            or record.openalex_id
                            or record.semantic_scholar_id
                        ),
                    )
                ]
                record.provenance.extend(matching)
            for provenance in matching:
                for note in note_values:
                    if note not in provenance.notes:
                        provenance.notes.append(note)

    def _execute(
        self,
        ledger: list[dict[str, Any]],
        *,
        provider_name: str,
        variant: QueryVariant,
        stage: str,
        route_reason: str,
        operation: str = "search",
        semantic: bool = False,
    ) -> list[PaperRecord]:
        provider = self.provider_map.get(provider_name)
        if provider is None:
            return []
        capability = "get_paper" if operation == "get_paper" else "search"
        available, reason = self._provider_available(provider_name, capability)
        request_key = (
            provider_name,
            operation,
            variant.query.casefold().strip(),
            bool(semantic),
        )
        if request_key in self.executed:
            ledger.append(
                {
                    "capability": capability,
                    "route_stage": stage,
                    "provider": provider_name,
                    "query_variant_id": variant.variant_id,
                    "query": variant.query,
                    "timestamp": self._timestamp(),
                    "status": "skipped",
                    "reason": "duplicate provider/query/operation request suppressed",
                    "request_budget": self.budget.snapshot(),
                }
            )
            return []
        if not available:
            ledger.append(
                {
                    "capability": capability,
                    "route_stage": stage,
                    "provider": provider_name,
                    "query_variant_id": variant.variant_id,
                    "query": variant.query,
                    "timestamp": self._timestamp(),
                    "status": "skipped",
                    "reason": reason,
                    "request_budget": self.budget.snapshot(),
                }
            )
            return []
        allowed, budget_reason = self.budget.can_consume(provider_name)
        if not allowed:
            ledger.append(
                {
                    "capability": capability,
                    "route_stage": stage,
                    "provider": provider_name,
                    "query_variant_id": variant.variant_id,
                    "query": variant.query,
                    "timestamp": self._timestamp(),
                    "status": "skipped",
                    "reason": budget_reason,
                    "request_budget": self.budget.snapshot(),
                }
            )
            return []

        before = self.budget.snapshot()
        self.budget.consume(provider_name)
        self.executed.add(request_key)
        started = self._timestamp()
        batch_diagnostics: dict[str, Any] = {}
        try:
            if operation == "get_paper":
                record = provider.get_paper(variant.query)
                found = [record] if record else []
            else:
                search = getattr(provider, "search_batch", provider.search)
                response = search(
                    variant.query,
                    limit=self.max_results,
                    after_date=self.after_date,
                    facet=f"{stage}:{variant.intent}",
                    filters=self.filters,
                    semantic=semantic,
                )
                if hasattr(response, "records") and hasattr(response, "diagnostics"):
                    found = response.records
                    batch_diagnostics = response.diagnostics
                else:
                    found = response
        except Exception as exc:
            message = str(exc)
            self.failed_providers[provider_name] = (
                "suppressed after an exhausted provider error: " + message
            )
            ledger.append(
                {
                    "capability": capability,
                    "route_stage": stage,
                    "route": route_reason,
                    "provider": provider_name,
                    "query_variant_id": variant.variant_id,
                    "query_variant_intent": variant.intent,
                    "query": variant.query,
                    "search_mode": "semantic" if semantic else "keyword",
                    "timestamp": started,
                    "status": "error",
                    "error": message,
                    "result_count": 0,
                    "request_budget_before": before,
                    "request_budget_after": self.budget.snapshot(),
                }
            )
            return []

        self.provider_result_counts[provider_name] = (
            self.provider_result_counts.get(provider_name, 0) + len(found)
        )
        self.completed.add(request_key)
        self._annotate_records(
            found,
            provider=provider,
            variant=variant,
            stage=stage,
            route_reason=route_reason,
            operation=operation,
        )
        ledger.append(
            {
                "capability": capability,
                "route_stage": stage,
                "route": route_reason,
                "provider": provider_name,
                "query_variant_id": variant.variant_id,
                "query_variant_intent": variant.intent,
                "query": variant.query,
                "search_mode": "semantic" if semantic else "keyword",
                "timestamp": started,
                "status": "partial" if batch_diagnostics.get("status") == "partial" else "ok",
                "result_count": len(found),
                "search_batch": batch_diagnostics,
                "request_budget_before": before,
                "request_budget_after": self.budget.snapshot(),
            }
        )
        return found

    @staticmethod
    def _coverage(records: list[PaperRecord]) -> dict[str, Any]:
        copies = [PaperRecord.from_dict(record.to_dict()) for record in records]
        unique = merge_records(copies)
        stable_count = sum(
            bool(
                record.doi
                or record.pmid
                or record.pmcid
                or record.openalex_id
                or record.semantic_scholar_id
                or record.arxiv_id
            )
            for record in unique
        )
        return {
            "unique_count": len(unique),
            "stable_identifier_count": stable_count,
            "stable_identifier_coverage": (
                stable_count / len(unique) if unique else 0.0
            ),
        }

    def _record_fallback(
        self,
        ledger: list[dict[str, Any]],
        *,
        next_stage: str,
        reasons: list[str],
        coverage: dict[str, Any],
    ) -> None:
        for reason in reasons:
            self.plan.add_fallback_reason(reason)
        ledger.append(
            {
                "capability": "fallback_trigger",
                "route_stage": next_stage,
                "timestamp": self._timestamp(),
                "status": "triggered",
                "reasons": reasons,
                "coverage": coverage,
                "request_budget": self.budget.snapshot(),
            }
        )

    def _targeted_names(self) -> list[str]:
        route = [
            str(item.get("provider") or "")
            for item in self.plan.recommended_provider_route
            if str(item.get("provider") or "") in self.provider_map
        ]
        if self.plan.identifiers:
            selected = [
                name
                for name in route
                if self._provider_available(name, "get_paper")[0]
            ]
            return selected[:3]
        selected = [
            name
            for name in route
            if self._provider_available(name, "search")[0]
            and name not in {"semantic_scholar"}
        ]
        if self.semantic_search and self._provider_available(
            "semantic_scholar", "search"
        )[0]:
            selected.append("semantic_scholar")
        return list(dict.fromkeys(selected))[:2]

    def _targeted_variant(self, provider_name: str) -> QueryVariant:
        if self.plan.identifiers:
            return self._variant("stable-identifier", "original")
        if provider_name in {"openalex", "semantic_scholar", "europe_pmc", "crossref"}:
            return self._variant(
                "english-term-expansion",
                "normalized-wide",
                "concept-wide",
                "original",
            )
        return self._variant("normalized-wide", "original", "concept-wide")

    def run(self, ledger: list[dict[str, Any]]) -> RoutingResult:
        records: list[PaperRecord] = []

        targeted_names = self._targeted_names()
        targeted_reasons = {
            name: next(
                (
                    str(item.get("role") or "capability match")
                    for item in self.plan.recommended_provider_route
                    if item.get("provider") == name
                ),
                "capability match",
            )
            for name in targeted_names
        }
        targeted_capability = "get_paper" if self.plan.identifiers else "search"
        self._record_decisions(
            ledger,
            stage="targeted",
            selected=targeted_reasons,
            capability=targeted_capability,
        )
        for name in targeted_names:
            variant = self._targeted_variant(name)
            semantic = (
                self.semantic_search
                and name == "openalex"
                and "semantic_search"
                in self.provider_map[name].status().capabilities
                and not self.plan.identifiers
            )
            records.extend(
                self._execute(
                    ledger,
                    provider_name=name,
                    variant=variant,
                    stage="targeted",
                    route_reason=targeted_reasons[name],
                    operation=(
                        "get_paper" if self.plan.identifiers else "search"
                    ),
                    semantic=semantic,
                )
            )

        targeted_coverage = self._coverage(records)
        primary = targeted_names[0] if targeted_names else ""
        general_reasons: list[str] = []
        if targeted_coverage["unique_count"] < self.fallback_threshold:
            general_reasons.append(
                "targeted route returned fewer unique records than the configured threshold"
            )
        if (
            targeted_coverage["unique_count"]
            and targeted_coverage["stable_identifier_coverage"]
            < self.stable_identifier_threshold
        ):
            general_reasons.append(
                "targeted route stable identifier coverage is below the configured threshold"
            )
        if primary and primary in self.failed_providers:
            general_reasons.append("primary provider failed")
        elif primary and self.provider_result_counts.get(primary, 0) == 0:
            general_reasons.append("primary provider returned no records")
        if self.plan.router_confidence < 0.65:
            general_reasons.append("router confidence is below 0.65")

        if general_reasons:
            self._record_fallback(
                ledger,
                next_stage="general-fallback",
                reasons=general_reasons,
                coverage=targeted_coverage,
            )
            general_selected = {
                "openalex": "broad keyword recall using the preserved original query",
                "crossref": "independent bibliographic search and DOI companion",
                "semantic_scholar": (
                    "configured semantic metadata companion within request budget"
                ),
            }
            self._record_decisions(
                ledger,
                stage="general-fallback",
                selected=general_selected,
                capability="search",
            )
            openalex_available = self._provider_available("openalex", "search")[0]
            if "openalex" in self.provider_map:
                records.extend(
                    self._execute(
                        ledger,
                        provider_name="openalex",
                        variant=self._variant("original"),
                        stage="general-fallback",
                        route_reason=general_selected["openalex"],
                    )
                )
            if "crossref" in self.provider_map:
                crossref_variant = self._unexecuted_variant(
                    "crossref",
                    "english-term-expansion",
                    *(
                        (
                            "normalized-wide",
                            "concept-wide",
                            "original",
                        )
                        if openalex_available
                        else (
                            "concept-wide",
                            "normalized-wide",
                            "original",
                        )
                    ),
                )
                records.extend(
                    self._execute(
                        ledger,
                        provider_name="crossref",
                        variant=crossref_variant,
                        stage="general-fallback",
                        route_reason=general_selected["crossref"],
                    )
                )
            if "semantic_scholar" in self.provider_map:
                records.extend(
                    self._execute(
                        ledger,
                        provider_name="semantic_scholar",
                        variant=self._variant(
                            "normalized-wide",
                            "english-term-expansion",
                            "original",
                        ),
                        stage="general-fallback",
                        route_reason=general_selected["semantic_scholar"],
                    )
                )

        post_general = self._coverage(records)
        coverage_reasons: list[str] = []
        if general_reasons:
            if post_general["unique_count"] < self.fallback_threshold:
                coverage_reasons.append(
                    "unique result coverage remains below the configured threshold"
                )
            if (
                post_general["unique_count"]
                and post_general["stable_identifier_coverage"]
                < self.stable_identifier_threshold
            ):
                coverage_reasons.append(
                    "stable identifier coverage remains below the configured threshold"
                )
            if primary and primary in self.failed_providers:
                coverage_reasons.append(
                    "the primary provider remained unavailable after bounded retries"
                )
            if self.plan.router_confidence < 0.65:
                coverage_reasons.append(
                    "low router confidence requires one bounded coverage pass"
                )

        if coverage_reasons:
            self._record_fallback(
                ledger,
                next_stage="coverage-fallback",
                reasons=coverage_reasons,
                coverage=post_general,
            )
            coverage_selected = {
                "europe_pmc": (
                    "biomedical or sparse-coverage expansion with a provider-suitable variant"
                ),
                "openalex": "single bounded expanded keyword pass",
                "crossref": "raw original-query safety fallback",
            }
            self._record_decisions(
                ledger,
                stage="coverage-fallback",
                selected=coverage_selected,
                capability="search",
            )
            if "europe_pmc" in self.provider_map:
                records.extend(
                    self._execute(
                        ledger,
                        provider_name="europe_pmc",
                        variant=self._unexecuted_variant(
                            "europe_pmc",
                            "english-term-expansion",
                            "concept-wide",
                            "normalized-wide",
                            "original",
                        ),
                        stage="coverage-fallback",
                        route_reason=coverage_selected["europe_pmc"],
                    )
                )
            if "openalex" in self.provider_map:
                records.extend(
                    self._execute(
                        ledger,
                        provider_name="openalex",
                        variant=self._unexecuted_variant(
                            "openalex",
                            "concept-wide",
                            "english-term-expansion",
                            "normalized-wide",
                            "original",
                        ),
                        stage="coverage-fallback",
                        route_reason=coverage_selected["openalex"],
                    )
                )

            # If no provider has completed the raw query, send it through one
            # remaining independent provider as the final safety route. This
            # remains inside the third stage, respects the same budget, and never
            # recurses.
            original = self._variant("original")
            original_completed = any(
                key[2] == original.query.casefold().strip()
                for key in self.completed
            )
            if not original_completed:
                safety_provider = ""
                for candidate in (
                    "crossref",
                    "openalex",
                    "europe_pmc",
                    "semantic_scholar",
                ):
                    request_key = (
                        candidate,
                        "search",
                        original.query.casefold().strip(),
                        False,
                    )
                    available, _ = self._provider_available(candidate, "search")
                    allowed, _ = self.budget.can_consume(candidate)
                    if available and allowed and request_key not in self.executed:
                        safety_provider = candidate
                        break
                if safety_provider:
                    records.extend(
                        self._execute(
                            ledger,
                            provider_name=safety_provider,
                            variant=original,
                            stage="coverage-fallback",
                            route_reason="raw original-query final safety fallback",
                        )
                    )
                else:
                    ledger.append(
                        {
                            "capability": "search",
                            "route_stage": "coverage-fallback",
                            "query_variant_id": original.variant_id,
                            "query": original.query,
                            "timestamp": self._timestamp(),
                            "status": "skipped",
                            "reason": (
                                "no unused configured provider remained within "
                                "budget for the raw original-query safety request"
                            ),
                            "request_budget": self.budget.snapshot(),
                        }
                    )

        ledger.append(
            {
                "capability": "routing_summary",
                "route_stage": "complete",
                "timestamp": self._timestamp(),
                "status": "degraded" if self.failed_providers else (
                    "partial" if any(item.get("status") == "partial" for item in ledger) else "ok"),
                "fallback_triggered": self.plan.fallback_triggered,
                "fallback_reasons": list(self.plan.fallback_reasons),
                "provider_result_counts": dict(self.provider_result_counts),
                "coverage": self._coverage(records),
                "request_budget": self.budget.snapshot(),
                "failed_providers": dict(self.failed_providers),
            }
        )
        return RoutingResult(
            records=records,
            failed_providers=dict(self.failed_providers),
            provider_result_counts=dict(self.provider_result_counts),
            budget=self.budget.snapshot(),
            request_budget=self.budget,
        )
