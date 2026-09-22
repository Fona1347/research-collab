# Changelog

## Unreleased

No changes yet.

## v2.0.0 - 2026-09-23

First Research Collab collection release, following the Paper Collab V1.2.1 lineage.
Includes nine independently versioned Skills; evidence schemas remain unchanged.

- Bind new distributions to explicit per-Skill inventories and require an explicit original restore target with receipt ownership checks; retain legitimate old backups/archive reads.
- Reject stale or unverifiable MinerU input caches; check public HTTP destinations and DNS before connections and every redirect, including robots, and strip cross-origin credentials.
- Apply Sci-Plot panel styles at axes creation, retain fonts at export, and share bar/heatmap data guards between validation and rendering (0.2.1).
- Capture Quick's run date once and add an optional deterministic --date without changing schema 1.2.
- Separate standard reading quality from remote-upload/wider-library authorization, reuse existing grants, and make source-content trust and outgoing-material boundaries explicit across all nine Skills.
- Add read-only Presentation handoff checks and Quick behavior coverage; enable same-repository canonical integration by default and add offline CI with actionable missing-PowerShell diagnostics.
- Document capability/compatibility limits and add bounded synthetic scientific-semantic evaluation cases, separate from structural tests.

- Rewrite the English and Chinese READMEs with a minimal local-reading quickstart and task-specific configuration guidance.
- Use a portable legacy-fixture layout in public Mapper tests while retaining historical hashes and validation assertions; keep original notebook locations private.
- Consolidate nine maintained research Skills under a single editable source tree.
- Add portable packaging, reviewed installation adoption, drift protection and rollback.
- Preserve existing Skill identifiers, evidence schemas and independent version history.
- Keep private research context and external runtimes outside public distributions.
- Preserve the newer Sciverse selection boundary from the active installation.
- Formalized `semantic-footnote-v1` for `paper-deep-reading`: normalized full first-author names, standard journal abbreviations, four-digit years, superscript-only body markers, complete end-of-report definitions, explicit `回到正文` backlinks, Source Registry key fields, and mechanical G5 validation.
- Added a backward-compatible Research Judgment Contract with triggered canonical `N-*` and `D-*` registries for originality, research generativity, perspective shifts, and function-first analysis of design necessity, sufficiency, baselines, counterfactual alternatives, discriminating controls, and matched comparisons.

## V1.2.1 - 2026-07-13

- Changed automatic run names to use the complete first-author name and a journal or publisher abbreviation, with distinct Zotero and non-Zotero separators.
- Added workspace-root `.paper-collab.yaml` output preferences, explicit-path precedence, collision-safe automatic directories, and protection for explicitly named directories.
- Standardized every available main PDF as run-root `<task_name>.pdf`; local and Zotero sources are copied rather than moved, and copied bytes are verified by SHA256.
- Added a narrow copy-only Zotero main-attachment route with formal-publication preference, ambiguity handling, and an absolute prohibition on Zotero writes or source modification.
- Retained `evidence_contract: v1.1`, the V1.0.x presentation fallback, and the existing `paper-presentation` interface.
- Published the runtime Skill payload in a fresh, sanitized repository without local history, research outputs, or machine configuration.
