# Research Collab

**Nine research Skills** for literature discovery, paper reading, research-route decisions, scientific plotting and presentation planning. Use each independently or combine them around a task, with traceable sources, reasoning and outputs.

[简体中文](README.zh-CN.md) · [Maintenance and installation](docs/maintenance.md) · [Sources and dependencies](docs/sources.md)

## Quickstart

You need Git, Python 3.11+ and a host that loads local Skills. The examples use Codex and PowerShell. On macOS/Linux, use the same Python commands with your own absolute target path.

### 1. Install into your research project

Run this where you keep tool source code. Set `$skillsDir` to the absolute `.agents/skills` path inside your research project:

```powershell
git clone https://github.com/Fona1347/research-collab.git
cd research-collab
$skillsDir = "D:/research-project/.agents/skills"

python scripts/skills.py install --skills-root "$skillsDir" --dry-run
```

Review the target and changes, then install and verify:

```powershell
python scripts/skills.py install --skills-root "$skillsDir"
python scripts/skills.py check --skills-root "$skillsDir"
```

This installs all nine Skills, including the experimental acquisition adapter. It does not install Python dependencies, register MCP servers or start research. To try one Skill, add `--skill paper-deep-reading` to the install and check commands. If an existing installation conflicts, follow the [adoption guide](docs/maintenance.md#adopt-an-existing-installation) and preserve local changes.

### 2. Read your first paper

Open that research project in Codex, attach or paste **readable full text you already have**, and send:

```text
$paper-deep-reading Create a reader report in English from the full text I provided.
task=full-report, validation=fully-local, presentation_handoff=no.
Output parent: D:/research-project/reports.
Explain the research question, methods, evidence and limitations.
Identify what the supplied material does not cover.
```

Use `fully-local` to start with local reading; request `validation=standard` when you need external evidence checks. PDF input needs the parser tools described below. When a full report is complete, start with `view-report.md` in its new run directory.

Codex loads project Skills from `.agents/skills`. In the CLI/IDE, use `$skill-name`; interfaces with a Skill selector can select the corresponding entry. If an installation does not appear, restart Codex and check the project you opened. See the [official loading and invocation guide](https://learn.chatgpt.com/docs/build-skills).

## Choose a Skill for the task

| Your task | Skill | Main output |
|---|---|---|
| Find papers, expand queries and organize sources | [research-lookup-enhanced](skills/research-lookup-enhanced/SKILL.md) | Traceable candidates and evidence packets |
| Retrieve passages or structured reading from Sciverse | [sciverse-research](skills/sciverse-research/SKILL.md) | Evidence with provenance and completeness status |
| Understand one paper and its evidence boundaries | [paper-deep-reading](skills/paper-deep-reading/SKILL.md) | Reader report and authoritative working artifacts |
| Create a Markdown note from a Zotero item | [zotero-literature-note](skills/zotero-literature-note/SKILL.md) | Traceable notes and figures |
| Compare research directions, examine a chosen interface or audit a plan | [research-opportunity-mapper](skills/research-opportunity-mapper/SKILL.md) | Route decisions, validation plans and decision records |
| Explore research opportunities quickly | [research-opportunity-mapper-quick](skills/research-opportunity-mapper-quick/SKILL.md) | Lightweight opportunity map |
| Plot numeric research data | [sci-plot](skills/sci-plot/SKILL.md) | SVG/PDF/PNG/TIFF and export checks |
| Turn completed reading into a presentation | [paper-presentation](skills/paper-presentation/SKILL.md) | Talk structure, speaker notes and asset plan |
| Orchestrate authorized full-text acquisition | [literature-fulltext-acquisition](skills/literature-fulltext-acquisition/SKILL.md) | Acquisition records and explicit failure states; **experimental** |

Ordinary discovery does not automatically start Mapper. For a formal route decision, the full Mapper recommends configuration from your decision needs; include any chosen interface, available resources and excluded directions. Presentation planning consumes existing reading artifacts; producing a final PPTX requires a separately selected presentation tool.

## Recommended setup

Configure the parts that support your own tasks.

### Set an output location and record research constraints

Create `.paper-collab.yaml` at the **research workspace root**, replacing the example with your own absolute path:

```yaml
default_output_parent: 'D:/research-project/reports'
```

This sets the default parent for deep-reading reports; each task gets its own child directory. A path explicitly supplied in the current request takes precedence. The setting is a path preference, not upload/download permission, and does not bypass workspace confirmation rules.

A short project guide or `AGENTS.md` can record your preferred language, research object, available equipment/compute, time budget, excluded directions and material-sharing constraints. Keep personal paths and unpublished research context local. This context reduces repeated questions without a fixed intake questionnaire.

### Prepare a usable PDF reading route

The local route typically needs `pdfinfo`, `pdftoppm` and `pypdf`; `PyMuPDF` can support parsing and visual checks. An existing, authorized MinerU route is another option. Formulas, tables and layout still need checking against the source.

Run the read-only preflight in your chosen Python environment, using the installation variable above:

```powershell
python "$skillsDir/paper-deep-reading/scripts/check_dependencies.py" --mode fully-local --input-kind pdf
```

It reports missing components without installing them. See the [deep-reading dependency guide](skills/paper-deep-reading/references/external-dependencies.md).

### Add external capabilities when needed

| When useful | Configuration | Benefit |
|---|---|---|
| Frequent discovery and source cross-checking | Set `OPENALEX_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY`; optionally `CROSSREF_MAILTO` and `UNPAYWALL_EMAIL` for lookup | Use the corresponding providers for discovery, metadata and open-access locations |
| Sciverse passages or Paper Schema | Connect Sciverse MCP/API separately, configure `SCIVERSE_API_TOKEN`, and inspect available tools and account scope | Context and structured information from supported content |
| A Zotero-based library workflow | Configure Zotero Desktop and the host's Zotero plugin/connector; identify the target item | Reuse item metadata, attachments, notes and verified parser caches |
| MinerU parsing | Set `mineru_python` and `mineru_wrapper` in the installed lookup Skill's `config/local.json`; keep `MINERU_API_KEY` in the environment | Bind an existing parser without a machine-specific development path |
| Experimental full-text acquisition | Set `tools_root` and `protected_root` in that installed Skill's `config/local.json`; requires existing tools and Windows / PowerShell 7 | Use the bundled wrapper and existing output protections |

In this lookup adapter, OpenAlex/Semantic Scholar are explicitly skipped when their keys are missing. Installing Skills does not install or enable Sciverse, Zotero, MinerU or acquisition services.

Start runtime settings from each component's `config/local.example.json`; preserve any existing local configuration. Put real credentials in the host's supported secret store or process environment, never in README files, Skills, command arguments or public logs. Remote MinerU parsing still requires the applicable source and upload authorization.

Details: [providers](skills/research-lookup-enhanced/references/provider-matrix.md) · [parsers](skills/research-lookup-enhanced/references/document-parsers.md) · [Sciverse](skills/sciverse-research/references/mcp-upgrade-notes.md) · [acquisition](skills/literature-fulltext-acquisition/references/tools.md).

### Keep plotting styles consistent

Select a Python environment with the [Sci-Plot dependencies](skills/sci-plot/pyproject.toml), then check it:

```powershell
python "$skillsDir/sci-plot/scripts/check_environment.py" --require
```

For repeated plotting, save `sci-plot.toml` at the **plotting project root**:

```toml
[project]
name = "my-research"
output_dir = "figures"

[render]
theme = "paper"
scienceplots = true
formats = ["svg", "png"]
dpi = 300
```

Supply the project root when rendering; CLI and figure-spec settings take precedence. For Chinese labels, set `render.chinese_font` to a font actually installed in that environment. Use the installed Skill's `scripts/run_sci_plot.py` launcher to run its bundled source. See the [Sci-Plot guide](skills/sci-plot/README.md) for examples.

## Updates, packages and maintenance

Run these from this repository root. `$skillsDir` still points to your research project's installation directory.

```powershell
python scripts/skills.py validate
python scripts/skills.py package --output dist/research-collab.zip
python scripts/skills.py package --skill paper-deep-reading --output dist/paper-deep-reading.zip
python scripts/skills.py install --skills-root "$skillsDir" --dry-run
python scripts/skills.py check --skills-root "$skillsDir"
```

For updates, pull the desired revision into a clean maintenance clone, preview changes and install. The tool backs up changes, records the source commit and hashes, and blocks the affected component on local drift. Generated packages are distribution artifacts; the only editable Skill sources are under `skills/<skill-name>`. See the [maintenance guide](docs/maintenance.md) for recovery commands.

`scripts/validate.py` runs component regressions; use `--component` to select scope and `--plot-python` for an existing plotting environment. Actual Mapper history requires an explicit `MAPPER_LEGACY_WORKSPACE`; otherwise tests use public synthetic material and report history-specific skips. The tests do not conduct formal research or real paper downloads.

## Status and license

The collection consolidation is **Unreleased**. The previous Paper Collab package release is V1.2.1; Skill and evidence-schema versions remain independent. Full-text acquisition remains experimental. Offline checks do not establish live-service or real-download success.

[MIT](LICENSE), with component copyright notices and [third-party attribution](docs/sources.md) retained. Papers, real research reports, personal profiles, credentials and external runtimes are outside public distributions.
