from __future__ import annotations

import importlib.util
import re
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
MAIN_KEY = "main-loc-p8-fig3"
SECONDARY_KEY = "main-ref-7"


def main_definition(key: str = MAIN_KEY) -> str:
    if key == MAIN_KEY:
        source = "主文：Example Review。"
    else:
        source = "A. Example. *Measured response in a model system*. Example Journal (2020). 转引自：Example Review；原文文献 [7]；未独立核验原始文献。"
    return f"[^{key}]: {source} 定位：p. 8, Fig. 3。 [回到正文](#ref-{key}-1)"


def main_report(key: str = MAIN_KEY) -> str:
    return report(key, (f"ref-{key}-1",), main_definition(key)).replace("外部核验文献", "主文与转引注释")


def main_audit(key: str = MAIN_KEY) -> str:
    return audit(key, (f"ref-{key}-1",), "main" if key == MAIN_KEY else key)


def native_report(text: str) -> str:
    text = checker.ANCHOR_RE.sub("", text)
    return checker.BACKLINK_RE.sub("", text)


def native_audit(text: str) -> str:
    text = re.sub(r"\| ref-[^|\n]+\|", "| native |", text)
    return text + "\nreader_backlinks: native\n"


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
        require_citations: bool = False,
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

            return checker.check_report(report_path, registry_path, audit_path, require_citations)

    def assert_blocked_with(self, result: dict, fragment: str) -> None:
        self.assertEqual("BLOCKED", result["status"], result)
        self.assertTrue(
            any(fragment in error for error in result["errors"]),
            f"Expected an error containing {fragment!r}: {result}",
        )

    def test_valid_semantic_footnote_contract_passes(self) -> None:
        result = self.run_check(report(), registry(), audit())
        self.assertEqual("PASS", result["status"], result)

    def test_no_citations_is_not_applicable_not_a_pass(self) -> None:
        result = self.run_check("# Reader report\n\nExternal validation was out of scope.\n")
        self.assertEqual("NOT-APPLICABLE", result["status"], result)

    def test_full_report_requires_citations_without_external_validation(self) -> None:
        result = self.run_check("# Reader report\n\nExternal validation was out of scope.\n", require_citations=True)
        self.assert_blocked_with(result, "requires citations")

    def test_main_paper_and_secondary_footnotes_need_no_external_registry(self) -> None:
        for key in (MAIN_KEY, SECONDARY_KEY):
            with self.subTest(key=key):
                result = self.run_check(main_report(key), audit_text=main_audit(key), require_citations=True)
                self.assertEqual("PASS", result["status"], result)
                self.assertEqual(0, result["counts"]["external_keys"])
                self.assertEqual(1, result["counts"]["main_source_keys"])
                self.assertFalse(result["rendering_checked"])

    def test_mixed_footnotes_keep_evidence_classes_separate(self) -> None:
        combined_audit = audit() + f"| {SECONDARY_KEY} | {SECONDARY_KEY} | ref-{SECONDARY_KEY}-1 |\n"
        result = self.run_check(main_report(SECONDARY_KEY) + "\n" + report(), registry(), combined_audit)
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(2, result["counts"]["body_references"])
        self.assertEqual(1, result["counts"]["external_keys"])

    def test_secondary_attribution_cannot_be_promoted_by_audit(self) -> None:
        result = self.run_check(main_report(SECONDARY_KEY), audit_text=main_audit(SECONDARY_KEY).replace(f"| {SECONDARY_KEY} | {SECONDARY_KEY} |", f"| {SECONDARY_KEY} | S-001 |"))
        self.assert_blocked_with(result, "Source ID must be")

    def test_main_footnotes_cannot_go_in_external_section(self) -> None:
        result = self.run_check(main_report().replace("主文与转引注释", "外部核验文献"), audit_text=main_audit())
        self.assert_blocked_with(result, "wrong citation section")

    def test_main_footnote_requires_locator_and_attribution(self) -> None:
        for old, new, error in (("定位：", "位置：", "lacks Locator"), ("主文：", "材料：", "main-paper attribution")):
            with self.subTest(error=error):
                result = self.run_check(main_report().replace(old, new), audit_text=main_audit())
                self.assert_blocked_with(result, error)

    def test_secondary_requires_citation_chain_and_unverified_disclosure(self) -> None:
        for old, new, error in (("转引自：", "相关：", "cited-via"), ("未独立核验原始文献", "相关研究", "not independently verified"), ("原文文献 [7]", "原文文献 [8]", "original reference [7]")):
            with self.subTest(error=error):
                result = self.run_check(main_report(SECONDARY_KEY).replace(old, new), audit_text=main_audit(SECONDARY_KEY))
                self.assert_blocked_with(result, error)

    def test_main_footnote_requires_backlink_and_audit(self) -> None:
        result = self.run_check(main_report().replace(f"[回到正文](#ref-{MAIN_KEY}-1)", ""), audit_text=main_audit())
        self.assert_blocked_with(result, "backlinks")
        self.assert_blocked_with(self.run_check(main_report()), "--audit is required")

    def test_main_footnote_audit_must_not_claim_blocked_delivery_passed(self) -> None:
        result = self.run_check(main_report(), audit_text=main_audit().replace("| pass |", "| blocked |"))
        self.assert_blocked_with(result, "must be `pass`")

    def test_main_reference_key_rejects_missing_or_zero_number(self) -> None:
        for key in ("main-ref-x", "main-ref-0"):
            with self.subTest(key=key):
                result = self.run_check(main_report(SECONDARY_KEY).replace(SECONDARY_KEY, key), audit_text=main_audit(SECONDARY_KEY).replace(SECONDARY_KEY, key))
                self.assert_blocked_with(result, "invalid footnote key")

    def test_plain_escaped_and_split_number_links_are_not_superscript_citations(self) -> None:
        for link in ("[7](#原文-7)", r"[\[7\]](#review-ref-7)", "[1\n\n7](#review-ref-17)", "[综述 p. 8](review.pdf#page=8)"):
            with self.subTest(link=link):
                self.assert_blocked_with(self.run_check(f"# Report\n\nClaim {link}.\n"), "ordinary citation link")

    def test_broken_footnote_and_empty_reference_link_are_blocked(self) -> None:
        for text, error in (("Claim[^main-ref-\n7]", "broken footnote marker"), ("[review-p8]:\n", "empty reference-link")):
            with self.subTest(text=text):
                self.assert_blocked_with(self.run_check(text), error)

    def test_examples_in_code_and_main_pdf_resource_links_are_not_citations(self) -> None:
        text = "# Report\n\n`[^broken` and `[7](#原文-7)`\n\n```md\n[review-p8]:\nClaim[^broken\n```\n\n[主文 PDF](review.pdf#page=1)\n"
        self.assertEqual("NOT-APPLICABLE", self.run_check(text)["status"])

    def test_registry_cited_sources_cannot_disappear_with_all_body_footnotes(self) -> None:
        result = self.run_check("# Report\n\nNo citations.\n", registry())
        self.assert_blocked_with(result, "report does not use it")

    def test_unindented_body_after_definition_is_checked(self) -> None:
        result = self.run_check(main_report() + "\nLater claim.[^main-ref-9]\n", audit_text=main_audit())
        self.assert_blocked_with(result, "body footnote has no definition")

    def test_indented_definition_continuation_is_supported(self) -> None:
        text = main_report().replace(" 定位：", "\n\n    定位：")
        result = self.run_check(text, audit_text=main_audit())
        self.assertEqual("PASS", result["status"], result)

    def test_native_main_footnotes_pass_without_html_or_manual_backlinks(self) -> None:
        for key in (MAIN_KEY, SECONDARY_KEY):
            with self.subTest(key=key):
                result = self.run_check(native_report(main_report(key)), audit_text=native_audit(main_audit(key)), require_citations=True)
                self.assertEqual("PASS", result["status"], result)
                self.assertEqual("native", result["backlink_mode"])
                self.assertEqual(0, result["counts"]["anchors"])

    def test_native_external_repeat_uses_renderer_links_and_preserves_registry(self) -> None:
        text = native_report(report(anchors=(ANCHOR_1, ANCHOR_2)))
        result = self.run_check(text, registry(anchors=("native",)), native_audit(audit(anchors=(ANCHOR_1, ANCHOR_2))))
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(2, result["counts"]["body_references"])
        self.assertFalse(result["rendering_checked"])

    def test_native_mixed_footnotes_share_audit_without_inflating_external_counts(self) -> None:
        text = native_report(main_report(SECONDARY_KEY) + "\n" + report())
        combined = audit() + f"| {SECONDARY_KEY} | {SECONDARY_KEY} | ref-{SECONDARY_KEY}-1 |\n"
        result = self.run_check(text, registry(anchors=("native",)), native_audit(combined))
        self.assertEqual("PASS", result["status"], result)
        self.assertEqual(1, result["counts"]["external_keys"])

    def test_native_mode_rejects_manual_anchors_and_return_links(self) -> None:
        for text, error in ((main_report(), "manual citation HTML anchors"), (checker.ANCHOR_RE.sub("", main_report()), "manual backlinks")):
            with self.subTest(error=error):
                result = self.run_check(text, audit_text=native_audit(main_audit()))
                self.assert_blocked_with(result, error)

    def test_native_registry_and_audit_must_agree(self) -> None:
        result = self.run_check(native_report(report()), registry(), native_audit(audit()))
        self.assert_blocked_with(result, "Source Registry backlink IDs")
        result = self.run_check(native_report(main_report()), audit_text=main_audit()+"\nreader_backlinks: native\n")
        self.assert_blocked_with(result, "Footnote Map backlink IDs")

    def test_native_mode_must_be_explicit_and_unambiguous_in_audit(self) -> None:
        for suffix, error in (("", "missing body backlink"), ("\nreader_backlinks: guessed\n", "single `native` or `explicit`"), ("\nreader_backlinks: native\nreader_backlinks: explicit\n", "single `native` or `explicit`")):
            with self.subTest(suffix=suffix):
                result = self.run_check(native_report(main_report()), audit_text=main_audit()+suffix)
                self.assert_blocked_with(result, error)

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
