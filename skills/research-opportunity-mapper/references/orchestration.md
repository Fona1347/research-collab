# Multi-Skill Orchestration

Assign each companion workflow a narrow epistemic role. Route requests whose primary deliverable belongs elsewhere; orchestrate companion skills only when their artifacts feed a mapper decision. Preserve provenance and mode/lineage across every handoff.

## Contents

- [Routing principle](#routing-principle)
- [When to route outside the mapper](#when-to-route-outside-the-mapper)
- [Mode-aware orchestration](#mode-aware-orchestration)
- [Evidence and ideation roles](#evidence-and-ideation-roles)
- [Recommended handoff sequence](#recommended-handoff-sequence)
- [Handoff packet](#handoff-packet)
- [Parallelism](#parallelism)
- [Conflict resolution](#conflict-resolution)
- [Return-to-mapper rule](#return-to-mapper-rule)

## Routing principle

First identify the requested primary deliverable:

- an explicitly requested Mapper task, continuation of an identified Mapper run, or a necessary formal route decision with alternatives, feasibility gates, and a roadmap -> keep the mapper as lead;
- a systematic review, full-paper interpretation, detailed experimental design, or power calculation -> route the primary task to the dedicated workflow below.

Do not keep the mapper as nominal lead merely because literature or experiments appear in the request. The mapper selects and audits routes; it does not replace specialist protocols.

When routing, record:

1. the original request;
2. the selected workflow and reason;
3. the artifacts and claim IDs transferred;
4. whether and how results should return to a parent mapper run.

## When to route outside the mapper

### Systematic review

Route to `literature-review` when the user primarily requests an exhaustive or protocol-governed review, PRISMA-style screening, a systematic evidence synthesis, or a meta-analysis-ready corpus.

Keep `research-opportunity-mapper` as lead only when search is in service of choosing or auditing a research route. In that case, use a scoping or claim-targeted search and do not claim systematic-review exhaustiveness.

Return useful systematic-review artifacts to the mapper as a bounded corpus, search protocol, inclusion/exclusion record, and synthesized claim set. Do not reduce the handoff to a prose conclusion.

### Full-paper deep reading

Route to `paper-deep-reading` when the primary object is one paper or a small, fixed set of papers and the user needs figure-, table-, formula-, methods-, or claim-level interpretation.

Use deep reading as a companion inside `evidence-audit` when a decision-critical claim cannot be assessed from the current verified context. Return exact locations, claim boundaries, methods, limitations, and source identity. A deep-reading interpretation does not establish field consensus or novelty by itself.

### Experimental design

Route to `experimental-design` when the route and primary hypothesis have already been selected and the user needs a detailed study design: treatment structure, controls, randomization, blocking, replication units, measurement schedule, or analysis-ready layout.

The mapper should specify the causal question, competing hypotheses, decision threshold, capability boundary, and cheapest decisive test. The experimental-design workflow should turn that skeleton into an executable design. Return the design, assumptions, estimand, failure modes, and decision rule to the parent `focus` run.

### Statistical power and sample size

Route to `statistical-power` only after the primary endpoint, effect definition, variance model, design, unit of analysis, error rates or decision criterion, and attrition/failure assumptions are explicit.

If those inputs are missing, do not invent them to produce a number. Return to `experimental-design` or the mapper's focus phase to define them. Power output should include assumptions and sensitivity, then return to the route protocol as a dependency rather than as proof of feasibility.

### Boundary examples

| User request | Lead | Mapper relationship |
|---|---|---|
| “Systematically review all controlled studies of X” | `literature-review` | Optional downstream opportunity mapping after corpus completion. |
| “Explain Fig. 3 and the mechanism in this paper” | `paper-deep-reading` | Optional evidence record for a claim audit. |
| “Which of five physical mechanisms should our lab pursue?” | `research-opportunity-mapper` | Landscape or focus lead; retrieve evidence as needed. |
| “Design the randomized experiment for the selected route” | `experimental-design` | Child/specialist handoff from focus. |
| “How many devices or batches do we need?” | `statistical-power` | Only after design and variance/effect assumptions exist. |
| “Check the evidence for these three paper claims” | Retrieval plus source reading | Standalone verification; no Mapper run required. |
| “Audit these decision-critical claims in the named Mapper route before continuing it” | `research-opportunity-mapper` | `evidence-audit`, with deep reading as needed. |

## Mode-aware orchestration

| Mapper mode | Common companion roles | Do not delegate |
|---|---|---|
| `landscape` | Controlled divergence, scoping search, structured retrieval, baseline and causal audit | Portfolio decision, capability intersection, or final Evidence/Inference/Recommendation synthesis. |
| `focus` | Targeted retrieval, deep reading, critical thinking, experimental design after route selection | Selection of primary route/comparator/fallback and mode completion judgment. |
| `evidence-audit` | Structured retrieval, deep reading, citation verification, conflict search | Claim-confidence ruling, hard-cap application, allowed wording, or parent disposition. |
| `run-audit` | Read-only integrity checks, targeted evidence verification, adversarial review | `Keep`, `Downgrade`, `Revise`, or `Kill` decision and parent-child mutation boundary. |

The discovery lens changes search entry, not skill authority:

- `frontier-led`: use retrieval/review tools to find recent authoritative synthesis and representative primary work, then limitations and direct neighbors;
- `gray-space-led`: search both sides of the mismatch independently and test adjacent terminology;
- `balanced`: run separate frontier and mismatch branches before merging through shared claim/evidence IDs.

## Evidence and ideation roles

### `academic-research-suite` or `academic-research-suite-legacy`

Use for decision framing, question architecture, hypotheses, work packages, and phase gates. Treat generated citations or scientific assertions as unverified until retrieved and checked.

### `scientific-brainstorming`

Use only after the decision, budget, and capability boundary are explicit. Vary bottleneck, state variable, control axis, readout, timescale, integration level, and baseline. It may generate candidates and competing hypotheses; it cannot establish novelty, evidence confidence, or capability.

### `literature-review`

Use scoping mode for broad mapper discovery and systematic mode only when the protocol is truly required. Preserve query logs, inclusion logic, coverage, and limitations.

### `sciverse-research` and other retrieval tools

Use corpus-aware retrieval for discovery, metadata, and claim-level passages. Expand decision-critical claims to sufficient context; retain DOI or stable link, source identifiers, retrievable location, search date, and verification status. Add authoritative primary databases or publisher records where corpus coverage is weak.

### `scientific-critical-thinking`

Use to challenge causality, alternative mechanisms, benchmark fairness, proxy-to-system inference, and hidden cost. Require objections to map to a discriminating search, experiment, or disposition.

### `paper-deep-reading`

Use for source-grounded interpretation of a decisive paper. Return precise claim/evidence units; do not ask it to rank the whole field from one source.

### `experimental-design`

Use after a focus route has a stable causal question. Preserve experimental unit, controls, randomization/blocking, measurement, and decision threshold.

### `statistical-power`

Use after design inputs stabilize. Preserve effect and variance assumptions, model, target power or decision criterion, hierarchy, attrition, and sensitivity.

## Recommended handoff sequence

Not every run needs every stage. Use the minimum sequence that satisfies the selected mode.

| Stage | Lead role | Input | Required return |
|---|---|---|---|
| Route and frame | Mapper | User request and context | Formal mode, lens, decision, boundary, capability status. |
| Controlled divergence | Brainstorming role | Landscape decision brief | Bottleneck/mechanism branches with failure reasons; no novelty claims. |
| Search design | Review role | Branches or atomic claims | Query lattice, evidence roles, inclusion logic, stop rule. |
| Retrieval | Retrieval role | Queries and seeds | Structured evidence, provenance, context status, misses. |
| Source expansion | Deep-reading role | Decision-critical source/claim | Exact contribution, location, method, boundary, contradiction. |
| Critical audit | Critical-thinking role | Claims, evidence, candidates | Alternatives, confounds, baselines, discriminating tests. |
| Route protocol | Mapper, then experimental design if needed | Surviving focus route | Primary/comparator/fallback and executable design handoff. |
| Power | Power workflow | Stable endpoint and design | Sample/device/batch requirement with assumptions and sensitivity. |
| Synthesis | Mapper | All accepted artifacts | Mode-appropriate report, disposition, uncertainty, and next action. |

## Handoff packet

Every handoff must contain:

1. parent run ID or standalone task reference;
2. selected mode, discovery lens, primary/secondary domain lenses, and decision
   boundary;
3. current artifact version or immutable source snapshot;
4. authoritative atomic claim and evidence IDs relevant to the task, including
   each evidence row's Claim-ID linkage and stance;
5. Evidence, Inference, and Recommendation kept separate;
6. assumptions, unknowns, confidence caps, and rejected alternatives;
7. exact questions the receiving workflow must answer;
8. required return format and where it will be integrated.

Do not hand off a prose summary alone. Do not pass a desired conclusion as if it were evidence.

## Parallelism

Parallelize only branches that can return independently into a fixed ontology and ID scheme. Useful branches include:

- independent bottleneck or mechanism families in landscape;
- frontier radar versus gray-space mismatch search in balanced lens;
- support versus contradiction searches for separate claims;
- baseline, direct-neighbor, and alternative-mechanism audits;
- independent deep readings of different decision-critical sources.

Do not parallelize decisions that share mutable ranking or lineage state. Merge by evidence and claim IDs, not by copying conclusions.

## Conflict resolution

When workflows disagree:

1. Prefer responsive primary evidence over generated interpretation.
2. Check whether apparent conflict comes from different regimes, definitions, or budgets.
3. Check source, sample, dataset, model, and laboratory dependence.
4. Apply the confidence hard caps rather than forcing consensus.
5. Design the smallest search, deep reading, or experiment that can resolve the disagreement.
6. Record unresolved conflict and its decision impact.

No companion skill has authority to override the mapper's evidence contract, parent immutability, or user-defined scope.

## Return-to-mapper rule

A specialist result returns to an already requested Mapper task only when it preserves traceability and changes its decision, confidence, route protocol, or dependency. Standalone retrieval, reading, and journal selection do not create a Mapper task merely to receive their output. On return:

- register new evidence and claim links;
- mark inherited versus newly verified information;
- apply active confidence caps;
- update the child decision log rather than silently rewriting a parent;
- rerun mode-specific red-team and validation gates.

Deliver the mapper's human-facing report first after integration. Keep specialist artifacts as linked evidence or execution plans.
