from __future__ import annotations

import unittest

from streamlit_app import (
    COLOR_OPTION_CUSTOM,
    FONT_OPTION_CUSTOM,
    format_font_option,
    format_color_option,
    join_color_sequence,
    recommend_grid_steps,
    recommended_minor_divisions,
    resolve_font_selection,
    resolve_color_selection,
    split_color_sequence,
)


class StreamlitAppHelperTests(unittest.TestCase):
    def test_split_and_join_color_sequence(self) -> None:
        colors = split_color_sequence("#000000, #ff0000, yellow")
        self.assertEqual(colors, ["#000000", "#ff0000", "yellow"])
        self.assertEqual(join_color_sequence(colors), "#000000, #ff0000, yellow")

    def test_resolve_color_selection_supports_presets_and_custom(self) -> None:
        preset_option, preset_custom = resolve_color_selection("#0000ff")
        self.assertEqual(preset_option, "#0000ff")
        self.assertEqual(preset_custom, "")

        custom_option, custom_value = resolve_color_selection("yellow")
        self.assertEqual(custom_option, COLOR_OPTION_CUSTOM)
        self.assertEqual(custom_value, "yellow")

    def test_format_color_option_labels(self) -> None:
        self.assertEqual(format_color_option("", "Theme default"), "Theme default")
        self.assertEqual(format_color_option(COLOR_OPTION_CUSTOM), "Custom")
        self.assertIn("Black", format_color_option("#000000"))

    def test_font_selection_supports_presets_and_custom(self) -> None:
        preset_option, preset_custom = resolve_font_selection("Arial, Helvetica, DejaVu Sans")
        self.assertEqual(preset_option, "Arial, Helvetica, DejaVu Sans")
        self.assertEqual(preset_custom, "")

        custom_option, custom_value = resolve_font_selection("Nanum Gothic, Arial")
        self.assertEqual(custom_option, FONT_OPTION_CUSTOM)
        self.assertEqual(custom_value, "Nanum Gothic, Arial")
        self.assertEqual(format_font_option(FONT_OPTION_CUSTOM), "Custom")

    def test_grid_recommendations_use_nice_steps(self) -> None:
        self.assertEqual(recommend_grid_steps([3.0, 3.2, 3.4, 3.6]), ["0.2", "0.1"])
        self.assertEqual(recommended_minor_divisions(list(range(5))), 2)
        self.assertEqual(recommended_minor_divisions(list(range(20))), 4)
        self.assertEqual(recommended_minor_divisions(list(range(40))), 5)


if __name__ == "__main__":
    unittest.main()
