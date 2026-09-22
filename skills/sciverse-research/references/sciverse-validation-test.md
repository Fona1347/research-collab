# Sciverse Validation Test

Portable validation guide. Prior host observations remain in the archived source project.

This document defines the workspace validation case for Sciverse REST API access and Codex MCP integration. Do not print, paste, store, or log the literal `SCIVERSE_API_TOKEN` value while running these checks.

## Preconditions

Inspect the current host's actual MCP configuration, exposed tools and credential
presence. Installation of this Skill establishes none of these prerequisites.
The commands below illustrate a Windows setup; adapt them to the host's approved
configuration. Run live checks only when the user's task requires them.

## TC-01 Credential Hygiene

Purpose: confirm credential storage is present without leaking the secret.

Commands:

```powershell
$proc = [Environment]::GetEnvironmentVariable('SCIVERSE_API_TOKEN','Process')
$user = [Environment]::GetEnvironmentVariable('SCIVERSE_API_TOKEN','User')
[pscustomobject]@{
  process_env_present = -not [string]::IsNullOrWhiteSpace($proc)
  user_env_present = -not [string]::IsNullOrWhiteSpace($user)
} | ConvertTo-Json -Compress
```

Expected result:

- `user_env_present` is `true`.
- `process_env_present` may be `false` if Codex or the terminal was started before the user environment variable was added.
- No command prints the actual token value.

Additional checks:

- Confirm `<user-home>/.codex/config.toml` contains `env_vars = ["SCIVERSE_API_TOKEN"]`.
- Confirm the config does not contain a literal Sciverse token.
- Confirm Skill references do not contain a literal Sciverse token.


## TC-02 REST Meta Search

Purpose: verify that the Sciverse token and API are usable independently of Codex MCP.

Request:

- Method: `POST`
- URL: `https://api.sciverse.space/meta-search`
- Query: `graphene battery cycle stability`
- Filter: `publication_published_year >= 2022`
- Fields: `title`, `doi`, `publication_published_year`, `publication_venue_name_unified`
- Page size: `3`

PowerShell smoke test:

```powershell
$token = [Environment]::GetEnvironmentVariable('SCIVERSE_API_TOKEN','User')
if ([string]::IsNullOrWhiteSpace($token)) {
  throw 'Missing Windows User-level SCIVERSE_API_TOKEN'
}

$headers = @{ Authorization = "Bearer $token" }
$body = @{
  query = 'graphene battery cycle stability'
  filters = @(@{
    field = 'publication_published_year'
    operator = 'FILTER_OP_GTE'
    value = 2022
  })
  fields = @(
    'title',
    'doi',
    'publication_published_year',
    'publication_venue_name_unified'
  )
  page = 1
  page_size = 3
} | ConvertTo-Json -Depth 8

$resp = Invoke-WebRequest `
  -Uri 'https://api.sciverse.space/meta-search' `
  -Method Post `
  -Headers $headers `
  -ContentType 'application/json' `
  -Body $body `
  -TimeoutSec 40

$json = $resp.Content | ConvertFrom-Json
$items = @()
if ($json.data) { $items = @($json.data) }
elseif ($json.results) { $items = @($json.results) }
elseif ($json.items) { $items = @($json.items) }

[pscustomobject]@{
  status_code = [int]$resp.StatusCode
  result_count = $items.Count
  sample = @($items | Select-Object -First 3 | ForEach-Object {
    [pscustomobject]@{
      title = $_.title
      year = $_.publication_published_year
      venue = $_.publication_venue_name_unified
      doi_present = -not [string]::IsNullOrWhiteSpace([string]$_.doi)
    }
  })
} | ConvertTo-Json -Depth 8 -Compress
```

Expected result:

- HTTP status is `200`.
- JSON parses successfully.
- `result_count >= 1`.
- Returned records include non-sensitive paper metadata such as title, year, venue, and DOI presence.


## TC-03 Codex MCP Config

Purpose: verify that Codex sees the Sciverse MCP server configuration.

Commands:

```powershell
codex mcp list
codex mcp get sciverse
```

Expected result:

- `sciverse` is listed.
- Status is `enabled`.
- Transport is `stdio`.
- For the illustrated Windows wrapper, command is `powershell.exe`.
- Args read the Windows User-level `SCIVERSE_API_TOKEN` and invoke `npx.cmd -y sciverse-mcp-server`.
- Env is shown as `SCIVERSE_API_TOKEN=*****`.
- Auth may show `Unsupported`; this is acceptable because Sciverse uses API-key environment forwarding rather than Codex OAuth login.


## TC-04 MCP Tool Availability

Purpose: verify that the current Codex session exposes Sciverse MCP tools.

Expected tools:

- `list_catalog`
- `search_papers`
- `semantic_search`
- `read_content`
- `get_resource`
- `list_paper_relations`

Manual validation prompts:

```text
Use sciverse list_catalog.
```

```text
Use sciverse search_papers to search graphene battery cycle stability, page size 3.
```

```text
Use sciverse semantic_search to search Transformer attention mechanism, top_k 3.
```

Pass criteria:

- At least `list_catalog` is callable.
- `search_papers` returns structured paper records for the test query.
- `semantic_search` returns evidence chunks with provenance fields when available.


## TC-05 Optional MCP Stdio Handshake

Purpose: verify the MCP server process can start and return its tool list.

Security requirement:

- Run this only after explicit user approval.
- This step executes the third-party npm package `sciverse-mcp-server`.
- This step injects the API key into that process.
- Do not run this as a workaround if approval is denied.

Expected result after approval:

- MCP `initialize` succeeds.
- MCP `tools/list` returns Sciverse tools including `list_catalog`, `search_papers`, `semantic_search`, `read_content`, and `get_resource`.

## Interpretation

- If TC-02 passes and TC-03 passes, the token and Codex configuration are usable at their own layers.
- If TC-04 fails, the likely issue is session/tool loading rather than Sciverse API authentication.
- If TC-04 passes, Codex can use Sciverse MCP as the live retrieval layer for the `sciverse-research` Skill.
- On Windows, prefer a PowerShell wrapper that reads the Windows User-level token at MCP startup and invokes `npx.cmd`; plain `npx` may not resolve correctly when spawned outside PowerShell, and inherited process env may be stale.
- Re-run TC-01 through TC-04 after token rotation, Codex config edits, Node/npm updates, `sciverse-mcp-server` updates, or opening Sciverse use in a new Codex surface.

## TC-06 Official Skills and Paper Schema Capability

Purpose: distinguish the general Sciverse Skill/MCP integration from the newer BETA Paper Schema capability.

Official pages checked on 2026-07-23:

- `https://sciverse.space/docs/sciverse/skills`
- `https://sciverse.space/docs/sciverse/skills/paper-schema`
- `https://sciverse.space/docs/sciverse/api/paper-schema`

Observed documentation state:

- General Skills documentation lists `npx skills add https://sciverse.space`, OpenClaw/ClawHub, Claude Plugin, manual Skill, Python/TypeScript SDK, and MCP loading paths.
- The general page describes five standard core Skill tools: `list_catalog`, `search_papers`, `semantic_search`, `read_content`, and `get_resource`.
- The Paper Schema page describes a separate BETA Skill with 9 intent tools wrapping 18 REST operations.
- Paper Schema is limited to papers with completed Schema extraction and is not a replacement for `meta-search` or `agentic-search`.

Capability availability must be inspected on the current host. The Skill's
Paper Schema instructions do not install its API tools or establish entitlement.

Pass criteria when Paper Schema is intentionally enabled later:

- Capability discovery succeeds without exposing the API token.
- The client preserves `schema_id`, `entity_id`, `relation_id`, `evidence_id`, provenance, `partial`, `truncated`, and `warnings`.
- `403` is interpreted as missing capability/field permission, not automatically as an invalid token.
- Unresolved citations remain distinct from resolved citation-graph edges.
