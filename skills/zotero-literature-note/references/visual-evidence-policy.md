# Visual Evidence Policy

Use this policy when generating literature notes from Zotero items with PDF attachments, MinerU cache, figures, tables, or rendered PDF pages.

## When To Run

Run visual evidence collection when:

- the user asks for a full reading note and allows PDF/full-text access;
- the selected template is `layered-explainer`;
- the paper is model-heavy, figure-heavy, formula-heavy, or mechanism-heavy;
- figures/tables are needed to explain the model, method, results, limitations, reproducibility, or user annotation questions.

Do not run visual evidence collection for simple metadata, BibTeX, citation, or collection-management tasks.

## Source Order

1. Verified MinerU `manifest.json` for figure/table labels, captions, pages, and image paths.
2. MinerU `images/` for existing extracted figure assets.
3. `full.md` and content lists for captions, nearby text, and figure/table context.
4. PDF skill or local PDF tools for high-resolution page rendering and crop generation when extracted images are missing, partial, or inadequate.
5. Direct PDF parsing only when cache is unavailable or insufficient and the user allows it.

## Figure/Panel Crop Decision Ladder

Use this crop-first ladder for visual evidence:

1. Prefer a verified MinerU figure image when it is complete, readable, and matches the intended figure/table label and caption.
2. If MinerU images are missing, fragmented, unexpectedly cropped, unreadable, or mismatched, render the relevant PDF page at high resolution.
3. From the high-resolution page render, crop the complete figure before considering page-level insertion.
4. When the note discusses specific subpanels, crop selected panels such as `fig5d` or `fig5f` after creating or verifying the full-figure crop.
5. Retain the full-page render as QA fallback or page evidence, but do not insert it into the final note by default.

Generating a rendered PDF page is an intermediate fallback step. It is not enough to claim visual evidence processing is complete unless the final note explicitly uses the full page because a crop would be misleading or incomplete.

## Selection Rules

Select figures/tables that directly support:

- model architecture;
- key mechanism;
- main results;
- important limitations;
- reproducibility-critical parameters;
- user annotation questions.

Avoid decorative, duplicate, unreadable, weakly relevant, or low-value images.

## Visual Evidence Layers

Use three layers:

| Layer | Purpose | Insert in final note |
|---|---|---|
| Main-note figure layer | Cropped full figures or high-value key panels used for reading flow | Yes, by default |
| Page evidence layer | Rendered full PDF pages preserving figure, caption, and nearby context | No, except when crop context is unsafe |
| Panel evidence layer | Cropped subpanels for complex multi-panel figures | Yes, when panels clarify mechanism or results |

For complex multi-panel figures, create a full figure crop first, then crop the important panels. Each retained panel should have its own inventory row.

Rendered full pages are reliable fallback evidence because they preserve context, but they are not ideal reading assets. Keep them under `pages/` or `qa/` unless the final note needs the whole page to avoid misleading cropping.

## Crop Acceptance Criteria

Accept a cropped figure or panel only when:

- figure or panel labels remain visible when those labels are used in the note;
- axes, legends, colorbars, scale bars, and critical annotations are retained;
- the crop is readable at the intended Typora display size;
- the crop does not include unrelated body text or partial captions unless the asset is intentionally classified as `figure+caption`;
- the crop supports a concrete discussion point in the note.

Do not create panel crops merely to make the note look more detailed. A panel crop should clarify a mechanism, result, limitation, parameter, or user annotation question. If a crop is too ambiguous, keep it as a QA candidate or use the full-page render as fallback/page evidence with a caution note.

## Asset Rules

Save selected images or rendered pages under:

```text
<paper-dir>/<note-filename-without-.md>.assets/
```

The asset directory is a Typora-style sibling directory named after the final Markdown note. For example, `paper-note_20260709-1907.md` uses `paper-note_20260709-1907.assets/`.

Use semantic kebab-case filenames with generic figure or panel labels, for example:

```text
fig1-model-framework.png
fig2-main-result.png
fig2-panel-b.png
fig3-method-comparison.png
supp-fig1-control-result.png
```

Default subdirectories for retained visual assets:

```text
<note-filename-without-.md>.assets/
├── fig1-model-framework.png
├── fig2-panel-b.png
├── pages/
│   └── fig2-page-render.png
├── qa/
│   └── fig2-crop-candidate.png
└── unused/
    └── fig2-rejected-panel-crop.png
```

Do not use Zotero storage paths, absolute paths, local file URLs, internal ZIP paths, or raw cache hash names in the final note.

## Typora Image Insertion

Insert images into the Markdown body with Typora-friendly HTML by default:

```html
<img src="./<note-filename-without-.md>.assets/fig1-short-label.png" alt="Fig. 1: short label" style="zoom:67%;" />
```

Rules:

- `src` must be a relative path beginning with `./<note-filename-without-.md>.assets/`.
- `alt` must include the figure/table label and a short label.
- `style` should use Typora-friendly `zoom:xx%;`.
- The displayed image should not exceed a CSS width of 1200px.
- Prefer generating or copying a derived image no wider than 1200px.
- If resizing is not available, use `zoom` and record actual width and zoom in `source-inventory.md` when known.

Use Markdown image syntax only as a fallback:

```markdown
![Fig. 1: short label](./<note-filename-without-.md>.assets/fig1-short-label.png)
```

## Visual QA

For each selected asset, verify:

- the file exists under the note-specific `<note-filename-without-.md>.assets/` directory;
- the image is nonblank;
- the content is readable enough for the note;
- the figure/table label matches the selected source;
- major panels are not accidentally cropped;
- panel labels are retained when panel-level interpretation depends on them;
- axes, legends, colorbars, scale bars, and critical annotations are retained;
- caption and image content are not mismatched.

If QA fails, try rendering the whole PDF page and keep that page under `pages/` or `qa/`. If still insufficient, include the figure/table in `source-inventory.md` as `needs caution` and explain the issue.

## Source Inventory Requirements

Record each visual source separately:

| Field | Meaning |
|---|---|
| asset path | relative path under the note-specific asset directory |
| evidence type | cropped PDF figure, cropped PDF panel, MinerU image, rendered page, QA fallback, unused candidate |
| insertion role | main note, panel detail, QA fallback, page evidence, unused |
| source locator | figure/table label, panel label, page, caption source, or crop notes |
| crop source | MinerU image, rendered PDF page, PDF text-block locator, or manual crop |
| source page | PDF page or source page when known |
| crop kind | figure-only, figure+caption, panel-only, page render, QA candidate, or unused crop |
| inserted/fallback role | inserted crop, inserted panel, page fallback, QA fallback, or unused |
| QA status | passed, needs caution, rejected, not inspected |
| fallback page asset | related full-page render under `pages/` when available |
| manual/automatic crop note | whether the crop box was manually selected, automatically derived, or unknown |
| reason | why this asset is inserted, kept only for QA, or excluded |

If a crop box is manually chosen, record that it was manual and state whether it is `figure-only`, `figure+caption`, or `panel-only`. Do not treat manually cropped assets as self-validating.

## Evidence Labels

Distinguish:

- caption evidence: caption text from `manifest.json`, `full.md`, or content lists;
- nearby-text evidence: paragraphs discussing the figure/table;
- image evidence: what was actually observed after opening the extracted image or rendered PDF page.

Use image evidence only after visual inspection. If the image was not inspected, write that the note is based on caption and nearby text only.
