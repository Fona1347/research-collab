from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from sci_plot import capture_inputs, export_and_audit, verify_bundle
from sci_plot.delivery import record_review, _publish
from sci_plot.fields import from_samples, load_npz_field, load_table_field, resample_components, plot_field
from sci_plot.errors import DataError, SafetyError
from sci_plot.qa import audit_figure


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.data = self.root / "data.csv"
        self.data.write_text("x,y\n0,1\n1,2\n", encoding="utf-8")
        self.fig, self.ax = plt.subplots(figsize=(4, 3), layout="constrained")
        self.ax.plot([0, 1], [1, 2])
        self.ax.set(xlabel="Time (s)", ylabel="Response (a.u.)")

    def tearDown(self):
        plt.close(self.fig)
        self.tmp.cleanup()

    def deliver(self, **kwargs):
        return export_and_audit(self.fig, "result", project_root=self.root,
                                inputs=[self.data], formats=["png", "svg"], dpi=100, **kwargs)

    def test_bundle_hashes_and_actual_sizes(self):
        result = self.deliver(input_fingerprints=capture_inputs([self.data]), provenance={"synthetic": True})
        m = json.loads(result["manifest"].read_text(encoding="utf-8"))
        self.assertEqual(m["integrity_boundary"], "read-render-export")
        self.assertEqual(m["visual_review"]["status"], "pending")
        self.assertEqual(m["qa"]["checks"][0]["size_px"], [400, 300])
        self.assertTrue(verify_bundle(result["manifest"])["valid"])
        self.data.write_text("changed", encoding="utf-8")
        self.assertFalse(verify_bundle(result["manifest"])["valid"])
        with self.assertRaises(SafetyError):
            record_review(result["manifest"], status="passed", notes="Must reject stale input")

    def test_inputs_changed_before_export_rejected(self):
        before = capture_inputs([self.data])
        self.data.write_text("changed", encoding="utf-8")
        with self.assertRaises(SafetyError):
            self.deliver(input_fingerprints=before)
        self.assertFalse((self.root/"result.png").exists())

    def test_cross_drive_references_remain_verifiable(self):
        import os
        relative_path = os.path.relpath

        def different_mount(path, start):
            if Path(path).resolve() in {self.data, self.root}:
                raise ValueError("path is on a different mount")
            return relative_path(path, start)

        # Exercise Windows cross-drive behavior on every CI platform.
        with patch("sci_plot.delivery.os.path.relpath", side_effect=different_mount):
            result = self.deliver(input_fingerprints=capture_inputs([self.data]),
                                  script_path=self.data)
        record = json.loads(result["manifest"].read_text(encoding="utf-8"))
        self.assertEqual(record["inputs"][0]["path"], str(self.data))
        self.assertEqual(record["sources"][0]["path"], str(self.data))
        self.assertEqual(record["project_root"], str(self.root))
        self.assertTrue(verify_bundle(result["manifest"])["valid"])

    def test_style_tight_crop_cannot_change_declared_dimensions(self):
        with matplotlib.rc_context({"savefig.bbox": "tight"}):
            result = self.deliver()
        self.assertEqual(result["qa"]["checks"][0]["size_px"], [400,300])

    def test_canvas_audit_ignores_undrawn_ticks_but_flags_real_text(self):
        self.ax.set_xlim(0,1)
        self.ax.set_xticks([-10,0,1,10])
        self.ax.set_xlim(0,1)
        self.assertFalse(audit_figure(self.fig)["outside_canvas"])
        self.fig.text(-.2,.5,"outside label")
        self.assertIn("outside label",audit_figure(self.fig)["outside_canvas"])

    def test_custom_3d_figure_uses_the_same_delivery(self):
        fig = plt.figure(figsize=(4,3), layout="constrained")
        try:
            ax = fig.add_subplot(projection="3d")
            t = np.linspace(0,1,20)
            line, = ax.plot(t,t*t,t**3)
            np.testing.assert_array_equal(line.get_data_3d()[2], t**3)
            result = export_and_audit(fig,"three-d",project_root=self.root,
                                     formats=["png","svg"],dpi=100,provenance={"synthetic":True})
            self.assertTrue(verify_bundle(result["manifest"])["valid"])
        finally:
            plt.close(fig)

    def test_sidecar_conflict_and_overwrite_preserve_bundle(self):
        first = self.deliver()
        old = first["manifest"].read_bytes()
        second = self.deliver()
        self.assertNotEqual(first["manifest"], second["manifest"])
        self.assertEqual(first["manifest"].read_bytes(), old)
        with self.assertRaises(SafetyError):
            self.deliver(conflict="error")
        with patch("sci_plot.delivery.audit_outputs", side_effect=SafetyError("audit failed")):
            with self.assertRaises(SafetyError):
                self.deliver(overwrite=True)
        self.assertEqual(first["manifest"].read_bytes(), old)
        self.assertTrue(verify_bundle(first["manifest"])["valid"])

    def test_output_cannot_alias_input_or_leave_root(self):
        protected = self.root / "protected.png"
        protected.write_bytes(b"original input")
        with self.assertRaises(SafetyError):
            export_and_audit(self.fig, protected, project_root=self.root,
                            inputs=[protected], formats=["png"], overwrite=True)
        with self.assertRaises(SafetyError):
            export_and_audit(self.fig, self.root.parent/"escape", project_root=self.root, formats=["png"])

    def test_transaction_rolls_back_partial_publish(self):
        stages = [self.root/"a.new", self.root/"b.new"]
        finals = [self.root/"a", self.root/"b"]
        for p in stages: p.write_text("new")
        for p in finals: p.write_text("old")
        import os
        actual = os.replace
        def fail_second(source, dest):
            if Path(source) == stages[1]: raise OSError("simulated failure")
            return actual(source, dest)
        with patch("sci_plot.delivery.os.replace", side_effect=fail_second):
            with self.assertRaises(OSError): _publish(stages, finals, True)
        self.assertEqual([p.read_text() for p in finals], ["old", "old"])


class FieldTests(unittest.TestCase):
    def grid(self):
        x, y = np.meshgrid([0., 1., 2.], [0., 1.])
        return x.ravel(), y.ravel()

    def test_q1_preserves_bilinear_function_and_bounds(self):
        x, y = self.grid()
        f = from_samples(x, y, {"u": 2*x+3*y+x*y, "v": x-y})
        target = resample_components(f, np.linspace(0, 2, 7), np.linspace(0, 1, 5))
        xx, yy = np.meshgrid(target.x, target.y)
        np.testing.assert_allclose(target.values["u"], 2*xx+3*yy+xx*yy)
        with self.assertRaises(DataError): resample_components(f, [-1, 2], [0, 1])

    def test_duplicate_conflict_and_geometry_holes(self):
        x, y = self.grid()
        with self.assertRaises(DataError): from_samples(x[:-1], y[:-1], {"u": x[:-1]})
        xx, yy = np.r_[x, x[0]], np.r_[y, y[0]]
        with self.assertRaises(DataError): from_samples(xx, yy, {"u": xx})
        f = from_samples(xx, yy, {"u": xx}, duplicate="identical")
        self.assertEqual(f.metadata["duplicates_removed"], 1)
        with self.assertRaises(DataError):
            from_samples(xx, yy, {"u": np.r_[x, 99]}, duplicate="identical")

    def test_comsol_repeated_time_and_explicit_selection(self):
        x, y = self.grid()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"fields.npz"
            np.savez(path, x=np.tile(x,(2,1)), y=np.tile(y,(2,1)),
                     tau=np.repeat([[0.],[1.]],len(x),axis=1), u=np.stack((x,x+2)))
            f = load_npz_field(path, x="x", y="y", fields={"u":"u"}, time_key="tau", time_index=1)
            np.testing.assert_allclose(f.values["u"].ravel(), x+2)
            self.assertEqual(f.metadata["time_value"], 1.)
            with self.assertRaises(DataError): load_npz_field(path, x="x", y="y", fields={"u":"u"})

    def test_txt_comments_header_and_columns(self):
        x, y = self.grid()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"instrument.txt"
            path.write_text("% exported simulation\nx y u\n" + "\n".join(f"{a} {b} {a+b}" for a,b in zip(x,y)))
            f = load_table_field(path, x="x", y="y", fields={"u":"u"},
                                 reader={"delimiter":r"\s+", "comment":"%"})
            np.testing.assert_allclose(f.values["u"].ravel(), x+y)

    def test_direction_mask_and_equal_aspect(self):
        x, y = self.grid()
        f = from_samples(x, y, {"u":x, "v":y})
        fig, ax = plt.subplots()
        try:
            mesh, record = plot_field(ax, f, components=("u","v"), color="direction", stride=1)
            self.assertTrue(np.ma.getmaskarray(mesh.get_array())[0,0])
            self.assertEqual(mesh.get_clim(), (-1,1))
            self.assertEqual(ax.get_aspect(), 1.)
            self.assertEqual(record["arrow_semantics"], "direction")
        finally:
            plt.close(fig)
