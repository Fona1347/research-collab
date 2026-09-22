from __future__ import annotations

import os

import hashlib
import json
import re
import shutil
import subprocess
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
    save_manifest,
    sha256,
    workspace_root,
)
from rom_contract import MODE_ROLES, WORKFLOW_CONTRACTS_BY_MODE  # noqa: E402
from validate_run import validate  # noqa: E402


INIT = SKILL_DIR / "scripts" / "init_run.py"
UPGRADE = SKILL_DIR / "scripts" / "upgrade_run.py"

CUSTOM_LENS_NOTES = "\n".join(
    [
        "Decision object: choose a bounded active thermal-control route",
        "State variables: control heater power and measure temperature and heat flux",
        "Persistent bottleneck: convection-limited stability persists in the target regime",
        "Causal chain: heater power -> temperature field -> heat flux -> bounded control value",
        "Alternative explanations: convection, contact resistance, and sensor drift",
        "Budgets and constraints: energy, latency, area, stability, and measurement uncertainty",
        "Baseline ladder: no-heater null, passive spreader, optimized controller, and system reference",
        "Validation hierarchy: simulation -> coupon experiment -> component -> system bridge",
        "Capability interface: modeling Observed, chamber Reported, and fabrication Unknown",
        "Decisive test: randomized heater control with a five-sigma threshold, three-way outcomes, and kill condition",
    ]
)
INCOMPLETE_CUSTOM_LENS_NOTES = "\n".join(CUSTOM_LENS_NOTES.splitlines()[:-1])


def tree_snapshot(root: Path) -> str:
    rows: list[str] = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        rows.append(
            f"{path.relative_to(root).as_posix()}\t{sha256(path)}\t{path.stat().st_size}\n"
        )
    return hashlib.sha256("".join(rows).encode("utf-8")).hexdigest()


class InitUpgradeTests(unittest.TestCase):
    work_name = "init-upgrade"

    def setUp(self) -> None:
        self.work = reset_work(self.work_name)
        self.workspace = workspace_root()

    def tearDown(self) -> None:
        cleanup_work(self.work_name)

    def run_script(self, script: Path, *args: object) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(script), *(str(arg) for arg in args)],
            cwd=SKILL_DIR,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def init_args(self, run_name: str, *extra: object) -> list[object]:
        return [
            "--domain", "bounded materials and hardware research",
            "--output", self.work,
            "--run-name", run_name,
            "--workspace-root", self.workspace,
            "--date", "2026-07-31",
            "--as-of-date", "2026-07-31",
            "--created-at", "2026-07-31T00:00:00+00:00",
            *extra,
        ]

    def assert_init_ok(self, run_name: str, *extra: object) -> Path:
        completed = self.run_script(INIT, *self.init_args(run_name, *extra))
        self.assertEqual(completed.returncode, 0, completed.stderr)
        run_dir = self.work / run_name
        self.assertTrue(run_dir.is_dir())
        return run_dir

    def test_default_manifest_persists_concrete_landscape_and_requested_auto(self) -> None:
        run_dir = self.assert_init_ok(
            "default",
            "--requested-mode", "auto",
            "--request", "route this broad request",
            "--routing-reason", "broad scope requires landscape coverage",
            "--routing-confidence", "high",
        )
        manifest = load_manifest(run_dir)
        self.assertEqual(manifest["schema_version"], "2.0")
        self.assertEqual(manifest["task_mode"], "landscape")
        self.assertEqual(manifest["run_type"], "landscape")
        self.assertEqual(manifest["routing"]["selected"], "landscape")
        self.assertEqual(manifest["routing"]["requested"], "auto")
        self.assertEqual(manifest["discovery_lens"], "balanced")
        self.assertEqual(manifest["completion_status"], "initialized")

    def test_generic_and_custom_domain_lenses_are_persisted_and_bounded(self) -> None:
        custom = self.assert_init_ok(
            "custom-lens",
            "--domain-lens", "custom",
            "--domain-lens-notes",
            CUSTOM_LENS_NOTES,
            "--secondary-domain-lens", "semiconductor-device",
        )
        manifest = load_manifest(custom)
        self.assertEqual(manifest["primary_domain_lens"], "custom")
        self.assertEqual(
            manifest["secondary_domain_lenses"], ["semiconductor-device"]
        )
        self.assertIn("temperature", manifest["domain_lens_notes"])
        intake = (custom / manifest["artifact_roles"]["intake"]).read_text(
            encoding="utf-8"
        )
        self.assertIn("custom", intake)
        self.assertIn("semiconductor-device", intake)
        self.assertIn("temperature", intake)

        missing_notes = self.run_script(
            INIT, *self.init_args("custom-without-notes", "--domain-lens", "custom")
        )
        self.assertEqual(missing_notes.returncode, 2)
        self.assertIn("requires --domain-lens-notes", missing_notes.stderr)
        self.assertFalse((self.work / "custom-without-notes").exists())

        incomplete = self.run_script(
            INIT,
            *self.init_args(
                "custom-incomplete-notes",
                "--domain-lens", "custom",
                "--domain-lens-notes", INCOMPLETE_CUSTOM_LENS_NOTES,
            ),
        )
        self.assertEqual(incomplete.returncode, 2)
        self.assertIn("decisive test", incomplete.stderr.lower())
        self.assertFalse((self.work / "custom-incomplete-notes").exists())

        slot_labels = [
            line.split(":", 1)[0] for line in CUSTOM_LENS_NOTES.splitlines()
        ]
        invalid_note_sets = {
            "same-as-above": "\n".join(
                f"{label}: same as above" for label in slot_labels
            ),
            "n-a-punctuation": "\n".join(
                f"{label}: N/A." for label in slot_labels
            ),
            "n-a-zero-width": "\n".join(
                f"{label}: N/A\u200b" for label in slot_labels
            ),
            "slot-label-echo": "\n".join(
                f"{label}: {label}" for label in slot_labels
            ),
            "todo-numbered": "\n".join(
                f"{label}: TODO {index}"
                for index, label in enumerate(slot_labels)
            ),
            "placeholder-numbered": "\n".join(
                f"{label}: placeholder {index}"
                for index, label in enumerate(slot_labels)
            ),
            "tbc-numbered": "\n".join(
                f"{label}: TBC {index}"
                for index, label in enumerate(slot_labels)
            ),
            "fixme-numbered": "\n".join(
                f"{label}: FIXME: later {index}"
                for index, label in enumerate(slot_labels)
            ),
            "zh-pending-numbered": "\n".join(
                f"{label}: 待补内容 {index}"
                for index, label in enumerate(slot_labels)
            ),
            "zh-placeholder-numbered": "\n".join(
                f"{label}: 占位 {index}"
                for index, label in enumerate(slot_labels)
            ),
            "tbc-bracket-numbered": "\n".join(
                f"{label}: [TBC {index:02d}]"
                for index, label in enumerate(slot_labels)
            ),
            "fixme-underscore-numbered": "\n".join(
                f"{label}: FIXME_{index}"
                for index, label in enumerate(slot_labels)
            ),
            "zh-pending-item-numbered": "\n".join(
                f"{label}: 待补第{index}项"
                for index, label in enumerate(slot_labels)
            ),
            "zh-placeholder-parenthesized": "\n".join(
                f"{label}: 占位（{index}）"
                for index, label in enumerate(slot_labels)
            ),
        }
        for case, invalid_notes in invalid_note_sets.items():
            with self.subTest(invalid_custom_notes=case):
                run_name = f"custom-invalid-{case}"
                rejected = self.run_script(
                    INIT,
                    *self.init_args(
                        run_name,
                        "--domain-lens", "custom",
                        "--domain-lens-notes", invalid_notes,
                    ),
                )
                self.assertEqual(rejected.returncode, 2, rejected.stderr)
                self.assertIn("domain_lens_notes", rejected.stderr)
                self.assertFalse((self.work / run_name).exists())

                manifest["domain_lens_notes"] = invalid_notes
                save_manifest(custom, manifest)
                invalid_report = validate(custom, workspace_root=self.workspace)
                self.assertTrue(
                    any(
                        "domain_lens_notes" in error
                        for error in invalid_report.errors
                    ),
                    invalid_report.errors,
                )
        meaningful_edge_notes = (
            CUSTOM_LENS_NOTES
            .replace(
                "choose a bounded active thermal-control route",
                "FIXME flags are excluded by the calibrated decision pipeline",
            )
            .replace(
                "control heater power and measure temperature and heat flux",
                "待补偿项由热漂移模型给出，并测量温度与热流",
            )
        )
        meaningful = self.assert_init_ok(
            "custom-substantive-placeholder-prefixes",
            "--domain-lens", "custom",
            "--domain-lens-notes", meaningful_edge_notes,
        )
        self.assertTrue(meaningful.is_dir())

        manifest["domain_lens_notes"] = INCOMPLETE_CUSTOM_LENS_NOTES
        (custom / "run-manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        report = validate(custom, workspace_root=self.workspace)
        self.assertTrue(
            any("decisive test" in error.lower() for error in report.errors),
            report.errors,
        )

    def test_bilingual_templates_and_unicode_space_output_path(self) -> None:
        output = self.work / "带 空格 outputs"
        for language, expected in (("zh-CN", "科研方向比较与路线判断"), ("en", "Research directions and route judgment")):
            with self.subTest(language=language):
                run_name = "中文 路线" if language == "zh-CN" else "english route"
                completed = self.run_script(
                    INIT,
                    "--domain", "可调材料硬件" if language == "zh-CN" else "tunable hardware",
                    "--output", output,
                    "--run-name", run_name,
                    "--language", language,
                    "--workspace-root", self.workspace,
                    "--date", "2026-07-31",
                    "--as-of-date", "2026-07-31",
                    "--created-at", "2026-07-31T00:00:00+00:00",
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                run_dir = Path(completed.stdout.strip())
                manifest = load_manifest(run_dir)
                report = (run_dir / manifest["primary_artifact"]).read_text(encoding="utf-8")
                self.assertIn(expected, report)
                if language == "zh-CN":
                    self.assertRegex(report, r"[\u4e00-\u9fff]")

    def test_each_mode_uses_its_exact_role_profile(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        context = self.work / "claim input.md"
        context.write_text("Audit the bounded claim B-001.\n", encoding="utf-8", newline="\n")
        cases: list[tuple[str, list[object]]] = [
            ("landscape", []),
            ("focus", ["--selected-branch", "standalone precise interface"]),
            ("evidence-audit", ["--context-source", f"claim-input={context}"]),
            ("run-audit", ["--parent-run", parent]),
        ]
        for mode, extra in cases:
            with self.subTest(mode=mode):
                run_dir = self.assert_init_ok(
                    f"init-{mode}", "--mode", mode, "--lens", "frontier-led", *extra
                )
                manifest = load_manifest(run_dir)
                expected = set(MODE_ROLES[mode].values()) | {"reader_report"}
                self.assertEqual(set(manifest["artifact_roles"]), expected)
                self.assertEqual(manifest["artifact_profile"], f"{mode}-v2")
                self.assertEqual(manifest["discovery_lens"], "frontier-led")
                self.assertEqual(
                    manifest["workflow_contracts"],
                    list(WORKFLOW_CONTRACTS_BY_MODE[mode]),
                )
                if mode != "run-audit":
                    search_text = (
                        run_dir / manifest["artifact_roles"]["search_log"]
                    ).read_text(encoding="utf-8")
                    evidence_text = (
                        run_dir / manifest["artifact_roles"]["evidence_matrix"]
                    ).read_text(encoding="utf-8")
                    self.assertIn("rom-table: coverage-audit", search_text)
                    self.assertIn("rom-table: deep-reading-handoff", evidence_text)
                    self.assertIn("verification_depth", evidence_text)
                if mode in {"landscape", "focus"}:
                    route_role = (
                        "candidate_portfolio"
                        if mode == "landscape"
                        else "route_protocol"
                    )
                    route_text = (
                        run_dir / manifest["artifact_roles"][route_role]
                    ).read_text(encoding="utf-8")
                    self.assertIn("rom-table: opportunity-gates", route_text)
                    self.assertIn("rom-table: route-fast-pilots", route_text)

    def test_run_audit_init_snapshots_incomplete_parent_observed_tree(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="incomplete-parent")
        parent_manifest = load_manifest(parent)
        (parent / parent_manifest["primary_artifact"]).unlink()
        (parent / "undeclared-observation.txt").write_text(
            "observable parent attachment\n", encoding="utf-8", newline="\n"
        )

        audit = self.assert_init_ok(
            "audit-incomplete-parent",
            "--mode", "run-audit",
            "--parent-run", parent,
        )
        lineage = load_manifest(audit)["lineage"]["parents"][0]
        observed = {
            path.relative_to(parent).as_posix()
            for path in parent.rglob("*")
            if path.is_file() and path.name != "run-manifest.json"
        }
        self.assertEqual(set(lineage["source_artifact_sha256"]), observed)
        self.assertNotIn(parent_manifest["primary_artifact"], observed)
        self.assertIn("undeclared-observation.txt", observed)

    def test_invalid_mode_and_lens_are_rejected_without_output(self) -> None:
        completed = self.run_script(INIT, *self.init_args("illegal-auto", "--mode", "auto"))
        self.assertEqual(completed.returncode, 2)
        self.assertFalse((self.work / "illegal-auto").exists())

        invalid_lens = self.run_script(
            INIT,
            *self.init_args(
                "illegal-lens",
                "--lens",
                "fashion-led",
            ),
        )
        self.assertEqual(invalid_lens.returncode, 2)
        self.assertIn("invalid choice", invalid_lens.stderr.lower())
        self.assertFalse((self.work / "illegal-lens").exists())

    def test_nonoverwrite_preserves_the_first_run_byte_for_byte(self) -> None:
        run_dir = self.assert_init_ok("same-name")
        before = tree_snapshot(run_dir)
        completed = self.run_script(INIT, *self.init_args("same-name"))
        self.assertEqual(completed.returncode, 2)
        self.assertIn("Refusing to overwrite", completed.stderr)
        self.assertEqual(tree_snapshot(run_dir), before)

    def test_parent_snapshot_is_read_only_and_fake_parent_ids_are_rejected(self) -> None:
        parent = make_run(self.work, mode="landscape", run_id="parent")
        before = tree_snapshot(parent)
        child = self.assert_init_ok(
            "focus-child",
            "--mode", "focus",
            "--parent-run", parent,
            "--selected-branch", "BR-001",
            "--inherit-claim", "B-001",
            "--inherit-evidence", "E-001",
            "--inherit-capability", "CAP-001",
        )
        self.assertEqual(tree_snapshot(parent), before)
        manifest = load_manifest(child)
        lineage = manifest["lineage"]["parents"][0]
        self.assertFalse(Path(lineage["workspace_relpath"]).is_absolute())
        self.assertEqual(lineage["source_manifest_sha256"], sha256(parent / "run-manifest.json"))

        parent_manifest = load_manifest(parent)
        report_path = parent / parent_manifest["primary_artifact"]
        report_path.write_text(
            report_path.read_text(encoding="utf-8")
            + "\n<!-- BR-999 -->\n```text\nBR-999\n```\nOrdinary BR-999 reference.\n",
            encoding="utf-8",
            newline="\n",
        )
        rejected = self.run_script(
            INIT,
            *self.init_args(
                "fake-parent-id",
                "--mode", "focus",
                "--parent-run", parent,
                "--selected-branch", "BR-999",
            ),
        )
        self.assertEqual(rejected.returncode, 2)
        self.assertIn("not present in the parent", rejected.stderr)

    @unittest.skipUnless(os.environ.get("MAPPER_LEGACY_WORKSPACE"), "Exact historical fixture assertions require MAPPER_LEGACY_WORKSPACE")
    def test_schema_11_is_read_only_compatible_and_copy_upgradeable(self) -> None:
        legacy_12 = (
            self.workspace
            / "Doc/Typora/note_2025_S2SPR/周工作/W22/sciver mapper/"
            "self-regulating-learning-hardware"
        )
        source = self.work / "synthetic-legacy-1.1"
        shutil.copytree(legacy_12, source)
        source_manifest = load_manifest(source)
        source_manifest["schema_version"] = "1.1"
        source_manifest.pop("primary_artifact", None)
        save_manifest(source, source_manifest)
        before = tree_snapshot(source)

        legacy_report = validate(source, workspace_root=self.workspace)
        self.assertFalse(legacy_report.errors, legacy_report.errors)
        self.assertFalse(legacy_report.warnings, legacy_report.warnings)

        target = self.work / "upgrade-1.1"
        args = [
            source,
            "--copy-to", target,
            "--workspace-root", self.workspace,
            "--date", "2026-07-31",
            "--as-of-date", "2026-07-31",
            "--created-at", "2026-07-31T00:00:00+00:00",
        ]
        dry = self.run_script(UPGRADE, *args, "--dry-run")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertFalse(target.exists())
        self.assertEqual(json.loads(dry.stdout)["source_schema"], "1.1")

        upgraded = self.run_script(UPGRADE, *args)
        self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
        self.assertEqual(tree_snapshot(source), before)
        upgraded_manifest = load_manifest(target)
        self.assertEqual(upgraded_manifest["schema_version"], "2.0")
        self.assertEqual(
            upgraded_manifest["completion_status"], "migrated-needs-review"
        )
        self.assertTrue((target / "migration-report.json").is_file())


    def test_upgrade_legacy_10_and_12_is_copy_only_and_marks_review_required(self) -> None:
        sources = [
            self.workspace / "Projects/research_map/validation-runs/ai-hardware-session-case",
            self.workspace / "Doc/Typora/note_2025_S2SPR/周工作/W22/sciver mapper/self-regulating-learning-hardware",
        ]
        for index, source in enumerate(sources):
            with self.subTest(schema=("1.0", "1.2")[index]):
                before = tree_snapshot(source)
                target = self.work / f"upgrade-{index}"
                args = [
                    source,
                    "--copy-to", target,
                    "--workspace-root", self.workspace,
                    "--date", "2026-07-31",
                    "--as-of-date", "2026-07-31",
                    "--created-at", "2026-07-31T00:00:00+00:00",
                ]
                dry = self.run_script(UPGRADE, *args, "--dry-run")
                self.assertEqual(dry.returncode, 0, dry.stderr)
                self.assertFalse(target.exists())
                plan = json.loads(dry.stdout)
                self.assertEqual(plan["source_schema"], ("1.0", "1.2")[index])
                self.assertFalse(plan["source_will_be_modified"])

                upgraded = self.run_script(UPGRADE, *args)
                self.assertEqual(upgraded.returncode, 0, upgraded.stderr)
                self.assertEqual(tree_snapshot(source), before)
                manifest = load_manifest(target)
                self.assertEqual(manifest["schema_version"], "2.0")
                self.assertEqual(manifest["completion_status"], "migrated-needs-review")
                self.assertEqual(manifest["lineage"]["parents"][0]["relation"], "migrated-copy")
                self.assertTrue((target / "migration-report.json").is_file())
                report = validate(target, workspace_root=self.workspace)
                self.assertTrue(any("not ready for delivery" in item for item in report.warnings))
                self.assertFalse(any("must use relation" in item for item in report.errors), report.errors)

        source = sources[0]
        nested_target = source / "__migration-descendant-must-not-exist__"
        before = tree_snapshot(source)
        nested_args = [
            source,
            "--copy-to", nested_target,
            "--workspace-root", self.workspace,
            "--date", "2026-07-31",
            "--as-of-date", "2026-07-31",
            "--created-at", "2026-07-31T00:00:00+00:00",
        ]
        for extra in (("--dry-run",), ()):
            with self.subTest(nested_target_dry_run=bool(extra)):
                rejected = self.run_script(UPGRADE, *nested_args, *extra)
                self.assertEqual(rejected.returncode, 2, rejected.stderr)
                self.assertIn("disjoint", rejected.stderr)
                self.assertFalse(nested_target.exists())
                self.assertEqual(tree_snapshot(source), before)

        overlap_cases = {
            "same-directory": source,
            "source-under-target": source.parent,
            "normalized-alias": source / ".." / source.name,
        }
        for case, overlap_target in overlap_cases.items():
            for extra in (("--dry-run",), ()):
                with self.subTest(
                    overlap_case=case,
                    dry_run=bool(extra),
                ):
                    rejected = self.run_script(
                        UPGRADE,
                        source,
                        "--copy-to",
                        overlap_target,
                        "--workspace-root",
                        self.workspace,
                        *extra,
                    )
                    self.assertEqual(rejected.returncode, 2, rejected.stderr)
                    self.assertIn("disjoint", rejected.stderr.lower())
                    self.assertIn("contain", rejected.stderr.lower())
                    self.assertEqual(tree_snapshot(source), before)

        help_result = self.run_script(UPGRADE, "--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        help_text = help_result.stdout.lower()
        self.assertIn("disjoint", help_text)
        self.assertIn("neither", help_text)
        self.assertIn("contain", help_text)

    def test_upgrade_persists_custom_domain_lens_without_mutating_legacy(self) -> None:
        source = self.workspace / "Projects/research_map/validation-runs/ai-hardware-session-case"
        before = tree_snapshot(source)
        target = self.work / "upgrade-custom-domain"
        completed = self.run_script(
            UPGRADE,
            source,
            "--copy-to", target,
            "--workspace-root", self.workspace,
            "--date", "2026-07-31",
            "--as-of-date", "2026-07-31",
            "--created-at", "2026-07-31T00:00:00+00:00",
            "--domain-lens", "custom",
            "--domain-lens-notes",
            CUSTOM_LENS_NOTES.replace("temperature", "polarization"),
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(tree_snapshot(source), before)
        manifest = load_manifest(target)
        self.assertEqual(manifest["primary_domain_lens"], "custom")
        self.assertEqual(manifest["secondary_domain_lenses"], [])
        self.assertIn("polarization", manifest["domain_lens_notes"])

        incomplete_target = self.work / "upgrade-custom-incomplete"
        incomplete = self.run_script(
            UPGRADE,
            source,
            "--copy-to", incomplete_target,
            "--workspace-root", self.workspace,
            "--date", "2026-07-31",
            "--as-of-date", "2026-07-31",
            "--created-at", "2026-07-31T00:00:00+00:00",
            "--domain-lens", "custom",
            "--domain-lens-notes", INCOMPLETE_CUSTOM_LENS_NOTES,
        )
        self.assertEqual(incomplete.returncode, 2)
        self.assertIn("decisive test", incomplete.stderr.lower())
        self.assertFalse(incomplete_target.exists())
        self.assertEqual(tree_snapshot(source), before)

    def test_upgrade_rejects_nonlegacy_source_without_writing(self) -> None:
        source = make_run(self.work, mode="landscape", run_id="schema-two-source")
        target = self.work / "illegal-upgrade"
        completed = self.run_script(
            UPGRADE,
            source,
            "--copy-to", target,
            "--workspace-root", self.workspace,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertFalse(target.exists())
        self.assertTrue(re.search(r"1\.0|1\.1|1\.2", completed.stderr))


if __name__ == "__main__":
    unittest.main()
