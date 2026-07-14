# Security Policy

## Supported Version

Security and privacy fixes target the latest published Paper Collab release.

## Reporting a Vulnerability

Do not open a public issue containing credentials, private papers, copyrighted full text, Zotero paths, attachment identifiers, unpublished research, or personal information.

Use GitHub's private vulnerability reporting for this repository when available. If that option is unavailable, contact the maintainer through a private channel listed on the maintainer's GitHub profile and include only the minimum information needed to reproduce the issue.

## Data-Safety Expectations

- Treat `.paper-collab.yaml` as local-only configuration.
- Never commit generated reports, PDFs, parser caches, Zotero exports, tokens, or environment files.
- Installing these Skills grants no filesystem, Zotero, network, parser, or upload permission.
- Zotero sources must remain read-only unless a user separately and explicitly authorizes a different workflow outside these Skills.
