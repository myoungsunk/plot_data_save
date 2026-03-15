from __future__ import annotations

import unittest
from pathlib import Path

from app.template_store import load_csv_table, load_template
from app.theme_engine import build_report_figure, export_figure_bytes, resolve_figure_dimensions, theme_rc_params


ROOT = Path(__file__).resolve().parent.parent


class ThemeEngineTests(unittest.TestCase):
    def test_theme_rc_params_include_serif_defaults(self) -> None:
        rc = theme_rc_params("mpfc_paper_v1")
        self.assertEqual(rc["font.family"], "serif")
        self.assertIn("Times New Roman", rc["font.serif"])

    def test_figure_presets_resolve_dimensions(self) -> None:
        width_mm, height_mm = resolve_figure_dimensions({"preset": "double-column", "rows": 2, "cols": 2, "auto_height": True})
        self.assertAlmostEqual(width_mm, 178.0)
        self.assertGreater(height_mm, 100.0)

    def test_general_demo_renders_and_exports(self) -> None:
        template = load_template(ROOT / "templates" / "general_demo.json")
        slot_tables = {
            "line_slot": load_csv_table(ROOT / "sample_data" / "line_demo.csv"),
            "bar_slot": load_csv_table(ROOT / "sample_data" / "bar_demo.csv"),
            "heatmap_slot": load_csv_table(ROOT / "sample_data" / "heatmap_demo.csv"),
        }
        result = build_report_figure(template, slot_tables)
        self.assertEqual(result.messages, [])
        for fmt in ["png", "svg", "pdf"]:
            payload = export_figure_bytes(result.figure, fmt, dpi=300)
            self.assertGreater(len(payload), 100)
        result.figure.clf()

    def test_rf_demo_renders(self) -> None:
        template = load_template(ROOT / "templates" / "rf_report_demo.json")
        slot_tables = {
            "cp_slot": load_csv_table(ROOT / "sample_data" / "rf" / "cp_meas_excerpt.csv"),
            "coupler_mag_slot": load_csv_table(ROOT / "sample_data" / "rf" / "coupler_mag_excerpt.csv"),
            "coupler_phase_slot": load_csv_table(ROOT / "sample_data" / "rf" / "coupler_phase_excerpt.csv"),
            "radiation_slot": load_csv_table(ROOT / "sample_data" / "rf" / "cp_radiation_rhcp_phi0_excerpt.csv"),
        }
        result = build_report_figure(template, slot_tables)
        self.assertEqual(result.messages, [])
        png_payload = export_figure_bytes(result.figure, "png", dpi=300)
        self.assertGreater(len(png_payload), 100)
        result.figure.clf()


if __name__ == "__main__":
    unittest.main()

