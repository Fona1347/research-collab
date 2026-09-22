from __future__ import annotations

import json
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
from rle.query_plan import build_query_plan  # noqa: E402


CHINESE_QUERY = "铁电器件用于时序计算的研究空白与潜在方向"
ENGLISH_QUERY = (
    "ferroelectric devices temporal computing "
    "time-series information processing"
)


def planning_details(plan: object) -> dict[str, object]:
    payload = plan.to_dict()
    return payload["provenance"][1]["details"]


class CaptureProvider:
    name = "openalex"
    capabilities = ("search", "provenance")

    def __init__(self) -> None:
        self.queries: list[str] = []

    def status(self) -> ProviderStatus:
        return ProviderStatus(self.name, True, "", self.capabilities)

    def search(self, query: str, **_: object) -> list[PaperRecord]:
        self.queries.append(query)
        return [
            PaperRecord(
                title="Ferroelectric devices for temporal computing",
                abstract=(
                    "Ferroelectric hardware processes time-series information."
                ),
                doi="10.1000/ferroelectric-temporal",
                year=2025,
            ),
            PaperRecord(
                title="Ocean salinity measurements",
                abstract="A marine reference record unrelated to device computing.",
                doi="10.1000/ocean-salinity",
                year=2025,
            ),
        ]


class QueryExpansionPlanTests(unittest.TestCase):
    def test_caller_supplied_english_query_is_additive_and_audited(self) -> None:
        plan = build_query_plan(CHINESE_QUERY, english_query=ENGLISH_QUERY)
        variant = plan.variant("english-term-expansion")

        self.assertEqual(plan.original_query, CHINESE_QUERY)
        self.assertIsNotNone(variant)
        self.assertEqual(variant.query, ENGLISH_QUERY)
        self.assertEqual(variant.source, "caller-supplied-english-query")
        self.assertEqual(plan.ranking_query_variant_id, "english-term-expansion")
        self.assertEqual(plan.ranking_query(), ENGLISH_QUERY)
        self.assertEqual(plan.router_confidence, 0.84)
        details = planning_details(plan)
        self.assertEqual(details["english_query_status"], "accepted")
        self.assertTrue(details["external_translation_supplied"])
        self.assertFalse(details["planner_llm_call_used"])

    def test_one_token_local_expansion_is_not_routed_as_english(self) -> None:
        plan = build_query_plan("铁电材料用于时序计算的研究空白")

        self.assertIsNone(plan.variant("english-term-expansion"))
        self.assertEqual(plan.ranking_query_variant_id, "original")
        self.assertEqual(plan.router_confidence, 0.58)
        details = planning_details(plan)
        self.assertEqual(details["bilingual_expansion_terms"], ["材料"])
        self.assertFalse(details["local_english_expansion_useful"])

    def test_invalid_english_queries_degrade_without_losing_original(self) -> None:
        invalid_values = (
            "",
            "仍然是中文",
            "materials",
            ("a" * 513) + " devices",
        )
        for value in invalid_values:
            with self.subTest(value=value[:30]):
                plan = build_query_plan(CHINESE_QUERY, english_query=value)
                self.assertEqual(plan.original_query, CHINESE_QUERY)
                self.assertIsNone(plan.variant("english-term-expansion"))
                self.assertEqual(plan.ranking_query(), CHINESE_QUERY)
                self.assertEqual(
                    planning_details(plan)["english_query_status"],
                    "rejected",
                )
                self.assertTrue(
                    planning_details(plan)["external_translation_supplied"]
                )
                self.assertFalse(
                    planning_details(plan)["external_translation_used"]
                )

    def test_variant_cap_prioritizes_supplied_query_but_never_drops_original(
        self,
    ) -> None:
        query = "  " + CHINESE_QUERY + "  "
        two = build_query_plan(
            query,
            english_query=ENGLISH_QUERY,
            max_variants=2,
        )
        self.assertEqual(
            [variant.variant_id for variant in two.query_variants],
            ["original", "english-term-expansion"],
        )

        one = build_query_plan(
            query,
            english_query=ENGLISH_QUERY,
            max_variants=1,
        )
        self.assertEqual(
            [variant.variant_id for variant in one.query_variants],
            ["original"],
        )
        self.assertEqual(one.ranking_query_variant_id, "original")
        self.assertEqual(
            planning_details(one)["english_query_status"],
            "accepted-not-selected",
        )
        self.assertTrue(
            planning_details(one)["external_translation_supplied"]
        )
        self.assertFalse(planning_details(one)["external_translation_used"])

    def test_identifier_lookup_ignores_supplied_translation(self) -> None:
        plan = build_query_plan(
            "DOI:10.1038/s41586-020-2649-2 柔性石墨烯传感器",
            english_query=ENGLISH_QUERY,
        )

        self.assertIsNotNone(plan.variant("stable-identifier"))
        self.assertIsNotNone(plan.variant("english-term-expansion"))
        self.assertEqual(plan.ranking_query_variant_id, "original")
        self.assertEqual(
            planning_details(plan)["english_query_status"],
            "ignored-identifier",
        )
        self.assertTrue(
            planning_details(plan)["external_translation_supplied"]
        )
        self.assertFalse(planning_details(plan)["external_translation_used"])

    def test_method_level_query_does_not_leak_between_plans(self) -> None:
        lookup = ResearchLookup(providers=["crossref"])
        translated = lookup.plan(CHINESE_QUERY, english_query=ENGLISH_QUERY)
        untranslated = lookup.plan(CHINESE_QUERY)

        self.assertEqual(
            translated["ranking_query_variant_id"],
            "english-term-expansion",
        )
        self.assertEqual(untranslated["ranking_query_variant_id"], "original")


class QueryExpansionPipelineTests(unittest.TestCase):
    def test_pipeline_routes_and_ranks_with_supplied_english_query(self) -> None:
        provider = CaptureProvider()
        with tempfile.TemporaryDirectory(prefix="rle-query-expansion-") as temporary:
            pipeline = ResearchPipeline(
                [provider],
                cache_dir=temporary,
                target_references=2,
                max_results_per_provider=2,
                unpaywall=None,
                easy_scholar=None,
                resolve_oa=False,
                request_budget=1,
                provider_budgets={"openalex": 1},
                fallback_threshold=1,
            )
            result = pipeline.run(
                CHINESE_QUERY,
                english_query=ENGLISH_QUERY,
            )

        self.assertTrue(result["success"])
        self.assertEqual(provider.queries, [ENGLISH_QUERY])
        self.assertEqual(
            result["query_plan"]["ranking_query_variant_id"],
            "english-term-expansion",
        )
        self.assertEqual(
            result["recommendations"][0]["record_key"],
            "doi:10.1000/ferroelectric-temporal",
        )


class QueryExpansionCliTests(unittest.TestCase):
    def test_parser_default_is_none(self) -> None:
        args = build_parser().parse_args([CHINESE_QUERY])
        self.assertIsNone(args.english_query)

    def test_show_plan_accepts_english_query_without_network(self) -> None:
        command = [
            sys.executable,
            "-B",
            str(SKILL_SCRIPTS / "research_lookup.py"),
            CHINESE_QUERY,
            "--english-query",
            ENGLISH_QUERY,
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
        payload = json.loads(completed.stdout)
        self.assertEqual(
            payload["ranking_query_variant_id"],
            "english-term-expansion",
        )
        self.assertEqual(
            payload["provenance"][1]["details"]["english_query_status"],
            "accepted",
        )

    def test_one_english_query_cannot_be_shared_by_multiple_batch_items(
        self,
    ) -> None:
        command = [
            sys.executable,
            "-B",
            str(SKILL_SCRIPTS / "research_lookup.py"),
            "--batch",
            CHINESE_QUERY,
            "另一条中文科研问题",
            "--english-query",
            ENGLISH_QUERY,
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
        self.assertIn("applies to exactly one query", completed.stderr)


if __name__ == "__main__":
    unittest.main()
