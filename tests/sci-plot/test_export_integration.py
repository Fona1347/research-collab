from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sci_plot.backends import Backend
from sci_plot.cli import main
from sci_plot.export import export_figure, output_paths
from sci_plot.render import _matplotlib
from sci_plot.safety import file_fingerprint


class ExportIntegrationTests(unittest.TestCase):
    def test_dotted_basename_is_preserved(self) -> None:
        paths = output_paths(Path("figure.v1"), ["svg", "pdf"])
        self.assertEqual(paths, [Path("figure.v1.svg"), Path("figure.v1.pdf")])

    def test_pubfig_receives_a_fresh_temp_path(self) -> None:
        _, plt, _ = _matplotlib()

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            figure, axis = plt.subplots()
            axis.plot([0, 1], [0, 1])

            calls = {}

            class FigureSpec:
                def __init__(
                    self,
                    name,
                    font_family,
                    single_column_mm,
                    double_column_mm,
                    default_raster_dpi,
                    background_color,
                ):
                    self.name = name
                    self.font_family = font_family
                    self.single_column_mm = single_column_mm
                    self.double_column_mm = double_column_mm
                    self.default_raster_dpi = default_raster_dpi
                    self.background_color = background_color

            def save_figure(
                fig,
                filename,
                *,
                spec,
                width,
                height_mm,
                raster_dpi,
                trim,
                svg_fonttype,
                transparent,
            ):
                target = Path(filename)
                self.assertFalse(target.exists())
                calls.update(
                    spec=spec,
                    width=width,
                    height_mm=height_mm,
                    raster_dpi=raster_dpi,
                    trim=trim,
                    svg_fonttype=svg_fonttype,
                    transparent=transparent,
                )
                fig.savefig(target, dpi=raster_dpi)

            backend = Backend(
                "pubfig",
                "0.3.0",
                SimpleNamespace(save_figure=save_figure, FigureSpec=FigureSpec),
            )
            final = root / "figure.svg"
            export_figure(
                figure,
                [final],
                ["svg"],
                dpi=300,
                backend=backend,
                rc_params={
                    "svg.fonttype": "none",
                    "font.sans-serif": ["Definitely Missing Font", "DejaVu Sans"],
                },
                theme="nature",
                overwrite=False,
            )
            self.assertTrue(final.is_file())
            self.assertAlmostEqual(calls["width"], figure.get_figwidth() * 25.4)
            self.assertAlmostEqual(calls["height_mm"], figure.get_figheight() * 25.4)
            self.assertEqual(calls["raster_dpi"], 300)
            self.assertFalse(calls["trim"])
            self.assertEqual(calls["svg_fonttype"], "none")
            self.assertEqual(calls["spec"].name, "sci-plot-nature")
            self.assertEqual(calls["spec"].font_family, "DejaVu Sans")
            plt.close(figure)

    def test_no_overwrite_commit_rolls_back_on_failure(self) -> None:
        _, plt, _ = _matplotlib()

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            figure, axis = plt.subplots()
            axis.plot([0, 1], [0, 1])
            finals = [root / "figure.svg", root / "figure.pdf"]
            real_replace = os.replace
            calls = 0

            def fail_second(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated commit failure")
                return real_replace(source, destination)

            with patch("sci_plot.export.os.replace", side_effect=fail_second):
                with self.assertRaisesRegex(OSError, "simulated"):
                    export_figure(
                        figure,
                        finals,
                        ["svg", "pdf"],
                        dpi=300,
                        backend=Backend("matplotlib", "test", None),
                        rc_params={"svg.fonttype": "none"},
                        theme="paper",
                        overwrite=False,
                    )
            self.assertFalse(any(path.exists() for path in finals))
            plt.close(figure)

    def test_overwrite_commit_restores_old_files_on_failure(self) -> None:
        _, plt, _ = _matplotlib()

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            finals = [root / "figure.svg", root / "figure.pdf"]
            old = {finals[0]: b"old-svg", finals[1]: b"old-pdf"}
            for path, payload in old.items():
                path.write_bytes(payload)
            figure, axis = plt.subplots()
            axis.plot([0, 1], [0, 1])
            real_replace = os.replace
            calls = 0

            def fail_second(source, destination):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("simulated overwrite commit failure")
                return real_replace(source, destination)

            with patch("sci_plot.export.os.replace", side_effect=fail_second):
                with self.assertRaisesRegex(OSError, "simulated overwrite"):
                    export_figure(
                        figure,
                        finals,
                        ["svg", "pdf"],
                        dpi=300,
                        backend=Backend("matplotlib", "test", None),
                        rc_params={"svg.fonttype": "none"},
                        theme="paper",
                        overwrite=True,
                    )
            self.assertEqual({path: path.read_bytes() for path in finals}, old)
            plt.close(figure)

    def test_backup_cleanup_failure_does_not_rollback_committed_outputs(self) -> None:
        _, plt, _ = _matplotlib()

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            finals = [root / "figure.svg", root / "figure.pdf"]
            for path in finals:
                path.write_bytes(b"old")
            figure, axis = plt.subplots()
            axis.plot([0, 1], [0, 1])
            real_unlink = Path.unlink
            failed = False

            def fail_one_nonempty_backup(path, *args, **kwargs):
                nonlocal failed
                if (
                    not failed
                    and path.suffix == ".bak"
                    and path.exists()
                    and path.stat().st_size > 0
                ):
                    failed = True
                    raise OSError("simulated backup cleanup failure")
                return real_unlink(path, *args, **kwargs)

            with patch("pathlib.Path.unlink", side_effect=fail_one_nonempty_backup, autospec=True):
                warnings = export_figure(
                    figure,
                    finals,
                    ["svg", "pdf"],
                    dpi=300,
                    backend=Backend("matplotlib", "test", None),
                    rc_params={"svg.fonttype": "none"},
                    theme="paper",
                    overwrite=True,
                )
            self.assertTrue(failed)
            self.assertEqual(len(warnings), 1)
            self.assertTrue(all(path.read_bytes() != b"old" for path in finals))
            self.assertEqual(len(list(root.glob("*.bak"))), 1)
            plt.close(figure)

    def _project(self, root: Path) -> Path:
        (root / "data.csv").write_text(
            "time,response,condition\n"
            "0,0.1,A\n1,0.2,A\n0,0.2,B\n1,0.4,B\n",
            encoding="utf-8",
        )
        spec = {
            "schema_version": 1,
            "kind": "line",
            "data": {"path": "data.csv"},
            "mapping": {"x": "time", "y": "response", "group": "condition"},
            "labels": {"title": "Response", "x": "Time", "y": "Response"},
            "export": {
                "path": "figures/response",
                "formats": ["svg", "pdf", "png", "tiff"],
                "dpi": 300,
            },
        }
        path = root / "figure.spec.json"
        path.write_text(json.dumps(spec), encoding="utf-8")
        return path

    def _run(self, argv: list[str]) -> tuple[int, dict, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        payload = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else {}
        return code, payload, stderr.getvalue()

    def test_four_formats_input_unchanged_and_conflict_timestamp(self) -> None:
        from PIL import Image

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = self._project(root)
            data = root / "data.csv"
            before = file_fingerprint(data)
            argv = ["render", str(spec), "--backend", "matplotlib", "--no-log"]
            code, first, error = self._run(argv)
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(file_fingerprint(data), before)
            first_paths = [Path(item) for item in first["outputs"]]
            self.assertEqual({path.suffix for path in first_paths}, {".svg", ".pdf", ".png", ".tiff"})
            first_fingerprints = {path: file_fingerprint(path) for path in first_paths}
            with Image.open(next(path for path in first_paths if path.suffix == ".tiff")) as image:
                self.assertEqual(image.mode, "RGBA")
                expected = (round(89 / 25.4 * 300), round(60 / 25.4 * 300))
                self.assertTrue(
                    all(
                        abs(actual - target) <= 2
                        for actual, target in zip(image.size, expected, strict=True)
                    )
                )

            code, second, error = self._run(argv)
            self.assertEqual((code, error), (0, ""))
            self.assertTrue(second["conflict_renamed"])
            second_paths = [Path(item) for item in second["outputs"]]
            stems = {path.stem for path in second_paths}
            self.assertEqual(len(stems), 1)
            self.assertNotEqual(first_paths, second_paths)
            self.assertEqual(
                {path: file_fingerprint(path) for path in first_paths},
                first_fingerprints,
            )
            self.assertEqual(file_fingerprint(data), before)

    def test_external_output_requires_explicit_flag(self) -> None:
        with tempfile.TemporaryDirectory() as raw_a, tempfile.TemporaryDirectory() as raw_b:
            root = Path(raw_a)
            spec = self._project(root)
            external = Path(raw_b) / "outside.svg"
            code, _, error = self._run(
                [
                    "render",
                    str(spec),
                    "--backend",
                    "matplotlib",
                    "--output",
                    str(external),
                    "--no-log",
                ]
            )
            self.assertEqual(code, 2)
            self.assertIn("outside the allowed root", error)
            self.assertFalse(external.exists())

            code, payload, error = self._run(
                [
                    "render",
                    str(spec),
                    "--backend",
                    "matplotlib",
                    "--output",
                    str(external),
                    "--allow-external-output",
                    "--no-log",
                ]
            )
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(payload["outputs"], [str(external.resolve())])
            self.assertTrue(external.is_file())


if __name__ == "__main__":
    unittest.main()
