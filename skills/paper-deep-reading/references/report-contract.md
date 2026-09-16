# Reader-Facing Report Contract (v1.1)

Use this reference when assembling, auditing, or handing off `view-report.md`. It defines the boundary between canonical evidence records and the reader-facing report, plus contracts for figures, equations, citations, derived artifacts, and group-meeting handoff. Keep retrieval and tool routing in `SKILL.md`.

## Contents

- [Report boundary](#report-boundary)
- [Preconditions and Report Claim Map](#preconditions-and-report-claim-map)
- [Reader-facing structure](#reader-facing-structure)
- [Core conclusion and fulltext overview](#core-conclusion-and-fulltext-overview)
- [Evidence language](#evidence-language)
- [Research-judgment modules](#research-judgment-modules)
- [Key-figure contract](#key-figure-contract)
- [Asset Registry and image QA](#asset-registry-and-image-qa)
- [Equation contract](#equation-contract)
- [External footnote contract](#external-footnote-contract)
- [Derived-artifact contract](#derived-artifact-contract)
- [Group-meeting handoff](#group-meeting-handoff)
- [Delivery QA](#delivery-qa)

## Report boundary

Treat `view-report.md` as a derived Chinese reader view, not a run log or canonical ledger. It may explain and compress canonical claims and research judgments, but may not introduce a key scientific claim or final judgment that is absent from the Claim Registry, triggered `N-*`/`D-*` Research Judgment Registries, or Evidence Ledger.

Keep these items out of `view-report.md`:

- task/validation mode names and workflow-stage narration;
- Claim, Research-Idea, Design-Choice, Source, Evidence, Asset, card, or Gate IDs;
- raw MinerU, Zotero, cache, download, or local absolute paths;
- hashes, permission logs, download logs, audit tables, or QA checklists;
- crop/render/staging instructions and `assets/pages/` links;
- internal module names such as `V8`, template labels, or agent-role labels;
- unresolved placeholders such as `[MISSING]`, `[TODO]`, `FIXME`, bare `[UNVERIFIED]`, or dummy citations.

An explicit `[UNVERIFIED: concrete reason]` may remain only when it is a reader-relevant evidence status whose reason and consequence are explained in prose. It is not a substitute for unfinished work. Convert missing information into a scoped limitation, `not established within scope`, or `blocked`; otherwise remove the placeholder before G5.

Translate internal provenance into readable evidence language and pinpoint anchors. Preserve the scientific limitation while hiding implementation machinery.

## Preconditions and Report Claim Map

Assemble strong report claims only after G0-G4 have a permitted state. Generate `view-report-audit.md` for every full report; a focused or fully local task may use a compact version.

Maintain this normative Report Claim Map in the audit:

| Report claim or judgment | Report section or paragraph | Canonical `C-*`, `N-*`, or `D-*` IDs | Main-paper locator or Evidence IDs | Intended wording strength | Gate status | Sync status |
| --- | --- | --- | --- | --- | --- | --- |

Map every strong, quantitative, novelty, causal, reliability, originality, perspective, necessity, sufficiency, alternative, superiority, and final-judgment statement. Use `in-sync` or `stale` for Sync status. Do not deliver while any mapped row is `stale`.

If drafting reveals a new key claim or research judgment, stop assembly, create or revise the canonical Claim Registry or applicable `N-*`/`D-*` row, update evidence and Gate decisions, then return to the report. Do not backfill provenance after publication-quality prose has already hardened the claim.

The audit remains internal. Do not use it as the main input to presentation planning; the presentation skill consumes the reader-facing report and creates its own commitments.

## Reader-facing structure

Use the paper's actual argument to choose headings and depth. The following modules define the contract, not an inflexible template:

| Module | Requirement |
| --- | --- |
| `论文信息卡` | Required; identify the paper and reader-relevant context without run metadata |
| `核心结论` | Required; one compact thesis paragraph |
| `全文速览` | Required for a full report; approximately a two-minute read |
| Problem and contribution | Required in substance; heading may be paper-specific |
| Method and evidence chain | Required in substance; distinguish evidence modes |
| `外部证据核验结果` | Include when external validation is in scope; otherwise state the scope limitation without pretending it ran |
| Originality, research generativity, and perspective | Include when the `N-*` trigger is positive; heading may be paper-specific |
| Design necessity, sufficiency, and alternatives | Include when the `D-*` trigger is positive; heading may be paper-specific |
| `关键图表精读` | Required when the paper has decision-relevant figures or tables; use a dynamic number of exhibits |
| Key equations/model logic | Include only when equations, derivations, or simulation logic matter to the claims |
| Meaning, limitations, and credibility | Required in substance; separate internal support from external validation where applicable |
| Open questions | Required when material uncertainties remain |
| `组会汇报建议` | Include only when `presentation_handoff=yes` |
| `外部核验文献` | Include when external sources are cited |

Write the reader-facing report in sectioned, high-density prose. Use paragraphs for scientific analysis and concise paragraph summaries for major blocks. Reserve tables and lists for condition comparisons, compact checks, and information that genuinely benefits from structure; do not turn the report into decorative bullets.

Do not force `图 1-5 精读` or any fixed exhibit count. Select the smallest set that makes the paper's evidence chain and limitations understandable. Retain a dynamic `关键图表精读` heading even when the selected figures are nonconsecutive in the original paper.

## Core conclusion and fulltext overview

Write `核心结论` as one paragraph of 3-5 Chinese sentences. State the main object, claimed mechanism or method, strongest evidence class, and principal limitation or risk. Do not use bullets, an all-bold paragraph, generic praise, or an unverified superlative.

Keep detailed locators and external comparisons in later sections. The compact conclusion may compress the argument only when every strong element maps to later support through the Report Claim Map.

Write `全文速览` for approximately two minutes of reading; treat length as a soft reader constraint, not a character-count Gate. Cover the bottleneck, approach, decisive evidence, principal limitation, and research implication. Remove greetings, process notes, empty transitions, and broad field significance unsupported by the paper.

Do not expose internal compression names or fixed-template terminology in either section.

## Evidence language

Make the provenance class legible in prose without printing internal IDs:

| Provenance | Reader-facing treatment |
| --- | --- |
| Main-paper evidence | Anchor to the relevant figure/panel, table, equation, section, or reported condition |
| External evidence | State whether it supports, weakens, contradicts, or contextualizes the main claim and attach a verified footnote |
| Inference | Mark as the report's interpretation and state the premises and boundary |
| User assumption | Identify it explicitly; do not merge it into the paper's conclusion |

Every detailed major claim must name a concrete object, mechanism or method, evidence anchor, and boundary or risk. Avoid two consecutive evaluative sentences without an anchor.

Use `first`, `fastest`, `highest`, `proves`, `completely excludes`, `breakthrough`, or equivalent wording only when the canonical records pass the high-risk epistemic check. A cautious synonym is not a valid repair if the underlying proposition remains too broad.

Preserve condition tuples in comparisons. Do not combine, for example, a 600 ps result from one condition with a 358 K result from another into one apparent operating point.

Use callouts sparingly for a reader-critical takeaway, caution, or next step. A callout must not replace the evidence paragraph or carry an otherwise unsupported strong statement.

## Research-judgment modules

Follow [research-judgment.md](research-judgment.md) when either trigger is positive. Use paper-appropriate Chinese headings equivalent to `原创性、研究生成力与关键视角` and `核心设计选择：必要性、充分性与替代机制`; the exact heading is flexible, but the logical distinctions are not.

For originality and research generativity:

- identify the nearest baseline and smallest atomic delta;
- distinguish internal distinctiveness from externally verified priority;
- state the transferable abstraction without relying on the paper's proprietary nouns;
- express each follow-up direction as a bounded report inference with a testable hypothesis, minimum decisive test, failure observable, and applicability boundary;
- express a perspective shift as old framing, new framing, newly visible design space, and boundary.

For design necessity and counterfactual alternatives:

- begin with the target function and operating constraints rather than the named material or module;
- distinguish physical, architectural, practical, and evidential necessity;
- distinguish component, joint, and system sufficiency;
- state what the minimum baseline already achieves and the exact failure mode;
- compare functionally equivalent alternatives under matched constraints and identify missing discriminating controls;
- use `not shown necessary`, `one implementation among alternatives`, or `superiority not established` when the evidence does not support a stronger verdict.

Do not expose `N-*` or `D-*` IDs in reader-facing prose. External priority, counterexample, and matched-comparison statements remain subject to the normal full-text and footnote eligibility rules.

## Key-figure contract

Before drafting each displayed figure or table, build a Figure Reading Packet in working notes or `view-report-audit.md`:

| Packet field | Required content |
| --- | --- |
| Display path | Run-relative path to the selected display asset |
| Source caption | MinerU/full-text caption or verified PDF caption |
| Local context | One to three relevant paragraphs before and after the exhibit |
| Later references | Later paragraphs that cite the figure or individual panels |
| Panel inventory | Every visible panel and any scientifically natural grouping |
| Canonical link | Claim IDs supported or bounded by the figure |
| Evidence judgment | Evidence mode, strength, and exact conditions |
| Boundary | Missing control, ambiguity, supplementary dependence, or other uncertainty |
| External link | Relevant Evidence IDs, or `none` |

Keep the packet out of the reader-facing report. Do not interpret from the caption alone unless full-text context is unavailable; record and surface that limitation when it affects the judgment.

For each displayed exhibit:

1. Introduce why the paper uses the exhibit and where it sits in the argument.
2. Embed a readable display asset with meaningful alt text and a run-relative path.
3. Add a short blockquote that paraphrases the caption's scientific content; do not default to a full caption translation.
4. Explain every visible panel in order. Group panels only when the caption or scientific logic naturally groups them.
5. State the claim supported, the evidence mode and strength, the relevant conditions, and the boundary.
6. State its group-meeting role only in the handoff section, not as image-processing narration.

Use this reader-facing shape when appropriate:

```markdown
### 图 X 精读：读者应从这张图看出什么

<img src="assets/figures/fig-xx-name-display.png" alt="图 X：简短图题" style="zoom:40%; max-width:100%;" />

> 图注核心内容的中文转述。

正文交代图在论证链中的位置，然后按 A、B、C-D 等自然顺序解释面板，最后说明它支持什么、不能推出什么。
```

Never embed a full-page render as a report exhibit. Files under `assets/pages/` are QA or crop inputs only and must not be mentioned or linked in `view-report.md`.

## Asset Registry and image QA

Keep the canonical Asset Registry in `assets/_manifest.md`:

| asset_id | source_type | source_ref | crop_ref | display_path | source_reason | exhibit_scope | is_full_page | source_dimensions | display_dimensions | report_zoom | readability | completeness | visual_qa | used_in_view_report |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

Use `mineru-image`, `pdf-crop`, or `manual-user-provided` for `source_type`. Keep `source_ref`, optional `crop_ref`, and `display_path` run-relative; use `none` when no crop exists. Prefer a complete readable MinerU figure/table/equation image. Use a PDF crop only when the MinerU output is missing, partial, fragmented, unreadable, or does not cover the intended exhibit. Use a manual image only when the user supplied it.

Set `is_full_page=false` for every report exhibit. Use `full-figure`, `panel-crop`, `table`, or `equation` for `exhibit_scope`. Record the reason for any fallback. Use `checked`, `failed`, or `not-applicable` for `visual_qa`; every asset used in the report must be `checked` and readable.

Create a readable `*-display.png` under `assets/figures/`, `assets/tables/`, or `assets/equations/`. Preserve legends, axes, scale bars, units, panel labels, and key visual details. A recommended physical width is 1200-1600 px or less when readability remains intact.

Use `style="zoom:40%; max-width:100%;"` by default. Use 50-60% for complex multi-panel exhibits and about 35% for simple schematics when that improves the rendered page. Report zoom does not excuse an unreadably small source asset.

Before delivery, visually inspect every used display asset at report scale and confirm that its manifest row matches the actual relative path, dimensions, zoom, scope, completeness, and use state.

## Equation contract

Include an equation only when it is necessary to understand a method, inference, fit, simulation, or conclusion. Preserve the original mathematical meaning and numbering.

Use this structure:

```markdown
**公式 (原文编号)：用途标题**

$$
\text{equation}
$$

- 为什么关键：
- 变量、单位与适用域：
- 论文如何使用：
- 支撑或导出的结论：
- 待核验参数、假设或边界条件：
```

If the paper shows no equation number, write `[UNVERIFIED: 原文未见编号]` in the internal draft and resolve it before delivery. In the final report, describe it as an unnumbered equation rather than leaving a placeholder.

Distinguish an original equation from a report-side derivation. Label any report derivation explicitly, show its premises, and do not attribute it to the authors. Do not rewrite a model fit as direct measurement or unique-mechanism proof.

When equation artwork is necessary, apply the same display-asset and manifest contract as other exhibits. Prefer accessible LaTeX for simple equations.

## External footnote contract

New reports use `reader_citation_contract: semantic-footnote-v1`. Use Markdown footnotes for external-validation sources cited in prose, but do not number them by first appearance. The semantic key is defined in `evidence-kernel.md` and must use the exact form:

```text
<first-author given name> <first-author family name>_<standard journal abbreviation>_<YYYY>
```

For example:

```markdown
<a id="ref-yujian-hu-nat-med-2025-1"></a>
该模型在外部队列中仍显示出明显的设备与协议迁移边界。[^Yujian Hu_Nat Med_2025]
```

The raw Markdown key is semantic, while the rendered body citation is only a superscript marker. Do not expose author-year text, numbered citations such as `[^1]`, temporary keys such as `[^Otani2021]`, or visible DOI/reference text in the body sentence. The invisible HTML anchor is permitted solely to support an explicit return link.

An external source is footnote-eligible only when:

- the source was actually read in full in this run;
- the cited proposition and conditions were checked;
- a page, section, figure/panel, table, equation, data point, stable HTML anchor, or justified fallback locator was verified;
- its Source Registry and Evidence Ledger rows are in sync;
- its first-author full name, standard journal abbreviation, and four-digit publication year are authoritative and normalized;
- its `Reader-facing footnote key` and `Backlink anchor IDs` are recorded in the Source Registry.

Do not cite metadata, abstracts, search snippets, citation graphs, or an unread PDF as verified evidence. Such records may remain audit candidates, but they cannot receive a reader-facing key.

Place all definitions at the end of the report under the exact heading `外部核验文献`. Each definition must contain author information, article title, journal, standard journal abbreviation, year, DOI or stable URL, evidence role, and a useful pinpoint locator. Italicize the article title and journal, and place the exact key abbreviation in brackets after the journal. Begin with the authoritative full first-author name; include the full author list when practical, while `et al.` is acceptable after that first author for a long list.

```markdown
## 外部核验文献

[^Yujian Hu_Nat Med_2025]: Yujian Hu, et al. *AI-based diagnosis of acute aortic syndrome from noncontrast CT*. *Nature Medicine* [Nat Med], 2025. DOI: https://doi.org/xxx. Evidence role: 外部性能与迁移边界核验。 Locator: p. 8, Fig. 3. [回到正文](#ref-yujian-hu-nat-med-2025-1)
```

Create `ref-<key-slug>-1`, `ref-<key-slug>-2`, and so on for each body occurrence of a source. Derive `<key-slug>` by case-folding the semantic key and replacing every run of non-letter/non-number characters with one hyphen. The definition must include one `[回到正文](#...)` link for every occurrence, in first-appearance order, and every target must exist in the body. Keep target-paper references distinct: preserve phrases such as `原文 refs. 3-8` when reporting the authors' citation chain, but do not convert those references into external-validation footnotes unless they were independently retrieved and read in this run.

Tie each footnote to the exact sentence or clause it supports. An S-grade verified source used in the final judgment must appear in prose, not only in a table or the reference list. A-grade verified sources may support mechanism, material-system plausibility, context, or boundaries when their limitations are stated.

End with the `外部核验文献` definitions when at least one external footnote is used. When external validation is out of scope or no source is eligible, do not create a decorative or empty citation section; state the validation boundary instead.

## Derived-artifact contract

Use one-way derivation:

```text
canonical Markdown registries
-> conditional analytical views
-> view-report-audit.md
-> view-report.md
-> group-meeting handoff
```

Treat these as conditional derived views:

| Artifact | Generate when | Boundary |
| --- | --- | --- |
| `auxiliary-paper-brief.md` | Detailed per-source extraction materially aids verification | Cite Source/Evidence IDs; do not create a new claim or final assessment |
| `auxiliary-evidence-cards.md` | Read/parsed auxiliary evidence needs compact routing | Cite canonical IDs; do not become an independent ledger |
| `review-matrix.md` | Comparative critique is requested or useful | Derive judgments from canonical claim/evidence status |
| `research-translation-matrix.md` | Research transfer or implementation implications are requested | Derive from applicable `C-*`, `N-*`, `D-*`, and `E-*` rows; separate evidence from inference and do not originate scientific facts |

Absence of an untriggered conditional view does not fail a core run. A generated view that disagrees with its canonical owner does fail G5.

For a full report, `view-report-audit.md` is required and internal. A focused or fully local task may omit it only when no full `view-report.md` is promised, or may use a compact form consistent with the Gates.

On correction, update the canonical owner, affected linked rows, conditional views, Report Claim Map, report prose, and handoff index in that order.

## Group-meeting handoff

When `presentation_handoff=yes`, include a `组会汇报建议` section that indexes only material already established in the report:

- the report's main argument;
- the smallest decisive figure/table set;
- approved cautious wording for high-risk claims;
- limitations and discussion questions already grounded in the analysis.

Enforce this boundary verbatim in intent:

> 本节仅索引报告中已有的主线、图表、谨慎表述和讨论点，不新增科学 claim，不生成 slide sequence、action titles 或 speaker notes。

Do not create a slide order, slide titles, layout plan, speaker notes, or presentation-only scientific claim. Do not treat the audit as the presentation's factual plan.

Use this handoff chain:

```text
paper-deep-reading
-> view-report.md / 组会汇报建议
-> paper-presentation
-> commitments.md
-> slides
```

Before handoff, expose this readiness control bundle without copying its internal IDs into `组会汇报建议`:

| Control input | Handoff meaning |
| --- | --- |
| `paper-package.md` | Must declare `evidence_contract: v1.1` for the v1.1 path |
| `view-report-audit.md` | Supplies G0-G5 results and the Report Claim Map for readiness control only, not slide planning |
| Claim/Evidence/Asset traces | Canonical `C-*`, `E-*`, and asset records remain available for trace checks; reference their owners rather than cloning them into presentation files |
| `view-report.md` / `组会汇报建议` | Supplies the reader-facing semantic input and seed material |

Conditional views are not handoff prerequisites. Their absence cannot block presentation readiness; if a generated conditional view conflicts with a canonical trace, G5 must block the handoff.

`commitments.md` is the sole source of truth for downstream presentation commitments and planning, but it is not a new scientific evidence owner. Every scientific commitment must remain traceable to the handoff's canonical records. The presentation skill may use a legacy fallback for v1.0.x artifacts; do not rewrite legacy inputs or manufacture a v1.1 audit to bypass that compatibility path.

## Delivery QA

Pass G5 only when all applicable checks succeed:

| Area | Pass condition |
| --- | --- |
| Claim and judgment mapping | Every strong report claim or research judgment maps to canonical support and all map rows are `in-sync` |
| Canonical integrity | `check_canonical.py --run-dir <actual-run-directory>` passes separately from footnotes; linked IDs, controlled states, one-source/one-claim evidence rows and distinct-source counters are valid |
| Reader boundary | No modes, workflow names, internal IDs, raw paths, hashes, logs, or QA narration leak into the report |
| Epistemic wording | Conditions and evidence modes remain distinct; every downgrade appears in reader-facing wording |
| Research judgment | Triggered originality/design sections preserve baselines, functions, necessity/sufficiency scope, alternatives, decisive tests, and unresolved boundaries without logical inflation |
| Figures | Dynamic selection, complete panel interpretation, relative display paths, readable assets, and synchronized manifest |
| Equations | Correct meaning/numbering, variables and units, use, inference, assumptions, and boundaries |
| Footnotes | `semantic-footnote-v1`; semantic keys use normalized full author/journal/year fields; body markers are superscripts only; definitions are under `外部核验文献`; every definition has a locator and explicit `[回到正文]`; Source Registry and Evidence Ledger are synchronized; no metadata-only evidence |
| Derived views | Generated views match canonical owners; untriggered conditional views are not required |
| Handoff | No new claim or slide plan; `paper-presentation` owns `commitments.md` |
| Filesystem | Every report-relative target exists; no unresolved placeholder; no pre-existing or legacy directory was overwritten or reorganized |

G5 permits only `pass` or `blocked`. Repair broken links, stale derived state, missing citations, unreadable assets, and placeholder text before delivery; do not downgrade these mechanical failures into prose caveats.

For a semantic-footnote report, the audit's structured Gate table must contain exactly one G5 row with `Status=pass`. The G5 portion of `view-report-audit.md` must also contain the exact line `reader_citation_contract: semantic-footnote-v1` and this structured Footnote Map. Separate anchor IDs with a comma and one space, in first-appearance order.

| Reader-facing footnote key | Source ID | Backlink anchor IDs |
| --- | --- | --- |
| Yujian Hu_Nat Med_2025 | S1 | ref-yujian-hu-nat-med-2025-1 |

The Footnote Map must match the report and Source Registry exactly, including the key set, Source IDs, anchor order, and absence of extra IDs. It is a derived audit view; the Source Registry remains the canonical owner of the key and anchor fields.
