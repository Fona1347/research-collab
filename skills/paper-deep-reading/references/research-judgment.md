# Research Judgment Contract (v1)

Use this reference when a deep-reading run must judge originality, transferable research value, perspective shifts, the necessity or sufficiency of a central design choice, or functionally equivalent alternatives. Keep retrieval and permission routing in `SKILL.md`, claim/source/evidence ownership in `evidence-kernel.md`, and reader-facing assembly in `report-contract.md`.

## Contents

- [Purpose and triggers](#purpose-and-triggers)
- [Canonical ownership](#canonical-ownership)
- [Novelty, generativity, and perspective](#novelty-generativity-and-perspective)
- [Design necessity and counterfactual alternatives](#design-necessity-and-counterfactual-alternatives)
- [External-validation roles](#external-validation-roles)
- [Gate integration](#gate-integration)
- [Reader-facing contract](#reader-facing-contract)
- [Cross-domain abstraction](#cross-domain-abstraction)

## Purpose and triggers

Research judgment is a layer above paper summary. It asks two different questions:

1. What is the smallest genuinely new and transferable knowledge unit, and what research can it generate?
2. Which function does a named material, layer, module, architecture, assay, or algorithmic component provide, and has the paper shown that this implementation is necessary, sufficient, or superior to alternatives?

For every `full-report`, perform a compact trigger scan. Create the applicable registry when at least one trigger is present:

| Module | Trigger |
| --- | --- |
| Novelty-Generativity-Perspective (`N-*`) | The paper or user raises novelty, priority, platform, paradigm, originality, research inspiration, transferable ideas, or a material reframing of the field problem |
| Design Necessity and Counterfactual Alternatives (`D-*`) | A central conclusion depends on a named design choice, the paper contrasts a baseline, the user asks “why this rather than that,” or necessity, sufficiency, uniqueness, superiority, or alternative mechanisms matter |

For a focused analysis, run only the requested or materially implicated module. If neither module applies, record the trigger scan as `not-applicable` in the structured analysis; do not create empty decorative tables.

The main paper can support an internal design interpretation, but it cannot by itself establish field-wide priority, the non-existence of alternatives, or broad superiority unless its comparison evidence genuinely covers those propositions. When external validation is prohibited, keep those judgments explicitly unresolved.

## Canonical ownership

Keep both registries in `reading-report.md`, after the Claim and Condition Registry. They are conditional canonical analysis, not new standalone artifacts:

- use `N-001`, `N-002`, and so on for Novelty-Generativity-Perspective rows;
- use `D-001`, `D-002`, and so on for Design Necessity and Counterfactual rows;
- assign an ID once and do not renumber it after weakening or exclusion;
- link every row to the relevant `C-*` Claim IDs and, when external validation runs, the relevant `E-*` Evidence IDs;
- use `none`, `not-applicable`, `unknown`, or `blocked: <reason>` rather than blanks;
- correct these canonical rows before refreshing `research-translation-matrix.md`, `review-matrix.md`, `view-report-audit.md`, or `view-report.md`.

The registries own report-side research judgments. They do not replace the Claim Registry, Source Registry, or Evidence Ledger and must not restate source lifecycle fields.

## Novelty, generativity, and perspective

### Analysis sequence

Apply this sequence rather than asking only whether the paper is “innovative”:

1. Identify the nearest baseline or prior-art family.
2. Decompose the contribution into the smallest atomic delta relative to that baseline.
3. Classify the novelty type.
4. Separate paper-internal distinctiveness from externally verified priority.
5. Remove paper-specific material and implementation nouns to state a transferable abstraction.
6. Derive a falsifiable follow-up direction with a minimum decisive test and failure criterion.
7. State any perspective shift as an old framing, new framing, newly visible design space, and boundary.

Maintain this normative table when the module is triggered:

| Idea ID | Candidate idea | Closest baseline or prior art | Atomic delta | Novelty type | Claim IDs | Evidence IDs | Transferable abstraction | Generative direction and decisive test | Perspective shift | Boundary | Judgment |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use one or more of these novelty types, but identify the primary type:

- `conceptual`: a new principle or problem formulation;
- `mechanistic`: a new causal or physical explanation supported by discriminating evidence;
- `architectural`: a new arrangement or control topology;
- `methodological`: a new experimental, analytical, fabrication, or computational procedure;
- `integrative`: known elements jointly produce a capability not previously established;
- `performance`: a record or material metric gain without a new governing principle;
- `reframing`: a change in the field's controlling variable, evaluation target, or problem definition.

Use one scoped judgment:

- `high-conceptual`;
- `high-mechanistic`;
- `high-architectural`;
- `high-integrative`;
- `incremental`;
- `performance-only`;
- `internally-distinctive; external-priority-not-established`;
- `not-established-within-scope`;
- `blocked: <reason>`.

Do not award a high-originality label because the paper uses a new material name, reports a large metric, or combines several familiar components. State the atomic delta and the nearest baseline that make the judgment meaningful.

### Generative-direction rule

An “inspiring future direction” must contain all of the following:

| Field | Required content |
| --- | --- |
| Premise | The established paper claim or bounded external evidence from which the direction follows |
| Testable hypothesis | A proposition that can fail |
| Minimum decisive test | The smallest experiment, analysis, simulation, or ablation that distinguishes the hypothesis |
| Success and failure observables | What result supports the route and what result closes or redirects it |
| Applicability boundary | Material, device, population, task, scale, environment, or assumption that limits transfer |
| Epistemic label | `evidence-grounded inference`, `speculative direction`, or `blocked` |

Do not treat a list of substitute materials, datasets, or application areas as research generation unless it specifies why the transfer should work and how it would be falsified.

### Perspective rule

Represent a perspective shift in this compact form:

```text
old framing -> new framing -> newly visible design space -> applicability boundary
```

A result summary is not automatically a perspective. A perspective must change how the problem, controlling variable, design space, or evaluation criterion is understood.

## Design necessity and counterfactual alternatives

### Function-first decomposition

Do not begin with the named implementation. First rewrite it as the set of functions required by the target claim:

```text
target system outcome
-> required functions and constraints
-> minimum baseline capability
-> named implementation
-> functionally equivalent alternatives
-> discriminating controls and matched comparison
```

Maintain this normative table when the module is triggered:

| Design ID | Named design choice | Target function and constraints | Minimum baseline | Baseline failure mode | Necessity judgment | Sufficiency scope | Joint dependencies | Alternatives and counterexamples | Discriminating control or matched comparison | Claim IDs | Evidence IDs | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

### Necessity classes

State which meaning of “necessary” is being assessed:

- `physical necessity`: without the underlying physical or logical condition, the target outcome cannot occur in principle;
- `architectural necessity`: the component is required inside the paper's stated topology, although another topology may realize the function;
- `practical necessity`: alternatives may work in principle but fail a stated combination of voltage, speed, retention, scaling, compatibility, cost, safety, or another operating constraint;
- `evidential necessity`: the paper has supplied controls that rule out the relevant alternative explanation or implementation.

Demonstrated feasibility does not establish any of these necessity classes by itself.

### Sufficiency scopes

State the scope of the sufficiency claim:

- `component sufficiency`: the named component alone supplies the claimed function;
- `joint sufficiency`: the function appears only with specified interfaces, contacts, bias history, preprocessing, model components, measurement choices, or other dependencies;
- `system sufficiency`: the complete implementation supports the claimed device, circuit, workflow, population-level, or task-level outcome under stated conditions.

Do not promote joint sufficiency to component sufficiency. Preserve every dependency that changes the conclusion.

### Baselines, alternatives, and verdicts

For the minimum baseline, record what it already achieves and the exact missing function. Classify a failure as one of:

- `principle-limited`;
- `architecture-limited`;
- `parameter-limited`;
- `implementation-limited`;
- `comparison-not-matched`;
- `not-established-within-scope`.

Search alternatives by required function, not only by the paper's material or module name. Compare alternatives under shared target functions and constraints; do not use a broad list of superficially related technologies as a counterfactual analysis.

Use one scoped verdict:

- `demonstrated-feasible`;
- `sufficient-under-stated-joint-conditions`;
- `necessary-within-stated-architecture`;
- `practically-preferred-under-stated-constraints`;
- `not-shown-necessary`;
- `one-implementation-among-alternatives`;
- `superiority-not-established`;
- `not-established-within-scope`;
- `blocked: <reason>`.

Never convert “no alternative found” into “no alternative exists.” State the databases, query concepts, date/scope, and remaining search boundary when an absence-style conclusion matters.

## External-validation roles

When external validation is authorized, derive targeted roles from open `N-*` and `D-*` rows:

| Judgment need | Preferred evidence role | Required comparison logic |
| --- | --- | --- |
| Priority or originality | `nearest-prior-art` or `priority/novelty` | Same target function and the closest earlier principle, architecture, or demonstrated capability |
| Transferability | `boundary/contradiction` or `mechanism` | Evidence that the abstraction survives or fails outside the target paper's exact implementation |
| Alternative existence | `alternative-mechanism` or `counterexample` | A functionally equivalent route, not merely a similar material or label |
| Necessity | `discriminating-control` | Removal, substitution, ablation, or another test that separates the named choice from joint dependencies |
| Superiority | `matched-comparison` or `quantitative benchmark` | Comparable conditions, constraints, outcome definitions, and system level |

Use the main paper's references for discovery, not automatic verification. Prefer primary full text for direct counterexamples and matched comparisons. A review may map the field but cannot by itself close a disputed device-, method-, or condition-specific claim when a primary source is available.

If validation is `main-paper-only` or `fully-local`, complete the function-first internal analysis but use `external-priority-not-established`, `alternatives-not-exhaustively-checked`, or an equivalent scoped boundary. Do not simulate a literature search from memory.

## Gate integration

Apply these extensions to the six Gates:

| Gate | Research-judgment requirement |
| --- | --- |
| G2 | Complete the trigger scan; create applicable `N-*` and `D-*` rows; link atomic claims, conditions, baselines, joint dependencies, and missing controls |
| G3 | Derive source roles from unresolved judgment rows; seek nearest prior art, functionally equivalent alternatives, counterexamples, discriminating controls, and matched comparisons where material |
| G4 | Reject feasibility-to-necessity inflation, joint-to-component sufficiency inflation, baseline-failure generalization, unbounded absence claims, unmatched superiority claims, and unfalsifiable “future directions” |
| G5 | Map every strong originality, perspective, necessity, sufficiency, alternative, and superiority statement to canonical `C-*`, `N-*`, `D-*`, and applicable `E-*` records; block stale or unmapped judgments |

If a judgment fails, use the existing single targeted closure pass when available, narrow the scope, downgrade the verdict, or mark it blocked. Do not repair a logical overclaim only by replacing it with a softer adjective.

## Reader-facing contract

When material, render the canonical analysis under paper-appropriate headings equivalent to:

- `原创性、研究生成力与关键视角`;
- `核心设计选择：必要性、充分性与替代机制`.

Do not expose `N-*`, `D-*`, or other internal IDs. For each major judgment:

1. name the concrete idea or design choice;
2. identify the comparison baseline or required function;
3. distinguish main-paper evidence, external evidence, and report inference;
4. state the verdict and its scope;
5. state the decisive missing control, alternative, or boundary when unresolved.

Write follow-up research directions as hypotheses with decisive tests, not as generic recommendation lists. Cite externally verified priority, counterexample, or matched-comparison evidence using the report's normal footnote contract.

## Cross-domain abstraction

The same function-first questions must survive changes of field:

| Domain-specific question | Transferable form |
| --- | --- |
| Is material or layer X necessary? | Which state variable, coupling, selectivity, persistence, or operating constraint must the control element provide, and which other mechanisms provide it? |
| Is model module X necessary? | Which memory, routing, invariance, representation, or optimization function is required, and does an ablation or alternative architecture supply it under matched compute/data conditions? |
| Is biomarker or assay X necessary? | Which biological specificity, sensitivity, timing, or causal discrimination is required, and can another marker or assay meet it under a matched population and endpoint? |

Preserve this abstraction discipline in new examples. Do not encode a single paper's material name, device stack, model family, or biological target as a universal rule.
