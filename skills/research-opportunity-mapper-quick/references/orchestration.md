# Multi-Skill Orchestration

## Principle

Assign each companion skill a narrow epistemic role. Do not ask one skill to brainstorm, retrieve evidence, judge novelty, and select a direction in a single step. Handoffs must be artifact-based so claims remain auditable.

## Recommended Sequence

| Stage | Lead skill | Input | Required output | Gate |
|---|---|---|---|---|
| Decision framing | `academic-research-suite-legacy` | User goal, time horizon, capability facts | Decision brief, assumptions, scope | Decision and guarantee are explicit |
| Controlled divergence | `scientific-brainstorming` | Decision brief, capability passport | Bottleneck families, mechanism families, speculative intersections | Breadth ledger meets minimum coverage |
| Search design | `literature-review` | Breadth ledger | Query lattice, source plan, inclusion/exclusion logic | Every branch has a search path |
| Retrieval | `sciverse-research` | Queries and seed papers | Structured records, evidence chunks, provenance, misses | Consequential claims have retrievable sources |
| Critical audit | `scientific-critical-thinking` | Evidence matrix and candidates | Confounds, counterclaims, baseline audit, kill criteria | Each finalist survives or is revised |
| Question architecture | `academic-research-suite-legacy` | Surviving candidates | Research question, hypotheses, work packages, milestones | Three-month and one-year paths are coherent |
| Final synthesis | This skill | All working artifacts | Primary reader-ready `map_report` plus map, portfolio, uncertainty register, and next actions | Reader report and audit-layer completion gates pass |

## Role Boundaries

### `academic-research-suite-legacy`

Use for Socratic clarification, research-question decomposition, method architecture, and stage gates. Do not treat its generated citations as evidence unless independently retrieved and verified.

### `scientific-brainstorming`

Use after constraints are explicit. Ask it to vary the bottleneck, state variable, control axis, readout, timescale, integration level, and benchmark. Require competing hypotheses and failure modes. It may generate candidates but cannot establish novelty or feasibility.

### `literature-review`

Use in scoping-review mode for opportunity maps unless an exhaustive systematic review is explicitly required. It should maintain query logs, inclusion rules, coverage, and thematic synthesis. Do not claim PRISMA-style exhaustiveness unless the actual protocol and screening were completed.

### `sciverse-research`

Use as the primary retrieval layer when its corpus covers the field:

1. Inspect catalog/schema when fields are uncertain.
2. Use semantic retrieval for concept discovery and claim-level passages.
3. Use structured paper search for DOI, year, venue, title, and filtered lists.
4. Read surrounding content for claims that affect ranking.
5. Expand from seed papers through related records when supported.

Save database identifiers, chunk or page locations, search date, and verification state. If Sciverse coverage is weak, add Crossref, OpenAlex, Semantic Scholar, publisher pages, arXiv, IEEE, ACM, PubMed, Lens, Google Patents, or domain databases as appropriate.

### `scientific-critical-thinking`

Use to test whether evidence supports causality, whether alternative mechanisms explain the result, whether benchmarks are fair, and whether system overhead erases device-level gains. It should produce explicit objections and tests that could resolve them.

## Handoff Packet

Every stage hands off:

1. Current artifact version.
2. Atomic claims and evidence IDs.
3. Assumptions and unknowns.
4. Rejected alternatives and reasons.
5. Questions the next stage must answer.

Do not hand off a prose summary alone. The receiving stage must be able to trace a recommendation back to evidence and a search query.

The final handoff is different: preserve the structured audit layer, but deliver the human-facing `map_report` first. The user should not need to inspect internal IDs or retrieval records to understand the decision.

## Parallelism

Parallelize independent branches only after the ontology and artifact schema are fixed. Useful parallel branches include:

- Bottleneck families.
- Mechanism families.
- Direct-neighbor searches for separate candidates.
- Baseline and counterexample searches.

Merge results through shared evidence IDs and candidate IDs. Do not merge by copying conclusions without their provenance.

## Conflict Resolution

When skills disagree:

1. Prefer primary evidence over generated interpretation.
2. Prefer direct measurements over analogies.
3. Prefer a bounded uncertainty label over forced consensus.
4. Design the smallest search or experiment that can resolve the conflict.
5. Record the unresolved conflict in the decision log.
