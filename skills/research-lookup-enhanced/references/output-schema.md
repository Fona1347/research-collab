# Output schema and artifacts

## Contents

- [Unified record](#unified-record)
- [Verification states](#verification-states)
- [Packet artifacts](#packet-artifacts)
- [Interpretation boundaries](#interpretation-boundaries)

## Unified record

Each merged paper contains bibliographic identifiers, metadata, OA locations,
provider provenance, evidence chunks, metrics, and conflict records. Important fields:

- `doi`, `pmid`, `pmcid`, `openalex_id`, `semantic_scholar_id`, `arxiv_id`
- `title`, `authors`, `publication_date`, `year`, `venue`, `abstract`
- `publication_types`, `fields_of_study`, `keywords`
- `fulltext_locations[]`: URL, kind, source, license, version, and OA status
- `evidence_chunks[]`: text, source type, locator, extraction method, and content hash
- `field_sources`: providers contributing each selected field
- `field_conflicts`: differing values with provider attribution
- `metrics_by_provider`: citation/reference counts without cross-provider collapse
- `journal_metrics.easy_scholar`: optional venue-level enrichment
- `ranking`: project rank, total score, preprint flag, and explained components
- `retrieval_routes[]`: query variant, provider, route stage/reason, operation, and
  fallback flag for every route contributing the record
- `provenance[]`: provider, request URL, cache artifact, operation, and retrieval time

Each ranking component contains a normalized `score`, a project `weight`, and a
short `reason`. Optional `details` retain raw provider/backend values and their
within-provider normalization. Required components are `title_match`,
`abstract_match`, `method_match`, `field_match`, and `year_fit`. Optional
components are `semantic_similarity`, `seed_graph_proximity`,
`evidence_availability`, and `normalized_citation_signal`. Missing metadata
produces a neutral or zero component with an explanation rather than an
exception.

The top-level result envelope also contains:

- `query_plan`: original/normalized query, language, concepts, filters, capped
  variants, provider route, request limits, fallback state/reasons, provenance,
  a `ranking_query_variant_id`, and a versioned `research_profile`
  decision/effective-settings snapshot
- `request_budget`: final global/provider routed-request usage
- `recommendations[]`: non-retracted ranked records with component explanations
- `ranking.backend_errors[]`: optional semantic backend failures that triggered fallback
- `ranking.excluded[]`: records excluded from recommendations, currently retractions

`query_plan.research_profile` contains `schema_version`, `decision`,
`profile_defaults`, `inferred_overrides`, `explicit_overrides`,
`effective_settings`, and `constraints_applied`. It is deterministic and contains
no runtime timestamps. The search ledger separately records
`research-level-selection` and `research-profile-outcome` so planned limits are not
confused with work actually performed.

For cross-language planning, `query_variants[].source` distinguishes
`caller-supplied-english-query` from `local-bilingual-lexicon-v1`.
`query_plan.provenance[].details` records `english_query_status`, any rejection
reason, whether the local expansion was useful, and whether external translation
was supplied. `planner_llm_call_used` remains false because the deterministic
planner never invokes a model. `ranking_query_variant_id` is `original` unless an
accepted English expansion survives the configured variant cap.

Preprints remain in `recommendations[]` with `preprint: true`. Retracted records
may remain in the auditable reference packet but never appear in recommendations
or claim support.

Schema 2 accepts unified `records`. `manuscript_packet.py` also maps the original
`sources=[...]` envelope for migration and retains `synthesis.consensus_evidence` as
an alias of `consensus_candidates`.

Packet references retain `source_publication_types` separately from the heuristic
`publication_type`. Explicit provider `peer-review` records are classified as
`peer-review-document`, not literature reviews; a packet warning requires host
screening before using an ordinary paper shortlist. Raw retrieval records remain.

## Verification states

| State | Meaning |
|---|---|
| `full-text-extracted` | Public/OA HTML, JATS, or PDF text was parsed locally |
| `page-extracted` | A public webpage was extracted, without claiming it is article full text |
| `abstract-verified` | Provider abstract is available, but no full text was parsed |
| `identifier-verified` | Stable DOI/PMID/provider identifier exists |
| `search-only` | Result lacks stronger verification |

Never describe metadata-only or abstract-only records as full-text reviewed.
Never compare raw relevance scores from different providers. Provider search
scores, recommendation ranks, and citation counts retain their raw source values
and are normalized within their own provider/backend before combination.

## Packet artifacts

| Artifact | Purpose |
|---|---|
| `packet.json` / `packet.md` | Complete machine/human packet |
| `references.json` / `references.bib` | Citation-ready records |
| `evidence-matrix.json` | Evidence, locators, quality labels, and conflicts |
| `claim-source-map.json` | Candidate statement to reference/excerpt mapping |
| `synthesis.json` | Candidate findings, conflict signals, patterns, and gaps |
| `section-briefs.json` | Introduction, methods-rationale, and discussion evidence |
| `coverage.json` | Target shortfall and source/evidence mix |
| `search-ledger.json` | Provider/facet request status and timestamps |
| `extraction-ledger.json` | OA download and local extraction attempts |
| `provenance.json` | Reference-level provenance records |
| `research-report.md` | Deterministic, citation-linked long report |
| `research-report-data.json` | Report inputs for optional external/local synthesizers |
| `fulltext/` | OA source files retained for local parsing/audit |

`search-ledger.json` request entries add `search_batch` with received, normalized,
discarded counts; provider-reported total; `has_more`; stop reason; and row errors.
`status=partial` means at least one row failed normalization, not a provider outage.
The list-based provider API remains available. Legacy adapters without raw diagnostics
return unknown received/discarded/total/page fields rather than fabricated counts.

`coverage.json` adds `retrieval_completeness`, `target_count_met`, and
`relevance_assessment.status=not-assessed`. `partial` completeness exposes failed
requests, budget stops, remaining pages or discarded rows; `bounded` only describes
the executed searches. Provider totals can overlap and must not be summed. Host
review of titles/abstracts is still required to decide whether the question is answered.

Local JATS/HTML extraction can emit section text, tables, figure/table captions, and
reference-list chunks. The extraction ledger retains the downloaded local path and
failure history; the evidence matrix retains source type, locator, method, URL, and
chunk hash.

PDF extraction additionally writes a per-document `parser-ledger.json` beneath the
parsed full-text directory. Every parser returns a `ParsedDocument` containing
text/Markdown, sections, tables, captions, references, source hash, parser
name/version, local output paths, warnings/errors, and ordered parser provenance.
The parser order is gated MinerU remote parsing, lazy local MarkItDown, then
low-structure-fidelity `pypdf`.

An optional external evidence handoff uses `EvidenceRecord` rather than importing
another Skill. It preserves DOI/PMID/PMCID when available, document/chunk IDs,
offset or page locator, direct evidence versus inference, and partial/truncated
warnings.

## Interpretation boundaries

The default report synthesizer is deterministic. It organizes source-derived text and
coverage signals but does not infer consensus, causality, recommendations, or the
user's Results. A future local LLM synthesizer must consume the same packet, retain
reference IDs, and label inference separately from evidence.
