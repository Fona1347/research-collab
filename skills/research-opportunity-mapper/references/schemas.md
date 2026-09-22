# Artifact and Data Schemas

This file is the normative persisted-data contract. Use `run-modes.md` for semantic completion gates, `evidence-confidence.md` for scientific confidence rules, and `reader-report.md` for the primary human-facing synthesis.

## Contents

- [Supported versions](#supported-versions)
- [Schema 2.0 manifest](#schema-20-manifest)
- [Routing, lens, and status fields](#routing-lens-and-status-fields)
- [Lineage and read-only context](#lineage-and-read-only-context)
- [Artifact profiles](#artifact-profiles)
- [Machine-stable Markdown contracts](#machine-stable-markdown-contracts)
- [Identifiers and cross-artifact closure](#identifiers-and-cross-artifact-closure)
- [Claim and evidence records](#claim-and-evidence-records)
- [Red-team decision propagation](#red-team-decision-propagation)
- [Reader-report closure](#reader-report-closure)
- [Legacy compatibility and migration](#legacy-compatibility-and-migration)

## Supported versions

| Schema | Meaning | Validation behavior |
|---|---|---|
| `1.0` | Legacy eight-artifact landscape; report not required by its manifest contract | Preserve the frozen legacy validator behavior. |
| `1.1` | Legacy landscape with exactly one reader report inferred from `artifact_files`; `primary_artifact` is not required | Preserve legacy behavior. |
| `1.2` | Legacy landscape with a primary reader report and extended report checks | Preserve legacy behavior. |
| `2.0` | Mode-aware contract defined here | Use strict manifest, role, evidence, lineage, and mode gates. |

Reject missing or malformed versions in schema-2 work. Reject unsupported versions such as `1.3`, `2.1`, `3.0`, or `99.0`; do not guess forward compatibility. Historical 1.x runs remain immutable.

## Schema 2.0 manifest

Every new run contains `run-manifest.json` with this shape:

```json
{
  "schema_version": "2.0",
  "skill": "research-opportunity-mapper",
  "skill_version": "2.2.0",
  "validator_version": "2.2.0",
  "run_id": "2026-07-31-example",
  "domain": "example scientific domain",
  "short_task_name": "example",
  "language": "zh-CN",
  "created_at": "2026-07-31T00:00:00+00:00",
  "as_of_date": "2026-07-31",
  "task_mode": "focus",
  "run_type": "focus",
  "discovery_lens": "balanced",
  "primary_domain_lens": "generic-physical-engineering",
  "secondary_domain_lenses": [],
  "domain_lens_notes": null,
  "artifact_profile": "focus-v2",
  "completion_status": "initialized",
  "workflow_contracts": [
    "deep-reading-handoff-v2",
    "opportunity-gates-v2",
    "coverage-tension-v2",
    "route-fast-pilot-v2"
  ],
  "parent_mutation_policy": "child-run-only",
  "routing": {
    "request": "Deepen branch BR-003",
    "requested": "auto",
    "selected": "focus",
    "reason": ["a branch and causal interface are already selected"],
    "confidence": "high"
  },
  "evidence_window": {
    "start": "2021-01-01",
    "end": "2026-07-31",
    "as_of": "2026-07-31",
    "canonical_pre_window_allowed": true
  },
  "frontier_policy": {
    "recent_years_default": 3,
    "canonical_pre_window_allowed": true,
    "citation_signal": "field-year-normalized-when-available",
    "citation_source_and_as_of_required": true,
    "salience_is_not_claim_confidence": true
  },
  "selected_branch": {"id": null, "label": "bounded example interface", "source": "standalone"},
  "lineage": {"parents": []},
  "inherited_ids": {"claims": [], "evidence": [], "capabilities": []},
  "context_sources": [],
  "primary_artifact": "focus_report_example_2026-07-31.md",
  "artifact_files": ["00_intake.md", "..."],
  "artifact_roles": {"intake": "00_intake.md", "reader_report": "focus_report_example_2026-07-31.md"}
}
```

`task_mode` is the canonical human-facing name. `run_type` is a schema/API compatibility alias and must be identical. `routing.selected` must equal both.

`discovery_lens` controls how opportunities are found. `primary_domain_lens`
controls the causal variables, confounds, layer bridges, and baseline contract.
It must be one registered key from `domain-lenses.md`; secondary lenses are a
unique list used only at real interfaces. `custom` requires substantive
`domain_lens_notes` instantiating every Common Lens Interface field.

All artifact values must be canonical safe relative paths: no absolute or
drive-relative path, `.`, `..`, empty segment, NTFS alternate-stream colon,
duplicate filename, or resolved target outside the run directory. Symlink and
junction targets are containment-checked before reading, hashing, parsing, or
copying. `primary_artifact` must be the file assigned to
`artifact_roles.reader_report` and declared in `artifact_files`.

New runs declare the exact additive workflow_contracts for their mode.
Landscape and focus use all four shown above; evidence-audit uses
deep-reading-handoff-v2 and coverage-tension-v2; run-audit uses an empty list.
The field is mandatory, and missing/partial/unknown declarations never disable
checks. New runs use current skill/validator 2.2.0 with schema 2.0. Historical
sealed runs retain their original declarations: daily integrity verification is
not certification under current scientific rules. Replay old rules only by
explicitly invoking the complete archived skill; never downgrade from a manifest.

## Routing, lens, and status fields

Persisted modes:

- `landscape`
- `focus`
- `evidence-audit`
- `run-audit`

Persisted discovery lenses:

- `frontier-led`
- `gray-space-led`
- `balanced`

`primary_domain_lens` is also mandatory and must be one of:
`generic-physical-engineering`, `materials-ferroelectric`,
`multiphysics-modeling`, `semiconductor-device`, `integrated-circuit`,
`neuromorphic-system`, `wave-metasurface`, or `custom`.
`secondary_domain_lenses` is a duplicate-free list of registered keys used
only where the claim crosses a real interface. `custom` is valid only with
nonempty `domain_lens_notes` that instantiate all ten Common Lens Interface
fields in `domain-lenses.md`; otherwise use
`generic-physical-engineering`.
`custom` notes use exactly one labeled, substantive entry for each canonical
slot (`Decision object` through `Decisive test`), separated by newlines or
semicolons; the registered Chinese aliases are equivalent. Init, copy-upgrade,
direct validation, and run-audit parent-manifest recomputation share the same
parser. Unicode/zero-width/punctuation normalization prevents disguised
`N/A`, `same as above`, and equivalent Chinese placeholders; slot-label echoes,
duplicate labels, cross-slot repeated values, free prose, empty values, and
missing slots are rejected before the run or its audit can pass.

`auto` is legal only in `routing.requested`. It is illegal in `task_mode`, `run_type`, and `routing.selected`.

Routing confidence is `low`, `moderate`, or `high`. Keep at least one nonempty reason. If `requested` differs from `selected`, preserve the original request or a bounded summary.

Completion states:

| State | Meaning |
|---|---|
| `initialized` | Templates created; not a deliverable. |
| `in-progress` | Work is active and incomplete. |
| `ready-for-validation` | Author asserts artifacts are populated; strict validation still required. |
| `complete` | Mode-specific strict validation passed and scientific limitations are reported. |
| `migrated-needs-review` | Legacy structure was copied into v2 without claiming v2 scientific completion. |
| `superseded` | A newer immutable child/revision replaces this run for decisions. |

Strict delivery requires `complete`. Migration and initialized states must fail or warn under strict validation.

## Lineage and read-only context

Each `lineage.parents[]` record contains:

| Field | Requirement |
|---|---|
| `run_id` | Exact source run ID. |
| `relation` | `extends-landscape`, `focuses-branch`, `supplements-evidence`, `audits-run`, or `migrated-copy`. |
| `workspace_relpath` | Workspace-relative parent directory, never the only absolute path. |
| `source_manifest_sha256` | 64 lowercase hexadecimal characters. |
| `source_artifact_sha256` | Hash map for inherited/audited source artifacts. |

`focus` with a parent declares `selected_branch`. Despite the compatibility field
name, its ID may be a parent `BR-###` branch, `C-###` route, or `I-###` open
interface and must resolve in the recorded parent snapshot. Free-text labels are
allowed only for standalone focus runs; a parent-backed label must first be
resolved to a stable parent ID. `run-audit` always declares a parent.
`evidence-audit` declares a parent or at least one explicit read-only context
source. Inherited claim, evidence, and capability IDs must exist in the parent
snapshot.

Each `context_sources[]` record contains a stable, unique `CTX-###` in
`source_id`, workspace-relative path, role, `access: read-only`, file/directory
kind, and a SHA-256 snapshot for files. A valid context `source_id` enters the
external ID closure, so visible references to it do not require a local table
definition. Context provides decision/capability input; it is not scientific
evidence by itself.

Use `supplement-only` for evidence/run audits. Do not overwrite a parent run. A changed parent hash invalidates inherited facts until re-audited.

`run-audit` declares exactly one parent. For `audits-run`,
`source_artifact_sha256` freezes the complete file tree observed at audit
initialization, including undeclared files and excluding `run-manifest.json`
(which has its own hash). This differs from inheritance relations, whose hash
map follows declared source artifacts. Declared-but-missing files do not block
audit initialization; they become deterministic inventory findings. Schema 1.0
has no authoritative reader report, so its citation projection is explicitly
`not-applicable-no-declared-reader`. Schema 1.1 infers the reader only when
`artifact_files` contains exactly one safe entry matching
`map_report_<short_task_name>_<YYYY-MM-DD>.md`; it neither requires nor relies
on `primary_artifact`. Schema 1.2 uses `primary_artifact`, and schema 2.0 uses
`artifact_roles.reader_report`.

`scripts/parent_audit.py` recomputes the parent artifact, manifest, ID, and
citation projections. The child tables must reproduce them exactly. A parent
snapshot mismatch is an identity failure; a faithfully reported parent defect
is an auditable finding. For every manifest row, `Required repair` is the exact
value returned by `canonical_manifest_repair(Check, Result)`; for `pass` and
`not-applicable` this is `retain observed state`.

Every manifest row contains exactly one syntactically valid `D-###`, and that ID
resolves to exactly one row in `decisions`. A `pass` or `not-applicable` row must
bind a `Keep` decision.

Every recomputed `Result=fail` manifest row has severity `high` or `blocking`
and forms a one-to-one closure with a decision ID used by no other manifest row.
That ID also may not be used by any `attack-register` row, and it must
resolve to exactly one `Downgrade`, `Revise`, or `Kill` decision. The decision's
`Target ID` and `Affected decision target IDs` are the same single authoritative
run-audit route/claim. Its Decision text is exactly
`Parent manifest failure [<check>]`, Trigger Attack IDs is exactly
`not-applicable: deterministic manifest check`, and Owner/next action is the
canonical repair.

The reader Finding is exactly lowercase
`parent manifest failure [<check>]`. When any failures exist, reader `integrity`
contains all and only those failure rows exactly once, with identical Evidence,
high/blocking Severity, the bound decision Verdict, canonical Repair, and
Decision ID. The clean-snapshot `Keep` sentinel is permitted only when the
recomputed failure set is empty.

A recomputed `id-closure` status of `dangling-reference` or
`duplicate-definition`, and every registered abnormal `citation-closure` status,
is a deterministic parent anomaly. Each anomaly has a meaningful `Repair`, one
valid `D-###` resolving to exactly one non-`Keep` decision, and the same single
authoritative Target/Affected route or claim. It does not reuse a
manifest-failure decision. A dedicated anomaly ID appears on only one anomaly
row and its decision uses `Parent <marker> anomaly [<key>:<status>]`, Trigger
Attack IDs `not-applicable: deterministic parent anomaly`, and Owner/next action
equal to `Repair`. The stable lowercase binding source is
`parent <marker> anomaly [<key>:<status>]`; a bracketed citation key is
normalized to its inner reference number.

An anomaly may instead share the same non-`Keep` decision as an attack. That is
a joint disposition: the attack decision text, trigger, and owner are not
rewritten. All anomaly bindings participate in strongest aggregation. Working
and reader `route-verdicts` match target, finding, verdict, allowed conclusion,
repair, and Decision ID; a selected dedicated anomaly binding uses its stable
lowercase source and exact `Repair` in both.

## Artifact profiles

Schema 2 uses semantic `artifact_roles`; validators do not infer meaning from a filename alone.

### `landscape-v2`

| Role | Default file |
|---|---|
| `intake` | `00_intake.md` |
| `breadth_ledger` | `01_breadth-ledger.md` |
| `search_log` | `02_search-log.md` |
| `evidence_matrix` | `03_evidence-matrix.md` |
| `research_map` | `04_research-map.md` |
| `candidate_portfolio` | `05_candidate-portfolio.md` |
| `red_team` | `06_red-team.md` |
| `decision_log` | `07_decision-log.md` |
| `reader_report` | `map_report_<short>_<date>.md` |

### `focus-v2`

| Role | Default file |
|---|---|
| `intake` | `00_intake.md` |
| `focus_scope` | `01_focus-scope.md` |
| `search_log` | `02_search-log.md` |
| `evidence_matrix` | `03_evidence-matrix.md` |
| `claim_mechanism_map` | `04_claim-mechanism-map.md` |
| `route_protocol` | `05_route-protocol.md` |
| `red_team` | `06_red-team.md` |
| `decision_log` | `07_decision-log.md` |
| `reader_report` | `focus_report_<short>_<date>.md` |

### `evidence-audit-v2`

| Role | Default file |
|---|---|
| `audit_scope` | `00_audit-scope.md` |
| `claim_register` | `01_claim-register.md` |
| `search_log` | `02_search-log.md` |
| `evidence_matrix` | `03_evidence-matrix.md` |
| `confidence_assessment` | `04_confidence-assessment.md` |
| `gap_plan` | `05_gap-plan.md` |
| `red_team` | `06_red-team.md` |
| `decision_log` | `07_decision-log.md` |
| `reader_report` | `evidence_audit_report_<short>_<date>.md` |

### `run-audit-v2`

| Role | Default file |
|---|---|
| `audit_scope` | `00_audit-scope.md` |
| `artifact_inventory` | `01_artifact-inventory.md` |
| `traceability_audit` | `02_traceability-audit.md` |
| `evidence_audit` | `03_evidence-audit.md` |
| `reasoning_audit` | `04_reasoning-audit.md` |
| `route_verdicts` | `05_route-verdicts.md` |
| `red_team` | `06_red-team.md` |
| `decision_log` | `07_decision-log.md` |
| `reader_report` | `run_audit_report_<short>_<date>.md` |

Read `run-modes.md` for role semantics and mode-specific completion gates. Focus and audit modes do not inherit landscape-wide breadth or risk quotas.

## Machine-stable Markdown contracts

Human headings may be Chinese, English, or descriptive. Put a stable marker immediately before contract sections and tables:

```markdown
<!-- rom-section: decision-summary -->
## 一页决策摘要

<!-- rom-table: claim-confidence -->
## Claim Confidence

| Claim ID | ... |
|---|---|
```

Validators inspect visible content after the marker, not keyword occurrences in comments or fenced code. Contract tables require:

- exact required column names for the active schema;
- a valid Markdown separator row;
- consistent row width;
- unique definition IDs;
- no unresolved `TBD`, `TODO`, `待填`, or `{{TOKEN}}` value;
- substantive values rather than repeated punctuation or copied headers.

Escape a literal table pipe as `\|`.

## Identifiers and cross-artifact closure

Use stable prefixes:

- `BR-###`: landscape branch.
- `B-###`: bottleneck/persistence claim.
- `M-###`: causal or physical mechanism claim.
- `S-###`: system/architecture claim.
- `C-###`: candidate or route.
- `CL-###`: general claim when B/M/S typing is inappropriate.
- `E-###`: evidence record.
- `Q-###`: search query.
- `CAP-###`: capability entry.
- `A-###`: adversarial attack/finding.
- `D-###`: decision.
- `I-###`: open interface.
- `GS-###`: gray-space mismatch entry.
- `H-###`: competing hypothesis.
- `G-###`: evidence gap.
- `F-###`: integrity or audit finding.
- `ART-###`: audited artifact entry.
- `R-###`: remediation action.
- `CTX-###`: read-only context source (stored in the manifest).
- `DR-###`: decision-linked Deep Reading handoff request.

`C-###` is a route/candidate identifier, not an atomic claim. Use `B-###`,
`M-###`, `S-###`, or `CL-###` in `inherited_ids.claims` and in claim-only table
columns.

Deep Reading handoff requests use DR-### identifiers.

An ID has one authoritative definition and may have many references. Validate at least:

- evidence records reference defined claims;
- query rows reference defined evidence or explicitly `none`;
- route artifacts reference defined claims/evidence/capabilities;
- red-team attacks reference a defined target and decision;
- every non-`Keep` attack appears in the decision log and reader report;
- report citations resolve to evidence records;
- no dangling or duplicate definition IDs.

### Authoritative definition roles

For schema 2, an ID is defined only by the exact definition column of the first
table bound to its registered `rom-table` marker in the manifest-declared
artifact role below:

| Definition marker | Exact ID column | Authoritative artifact role |
|---|---|---|
| `atomic-claims` | `Claim ID` | `evidence_matrix` |
| `breadth-branches` | `Branch ID` | `breadth_ledger` |
| `candidate-routes`, `rejected-routes` | `Candidate ID` | `candidate_portfolio` |
| `local-alternatives` | `Alternative ID` | `focus_scope` |
| `evidence-records` | `Evidence ID` | `evidence_matrix` |
| `deep-reading-handoff` | `Deep-read request ID` | `evidence_matrix` |
| `search-queries` | `Query ID` | `search_log` |
| `capability-passport` | `Capability ID` | `intake` |
| `attack-register` | `Attack ID` | `red_team` |
| `decisions` | `Decision ID` | `decision_log` |
| `open-interfaces` | `Interface ID` | `research_map` |
| `gray-space-mismatch` | `Mismatch ID` | `breadth_ledger` |
| `competing-hypotheses` | `Hypothesis ID` | `claim_mechanism_map` |
| `evidence-gaps` | `Gap ID` | `gap_plan` |
| `artifact-inventory` | `Artifact ID` | `artifact_inventory` |
| `dangling-references` | `Finding ID` | `traceability_audit` |
| `confidence-violations` | `Finding ID` | `evidence_audit` |
| `remediation-plan` | `Repair ID` | `route_verdicts` |

Every `capability-passport` row has a meaningful `Source or evidence` cell, not
a blank, placeholder, or generic status label. For both `Observed` and
`Reported`, that cell may not consist only of an uncertain basis such as `not
yet verified`, `unverified`, `unknown`, `assumed`, `learning only`, `planned
only`, or `not documented` (including equivalent Chinese wording). `Reported`
does not require independent replication, but it must name the report, record,
or other source on which the state is based.

An ID-looking token in prose, a comment, a fenced example, a reader report,
a reference column, a second table after the same marker, or the correct marked
table in the wrong artifact role is a reference at most; it does not define the
ID. A wrong-role pseudo-definition cannot repair a dangling reference or become
an inheritable parent fact. Exact header spelling, ID shape, marker binding,
manifest role, and uniqueness are all part of definition authority. Frozen
schema-1 validation keeps its legacy behavior; do not retroactively apply this
schema-2 authority model to an immutable legacy run.

Owner binding also applies to non-definition contract tables. Every registered
working marker may appear only in one of its declared artifact roles; a same-name
table in an earlier wrong role is an error and cannot shadow the authoritative
table. Decision-critical lookups (`claim-register`, attack/decision tables,
mode main-target tables, and run-audit claim-only tables) resolve by owner role
rather than first match.

In particular, evidence-audit `claim-register`, focus `focus-routes`,
reader-report route/claim tables, and run-audit `route-verdicts` project or
adjudicate IDs defined elsewhere; their ID-looking first columns are references,
not new definitions. For evidence-audit, the unique Claim-ID set in
`claim-register` must exactly equal the unique Claim-ID set declared by the
`target-claims` scope table. A locally valid but undeclared `B/M/S/CL-###`
cannot silently replace the requested target. For run-audit, target authority
comes from the recomputed immutable parent projection. This local audit boundary
accepts legacy candidate forms `C-L##`, `C-M##`, and `C-H##` only when present
in that parent; it does not expand the global schema-2 candidate definition
shape, which remains `C-###`.

Within `run-audit`, a parent route may be the main adjudication target, but it
cannot impersonate an atomic claim. `audited-claims`, `confidence-violations`,
`contradictions`, `open-position-audit`, and `evidence-independence` Claim-ID
columns accept only parent-authoritative `B/M/S/CL-###` IDs. The reader
`scientific-red-team` Claim field likewise contains exactly one such parent
claim (plus an optional numbered citation), even when `route-verdicts` targets
a parent `C-###` or legacy `C-L/M/H##` route.

## Claim and evidence records

The `atomic-claims` table records claim ID, type, bounded proposition, scope/regime, epistemic label, decision-critical flag, status, and optional parent claim.

The `evidence-records` table records:

```text
Evidence ID; Claim IDs; Source role; Stance; Directness;
Study/source type; Publication status; Core contribution;
Exact supported/limited claim; Scope/regime; Method-validity note;
Independence/replication; Source metadata; DOI/stable URL;
Provenance locator; Full-context status; verification_depth; Verification;
Canonical cross-run ref; Frontier signal; Citation signal/source/as-of;
Reader ref
```

verification_depth is one of metadata, abstract, full-text, or
canonical-deep-read and must agree with Full-context status.
canonical-deep-read also requires Verification=verified and a cross-run
reference to a canonical Deep Reading artifact. Canonical files are
paper-package.md, reading-report.md, auxiliary-literature-table.md,
external-evidence-matrix.md, and view-report-audit.md; derived view-report.md
is forbidden as evidence. deep-reading-handoff records the paper key, target
claim/route, decision-changing question, priority, lifecycle status, run path,
canonical refs, imported Evidence IDs, and disposition. Use absolute paths or
workspace-relative paths with --workspace-root. Resolve actual files and typed
claim/source/evidence record IDs in their owning canonical run; match a main or
auxiliary source identity as appropriate. Every canonical-depth row has exactly
one imported handoff owner. Non-imported requests list no imported Evidence IDs.
The installed sibling Deep Reading checker is used by default; maintenance-source
checks pass --canonical-checker path/to/check_canonical.py explicitly. Missing
checker or malformed canonical content fails closed, with no network fallback.

coverage-audit contains each of the six stable search lanes exactly once. A
lane marked out-of-scope requires an explained boundary and stop rationale;
bare N/A, not applicable, unknown or equivalent sentinels are not explanations.
The appropriateness of a substantive exclusion remains a scientific review. A
covered row requires a known positive same-lane result count and evidence selected
by its cited Query IDs. Unknown counts are not positive. The contradictions row
also records Tension type: direct-conflict/evidence-gap/condition-difference,
the source-bound condition delta and one exact
adjudication: support-dominant, limit-dominant, condition-split, or unresolved.

For landscape and focus, opportunity-gates contains exactly one row per active
route. Each of openness, contribution, and feasibility is pass, conditional,
fail, or unknown. Compute Overall without discretion:

1. any fail -> no-go;
2. otherwise any unknown -> defer;
3. otherwise any conditional -> conditional-go;
4. otherwise -> go.

Every gate row retains known Evidence IDs, its binding condition/next check, and
a recall caveat naming bounded search coverage. route-fast-pilots selects only
at most three go or conditional-go routes, ranks them contiguously from one,
contrasts two distinct hypotheses, and records a discriminating test,
observable, one-to-fourteen-day horizon, resource cap, advance threshold, and
kill/revise threshold. If no route is eligible, its header-only empty table is
valid; do not manufacture pilots. Fourteen days does not limit other planning
horizons. Zero candidates also permits empty candidate, shared-platform, scorecard,
rejected-route, gate, pilot and reader route collections, with explicit
Selection outcome: no-candidate and atomic-claim red-team/decision closure.
Focus likewise permits 0/1/several substantive candidates: if nonempty, exactly
one primary, with optional comparator/fallback candidate roles. These design
roles need no distinct candidate ID when covered by baseline/hypotheses and
activation-rule fields. For zero focus, local-alternatives, focus-routes,
claim-null-test-threshold, staged-execution, route-boundaries, outcomes and
reader route collections are empty. Both zero-candidate modes still need a
claim-linked information check or bounded stop with inputs and deliverable.

`Claim IDs` is a machine relation, not a topic annotation. It contains one or
more defined `B/M/S/CL-###` IDs to which the row's stance applies, or exactly
`none` for discovery-only context that is not used in a confidence decision.
If one source supports one claim but limits another, split it into separate
evidence rows so each row has one unambiguous stance over all listed claims.

Use exactly one `Stance` value per evidence row:

| Stance | Meaning | Legal confidence use |
|---|---|---|
| `supports` | Responsive evidence favors the listed bounded claim(s). | May appear in `Supporting Evidence IDs`. |
| `limits` | Narrows scope, regime, wording, or applicability without directly negating the claim. | Must appear in `Limiting Evidence IDs`, not supporting. |
| `contradicts` | Responsive evidence conflicts with the listed claim in an overlapping regime. | Must appear in `Limiting Evidence IDs` and conflict handling. |
| `mixed` | The same responsive result has materially supporting and limiting components that cannot be separated without distortion. | If used as supporting evidence, it must also appear in `Limiting Evidence IDs`; its limiting component binds caps and allowed wording. |
| `context` | Defines terminology, frontier salience, or background but does not adjudicate the claim. | Cannot satisfy supporting or limiting evidence requirements. |

Every evidence ID used in a claim-confidence row must list that claim in
`Claim IDs`, and its stance must agree with whether it is cited as supporting
or limiting. `Source role` and `Stance` are independent: for example,
`frontier-signal` describes why a record was retrieved, while `context`
states that it cannot support scientific confidence. Multiple source roles do
not authorize multiple or contradictory stances in one row.

The `claim-confidence` or mode-specific confidence table records supporting and
limiting IDs, directness, full-context status, method validity, independence,
conflict, applicability, confidence, `Active cap codes`, a human-readable cap
reason, allowed wording, and upgrade/overturn evidence. Use `none` only when no
machine cap applies; otherwise list every active code from
`evidence-confidence.md`.
It contains at most one row per authoritative claim and exactly one row for
every decision-critical claim.

For `evidence-audit`, `target-claims` declares a unique target set.
`claim-register`, canonical `claim-confidence`, `confidence-assessment`,
`allowed-wording`, and reader `claim-verdicts` each contain exactly that set,
with every target occurring exactly once. Confidence and Active cap codes agree
across canonical, assessment, and reader rows; allowed wording agrees across all
four projections; parent impact agrees between assessment and reader. Every
target has one or more `evidence-gaps` rows, but gaps may repeat a target and
must never name an undeclared claim.

Apply the exact hard caps in `evidence-confidence.md`. The validator checks declared records for internal consistency; it cannot determine whether a paper or mechanism is scientifically true.

The `decisions` table records:

```text
Decision ID; Date; Target ID; Affected decision target IDs;
Status: Keep/Downgrade/Revise/Kill; Decision; Evidence IDs; Inference;
Alternative; Trigger Attack IDs; Reversal condition; Owner/next action
```

`Target ID` is the claim, route, or other defined object directly attacked.
`Affected decision target IDs` is a non-empty list of defined or inherited IDs
whose authoritative main-mode disposition must change because of that attack.
The two fields may be identical, but they are deliberately separate: an attack
on a mechanism claim can bind one or more route decisions. Aggregate attacks by
each affected target and apply the strongest linked verdict in the order
`Kill > Revise > Downgrade > Keep`.

## Red-team decision propagation

The `attack-register` table records:

```text
Attack ID; target claim/route; attack surface; strongest objection;
Evidence IDs or test; severity; required repair/discriminating test;
Keep/Downgrade/Revise/Kill verdict; Decision ID; status
```

Use only the eight attack-surface keys in `critical-thinking.md`, severity
`low/medium/high/blocking`, and status
`open/unresolved/accepted/mitigated/resolved/closed`. The first three statuses
remain unresolved for gating; unresolved `high` or `blocking` attacks cannot be
`Keep`.

Every run must cover all eight surfaces: problem adequacy, mechanism, evidence,
open position, capability, cross-scale inference, baseline/system cost, and
bio-inspired translation. A non-biological run records the last surface as an
explicit bounded not-applicable test rather than omitting it.


For `run-audit`, the same maximum also includes every manifest-failure closure
decision and recomputed parent ID/citation-anomaly decision bound to that
route/claim. The working and reader `route-verdicts` rows
must use the maximum across attacks, manifest failures, and anomalies and a Decision
ID that carries it. If an attack and a manifest failure tie at the maximum rank,
an equally strong manifest-failure Decision ID is binding; if several integrity
decisions tie, any one of those maximum-rank integrity IDs may bind.
A high or blocking finding cannot remain decorative. Every attack links to a
`D-###`; the decision log must repeat the directly attacked `Target ID`, name at
least one `Affected decision target ID`, and the primary report must reproduce
the complete attack projection. Each affected main route/claim disposition must
adopt the strongest verdict linked to that affected ID rather than leaving the
audit in a side table.

This propagation rule applies to every non-`Keep` attack, not only high or
blocking ones. The mode's main-target table is `candidate-routes` for landscape,
`local-alternatives` for focus, `claim-register` for evidence-audit, and
`route-verdicts` for run-audit. Every target is unique and type-checked. The two
route modes use their defined `C-###` IDs; evidence-audit may select only the
local atomic or explicitly inherited claim IDs declared in `target-claims`;
run-audit may select only claim/route IDs recomputed from the immutable parent
snapshot, including a legacy `C-L##`/`C-M##`/`C-H##` only under that local
parent contract. A-008 always owns `bio-inspired-translation`, independent of
whether the run contains a biological premise. Its Target, Verdict, and Decision
ID must align with every registered owner audit and the reader even for a
non-biological run; a complete non-N/A translation chain is additionally
required only when a biological premise is triggered. For each affected
decision target, the working table, decision log, and reader-facing decision
surface must adopt the strongest binding verdict in the order
`Kill > Revise > Downgrade > Keep`.

## Reader-report closure

The `reader_report` is the primary delivery. Use the localized, mode-specific template and the narrative contract in `reader-report.md`.

Landscape reader `decision-summary` reproduces the complete authoritative
`C-### -> low|medium|high` mapping from `candidate-routes` exactly once per
candidate. Focus reader `recommended-routes` reproduces the complete
`C-### -> primary|comparator|fallback` mapping from `focus-routes` exactly once
per route. A role or risk label attached to the wrong C-ID is a closure failure
even when the counts are otherwise correct.

References must be numbered and contain a DOI or stable link. For schema-2 modes
other than `run-audit`, every non-sentinel evidence `Reader ref` maps to one
numbered reader reference, and every numbered reader reference maps back to one
evidence record; duplicate or orphan mappings fail. The normalized DOI or stable
link must match on both sides. `unavailable`, `not applicable`, and `none` are
the only non-mapping sentinels. Reader reference numbers remain unique,
contiguous, and cited in the report body. A run-audit report's own bibliography
is closed against its own body, while its `citation-closure` table independently
projects the parent report and evidence matrix. Do not expose internal retrieval
IDs in the report. Keep detailed provenance in the evidence matrix.

Report validation checks structure, citation closure, dispositions, and declared evidence boundaries. It does not prove novelty, feasibility, or scientific truth.

## Legacy compatibility and migration

Do not edit historical 1.x runs to make them appear schema 2 compliant. Validate them through the frozen legacy branch.

Use the non-destructive migration helper only when a copy is needed:

```powershell
python scripts/upgrade_run.py "<legacy-run>" `
  --copy-to "<new-run-directory>" `
  --workspace-root "<workspace-root>" `
  --lens balanced `
  --dry-run
```

Migration supports explicit `1.0`, `1.1`, or `1.2` landscapes only; it never upgrades in place, ignores undeclared binary attachments, records source hashes, and sets `migrated-needs-review`. Create a child `focus`, `evidence-audit`, or `run-audit` instead of pretending a legacy landscape was one of those modes.

## Reader presentation and compatibility

Schema 2.0 keeps the same authority, IDs, source closure, scientific gates and
decision propagation. New localized templates use the narrative envelope and
explicit appendix projections in [reader-report.md](reader-report.md).
Existing section-bound reader tables, including wide rows and the 2.1 compact
landscape/focus rows, remain readable under the current checks. Presentation
is recognized from report markers, never by downgrading a manifest or loading
a release-specific parser. Sealed runs retain their original files and versions.
