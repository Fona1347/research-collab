# Evidence Kernel Contract (v1.1)

Use this reference when initializing or updating a deep-reading run's canonical Markdown records. It defines data ownership, field vocabularies, authorization resolution, evidence selection, epistemic controls, and the six fail-fast Gates. Keep orchestration and resource routing in `SKILL.md`; keep the detailed records here.

## Contents

- [Contract principles](#contract-principles)
- [Canonical ownership](#canonical-ownership)
- [Identifiers, missing values, and locators](#identifiers-missing-values-and-locators)
- [Bibliographic normalization and reader-facing keys](#bibliographic-normalization-and-reader-facing-keys)
- [Run Contract](#run-contract)
- [Output resolution and run-directory naming](#output-resolution-and-run-directory-naming)
- [Main-PDF staging](#main-pdf-staging)
- [Main-paper identity](#main-paper-identity)
- [Claim and Condition Registry](#claim-and-condition-registry)
- [Source Registry](#source-registry)
- [Evidence Ledger](#evidence-ledger)
- [Authorization resolution](#authorization-resolution)
- [Budgets and counters](#budgets-and-counters)
- [Candidate selection and stopping](#candidate-selection-and-stopping)
- [Review roles and correlated cross-checks](#review-roles-and-correlated-cross-checks)
- [Epistemic rules](#epistemic-rules)
- [Six fail-fast Gates](#six-fail-fast-gates)
- [Gate recording and correction order](#gate-recording-and-correction-order)

## Contract principles

1. Use structured Markdown tables as the canonical data layer. Do not create parallel JSONL ledgers, schemas, migrations, renderers, or workflow state files.
2. Give each field exactly one canonical owner. Other artifacts may cite a stable ID, but must not maintain an independently editable copy of the same fact.
3. Separate relevance, acquisition, parsing, reading, verification, and citation state. Never infer one state from another.
4. Treat `view-report.md` and all optional summaries as derived views. They may not originate a key scientific claim or final judgment.
5. Correct canonical records first, then refresh every affected derived view. A stale derived view is a delivery failure, not an alternative interpretation.
6. Preserve uncertainty and unresolved scope. `not established within scope` is a valid outcome.

## Canonical ownership

| Artifact | Canonical entity or field family | May derive, but must not redefine |
| --- | --- | --- |
| `paper-package.md` | Run Contract and main-paper identity | Gate summaries, report scope labels |
| `reading-report.md` | Claim and Condition Registry | Reader-facing claims, review summaries |
| `auxiliary-literature-table.md` | Source Registry | Evidence cards, auxiliary briefs, reference lists |
| `external-evidence-matrix.md` | Evidence Ledger | External-validation prose, confidence summaries |
| `assets/_manifest.md` | Asset Registry | Figure embeds and exhibit lists |
| `view-report-audit.md` | Gate results and Report Claim Map | Delivery summary |
| `view-report.md` | Derived reader-facing report only | Presentation handoff |

Do not copy a final assessment into a derived table and later edit it there. Link the derived row to its canonical `Claim ID` or `Evidence ID` and apply any correction upstream.

## Identifiers, missing values, and locators

Use stable, zero-padded identifiers within one run:

| Entity | Format | Rule |
| --- | --- | --- |
| Claim | `C-001` | Assign once; do not renumber after exclusion or weakening |
| Source | `S-001` | Assign after metadata deduplication |
| Evidence | `E-001` | One source-to-claim relation per row; split materially different conditions or relations |

Use `none`, `not-applicable`, `unknown`, or `blocked: <reason>` instead of an ambiguous blank cell. Do not use `not-applicable` to conceal an unperformed required check.

Prefer a human-verifiable locator in this order:

1. page plus section and figure/panel, table, equation, or named data point;
2. section plus figure/panel, table, equation, or named data point when stable page numbers do not exist;
3. stable HTML heading or paragraph anchor;
4. MinerU block identifier only when the preceding locators are unavailable.

Record why no stronger locator is available. Evidence without a usable locator cannot be `strong` and cannot support an unqualified strong statement.

Carry conditions with every quantitative or mechanistic locator. At minimum record the applicable material/system, device or model, temperature, bias/voltage, pulse width or duration, measurement/readout method, sample size or cycle count, and any other condition that changes comparability. Use `not reported` when the paper omits a condition.

## Bibliographic normalization and reader-facing keys

Use one bibliographic normalization method for automatic run names and reader-facing external footnotes. Do not create a second ad hoc citation-key convention in `view-report.md`.

For an external journal article, establish the following canonical fields before assigning a reader-facing key:

- `first_author_full_name`: the first author's complete given name followed by family name, such as `Yujian Hu`. Resolve it from the full text, publisher record, or another authoritative bibliographic record. Do not expand initials by guesswork. Preserve Unicode letters, diacritics, meaningful hyphens, apostrophes, and multi-token names; collapse whitespace to single spaces.
- `standard_journal_abbreviation`: prefer a verified Zotero `journalAbbreviation`, then the publisher's official abbreviation, then an authoritative NLM/Index Medicus abbreviation. DOI metadata may establish article identity and may supply the abbreviation only when it explicitly does so. Never invent an abbreviation by manually shortening the title.
- `publication_year`: the four-digit year for the cited article version. When online-first and issue years differ, use the canonical year of the version actually cited and record the date distinction in the complete definition when relevant.

Normalize each key component by preserving Unicode letters, combining marks, numbers, meaningful hyphens, apostrophes, and single spaces; replace underscores, control characters, Windows-invalid characters, and other structural punctuation runs with one space; then collapse and trim whitespace. Reserve underscores for the key separators. The base reader-facing key is exactly:

```text
<first-author given name> <first-author family name>_<standard journal abbreviation>_<YYYY>
```

For example:

```markdown
[^Yujian Hu_Nat Med_2025]
```

If two or more distinct deduplicated sources cited in the same reader-facing report produce the same base key, sort that cited collision set by normalized DOI, then normalized title when DOI is absent, and append `_a`, `_b`, and so on. Use no suffix when only one member of a possible collision set is cited; whenever suffixes are present, the report must contain a contiguous set beginning with `_a` and `_b`. Reuse one key for every occurrence of the same source. A source with an unverified full name, unresolved official abbreviation, or unestablished year cannot receive a reader-facing key; either resolve the metadata or remove/downgrade the citation before G5.

Derive hidden backlink IDs from the same key so that the first occurrence is `ref-<key-slug>-1`, the second is `ref-<key-slug>-2`, and so on. Create `<key-slug>` by case-folding the key and replacing every run of non-letter/non-number characters with one hyphen. Preserve Unicode letters and numbers, trim hyphens, and keep the occurrence suffix. This slug is an internal anchor only; it must not replace the semantic key shown in Markdown source.

## Run Contract

Place a `Run Contract` table near the start of `paper-package.md`.

| Field | Allowed value or required content |
| --- | --- |
| `evidence_contract` | Exactly `v1.1` |
| `reader_citation_contract` | Exactly `semantic-footnote-v1` for newly generated reader-facing reports; historical artifacts created before this contract may omit the field, and must not be retrofitted unless the report is regenerated |
| `paper_identity` | Title plus DOI or another canonical identifier; record an identity limitation if none exists |
| `task_name` | Derived run-directory basename, or the basename of an explicitly named run directory |
| `output_directory` | User-approved run directory |
| `task` | `full-report`, `focused-analysis`, or `plan-only` |
| `validation` | `standard`, `main-paper-only`, `fully-local`, or `custom` |
| `presentation_handoff` | `yes` or `no` |
| `permissions` | Link to the resolved permission table in the same artifact |
| `candidate_policy` | `soft-target` or `hard-limit`; use `hard-limit` only from an explicit user limit |
| `candidate_target` | Default `15-30`; a target is not a hard limit |
| `candidate_hard_limit` | Default `null`; set only from an explicit user limit |
| `materialized_aux_pdf_limit` | Default `10` under authorized standard validation |
| `parser_submission_limit` | Default `10` under authorized standard validation |
| `cited_external_source_limit` | Default `null` |
| `candidate_count` | Current deduplicated metadata-candidate count; initialize at `0` |
| `materialized_aux_pdf_count` | Current distinct materialized auxiliary-PDF count; initialize at `0` |
| `parser_submission_count` | Current distinct first-submission count; initialize at `0` |
| `verified_external_source_count` | Current full-read, locator-verified external-source count; initialize at `0` |
| `cited_external_source_count` | Current externally cited source count; initialize at `0` |
| `user_overrides` | Exact user additions, exclusions, and hard limits, or `none` |
| `excluded_resources` | Supplementary, restricted, sensitive, or other explicitly excluded resources |

Treat the three axes as orthogonal. For example, `task=full-report` does not imply `validation=standard`, and `presentation_handoff=yes` does not authorize presentation generation.

## Output resolution and run-directory naming

Treat workspace `.paper-collab.yaml` as a stored path preference, not an authorization record. Accept exactly one required setting:

```yaml
default_output_parent: 'D:\paper-reports'
```

Read this file only from the workspace root and require an absolute `default_output_parent`. If the file is missing or unreadable, its YAML is malformed, the setting is missing, or the value is not absolute, treat the preference as unresolved and ask for an absolute default parent; do not invent, normalize, or silently substitute a fallback. Resolve output in this order:

1. preserve a complete run directory explicitly supplied for the current task;
2. append an automatically derived `task_name` to an explicit output parent;
3. append `task_name` to the workspace configuration's default parent;
4. when none is available, ask for an absolute default parent and do not silently fall back.

If a higher-priority workspace rule requires confirmation for each research output, show the resolved full directory and obtain that confirmation before creating it. An explicit one-run directory does not silently replace the stored default. If a complete explicit directory already exists and may contain work, stop and ask for a new directory; do not merge or append a suffix to a name the user explicitly chose. Never migrate, rename, merge, or reorganize an existing or legacy run directory.

For automatically named child directories, use these exact forms:

```text
Zotero item: <item-key>-<first-author-full-name>_<year>_<journal-or-publisher>-<short-title>
Other input: <first-author-full-name>-<year>-<journal-or-publisher>-<short-title>
```

- Preserve the Zotero item key exactly and place it first whenever the main paper is identified from a Zotero item.
- Use the first author's complete canonical name in given-name-then-family-name order and preserve single internal spaces. Preserve a one-field institutional author; use `unknown-author` when no author can be established.
- Prefer an official journal abbreviation for journal articles and an official publisher or venue abbreviation for other item types. For Zotero, prefer `journalAbbreviation`, then the applicable publication or publisher field; use authoritative DOI metadata when needed. If no official abbreviation exists, use the normalized full journal or publisher name and set the completion notice; use `unknown-venue` when no venue can be established.
- Use the four-digit publication year; use `undated` when it cannot be established.
- Form `short-title` from a distinctive portion of the canonical title: normally 3-8 content words for a space-delimited title or 6-20 characters for a CJK title. Use `untitled` when no title can be established.
- In author and venue segments, preserve Unicode letters/numbers, diacritics, apostrophes, meaningful hyphens, and single spaces; replace every other punctuation, underscore, control-character, or Windows-invalid-character run with one space, then collapse and trim whitespace. Normalize every `short-title` whitespace or punctuation run to one hyphen and trim leading or trailing hyphens, dots, and spaces. Reserve structural underscores for the Zotero form.
- Keep the final `task_name`, including a collision suffix, at most 100 characters by shortening only `short-title`. Do not remove or truncate the item key, complete author, year, or venue. If those fixed segments exceed the limit, require an explicit complete run directory.
- If an automatically named directory exists, do not overwrite or merge it. Append the smallest available numeric suffix, starting with `-2`, and shorten `short-title` if needed to preserve the length limit.

Examples:

```text
ABCD1234-John Smith_2024_Nat Commun-Ferroelectric-Memory
John Smith-2024-Nat Commun-Ferroelectric-Memory
ABCD1234-Li Ming_undated_unknown-venue-二维铁电存储器
```

## Main-PDF staging

When a main PDF is available, place it at the run root as `<task_name>.pdf` and use that run-relative file as the canonical main source.

- For a local PDF, copy rather than move or rename the source; verify source and destination SHA256 match.
- For a DOI, title, or other non-file input, save an authorized retrieved PDF directly as `<task_name>.pdf`.
- For an explicitly supplied Zotero item, read the parent metadata; after G0, use read-only child metadata solely to select the main PDF and use an attachment/file route only for that selected file. This narrow grant excludes note content, SI content, non-selected attachment content, and unrelated items. Copy one selected main PDF; never rename, move, update, attach, tag, delete, import, or upload anything in Zotero.
- For one eligible Zotero PDF, select it without broadening access. For multiple PDFs, exclude non-PDF files and files clearly identified as supplementary/SI, in-progress, or preprint when a formal version exists. Prefer the newest formal published full text whose DOI or title matches the parent item. Never promote SI to the main paper; ask when the choice remains ambiguous or only a non-final preprint is available.
- When a Zotero item has no usable PDF, retrieve an OA copy only when existing network/OA permissions allow it, save it in the run directory, and never attach it back to Zotero.
- For every input kind, if no PDF is available, create no placeholder. Set G1 to `pass-with-downgrade` only when an authorized, sufficiently complete non-PDF full text supports the requested task; record the actual representation, `page count: not-applicable`, affected claims, and PDF-dependent limitations. Otherwise set G1 to `blocked` for a PDF-dependent full report.
- Record Zotero item and attachment keys, destination-relative path, size, and SHA256 in the operational record. Do not record a source Zotero absolute path in reader-facing output.
- Staging the main PDF consumes neither `materialized_aux_pdf_count` nor `parser_submission_count`.

### Legacy aliases

Resolve legacy terms only as compatibility aliases:

| Legacy term | Normalized value |
| --- | --- |
| `full-deep-reading` | `task=full-report` |
| `complete-validation` | `validation=standard`, when the user explicitly requests/permits it or gives the unqualified command `精读` |
| `structure-only` | `task=plan-only` |
| `presentation-prep` | `presentation_handoff=yes` |

## Main-paper identity

Keep the following main-source record in `paper-package.md`:

| Field | Required content |
| --- | --- |
| Input kind | `zotero-item`, `local-pdf`, `doi`, `title`, or another explicit descriptor |
| Canonical title | Title read from the paper or authoritative metadata |
| DOI or canonical identifier | Normalized DOI, PMID, arXiv ID, or explicit `not available` |
| Naming metadata | Complete first-author name, year, venue value, and venue status: `official-abbreviation`, `normalized-full-name`, or `unknown-venue` |
| Zotero source keys | Item and selected attachment keys when applicable; otherwise `not-applicable` |
| Source file | Run-relative `<task_name>.pdf` when a main PDF is available; otherwise the authorized source descriptor |
| Page count | PDF page count, or `not-applicable` for a non-PDF source |
| File size | Byte count of the actually read local file when one exists |
| SHA256 | Hash of the actually read local file when one exists |
| Parse status | `not-required`, `not-submitted`, `parsed`, `partial`, `failed`, or `blocked` |
| Actual read source | Exact parsed output, PDF, or full-text representation used for claims |
| Identity or parse limitations | Mismatch, missing pages, OCR loss, inaccessible content, or `none` |

Do not pass G1 merely because a file exists. Confirm that the identity, hash where applicable, parse result, and actual read source refer to the intended paper.

## Claim and Condition Registry

Maintain this normative table in `reading-report.md`:

| Claim ID | Atomic claim | Priority | Evidence mode | Main-paper locator | Conditions | Jointly demonstrated | Supplementary dependency | Validation roles | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Apply these field rules:

- Make each claim atomic enough that it can be supported, weakened, or contradicted without changing another proposition in the row.
- Use `high`, `medium`, or `low` for Priority. Mark novelty/priority, causal mechanism, record performance, safety/reliability, and high-risk extrapolation claims `high` unless a narrower scope justifies otherwise.
- Use exactly one Evidence mode: `direct measurement`, `derived`, `model fit`, `simulation`, `extrapolation`, or `author interpretation`.
- Put the complete comparison tuple in Conditions; do not leave a value implicit because it appears in nearby prose.
- In Jointly demonstrated, list other Claim IDs only when the claims require the same multi-part evidence chain; otherwise use `none`.
- In Supplementary dependency, record both dependency and read state. An unread dependency requires a downgrade.
- In Validation roles, record each required evidence role and its state: `open`, `closed`, `downgraded`, `blocked`, or `not-applicable`.
- Use exactly one Status: `supported`, `weakened`, `contradicted`, `not established within scope`, or `blocked`.

Claim status reflects the scoped evidence judgment, not author confidence or source relevance grade.

## Source Registry

Maintain this normative table in `auxiliary-literature-table.md`:

| Source ID | Canonical identifier | Title / year | Discovery route | Related Claim IDs | Evidence role | Relevance grade | Directness | Independence | Comparability | Counter-evidence value | Full-text status | PDF status | Parse status | Read status | Verification status | Citation status | Reader-facing footnote key | Backlink anchor IDs | Include/exclude reason |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use DOI as the preferred identifier; otherwise use a stable PMID, arXiv ID, publisher URL, or normalized title/year key. Deduplicate before assigning the Source ID.

Use evidence roles that answer a claim-specific need, such as `priority/novelty`, `quantitative benchmark`, `mechanism`, `boundary/contradiction`, `method/provenance`, or `context`. Add a narrower role when needed; do not replace a missing decisive role with repeated context papers.

Use S/A/B/C/D only for relevance and selection priority:

| Grade | Meaning |
| --- | --- |
| S | Decisive and direct for a high-priority claim, with sufficiently comparable conditions |
| A | Strongly relevant and potentially claim-changing, but less direct or less comparable than S |
| B | Useful context or a candidate lead; not decisive by itself |
| C | Remote, redundant, or materially incomparable for the current claim |
| D | Exclude because it is irrelevant, unreliable, superseded for the use, or outside authorized scope |

Do not calculate a weighted total. Grade is not verification status and does not prove evidence strength.

Keep lifecycle statuses independent:

| Status field | Controlled values and interpretation |
| --- | --- |
| Full-text status | `available`, `unavailable`, `access-blocked`, `unknown` |
| PDF status | `not-needed`, `not-materialized`, `materialized`, `failed`, `not-authorized` |
| Parse status | `not-needed`, `not-submitted`, `parsed`, `partial`, `failed`, `not-authorized` |
| Read status | `unread`, `partial`, `full` |
| Verification status | `not-started`, `verified`, `conflicted`, `rejected`, `blocked` |
| Citation status | `not-cited`, `planned`, `cited` |

Publisher HTML or Zotero indexed full text may reach `Read status=full` and `Verification status=verified` without a materialized or parsed PDF, provided the relevant content and locator were actually checked. Metadata, an abstract, a search snippet, or a citation graph alone can never reach `verified`.

For `Reader-facing footnote key`, use the exact semantic key or `not-cited`, `not-applicable`, `pending`, or `blocked: <reason>`. For `Backlink anchor IDs`, list the exact HTML IDs in first-appearance order separated by a comma and one space, or use the same controlled value when no reader-facing citation exists. A semantic key requires `Citation status=cited`; every cited semantic key and its ordered anchor list must match the generated report exactly, with no missing, reordered, or extra IDs.

## Evidence Ledger

Maintain this normative table in `external-evidence-matrix.md`:

| Evidence ID | Claim ID | Source ID | Relation | Evidence mode | Locator | Conditions | Evidence summary | Limitations/conflict | Evidence strength | Final assessment | Report target |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use only `supports`, `weakens`, `contradicts`, or `contextualizes` for Relation. Use the Claim Registry vocabulary for Evidence mode.

Use `strong`, `moderate`, `weak`, or `unusable` for Evidence strength. Base strength on directness, locator quality, condition comparability, source independence, completeness of reading, and unresolved conflict—not on Relevance grade alone.

Use the Claim Registry status vocabulary for Final assessment. Multiple evidence rows may feed one final claim assessment; preserve disagreeing rows rather than overwriting them with a consensus summary.

Write a quote-free, claim-specific Evidence summary. Put incomparable conditions, circular citation, supplementary dependence, missing controls, source overlap, and contrary results in Limitations/conflict. Report target names the intended reader-facing section or `audit-only`.

## Authorization resolution

Delivery intent alone grants no external capability. A request for `view-report.md`, a report, or a summary does not by itself authorize networking, Zotero, downloads, uploads, or parsing.

Exception: an unqualified user request containing `精读` invokes the project-defined standard-validation preset and is treated as explicit permission for the capabilities covered by that preset.

Resolve every capability in this precedence order:

```text
explicit user denial > explicit user permission > authorized preset > inferred default
```

Record the result in `paper-package.md`:

| Capability | Decision | Basis | Scope, limit, or exclusion |
| --- | --- | --- | --- |
| Main-PDF staging | `allowed`, `denied`, or `ask-before-use` | explicit input, user, preset, or default | One identified main source and approved run directory |
| Main-paper upload/remote parsing | `allowed`, `denied`, or `ask-before-use` | user, preset, or default | Service and file scope |
| Public network search | same | same | Query/topic scope |
| Zotero read-only access | same | same | Trigger and library scope |
| OA download | same | same | Allowed source classes |
| Auxiliary PDF materialization | same | same | Count limit and destination |
| Auxiliary PDF parsing/upload | same | same | Count limit and service |
| Supplementary material access | same | same | File scope |
| Restricted/paid/login resources | same | same | Resource scope |
| Zotero or library writes | same | same | Normally excluded; requires separate permission |
| Sensitive local-file copying | same | same | Requires separate permission |

An explicitly supplied local PDF, DOI, title, or Zotero item establishes narrow input-identity access. Before G0 is complete, read only the parent item, file metadata, or authoritative bibliographic metadata needed to determine the canonical author, year, venue, and title; do not enumerate attachments, retrieve full text, download, copy, upload, parse, or run broader search. After the run directory is approved, the selected source may establish `main_pdf_staging=allowed` unless the user denies copying. For a supplied Zotero key, child enumeration is limited to attachment metadata needed to select one main PDF, and content/file access is limited to the selected attachment. This permission does not authorize note content, SI content, non-selected attachments, unrelated local files, other Zotero items, supplementary attachments, or any Zotero write. A Zotero item discovered indirectly during validation remains `ask-before-use` for attachment copying until the user selects or confirms it as the main source.

When neither the user nor an authorized preset resolves an external capability, use `ask-before-use`; an inferred default must not silently become permission.

Apply `validation=standard` when either:

1. the user explicitly requests or permits standard validation; or
2. the user gives the unqualified command `精读`.

The standard preset is a permission ceiling, not a mandatory action list. It permits:

- staging the explicitly identified main PDF in the approved run directory;
- main-paper MinerU upload and remote parsing;
- public scholarly search;
- metadata and OA lookup;
- OA auxiliary-PDF download;
- materialization of at most 10 distinct auxiliary PDFs;
- remote parsing of at most 10 distinct auxiliary PDFs;
- Zotero read-only lookup when useful.

The standard preset always denies Zotero or library writes. Read-only Zotero access includes searching items, collections, tags, indexed full text, notes, annotations, and existing attachment metadata/content when the available Zotero capability supports them. Copying one explicitly selected main attachment to the approved run directory is governed by `main_pdf_staging`; it never includes creating, updating, tagging, importing, deleting, moving, renaming, or uploading any Zotero object.

Explicit user denial overrides the preset. The preset excludes paid/login-only resources, supplementary material, restricted resources, and sensitive-file copying beyond the selected main paper unless separately authorized.

Interpret other scopes as follows:

- `main-paper-only`: analyze the main paper under its resolved staging and parser permissions; do not search, use Zotero beyond an explicitly supplied main item, obtain auxiliary sources, or claim external validation.
- `fully-local`: do not use network, remote upload, or new downloads; use only user-authorized local material, including an explicitly supplied Zotero main item.
- `custom`: enumerate every allowed, denied, and ask-before-use capability.
- `plan-only`: describe actions and gates without executing live external actions.

Do not silently broaden a preset to overcome a blocker.

## Budgets and counters

Use these defaults unless the user explicitly supplies a hard limit:

| Budget field | Default |
| --- | --- |
| `candidate_policy` | `soft-target` |
| `candidate_target` | `15-30` |
| `candidate_hard_limit` | `null` |
| `materialized_aux_pdf_limit` | `10` |
| `parser_submission_limit` | `10` |
| `cited_external_source_limit` | `null` |

Keep the used counts canonically in the `paper-package.md` Run Contract and update them after every relevant state transition. Apply these counting rules:

1. Count a Candidate after metadata deduplication. Candidates consume neither PDF nor parser budget.
2. Staging the main PDF as `<task_name>.pdf` consumes neither auxiliary-PDF counter.
3. Increment `materialized_aux_pdf_count` once when a distinct auxiliary PDF is downloaded or copied into the run.
4. Increment `parser_submission_count` once on the first MinerU submission of a distinct auxiliary PDF. Retries of the same PDF do not increment it again.
5. Reading publisher HTML or Zotero indexed full text without copying a PDF consumes neither materialization nor parser budget.
6. Interpret “no more than 10 auxiliary papers” as the materialized/parsed PDF ceiling unless the user explicitly says the candidate set itself must contain at most 10.
7. Do not limit final cited sources by default, but cite only sources read in full with a verified locator.

Thus, 20 deduplicated candidates, 8 materialized PDFs, and 6 first parser submissions remain within the default limits.

## Candidate selection and stopping

Select candidates lexicographically, without a weighted score:

1. Cover an open, high-priority evidence role.
2. Prefer direct evidence and comparable conditions.
3. For novelty, record, causal-mechanism, and high-risk extrapolation claims, prefer independent, contrary, or boundary evidence.
4. Prefer available full text and a verifiable locator.
5. Reduce repeated authorship, citation-chain dependence, and duplicated experimental conditions.
6. Break any remaining tie by normalized DOI, then normalized title.

After the initial screen, run at most one targeted follow-up search for still-open high-risk roles. This search refinement does not authorize supplementary files or any other excluded resource.

Stop when any applicable condition is met:

- all required high-priority roles are closed or honestly downgraded;
- the one targeted search adds no decisive S/A candidate;
- a user hard limit is reached;
- access or authorization blockers are recorded and the affected claim is downgraded or marked `blocked`;
- further candidates only repeat authors, citation chains, conditions, or already-covered context.

Never keep searching merely to force `supported`. Use `not established within scope` when the scoped evidence does not close the claim.

## Review roles and correlated cross-checks

Treat these as logical responsibilities; do not require four actual agents:

| Role | Responsibility | Prohibited shortcut |
| --- | --- | --- |
| Extractor | Extract numbers, conditions, and locators | Interpret mechanism or upgrade strength |
| Verifier | Match an atomic claim to the actual source content | Treat metadata or abstract agreement as verification |
| Challenger | Seek counterexamples, alternative mechanisms, and incomparable conditions | Suppress conflict to create closure |
| Editor | Assemble only verified records and preserve their limits | Invent a bridging claim or final judgment |

Apply a full role-separated review to high-risk claims, S-grade sources, and disputed judgments. For routine low-risk context, combine roles while still recording the checks performed.

A subagent is not automatically an independent verifier. Mark agreement as `correlated cross-check` when any of the following remain shared:

- the same model family or substantially identical reasoning process;
- the same source set;
- the same extracted context or prompt framing.

Record the label in Validation roles, Limitations/conflict, or the audit. A correlated cross-check may catch transcription, locator, or consistency errors, but it must not:

- raise Relevance grade or Evidence strength;
- close a missing external evidence role;
- convert a model fit into causal proof;
- erase disagreement;
- be described as independent replication or independent validation.

Scientific independence comes primarily from independent evidence and sufficiently comparable conditions, not from the number of agents that repeat the same context.

## Epistemic rules

Apply these rules before reader-facing assembly:

1. Do not splice metrics across different materials, devices, temperatures, voltages, pulse widths, durations, cycle counts, or readout conditions. A result at 600 ps and a result at 358 K remain separate unless one source reports that joint condition.
2. Distinguish `direct measurement`, `derived`, `model fit`, `simulation`, `extrapolation`, and `author interpretation` in both the registry and prose.
3. A fit or consistency with a model does not establish that model as the unique mechanism. Record viable alternatives and missing discriminating controls.
4. Do not convert a nominal state count into reliable information capacity. For example, 32 nominal resistance states do not establish 5 reliable bits without state distributions, error rates, retention, read margin, and decoding conditions.
5. If a claim depends on unread supplementary material, lower its strength and state the dependency. Do not infer that the main text fully demonstrates it.
6. Preserve conflicting evidence, circular citation, shared datasets, overlapping authorship, and incomparable benchmarks through the final assessment.
7. Do not expand “not detected” or “no evidence observed” into “completely excluded.” State the detection limit, tested scope, or missing sensitivity when available.

Treat claims using `first`, `fastest`, `highest`, `proves`, `completely excludes`, or an equivalent superlative/causal absolute as high risk. If the epistemic check fails, do one permitted targeted search, narrow the wording, downgrade the claim, or record a blocker. Never pass G4 by stylistic substitution while leaving the unsupported meaning intact.

## Six fail-fast Gates

Use only the statuses listed below:

| Gate | Required checks | Allowed statuses |
| --- | --- | --- |
| G0 Run Contract | Paper, confirmed output directory, normalized task/validation/handoff, `main_pdf_staging`, resolved permissions, budgets, exclusions, user overrides | `pass`, `blocked` |
| G1 Main Source | Canonical identity, staged filename when applicable, source/destination hash agreement when copied, page count, parse status, actual read source, source limitations | `pass`, `pass-with-downgrade`, `blocked` |
| G2 Claims and Figures | Atomic claims, conditions, main-paper locators, evidence modes, supplementary dependencies, Figure Reading Packets for report exhibits | `pass`, `pass-with-downgrade`, `blocked` |
| G3 Sources and Evidence | Deduplication, independent lifecycle states, role coverage, external locators, conditions, conflicts, ledger linkage | `pass`, `pass-with-downgrade`, `blocked`, `not-applicable` |
| G4 Epistemic Pre-report | No condition splicing, mode inflation, nominal-bit inflation, hidden supplementary dependence/conflict, or unsupported strong wording | `pass`, `pass-with-downgrade`, `blocked` |
| G5 Delivery QA | Report Claim Map, canonical/derived synchronization, main-PDF naming, images and manifest, footnotes, relative paths, placeholders, protection of pre-existing directories | `pass`, `blocked` |

Apply the Gates in order:

1. Use only narrowly authorized identity-metadata reads needed to construct G0. Resolve G0, including any higher-priority per-run output confirmation, before attachment enumeration, full-text access, directory creation, broader search, download, copy, upload, or parsing actions.
2. Resolve G1 before treating parsed content as the main paper.
3. Resolve G2 before using figures or non-atomic claims in external verification.
4. Resolve G3 before describing external evidence as complete or verified. When external verification is prohibited or outside scope, use `not-applicable` or `pass-with-downgrade`; never simulate completion.
5. Resolve G4 before drafting strong reader-facing conclusions.
6. Pass G5 before delivery. G5 has no downgrade state because broken provenance, links, or synchronization must be repaired or delivery must stop.

Every `pass-with-downgrade` must identify the affected Claim IDs, the missing or weak evidence, the reader-facing limitation, and wording that is prohibited as a result. Use `blocked` when the requested outcome cannot be produced responsibly within authorization and evidence limits.

## Gate recording and correction order

For a full `view-report.md`, keep the Gate table in required internal `view-report-audit.md`:

| Gate | Status | Checked canonical artifacts | Affected Claim IDs | Missing/weak evidence or blocker | Reader-facing limit and prohibited wording | Required action |
| --- | --- | --- | --- | --- | --- | --- |

Focused or fully local tasks may use a compact audit, but must still record every applicable Gate. `view-report-audit.md` is internal and is not the primary presentation input.

When a Gate detects an error, correct in this order:

```text
canonical owner
-> linked canonical rows
-> conditional derived views
-> view-report-audit.md Report Claim Map
-> view-report.md
-> presentation handoff index
```

Do not repair a reader-facing sentence alone when its canonical claim, source, evidence, or asset record remains wrong.
