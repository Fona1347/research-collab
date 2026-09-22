# Search and Evidence Strategy

This file governs retrieval, coverage accounting, and bounded search
conclusions. Select the mode and discovery lens with
[run-modes.md](run-modes.md), assess evidence with
[evidence-confidence.md](evidence-confidence.md), and instantiate terminology
and cross-layer searches with [domain-lenses.md](domain-lenses.md).

## Contents

- [Search objective](#search-objective)
- [General query lattice](#general-query-lattice)
- [Discovery lenses](#discovery-lenses)
- [Six search lanes](#six-search-lanes)
- [Frontier salience is not claim confidence](#frontier-salience-is-not-claim-confidence)
- [Source selection and evidence depth](#source-selection-and-evidence-depth)
- [Retrieval and provenance](#retrieval-and-provenance)
- [Gray-space and bounded-open-position rule](#gray-space-and-bounded-open-position-rule)
- [Mode-specific coverage and stop gates](#mode-specific-coverage-and-stop-gates)
- [Search misses](#search-misses)
- [Global stop rule](#global-stop-rule)

## Search objective

Search must support distinct decisions rather than one oversized query:

1. establish the persistent problem and its operating boundary;
2. identify canonical concepts, current approach families, and strongest
   baselines;
3. test the proposed causal or physical mechanism;
4. find direct neighbors, contradictory evidence, replication, and hidden
   costs;
5. bound an open interface without turning a search miss into novelty.

Record which purpose every query serves. Search effort should be proportional to
the consequence of the claim, not to how attractive the preferred route appears.

## General query lattice

Build queries from the selected domain lens. Do not force pure materials,
semiconductor, neuromorphic, or wave problems into one AI-device vocabulary.

| Layer | Query dimensions |
|---|---|
| Decision context | scientific question, application, platform, comparison, operating environment |
| Desired function or observable | state, response, transformation, information operation, target metric |
| Persistent bottleneck | limiting mechanism, system budget, reliability, controllability, manufacturability |
| Missing primitive or knowledge | control, readout, discrimination, stability, scaling, integration |
| Mechanism | state variable, governing dynamics, coupling, transport, resonance, transition |
| Implementation | material, process, device, model, circuit, array, architecture, measurement |
| Failure and alternative | artifact, confound, null result, variability, loss, drift, overhead, conventional substitute |
| Evidence role | canonical, frontier, SOTA, direct neighbor, baseline, limitation, replication, translation |

Use synonyms, historical terms, equations or descriptors, adjacent-community
vocabulary, author or citation neighborhoods, and decomposed layer pairs. A
sparse exact phrase often indicates terminology mismatch rather than absence.

## Discovery lenses

The normative lens definitions are in
[run-modes.md](run-modes.md#discovery-lens-contracts). Apply them operationally
as follows.

### Frontier-led

1. Begin with recent authoritative syntheses, roadmaps, field-recognized venues,
   and representative primary work inside the evidence window.
2. Extract approach families, benchmark regimes, metrics, canonical anchors,
   and acknowledged failure modes.
3. Expand every decision-critical frontier signal to responsive primary
   evidence and full context.
4. Add direct-neighbor, limitation, negative, strongest-baseline, and
   replication searches before ranking.

Recent top-venue or highly cited work receives early attention for field-state
sensing only. It does not receive a credibility bonus.

### Gray-space-led

Build a mismatch ledger before ranking:

- mature need versus missing physical or computational primitive;
- known mechanism versus untested state operation;
- material physics versus missing independent control or readout;
- device effect versus missing system metric;
- studied platform versus untested regime;
- adjacent fields versus mismatched terminology or evaluation standards.

Every candidate must pass the two-sided plus bounded-miss rule described below.
Do not use exact-query zero hits as a discovery method by themselves.

### Balanced

Use balanced by default:

1. build a recent frontier radar and canonical anchor set;
2. build an independent mismatch ledger;
3. compare agreements, conflicts, and neglected interfaces;
4. divide effort between support and disconfirmation;
5. retain at least one route not selected solely by the fashionable
   implementation family.

## Six search lanes

Use six stable lane labels in the search log. A query may serve more than one
lane only when each role is explicit.

### L1: Canonical anchors

Find the sources that define accepted terminology, governing mechanisms,
metrics, benchmarks, and historical baselines. Older work is allowed when it
defines what current papers measure or assume.

### L2: Frontier radar

Find recent authoritative reviews, roadmaps, major field venues, emerging
primary studies, and cross-source momentum. Use this lane for terminology and
trend awareness, not causal proof.

### L3: SOTA families and strongest baselines

Group current approaches by mechanism or strategy. Retrieve the best
demonstrated regime, enabling assumptions, full-budget comparator, and current
failure boundary for each family. Search the strongest conventional solution by
name rather than comparing only with weak local baselines.

### L4: Direct neighbors and crowding

Search the complete proposed interface and its decomposed pairs, synonyms,
adjacent modules, authors, references, citing work, recent conferences,
preprints, and patents when relevant. Record the nearest matches and precisely
which causal or integration interface they do or do not close.

### L5: Disconfirmation, limitations, and replication

Search null, negative, mixed, failure, variability, scaling, calibration,
overhead, alternative-mechanism, skeptical-review, and independent-replication
terms. Search credible nonpreferred explanations and the cheapest conventional
substitute.

### L6: Translation, cross-layer, and priority

When a claim crosses material, model, device, cell, array, circuit,
architecture, workload, fabrication, or measurement layers, retrieve evidence
for each bridge. Search patents, grants, industry disclosures, standards, and
major conferences when translation or priority matters. This lane is not a
legal freedom-to-operate opinion.

### Six-lane reconciliation

After the query pass, reconcile all six labels in coverage-audit. Bind each
lane to same-lane Query IDs and relevant Evidence IDs, name the blind spot or
failure mode, and choose a next query or justified stop. Use only covered,
thin, query-failed, or out-of-scope. A zero-result query is a bounded
observation and cannot make its lane covered.

## Frontier salience is not claim confidence

Maintain two independent fields:

- **frontier_salience** prioritizes what to inspect for current field awareness;
- **claim_confidence** governs what the report may say.

For every venue or citation signal used in salience, record:

| Field | Requirement |
|---|---|
| Signal type | Venue, roadmap, raw citations, normalized citations, or cross-source convergence |
| Provider | Database or service that supplied the signal |
| Observation date | Date on which the value was retrieved |
| Raw value | Exact value when available |
| Normalization | Field and publication-year method, comparator set, and percentile or ratio |
| Availability | Verified value or unavailable |

Prefer field- and publication-year-normalized citation signals when the provider
supports them. Never invent a normalized value from a raw count. If the
provider, observation date, or normalization cannot be verified, write
**unavailable**. Venue prestige, recency, citation count, and expert enthusiasm
cannot raise claim confidence; apply the confidence contract to responsive
evidence.

## Source selection and evidence depth

Default inclusion:

- primary research that directly observes or intervenes on the claim;
- recent syntheses that define frontier topology or consensus boundaries;
- canonical work needed to define a mechanism, metric, or baseline;
- strongest conventional, digital, physical, or measurement baselines;
- direct neighbors, independent replications, and negative or mixed evidence;
- circuit, system, manufacturing, measurement, or translation evidence when a
  claim crosses those layers.

Default exclusion:

- papers selected only for fashionable title terms, venue, or citation count;
- demonstrations without the relevant mechanism, comparator, or metric;
- unverified model-generated citations;
- duplicate preprint and published versions unless version differences matter;
- secondary summaries used for a precise experimental value when the primary
  source is available.

Use metadata for discovery, passages for bounded textual support, and full
context for consequential claims. The definitions and confidence caps are
normative in [evidence-confidence.md](evidence-confidence.md). Do not repeat or
weaken them here.

## Retrieval and provenance

When Sciverse is available:

1. inspect the catalog or schema when searchable fields are uncertain;
2. use semantic retrieval for vocabulary and relevant passages;
3. use structured paper search for date filters, DOI resolution, exact titles,
   venues, and reproducible lists;
4. inspect surrounding methods, figures, tables, supplementary conditions, and
   caveats for decision-critical claims;
5. expand seed papers through citation or relationship neighborhoods when
   available.

Use primary databases and authoritative publisher or domain sources when
Sciverse coverage is weak. Record source coverage rather than treating one tool
as exhaustive.

Every query record must retain:

| Query ID | Date | Mode | Lens | Lane | Source | Exact query and filters | Results | Screened and selected | Evidence IDs | Miss or limitation | Next or stop decision |
|---|---|---|---|---|---|---|---|---|---|---|---|

Every selected source must retain DOI or stable URL, publication status,
retrievable location, evidence depth, verification date, and source role.
Preserve document, chunk, page, figure, table, section, or offset locators in
the audit artifact, not in the human-facing report.

Also record an explicit claim relation and stance. `Claim IDs` contains
authoritatively defined atomic claims, not topic keywords. Use one stance per
evidence row: `supports`, `limits`, `contradicts`, `mixed`, or
`context`. When one source has different stances toward different claims,
split it into separate evidence rows. A context-only frontier or canonical
record may use `Claim IDs: none`, but it cannot enter a claim's supporting or
limiting confidence lists. See `evidence-confidence.md` for the bidirectional
linkage rule.

## Gray-space and bounded-open-position rule

An open-position claim requires all three elements:

### Side A: Positive problem evidence

Show that the target need, bottleneck, missing operation, or unresolved
measurement is real in a stated regime and metric.

### Side B: Positive enabling evidence

Show that the proposed mechanism, controllable state, process, measurement, or
transferable capability exists in a relevant regime. Analogy alone is not
enabling evidence.

### Bounded neighbor miss

Search direct and decomposed interfaces across synonyms, adjacent fields,
dates, venues, languages, patents or conferences when relevant, and access
boundaries. List the nearest matches and the exact interface left unresolved.

If either positive side is missing, classify the item as speculation or an
evidence gap. If the neighbor search is incomplete, classify it as unsearched.
Zero hits establish only a bounded retrieval result, never absence, priority,
novelty, or an open position.

## Mode-specific coverage and stop gates

### Landscape

Cover the breadth gate defined in run-modes. Across the map, represent all six
lanes. For every finalist, require:

- canonical and frontier context;
- its SOTA approach family and strongest baseline;
- direct neighbors and bounded crowding;
- at least one limitation, disconfirmation, or alternative;
- cross-layer or translation evidence when system value is claimed.

Stop broadening only when new searches mostly recover known families, the
global breadth gate is satisfied or justified, and every finalist can be
compared and falsified.

### Focus

Use a local breadth gate around the selected interface. Search:

- the proposed mechanism;
- the strongest alternative mechanism;
- the strongest practical comparison route;
- direct neighbors, boundary regimes, failure modes, and dependencies;
- every cross-layer bridge needed by the route.

Stop when the primary route, comparator, and fallback have responsive evidence,
the decisive claims have a confidence disposition, and remaining uncertainty
is cheaper to resolve with a named experiment or dependency check.

### Evidence audit

Begin from atomic claims and required evidence roles. Search support,
limitations, contradictions, independence or replication, applicability,
direct neighbors, and strongest baselines only where the claim type requires
them.

Stop when every decision-critical claim has High, Moderate, Low, or
Insufficient confidence, all caps and allowed wording are explicit, and each
unresolved gap has an upgrade or overturn action. Do not use a paper-count
target as a completion gate.

### Run audit

Audit inherited search coverage before adding external queries. Search only to
resolve a named integrity or scientific finding, such as an untested neighbor,
unsupported persistence claim, missing comparator, or priority overclaim.

Stop when every in-scope finding has a Keep, Downgrade, Revise, or Kill
disposition and the exact repair or residual uncertainty is recorded. Do not
force a new landscape or minimum query count.

## Search misses

Record misses because they constrain the next query, but phrase them exactly:

Acceptable:

> No direct match was retrieved from databases D using queries Q, dates Y,
> filters F, languages L, and access A as of DATE; nearest matches E leave
> interface I unresolved.

Not acceptable:

> Nobody has studied this.

A miss may reflect terminology mismatch, indexing delay, inaccessible
proceedings, non-English work, patents, unpublished work, or a genuinely sparse
area. Classify it as bounded negative evidence and schedule the nearest useful
synonym, neighbor, or source expansion.

## Global stop rule

Stop a search branch when:

- new queries predominantly return already-screened sources or known neighbors;
- the decision-critical bottleneck, mechanism, baseline, and limitation claims
  have responsive evidence;
- cross-layer transfers are evidenced or explicitly capped;
- the open-position statement is bounded by an adequate neighbor search;
- every remaining uncertainty has a named experiment, specialized source, or
  external dependency that is more decision-efficient than further general
  searching.

Do not stop because a favored route already looks attractive, a top paper has
been found, or an arbitrary paper quota has been reached.
