# Evidence Audit Scope

- Domain/decision: {{DOMAIN}}
- Run ID: {{RUN_ID}}
- Parent run: {{PARENT_RUN}}
- Evidence as-of: {{AS_OF_DATE}}

<!-- rom-section: audit-decision -->
## Audit Decision

- Natural-language audit request: {{ROUTING_REQUEST}}
- Decision affected: TBD
- Required guarantee: TBD
- Audit boundaries and exclusions: TBD

<!-- rom-section: parent-mutation-policy -->
## Parent Relation and Mutation Policy

- Parent relation: supplement/audit
- Parent mutation policy: supplement-only; do not silently rewrite parent artifacts.
- Parent snapshot: {{PARENT_RUN}}
- How changed conclusions will propagate: record a `D-###` decision and an explicit parent-impact statement.

<!-- rom-section: target-claims -->
## Target Claims

| Claim ID | Claim type | Atomic bounded claim | Scope/regime | Decision critical: yes/no | Existing confidence | Parent source |
|---|---|---|---|---|---|---|
| B-001 | persistence | TBD | TBD | yes | Insufficient | TBD |

<!-- rom-section: evidence-requirements -->
## Evidence Requirements

| Claim ID | Required evidence roles | Required directness/context | Independence need | Critical missing role | Completion rule |
|---|---|---|---|---|---|
| B-001 | direct support; limitation; independent corroboration | full context | TBD | TBD | TBD |
