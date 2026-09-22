# Template Index

Select one template after completing source inventory.

| Template | File | Use When | Tradeoff |
|---|---|---|---|
| research-standard | `references/templates/research-standard.md` | Default for most research papers | Structured and concise, less flexible |
| flexible-note | `references/templates/flexible-note.md` | Paper type is unusual or material is uneven | Adaptive, less standardized |
| layered-explainer | `references/templates/layered-explainer.md` | User wants a summary first and then detailed explanation | More readable for complex papers, longer |

## Default Selection

Recommend `research-standard` unless the inventory suggests another template.

## Routing Rules

- Use `research-standard` for standard empirical, modeling, computational, or materials papers.
- Use `flexible-note` when the paper is a perspective, review, dataset paper, tool paper, protocol, or when Zotero materials are sparse.
- Use `layered-explainer` when the paper is technically dense, figure-heavy, formula-heavy, or intended for teaching/reading group use.

Always ask the user to confirm the recommended template unless the user already specified one.
