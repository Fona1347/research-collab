"""Explicit adapters for exported rectangular fields, independent of solvers."""
from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field
from pathlib import Path
import numpy as np

from .errors import DataError


@dataclass
class Field2D:
    x: np.ndarray
    y: np.ndarray
    values: dict[str, np.ndarray]
    metadata: dict = dataclass_field(default_factory=dict)


def from_samples(x, y, values, *, units=None, duplicate="error", allow_incomplete=False, metadata=None):
    """Build a rectangular grid from unordered point samples, without smoothing.

    Duplicate points are rejected unless duplicate='identical' is explicitly set
    and all their values agree exactly. Missing grid cells need explicit opt-in.
    Non-rectangular meshes require a separate triangulation/domain adapter.
    """
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    arrays = {str(k): np.asarray(v, dtype=float) for k, v in values.items()}
    if x.ndim != 1 or y.shape != x.shape or not arrays or any(v.shape != x.shape for v in arrays.values()):
        raise DataError("Coordinates and fields must be equal-length one-dimensional arrays")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise DataError("Field coordinates must be finite")
    if any(not np.isfinite(v).all() for v in arrays.values()):
        raise DataError("Field samples contain NaN/Inf; apply and document a domain/missing-data mask first")
    if duplicate not in {"error", "identical"}:
        raise DataError("duplicate must be error or identical")
    xs, xi = np.unique(x, return_inverse=True)
    ys, yi = np.unique(y, return_inverse=True)
    if min(len(xs), len(ys)) < 2:
        raise DataError("A 2D field needs at least two distinct coordinates on each axis")
    index = yi * len(xs) + xi
    unique, first, inverse, counts = np.unique(index, return_index=True, return_inverse=True, return_counts=True)
    if np.any(counts > 1):
        if duplicate == "error":
            raise DataError("Duplicate coordinates: select time/parameter/domain first, or explicitly allow identical duplicates")
        if any(not np.array_equal(a, a[first][inverse]) for a in arrays.values()):
            raise DataError("Duplicate coordinates contain conflicting values")
    cells = len(xs) * len(ys)
    if cells != len(unique) and not allow_incomplete:
        raise DataError("Incomplete rectangular grid; do not infer cells across geometry holes")
    # Avoid allocating an accidental Cartesian product of an unstructured mesh.
    if cells > max(4 * len(unique), 1_000_000):
        raise DataError("Coordinates appear unstructured; use a mesh/domain-aware adapter")
    grids = {}
    for name, data in arrays.items():
        grid = np.full(cells, np.nan)
        grid[unique] = data[first]
        grids[name] = grid.reshape(len(ys), len(xs))
    info = dict(metadata or {})
    info.update(units=dict(units or {}), grid_shape=[len(ys), len(xs)],
                duplicate_policy=duplicate, duplicates_removed=int(len(x)-len(unique)),
                missing_cells=int(cells-len(unique)), interpolation="none", smoothing="none")
    return Field2D(xs, ys, grids, info)


def load_npz_field(path, *, x, y, fields, time_key=None, time_index=None, time_axis=0,
                   coordinate_scale=1.0, coordinate_decimals=None, units=None,
                   duplicate="error", metadata=None):
    """Read named COMSOL/other exported arrays. Time selection is explicit.

    Static coordinates may have shape (N,); each selected field must resolve to
    (N,). A time series must have shape (T,N) or (N,T) and declare time_axis.
    Structured (ny,nx) data should be flattened explicitly in a project adapter.
    """
    path = Path(path).resolve()
    if not np.isfinite(coordinate_scale) or coordinate_scale <= 0:
        raise DataError("coordinate_scale must be positive and finite")
    with np.load(path, allow_pickle=False) as data:
        requested = [x, y, *fields.values(), *([time_key] if time_key else [])]
        missing = set(requested) - set(data.files)
        if missing:
            raise DataError(f"Missing NPZ keys: {sorted(missing)}")
        time = None
        if time_key is not None:
            times = np.asarray(data[time_key])
            if times.ndim == 2 and time_axis in (0, 1):
                # COMSOL Eval exports can repeat each time over all spatial nodes.
                axis = 1 - time_axis
                collapsed = np.take(times, 0, axis=axis)
                if not np.array_equal(times, np.broadcast_to(np.expand_dims(collapsed, axis), times.shape)):
                    raise DataError("Time varies across nodes; select a consistent solution first")
                times = collapsed
            if times.ndim != 1 or time_index is None or isinstance(time_index, bool) or not 0 <= time_index < len(times):
                raise DataError("Provide a valid time_index for the one-dimensional time array")
            time = float(times[time_index])
            if not np.isfinite(time):
                raise DataError("Selected time is not finite")
        elif time_index is not None:
            raise DataError("time_index requires time_key")
        def select(key):
            array = np.asarray(data[key], dtype=float)
            if array.ndim == 2 and time_key is not None:
                if time_axis not in (0, 1) or array.shape[time_axis] != len(times):
                    raise DataError(f"Time axis does not match {key}")
                array = np.take(array, time_index, axis=time_axis)
            if array.ndim != 1:
                raise DataError(f"{key}: select time/parameters and flatten the spatial samples explicitly")
            return array
        xx, yy = select(x)*coordinate_scale, select(y)*coordinate_scale
        if coordinate_decimals is not None:
            if isinstance(coordinate_decimals, bool) or not isinstance(coordinate_decimals, int):
                raise DataError("coordinate_decimals must be an explicit integer")
            xx, yy = np.round(xx, coordinate_decimals), np.round(yy, coordinate_decimals)
        info = dict(metadata or {})
        info.update(source_format="npz", keys={"x": x, "y": y, "fields": fields},
                    time_key=time_key, time_index=time_index, time_value=time,
                    time_axis=time_axis, coordinate_scale=coordinate_scale,
                    coordinate_decimals=coordinate_decimals)
        return from_samples(xx, yy, {name: select(key) for name, key in fields.items()},
                            units=units, duplicate=duplicate, metadata=info)


def load_table_field(path, *, x, y, fields, reader=None, units=None, duplicate="error"):
    from .data import load_table
    path = Path(path).resolve()
    table, _, fmt = load_table({"path": str(path), "reader": reader or {}}, path)
    required = {x, y, *fields.values()}
    if not required <= set(table.columns):
        raise DataError(f"Missing field columns: {sorted(required-set(table.columns))}")
    return from_samples(table[x], table[y], {name: table[key] for name, key in fields.items()},
                        units=units, duplicate=duplicate,
                        metadata={"source_format": fmt, "mapping": {"x": x, "y": y, "fields": fields}})


def resample_components(field, x, y):
    """Explicit Q1/bilinear resampling of components, never of wrapped angles."""
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    if any(a.ndim != 1 or len(a) < 2 or not np.isfinite(a).all() or not np.all(np.diff(a)>0) for a in (x, y)):
        raise DataError("Target coordinates must be finite, increasing one-dimensional arrays")
    if x[0] < field.x[0] or x[-1] > field.x[-1] or y[0] < field.y[0] or y[-1] > field.y[-1]:
        raise DataError("Extrapolation outside the source grid is forbidden")
    grids = {}
    for name, z in field.values.items():
        if not np.isfinite(z).all():
            raise DataError("Q1 resampling cannot bridge missing grid cells")
        along_x = np.array([np.interp(x, field.x, row) for row in z])
        grids[name] = np.array([np.interp(y, field.y, col) for col in along_x.T]).T
    return Field2D(x, y, grids, {**field.metadata, "interpolation": "Q1 bilinear components",
                                "target_shape": [len(y), len(x)]})


def plot_field(ax, field, *, scalar=None, components=None, color="magnitude", arrows="direction",
               stride=8, zero_threshold=0.0, limits=None, cmap=None):
    """Return a mappable and an explicit scientific plotting record."""
    if not np.isfinite(zero_threshold) or zero_threshold < 0 or isinstance(stride, bool) or not isinstance(stride, int) or stride < 1:
        raise DataError("Use a nonnegative finite mask threshold and positive integer stride")
    if arrows not in {"none", "direction", "magnitude"}:
        raise DataError("arrows must be none, direction or magnitude")
    if components is not None:
        u, v = (field.values[k] for k in components)
        mag = np.hypot(u, v)
        mask = (~np.isfinite(mag)) | (mag <= zero_threshold)
        if color not in {"direction", "magnitude"}:
            raise DataError("Vector color must be direction or magnitude")
        z = np.ma.masked_where(mask, np.arctan2(v, u)/np.pi) if color == "direction" else mag
        cmap = cmap or ("twilight_shifted" if color == "direction" else "viridis")
        limits = limits or ((-1, 1) if color == "direction" else (0, float(np.nanmax(mag))))
    elif scalar is not None:
        z = field.values[scalar]
        cmap = cmap or "viridis"
        arrows = "none"
    else:
        raise DataError("Specify a scalar field or two vector components")
    kwargs = {"vmin": limits[0], "vmax": limits[1]} if limits is not None else {}
    mesh = ax.pcolormesh(field.x, field.y, z, shading="nearest", cmap=cmap, rasterized=True, **kwargs)
    if components is not None and arrows != "none":
        arrow_options = {}
        if arrows == "direction":
            u = np.divide(u, mag, out=np.zeros_like(u), where=~mask)
            v = np.divide(v, mag, out=np.zeros_like(v), where=~mask)
            length = .7 * min(float(np.min(np.diff(field.x))), float(np.min(np.diff(field.y)))) * stride
            arrow_options = {"scale_units": "xy", "scale": 1/length}
        u, v = np.ma.masked_where(mask, u), np.ma.masked_where(mask, v)
        ix, iy = np.arange(0,len(field.x),stride), np.arange(0,len(field.y),stride)
        if arrows == "direction":
            # Keep complete glyphs inside the displayed cell footprint.
            left, right = field.x[0]-np.diff(field.x)[0]/2, field.x[-1]+np.diff(field.x)[-1]/2
            bottom, top = field.y[0]-np.diff(field.y)[0]/2, field.y[-1]+np.diff(field.y)[-1]/2
            ix = ix[(field.x[ix] >= left+length/2) & (field.x[ix] <= right-length/2)]
            iy = iy[(field.y[iy] >= bottom+length/2) & (field.y[iy] <= top-length/2)]
        xx, yy = np.meshgrid(field.x[ix], field.y[iy])
        if len(ix) and len(iy):
            ax.quiver(xx, yy, u[np.ix_(iy,ix)], v[np.ix_(iy,ix)], angles="xy",
                      color="white", edgecolor="#222222", linewidth=.25, pivot="mid", **arrow_options)
    ax.set_aspect("equal", adjustable="box")
    units = field.metadata.get("units", {})
    ax.set_xlabel("x" + (f" ({units['x']})" if units.get("x") else ""))
    ax.set_ylabel("y" + (f" ({units['y']})" if units.get("y") else ""))
    record = {**field.metadata, "scalar": scalar, "components": components,
              "color": color if components else scalar, "arrow_semantics": arrows,
              "arrow_stride": stride, "direction_mask": f"magnitude <= {zero_threshold}",
              "arrow_scale": "automatic display scale; relative magnitude only" if arrows == "magnitude" else "equal-length direction",
              "direction_arrow_length": length if components is not None and arrows == "direction" else None,
              "arrow_boundary": "direction samples inset to retain complete glyphs; field extent unchanged",
              "color_limits": list(mesh.get_clim()), "colormap": cmap, "aspect": "equal",
              "rasterized": ["field cells"], "angle_unit": "pi radians" if color == "direction" else None}
    return mesh, record
