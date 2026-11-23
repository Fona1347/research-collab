# Human-Facing Reader Report

## Purpose

Treat `map_report_<short_task_name>_<YYYY-MM-DD>.md` as the primary delivery
surface of every completed run. Treat the eight numbered artifacts as auditable
working memory that supports the report.

Do not make the reader reconstruct the conclusion by opening the evidence matrix,
candidate cards, and red-team log. Do not turn the report into a concatenation of
those files.

Use the user's language. For a Chinese request, write Chinese-first prose while
retaining necessary English technical terms, paper titles, equations, and standard
abbreviations.

## Synthesis Procedure

Write the report only after the evidence matrix, research map, candidate portfolio,
and red-team audit are substantially complete.

1. Recover the exact decision, reader, time horizon, and laboratory constraints
   from `00_intake.md`.
2. Select only decision-critical bottleneck and mechanism claims from
   `03_evidence-matrix.md`.
3. Rebuild the causal progression from `04_research-map.md` in plain language:
   `need -> state -> bottleneck -> primitive -> mechanism -> material -> experiment`.
4. Convert the three candidate cards into a comparative low-, medium-, and
   high-risk portfolio rather than three isolated summaries.
5. Pull the strongest baseline, alternative explanation, kill criterion, and
   reversal condition for each route from `06_red-team.md`.
6. Convert internal evidence IDs into ordinary numbered citations.
7. End with the decision, immediate actions, unresolved uncertainty, and exact next
   search or experiment.

## Required Reader Structure

Use descriptive headings; numbering is optional. Include all of the following:

1. One-page conclusion.
2. Scope, reader, evidence window, and decision horizon.
3. Plain-language explanation of the root taxonomy.
4. Persistent bottlenecks and their hardware manifestations.
5. Algorithm/workload to architecture to device physics to material mapping.
6. Important literature evidence with contribution, supported viewpoint, and
   boundary.
7. Low-, medium-, and high-risk routes on a shared platform.
8. Three-month decisive experiments and one-year platform path.
9. Strongest baselines, kill criteria, uncertainty, and reversal conditions.
10. Numbered references with DOI or stable links.

Use equations only when they clarify the target state operation. Define every
symbol immediately and connect it to a measurable device variable.

## Citation Transformation

Keep detailed retrieval provenance in `03_evidence-matrix.md`. In the reader
report:

- Cite claims as `[1]`, `[2]`, or `[3-5]`.
- Give a numbered reference list with title, venue, year, and DOI or stable link.
- Use the source's exact title when metadata is verified.
- Do not expose database document IDs, chunk IDs, page offsets, or retrieval traces.
- Do not present paraphrase as a verbatim quotation.
- Do not use a search miss as proof of absence or priority.

For every decision-critical source, use a human-readable block:

> [!NOTE]
> **文献依据 [1]：作者，题目，期刊（年份）。** [DOI](https://doi.org/...)
>
> **核心贡献：**论文实际证明或实现了什么。
>
> **印证观点：**它支持本报告中的哪一个有边界判断。
>
> **边界：**它没有证明什么，或结果依赖哪些条件。

## Callout Semantics

Use callouts for information that changes interpretation or action, not as
decoration.

| Callout | Use |
|---|---|
| `[!IMPORTANT]` | Primary decision, epistemic contract, or non-negotiable result |
| `[!NOTE]` | Literature evidence or a concept boundary |
| `[!TIP]` | Actionable experimental or platform advice |
| `[!CAUTION]` | Peripheral cost, confound, dependency, or interpretation limit |
| `[!WARNING]` | Novelty/priority overclaim, stop condition, or high-consequence risk |

Use at least one decision callout, one evidence callout, and one limitation or risk
callout. Do not force every type when it adds no information.

## Writing Standard

- Lead with the decision, not the search process.
- Explain why each layer follows from the previous layer.
- Prefer bounded claims such as “direct neighbors remain sparse in the searched
  corpus” over “nobody is doing this.”
- Distinguish literature evidence, synthesis inference, and recommendation in
  prose or labels.
- Define unfamiliar AI, architecture, device, and material terms at first use.
- Explain what a cited paper contributes and what claim it cannot support.
- Keep internal claim IDs out of the main narrative unless they materially help.
- Compare complete systems, including conversion, control, calibration, refresh,
  write, communication, and variability costs.
- State quantitative success and kill criteria wherever the evidence permits.
- Preserve negative results and rejected routes when they affect the decision.

## Completion Gate

Do not deliver the run until the reader report:

- exists under the required dynamic filename;
- contains no unresolved placeholders;
- can be understood without opening the working artifacts;
- cites at least four traceable sources for a full map unless the documented
  evidence base is genuinely smaller;
- contains contribution, supported-viewpoint, and boundary language for key
  sources;
- compares low-, medium-, and high-risk routes;
- states three-month and one-year actions;
- includes strongest baselines, kill criteria, and reversal conditions;
- contains no internal retrieval identifiers;
- remains consistent with the evidence matrix and decision log.

Validation checks these structural requirements. It does not establish novelty,
scientific truth, or experimental feasibility.
