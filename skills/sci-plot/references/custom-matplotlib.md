# Custom Matplotlib and 3D scripts

`sci-plot.toml` is not a Matplotlib global configuration file. A custom script must
explicitly enter the Sci Plot project style context:

```python
from pathlib import Path

import matplotlib.pyplot as plt
from sci_plot import project_style, capture_inputs, export_and_audit

project_root = Path(r"E:\path\to\project")
inputs = [project_root / "data" / "observations.csv"]
before = capture_inputs(inputs)  # before loading data

with project_style(project_root) as style:
    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")
    ax.plot([0, 1], [0, 1], [0, 1], color=style.palette[0])
    # The coordinates above are a synthetic illustration, not measured data.
    result = export_and_audit(
        fig, "outputs/scientific-plotting/custom", project_root=project_root,
        inputs=inputs, input_fingerprints=before, script_path=__file__,
        provenance={"synthetic": True, "transformations": "none"},
        formats=("png", "pdf", "svg"), dpi=450,
    )
```

Figures created inside the context inherit the configured SciencePlots layer, theme,
font stack, custom rcParams, palette cycle, physical size, and DPI. The yielded
`AppliedStyle` also exposes the resolved config path, palette, dimensions, DPI, and
requested formats.

The style context alone does not save or check files. `export_and_audit` provides
those checks for ordinary Matplotlib, 3D and EasyPlot-created figures without
changing their layout or palette. It preserves vector text and uses a guarded
multi-file delivery with a `.manifest.json` sidecar. Record transformations, units,
uncertainty definitions, seeds and rasterized layers in `provenance`.

For existing EasyPlot code, retain its `publication_context()` and layout helpers;
replace the final export call with this common delivery API. Use an explicitly
resolved installed EasyPlot path; do not add it to a global Python path.

Use `capture_inputs` before loading; omitting it can only check integrity during
export and is recorded as `export-only`. Data are never copied into the shared skill.
Call `verify-bundle` for checksum verification and inspect previews separately.
