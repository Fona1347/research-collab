from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_SCRIPTS = PROJECT_ROOT / "skills" / "research-lookup-enhanced" / "scripts"
sys.path.insert(0, str(SKILL_SCRIPTS))

from research_lookup import ResearchLookup, build_parser  # noqa: E402
from rle.models import PaperRecord  # noqa: E402
from rle.pipeline import ResearchPipeline  # noqa: E402
from rle.providers import ProviderStatus  # noqa: E402
from rle.query_plan import build_query_plan, emergency_query_plan  # noqa: E402
from rle.research_profile import (  # noqa: E402
    RESEARCH_PROFILES,
    ResearchLevelResolver,
)


class EmptyProvider:
    name = "crossref"
    capabilities = ("search", "get_citations", "get_references", "provenance")

    def status(self) -> ProviderStatus:
        return ProviderStatus(self.name, True, "", self.capabilities)

    def search(self, query: str, **_: object) -> list[object]:
        del query
        return []

    def get_citations(self, identifier: str, *, limit: int = 50) -> list[object]:
        del identifier, limit
        return []

    def get_references(self, identifier: str, *, limit: int = 50) -> list[object]:
        del identifier, limit
        return []


class OneRecordProvider(EmptyProvider):
    def search(self, query: str, **_: object) -> list[PaperRecord]:
        del query
        return [
            PaperRecord(
                title="Traceable scientific evidence",
                doi="10.1000/traceable-evidence",
                abstract="A deterministic offline test record.",
                year=2024,
            )
        ]


class ResearchProfileTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = ResearchLevelResolver()

    def test_profile_values(self) -> None:
        quick = RESEARCH_PROFILES["quick"]
        standard = RESEARCH_PROFILES["standard"]
        deep = RESEARCH_PROFILES["deep"]

        self.assertEqual((quick.target_references, quick.max_results), (12, 5))
        self.assertEqual(quick.request_budget, 6)
        self.assertEqual(
            dict(quick.provider_budgets),
            {
                "openalex": 2,
                "crossref": 2,
                "semantic_scholar": 1,
                "europe_pmc": 2,
            },
        )
        self.assertEqual((quick.fallback_threshold, quick.max_query_variants), (5, 3))
        self.assertEqual(quick.stable_identifier_threshold, 0.5)
        self.assertTrue(quick.resolve_oa)
        self.assertFalse(quick.easy_scholar)
        self.assertFalse(quick.extract_fulltext)
        self.assertEqual((quick.extract_limit, quick.graph_limit), (5, 20))

        self.assertEqual((standard.target_references, standard.max_results), (60, 10))
        self.assertEqual(standard.request_budget, 12)
        self.assertEqual(
            dict(standard.provider_budgets),
            {
                "openalex": 4,
                "crossref": 3,
                "semantic_scholar": 2,
                "europe_pmc": 3,
            },
        )
        self.assertEqual(standard.fallback_threshold, 12)
        self.assertEqual(standard.stable_identifier_threshold, 0.5)
        self.assertEqual(standard.max_query_variants, 6)
        self.assertTrue(standard.resolve_oa)
        self.assertTrue(standard.easy_scholar)
        self.assertFalse(standard.extract_fulltext)
        self.assertEqual((standard.extract_limit, standard.graph_limit), (20, 50))

        self.assertEqual((deep.target_references, deep.max_results), (100, 20))
        self.assertEqual(deep.request_budget, 24)
        self.assertEqual(
            dict(deep.provider_budgets),
            {
                "openalex": 8,
                "crossref": 6,
                "semantic_scholar": 4,
                "europe_pmc": 6,
            },
        )
        self.assertEqual(deep.fallback_threshold, 24)
        self.assertEqual(deep.stable_identifier_threshold, 0.65)
        self.assertEqual(deep.max_query_variants, 6)
        self.assertTrue(deep.resolve_oa)
        self.assertTrue(deep.easy_scholar)
        self.assertFalse(deep.extract_fulltext)
        self.assertEqual((deep.extract_limit, deep.graph_limit), (40, 100))

    def test_omitted_level_preserves_standard(self) -> None:
        config = self.resolver.resolve("ordinary scientific question")
        self.assertEqual(config.decision.requested_level, None)
        self.assertEqual(config.decision.effective_level, "standard")
        self.assertEqual(config.decision.source, "default-standard")
        self.assertEqual(config.request_budget, 12)
        self.assertFalse(config.extract_fulltext)

    def test_explicit_override_is_recorded_even_at_old_default(self) -> None:
        config = self.resolver.resolve(
            "comprehensive search of a scientific topic",
            requested_level="deep",
            source="explicit-user-intent",
            reason="  user\x00 requested   deep research  ",
            explicit_overrides={
                "request_budget": 12,
                "extract_fulltext": False,
                "provider_budgets": {"openalex": 5},
            },
        )
        self.assertEqual(config.request_budget, 12)
        self.assertFalse(config.extract_fulltext)
        self.assertEqual(config.provider_budgets["openalex"], 5)
        self.assertEqual(config.provider_budgets["crossref"], 6)
        payload = config.research_profile_payload()
        self.assertEqual(payload["explicit_overrides"]["request_budget"], 12)
        self.assertEqual(config.decision.reason, "user requested deep research")

    def test_auto_rules_and_false_positives(self) -> None:
        cases = {
            "快速找几篇相关论文": "quick",
            "DOI:10.1038/s41586-020-2649-2": "quick",
            "PMID:12345678": "quick",
            "PMCID:1234567": "quick",
            "arXiv:2301.01234": "quick",
            "调研一下这个研究问题": "standard",
            "全面检索这个科研问题": "deep",
            "请对这个科研问题开展深度调研": "deep",
            "comprehensive search for gene editing evidence": "deep",
            "conduct deep research on gene editing evidence": "deep",
            "deep": "standard",
            "review": "standard",
            "full-text": "standard",
            "deep learning for protein structure prediction": "standard",
            "full-text classification methods": "standard",
            "review classification using transformers": "standard",
            "请不要开展深度调研，只需回答普通研究问题": "standard",
            "do not conduct a systematic review of this scientific topic": "standard",
        }
        for query, expected in cases.items():
            with self.subTest(query=query):
                config = self.resolver.resolve(query, requested_level="auto")
                self.assertEqual(config.decision.effective_level, expected)

        ambiguous = self.resolver.resolve(
            "快速全面检索这个问题",
            requested_level="auto",
        )
        self.assertEqual(ambiguous.decision.effective_level, "standard")
        self.assertEqual(ambiguous.decision.reason_code, "auto-ambiguous-standard")

        ambiguous_fulltext = self.resolver.resolve(
            "快速找几篇论文并阅读全文比较",
            requested_level="auto",
        )
        self.assertEqual(
            ambiguous_fulltext.decision.effective_level,
            "standard",
        )
        self.assertTrue(ambiguous_fulltext.extract_fulltext)

    def test_auto_fulltext_and_explicit_negation(self) -> None:
        inferred = self.resolver.resolve(
            "全面检索并阅读全文比较这些证据",
            requested_level="auto",
        )
        self.assertEqual(inferred.decision.effective_level, "deep")
        self.assertTrue(inferred.extract_fulltext)
        self.assertEqual(
            dict(inferred.inferred_overrides),
            {"extract_fulltext": True},
        )

        negated = self.resolver.resolve(
            "全面检索这个问题，但不要阅读全文",
            requested_level="auto",
        )
        self.assertEqual(negated.decision.effective_level, "deep")
        self.assertFalse(negated.extract_fulltext)

        explicit_off = self.resolver.resolve(
            "全面检索并阅读全文比较这些证据",
            requested_level="auto",
            explicit_overrides={"extract_fulltext": False},
        )
        self.assertFalse(explicit_off.extract_fulltext)

    def test_auto_rejects_external_source_or_reason(self) -> None:
        with self.assertRaisesRegex(ValueError, "auto generates its own"):
            self.resolver.resolve(
                "ordinary research question",
                requested_level="auto",
                reason="caller supplied text",
            )
        with self.assertRaisesRegex(ValueError, "explicit non-auto"):
            self.resolver.resolve(
                "ordinary research question",
                source="agent-inference",
            )

    def test_reason_is_a_bounded_audit_string(self) -> None:
        config = self.resolver.resolve(
            "ordinary research question",
            requested_level="standard",
            source="agent-inference",
            reason="  selected\x00 by   agent  " + ("x" * 600),
        )
        self.assertNotIn("\x00", config.decision.reason)
        self.assertNotIn("  ", config.decision.reason)
        self.assertEqual(len(config.decision.reason), 512)


class QueryPlanProfileTests(unittest.TestCase):
    def test_standard_profile_preserves_legacy_plan_behavior(self) -> None:
        query = "ordinary scientific question"
        legacy = build_query_plan(query).to_dict()
        config = ResearchLevelResolver().resolve(query)
        profiled = build_query_plan(
            query,
            max_variants=config.max_query_variants,
            global_request_budget=config.request_budget,
            provider_budgets=config.provider_budgets,
            research_profile=config.research_profile_payload(),
        ).to_dict()
        legacy.pop("research_profile")
        profiled.pop("research_profile")
        self.assertEqual(legacy, profiled)

    def test_profile_snapshot_is_deterministic_and_budget_aligned(self) -> None:
        config = ResearchLevelResolver().resolve(
            "comprehensive search for scientific evidence",
            requested_level="auto",
        )
        plan = build_query_plan(
            "comprehensive search for scientific evidence",
            max_variants=config.max_query_variants,
            global_request_budget=config.request_budget,
            provider_budgets=config.provider_budgets,
            research_profile=config.research_profile_payload(),
        )
        again = build_query_plan(
            "comprehensive search for scientific evidence",
            max_variants=config.max_query_variants,
            global_request_budget=config.request_budget,
            provider_budgets=config.provider_budgets,
            research_profile=config.research_profile_payload(),
        )
        self.assertEqual(plan.to_dict(), again.to_dict())
        self.assertEqual(plan.request_budget["global_limit"], 24)
        self.assertEqual(
            plan.research_profile["decision"]["effective_level"],
            "deep",
        )

    def test_emergency_plan_keeps_profile(self) -> None:
        config = ResearchLevelResolver().resolve(
            "a scientific question",
            requested_level="quick",
        )
        plan = emergency_query_plan(
            "a scientific question",
            error="synthetic",
            global_request_budget=config.request_budget,
            provider_budgets=config.provider_budgets,
            research_profile=config.research_profile_payload(),
        )
        self.assertEqual(
            plan.research_profile["decision"]["effective_level"],
            "quick",
        )
        ordinary = build_query_plan(
            "a scientific question",
            global_request_budget=config.request_budget,
            provider_budgets=config.provider_budgets,
            research_profile=config.research_profile_payload(),
        )
        self.assertEqual(
            plan.research_profile["decision"],
            ordinary.research_profile["decision"],
        )


class RuntimeProfileTests(unittest.TestCase):
    def test_batch_planning_has_no_level_state_leak(self) -> None:
        lookup = ResearchLookup(providers=["crossref"], research_level="auto")
        levels = [
            lookup.plan("DOI:10.1038/s41586-020-2649-2")["research_profile"]
            ["decision"]["effective_level"],
            lookup.plan("ordinary research question")["research_profile"]
            ["decision"]["effective_level"],
            lookup.plan("全面检索这个科研问题")["research_profile"]
            ["decision"]["effective_level"],
        ]
        self.assertEqual(levels, ["quick", "standard", "deep"])

    def test_batch_continues_after_auto_fulltext_configuration_error(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rle-batch-test-") as temporary:
            lookup = ResearchLookup(
                providers=["crossref"],
                cache_dir=temporary,
                research_level="auto",
            )
            lookup.pipeline = ResearchPipeline(
                [EmptyProvider()],
                cache_dir=temporary,
                unpaywall=None,
                easy_scholar=None,
            )
            results = lookup.batch_lookup(
                [
                    "全面检索并阅读全文比较这些证据",
                    "ordinary research question",
                ],
                delay=0,
            )

        self.assertEqual(len(results), 2)
        self.assertIn("packet_dir", results[0]["error"])
        self.assertEqual(
            results[0]["research_profile"]["decision"]["effective_level"],
            "deep",
        )
        self.assertIn("No provider returned", results[1]["error"])
        self.assertEqual(
            results[1]["query_plan"]["research_profile"]["decision"]
            ["effective_level"],
            "standard",
        )

    def test_no_result_path_records_selection_and_outcome(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rle-profile-test-") as temporary:
            pipeline = ResearchPipeline(
                [EmptyProvider()],
                cache_dir=temporary,
                unpaywall=None,
                easy_scholar=None,
            )
            config = ResearchLevelResolver().resolve(
                "ordinary research question",
                requested_level="standard",
            )
            result = pipeline.run(
                "ordinary research question",
                run_config=config,
            )

        self.assertFalse(result["success"])
        stages = [
            item.get("stage")
            for item in result["search_ledger"]
            if item.get("capability") == "pipeline_stage"
        ]
        self.assertLess(
            stages.index("research-level-selection"),
            stages.index("question-decomposition"),
        )
        self.assertIn("research-profile-outcome", stages)

    def test_seed_graph_uses_remaining_budget_and_audits_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rle-graph-test-") as temporary:
            pipeline = ResearchPipeline(
                [EmptyProvider()],
                cache_dir=temporary,
                unpaywall=None,
                easy_scholar=None,
            )
            config = ResearchLevelResolver().resolve(
                "ordinary research question",
                requested_level="quick",
                explicit_overrides={
                    "request_budget": 1,
                    "provider_budgets": {"crossref": 1},
                },
            )
            result = pipeline.run(
                "ordinary research question",
                citation_seed="DOI:10.1000/example",
                run_config=config,
            )

        outcome = next(
            item
            for item in result["search_ledger"]
            if item.get("stage") == "research-profile-outcome"
        )
        self.assertTrue(outcome["graph_requested"])
        self.assertFalse(outcome["graph_expansion_performed"])
        self.assertEqual(outcome["graph_skip_reason"], "request-budget-exhausted")

    def test_success_path_records_profile_outcome(self) -> None:
        with tempfile.TemporaryDirectory(prefix="rle-success-test-") as temporary:
            pipeline = ResearchPipeline(
                [OneRecordProvider()],
                cache_dir=temporary,
                unpaywall=None,
                easy_scholar=None,
            )
            config = ResearchLevelResolver().resolve(
                "ordinary research question",
                requested_level="quick",
                explicit_overrides={
                    "request_budget": 1,
                    "provider_budgets": {"crossref": 1},
                },
            )
            result = pipeline.run(
                "ordinary research question",
                run_config=config,
            )

        self.assertTrue(result["success"])
        outcomes = [
            item
            for item in result["search_ledger"]
            if item.get("stage") == "research-profile-outcome"
        ]
        self.assertEqual(len(outcomes), 1)
        self.assertEqual(outcomes[0]["effective_level"], "quick")
        self.assertEqual(outcomes[0]["graph_skip_reason"], "no-seed-supplied")
        self.assertEqual(outcomes[0]["route_stages_executed"], ["targeted"])
        self.assertEqual(outcomes[0]["fallback_stages_executed"], [])

    def test_auto_fulltext_requires_packet_directory_at_execution(self) -> None:
        lookup = ResearchLookup(providers=["crossref"], research_level="auto")
        result = lookup.lookup("全面检索并阅读全文比较这些证据")
        self.assertFalse(result["success"])
        self.assertIn("packet_dir", result["error"])
        self.assertNotIn("allow_remote_parser", result["research_profile"])

    def test_python_api_cannot_authorize_remote_parser_via_auto(self) -> None:
        with self.assertRaisesRegex(ValueError, "explicit extract_fulltext=True"):
            ResearchLookup(
                providers=["crossref"],
                research_level="auto",
                allow_remote_parser=True,
            )

        with tempfile.TemporaryDirectory(prefix="rle-remote-gate-") as temporary:
            pipeline = ResearchPipeline(
                [EmptyProvider()],
                cache_dir=temporary,
                unpaywall=None,
                easy_scholar=None,
                allow_remote_parser=True,
            )
            inferred = ResearchLevelResolver().resolve(
                "全面检索并阅读全文比较这些证据",
                requested_level="auto",
            )
            with self.assertRaisesRegex(ValueError, "cannot authorize upload"):
                pipeline.run(
                    "全面检索并阅读全文比较这些证据",
                    packet_dir=temporary,
                    run_config=inferred,
                )


class CliProfileTests(unittest.TestCase):
    def test_parser_preserves_absence_and_boolean_intent(self) -> None:
        parser = build_parser()
        omitted = parser.parse_args(["a scientific question"])
        self.assertIsNone(omitted.research_level)
        self.assertIsNone(omitted.target_references)
        self.assertIsNone(omitted.max_results)
        self.assertIsNone(omitted.request_budget)
        self.assertIsNone(omitted.fallback_threshold)
        self.assertIsNone(omitted.stable_id_threshold)
        self.assertIsNone(omitted.max_query_variants)
        self.assertIsNone(omitted.extract_fulltext)
        self.assertIsNone(omitted.extract_limit)
        self.assertIsNone(omitted.resolve_oa)
        self.assertIsNone(omitted.easy_scholar)
        self.assertIsNone(omitted.graph_limit)

        disabled = parser.parse_args(
            ["a scientific question", "--no-extract-fulltext"]
        )
        self.assertFalse(disabled.extract_fulltext)

    def test_show_plan_is_offline_and_does_not_require_packet_dir(self) -> None:
        command = [
            sys.executable,
            str(SKILL_SCRIPTS / "research_lookup.py"),
            "全面检索并阅读全文比较这些证据",
            "--research-level",
            "auto",
            "--show-query-plan",
        ]
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertTrue(
            payload["research_profile"]["effective_settings"]["extract_fulltext"]
        )

    def test_remote_parser_requires_explicit_fulltext_flag(self) -> None:
        command = [
            sys.executable,
            str(SKILL_SCRIPTS / "research_lookup.py"),
            "全面检索并阅读全文比较这些证据",
            "--research-level",
            "auto",
            "--allow-remote-parser",
            "--show-query-plan",
        ]
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("explicit --extract-fulltext", completed.stderr)

    def test_source_and_reason_require_non_auto_level(self) -> None:
        for extra in (
            ["--research-level-source", "agent-inference"],
            ["--research-level-reason", "agent selected this"],
            [
                "--research-level",
                "auto",
                "--research-level-reason",
                "not allowed",
            ],
        ):
            with self.subTest(extra=extra):
                command = [
                    sys.executable,
                    str(SKILL_SCRIPTS / "research_lookup.py"),
                    "ordinary research question",
                    "--show-query-plan",
                    *extra,
                ]
                completed = subprocess.run(
                    command,
                    cwd=PROJECT_ROOT,
                    capture_output=True,
                    text=True,
                    timeout=20,
                    check=False,
                )
                self.assertEqual(completed.returncode, 2)
                self.assertIn("explicit quick, standard, or deep", completed.stderr)

    def test_agent_level_source_and_reason_are_audited(self) -> None:
        command = [
            sys.executable,
            str(SKILL_SCRIPTS / "research_lookup.py"),
            "ordinary research question",
            "--research-level",
            "standard",
            "--research-level-source",
            "agent-inference",
            "--research-level-reason",
            "ordinary bounded research request",
            "--show-query-plan",
        ]
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        decision = json.loads(completed.stdout)["research_profile"]["decision"]
        self.assertEqual(decision["source"], "agent-inference")
        self.assertEqual(
            decision["reason"],
            "ordinary bounded research request",
        )


if __name__ == "__main__":
    unittest.main()
