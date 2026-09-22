# Run Modes, Discovery Lenses, and Domain Lenses

This document is the normative routing and completion contract for schema 2.x
runs. It separates **what work is performed** (`task_mode`), **how
opportunities enter the search** (`discovery_lens`), and **which scientific
variables, confounds, bridges, and baselines govern the object**
(`primary_domain_lens` plus optional secondary lenses). Apply all three before
choosing templates, search depth, or completion gates.

## Contents

- [Invariant core](#invariant-core)
- [Three orthogonal controls](#three-orthogonal-controls)
- [Natural-language routing](#natural-language-routing)
- [Discovery-lens contracts](#discovery-lens-contracts)
- [Landscape contract](#landscape-contract)
- [Focus contract](#focus-contract)
- [Evidence-audit contract](#evidence-audit-contract)
- [Run-audit contract](#run-audit-contract)
- [Parent-child and mutation rules](#parent-child-and-mutation-rules)
- [Cross-mode transitions](#cross-mode-transitions)
- [Routing outside this skill](#routing-outside-this-skill)
- [Global prohibitions](#global-prohibitions)

## Invariant core

Every mode must preserve this intersection:

`durable bottleneck x falsifiable causal/physical mechanism x transferable capability x bounded open position`

The four factors are necessary, not interchangeable:

1. **Durable bottleneck**: establish that a consequential limitation persists under a stated regime and metric; popularity alone is not a bottleneck.
2. **Falsifiable mechanism**: identify the controlled variable, proposed causal path, alternatives, null result, and discriminating observation.
3. **Transferable capability**: distinguish `Observed`, `Reported`, `Assumed`, and `Unknown`; give every capability a meaningful `Source or evidence` basis. `Observed` and `Reported` cannot use an uncertain-only basis such as not yet verified, unverified, unknown, assumed, learning only, planned only, or not documented. A `Reported` capability may remain independently unreplicated when it names the underlying report, record, or source. Never turn training, plans, or adjacent experience into mature capability.
4. **Bounded open position**: state databases, terminology, dates, languages, access, neighbor definitions, and search misses. A miss is not proof of novelty.

Before naming a preferred material, device, architecture, or application, define the decision, target state or workload, mechanism, metric, budget, and boundary. Keep `Evidence`, `Inference`, and `Recommendation` visibly separate in every mode.

Valid unique `context_sources[].source_id` values (`CTX-###`) belong to the
external ID closure. For schema-2 modes other than `run-audit`, non-sentinel
evidence `Reader ref` values and numbered reader references also close in both
directions, one evidence row per number with matching normalized DOI/stable
links. Run-audit bibliography closure and parent citation projection remain
separate.
`claim-confidence` has at most one row per authoritative claim and exactly one
row for every decision-critical claim.

## Three orthogonal controls

Persist exactly one formal `task_mode`:

- `landscape`
- `focus`
- `evidence-audit`
- `run-audit`

Persist exactly one `discovery_lens`:

- `frontier-led`
- `gray-space-led`
- `balanced`

Persist exactly one `primary_domain_lens` and zero or more interface-only
`secondary_domain_lenses`. Select by the object and scale, not a familiar
material name. If specialized lenses do not fit, explain why and draft the
task-local `custom` interface before asking consequential questions.
Use `generic-physical-engineering` with an explicit fit/fallback rationale,
not a silent downgrade. Custom still requires all ten substantive interface
fields from `domain-lenses.md`; unknown facts must remain identified as unknown.

`auto` is a router request, not a formal mode. Never persist `task_mode: auto`. Resolve it to one of the four formal modes and record the original request, selected mode, reason, and routing confidence.

The three controls answer different questions:

| Control | Question answered | Example |
|---|---|---|
| `task_mode` | What decision artifact is needed? | Deepen one causal interface with `focus`. |
| `discovery_lens` | Where should candidate signals enter? | Search adjacent mismatches with `gray-space-led`. |
| `primary_domain_lens` plus secondary lenses | Which state variables, confounds, layer bridges, and baseline ladder govern the claim? | Use `semiconductor-device` with an interface-only `integrated-circuit` secondary lens. |

Any valid combination is allowed. For example, `focus + frontier-led` tests a hot branch deeply, while `landscape + gray-space-led` maps underexplored interfaces across a broad field.

## Natural-language routing

Route by the decision the user needs, not by topic breadth in the prompt alone.
These signals select a mode only after the SKILL.md invocation boundary is met.
An ordinary single-paper credibility check stays with focused reading; this
table does not turn that request into a formal Mapper audit.

| Request signal | Select | Required clarification encoded in intake |
|---|---|---|
| “Map this field”, “compare directions”, “what opportunities exist?” | `landscape` | Domain boundary, decision horizon, risk tolerance, and capability context. |
| “Deepen this direction”, “turn this branch into an executable route” | `focus` | Selected branch/interface, current evidence, strongest comparator, and first-data deadline. |
| “Complete the evidence chain”, “audit these claims/papers”, “how credible is this?” | `evidence-audit` | Atomic claims, allowed update scope, parent run if any, and evidence cutoff. |
| “Audit this run/report”, “red-team the recommendation”, “find integrity failures” | `run-audit` | Target run, audit boundary, and whether proposed revisions may be written as a child run. |

When signals conflict, choose the smallest mode that can answer the decision without discarding necessary alternatives:

1. Prefer `run-audit` when an existing run is the audit object.
2. Prefer `evidence-audit` when the object is a set of claims or sources rather than a route.
3. Prefer `focus` when a branch is already selected but needs comparison and a decisive protocol.
4. Use `landscape` when candidate families have not been mapped or the user needs portfolio selection.

Record low routing confidence and the unresolved ambiguity. Do not silently broaden a narrow audit into a new landscape or silently narrow a landscape to the agent's favorite route.

Recommend mode from the required decision, discovery lens from the discovery
task, and domain lens from the object and scale. Give reasons before confirming
inferred axes. User-specified axes stay fixed; ask only about missing information
that changes the selection. Research preflight does not apply to Skill maintenance.

Balanced is justified when both a frontier map and mismatch search serve the
decision. Otherwise prefer the better-supported single lens; balanced is only
an explained fallback when no stronger reason exists. Every lens still seeks
limitations, competitors and negative evidence.

## Discovery-lens contracts

### `frontier-led`

Use frontier signals to orient search, not to determine truth.

1. Start with recent authoritative syntheses, roadmaps, field-defining venues, and representative primary studies inside the run's evidence window.
2. Use field- and year-normalized citation signals when available; record the provider and observation date.
3. Recover canonical older work when it defines the mechanism, metric, benchmark, or failure mode.
4. Add direct-neighbor, limitation, negative, and strongest-baseline searches before recommending a route.
5. Keep `frontier_salience` separate from claim confidence. Venue prestige, recency, and citations cannot upgrade an unsupported causal claim.

### `gray-space-led`

Generate candidates from bounded mismatches such as:

- mature need x missing physical or computational primitive;
- known mechanism x untested state operation;
- material physics x missing control or readout;
- device effect x missing system metric;
- studied platform x untested operating regime;
- adjacent fields x terminology or evaluation mismatch.

An open-position statement requires all of the following:

1. Positive evidence that the need, limitation, or target operation is real.
2. Positive evidence that the proposed mechanism or enabling capability exists in a relevant regime.
3. A bounded direct-neighbor search across synonyms, adjacent modules, dates, venues, patents or conferences when relevant.
4. Explicit nearest matches and the precise interface they do not close.
5. A falsifiable mechanism and a feasible discriminating test.

Zero hits establish only a search result. They never establish “nobody has done this”, “white space”, priority, or novelty.

### `balanced`

Use `balanced` when both discovery needs serve the decision, or as an explained fallback when neither single lens has a stronger basis. Once selected:

1. Build a recent frontier radar and a canonical anchor set.
2. Build a mismatch ledger independently of publication popularity.
3. Compare where the two sets agree, conflict, or expose a neglected interface.
4. Allocate search effort to both confirmation and disconfirmation.
5. Check that any surviving candidates are justified by the problem and mechanism,
   not solely by the currently fashionable material or architecture. Do not
   create a candidate merely to satisfy a diversity quota.

## Landscape contract

### Purpose

Compare substantive causal interfaces within the requested scientific scope and retain zero, one, or several candidates. Risk labels classify the actual candidates; no low/medium/high quota applies.

### Required artifact roles

- Decision intake and capability passport.
- Breadth ledger and mapping lattice.
- Search log and claim-level evidence matrix.
- Research map with Evidence/Inference/Recommendation labels.
- Candidate portfolio with risk labels for the actual zero, one, or several substantive routes; risk levels are not quotas.
- Adversarial audit, rejected-route log, uncertainty register, and decision log.
- A human-facing landscape report.

### Required gates

1. Satisfy the global breadth gate across bottleneck, mechanism, application, and out-of-favorite-family branches, or justify every scoped exception.
2. Compare mechanism families before ranking material or device implementations.
3. Include canonical anchors, recent frontier evidence, direct neighbors, strongest baselines, negative/limiting evidence, and translation evidence where relevant.
4. Select only substantive candidates. A shared infrastructure or dependency does not itself make routes identical, but information/mechanism/system stages are not separate directions unless each has an independent question, knowledge product and termination condition. Do not broaden a narrow request or invent risk tiers to fill the template.
5. Give every finalist a decisive experiment, success threshold, kill criterion, dependencies, reversal conditions, and retained value after failure.
6. Red-team at least one initially attractive route and allow the audit to revise, downgrade, or kill it.
7. Give every finalist its own route-artifact execution fields and its own
   reader-report execution row, plus route-owned `positive`, `negative`, and
   `ambiguous` interpretations. An unassigned shared experiment or outcome
   tree does not close a multi-route portfolio.
8. Project the exact authoritative `C-### -> low|medium|high` mapping from
   `candidate-routes` into reader `decision-summary`, once per candidate.

Landscape requires breadth appropriate to its declared scope, not a three-level portfolio. Zero candidates is a valid selection outcome when the report gives claim-owned rejection reasons and reopening conditions; it is distinct from having candidates but zero gate-eligible pilots.

## Focus contract

### Purpose

Deepen one selected branch, unresolved causal interface, or candidate route until it becomes executable and discriminating without recreating an artificial broad portfolio.

### Required artifact roles

- Focus intake, parent lineage when applicable, and selected branch boundary.
- Local alternative map: at least the proposed mechanism, strongest alternative mechanism, and strongest conventional route.
- Search log and claim-level evidence matrix scoped to the branch.
- Claim-mechanism map with nulls, confounds, and discriminating observables.
- Protocol for actual routes, strongest comparison and fallback designs, and phase gates.
- Adversarial audit, uncertainty register, decision log, and human-facing focus report.

### Required gates

1. Identify why the question is sufficient, necessary, timely, and decision-relevant.
2. State `control X -> state operation Y -> observable A` under constraints `Z`, compared with baseline `B`.
3. Test at least one credible alternative mechanism and the strongest practical comparator.
4. Specify baseline, controls, parameter/regime boundaries, success threshold, kill criterion, and dependencies.
5. Give each substantive candidate its own execution row
   and separate positive, negative, and ambiguous outcomes in both the route
   protocol and reader report; each branch must change belief or the next action.
6. Allow zero, one, or several substantive routes; require one primary only when nonempty. Preserve the strongest comparator and fallback in existing design fields rather than inventing separate C-IDs. For zero routes, declare Selection outcome: no-candidate, close atomic-claim decisions and give a concrete information check or bounded stop.
7. Inherit parent evidence or capability facts only through declared IDs and lineage; re-check facts whose scope or freshness changes.
8. Project the exact `C-### -> primary|comparator|fallback` mapping from
   `focus-routes` into reader `recommended-routes`, once per route.

Apply a local breadth check around the selected interface, not the landscape global breadth gate.

## Evidence-audit contract

### Purpose

Complete or challenge the evidence chain for explicit claims, estimate claim-level confidence, constrain allowed wording, and identify the cheapest evidence that could upgrade or overturn a decision.

### Required artifact roles

- Audit scope and atomic claim register.
- Required-evidence-role map for each decision-critical claim.
- Search log covering support, limitations, contradictions, replication, direct neighbors, and strongest baselines.
- Evidence matrix with retrievable provenance and verification depth.
- Claim-confidence assessment and hard-cap reasons.
- Evidence-gap plan, contradiction audit, decision log, and human-facing evidence-audit report.

### Required gates

1. Split broad propositions into atomic claims with explicit scope, regime, metric, and claim type.
2. Identify which claims are decision-critical and what evidence role each requires.
3. Evaluate evidence directness, full-context status, method validity, independence, replication, consistency, applicability, and contradictions.
4. Assign only `High`, `Moderate`, `Low`, or `Insufficient` under the confidence contract; record every cap and downgrade.
5. State allowed wording at the assessed confidence and the evidence needed to upgrade or overturn it.
6. Separate frontier salience from confidence and record citation data as `unavailable` when it cannot be verified.
7. When attached to a parent run, default to a supplement. Never silently rewrite the parent's recommendation; record a proposed `Keep`, `Downgrade`, `Revise`, or `Kill` change in the child decision log.
8. Require every evidence row's `Claim IDs` to resolve to authoritative atomic
   claims and require its `Stance` to agree with supporting versus limiting
   confidence lists. Context-only evidence cannot satisfy a decision-critical
   evidence role.
9. Make `target-claims`, `claim-register`, canonical `claim-confidence`,
   `confidence-assessment`, `allowed-wording`, and reader `claim-verdicts`
   exact-once projections of the same target set. Give each target one or more
   `evidence-gaps` rows; multiple gaps are allowed, but undeclared Claim IDs are
   not.

Evidence audit is complete when each decision-critical claim has a disposition, not when a target paper count is reached.

## Run-audit contract

### Purpose

Adversarially assess an existing run's traceability, causal reasoning, capability fit, open-position language, cross-scale claims, and reader-report consistency.

### Required audit surfaces

1. Manifest, schema version, lineage, artifact presence, and completion state.
2. Cross-artifact IDs, DOI or stable-link references, and dangling or orphaned records.
3. Claim scope, evidence depth, confidence caps, and unresolved contradictions.
4. Bottleneck persistence and whether the metric or boundary manufactures a false problem.
5. Causal mechanism, competing explanations, controls, nulls, and discriminating outcomes.
6. Open-position search breadth, terminology mismatch, close neighbors, and unsupported priority language.
7. Capability status inflation and unverified access to tools, samples, processes, or measurement systems.
8. Material/device proxy to cell, array, architecture, or workload layer jumps.
9. Strongest conventional, digital, or non-biomimetic baseline and same-budget comparison.
10. Peripheral, calibration, PVT, yield, reliability, fabrication, and measurement costs where relevant.
11. Reader report versus audit artifacts: citations, recommendations, uncertainty, stop conditions, and outcome interpretation.

For schema 2, verify definition authority as well as string occurrence. An ID in
prose, a reader table, a fenced example, a reference column, or a correctly
named table in the wrong manifest artifact role does not define or authorize
that ID.

Before scientific judgment, run `scripts/parent_audit.py` against the immutable
parent and reproduce all four local projections. The validator independently
recomputes them. It compares `citation-closure` to the parent reader and parent
evidence matrix, never to the audit report's own references. A schema-1.0 parent
uses the explicit no-declared-reader sentinel. Schema 1.1 infers exactly one safe
matching reader from `artifact_files` and does not require `primary_artifact`;
schema 1.2 uses `primary_artifact`, and schema 2 uses
`artifact_roles.reader_report`. An incomplete parent is a valid audit target;
parent drift after snapshot creation is not.

### Required disposition

Every decision-critical finding must produce one action:

- `Keep`: the conclusion survives within its stated boundary.
- `Downgrade`: retain the proposition with lower confidence or narrower wording.
- `Revise`: change the route, experiment, mechanism, scope, or evidence plan.
- `Kill`: stop recommending the route under the current decision conditions.

Propagate dispositions into the audit decision log and final report. Every
non-`Keep` attack must change the affected authoritative route/claim verdict,
confidence or wording, or explicit parent impact. When several attacks share a
target, the strongest binding verdict governs
(`Kill > Revise > Downgrade > Keep`). A risk list that cannot change a
recommendation does not satisfy `run-audit`.

Every manifest row uses `canonical_manifest_repair(Check, Result)`; `pass` and
`not-applicable` rows use `retain observed state`. Every row carries exactly one
valid `D-###` that resolves to exactly one decision; `pass` and
`not-applicable` bind `Keep`. Each failed row is high/blocking and owns a
Decision ID used by no other manifest row or attack. It resolves to one non-`Keep` decision whose Target ID
and Affected decision target IDs are the same single authoritative route/claim,
whose Decision is `Parent manifest failure [<check>]`, whose Trigger Attack IDs
is `not-applicable: deterministic manifest check`, and whose Owner/next action
is the canonical repair. Reader integrity contains all and only these failures
once as lowercase `parent manifest failure [<check>]`; the clean Keep sentinel
is allowed only with zero failures.

For each route/claim, take the strongest disposition across both attacks and
manifest-failure decisions plus recomputed parent ID/citation anomalies. If
integrity ties an attack at the maximum rank,
bind the route verdict to an equally strong integrity Decision ID.

Every anomaly binds a substantive Repair and non-`Keep` decision with one
authoritative Target/Affected target. A dedicated anomaly decision is unique
among anomaly rows, does not reuse a manifest-failure decision, and uses
`Parent <marker> anomaly [<key>:<status>]`, trigger
`not-applicable: deterministic parent anomaly`, and Owner/next action equal to
Repair. Its stable lowercase source is
`parent <marker> anomaly [<key>:<status>]`.

An anomaly may jointly share the same non-`Keep` attack decision; then retain
the attack source/trigger/owner instead of rewriting it. Working and reader
route verdicts match exactly, and a selected dedicated anomaly maximum preserves
its stable finding, Repair, verdict, and Decision ID in both.

## Parent-child and mutation rules

1. Treat historical and parent runs as immutable evidence objects.
2. Create a child run for focus, evidence completion, or audit work; record relation, selected branch or claims, inherited IDs, source manifest reference, and source-manifest hash.
3. Use workspace-relative references plus stable run IDs. Do not rely on an absolute path as the sole lineage key.
4. Distinguish inherited facts from newly verified, revised, or rejected facts.
5. Never overwrite a parent recommendation silently. Propose the changed disposition in the child and require an explicit integration step.
6. If the parent cannot be resolved or its hash differs, record lineage as unresolved and do not claim a verified inheritance chain.
7. A `run-audit` has exactly one parent and freezes every observed parent file, including undeclared files; it does not require the parent itself to pass validation.

## Cross-mode transitions

Use explicit transitions rather than changing a run's meaning in place:

| From | Trigger | Create |
|---|---|---|
| `landscape` | A branch is selected for execution | Child `focus` run. |
| `focus` | One or more claims control the route but remain weak | Child `evidence-audit` run. |
| Any persisted run | Integrity or recommendation is challenged | Child `run-audit` run. |
| `evidence-audit` | Evidence supports a bounded executable interface | New or resumed `focus` run with declared inheritance. |
| `run-audit` | Audit finds breadth was prematurely collapsed | New `landscape` run or a declared landscape revision. |

## Routing outside this skill

Route or orchestrate a companion workflow when the requested deliverable is primarily:

- a systematic review with protocol-level inclusion and synthesis;
- a full-paper deep reading rather than claim comparison;
- an experimental design after the research route is already chosen;
- statistical power or sample-size analysis;
- implementation of a device model, circuit, data pipeline, or experiment rather than route selection.

Record the routing decision and preserve any claims or lineage passed to the companion workflow. Do not pretend that this skill's structural validator replaces domain review, experiment design, or scientific truth assessment.

## Global prohibitions

- Do not persist `auto` as `task_mode`.
- Do not force a focus or audit run through landscape-wide breadth or risk quotas.
- Do not equate top venue, citation count, novelty language, or recent publication with reliable evidence.
- Do not convert a search miss into absence, priority, or novelty.
- Do not make recommendation language appear as Evidence.
- Do not infer mature capability from plans, training, documentation, or adjacent experience.
- Do not infer array, circuit, architecture, or workload benefit from a material/device proxy without explicit intermediate models and same-budget baselines.
- Do not let red-team findings remain decorative; disposition every decision-critical attack.
- Do not omit any of the eight registered attack surfaces. A genuinely
  non-biological run keeps a bounded not-applicable bio-translation attack; a
  bio-triggered run must show the de-biologized question, mathematical operator
  or state update, algorithm, hardware primitive, matched baseline, ablation,
  and measurable boundary and cannot mark the chain wholly `not applicable`.
- Do not let an ID occurrence in a wrong-role artifact act as an authoritative
  definition or an inheritable parent fact.
