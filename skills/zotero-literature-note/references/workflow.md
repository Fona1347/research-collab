# Workflow

Use this workflow when generating, revising, enriching, or versioning a Markdown literature reading note from a Zotero item.

## 1. Intake

Parse the user's request for:

- Zotero item title, item key, DOI, or selected item.
- Output root directory.
- Target language.
- Target length, if already provided.
- Writing style, if already provided.
- Template preference, if already provided.

If the output root directory is missing, ask for it before collecting materials.

If the user provides a final `.md` path instead of an output root, confirm whether to skip the default paper subdirectory rule before saving.

## 2. Zotero Material Collection

Use the Zotero plugin / Zotero skill as the primary access route. Do not draft a full note before locating or confirming the Zotero item.

Collect what is available:

- Zotero metadata: title, authors, year, journal, DOI, item key.
- BibTeX or citation key when available.
- Children and notes, including Markdown child notes.
- Attachments, including PDF attachment keys.
- Annotations.
- `[LLM for Zotero]` generated notes and MinerU cache ZIPs when present.
- PDF/full text or parsed full text when available and requested by the task.

Only use web search after the user explicitly allows it as fallback.

## 3. MinerU Cache Discovery

For paper-content tasks, check for a matching `[LLM for Zotero] MinerU cache` after locating the Zotero item and listing its children.

Use `references/mineru-cache-policy.md` for details. The required behavior is:

1. Find PDF attachment candidates and their attachment keys.
2. Look for child ZIP attachments named like `[LLM for Zotero] MinerU cache <PDF_ATTACHMENT_KEY>.zip`.
3. Verify the cache belongs to the parent Zotero item and source PDF before using it.
4. If verified, prefer `manifest.json` for structure and `full.md` or content lists for paper content.
5. If no matching cache exists, ask before raw PDF parsing.
6. If web search would be needed, ask separately and use it only as fallback.

Do not modify Zotero items, child notes, tags, collections, attachments, or cache ZIPs.

## 4. Source Inventory

Create `<paper-dir>/source-inventory.md`.

Classify each source with:

| Field | Meaning |
|---|---|
| source id | item key, note key, attachment key, or stable label |
| type | metadata, BibTeX, PDF/full text, MinerU cache, manual Markdown note, LLM-generated Markdown note, annotation, figure note, formula note, etc. |
| content signal | short description of useful content |
| evidence level | high, medium, low |
| use decision | main draft, local enhancement, background only, excluded, needs caution |
| reason | why it is used or excluded |

For MinerU cache rows, also record Zotero item key, PDF attachment key, cache attachment key, cache status, used files, and read scope when available.

Inventory must filter, not merely list. Use these decisions:

- `main draft`: structure or substantively write the note.
- `local enhancement`: support formulas, figures, annotation questions, or limitations.
- `background only`: useful context but not central.
- `excluded`: duplicate, vague, unsupported, irrelevant, or low quality.
- `needs caution`: useful but conflicts with stronger evidence or lacks direct support.

Do not place the full inventory in the final note body.

## 5. Visual Evidence Collection

Run this step when PDF/full-text access is allowed and the paper is figure-heavy, model-heavy, formula-heavy, mechanism-heavy, or the selected output would benefit from visual explanation.

Use `references/visual-evidence-policy.md` and `references/pdf-toolchain-appendix.md` for details. The required behavior is:

1. Read the verified MinerU cache `manifest.json` to identify figures, tables, captions, pages, and image paths.
2. Select only high-value figures/tables that directly support the note objective.
3. Follow the crop-first decision ladder: verified MinerU figure image, high-resolution PDF page render when needed, complete figure crop, selected panel crop when the note discusses specific panels, then full-page fallback only if crop context is unsafe.
4. Prefer cropped figure assets or cropped key-panel assets for main-note insertion.
5. Use rendered full PDF pages as QA fallback or page evidence when MinerU images are incomplete, panel-level crops are ambiguous, or figure crops cannot be trusted.
6. Save copied, extracted, cropped, or rendered visual assets under the final note's Typora-style sibling asset directory: `<note-filename-without-.md>.assets/`.
7. Put inserted crops at the asset root, full page renders under `pages/`, QA candidates under `qa/`, and rejected-but-retained crops under `unused/` when retained.
8. Use semantic kebab-case filenames instead of raw cache hash names.
9. Visually inspect each selected asset before calling it image evidence.
10. Record visual evidence in `source-inventory.md`, including asset path, evidence type, crop source, source page, crop kind, inserted/fallback role, QA status, fallback page asset, manual/automatic crop note, actual width when known, and display zoom when used.
11. Insert only selected cropped figures/panels into the final Markdown note by default. Insert full pages only when a crop cannot preserve the needed context and label that asset as rendered page fallback.

Use this image syntax by default:

```html
<img src="./<note-filename-without-.md>.assets/fig1-short-label.png" alt="Fig. 1: short label" style="zoom:67%;" />
```

Use Markdown image syntax only as a fallback when the target renderer cannot use HTML:

```markdown
![Fig. 1: short label](./<note-filename-without-.md>.assets/fig1-short-label.png)
```

Do not copy, edit, or write back to Zotero attachments or MinerU cache ZIPs. Do not expose Zotero storage paths, absolute local paths, local file URLs, or internal ZIP paths in the final note.

## 6. Template Routing

After inventory, ask or confirm:

- Target length.
- Writing style.
- Note template.

Recommend one template:

- `research-standard`: default, concise research note.
- `flexible-note`: adaptive structure for unusual paper types.
- `layered-explainer`: summary first, detailed explanation later.

Use the user's explicit choice when provided.

## 7. Draft and Enhancement

Generate the note using the selected template.

Automatic enhancement is on by default after template and writing preferences are confirmed. Do not ask for each enhancement module separately unless material is missing, web search would be needed, the user disables it, or the target length makes it impossible.

Default enhancement order:

1. Model, method, and key formulas.
2. Figures, tables, and visual logic.
3. Annotation questions and unresolved issues.
4. Contributions, limitations, and cautions.

Keep the main body close to the target length. Slight overflow is acceptable for accuracy. Move complex details to appendices when they would overload the main body.

## 8. Save Output

Default layout:

```text
<output-root>/
└── <normalized-paper-short-title>/
    ├── <short-title>_文献阅读笔记_YYYYMMDD-HHMM.md
    ├── <short-title>_文献阅读笔记_YYYYMMDD-HHMM.assets/
    ├── source-inventory.md
    └── README.md
```

If target files already exist:

1. Read existing note files and README if present.
2. Summarize what exists.
3. Ask whether to locally update the current file, create a new timestamped version, or only provide suggestions.
4. Default to a new timestamped version unless the user explicitly permits editing the current file.

## 9. Failure and Fallback

Use this ladder:

1. Stop and report the exact missing gate.
2. Ask whether the user wants to supply missing material or allow web search.
3. If web search is allowed, use it only for missing bibliographic data, DOI/publisher lookup, related-paper verification, or open full text discovery.
4. If material remains insufficient, generate a downgraded note only when useful and clearly label it as based on limited evidence.

If only metadata is available, do not generate a full reading note. Produce a bibliographic stub and ask for verified cache, PDF/full text, notes, permission to parse PDF, or permission to search.

## 10. Manual Edit Handoff

If the user says they manually edited the note:

1. Read the current Markdown file first.
2. Summarize current structure and notable user changes.
3. Ask whether to locally modify the current file, create a new timestamped version, or only provide suggested edits.
4. Default to a new timestamped version if the user does not explicitly permit editing the current file.

Never revert user edits.
