# Decision-Critical Claim Register

- Domain: {{DOMAIN}}
- Run ID: {{RUN_ID}}

<!-- rom-table: claim-register -->
## Decision-Critical Claims

| Claim ID | Claim type | Atomic bounded claim | Scope/regime | Decision importance | Required evidence roles | Current Evidence IDs | Missing role | Audit priority | Parent Claim ID |
|---|---|---|---|---|---|---|---|---|---|
| B-001 | persistence | TBD | TBD | decision-critical | TBD | E-001 | TBD | high | none |

<!-- rom-table: claim-dependencies -->
## Claim Dependencies

| Upstream Claim ID | Downstream Claim ID | Dependency type | Failure consequence | Test/search to break dependency |
|---|---|---|---|---|
| B-001 | M-001 | necessary | TBD | TBD |

<!-- rom-section: audit-priority -->
## Audit Priority and Stop Rule

- Highest-value uncertainty: TBD
- Search stop rule: TBD
- Claims explicitly outside this audit: TBD
