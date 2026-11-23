"""Multi-provider retrieval, OA enrichment, extraction, packet, and report pipeline."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from manuscript_packet import build_manuscript_packet, packet_markdown, save_packet

from .extraction import FullTextManager
from .models import PaperRecord, merge_pair, merge_records, record_score
from .providers import EasyScholarEnricher, Provider, SearchFilters, UnpaywallProvider
from .query_plan import (
    QueryPlan,
    build_query_plan,
    emergency_query_plan,
)
from .ranking import RankingReport, SemanticBackend, rank_papers, record_key
from .research_profile import EffectiveRunConfig
from .reporting import save_report
from .source_router import RequestBudget, SourceRouter


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_dict(provider: Provider) -> dict[str, Any]:
    status = provider.status()
    return {
        "name": status.name,
        "configuration": "configured" if status.enabled else "not configured",
        "capabilities": list(status.capabilities),
    }


def _record_stage(
    ledger: list[dict[str, Any]], stage: str, **details: Any
) -> None:
    ledger.append(
        {
            "capability": "pipeline_stage",
            "stage": stage,
            "timestamp": _timestamp(),
            "status": "ok",
            **details,
        }
    )


class ResearchPipeline:
    def __init__(
        self,
        providers: Iterable[Provider],
        *,
        cache_dir: str | Path,
        target_references: int = 60,
        max_results_per_provider: int = 10,
        academic: bool = True,
        after_date: str | None = None,
        manuscript_context: dict[str, Any] | None = None,
        unpaywall: UnpaywallProvider | None = None,
        easy_scholar: EasyScholarEnricher | None = None,
        search_filters: SearchFilters | None = None,
        semantic_search: bool = False,
        rank_results: bool = True,
        ranking_backends: Iterable[SemanticBackend] = (),
        resolve_oa: bool = True,
        extract_fulltext: bool = False,
        extract_limit: int = 20,
        request_budget: int = 12,
        provider_budgets: dict[str, int] | None = None,
        fallback_threshold: int = 12,
        stable_identifier_threshold: float = 0.5,
        max_query_variants: int = 6,
        allow_remote_parser: bool = False,
    ) -> None:
        self.providers = list(providers)
        if not self.providers:
            raise ValueError("At least one discovery provider is required.")
        if target_references < 1 or max_results_per_provider < 1:
            raise ValueError("Reference and result limits must be positive.")
        self.cache_dir = Path(cache_dir)
        self.target_references = target_references
        self.max_results_per_provider = max_results_per_provider
        self.academic = academic
        self.after_date = after_date
        self.manuscript_context = manuscript_context or {}
        self.unpaywall = unpaywall
        self.easy_scholar = easy_scholar
        self.search_filters = search_filters or SearchFilters()
        self.semantic_search = semantic_search
        self.rank_results = rank_results
        self.ranking_backends = list(ranking_backends)
        self.resolve_oa = resolve_oa
        self.extract_fulltext = extract_fulltext
        self.extract_limit = max(0, extract_limit)
        self.request_budget = max(1, int(request_budget))
        self.provider_budgets = dict(provider_budgets or {})
        self.fallback_threshold = max(1, int(fallback_threshold))
        self.stable_identifier_threshold = min(
            1.0, max(0.0, float(stable_identifier_threshold))
        )
        self.max_query_variants = max(1, min(6, int(max_query_variants)))
        self.allow_remote_parser = bool(allow_remote_parser)
        self._suppressed_providers: dict[str, str] = {}

    def build_query_plan(
        self,
        query: str,
        *,
        english_query: str | None = None,
        run_config: EffectiveRunConfig | None = None,
    ) -> QueryPlan:
        configured = {
            provider.name: bool(provider.status().enabled)
            for provider in self.providers
        }
        combined_filters = SearchFilters(
            after_date=self.search_filters.after_date or self.after_date,
            before_date=self.search_filters.before_date,
            fields_of_study=self.search_filters.fields_of_study,
            publication_types=self.search_filters.publication_types,
            open_access_only=self.search_filters.open_access_only,
            min_citation_count=self.search_filters.min_citation_count,
        )
        return build_query_plan(
            query,
            english_query=english_query,
            filters=combined_filters,
            academic=self.academic,
            semantic_search=self.semantic_search,
            max_variants=(
                run_config.max_query_variants
                if run_config is not None
                else self.max_query_variants
            ),
            global_request_budget=(
                run_config.request_budget
                if run_config is not None
                else self.request_budget
            ),
            provider_budgets=(
                run_config.provider_budgets
                if run_config is not None
                else self.provider_budgets
            ),
            provider_configuration=configured,
            research_profile=(
                run_config.research_profile_payload()
                if run_config is not None
                else None
            ),
        )

    def _recommend(
        self,
        records: list[PaperRecord],
        *,
        positive_seeds: list[str],
        negative_seeds: list[str],
        graph_limit: int,
        ledger: list[dict[str, Any]],
        request_budget: RequestBudget,
    ) -> list[PaperRecord]:
        expanded = list(records)
        for provider in self.providers:
            status = provider.status()
            if provider.name in self._suppressed_providers:
                ledger.append(
                    {
                        "capability": "recommend",
                        "provider": provider.name,
                        "timestamp": _timestamp(),
                        "status": "skipped",
                        "reason": self._suppressed_providers[provider.name],
                        "request_budget": request_budget.snapshot(),
                    }
                )
                continue
            if "recommend" not in status.capabilities:
                continue
            recommendation_status = getattr(provider, "recommendation_status", None)
            capability_status = recommendation_status() if recommendation_status else status
            started = _timestamp()
            if not capability_status.enabled:
                ledger.append(
                    {
                        "capability": "recommend",
                        "provider": provider.name,
                        "timestamp": started,
                        "status": "skipped",
                        "reason": capability_status.reason,
                        "request_budget": request_budget.snapshot(),
                    }
                )
                continue
            allowed, budget_reason = request_budget.can_consume(provider.name)
            if not allowed:
                ledger.append(
                    {
                        "capability": "recommend",
                        "provider": provider.name,
                        "timestamp": started,
                        "status": "skipped",
                        "reason": budget_reason,
                        "request_budget": request_budget.snapshot(),
                    }
                )
                continue
            before = request_budget.snapshot()
            request_budget.consume(provider.name)
            try:
                values = provider.recommend(  # type: ignore[attr-defined]
                    positive_seeds,
                    negative_identifiers=negative_seeds,
                    limit=graph_limit,
                )
            except Exception as exc:
                ledger.append(
                    {
                        "capability": "recommend",
                        "provider": provider.name,
                        "timestamp": started,
                        "status": "error",
                        "error": str(exc),
                        "request_budget_before": before,
                        "request_budget_after": request_budget.snapshot(),
                    }
                )
                continue
            expanded.extend(values)
            ledger.append(
                {
                    "capability": "recommend",
                    "provider": provider.name,
                    "timestamp": started,
                    "status": "ok",
                    "positive_seed_count": len(positive_seeds),
                    "negative_seed_count": len(negative_seeds),
                    "result_count": len(values),
                    "request_budget_before": before,
                    "request_budget_after": request_budget.snapshot(),
                }
            )
        return expanded

    def _rank(
        self,
        query: str,
        records: list[PaperRecord],
        ledger: list[dict[str, Any]],
        *,
        preliminary: bool = False,
    ) -> tuple[list[PaperRecord], RankingReport | None]:
        if not self.rank_results:
            records.sort(key=record_score, reverse=True)
            return records, None
        report = rank_papers(
            query,
            records,
            context=self._ranking_context(),
            semantic_backends=[] if preliminary else self.ranking_backends,
        )
        ordered = [result.record for result in report.ranked]
        ordered.extend(record for record in records if record.is_retracted)
        if not preliminary:
            ledger.append(
                {
                    "capability": "ranking",
                    "timestamp": _timestamp(),
                    "status": "degraded" if report.backend_errors else "ok",
                    "ranked_count": len(report.ranked),
                    "excluded_count": len(report.excluded),
                    "backend_errors": report.backend_errors,
                    "components": [
                        "title_match",
                        "abstract_match",
                        "method_match",
                        "field_match",
                        "year_fit",
                        "semantic_similarity",
                        "seed_graph_proximity",
                        "evidence_availability",
                        "normalized_citation_signal",
                    ],
                }
            )
        return ordered, report

    def _ranking_context(self) -> dict[str, Any]:
        """Combine manuscript context with neutral filters used for discovery."""
        context = dict(self.manuscript_context)
        existing_fields = context.get("fields", context.get("fields_of_study", ()))
        if isinstance(existing_fields, str):
            fields = [existing_fields]
        else:
            fields = [str(value) for value in existing_fields or ()]
        fields.extend(self.search_filters.fields_of_study)
        if fields:
            context["fields"] = list(dict.fromkeys(fields))
        if not any(name in context for name in ("after_year", "year_from", "after_date")):
            after_date = self.search_filters.after_date or self.after_date
            if after_date:
                context["after_date"] = after_date
        if not any(name in context for name in ("before_year", "year_to", "before_date")):
            if self.search_filters.before_date:
                context["before_date"] = self.search_filters.before_date
        return context

    def _expand_graph(
        self,
        records: list[PaperRecord],
        seed_identifier: str,
        *,
        graph_limit: int,
        ledger: list[dict[str, Any]],
        request_budget: RequestBudget,
    ) -> list[PaperRecord]:
        expanded = list(records)
        for provider in self.providers:
            status = provider.status()
            if provider.name in self._suppressed_providers:
                ledger.append(
                    {
                        "capability": "citation_graph",
                        "provider": provider.name,
                        "seed": seed_identifier,
                        "timestamp": _timestamp(),
                        "status": "skipped",
                        "reason": self._suppressed_providers[provider.name],
                    }
                )
                continue
            if not status.enabled:
                ledger.append(
                    {
                        "capability": "citation_graph",
                        "provider": provider.name,
                        "seed": seed_identifier,
                        "timestamp": _timestamp(),
                        "status": "skipped",
                        "reason": status.reason,
                    }
                )
                continue
            for operation in ("get_citations", "get_references"):
                if operation not in status.capabilities:
                    continue
                allowed, budget_reason = request_budget.can_consume(provider.name)
                if not allowed:
                    ledger.append(
                        {
                            "capability": operation,
                            "provider": provider.name,
                            "seed": seed_identifier,
                            "timestamp": _timestamp(),
                            "status": "skipped",
                            "reason": budget_reason,
                            "request_budget": request_budget.snapshot(),
                        }
                    )
                    continue
                before = request_budget.snapshot()
                request_budget.consume(provider.name)
                started = _timestamp()
                try:
                    values = getattr(provider, operation)(seed_identifier, limit=graph_limit)
                except Exception as exc:
                    ledger.append(
                        {
                            "capability": operation,
                            "provider": provider.name,
                            "seed": seed_identifier,
                            "timestamp": started,
                            "status": "error",
                            "error": str(exc),
                            "request_budget_before": before,
                            "request_budget_after": request_budget.snapshot(),
                        }
                    )
                    continue
                expanded.extend(values)
                ledger.append(
                    {
                        "capability": operation,
                        "provider": provider.name,
                        "seed": seed_identifier,
                        "timestamp": started,
                        "status": "ok",
                        "result_count": len(values),
                        "request_budget_before": before,
                        "request_budget_after": request_budget.snapshot(),
                    }
                )
        return expanded

    def _resolve_open_access(
        self,
        records: list[PaperRecord],
        ledger: list[dict[str, Any]],
        *,
        enabled: bool,
        target_references: int,
    ) -> list[PaperRecord]:
        if not enabled or not self.unpaywall:
            return records
        status = self.unpaywall.status()
        if not status.enabled:
            ledger.append(
                {
                    "capability": "resolve_fulltext",
                    "provider": self.unpaywall.name,
                    "timestamp": _timestamp(),
                    "status": "skipped",
                    "reason": status.reason,
                }
            )
            return records
        for record in records[:target_references]:
            if not record.doi:
                continue
            started = _timestamp()
            try:
                enriched = self.unpaywall.get_paper(record.doi)
            except Exception as exc:
                ledger.append(
                    {
                        "capability": "resolve_fulltext",
                        "provider": self.unpaywall.name,
                        "doi": record.doi,
                        "timestamp": started,
                        "status": "error",
                        "error": str(exc),
                    }
                )
                continue
            if enriched:
                merge_pair(record, enriched)
            ledger.append(
                {
                    "capability": "resolve_fulltext",
                    "provider": self.unpaywall.name,
                    "doi": record.doi,
                    "timestamp": started,
                    "status": "ok",
                    "location_count": len(enriched.fulltext_locations) if enriched else 0,
                }
            )
        return records

    def _extract(
        self,
        records: list[PaperRecord],
        packet_dir: Path,
        *,
        enabled: bool,
        extract_limit: int,
    ) -> list[dict[str, Any]]:
        if not enabled or not extract_limit:
            return []
        manager = FullTextManager(
            cache_dir=self.cache_dir,
            allow_remote_parser=self.allow_remote_parser,
        )
        extraction_ledger: list[dict[str, Any]] = []
        candidates = sorted(
            records,
            key=lambda record: (
                float(record.ranking.get("total_score") or 0.0),
                record_score(record),
            ),
            reverse=True,
        )
        processed = 0
        for record in candidates:
            if processed >= extract_limit:
                break
            if not manager.ranked_locations(record):
                continue
            processed += 1
            _, attempts = manager.download_and_extract(
                record,
                directory=packet_dir / "fulltext",
            )
            extraction_ledger.append(
                {
                    "record": record.doi or record.pmid or record.title,
                    "timestamp": _timestamp(),
                    "attempts": attempts,
                }
            )
        return extraction_ledger

    @staticmethod
    def _record_profile_outcome(
        ledger: list[dict[str, Any]],
        *,
        run_config: EffectiveRunConfig | None,
        query_plan: QueryPlan,
        request_budget: RequestBudget,
        positive_seed_requested: bool,
        citation_seed_requested: bool,
        extraction_ledger: list[dict[str, Any]],
    ) -> None:
        route_order = ("targeted", "general-fallback", "coverage-fallback")
        executed_stages = {
            str(item.get("route_stage"))
            for item in ledger
            if item.get("route_stage") in route_order
            and item.get("status") in {"ok", "error"}
        }
        providers_attempted = sorted(
            {
                str(item.get("provider"))
                for item in ledger
                if item.get("route_stage") in route_order
                and item.get("status") in {"ok", "error"}
                and item.get("provider")
            }
        )
        graph_requested = positive_seed_requested or citation_seed_requested
        graph_capabilities = {
            "recommend",
            "citation_graph",
            "get_citations",
            "get_references",
        }
        graph_entries = [
            item
            for item in ledger
            if item.get("capability") in graph_capabilities
        ]
        graph_performed = any(
            item.get("status") == "ok"
            and item.get("capability")
            in {"recommend", "get_citations", "get_references"}
            for item in graph_entries
        )
        if not graph_requested:
            graph_skip_reason = "no-seed-supplied"
        elif graph_performed:
            graph_skip_reason = ""
        elif any(
            "budget exhausted" in str(item.get("reason") or "").casefold()
            for item in graph_entries
        ):
            graph_skip_reason = "request-budget-exhausted"
        else:
            graph_skip_reason = "no-successful-graph-request"

        parsed_records = sum(
            any(attempt.get("status") == "ok" for attempt in item.get("attempts") or [])
            for item in extraction_ledger
        )
        budget_snapshot = request_budget.snapshot()
        _record_stage(
            ledger,
            "research-profile-outcome",
            effective_level=(
                run_config.decision.effective_level
                if run_config is not None
                else "standard"
            ),
            requests_used=budget_snapshot["global"]["used"],
            request_budget=budget_snapshot,
            query_variants_built=len(query_plan.query_variants),
            providers_attempted=providers_attempted,
            route_stages_executed=[
                stage for stage in route_order if stage in executed_stages
            ],
            fallback_stages_executed=[
                stage
                for stage in route_order[1:]
                if stage in executed_stages
            ],
            graph_requested=graph_requested,
            graph_expansion_performed=graph_performed,
            graph_skip_reason=graph_skip_reason,
            fulltext_attempted=len(extraction_ledger),
            fulltext_parsed=parsed_records,
        )

    def run(
        self,
        query: str,
        *,
        english_query: str | None = None,
        packet_dir: str | Path | None = None,
        citation_seed: str | None = None,
        graph_limit: int | None = None,
        positive_seeds: Iterable[str] = (),
        negative_seeds: Iterable[str] = (),
        run_config: EffectiveRunConfig | None = None,
    ) -> dict[str, Any]:
        target_references = (
            run_config.target_references
            if run_config is not None
            else self.target_references
        )
        max_results = (
            run_config.max_results
            if run_config is not None
            else self.max_results_per_provider
        )
        request_budget_limit = (
            run_config.request_budget
            if run_config is not None
            else self.request_budget
        )
        provider_budgets = (
            dict(run_config.provider_budgets)
            if run_config is not None
            else self.provider_budgets
        )
        fallback_threshold = (
            run_config.fallback_threshold
            if run_config is not None
            else self.fallback_threshold
        )
        stable_identifier_threshold = (
            run_config.stable_identifier_threshold
            if run_config is not None
            else self.stable_identifier_threshold
        )
        resolve_oa = (
            run_config.resolve_oa
            if run_config is not None
            else self.resolve_oa
        )
        easy_scholar_enabled = (
            run_config.easy_scholar
            if run_config is not None
            else True
        )
        extract_fulltext = (
            run_config.extract_fulltext
            if run_config is not None
            else self.extract_fulltext
        )
        extract_limit = (
            run_config.extract_limit
            if run_config is not None
            else self.extract_limit
        )
        effective_graph_limit = (
            run_config.graph_limit
            if run_config is not None
            else max(1, int(graph_limit if graph_limit is not None else 50))
        )
        if (
            self.allow_remote_parser
            and extract_fulltext
            and run_config is not None
            and run_config.explicit_overrides.get("extract_fulltext") is not True
        ):
            raise ValueError(
                "Remote parsing requires an explicit extract_fulltext=True "
                "override; research level and auto intent cannot authorize upload."
            )
        if extract_fulltext and packet_dir is None:
            raise ValueError(
                "Full-text extraction requires packet_dir so source files have "
                "an audit location."
            )

        ledger: list[dict[str, Any]] = []
        self._suppressed_providers = {}
        if run_config is not None:
            _record_stage(
                ledger,
                "research-level-selection",
                **run_config.research_profile_payload(),
            )
        try:
            query_plan = self.build_query_plan(
                query,
                english_query=english_query,
                run_config=run_config,
            )
        except Exception as exc:
            query_plan = emergency_query_plan(
                query,
                filters=self.search_filters,
                error=str(exc),
                global_request_budget=request_budget_limit,
                provider_budgets=provider_budgets,
                research_profile=(
                    run_config.research_profile_payload()
                    if run_config is not None
                    else None
                ),
            )
        _record_stage(
            ledger,
            "question-decomposition",
            original_query=query,
            query_plan=query_plan.to_dict(),
        )
        router = SourceRouter(
            self.providers,
            query_plan=query_plan,
            filters=self.search_filters,
            max_results_per_request=max_results,
            fallback_threshold=min(
                target_references,
                fallback_threshold,
            ),
            stable_identifier_threshold=stable_identifier_threshold,
            after_date=self.after_date,
            semantic_search=self.semantic_search,
        )
        routing_result = router.run(ledger)
        records = routing_result.records
        request_budget = routing_result.request_budget
        self._suppressed_providers = dict(routing_result.failed_providers)
        _record_stage(
            ledger,
            "multi-source-retrieval",
            retrieved_records=len(records),
            fallback_triggered=query_plan.fallback_triggered,
            request_budget=routing_result.budget,
        )
        positive = [value for value in positive_seeds if str(value).strip()]
        negative = [value for value in negative_seeds if str(value).strip()]
        if positive:
            records = self._recommend(
                records,
                positive_seeds=positive,
                negative_seeds=negative,
                graph_limit=effective_graph_limit,
                ledger=ledger,
                request_budget=request_budget,
            )
            _record_stage(
                ledger,
                "seed-paper-recommendations",
                records_after_recommendations=len(records),
            )
        if citation_seed:
            records = self._expand_graph(
                records,
                citation_seed,
                graph_limit=effective_graph_limit,
                ledger=ledger,
                request_budget=request_budget,
            )
            _record_stage(ledger, "citation-graph-expansion", records_after_graph=len(records))
        _record_stage(
            ledger,
            "request-budget-finalization",
            request_budget=request_budget.snapshot(),
        )
        records_before_merge = len(records)
        records = merge_records(records)
        _record_stage(
            ledger,
            "deduplication-and-ranking",
            input_records=records_before_merge,
            unique_records=len(records),
        )
        if not records:
            self._record_profile_outcome(
                ledger,
                run_config=run_config,
                query_plan=query_plan,
                request_budget=request_budget,
                positive_seed_requested=bool(positive),
                citation_seed_requested=bool(citation_seed),
                extraction_ledger=[],
            )
            return {
                "success": False,
                "query": query,
                "query_plan": query_plan.to_dict(),
                "error": "No provider returned usable records.",
                "timestamp": _timestamp(),
                "backend": "multi-source",
                "provider_status": [_status_dict(provider) for provider in self.providers],
                "search_ledger": ledger,
                "request_budget": request_budget.snapshot(),
            }
        records, ranking_report = self._rank(
            query_plan.ranking_query(),
            records,
            ledger,
            preliminary=True,
        )
        records = self._resolve_open_access(
            records,
            ledger,
            enabled=resolve_oa,
            target_references=target_references,
        )
        _record_stage(
            ledger,
            "open-access-resolution",
            enabled=resolve_oa,
            open_access_records=sum(record.is_open_access is True for record in records),
        )
        if (
            easy_scholar_enabled
            and self.easy_scholar
            and self.easy_scholar.status().enabled
        ):
            try:
                records = self.easy_scholar.enrich(records)
                ledger.append(
                    {
                        "capability": "journal_enrichment",
                        "provider": self.easy_scholar.name,
                        "timestamp": _timestamp(),
                        "status": "ok",
                        "record_count": len(records),
                    }
                )
            except Exception as exc:
                ledger.append(
                    {
                        "capability": "journal_enrichment",
                        "provider": self.easy_scholar.name,
                        "timestamp": _timestamp(),
                        "status": "error",
                        "error": str(exc),
                    }
                )
        elif self.easy_scholar:
            reason = (
                self.easy_scholar.status().reason
                if easy_scholar_enabled
                else "disabled by effective research profile"
            )
            ledger.append(
                {
                    "capability": "journal_enrichment",
                    "provider": self.easy_scholar.name,
                    "timestamp": _timestamp(),
                    "status": "skipped",
                    "reason": reason,
                }
            )

        records, ranking_report = self._rank(
            query_plan.ranking_query(),
            records,
            ledger,
        )
        destination = Path(packet_dir) if packet_dir else None
        extraction_ledger = (
            self._extract(
                records,
                destination,
                enabled=extract_fulltext,
                extract_limit=extract_limit,
            )
            if destination
            else []
        )
        _record_stage(
            ledger,
            "full-text-extraction",
            attempted_records=len(extraction_ledger),
            enabled=extract_fulltext,
            record_limit=extract_limit,
        )
        _record_stage(
            ledger,
            "identifier-and-citation-verification",
            stable_identifier_records=sum(
                bool(
                    record.doi
                    or record.pmid
                    or record.pmcid
                    or record.openalex_id
                    or record.semantic_scholar_id
                )
                for record in records
            ),
        )
        _record_stage(
            ledger,
            "evidence-matrix-and-synthesis",
            candidate_records=len(records),
        )
        self._record_profile_outcome(
            ledger,
            run_config=run_config,
            query_plan=query_plan,
            request_budget=request_budget,
            positive_seed_requested=bool(positive),
            citation_seed_requested=bool(citation_seed),
            extraction_ledger=extraction_ledger,
        )
        packet = build_manuscript_packet(
            query=query,
            records=records,
            search_ledger=ledger,
            target_references=target_references,
            manuscript_context=self.manuscript_context,
            extraction_ledger=extraction_ledger,
            query_plan=query_plan.to_dict(),
        )
        artifacts: dict[str, str] = {}
        if destination:
            artifacts.update(save_packet(packet, destination))
            artifacts.update(save_report(packet, destination))
        return {
            "success": True,
            "query": query,
            "query_plan": query_plan.to_dict(),
            "response": packet_markdown(packet),
            "timestamp": _timestamp(),
            "backend": "multi-source",
            "model": "deterministic-evidence-pipeline",
            "academic": self.academic,
            "provider_status": [_status_dict(provider) for provider in self.providers],
            "references": packet["references"],
            "recommendations": [
                {
                    "record_key": record_key(item.record),
                    "rank": item.rank,
                    "total_score": round(item.total_score, 6),
                    "preprint": item.preprint,
                    "components": {
                        name: component.to_dict()
                        for name, component in item.components.items()
                    },
                }
                for item in (ranking_report.ranked if ranking_report else [])
            ],
            "ranking": {
                "backend_errors": ranking_report.backend_errors if ranking_report else [],
                "excluded": ranking_report.excluded if ranking_report else [],
            },
            "sources": [
                {
                    "title": item["title"],
                    "url": item["url"],
                    "doi": item["doi"],
                    "providers": item["providers"],
                }
                for item in packet["references"]
            ],
            "citations": [
                {
                    "type": "doi" if item["doi"] else "source",
                    "title": item["title"],
                    "url": f"https://doi.org/{item['doi']}" if item["doi"] else item["url"],
                    "doi": item["doi"],
                }
                for item in packet["references"]
                if item["doi"] or item["url"]
            ],
            "search_ledger": ledger,
            "request_budget": request_budget.snapshot(),
            "packet": packet,
            "artifacts": artifacts,
        }
