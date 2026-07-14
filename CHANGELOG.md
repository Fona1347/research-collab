# Changelog

## V1.2.1 - 2026-07-13

- Changed automatic run names to use the complete first-author name and a journal or publisher abbreviation, with distinct Zotero and non-Zotero separators.
- Added workspace-root `.paper-collab.yaml` output preferences, explicit-path precedence, collision-safe automatic directories, and protection for explicitly named directories.
- Standardized every available main PDF as run-root `<task_name>.pdf`; local and Zotero sources are copied rather than moved, and copied bytes are verified by SHA256.
- Added a narrow copy-only Zotero main-attachment route with formal-publication preference, ambiguity handling, and an absolute prohibition on Zotero writes or source modification.
- Retained `evidence_contract: v1.1`, the V1.0.x presentation fallback, and the existing `paper-presentation` interface.
- Published the runtime Skill payload in a fresh, sanitized repository without local history, research outputs, or machine configuration.
