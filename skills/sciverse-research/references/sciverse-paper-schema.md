# Sciverse Paper Schema BETA

Recorded: 2026-07-23 from the official Sciverse Skills and `paper-schema` documentation.

Official pages:

- https://sciverse.space/docs/sciverse/skills
- https://sciverse.space/docs/sciverse/skills/paper-schema
- https://sciverse.space/docs/sciverse/api/paper-schema
- Official source repository: https://github.com/opendatalab/Sciverse-Agent-Tools

## What it is

Paper Schema pre-parses eligible papers into structured `Paper`, `Entity`, `Relation`, `Evidence`, and `Citation` objects, while retaining precise provenance back to source paragraphs. The official API page describes it as a BETA capability focused on more than one million currently parsed AI conference papers.

It is suitable for:

- structured reading of a known paper;
- searching Problems, Components, Findings, Measures, Resources, and References;
- retrieving internal Entity-to-Entity relations;
- inspecting formulas, tables, results, comparisons, resources, and citation semantics;
- resolving evidence back to a paragraph or marker;
- building a bounded citation graph or research-material package.

It is not a replacement for:

- `meta-search` for full bibliographic coverage, author/journal statistics, or broad metadata filtering;
- `agentic-search` for open-ended full-text semantic recall;
- complete citation counts or an exhaustive global citation graph.

## Official loading and access paths

The general Sciverse Skills page currently describes these integration paths:

- `npx skills add https://sciverse.space` for environments supporting the Skills CLI;
- OpenClaw / ClawHub;
- Claude Plugin;
- manual Skill installation from the official repository;
- Python / TypeScript SDK;
- MCP through `sciverse-mcp-server`.

The standalone Paper Schema Skill page lists a separate Paper Schema Skill with 9 intent-oriented tools wrapping 18 REST operations. It documents Node.js 18+ and the `SCIVERSE_API_TOKEN` environment variable. Its example installation command is OpenClaw-specific:

```text
openclaw skills install @sciverse/paper-schema
```

Do not treat that OpenClaw command as a Codex installation command. Inspect the current host's available MCP tools and Paper Schema entitlement; installing this Skill does not expose additional service tools.

## 9 official intent tools

| Intent tool | Purpose |
|---|---|
| `paper_schema_capabilities` | Read the public contract, Entity taxonomy, Evidence groups, Relation types, and limits. |
| `search_paper_schemas` | Search schema-extracted papers by academic terms and metadata. |
| `discover_related_papers` | Expand from Entity semantics or a known seed paper. |
| `query_paper_entities` | Search across papers or list/read Entity objects in one paper. |
| `query_paper_relations` | Query internal Entity-to-Entity relations within a paper. |
| `query_paper_citations` | Read citation summary, full citation lists, or a navigable citation graph. |
| `query_paper_evidence` | Search or read formulas, tables, results, resources, comparisons, and citation semantics. |
| `resolve_paper_context` | Resolve provenance to source paragraphs, search within one paper, or hydrate context in batches. |
| `build_paper_materials` | Build bounded `overview`, `survey`, `benchmark`, `method`, or `reproduction` material packages. |

## REST operation groups

The official API exposes 18 operations below the `https://api.sciverse.space/paper-schema` prefix:

### Capability

- `GET /paper-schema`

### Paper discovery

- `POST /paper-schema/search`
- `POST /paper-schema/entities/related-papers`
- `POST /paper-schema/schemas/{schema_id}/related-papers`

### Entity

- `POST /paper-schema/entities/search`
- `GET /paper-schema/schemas/{schema_id}/entities`
- `GET /paper-schema/schemas/{schema_id}/entities/{entity_id}`

### Internal relations

- `POST /paper-schema/relations/search`
- `GET /paper-schema/schemas/{schema_id}/relations/{relation_id}`

### External citations

- `GET /paper-schema/schemas/{schema_id}/citation-summary`
- `GET /paper-schema/schemas/{schema_id}/citations`
- `GET /paper-schema/schemas/{schema_id}/citation-graph`

### Evidence and content

- `POST /paper-schema/evidence/search`
- `GET /paper-schema/schemas/{schema_id}/evidence/{evidence_id}`
- `POST /paper-schema/resolve-provenance`
- `POST /paper-schema/search-in-schema`
- `POST /paper-schema/hydrate-items`

### Research materials

- `POST /paper-schema/materials`

## Common response and provenance fields

Depending on the operation, preserve:

- `schema_id`: Paper Schema primary key;
- `entity_id`, `relation_id`, `evidence_id`: identifiers within the schema context;
- `items`, `nodes`, `edges`: returned structured objects or graph data;
- `next_cursor`: opaque pagination cursor; pass it back unchanged;
- `partial`: a dependency failed or degraded while usable results were returned;
- `truncated`: the query reached an operation, graph, or material-package limit;
- `warnings`: required explanation for partial or degraded output;
- provenance fields such as paragraph ID, marker, section, and source location.

Never infer that an unresolved citation is absent. The official API distinguishes complete reference/citation totals, resolved coverage, and resolved citation edges. An unresolved reference remains in the citation list but does not become a graph edge.

## Recommended decision rule

```text
Need a broad paper list or author/venue statistics?
  -> search_papers

Need open-ended semantic evidence across the wider corpus?
  -> semantic_search

Need structured objects inside an eligible parsed AI paper?
  -> Paper Schema Skill / paper-schema API

Need exact source verification after any structured or semantic result?
  -> read_content or Paper Schema provenance resolution
```

## Authentication and error handling

- Use `Authorization: Bearer <token>`.
- Keep `SCIVERSE_API_TOKEN` outside workspace files, URLs, request bodies, logs, and prompts.
- Preserve `X-Request-ID` when supplied or returned for troubleshooting.
- `401`: missing, invalid, disabled, or malformed token; do not retry blindly.
- `403`: valid token but Paper Schema or requested field is not enabled for the account.
- `404`: schema/entity/relation/evidence not found.
- `429`: quota or rate limit; honor `Retry-After` or `retry_after`.
- `400/422`: invalid or overly broad operation parameters; correct the request.
- `502/503/504`: bounded exponential retry is acceptable.
