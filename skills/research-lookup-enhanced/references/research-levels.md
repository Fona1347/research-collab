# Research levels

Use research levels only after the request has already been identified as a
scientific topic, research question, paper lookup, or scholarly evidence task.
The resolver chooses the depth of a valid research lookup; it is not a generic
web-query classifier.

## Profiles

| Setting | quick | standard | deep |
|---|---:|---:|---:|
| Target references | 12 | 60 | 100 |
| Results per provider request | 5 | 10 | 20 |
| Routed discovery/graph budget | 6 | 12 | 24 |
| OpenAlex budget | 2 | 4 | 8 |
| Crossref budget | 2 | 3 | 6 |
| Semantic Scholar budget | 1 | 2 | 4 |
| Europe PMC budget | 2 | 3 | 6 |
| Fallback threshold | 5 | 12 | 24 |
| Stable-identifier threshold | 0.5 | 0.5 | 0.65 |
| Query variants | 3 | 6 | 6 |
| Resolve OA locations | yes | yes | yes |
| Easy Scholar enrichment | no | yes | yes |
| Full-text record limit, when enabled | 5 | 20 | 40 |
| Seed graph result limit | 20 | 50 | 100 |

`standard` reproduces the pre-profile defaults. `target_references` is a
coverage target, not a hard output limit. The routed request budget covers
discovery, Semantic Scholar recommendations, and citation/reference expansion;
Unpaywall and Easy Scholar remain post-merge stages.

## Selection and overrides

The level precedence is:

```text
explicit user level
> structured Agent selection
> deterministic local auto rules
> standard default
```

The settings precedence is:

```text
profile defaults
→ high-confidence auto intent
→ explicit CLI or Python overrides
→ hard limits and safety gates
```

Omitting `--research-level` selects `standard`. Use `--research-level auto`
only when the standalone CLI should apply local rules. A non-auto level passed
directly on the CLI is recorded as `explicit-cli`; an Agent may additionally
pass `--research-level-source explicit-user-intent|agent-inference` and an audit
reason.

An explicit concrete value always overrides its Profile value, including when
it happens to equal the old default. Repeatable `--provider-budget` values
override only the named providers. `--no-extract-fulltext` always wins over an
inferred full-text intent.

## Conservative auto behavior

Auto selects `quick` for an explicit request to quickly find a few papers or
for a simple DOI, PMID, PMCID, or arXiv lookup. It selects `deep` only for
high-confidence operations such as comprehensive searching, deep research,
reading and comparing full text, tracing a citation network, or comparing
conflicting evidence. Ambiguous or ordinary research questions use `standard`.

Quick and deep signals together fall back to `standard` with an ambiguity
reason. Negated actions are suppressed. Bare subject terms are insufficient:
`deep learning`, `full-text classification`, and `review classification` are
ordinary topics unless the request also contains an explicit research action.

Auto records stable reason and matched-signal codes. Free-form reason text is
for audit only and never controls execution.

## Full text and graph boundaries

No Profile enables full-text extraction by itself. Deep only raises the record
limit used after the user or Agent explicitly requests full text. A
high-confidence full-text action detected in `auto` may enable local legal-OA
extraction, and actual execution then requires a packet directory.

Research level never enables MinerU remote upload or model download. Remote PDF
parsing still requires explicit `--extract-fulltext --allow-remote-parser`, a
configured key, and an explicitly OA location.

There is no graph-enable boolean. Citation expansion requires
`--citation-seed`; recommendations require at least one `--positive-seed`.
Both use the routed budget remaining after discovery. If no budget remains, the
operation is skipped and the ledger records `request-budget-exhausted`.
