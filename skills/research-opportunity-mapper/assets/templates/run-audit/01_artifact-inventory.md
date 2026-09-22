# Audited Artifact Inventory

- Audit run ID: {{RUN_ID}}
- Parent run: {{PARENT_RUN}}

<!-- rom-table: artifact-inventory -->
## Artifact Inventory

Run `python scripts/parent_audit.py PATH_TO_PARENT_RUN` and reproduce the complete
`artifact_projection` exactly. `ART-001` is the parent manifest; subsequent
rows cover the union of declared and observed parent files in sorted order.

| Artifact ID | Manifest role | Workspace-relative file | Declared: yes/no | Exists: yes/no | SHA-256 | Schema/contract | Status |
|---|---|---|---|---|---|---|---|
| ART-001 | intake | TBD | yes | yes | TBD | TBD | inspect |

<!-- rom-section: manifest-lineage-audit -->
## Manifest and Lineage Audit

Reproduce every helper row exactly in `Check`, `Evidence`, and `Result`. Set
`Required repair` exactly to `canonical_manifest_repair(Check, Result)`; pass
and not-applicable rows therefore use `retain observed state`. Give every row
exactly one valid `D-###` that resolves to exactly one decision; pass and
not-applicable bind `Keep`. Every failure is `high` or `blocking` and owns a
Decision ID used by no other manifest row or attack. That ID resolves to exactly one non-`Keep`
decision whose Target and Affected target are the same single authoritative
route/claim, Decision is `Parent manifest failure [<check>]`, Trigger Attack IDs
is `not-applicable: deterministic manifest check`, and Owner/next action is the
canonical repair.

| Check | Evidence | Result: pass/fail/uncertain | Severity | Required repair | Decision ID |
|---|---|---|---|---|---|
| schema-supported | TBD | TBD | TBD | TBD | D-001 |

<!-- rom-section: missing-extra-artifacts -->
## Missing or Extra Artifacts

| File/role | Missing/extra/undeclared | Why it matters | Exact repair | Decision ID |
|---|---|---|---|---|
| TBD | TBD | TBD | TBD | D-001 |
