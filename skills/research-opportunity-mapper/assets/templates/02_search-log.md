# Search Log

- Domain: {{DOMAIN}}
- Run ID: {{RUN_ID}}
- Task mode: {{TASK_MODE}}
- Discovery lens: {{DISCOVERY_LENS}}
- Evidence window: {{EVIDENCE_WINDOW}}
- Evidence as-of: {{AS_OF_DATE}}

<!-- rom-section: search-policy -->
## Search Policy

- Frontier sensing: prioritize recent authoritative syntheses and representative primary work; record venue/citation signals only as salience signals.
- Claim adjudication: prioritize direct, method-valid, independently informative evidence, including specialist venues, limitations, negative results, and strongest baselines.
- Citation signal rule: record source and query date; use field/year normalization when available; otherwise write `unavailable`.
- Inclusion rules: TBD
- Exclusion rules: TBD
- Coverage stop rule: TBD

<!-- rom-table: search-queries -->
## Queries

| Query ID | Date | Task mode | Discovery lens | Search lane | Source/database | Exact query and filters | Purpose | Results | Screened/selected | Evidence IDs | Miss/limitation | Stop or next-query decision |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Q-001 | {{DATE}} | {{TASK_MODE}} | {{DISCOVERY_LENS}} | canonical-anchor | TBD | TBD | TBD | TBD | TBD | E-001 | TBD | TBD |

Use the applicable lanes: `canonical-anchor`, `frontier-radar`, `SOTA-family`, `direct-neighbor`, `baseline-negative`, and `translation`.

<!-- rom-table: frontier-signals -->
## Frontier Signals

| Evidence ID | Signal type | Value or unavailable | Source | As-of date | Field/year normalized: yes/no/unavailable | Use in decision |
|---|---|---|---|---|---|---|
| E-001 | TBD | unavailable | unavailable | {{AS_OF_DATE}} | unavailable | Retrieval priority only; not confidence. |

<!-- rom-section: seed-expansion -->
## Seed Expansion

| Seed Evidence ID | Relation explored | Records selected | New Evidence IDs | Coverage note |
|---|---|---|---|---|
| E-001 | TBD | TBD | E-002 | TBD |

<!-- rom-section: bounded-negative-evidence -->
## Bounded Negative Evidence

State the databases, queries, dates, filters, languages, adjacent terms, and source types covered. A miss supports only `sparse evidence` or `unsearched`, never priority or absence.

- TBD

<!-- rom-table: coverage-audit -->
## Six-Lane Coverage and Blind Spots

| Lane | Query IDs | Relevant Evidence IDs | Coverage status: covered/thin/query-failed/out-of-scope | Blind spot or failure mode | Next query or stop rationale |
|---|---|---|---|---|---|
| canonical-anchor | Q-001 | E-001 | thin | TBD | TBD |
| frontier-radar | Q-001 | E-001 | thin | TBD | TBD |
| SOTA-family | Q-001 | E-001 | thin | TBD | TBD |
| direct-neighbor | Q-001 | E-001 | thin | TBD | TBD |
| baseline-negative | Q-001 | E-001 | thin | TBD | TBD |
| translation | Q-001 | E-001 | thin | TBD | TBD |
