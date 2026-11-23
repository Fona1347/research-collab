# Routing and interaction

## Quantitative versus conceptual

Use the deterministic Sci Plot path when exact values determine marks, axes,
uncertainty, labels, or layout. This includes line, bar, scatter, heatmap, explicit
error-bar, and multi-panel result figures.

Route conceptual architecture, mechanisms, workflows, and graphical abstracts to an
illustration or schematic skill. For mixed figures, render every quantitative panel
locally first and keep any generated illustration visually and procedurally separate.

## Dependency model

Keep three different concepts separate:

1. Python runtime dependencies belong in pyproject.toml.
2. Optional Skills are composed by the agent at request time from the current Skill
   catalog.
3. Reference material may inform Sci Plot's own lightweight rules without invoking or
   copying another Skill.

Do not add Skill names to pyproject.toml. Do not add a `[handoffs]` table and imply it
installs, discovers, or invokes another Skill: Sci Plot has no handoff executor. A
future orchestrator may consume such configuration only after it has an explicit
capability-discovery and invocation contract.

Use canonical Skill names from each SKILL.md frontmatter. The local folder prefixes
are not part of those names: for example, directory `sa.statistical-analysis` exposes
`statistical-analysis`, and directory `ns.nature-figure` exposes `nature-figure`.
Filesystem presence alone is insufficient; the Skill must also be available in the
current session catalog.

## Optional workflow composition

Basic data validation, deterministic plotting, export safety, and lightweight QA
always remain inside Sci Plot. Compose another Skill only when the user's requested
work crosses one of the following boundaries.

| Canonical Skill | Compose when | Result Sci Plot should consume | Default |
|---|---|---|---|
| `exploratory-data-analysis` | The user asks for comprehensive exploration, data-quality diagnosis, anomaly review, or advice on which figure to make | Data profile, limitations, and a recommended mapping/spec; write a report only to a user-approved location | Off |
| `statistical-analysis` | Collected data require a test, model, regression, effect size, confidence/credible interval, multiple-testing correction, or significance annotation | Structured estimates, interval definition, test name, exact/adjusted p-values, effect sizes, sample sizes, and plot-ready derived values | Off |
| `statistical-power` | The primary request is sample size, power, MDE, sensitivity analysis, or a power curve | Assumptions plus a numeric table of n/effect size/power; Sci Plot owns the final visual style and export | Off |
| `experimental-design` | The request concerns pre-collection randomization, blocking, allocation, factorial/DOE, or run order | A design/allocation table and provenance; visualization is optional and downstream | Off |
| `nature-figure` | The user requests a submission-grade, journal-specific, multi-panel, or final manuscript audit | A QA/audit result and explicit corrections; Sci Plot's Python backend is already selected when the workflows are composed | Off |
| `scientific-visualization` | The user explicitly requests this Skill or needs unique material not covered by Sci Plot or `nature-figure` | Advisory material only, subject to Sci Plot's safety and statistical-integrity rules | Off |

The `statistical-analysis` Skill also mentions power calculations. Resolve the overlap
by intent: route a primary sample-size/power/MDE request to `statistical-power`, and
route inference on already collected data to `statistical-analysis`.

Do not automatically use `exploratory-data-analysis` for a known CSV-to-plot mapping;
`sci-plot inspect-data` already checks shape, columns, types, and missing values. The
full EDA workflow can generate a report and load domain-specific libraries, so it
requires an explicit exploratory request and an approved output location.

Do not routinely compose `scientific-visualization`. It overlaps heavily with Sci
Plot and `nature-figure`, and its generic advice that figures should always contain
error bars or significance markers is not universally valid. A figure may display
those elements only when the design and analysis justify them and their meaning is
explicit.

## Composition protocol

When an optional Skill is warranted:

1. Verify its canonical name is present in the active Skill catalog. Never import its
   SKILL.md from Python or install its Python stack during an ordinary render.
2. Run the upstream reasoning step first and preserve its assumptions and provenance.
3. Pass only explicit, plot-ready results into Sci Plot. Prefer in-memory structured
   data; create a derived file only at a user-approved path.
4. Validate the resulting figure spec. Never turn a p-value alone into an invented
   comparison, uncertainty range, or significance geometry.
5. If the optional Skill is unavailable, report that limitation. Continue only when
   the user has supplied sufficient validated results for deterministic plotting.

Basic publication QA is always on. `nature-figure` is not auto-invoked for every
render; use it for explicit submission-grade or journal-specific review. Because Sci
Plot is a Python workflow, a composed `nature-figure` review has an already resolved
Python backend and should not reopen backend selection.

## Minimum information

Resolve these items before a first render:

1. Scientific project root.
2. Output directory.
3. Theme or publication target.
4. General-paper or SciencePlots style.
5. Whether SciencePlots may be used.

When the user chooses to persist a new project configuration, also confirm the project
name. Do not require a project name for a one-off in-memory render.

Do not block a simple task on advanced journal, font, palette, or statistical choices.
Use the general-paper fallback and report that choice.

## Project root

Treat --project-root, the location of an explicitly named project configuration, or a
user-confirmed path as authoritative. Never infer the whole compound workspace as the
project root. A spec-relative data or output path is allowed without inventing a
project root; the spec directory is then only a resolution boundary, not a persisted
project identity.

Running sci-plot init PROJECT_ROOT is explicit consent to create
PROJECT_ROOT/sci-plot.toml. Ordinary validation and rendering never create that file.

Supported built-in themes are paper, nature, science, and cell. They are
publication-inspired profiles, not official publisher specifications. Use theme
custom with a project palette or rcparams for a project-specific theme. Supported
styles are general-paper, minimal, and custom; custom requires rcparams.
