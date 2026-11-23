# Artifact and Data Schemas

## File Set

Every run contains:

| File | Purpose |
|---|---|
| `00_intake.md` | Decision, constraints, capability passport, assumptions |
| `01_breadth-ledger.md` | Coverage accounting and anti-anchor gate |
| `02_search-log.md` | Reproducible queries, sources, selections, and misses |
| `03_evidence-matrix.md` | Claim-level evidence and provenance |
| `04_research-map.md` | Layered map and synthesis |
| `05_candidate-portfolio.md` | Candidate cards and risk-balanced selection |
| `06_red-team.md` | Counterarguments, baselines, confounds, kill tests |
| `07_decision-log.md` | Decisions, reversals, rejected routes, next actions |
| `map_report_<short_task_name>_<YYYY-MM-DD>.md` | User-facing synthesis with human-readable citations, callouts, recommendations, and evidence boundaries |
| `run-manifest.json` | Run metadata for validation and reuse |

The eight numbered Markdown files are auditable working artifacts. The dynamic `map_report` is the primary delivery surface for a human reader and must remain understandable without exposing internal document, chunk, or offset identifiers. A run is incomplete when only the working artifacts are populated.

Schema 1.2 manifests set `primary_artifact` to the dynamic `map_report` filename. Consumers should open or present that file by default and expose the numbered files as supporting audit material.

## Claim IDs

Use stable prefixes:

- `B-###`: bottleneck claim.
- `M-###`: mechanism claim.
- `S-###`: system or architecture claim.
- `C-###`: candidate claim.
- `E-###`: evidence record.
- `Q-###`: query.
- `D-###`: decision.

One atomic claim may cite several evidence records. One evidence record may support or contradict several claims.

## Evidence Matrix Columns

Required columns:

| Column | Meaning |
|---|---|
| Evidence ID | Stable `E-###` identifier |
| Claim ID | Atomic claim linked to this record |
| Support | `supports`, `contradicts`, `mixed`, or `context` |
| Directness | `direct`, `indirect`, or `background` |
| Core contribution | What the source demonstrated |
| What it supports | Exact bounded claim |
| Limitations | What remains unproven |
| Source | Title, authors, year, venue |
| DOI or URL | Stable identifier or link |
| Provenance | Database, document/chunk/page/location |
| Evidence depth | `metadata`, `passage`, or `full context` |
| Verification | `verified`, `partially verified`, or `unverified` |

Optional columns include sample size, device count, benchmark, material stack, process conditions, statistical strength, replication, and notes.

## Evidence Annotation

Use this human-readable block next to important claims:

> **E-### | Title (year), DOI or stable link**
> - Core contribution: ...
> - Supports: B-### or M-###, with a bounded statement.
> - Limits: ...
> - Provenance: source, document ID, chunk/page/location; verification state.

This is a blockquote-style annotation. Use quotation marks only for short text verified against the source.

## Human-Facing Report Schema

Follow `reader-report.md` as the authoritative synthesis and writing contract.

The reader report must include:

1. A one-page conclusion and low-, medium-, and high-risk recommendation table.
2. A plain-language explanation of the map's root categories and causal progression.
3. A workload-to-architecture-to-mechanism-to-material mapping.
4. Key source blocks using GitHub callouts and reader-facing numbered citations.
5. For each source block: core contribution, supported viewpoint, and boundary.
6. Three-month decisive experiments, one-year platform paths, strongest baselines, kill criteria, and reversal conditions.
7. A numbered reference list with DOI or stable links.

Detailed retrieval provenance belongs in `03_evidence-matrix.md`; the reader report should cite it by ordinary reference number rather than duplicating database internals.

## Candidate Card Schema

Each candidate must include:

1. Candidate ID and risk level.
2. Persistent bottleneck and state type.
3. Missing primitive and target state operation.
4. Scientific question.
5. Falsifiable hypothesis and causal chain.
6. Physical state variable, control, readout, timescale, and failure modes.
7. Material/process options and why they are options rather than assumptions.
8. Transferable laboratory modules and external dependencies.
9. Direct neighbors and bounded crowding classification.
10. Strongest baseline and full-system cost hypothesis.
11. Three-month minimal decisive experiment.
12. Controls, quantitative success thresholds, and kill criteria.
13. One-year platform path and shared infrastructure.
14. Evidence IDs, confidence, and reversal conditions.

## Breadth Ledger Schema

Track counts at the top:

```text
Bottleneck families covered: N
Mechanism families covered: N
Application contexts covered: N
Counterexample searches completed: N
Outside-favorite-material routes: N
```

Then use a table with branch ID, bottleneck, state type, application, architecture, missing primitive, mechanism families, representative evidence, counterexample query, and disposition.

## Search Log Schema

Each query record includes:

- Query ID.
- Date.
- Database or corpus.
- Exact query and filters.
- Search purpose.
- Results returned when available.
- Records screened and selected.
- Evidence IDs created.
- Miss or limitation.
- Next query.

## Decision Log Schema

Record decisions chronologically:

| Decision ID | Date | Decision | Evidence | Inference | Alternative | Reversal condition | Owner/next action |
|---|---|---|---|---|---|---|---|

Do not erase superseded decisions. Mark them `revised` or `rejected` and preserve why.

## Ordinal Scorecard

Use 1-5 grades with written anchors:

| Criterion | 1 | 3 | 5 |
|---|---|---|---|
| Persistence | likely bypassed | material in a defined regime | fundamental or growing across regimes |
| Mechanism depth | descriptive effect | competing mechanisms testable | causal state operation with decisive tests |
| Lab transfer | major new infrastructure | several adaptable modules | existing modules cover decisive experiment |
| First data | dependency-dominated | feasible with moderate risk | decisive data within target window |
| Platform leverage | one-off device | reusable methods | shared platform supports multiple questions |
| Open-interface evidence | direct crowding | active but unresolved | sparse direct matches after broad search |
| System value | unclear metric | plausible scoped benefit | survives baseline and overhead audit |

Report sensitivity and dependency penalties separately. Scores support discussion; they are not bibliometric facts.
