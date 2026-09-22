# Changelog

## Unreleased - 2026-08-25

- Added `STATUS.md` with the current implementation, verification evidence,
  external Elsevier access status, and remaining closure work.
- Recorded successful loading of the opt-in Codex `literature` profile while
  keeping paper-search MCP out of the default configuration.
- Documented that Elsevier Article Retrieval still returns HTTP 403 even though
  campus-browser subscription access succeeds.
- Recorded the unresolved automatic retrieval pipeline, manifest generation,
  and Skill discovery work.

## 0.1.0 - 2026-08-18

- Established the local maintenance repository.
- Added the canonical `literature-fulltext-acquisition` Skill source.
- Added guarded wrappers for paper-search, OpenAlex Official CLI, and InstSci.
- Recorded pinned upstream versions and the OpenAlex Windows compatibility patch.
- Added smoke tests and an opt-in paper-search MCP configuration template.
- Documented that the optional MCP profile/launcher is not wired yet.
