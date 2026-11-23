# Audited Route Verdicts and Remediation

- Audit run ID: {{RUN_ID}}
- Parent run: {{PARENT_RUN}}

<!-- rom-table: route-verdicts -->
## Route Verdicts

Give each authoritative parent route/claim exactly one row. Aggregate every
attack decision, manifest-failure decision, and recomputed parent
ID/citation-anomaly decision bound to that target, then
use the strongest verdict in the order
`Kill > Revise > Downgrade > Keep`. The Decision ID must carry that maximum
verdict. If integrity and an attack tie at the maximum rank, bind an equally
strong integrity Decision ID; if several integrity decisions tie, any one of
those maximum-rank integrity IDs may bind.
Working and reader verdict rows match target, strongest finding, verdict,
allowed conclusion, required repair, and Decision ID. When a dedicated anomaly
decision binds the maximum, Strongest finding is exactly lowercase
`parent <marker> anomaly [<key>:<status>]`, Required repair equals its Repair,
and both rows use that D-ID. A joint shared attack decision retains the attack
finding/repair convention instead of requiring this dedicated source.

| Route/claim ID | Parent status | Strongest finding | Severity | Verdict: Keep/Downgrade/Revise/Kill | Allowed current conclusion | Required repair | Decision ID |
|---|---|---|---|---|---|---|---|
| C-001 | recommended | TBD | high | Revise | TBD | TBD | D-001 |

<!-- rom-table: remediation-plan -->
## Exact Remediation Plan

| Repair ID | Affected artifact/section | Exact change | Dependency | Verification command/gate | Owner | Status |
|---|---|---|---|---|---|---|
| R-001 | TBD | TBD | TBD | TBD | TBD | open |

<!-- rom-section: stop-conditions -->
## Stop and Re-entry Conditions

| Route/claim ID | Stop condition | Re-entry evidence | Retained knowledge/asset | Next decision date |
|---|---|---|---|---|
| C-001 | TBD | TBD | TBD | TBD |

<!-- rom-section: report-impact -->
## Reader-Report Impact

For every non-`Keep` verdict, record the exact parent-report conclusion that must be downgraded, revised, or removed. This audit report must not present an unchanged recommendation after a blocking finding.

- TBD
