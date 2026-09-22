# Human-Facing Reader Report

This file is the sole normative narrative contract for every schema 2.x primary
report. Use [run-modes.md](run-modes.md) for mode selection and artifact gates,
[evidence-confidence.md](evidence-confidence.md) for claim confidence and allowed
wording, and [domain-lenses.md](domain-lenses.md) for domain-specific layer
bridges. Do not duplicate those contracts here.

## Contents

- [Authority and purpose](#authority-and-purpose)
- [Synthesis procedure](#synthesis-procedure)
- [Stable bilingual section markers](#stable-bilingual-section-markers)
- [Common narrative contract](#common-narrative-contract)
- [Mode-specific narrative](#mode-specific-narrative)
- [Route logic and outcome interpretation](#route-logic-and-outcome-interpretation)
- [SOTA family synthesis](#sota-family-synthesis)
- [Citation transformation](#citation-transformation)
- [Callout semantics](#callout-semantics)
- [Writing standard](#writing-standard)
- [Completion gate](#completion-gate)

## Authority and purpose

Treat the manifest-declared primary report as the reader's decision surface.
Treat numbered artifacts as auditable working memory. A report is incomplete if
the reader must reconstruct the recommendation or audit verdict by opening the
evidence matrix, candidate cards, or red-team log.

**Compact summary, complete body.** The primary report must independently
explain the scientific question, essential concepts, key sources and their
relationships, judgment, route choice, validation, and outcome meaning.
Tables serve comparison and precise execution; they do not replace explanation.
Do not set minimum words, paragraphs, length or table ratios.

Use the new narrative envelope below for new reports. Keep a single primary
report with a navigable audit appendix, not a second competing human-version
truth. The existing `recommended-routes` short projection remains valid:
`Route | Summary | Disposition | Decision ID` (focus prepends `Role`).
A nonempty Summary is an index to a route's argument, not that argument itself.
The canonical working tables remain authoritative. The summary must say what is
currently credible, why it matters, what blocks progress, what to check first,
and which result changes the decision. Match IDs, dispositions, quantities,
units, thresholds, stages and gate status to those tables and decision records.
An independent semantic review checks this consistency; software does not prove
scientific validity from keywords. Historical reports with placeholders are
negative examples by default, not evidence of scientific correctness.
Apply the [quantitative decision sanity checks](critical-thinking.md#quantitative-decision-sanity)
to decision-critical formulas and thresholds before projecting them into the report.

For zero landscape or focus candidates use `Claim | Disposition | Decision ID` in the
decision summary and leave route cards/execution/outcome tables empty; report
the existing atomic-claim decisions and concrete reopening checks instead.
Zero eligible pilots is a different case: real candidate cards and conditional
medium-/long-term plans remain, while no fast pilot is proposed.

Write in the user's requested language. Select a Chinese or English report
template rather than changing language metadata while copying the same template.
Chinese reports may retain necessary English technical terms, paper titles,
equations, and standard abbreviations.

Lead with the decision. Preserve this causal invariant in recommendation reports:

    durable bottleneck x falsifiable causal/physical mechanism
    x transferable capability x bounded open position

## Synthesis procedure

Write the report only after the mode-required evidence, synthesis, adversarial
audit, and decision log are stable enough to support a disposition.

1. Recover the exact decision, reader, mode, discovery lens, primary and
   secondary domain lenses, scope, evidence window, capability boundary, parent
   lineage, and horizon from the manifest and intake.
2. Select only decision-critical claims and preserve their assessed scope,
   confidence cap, allowed wording, and limiting evidence.
3. Rebuild the causal progression in plain language. Use the general chain
   need or desired function -> state/observable -> bottleneck -> missing
   primitive -> mechanism -> implementation -> discriminating test. Apply the
   selected domain lens instead of forcing every field into an AI-device chain.
4. Pull the strongest baseline, competing hypothesis, hidden cost, kill
   criterion, and reversal condition from the adversarial audit.
5. Propagate every decision-critical Keep, Downgrade, Revise, or Kill
   disposition from the decision log.
6. Convert internal evidence IDs into ordinary numbered citations.
7. End with actions that resolve a decision, not a generic request for more
   literature.

## Stable bilingual section markers

New templates separate narrative sections from audit projections. These
markers delimit machine-readable regions, not a fixed number of human chapters.
Use natural headings and subheadings inside the argument as the decision needs.

| Mode | New section envelope, in order |
|---|---|
| landscape, focus | `decision-summary`, `scientific-argument`, `audit-appendix`, `references` |
| evidence-audit, run-audit | `decision-summary`, `audit-findings`, `audit-appendix`, `references` |

The writing progression is conclusion → necessary background/concepts →
existing methods and key papers → why the bottleneck remains → route selection
or rejection → validation → outcome meaning and next decision. It is a writing
logic, not a mandatory list of chapters. Landscape emphasizes direction
comparison; focus argues the selected interface; audits lead with adjudication
and exact repairs.

Place each route's explanation in `scientific-argument` after
`<!-- rom-route: C-001 -->`, followed by its natural-language heading and prose.
Use one such block per actual authoritative route; do not tag stages, comparison
designs or fallback actions as independent candidates. With no candidates use
no route blocks: explain the atomic-claim decisions and reopening checks.
Route blocks end at the next route or section marker.

Inside `audit-appendix` place each complete projection after
`<!-- rom-projection: NAME -->`. The required names are:

| Mode | Complete appendix projections |
|---|---|
| landscape | decision-summary, recommended-routes, execution, outcome-interpretation, evidence-confidence, bio-inspired-translation, red-team-impact |
| focus | recommended-routes, execution, outcome-interpretation, evidence-confidence, bio-inspired-translation, red-team-impact |
| evidence-audit | claim-verdicts, evidence-confidence, gap-plan, bio-inspired-audit, red-team-impact |
| run-audit | integrity, scientific-red-team, route-verdicts, bio-inspired-audit, red-team-impact |

Projection order within the appendix is free. Use exactly one continuous table
per projection with the existing registered headers and complete rows. Never
place a small comparison table before the required table inside that projection;
put it in the argument instead. The explicit projection marker prevents an
earlier narrative table from being parsed as the authority projection.
Unmarked tables in the main text are explanatory, never an ID-definition source.

The scope, concepts, necessity, approach-family comparison and bounded-open-position
requirements remain substantive narrative duties; their former fixed table
shapes are not required in the new envelope. All remaining source, confidence,
route ownership, red-team, gate and decision checks still apply. Keep readable
confidence levels, caps, capability unknowns, blocking gates and decisive
objections in the body. The appendix may carry full IDs, enumerations and
row-by-row details; it cannot be the only location of decisive counterevidence.

Give visible links to the argument, audit appendix and references; use meaningful
localized link labels. An ordinary expanded appendix is the default. Do not
use folding without checking the actual client rendering.

### Existing section-bound format

The older format below remains supported, including both wide and compact route
projections. Its exact section order is unchanged. The parser reads the first
continuous table in each section. Do not reorder its markers or insert a small
table before the required one. Do not rewrite sealed reports to adopt the new
layout; old readability does not require a per-release parser or run registry.

Place the exact machine-readable marker before the corresponding localized
heading. Validators inspect markers and artifact roles rather than guess from
Chinese or English keywords.

Example:

    <!-- rom-section: decision-summary -->
    ## 一页决策摘要

In the existing section-bound format, the exact marker set is mode-specific:

| Mode | Required markers in narrative order |
|---|---|
| `landscape` | `decision-summary`, `scope`, `background-question`, `necessity-timing`, `need-to-know`, `persistent-bottleneck`, `sota-families`, `bounded-open-position`, `bio-inspired-translation`, `recommended-routes`, `baseline-hypotheses`, `execution`, `outcome-interpretation`, `evidence-confidence`, `red-team-impact`, `reversal`, `references` |
| `focus` | `decision-summary`, `lineage`, `background-question`, `necessity-timing`, `need-to-know`, `sota-families`, `bounded-open-position`, `bio-inspired-translation`, `recommended-routes`, `baseline-hypotheses`, `execution`, `outcome-interpretation`, `evidence-confidence`, `red-team-impact`, `references` |
| `evidence-audit` | `decision-summary`, `audit-scope`, `claim-verdicts`, `evidence-confidence`, `supplemental-search`, `bio-inspired-audit`, `allowed-wording`, `gap-plan`, `decisions`, `red-team-impact`, `references` |
| `run-audit` | `decision-summary`, `audited-snapshot`, `integrity`, `scientific-red-team`, `capability-cross-scale`, `open-position-bio`, `bio-inspired-audit`, `route-verdicts`, `red-team-impact`, `remediation`, `residual-uncertainty`, `references` |

Chinese and English implementations use the same marker names but different
localized headings and prose. Headings may be made more descriptive, but the
marker, order, and semantic role must not change. A validator may require the
exact mode set; do not satisfy a missing section with a keyword in a comment or
fenced example.

## Common narrative contract

### One-page decision

State the current decision, confidence, most important reason, strongest reason
to reject it, immediate action, and reversal condition. For an audit, state the
highest-consequence finding and its disposition before describing the process.

Every report must also answer the same five reader questions in a mode-appropriate
form:

1. **What** decision, route, claim, or persisted run is being judged?
2. **Why** does that judgment matter now and what decision changes?
3. **Need to know**: which states, mechanisms, evidence criteria, boundaries, or
   integrity facts are necessary to judge it?
4. **How** will the route be tested, the claim adjudicated, or the run audited and
   repaired?
5. **What we learn**: what bounded conclusion and next decision follow from each
   relevant outcome or verdict?

### Scope and evidence boundary

State the reader, task mode, discovery lens, primary and secondary domain
lenses, parent run if any, evidence window and as-of date, databases and access
limits, operating regime, capability boundary, decision horizon, and explicit
exclusions. For `custom`, summarize the manifest's domain-lens boundary rather
than leaving its scientific contract hidden in metadata.

Every capability row needs a meaningful `Source or evidence` basis. Neither
`Observed` nor `Reported` may rest only on wording such as not yet verified,
unverified, unknown, assumed, learning only, planned only, or not documented.
A `Reported` capability may be unreplicated, but its actual report, record, or
source must be named.

### Background and key scientific question

For landscape and focus, explain the current background and the exact scientific
question without beginning from a preferred material, fashionable application,
or biological analogy. Distinguish the desired function, observable or state,
persistent bottleneck, and missing controllable primitive.

### Sufficiency, necessity, timeliness, and urgency

Answer four separate questions:

| Dimension | Required argument |
|---|---|
| Sufficiency | Is the question precise and causal enough that a result changes belief or action? |
| Necessity | Does solving it remove a consequential bottleneck rather than improve a proxy? |
| Timeliness | Which recent capability, evidence, benchmark, or constraint makes it answerable now? |
| Urgency | What decision, competitive window, platform dependency, or accumulating cost makes delay consequential? |

Include the strongest counterargument for each favorable judgment. Popularity,
venue prestige, and citation count cannot supply these arguments by themselves.

### What the reader needs to know

Define only the states, mechanisms, scales, equations, budgets, and metrics
needed to understand the decision. Define every symbol next to the equation and
connect it to a measurable or computable variable. Use the selected domain lens
to expose missing cross-layer bridges.

### Evidence and decisions

Keep Evidence, Inference, Recommendation, and Speculation visibly distinct.
Report claim confidence and active caps, not a paper-level quality score. A
search miss may be reported only with its databases, terminology, dates,
filters, languages, and access boundary.

### Visible adversarial impact

Every report must retain a complete `red-team-impact` projection (in the new
layout's audit appendix) with these exact columns:

| Attack ID | Target ID | Attack surface | Strongest objection | Severity | Verdict | Status | Exact repair | Decision ID |
|---|---|---|---|---|---|---|---|---|

Copy every attack into this audit projection, including attacks on
`B/M/S/CL` claims rather than only candidate routes; no non-`Keep` attack may be
omitted. The target, verdict, status,
repair, and Decision ID must remain consistent with the red-team and decision
artifacts. A disposition without the objection and exact repair is not visible
propagation. The linked decision row must distinguish its directly attacked
`Target ID` from its non-empty `Affected decision target IDs`. For each affected
decision target, the mode's main decision table must adopt the strongest verdict
across all linked attacks (`Kill > Revise > Downgrade > Keep`) and a Decision ID
that carries that verdict; the impact table cannot be a decorative appendix
beside a stale recommendation. Thus an attack on `M-###` may visibly revise a
`C-###` route without pretending that the route itself was the direct attack
target.
For `run-audit`, aggregate manifest-failure closure decisions with attack
decisions before selecting this maximum. If an integrity decision ties an attack
at the maximum rank, the route verdict binds an equally strong integrity
Decision ID.
Affected targets must be unique and mode-authoritative: landscape/focus use
defined `C-###` routes; evidence-audit uses locally defined atomic claims or
explicitly inherited claim IDs and its claim-register must exactly equal the
scope declared in `target-claims`; run-audit uses claim/route IDs recomputed from
the immutable parent snapshot. A run-audit may therefore adjudicate legacy
candidate IDs such as `C-L01`, `C-M01`, or `C-H01` when and only when that ID is
recomputed from the declared legacy parent. Evidence, decision, finding, or other audit-local
IDs cannot impersonate a main decision target.

The table must include at least one row for each of the eight registered
surfaces: `problem-adequacy`, `mechanism`, `evidence`,
`open-position`, `capability`, `cross-scale`,
`baseline-system-cost`, and `bio-inspired-translation`. Do not collapse
several surfaces into one generic “risk” row.

### Visible bio-inspired translation

Landscape and focus reports must contain `bio-inspired-translation`; both audit
reports must contain `bio-inspired-audit`. When biological reasoning is invoked,
show the complete chain:

    biological observation -> abstract computational principle
    -> mathematical operator/state-update rule -> algorithm -> hardware primitive
    -> de-biologized scientific question
    -> strongest same-budget non-biological baseline
    -> principle-specific ablation -> measurable intrinsic gain and boundary

Also state the scientific question after removing brain, neuron, synapse, and
biomimetic labels. `not applicable` is permitted only when no biological premise
or superiority claim affects the decision; give the reason explicitly. It may
not be used to bypass the chain in a bio-related run.

Treat a domain lens as scientific routing metadata, not as a biological claim.
A neuromorphic-system lens alone does not activate this gate. An actual
biological premise, biomimetic superiority argument, or bio-inspired mechanism
in the request, domain, or a mode-owned decision/claim surface does activate it.
A term confined to a capability inventory, retrieval queries, rejected-neighbor
notes, evidence support, or provenance logs does not activate the gate unless
the run promotes it into a
scientific premise, claim, or recommendation. Structural field names such as
`bio-inspired-translation` and `bio-inspired-audit` never activate the gate by
themselves.
Premise-bearing variants such as biologically inspired, biology-inspired,
neuromorphic computing, artificial neuron or artificial synapse, and neuro-,
neural-, immune-, retina-, nature-, neuron-, synapse-, or brain-inspired/like/
mimicking framing count as substantive biological claims. So do
biological-superiority, `人工神经元`, `人工突触`, `类脑`, neuronal/synaptic/
cortical/astrocytic/glial/dendritic/axonal computation, brain computation,
homeostatic plasticity, and metaplasticity. Unicode dash variants are normalized
before matching. Wording confined to capability inventory blocks, run-audit
`cross-scale-audit`, reader `capability-cross-scale`, or a custom
`Capability interface` slot remains non-premise unless promoted elsewhere.
Request/domain prose is suppressed only with an explicit capability-only
disclaimer in a sentence that contains no route, mechanism, scientific question,
advantage, investigation, or proposal. Wording variation cannot bypass the
gate. Generic uses of `neural` alone are not treated as biological-premise
evidence.


Recommendation reports use these exact translation columns:

| Biological observation | Abstract computational principle | Mathematical operator/state-update rule | Algorithm | Hardware primitive | De-biologized scientific question | Non-biological strong baseline | Principle-specific ablation | Measurable intrinsic gain and boundary |
|---|---|---|---|---|---|---|---|---|

Audit reports add `Target`, `Verdict`, and `Decision ID` around the same
scientific chain. Once a biological premise triggers the gate, an all-N/A row
is invalid: populate the links or issue a non-`Keep` verdict with an exact
repair. Only a genuinely non-biological run may use N/A throughout, with the
reason and ordinary-baseline boundary stated explicitly.
Every run, including a non-biological run, must reserve A-008 for the
`bio-inspired-translation` attack surface; swapping that ID with another surface
is invalid. The authoritative `red_team` row and reader audit must always match
A-008 on Target, Verdict, and Decision ID. When the bio gate is triggered, that
matched row must also contain the complete non-N/A chain. In `run-audit`, the
registered `reasoning_audit` row independently obeys the same unconditional
alignment and the same trigger-dependent completeness rule. Neither an extra
table in another artifact nor one valid owner may substitute for an incomplete
or mismatched authoritative owner. For recommendation runs, the working
translation owner is exactly `research_map` in landscape and
`claim_mechanism_map` in focus.

## Mode-specific narrative

### Landscape

Explain the root taxonomy, persistent bottleneck families, mechanism families,
SOTA approaches, bounded open interfaces, and comparative map. Present a
scope-appropriate portfolio only after the breadth gate. Retain zero, one, or
several substantive routes, never a risk quota. Show genuine alternatives and reuse of process, measurement,
modeling, or integration infrastructure.

Each finalist needs a decisive experiment, quantitative threshold, strongest
baseline, kill condition, one-year leverage, retained asset after failure, and
reversal condition.

Every `decision-summary` risk row owns exactly one `C-###`, occurs once, and
preserves the full `C-### -> low|medium|high` mapping from
`candidate-routes`.

### Focus

Do not recreate a broad portfolio. Explain why the selected branch survived a
local alternative search and present:

1. zero, one, or several substantive candidates, with one primary when nonempty;
2. the strongest comparison design, without requiring a separate candidate;
3. a fallback that preserves a useful scientific result or platform, using its
   activation rule rather than a fabricated C-ID.

State the parent lineage and inherited claims when applicable. Narrow every
claim to the selected regime. The report must include competing mechanisms,
discriminating controls, phase gates, and positive, negative, and ambiguous
interpretations.

Each reader `recommended-routes` row owns exactly one `C-###`, occurs once, and
preserves the full `C-### -> primary|comparator|fallback` mapping from working
`focus-routes`.

Show the exact bounded open position that survived the local search: positive
evidence on both sides, closest direct neighbors, adjacent terminology, search
and access boundary, and the still-unclosed falsifiable interface.

### Evidence audit

Organize the report around decision-critical claims, not routes. For each claim,
show scope, evidence roles, supporting and limiting evidence, confidence,
active cap, allowed wording, and the cheapest upgrade or overturn action.
Separate frontier salience from claim confidence.

`claim-confidence` contains at most one row per claim and exactly one for every
decision-critical claim. The evidence-audit target set appears exactly once in
each of `target-claims`, `claim-register`, canonical `claim-confidence`,
`confidence-assessment`, `allowed-wording`, and reader `claim-verdicts`.
Evidence-gap rows may be one-to-many, but every target needs at least one and no
gap may point outside the declared target set.

When a parent exists, state whether the parent decision should be kept,
downgraded, revised, or killed. Treat the report as a supplement unless an
explicit integration step is authorized.

Answer the audit form of the five questions: what claims are audited, why they
change the parent decision, what evidence roles and confidence constraints are
needed, how they were adjudicated, and what bounded wording or parent action now
follows. Do not invent a route merely to satisfy a recommendation-shaped report.

### Run audit

Lead with integrity and scientific verdicts. Cover manifest and lineage,
cross-artifact IDs and citations, claim-evidence-report consistency, causal
reasoning, capability inflation, bounded open-position language, cross-scale
claims, baselines, hidden costs, and reader-report consistency.

For every decision-critical finding, state Keep, Downgrade, Revise, or Kill,
the exact repair, its target artifact or claim, and the residual uncertainty.
Every `manifest-lineage-audit` repair must equal
`canonical_manifest_repair(Check, Result)`; `pass` and `not-applicable` rows
therefore use `retain observed state`. Every row uses exactly one valid `D-###`
that resolves to exactly one decision; `pass` and `not-applicable` bind `Keep`.
Each `Result=fail` row is `high` or `blocking` and owns a Decision ID used by no
other manifest row or attack. That ID resolves to exactly one non-`Keep` decision whose
Target ID and Affected decision target IDs are the same single authoritative
route/claim, whose Decision is exactly `Parent manifest failure [<check>]`, whose
Trigger Attack IDs is `not-applicable: deterministic manifest check`, and whose
Owner/next action is the canonical repair.

Reader Finding is exactly lowercase
`parent manifest failure [<check>]`. When failures exist, `integrity` contains
all and only those rows exactly once, with identical evidence, high/blocking
severity, bound verdict, canonical repair, and Decision ID. Use the single clean
`Keep` sentinel only when the recomputed failure set is empty. Aggregate these
integrity decisions, recomputed parent ID/citation-anomaly decisions, and attack
decisions in `route-verdicts`; apply
`Kill > Revise > Downgrade > Keep`, and bind an integrity Decision ID on an
equal-rank integrity/attack tie.

Every abnormal recomputed `id-closure` or `citation-closure` row binds a
substantive `Repair` and a non-`Keep` decision targeting and affecting the same
authoritative route/claim. A dedicated anomaly decision is unique among anomaly
rows and uses `Parent <marker> anomaly [<key>:<status>]`, trigger
`not-applicable: deterministic parent anomaly`, and Owner/next action equal to
`Repair`; its stable final finding is lowercase
`parent <marker> anomaly [<key>:<status>]`. It cannot reuse a manifest-failure
decision.

Sharing the same non-`Keep` attack decision is allowed as a joint disposition;
retain the attack decision's source, trigger, and owner rather than rewriting
it. Working and reader route verdicts are identical on target, strongest
finding, verdict, allowed conclusion, repair, and Decision ID. When a dedicated
anomaly decision is the selected maximum, both use its stable finding, exact
repair, and ID.
This includes an incomplete ten-slot `custom` domain lens in a schema-2 parent:
the child audit may describe the defect but may not hide or narratively soften it.
Do not force a literature portfolio or SOTA section when no new field claim is
being made.

Answer the audit form of the five questions: what immutable snapshot is audited,
why its defects matter to a live decision, what integrity and scientific facts
are needed, how each defect was reproduced and repaired, and what the audit
changes or leaves unresolved.

## Route logic and outcome interpretation

For each stage, state the baseline and controls, resource/input dependency,
measured quantity, operating interval, statistic, advance and stop/revise rule,
and retained asset. Classify quantitative thresholds as cited findings,
requirements, or proposed design choices. Sampling points are not independent
devices, batches or replications. Match task, input information, state/precision,
tuning budget, stopping rules and full cost boundary where comparisons permit.
An unreproduced comparator loses comparison eligibility; that does not establish
the target's superiority. Deferred routes still need an immediately useful
input-to-deliverable-to-gate next action, without implying experimental authority.

Use these questions to check each route's prose, not as a required output card:

| Question | Required answer |
|---|---|
| What | In plain language, what will be controlled, changed, built, or tested? |
| Why | Why is the problem sufficient, necessary, timely, and decision-relevant? |
| Need to know | Which state, mechanism, metric, regime, and baseline must be understood first? |
| How | What existing capability is reused, what new method is introduced, what is measured, and with which controls? |
| What we learn | Which bounded conclusion follows from positive, negative, and ambiguous results? |

The recommended-routes table contains exactly one compact summary row for every
authoritative route and no extra route. The primary report itself retains the five questions, baseline, competing
hypotheses, three outcomes, kill criterion, retained asset and reversal condition
for that route. The working tables verify this argument; they cannot supply
explanations missing from it. Explain why the evidence warrants the choice, its
strongest alternative explanation, how controls distinguish the alternatives,
and what success or failure changes. Avoid generic one-sentence summaries.
The older wide projection remains readable, but is not the default authoring
template. Compact rows keep disposition and Decision ID; focus also keeps role.

The working focus protocol must give every actual candidate one route-boundaries
row containing its kill criterion,
reversal condition, retained value after failure, and exact comparator or
fallback activation rule. Global boundary prose cannot stand in for per-route
ownership.

Both the `execution` and `outcome-interpretation` audit projections use `Route` as the
first column. Give every recommended route an owned execution row and separate
positive, negative, and ambiguous rows; do not collapse a multi-route report
into one unassigned protocol or outcome tree.

Ownership must agree with the authoritative working route set: all landscape
`candidate-routes` and all focus `local-alternatives`/`focus-routes` must
appear. Focus must also give those same route IDs owned
`staged-execution` rows and owned working positive/negative/ambiguous rows
before the reader projection is written.

Outcome branches must be decision-bearing:

- Positive: state which mechanism or route gains support and what remains
  unproven.
- Negative: distinguish mechanism falsification from implementation failure and
  state whether to revise or kill.
- Ambiguous: identify the confounded hypotheses and the smallest discriminating
  control or search.

## SOTA family synthesis

Landscape and focus reports compare approach families in connected prose.
Explain the mechanism of each relevant family, what its key papers established,
how families agree or differ, and why those results leave the claimed bottleneck
open. A concise comparison table can help; the following fields are a reasoning
checklist, not a required seven-column table in the new narrative layout:

| Approach family | Core idea | Best demonstrated regime | Enabling assumption | Strongest evidence | Unresolved failure mode | Why the persistent bottleneck remains |
|---|---|---|---|---|---|---|

Use recent influential work to sense the frontier, then rely on responsive
primary evidence, direct neighbors, baselines, and limitations to judge claims.
Do not imply that a highly cited or top-venue source is more causally credible
without method-responsive evidence.

## Citation transformation

Keep detailed provenance in the evidence artifact. In the primary report:

- Cite claims as [1], [2], or [3-5].
- Give a numbered reference list with verified title, venue, year, and DOI or
  stable link.
- Outside `run-audit`, require two-way closure between every non-sentinel
  evidence `Reader ref` and the numbered reference list: no orphan on either
  side, one evidence row per number, and the same normalized DOI/stable link.
- In `run-audit`, close the audit report's own numbered references against its
  body and keep the recomputed parent citation projection separate.
- Keep document IDs, chunk IDs, offsets, and retrieval traces out of the
  reader narrative.
- Do not present paraphrase as a verbatim quotation.
- Do not use a search miss as proof of absence or priority.

Discuss decision-critical sources where they enter the argument: what was
actually demonstrated, which report judgment is supported or limited, and where
the result cannot transfer. Relate sources to one another (support, refinement,
contradiction under matched conditions, or different regimes). Do not turn every
reference into an identical card or a flat paper list. Ordinary prose is the
default; this bilingual source block is an optional example:

> [!NOTE]
> **文献依据 / Evidence [1]：Author, title, venue (year).** DOI or stable link
>
> **核心贡献 / Core contribution:** What the source actually demonstrated.
>
> **印证观点 / Supports:** The exact bounded report claim it supports.
>
> **边界 / Boundary:** What it did not establish and the conditions that limit transfer.

## Callout semantics

| Callout | Use |
|---|---|
| IMPORTANT | Primary decision, audit verdict, or non-negotiable epistemic condition |
| NOTE | Literature evidence or a concept boundary |
| TIP | Actionable experiment, search, or platform advice |
| CAUTION | Confound, dependency, hidden cost, or interpretation limit |
| WARNING | Unsupported priority claim, kill condition, or high-consequence risk |

Use at least one decision callout, one evidence callout when external evidence
is used, and one limitation or risk callout. Do not use callouts decoratively.

## Writing standard

- Lead with the outcome, then develop the scientific argument.
- In Chinese reports use natural Chinese; explain necessary technical terms on
  first use. Keep internal enums and IDs at genuine traceability points.
- Explain symbols next to formulas, preserve units and applicable regimes, and
  inspect damaged escapes, truncated cells and horizontal reading burden. Move
  long relations into display math when inline fractions or subscripts become
  difficult to read in the actual preview.
- Give each piece of information a primary location. The summary states the
  decision; route prose explains it; execution specifies controls; the appendix
  supplies exact projections. Use links instead of repeating complete protocols.
- Preserve source-specific reproduction blockers and decisive counterexamples.
  A generic phrase such as “fair comparison” or “same normalization” cannot
  replace a known metric-definition discrepancy, unresolved printed formula or
  counterexample that changes the decision.
- Distinguish missing explanation from an unresolved scientific or planning
  choice. Name unresolved task/baseline selection, statistical applicability,
  stage dependencies or timing without inventing a resolution to smooth prose.
- Maintain completeness without word, paragraph, page or table-ratio quotas.
- Explain why each causal layer follows from the previous layer.
- Use bounded language and the allowed wording from the confidence assessment.
- Define unfamiliar cross-domain terms at first use.
- Compare complete systems only when the necessary layer bridges are evidenced.
- Preserve negative results, rejected routes, and audit downgrades when they
  change the decision.
- Keep the main narrative free of internal IDs unless an ID materially helps an
  audit reader.
- Do not concatenate working artifacts.

## Completion gate

Do not deliver the primary report until it:

- is the exact manifest-declared primary artifact and contains no placeholders;
- uses the required rom-section markers for its task mode;
- can be understood without opening working artifacts;
- states scope, evidence window, boundaries, confidence, and reversal conditions;
- follows the correct mode contract: landscape portfolio, focused route set,
  claim verdicts, or run-audit dispositions;
- includes the five-question route logic and three outcome branches whenever a
  route is recommended;
- gives every landscape/focus route readable validation/outcome reasoning and
  exact execution ownership plus positive, negative, and ambiguous audit rows;
- includes the SOTA family and residual-bottleneck analysis for landscape and
  focus;
- retains every attack in the exact `red-team-impact` projection, especially every
  non-`Keep` attack, with its
  target, objection, severity, status, repair, and Decision ID;
- shows all eight registered attack surfaces and propagates the strongest
  target-level verdict into the main mode decision rather than only the impact
  table;
- for `run-audit`, uses canonical manifest repairs, high/blocking failure
  severity, one distinct non-attack decision per failed check, the exact reader
  Finding projection, and a clean sentinel only when no failures exist;
- for `run-audit`, ranks manifest-failure decisions together with attacks in the
  final route disposition and binds an integrity Decision ID whenever integrity
  ties at the maximum rank;
- retains the applicable bio-inspired translation/audit projection and permits
  `not applicable` only with a reason in a genuinely non-biological run;
- keeps the mathematical operator/state update, algorithm, hardware primitive,
  and de-biologized scientific question as separate bio-translation fields,
  and never uses an all-N/A chain after the bio gate is triggered;
- traces every decision-critical external source with contribution, support,
  boundary, and an ordinary numbered citation;
- remains consistent with confidence caps, the adversarial audit, and the
  decision log;
- contains no internal retrieval identifiers or unbounded absence claims.

Validation may prove structural consistency. It cannot establish novelty,
scientific truth, experimental feasibility, or the correctness of a decision.

### Reader comprehension gate

After structural validation, read the main narrative without opening the working
artifacts. For each recommendation, or the corresponding audit judgment, answer:

- What scientific problem is being decided?
- Why is it worth considering under the stated constraints?
- Which key papers support or limit which judgments, and how do they relate?
- Why choose or reject this route relative to its strongest alternative?
- What can be done now, and which evidence or capability is still missing?
- Which positive, negative or ambiguous result changes the decision, and how?

Locate each answer in the body. If an answer can only be recovered from audit
cells, IDs or a work file, repair that explanation. When independent reading is
available and authorized, use a reader unaware of the drafting history; judge
their actual answers and omissions, not length or a fluency preference.

Check the same facts against the authoritative artifacts: sources and key
counterevidence, confidence/caps, capability state, three gates and deterministic
Overall, route/stage/comparator relationships, thresholds and applicability,
stop rules, dispositions and Decision IDs. Record unresolved semantic or render
issues with the existing validation/decision notes, without creating a second
scientific truth. The parser checks prose presence and ownership only; a generic
paragraph can pass it and still fail this comprehension gate.

Preview a representative localized report in the intended available client.
Check formula symbols/escaping, table widths and row endings, appendix links and
return navigation. If no preview is available, state that rendering is unverified.
