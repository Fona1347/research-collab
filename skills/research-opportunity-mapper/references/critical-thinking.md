# Critical-Thinking and Adversarial Audit Protocol

Use this protocol to attack a claim, route, portfolio, or persisted run before
delivery. Select mode obligations with [run-modes.md](run-modes.md), apply
claim-level caps from [evidence-confidence.md](evidence-confidence.md), and
instantiate domain-specific confounds and layer bridges with
[domain-lenses.md](domain-lenses.md). Do not duplicate those contracts here.

## Contents

- [Invariant and epistemic labels](#invariant-and-epistemic-labels)
- [Finding record and dispositions](#finding-record-and-dispositions)
- [Eight mandatory attack surfaces](#eight-mandatory-attack-surfaces)
- [Alternative-explanation test](#alternative-explanation-test)
- [Baseline ladder](#baseline-ladder)
- [Outcome interpretation and kill criteria](#outcome-interpretation-and-kill-criteria)
- [Quantitative decision sanity](#quantitative-decision-sanity)
- [Decision propagation](#decision-propagation)
- [Mode-specific application](#mode-specific-application)
- [Recommendation rule](#recommendation-rule)

## Invariant and epistemic labels

The audit protects this intersection:

    durable bottleneck x falsifiable causal/physical mechanism
    x transferable capability x bounded open position

Use these labels consistently:

- **Evidence**: directly supported by a cited source or observed laboratory
  fact inside a stated boundary.
- **Inference**: derived from evidence or a model; expose the reasoning and
  uncertainty.
- **Recommendation**: a choice under explicit objectives and constraints.
- **Speculation**: a plausible search or experiment lead with insufficient
  decision support.

Do not let recommendation language masquerade as Evidence. Do not treat an
adversarial objection as established fact without evidence or a discriminating
test.

## Finding record and dispositions

Create one row for every substantive attack:

| Finding ID | Target claim, route, or decision ID | Attack surface | Strongest objection | Evidence or test | Severity | Disposition | Exact repair | Decision ID | Status |
|---|---|---|---|---|---|---|---|---|---|

Use exactly one decision effect:

- **Keep**: the conclusion survives within its existing boundary.
- **Downgrade**: retain it with lower confidence or narrower allowed wording.
- **Revise**: change the question, route, experiment, mechanism, baseline,
  scope, or evidence plan.
- **Kill**: stop recommending it under the current decision conditions.

Keep is not a default. It requires the attack to be answered by responsive
evidence, an existing control, or an already-correct boundary. A critical or
high-severity unresolved objection cannot end as Keep.

Use only `low`, `medium`, `high`, or `blocking` for severity. Use only `open`,
`unresolved`, `accepted`, `mitigated`, `resolved`, or `closed` for status.
`open`, `unresolved`, and `accepted` remain unresolved for decision gating; an
unresolved `high` or `blocking` attack cannot receive `Keep`.

## Eight mandatory attack surfaces

Every run must contain at least one structured attack row for each of the eight
registered surfaces below. If biology is genuinely out of scope, retain the
`bio-inspired-translation` row with an explicit not-applicable rationale and a
matched non-biological baseline boundary; do not omit the surface. Additional
attacks are allowed, but invented surface keys are not. Every attack row,
including `Keep`, must be copied to the reader-facing impact table. Every
non-`Keep` row must also alter the affected main route/claim decision,
confidence or allowed wording, or explicit parent impact.

### 1. Problem adequacy

Attack the problem before its proposed solution.

- **Sufficiency**: Is the question precise and causal enough that a positive,
  negative, or ambiguous result changes belief or action?
- **Necessity**: Does the question address a consequential bottleneck, or only
  improve a convenient proxy or fashionable benchmark?
- **Timeliness**: Which new capability, evidence, benchmark, or constraint makes
  the question answerable now?
- **Urgency**: What decision, platform dependency, competitive window, or
  accumulating cost makes delay consequential?
- Does the bottleneck survive plausible improvements in the strongest
  conventional route?
- Is the apparent problem manufactured by a narrow metric, operating regime,
  terminology choice, or omitted budget?

Popularity, top-venue attention, citation count, and biological importance do
not establish adequacy.

### 2. Causal mechanism and independent control

- What state variable changes, what controls it, and what is read out?
- What governing equation, causal path, or kinetic model links control to
  observable?
- What is the null hypothesis?
- Which credible alternative mechanisms produce the same observable?
- Are claimed control axes independent, or merely correlated access to the same
  state?
- What intervention, ablation, or discriminating signature separates the
  preferred mechanism from alternatives?
- Can the result distinguish mechanism failure from implementation failure?

An attractive curve or image is not decisive when several mechanisms predict
it.

### 3. Evidence integrity and confidence

- Is the atomic claim narrower or broader than the responsive evidence?
- Was the relevant full context, method, figure, table, or supplement checked?
- Can the method answer the claim and exclude important confounds?
- Are evidence chains independent across group, sample, device, batch, seed,
  dataset, and upstream model?
- Are negative, mixed, and contradictory sources represented?
- Does evidence apply to the target material, geometry, regime, scale, budget,
  and measurement?
- Were venue prestige, recency, or citations improperly used as credibility?
- Does the assessed confidence obey every hard cap and allowed wording rule?

Apply the normative confidence rules in evidence-confidence.md. The red team
may challenge a score but must not silently invent a different scoring system.

### 4. Bounded open position and crowding

- Are there direct neighbors with the same mechanism, operation, regime, and
  comparator?
- Were synonyms, adjacent modules, authors, citations, conferences, preprints,
  patents, and neighboring fields searched where relevant?
- Is the claimed distinction causal and experimentally consequential, or only a
  material substitution or renamed application?
- Are positive problem evidence and positive enabling evidence both present?
- Is a zero-result query being converted into novelty, priority, or absence?
- Would the open-position statement remain meaningful after removing first,
  novel, and the application label?

Classify the result as crowded, active but open, sparse evidence, or unsearched.
State the search boundary and nearest matches.

### 5. Capability and operational feasibility

- Which capability facts are Observed, Reported, Assumed, or Unknown?
- Which process, model, sample, instrument, measurement, packaging, and
  integration modules transfer unchanged?
- Which new module or collaborator lies on the critical path?
- Are planned training, documentation, adjacent experience, or hoped-for access
  being presented as mature capability?
- Can the decisive test avoid the hardest dependency?
- Are lead time, procurement, safety, fabrication tolerance, calibration, and
  data requirements compatible with the decision horizon?
- If the flagship route fails, which verified capability or reusable asset
  remains?

An assumed capability caps route confidence until verified or designed around.

### 6. Cross-scale and translation validity

- What is the last directly validated layer?
- Which bridges to material, model, device, cell, array, circuit,
  architecture, workload, fabrication, or measurement are validated, modeled,
  assumed, or missing?
- Is a simulation being presented as experimental existence?
- Is a material or device proxy being promoted to reliability, array, chip, or
  system value?
- Do ideal-device, periodic-unit-cell, zero-parasitic, or perfect-calibration
  assumptions carry the conclusion?
- Does the proposed value survive variability, finite size, PVT, yield,
  interconnect, control, and measurement?

Cap the conclusion at the last evidenced layer. Use domain-lenses.md to select
the required bridge and cheapest decisive validation.

### 7. Strongest baseline and complete cost

- What is the cheapest credible conventional solution?
- What is the strongest alternative mechanism under a matched regime?
- Are task, precision, accuracy, sample hierarchy, tuning effort, data split,
  aperture, bandwidth, area, latency, energy, calibration, and reliability
  budgets matched where applicable?
- Are conversion, drivers, sensing, refresh, communication, training,
  redundancy, packaging, fabrication, and control costs included?
- Has the proposed method received more parameters, state dimensions, training,
  measurement access, or expert tuning than the baseline?
- Does the local gain survive the next integration layer and an adverse
  sensitivity case?

Do not compare a complete proposed device with an intentionally weak baseline,
or an isolated physical effect with an end-to-end conventional system.

### 8. Bio-inspired translation and prior assumptions

When biology is invoked, require this chain:

    biological observation
    -> abstract functional or computational principle
    -> scientific question without biological labels
    -> mathematical operator or state-update rule
    -> algorithm
    -> hardware primitive
    -> strong non-biomimetic baseline
    -> principle-specific ablation
    -> measurable intrinsic gain and boundary

Attack each link:

- Does the scientific question remain meaningful after biological language is
  removed?
- Is full biological imitation necessary, or is a smaller abstract principle
  sufficient?
- Can a conventional algorithm or control strategy reproduce the gain?
- Does the ablation isolate the claimed principle?
- Is the apparent benefit explained by more parameters, tuning, training,
  hidden software, or hardware complexity?
- Which metric and operating regime show an intrinsic gain after equal-budget
  comparison?

Brain function, synapse-like curves, hysteresis, or biomimetic terminology do
not establish computational or hardware superiority.

The bio gate is triggered when a biological observation, analogy, label,
superiority premise, or claimed biological function affects the question or
route on a mode-owned decision/claim surface. Capability inventories, retrieval
queries, rejected-neighbor notes, evidence support, and provenance logs do not
trigger it unless that idea
is promoted into a scientific premise, claim, or recommendation. Semantic
variants include biologically/biology-inspired claims; neuromorphic computing;
artificial-neuron or artificial-synapse framing; neuro-, neural-, immune-,
retina-, nature-, neuron-, synapse-, or brain-inspired/like/mimicking framing;
neuronal, synaptic, cortical, astrocytic/glial, dendritic, or axonal computation;
brain-computation superiority; homeostatic plasticity; metaplasticity; and
corresponding Chinese terms such as `人工神经元`, `人工突触`, and `类脑`. Unicode
dash variants are normalized before matching; do not rely only on ASCII
`bio-inspired` keywords. Capability-only text in capability/cross-scale blocks
and the custom `Capability interface` slot is non-premise. Unstructured
request/domain metadata is excluded only when the same sentence explicitly says
it is capability/inventory context rather than a scientific premise and contains
no route, mechanism, question, advantage, investigation, or proposal. Once
triggered, the translation record may not be wholly
`not applicable`; populate every link or issue `Revise`/`Kill` with the
missing-link repair. Only a genuinely non-biological run may use an all-N/A
translation row, and it must state why the gate is irrelevant plus the boundary
of the strongest ordinary baseline. A-008 owns the bio-translation attack
surface even when the gate is not triggered, and its Target, Verdict, and
Decision ID must always align across the attack, registered audit owner, and
reader. Chain completeness is additionally required when the gate is triggered.
Landscape reads the working translation only from `research_map`, focus only
from `claim_mechanism_map`, and audit rows only from their registered owners.

## Alternative-explanation test

For every decisive observable, create:

| Observable | Preferred mechanism | Strongest alternative | Discriminating control | Expected signatures | Positive interpretation | Negative interpretation | Ambiguous interpretation | Decision rule |
|---|---|---|---|---|---|---|---|---|

The control must generate different expected signatures under competing
hypotheses. If all hypotheses predict the same result, the proposed experiment
is descriptive rather than decisive.

## Baseline ladder

Instantiate the ladder with the selected domain lens:

1. physical or methodological null;
2. same implementation with the proposed control or principle disabled;
3. strongest alternative mechanism or established local method;
4. strongest practical next-layer implementation under matched assumptions;
5. end-to-end same-budget baseline when system or application value is claimed.

State which level is feasible now, which belongs to a later platform stage, and
where the claim must stop if a bridge is missing.

## Outcome interpretation and kill criteria

Every decisive test for every recommended route must define:

- **Positive**: which causal link gains support, the quantitative threshold,
  and what remains unproven.
- **Negative**: whether it falsifies the mechanism, exposes implementation
  failure, triggers a fallback, or kills the route.
- **Ambiguous**: which hypotheses remain confounded and the smallest next
  control that can separate them.

Kill criteria must be quantitative where possible and tied to the causal claim.
Each criterion needs a threshold, earliest test, consequence, and retained
asset. Do not use “performance is poor” without a metric and decision effect.

Examples include:

- the proposed control axis is not independent within measurement uncertainty;
- the state or response cannot reach the task-relevant regime;
- a simpler mechanism explains the observable;
- variability, calibration, loss, or peripheral cost removes the matched-budget
  advantage;
- a direct neighbor already closes the claimed interface more strongly;
- a critical dependency is unavailable and no scientifically valid fallback
  exists.

## Quantitative decision sanity

Before a numerical rule changes a decision, check the following where relevant
within the existing attack and decision records; do not add another gate or table.

- Expand shared symbol definitions into each decision-critical equation. Check
  units, encoding, duplicated terms, attainable bounds and limiting cases across
  the mechanism, protocol and reader report. Define improvement ratios so their
  direction is unambiguous. Do not lower a threshold merely to make it pass.
- Freeze measurement-based normalization for mixed-output metrics; test whether
  changing units or nearly zero responses changes the verdict. Require identifiable
  signal and uncertainty, not a favorable dimensionless score alone.
- Apply each threshold to its stated task, workpoint and evidence layer. A proxy,
  local transition rule or aggregate terminal measurement does not by itself prove
  a target distribution, causal origin or spatial localization; name the missing
  bridge or narrow the claim. Registration accuracy is not spatial resolution.
- For the same stage and valid observation, advance, stop and ambiguous rules must
  not conflict. Separate a valid subthreshold result from missing/invalid data or
  an interval crossing the threshold; bound any follow-up and its final decision.
- Bind necessary resources to the actual stage and branch: distinguish AND from
  OR dependencies, check fallback access independently, and define what substitute
  data must contain. An untested or inaccessible branch is not a scientific failure.
- State the error denominator, independent sampling unit and uncertainty before
  using small-sample screening as a performance guarantee. Many points or cycles
  cannot replace independent devices/batches or evidence of out-of-sample validity.

These are scientific review responsibilities, not claims that the structural
validator can establish mathematical or experimental validity.

## Decision propagation

A red-team section is not complete when it merely lists risks.

1. Link every decision-critical finding to a directly attacked claim, route, or
   prior decision as `Target ID`.
2. Name at least one `Affected decision target ID`: the defined or inherited
   route/claim whose main-mode disposition the finding must actually change.
   A subclaim attack may affect several route decisions.
   The target must be unique and mode-authoritative: a defined candidate route
   for landscape/focus; a local atomic or explicitly inherited claim for
   evidence-audit whose audited set exactly matches `target-claims`; and a
   claim/route recomputed from the immutable parent for run-audit. The latter
   includes legacy `C-L##`, `C-M##`, and `C-H##` candidate forms only inside a
   run-audit whose parent projection actually contains them. Do not promote an evidence, attack, decision, finding, or local
   audit-helper ID into the main decision surface.
3. Assign Keep, Downgrade, Revise, or Kill.
4. Record the evidence, confidence effect, allowed-wording change, exact
   repair, direct target, and affected decision targets in the decision log.
5. Update the candidate, route protocol, or confidence assessment in the child
   run; do not silently rewrite an immutable parent.
6. Propagate the disposition and residual uncertainty into the primary report.
7. Preserve rejected and superseded positions so the change remains auditable.
8. Copy every attack into the exact reader-facing impact table, including claim
   attacks that do not target a route.
9. For each affected decision target, aggregate every linked attack and update
   the mode's main decision surface to the strongest binding verdict in the order
   `Kill > Revise > Downgrade > Keep`; a side-table verdict beside an unchanged
   recommendation is failed propagation.

If several findings affect the same main decision target, the strictest linked
disposition governs, whether or not that ID was the direct object of every
attack. A later Keep requires new evidence or a documented resolution, not
simple disagreement with the red team.

## Mode-specific application

### Landscape

Attack all finalists and at least one initially attractive branch before the
scope-appropriate portfolio is fixed. Test whether candidates are substantive
alternatives rather than stages of one route; risk tiers are not quotas. With
no candidates, use existing decision-critical atomic claims for rejection and
red-team closure. Share a platform where genuinely useful. Do not force a rejection,
but require every surviving route to earn Keep. Give each finalist owned
execution fields and owned positive, negative, and ambiguous outcome
interpretations in the working route artifact and primary report.

### Focus

Concentrate attacks on the actual routes and their strongest comparator/fallback designs,
competing mechanisms, decisive controls, phase gates, and three outcome
branches. Apply local rather than global breadth. Every substantive candidate
owns its execution and positive, negative, and ambiguous results. A comparator
or fallback need not be a separate candidate. If all candidates are rejected,
close the atomic-claim decisions and bounded next information check instead.

### Evidence audit

Attack each decision-critical claim's scope, evidence roles, method validity,
independence, applicability, conflict handling, confidence cap, and allowed
wording. The disposition changes the claim or parent decision, not an artificial
route portfolio.

### Run audit

Apply all eight surfaces plus manifest, lineage, cross-artifact ID, DOI,
citation, report, and decision-log integrity. Every decision-critical finding
must propagate to the audit report and remediation plan.

## Recommendation rule

For landscape and focus, compare the selected pilots and their order with the
stated route preference and its sensitivity conditions. If they differ, explain
the changed evidence or constraint in the existing decision record; eligibility
and contiguous rank numbers alone do not justify the choice. Do not invent a
fixed score or ranking formula.

Recommend or keep a route only when:

- the problem is sufficient, necessary, timely, and consequential within a
  stated regime;
- the bottleneck is evidenced and plausibly durable;
- the mechanism exposes a falsifiable unknown with a discriminating test;
- capability is observed or bounded by an executable verification plan;
- direct neighbors leave a bounded unresolved interface;
- the strongest alternative and complete-cost baseline do not erase the value;
- cross-scale claims stop at the last validated bridge;
- positive, negative, and ambiguous results all lead to an explicit decision;
- failure retains interpretable knowledge or reusable infrastructure.

When any condition fails, Downgrade, Revise, or Kill. Preserve uncertainty rather
than forcing a recommendation.
