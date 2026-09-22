from __future__ import annotations

import sys
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(SKILL_DIR / "scripts"), str(SKILL_DIR / "tests")]

from fixture_factory import cleanup_work, reset_work, workspace_root  # noqa: E402
from forward_runner import (  # noqa: E402
    ForwardCaseRunner,
    assert_catalog_contract,
    load_cases,
)


CASES_FILE = SKILL_DIR / "tests" / "forward-cases.json"


class ForwardCaseTests(unittest.TestCase):
    work_name = "forward-cases"

    def setUp(self) -> None:
        self.work = reset_work(self.work_name)
        self.workspace = workspace_root()
        self.cases = load_cases(CASES_FILE)
        self.runner = ForwardCaseRunner(work=self.work, workspace=self.workspace)

    def tearDown(self) -> None:
        cleanup_work(self.work_name)

    def test_catalog_declares_eight_executable_scenario_contracts(self) -> None:
        assert_catalog_contract(self.cases)
        declared = {
            case["id"]: tuple(behavior["id"] for behavior in case["required_behavior"])
            for case in self.cases
        }
        self.assertTrue(all(declared.values()))
        self.assertEqual(len({item for values in declared.values() for item in values}), 30)

    def test_all_eight_cases_consume_every_required_behavior_and_validate(self) -> None:
        assert_catalog_contract(self.cases)
        results = {}
        for case in self.cases:
            with self.subTest(case=case["id"]):
                result = self.runner.run(case)
                expected = tuple(behavior["id"] for behavior in case["required_behavior"])
                self.assertEqual(result.checked_behaviors, expected)
                results[case["id"]] = result
        self.assertEqual(set(results), {case["id"] for case in self.cases})

    def test_f07_parent_chain_and_f08_real_legacy_target_are_explicit(self) -> None:
        by_id = {case["id"]: case for case in self.cases}
        f07 = by_id["landscape-child-focus-lineage"]
        self.assertEqual(f07["parent"]["kind"], "generated-landscape")
        self.assertIn(
            {"kind": "lineage", "manifest_sha256": True},
            [check for behavior in f07["required_behavior"] for check in behavior["checks"]],
        )

        f08 = by_id["existing-run-adversarial-audit"]
        self.assertEqual(f08["parent"]["kind"], "workspace-legacy")
        self.assertEqual(f08["parent"]["run_id"], "self-regulating-learning-hardware")
        self.assertEqual(f08["parent"]["schema_version"], "1.2")
        self.assertEqual(f08["audit_target"], "C-L01")
        legacy = (self.workspace / Path(f08["parent"]["workspace_relpath"])).resolve()
        self.assertTrue((legacy / "run-manifest.json").is_file())
        self.assertNotIn("tests/.work", legacy.as_posix())


if __name__ == "__main__":
    unittest.main()
