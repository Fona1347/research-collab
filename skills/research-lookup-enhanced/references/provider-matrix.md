# Provider matrix

## Contents

- [Discovery and enrichment roles](#discovery-and-enrichment-roles)
- [Environment variables](#environment-variables)
- [Implemented endpoints](#implemented-endpoints)
- [Open-source and backend reuse audit](#open-source-and-backend-reuse-audit)
- [Rate and retry policy](#rate-and-retry-policy)
- [Field conflict policy](#field-conflict-policy)

## Discovery and enrichment roles

| Provider | Discovery | Details | Citations | References | OA/full text | Enrichment |
|---|---:|---:|---:|---:|---:|---:|
| OpenAlex (key-gated) | Keyword + optional semantic | Yes | Yes | Yes | OA locations | Topics, keywords, provider-local relevance |
| Semantic Scholar (key-gated) | Keyword + seed recommendations | Yes | Yes | Yes | `openAccessPdf` | Fields of study, recommendation order |
| Crossref | Yes | DOI | No | Deposited list | Licensed links only | Publisher metadata |
| Europe PMC | Yes | Yes | Yes | Yes | OA `fullTextXML` and links | No |
| Unpaywall | No | DOI | No | No | Legal OA resolver | No |
| Easy Scholar | No | No | No | No | No | Venue ranks/metrics only |

No single provider is authoritative for every field. Preserve provenance and
provider-specific metrics.

## Environment variables

| Variable | Required | Use |
|---|---:|---|
| `OPENALEX_API_KEY` | Required for OpenAlex | OpenAlex authentication |
| `OPENALEX_MAILTO` | Optional | Contact identification; never an authentication substitute |
| `SEMANTIC_SCHOLAR_API_KEY` | Required for Semantic Scholar | Semantic Scholar `x-api-key` |
| `S2_API_KEY` | Legacy alias | Accepted only when the primary variable is absent |
| `CROSSREF_MAILTO` | Recommended | Crossref polite identification |
| `UNPAYWALL_EMAIL` | Required for Unpaywall | Real contact email query parameter |
| `EASYSCHOLAR_SECRET_KEY` | Required for Easy Scholar | Venue-level enrichment |
| `EASYSCHOLAR_API_KEY` | Legacy alias | Accepted only when the primary variable is absent |

Do not put real values in repository files.

OpenAlex and Semantic Scholar report `not configured` and are skipped when their
primary API keys are absent. Status output never includes key values.

## Implemented endpoints

### OpenAlex

- `GET https://api.openalex.org/works?search=...`
- `GET https://api.openalex.org/works?search.semantic=...`
- `GET https://api.openalex.org/works/{id-or-doi}`
- `GET https://api.openalex.org/works?filter=cites:{openalex_id}`
- `GET https://api.openalex.org/works?filter=openalex_id:{id1|id2}`

Official documentation: <https://developers.openalex.org/api-reference/works>

Supported neutral filters map to `from_publication_date`,
`to_publication_date`, `type`, `is_oa`, `cited_by_count`, and OpenAlex Topic IDs.
Field names that are not Topic IDs remain ranking context rather than being
silently translated to an unreliable OpenAlex filter.

### Semantic Scholar

- `GET /graph/v1/paper/search`
- `GET /graph/v1/paper/{paper_id}`
- `POST /graph/v1/paper/batch` for up to 500 requested identifiers per batch
- `GET /graph/v1/paper/{paper_id}/citations`
- `GET /graph/v1/paper/{paper_id}/references`
- `POST /recommendations/v1/papers/` with positive and optional negative paper IDs

Official documentation: <https://api.semanticscholar.org/api-docs/>

Search filters map to `publicationDateOrYear`, `fieldsOfStudy`,
`publicationTypes`, `openAccessPdf`, and `minCitationCount`. The multi-paper
Recommendations endpoint requires an API key in the documented tutorial. Its
response is ordered by relevance but has no numeric relevance field, so the
adapter stores `recommendation_rank` and does not invent a provider score.

### Crossref

- `GET https://api.crossref.org/works`
- `GET https://api.crossref.org/works/{doi}`

Official documentation: <https://www.crossref.org/documentation/retrieve-metadata/rest-api/>

### Europe PMC

- `GET https://www.ebi.ac.uk/europepmc/webservices/rest/search`
- `GET /{source}/{id}/citations`
- `GET /{source}/{id}/references`
- `GET /{pmcid}/fullTextXML`

Official documentation: <https://europepmc.org/RestfulWebService>

### Unpaywall

- `GET https://api.unpaywall.org/v2/{doi}?email=...`

Use DOI lookup, not its search endpoint. Official documentation:
<https://data.unpaywall.org/products/api>

### Easy Scholar

- `GET https://www.easyscholar.cc/open/getPublicationRank`
- Query parameters: `secretKey`, `publicationName`

Treat the response as venue-level enrichment. Keep the raw `officialRank.select`,
`officialRank.all`, and `customRank` groups separated. The public overview is at
<https://www.easyscholar.cc/blogs/10007>.

## Open-source and backend reuse audit

Audit date: 2026-07-30. No repository below is vendored.

### Metadata clients

| Candidate | Current state and license | Runtime/dependencies | Fit and decision |
|---|---|---|---|
| [PyAlex](https://github.com/J535D165/pyalex) | 0.21 released 2026-02-23; MIT; Python >=3.8 | `requests`, `urllib3`; CPU-only; no model; OpenAlex key needed at scale | It exposes filters, paging, abstract reconstruction, and `Works().similar()`. The project already implements the required Work operations, normalization, cache, pacing, retries, redaction, and provenance. Replacing the client would duplicate code and risk bypassing those controls; not added. The missing semantic endpoint and filters are implemented as a thin extension of the existing adapter. |
| [semanticscholar](https://github.com/danielnsilva/semanticscholar) | 0.12.0 released 2026-03-29; MIT; Python >=3.10 | `httpx`, `tenacity`; CPU-only; no model | It provides typed sync/async paging and covers Graph, Recommendations, and Datasets APIs. The current client already has batch detail, cache, pacing, retries, key redaction, and `PaperRecord` mapping. Adding the SDK would create a second HTTP/retry stack without closing a current gap; not added. The Recommendations endpoint is added directly through the existing client. |

Both clients can be mocked offline, but neither natively produces this project's
`field_sources`, `field_conflicts`, `provenance`, or provider-separated metrics.
An adapter would still be required. Their permissive licenses do not by
themselves justify a new production dependency.

### Relevance backends

| Candidate | Current state and license | Compute/model/key | Fit and decision |
|---|---|---|---|
| [SPECTER2](https://github.com/allenai/SPECTER2) | Apache-2.0; repository has 52 commits; public model files last updated 2024-12; repository package declares Python >=3.8,<3.11 | Base weights about 440 MB plus adapters; PyTorch, Transformers, Adapters and many transitive packages; CPU inference is possible but slower and needs RAM above the model size; GPU is optional | Scientifically appropriate for query/paper embeddings, but the repository package's Python ceiling conflicts with this Python 3.11+ project and its pinned stack is a material supply-chain/compatibility cost. Added only as a lazy adapter. It imports nothing and downloads nothing in the default path; `--allow-model-download` is explicit. Scores are normalized within the backend and remain one low-weight component. |
| [ASReview](https://github.com/asreview/asreview) | 3.0.5 released 2026-04-20; Apache-2.0; Python >=3.10 | CPU-friendly TF-IDF/scikit-learn defaults; no large model required; sizable NumPy/Pandas/scikit-learn/Flask/SQL dependency and web UI surface | Strong fit only after repeated human relevant/irrelevant labels exist. It is not a general one-shot query ranker and cannot preserve the current pipeline controls without a project/session adapter. Not added to the default workflow. Reconsider an optional mode only when interactive screening state and export/import semantics are in scope. |
| [OpenAlex semantic search](https://developers.openalex.org/guides/searching) | Hosted official API; OpenAlex data is CC0, API use follows current service terms | No local model/GPU; API key and credits for normal use; cannot run live offline | Closes the long-query semantic discovery gap with the smallest adapter. Adopted as `--semantic-search`. Raw `relevance_score` and search mode stay under `metrics_by_provider.openalex`; mocked tests cover mapping and fallback. OpenAlex says keyword relevance also includes citation count, so the provider score is never used as the whole project score. |
| [Semantic Scholar Recommendations](https://api.semanticscholar.org/api-docs/recommendations) | Hosted official API under the Semantic Scholar API license | No local model/GPU; multi-seed tutorial requires an API key; live service unavailable offline | Closes the positive/negative seed-paper gap. Adopted as a thin POST adapter using the existing cached, rate-limited client. The response order is retained as raw rank, normalized only within Semantic Scholar, and combined as `seed_graph_proximity`. |

### Existing providers

- **OpenAlex** already supplies broad discovery, stable IDs, topics, citation
  graph, OA locations, retraction flags, and provider-specific citations. Added
  structured filters, topic/keyword mapping, arXiv ID retention, and optional
  semantic search; no SDK was needed.
- **Semantic Scholar** already supplies search, details, batch lookup, citation
  context, references, OA PDF, and provider-specific metrics. Added field mapping,
  OpenAlex ID retention, filters, and seed recommendations; no SDK was needed.
- **Crossref** remains the publisher/DOI metadata source. Date/type filters were
  extended, but it is not treated as a semantic or recommendation backend.
- **Europe PMC** remains the biomedical metadata/JATS source. Date and OA filters
  use its query language; it is not treated as a cross-field relevance oracle.
- **Unpaywall** remains DOI-only OA resolution after merge and is never a discovery
  or ranking provider.
- **Easy Scholar** remains post-merge venue enrichment and is excluded from paper
  relevance scoring.

All hosted backends are tested with mocks only. Live API behavior, quotas, account
entitlements, and SPECTER2 model compatibility remain explicitly unverified.

## Rate and retry policy

- Serialize all Semantic Scholar requests across client instances in the same
  process and keep request starts at least 1.2 seconds apart.
- Pace Europe PMC at one request per second by default.
- Deduplicate Easy Scholar lookups by normalized venue, execute them serially at
  least one second apart, and do not persist their responses.
- Send Crossref contact identification when configured.
- Retry HTTP 429 and 5xx with bounded exponential backoff and jitter.
- Cache successful GET responses by a SHA-256 request key.
- Cache the idempotent Semantic Scholar batch-detail POST by URL plus request-body hash.
- Cache the idempotent Semantic Scholar Recommendations POST by URL plus request-body hash.
- Do not persist Easy Scholar responses until its reuse and caching terms are confirmed.
- Redact key-like query parameters from provenance and error messages.
- Do not use multiple keys to bypass a provider's limits.
- Apply the shared global/provider request budget to routed discovery,
  Semantic Scholar recommendations, and citation/reference graph expansion.
  Unpaywall OA resolution and unique-venue enrichment remain separately bounded
  post-merge stages.

## Field conflict policy

- Prefer Crossref for deposited DOI/title/author/date/venue metadata.
- Prefer Europe PMC, then Semantic Scholar, for abstracts when available.
- Preserve citation/reference counts in `metrics_by_provider`; never imply they are
  directly interchangeable.
- Preserve OpenAlex relevance and Semantic Scholar recommendation rank under their
  provider metric groups. Normalize provider/backend signals independently before
  the project ranker combines them.
- Prefer Unpaywall for OA status, then Europe PMC, OpenAlex, and Semantic Scholar.
- Preserve every differing selected value in `field_conflicts` with provider names.
