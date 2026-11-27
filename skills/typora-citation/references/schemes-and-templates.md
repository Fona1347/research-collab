# Typora & Markdown Citation Schemes (`A`–`F`) & User Default Configuration

All numbered schemes (`A`–`E`) enforce **strict order-of-first-appearance numbering (`1, 2, ..., N`)** from top to bottom, left to right across body prose and tables.

---

## Scheme A (Default): Native Hoverable Jump-and-Return Footnotes `[^1]`

Best for **Antigravity responses** and **Typora reading/writing**:
- In **Antigravity**: inline `[^1]` renders cleanly inside the Agent's answer, clicking jumps directly to the full citation at the bottom, clicking the trailing `[DOI]`/`[Website]` link opens the original paper, and clicking `↩` returns straight to the sentence you were reading.
- In **Typora**: hovering over `[^1]` pops up a floating preview card showing the full formatted reference, clicking jumps to the bottom, and `↩` jumps back.

### Syntax Rules
- **Single citation**: `[^1]`
- **Multiple citations at the same spot**: Must be written as **individual adjacent footnote tags** sorted ascending, e.g., `[^1][^2][^3]` — **never** `[^1-3]` and **never** `[^1, 2]` (Typora and GFM footnote parsers require separate `[^k]` tokens to bind each jump/hover card).
- **Bottom reference block**: Placed at the end of the document under `## 参考文献（References）` (or `## References` for English documents), with **one blank line (`\n\n`) between every `[^k]:` definition**:

```markdown
Cover 证明了高维非线性特征映射的线性可分性定理[^1]，而 Transformer 架构实现了完全基于注意力的并行序列建模[^2]。

---

## 参考文献（References）

[^1]: T. M. Cover, "Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition," *IEEE Trans. Electron. Comput.*, vol. EC-14, no. 3, pp. 326–334, 1965, doi: 10.1109/PGEC.1965.264137. [DOI](https://doi.org/10.1109/PGEC.1965.264137)

[^2]: A. Vaswani *et al.*, "Attention is all you need," *arXiv preprint* arXiv:1706.03762, 2017, doi: 10.48550/arXiv.1706.03762. [DOI](https://doi.org/10.48550/arXiv.1706.03762)
```

---

## Scheme B: IEEE Flat Bracket + In-Page Anchor Jump `[[1]](#ref-1)`

Matches traditional IEEE journal visual appearance (non-superscript inline `[1]`, `[2]–[4]`) while supporting `Ctrl + Click` / click jump to the reference entry in Typora and GitHub.

### Syntax Rules
- **Single citation**: `[[1]](#ref-1)` (preceded by a space in English prose: `...framework [[1]](#ref-1).`; flush in Chinese prose: `……框架[[1]](#ref-1)。`)
- **Multiple citations**:
  - 2 numbers: `[[1]](#ref-1), [[2]](#ref-2)`
  - >= 3 contiguous numbers: `[[2]](#ref-2)–[[4]](#ref-4)`
- **Bottom reference block**:

```markdown
<a id="ref-1"></a>[1] T. M. Cover, "Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition," *IEEE Trans. Electron. Comput.*, vol. EC-14, no. 3, pp. 326–334, 1965, doi: 10.1109/PGEC.1965.264137. [DOI](https://doi.org/10.1109/PGEC.1965.264137)
```

---

## Scheme C: IEEE Flat Bracket + Hover Title Tooltip + Jump `[[1]][ref-1]`

Combines flat IEEE bracket visuals `[1]` with native Markdown reference-link hover tooltips and click-to-jump.

### Syntax Rules
- **Inline**: `[[1]][ref-1]`, contiguous range `[[2]][ref-2]–[[4]][ref-4]`
- **Visible bottom entry**: `<a id="ref-1"></a>[1] <Full formatted reference> [DOI](...)`
- **Hidden link-definition footer** (hidden in Typora reading view; double quotes inside title escaped):

```markdown
[ref-1]: #ref-1 "Cover — Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition (IEEE Trans. Electron. Comput., 1965)"
```

---

## Scheme D: Superscript Bracketed Anchor `<sup>[[1]](#ref-1)</sup>`

Matches Chinese doctoral dissertations and Chinese journal conventions (superscript `^[1]`, `^[2–4]`) with clickable in-page jump.

### Syntax Rules
- **Single citation**: `<sup>[[1]](#ref-1)</sup>`
- **Multiple citations**: `<sup>[[2]](#ref-2)–[[4]](#ref-4)</sup>` or `<sup>[[1]](#ref-1),[[3]](#ref-3)</sup>`
- **Bottom reference block**: `<a id="ref-1"></a>[1] <Full formatted reference>` separated by `\n\n`.

---

## Scheme E (`cn-proposal` Preset): Clean Plain-Text Brackets `[1]`, `[2–4]`

Zero-markup plain text brackets ideal for Chinese PhD proposals, dissertations, clean Git diffs, and direct Word/LaTeX export.

### Syntax Rules
- **Single citation**: `[1]`
- **Compressed ranges & lists**: `[2–4]`, `[1, 3–5]` (using en-dash `–`, U+2013)
- **Bottom reference block**:
  - With `--preset cn-proposal` (`--scheme E --bib-style gbt7714 --link-mode off`):
    ```markdown
    ## 参考文献

    [1] Cover T M. Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition[J]. IEEE Transactions on Electronic Computers, 1965, EC-14(3): 326–334. DOI: 10.1109/PGEC.1965.264137.
    ```
  - With `--scheme E --bib-style ieee`:
    ```markdown
    ## 参考文献（References）

    [1] T. M. Cover, "Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition," *IEEE Trans. Electron. Comput.*, vol. EC-14, no. 3, pp. 326–334, 1965, doi: 10.1109/PGEC.1965.264137. [DOI](https://doi.org/10.1109/PGEC.1965.264137)
    ```

---

## Scheme F: Pandoc Citation Syntax `[@CiteKey]` + Companion `.bib`

For external `pandoc --citeproc --csl=ieee.csl` compilation into Word (`.docx`) or LaTeX/PDF:
- **Inline**: `[@Cover1965_1]` or `[@Cover1965_1; @Vaswani2017_2]`
- **Companion file**: Generates deterministic UTF-8 BibTeX `<stem>.bib` alongside the `.md` file.

---

## Persistent User Defaults (`config/local.json` & `.typora-citation.json`)

Users can customize the default bibliography style, inline scheme, trailing link mode, link label, or heading without passing CLI flags on every call:

```json
{
  "default_scheme": "A",
  "default_bib_style": "ieee",
  "link_mode": "auto",
  "link_label": "auto",
  "heading": null
}
```

- **Personal skill-wide default**: `<skill_dir>/config/local.json` (created/updated via `citation_tool.py config --set-bib-style <style>`; preserved across `research-collab` updates and excluded from public packages).
- **Per-project default**: `.typora-citation.json` in a research workspace root (`citation_tool.py config --scope workspace --set-bib-style nature`).
- **One-off override**: CLI flags (`--bib-style`, `--scheme`, `--link-mode`, `--no-links`, `--link-label`, `--preset`) always override stored defaults.
