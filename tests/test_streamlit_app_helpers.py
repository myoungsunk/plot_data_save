from __future__ import annotations

import unittest

from streamlit_app import (
    COLOR_OPTION_CUSTOM,
    format_color_option,
    join_color_sequence,
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


if __name__ == "__main__":
    unittest.main()
