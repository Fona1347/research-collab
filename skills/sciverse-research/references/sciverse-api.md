# Sciverse API Reference

## Authentication

- Base URL: `https://api.sciverse.space`
- Token source: `https://sciverse.space/tokens`
- Header: `Authorization: Bearer <SCIVERSE_API_TOKEN>`
- Keep the token out of Git, Skill files, notes, logs, and shared prompts.

## Official Tool Mapping

The current Sciverse MCP package/session exposes six core capabilities. The general Skills page's tool overview currently lists five standard core Skill tools and does not list `list_paper_relations`; the local MCP surface still exposes and documents `list_paper_relations` because the API navigation includes `meta-paper-relations`. The official documentation now also lists the BETA Paper Schema API, which is a narrower structured-paper capability rather than a replacement for the core retrieval APIs.

| MCP/tool style | REST endpoint | Use |
|---|---|---|
| `list_catalog` | `GET /meta-catalog` | Discover fields, filter operators, sorting, and sample values. |
| `search_papers` | `POST /meta-search` | Structured metadata search over papers/authors/sources. |
| `semantic_search` | `POST /agentic-search` | Natural-language evidence chunk retrieval for RAG. |
| `read_content` | `GET /content` | Read source text by `doc_id`, `offset`, and `limit`. |
| `get_resource` | `GET /resource` | Fetch figure/table/image bytes by relative `file_name`. |
| `list_paper_relations` | `POST /meta-paper-relations` | Paginate citations, references, and related works by `unique_id`. |

Paper Schema BETA is documented separately at [`paper-schema`](https://sciverse.space/docs/sciverse/api/paper-schema). Its REST prefix is `https://api.sciverse.space/paper-schema`; it exposes 18 operations grouped into capability discovery, paper discovery, Entity, internal Relation, external Citation, Evidence/content, and research materials. The official Paper Schema Skill wraps these routes into 9 intent-oriented tools. See `sciverse-paper-schema.md` for the full route map and workspace status.

## Common REST Requests

### Evidence Retrieval

`POST /agentic-search`

Required: `query`

Useful optional fields: `top_k`, `sub_queries`, `filters`

Use for natural-language scientific questions and evidence chunks. Returned hits may include `chunk_id`, `chunk`, `doc_id`, `title`, `abstract`, `score`, `source_type`, `offset`, `page_no`, `lang`, `metadata_type`, `author`, `publication_venue_name_unified`, `publication_published_year`, and citation counts.

### Metadata Search

`POST /meta-search`

Useful fields: `collection`, `query`, `filters`, `sort`, `fields`, `page`, `page_size`, `cursor`, `freshness_boost`, `impact_boost`

Use for paper lists, DOI/title/year/journal filters, sortable bibliographies, and exports. This returns metadata, not full evidence passages. `doc_id` is for content reading; `unique_id` is for paper relations.

### Field Discovery

`GET /meta-catalog`

Useful query params: `collection=papers|authors|sources`, `include_sample_values=true|false`

Call this before constructing precise filters or UI/agent filter schemas. Do not treat sample values as complete enumerations.

### Full Text

`GET /content`

Required: `doc_id`

Optional: `offset`, `limit`

Use `offset` and `next_offset` to read long text in chunks. Treat returned text as source context for verification, not as a final conclusion by itself.

### Resources

`GET /resource`

Required: `file_name`

Only pass relative paths returned by Sciverse. Never pass a full URL, an absolute path, `..`, or backslashes.

### Paper Relations

`POST /meta-paper-relations`

Required: `unique_id`, `relation`

Relations: `CITATIONS`, `REFERENCES`, `RELATED_WORKS`

Use `unique_id`, not `doc_id`.

### Paper Schema BETA

Use Paper Schema only when the task is about structured reading of a schema-extracted paper: Entity, internal Relation, Evidence, citation graph, provenance resolution, or a bounded research-material package.

Key boundaries:

- It covers only papers with completed Schema extraction, currently described by the official page as more than one million AI conference papers.
- Use `search_papers` for full bibliographic coverage, author/venue statistics, and broad metadata filtering.
- Use `semantic_search` for open-ended semantic evidence recall across the wider corpus.
- `Relation` is an internal Entity-to-Entity relation within one paper; `Citation` is a paper-to-paper relation. Do not interchange them.
- Citation lists distinguish resolved and unresolved references. Unresolved references remain references but do not become graph edges.
- Preserve `schema_id`, `entity_id`, `relation_id`, `evidence_id`, provenance markers, `partial`, `truncated`, and `warnings`.

Common Paper Schema response fields include:

```text
schema_id
items / nodes / edges
next_cursor
partial
truncated
warnings
```

Paper Schema authentication uses the same Sciverse API Token. Preserve `X-Request-ID` when supplied or returned. Treat `401`, `403`, and `404` as non-retryable until the credential, permission, or identifier is corrected; honor `Retry-After` for `429`; use bounded retry for `502/503/504`.

### Official Skills loading paths

The current official Skills page describes these loading paths:

- `npx skills add https://sciverse.space` for environments supporting the Skills CLI;
- OpenClaw / ClawHub;
- Claude Plugin;
- manual Skill installation from the official repository;
- Python / TypeScript SDK;
- MCP through `sciverse-mcp-server`.

This collection maintains the workflow Skill. MCP registration and the availability of the 9 Paper Schema intent tools depend on the current host; inspect them before selecting a route.

## Error Handling

- Retry `500`, `502`, `503`, and `504` with exponential backoff.
- Do not blindly retry `400`, `401`, `403`, or `404`.
- For `429`, reduce rate and wait for the rate-limit window or daily quota reset.

## Environment Variable Placement

For this workspace, prefer a user-level environment variable or secret manager entry named `SCIVERSE_API_TOKEN`. Do not store the token in `.agents`, `AGENTS.md`, `~/.codex/config.toml`, committed `.env` files, or Skill references.

For future MCP configuration in Codex, prefer forwarding the variable by name:

Windows workspace target:

```toml
[mcp_servers.sciverse]
command = "powershell.exe"
args = ["-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "$env:SCIVERSE_API_TOKEN = [Environment]::GetEnvironmentVariable('SCIVERSE_API_TOKEN','User'); if ([string]::IsNullOrWhiteSpace($env:SCIVERSE_API_TOKEN)) { [Console]::Error.WriteLine('[sciverse-mcp] missing Windows User SCIVERSE_API_TOKEN'); exit 2 }; & npx.cmd -y sciverse-mcp-server"]
env_vars = ["SCIVERSE_API_TOKEN"]
startup_timeout_sec = 20
tool_timeout_sec = 60
```

Generic target when direct `npx` process spawning and inherited env vars are reliable:

```toml
[mcp_servers.sciverse]
command = "npx"
args = ["-y", "sciverse-mcp-server"]
env_vars = ["SCIVERSE_API_TOKEN"]
```

If a specific Codex version requires inline `env`, keep that config local and uncommitted; do not put the token in a workspace file.

## Verified Documentation URLs

Checked during setup:

- Sciverse docs overview: `https://sciverse.space/docs`
- Exact agentic-search API page: `https://sciverse.space/docs/sciverse/api/agentic-search#sciverse/overview`
- Sciverse Skills integration page: `https://sciverse.space/docs/sciverse/skills`
- Paper Schema BETA API page: `https://sciverse.space/docs/sciverse/api/paper-schema`
- Paper Schema Agent Skill page: `https://sciverse.space/docs/sciverse/skills/paper-schema`

The Skills and Paper Schema pages were rechecked on 2026-07-23. The pages now describe multiple Skill loading paths, a standalone Paper Schema Skill with 9 intent tools, and 18 Paper Schema REST operations. See `sciverse-paper-schema.md` for the synchronized local reference.

Confirmed from the exact `agentic-search` page:

- Method and path: `POST /agentic-search`.
- Purpose: natural-language search that returns citable literature passages for LLM Agent and RAG workflows.
- Use cases: RAG evidence, Agent tool calls, and source-grounded QA.
- Request body includes `query`, `top_k`, `sub_queries`, and `filters`.
- `query` is required and documented with a maximum of 4096 characters.
- `top_k` defaults to 10 and supports 1-100.
- `sub_queries` defaults to 0 and supports 0-4.
- Returned hits include evidence text plus provenance fields such as `chunk_id`, `doc_id`, `title`, `abstract`, `score`, `offset`, `page_no`, language, venue, publication year, and citation counts.
- The page explicitly says `agentic-search` does not generate final reviews or answers; the upper-layer Agent/RAG app is responsible for synthesis.
- To expand evidence context, call `content` with `doc_id` and `offset`.
- Returned chunks can be used as citation leads, but final answers should preserve `doc_id`, `doi`, `chunk_id`, `offset`, or page information.
