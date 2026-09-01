---
name: paper-deep-reading
description: Deeply read, analyze, verify, or interpret one academic paper and produce traceable artifacts, especially a reader-facing Chinese view-report.md. Use for PDF-first technical explanation, figure/table/equation reading, claim and reliability assessment, originality and research-generativity judgment, design necessity/sufficiency and counterfactual alternatives, complete external validation with public or authorized sources, research translation, or a group-meeting handoff; keep evidence, permissions, provenance, and report boundaries explicit.
---

# Paper Deep Reading

## Core Contract

Treat `view-report.md` as the final reader-facing Chinese report. Build it from canonical run, claim, source, evidence, and asset records; do not treat separately written briefs or matrices as independent truth.

Read the bundled references as follows:

- Read [references/evidence-kernel.md](references/evidence-kernel.md) before creating the Run Contract, claims, candidates, external evidence, or gate judgments.
- Read [references/research-judgment.md](references/research-judgment.md) when originality, transferable ideas, perspective shifts, design necessity/sufficiency, baselines, or alternative mechanisms are requested or materially implicated.
- Read [references/report-contract.md](references/report-contract.md) before staging figures, writing `view-report.md`, creating its audit, or preparing a presentation handoff.

Keep these boundaries:

- Analyze one main paper. Route topic-level systematic reviews to `literature-review`.
- Do not write, import, tag, delete, or upload to Zotero without separate permission.
- Never rename, move, or modify a source Zotero attachment. Copy an explicitly selected main PDF only under the narrow `main_pdf_staging` permission.
- Do not use paid, login-only, private, confidential, or non-public resources without separate permission.
- Do not retrieve or parse supplementary materials unless separately authorized.
- Do not generate a PPT or final slide deck. Hand presentation planning to `paper-presentation`.
- Do not cite metadata, snippets, unread papers, unavailable attachments, or uninspected parser output as verified evidence.

## Scope Gate And Internal State

Resolve the paper identity, output directory, upload/network permissions, explicit exclusions, and resource budgets before live work. Use only user-supplied data or narrowly authorized main-item/PDF/DOI metadata reads to obtain the author, year, venue, and title needed to build G0; defer attachment enumeration, full-text access, download, copy, upload, parsing, and broader search until G0 passes. An explicitly supplied Zotero item key permits child metadata only for main-PDF selection after G0 and file access only for the selected main attachment; it does not permit note content, SI content, non-selected attachment content, or unrelated items. Treat workspace `.paper-collab.yaml` as a path preference, never as permission. If a higher-priority workspace rule requires per-run output confirmation, show the resolved directory and obtain that confirmation before creating directories or copying files. If multiple blocking inputs are missing, ask for them together in one concise question.

Resolve output in this order: an explicit complete run directory, an explicit output parent plus an automatically named child, a valid workspace-root configuration plus an automatically named child, then a required question for an absolute default parent. Treat a missing, unreadable, malformed, incomplete, or non-absolute configuration as unresolved; do not invent or normalize a fallback. When the user provides an output parent rather than a complete run-directory name, derive `task_name` and the child run directory with the naming contract in `evidence-kernel.md`. Preserve an explicitly named run directory. Never overwrite an existing directory to enforce the convention, and never rename or migrate a legacy run.

Stage every available main PDF inside the approved run directory as `<task_name>.pdf`. Copy local or Zotero files rather than moving them, verify copied bytes by SHA256, and use the staged file as the canonical main source. This main file never consumes an auxiliary-PDF budget.

Record three orthogonal fields in the Run Contract:

```yaml
task: full-report | focused-analysis | plan-only
validation: standard | main-paper-only | fully-local | custom
presentation_handoff: yes | no
```

Interpret legacy names as compatibility aliases:

```text
full-deep-reading -> task=full-report
complete-validation -> validation=standard, when explicitly requested/allowed or triggered by unqualified 精读
structure-only -> task=plan-only
presentation-prep -> presentation_handoff=yes
```

Requesting `view-report.md` determines the delivery intent; it does not by itself authorize search, Zotero, downloads, or upload-based parsing.

### Default Deep-Reading Preset

Treat an unqualified user request containing `精读` as an explicit invocation of the standard-validation preset, not merely as delivery intent.

Normalize it as:

```yaml
task: full-report
validation: standard
presentation_handoff: no
```

Unless the user narrows or denies a capability, this preset authorizes:

- staging the explicitly identified main PDF inside the approved run directory;
- upload-based MinerU parsing of the main paper;
- public academic search and metadata/OA lookup;
- open-access auxiliary PDF download into the run directory;
- materializing and remotely parsing at most 10 distinct auxiliary PDFs;
- read-only Zotero access when useful to the evidence task.

The preset explicitly denies:

- creating, updating, tagging, importing, deleting, or uploading anything in Zotero;
- restricted, paid, login-only, private, or confidential resources;
- supplementary materials unless separately authorized;
- sensitive or unrelated local-file copying beyond the explicitly identified main paper.

An authorized capability is optional. Use it only when it materially helps the task, and record unused capabilities as `not-applicable`.

Explicit user instructions override this preset. For example, `精读，但不要联网` must disable public search, downloads, Zotero, and remote parsing.

Do not ask again for permissions already covered by this preset. Ask only for missing paper identity, unresolved output configuration or required workspace confirmation, supplementary-material access, restricted/login-only resources, Zotero writes, or sensitive/confidential resources outside the preset.

Apply authorization in this order:

```text
explicit deny > explicit allow > standard preset > inferred default
```

Treat `允许标准核验`, `允许标准 complete-validation`, and an unqualified `精读` request as the same standard-validation permission ceiling. Unless the user narrows it, the preset permits:

- staging the explicitly identified main PDF inside the approved run directory;
- upload-based MinerU parsing of the main paper;
- public academic search and metadata/OA lookup;
- open-access auxiliary PDF download into the run directory;
- materializing and parsing at most 10 distinct auxiliary PDFs;
- Zotero read-only access when it is useful to the evidence task, including checking existing local records, notes, indexed full text, annotations, or attachment metadata/content where available.

The preset never permits Zotero writes, restricted resources, supplementary materials, or sensitive-library copying beyond the selected main attachment. An authorized action is optional when it is unnecessary; record `not-applicable` rather than performing it mechanically.

Distinguish validation scopes:

- `standard`: use authorized public or read-only external evidence as needed.
- `main-paper-only`: analyze the main paper, allow its authorized parser route, and do not search, use Zotero beyond an explicitly supplied main item, or obtain auxiliary sources.
- `fully-local`: do not use network tools or upload the paper; use only user-authorized local material, including an explicitly supplied Zotero main item, and explicitly downgrade unavailable checks.
- `custom`: expand explicit permissions and exclusions into individual Run Contract fields.

## External Dependency Preflight

Before any live G0 action, run a read-only external-dependency preflight. When this Skill is installed as a directory, use the bundled script when available:

```text
python scripts/check_dependencies.py --mode <validation>
```

Use `--json` when the result will be merged with the agent's Skill and tool registry checks. For `main-paper-only` or `fully-local`, pass `--input-kind pdf` when the supplied main source is a PDF; use `--input-kind full-text` for a sufficiently complete non-PDF source. The default `unknown` keeps the parser route conditional in those two modes. After the agent confirms a capability, it may pass the corresponding repeated `--agent-check <name>` flag to merge that result, for example:

```text
python scripts/check_dependencies.py --mode standard --json --agent-check paper-lookup.skill --agent-check paper-lookup.http-fetch --agent-check sciverse-research.skill --agent-check sciverse.mcp-tools
```

Only pass `--agent-check` for capabilities actually present in the agent's Skill/tool catalog. The script must not install packages, access the network, upload files, modify environment variables, enable Zotero, or print secret values. API-key checks report presence only. The agent must supplement the script with its own available-Skill and MCP-tool catalog; a filesystem-only script cannot prove that an MCP server is exposed.

Without the agent-side flags, `standard` intentionally leaves HTTP and MCP checks as `BLOCKED` and returns exit code `1`; this is a guard for incomplete preflight, not permission to skip the agent catalog check.

Use these result states consistently: `PASS`, `MISSING`, `BLOCKED`, `OPTIONAL`, and `NOT-APPLICABLE`. Report the merged result to the user before starting G0, grouped as must-have, strongly recommended, and optional dependencies. Keep the complete maintenance table in [references/external-dependencies.md](references/external-dependencies.md).

For `validation=standard`, the following are required before the standard workflow can start:

- `paper-lookup` Skill and an available HTTP-fetch route for DOI, OA, citation, and candidate checks;
- the `sciverse-research` Skill, the Sciverse MCP tools, and a non-empty `SCIVERSE_API_TOKEN`;
- at least one usable PDF route: the preferred `mineru-pdf` route or the local `pdf` fallback route.

The preferred MinerU route requires the `mineru-pdf` Skill, its wrapper, a usable Python runtime, and `MINERU_API_KEY`. The local fallback should expose `pdfinfo`, `pdftoppm`, `pypdf`, and preferably `PyMuPDF`/`fitz` for parsing, rendering, and visual QA. A missing preferred MinerU component is a downgrade rather than a blocker when the local PDF route is usable. If both routes are unavailable, block PDF-dependent work and explain the available remediation.

`parallel-web` and `research-lookup` are conditional enhancements for open-ended web retrieval or deep research. Their absence must not block the basic DOI/OA/citation/candidate workflow or a standard single-paper reading run when the required routes above are available. `zotero:Zotero` is conditional on a user-authorized Zotero input and remains read-only.

`main-paper-only`, `fully-local`, and `plan-only` must not be blocked by missing Sciverse, `paper-lookup`, `parallel-web`, or `research-lookup` dependencies. `main-paper-only` and `fully-local` still need a usable local or explicitly authorized parser route when the supplied main source is a PDF; `plan-only` does not need a parser route.

If a required dependency is `MISSING` or `BLOCKED`, stop the standard workflow before G0 and offer the applicable narrower mode or user action. If only a strongly recommended dependency is missing, continue with an explicit downgrade in the Run Contract and report. Never silently install software, modify credentials or environment variables, configure MCP, enable Zotero, or upload a file. Never reveal any API-key value.

## Budget Semantics

Use these defaults unless the user overrides them:

```yaml
candidate_policy: soft-target
candidate_target: 15-30
candidate_hard_limit: null
materialized_aux_pdf_limit: 10
parser_submission_limit: 10
cited_external_source_limit: null
```

A candidate is a deduplicated metadata record and does not consume a PDF budget. Staging the main PDF consumes neither auxiliary-PDF budget. Downloading or copying a distinct auxiliary PDF consumes the materialized-PDF budget. The first MinerU submission of a distinct auxiliary PDF consumes the parser budget; retries of the same file do not consume it again. Read-only publisher HTML or Zotero indexed full text consumes neither PDF budget.

Interpret an otherwise unqualified “最多 10 篇辅助文献” as the materialized and parsed auxiliary-PDF limits. Restrict metadata candidates only when the user explicitly names the candidate set or candidate count. Treat `15-30` as a soft search range, not a minimum, hard cap, or completion criterion.

Keep canonical used counters for candidates, materialized auxiliary PDFs, distinct first parser submissions, verified external sources, and cited external sources in `paper-package.md`; update them as the run changes.

## Six-Gate Workflow

Follow this sequence and persist each gate result in `view-report-audit.md` for a full report:

```text
G0 Run Contract
-> G1 Main Source
-> G2 Claims and Figures
-> G3 Sources and Evidence
-> G4 Epistemic Pre-report
-> G5 Delivery QA
```

### G0 Run Contract

Create `paper-package.md` before live actions. Record main-paper identity, resolved output, `main_pdf_staging`, internal state, permission flags, budgets, explicit user overrides, `evidence_contract: v1.1`, and `reader_citation_contract: semantic-footnote-v1` for newly generated reader-facing reports. Stop if identity, output confirmation, or required permission is unresolved.

### G1 Main Source

Stage an available main PDF as `<task_name>.pdf`, then verify its identity, DOI when available, page count, file size/hash, parser status, and exact read source. For a copied local or Zotero source, confirm source and destination SHA256 match and do not expose the source Zotero path. If no PDF is available, create no placeholder: use G1 `pass-with-downgrade` only when an authorized, sufficiently complete non-PDF full text supports the requested task and its limits are recorded; otherwise block a PDF-dependent full report. Prefer `mineru-pdf` when upload is authorized; use local PDF fallback in `fully-local` or when MinerU is unavailable.

For MinerU output, read in this order:

1. `manifest.json`
2. `full.md`
3. `content_list.json`
4. targeted files in `images/`
5. `_raw_extract/` only for debugging

Do not claim parser evidence merely because files exist.

### G2 Claims And Figures

Perform a structure scan, technical deconstruction, and research judgment. Create the canonical Claim/Condition Registry in `reading-report.md`. Make each important claim atomic and record its conditions, main-paper locator, evidence mode, joint-demonstration status, supplementary dependency, validation role, and closure status.

For every full report, run the compact research-judgment trigger scan in `research-judgment.md`. When triggered, add the canonical `N-*` Novelty-Generativity-Perspective Registry and/or `D-*` Design Necessity and Counterfactual Registry to `reading-report.md`. Link each judgment to atomic `C-*` claims, state the nearest baseline or required function, and record missing discriminating controls rather than relying on evaluative prose.

Build a Figure Reading Packet before writing every displayed figure section. Use the caption, surrounding full-text context (`full.md` when MinerU is used or verified local PDF context otherwise), later figure references, visible panels, linked claims, conditions, and boundaries. Do not interpret a multi-panel figure from its caption alone.

### G3 Sources And Evidence

Skip external actions when validation forbids them and record `not-applicable` or `pass-with-downgrade`.

When external validation is authorized:

1. derive evidence roles from high-priority claims;
2. search metadata and public scholarly sources;
3. deduplicate candidates and populate the Source Registry in `auxiliary-literature-table.md`;
4. grade relevance separately from access, parsing, reading, verification, and citation states;
5. select sources by uncovered role, directness, comparability, independence or boundary value, locator availability, and low redundancy;
6. download only allowed OA or explicitly authorized PDFs;
7. parse selected PDFs within the distinct-PDF budgets;
8. read the relevant full text and create claim-level Evidence Ledger rows in `external-evidence-matrix.md`;
9. run at most one targeted closure search for unresolved high-risk roles;
10. close, downgrade, or record a blocker without forcing certainty.

Use `not established within scope` as a valid conclusion. Do not require a supporting and opposing paper for every claim, but actively seek independent or boundary evidence for novelty, performance records, causal mechanisms, and high-risk extrapolations. For open `N-*` or `D-*` rows, search by target function and derive explicit roles for nearest prior art, functionally equivalent alternatives, counterexamples, discriminating controls, and matched comparisons. Do not treat the main paper's reference list as verified priority evidence or convert an unsuccessful search into proof that no alternative exists.

For high-risk claims, separate extraction, locator verification, challenge, and editing roles when subagents are available. Give reviewers raw or narrowly scoped evidence where practical. Label same-model, same-context agreement as `correlated cross-check`; never raise evidence strength because several such agents agree.

### G4 Epistemic Pre-report

Run every epistemic check in `evidence-kernel.md` before report prose. In particular, do not merge incompatible conditions, confuse measurement with fit/simulation/extrapolation, treat fit as unique mechanism proof, convert nominal states directly into reliable bits, hide unread-supplementary dependence or conflicting evidence, or turn non-detection into complete exclusion.

If a high-risk claim fails, perform the single allowed targeted closure pass if unused, narrow the wording, or mark it `blocked`. Do not use “first,” “fastest,” “highest,” “proves,” or equivalent strong language without the required evidence and conditions.

Apply the research-judgment checks as logical constraints: feasibility does not prove necessity; joint sufficiency does not prove component sufficiency; failure of one baseline under the paper's conditions does not prove principle-level impossibility; an unmatched comparison does not prove superiority; and a future direction is not research-generative unless it states a falsifiable hypothesis, minimum decisive test, failure observable, and boundary.

### G5 Delivery QA

Assemble `view-report.md` only from eligible canonical records. Verify report-to-claim-and-judgment mapping, semantic external footnotes, display assets, relative paths, figure completeness, equation status, placeholders, internal-path leakage, and protection of pre-existing outputs. Map every strong originality, perspective, necessity, sufficiency, alternative, and superiority statement to canonical `C-*`, `N-*`, `D-*`, and applicable `E-*` records. Run the bundled mechanical check from the resolved Skill root when the report contains external footnotes; the three artifact paths may be absolute:

```text
python <skill-root>/scripts/check_report_footnotes.py --report view-report.md --registry auxiliary-literature-table.md --audit view-report-audit.md
```

The script checks syntax, key normalization, definition completeness, anchors, backlinks, and registry/audit synchronization; it does not establish bibliographic authority, verify DOI-based collision ordering, replace full-text reading, or verify locators. A derived-view conflict or either failed G5 layer must fail this gate until the canonical record is corrected and the view is regenerated.

Use gate states exactly as defined in `evidence-kernel.md`. Do not describe external validation as complete when G3 is `not-applicable`, downgraded, or blocked.

## Capability Routing

Use the narrowest available capability and its own Skill instructions:

| Need | Preferred capability |
| --- | --- |
| Main or auxiliary PDF parsing | `mineru-pdf` |
| Local PDF fallback, rendering, crop, visual QA | `pdf` |
| DOI, OA, citation graph, OpenAlex/Crossref/Semantic Scholar | `paper-lookup` |
| Academic web and official/publisher page retrieval | `parallel-web` or `research-lookup` |
| Provenance-preserving evidence chunks | `sciverse-research` |
| Citation metadata cleanup | `citation-management` |
| Local Zotero item metadata, indexed text, and attachments | `zotero:Zotero`, read-only and only when authorized/relevant |
| Scientific evidence critique | `scientific-critical-thinking` |
| Topic-level synthesis | `literature-review` |

Preserve database/query provenance and stable source identity for search results. Store the staged main PDF and downloaded or authorized copied auxiliary files only in the run directory. Record Zotero item and attachment keys rather than source paths. Never expose source Zotero paths in reader-facing output.

## Canonical And Derived Artifacts

Use these canonical owners:

| Artifact | Canonical responsibility |
| --- | --- |
| `paper-package.md` | Run Contract and main-source identity |
| `reading-report.md` | Claim/Condition Registry plus triggered `N-*` and `D-*` research-judgment registries |
| `auxiliary-literature-table.md` | Source Registry whenever any external source is considered or evaluated |
| `external-evidence-matrix.md` | Evidence Ledger when external evidence evaluation runs, including a no-decisive-evidence result |
| `assets/_manifest.md` | Asset Registry |
| `view-report-audit.md` | Gate results and Report Claim Map for a full report |
| `view-report.md` | Derived reader-facing narrative |

Keep raw operational records such as `sources/`, `download-manifest`, `auxiliary-pdfs/`, and `auxiliary-mineru/` when the corresponding actions occur.

Treat `auxiliary-paper-brief.md`, `auxiliary-evidence-cards.md`, `review-matrix.md`, and `research-translation-matrix.md` as conditional derived views. Create them only when the task benefits from the view. They must cite applicable canonical `C-*`, `N-*`, `D-*`, or `E-*` IDs, must not introduce a new final judgment, and must be regenerated after canonical corrections. Their absence must not fail an otherwise complete core run.

## Reader-Facing Report Boundary

Follow `report-contract.md`. In particular:

- keep `view-report.md` free of modes, internal IDs, raw paths, hashes, logs, permission tables, and QA narration;
- use a dynamic `关键图表精读` section rather than a fixed figure count;
- write `核心结论` as one paragraph of 3-5 Chinese sentences;
- treat `全文速览` as a concise two-minute reading section, not a hard character quota;
- use readable `*-display.png` assets and Typora-compatible relative HTML image paths;
- never embed full-page renders from `assets/pages/`;
- explain every visible panel or natural panel group using caption and body context;
- preserve original equation numbers or mark an unavailable number explicitly;
- include paper-appropriate sections equivalent to `原创性、研究生成力与关键视角` and `核心设计选择：必要性、充分性与替代机制` when their trigger scan is positive;
- present follow-up directions as bounded, falsifiable report inferences with a minimum decisive test, not as generic application or material-substitution lists;
- use `reader_citation_contract: semantic-footnote-v1`: semantic Markdown footnote keys, superscript-only body markers, complete definitions under `外部核验文献`, and explicit `[回到正文]` links;
- derive author, journal abbreviation, and year from the shared normalization rules in `references/evidence-kernel.md`;
- cite only externally verified full text with reader-facing Markdown footnotes;
- label `Internal Evidence`, `External Evidence`, `Inference`, and `User Assumption` where relevant;
- retain `组会汇报建议` only as a handoff seed and do not generate slide sequence, action titles, or speaker notes.

Hand presentation work to `paper-presentation`; `commitments.md` remains the sole presentation-planning source of truth.

## Completion Contract

Before completion:

- confirm all applicable gates have an honest terminal state;
- confirm no unread or metadata-only source is presented as verified evidence;
- confirm every strong external evidence row has a usable locator or is downgraded;
- confirm unresolved scope is visible as `not established within scope`, `blocked`, or a report limitation;
- confirm final images, semantic footnotes, equations, relative paths, reader-facing boundaries, and the bundled G5 footnote check pass;
- confirm an available main PDF is named `<task_name>.pdf`, its staged-copy hash is verified when applicable, and it did not consume an auxiliary-PDF budget;
- confirm unauthorized Zotero, restricted-resource, supplementary, and sensitive-copy actions did not occur.

Lead the final response with the `view-report.md` link. Then state the actual validation scope, number of external full texts verified when applicable, image-QA status, and unresolved evidence boundary. If no official journal or publisher abbreviation was available, state that the directory name used a normalized full name or `unknown-venue`; keep this notice out of `view-report.md`. Omit internal modes, candidate counts, hashes, full artifact inventories, and command logs unless the user asks.
