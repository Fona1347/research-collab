# Claim-Level Evidence Confidence

Use this contract to assess what the evidence permits the run to say. Score atomic claims, never papers as a whole. Keep scientific credibility (`claim_confidence`) separate from attention or momentum (`frontier_salience`).

## Contents

- [Unit of assessment](#unit-of-assessment)
- [Required claim register](#required-claim-register)
- [Evidence roles and record fields](#evidence-roles-and-record-fields)
- [Evidence-to-claim linkage and stance](#evidence-to-claim-linkage-and-stance)
- [Frontier salience](#frontier-salience)
- [Confidence dimensions](#confidence-dimensions)
- [Confidence levels](#confidence-levels)
- [Hard caps and downgrade rules](#hard-caps-and-downgrade-rules)
- [Claim-type requirements](#claim-type-requirements)
- [Conflicts, dependence, and applicability](#conflicts-dependence-and-applicability)
- [Allowed wording](#allowed-wording)
- [Upgrade and overturn actions](#upgrade-and-overturn-actions)
- [Validator boundary](#validator-boundary)

## Unit of assessment

An atomic claim asserts one relationship in one bounded regime. It must be possible to state what observation would support, narrow, or contradict it.

Bad unit:

> Ferroelectric topological devices are promising for neuromorphic computing.

Better units:

- Under regime R, control X changes state descriptor Y beyond threshold T.
- Under matched read conditions, state descriptor Y predicts device observable Z after controlling for average polarization and trapped charge.
- Under budget B, a hardware implementation improves metric M relative to baseline D without shifting cost to peripheral operation P.

Do not average confidence across unrelated claims from one source. A paper may provide direct existence evidence, indirect mechanism evidence, and no system-value evidence.

## Required claim register

For every decision-critical claim, record:

| Field | Requirement |
|---|---|
| `claim_id` | Stable `B-###`, `M-###`, `S-###`, or `CL-###` identifier. `C-###` is reserved for a route/candidate. |
| `claim` | Atomic proposition, not a topic label. |
| `claim_type` | One of the defined types below. |
| `scope_regime` | Material, geometry, operating range, environment, timescale, population, and metric as applicable. |
| `decision_role` | Why the claim can advance, revise, downgrade, or kill a route. |
| `required_evidence_roles` | Direct observation, mechanism discrimination, baseline, replication, limitation, translation, or other explicit role. |
| `supporting_evidence_ids` | Evidence records whose `Claim IDs` include this exact bounded claim and whose stance is `supports` or `mixed`. A mixed record is not unqualified support. |
| `limiting_evidence_ids` | Evidence records whose `Claim IDs` include this claim and whose stance is `limits`, `contradicts`, or `mixed`. |
| `directness` | `direct`, `supporting`, `indirect`, or `none`. |
| `full_context_status` | `full-context-verified`, `abstract-only`, `metadata-only`, or `not-accessed`. |
| `method_validity` | Whether the study design and observable can answer the claim; include rationale. |
| `independence_replication` | Team, sample, device, batch, seed, dataset, and laboratory independence as applicable. |
| `consistency` | Agreement, heterogeneity, or unresolved conflict. |
| `applicability` | Match to the target material, device, regime, scale, and budget. |
| `confidence` | `High`, `Moderate`, `Low`, or `Insufficient`. |
| `active_cap_codes` | Every applicable machine cap code below, or exactly `none`. |
| `cap_or_downgrade_reason` | Every active hard cap and important weakness. |
| `allowed_wording` | Strongest defensible human-facing formulation. |
| `upgrade_action` | Cheapest evidence that could raise confidence. |
| `overturn_condition` | Evidence or result that would falsify or materially reverse the claim. |

Allowed `claim_type` values:

- `existence`: an entity, state, response, or phenomenon occurs.
- `mechanism`: a specified causal or physical mechanism produces the response.
- `comparative`: one method or state outperforms another under a matched budget.
- `persistence`: a bottleneck, state, effect, or limitation persists over a defined condition or time.
- `generalization`: a relationship transfers across samples, materials, regimes, tasks, or laboratories.
- `system-value`: a lower-level effect yields cell, array, circuit, architecture, workload, energy, latency, accuracy, or reliability value.
- `open-position`: a precise interface remains incompletely closed under a bounded search.
- `forecast`: a future research, adoption, or performance trajectory is expected.

## Evidence roles and record fields

Tag each evidence record by the role it plays; one record may have multiple roles only when each use is explicit.

- `canonical-anchor`: defines accepted terminology, mechanism, metric, or historical baseline.
- `frontier-signal`: indicates recent attention, capability, or emerging approach families.
- `direct-support`: directly measures or tests the bounded claim.
- `direct-neighbor`: closes or approaches the proposed interface and constrains openness.
- `strongest-baseline`: establishes the best relevant conventional or alternative performance.
- `limitation-negative`: reports failure, null, mixed evidence, confound, or boundary.
- `independent-replication`: tests the proposition outside the originating evidence chain.
- `translation`: connects material, device, circuit, architecture, workload, manufacturing, patent, or industry layers.

Every evidence record used for a decision-critical claim should retain:

- stable evidence ID;
- title, year, source type, and publication status;
- DOI or stable URL when available;
- authors or group identity needed to judge independence;
- study type and method;
- exact measured object, comparator, sample/seed/device hierarchy, and regime;
- retrievable locator such as page, figure, table, section, chunk, or offset;
- full-context status and verification date;
- verification_depth: metadata, abstract, full-text, or canonical-deep-read;
- a canonical cross-run reference when evidence is imported from Deep Reading;
- source role;
- method-quality rationale;
- supported claim IDs and limited/contradicted claim IDs;
- venue and citation signal only as salience metadata, with provider/date;
- explicit boundaries and unresolved extraction gaps.

## Evidence-to-claim linkage and stance

Treat `Evidence ID -> Claim IDs` as an explicit typed edge. Every
`B/M/S/CL-###` in an evidence row must already be defined in the authoritative
`atomic-claims` table. A source title, topic overlap, or nearby ID in prose
does not create that relationship.

Use one exact stance for the whole row:

- `supports`: responsive evidence favors every listed bounded claim;
- `limits`: evidence narrows scope, regime, wording, or applicability;
- `contradicts`: evidence conflicts with the listed claim in an overlapping
  regime;
- `mixed`: inseparable supporting and limiting components; if it is linked as
  support, it must also be linked as limiting evidence so its limiting component
  binds caps and wording;
- `context`: terminology, frontier salience, or background only; it cannot
  raise or lower claim confidence.

If the same paper supports `M-001` but limits `S-001`, create two evidence
rows with separate evidence IDs, Claim IDs, exact supported/limited statements,
and stances. Do not place both claims in one row with an ambiguous stance.
`Claim IDs: none` is allowed only for discovery-only `context` records that
are absent from all supporting and limiting confidence lists.

A confidence edge is valid only when both directions agree:

1. a supporting evidence ID lists the assessed claim and has stance `supports`
   or `mixed`;
2. a limiting evidence ID lists the assessed claim and has stance `limits`,
   `contradicts`, or `mixed`;
3. a `mixed` ID used as support also appears in the limiting list;
4. `context` evidence appears in neither list;
5. every cited evidence ID resolves to one authoritative evidence definition.

`Source role` answers why the record matters to the search
(`canonical-anchor`, `frontier-signal`, `direct-support`, and so on).
`Stance` answers what that record does to one bounded claim. Keep the two
fields independent; neither venue, source role, nor directness silently changes
stance.

## Frontier salience

Use `frontier_salience` only for discovery priority and field-state awareness. Assess it independently from confidence using available signals such as:

- recency relative to the run's evidence window;
- authoritative review or roadmap attention;
- representative primary work in important field venues;
- field- and publication-year-normalized citation signal;
- convergence across conferences, journals, patents, or industry evidence when relevant.

Record the citation provider, query date, and normalization method. If the signal cannot be verified, write `unavailable`; do not estimate it. A top venue, high citation count, recent date, or roadmap mention cannot raise `claim_confidence` by itself.

Suggested salience labels are `high`, `medium`, `low`, and `unavailable`. They are not scientific-quality grades.

## Confidence dimensions

Judge confidence using the weakest decision-relevant dimension rather than a simple paper count.

### Scope precision

Does the claim state the exact material, device, geometry, conditions, timescale, metric, and comparison it needs? Broad claims supported by narrow evidence must be narrowed before scoring.

### Directness

- `direct`: the design directly observes or intervenes on the claimed relationship.
- `supporting`: the evidence measures a necessary link but not the full relationship.
- `indirect`: the connection requires an unverified model, analogy, proxy, or scale transition.
- `none`: the record does not bear on the claim.

### Full-context verification

Determine whether methods, figures, tables, supplementary conditions, caveats, and relevant surrounding text were checked. Metadata and abstracts are discovery evidence, not sufficient verification of a decision-critical scientific conclusion.

### Method validity

Ask whether the method can distinguish the proposition from alternatives. Check controls, calibration, leakage, selection effects, convergence, sample hierarchy, statistics, measurement resolution, model identifiability, and missing costs as relevant.

### Independence and replication

Count independent evidence chains, not citations. Multiple papers sharing a group, device batch, dataset, model assumption, or upstream measurement may not be independent.

Use the existing evidence `Independence/replication` cell as
`chains=EC-001; basis=<group, sample/dataset and upstream relationship>`; use
`chains=unknown; <missing information>` when it is unresolved. Reuse one chain ID
across papers sharing data, devices or upstream measurements. Rows from the same
DOI are merged regardless of wording or chain aliases. Do not introduce a separate
registry. Reading depth, directness and chain identity are independent dimensions:
an unread direct experiment is context-unverified, not automatically indirect;
zero supporting chains is absence of support, not single-chain support.

For a broad High claim, the claim-level Independence/replication cell records
`review=independent; reviewer=<attributable reviewer>; basis=<scope and source
independence rationale>`. This records a review; the parser cannot certify its
scientific adequacy. A strong multi-method, multi-sample single-study exception
also records `design=strong-multimethod` in that cell, with explicit design and
replication locators in Method validity. Neither different IDs nor a declared
exception automatically establish independence or method validity.

### Consistency

Record whether direct studies agree, disagree because regimes differ, or remain in unresolved conflict. Do not erase heterogeneity by averaging incompatible conditions.

### Applicability

Evidence can be internally strong yet inapplicable to the proposed regime. Trace every transfer across material, geometry, temperature, timescale, model, device, cell, array, architecture, and workload.

## Confidence levels

### `High`

Use only when the claim is precise and the relevant causal or observational chain is directly verified in full context, the method can answer the claim, applicability is strong, and no unresolved direct contradiction remains.

For `mechanism`, `comparative`, `persistence`, `generalization`, and `system-value` claims, High normally requires at least two independent direct evidence chains or a comparably strong multi-method, multi-sample design with explicit replication.

Exception: one decisive, full-context study may support a **narrow existence claim** at High when the observation is direct, the method is specific, the regime is tightly bounded, and the result does not rely on an unresolved alternative explanation. This exception does not upgrade a universal mechanism, generalization, or system advantage.

### `Moderate`

Use when direct evidence supports the bounded claim but one material limitation remains, such as limited independent replication, partial applicability, moderate heterogeneity, or a single unresolved conflict that caps confidence. State the cap explicitly.

### `Low`

Use when support is preliminary, indirect, proxy-based, single-chain, weakly applicable, abstract-only for a noncritical orientation claim, or vulnerable to major confounds. Low means plausible enough to test, not safe to present as established.

### `Insufficient`

Use when the evidence needed to assess the claim is absent, inaccessible, nonresponsive, internally uninterpretable, or too weak to distinguish the claim from alternatives. `Insufficient` is not evidence that the claim is false.

## Hard caps and downgrade rules

Apply all relevant caps; the strictest cap wins.

| Active cap code | Condition | Maximum confidence | Required response |
|---|---|---|---|
| `context-unverified` | Decision-critical support is metadata-only, abstract-only, or the relevant context is unverified | `Low` | Verify full context or narrow/remove the claim. It can be `Insufficient` when the abstract does not expose necessary conditions. |
| `indirect-only` | All supporting evidence is indirect or crosses an unvalidated proxy/scale transition | `Low` | Add a direct discriminating measurement or label the statement as a hypothesis. |
| `unresolved-direct-conflict` | A direct contradiction remains unresolved | `Moderate` | Describe both regimes, conflict source, and discriminating test. |
| `single-chain-broad-claim` | Broad mechanism/generalization/system claim relies on one group or one evidence chain | `Moderate` | Narrow the scope or seek independent replication. |
| `method-nondiscriminating` | Method cannot distinguish the proposed mechanism from a credible alternative | `Low` | Recast as association and specify a causal control. |
| `regime-transfer-unvalidated` | Evidence applies to a materially different regime with no validated transfer model | `Low` | State the transfer as inference and validate the bridge. |
| `salience-only` | Citation count, venue, recency, or expert enthusiasm is the main support | `Insufficient` | Treat it only as salience and retrieve responsive evidence. |
| `search-miss-novelty` | Search miss is used to claim novelty, priority, or global absence | `Insufficient` | Replace with a bounded search statement and direct-neighbor plan. |
| `proxy-to-system-unvalidated` | Material/device proxy is used to claim array, circuit, architecture, or workload benefit without intermediate validation | `Low` | Add compact/circuit/array/system bridge and same-budget baseline. |
| `assumed-capability` | Capability access or maturity is only assumed | no route-level confidence above `Moderate` | Add a capability verification task or redesign around observed capability. |

Do not combine several Low items into High by vote counting. Do not allow a review article to substitute for the primary evidence required by a precise performance or mechanism claim.

## Claim-type requirements

### Existence

Require a specific observation and a method capable of identifying the state or effect. Distinguish morphology from topology, response from mechanism, and simulated possibility from experimental existence.

### Mechanism

Require intervention or discriminating variation, a causal path, credible alternatives, controls, and a result that differs between hypotheses. Correlation between a state image and an output is not sufficient when average polarization, domain walls, traps, ions, heat, or leakage could explain both.

### Comparative

Require a matched task, operating regime, budget, tuning effort, data split, calibration, and uncertainty. Identify costs moved to peripherals, training, refresh, sensing, or fabrication.

### Persistence

Define time, cycles, environmental range, sample hierarchy, and failure threshold. A short observation window cannot support long-retention language; one device cannot establish population reliability.

### Generalization

Specify the transfer axis and demand evidence across that axis. Parameter sweeps inside one calibrated model are not independent material or laboratory replication.

### System value

Trace the full bridge:

`physical state -> device observable -> compact behavior -> cell -> array/peripheral -> architecture -> workload -> same-budget metric`

Any unvalidated bridge limits the final claim. Report lower-level value without inflating it to system value.

### Open position

Require positive evidence on both sides of the proposed interface, a bounded neighbor search, nearest matches, and an exact unresolved interface. “No exact query hit” is not an open-position claim.

### Forecast

Identify assumptions, horizon, leading indicators, alternatives, and reversal signals. Forecast confidence must not masquerade as current causal evidence.

## Conflicts, dependence, and applicability

When evidence conflicts:

1. Check whether the claims actually share material, geometry, state definition, measurement, operating regime, and metric.
2. Check source dependence, shared datasets, shared samples, shared models, and citation inheritance.
3. Separate true contradiction from regime-dependent heterogeneity.
4. Preserve both supporting and limiting evidence IDs.
5. State the exact condition delta and adjudicate as support-dominant,
   limit-dominant, condition-split, or unresolved.
6. Cap confidence until a discriminating explanation is evidenced.

The existing contradictions table records `Tension type` as `direct-conflict`,
`evidence-gap`, or `condition-difference`. Only an unresolved direct conflict in
overlapping conditions can activate the conflict cap; limits, missing system
comparisons, and different conditions are not contradictions by themselves.
For an unresolved direct conflict, the claim consistency cell starts
`type=direct-conflict; status=unresolved; ...`. Preserve both direct sides and
their condition-specific sources. Scientific review determines whether the
conditions really overlap; the validator checks declared relationships.

When transferring evidence across layers, label each bridge as `validated`, `modeled`, `assumed`, or `missing`. The weakest bridge determines the maximum confidence of the end-to-end claim.

## Allowed wording

Tie prose strength to the confidence and claim type.

| Confidence | Permitted pattern | Avoid |
|---|---|---|
| `High` | “Within [scope], direct evidence establishes/shows …” | Universal language beyond the assessed regime. |
| `Moderate` | “Evidence supports … within [scope], but [cap] remains.” | “Proves”, “settled”, or unqualified generalization. |
| `Low` | “Preliminary/indirect evidence is consistent with …; test X is required.” | “Demonstrates” or recommendation presented as established fact. |
| `Insufficient` | “Current evidence is insufficient to determine …” | Treating insufficiency as falsity or novelty. |

For open positions, use wording such as:

> Within databases D, terminology T, dates Y, access A, and neighbor definition N, no source was found that closes interface I; nearest matches E-### and E-### leave boundary B unresolved.

Never write “nobody has done this” unless the statement itself has an extraordinary, independently auditable evidentiary basis.

## Upgrade and overturn actions

For each decision-critical claim, define:

- the cheapest full-context verification or retrieval action;
- the closest missing independent evidence role;
- the control that separates the leading mechanism from its strongest alternative;
- the target regime or population needed for applicability;
- the result that would downgrade, revise, or kill the route.

Prefer an action that changes a decision over additional papers that merely repeat the same evidence chain.

## Validator boundary

A validator may enforce:

- legal labels and required fields;
- authoritative Claim-ID linkage and stance compatibility between evidence
  records and supporting/limiting confidence lists;
- retrievable identifiers and verification status;
- cross-artifact claim/evidence references;
- hard-cap consistency;
- presence of contradiction and downgrade reasons;
- allowed-wording fields and upgrade/overturn actions.

A validator cannot determine whether a paper is truthful, a method is scientifically valid, a mechanism is real, or a recommendation is correct. Treat structural validation as an integrity check, not an automated scientific verdict.
