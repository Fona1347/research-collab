# Cross-Artifact Traceability Audit

- Audit run ID: {{RUN_ID}}
- Parent run: {{PARENT_RUN}}

<!-- rom-table: id-closure -->
## Cross-Artifact ID Audit

Reproduce the helper's complete `id_projection` exactly in the first five
columns. Do not select only the anomalies.

| ID | Type | Defined in | Referenced in | Dangling/duplicate/mismatch | Severity | Repair | Decision ID |
|---|---|---|---|---|---|---|---|
| E-001 | evidence | TBD | TBD | TBD | TBD | TBD | D-001 |

<!-- rom-table: citation-closure -->
## Citation and DOI Closure

These rows audit the parent reader report, not this audit report. Reproduce
the helper's complete `citation_projection` exactly in the first six columns.
External metadata verification belongs in the evidence audit and is not
inferred by this local integrity check.

| Reader reference | Report DOI/stable URL | Evidence ID | Evidence-matrix DOI/stable URL | Match: yes/no | Computed status | Repair | Decision ID |
|---|---|---|---|---|---|---|---|
| [1] | https://doi.org/TBD | E-001 | https://doi.org/TBD | no | url-mismatch | TBD | D-001 |

<!-- rom-section: dangling-references -->
## Dangling References and Provenance Gaps

| Finding ID | Claim/report location | Missing definition/source/locator | Decision consequence | Repair | Decision ID |
|---|---|---|---|---|---|
| F-001 | TBD | TBD | TBD | TBD | D-001 |
