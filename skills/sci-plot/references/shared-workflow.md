# Shared scientific plotting workflow

Keep research intent, data meaning and the figure together: inspect read-only data,
retain supplied analysis, choose geometry, render, check numbers/files, inspect the
actual picture, revise if needed and deliver the reproducible bundle. Simple plots
need only relevant stages and records. No external model, gallery download, MCP
server or full EDA is required for a local data plot.

## Delivery and replay

The CLI and public `export_and_audit` API use the same delivery path. Each bundle
contains selected figure formats and a manifest recording input/source paths
with SHA-256, software versions, effective configuration or custom parameters,
output hashes, dimensions/DPI, font evidence and warnings. Keep scripts/specs and
their data references with the project. The shared installation contains only code,
public resources and synthetic demonstrations. References are relative where
possible; Windows paths on another drive or share remain absolute.

`verify-bundle` detects changed data, scripts/specs or outputs. Reproduce a native
spec with the same render command; rerun a custom script explicitly. Verification
does not execute a script from a manifest. For external input paths, retain the
declared relative directory relationship or absolute location, or update the source mapping and generate
a new bundle. Environment versions are recorded; identical pixels across different
OS/font stacks are not guaranteed.

`project_style` preserves established configuration. A custom figure may instead
use EasyPlot or its own Matplotlib styling. `export_and_audit` checks the actual
figure size, retains editable SVG text and embeds TrueType fonts in PDF where
supported. PNG/SVG/PDF and RGBA TIFF remain available. Existing outputs are preserved
by timestamped names; explicit overwrite is transactional across images/manifest.

## Verification boundaries

- Common figure specs validate column mappings, missing/nonfinite values and
  supported geometry. For custom code, verify the relevant plotted arrays against
  the source; file integrity cannot prove a scientific mapping is correct.
- Raster size/DPI and SVG dimensions/text are checked locally. Poppler `pdfinfo`
  and `pdffonts` check PDF dimensions and embedded-font evidence; absent tools are
  reported as unchecked, never as successful checks.
- Canvas/font warnings are advisory. There is no automatic claim that labels never
  overlap. View PNG and rendered PDF previews at the intended physical size.
- After actual visual review, `record-review` saves notes and the manifest hash in
  a separate non-overwriting review record. A manifest always starts as pending.
  Regenerated figures require a fresh review. Scientific conclusions remain the
  researcher's responsibility.

## Setup and regression

Run `scripts/check_environment.py --require --require-pdf` and `doctor` using the
selected existing interpreter. Core Python dependencies are declared in
`pyproject.toml`; Poppler is an optional system tool for complete PDF checking and
previews. Request approval before installing missing dependencies, with exact
source/version, command and environment. Never silently upgrade a working runtime.

`scripts/demo_workflow.py --output-root NEW_DIRECTORY` creates clearly labelled
synthetic table, distribution, classification and vector-field figures. Optional
`--easyplot EXISTING_SKILL_DIRECTORY` checks integration with that installed source.
Optional `--comsol EXISTING_FIELDS_NPZ` verifies the documented COMSOL Eval layout
read-only; it does not load or solve an MPH model. See `field-data.md` for its
explicit keys/normalization and adapt these before using a different export.

Use a fresh directory for each run, inspect all representative PNGs, render PDF
previews with existing `pdftoppm`, then record reviews. Retain only synthetic data
in distributable examples. Host paths, validation reports and real research figures
belong in the project's local output area.

For a shared deployment, publish a validated fixed source snapshot with the
collection's guarded installer. Keep its hashes and backup/restore receipt. Test
restore in an isolated installation before updating live project links. Junctions
share the installed code on this computer; they do not synchronize other computers.
