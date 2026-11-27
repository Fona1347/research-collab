# Typora & Academic Markdown Citation (`typora-citation`)

Format, convert, renumber, enrich, and audit academic citations in Markdown—built for **Antigravity chat, Typora, and multi-venue academic publishing** with zero third-party Python dependencies.

## Why Researchers & Students Love It

- **Interactive Jump-and-Return in Antigravity & Typora**: Default **Scheme A** (`[^1]`) renders superscript footnotes directly inside Agent responses and Typora notes—click to jump to the reference, click the trailing hyperlink to open the original paper, and click `↩` to return to the exact sentence.
- **7 Academic Bibliography Styles with User-Configurable Default**: Built-in default is official **IEEE (`ieee`)**, and you can switch per run or persist your own default across **IEEE**, **GB/T 7714-2015 (`gbt7714`)**, **Nature (`nature`)**, **APA 7th (`apa`)**, **Vancouver (`vancouver`)**, **ACS (`acs`)**, and **Chicago 17th (`chicago`)**.
- **Clickable Trailing Source Hyperlinks**: Automatically appends a verified clickable link (`[DOI](https://doi.org/...)`, `[arXiv](https://arxiv.org/abs/...)`, or `[Website](https://...)`) at the end of each reference entry, with customizable link text (e.g., `--link-label "Website Connection"` or `--link-label "原文链接"`) and one-flag opt-out (`--no-links`) for print-ready drafts.
- **Strict `1..N` First-Appearance Renumbering & QA**: Re-indexes edited drafts automatically, switches losslessly across Schemes `A`–`F` (including Pandoc `[@key]` + `.bib`), checks DOI-suffix-as-article-number hallucinations, and protects `$math$`, inline code, headings, and `mermaid` blocks.

## Quick Start

```powershell
# Inspect or set your persistent default citation style & link label
python scripts/citation_tool.py config --show
python scripts/citation_tool.py config --set-bib-style ieee --set-link-label auto
python scripts/citation_tool.py config --set-bib-style nature --set-link-label "Website Connection"

# Resolve a BibTeX library (offline, or add --online for Crossref lookup)
python scripts/citation_tool.py resolve --bib refs.bib --out refs_master.json

# Render a draft with [^Key] or [@Key] placeholders
python scripts/citation_tool.py render draft.md --refs refs_master.json -o output.md

# Convert an existing document to another style or scheme
python scripts/citation_tool.py convert output.md -o output_apa.md --preset typora-apa
python scripts/citation_tool.py convert output.md -o proposal.md --preset cn-proposal

# Deterministic QA check
python scripts/citation_tool.py verify output.md --scheme A
```

## Configuration Precedence

1. Explicit CLI flags (`--preset`, `--scheme`, `--bib-style`, `--link-mode` / `--no-links`, `--link-label`, `--heading`)
2. Explicit `--config <path>`
3. Project-level `.typora-citation.json` (auto-discovered upward from the input file or working directory)
4. Skill-level `config/local.json` (see [config/local.example.json](config/local.example.json); preserved across `research-collab` updates and excluded from public packages)
5. Built-in defaults: `Scheme A`, `ieee`, `link_mode=auto`, `link_label=auto`

## Example Output (Scheme A + IEEE + Clickable Links)

```markdown
High-dimensional nonlinear projections expand linear separability[^1], while attention architectures enable parallel sequence modeling[^2].

---

## References

[^1]: T. M. Cover, "Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition," *IEEE Trans. Electron. Comput.*, vol. EC-14, no. 3, pp. 326–334, 1965, doi: 10.1109/PGEC.1965.264137. [DOI](https://doi.org/10.1109/PGEC.1965.264137)

[^2]: A. Vaswani *et al.*, "Attention is all you need," *arXiv preprint* arXiv:1706.03762, 2017, doi: 10.48550/arXiv.1706.03762. [DOI](https://doi.org/10.48550/arXiv.1706.03762)
```

See [SKILL.md](SKILL.md), [references/bibliography-styles.md](references/bibliography-styles.md), [references/schemes-and-templates.md](references/schemes-and-templates.md), and [references/academic-prose-rules.md](references/academic-prose-rules.md) for full rules.
