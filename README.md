[English](README.md) | [简体中文](README.zh-CN.md)

# Paper Collab Skills

Paper Collab is a small, source-only Agent Skills package for traceable single-paper reading and presentation planning.

Current package version: `V1.2.1`

## Included Skills

- `paper-deep-reading` coordinates PDF-first reading, evidence tracking, validation boundaries, originality and research-generativity judgment, function-first design-choice analysis, reader-facing Chinese reports, deterministic run naming, and canonical main-PDF staging.
- `paper-presentation` converts bounded deep-reading artifacts into a traceable presentation plan, speaker notes, or paper card without rerunning retrieval.

The presentation skill is intentionally paired with the deep-reading skill, so installing both is recommended.

## Repository Layout

```text
skills/
  paper-deep-reading/
    SKILL.md
    agents/openai.yaml
    references/
  paper-presentation/
    SKILL.md
    agents/openai.yaml
```

No runtime service, dependency installer, paper PDF, report output, Zotero data, or machine-specific configuration is bundled.

## Installation

Copy either skill directory, preserving its contents, into the skills directory used by your compatible agent environment. For Codex, install both folders under your Codex skills root:

```text
<codex-skills-dir>/paper-deep-reading
<codex-skills-dir>/paper-presentation
```

You can also ask a skill-aware agent:

```text
Install both Agent Skills from https://github.com/Fona1347/paper-collab-skills,
then validate paper-deep-reading and paper-presentation without running a live paper workflow.
```

Installing a Skill does not grant access to Zotero, local PDFs, network services, external parsers, or output locations. Those permissions remain subject to the user's instructions and workspace rules.

## Output Configuration

An optional workspace-root `.paper-collab.yaml` may provide an absolute default output parent:

```yaml
default_output_parent: 'D:\paper-reports'
```

This file is a local path preference, not a permission grant, and is intentionally ignored by Git. An explicitly supplied run directory always takes precedence.

Automatically generated run names use:

```text
Zotero:
<item-key>-<first-author-full-name>_<year>_<journal-or-publisher>-<short-title>

Other inputs:
<first-author-full-name>-<year>-<journal-or-publisher>-<short-title>
```

When a main PDF is available, the skill stages a copy as `<task_name>.pdf` inside the approved run directory. Zotero source items and attachments remain read-only and are never renamed or modified.

## Quick Start

```text
Use $paper-deep-reading to deeply read <PDF, DOI, title, or Zotero item key>.
Show me the resolved output directory before creating research artifacts.
```

```text
Use $paper-presentation to turn the approved paper-deep-reading artifacts into
a journal-club presentation plan without rerunning retrieval.
```

## Version Compatibility

`V1.2.1` is the package release version. Its canonical report artifacts continue to use `evidence_contract: v1.1`; this is the evidence schema version, not the package version. `paper-presentation` also retains a read-only fallback for legacy V1.0.x artifacts.

## Security and Privacy

Do not commit papers, reports, Zotero exports, local configuration, credentials, caches, or user-specific paths. See [SECURITY.md](SECURITY.md) for private reporting guidance.

## License

MIT. See [LICENSE](LICENSE).
