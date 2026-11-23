# Experimental acquisition adapter

The imported adapter retains its existing guarded CLI and access boundaries.
Its original local status diary remains in the archived project.

The collection adds a portable wrapper location and local runtime configuration.
It does not install, upgrade, register or authenticate upstream tools.
The external compatibility baseline is recorded in tools.lock.json.

Outstanding limitations:
- End-to-end live acquisition is not certified by offline tests.
- Institutional entitlement and publisher API access remain external prerequisites.
- The retrieval manifest is produced by the agent workflow, not automatically by
  the wrapper.
- MCP registration remains opt-in; an example template is not an active profile.
- The current adapter targets Windows and PowerShell 7.
