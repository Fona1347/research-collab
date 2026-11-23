from __future__ import annotations

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
from rom_contract import (  # noqa: E402
    ID_DEFINITION_MARKER_ROLES,
    ID_DEFINITION_SPECS,
    collect_parent_definition_ids,
    snapshot_parent_run,
)


BRANCH_TABLE = """<!-- rom-table: breadth-branches -->
| Branch ID | Branch |
|---|---|
| BR-999 | misplaced branch definition |
"""


class RoleAwareParentIdTests(unittest.TestCase):
    work_name = "rom-contract-ids"

    def setUp(self) -> None:
        self.work = reset_work(self.work_name)
        self.workspace = workspace_root()

    def tearDown(self) -> None:
        cleanup_work(self.work_name)

    def test_definition_registry_assigns_every_marker_to_a_role(self) -> None:
        self.assertEqual(
            set(ID_DEFINITION_MARKER_ROLES),
            set(ID_DEFINITION_SPECS),
        )
        self.assertTrue(all(ID_DEFINITION_MARKER_ROLES.values()))

    def test_schema_two_mapping_honors_role_but_legacy_scans_all_text(self) -> None:
        self.assertEqual(
            collect_parent_definition_ids(
                {"breadth_ledger": BRANCH_TABLE}, schema_version="2.0"
            ),
            {"BR-999"},
        )
        self.assertEqual(
            collect_parent_definition_ids(
                {"reader_report": BRANCH_TABLE}, schema_version="2.0"
            ),
            set(),
        )
        self.assertEqual(
            collect_parent_definition_ids(
                {"reader_report": BRANCH_TABLE}, schema_version="1.2"
            ),
            {"BR-999"},
        )

    def test_parent_snapshot_ignores_marker_in_wrong_artifact_role(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        manifest = load_manifest(parent)
        reader = parent / manifest["primary_artifact"]
        reader.write_text(
            reader.read_text(encoding="utf-8") + "\n" + BRANCH_TABLE,
            encoding="utf-8",
            newline="\n",
        )

        snapshot = snapshot_parent_run(
            parent,
            workspace_root=self.workspace,
            relation="focuses-branch",
        )

        self.assertIn("BR-001", snapshot.available_ids)
        self.assertNotIn("BR-999", snapshot.available_ids)


if __name__ == "__main__":
    unittest.main()
