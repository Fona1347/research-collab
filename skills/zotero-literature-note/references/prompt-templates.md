# Prompt Templates

These prompts are user-facing examples. Replace placeholders before use.

## Generate a Literature Note

```text
Use $zotero-literature-note with Zotero item "{paper title}".
Output to "{output root}".
Ask me for target length, writing style, and template after you inventory Zotero materials.
```

## Inventory Child Notes Only

```text
Use $zotero-literature-note to inspect Zotero item "{paper title}".
Do not draft yet. First inventory child notes, Markdown notes, annotations, attachments, [LLM for Zotero] MinerU cache, and available full text, then classify each source by use value.
```

## Enrich an Existing Note

```text
Use $zotero-literature-note to enrich the current note for Zotero item "{paper title}".
Reread the current Markdown first, then use Zotero child notes and annotations to add high-value details without repeating existing content.
```

## Add Formulas, Figures, or Model Comparison

```text
Use $zotero-literature-note to add model comparison, key formulas, and figure interpretation to the existing reading note for "{paper title}".
Distinguish paper facts, author claims, interpretation, and caution.
```

## Explain Annotation Questions

```text
Use $zotero-literature-note to review annotation questions for "{paper title}".
Explain which questions the paper answers, which remain uncertain, and which should become follow-up reading items.
```

## Continue After Manual Edits

```text
I have manually edited the note.
Use $zotero-literature-note to reread the current Markdown first, treat it as canonical, and ask whether to locally modify it, create a timestamped version, or only suggest edits.
```

## Request Web Fallback

```text
If Zotero materials are insufficient, stop and tell me what is missing.
Ask before using web search to check DOI, publisher metadata, related papers, or open full text.
```

## Zotero and MinerU Cache Inventory

```text
Use $zotero-literature-note for a Zotero + MinerU cache inventory.

Target paper DOI:
<doi>

Output root:
<output-root>

You may access Zotero through the Zotero plugin.
Do not write to or modify the Zotero library.
Do not use web search.
Do not parse the raw PDF unless I explicitly allow it later.
Do not expose private attachment paths or local file URLs.

First locate the Zotero item by DOI, then inventory metadata, BibTeX, children, Markdown notes, annotations, PDF attachments, and matching [LLM for Zotero] MinerU cache ZIPs.

If a cache is found, verify it against the parent item and PDF attachment key. Report the item key, PDF attachment key, cache attachment key, cache status, used files you would read, and what would be written to source-inventory.md. Pause before drafting.
```
