from __future__ import annotations

import unittest
from pathlib import Path

from app.template_store import default_template, load_csv_table, load_template
from app.theme_engine import build_report_figure, export_figure_bytes, get_theme, resolve_figure_dimensions, theme_rc_params


ROOT = Path(__file__).resolve().parent.parent


class ThemeEngineTests(unittest.TestCase):
    def test_theme_rc_params_include_serif_defaults(self) -> None:
        rc = theme_rc_params("mpfc_paper_v1")
        self.assertEqual(rc["font.family"], "serif")
        self.assertIn("Times New Roman", rc["font.serif"])
        override_rc = theme_rc_params("mpfc_paper_v1", "Arial, DejaVu Sans")
        self.assertEqual(override_rc["font.serif"][0], "Arial")
        dark_rc = theme_rc_params("mpfc_dark_v2")
        self.assertEqual(dark_rc["font.family"], "sans-serif")
        self.assertIn("Arial", dark_rc["font.sans-serif"])
        self.assertEqual(dark_rc["figure.facecolor"], "white")
        self.assertEqual(dark_rc["axes.facecolor"], "white")

    def test_figure_presets_resolve_dimensions(self) -> None:
        width_mm, height_mm = resolve_figure_dimensions({"preset": "double-column", "rows": 2, "cols": 2, "auto_height": True})
        self.assertAlmostEqual(width_mm, 178.0)
        self.assertGreater(height_mm, 100.0)

    def test_general_demo_renders_and_exports(self) -> None:
        template = load_template(ROOT / "templates" / "general_demo.json")
        template["figure"]["font_family_override"] = "Arial, DejaVu Sans"
        template["panels"][0]["style_overrides"].update(
            {
                "line_colors": "#112233,#445566",
                "marker_colors": "#778899,#aabbcc",
                "marker_every": 2,
                "show_major_grid": False,
                "show_minor_grid": False,
            }
        )
        slot_tables = {
            "line_slot": load_csv_table(ROOT / "sample_data" / "line_demo.csv"),
            "bar_slot": load_csv_table(ROOT / "sample_data" / "bar_demo.csv"),
            "heatmap_slot": load_csv_table(ROOT / "sample_data" / "heatmap_demo.csv"),
        }
        result = build_report_figure(template, slot_tables)
        self.assertEqual(result.messages, [])
        first_line = result.figure.axes[0].lines[0]
        self.assertEqual(first_line.get_color().lower(), "#112233")
        self.assertEqual(first_line.get_markerfacecolor().lower(), "#778899")
        self.assertEqual(first_line.get_markevery(), 2)
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

    def test_dark_theme_uses_white_page_and_black_leading_line(self) -> None:
        template = default_template()
        template["theme"] = "mpfc_dark_v2"
        template["data_slots"][0]["slot_id"] = "line_slot"
        template["panels"][0].update(
            {
                "title": "Dark Demo",
                "source_slot": "line_slot",
                "x": "frequency_ghz",
                "y": ["measured_db", "simulated_db"],
            }
        )
        template["panels"][0]["style_overrides"].update(
            {
                "line_width": None,
                "marker_size": None,
                "marker": "",
                "major_grid_linestyle": "",
                "minor_grid_linestyle": "",
            }
        )
        slot_tables = {
            "line_slot": load_csv_table(ROOT / "sample_data" / "line_demo.csv"),
        }
        result = build_report_figure(template, slot_tables)
        self.assertEqual(result.messages, [])
        theme = get_theme("mpfc_dark_v2")
        axis = result.figure.axes[0]
        first_line = axis.lines[0]
        self.assertEqual(first_line.get_color().lower(), theme["colors"][0].lower())
        self.assertEqual(first_line.get_marker(), theme["marker_cycle"][0])
        self.assertEqual(axis.get_facecolor(), (1.0, 1.0, 1.0, 1.0))
        self.assertEqual(result.figure.get_facecolor(), (1.0, 1.0, 1.0, 1.0))
        result.figure.clf()

    def test_numeric_grid_steps_apply_to_axes(self) -> None:
        template = default_template()
        template["data_slots"][0]["slot_id"] = "line_slot"
        template["panels"][0].update(
            {
                "title": "Grid Step Demo",
                "source_slot": "line_slot",
                "x": "frequency_ghz",
                "y": ["measured_db"],
            }
        )
        template["panels"][0]["style_overrides"].update(
            {
                "x_major_step": 0.2,
                "y_major_step": 2.0,
                "x_minor_divisions": 4,
                "y_minor_divisions": 2,
            }
        )
        slot_tables = {
            "line_slot": load_csv_table(ROOT / "sample_data" / "line_demo.csv"),
        }
        result = build_report_figure(template, slot_tables)
        axis = result.figure.axes[0]
        x_ticks = axis.get_xticks()
        y_ticks = axis.get_yticks()
        self.assertGreaterEqual(len(x_ticks), 3)
        self.assertGreaterEqual(len(y_ticks), 3)
        self.assertAlmostEqual(x_ticks[1] - x_ticks[0], 0.2, places=6)
        self.assertAlmostEqual(y_ticks[1] - y_ticks[0], 2.0, places=6)
        result.figure.clf()


if __name__ == "__main__":
    unittest.main()
