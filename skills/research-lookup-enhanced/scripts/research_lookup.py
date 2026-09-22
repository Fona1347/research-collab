#!/usr/bin/env python3
"""Multi-source scholarly lookup without Parallel CLI or paid research backends."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

from rle.pipeline import ResearchPipeline
from rle.providers import (
    EasyScholarEnricher,
    SearchFilters,
    UnpaywallProvider,
    build_provider,
)
from rle.ranking import SemanticBackend, Specter2Backend
from rle.research_profile import EffectiveRunConfig, ResearchLevelResolver


DEFAULT_PROVIDERS = "openalex,semantic_scholar,crossref,europe_pmc"


def _load_context(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("The manuscript context file must contain a JSON object.")
    return payload


def _provider_names(value: str) -> list[str]:
    names = [part.strip() for part in value.split(",") if part.strip()]
    return list(dict.fromkeys(names))


def _provider_budgets(values: list[str]) -> dict[str, int]:
    budgets: dict[str, int] = {}
    for raw in values:
        if "=" not in raw:
            raise ValueError(
                f"Invalid --provider-budget value {raw!r}; expected PROVIDER=COUNT"
            )
        provider, count = raw.split("=", 1)
        name = provider.strip().lower().replace("-", "_")
        if not name:
            raise ValueError("Provider budget name cannot be empty.")
        try:
            parsed = int(count)
        except ValueError as exc:
            raise ValueError(
                f"Invalid request count for provider {provider!r}: {count!r}"
            ) from exc
        if parsed < 0:
            raise ValueError("Provider request budgets cannot be negative.")
        budgets[name] = parsed
    return budgets


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60] or "research"


class ResearchLookup:
    """Reusable wrapper around the provider-neutral research pipeline."""

    def __init__(
        self,
        *,
        providers: list[str] | None = None,
        cache_dir: str | Path = ".cache/research-lookup-enhanced",
        academic: bool = True,
        research_level: str | None = None,
        research_level_source: str | None = None,
        research_level_reason: str | None = None,
        target_references: int | None = None,
        max_results: int | None = None,
        after_date: str | None = None,
        search_filters: SearchFilters | None = None,
        semantic_search: bool = False,
        rank_results: bool = True,
        ranking_backends: list[SemanticBackend] | None = None,
        manuscript_context: dict[str, Any] | None = None,
        resolve_oa: bool | None = None,
        easy_scholar: bool | None = None,
        extract_fulltext: bool | None = None,
        extract_limit: int | None = None,
        request_budget: int | None = None,
        provider_budgets: dict[str, int] | None = None,
        fallback_threshold: int | None = None,
        stable_identifier_threshold: float | None = None,
        max_query_variants: int | None = None,
        graph_limit: int | None = None,
        allow_remote_parser: bool = False,
    ) -> None:
        if allow_remote_parser and extract_fulltext is not True:
            raise ValueError(
                "allow_remote_parser requires explicit extract_fulltext=True"
            )
        cache = Path(cache_dir)
        discovery = [
            build_provider(name, cache_dir=cache)
            for name in (providers or _provider_names(DEFAULT_PROVIDERS))
            if name.replace("-", "_") not in {"unpaywall", "easy_scholar"}
        ]
        unpaywall = UnpaywallProvider(cache_dir=cache) if resolve_oa is not False else None
        journal_enricher = (
            EasyScholarEnricher(cache_dir=cache)
            if easy_scholar is not False
            else None
        )
        self.research_level = research_level
        self.research_level_source = research_level_source
        self.research_level_reason = research_level_reason
        self.resolver = ResearchLevelResolver()
        self._profile_overrides: dict[str, Any] = {
            name: value
            for name, value in {
                "target_references": target_references,
                "max_results": max_results,
                "request_budget": request_budget,
                "fallback_threshold": fallback_threshold,
                "stable_identifier_threshold": stable_identifier_threshold,
                "max_query_variants": max_query_variants,
                "resolve_oa": resolve_oa,
                "easy_scholar": easy_scholar,
                "extract_fulltext": extract_fulltext,
                "extract_limit": extract_limit,
                "graph_limit": graph_limit,
            }.items()
            if value is not None
        }
        if provider_budgets:
            self._profile_overrides["provider_budgets"] = dict(provider_budgets)
        self.pipeline = ResearchPipeline(
            discovery,
            cache_dir=cache,
            target_references=target_references or 60,
            max_results_per_provider=max_results or 10,
            academic=academic,
            after_date=after_date,
            search_filters=search_filters,
            semantic_search=semantic_search,
            rank_results=rank_results,
            ranking_backends=ranking_backends or [],
            manuscript_context=manuscript_context,
            unpaywall=unpaywall,
            easy_scholar=journal_enricher,
            resolve_oa=True if resolve_oa is None else resolve_oa,
            extract_fulltext=False if extract_fulltext is None else extract_fulltext,
            extract_limit=20 if extract_limit is None else extract_limit,
            request_budget=12 if request_budget is None else request_budget,
            provider_budgets=provider_budgets,
            fallback_threshold=12 if fallback_threshold is None else fallback_threshold,
            stable_identifier_threshold=(
                0.5
                if stable_identifier_threshold is None
                else stable_identifier_threshold
            ),
            max_query_variants=6 if max_query_variants is None else max_query_variants,
            allow_remote_parser=allow_remote_parser,
        )

    def _resolve_run_config(
        self,
        query: str,
        *,
        graph_limit: int | None = None,
    ) -> EffectiveRunConfig:
        overrides = dict(self._profile_overrides)
        if graph_limit is not None:
            overrides["graph_limit"] = graph_limit
        return self.resolver.resolve(
            query,
            requested_level=self.research_level,
            source=self.research_level_source,
            reason=self.research_level_reason,
            explicit_overrides=overrides,
        )

    def plan(
        self,
        query: str,
        *,
        english_query: str | None = None,
    ) -> dict[str, Any]:
        run_config = self._resolve_run_config(query)
        return self.pipeline.build_query_plan(
            query,
            english_query=english_query,
            run_config=run_config,
        ).to_dict()

    def lookup(
        self,
        query: str,
        *,
        english_query: str | None = None,
        packet_dir: str | Path | None = None,
        citation_seed: str | None = None,
        graph_limit: int | None = None,
        positive_seeds: list[str] | None = None,
        negative_seeds: list[str] | None = None,
    ) -> dict[str, Any]:
        run_config: EffectiveRunConfig | None = None
        try:
            run_config = self._resolve_run_config(query, graph_limit=graph_limit)
            return self.pipeline.run(
                query,
                english_query=english_query,
                packet_dir=packet_dir,
                citation_seed=citation_seed,
                positive_seeds=positive_seeds or [],
                negative_seeds=negative_seeds or [],
                run_config=run_config,
            )
        except Exception as exc:
            failure = {
                "success": False,
                "query": query,
                "backend": "multi-source",
                "model": "deterministic-evidence-pipeline",
                "error": str(exc),
            }
            if run_config is not None:
                failure["research_profile"] = run_config.research_profile_payload()
            return failure

    def batch_lookup(
        self,
        queries: list[str],
        *,
        english_query: str | None = None,
        packet_dir: str | Path | None = None,
        delay: float = 0.25,
        citation_seed: str | None = None,
        graph_limit: int | None = None,
        positive_seeds: list[str] | None = None,
        negative_seeds: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        if english_query is not None and len(queries) != 1:
            raise ValueError(
                "english_query applies to exactly one query; run multilingual "
                "batch items independently"
            )
        results: list[dict[str, Any]] = []
        for index, query in enumerate(queries):
            if index and delay > 0:
                time.sleep(min(delay, 60.0))
            destination = None
            if packet_dir:
                destination = Path(packet_dir)
                if len(queries) > 1:
                    destination = destination / f"{index + 1:02d}-{_slug(query)}"
            results.append(
                self.lookup(
                    query,
                    english_query=english_query,
                    packet_dir=destination,
                    citation_seed=citation_seed,
                    graph_limit=graph_limit,
                    positive_seeds=positive_seeds,
                    negative_seeds=negative_seeds,
                )
            )
        return results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Open multi-source scholarly research and evidence packet compiler",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python research_lookup.py "CRISPR off-target effects" --academic \
    --packet-dir sources/crispr --json

  python research_lookup.py "memristor endurance variability" \
    --providers openalex,crossref,europe_pmc --no-resolve-oa

  python research_lookup.py "topic" --citation-seed DOI:10.1000/example \
    --graph-limit 30 --packet-dir sources/topic
        """,
    )
    parser.add_argument("query", nargs="?", help="Research question or topic")
    parser.add_argument("--batch", nargs="+", help="Run multiple queries")
    parser.add_argument(
        "--english-query",
        help=(
            "Caller-supplied English scholarly query variant for one Chinese or "
            "mixed query; never replaces the original query"
        ),
    )
    parser.add_argument(
        "--providers",
        default=DEFAULT_PROVIDERS,
        help="Comma-separated discovery providers",
    )
    parser.add_argument(
        "--academic",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Plan bounded evidence-coverage routing (default: enabled)",
    )
    parser.add_argument(
        "--research-level",
        choices=("auto", "quick", "standard", "deep"),
        help="Research depth; omitted preserves the standard profile",
    )
    parser.add_argument(
        "--research-level-source",
        choices=("explicit-user-intent", "agent-inference"),
        help="Audit source for an Agent-supplied non-auto research level",
    )
    parser.add_argument(
        "--research-level-reason",
        help="Audit-only explanation for an explicitly selected research level",
    )
    parser.add_argument("--target-references", type=int, default=None)
    parser.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Override the Profile's records-per-provider-request limit",
    )
    parser.add_argument("--after-date", help="Publication cutoff in YYYY-MM-DD form")
    parser.add_argument("--before-date", help="Upper publication cutoff in YYYY-MM-DD form")
    parser.add_argument(
        "--field",
        action="append",
        default=[],
        help="Provider field-of-study filter; repeat for multiple values",
    )
    parser.add_argument(
        "--publication-type",
        action="append",
        default=[],
        help="Provider publication-type filter; repeat for multiple values",
    )
    parser.add_argument(
        "--open-access-only",
        action="store_true",
        help="Request open-access records where the provider supports that filter",
    )
    parser.add_argument("--min-citations", type=int)
    parser.add_argument(
        "--semantic-search",
        action="store_true",
        help="Add an OpenAlex search.semantic companion pass",
    )
    parser.add_argument(
        "--rank",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Apply explainable relevance ranking (default: enabled)",
    )
    parser.add_argument(
        "--specter2",
        action="store_true",
        help="Use an installed/cached SPECTER2 model as an optional ranking backend",
    )
    parser.add_argument(
        "--allow-model-download",
        action="store_true",
        help="Permit --specter2 to download missing model files",
    )
    parser.add_argument("--context-file", help="JSON object with manuscript context")
    parser.add_argument(
        "--cache-dir",
        default=".cache/research-lookup-enhanced",
        help="HTTP response cache directory",
    )
    parser.add_argument(
        "--resolve-oa",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override Profile OA-location resolution",
    )
    parser.add_argument(
        "--easy-scholar",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Override Profile venue-metric enrichment",
    )
    parser.add_argument(
        "--extract-fulltext",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Explicitly enable or disable legal-OA full-text extraction",
    )
    parser.add_argument("--extract-limit", type=int, default=None)
    parser.add_argument(
        "--allow-remote-parser",
        action="store_true",
        help="Allow explicitly OA PDFs to be uploaded through the MinerU wrapper",
    )
    parser.add_argument(
        "--request-budget",
        type=int,
        default=None,
        help="Override the Profile's routed discovery/graph request budget",
    )
    parser.add_argument(
        "--provider-budget",
        action="append",
        default=[],
        metavar="PROVIDER=COUNT",
        help="Override one provider request budget; repeatable",
    )
    parser.add_argument(
        "--fallback-threshold",
        type=int,
        default=None,
        help="Override the Profile's bounded fallback threshold",
    )
    parser.add_argument(
        "--stable-id-threshold",
        type=float,
        default=None,
        help="Override stable-identifier coverage threshold in the 0..1 range",
    )
    parser.add_argument(
        "--max-query-variants",
        type=int,
        default=None,
        help="Deterministic query-variant cap; hard-capped at 6",
    )
    parser.add_argument("--citation-seed", help="DOI/PMID/provider ID for graph expansion")
    parser.add_argument(
        "--positive-seed",
        action="append",
        default=[],
        help="Relevant seed paper ID for Semantic Scholar recommendations; repeatable",
    )
    parser.add_argument(
        "--negative-seed",
        action="append",
        default=[],
        help="Irrelevant seed paper ID for Semantic Scholar recommendations; repeatable",
    )
    parser.add_argument("--graph-limit", type=int, default=None)
    parser.add_argument("--packet-dir", help="Write packet and report artifacts here")
    parser.add_argument("--batch-delay", type=float, default=0.25)
    parser.add_argument("--show-provider-status", action="store_true")
    parser.add_argument(
        "--show-query-plan",
        action="store_true",
        help="Build and print the deterministic QueryPlan without network requests",
    )
    parser.add_argument("-o", "--output", help="Write the primary CLI output")
    parser.add_argument("--json", action="store_true", help="Render result envelopes as JSON")
    return parser


def _render_human(results: list[dict[str, Any]]) -> str:
    blocks: list[str] = []
    for index, result in enumerate(results, start=1):
        if not result.get("success"):
            blocks.append(f"Query {index} failed: {result.get('error', 'unknown error')}")
            continue
        blocks.append(str(result.get("response") or ""))
        if result.get("artifacts"):
            blocks.append("Artifacts:\n" + "\n".join(
                f"- {name}: {path}" for name, path in result["artifacts"].items()
            ))
    return "\n\n".join(blocks).rstrip() + "\n"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if (
        not args.query
        and not args.batch
        and not args.show_provider_status
    ):
        parser.print_help()
        return 1
    try:
        if (
            args.extract_fulltext is True
            and not args.packet_dir
            and not args.show_query_plan
        ):
            raise ValueError("--extract-fulltext requires --packet-dir so source files have an audit location")
        if args.allow_remote_parser and args.extract_fulltext is not True:
            raise ValueError(
                "--allow-remote-parser requires explicit --extract-fulltext"
            )
        if args.allow_model_download and not args.specter2:
            raise ValueError("--allow-model-download requires --specter2")
        if (
            args.research_level_source is not None
            or args.research_level_reason is not None
        ) and args.research_level in {None, "auto"}:
            raise ValueError(
                "--research-level-source/--research-level-reason require an "
                "explicit quick, standard, or deep level"
            )
        if args.show_query_plan and (not args.query or args.batch):
            raise ValueError("--show-query-plan requires one positional query")
        if args.english_query is not None and args.batch and len(args.batch) != 1:
            raise ValueError(
                "--english-query applies to exactly one query; run multilingual "
                "batch items independently"
            )
        if (
            args.stable_id_threshold is not None
            and not 0.0 <= args.stable_id_threshold <= 1.0
        ):
            raise ValueError("--stable-id-threshold must be between 0 and 1")
        ranking_backends: list[SemanticBackend] = []
        if args.specter2:
            ranking_backends.append(
                Specter2Backend(allow_model_download=args.allow_model_download)
            )
        research = ResearchLookup(
            providers=_provider_names(args.providers),
            cache_dir=args.cache_dir,
            academic=args.academic,
            research_level=args.research_level,
            research_level_source=args.research_level_source,
            research_level_reason=args.research_level_reason,
            target_references=args.target_references,
            max_results=args.max_results,
            after_date=args.after_date,
            search_filters=SearchFilters(
                before_date=args.before_date,
                fields_of_study=tuple(args.field),
                publication_types=tuple(args.publication_type),
                open_access_only=args.open_access_only,
                min_citation_count=args.min_citations,
            ),
            semantic_search=args.semantic_search,
            rank_results=args.rank,
            ranking_backends=ranking_backends,
            manuscript_context=_load_context(args.context_file),
            resolve_oa=args.resolve_oa,
            easy_scholar=args.easy_scholar,
            extract_fulltext=args.extract_fulltext,
            extract_limit=args.extract_limit,
            request_budget=args.request_budget,
            provider_budgets=_provider_budgets(args.provider_budget),
            fallback_threshold=args.fallback_threshold,
            stable_identifier_threshold=args.stable_id_threshold,
            max_query_variants=args.max_query_variants,
            graph_limit=args.graph_limit,
            allow_remote_parser=args.allow_remote_parser,
        )
    except Exception as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    if args.show_provider_status:
        provider_objects: list[Any] = list(research.pipeline.providers)
        if research.pipeline.unpaywall:
            provider_objects.append(research.pipeline.unpaywall)
        if research.pipeline.easy_scholar:
            provider_objects.append(research.pipeline.easy_scholar)
        statuses = []
        for provider in provider_objects:
            status = provider.status()
            statuses.append(
                {
                    "name": status.name,
                    "configuration": (
                        "configured" if status.enabled else "not configured"
                    ),
                    "capabilities": list(status.capabilities),
                }
            )
        print(json.dumps(statuses, ensure_ascii=False, indent=2, default=list))
        return 0

    if args.show_query_plan:
        print(
            json.dumps(
                research.plan(args.query, english_query=args.english_query),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    queries = args.batch or [args.query]
    results = research.batch_lookup(
        queries,
        english_query=args.english_query,
        packet_dir=args.packet_dir,
        delay=args.batch_delay,
        citation_seed=args.citation_seed,
        positive_seeds=args.positive_seed,
        negative_seeds=args.negative_seed,
    )
    rendered = (
        json.dumps(results, ensure_ascii=False, indent=2, default=str) + "\n"
        if args.json
        else _render_human(results)
    )
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if all(result.get("success") for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
