from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "skills" / "typora-citation" / "scripts" / "citation_tool.py"

SYNTHETIC_BIB = r"""
@article{Cover1965,
  author = {Cover, Thomas M.},
  title = {Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition},
  journal = {IEEE Transactions on Electronic Computers},
  volume = {EC-14},
  number = {3},
  pages = {326--334},
  year = {1965},
  doi = {10.1109/PGEC.1965.264137}
}

@article{Horsman2014,
  author = {Horsman, Clare and Stepney, Susan and Wagner, Rob C. and Kendon, Viv},
  title = {When does a physical system compute?},
  journal = {Proceedings of the Royal Society A},
  volume = {470},
  number = {2169},
  eid = {20140182},
  year = {2014},
  doi = {10.1098/rspa.2014.0182}
}

@article{Hohenberg1977,
  author = {Hohenberg, Pierre C. and Halperin, Bertrand I.},
  title = {Theory of dynamic critical phenomena},
  journal = {Reviews of Modern Physics},
  volume = {49},
  number = {3},
  pages = {435--479},
  year = {1977},
  doi = {10.1103/RevModPhys.49.435}
}

@article{SyntheticMany2025,
  author = {Chen, Li-Qiang and Wang, Ming and Patel, Asha and Kim, Min-Jun and Rossi, Elena and Silva, Diego and Novak, Jan},
  title = {Benchmarking synthetic citation workflows across academic publishing venues},
  journal = {Nature Communications},
  volume = {16},
  number = {1},
  eid = {4201},
  year = {2025},
  doi = {10.1038/s41467-025-12345-6}
}

@misc{SyntheticPreprint2025,
  author = {Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and Uszkoreit, Jakob and others},
  title = {Attention is all you need},
  year = {2017},
  archivePrefix = {arXiv},
  eprint = {1706.03762}
}

@inproceedings{WebResource2024,
  author = {Miller, Julian F. and Downing, Keith},
  title = {Evolution in materio: Looking beyond the silicon box},
  booktitle = {Proc. NASA/DoD Conf. Evolvable Hardw. (EH)},
  pages = {167--176},
  year = {2002},
  url = {https://example.org/papers/miller-downing-2002}
}
""".strip() + "\n"

SYNTHETIC_DRAFT = """# Academic Citation Regression Draft

## 1. Overview

Synthetic multi-author benchmark results were validated across venues。[^SyntheticMany2025]
Hohenberg 与 Halperin 分类了动态临界现象[^Hohenberg1977]，并可与高维线性可分性及物理计算判据对照[^SyntheticMany2025][^Cover1965][^Horsman2014][^Cover1965]。
Transformer 预印本[^SyntheticPreprint2025]与会议主页文献[^WebResource2024]一并纳入测试。

Protected spans: $P_z[1] + \\chi[2] = 0$, `arr[1]`, and [Regular Link](https://example.org/doc) must stay untouched.

```mermaid
flowchart LR
    A["Input x[1]"] --> B["Cover (1965) Theorem"]
```
"""


class TyporaCitationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="typora-citation-")
        self.work = Path(self.temp.name)
        self.bib_path = self.work / "refs.bib"
        self.bib_path.write_text(SYNTHETIC_BIB, encoding="utf-8", newline="\n")
        self.draft_path = self.work / "draft.md"
        self.draft_path.write_text(SYNTHETIC_DRAFT, encoding="utf-8", newline="\n")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def run_cli(self, *args: str, cwd: Path | None = None, expect_rc: int = 0) -> subprocess.CompletedProcess[str]:
        proc = subprocess.run(
            [sys.executable, str(TOOL), *args],
            cwd=cwd or self.work,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        if proc.returncode != expect_rc:
            self.fail(
                f"CLI failed (expected rc={expect_rc}, got {proc.returncode}): {' '.join(args)}\n"
                f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
            )
        return proc

    def test_resolve_all_seven_styles_and_links(self) -> None:
        out_json = self.work / "resolved.json"
        self.run_cli("resolve", "--bib", str(self.bib_path), "--out", str(out_json))
        data = json.loads(out_json.read_text(encoding="utf-8"))
        self.assertEqual(len(data), 6)

        # IEEE rules: 2 authors no Oxford comma, 4 authors Oxford comma, >=7 et al., ?-title no comma
        self.assertIn("P. C. Hohenberg and B. I. Halperin,", data["Hohenberg1977"]["raw_ieee"])
        self.assertIn("R. C. Wagner, and V. Kendon,", data["Horsman2014"]["raw_ieee"])
        self.assertIn('"When does a physical system compute?"', data["Horsman2014"]["raw_ieee"])
        self.assertIn("L.-Q. Chen *et al.*,", data["SyntheticMany2025"]["raw_ieee"])
        self.assertIn("Art. no. 4201", data["SyntheticMany2025"]["raw_ieee"])

        # All 7 styles generated with smart trailing clickable links
        for style in ("ieee", "gbt7714", "nature", "apa", "vancouver", "acs", "chicago"):
            self.assertIn(style, data["Cover1965"]["formatted"])
            self.assertIn("[DOI](https://doi.org/10.1109/PGEC.1965.264137)", data["Cover1965"]["formatted"][style])

        self.assertIn("[arXiv](https://arxiv.org/abs/1706.03762)", data["SyntheticPreprint2025"]["formatted"]["ieee"])
        self.assertIn("[Website](https://example.org/papers/miller-downing-2002)", data["WebResource2024"]["formatted"]["ieee"])

        # Style-specific structural signatures
        self.assertIn("*Nat. Commun.* **16**, 4201 (2025).", data["SyntheticMany2025"]["formatted"]["nature"])
        self.assertIn("(1965).", data["Cover1965"]["formatted"]["apa"])
        self.assertIn("1965;EC-14(3):326–334.", data["Cover1965"]["formatted"]["vancouver"])
        self.assertIn("**1965**, *EC-14* (3), 326–334.", data["Cover1965"]["formatted"]["acs"])
        self.assertIn("EC-14, no. 3 (1965): 326–334.", data["Cover1965"]["formatted"]["chicago"])
        self.assertIn("[J]. Nature Communications, 2025, 16(1): 4201.", data["SyntheticMany2025"]["raw_gbt"])

    def test_render_default_ieee_clickable_links_and_custom_label(self) -> None:
        out_default = self.work / "out_default.md"
        self.run_cli("render", str(self.draft_path), "--bib", str(self.bib_path), "-o", str(out_default))
        text = out_default.read_text(encoding="utf-8")

        # Strict first-appearance order + CJK punctuation fix
        self.assertIn("validated across venues[^1]。", text)
        self.assertIn("对照[^1][^3][^4]。", text)
        # Protected spans untouched
        self.assertIn("$P_z[1] + \\chi[2] = 0$", text)
        self.assertIn("`arr[1]`", text)
        self.assertIn("[Regular Link](https://example.org/doc)", text)
        self.assertIn('A["Input x[1]"]', text)
        # Default trailing links: DOI, arXiv, Website
        self.assertIn("[DOI](https://doi.org/10.1038/s41467-025-12345-6)", text)
        self.assertIn("[arXiv](https://arxiv.org/abs/1706.03762)", text)
        self.assertIn("[Website](https://example.org/papers/miller-downing-2002)", text)

        # Custom link label: [Website Connection](...)
        out_custom = self.work / "out_custom_label.md"
        self.run_cli(
            "render",
            str(self.draft_path),
            "--bib",
            str(self.bib_path),
            "-o",
            str(out_custom),
            "--link-label",
            "Website Connection",
        )
        custom_text = out_custom.read_text(encoding="utf-8")
        self.assertIn("[Website Connection](https://doi.org/10.1038/s41467-025-12345-6)", custom_text)
        self.assertIn("[Website Connection](https://arxiv.org/abs/1706.03762)", custom_text)
        self.assertIn("[Website Connection](https://example.org/papers/miller-downing-2002)", custom_text)

        # --no-links omits trailing Markdown links cleanly
        out_nolink = self.work / "out_nolink.md"
        self.run_cli("render", str(self.draft_path), "--bib", str(self.bib_path), "-o", str(out_nolink), "--no-links")
        nolink_text = out_nolink.read_text(encoding="utf-8")
        self.assertNotIn("[DOI](https://doi.org/", nolink_text)
        self.assertNotIn("[arXiv](https://arxiv.org/", nolink_text)

    def test_persistent_config_defaults_and_cli_override(self) -> None:
        cfg_file = self.work / ".typora-citation.json"
        self.run_cli(
            "config",
            "--path",
            str(cfg_file),
            "--set-bib-style",
            "nature",
            "--set-link-label",
            "Website Connection",
        )
        self.assertTrue(cfg_file.is_file())

        # Render without --bib-style or --link-label: should inherit workspace .typora-citation.json!
        out_ws = self.work / "out_from_workspace_default.md"
        self.run_cli("render", str(self.draft_path), "--bib", str(self.bib_path), "-o", str(out_ws))
        ws_text = out_ws.read_text(encoding="utf-8")
        self.assertIn("*Nat. Commun.* **16**, 4201 (2025). [Website Connection](https://doi.org/10.1038/s41467-025-12345-6)", ws_text)

        # Explicit CLI flag overrides workspace default
        out_override = self.work / "out_cli_override.md"
        self.run_cli(
            "render",
            str(self.draft_path),
            "--bib",
            str(self.bib_path),
            "-o",
            str(out_override),
            "--bib-style",
            "apa",
            "--link-label",
            "auto",
        )
        ov_text = out_override.read_text(encoding="utf-8")
        self.assertIn("(2025).", ov_text)
        self.assertIn("[DOI](https://doi.org/10.1038/s41467-025-12345-6)", ov_text)

        # Reset workspace config back to builtin IEEE default
        self.run_cli("config", "--path", str(cfg_file), "--reset")
        self.assertFalse(cfg_file.is_file())
        out_reset = self.work / "out_after_reset.md"
        self.run_cli("render", str(self.draft_path), "--bib", str(self.bib_path), "-o", str(out_reset))
        self.assertIn("Art. no. 4201, 2025, doi: 10.1038/s41467-025-12345-6. [DOI](https://doi.org/10.1038/s41467-025-12345-6)", out_reset.read_text(encoding="utf-8"))

    def test_multi_style_and_multi_scheme_roundtrip_no_duplicate_links(self) -> None:
        cur = self.work / "step_ieee.md"
        self.run_cli("render", str(self.draft_path), "--bib", str(self.bib_path), "-o", str(cur), "--scheme", "A", "--bib-style", "ieee")

        # Round-trip through all 7 bibliography styles and verify author/title preservation + no duplicate links
        for style in ("nature", "apa", "vancouver", "acs", "chicago", "gbt7714", "ieee"):
            nxt = self.work / f"step_{style}.md"
            self.run_cli("convert", str(cur), "-o", str(nxt), "--scheme", "A", "--bib-style", style)
            self.run_cli("verify", str(nxt), "--scheme", "A")
            body = nxt.read_text(encoding="utf-8")
            self.assertIn("https://doi.org/10.1038/s41467-025-12345-6", body)
            self.assertIn("Geometrical and statistical properties of systems of linear inequalities", body)
            self.assertNotIn('"M. Geometrical', body)
            self.assertNotIn("(1965). M. Geometrical", body)
            self.assertNotIn(") [DOI](", body)
            cur = nxt
        self.assertIn('T. M. Cover, "Geometrical and statistical properties', cur.read_text(encoding="utf-8"))

        # Verify toggling APA between --no-links and --link-mode auto never duplicates DOI URLs
        apa_off = self.work / "apa_nolinks.md"
        apa_on = self.work / "apa_links_back.md"
        self.run_cli("convert", str(cur), "-o", str(apa_off), "--scheme", "A", "--bib-style", "apa", "--no-links")
        self.assertIn("https://doi.org/10.1109/PGEC.1965.264137", apa_off.read_text(encoding="utf-8"))
        self.assertNotIn("[DOI](", apa_off.read_text(encoding="utf-8"))
        self.run_cli("convert", str(apa_off), "-o", str(apa_on), "--scheme", "A", "--bib-style", "apa", "--link-mode", "auto")
        apa_on_text = apa_on.read_text(encoding="utf-8")
        self.assertEqual(apa_on_text.count("10.1109/PGEC.1965.264137"), 1)
        self.assertIn("[DOI](https://doi.org/10.1109/PGEC.1965.264137)", apa_on_text)

        # Round-trip through schemes B -> C -> D -> E (cn-proposal) -> A and F (.bib)
        for sch in ("B", "C", "D"):
            nxt = self.work / f"scheme_{sch}.md"
            self.run_cli("convert", str(cur), "-o", str(nxt), "--scheme", sch)
            self.run_cli("verify", str(nxt), "--scheme", sch)
            cur = nxt

        out_e = self.work / "scheme_E_proposal.md"
        self.run_cli("convert", str(cur), "-o", str(out_e), "--preset", "cn-proposal")
        self.run_cli("verify", str(out_e), "--scheme", "E")
        self.assertNotIn("[DOI](https://doi.org/", out_e.read_text(encoding="utf-8"))

        out_f = self.work / "scheme_F.md"
        self.run_cli("convert", str(cur), "-o", str(out_f), "--scheme", "F")
        self.assertTrue(out_f.with_suffix(".bib").is_file())
        self.assertIn("url = {https://example.org/papers/miller-downing-2002}", out_f.with_suffix(".bib").read_text(encoding="utf-8"))

    def test_verify_catches_hallucination_and_link_defects(self) -> None:
        base = self.work / "good.md"
        self.run_cli("render", str(self.draft_path), "--bib", str(self.bib_path), "-o", str(base))
        good_text = base.read_text(encoding="utf-8")

        # 1. DOI-suffix-as-article-number hallucination (12345 from s41467-025-12345-6)
        bad_art = self.work / "bad_art.md"
        bad_art.write_text(good_text.replace("Art. no. 4201", "Art. no. 12345"), encoding="utf-8", newline="\n")
        res_art = self.run_cli("verify", str(bad_art), "--scheme", "A", expect_rc=1)
        self.assertIn("DOI-suffix-as-article-number", res_art.stderr)

        # 2. Mismatched inline DOI vs trailing hyperlink
        bad_mismatch = self.work / "bad_mismatch.md"
        bad_mismatch.write_text(
            good_text.replace(
                "[DOI](https://doi.org/10.1038/s41467-025-12345-6)",
                "[DOI](https://doi.org/10.1038/s41467-025-99999-9)",
            ),
            encoding="utf-8",
            newline="\n",
        )
        res_mis = self.run_cli("verify", str(bad_mismatch), "--scheme", "A", expect_rc=1)
        self.assertIn("does not match trailing hyperlink", res_mis.stderr)

        # 3. Duplicate trailing hyperlink
        bad_dup = self.work / "bad_dup.md"
        bad_dup.write_text(
            good_text.replace(
                "[DOI](https://doi.org/10.1038/s41467-025-12345-6)",
                "[DOI](https://doi.org/10.1038/s41467-025-12345-6) [Website](https://doi.org/10.1038/s41467-025-12345-6)",
            ),
            encoding="utf-8",
            newline="\n",
        )
        res_dup = self.run_cli("verify", str(bad_dup), "--scheme", "A", expect_rc=1)
        self.assertIn("Duplicate trailing Markdown hyperlinks", res_dup.stderr)


if __name__ == "__main__":
    unittest.main()
