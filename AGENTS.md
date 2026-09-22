# Research Collab maintenance

- The only editable Skill sources are under skills/<skill-name>. Installed copies
  and generated ZIPs are deployment artifacts. Preserve each Skill's invocation
  policy, contracts, versions, and external-service authorization boundaries.
- Use scripts/skills.py for validate/package/install/check/restore. Inspect a
  target before adoption; preserve drift, user settings, and unknown files.
- Run scripts/validate.py for affected offline regressions. Supply --plot-python
  for an existing Sci-Plot environment. Never install dependencies, upgrade
  runtimes, register MCP servers, or launch research as part of these checks.
- Keep source provenance, licenses and component changelogs. Sciverse contracts
  live under contracts/sciverse-research; its routing cases live under tests.
- Put migration evidence, host paths, backups, installation settings and test
  output under ignored .local/. Keep papers, real reports, personal profiles,
  tokens, browser state and historical research runs outside public commits.
- MAPPER_LEGACY_WORKSPACE is an explicit read-only opt-in for historical Mapper
  regression. Ordinary tests generate synthetic fixtures in the test directory.
- Do not modify archived projects except a migration pointer. Do not modify
  other Skills, plugin caches, workspace root rules, or human decision records.
- Use subagents only when the user explicitly requests delegation.
