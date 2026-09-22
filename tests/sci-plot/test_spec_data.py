from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sci_plot.data import SUPPORTED_FORMATS, load_plot_data, load_table
from sci_plot.errors import DataError, SpecError
from sci_plot.spec import load_spec, validate_spec


def basic_spec(data_name: str = "data.csv") -> dict:
    return {
        "schema_version": 1,
        "kind": "line",
        "data": {"path": data_name},
        "mapping": {"x": "x", "y": "y"},
        "labels": {"x": "X", "y": "Y"},
        "export": {"path": "figures/test.svg"},
    }


def errorbar_spec(mapping: dict[str, str] | None = None) -> dict:
    return {
        "schema_version": 1,
        "kind": "errorbar",
        "data": {"path": "errors.csv"},
        "mapping": mapping or {"x": "x", "y": "y", "yerr": "error"},
        "labels": {"x": "X", "y": "Y", "uncertainty": "SD"},
    }


class SpecDataTests(unittest.TestCase):
    def test_csv_mapping_and_missing_values(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "data.csv").write_text("x,y\n0,1\n1,2\n", encoding="utf-8")
            path = root / "figure.spec.json"
            path.write_text(json.dumps(basic_spec()), encoding="utf-8")
            spec = load_spec(path)
            frame, resolved, data_format = load_plot_data(spec, path)
            self.assertEqual(frame.shape, (2, 2))
            self.assertEqual(resolved, (root / "data.csv").resolve())
            self.assertEqual(data_format, "csv")

            (root / "data.csv").write_text("x,y\n0,\n", encoding="utf-8")
            with self.assertRaisesRegex(DataError, "missing values"):
                load_plot_data(spec, path)

    def test_invalid_column_is_clear(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "data.csv").write_text("x,z\n0,1\n", encoding="utf-8")
            path = root / "figure.spec.json"
            path.write_text(json.dumps(basic_spec()), encoding="utf-8")
            with self.assertRaisesRegex(DataError, "Mapped column"):
                load_plot_data(load_spec(path), path)

    def test_duplicate_json_key_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "bad.json"
            path.write_text('{"schema_version":1,"kind":"line","kind":"bar"}', encoding="utf-8")
            with self.assertRaisesRegex(SpecError, "Duplicate JSON key"):
                load_spec(path)

    def test_spec_overwrite_is_forbidden(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            spec = basic_spec()
            spec["export"]["overwrite"] = True
            path = root / "bad.json"
            path.write_text(json.dumps(spec), encoding="utf-8")
            with self.assertRaisesRegex(SpecError, "forbidden"):
                load_spec(path)

    def test_errorbar_spec_requires_one_named_uncertainty_form(self) -> None:
        validate_spec(errorbar_spec())
        validate_spec(
            errorbar_spec(
                {"x": "x", "y": "y", "ymin": "low", "ymax": "high"}
            )
        )

        missing = errorbar_spec({"x": "x", "y": "y"})
        with self.assertRaisesRegex(SpecError, "exactly one uncertainty form"):
            validate_spec(missing)

        both = errorbar_spec(
            {
                "x": "x",
                "y": "y",
                "yerr": "error",
                "ymin": "low",
                "ymax": "high",
            }
        )
        with self.assertRaisesRegex(SpecError, "exactly one uncertainty form"):
            validate_spec(both)

        partial = errorbar_spec({"x": "x", "y": "y", "ymin": "low"})
        with self.assertRaisesRegex(SpecError, "both ymin and ymax"):
            validate_spec(partial)

        unnamed = errorbar_spec()
        unnamed["labels"].pop("uncertainty")
        with self.assertRaisesRegex(SpecError, "labels.uncertainty"):
            validate_spec(unnamed)

    def test_errorbar_data_rejects_invalid_errors_and_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "figure.spec.json"
            plot = errorbar_spec()

            (root / "errors.csv").write_text(
                "x,y,error\n0,1,0.1\n1,2,0.2\n",
                encoding="utf-8",
            )
            frame, _, _ = load_plot_data(plot, path)
            self.assertEqual(frame.shape, (2, 3))

            (root / "errors.csv").write_text(
                "x,y,error\n0,1,-0.1\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DataError, "non-negative"):
                load_plot_data(plot, path)

            bounded = errorbar_spec(
                {"x": "x", "y": "y", "ymin": "low", "ymax": "high"}
            )
            (root / "errors.csv").write_text(
                "x,y,low,high\n0,1,1.1,1.2\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DataError, "ymin <= y <= ymax"):
                load_plot_data(bounded, path)

            (root / "errors.csv").write_text(
                "x,y,error\n0,1,inf\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(DataError, "non-finite"):
                load_plot_data(plot, path)

    def test_xlsx_dispatch_uses_openpyxl(self) -> None:
        import pandas as pd

        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "data.xlsx"
            path.write_bytes(b"placeholder")
            with patch.object(
                pd,
                "read_excel",
                return_value=pd.DataFrame({"x": [0], "y": [1]}),
            ) as read_excel:
                frame, resolved, data_format = load_table(
                    {"path": str(path)},
                    root / "figure.spec.json",
                )
            self.assertEqual(frame.shape, (1, 2))
            self.assertEqual(resolved, path.resolve())
            self.assertEqual(data_format, "xlsx")
            read_excel.assert_called_once_with(path.resolve(), engine="openpyxl")

    def test_declared_data_formats(self) -> None:
        self.assertEqual(
            SUPPORTED_FORMATS,
            ("csv", "tsv", "json", "xlsx", "npy", "npz"),
        )

    def test_non_finite_geometry_is_rejected_for_every_plot_family(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            path = root / "figure.spec.json"
            (root / "xy.csv").write_text("x,y\n0,inf\n", encoding="utf-8")
            for kind in ("line", "bar", "scatter"):
                plot = {
                    "kind": kind,
                    "data": {"path": "xy.csv"},
                    "mapping": {"x": "x", "y": "y"},
                }
                with self.assertRaisesRegex(DataError, "non-finite"):
                    load_plot_data(plot, path)

            (root / "heat.csv").write_text(
                "x,y,value\na,row,inf\n",
                encoding="utf-8",
            )
            heatmap = {
                "kind": "heatmap",
                "data": {"path": "heat.csv"},
                "mapping": {"x": "x", "y": "y", "value": "value"},
            }
            with self.assertRaisesRegex(DataError, "non-finite"):
                load_plot_data(heatmap, path)

            (root / "xy.csv").write_text("x,y\ninf,1\n", encoding="utf-8")
            with self.assertRaisesRegex(DataError, "non-finite"):
                load_plot_data(
                    {
                        "kind": "scatter",
                        "data": {"path": "xy.csv"},
                        "mapping": {"x": "x", "y": "y"},
                    },
                    path,
                )


if __name__ == "__main__":
    unittest.main()
