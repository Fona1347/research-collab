# Focus Route Protocol

- Domain: {{DOMAIN}}
- Run ID: {{RUN_ID}}

<!-- rom-table: focus-routes -->
## Primary Route, Comparator, and Fallback

Keep 0/1/several substantive candidates, one primary when nonempty. Preserve
comparators in Strongest baseline/Competing hypotheses and fallback in the
activation-rule field; do not create C-IDs merely for roles or dependent stages.
For zero candidates, write Selection outcome: no-candidate, leave all route-owned
tables empty, close atomic-claim decisions and give a concrete information check
or bounded stop with inputs, deliverable and reopening condition in next-actions.

| Candidate ID | Route role: primary/comparator/fallback | What | Why | Need to know | How | What we learn | Strongest baseline | Competing hypotheses | Evidence IDs |
|---|---|---|---|---|---|---|---|---|---|
| C-001 | primary | TBD | TBD | TBD | TBD | TBD | TBD | H-001 | E-001 |

<!-- rom-table: staged-execution -->
## Phased Execution and Stage Gates

| Stage | Route | Action | Required evidence | Quantitative pass threshold | Kill/revise threshold | Dependency | Retained asset |
|---|---|---|---|---|---|---|---|
| 0 | C-001 | TBD | TBD | TBD | TBD | TBD | TBD |

<!-- rom-table: outcome-interpretation -->
## Positive, Negative, and Ambiguous Outcomes

| Candidate ID | Outcome class: positive/negative/ambiguous | Observable pattern | Allowed conclusion | Forbidden conclusion | Next action | Decision ID |
|---|---|---|---|---|---|---|
| C-001 | positive | TBD | TBD | TBD | TBD | D-001 |
| C-001 | negative | TBD | TBD | TBD | TBD | D-001 |
| C-001 | ambiguous | TBD | TBD | TBD | TBD | D-001 |

<!-- rom-section: route-boundaries -->
## Kill, Reversal, and Retained Value

| Candidate ID | Kill criterion | Reversal condition | Retained value after failure | Comparator/fallback activation rule |
|---|---|---|---|---|
| C-001 | TBD | TBD | TBD | TBD |

<!-- rom-table: opportunity-gates -->
## Opportunity Gates

Overall is deterministic: any fail -> no-go; otherwise any unknown -> defer; otherwise any conditional -> conditional-go; otherwise go. The recall caveat must name the bounded databases/corpora, dates, languages or terminology, and access limits; a search miss is not proof of absence.

| Candidate ID | Openness gate: pass/conditional/fail/unknown | Contribution gate: pass/conditional/fail/unknown | Feasibility gate: pass/conditional/fail/unknown | Overall: go/conditional-go/defer/no-go | Recall caveat | Gate Evidence IDs | Binding condition or next check |
|---|---|---|---|---|---|---|---|
| C-001 | unknown | unknown | unknown | defer | TBD | E-001 | TBD |

<!-- rom-table: route-fast-pilots -->
## Top Route Fast Pilots

If go/conditional-go routes exist, select at most three for bounded fast pilots. If none is eligible, leave this table empty; do not invent a proxy merely to fill it. Fourteen days applies only here, not to conditional three-month and one-year research plans. Deferred routes need concrete input, deliverable, and gate-changing next actions in the decision log.

| Candidate ID | Rank: 1-3 | Hypothesis A | Hypothesis B | Discriminating test | Observable | Horizon days: 1-14 | Resource cap | Advance threshold | Kill or revise threshold |
|---|---|---|---|---|---|---|---|---|---|
| C-001 | 1 | TBD | TBD | TBD | TBD | 14 | TBD | TBD | TBD |
