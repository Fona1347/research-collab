# Privacy

Zotero Literature Note is a Codex skill workflow. It does not include a standalone Zotero client, external service, or telemetry system.

## Defaults

- Zotero is read-first. The skill should not write to or modify a Zotero library unless the user explicitly asks.
- Web search is optional and should be requested before use.
- Raw PDF parsing, uploads, and MinerU processing should be requested before use when they may expose document content outside the local environment.
- Final notes should not expose absolute Zotero storage paths, profile paths, local file URLs, or internal cache paths.

## Local Materials

The skill may guide Codex to inspect Zotero metadata, BibTeX, child notes, annotations, PDF attachments, indexed full text, and verified MinerU cache content when the user's Codex environment provides those capabilities.

Generated notes should use portable relative paths for assets and should keep source inventory details separate from the reader-facing note body.

## User Responsibility

Review prompts, tool permissions, generated notes, and exported assets before sharing them. Do not use the skill on confidential papers or private notes unless the active Codex environment and enabled tools are appropriate for that material.
