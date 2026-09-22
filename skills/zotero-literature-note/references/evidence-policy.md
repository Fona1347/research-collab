# Evidence Policy

Use this policy to decide what can support the final note and how conflicts are handled.

## Evidence Priority

1. Verified paper full text, including a validated `[LLM for Zotero] MinerU cache` `full.md`.
2. Verified structured cache evidence such as `manifest.json`, content lists, figure/table captions, and targeted image checks.
3. User-authored annotations and Zotero Markdown notes.
4. Focused child notes such as model derivation, figure interpretation, methods, or parameter notes.
5. Compact summary notes and `[LLM for Zotero]` generated Markdown summaries.
6. Long Q&A notes, used only by targeted extraction.
7. Zotero metadata and BibTeX, used for bibliographic fields.
8. External web sources, only after user permission and only as fallback.

## Conflict Handling

- Prefer paper full text over metadata, notes, and external summaries.
- Prefer verified MinerU `full.md` or paper full text over unverified generated notes.
- If Zotero metadata conflicts with paper full text, use paper full text and note the discrepancy when relevant.
- If child notes conflict with paper full text, prefer paper full text.
- If user annotations raise unresolved concerns, preserve them as questions or cautions.
- If a MinerU cache does not match the Zotero item or PDF attachment, exclude it.
- If external sources conflict with Zotero/PDF evidence, mark them as external and lower priority.
- Do not silently reconcile conflicts.

## Required Distinctions

Distinguish these categories in the final note:

- paper facts,
- author claims,
- user or AI interpretation,
- inference,
- caution or limitation.

## Visual Evidence

For figures and tables, distinguish:

- caption evidence: caption text from `manifest.json`, `full.md`, or content lists;
- nearby-text evidence: paragraphs discussing the figure/table;
- image evidence: what was actually observed after opening the extracted image or rendered PDF page.

Use image evidence only after visual inspection. If a figure/table was not visually inspected, state that the note is based on caption and nearby text only.

Mark visual sources as `needs caution` when the image is cropped, blurry, incomplete, unreadable, mismatched with the caption, or produced by an uncertain fallback.

## Prohibitions

Do not invent:

- DOI,
- authors,
- journal,
- publication year,
- formulas,
- figures,
- datasets,
- results,
- claims,
- related works.

If evidence is insufficient, say so and ask for more material or permission to use fallback search.
