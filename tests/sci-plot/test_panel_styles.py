"""Behavior tests: panel styles survive rendering; validation matches data guards."""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from sci_plot.cli import main
from sci_plot.config import load_effective_config
from sci_plot.errors import SpecError
from sci_plot.render import _matplotlib, render_figure
from sci_plot.spec import validate_spec


class PanelStyleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="panel styles ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / "figure.json"
        (self.root / "data.csv").write_text("x,y\n0,1\n1,3\n", encoding="utf-8")
        self.spec = {
            "schema_version": 1, "kind": "multi_panel",
            "data": {"path": "data.csv"}, "mapping": {"x": "x", "y": "y"},
            "labels": {"x": "X", "y": "Y"},
            "style": {"backend": "matplotlib", "scienceplots": False},
            "panels": [
                {"kind": "line", "style": {"palette": ["#ff0000"], "font_size": 12,
                 "grid": True, "rcparams": {"lines.linewidth": 3, "axes.labelsize": 12}}},
                {"kind": "line", "style": {"palette": ["#0000ff"], "font_size": 8,
                 "grid": False, "rcparams": {"lines.linewidth": 1, "axes.labelsize": 8}}},
            ],
        }

    def test_styles_survive_draw_and_do_not_leak(self):
        mpl, plt, _ = _matplotlib()
        before = {k: mpl.rcParams[k] for k in ("font.size", "axes.grid", "lines.linewidth")}
        config, _ = load_effective_config(project_root=None, figure_spec=self.spec)
        result = render_figure(self.spec, self.path, config)
        self.addCleanup(plt.close, result.figure)
        result.figure.canvas.draw()
        left, right = result.figure.axes
        self.assertEqual([a.lines[0].get_color() for a in (left, right)], ["#ff0000", "#0000ff"])
        self.assertEqual([a.lines[0].get_linewidth() for a in (left, right)], [3, 1])
        self.assertEqual([a.xaxis.label.get_fontsize() for a in (left, right)], [12, 8])
        self.assertTrue(any(line.get_visible() for line in left.get_xgridlines()))
        self.assertFalse(any(line.get_visible() for line in right.get_xgridlines()))
        self.assertEqual(before, {k: mpl.rcParams[k] for k in before})
        result.figure.savefig(self.root / "panels.svg")
        self.assertIn("#ff0000", (self.root / "panels.svg").read_text())
        self.assertIn("#0000ff", (self.root / "panels.svg").read_text())

    def test_panel_font_family_is_stored_on_artist(self):
        self.spec["panels"][0]["style"]["chinese_font"] = "DejaVu Sans"
        self.spec["panels"][1]["style"]["chinese_font"] = "DejaVu Serif"
        config, _ = load_effective_config(project_root=None, figure_spec=self.spec)
        result = render_figure(self.spec, self.path, config)
        _, plt, _ = _matplotlib()
        self.addCleanup(plt.close, result.figure)
        result.figure.canvas.draw()
        self.assertIn("DejaVu Serif", result.figure.axes[1].xaxis.label.get_fontfamily())
        self.assertNotIn("DejaVu Serif", result.figure.axes[0].xaxis.label.get_fontfamily())

    def test_explicit_cli_render_settings_override_panel(self):
        config, _ = load_effective_config(project_root=None, figure_spec=self.spec,
            cli_overrides={"render": {"palette": ["#00ff00"], "grid": False}})
        result = render_figure(self.spec, self.path, config)
        _, plt, _ = _matplotlib()
        self.addCleanup(plt.close, result.figure)
        self.assertTrue(all(a.lines[0].get_color() == "#00ff00" for a in result.figure.axes))
        self.assertFalse(any(line.get_visible() for a in result.figure.axes for line in a.get_xgridlines()))

    def test_figure_settings_in_panel_and_undersized_grid_rejected(self):
        for key, value in (("backend", "matplotlib"), ("dpi", 300), ("formats", ["svg"]),
                           ("width_mm", 89), ("rcparams", {"savefig.dpi": 300})):
            with self.subTest(key=key):
                spec = json.loads(json.dumps(self.spec))
                spec["panels"][0]["style"][key] = value
                with self.assertRaises(SpecError):
                    validate_spec(spec)
        self.spec["layout"] = {"rows": 1, "cols": 1}
        with self.assertRaisesRegex(SpecError, "panel count"):
            validate_spec(self.spec)

    def test_validate_rejects_invalid_data_before_render(self):
        cases = [
            ("bar", "x,y\na,1\na,2\n", {"x": "x", "y": "y"}, "duplicate x"),
            ("bar", "x,y,g\na,1,p\na,2,q\nb,3,p\n",
             {"x": "x", "y": "y", "group": "g"}, "incomplete"),
            ("heatmap", "x,y,v\na,p,1\na,q,2\nb,p,3\n",
             {"x": "x", "y": "y", "value": "v"}, "rectangular"),
            ("heatmap", "x,y,v\na,p,1\na,p,2\n",
             {"x": "x", "y": "y", "value": "v"}, "duplicate"),
        ]
        for kind, data, mapping, message in cases:
            with self.subTest(kind=kind, message=message):
                (self.root / "data.csv").write_text(data, encoding="utf-8")
                spec = {"schema_version": 1, "kind": kind, "data": {"path": "data.csv"},
                        "mapping": mapping, "style": {"scienceplots": False}}
                self.path.write_text(json.dumps(spec), encoding="utf-8")
                output = io.StringIO()
                with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                    self.assertEqual(main(["validate", str(self.path)]), 2)
                self.assertIn(message, output.getvalue())

    def test_validate_checks_panel_value_without_reading_data_in_schema_only(self):
        self.spec["panels"][0]["style"]["font_size"] = -1
        self.path.write_text(json.dumps(self.spec), encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            self.assertEqual(main(["validate", str(self.path), "--schema-only"]), 2)
        self.assertIn("font_size", output.getvalue())


if __name__ == "__main__":
    unittest.main()
