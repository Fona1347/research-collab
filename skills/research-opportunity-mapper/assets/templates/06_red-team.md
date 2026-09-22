# Adversarial Red-Team Audit

- Domain: {{DOMAIN}}
- Run ID: {{RUN_ID}}
- Task mode: {{TASK_MODE}}

<!-- rom-table: attack-register -->
## Attack Register

| Attack ID | Target claim/route | Attack surface | Strongest objection | Evidence IDs or test | Severity: low/medium/high/blocking | Required repair or discriminating test | Verdict: Keep/Downgrade/Revise/Kill | Decision ID | Status |
|---|---|---|---|---|---|---|---|---|---|
| A-001 | B-001 | problem-adequacy | TBD | E-001 | high | TBD | Revise | D-001 | open |

Include at least one row for each exact attack surface: `problem-adequacy`, `mechanism`, `evidence`, `open-position`, `capability`, `cross-scale`, `baseline-system-cost`, and `bio-inspired-translation`. In a genuinely non-biological run, keep the last row and record an explicit not-applicable rationale plus the non-biological baseline boundary; do not omit it.

For `run-audit`, every attack Decision ID must be disjoint from every Decision
ID assigned to a failed `manifest-lineage-audit` check.
A non-`Keep` attack decision may also jointly dispose of recomputed parent
ID/citation anomalies. When shared, retain the attack decision's text, trigger
IDs, and owner; do not rewrite it to the dedicated anomaly source. An anomaly
still may not share a manifest-failure Decision ID.

Allowed severity values are `low`, `medium`, `high`, and `blocking`. Allowed
status values are `open`, `unresolved`, `accepted`, `mitigated`, `resolved`, and
`closed`; `open`, `unresolved`, and `accepted` remain unresolved for decision
gating. An unresolved `high` or `blocking` attack cannot receive `Keep`.

<!-- rom-table: baseline-ladder -->
## Strongest Baseline Ladder

| Target claim/route | Material/device baseline | Control-disabled baseline | Alternative mechanism | Circuit/digital or conventional baseline | End-to-end baseline | Missing comparison | Decision impact |
|---|---|---|---|---|---|---|---|
| B-001 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

<!-- rom-table: alternative-explanations -->
## Alternative-Explanation Tests

| Target claim/route | Observable | Preferred mechanism | Alternative explanation | Discriminating control | Expected signatures | Decision rule | Threshold |
|---|---|---|---|---|---|---|---|
| B-001 | TBD | TBD | TBD | TBD | TBD | TBD | TBD |

<!-- rom-table: evidence-independence -->
## Evidence and Independence Audit

| Claim ID | Single-source/team risk | Full-context gap | Replication gap | Direct conflict | Confidence cap | Required evidence | Decision ID |
|---|---|---|---|---|---|---|---|
| B-001 | TBD | TBD | TBD | TBD | TBD | TBD | D-001 |

<!-- rom-table: capability-scale -->
## Cross-Scale and Capability Audit

| Target claim/route | Starting evidence scale | Claimed destination scale | Missing bridge | Capability ID/state | PVT/variation/yield/reliability or analogous cost | Verdict | Decision ID |
|---|---|---|---|---|---|---|---|
| B-001 | TBD | TBD | TBD | CAP-001 / Unknown | TBD | Revise | D-001 |

<!-- rom-table: bio-inspired-audit -->
## Bio-Inspired Translation Audit

| Target | Biological observation | Abstract principle | Mathematical operator/state-update rule | Algorithm | Hardware primitive | De-biologized scientific question | Non-biological baseline | Principle-specific ablation | Intrinsic gain/boundary | Verdict | Decision ID |
|---|---|---|---|---|---|---|---|---|---|---|---|
| not applicable | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Keep | D-001 |

<!-- rom-table: kill-criteria -->
## Target Kill or Revision Criteria

| Target claim/route | Kill criterion | Quantitative threshold | Earliest test | Consequence | Fallback/retained asset | Decision ID |
|---|---|---|---|---|---|---|
| B-001 | TBD | TBD | TBD | TBD | TBD | D-001 |

<!-- rom-section: decision-impact -->
## Decision Impact

Summarize how every `Downgrade`, `Revise`, or `Kill` finding changed the route artifact and final report. A risk paragraph without a propagated decision does not close the audit.

- TBD
