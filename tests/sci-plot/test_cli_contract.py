from __future__ import annotations

import contextlib
import io
import json
import tempfile
import tomllib
import unittest
from pathlib import Path

from sci_plot.cli import main
from sci_plot.config import REPOSITORY_ROOT


class CliContractTests(unittest.TestCase):
    def _run(self, argv: list[str]) -> tuple[int, dict, str]:
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(argv)
        payload = json.loads(stdout.getvalue()) if stdout.getvalue().strip() else {}
        return code, payload, stderr.getvalue()

    def test_entry_point_and_skill_identity(self) -> None:
        with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)
        self.assertEqual(project["project"]["version"], "0.2.0")
        self.assertIn("SciencePlots>=2.1,<3", project["project"]["dependencies"])
        self.assertEqual(project["project"]["scripts"]["sci-plot"], "sci_plot.cli:main")
        self.assertEqual(project["project"]["readme"], "README.md")
        self.assertTrue((REPOSITORY_ROOT / "README.md").is_file())
        skill = (REPOSITORY_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("name: sci-plot", skill)
        metadata = (REPOSITORY_ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8")
        self.assertIn('display_name: "Sci Plot"', metadata)
        self.assertEqual(
            (REPOSITORY_ROOT / "config" / "defaults.toml").read_bytes(),
            (
                REPOSITORY_ROOT
                / "src"
                / "sci_plot"
                / "resources"
                / "defaults.toml"
            ).read_bytes(),
        )
        self.assertEqual(
            tomllib.loads(
                (REPOSITORY_ROOT / "upstream" / "sources.toml").read_text(
                    encoding="utf-8"
                )
            ),
            tomllib.loads(
                (
                    REPOSITORY_ROOT
                    / "src"
                    / "sci_plot"
                    / "resources"
                    / "sources.toml"
                ).read_text(encoding="utf-8")
            ),
        )

    def test_optional_skill_composition_contract(self) -> None:
        routing = (REPOSITORY_ROOT / "references" / "routing.md").read_text(
            encoding="utf-8"
        )
        for canonical_name in (
            "experimental-design",
            "exploratory-data-analysis",
            "nature-figure",
            "scientific-visualization",
            "statistical-analysis",
            "statistical-power",
        ):
            self.assertIn(f"`{canonical_name}`", routing)
        defaults = (REPOSITORY_ROOT / "config" / "defaults.toml").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("[handoffs]", defaults)
        self.assertTrue(tomllib.loads(defaults)["render"]["scienceplots"])

    def test_templates_and_example_validation(self) -> None:
        code, payload, error = self._run(["list-templates"])
        self.assertEqual((code, error), (0, ""))
        self.assertEqual(
            {item["kind"] for item in payload["templates"]},
            {"line", "bar", "scatter", "heatmap", "errorbar", "multi_panel"},
        )
        errorbar = next(
            item for item in payload["templates"] if item["kind"] == "errorbar"
        )
        self.assertEqual(errorbar["required_mapping"], ["x", "y"])
        self.assertEqual(
            errorbar["optional_mapping"],
            ["group", "yerr", "ymin", "ymax"],
        )
        code, payload, error = self._run(
            ["validate", str(REPOSITORY_ROOT / "examples" / "figure.spec.json")]
        )
        self.assertEqual((code, error), (0, ""))
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["kind"], "line")
        self.assertTrue(payload["effective_render"]["scienceplots"])

    def test_validate_checks_effective_render_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "data.csv").write_text("x,y\n0,1\n", encoding="utf-8")
            spec = {
                "schema_version": 1,
                "kind": "line",
                "data": {"path": "data.csv"},
                "mapping": {"x": "x", "y": "y"},
                "export": {"dpi": "not-a-number"},
            }
            path = root / "bad.spec.json"
            path.write_text(json.dumps(spec), encoding="utf-8")
            code, _, error = self._run(["validate", str(path)])
            self.assertEqual(code, 2)
            self.assertIn("render.dpi", error)

    def test_validate_uses_explicit_project_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "sci-plot.toml").write_text(
                "[render]\ntheme = \"nature\"\ndpi = 450\nscienceplots = false\n",
                encoding="utf-8",
            )
            (root / "data.csv").write_text("x,y\n0,1\n", encoding="utf-8")
            spec = {
                "schema_version": 1,
                "kind": "line",
                "data": {"path": "data.csv"},
                "mapping": {"x": "x", "y": "y"},
            }
            path = root / "figure.spec.json"
            path.write_text(json.dumps(spec), encoding="utf-8")
            code, payload, error = self._run(
                ["validate", str(path), "--project-root", str(root)]
            )
            self.assertEqual((code, error), (0, ""))
            self.assertEqual(payload["project_root"], str(root.resolve()))
            self.assertEqual(
                payload["project_config"], str((root / "sci-plot.toml").resolve())
            )
            self.assertEqual(payload["effective_render"]["theme"], "nature")
            self.assertEqual(payload["effective_render"]["dpi"], 450)
            self.assertFalse(payload["effective_render"]["scienceplots"])

    def test_init_command_is_explicit_consent(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            code, payload, error = self._run(
                ["init", str(root), "--project-name", "Demo"]
            )
            self.assertEqual((code, error), (0, ""))
            config = Path(payload["created"])
            self.assertTrue(config.is_file())
            self.assertTrue(
                tomllib.loads(config.read_text(encoding="utf-8"))["render"][
                    "scienceplots"
                ]
            )
            code, _, error = self._run(["init", str(root)])
            self.assertEqual(code, 2)
            self.assertIn("already exists", error)

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            code, payload, error = self._run(
                ["init", str(root), "--no-scienceplots"]
            )
            self.assertEqual((code, error), (0, ""))
            config = Path(payload["created"])
            self.assertFalse(
                tomllib.loads(config.read_text(encoding="utf-8"))["render"][
                    "scienceplots"
                ]
            )


if __name__ == "__main__":
    unittest.main()
