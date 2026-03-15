from __future__ import annotations

import copy
from pathlib import Path

try:
    import streamlit as st
except ModuleNotFoundError as exc:  # pragma: no cover - only triggered without app dependencies
    raise SystemExit(
        "Streamlit is not installed. Run `pip install -r requirements.txt` and then `streamlit run streamlit_app.py`."
    ) from exc

from app.template_store import (
    FILTER_OPERATORS,
    FIGURE_PRESETS,
    LoadedTable,
    default_filter,
    default_template,
    ensure_template_shape,
    list_templates,
    load_csv_table,
    load_template,
    load_template_bytes,
    resize_panels,
    resize_slots,
    sanitize_filename,
    save_template,
    table_preview_rows,
    template_to_json_bytes,
)
from app.theme_engine import THEME_PRESETS, build_report_figure, export_figure_bytes, resolve_figure_dimensions


def init_state() -> None:
    if "template" not in st.session_state:
        st.session_state.template = default_template()
    if "slot_file_map" not in st.session_state:
        st.session_state.slot_file_map = {}


def load_selected_template(template_path: Path) -> None:
    st.session_state.template = load_template(template_path)
    st.session_state.slot_file_map = {}


def reset_template() -> None:
    st.session_state.template = default_template()
    st.session_state.slot_file_map = {}


def parse_limit_value(text: str | None) -> float | None:
    if text in (None, ""):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def build_slot_editor(template: dict, uploaded_names: list[str]) -> tuple[list[dict], dict[str, str]]:
    slot_count = st.number_input(
        "Data slot count",
        min_value=1,
        max_value=12,
        value=len(template["data_slots"]),
        step=1,
    )
    working_template = resize_slots(template, int(slot_count))
    slot_map = copy.deepcopy(st.session_state.slot_file_map)
    built_slots: list[dict] = []

    for index, slot in enumerate(working_template["data_slots"]):
        with st.expander(f"Slot {index + 1}: {slot['slot_id']}", expanded=index == 0):
            slot_id = st.text_input("Slot id", value=slot["slot_id"], key=f"slot_id_{index}")
            label = st.text_input("Label", value=slot["label"], key=f"slot_label_{index}")
            description = st.text_area("Description", value=slot.get("description", ""), key=f"slot_desc_{index}", height=68)
            selected_file = st.selectbox(
                "Mapped uploaded file",
                options=[""] + uploaded_names,
                index=([""] + uploaded_names).index(slot_map.get(slot["slot_id"], "")) if slot_map.get(slot["slot_id"], "") in uploaded_names else 0,
                key=f"slot_map_{index}",
            )
            built_slots.append(
                {
                    "slot_id": slot_id,
                    "label": label,
                    "description": description,
                }
            )
            slot_map[slot["slot_id"]] = selected_file

    rebuilt_template = ensure_template_shape({**working_template, "data_slots": built_slots})
    rebuilt_slot_map: dict[str, str] = {}
    for old_slot, new_slot in zip(working_template["data_slots"], rebuilt_template["data_slots"]):
        rebuilt_slot_map[new_slot["slot_id"]] = slot_map.get(old_slot["slot_id"], "")
    return rebuilt_template["data_slots"], rebuilt_slot_map


def choose_default(option_list: list[str], current: str) -> int:
    if current in option_list:
        return option_list.index(current)
    return 0


def panel_editor(template: dict, slot_tables: dict[str, LoadedTable]) -> list[dict]:
    panel_count = template["figure"]["rows"] * template["figure"]["cols"]
    working_template = resize_panels(template, panel_count)
    built_panels: list[dict] = []

    for index, panel in enumerate(working_template["panels"]):
        slot_ids = [slot["slot_id"] for slot in working_template["data_slots"]]
        selected_slot = panel["source_slot"] if panel["source_slot"] in slot_ids else slot_ids[0]
        table = slot_tables.get(selected_slot)
        columns = table.columns if table else []
        numeric_columns = table.numeric_columns if table else []
        chart_types = ["line", "scatter", "bar", "heatmap"]

        with st.expander(f"Panel {index + 1}: {panel['title']}", expanded=index == 0):
            col_a, col_b = st.columns(2)
            with col_a:
                title = st.text_input("Panel title", value=panel["title"], key=f"panel_title_{index}")
                chart_type = st.selectbox(
                    "Chart type",
                    options=chart_types,
                    index=choose_default(chart_types, panel["chart_type"]),
                    key=f"panel_chart_type_{index}",
                )
                source_slot = st.selectbox(
                    "Source slot",
                    options=slot_ids,
                    index=choose_default(slot_ids, selected_slot),
                    key=f"panel_slot_{index}",
                )
            with col_b:
                show_legend = st.checkbox("Show legend", value=panel.get("show_legend", True), key=f"panel_legend_{index}")
                xlabel = st.text_input("X label override", value=panel.get("xlabel", ""), key=f"panel_xlabel_{index}")
                ylabel = st.text_input("Y label override", value=panel.get("ylabel", ""), key=f"panel_ylabel_{index}")

            bound_table = slot_tables.get(source_slot)
            bound_columns = bound_table.columns if bound_table else []
            bound_numeric = bound_table.numeric_columns if bound_table else []
            if not bound_table:
                st.info("Map a CSV file to this panel's source slot to configure columns.")

            x_column = st.selectbox(
                "X column",
                options=[""] + bound_columns,
                index=choose_default([""] + bound_columns, panel.get("x", "")),
                key=f"panel_x_{index}",
            )

            if chart_type == "heatmap":
                heatmap_y = st.selectbox(
                    "Heatmap row column",
                    options=[""] + bound_columns,
                    index=choose_default([""] + bound_columns, panel.get("heatmap_y", "")),
                    key=f"panel_heatmap_y_{index}",
                )
                value_column = st.selectbox(
                    "Heatmap value column",
                    options=[""] + bound_numeric,
                    index=choose_default([""] + bound_numeric, panel.get("value", "")),
                    key=f"panel_value_{index}",
                )
                y_columns: list[str] = []
                series_column = ""
            else:
                y_columns = st.multiselect(
                    "Y column(s)",
                    options=bound_columns,
                    default=[column for column in panel.get("y", []) if column in bound_columns],
                    key=f"panel_y_{index}",
                )
                series_column = st.selectbox(
                    "Optional grouping column",
                    options=[""] + bound_columns,
                    index=choose_default([""] + bound_columns, panel.get("series", "")),
                    key=f"panel_series_{index}",
                )
                heatmap_y = ""
                value_column = ""

            st.caption("Optional row filters")
            filter_count = st.number_input(
                "Number of filters",
                min_value=0,
                max_value=4,
                value=len(panel.get("filters", [])),
                step=1,
                key=f"panel_filter_count_{index}",
            )
            filters: list[dict] = []
            for filter_index in range(int(filter_count)):
                default_rule = panel.get("filters", [default_filter()] * int(filter_count))
                current_rule = default_rule[filter_index] if filter_index < len(default_rule) else default_filter()
                filter_cols = st.columns(3)
                with filter_cols[0]:
                    filter_column = st.selectbox(
                        "Column",
                        options=[""] + bound_columns,
                        index=choose_default([""] + bound_columns, current_rule.get("column", "")),
                        key=f"panel_filter_column_{index}_{filter_index}",
                    )
                with filter_cols[1]:
                    filter_operator = st.selectbox(
                        "Operator",
                        options=FILTER_OPERATORS,
                        index=choose_default(FILTER_OPERATORS, current_rule.get("operator", "eq")),
                        key=f"panel_filter_operator_{index}_{filter_index}",
                    )
                with filter_cols[2]:
                    filter_value = st.text_input(
                        "Value",
                        value=current_rule.get("value", ""),
                        key=f"panel_filter_value_{index}_{filter_index}",
                    )
                filters.append({"column": filter_column, "operator": filter_operator, "value": filter_value})

            style_defaults = panel.get("style_overrides", {})
            style_cols = st.columns(4)
            with style_cols[0]:
                line_width = st.number_input(
                    "Line width",
                    min_value=0.2,
                    max_value=5.0,
                    value=float(style_defaults.get("line_width", 1.2)),
                    step=0.1,
                    key=f"panel_line_width_{index}",
                )
            with style_cols[1]:
                marker_size = st.number_input(
                    "Marker size",
                    min_value=1.0,
                    max_value=16.0,
                    value=float(style_defaults.get("marker_size", 4.0)),
                    step=0.5,
                    key=f"panel_marker_size_{index}",
                )
            with style_cols[2]:
                marker = st.selectbox(
                    "Marker",
                    options=["o", "s", "^", "D", "v", "P", "X", "*", "."],
                    index=choose_default(["o", "s", "^", "D", "v", "P", "X", "*", "."], str(style_defaults.get("marker", "o"))),
                    key=f"panel_marker_{index}",
                )
            with style_cols[3]:
                cmap = st.text_input(
                    "Heatmap colormap",
                    value=str(style_defaults.get("cmap", "viridis")),
                    key=f"panel_cmap_{index}",
                )

            limit_cols = st.columns(4)
            with limit_cols[0]:
                x_min = st.text_input("X min", value="" if panel["xlim"]["min"] is None else str(panel["xlim"]["min"]), key=f"panel_xmin_{index}")
            with limit_cols[1]:
                x_max = st.text_input("X max", value="" if panel["xlim"]["max"] is None else str(panel["xlim"]["max"]), key=f"panel_xmax_{index}")
            with limit_cols[2]:
                y_min = st.text_input("Y min", value="" if panel["ylim"]["min"] is None else str(panel["ylim"]["min"]), key=f"panel_ymin_{index}")
            with limit_cols[3]:
                y_max = st.text_input("Y max", value="" if panel["ylim"]["max"] is None else str(panel["ylim"]["max"]), key=f"panel_ymax_{index}")

            show_colorbar = st.checkbox(
                "Show heatmap colorbar",
                value=bool(style_defaults.get("show_colorbar", True)),
                key=f"panel_colorbar_{index}",
            )

            built_panels.append(
                {
                    "panel_id": panel["panel_id"],
                    "title": title,
                    "chart_type": chart_type,
                    "source_slot": source_slot,
                    "x": x_column,
                    "y": y_columns,
                    "series": series_column,
                    "heatmap_y": heatmap_y,
                    "value": value_column,
                    "aggregation": "mean",
                    "filters": filters,
                    "xlabel": xlabel,
                    "ylabel": ylabel,
                    "xlim": {"min": parse_limit_value(x_min), "max": parse_limit_value(x_max)},
                    "ylim": {"min": parse_limit_value(y_min), "max": parse_limit_value(y_max)},
                    "show_legend": show_legend,
                    "style_overrides": {
                        "line_width": line_width,
                        "marker_size": marker_size,
                        "marker": marker,
                        "cmap": cmap,
                        "show_colorbar": show_colorbar,
                    },
                }
            )
    return built_panels


def load_uploaded_tables() -> dict[str, LoadedTable]:
    uploaded_files = st.file_uploader("Upload CSV files", type=["csv"], accept_multiple_files=True)
    tables: dict[str, LoadedTable] = {}
    if uploaded_files:
        for file in uploaded_files:
            table = load_csv_table(file, name=file.name)
            tables[file.name] = table
    return tables


def main() -> None:
    st.set_page_config(page_title="MPFC Paper-Style CSV Plotter", layout="wide")
    init_state()

    st.title("MPFC Paper-Style CSV Plotter")
    st.caption("Upload CSVs, map them to logical slots, configure panels, and export paper-ready figures.")

    with st.sidebar:
        st.header("Template Library")
        template_paths = list_templates()
        template_labels = [""] + [path.stem for path in template_paths]
        selected_label = st.selectbox("Saved templates", options=template_labels, index=0)
        if st.button("Load saved template", use_container_width=True):
            if selected_label:
                selected_path = next(path for path in template_paths if path.stem == selected_label)
                load_selected_template(selected_path)
                st.rerun()
        imported_template = st.file_uploader("Import template JSON", type=["json"], key="template_import")
        if st.button("Load imported template", use_container_width=True):
            if imported_template is not None:
                st.session_state.template = load_template_bytes(imported_template.read())
                st.session_state.slot_file_map = {}
                st.rerun()
        if st.button("Reset to blank template", use_container_width=True):
            reset_template()
            st.rerun()

    template = ensure_template_shape(st.session_state.template)
    uploaded_tables = load_uploaded_tables()
    uploaded_names = list(uploaded_tables.keys())

    with st.expander("Figure Settings", expanded=True):
        figure = copy.deepcopy(template["figure"])
        config_cols = st.columns(4)
        with config_cols[0]:
            template_name = st.text_input("Template name", value=template.get("name", "untitled_template"))
            theme_id = st.selectbox(
                "Theme preset",
                options=list(THEME_PRESETS.keys()),
                index=choose_default(list(THEME_PRESETS.keys()), template.get("theme", "mpfc_paper_v1")),
            )
        with config_cols[1]:
            preset_id = st.selectbox(
                "Figure preset",
                options=list(FIGURE_PRESETS.keys()),
                index=choose_default(list(FIGURE_PRESETS.keys()), figure.get("preset", "single-column")),
            )
            rows = st.number_input("Rows", min_value=1, max_value=6, value=int(figure.get("rows", 1)), step=1)
        with config_cols[2]:
            cols = st.number_input("Columns", min_value=1, max_value=6, value=int(figure.get("cols", 1)), step=1)
            auto_height = st.checkbox("Auto height from preset", value=bool(figure.get("auto_height", True)))
        with config_cols[3]:
            dpi = st.number_input("Raster export DPI", min_value=72, max_value=1200, value=int(figure.get("dpi", 300)), step=1)
            figure_title = st.text_input("Figure title", value=figure.get("title", ""))

        width_mm, auto_height_mm = resolve_figure_dimensions({**figure, "preset": preset_id, "rows": rows, "cols": cols, "auto_height": True})
        size_cols = st.columns(2)
        with size_cols[0]:
            manual_width = st.number_input("Width (mm)", min_value=40.0, max_value=300.0, value=float(width_mm), step=1.0)
        with size_cols[1]:
            manual_height = st.number_input(
                "Height (mm)",
                min_value=40.0,
                max_value=400.0,
                value=float(auto_height_mm if auto_height else figure.get("height_mm", auto_height_mm)),
                step=1.0,
                disabled=auto_height,
            )

        template["name"] = template_name
        template["theme"] = theme_id
        template["figure"] = {
            "title": figure_title,
            "preset": preset_id,
            "rows": int(rows),
            "cols": int(cols),
            "width_mm": float(manual_width),
            "height_mm": float(auto_height_mm if auto_height else manual_height),
            "auto_height": bool(auto_height),
            "dpi": int(dpi),
        }
        template = resize_panels(template, template["figure"]["rows"] * template["figure"]["cols"])

    slot_cols = st.columns([2, 1])
    with slot_cols[0]:
        st.subheader("Data Slots")
    with slot_cols[1]:
        st.caption("Map uploaded files to reusable slot ids")
    slots, slot_file_map = build_slot_editor(template, uploaded_names)
    template["data_slots"] = slots
    st.session_state.slot_file_map = slot_file_map

    slot_tables: dict[str, LoadedTable] = {}
    for slot in template["data_slots"]:
        mapped_name = slot_file_map.get(slot["slot_id"], "")
        if mapped_name and mapped_name in uploaded_tables:
            slot_tables[slot["slot_id"]] = uploaded_tables[mapped_name]

    if uploaded_tables:
        with st.expander("Uploaded Dataset Preview", expanded=False):
            preview_name = st.selectbox("Preview uploaded CSV", options=list(uploaded_tables.keys()))
            preview_table = uploaded_tables[preview_name]
            st.write(f"Columns: {', '.join(preview_table.columns)}")
            st.dataframe(table_preview_rows(preview_table, limit=8), use_container_width=True)

    st.subheader("Panels")
    template["panels"] = panel_editor(template, slot_tables)
    template = ensure_template_shape(template)
    st.session_state.template = template

    render_result = build_report_figure(template, slot_tables)
    if render_result.messages:
        for message in render_result.messages:
            st.warning(message)

    st.subheader("Preview")
    st.pyplot(render_result.figure, use_container_width=False)

    export_cols = st.columns(3)
    for column, fmt in zip(export_cols, ["png", "svg", "pdf"]):
        with column:
            payload = export_figure_bytes(render_result.figure, fmt, dpi=template["figure"]["dpi"])
            st.download_button(
                f"Download {fmt.upper()}",
                data=payload,
                file_name=f"{sanitize_filename(template['name'])}_report.{fmt}",
                mime=f"image/{fmt}" if fmt != "pdf" else "application/pdf",
                use_container_width=True,
            )

    template_json = template_to_json_bytes(template)
    save_cols = st.columns(2)
    with save_cols[0]:
        if st.button("Save template to templates/", use_container_width=True):
            path = save_template(template, template["name"])
            st.success(f"Saved template to {path.name}")
    with save_cols[1]:
        st.download_button(
            "Download template JSON",
            data=template_json,
            file_name=f"{sanitize_filename(template['name'])}.json",
            mime="application/json",
            use_container_width=True,
        )

    st.caption("Bundled figure presets: single-column, double-column, stacked-column.")


if __name__ == "__main__":
    main()

