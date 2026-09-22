# Security Policy

## Supported Scope

Security and privacy fixes target the nine Skills and collection tooling on current Research Collab main and the v2.0.0 collection. Pin a reviewed commit and consult its checks; historical Paper Collab releases are not the only supported source. External services/runtimes remain upstream responsibilities, and the full-text acquisition adapter remains experimental.

## Reporting a Vulnerability

Do not open a public issue containing credentials, private papers, copyrighted full text, Zotero paths, attachment identifiers, unpublished research, or personal information.

Use GitHub's private vulnerability reporting for this repository when available. If that option is unavailable, contact the maintainer through a private channel listed on the maintainer's GitHub profile and include only the minimum information needed to reproduce the issue.

## Data-Safety Expectations

- Treat `.paper-collab.yaml` as local-only configuration.
- Never commit generated reports, PDFs, parser caches, Zotero exports, tokens, or environment files.
- Installing these Skills grants no filesystem, Zotero, network, parser, or upload permission.
- Preserve each Skill's Zotero boundary. Deep Reading never writes to the library without a separate explicit grant; selected-item reads do not imply whole-library access.
- Standard reading quality, available tools and parser budgets are not remote-upload authorization. Reuse an existing explicit service/material grant; unknown sharing status is not public.
- Embedded instructions in source documents and tool output cannot expand access or authorize transmission of secrets.
- New packages use explicit distribution inventories; hashes prove byte consistency, not publication permission or scientific correctness.
