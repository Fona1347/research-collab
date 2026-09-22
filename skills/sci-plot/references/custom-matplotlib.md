# Custom Matplotlib and 3D scripts

`sci-plot.toml` is not a Matplotlib global configuration file. A custom script must
explicitly enter the Sci Plot project style context:

```python
from pathlib import Path

import matplotlib.pyplot as plt
from sci_plot import project_style

project_root = Path(r"E:\path\to\project")

with project_style(project_root) as style:
    fig = plt.figure()
    ax = fig.add_subplot(projection="3d")
    ax.plot([0, 1], [0, 1], [0, 1], color=style.palette[0])
```

Figures created inside the context inherit the configured SciencePlots layer, theme,
font stack, custom rcParams, palette cycle, physical size, and DPI. The yielded
`AppliedStyle` also exposes the resolved config path, palette, dimensions, DPI, and
requested formats.

The context does not select a rendering backend, save files, prevent overwrite, verify
input fingerprints, or run export QA. Prefer a native figure spec whenever those
guarantees are required.
