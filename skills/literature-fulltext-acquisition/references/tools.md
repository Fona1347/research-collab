# Local tool reference

## Guarded entry point

Resolve scripts/literature-tools.ps1 relative to this Skill's SKILL.md. Its command
shape remains: literature-tools.ps1 TOOL [TOOL_ARGUMENTS]. Never assume a working
directory or an archived development repository.

Copy config/local.example.json to config/local.json and set absolute tools_root
and protected_root for the existing installation. This file is local, excluded
from releases, and preserved during updates. Environment variables
LITERATURE_TOOLS_ROOT and LITERATURE_PROTECTED_ROOT override the matching local
values. Store no credentials in this configuration.

tools_root contains runtimes/paper-search/.venv, runtimes/openalex/.venv,
runtimes/instsci/.venv and state/. protected_root is the shared tool workspace
that must never receive downloaded research content. The wrapper blocks both
that root and tools_root as output destinations. Missing configuration or tools
does not authorize installation, live retrieval, or access-control bypasses.

Run the wrapper with status first. It reports installed/missing executables and
credential presence without values. This adapter currently targets Windows and
PowerShell 7; the external runtimes remain separate dependencies.

## OA and institution routes

- paper-search download requires an explicit -o or --save-path destination.
- openalex download requires -o or --output; --content additionally requires an
  OA/license filter. Cached content can consume credits; follow the user's scope.
- instsci papers accepts an explicit DOI-list path, --publisher auto, --output,
  --no-broker, and --concurrency 1. Only user-authorized institutional access is
  allowed. The user completes visible login, MFA, CAPTCHA, and consent.
- Hand only unresolved OA requests to the institutional stage; do not race the
  same DOI across providers.
- config/literature.config.toml.example is an opt-in MCP template. Substitute its
  placeholders deliberately; installing this Skill never registers a server.
  download_scihub and download_with_fallback remain disabled.

Compatibility patches are maintained outside the Skill in the collection's
maintenance/literature-fulltext-acquisition directory. Their presence is not
evidence that an external runtime is patched; the existing runtime check remains.
