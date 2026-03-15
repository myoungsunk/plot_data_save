from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.template_store import (
    autofill_template_from_tables,
    default_template,
    ensure_template_shape,
    humanize_filename,
    infer_x_column,
    list_templates,
    load_csv_table,
    load_template,
    resize_panels,
    resize_slots,
    save_template,
)


ROOT = Path(__file__).resolve().parent.parent


class TemplateStoreTests(unittest.TestCase):
    def test_default_template_is_normalized(self) -> None:
        template = ensure_template_shape(default_template())
        self.assertEqual(template["theme"], "mpfc_paper_v1")
        self.assertEqual(template["figure"]["rows"], 1)
        self.assertEqual(len(template["data_slots"]), 1)
        self.assertEqual(len(template["panels"]), 1)
        self.assertIsNone(template["panels"][0]["style_overrides"]["line_width"])
        self.assertEqual(template["panels"][0]["style_overrides"]["marker"], "")

    def test_resize_helpers_keep_template_consistent(self) -> None:
        template = ensure_template_shape(default_template())
        template = resize_slots(template, 3)
        template["figure"]["rows"] = 2
        template["figure"]["cols"] = 2
        template = resize_panels(template, 4)
        self.assertEqual(len(template["data_slots"]), 3)
        self.assertEqual(len(template["panels"]), 4)

    def test_save_and_load_roundtrip(self) -> None:
        template = ensure_template_shape(default_template())
        with tempfile.TemporaryDirectory() as temp_dir:
            path = save_template(template, "roundtrip", Path(temp_dir))
            loaded = load_template(path)
            self.assertEqual(loaded["name"], "roundtrip")
            self.assertTrue(list_templates(Path(temp_dir)))

    def test_csv_loader_inferrs_numeric_columns(self) -> None:
        table = load_csv_table(ROOT / "sample_data" / "line_demo.csv")
        self.assertIn("frequency_ghz", table.numeric_columns)
        self.assertIn("measured_db", table.numeric_columns)
        self.assertGreater(len(table.rows), 1)

    def test_infer_x_column_prefers_frequency_like_fields(self) -> None:
        table = load_csv_table(ROOT / "sample_data" / "line_demo.csv")
        self.assertEqual(infer_x_column(table), "frequency_ghz")

    def test_autofill_single_upload_builds_one_panel_and_slot(self) -> None:
        table = load_csv_table(ROOT / "sample_data" / "line_demo.csv")
        template, slot_map = autofill_template_from_tables({"line_demo.csv": table}, default_template())
        self.assertEqual(template["figure"]["rows"], 1)
        self.assertEqual(template["figure"]["cols"], 1)
        self.assertEqual(len(template["data_slots"]), 1)
        self.assertEqual(len(template["panels"]), 1)
        self.assertEqual(template["panels"][0]["source_slot"], template["data_slots"][0]["slot_id"])
        self.assertEqual(template["panels"][0]["x"], "frequency_ghz")
        self.assertIn("measured_db", template["panels"][0]["y"])
        self.assertEqual(slot_map[template["data_slots"][0]["slot_id"]], "line_demo.csv")
        self.assertEqual(template["figure"]["title"], "line demo")

    def test_humanize_filename_uses_stem(self) -> None:
        self.assertEqual(humanize_filename("CP_MEAS.csv"), "CP MEAS")


if __name__ == "__main__":
    unittest.main()
