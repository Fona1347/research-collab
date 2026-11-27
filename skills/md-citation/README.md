# Academic Markdown Citation (`md-citation`)

Format, convert, renumber, enrich, and audit academic citations in Markdown—with zero third-party Python dependencies, designed for **GFM-footnote hosts (Google Antigravity, Typora, Obsidian, GitHub/GitLab)** and **compatible fallback schemes (`B`–`F`)** everywhere else.

## Key Capabilities

- **GFM Jump-and-Return Footnotes + Multi-Host Fallback**: Defaults to standard GFM footnotes (**Scheme A**, `[^1]`), which render clickable superscript jump-to-bottom and `↩` return links in Google Antigravity, Typora, Obsidian, and GitHub/GitLab. In chat or editor environments without GFM footnote rendering, switch in one command to flat anchors (`[[1]](#ref-1)`), hover reference links (`[[1]][ref-1]`), superscript anchors, plain brackets (`[1]`, `[2–4]`), or Pandoc `[@key]` + `.bib`.
- **7 Academic Bibliography Styles with User-Configurable Default**: Built-in default is official **IEEE (`ieee`)**, and you can switch per run or persist your own default across **IEEE**, **GB/T 7714-2015 (`gbt7714`)**, **Nature (`nature`)**, **APA 7th (`apa`)**, **Vancouver (`vancouver`)**, **ACS (`acs`)**, and **Chicago 17th (`chicago`)**.
- **Clickable Trailing Source Hyperlinks**: Automatically appends a verified clickable link (`[DOI](https://doi.org/...)`, `[arXiv](https://arxiv.org/abs/...)`, or `[Website](https://...)`) at the end of each reference entry, with customizable link text (e.g., `--link-label "Website Connection"` or `--link-label "原文链接"`) and one-flag opt-out (`--no-links`) for print-ready drafts.
- **Strict `1..N` First-Appearance Renumbering & Deterministic QA**: Re-indexes edited drafts automatically, switches losslessly across Schemes `A`–`F` and all 7 styles, checks DOI-suffix-as-article-number hallucinations and DOI/link mismatches, and protects `$math$`, inline code, headings, and `mermaid` blocks.

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
python scripts/citation_tool.py render draft.md --bib refs.bib -o chat_reply.md --preset chat-gfm  # unique per-turn prefix for shared-DOM chat

# Convert an existing document to another style or scheme (also strips chat prefixes back to bare [^1])
python scripts/citation_tool.py convert output.md -o output_apa.md --preset md-apa
python scripts/citation_tool.py convert output.md -o proposal.md --preset cn-proposal
python scripts/citation_tool.py convert output.md -o compat_flat.md --scheme B --id-prefix auto

# Deterministic QA check
python scripts/citation_tool.py verify output.md --scheme A
```

## Configuration Precedence

1. Explicit CLI flags (`--preset`, `--scheme`, `--bib-style`, `--link-mode` / `--no-links`, `--link-label`, `--heading`)
2. Explicit `--config <path>`
3. Project-level `.md-citation.json` (auto-discovered upward from the input file or working directory)
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
