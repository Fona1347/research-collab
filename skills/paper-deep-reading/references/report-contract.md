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

Treat `view-report.md` as a derived Chinese reader view, not a run log or canonical ledger. Synthesize canonical claims and research judgments into a sufficiently developed explanation of the paper. A key scientific claim or final judgment must have support in the Claim Registry, triggered `N-*`/`D-*` Research Judgment Registries, or Evidence Ledger.

Keep these items out of `view-report.md`:

- task/validation mode names and workflow-stage narration;
- Claim, Research-Idea, Design-Choice, Source, Evidence, Asset, card, or Gate IDs;
- raw operational MinerU, Zotero, cache, download, or system paths;
- hashes, permission logs, download logs, audit tables, or QA checklists;
- crop/render/staging instructions and `assets/pages/` links;
- internal module names such as `V8`, template labels, or agent-role labels;
- unresolved placeholders such as `[MISSING]`, `[TODO]`, `FIXME`, bare `[UNVERIFIED]`, or dummy citations.

An explicit `[UNVERIFIED: concrete reason]` may remain only when it is a reader-relevant evidence status whose reason and consequence are explained in prose. It is not a substitute for unfinished work. Convert missing information into a scoped limitation, `not established within scope`, or `blocked`; otherwise remove the placeholder before G5.

Translate internal provenance into readable evidence language and pinpoint anchors. Paper versions, reading dates, material coverage and useful resource links are reader context. Use meaningful link labels, run-relative targets for staged files, and working links to relevant user-selected workspace resources. Never expose source Zotero storage/profile paths or parser/cache internals. Preserve scientific limitations where they affect interpretation.

## Preconditions and Report Claim Map

Assemble strong report claims only after G0-G4 have a permitted state. Generate `view-report-audit.md` for every full report; a focused or fully local task may use a compact version.

Maintain this normative Report Claim Map in the audit:

| Report claim or judgment | Report section or paragraph | Canonical `C-*`, `N-*`, or `D-*` IDs | Main-paper locator or Evidence IDs | Intended wording strength | Gate status | Sync status |
| --- | --- | --- | --- | --- | --- | --- |

Map every strong, quantitative, novelty, causal, reliability, originality, perspective, necessity, sufficiency, alternative, superiority, and final-judgment statement. Use `in-sync` or `stale` for Sync status. Do not deliver while any mapped row is `stale`.

If drafting reveals a new key claim or research judgment, stop assembly, create or revise the canonical Claim Registry or applicable `N-*`/`D-*` row, update evidence and Gate decisions, then return to the report. Do not backfill provenance after publication-quality prose has already hardened the claim.

The audit remains internal. Do not use it as the main input to presentation planning; the presentation skill consumes the reader-facing report and creates its own commitments.

## Reader-facing structure

Use the paper's actual argument and the user's reading purpose to choose headings and depth. The following modules specify coverage; combine related material instead of repeating it under separate headings. Registry structure is not report structure.

| Module | Requirement |
| --- | --- |
| `论文信息卡` | Required; paper identity, version, dates, reading coverage and useful material links |
| Core answer and full-paper overview | Required in substance for a full report; may share an opening section, with a clear answer and a map of the argument |
| Background, research question and contribution | Required in substance; connect relevant prior work and unresolved problems to the paper's approach |
| Method and reasoning/evidence chain | Required in substance; develop the method rationale, key equations or reasoning steps, and distinguish evidence modes |
| External evidence and related work | Include when external validation is in scope; explain how comparisons affect interpretation under a reader-relevant heading, and state actual coverage when checks are out of scope or incomplete |
| Originality, research generativity, and perspective | Cover applicable `N-*` judgments when triggered; integrate with contribution/evidence discussion where clearer |
| Design necessity, sufficiency, and alternatives | Cover applicable `D-*` judgments when triggered; integrate with method/evidence discussion where clearer |
| `关键图表精读` | Required when the paper has decision-relevant figures or tables; use a dynamic number of exhibits |
| Key equations/model logic | Develop the equations, derivations or simulation logic that carry the argument, including their consequential links |
| Meaning, limitations, and credibility | Required in substance; separate internal support from external validation where applicable |
| Open questions | Required when material uncertainties remain |
| `组会汇报建议` | Include only when `presentation_handoff=yes` |
| `外部核验文献` | Include when external sources are cited |

Build the information card from verified source identity and the actual reading record in `paper-package.md`. Include the title, first author(s) and corresponding author(s) as marked in the source, venue/citation, and DOI with the full identifier as link text. Keep online/publication date and the version read (such as preprint, accepted manuscript or Article in Press) distinct from reading, revision and archive dates. Describe materials actually used, with page/file coverage when useful; link available main text, supplements, data, review files, source archives or related analyses that help the reader. A related-resource link does not imply the material was read. Record missing metadata plainly rather than infer authorship roles or dates.

Develop background at the level the question needs: orient the reader to the broader topic, then explain what the closest relevant work established, what remains unresolved, and why this paper's move addresses that gap. Connect this rationale to the analysis, tests, proof or interpretation and the resulting contribution. These are relationships to explain, not mandatory headings or a fixed linear story; arguments may branch, compare alternatives or revise a concept. Attribute prior-work accounts from the main paper, and use verified external evidence for independent contribution judgments.

There is no default total length or section quota. Let complexity and reading purpose determine depth. Preserve the explanatory middle: definitions by their role, method choices, key derivations or feedback, reasons for controls, meaningful examples and comparisons. Remove duplicated conclusions, process labels and empty transitions; an explanation that connects evidence to a conclusion is substantive content. Give the body room to develop what the overview only introduces.

Develop one point per paragraph with its evidence. Use tables for comparisons or detailed values and lists for parallel items. Use bold selectively for meaningful short figure captions, panel-group leads or paragraph judgments that help a reader scan the argument. Choose emphasis by semantic importance, not a fixed sentence position, panel label, number or template slot; keep supporting explanation in normal text.

Select exhibits for their explanatory roles, including informative controls and contrary results, without a minimum or maximum count. Figures and tables often carry the argument; connect them through the questions they answer and the next reasoning step. They may be integrated with topic sections or collected under `关键图表精读`; nonconsecutive figures and logically grouped panels are welcome.

## Core conclusion and fulltext overview

Open with the research object, question and substantive answer, supported by the paper's decisive reasoning and essential conditions. The core answer and overview can be combined when that reads better. Avoid generic praise and unverified superlatives.

Use the overview to orient readers through the actual argument: how the problem arises, the authors' key move, and how the evidence or reasoning develops the answer. A short narrative, an optional arrow sequence or a comparison of explanations can serve this purpose. An arrow may show reading order or logical dependence; do not turn it into an unsupported causal claim.

Keep this entry easy to scan; an approximately two-minute overview is an orientation option, not a length constraint on the report. Develop methods, equations, evidence and external comparisons in the body. Every strong opening statement maps to that later support through the Report Claim Map, with consequential uncertainty retained.

## Evidence language

Make the provenance class legible in prose without printing internal IDs:

| Provenance | Reader-facing treatment |
| --- | --- |
| Main-paper evidence | Anchor to the relevant figure/panel, table, equation, section, or reported condition |
| External evidence | State whether it supports, weakens, contradicts, or contextualizes the main claim and attach a verified footnote |
| Inference | Mark as the report's interpretation and state the premises and boundary |
| User assumption | Identify it explicitly; do not merge it into the paper's conclusion |

Anchor major claims to evidence and explain the link without inventing a causal or logical bridge. Place limitations beside the affected conclusions; explain a shared limitation once with clear scope. Standalone takeaways still need their essential qualifications. Avoid generic caveats on every paragraph; never hide material downgrades in internal records.

Select numbers for scale, comparison, uncertainty, applicability, or reproduction; explain their meaning. Retain denominators, sample sizes, uncertainty, thresholds, and exact conditions when they affect judgment. Distinguish measured, fitted, and extrapolated values. Put other recorded detail in useful tables or internal records. Use no numerical quota, and do not broaden a claim or erase conflict by compressing it.

Use `first`, `fastest`, `highest`, `proves`, `completely excludes`, `breakthrough`, or equivalent wording only when the canonical records pass the high-risk epistemic check. A cautious synonym is not a valid repair if the underlying proposition remains too broad.

Preserve condition tuples in comparisons. Do not combine, for example, a 600 ps result from one condition with a 358 K result from another into one apparent operating point.

Use callouts sparingly for a reader-critical takeaway, caution, or next step. A callout must not replace the evidence paragraph or carry an otherwise unsupported strong statement.

## Research-judgment modules

Follow [research-judgment.md](research-judgment.md) when triggered. Explain what the nearest prior work already achieved, the remaining constraint, and what this paper adds. Distinguish why a problem deserves study, why the chosen approach is reasonable, and whether the evidence establishes a design's necessity or sufficiency under stated conditions. Preserve the registry's baselines, alternatives, joint dependencies, scoped verdict and unresolved evidence within the argument.

Organize related work by its relationship to the main question: a direct precursor, methodological basis, alternative explanation or comparison that changes the judgment. A paragraph can open with a short bold relationship statement, explain the evidence and conditions, then return to what it clarifies about the present paper. Retain decisive external comparisons even when they require more space. External priority, counterexample and comparison claims retain normal full-text and footnote requirements.

Offer a reasoned reading: what becomes clearer through the comparison, which assumption matters, or which idea can transfer. Mark report-side inference and connect it to canonical premises. Include follow-up directions when requested or grounded in a useful unresolved question, retaining the hypothesis, decisive test, failure observable and boundary; do not manufacture a novel viewpoint or future direction to fill a section.

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

1. Introduce the question, comparison or reasoning step the exhibit addresses and connect it to the surrounding argument.
2. Embed a readable display asset with meaningful alt text and a run-relative path.
3. Explain every visible panel in scientifically coherent groups: how to read the relevant features, what is observed or compared, and how that bears on the argument. Preserve evidence mode, strength, conditions and boundaries. Explain the method or control rationale where it enables understanding.

Use a short descriptive caption or panel-group lead when it helps navigation, with selective bold as described above. For example, **图3｜从预测到观测的对应。** identifies a role in the argument; the following prose must explain the actual comparison. Adapt wording and grouping to the exhibit, including conceptual diagrams, proofs or qualitative evidence. Avoid repeating the full explanation in both caption and body. Put group-meeting roles only in the handoff section.

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

Retain equations that carry key definitions, governing relations, model coupling, proof steps, fits or inference, preserving their mathematical meaning and original numbering. Present a linked system when the relationships between equations explain how the method works; module names or a list of functions are insufficient substitutes. Select depth by the paper's argument, without an equation quota or a requirement to add mathematics where it has no explanatory role.

Explain purpose, variables, applicable units, domain, assumptions and boundary conditions. Walk through the consequential intermediate steps: what enters, what is solved or inferred, how terms or modules interact, and how the result answers the question. Use prose, a worked example, derivation or symbol table as appropriate. Keep enough mathematical detail for readers to reconstruct the reasoning; move routine algebra or reproduction parameters to a useful supporting location.

Verify the original number when one exists; otherwise describe it as an unnumbered equation. Resolve uncertain numbering against the source before delivery rather than leaving a placeholder.

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

Propagate corrections through the canonical owner, linked rows, conditional views, Report Claim Map, report prose, and handoff index in that order, updating only affected records. Apply the continuation rules in `evidence-kernel.md` when earlier work remains valid.

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
| Reader boundary | No modes, workflow names, internal IDs, raw operational paths, hashes, logs, or QA narration; verified paper/author/version/date information, actual material coverage and useful reader links are present |
| Explanation and selection | Read for comprehension, then check against sources and canonical records: sufficient background and prior-work context, clear method rationale, key equations and reasoning links, meaningful exhibit roles and contribution judgment; no invented links or loss of material conditions, uncertainty or conflicting evidence |
| Epistemic wording | Conditions and evidence modes remain distinct; every applicable downgrade is visible, near the affected claim or in a clearly scoped shared explanation |
| Research judgment | Triggered originality/design judgments preserve baselines, functions, necessity/sufficiency scope, alternatives, applicable decisive tests, and unresolved boundaries without logical inflation |
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
