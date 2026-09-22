---
name: sci-plot
description: Create and audit exact, publication-ready scientific plots from CSV, TSV, JSON, XLSX, NPY, or NPZ data with a deterministic Python/Matplotlib workflow, default SciencePlots styling, optional pubfig export, safe SVG/PDF/PNG/TIFF output, project themes, figure specs, explicit error bars, batch formats, and publication QA. Use for requests such as 画一张科研图、科研绘图、论文图表、误差图、用项目主题绘图、自定义 Matplotlib 或 3D 脚本复用项目样式、根据 CSV 生成论文图、把实验数据画成折线图、生成 Nature 风格图、导出 SVG/PDF/PNG/TIFF、根据 figure spec 生成图、检查科研图是否符合出版要求、使用项目配置绘图、批量导出科研图, or any exact numeric line, bar, scatter, heatmap, errorbar, or simple multi-panel figure. Do not use image generation for numeric values, axes, curves, or error geometry.
---

# Sci Plot

Use Sci Plot for exact numeric figures. Keep conceptual diagrams, mechanisms, and
architectures on a separate illustration path; never ask an image model to reproduce
data, axes, uncertainty, or benchmark geometry.

## Core workflow

1. Classify the request as quantitative or conceptual. Read
   [references/routing.md](references/routing.md) when the boundary is unclear.
   Also read it when the request includes comprehensive EDA, inferential statistics,
   power/sample-size work, experimental design, or submission-grade figure review.
   Those are optional Skill compositions, not Python dependencies.
2. Establish the figure's one-sentence conclusion and the role of each panel.
3. Determine an explicit scientific project root. Do not treat a compound workspace
   root as the project root. If no project root can be established, ask for it.
4. Read sci-plot.toml only from that project root. If it is absent, use in-memory
   defaults; create it only after explicit consent or an explicit sci-plot init.
5. Confirm only the missing essentials: output location, theme, and plot style.
   SciencePlots is enabled by default but may be explicitly disabled. Confirm a project
   name only when persisting a new project configuration. Fall back to the general-paper
   style rather than blocking a simple plot.
6. Inspect all source data read-only. Never edit, rename, move, delete, or overwrite
   an input. Perform transformations in memory or write an explicitly named derived
   file.
7. Create or validate a versioned JSON figure spec. Run sci-plot validate SPEC before
   rendering when the input or mappings are new. For `errorbar`, require an explicit
   `yerr` or `ymin`/`ymax` mapping and name the interval in `labels.uncertainty`.
8. Render through sci-plot render SPEC. The CLI uses the Sci Plot schema, not the
   upstream pubfig schema. Read
   [references/pubfig-adapter.md](references/pubfig-adapter.md) before changing the
   backend or adapter.
9. Preserve the default no-overwrite behavior. An external output needs the user's
   confirmation, represented in the CLI by --allow-external-output. Existing outputs
   receive one common timestamp unless the user explicitly passes --overwrite.
10. Run the built-in export QA and report the resolved input, output, theme, actual
    backend, formats, versions, and warnings. For submission-grade review, read
    [references/publication-qa.md](references/publication-qa.md).

For a custom Matplotlib or 3D script that must reuse `sci-plot.toml`, read
[references/custom-matplotlib.md](references/custom-matplotlib.md). Treat that path as
style reuse only; it does not inherit Sci Plot's safe export or QA pipeline.

Never infer a statistical test or add significance stars from raw data during a
render. Consume user-supplied or analysis-derived estimates, intervals, tests, and
adjusted p-values as explicit plotting inputs.

## Runtime preflight

Resolve scripts relative to this SKILL.md, never from an assumed working directory.
Before the first render in an unfamiliar Python environment, run
scripts/check_environment.py --require. The check is read-only. If a required
dependency is absent, report it and obtain authorization before changing an
environment.

When the Skill contains src/sci_plot, use its bundled scripts/run_sci_plot.py
launcher with the selected Python interpreter. This ensures the installed Skill's
own code runs even when that interpreter has an older editable Sci-Plot install.
The launcher only adds the bundled src directory for that process; it installs
nothing. Use an installed sci-plot entry point or python -m sci_plot only after
confirming sci_plot.__file__ belongs to the intended package.

## Commands

    python -m sci_plot init PROJECT_ROOT
    python -m sci_plot inspect-data DATA
    python -m sci_plot validate FIGURE_SPEC [--project-root ROOT]
    python -m sci_plot render FIGURE_SPEC [--project-root ROOT] [--output PATH]
    python -m sci_plot list-templates
    python -m sci_plot source status
    python -m sci_plot source check
    python -m sci_plot source --manifest WRITABLE_SOURCES_TOML check --record
    python -m sci_plot source --manifest WRITABLE_SOURCES_TOML update --source ID --ref REF --approve --tests-passed

The command forms above also work through scripts/run_sci_plot.py. Do not
install packages, upgrade the shared plotting environment, or change the project's
SciencePlots setting during an ordinary render.

## Maintenance boundary

Read [references/source-maintenance.md](references/source-maintenance.md) before
checking or approving an upstream revision. A check is remote read-only and does not
change code, configuration, or environments unless --record is explicitly used. An
update records an already reviewed immutable ref; it does not install a package or
rewrite adapter code. For an installed wheel, first copy the baseline path printed by
source status to a new workspace-owned file, then pass that file with --manifest for
recording or approval. Never overwrite the packaged baseline.
