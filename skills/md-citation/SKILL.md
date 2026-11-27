---
name: md-citation
description: >-
  Format, convert, renumber, enrich, and validate academic citations and
  bibliographies in Markdown across Antigravity, Typora, Obsidian, GitHub, and
  downstream publishing. Defaults to standard GFM hoverable jump-and-return
  footnotes (`[^1]`) with official IEEE (`IEEEtran`) references and clickable
  trailing source links (`[DOI](...)` / `[arXiv](...)` / `[Website](...)`),
  while letting users customize and persist their default bibliography style
  (IEEE, GB/T 7714-2015, Nature, APA 7th, Vancouver, ACS, Chicago) and link
  label, and switch in one command to compatible flat-anchor or plain-bracket
  schemes (`[[1]](#ref-1)`, `[[1]][ref-1]`, thesis superscripts, `[1]`
  proposals, and Pandoc `[@key]` + `.bib`) for hosts without GFM footnote
  rendering. Activate whenever the user asks to format Markdown references,
  configure a default citation style, add clickable source links, unify
  citations into IEEE/Nature/APA/GB-T 7714 style, convert `(Author, Year)` /
  `.bib` / raw DOIs, or renumber citations after editing prose.
---

# Academic Markdown Citation Workflow (`md-citation`)

Standardize Markdown citations and reference lists across **GFM-footnote hosts (Google Antigravity, Typora, Obsidian, GitHub/GitLab)** and **plain/fallback hosts** with **100% first-appearance numbering bijection (`1..N`)**, **multi-style bibliography adaptation with user-configurable defaults**, **clickable trailing source hyperlinks**, **zero Zotero-MCP lock-in**, and **deterministic Python verification**.

---

## 1. Defaults, Host Compatibility & Configurable Preset Matrix

Built-in defaults apply unless overridden by the user's persistent config (`config/local.json` or project `.md-citation.json`) or an explicit request/flag:

| Dimension | Built-in Default | Switchable Alternatives & Customization | Reference Spec |
| :--- | :--- | :--- | :--- |
| **Inline Citation Scheme** | **Scheme A**: Standard GFM footnotes `[^1]`, multi-cite `[^45][^46]` (renders jump-and-return `↩` in Antigravity, Typora, Obsidian, GitHub/GitLab) | **B** `[[1]](#ref-1)` · **C** `[[1]][ref-1]` · **D** superscript anchor · **E** `[1]`, `[2–4]` · **F** `[@key]` (one-command fallback for chat/editor hosts that do not render GFM footnotes) | [schemes-and-templates.md](./references/schemes-and-templates.md) |
| **Bibliography Style** | **IEEE (`ieee`)** *(user-configurable default)* | **`gbt7714`** (GB/T 7714-2015) · **`nature`** · **`apa`** (APA 7th) · **`vancouver`** (ICMJE) · **`acs`** · **`chicago`** (17th) | [bibliography-styles.md](./references/bibliography-styles.md) |
| **Trailing Clickable Link** | **`--link-mode auto`**, **`--link-label auto`** (`[DOI](https://doi.org/...)`, `[arXiv](https://arxiv.org/abs/...)`, or `[Website](https://...)` from verified metadata only) | Custom label via `--link-label "Website"` / `"Website Connection"` / `"原文链接"`, or disable via `--link-mode off` / `--no-links` (default off in `cn-proposal`) | [bibliography-styles.md](./references/bibliography-styles.md) |
| **User Default Persistence** | Skill `config/local.json` or workspace `.md-citation.json` | Run `citation_tool.py config --set-bib-style <style>` (or `--show` / `--reset`). CLI flags always take highest precedence. | [schemes-and-templates.md](./references/schemes-and-templates.md) |
| **Prose Integration** | **Mode 1 (Rigorous Academic)**: Auto-match ZH/EN narrative syntax (`某某等指出……[^1]`) when writing or asked to polish | **Mode 2 (Lightweight Preserve)**: Zero prose wording changes; replace/renumber markers & bottom list only | [academic-prose-rules.md](./references/academic-prose-rules.md) |
| **Metadata Resolution** | **Offline-First + Crossref Fallback**: Document/`.bib`/`.json` first -> Crossref/DOI REST API (`--online`) -> `[待核实]` | Strict offline mode by default (only queries Crossref when `--online` is explicitly passed) | [bibliography-styles.md](./references/bibliography-styles.md) |

### Host Rendering Compatibility Note

- **GFM Footnote Rendering (`Scheme A`, `[^1]`)**: Supported natively with superscript jump-to-bottom and `↩` return in **Google Antigravity**, **Typora**, **Obsidian**, **GitHub / GitLab**, and `remark-gfm`-enabled web renderers.
- **Hosts Without GFM Footnote Support** *(e.g., plain terminal output, default ChatGPT/Claude/Cursor chat panes without footnote plugins)*: Switch cleanly in one command to **Scheme B** (`[[1]](#ref-1)`), **Scheme D** (superscript anchor), **Scheme E** (`[1]`, `[2–4]`), or **Scheme F** (`[@key]` + `.bib`).

### Setting or Checking the User's Default Citation Style

When the user asks to change their default citation format, scheme, or link label (e.g., *"以后默认用 Nature 格式"*, *"set default bibliography style to APA"*, *"把末尾超链接文字改成 Website Connection"*):
1. Run `citation_tool.py config --set-bib-style <style>` (and/or `--set-link-label "<label>"`, `--set-scheme <A-F>`, `--set-link-mode <auto|off>`).
2. Use `--scope skill` (default, writes `<skill_dir>/config/local.json`, preserved across `research-collab` updates) for global personal preference, or `--scope workspace` (writes `.md-citation.json` in the current project) for per-project overrides.
3. Run `citation_tool.py config --show` to confirm the active effective defaults.

Precedence order (highest to lowest):
`CLI flags / --preset` > `--config <path>` > workspace `.md-citation.json` > skill `config/local.json` > built-in defaults (`Scheme A` + `ieee` + `link_mode=auto` + `link_label=auto`).

---

## 2. Core Operating Modes

### Scenario A — Writing New Academic Markdown or Research Replies
1. **Use Standard GFM Footnotes (`Scheme A`) with Clickable Source Links**:
   - In GFM-footnote-enabled hosts (Antigravity, Typora, Obsidian, GitHub), place `[^1]`, `[^2]` right before clause/sentence punctuation and list `[^1]: ... [DOI](https://doi.org/...)` at the bottom separated by blank lines. Readers see superscript footnotes inline, click to jump straight to the citation, click the trailing link to open the original paper, and click `↩` to return to the exact line.
   - If the target host does not render GFM footnotes, emit **Scheme B** (`[[1]](#ref-1)`) or **Scheme E** (`[1]`) instead.
2. **Detect Document Language & Prose Mode**:
   - Follow [academic-prose-rules.md](./references/academic-prose-rules.md): in Chinese prose, write `Everschor-Sitte 等提出了……[^1]` (3+ authors), `Miller 与 Downing 提出了……[^2]` (2 authors), or place `[^k]` immediately **before** clause/sentence punctuation (`……已获实验验证[^3][^4]。`). In English prose, write `Everschor-Sitte *et al.* demonstrated...[^1]` or `...verified experimentally[^3][^4].`
   - Never place citation markers inside headings (`#`), `$math$`, `$$math$$`, inline code `` `...` ``, or `mermaid` blocks.
3. **Drafting Multi-Section or Long Documents**:
   - Assign stable temporary keys (`[^R001]`, `[^R002]`, … or `[@CiteKey]`) mapped to a JSON/BibTeX manifest during drafting, then run [`citation_tool.py render`](./scripts/citation_tool.py) once at assembly to assign strict `1..N` first-appearance numbers and emit the formatted reference section in the active default (or requested) style.

### Scenario B — Converting Existing Markdown (`(Author, Year)`, Raw DOIs, `.bib`, or Mixed Styles)
1. **Back Up Original First**: Create a byte-identical backup before rewriting any substantive user document.
2. **Extract & Resolve Metadata (No Zotero MCP Required)**:
   - Parse existing bottom reference lists, adjacent `.bib`/`.json` files, or inline DOIs directly via [`citation_tool.py resolve`](./scripts/citation_tool.py). Do **not** invoke Zotero MCP unless the user explicitly asks to pull from Zotero.
   - For entries missing `vol.`, `no.`, `pp.`/`Art. no.`, or `doi:`, run `resolve --online` to query public Crossref (`api.crossref.org/works/<doi>`).
   - **Anti-Hallucination Rule**: Never invent volume, issue, page numbers, or URLs, and never copy a DOI manuscript suffix (e.g., `s41467-025-12345-6` != `12345`) as an article number. Tag genuinely unavailable fields with `[待核实]` (ZH) or `[To be verified]` (EN); label unrefereed preprints explicitly with `arXiv:XXXX.XXXXX`. Only emit a trailing hyperlink when a verified `doi`, `arxiv_id`, or `url` exists.
3. **Apply Prose Mode**:
   - **Lightweight Mode (ordinary conversion / quick cleanup)**: Keep prose untouched; convert markers to `[^Rxxx]` (or run `citation_tool.py convert` directly for numbered styles).
   - **Rigorous Academic Mode (formal surveys, proposals, papers)**: Smoothly absorb parenthetical `(Author et al., 2025; DOI: ...)` dumps into natural ZH/EN academic narrative per [academic-prose-rules.md](./references/academic-prose-rules.md), ensuring zero surgical scars (`()`, `（）`, `。。`, dangling semicolons).
4. **Render & Verify**: Run `citation_tool.py convert` / `render` followed by `citation_tool.py verify`.

### Scenario C — Renumbering or Switching Styles & Schemes
When paragraphs are reordered/edited, or when switching between bibliography styles (`ieee` <-> `nature` <-> `apa` <-> `gbt7714` <-> `acs` <-> `vancouver` <-> `chicago`) or inline schemes (`A` <-> `B/C/D/E/F`):
- Run [`citation_tool.py convert`](./scripts/citation_tool.py) directly on the Markdown file. It strips any existing trailing link cleanly (preserving its URL/DOI without duplication), parses existing numbered citations (`A`–`E`), re-indexes them strictly in `1..N` order of first appearance, deduplicates and sorts multi-citation clusters, fixes misplaced post-punctuation markers, and re-emits the target scheme, bibliography style, and clickable trailing link.

---

## 3. CLI Quick Reference (`scripts/citation_tool.py`)

Run with standard `python` (pure Python 3.10+ stdlib, zero external packages):

```powershell
# 0. Inspect or customize persistent defaults (stored in config/local.json or project .md-citation.json)
python "<skill_dir>/scripts/citation_tool.py" config --show
python "<skill_dir>/scripts/citation_tool.py" config --set-bib-style nature --set-link-label "Website"
python "<skill_dir>/scripts/citation_tool.py" config --set-bib-style apa --scope workspace
python "<skill_dir>/scripts/citation_tool.py" config --reset

# 1. Resolve .bib or raw DOIs into normalized metadata + all 7 bibliography styles (offline or --online Crossref)
python "<skill_dir>/scripts/citation_tool.py" resolve --bib refs.bib --out refs_master.json --online

# 2. Render a draft containing [^R001] / [@Key] placeholders (uses configured default: built-in Scheme A + IEEE + clickable links)
python "<skill_dir>/scripts/citation_tool.py" render input_draft.md --refs refs_master.json -o output.md
python "<skill_dir>/scripts/citation_tool.py" render input_draft.md --bib refs.bib -o output_nature.md --bib-style nature --link-label "Website Connection"

# 3. Renumber an edited Markdown file OR switch between Schemes (A-F) and Styles (ieee/gbt7714/nature/apa/vancouver/acs/chicago)
python "<skill_dir>/scripts/citation_tool.py" convert report.md -o report_renumbered.md
python "<skill_dir>/scripts/citation_tool.py" convert report.md -o report_apa.md --preset md-apa
python "<skill_dir>/scripts/citation_tool.py" convert report.md -o proposal_clean.md --preset cn-proposal
python "<skill_dir>/scripts/citation_tool.py" convert report.md -o ieee_flat.md --scheme B --no-links

# 4. Run deterministic QA audit (1..N bijection, first-appearance order, link integrity, punctuation, math/table safety)
python "<skill_dir>/scripts/citation_tool.py" verify output.md --scheme A
```

---

## 4. Mandatory Verification Gate

Before declaring any citation task complete, run `citation_tool.py verify <file.md> --scheme <A|B|C|D|E>` and confirm `0` errors:
1. **Exact `1..N` Bijection & Monotonic First Appearance**: Every inline citation `1..N` maps 1-to-1 to a bottom reference entry, and the first appearance of each unique reference across the body is strictly `1, 2, ..., N`.
2. **Scheme-Specific Rendering Integrity**:
   - In **Scheme A**: Adjacent citations are separate `[^45][^46]` tags (never `[^45-47]` or `[^45, 46]`), and every `[^k]: ...` definition at the bottom is separated by a blank line (`\n\n`) so footnote hover cards and jump-back links stay isolated.
   - In **Schemes B/D/E**: Contiguous runs of >= 3 citations compress cleanly with en-dash (`[45–47]`), and non-contiguous clusters sort ascending (`[12, 45–47]`).
3. **Clickable Link & Anti-Hallucination Hygiene**:
   - Every trailing hyperlink uses a valid `http://` or `https://` target with no duplicate trailing links and no DOI mismatch between inline `doi:` text and the trailing `doi.org` URL.
   - Zero DOI-suffix-as-article-number collisions.
4. **Punctuation, Math & Table Hygiene**: `0` citations placed after Chinese sentence-ending punctuation (`[，。；：！？][^\d+]`), `0` citations inside `$...$`/`$$...$$`/`mermaid`/headings, `0` empty parentheses `()`/`（）`, and `0` broken GFM table pipes.
