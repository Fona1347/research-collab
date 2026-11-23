from __future__ import annotations

import csv
import os
from dataclasses import FrozenInstanceError
import tempfile
import unittest
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sci_plot import project_style
from sci_plot.backends import resolve_backend
from sci_plot.config import load_effective_config
from sci_plot.errors import ConfigurationError, DependencyError
from sci_plot.render import _matplotlib, render_figure


class RenderKindTests(unittest.TestCase):
    def test_broken_pubfig_install_has_a_clear_dependency_error(self) -> None:
        missing = ModuleNotFoundError("No module named 'sklearn'", name="sklearn")
        with (
            patch("sci_plot.backends.installed_version", return_value="0.3.0"),
            patch("sci_plot.backends.importlib.import_module", side_effect=missing),
        ):
            with self.assertRaisesRegex(DependencyError, "sklearn"):
                resolve_backend("pubfig")

    def test_auto_falls_back_when_pubfig_import_is_broken(self) -> None:
        missing = ModuleNotFoundError("No module named 'sklearn'", name="sklearn")

        def version(name: str) -> str:
            return "0.3.0" if name == "pubfig" else "3.11.0"

        with (
            patch("sci_plot.backends.installed_version", side_effect=version),
            patch("sci_plot.backends.importlib.import_module", side_effect=missing),
        ):
            backend = resolve_backend("auto")
        self.assertEqual(backend.name, "matplotlib")
        self.assertIn("unusable pubfig", backend.warning or "")

    def test_pubfig_api_is_preflighted_before_auto_selection(self) -> None:
        incompatible = SimpleNamespace(
            FigureSpec=object,
            save_figure=lambda figure, path: None,
        )

        def version(name: str) -> str:
            return "0.3.0" if name == "pubfig" else "3.11.0"

        with (
            patch("sci_plot.backends.installed_version", side_effect=version),
            patch("sci_plot.backends.importlib.import_module", return_value=incompatible),
        ):
            fallback = resolve_backend("auto")
            self.assertEqual(fallback.name, "matplotlib")
            self.assertIn("export API", fallback.warning or "")
            with self.assertRaisesRegex(DependencyError, "export API"):
                resolve_backend("pubfig")

    def test_pubfig_figure_spec_constructor_is_preflighted(self) -> None:
        class IncompatibleFigureSpec:
            def __init__(self, name):
                self.name = name

        def compatible_save(
            figure,
            path,
            *,
            spec,
            width,
            height_mm,
            raster_dpi,
            trim,
            svg_fonttype,
        ):
            return None

        incompatible = SimpleNamespace(
            FigureSpec=IncompatibleFigureSpec,
            save_figure=compatible_save,
        )

        def version(name: str) -> str:
            return "0.3.0" if name == "pubfig" else "3.11.0"

        with (
            patch("sci_plot.backends.installed_version", side_effect=version),
            patch("sci_plot.backends.importlib.import_module", return_value=incompatible),
        ):
            fallback = resolve_backend("auto")
            self.assertEqual(fallback.name, "matplotlib")
            self.assertIn("FigureSpec API", fallback.warning or "")
            with self.assertRaisesRegex(DependencyError, "FigureSpec API"):
                resolve_backend("pubfig")

    def test_matplotlib_cache_falls_back_to_temp(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("MPLCONFIGDIR", None)
                with patch("sci_plot.render.tempfile.gettempdir", return_value=raw):
                    _matplotlib()
                self.assertEqual(
                    os.environ["MPLCONFIGDIR"],
                    str(Path(raw) / "sci-plot-matplotlib"),
                )
                self.assertTrue(Path(os.environ["MPLCONFIGDIR"]).is_dir())

    def test_resolved_rc_overrides_optional_style_layer(self) -> None:
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, "xy.csv", [{"x": 0, "y": 1}, {"x": 1, "y": 2}])
            spec = {
                "schema_version": 1,
                "kind": "line",
                "data": {"path": "xy.csv"},
                "mapping": {"x": "x", "y": "y"},
            }
            config, _ = load_effective_config(
                project_root=None,
                cli_overrides={
                    "render": {
                        "backend": "matplotlib",
                        "scienceplots": True,
                        "rcparams": {"axes.linewidth": 3.25},
                    }
                },
            )
            real_context = plt.style.context

            def competing_style(_):
                return real_context({"axes.linewidth": 9.0})

            with patch.dict(sys.modules, {"scienceplots": object()}):
                with patch("matplotlib.pyplot.style.context", side_effect=competing_style):
                    rendered = render_figure(spec, root / "figure.spec.json", config)
            self.assertEqual(
                rendered.figure.axes[0].spines["left"].get_linewidth(),
                3.25,
            )
            plt.close(rendered.figure)

    def _config(self) -> dict:
        config, _ = load_effective_config(
            project_root=None,
            cli_overrides={
                "render": {
                    "backend": "matplotlib",
                    "width_mm": 89,
                    "height_mm": 60,
                },
                "logging": {"enabled": False},
            },
        )
        return config

    def _write(self, root: Path, name: str, rows: list[dict[str, object]]) -> Path:
        path = root / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_line_bar_scatter_and_heatmap(self) -> None:
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(
                root,
                "xy.csv",
                [
                    {"x": 0, "y": 1, "group": "A"},
                    {"x": 1, "y": 2, "group": "A"},
                    {"x": 0, "y": 2, "group": "B"},
                    {"x": 1, "y": 3, "group": "B"},
                ],
            )
            self._write(
                root,
                "heat.csv",
                [
                    {"x": "a", "y": "r1", "value": 1},
                    {"x": "b", "y": "r1", "value": 2},
                    {"x": "a", "y": "r2", "value": 3},
                    {"x": "b", "y": "r2", "value": 4},
                ],
            )
            for kind in ("line", "bar", "scatter"):
                spec = {
                    "schema_version": 1,
                    "kind": kind,
                    "data": {"path": "xy.csv"},
                    "mapping": {"x": "x", "y": "y", "group": "group"},
                }
                rendered = render_figure(spec, root / "figure.spec.json", self._config())
                self.assertEqual(rendered.backend.name, "matplotlib")
                self.assertEqual(rendered.inputs, [(root / "xy.csv").resolve()])
                plt.close(rendered.figure)

            heat = {
                "schema_version": 1,
                "kind": "heatmap",
                "data": {"path": "heat.csv"},
                "mapping": {"x": "x", "y": "y", "value": "value"},
            }
            rendered = render_figure(heat, root / "heat.spec.json", self._config())
            self.assertEqual(len(rendered.figure.axes), 2)
            plt.close(rendered.figure)

    def test_errorbar_supports_symmetric_bounds_and_groups(self) -> None:
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(
                root,
                "errors.csv",
                [
                    {"x": 0, "y": 1.0, "error": 0.1, "low": 0.8, "high": 1.2, "group": "A"},
                    {"x": 1, "y": 1.5, "error": 0.2, "low": 1.2, "high": 1.8, "group": "A"},
                    {"x": 0, "y": 2.0, "error": 0.15, "low": 1.7, "high": 2.3, "group": "B"},
                    {"x": 1, "y": 2.4, "error": 0.25, "low": 2.0, "high": 2.8, "group": "B"},
                ],
            )
            symmetric = {
                "schema_version": 1,
                "kind": "errorbar",
                "data": {"path": "errors.csv"},
                "mapping": {
                    "x": "x",
                    "y": "y",
                    "yerr": "error",
                    "group": "group",
                },
                "labels": {"uncertainty": "SD"},
            }
            rendered = render_figure(
                symmetric,
                root / "errorbar.spec.json",
                self._config(),
            )
            self.assertEqual(len(rendered.figure.axes[0].containers), 2)
            self.assertEqual(
                [
                    text.get_text()
                    for text in rendered.figure.axes[0].get_legend().get_texts()
                ],
                ["A", "B"],
            )
            plt.close(rendered.figure)

            bounded = {
                **symmetric,
                "mapping": {
                    "x": "x",
                    "y": "y",
                    "ymin": "low",
                    "ymax": "high",
                },
                "labels": {"uncertainty": "95% CI"},
            }
            rendered = render_figure(
                bounded,
                root / "bounded.spec.json",
                self._config(),
            )
            self.assertEqual(len(rendered.figure.axes[0].containers), 1)
            plt.close(rendered.figure)

    def test_simple_multi_panel(self) -> None:
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(
                root,
                "xy.csv",
                [{"x": 0, "y": 1}, {"x": 1, "y": 2}],
            )
            spec = {
                "schema_version": 1,
                "kind": "multi_panel",
                "data": {"path": "xy.csv"},
                "mapping": {"x": "x", "y": "y"},
                "layout": {"rows": 1, "cols": 2},
                "panels": [
                    {"kind": "line", "labels": {"title": "Line"}},
                    {"kind": "scatter", "labels": {"title": "Scatter"}},
                ],
            }
            rendered = render_figure(spec, root / "multi.spec.json", self._config())
            self.assertEqual(len(rendered.figure.axes), 2)
            plt.close(rendered.figure)

    def test_theme_and_style_change_rendered_artists(self) -> None:
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, "xy.csv", [{"x": 0, "y": 1}, {"x": 1, "y": 2}])
            spec = {
                "schema_version": 1,
                "kind": "line",
                "data": {"path": "xy.csv"},
                "mapping": {"x": "x", "y": "y"},
            }
            nature, _ = load_effective_config(
                project_root=None,
                cli_overrides={"render": {"backend": "matplotlib", "theme": "nature"}},
            )
            science, _ = load_effective_config(
                project_root=None,
                cli_overrides={
                    "render": {
                        "backend": "matplotlib",
                        "theme": "science",
                        "style": "minimal",
                    }
                },
            )
            first = render_figure(spec, root / "figure.spec.json", nature)
            second = render_figure(spec, root / "figure.spec.json", science)
            self.assertNotEqual(
                first.figure.axes[0].lines[0].get_color(),
                second.figure.axes[0].lines[0].get_color(),
            )
            self.assertFalse(second.figure.axes[0].spines["left"].get_visible())
            plt.close(first.figure)
            plt.close(second.figure)

    def test_invalid_custom_palette_and_rcparam_are_clear(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            self._write(root, "xy.csv", [{"x": 0, "y": 1}, {"x": 1, "y": 2}])
            spec = {
                "schema_version": 1,
                "kind": "line",
                "data": {"path": "xy.csv"},
                "mapping": {"x": "x", "y": "y"},
            }
            bad_palette, _ = load_effective_config(
                project_root=None,
                cli_overrides={
                    "render": {
                        "backend": "matplotlib",
                        "theme": "custom",
                        "palette": ["not-a-color"],
                    }
                },
            )
            with self.assertRaisesRegex(ConfigurationError, "palette"):
                render_figure(spec, root / "figure.spec.json", bad_palette)

            bad_rc, _ = load_effective_config(
                project_root=None,
                cli_overrides={
                    "render": {
                        "backend": "matplotlib",
                        "style": "custom",
                        "rcparams": {"not.a.real.rcparam": 1},
                    }
                },
            )
            with self.assertRaisesRegex(ConfigurationError, "rcParam"):
                render_figure(spec, root / "figure.spec.json", bad_rc)

    def test_project_style_applies_and_restores_custom_matplotlib_settings(self) -> None:
        import matplotlib
        import matplotlib.pyplot as plt

        before_linewidth = matplotlib.rcParams["axes.linewidth"]
        before_figsize = list(matplotlib.rcParams["figure.figsize"])
        before_backend = matplotlib.get_backend()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "sci-plot.toml").write_text(
                "[render]\n"
                "theme = \"nature\"\n"
                "scienceplots = false\n"
                "width_mm = 100\n"
                "height_mm = 70\n"
                "dpi = 420\n"
                "formats = [\"svg\", \"png\"]\n"
                "palette = [\"#112233\", \"#445566\"]\n"
                "rcparams = { \"axes.linewidth\" = 2.5 }\n",
                encoding="utf-8",
            )
            with project_style(root) as style:
                figure = plt.figure()
                figure.add_subplot(projection="3d")
                self.assertEqual(style.config_path, (root / "sci-plot.toml").resolve())
                self.assertEqual(style.palette, ("#112233", "#445566"))
                self.assertEqual(style.formats, ("svg", "png"))
                self.assertEqual(style.dpi, 420)
                self.assertAlmostEqual(figure.get_figwidth(), 100 / 25.4)
                self.assertAlmostEqual(figure.get_figheight(), 70 / 25.4)
                self.assertEqual(figure.dpi, 420)
                self.assertEqual(matplotlib.rcParams["axes.linewidth"], 2.5)
                self.assertEqual(
                    matplotlib.rcParams["axes.prop_cycle"].by_key()["color"],
                    ["#112233", "#445566"],
                )
                with self.assertRaises(FrozenInstanceError):
                    style.dpi = 300
                plt.close(figure)

        self.assertEqual(matplotlib.get_backend(), before_backend)
        self.assertEqual(matplotlib.rcParams["axes.linewidth"], before_linewidth)
        self.assertEqual(list(matplotlib.rcParams["figure.figsize"]), before_figsize)

    def test_missing_explicit_chinese_font_is_clear(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "sci-plot.toml").write_text(
                "[render]\n"
                "scienceplots = false\n"
                "chinese_font = \"__sci_plot_font_does_not_exist__\"\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ConfigurationError, "chinese_font"):
                with project_style(root):
                    pass


if __name__ == "__main__":
    unittest.main()
