from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sci_plot.config import DEFAULTS_PATH, load_effective_config
from sci_plot.errors import ConfigurationError
from sci_plot.project import init_project, resolve_project_root


class ConfigProjectTests(unittest.TestCase):
    def test_config_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "sci-plot.toml").write_text(
                "[render]\ntheme = \"nature\"\ndpi = 200\n",
                encoding="utf-8",
            )
            spec = {
                "style": {"dpi": 400, "theme": "science"},
                "export": {"dpi": 450, "formats": ["pdf"]},
            }
            config, path = load_effective_config(
                project_root=root,
                figure_spec=spec,
                cli_overrides={"render": {"dpi": 600, "theme": "cell"}},
                defaults_path=DEFAULTS_PATH,
            )
            self.assertEqual(config["render"]["dpi"], 600)
            self.assertEqual(config["render"]["theme"], "cell")
            self.assertEqual(config["render"]["formats"], ["pdf"])
            self.assertEqual(path, root / "sci-plot.toml")

    def test_missing_project_config_is_not_created(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            config, path = load_effective_config(project_root=root)
            self.assertEqual(config["render"]["theme"], "paper")
            self.assertTrue(config["render"]["scienceplots"])
            self.assertIsNone(path)
            self.assertFalse((root / "sci-plot.toml").exists())

    def test_unknown_theme_or_style_is_rejected(self) -> None:
        with self.assertRaisesRegex(ConfigurationError, "render.theme"):
            load_effective_config(
                project_root=None,
                cli_overrides={"render": {"theme": "not-a-theme"}},
            )
        with self.assertRaisesRegex(ConfigurationError, "render.style"):
            load_effective_config(
                project_root=None,
                cli_overrides={"render": {"style": "not-a-style"}},
            )

    def test_init_is_explicit_and_never_overwrites(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = init_project(
                root,
                project_name="Demo",
                output_dir="figures",
                theme="paper",
                style="general-paper",
                scienceplots=False,
            )
            before = path.read_bytes()
            with self.assertRaises(ConfigurationError):
                init_project(
                    root,
                    project_name="Changed",
                    output_dir="other",
                    theme="cell",
                    style="general-paper",
                    scienceplots=False,
                )
            self.assertEqual(path.read_bytes(), before)

    def test_project_root_is_not_guessed_from_ancestors(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            nested = root / "nested"
            nested.mkdir()
            (root / "sci-plot.toml").write_text("[project]\nname=\"root\"\n", encoding="utf-8")
            spec = nested / "figure.spec.json"
            spec.write_text("{}", encoding="utf-8")
            self.assertIsNone(resolve_project_root(spec, None))
            self.assertEqual(resolve_project_root(spec, root), root.resolve())


if __name__ == "__main__":
    unittest.main()
