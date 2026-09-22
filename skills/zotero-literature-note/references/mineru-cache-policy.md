# MinerU Cache Policy

Use this policy when a Zotero item may contain `[LLM for Zotero] MinerU cache` attachments.

## When to Check Cache

Check MinerU cache for paper-content tasks such as reading notes, summaries, figure/table explanation, formula extraction, method extraction, comparison, or RAG-style evidence work.

Do not read cache for simple bibliographic tasks such as finding an item, checking a DOI, listing collections, exporting BibTeX, or inserting a citation.

## Cache Identity

MinerU cache is expected to appear as a Zotero child ZIP attachment named like:

```text
[LLM for Zotero] MinerU cache <PDF_ATTACHMENT_KEY>.zip
```

Treat the cache attachment key and the source PDF attachment key as separate identifiers. The Zotero item key is the parent identifier.

## Discovery Order

1. Locate or confirm the Zotero item.
2. List children and identify PDF attachments.
3. Look for matching `[LLM for Zotero] MinerU cache` ZIP attachments under the same item.
4. Prefer a cache whose title contains the source PDF attachment key.
5. If multiple caches match the same PDF, prefer the latest generated or updated cache when that metadata is available.
6. If no safe choice exists, report the candidate cache attachments and ask the user to choose.

## Validation

Use cache content only after validating it against the Zotero item and PDF attachment.

Read the ZIP as read-only. Do not modify, rename, delete, or rewrite the attachment or cache ZIP. Do not extract it into the workspace unless the user explicitly asks for derived files.

Read these files in order when present:

1. `_llm_source.json`: confirm parent item key and source PDF attachment key.
2. `_llm_sync.json`: record addon/cache version, parsed time, and content hash when available.
3. `manifest.json`: inspect sections, pages, figures, tables, captions, and reading scope.
4. `full.md`: use as the main parsed paper text for normal reading-note drafting.
5. `content_list.json` or `*_content_list_v2.json`: use for precise blocks, locations, and RAG-style extraction.
6. `images/`: read only for figure/table tasks or visual verification.
7. `*_model.json`: avoid by default; use only for parsing-quality diagnosis.

If `_llm_source.json` shows a parent item or PDF attachment mismatch, do not use that cache.

## Source Inventory Fields

For each cache source, record:

| Field | Meaning |
|---|---|
| source id | cache attachment key or stable cache label |
| type | `[LLM for Zotero] MinerU cache ZIP` |
| Zotero item key | parent item key |
| PDF attachment key | source PDF attachment key |
| cache attachment key | Zotero key for the cache ZIP |
| cache status | verified, missing, mismatch, incomplete, unreadable, ambiguous |
| used files | manifest, full.md, content list, images, etc. |
| read scope | full paper, selected sections, figures, tables, or targeted blocks |
| evidence level | high when verified and content is complete; medium or low when partial |
| use decision | main draft, local enhancement, background only, excluded, needs caution |
| reason | why it is used or excluded |

## Fallbacks

- No cache: use Zotero metadata, notes, annotations, and available indexed text; ask before raw PDF parsing.
- Multiple caches: match by PDF attachment key; if still ambiguous, ask the user.
- Cache/PDF mismatch: exclude the cache and report the mismatch.
- Missing `full.md`: try content lists; if still incomplete, report the limitation.
- Missing `manifest.json`: `full.md` may still be used, but report that section/page/figure indexing is limited.
- Broken ZIP or inaccessible attachment: report the blocker and continue only with other verified sources.
- Missing images: answer from captions and text only, and state that image evidence was not checked.

## Privacy

Report Zotero item keys, PDF attachment keys, cache attachment keys, cache file names, and workspace output paths. Do not expose private local attachment paths or local file URLs in normal answers.
