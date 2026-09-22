# Output and Versioning

Use these rules when saving generated notes and inventories.

## Output Root

The default user-provided path is an output root directory, not a final file path.

Default layout:

```text
<output-root>/
└── <normalized-paper-short-title>/
    ├── <short-title>_文献阅读笔记_YYYYMMDD-HHMM.md
    ├── <short-title>_文献阅读笔记_YYYYMMDD-HHMM.assets/
    ├── source-inventory.md
    └── README.md
```

If the user provides a final `.md` file path, confirm whether to skip the default paper subdirectory rule.

## Paper Directory

Create a normalized paper directory from the Zotero title.

Rules:

- Prefer readable ASCII plus established abbreviations when available.
- Remove filesystem-unsafe characters.
- Keep the directory stable across versions of the same paper.
- Do not include private Zotero storage paths.

## Note Filename

Use local time.

```text
<short-title>_文献阅读笔记_YYYYMMDD-HHMM.md
```

## Existing Files

Never overwrite an existing note by default.

If the target file or paper directory exists:

1. Read existing note files and README if present.
2. Summarize what exists.
3. Ask whether to locally update a current file, create a new timestamped version, or only provide suggestions.
4. If the user does not explicitly choose overwrite or local update, create a new timestamped version.

## README.md

Every paper directory should contain a lightweight `README.md`.

Use this table:

| version file | generated time | trigger | template | main changes | difference from previous version |
|---|---|---|---|---|---|

Add short version-detail subsections only when needed.

## source-inventory.md

`source-inventory.md` is a fixed file in the paper directory.

Update it for the current generation state rather than creating timestamped copies.

Do not insert the full inventory into the final note body.

## Visual Assets

When figures, tables, extracted images, or rendered PDF pages are included, save them under:

```text
<paper-dir>/<note-filename-without-.md>.assets/
```

Rules:

- Put visual assets in the same parent directory as the final Markdown note, under a Typora-style sibling directory named after the final Markdown file.
- Example: `<short-title>_文献阅读笔记_YYYYMMDD-HHMM.md` uses `<short-title>_文献阅读笔记_YYYYMMDD-HHMM.assets/`.
- Keep cropped figures and inserted panel images at the asset root.
- Store rendered full pages under `pages/` when they are retained as page evidence.
- Store QA candidates under `qa/` and rejected-but-retained crops under `unused/`.
- Do not insert rendered full pages into the final note by default; insert them only when crop context would be unsafe or a crop failed and the fallback is clearly labeled.
- Keep full-page fallback assets available for QA and traceability even when they are not inserted into the final note.
- Insert images in the final note with relative paths only.
- Prefer semantic kebab-case filenames such as `fig1-model-framework.png`.
- Do not link to Zotero storage paths, absolute local paths, local file URLs, internal cache ZIP paths, or raw cache hash names.
- Do not overwrite existing assets unless regenerating the same note version intentionally.
- Prefer derived images no wider than 1200px.
- If resizing is not available, use Typora `zoom` in the inserted image tag and record the actual width and zoom when known.

Use Typora-friendly HTML by default:

```html
<img src="./<note-filename-without-.md>.assets/fig1-short-label.png" alt="Fig. 1: short label" style="zoom:67%;" />
```

Use standard Markdown only as a fallback:

```markdown
![Fig. 1: short label](./<note-filename-without-.md>.assets/fig1-short-label.png)
```
