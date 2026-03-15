from __future__ import annotations

import copy
import csv
import io
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - exercised in dependency-light environments
    pd = None


TEMPLATE_VERSION = "1.0"
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

FIGURE_PRESETS: dict[str, dict[str, float | str]] = {
    "single-column": {
        "label": "Single Column",
        "width_mm": 85.0,
        "base_height_mm": 65.0,
        "row_height_mm": 52.0,
    },
    "double-column": {
        "label": "Double Column",
        "width_mm": 178.0,
        "base_height_mm": 70.0,
        "row_height_mm": 54.0,
    },
    "stacked-column": {
        "label": "Stacked Column",
        "width_mm": 85.0,
        "base_height_mm": 90.0,
        "row_height_mm": 72.0,
    },
}

FILTER_OPERATORS = [
    "eq",
    "neq",
    "contains",
    "gt",
    "gte",
    "lt",
    "lte",
]


@dataclass
class LoadedTable:
    name: str
    columns: list[str]
    rows: list[dict[str, Any]]
    numeric_columns: list[str]
    categorical_columns: list[str]


def default_figure_config() -> dict[str, Any]:
    return {
        "title": "",
        "preset": "single-column",
        "rows": 1,
        "cols": 1,
        "width_mm": FIGURE_PRESETS["single-column"]["width_mm"],
        "height_mm": 90.0,
        "auto_height": True,
        "dpi": 300,
        "font_family_override": "",
    }


def default_slot(index: int) -> dict[str, Any]:
    return {
        "slot_id": f"slot_{index + 1}",
        "label": f"Dataset {index + 1}",
        "description": "",
    }


def default_filter() -> dict[str, Any]:
    return {
        "column": "",
        "operator": "eq",
        "value": "",
    }


def default_panel(index: int, slot_id: str = "slot_1") -> dict[str, Any]:
    return {
        "panel_id": f"panel_{index + 1}",
        "title": f"Panel {index + 1}",
        "chart_type": "line",
        "source_slot": slot_id,
        "x": "",
        "y": [],
        "series": "",
        "heatmap_y": "",
        "value": "",
        "aggregation": "mean",
        "filters": [],
        "xlabel": "",
        "ylabel": "",
        "xlim": {"min": None, "max": None},
        "ylim": {"min": None, "max": None},
        "show_legend": True,
        "style_overrides": {
            "line_width": None,
            "marker_size": None,
            "marker": "",
            "marker_every": 1,
            "line_colors": "",
            "marker_colors": "",
            "cmap": "viridis",
            "show_colorbar": True,
            "show_major_grid": True,
            "show_minor_grid": True,
            "major_grid_color": "",
            "minor_grid_color": "",
            "major_grid_linestyle": "",
            "minor_grid_linestyle": "",
        },
    }


def default_template() -> dict[str, Any]:
    return {
        "version": TEMPLATE_VERSION,
        "name": "untitled_template",
        "theme": "mpfc_paper_v1",
        "figure": default_figure_config(),
        "data_slots": [default_slot(0)],
        "panels": [default_panel(0)],
    }


def sanitize_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", name.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "template"


def ensure_unique_slot_ids(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    fixed: list[dict[str, Any]] = []
    for index, slot in enumerate(slots):
        base = sanitize_filename(str(slot.get("slot_id", "") or f"slot_{index + 1}"))
        candidate = base
        suffix = 2
        while candidate in seen:
            candidate = f"{base}_{suffix}"
            suffix += 1
        seen.add(candidate)
        item = copy.deepcopy(slot)
        item["slot_id"] = candidate
        item.setdefault("label", candidate.replace("_", " ").title())
        item.setdefault("description", "")
        fixed.append(item)
    return fixed


def resize_slots(template: dict[str, Any], slot_count: int) -> dict[str, Any]:
    slot_count = max(1, int(slot_count))
    updated = copy.deepcopy(template or default_template())
    slots = updated["data_slots"][:slot_count]
    while len(slots) < slot_count:
        slots.append(default_slot(len(slots)))
    updated["data_slots"] = ensure_unique_slot_ids(slots)
    valid_ids = [slot["slot_id"] for slot in updated["data_slots"]]
    fallback = valid_ids[0]
    panels = updated.get("panels") or [default_panel(0, slot_id=fallback)]
    updated["panels"] = [ensure_panel_shape(panel, index, fallback) for index, panel in enumerate(panels)]
    for panel in updated["panels"]:
        if panel.get("source_slot") not in valid_ids:
            panel["source_slot"] = fallback
    return updated


def resize_panels(template: dict[str, Any], panel_count: int) -> dict[str, Any]:
    panel_count = max(1, int(panel_count))
    updated = copy.deepcopy(template or default_template())
    slots = ensure_unique_slot_ids(updated.get("data_slots") or [default_slot(0)])
    updated["data_slots"] = slots
    slot_id = updated["data_slots"][0]["slot_id"]
    panels = list(updated.get("panels") or [])[:panel_count]
    while len(panels) < panel_count:
        panels.append(default_panel(len(panels), slot_id=slot_id))
    updated["panels"] = [ensure_panel_shape(panel, index, slot_id) for index, panel in enumerate(panels)]
    return updated


def ensure_panel_shape(panel: dict[str, Any], index: int, fallback_slot: str) -> dict[str, Any]:
    normalized = copy.deepcopy(default_panel(index, slot_id=fallback_slot))
    normalized.update(copy.deepcopy(panel))
    normalized["panel_id"] = normalized.get("panel_id") or f"panel_{index + 1}"
    normalized["title"] = normalized.get("title") or f"Panel {index + 1}"
    normalized["source_slot"] = normalized.get("source_slot") or fallback_slot
    normalized["y"] = list(normalized.get("y") or [])
    normalized["filters"] = [normalize_filter(rule) for rule in normalized.get("filters", [])]
    normalized["xlim"] = normalize_limits(normalized.get("xlim"))
    normalized["ylim"] = normalize_limits(normalized.get("ylim"))
    overrides = copy.deepcopy(default_panel(index, fallback_slot)["style_overrides"])
    overrides.update(copy.deepcopy(normalized.get("style_overrides") or {}))
    normalized["style_overrides"] = overrides
    return normalized


def normalize_filter(rule: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(default_filter())
    normalized.update(copy.deepcopy(rule or {}))
    if normalized["operator"] not in FILTER_OPERATORS:
        normalized["operator"] = "eq"
    normalized["column"] = str(normalized.get("column") or "")
    normalized["value"] = "" if normalized.get("value") is None else str(normalized["value"])
    return normalized


def normalize_limits(limits: Any) -> dict[str, Any]:
    if isinstance(limits, dict):
        return {
            "min": parse_optional_float(limits.get("min")),
            "max": parse_optional_float(limits.get("max")),
        }
    if isinstance(limits, (list, tuple)) and len(limits) == 2:
        return {"min": parse_optional_float(limits[0]), "max": parse_optional_float(limits[1])}
    return {"min": None, "max": None}


def ensure_template_shape(template: dict[str, Any]) -> dict[str, Any]:
    normalized = copy.deepcopy(default_template())
    if template:
        normalized.update(copy.deepcopy(template))
    normalized["version"] = str(normalized.get("version") or TEMPLATE_VERSION)
    normalized["name"] = str(normalized.get("name") or "untitled_template")
    figure = copy.deepcopy(default_figure_config())
    figure.update(copy.deepcopy(normalized.get("figure") or {}))
    figure["rows"] = max(1, int(figure.get("rows", 1)))
    figure["cols"] = max(1, int(figure.get("cols", 1)))
    figure["dpi"] = max(72, int(figure.get("dpi", 300)))
    figure["preset"] = figure.get("preset") or "single-column"
    figure["width_mm"] = float(figure.get("width_mm") or FIGURE_PRESETS["single-column"]["width_mm"])
    figure["height_mm"] = float(figure.get("height_mm") or 90.0)
    figure["auto_height"] = bool(figure.get("auto_height", True))
    normalized["figure"] = figure

    slots = normalized.get("data_slots") or [default_slot(0)]
    normalized["data_slots"] = ensure_unique_slot_ids(slots)
    fallback_slot = normalized["data_slots"][0]["slot_id"]
    panels = normalized.get("panels") or [default_panel(0, slot_id=fallback_slot)]
    panel_target = normalized["figure"]["rows"] * normalized["figure"]["cols"]
    trimmed_panels = list(panels)[:panel_target]
    while len(trimmed_panels) < panel_target:
        trimmed_panels.append(default_panel(len(trimmed_panels), slot_id=fallback_slot))
    normalized["panels"] = [ensure_panel_shape(panel, index, fallback_slot) for index, panel in enumerate(trimmed_panels)]
    for panel in normalized["panels"]:
        if panel.get("source_slot") not in {slot["slot_id"] for slot in normalized["data_slots"]}:
            panel["source_slot"] = fallback_slot
    return normalized


def template_to_json_bytes(template: dict[str, Any]) -> bytes:
    payload = ensure_template_shape(template)
    return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")


def save_template(template: dict[str, Any], name: str, directory: Path | None = None) -> Path:
    directory = directory or TEMPLATES_DIR
    directory.mkdir(parents=True, exist_ok=True)
    filename = sanitize_filename(name)
    if not filename.endswith(".json"):
        filename = f"{filename}.json"
    payload = ensure_template_shape(template)
    payload["name"] = Path(filename).stem
    path = directory / filename
    path.write_bytes(template_to_json_bytes(payload))
    return path


def load_template(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_text(encoding="utf-8")
    return ensure_template_shape(json.loads(raw))


def load_template_bytes(data: bytes) -> dict[str, Any]:
    return ensure_template_shape(json.loads(data.decode("utf-8")))


def list_templates(directory: Path | None = None) -> list[Path]:
    directory = directory or TEMPLATES_DIR
    if not directory.exists():
        return []
    return sorted(directory.glob("*.json"))


def parse_optional_float(value: Any) -> float | None:
    if value in (None, "", "None"):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(parsed):
        return None
    return parsed


def parse_scalar(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (int, float, bool)):
        return value
    text = str(value).strip()
    if text == "":
        return None
    try:
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        if any(token in text for token in [".", "e", "E"]):
            number = float(text)
            return None if math.isnan(number) else number
        return int(text)
    except ValueError:
        return text


def _normalized_headers(headers: list[str | None]) -> list[str]:
    normalized: list[str] = []
    seen: dict[str, int] = {}
    for index, header in enumerate(headers):
        candidate = str(header or "").strip()
        if not candidate:
            candidate = f"unnamed_{index + 1}"
        count = seen.get(candidate, 0)
        seen[candidate] = count + 1
        if count:
            candidate = f"{candidate}_{count + 1}"
        normalized.append(candidate)
    return normalized


def _rows_from_pandas_frame(dataframe: Any, name: str) -> LoadedTable:
    raw_headers = list(dataframe.columns)
    headers = _normalized_headers(raw_headers)
    dataframe = dataframe.copy()
    dataframe.columns = headers
    records = dataframe.where(dataframe.notna(), None).to_dict(orient="records")
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.append({key: parse_scalar(value) for key, value in record.items()})
    numeric_columns, categorical_columns = infer_column_types(rows, headers)
    return LoadedTable(
        name=name,
        columns=headers,
        rows=rows,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
    )


def _rows_from_csv_text(text: str, name: str) -> LoadedTable:
    reader = csv.DictReader(io.StringIO(text))
    raw_headers = list(reader.fieldnames or [])
    headers = _normalized_headers(raw_headers)
    rows: list[dict[str, Any]] = []
    for raw_row in reader:
        row: dict[str, Any] = {}
        for old_header, new_header in zip(raw_headers, headers):
            row[new_header] = parse_scalar(raw_row.get(old_header))
        rows.append(row)
    numeric_columns, categorical_columns = infer_column_types(rows, headers)
    return LoadedTable(
        name=name,
        columns=headers,
        rows=rows,
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
    )


def load_csv_table(source: Any, name: str | None = None) -> LoadedTable:
    dataset_name = name or getattr(source, "name", "dataset")
    if pd is not None:
        try:
            if hasattr(source, "seek"):
                source.seek(0)
            frame = pd.read_csv(source)
            if hasattr(source, "seek"):
                source.seek(0)
            return _rows_from_pandas_frame(frame, dataset_name)
        except Exception:
            if hasattr(source, "seek"):
                source.seek(0)

    if isinstance(source, (str, Path)):
        text = Path(source).read_text(encoding="utf-8-sig")
    else:
        raw = source.read()
        if hasattr(source, "seek"):
            source.seek(0)
        if isinstance(raw, bytes):
            text = raw.decode("utf-8-sig")
        else:
            text = str(raw)
    return _rows_from_csv_text(text, dataset_name)


def infer_column_types(rows: list[dict[str, Any]], columns: list[str]) -> tuple[list[str], list[str]]:
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []
    for column in columns:
        values = [row.get(column) for row in rows if row.get(column) is not None]
        if values and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            numeric_columns.append(column)
        else:
            categorical_columns.append(column)
    return numeric_columns, categorical_columns


def ordered_unique(values: list[Any], numeric: bool = False) -> list[Any]:
    unique: list[Any] = []
    seen: set[Any] = set()
    for value in values:
        marker = value
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(value)
    if numeric:
        return sorted(unique)
    return unique


def table_preview_rows(table: LoadedTable, limit: int = 5) -> list[dict[str, Any]]:
    return table.rows[:limit]


def humanize_filename(name: str) -> str:
    stem = Path(name).stem
    text = re.sub(r"[_\-]+", " ", stem).strip()
    return text or "Dataset"


def infer_x_column(table: LoadedTable) -> str:
    if not table.columns:
        return ""
    numeric = table.numeric_columns
    if not numeric:
        return table.columns[0]

    priorities = [
        "freq",
        "frequency",
        "time",
        "theta",
        "phi",
        "angle",
        "deg",
        "ghz",
        "hz",
        "index",
        "sample",
    ]
    scored: list[tuple[int, int, str]] = []
    for idx, column in enumerate(numeric):
        lower = column.lower()
        score = 0
        for rank, token in enumerate(priorities):
            if token in lower:
                score = max(score, 100 - rank)
        if idx == 0:
            score = max(score, 50)
        scored.append((score, -idx, column))
    scored.sort(reverse=True)
    return scored[0][2]


def suggest_panel_for_table(table: LoadedTable, slot_id: str, panel_index: int = 0) -> dict[str, Any]:
    panel = default_panel(panel_index, slot_id=slot_id)
    panel["source_slot"] = slot_id
    panel["title"] = humanize_filename(table.name)

    numeric = list(table.numeric_columns)
    categorical = [column for column in table.columns if column not in numeric]

    if len(numeric) >= 2:
        x_column = infer_x_column(table)
        y_candidates = [column for column in numeric if column != x_column]
        panel["chart_type"] = "line"
        panel["x"] = x_column
        panel["y"] = y_candidates[: min(2, len(y_candidates))]
        return panel

    if len(numeric) == 1 and categorical:
        panel["chart_type"] = "bar"
        panel["x"] = categorical[0]
        panel["y"] = [numeric[0]]
        return panel

    if len(table.columns) >= 2:
        panel["chart_type"] = "line"
        panel["x"] = table.columns[0]
        panel["y"] = [table.columns[1]]
        return panel

    if table.columns:
        panel["x"] = table.columns[0]
    return panel


def autofill_template_from_tables(
    uploaded_tables: dict[str, LoadedTable],
    template: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, str]]:
    if not uploaded_tables:
        base = ensure_template_shape(template or default_template())
        return base, {}

    base = ensure_template_shape(template or default_template())
    file_names = list(uploaded_tables.keys())
    slots: list[dict[str, Any]] = []
    slot_map: dict[str, str] = {}
    seen_ids: set[str] = set()

    for index, file_name in enumerate(file_names):
        candidate = sanitize_filename(Path(file_name).stem) or f"slot_{index + 1}"
        unique_id = candidate
        suffix = 2
        while unique_id in seen_ids:
            unique_id = f"{candidate}_{suffix}"
            suffix += 1
        seen_ids.add(unique_id)
        slots.append(
            {
                "slot_id": unique_id,
                "label": humanize_filename(file_name),
                "description": f"Auto-mapped from {file_name}",
            }
        )
        slot_map[unique_id] = file_name

    first_slot = slots[0]["slot_id"]
    first_table = uploaded_tables[file_names[0]]
    panel = suggest_panel_for_table(first_table, first_slot, panel_index=0)

    base["name"] = sanitize_filename(Path(file_names[0]).stem)
    base["figure"].update(
        {
            "rows": 1,
            "cols": 1,
            "preset": "single-column",
            "auto_height": True,
            "title": humanize_filename(file_names[0]),
        }
    )
    base["data_slots"] = slots
    base["panels"] = [panel]
    return ensure_template_shape(base), slot_map
