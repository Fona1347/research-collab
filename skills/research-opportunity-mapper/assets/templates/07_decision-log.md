# Decision Log

- Domain: {{DOMAIN}}
- Run ID: {{RUN_ID}}
- Task mode: {{TASK_MODE}}

<!-- rom-table: decisions -->
## Decisions

For `run-audit`, give every `manifest-lineage-audit` row exactly one valid
`D-###`, and ensure that each referenced ID resolves to exactly one row here.
Rows with `pass` or `not-applicable` bind a `Keep` decision. Give each failure a
non-`Keep` Decision ID used by no other manifest row or attack. Set `Target ID` and
`Affected decision target IDs` to the same single authoritative route/claim;
set Status to `Downgrade`, `Revise`, or `Kill`; set Decision exactly to
`Parent manifest failure [<check>]`; set Trigger Attack IDs exactly to
`not-applicable: deterministic manifest check`; and set Owner/next action to
`canonical_manifest_repair(Check, Result)`. These deterministic closure rows do
not masquerade as attacks. Other columns must state the reproduced evidence,
inference, alternative boundary, and reversal condition substantively.

For `run-audit`, every abnormal recomputed `id-closure` or `citation-closure`
row also binds a substantive Repair and one non-`Keep` decision with the same
single authoritative Target/Affected target. A dedicated anomaly D-ID is unique
among anomaly rows, does not reuse a manifest-failure D-ID, and uses Decision
`Parent <marker> anomaly [<key>:<status>]`, Trigger Attack IDs
`not-applicable: deterministic parent anomaly`, and Owner/next action equal to
Repair. If the anomaly shares the same non-`Keep` attack decision, keep the
attack decision's text, trigger, and owner rather than rewriting them.

| Decision ID | Date | Target ID | Affected decision target IDs | Status: Keep/Downgrade/Revise/Kill | Decision | Evidence IDs | Inference | Alternative | Trigger Attack IDs | Reversal condition | Owner/next action |
|---|---|---|---|---|---|---|---|---|---|---|---|
| D-001 | {{DATE}} | B-001 | B-001 | Revise | TBD | E-001 | TBD | TBD | A-001 | TBD | TBD |

<!-- rom-table: revisions -->
## Revisions and Rejections

| Target ID | Previous position | Trigger Evidence/Attack IDs | Revised position | Report section changed | Knowledge retained |
|---|---|---|---|---|---|
| B-001 | TBD | A-001 | TBD | TBD | TBD |

<!-- rom-table: open-uncertainty -->
## Open Uncertainty

| Uncertainty | Priority | Affected IDs | Resolution action | Owner | Due date |
|---|---|---|---|---|---|
| TBD | TBD | B-001 | TBD | TBD | TBD |

<!-- rom-table: next-actions -->
## Next Actions

| Action | Type: search/experiment/model/collaboration | Dependency | Deliverable | Decision enabled |
|---|---|---|---|---|
| TBD | TBD | TBD | TBD | TBD |
