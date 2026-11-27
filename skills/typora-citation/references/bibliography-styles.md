# Multi-Style Academic Bibliography Rules & Clickable Source Links

`typora-citation` supports **7 academic bibliography styles** (`ieee` built-in default, user-configurable via `config/local.json` or `.typora-citation.json`) plus **verified trailing clickable hyperlinks** (`[DOI](...)`, `[arXiv](...)`, `[Website](...)`, or custom label).

---

## 1. Official IEEE (`--bib-style ieee`, Built-in Default)

Follow the **IEEE Editorial Style Manual (`IEEEtran`)**:

### 1.1 Author List Rules
- Format given names as initials with periods and spaces **before** the surname; preserve hyphenated given-name initials (`T. M. Cover`, `J.-C. Gartside`, `L.-Q. Chen`).
- **1 author**: `T. M. Cover,`
- **2 authors**: `P. C. Hohenberg and B. I. Halperin,` *(no comma before `and`)*
- **3 to 6 authors**: List **all** authors with an Oxford comma before `and`:
  `C. Horsman, S. Stepney, R. C. Wagner, and V. Kendon,`
- **7 or more authors**: First author followed by italicized `*et al.*,`:
  `A. Vaswani *et al.*,`
- **Chinese-language literature**: Keep Chinese names consistently (`张伟等,`) or romanize uniformly.

### 1.2 Article / Chapter Title Rules
- Enclose journal/conference/preprint titles in straight double quotes `"..."` with the **trailing comma inside the closing quote**: `"Title of paper,"`.
- If the title ends with `?` or `!`, omit the comma: `"When does a physical system compute?"`.
- Use **sentence case** while preserving proper nouns, chemical formulas (`$\text{SiO}_2$`), and acronyms (`CMOS`, `LLM`, `NLP`).

### 1.3 Entry Templates by Publication Type
1. **Journal Article (Page Range)**:
   `T. M. Cover, "Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition," *IEEE Trans. Electron. Comput.*, vol. EC-14, no. 3, pp. 326–334, 1965, doi: 10.1109/PGEC.1965.264137. [DOI](https://doi.org/10.1109/PGEC.1965.264137)`
2. **Journal Article (Electronic Article Number — `Nat. Commun.`, `Sci. Adv.`, `Phys. Rev.`, `Adv. Mater.`, etc.)**:
   `A. Researcher *et al.*, "Title of paper," *Nat. Commun.*, vol. 16, no. 1, Art. no. 4201, 2025, doi: 10.1038/s41467-025-12345-6. [DOI](https://doi.org/10.1038/s41467-025-12345-6)`
3. **Conference Proceedings**:
   `A. Vaswani *et al.*, "Attention is all you need," in *Adv. Neural Inf. Process. Syst. (NeurIPS)*, vol. 30, 2017, pp. 5998–6008. [Website](https://papers.nips.cc/paper/7181-attention-is-all-you-need)`
4. **Book / Monograph** *(italicized title, no quotes)*:
   `G. Pask, *An Approach to Cybernetics*. London, U.K.: Hutchinson, 1961.`
5. **Preprint (`arXiv` / `bioRxiv` — explicitly labeled as preprint)**:
   `A. Vaswani *et al.*, "Attention is all you need," *arXiv preprint* arXiv:1706.03762, 2017, doi: 10.48550/arXiv.1706.03762. [DOI](https://doi.org/10.48550/arXiv.1706.03762)`

---

## 2. GB/T 7714-2015 (`--bib-style gbt7714`)

Matches Chinese national academic, thesis, and doctoral proposal standards (`--preset cn-proposal` pairs Scheme E + `gbt7714` + `--link-mode off` by default):

- **Authors**: Surname followed by given-name initials **without periods** (`Cover T M.` or `Horsman C, Stepney S, Wagner R C, et al.`); list up to **3 authors**, then `, et al.` (EN) or `, 等.` (ZH).
- **Document Type Identifiers**: `[J]` journal, `[C]` conference, `[M]` monograph/book, `[D]` dissertation, `[EB/OL]` preprint/online resource.
- **Journal Template**:
  `[1] Cover T M. Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition[J]. IEEE Transactions on Electronic Computers, 1965, EC-14(3): 326–334. DOI: 10.1109/PGEC.1965.264137.`
- **Preprint Template**:
  `[2] Vaswani A, Shazeer N, Parmar N, et al. Attention is all you need[EB/OL]. arXiv:1706.03762, 2017. DOI: 10.48550/arXiv.1706.03762.`

---

## 3. Nature Portfolio (`--bib-style nature`, `--preset typora-nature`)

- **Authors**: `Surname, I. I.` up to **5 authors** with `&` before the last; 6+ authors collapse to `First, I. I. *et al.*`.
- **Journal Template**: No quotes around article title, abbreviated italic journal, **bold** volume, pages/article number, year in parentheses:
  `Cover, T. M. Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition. *IEEE Trans. Electron. Comput.* **EC-14**, 326–334 (1965). [DOI](https://doi.org/10.1109/PGEC.1965.264137)`

---

## 4. APA 7th Edition (`--bib-style apa`, `--preset typora-apa`)

- **Authors**: `Surname, I. I.`, up to 20 authors with `, & ` before the final author (or first author `et al.` when truncated).
- **Journal Template**: Year in parentheses after authors, sentence-case title without quotes, *italicized full journal name*, *italicized volume*(issue), pages:
  `Cover, T. M. (1965). Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition. *IEEE Transactions on Electronic Computers*, *EC-14*(3), 326–334. [DOI](https://doi.org/10.1109/PGEC.1965.264137)`
  *(When `--link-mode off` is selected, appends the canonical `https://doi.org/...` URL directly per APA 7th.)*

---

## 5. Vancouver / ICMJE (`--bib-style vancouver`, `--preset typora-vancouver`)

Standard biomedical and clinical style:
- **Authors**: `Surname II` (compact initials without periods/spaces), up to 6 authors then `et al.`.
- **Journal Template**:
  `Cover TM. Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition. *IEEE Trans. Electron. Comput.* 1965;EC-14(3):326–334. doi:10.1109/PGEC.1965.264137. [DOI](https://doi.org/10.1109/PGEC.1965.264137)`

---

## 6. American Chemical Society (`--bib-style acs`, `--preset typora-acs`)

Widely used in chemistry, materials science, and nanotechnology:
- **Authors**: Semicolon-separated `Surname, I. I.; Surname2, I.`.
- **Journal Template**: Bold year, italic volume, parenthesized issue, pages:
  `Cover, T. M. Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition. *IEEE Trans. Electron. Comput.* **1965**, *EC-14* (3), 326–334. [DOI](https://doi.org/10.1109/PGEC.1965.264137)`

---

## 7. Chicago 17th Bibliography (`--bib-style chicago`, `--preset typora-chicago`)

- **Authors**: First author inverted (`Surname, Given`), subsequent authors normal order (`Given Surname`), `, and ` before final author.
- **Journal Template**: Quoted title with period inside closing quote, *italicized full journal*, `vol, no. issue (year): pages`:
  `Cover, Thomas M. "Geometrical and statistical properties of systems of linear inequalities with applications in pattern recognition." *IEEE Transactions on Electronic Computers* EC-14, no. 3 (1965): 326–334. [DOI](https://doi.org/10.1109/PGEC.1965.264137)`

---

## 8. Clickable Trailing Hyperlinks (`--link-mode` & `--link-label`)

To make every footnote immediately verifiable in Antigravity and Typora, `citation_tool.py` appends a clickable Markdown link at the end of each reference entry by default (`--link-mode auto`):

- **Verified URL Resolution Priority** *(never fabricates links)*:
  1. `doi` -> `https://doi.org/<normalized_doi>` (auto label: `[DOI]`)
  2. `arxiv_id` -> `https://arxiv.org/abs/<arxiv_id>` (auto label: `[arXiv]`)
  3. Explicit `url` starting with `http://` or `https://` -> `<url>` (auto label: `[Website]`)
  4. None available -> omit trailing link cleanly.
- **Custom Link Label**: Pass `--link-label "Website"`, `--link-label "Website Connection"`, `--link-label "Link"`, or `--link-label "原文链接"` — or persist it via `citation_tool.py config --set-link-label "Website Connection"`.
- **Disable for Print / Plain Export**: Pass `--no-links` or `--link-mode off` (automatically off in `--preset cn-proposal` unless `--link-mode auto` is explicitly passed).
- **Lossless Round-Trip**: Re-running `convert` strips any prior trailing `[Label](url)` first while retaining its URL/DOI metadata, so links never duplicate.

---

## 9. Offline-First Metadata Resolution & Anti-Hallucination Rules

1. **Zero Zotero-MCP Lock-In**:
   - Parse existing references inside the Markdown file or local `.bib`/`.json` files directly in Python. Do not query Zotero MCP unless the user explicitly asks to pull from Zotero.
2. **Optional Crossref Public API Enrichment (`--online`)**:
   - When fields (`vol.`, `no.`, `pp.`/`Art. no.`, full authors, `URL`) are missing and network lookup is explicitly requested via `--online`, query `https://api.crossref.org/works/<doi>`.
3. **Strict Anti-Hallucination Guardrails**:
   - **Never copy DOI manuscript IDs as page/article numbers**: In Nature Portfolio (`10.1038/s41467-025-12345-6`) and Wiley (`10.1002/adma.202512345`) DOIs, the 5-digit manuscript suffix frequently differs from the published `article-number`. Verify `article-number` or `page` explicitly.
   - **Never fabricate URLs**: Only emit a clickable trailing link from a verified `doi`, `arxiv_id`, or `url`.
   - **Explicit `[待核实]` Fallback**: If offline or Crossref lacks a field, emit `[待核实]` (or `[To be verified]`) rather than guessing.
