from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = (
    REPOSITORY_ROOT
    / "skills"
    / "paper-deep-reading"
    / "scripts"
    / "check_report_footnotes.py"
)

spec = importlib.util.spec_from_file_location("check_report_footnotes", CHECKER_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Cannot load checker from {CHECKER_PATH}")
checker = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = checker
spec.loader.exec_module(checker)


KEY = "Yujian Hu_Nat Med_2025"
ANCHOR_1 = "ref-yujian-hu-nat-med-2025-1"
ANCHOR_2 = "ref-yujian-hu-nat-med-2025-2"


def definition(key: str = KEY, anchors: tuple[str, ...] = (ANCHOR_1,)) -> str:
    backlinks = " ".join(f"[回到正文](#{anchor})" for anchor in anchors)
    return (
        f"[^{key}]: Yujian Hu, Mei Li. *AI-based diagnosis of acute aortic syndrome*. "
        f"*Nature Medicine* [Nat Med], 2025. DOI: https://doi.org/10.1000/example. "
        f"Evidence role: boundary evidence. Locator: p. 8, Fig. 3. {backlinks}"
    )


def report(
    key: str = KEY,
    anchors: tuple[str, ...] = (ANCHOR_1,),
    footnote_definition: str | None = None,
) -> str:
    body = []
    for index, anchor in enumerate(anchors, start=1):
        body.extend(
            [
                f'<a id="{anchor}"></a>',
                f"External-validation statement {index}.[^{key}]",
                "",
            ]
        )
    rendered_definition = footnote_definition or definition(key, anchors)
    return "\n".join(
        [
            "# Reader report",
            "",
            *body,
            "## 外部核验文献",
            "",
            rendered_definition,
            "",
        ]
    )


def registry(
    key: str = KEY,
    anchors: tuple[str, ...] = (ANCHOR_1,),
    source_id: str = "S1",
) -> str:
    anchor_cell = ", ".join(anchors)
    return "\n".join(
        [
            "| Source ID | Citation status | Reader-facing footnote key | Backlink anchor IDs |",
            "| --- | --- | --- | --- |",
            f"| {source_id} | cited | {key} | {anchor_cell} |",
            "",
        ]
    )


def audit(
    key: str = KEY,
    anchors: tuple[str, ...] = (ANCHOR_1,),
    source_id: str = "S1",
) -> str:
    anchor_cell = ", ".join(anchors)
    return "\n".join(
        [
            "# G5",
            "",
            "| Gate | Status |",
            "| --- | --- |",
            "| G5 Delivery QA | pass |",
            "",
            "reader_citation_contract: semantic-footnote-v1",
            "",
            "| Reader-facing footnote key | Source ID | Backlink anchor IDs |",
            "| --- | --- | --- |",
            f"| {key} | {source_id} | {anchor_cell} |",
            "",
        ]
    )


class CheckReportFootnotesTests(unittest.TestCase):
    def run_check(
        self,
        report_text: str,
        registry_text: str | None = None,
        audit_text: str | None = None,
    ) -> dict:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            report_path = root / "view-report.md"
            report_path.write_text(report_text, encoding="utf-8")

            registry_path = None
            if registry_text is not None:
                registry_path = root / "auxiliary-literature-table.md"
                registry_path.write_text(registry_text, encoding="utf-8")

            audit_path = None
            if audit_text is not None:
                audit_path = root / "view-report-audit.md"
                audit_path.write_text(audit_text, encoding="utf-8")

            return checker.check_report(report_path, registry_path, audit_path)

    def assert_blocked_with(self, result: dict, fragment: str) -> None:
        self.assertEqual("BLOCKED", result["status"], result)
        self.assertTrue(
            any(fragment in error for error in result["errors"]),
            f"Expected an error containing {fragment!r}: {result}",
        )

    def test_valid_semantic_footnote_contract_passes(self) -> None:
        result = self.run_check(report(), registry(), audit())
        self.assertEqual("PASS", result["status"], result)

    def test_report_without_external_footnotes_passes(self) -> None:
        result = self.run_check("# Reader report\n\nExternal validation was out of scope.\n")
        self.assertEqual("PASS", result["status"], result)

    def test_empty_external_validation_section_is_blocked(self) -> None:
        result = self.run_check("# Reader report\n\n## 外部核验文献\n")
        self.assert_blocked_with(result, "must not be empty")

    def test_definition_requires_author_title_and_journal(self) -> None:
        incomplete = (
            f"[^{KEY}]: 2025. DOI: https://doi.org/10.1000/example. "
            f"Evidence role: boundary evidence. Locator: p. 8. "
            f"[回到正文](#{ANCHOR_1})"
        )
        result = self.run_check(report(footnote_definition=incomplete), registry(), audit())
        self.assert_blocked_with(result, "author, article title, and journal")

    def test_definition_must_begin_with_the_key_first_author(self) -> None:
        wrong_first_author = definition().replace(
            "Yujian Hu, Mei Li.",
            "Other Person, Yujian Hu.",
        )
        result = self.run_check(
            report(footnote_definition=wrong_first_author),
            registry(),
            audit(),
        )
        self.assert_blocked_with(result, "first-author name")

    def test_registry_anchor_ids_must_match_exactly_and_in_order(self) -> None:
        wrong_registry = registry(anchors=(ANCHOR_2, ANCHOR_1, "ref-extra-3"))
        result = self.run_check(
            report(anchors=(ANCHOR_1, ANCHOR_2)),
            wrong_registry,
            audit(anchors=(ANCHOR_1, ANCHOR_2)),
        )
        self.assert_blocked_with(result, "must be exactly")

    def test_collision_suffix_cannot_start_at_b(self) -> None:
        key = f"{KEY}_b"
        anchor = "ref-yujian-hu-nat-med-2025-b-1"
        result = self.run_check(
            report(key=key, anchors=(anchor,)),
            registry(key=key, anchors=(anchor,)),
            audit(key=key, anchors=(anchor,)),
        )
        self.assert_blocked_with(result, "collision suffixes")

    def test_collision_suffix_requires_at_least_two_cited_sources(self) -> None:
        key = f"{KEY}_a"
        anchor = "ref-yujian-hu-nat-med-2025-a-1"
        result = self.run_check(
            report(key=key, anchors=(anchor,)),
            registry(key=key, anchors=(anchor,)),
            audit(key=key, anchors=(anchor,)),
        )
        self.assert_blocked_with(result, "collision suffixes")

    def test_contiguous_collision_suffixes_pass(self) -> None:
        key_a = f"{KEY}_a"
        key_b = f"{KEY}_b"
        anchor_a = "ref-yujian-hu-nat-med-2025-a-1"
        anchor_b = "ref-yujian-hu-nat-med-2025-b-1"
        report_text = "\n".join(
            [
                "# Reader report",
                "",
                f'<a id="{anchor_a}"></a>',
                f"First source.[^{key_a}]",
                "",
                f'<a id="{anchor_b}"></a>',
                f"Second source.[^{key_b}]",
                "",
                "## 外部核验文献",
                "",
                definition(key_a, (anchor_a,)),
                definition(key_b, (anchor_b,)),
                "",
            ]
        )
        registry_text = "\n".join(
            [
                "| Source ID | Citation status | Reader-facing footnote key | Backlink anchor IDs |",
                "| --- | --- | --- | --- |",
                f"| S1 | cited | {key_a} | {anchor_a} |",
                f"| S2 | cited | {key_b} | {anchor_b} |",
                "",
            ]
        )
        audit_text = "\n".join(
            [
                "| Gate | Status |",
                "| --- | --- |",
                "| G5 Delivery QA | pass |",
                "",
                "reader_citation_contract: semantic-footnote-v1",
                "",
                "| Reader-facing footnote key | Source ID | Backlink anchor IDs |",
                "| --- | --- | --- |",
                f"| {key_a} | S1 | {anchor_a} |",
                f"| {key_b} | S2 | {anchor_b} |",
                "",
            ]
        )
        result = self.run_check(report_text, registry_text, audit_text)
        self.assertEqual("PASS", result["status"], result)

    def test_audit_requires_a_structured_footnote_map(self) -> None:
        unstructured_audit = (
            f"# G5\n\nreader_citation_contract: semantic-footnote-v1\n\n"
            f"G5 PASS: {KEY}, S1, {ANCHOR_1}\n"
        )
        result = self.run_check(report(), registry(), unstructured_audit)
        self.assert_blocked_with(result, "Footnote Map")

    def test_audit_requires_a_structured_g5_gate_result(self) -> None:
        map_without_gate_table = "\n".join(
            [
                "# G5",
                "",
                "reader_citation_contract: semantic-footnote-v1",
                "",
                "| Reader-facing footnote key | Source ID | Backlink anchor IDs |",
                "| --- | --- | --- |",
                f"| {KEY} | S1 | {ANCHOR_1} |",
                "",
            ]
        )
        result = self.run_check(report(), registry(), map_without_gate_table)
        self.assert_blocked_with(result, "G5 Gate table")

    def test_audit_requires_g5_to_pass(self) -> None:
        blocked_audit = audit().replace(
            "| G5 Delivery QA | pass |",
            "| G5 Delivery QA | blocked |",
        )
        result = self.run_check(report(), registry(), blocked_audit)
        self.assert_blocked_with(result, "must be `pass`")

    def test_audit_source_id_must_match_the_registry(self) -> None:
        result = self.run_check(report(), registry(source_id="S1"), audit(source_id="S2"))
        self.assert_blocked_with(result, "Source ID")


if __name__ == "__main__":
    unittest.main()
