# Claim and Evidence Matrix

- Domain: {{DOMAIN}}
- Run ID: {{RUN_ID}}
- Evidence as-of: {{AS_OF_DATE}}

<!-- rom-table: atomic-claims -->
## Atomic Claims

| Claim ID | Claim type | Atomic bounded claim | Scope/regime | Epistemic label | Decision critical: yes/no | Status | Parent Claim ID |
|---|---|---|---|---|---|---|---|
| B-001 | persistence | TBD | TBD | Evidence | yes | open | none |

Allowed claim types: `existence`, `mechanism`, `comparative`, `persistence`, `generalization`, `system-value`, `open-position`, and `forecast`.

<!-- rom-table: evidence-records -->
## Evidence Records

| Evidence ID | Claim IDs | Source role | Stance | Directness | Study/source type | Publication status | Core contribution | Exact supported/limited claim | Scope/regime | Method-validity note | Independence/replication | Source metadata | DOI or stable URL | Provenance locator | Full-context status | verification_depth | Verification | Canonical cross-run ref | Frontier signal | Citation signal/source/as-of | Reader ref |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| E-001 | B-001 | canonical-anchor | context | none | TBD | published | TBD | TBD | TBD | TBD | chains=unknown; basis=TBD | TBD | https://doi.org/TBD | TBD | metadata-only | metadata | unverified | none | TBD | unavailable | [1] |

<!-- rom-table: deep-reading-handoff -->
## Deep Reading Handoff Queue

Use existing workspace-relative or absolute Deep Reading run paths. The checker validates actual canonical files, record ownership and main/auxiliary source identities. A canonical-depth evidence row requires exactly one imported handoff; no import IDs in other statuses. In Canonical refs, cite only Deep Reading canonical artifacts (paper-package.md, reading-report.md, auxiliary-literature-table.md, external-evidence-matrix.md, or view-report-audit.md); never import from derived view-report.md. Percent-encode record-key hyphens in cross-run anchors, for example reading-report.md#claim=C%2D001.

| Deep-read request ID | Paper key | Target Claim/Route IDs | Decision-changing question | Priority: high/medium/low | Status: queued/in-progress/imported/blocked/skipped | Deep Reading run | Canonical refs | Imported Evidence IDs | Blocker or import decision |
|---|---|---|---|---|---|---|---|---|---|
| DR-001 | TBD | B-001 | TBD | high | queued | none | none | none | TBD |

<!-- rom-table: claim-confidence -->
## Claim Confidence

| Claim ID | Required evidence roles | Supporting Evidence IDs | Limiting Evidence IDs | Directness summary | Full-context status | Method validity | Independence/replication | Consistency/conflict status | Applicability | Confidence: High/Moderate/Low/Insufficient | Active cap codes | Cap/downgrade reason | Allowed wording | Upgrade evidence/action | Overturn condition |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B-001 | TBD | E-001 | none | none | metadata-only | TBD | chains=unknown; basis=TBD | unresolved | TBD | Insufficient | context-unverified | Metadata cannot establish the claim. | Evidence is currently insufficient. | TBD | TBD |

<!-- rom-section: source-annotations -->
## Important Source Annotations

> **E-001 | TBD (year), DOI or stable link**
> - Core contribution: TBD
> - Supports or limits: B-001 — TBD
> - Scope and boundary: TBD
> - Provenance and verification: TBD

<!-- rom-table: contradictions -->
## Contradictions and Mixed Evidence

| Claim ID | Supporting Evidence IDs | Contradicting/limiting Evidence IDs | Independence | Tension type: direct-conflict/evidence-gap/condition-difference | Condition delta | Adjudication: support-dominant/limit-dominant/condition-split/unresolved | Current interpretation | Resolution action | Decision ID |
|---|---|---|---|---|---|---|---|---|---|
| B-001 | E-001 | none | TBD | evidence-gap | TBD | unresolved | TBD | TBD | D-001 |
