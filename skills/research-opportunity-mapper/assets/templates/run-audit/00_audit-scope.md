# Existing Run Audit Scope

- Audit run ID: {{RUN_ID}}
- Audited parent run: {{PARENT_RUN}}
- Domain: {{DOMAIN}}
- Audit as-of: {{AS_OF_DATE}}

<!-- rom-section: audit-decision -->
## Audit Decision

- Natural-language audit request: {{ROUTING_REQUEST}}
- Intended reader/decision: TBD
- Audit depth: manifest, artifacts, evidence, reasoning, routes, and reader report
- Required guarantee: identify blocking defects and propagate material findings into explicit decisions.

<!-- rom-section: parent-snapshot -->
## Audited Parent Snapshot

| Parent run ID | Workspace-relative manifest reference | Manifest SHA-256 | Selected artifacts/hashes | Schema | Audit boundary |
|---|---|---|---|---|---|
| {{PARENT_RUN}} | TBD | TBD | TBD | TBD | TBD |

<!-- rom-section: mutation-policy -->
## Mutation Policy

- Audit artifacts are supplemental and do not mutate the parent run.
- Repairs require a separate revision/copy operation after audit decisions are accepted.
- Parent changes after the recorded snapshot invalidate affected findings.
