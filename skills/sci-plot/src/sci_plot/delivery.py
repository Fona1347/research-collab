"""One delivery boundary for spec figures and arbitrary Matplotlib figures."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile
from datetime import datetime, timezone

from .backends import Backend
from .errors import SafetyError
from .export import choose_output_paths, export_figure
from .qa import audit_figure, audit_outputs
from .runlog import version_report
from .safety import file_fingerprint, require_distinct_from_inputs, require_output_authorization, verify_fingerprints


def capture_inputs(paths):
    """Call BEFORE reading data; pass this snapshot to export_and_audit."""
    return {Path(p).resolve(): file_fingerprint(Path(p).resolve()) for p in paths}


def _reference_path(path, root):
    path = Path(path).resolve()
    try:
        return os.path.relpath(path, root)
    except ValueError:
        # Windows cannot express relative references across drives or shares.
        return str(path)


def _record(path, root):
    path = Path(path).resolve()
    return {"path": _reference_path(path, root), **file_fingerprint(path)}


def _runtime_record():
    package = Path(__file__).parent
    files = {p.relative_to(package).as_posix(): file_fingerprint(p)["sha256"]
             for p in sorted(package.rglob("*")) if p.is_file() and p.suffix in {".py", ".toml"}}
    return {"python": __import__("sys").version.split()[0], "package_files": files,
            "package_tree_sha256": hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()}


def _json_default(value):
    from cycler import Cycler
    import numpy as np
    if isinstance(value, Cycler):
        return {"cycler": list(value)}
    if isinstance(value, (np.ndarray, np.generic)):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported provenance/configuration type: {type(value).__name__}")


def _publish(staged, finals, overwrite):
    """Publish a complete checked bundle, restoring previous files on failure."""
    reserved, committed, backups = [], [], {}
    try:
        for source, final in zip(staged, finals, strict=True):
            if overwrite and final.exists():
                backup = source.with_name(source.name + ".previous")
                shutil.copy2(final, backup)
                backups[final] = backup
            elif not overwrite:
                with final.open("xb"):
                    pass
                reserved.append(final)
        for source, final in zip(staged, finals, strict=True):
            os.replace(source, final)
            committed.append(final)
    except Exception:
        for final in reversed(committed):
            if final in backups:
                os.replace(backups.pop(final), final)
            else:
                final.unlink(missing_ok=True)
        for final in reserved:
            if final not in committed:
                final.unlink(missing_ok=True)
        raise


def export_and_audit(
    figure, output_base, *, project_root, inputs=(), input_fingerprints=None,
    spec_path=None, script_path=None, provenance=None, effective_config=None,
    formats=("png", "pdf", "svg"), dpi=450, backend=None, rc_params=None,
    theme="custom", conflict="timestamp", overwrite=False, allow_external=False,
):
    """Export without restyling; write hashes, parameters, QA and review status.

    Formats and physical size describe this figure, including EasyPlot/3D figures.
    Source data are referenced, never copied into a shared directory. Supplying
    input_fingerprints protects the full read/render boundary; otherwise only the
    export boundary can be verified. A visual review remains explicitly pending.
    """
    import matplotlib as mpl

    root = Path(project_root).resolve()
    base = Path(output_base)
    base = (root / base).resolve() if not base.is_absolute() else base.resolve()
    formats = list(dict.fromkeys(formats))
    if not formats or any(f not in {"png", "pdf", "svg", "tiff"} for f in formats):
        raise SafetyError("Choose one or more of png, pdf, svg, tiff")
    if isinstance(dpi, bool) or not isinstance(dpi, int) or dpi <= 0:
        raise SafetyError("dpi must be a positive integer")
    require_output_authorization(base, allowed_root=root, allow_external=allow_external)
    paths, renamed = choose_output_paths(base, formats, conflict=conflict, overwrite=overwrite)
    # Sidecars participate in the same no-overwrite decision as the figures.
    manifest = paths[0].with_suffix(".manifest.json")
    while manifest.exists() and not overwrite:
        if conflict == "error":
            raise SafetyError(f"Output already exists: {manifest}")
        base = paths[0].with_suffix("").with_name(paths[0].stem + "_next")
        paths, _ = choose_output_paths(base, formats, conflict=conflict, overwrite=False)
        manifest, renamed = paths[0].with_suffix(".manifest.json"), True
    inputs = [Path(p).resolve() for p in inputs]
    fingerprints = input_fingerprints if input_fingerprints is not None else capture_inputs(inputs)
    fingerprints = {Path(p).resolve(): v for p, v in fingerprints.items()}
    if set(inputs) != set(fingerprints):
        raise SafetyError("Input snapshot must cover exactly the declared input files")
    sources = [Path(p).resolve() for p in (spec_path, script_path) if p is not None]
    project_config = root / "sci-plot.toml"
    if project_config.is_file():
        sources.append(project_config)
    source_snapshot = capture_inputs(sources)
    require_distinct_from_inputs([*paths, manifest], [*inputs, *sources])
    verify_fingerprints(fingerprints)
    visual = audit_figure(figure)
    params = dict(rc_params or {})
    # A style's global tight crop must not silently change the declared canvas.
    params.update({"pdf.fonttype": 42, "svg.fonttype": "none", "savefig.bbox": None})
    backend = backend or Backend("matplotlib", mpl.__version__, mpl)
    size = tuple(float(x) * 25.4 for x in figure.get_size_inches())
    manifest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".sci-plot-", dir=manifest.parent) as tmp:
        stage = Path(tmp)
        staged = [stage / p.name for p in paths]
        export_warnings = export_figure(figure, staged, formats, dpi=dpi, backend=backend,
                                       rc_params=params, theme=theme, overwrite=False)
        qa = audit_outputs(staged, formats, expected_dpi=dpi, expected_size_mm=size)
        verify_fingerprints(fingerprints)
        verify_fingerprints(source_snapshot)
        for check, final in zip(qa["checks"], paths, strict=True):
            check["path"] = os.path.relpath(final, manifest.parent)
        output_records = [{**_record(s, stage), "path": p.name}
                          for s, p in zip(staged, paths, strict=True)]
        record = {
            "schema_version": 1, "created_utc": datetime.now(timezone.utc).isoformat(),
            "project_root": _reference_path(root, manifest.parent),
            "inputs": [_record(p, manifest.parent) for p in inputs],
            "sources": [_record(p, manifest.parent) for p in sources],
            "outputs": output_records, "versions": version_report(),
            "runtime": _runtime_record(),
            "render": {"backend": backend.name, "backend_version": backend.version,
                       "formats": formats, "dpi": dpi, "size_mm": list(size), "theme": theme,
                       "effective_config": effective_config or {}, "export_rcparams": params},
            "provenance": provenance or {}, "qa": qa, "figure_checks": visual,
            "input_unchanged": True,
            "integrity_boundary": "read-render-export" if input_fingerprints is not None else "export-only",
            "visual_review": {"status": "pending", "instruction": "Inspect the actual exports at final size; record a separate hash-bound review."},
            "warnings": [*export_warnings, *qa["warnings"], *visual["warnings"]],
        }
        if input_fingerprints is None and inputs:
            record["warnings"].append("Input integrity starts at export; capture_inputs before loading for full coverage.")
        draft = stage / manifest.name
        draft.write_text(json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False,
                                   default=_json_default) + "\n", encoding="utf-8")
        _publish([*staged, draft], [*paths, manifest], overwrite)
    return {"outputs": paths, "manifest": manifest, "qa": qa, "warnings": record["warnings"],
            "conflict_renamed": renamed}


def verify_bundle(manifest_path):
    manifest_path = Path(manifest_path).resolve()
    record = json.loads(manifest_path.read_text(encoding="utf-8"))
    if record.get("schema_version") != 1:
        raise SafetyError("Unsupported delivery manifest")
    checks = []
    for group in ("inputs", "sources", "outputs"):
        for item in record[group]:
            path = (manifest_path.parent / item["path"]).resolve()
            ok = path.is_file() and file_fingerprint(path)["sha256"] == item["sha256"]
            checks.append({"group": group, "path": item["path"], "matches": ok})
    return {"valid": all(c["matches"] for c in checks), "checks": checks}


def record_review(manifest_path, *, status, notes):
    path = Path(manifest_path).resolve()
    if status not in {"passed", "needs_revision"} or not notes.strip():
        raise SafetyError("Review needs a status and concrete inspection notes")
    verified = verify_bundle(path)
    if not verified["valid"]:
        raise SafetyError("Bundle changed; inspect and regenerate before recording a review")
    target = path.with_name(path.name.replace(".manifest.json", ".review.json"))
    record = {"status": status, "notes": notes, "manifest_sha256": file_fingerprint(path)["sha256"],
              "reviewed_utc": datetime.now(timezone.utc).isoformat(),
              "scope": "visual inspection; not a validation of scientific conclusions"}
    with target.open("x", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, indent=2)
    return target
