#!/usr/bin/env python3
"""Reproducible synthetic validation; optional existing EasyPlot and COMSOL data."""
from pathlib import Path
import argparse
import contextlib
import io
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sci_plot import capture_inputs, export_and_audit, project_style, verify_bundle
from sci_plot.cli import main as cli
from sci_plot.fields import load_npz_field, plot_field


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--easyplot", type=Path, help="Existing EasyPlot skill directory")
    parser.add_argument("--comsol", type=Path, help="Existing x_m/z_m/P1/P2/tau NPZ export, read only")
    args = parser.parse_args()
    root = args.output_root.resolve()
    root.mkdir(parents=True, exist_ok=False)
    data = root / "data"
    data.mkdir()
    rng = np.random.default_rng(241015)
    observations = rng.normal([1., 1.45], [.15, .20], size=(30, 2))
    samples = data / "synthetic_observations.csv"
    pd.DataFrame(observations, columns=["Control", "Treatment"]).to_csv(samples, index=False)
    time = np.arange(6, dtype=float)
    trajectory = data / "synthetic_summary.csv"
    pd.DataFrame({"time": time, "response": np.exp(-time/3), "sem": np.full(6, .05)}).to_csv(trajectory, index=False)
    spec = {"schema_version": 1, "kind": "errorbar", "conclusion": "Synthetic validation only",
            "data": {"path": "data/synthetic_summary.csv"},
            "mapping": {"x": "time", "y": "response", "yerr": "sem"},
            "labels": {"x": "Time (s)", "y": "Response (a.u.)", "title": "Synthetic demonstration",
                       "uncertainty": "Illustrative supplied SEM; synthetic"},
            "style": {"width_mm": 120, "height_mm": 85, "backend": "matplotlib"},
            "export": {"path": "figures/table", "formats": ["png", "pdf", "svg"], "dpi": 450}}
    spec_path = root / "table.spec.json"
    spec_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    with contextlib.redirect_stdout(io.StringIO()) as out:
        code = cli(["render", str(spec_path), "--project-root", str(root)])
    if code:
        raise RuntimeError(out.getvalue())
    table_result = json.loads(out.getvalue())
    x, y = np.meshgrid(np.linspace(-2, 2, 65), np.linspace(-1, 1, 33))
    field_data = data / "synthetic_fields.npz"
    np.savez_compressed(field_data, x=x.ravel(), y=y.ravel(),
                        u=-y.ravel(), v=x.ravel())
    before = capture_inputs([samples, field_data])
    field = load_npz_field(field_data, x="x", y="y", fields={"u":"u", "v":"v"},
                           units={"x":"mm", "y":"mm", "u":"a.u.", "v":"a.u."})
    values = pd.read_csv(samples).to_numpy()
    with project_style(root):
        fig, axes = plt.subplots(2, 2, figsize=(180/25.4, 150/25.4), layout="constrained")
        axes[0,0].boxplot(values, tick_labels=["Control", "Treatment"], showfliers=False)
        for i, column in enumerate(values.T):
            axes[0,0].scatter(np.full(len(column), i+1)+rng.uniform(-.12,.12,len(column)), column,
                              s=8, alpha=.7, color=["#0072B2", "#D55E00"][i])
        axes[0,0].set(ylabel="Response (a.u.)", title="a  Raw observations; n=30/group")
        # Synthetic classification results; counts are calculated from labels.
        actual = np.repeat([0,1], 50)
        predicted = actual.copy()
        predicted[[1,4,7,55,60,72,80]] = 1-predicted[[1,4,7,55,60,72,80]]
        confusion = np.zeros((2,2), dtype=int)
        np.add.at(confusion, (actual, predicted), 1)
        image = axes[0,1].imshow(confusion, cmap="Blues", vmin=0, vmax=50)
        for (row,col), count in np.ndenumerate(confusion):
            axes[0,1].text(col,row,str(count),ha="center",va="center",color="white" if count>25 else "black")
        axes[0,1].set(xticks=[0,1],yticks=[0,1],xlabel="Predicted class",ylabel="True class",
                      title="b  Classification counts")
        records = []
        for ax, color, title in zip(axes[1], ["direction","magnitude"], ["c  Vector direction", "d  Vector magnitude"]):
            mesh, record = plot_field(ax, field, components=("u","v"), color=color,
                                      arrows="direction" if color=="direction" else "none", stride=5)
            fig.colorbar(mesh, ax=ax, label="Angle / pi" if color=="direction" else "Magnitude (a.u.)", shrink=.8)
            ax.set_title(title)
            records.append(record)
        fig.suptitle("SYNTHETIC VALIDATION — no experimental conclusions", fontsize=9)
        result = export_and_audit(fig, "figures/multi-panel", project_root=root,
                                 inputs=[samples,field_data], input_fingerprints=before, script_path=__file__,
                                 provenance={"synthetic":True, "seed":241015, "fields":records,
                                             "classification":{"true":actual.tolist(),"predicted":predicted.tolist()}}, dpi=450)
        plt.close(fig)
    manifests = [Path(table_result["manifest"]), result["manifest"]]
    if args.easyplot:
        sys.path.insert(0, str(args.easyplot.resolve()/"scripts"))
        from easyplot_py import publication_context, make_scientific_plate
        before = capture_inputs([trajectory])
        with publication_context():
            fig, axes = plt.subplots(figsize=(120/25.4,80/25.4),layout="constrained")
            table = pd.read_csv(trajectory)
            axes.plot(table.time,table.response, marker="o")
            axes.set(xlabel="Time (s)",ylabel="Response (a.u.)",title="Synthetic EasyPlot compatibility")
            result = export_and_audit(fig,"figures/easyplot",project_root=root,inputs=[trajectory],
                                     input_fingerprints=before,script_path=__file__,
                                     provenance={"synthetic":True,"style_backend":"EasyPlot"},dpi=450)
            manifests.append(result["manifest"])
            plt.close(fig)
    if args.comsol:
        source = args.comsol.resolve()
        before = capture_inputs([source])
        with np.load(source,allow_pickle=False) as archive:
            last = archive["tau"].shape[0]-1
        field = load_npz_field(source,x="x_m",y="z_m",fields={"u":"P1","v":"P2"},
                               time_key="tau",time_index=last,coordinate_scale=1e9,coordinate_decimals=10,
                               duplicate="identical",units={"x":"nm","y":"nm","u":"P/P0","v":"P/P0"})
        with project_style(root):
            fig,axes = plt.subplots(2,1,figsize=(180/25.4,105/25.4),layout="constrained")
            records=[]
            for ax,color in zip(axes,["direction","magnitude"]):
                mesh,record=plot_field(ax,field,components=("u","v"),color=color,stride=12,
                                      arrows="direction" if color=="direction" else "none")
                fig.colorbar(mesh,ax=ax,label="Angle / pi" if color=="direction" else "|P| / P0",shrink=.8)
                ax.set_ylabel("z (nm)")
                records.append(record)
            fig.suptitle(f"Existing COMSOL export; normalized time tau={field.metadata['time_value']:g}",fontsize=9)
            result=export_and_audit(fig,"figures/comsol-existing",project_root=root,inputs=[source],
                                   input_fingerprints=before,script_path=__file__,
                                   provenance={"synthetic":False,"new_solves":0,"fields":records},dpi=450)
            manifests.append(result["manifest"])
            plt.close(fig)
    report={"manifests":[str(p) for p in manifests],
            "hash_verification":[verify_bundle(p) for p in manifests],
            "visual_review":"pending; open PNG and PDF previews before recording review"}
    (root/"validation.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"root":str(root),"bundles":len(manifests),"valid":all(r["valid"] for r in report["hash_verification"])},indent=2))


if __name__ == "__main__":
    main()
