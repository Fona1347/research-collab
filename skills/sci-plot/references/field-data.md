# Tables and exported fields

CSV/TSV/JSON/XLSX/NPY/NPZ keep the existing figure-spec interface. TXT needs an
explicit reader, for example:

```json
{"path":"instrument.txt","format":"txt",
 "reader":{"delimiter":"\\s+","comment":"%","header":null,
           "names":["x_nm","z_nm","Px","Pz"]}}
```

Only delimited tables accept delimiter/comment/encoding. XLSX accepts sheet_name,
header, names and skiprows. Select real sheets/columns; do not infer a physical unit
from a filename. Normalized coordinates and dimensionless time need explicit labels.

## Rectangular scalar/vector fields

```python
from sci_plot import capture_inputs, export_and_audit
from sci_plot.fields import load_npz_field, plot_field

before = capture_inputs([source])
field = load_npz_field(
    source, x="x_m", y="z_m", fields={"u":"P1", "v":"P2"},
    time_key="tau", time_index=15, time_axis=0,
    coordinate_scale=1e9, coordinate_decimals=10,
    duplicate="identical", units={"x":"nm", "y":"nm", "u":"P/P0", "v":"P/P0"},
)
mappable, settings = plot_field(ax, field, components=("u","v"),
                                color="direction", arrows="direction", stride=12)
fig.colorbar(mappable, ax=ax, label="Angle / pi")
result = export_and_audit(fig, output, project_root=project, inputs=[source],
                          input_fingerprints=before, script_path=__file__,
                          provenance={"field":settings})
```

The names, index, coordinate scaling/rounding and polarization normalization above
are an explicit example, not universal COMSOL defaults. `tau` may be a time vector
or a time-by-node array that is constant across each spatial row. A parameter scan
or a higher-dimensional array needs an explicit project adapter and selection.
Static arrays use shape `(N,)`; time arrays use `(T,N)` or `(N,T)`. For separate
rectangular axis vectors, construct `meshgrid` and flatten all arrays consistently.

`load_table_field` handles long-form instrument/simulation tables using the same
reader options. `from_samples` checks coordinates, duplicates and complete grids.
It rejects conflicting duplicate values; `duplicate="identical"` only removes
points whose component values agree exactly. Missing cells require explicit opt-in
via `from_samples(..., allow_incomplete=True)` and remain NaN, without interpolation.

`resample_components(field, new_x, new_y)` performs optional Q1/bilinear component
interpolation on a complete rectangular grid. It refuses extrapolation and missing
cells. Compute angle after resampling components; do not interpolate a wrapped
angle image. No smoothing is applied automatically.

Direction color uses atan2(v,u)/pi with a cyclic colormap. Zero vectors have no
defined direction and are masked; an additional threshold must be explicitly
chosen and is recorded. Magnitude is shown separately. Direction arrows have
equal length; magnitude arrows preserve relative magnitudes but use automatic
display scaling. Use a separately calibrated quiver key for absolute vector units.
Spatial aspect is equal and comparable panels should declare common limits.

Nonrectangular/unstructured meshes require a domain-aware triangulation or other
adapter. Do not fill geometry holes or reshape a finite-element mesh into a
rectangle. Native MPH loading, exports from live models and solving are outside
this exported-data helper.
