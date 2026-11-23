# Contributing

Edit the canonical skills/<skill-name> source, retain its behavioral contract and
external authorization boundaries, and describe the user-visible effect.

Run scripts/skills.py validate and the affected scripts/validate.py component group.
Use synthetic/publicly distributable fixtures. Include installation or packaging
tests when those interfaces change. Preserve versions and source provenance.

Keep papers, real reports, private profiles, API keys, browser state, environments,
and host-specific runtime settings out of public commits. Do not update installed
copies first, add automatic dependency installation, or trigger research while
testing maintenance changes.

Collection changes are reviewed by pull request. A Skill's version, the collection
release and its evidence schema are separate concepts.
