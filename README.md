# Research Collab

A maintained collection of nine research Skills: discovery, evidence-grounded
reading, research-route decisions, plotting and presentation planning.

[简体中文](README.zh-CN.md) · [Maintenance and installation](docs/maintenance.md) ·
[Sources and dependencies](docs/sources.md)

The collection expansion is **Unreleased**. The previous Paper Collab package
release is V1.2.1; individual Skill and evidence-schema versions remain independent.
No research workflow starts merely because this collection is installed.

| Skill | Purpose |
|---|---|
| paper-deep-reading | Single-paper reading, canonical-source integrity and research judgment |
| paper-presentation | Presentation plans from approved reading artifacts |
| zotero-literature-note | Structured notes from user-selected Zotero material |
| research-lookup-enhanced | Bounded discovery and traceable evidence packets |
| sciverse-research | Supported-corpus evidence and Sciverse/Paper Schema workflows |
| research-opportunity-mapper | Formal research-route comparison, focus and audits |
| research-opportunity-mapper-quick | Standalone lightweight opportunity mapping |
| sci-plot | Deterministic numeric scientific figures and export checks |
| literature-fulltext-acquisition | Experimental orchestration of authorized full-text acquisition |

## Develop and install

Edit each Skill under skills/<skill-name>. Its own scripts, references and assets
remain together, including Sci-Plot's src/sci_plot package. Component development
documentation, contracts and collection tooling live outside the Skill folders.

Use Python 3.11+ for the collection tools. From the repository root:

    python scripts/skills.py validate
    python scripts/skills.py package --skill paper-deep-reading --output dist/reading-preview.zip
    python scripts/skills.py package --output dist/research-collab-preview.zip
    python scripts/skills.py install --skill paper-deep-reading --skills-root <absolute-skills-directory> --dry-run
    python scripts/skills.py install --skill paper-deep-reading --skills-root <absolute-skills-directory>
    python scripts/skills.py check --skill paper-deep-reading --skills-root <absolute-skills-directory>

Repeat --skill to select several components. Omission selects all nine, including
the experimental acquisition adapter. Archives contain named Skill folders,
licenses and a hash manifest. Generated archives are not editable sources.

An existing conflicting installation requires a reviewed local adoption baseline;
the installer will not silently replace it. Subsequent updates detect edits using
the prior installation receipt and preserve unknown files and config/local.json.
See the maintenance guide for backups, restoration and per-component failures.

## Dependencies and boundaries

Skill installation does not install Python packages, configure services, register
MCP servers, access a library, or grant remote upload/download authorization.
Sci-Plot needs its declared Python libraries. Sciverse and Zotero depend on
separately configured services/connectors. Paper Fetch, MinerU and other companion
Skills remain external dependencies; none are rebranded as original code here.

The optional MinerU adapter and experimental acquisition wrapper accept local
runtime settings, documented within their references. Missing prerequisites remain
explicit limitations. Acquisition currently uses Windows and PowerShell 7.

.paper-collab.yaml remains the existing local output preference for deep reading.
Personal Mapper profiles and historical studies are not bundled. Existing local
profiles remain user-controlled, read-only intake inputs, never scientific evidence.

## Validate

    python scripts/validate.py --plot-python <existing-sci-plot-python>

The checks are offline and use synthetic data. Host skill-creator validation is
included when available. Historical Mapper regression requires the explicit
MAPPER_LEGACY_WORKSPACE environment variable; without it the history-specific checks are reported
as skipped. No account credential is needed for the public synthetic regressions.

## License

MIT; existing notices are retained. See LICENSE, per-Skill licenses, and
[dependency attribution](docs/sources.md). Research data, downloaded papers,
credentials, private profiles and external runtimes are outside this repository.
