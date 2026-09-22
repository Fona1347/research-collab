import copy
import os
import json
import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SKILL_DIR / "scripts"), str(SKILL_DIR / "tests")]

from fixture_factory import (  # noqa: E402
    cleanup_work,
    load_manifest,
    make_run,
    reset_work,
    workspace_root,
)
from parent_audit import (  # noqa: E402
    MANIFEST_FAILURE_REPAIRS,
    canonical_manifest_repair,
    inspect_parent_for_audit,
)
from rom_contract import ContractError  # noqa: E402


class ParentAuditTests(unittest.TestCase):
    work_name = "parent-audit"

    def setUp(self) -> None:
        self.work = reset_work(self.work_name)
        self.workspace = workspace_root()

    def tearDown(self) -> None:
        cleanup_work(self.work_name)

    @unittest.skipUnless(os.environ.get("MAPPER_LEGACY_WORKSPACE"), "Exact historical fixture assertions require MAPPER_LEGACY_WORKSPACE")
    def test_legacy_research_map_definitions_use_companion_columns(self) -> None:
        baseline = json.loads(
            (SKILL_DIR / "tests" / "baselines" / "legacy-runs.json").read_text(
                encoding="utf-8"
            )
        )
        expected_ids = {
            "1.0": {"B-003", "B-004", "M-003", "M-004"},
            "1.2": {f"M-{index:03d}" for index in range(1, 9)},
        }
        for item in baseline["runs"]:
            with self.subTest(schema=item["schema_version"]):
                parent = self.workspace / Path(item["workspace_relpath"])
                manifest = load_manifest(parent)
                facts = inspect_parent_for_audit(
                    parent, manifest, {"run_id": manifest["run_id"]}
                )
                rows = {row[0]: row for row in facts.id_projection}
                for identifier in expected_ids[item["schema_version"]]:
                    self.assertIn(identifier, rows)
                    self.assertNotIn(
                        rows[identifier][4],
                        {"dangling-reference", "duplicate-definition"},
                        rows[identifier],
                    )
                    self.assertIn("04_research-map.md", rows[identifier][2])

    def test_schema2_manifest_projection_covers_structural_contract(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        runs = (
            parent,
            make_run(self.work, mode="focus", parent=parent, run_id="focus"),
            make_run(
                self.work,
                mode="evidence-audit",
                parent=parent,
                run_id="evidence-audit",
            ),
            make_run(
                self.work, mode="run-audit", parent=parent, run_id="run-audit"
            ),
        )
        structural_checks = {
            "package-versions",
            "identity-metadata",
            "domain-lenses",
            "created-at",
            "evidence-window",
            "frontier-policy",
            "routing-contract",
            "parent-mutation-policy",
            "lineage-structure",
            "context-sources",
            "selected-branch",
            "inherited-ids",
        }
        for run in runs:
            with self.subTest(valid_mode=load_manifest(run)["run_type"]):
                run_manifest = load_manifest(run)
                run_facts = inspect_parent_for_audit(
                    run, run_manifest, {"run_id": run_manifest["run_id"]}
                )
                results = {
                    row[0]: row[2] for row in run_facts.manifest_projection
                }
                self.assertTrue(structural_checks <= results.keys())
                self.assertTrue(
                    all(results[name] == "pass" for name in structural_checks),
                    run_facts.manifest_projection,
                )

        manifest = load_manifest(parent)
        lineage = {"run_id": manifest["run_id"]}

        mutations = {
            "package-versions": lambda value: value.update(
                {"validator_version": "9.9.9"}
            ),
            "identity-metadata": lambda value: value.update({"domain": ""}),
            "domain-lenses": lambda value: value.update(
                {
                    "primary_domain_lens": "custom",
                    "secondary_domain_lenses": [],
                    "domain_lens_notes": "Decision object: only one populated slot",
                }
            ),
            "created-at": lambda value: value.update(
                {"created_at": "2026-07-31T00:00:00"}
            ),
            "evidence-window": lambda value: value["evidence_window"].update(
                {"end": "2026-08-01"}
            ),
            "frontier-policy": lambda value: value["frontier_policy"].update(
                {"salience_is_not_claim_confidence": False}
            ),
            "routing-contract": lambda value: value["routing"].update(
                {"reason": []}
            ),
            "mode-routing": lambda value: value.update({"task_mode": []}),
            "parent-mutation-policy": lambda value: value.update(
                {"parent_mutation_policy": "supplement-only"}
            ),
            "lineage-structure": lambda value: value.update(
                {"lineage": {"parents": "not-a-list"}}
            ),
            "context-sources": lambda value: value.update(
                {"context_sources": {"source_id": "CTX-001"}}
            ),
            "selected-branch": lambda value: value.update(
                {"selected_branch": {"id": "BR-001", "source": "standalone"}}
            ),
            "inherited-ids": lambda value: value["inherited_ids"].update(
                {"claims": ["C-001"]}
            ),
        }
        for check, mutate in mutations.items():
            with self.subTest(check=check):
                changed = copy.deepcopy(manifest)
                mutate(changed)
                changed_facts = inspect_parent_for_audit(parent, changed, lineage)
                changed_results = {
                    row[0]: row[2] for row in changed_facts.manifest_projection
                }
                self.assertEqual(
                    changed_results[check], "fail", changed_facts.manifest_projection
                )

    def test_manifest_repair_registry_covers_every_emitted_check_and_fails_closed(
        self,
    ) -> None:
        parent = make_run(self.work, mode="landscape", run_id="repair-registry")
        manifest = load_manifest(parent)
        facts = inspect_parent_for_audit(
            parent,
            manifest,
            {"run_id": manifest["run_id"]},
        )
        emitted_checks = {row[0] for row in facts.manifest_projection}
        self.assertEqual(emitted_checks, set(MANIFEST_FAILURE_REPAIRS))
        for check in emitted_checks:
            with self.subTest(check=check):
                self.assertEqual(
                    canonical_manifest_repair(check, "pass"),
                    "retain observed state",
                )
                self.assertEqual(
                    canonical_manifest_repair(check, "fail"),
                    MANIFEST_FAILURE_REPAIRS[check],
                )
        for result in ("pass", "fail", "not-applicable"):
            with self.subTest(unknown_result=result):
                with self.assertRaises(ContractError):
                    canonical_manifest_repair("future-unknown-check", result)


if __name__ == "__main__":
    unittest.main()
