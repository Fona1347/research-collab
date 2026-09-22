> Component manual. The collection's docs/maintenance.md supersedes the old standalone publish/validate scripts.

# Research Lookup Enhanced: Quickstart

<p align="center">
  <a href="QUICKSTART.md">English</a> |
  <a href="QUICKSTART.zh-CN.md">简体中文</a> |
  <a href="README.md">Technical README</a>
</p>

<!-- Keep this file synchronized with QUICKSTART.zh-CN.md. -->

This tutorial is for human users. Copy any `text` block directly into the Codex or
ChatGPT textbox. `$research-lookup-enhanced` explicitly selects the local Skill.
Unless a prompt asks for an evidence-packet directory, results can be returned in
the conversation.

## Contents

- [Start in 30 seconds](#start-in-30-seconds)
- [First use: check the Skill and providers](#first-use-check-the-skill-and-providers)
- [The shortest useful prompt structure](#the-shortest-useful-prompt-structure)
- [A. Discover and verify papers](#a-discover-and-verify-papers)
- [B. Constrain scope and improve coverage](#b-constrain-scope-and-improve-coverage)
- [C. Full text, evidence, and writing artifacts](#c-full-text-evidence-and-writing-artifacts)
- [D. Citation relations, recommendations, and SPECTER2](#d-citation-relations-recommendations-and-specter2)
- [E. Batch work and auditing](#e-batch-work-and-auditing)
- [Use the CLI directly](#use-the-cli-directly)
- [Read an evidence packet](#read-an-evidence-packet)
- [Boundaries](#boundaries)

## Start in 30 seconds

The shortest useful call is one sentence:

```text
Use $research-lookup-enhanced to research “CRISPR base editing for sickle cell disease.”
```

For an ordinary scientific question, the Agent selects `standard` when no level is
specified. To retain the complete trace and machine-readable output:

```text
Use $research-lookup-enhanced at standard depth to research “CRISPR base editing for sickle cell disease.” Create a traceable evidence packet in this project's artifacts/quickstart-scd directory.
```

You normally receive normalized references, provider provenance, coverage,
metadata conflicts, explained ranking, and a search ledger. Full text is processed
only when explicitly requested and all OA/safety gates pass.

## First use: check the Skill and providers

### 1. Check the local Skill

If the Skill is published in the workspace, test it without network access:

```text
Use $research-lookup-enhanced to briefly explain which scientific lookup tasks it should handle and which tasks should not trigger it. Do not make network requests.
```

The Skill is limited to scientific topics, research questions, paper/identifier
lookups, and scholarly evidence organization. News, shopping, general web, and code
search are outside its scope.

### 2. Check provider configuration

```text
Use $research-lookup-enhanced to check provider configuration. Report only configured or not configured, reveal no credentials, and do not search for papers.
```

Equivalent local command:

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  --show-provider-status
```

| Provider | Minimum configuration | Main role |
|---|---|---|
| Crossref | None | DOI and publisher metadata |
| Europe PMC | None | Biomedical papers, PMID/PMCID, JATS, citation relations |
| OpenAlex | `OPENALEX_API_KEY` | Cross-domain discovery, identifiers, citation relations |
| Semantic Scholar | `SEMANTIC_SCHOLAR_API_KEY` | Semantic metadata, citation relations, seed recommendations |
| Unpaywall | `UNPAYWALL_EMAIL` | Legal OA locations for DOI records |
| Easy Scholar | `EASYSCHOLAR_SECRET_KEY` | Optional venue metrics |
| MinerU | `MINERU_API_KEY` plus explicit remote consent | Confirmed-OA PDF parsing only |

The program reads process environment variables and does not automatically load
`.env`. `configured` means only that a variable is non-empty; it does not prove
that a key, quota, or account entitlement passed a live request. Never paste live
keys into prompts, command arguments, Markdown, or Git.

### 3. Create a source-development environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

`pip install -e .` installs development dependencies and distribution metadata; it
does not create a global CLI. Continue to invoke `research_lookup.py` by source
path. Install `.[html]` or `.[markitdown]` only when those local parser fallbacks
are needed.

### 4. Run one offline preflight

```text
Use $research-lookup-enhanced to run a preflight for “flexible ferroelectric devices for nonvolatile memory.” Check whether provider environment variables are configured, identify the current Python/virtual environment, inspect local HTML/MarkItDown/pypdf dependencies, report whether artifacts/preflight already exists or is non-empty, and build the query plan. Make no scholarly API request, reveal no credential, and create, delete, or overwrite no file.
```

This validates local readiness but cannot prove that keys, quotas, or remote account
entitlements work. A live health check must be requested separately and must still
respect every provider's pacing policy.

## The shortest useful prompt structure

Most requests fit this compact cross-shaped template:

```text
Use $research-lookup-enhanced at [quick / standard / deep] depth:
[scientific question, topic, or DOI/PMID/PMCID/arXiv identifier];
[date, field, publication type, OA, and result constraints];
[desired output: short list / citation neighborhood / evidence packet / excerpts];
[safety boundary: remote parsing or model download permission].
```

The minimal form remains:

```text
Use $research-lookup-enhanced to find papers about “your scientific question.”
```

### Choose a research level

| Level | Use it for | Natural phrasing | It does not automatically do |
|---|---|---|---|
| `quick` | Known papers and a small core set | “quickly,” “a few papers,” “verify this DOI” | Full text or Easy Scholar |
| `standard` | Ordinary scientific questions and multi-source retrieval | “research,” “find evidence” | Formal systematic review |
| `deep` | Broader coverage, more fallback, complex evidence work | “comprehensive search,” “deep research,” “trace citations” | Full text, PDF upload, seed choice, or model download |

The standalone CLI offers explicit `auto` rules. When using an Agent, state the
depth naturally; use `standard` when uncertain.

## A. Discover and verify papers

### A1. Find a small core set quickly

```text
Use $research-lookup-enhanced at quick depth to find the 10 most relevant core papers on “flexible pressure sensors for gait monitoring.” Keep DOI or PMID identifiers and briefly explain why each paper is relevant.
```

The reference target is a coverage goal, not a promise of exactly that many
outputs. Sparse providers are not padded with low-quality records.

### A2. Research an ordinary scientific question

```text
Use $research-lookup-enhanced at standard depth to research “how polarization vortices in two-dimensional ferroelectrics affect nonvolatile memory devices.” Search multiple providers, deduplicate records, explain ranking, and return traceable references.
```

To create files, add an explicit destination:

```text
Use $research-lookup-enhanced at standard depth to research “how polarization vortices in two-dimensional ferroelectrics affect nonvolatile memory devices.” Save the evidence packet to this project's artifacts/polar-vortex-memory directory.
```

### A3. Verify a DOI, PMID, PMCID, or arXiv paper

```text
Use $research-lookup-enhanced at quick depth to verify DOI:10.1038/s41586-020-2649-2. Reconcile title, authors, venue, publication date, stable identifiers, and OA status, preserving field conflicts between providers.
```

Shortest form:

```text
Use $research-lookup-enhanced to look up DOI:10.1038/s41586-020-2649-2.
```

Metadata found does not mean full text reviewed. Preserve verification states such
as `identifier-verified`, `abstract-verified`, and `full-text-extracted`.

### A4. Find only a legal OA location

```text
Use $research-lookup-enhanced to find a legal open-access version of DOI:10.1038/s41586-020-2649-2. State which provider supplied each OA location and do not use download sources that are not marked OA.
```

Unpaywall resolves DOI records to OA locations; it does not discover topics or rank
relevance.

## B. Constrain scope and improve coverage

### B1. Filter by date, field, publication type, and OA

```text
Use $research-lookup-enhanced at standard depth to find Biology papers published after 2022-01-01 about “single-cell spatial transcriptomics benchmarking.” Prefer original studies and reviews, request open-access filtering where each provider supports it, state which constraints are not global hard filters, and create a coverage report.
```

Filters map only to providers that support them. An unmappable field name remains
ranking context rather than being misrepresented as a provider-side filter.

### B2. Treat citation count as an auxiliary signal

```text
Use $research-lookup-enhanced to find papers on “solid-state battery interface stability” with at least 20 citations. Use citation counts only as a filter and low-weight ranking aid; do not call highly cited papers high-quality evidence.
```

Provider citation counts remain separate because they are not directly comparable.

### B3. Increase coverage with deep research

```text
Use $research-lookup-enhanced at deep depth to comprehensively search for evidence on “CRISPR base-editing off-target effects in hematopoietic stem cells.” Expand multi-provider coverage and bounded fallback, report uncovered questions and provider failures, and do not automatically parse full text or upload PDFs.
```

`deep` increases budgets and coverage limits. It does not grant full-text or remote
processing permission.

### B4. Look for supportive, opposing, and null findings

```text
Use $research-lookup-enhanced at deep depth to find supportive, opposing, null, and failed results for “transcranial alternating-current stimulation for working-memory improvement.” Distinguish source text, abstract evidence, and inference; do not call candidate patterns scientific consensus.
```

This can organize conflict signals, but it is not an automated systematic review,
risk-of-bias assessment, or final consensus decision.
## C. Full text, evidence, and writing artifacts

### C1. Process OA full text locally

```text
Use $research-lookup-enhanced at standard depth to research “benchmarking methods for single-cell spatial transcriptomics.” Parse only explicitly open-access full text; extract methods, key findings, limitations, and locator-bearing excerpts; use local parsers only and upload nothing to a remote service. Save the packet to this project's artifacts/spatial-benchmark-fulltext directory.
```

Full-text extraction needs a packet directory for source files, hashes, and parser
ledgers. HTML/JATS stay local. OA PDFs try installed MarkItDown and then the
low-structure-fidelity `pypdf` fallback.

### C2. Explicitly allow remote MinerU parsing

Copy this only if you accept an OA PDF being uploaded to a remote service:

```text
Use $research-lookup-enhanced to parse open-access full text about “flexible ferroelectric devices.” I explicitly allow PDFs already confirmed as open access to be uploaded to the MinerU remote parsing service. Record every parser attempt, output, and fallback reason, and save the packet to this project's artifacts/ferroelectric-mineru directory.
```

This consent maps to `--extract-fulltext --allow-remote-parser`. `deep`, `auto`, a
reason string, or merely configuring `MINERU_API_KEY` cannot replace upload consent.

### C3. Build a manuscript-oriented evidence packet

```text
Use $research-lookup-enhanced at standard depth to build a manuscript evidence packet for “flexible ferroelectric devices for nonvolatile memory.” Organize sources for Introduction, Methods rationale, and Discussion; emit BibTeX, an evidence matrix, coverage, and claim-source mappings; never present external literature as my experimental Results.
```

To audit evidence level sentence by sentence:

```text
Use $research-lookup-enhanced to research “your question” and label every candidate statement as full-text evidence, abstract evidence, metadata, or inference. Preserve a reference ID and locator for each statement.
```

The deterministic report organizes evidence; it does not infer consensus, causality,
or clinical recommendations.

## D. Citation relations, recommendations, and SPECTER2

### D0. Remember the directions

```text
forward citation: later paper -> cites -> seed paper
backward reference: seed paper -> cites -> earlier paper
```

`--citation-seed` currently attempts both directions on capable providers with
remaining budget. Each direction is a bounded, single-page, one-hop retrieval. It
does not guarantee all citations or recursively build a complete network. Do not
infer direction from the result envelope's top-level `citations` list; use each
record's citation/reference facet and the search ledger.

### D1. Retrieve a two-direction citation neighborhood

```text
Use $research-lookup-enhanced with DOI:10.1002/adma.202522292 as the seed. Retrieve forward citations and backward references, keep them in separate groups, preserve provider and citation/reference facets, and never label similarity recommendations as citation relations.
```

Graph expansion uses the routed budget left after discovery. When budget or a
provider is unavailable, inspect `search-ledger.json`; an empty source is not proof
that no citation exists globally.

### D2. Display only one direction

```text
Use $research-lookup-enhanced with DOI:10.1002/adma.202522292 as the seed. In the final answer, show only later papers that cite it—forward citations—and state retrieval date, providers, and non-detection limits.
```

```text
Use $research-lookup-enhanced with DOI:10.1002/adma.202522292 as the seed. In the final answer, show only papers cited by it—backward references—and group them by research topic.
```

The CLI has no citations-only or references-only switch. Even when the presentation
shows one group, `--citation-seed` may request both directions. This is output
filtering, not a reduction in provider calls.

### D3. Recommend similar papers from positive/negative seeds

```text
Use $research-lookup-enhanced to research “freestanding ferroelectric vortex devices,” with DOI:10.1002/adma.202522292 as a positive seed and DOI:10.1038/s41586-020-2649-2 as a negative seed. Keep Semantic Scholar recommendations separate from true citation relations and preserve provider order.
```

This requires configured Semantic Scholar. Provider recommendation order is not a
citation edge, and the runtime does not invent a native numerical score.

### D4. Rerank with an already-local SPECTER2 model

```text
Use $research-lookup-enhanced to search “your target topic,” then use an already-present local SPECTER2 model as an auxiliary semantic reranker. If the model or dependencies are missing, download nothing, record the backend error, and fall back to the default explainable ranker.
```

SPECTER2 is a low-weight ranking signal in the current implementation. It does not
automatically cluster papers, name topics, or build citation graphs. Permit
`--allow-model-download` only after accepting the model and dependency surface.

### D5. Draw a graph from verified relations

```text
Use $research-lookup-enhanced with DOI:10.1002/adma.202522292 as the seed, retrieve its citation neighborhood, and draw a Mermaid graph. Use solid arrows for verified citation/reference edges and dashed lines for Semantic Scholar recommendations or SPECTER2 similarity. Include a legend for forward citations, backward references, and semantic similarity, and never call manual groups vector clusters.
```

The Skill returns records and citation/reference facets, not a standalone edge-list
or rendered graph artifact. Layout and topic labels belong to a downstream
presentation step that must preserve relation type and source.

## E. Batch work and auditing

### E1. Preview the plan without network access

```text
Use $research-lookup-enhanced to build only a search plan for “flexible graphene sensors for Parkinsonian gait monitoring.” Make no scholarly API request. Show the original question, research level, query variants, provider route, filters, and budgets.
```

This maps to `--show-query-plan` and is useful before consuming external quota.

### E2. Process several scientific questions

```text
Use $research-lookup-enhanced to process these questions separately. Select a research level and budget independently for each, and create separate coverage results without carrying configuration from one query to the next:
1. Flexible pressure sensors for gait monitoring
2. CRISPR base-editing off-target effects
3. Single-cell spatial-transcriptomics benchmarking methods
```

Provider clients and caches may be shared; each batch query must still receive its
own `EffectiveRunConfig`.

### E3. Audit sparse results

```text
Use $research-lookup-enhanced to audit why this search is sparse. Check provider configuration, query variants, filters, global/provider budgets, stable-identifier coverage, fallback triggers, and the search ledger. Do not infer the cause from result count alone.
```

### E4. Audit parser fallback

```text
Use $research-lookup-enhanced to explain why this full-text run degraded. Read extraction-ledger.json and each parser-ledger.json, then list OA gates, remote consent, missing dependencies, parser errors, and the parser actually selected.
```

## Use the CLI directly

Run these commands from the project root.

### Help and configuration

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py --help

.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  --show-provider-status
```

### Offline plan preview

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "flexible graphene sensors for Parkinsonian gait monitoring" `
  --research-level standard `
  --show-query-plan
```

### Standard search and evidence packet

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "CRISPR base editing for sickle cell disease" `
  --research-level standard `
  --after-date 2020-01-01 `
  --packet-dir artifacts\sickle-cell `
  --json
```

### Explicit OA full text with local parsers

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "single-cell spatial transcriptomics benchmarking" `
  --open-access-only `
  --extract-fulltext `
  --packet-dir artifacts\spatial-fulltext
```

MinerU additionally requires explicit `--allow-remote-parser` and a configured
`MINERU_API_KEY`. Never add that option merely because the level is `deep`.

### Two-direction citation/reference expansion

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "ferroelectric vortex devices" `
  --citation-seed DOI:10.1002/adma.202522292 `
  --graph-limit 50 `
  --packet-dir artifacts\vortex-citation-neighborhood
```

This attempts both directions; it is not a forward-citation-only command.

### Semantic Scholar seed recommendations

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  "freestanding ferroelectric vortex devices" `
  --positive-seed DOI:10.1002/adma.202522292 `
  --negative-seed DOI:10.1038/s41586-020-2649-2 `
  --graph-limit 50 `
  --packet-dir artifacts\seed-recommendations
```

### Per-query auto rules in a batch

```powershell
.\.venv\Scripts\python.exe `
  .\skills\research-lookup-enhanced\scripts\research_lookup.py `
  --batch `
    "DOI:10.1038/s41586-020-2649-2" `
    "research flexible sensors for gait monitoring" `
    "comprehensively search CRISPR off-target evidence" `
  --research-level auto `
  --packet-dir artifacts\batch-demo
```

An Agent should normally pass a structured non-auto level. `auto` mainly serves the
standalone CLI.

## Read an evidence packet

Recommended order:

1. `coverage.json`: determine whether the target was met and which sources are absent.
2. `search-ledger.json`: inspect level, variants, routing, budgets, fallback, graph work, and errors.
3. `references.json`: inspect stable IDs, field sources/conflicts, and rank components.
4. `evidence-matrix.json`: verify excerpts, locators, source types, and states.
5. `packet.md`: read the human-oriented summary.
6. `references.bib`: import citation-ready metadata.
7. `extraction-ledger.json` / `parser-ledger.json`: audit OA and parser paths.
8. `research-report.md`: treat it as deterministic evidence organization, not an automatically validated scientific conclusion.

## Boundaries

- Do not use it for general web, news, shopping, or code search.
- Do not describe metadata-only or abstract-only records as full-text reviewed.
- Do not bypass paywalls; process only explicitly legal OA locations.
- Do not upload PDFs automatically; MinerU requires explicit consent each time.
- Do not infer paper quality from citation count.
- Do not render Semantic Scholar recommendations or SPECTER2 similarity as citation edges.
- Do not claim single-page citation expansion is a complete network or all citations.
- Do not call manual topical groups SPECTER2 clusters.
- Do not call deterministic candidate patterns scientific consensus.
- Use a dedicated systematic-review tool for formal PRISMA screening, exclusions, and risk of bias.

To study the implementation or prepare a PR, continue with [README.md](README.md).
