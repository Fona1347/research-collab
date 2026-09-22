from __future__ import annotations

import re
import unittest
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]

REPORT_MARKERS = {
    mode: ("decision-summary",
           "scientific-argument" if mode in {"landscape", "focus"} else "audit-findings",
           "audit-appendix", "references")
    for mode in ("landscape", "focus", "evidence-audit", "run-audit")
}


class PackageContractTests(unittest.TestCase):
    def test_localized_reports_have_identical_mode_marker_contracts(self) -> None:
        marker_pattern = re.compile(
            r"^<!--\s*rom-section:\s*([a-z0-9-]+)\s*-->$", re.MULTILINE
        )
        for language in ("zh-CN", "en"):
            for mode, expected in REPORT_MARKERS.items():
                with self.subTest(language=language, mode=mode):
                    path = (
                        SKILL_DIR
                        / "assets"
                        / "templates"
                        / "reports"
                        / language
                        / f"{mode}.md"
                    )
                    markers = tuple(marker_pattern.findall(path.read_text(encoding="utf-8")))
                    self.assertEqual(markers, expected)

    def test_schema2_templates_use_numeric_route_ids(self) -> None:
        bad_route = re.compile(r"\bC-[A-Z][A-Z0-9]*\b")
        offenders: list[str] = []
        for path in (SKILL_DIR / "assets" / "templates").rglob("*.md"):
            if path.name == "map_report.md":
                continue
            if bad_route.search(path.read_text(encoding="utf-8")):
                offenders.append(path.relative_to(SKILL_DIR).as_posix())
        self.assertEqual(offenders, [])

    def test_internal_markdown_links_resolve(self) -> None:
        link_pattern = re.compile(r"\[[^]]+\]\(([^)]+\.md)(?:#[^)]+)?\)")
        roots = [SKILL_DIR / "SKILL.md", *(SKILL_DIR / "references").glob("*.md")]
        missing: list[str] = []
        for path in roots:
            for target in link_pattern.findall(path.read_text(encoding="utf-8")):
                if "://" in target:
                    continue
                resolved = (path.parent / target).resolve()
                if not resolved.is_file():
                    missing.append(
                        f"{path.relative_to(SKILL_DIR).as_posix()} -> {target}"
                    )
        self.assertEqual(missing, [])

    def test_long_references_have_contents(self) -> None:
        missing: list[str] = []
        for path in (SKILL_DIR / "references").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            if len(text.splitlines()) > 100 and "## Contents" not in text:
                missing.append(path.name)
        self.assertEqual(missing, [])

    def test_agent_interface_invokes_the_skill_explicitly(self) -> None:
        text = (SKILL_DIR / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn("$research-opportunity-mapper", text)
        match = re.search(r'short_description:\s*"([^"]+)"', text)
        self.assertIsNotNone(match)
        assert match is not None
        self.assertGreaterEqual(len(match.group(1)), 25)
        self.assertLessEqual(len(match.group(1)), 64)


if __name__ == "__main__":
    unittest.main()
