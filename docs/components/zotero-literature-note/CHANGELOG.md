# Changelog

## Unreleased

- Standardized the current public display name as `Zotero Literature Note` across skill metadata, repository documentation, examples, validation, and release tooling while keeping `zotero-literature-note` as the repository, package, skill, and invocation name.

## 0.3.0-beta - 2026-07-14

- Prepared the first public beta release for ZotLiteNote.
- Adopted `ZotLiteNote` as the public display name while keeping `zotero-literature-note` as the repository, package, skill, and invocation name.
- Added public release, privacy, security, contribution, CI, export, and package-generation documentation.
- Added a synthetic example output for public inspection.
- Replaced release examples derived from local papers or workspaces with generic placeholders.
- Added fail-closed skill, repository, archive, and privacy validation.
- Added a strict public-file export manifest and included the MIT license in the installable release archive.

## 0.2.3 - 2026-07-13

- Standardized public project naming on `zotero-literature-note` to match the installable skill folder and Codex invocation name.
- Replaced the README installation example with a generic `<codex-skills-dir>/zotero-literature-note/` target.
- Replaced workspace-specific deployment path examples and records with `<repo-root>` and `<workspace-root>` placeholders.
- Solidified the crop-first visual evidence workflow: final notes should prefer cropped figures or selected panel crops, while rendered full PDF pages remain QA fallback or page evidence.
- Added explicit crop decision ladder, crop acceptance criteria, and source-inventory fields for crop source, source page, crop kind, insertion/fallback role, QA status, fallback page asset, and manual/automatic crop notes.
- Clarified that PDF toolchains support high-resolution render-to-crop workflows rather than treating whole-page screenshots as completed visual evidence.
- Updated the layered explainer template, README, static checklist, and validator checks for figure/panel crop behavior.

## 0.2.2 - 2026-07-09

- Updated visual asset output rules to match Typora's note-specific sibling directory convention: `<note-filename-without-.md>.assets/`.
- Updated workflow, output versioning, visual evidence policy, PDF toolchain guidance, layered explainer template, README, and static checklist to use note-specific asset directories instead of a shared `<paper-dir>/.assets/`.
- Added a dual-track visual evidence workflow: cropped figures/panels are preferred for main-note insertion, while rendered full pages are retained as QA fallback or page evidence.
- Added source inventory distinctions for main-note crops, panel crops, page evidence, QA candidates, and unused candidates.

## 0.2.1 - 2026-07-09

- Added visual evidence collection and figure/table QA workflow.
- Added `references/visual-evidence-policy.md` for image selection, `.assets` output, Typora-friendly insertion, QA, and evidence labeling.
- Added `references/pdf-toolchain-appendix.md` for local PDF toolchain selection and minimum viable fallbacks.
- Updated output versioning to support `.assets` and relative-path image insertion with 1200px width guidance.
- Updated the layered explainer template to insert figures before figure-reading notes.

## 0.2.0 - 2026-07-09

- Added explicit `[LLM for Zotero] MinerU cache` discovery and validation workflow.
- Added `references/mineru-cache-policy.md` for cache identity, read order, fallback, and privacy rules.
- Updated evidence priority to prefer verified MinerU `full.md` and structured cache evidence for paper-content tasks.
- Expanded source inventory requirements for cache attachment keys, PDF attachment keys, cache status, used files, and read scope.
- Added a reusable Zotero + MinerU cache inventory prompt template.

## 0.1.0 - 2026-07-09

- Added workspace-level deployment validation workflow for `zotero-literature-note`.
- Documented `.codex/skills/zotero-literature-note` as the local test deployment target.
- Added static structure and privacy validation support.
- Kept runtime skill package script-free and Zotero-plugin-driven.
