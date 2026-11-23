# Query planning and source routing

## Contents

- [QueryPlan fields](#queryplan-fields)
- [Deterministic construction](#deterministic-construction)
- [Capability route](#capability-route)
- [Fallback stages](#fallback-stages)
- [Request budget and ledger](#request-budget-and-ledger)
- [Stability invariants](#stability-invariants)

## QueryPlan fields

`QueryPlan` records:

- `original_query`: exact user text, retained verbatim;
- `query_language` and `normalized_query`;
- stable `identifiers` such as DOI, PMID, PMCID, or arXiv ID;
- `core_concepts`, `method_terms`, `materials_or_objects`, `task_terms`, and
  `outcome_terms`;
- structured date, field, publication-type, OA, and citation filters;
- explicit retrieval `intents`;
- capped `query_variants` with source, language, intent, provider hints, and an
  original-preservation flag;
- `ranking_query_variant_id`, identifying the audited variant used for textual
  relevance ranking;
- `recommended_provider_route`;
- global and provider request limits;
- the selected research level, Profile defaults, explicit/inferred overrides, final
  run settings, and applied constraints;
- route confidence, fallback state/reasons, and construction provenance.

Use `--show-query-plan` to build this artifact without a network request.

## Deterministic construction

Normalize with Unicode NFKC, control-character removal, and whitespace compaction.
Detect English, Chinese, or mixed text by character classes. Extract identifiers
before concepts. Categorize terms with local auditable lexicons.

For Chinese queries, preserve the original and normalized Chinese variants. A small
local bilingual lexicon may add an English term expansion when it contains at least
two English content terms. A one-token match such as `materials` is too weak to
route as an English query and must not raise router confidence.

The caller may provide one `english_query` for a Chinese or mixed-language query
without a stable identifier. Normalize and validate it locally, require at least two
English content terms, cap it at 512 characters, and reject CJK-containing input.
When accepted, it takes priority over the local lexicon and becomes the
`english-term-expansion` variant. It is additive: the exact original query remains
available. Record accepted, rejected, ignored, or variant-cap-excluded status in
construction provenance. Invalid input degrades to the useful local expansion or
the original query instead of aborting the search.

The planner makes no LLM or translation-service request. A hosting Agent may create
the supplied English query after an offline plan reports confidence below `0.65`.
Translate scientific concepts rather than request language, and do not silently
introduce adjacent methods or hypotheses.

Use the accepted English variant for textual relevance ranking as well as English
provider retrieval. Otherwise English records retrieved from a translated query
would be ranked against Chinese character tokens.

Never generate more than six variants. Do not append the same fixed recent/review/
seminal/method/contradiction suffix set to every provider. Record those intents only
when detected or needed for evidence coverage, and let the router choose a
provider-suitable variant.

## Capability route

- OpenAlex: key-gated cross-disciplinary primary discovery and optional hosted
  semantic search.
- Crossref: bibliographic discovery, DOI lookup, and deposited metadata companion.
- Europe PMC: biomedical discovery, PMID/PMCID, citations/references, OA links, and
  JATS.
- Semantic Scholar: key-gated semantic metadata, batch details, citation/reference
  graph, and recommendations.
- Unpaywall: post-merge DOI-to-OA resolution only.
- Easy Scholar: post-merge unique-venue enrichment only.

The optional `EvidenceProvider` protocol can accept a Sciverse-style evidence
handoff. The router does not import or require Sciverse internals.

## Fallback stages

1. **Targeted route**: use the highest-confidence provider capability and a suitable
   variant. A stable identifier uses `get_paper` where available.
2. **General scholarly fallback**: use the raw original query for OpenAlex keyword
   recall, the checked English variant when available (otherwise a conservative
   normalized/concept query) for Crossref, and configured
   Semantic Scholar within budget.
3. **Coverage fallback**: when unique count, stable identifiers, primary-provider
   health, or router confidence remains insufficient, run one bounded expansion.
   Add Europe PMC for biomedical or sparse coverage and at most one unused OpenAlex
   expansion. Use Crossref with the raw original query if no provider completed that
   safety request.

Do not recurse, generate new variants during fallback, or retry a failed provider
indefinitely.

## Request budget and ledger

When no research level is supplied, use the `standard` Profile and the limits
below. `quick` and `deep` use the versioned settings in
[research-levels.md](research-levels.md). Profile settings are defaults; explicit
CLI or Python values override them before the existing hard caps are applied.

Default routed discovery/graph limits are:

| Scope | Limit |
|---|---:|
| Global | 12 |
| OpenAlex | 4 |
| Crossref | 3 |
| Semantic Scholar | 2 |
| Europe PMC | 3 |

Override them with `--request-budget` and repeatable
`--provider-budget PROVIDER=COUNT`. An exhausted request still consumes budget.
The same controller also gates Semantic Scholar recommendations and
citation/reference graph expansion after the initial routing stages. Post-merge
Unpaywall and Easy Scholar enrichment are separate bounded stages. Cache hits are
resolved inside the HTTP client before a network attempt.

For every decision or request, record:

- query variant ID, text, intent, route stage, and route reason;
- selected or skipped status and why;
- request budget before and after;
- search mode and result count;
- error/degradation and suppressed-provider reason;
- fallback trigger and coverage snapshot.

The diagnostic `search_batch()` companion returns records and per-page diagnostics;
`search()` keeps returning a list. A bad row is isolated and listed by index, stable
identifier and error type. Partial parsing does not suppress the whole provider.
Provider totals and `has_more` describe the executed response page; unknown values
stay null. Topic-search Crossref uses the checked English variant first; identifier
lookup and the bounded original-query safety route stay unchanged.

Add the same route stage, variant, operation, and fallback flag to each
`PaperRecord.retrieval_routes`.

Write `research-level-selection` before question decomposition. It records the
deterministic decision, Profile defaults, inferred and explicit overrides, final
settings, and clamps. Write `research-profile-outcome` before returning to separate
planned settings from requests, fallback stages, graph work, and extraction that
actually occurred.

## Stability invariants

- The exact original query always remains available.
- A supplied English query never replaces the original or identifier route.
- Invalid or weak English expansion falls back locally without a network-dependent
  translation step.
- Omitting a research level remains equivalent to the historical `standard`
  behavior, and each batch query receives an independent run configuration.
- A query-builder exception creates an emergency raw-query plan.
- One provider failure cannot terminate the whole search.
- Results from every route pass use the same merge, conflict, and rank logic.
- HTTP 429/5xx retries are finite, jittered, and `Retry-After` aware.
- Semantic Scholar requests are process-wide serialized and paced at least 1.2
  seconds apart.
- Multiple keys or processes must never be used to evade a provider limit.
- Research levels never authorize remote parsing or model downloads. Graph work
  still requires explicit seeds and uses only the routed budget left after discovery.
