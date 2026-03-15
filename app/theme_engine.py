from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import AutoMinorLocator

from app.template_store import FIGURE_PRESETS, LoadedTable, ordered_unique


MPFC_COLORS = [
    "#000000",
    "#e41a1c",
    "#377eb8",
    "#4daf4a",
    "#984ea3",
    "#00cfe3",
    "#ff7f00",
    "#ffd500",
]
MPFC_MARKERS = ["s", "o", "^", "D", "v", "P", "X", "*"]

THEME_PRESETS: dict[str, dict[str, Any]] = {
    "mpfc_paper_v1": {
        "label": "MPFC Paper v1",
        "font_family": ["Times New Roman", "Times", "DejaVu Serif"],
        "font_sizes": {
            "figure_title": 10.0,
            "axes_title": 9.0,
            "axes_label": 9.0,
            "ticks": 8.0,
            "legend": 7.5,
        },
        "line_width": 1.2,
        "marker_size": 4.0,
        "spine_width": 0.8,
        "colors": MPFC_COLORS,
        "marker_cycle": MPFC_MARKERS,
        "grid": {
            "major_color": "#c9c9c9",
            "major_linewidth": 0.6,
            "major_linestyle": "-",
            "minor_color": "#dddddd",
            "minor_linewidth": 0.45,
            "minor_linestyle": ":",
        },
        "legend": {
            "facecolor": "white",
            "edgecolor": "black",
            "framealpha": 1.0,
            "borderpad": 0.25,
        },
        "axes_facecolor": "white",
        "figure_facecolor": "white",
    }
}


@dataclass
class RenderResult:
    figure: Any
    messages: list[str]


def mm_to_inches(mm: float) -> float:
    return mm / 25.4


def get_theme(theme_id: str) -> dict[str, Any]:
    return THEME_PRESETS.get(theme_id, THEME_PRESETS["mpfc_paper_v1"])


def parse_style_list(value: Any) -> list[str]:
    if value in (None, ""):
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple)):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def theme_rc_params(theme_id: str, font_family_override: str | list[str] | None = None) -> dict[str, Any]:
    theme = get_theme(theme_id)
    font_sizes = theme["font_sizes"]
    font_family = parse_style_list(font_family_override) or theme["font_family"]
    return {
        "font.family": "serif",
        "font.serif": font_family,
        "axes.labelsize": font_sizes["axes_label"],
        "axes.titlesize": font_sizes["axes_title"],
        "xtick.labelsize": font_sizes["ticks"],
        "ytick.labelsize": font_sizes["ticks"],
        "legend.fontsize": font_sizes["legend"],
        "axes.facecolor": theme["axes_facecolor"],
        "figure.facecolor": theme["figure_facecolor"],
        "axes.edgecolor": "black",
        "xtick.direction": "out",
        "ytick.direction": "out",
        "savefig.facecolor": "white",
        "savefig.bbox": "tight",
    }


def resolve_figure_dimensions(figure_config: dict[str, Any]) -> tuple[float, float]:
    preset_id = figure_config.get("preset", "single-column")
    preset = FIGURE_PRESETS.get(preset_id, FIGURE_PRESETS["single-column"])
    rows = max(1, int(figure_config.get("rows", 1)))
    width_mm = float(figure_config.get("width_mm") or preset["width_mm"])
    if figure_config.get("auto_height", True):
        height_mm = float(preset["base_height_mm"]) + float(preset["row_height_mm"]) * max(rows - 1, 0)
    else:
        height_mm = float(figure_config.get("height_mm") or preset["base_height_mm"])
    return width_mm, height_mm


def export_figure_bytes(figure: Any, fmt: str, dpi: int = 300) -> bytes:
    buffer = io.BytesIO()
    figure.savefig(buffer, format=fmt, dpi=dpi)
    buffer.seek(0)
    return buffer.read()


def build_report_figure(template: dict[str, Any], slot_tables: dict[str, LoadedTable]) -> RenderResult:
    theme = get_theme(template.get("theme", "mpfc_paper_v1"))
    figure_cfg = template["figure"]
    rows = max(1, int(figure_cfg["rows"]))
    cols = max(1, int(figure_cfg["cols"]))
    width_mm, height_mm = resolve_figure_dimensions(figure_cfg)
    messages: list[str] = []

    with plt.rc_context(
        theme_rc_params(template.get("theme", "mpfc_paper_v1"), figure_cfg.get("font_family_override", ""))
    ):
        figure, axes = plt.subplots(
            rows,
            cols,
            figsize=(mm_to_inches(width_mm), mm_to_inches(height_mm)),
            squeeze=False,
        )
        figure.patch.set_facecolor(theme["figure_facecolor"])
        figure.subplots_adjust(
            left=0.11,
            right=0.985,
            top=0.90 if figure_cfg.get("title") else 0.96,
            bottom=0.12,
            wspace=0.42,
            hspace=0.60,
        )

        if figure_cfg.get("title"):
            figure.suptitle(figure_cfg["title"], fontsize=theme["font_sizes"]["figure_title"])

        flat_axes = axes.ravel()
        for index, axis in enumerate(flat_axes):
            if index >= len(template["panels"]):
                axis.axis("off")
                continue
            panel = template["panels"][index]
            slot_id = panel.get("source_slot", "")
            table = slot_tables.get(slot_id)
            if table is None:
                render_placeholder(axis, f"No dataset mapped for slot '{slot_id}'")
                messages.append(f"{panel['panel_id']}: missing dataset for slot '{slot_id}'.")
                continue
            try:
                render_panel(axis, figure, table, panel, theme)
            except Exception as exc:  # pragma: no cover - UI safeguard
                render_placeholder(axis, str(exc))
                messages.append(f"{panel['panel_id']}: {exc}")
        return RenderResult(figure=figure, messages=messages)


def render_placeholder(axis: Any, message: str) -> None:
    axis.set_facecolor("white")
    axis.text(0.5, 0.5, message, ha="center", va="center", fontsize=9, transform=axis.transAxes)
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(True)


def render_panel(axis: Any, figure: Any, table: LoadedTable, panel: dict[str, Any], theme: dict[str, Any]) -> None:
    chart_type = panel.get("chart_type", "line")
    rows = apply_filters(table.rows, panel.get("filters", []))
    if not rows:
        raise ValueError("No rows remain after filtering.")

    if chart_type == "line":
        render_line_or_scatter(axis, rows, table, panel, theme, scatter=False)
    elif chart_type == "scatter":
        render_line_or_scatter(axis, rows, table, panel, theme, scatter=True)
    elif chart_type == "bar":
        render_bar(axis, rows, table, panel, theme)
    elif chart_type == "heatmap":
        render_heatmap(axis, figure, rows, table, panel)
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    apply_common_axis_style(axis, panel, theme)


def apply_filters(rows: list[dict[str, Any]], filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    filtered = rows
    for rule in filters:
        column = rule.get("column", "")
        operator = rule.get("operator", "eq")
        raw_value = rule.get("value", "")
        if not column:
            continue
        target = parse_filter_value(raw_value)

        def keep(row: dict[str, Any]) -> bool:
            candidate = row.get(column)
            if operator == "eq":
                return candidate == target
            if operator == "neq":
                return candidate != target
            if operator == "contains":
                return target is not None and str(target) in str(candidate)
            if candidate is None or target is None:
                return False
            if operator == "gt":
                return candidate > target
            if operator == "gte":
                return candidate >= target
            if operator == "lt":
                return candidate < target
            if operator == "lte":
                return candidate <= target
            return True

        filtered = [row for row in filtered if keep(row)]
    return filtered


def parse_filter_value(value: Any) -> Any:
    parsed = parse_optional_float(value)
    return parsed if parsed is not None else (None if value in (None, "") else str(value))


def build_series(rows: list[dict[str, Any]], panel: dict[str, Any]) -> list[tuple[str, list[Any], list[Any]]]:
    x_column = panel.get("x", "")
    y_columns = [column for column in panel.get("y", []) if column]
    series_column = panel.get("series", "")

    if not x_column:
        raise ValueError("Select an x column.")
    if not y_columns:
        raise ValueError("Select at least one y column.")

    if series_column and len(y_columns) == 1:
        y_column = y_columns[0]
        groups = ordered_unique([row.get(series_column) for row in rows if row.get(series_column) is not None], numeric=False)
        prepared: list[tuple[str, list[Any], list[Any]]] = []
        for group in groups:
            group_rows = [row for row in rows if row.get(series_column) == group]
            x_values = [row.get(x_column) for row in group_rows]
            y_values = [row.get(y_column) for row in group_rows]
            prepared.append((str(group), x_values, y_values))
        return prepared

    prepared = []
    for y_column in y_columns:
        x_values = [row.get(x_column) for row in rows]
        y_values = [row.get(y_column) for row in rows]
        prepared.append((str(y_column), x_values, y_values))
    return prepared


def render_line_or_scatter(
    axis: Any,
    rows: list[dict[str, Any]],
    table: LoadedTable,
    panel: dict[str, Any],
    theme: dict[str, Any],
    scatter: bool,
) -> None:
    series = build_series(rows, panel)
    overrides = panel.get("style_overrides", {})
    line_width = float(overrides.get("line_width", theme["line_width"]))
    marker_size = float(overrides.get("marker_size", theme["marker_size"]))
    forced_marker = overrides.get("marker") or None
    marker_every = max(1, int(overrides.get("marker_every", 1) or 1))
    line_colors = parse_style_list(overrides.get("line_colors", ""))
    marker_colors = parse_style_list(overrides.get("marker_colors", ""))

    for index, (label, x_values, y_values) in enumerate(series):
        points = [(x, y) for x, y in zip(x_values, y_values) if x is not None and y is not None]
        if not points:
            continue
        x_plot, y_plot = zip(*points)
        if all(isinstance(value, (int, float)) for value in x_plot):
            paired = sorted(zip(x_plot, y_plot), key=lambda item: item[0])
            x_plot, y_plot = zip(*paired)
        color = line_colors[index % len(line_colors)] if line_colors else theme["colors"][index % len(theme["colors"])]
        marker_color = marker_colors[index % len(marker_colors)] if marker_colors else color
        marker = forced_marker or theme["marker_cycle"][index % len(theme["marker_cycle"])]
        if scatter:
            if marker_every > 1:
                sampled_points = list(zip(x_plot, y_plot))[::marker_every]
                x_plot, y_plot = zip(*sampled_points)
            axis.scatter(
                x_plot,
                y_plot,
                s=marker_size**2,
                color=marker_color,
                marker=marker,
                label=label,
                linewidths=0.6,
            )
        else:
            axis.plot(
                x_plot,
                y_plot,
                color=color,
                marker=marker,
                linewidth=line_width,
                markersize=marker_size,
                markerfacecolor=marker_color,
                markeredgecolor=marker_color,
                markeredgewidth=0.0,
                markevery=marker_every if marker_every > 1 else None,
                label=label,
            )


def render_bar(axis: Any, rows: list[dict[str, Any]], table: LoadedTable, panel: dict[str, Any], theme: dict[str, Any]) -> None:
    x_column = panel.get("x", "")
    y_columns = [column for column in panel.get("y", []) if column]
    series_column = panel.get("series", "")
    if not x_column or not y_columns:
        raise ValueError("Bar charts require x and y selections.")

    overrides = panel.get("style_overrides", {})
    line_width = float(overrides.get("line_width", theme["line_width"]))
    line_colors = parse_style_list(overrides.get("line_colors", ""))

    if series_column and len(y_columns) == 1:
        y_column = y_columns[0]
        x_categories = ordered_unique([row.get(x_column) for row in rows], numeric=False)
        series_categories = ordered_unique([row.get(series_column) for row in rows], numeric=False)
        positions = np.arange(len(x_categories))
        width = 0.8 / max(len(series_categories), 1)
        for index, category in enumerate(series_categories):
            heights = []
            for x_category in x_categories:
                matches = [
                    row.get(y_column)
                    for row in rows
                    if row.get(x_column) == x_category and row.get(series_column) == category and row.get(y_column) is not None
                ]
                heights.append(float(np.mean(matches)) if matches else np.nan)
            offset = (index - (len(series_categories) - 1) / 2.0) * width
            axis.bar(
                positions + offset,
                heights,
                width=width,
                label=str(category),
                color=line_colors[index % len(line_colors)] if line_colors else theme["colors"][index % len(theme["colors"])],
                edgecolor="black",
                linewidth=line_width * 0.5,
            )
        axis.set_xticks(positions)
        axis.set_xticklabels([str(item) for item in x_categories], rotation=0)
        return

    x_labels = [row.get(x_column) for row in rows]
    positions = np.arange(len(x_labels))
    width = 0.8 / max(len(y_columns), 1)
    for index, y_column in enumerate(y_columns):
        heights = [row.get(y_column) for row in rows]
        offset = (index - (len(y_columns) - 1) / 2.0) * width
        axis.bar(
            positions + offset,
            heights,
            width=width,
            label=str(y_column),
            color=line_colors[index % len(line_colors)] if line_colors else theme["colors"][index % len(theme["colors"])],
            edgecolor="black",
            linewidth=line_width * 0.5,
        )
    axis.set_xticks(positions)
    axis.set_xticklabels([str(item) for item in x_labels], rotation=0)


def render_heatmap(axis: Any, figure: Any, rows: list[dict[str, Any]], table: LoadedTable, panel: dict[str, Any]) -> None:
    x_column = panel.get("x", "")
    y_column = panel.get("heatmap_y", "")
    value_column = panel.get("value", "")
    if not x_column or not y_column or not value_column:
        raise ValueError("Heatmaps require x, heatmap_y, and value columns.")

    x_numeric = x_column in table.numeric_columns
    y_numeric = y_column in table.numeric_columns
    x_categories = ordered_unique([row.get(x_column) for row in rows if row.get(x_column) is not None], numeric=x_numeric)
    y_categories = ordered_unique([row.get(y_column) for row in rows if row.get(y_column) is not None], numeric=y_numeric)
    if not x_categories or not y_categories:
        raise ValueError("Heatmap dimensions are empty.")

    x_index = {value: idx for idx, value in enumerate(x_categories)}
    y_index = {value: idx for idx, value in enumerate(y_categories)}
    matrix = np.full((len(y_categories), len(x_categories)), np.nan, dtype=float)
    buckets: dict[tuple[int, int], list[float]] = {}
    for row in rows:
        x_value = row.get(x_column)
        y_value = row.get(y_column)
        z_value = row.get(value_column)
        if x_value is None or y_value is None or z_value is None:
            continue
        key = (y_index[y_value], x_index[x_value])
        buckets.setdefault(key, []).append(float(z_value))
    for (row_idx, col_idx), values in buckets.items():
        matrix[row_idx, col_idx] = float(np.mean(values))

    overrides = panel.get("style_overrides", {})
    cmap = overrides.get("cmap", "viridis")
    image = axis.imshow(matrix, aspect="auto", origin="lower", cmap=cmap)
    axis.set_xticks(range(len(x_categories)))
    axis.set_yticks(range(len(y_categories)))
    axis.set_xticklabels([str(value) for value in x_categories], rotation=45, ha="right")
    axis.set_yticklabels([str(value) for value in y_categories])
    if overrides.get("show_colorbar", True):
        colorbar = figure.colorbar(image, ax=axis, fraction=0.046, pad=0.04)
        colorbar.ax.tick_params(labelsize=8)


def apply_common_axis_style(axis: Any, panel: dict[str, Any], theme: dict[str, Any]) -> None:
    font_sizes = theme["font_sizes"]
    overrides = panel.get("style_overrides", {})
    x_label = panel.get("xlabel") or pretty_axis_label(panel.get("x", ""))
    if panel.get("chart_type") == "heatmap":
        y_default = panel.get("heatmap_y", "")
    elif len(panel.get("y", [])) == 1:
        y_default = panel["y"][0]
    else:
        y_default = ""
    y_label = panel.get("ylabel") or pretty_axis_label(y_default)

    axis.set_title(panel.get("title", ""), fontsize=font_sizes["axes_title"], pad=4)
    axis.set_xlabel(x_label, fontsize=font_sizes["axes_label"])
    axis.set_ylabel(y_label, fontsize=font_sizes["axes_label"])

    for spine in axis.spines.values():
        spine.set_linewidth(theme["spine_width"])
        spine.set_color("black")

    axis.tick_params(axis="both", which="major", labelsize=font_sizes["ticks"], length=3, width=0.8)
    axis.tick_params(axis="both", which="minor", labelsize=font_sizes["ticks"], length=2, width=0.6)

    if panel.get("chart_type") != "heatmap":
        show_major_grid = bool(overrides.get("show_major_grid", True))
        show_minor_grid = bool(overrides.get("show_minor_grid", True))
        major_grid_color = overrides.get("major_grid_color") or theme["grid"]["major_color"]
        minor_grid_color = overrides.get("minor_grid_color") or theme["grid"]["minor_color"]
        major_grid_linestyle = overrides.get("major_grid_linestyle") or theme["grid"]["major_linestyle"]
        minor_grid_linestyle = overrides.get("minor_grid_linestyle") or theme["grid"]["minor_linestyle"]
        axis.set_axisbelow(True)
        if show_major_grid:
            axis.grid(
                True,
                which="major",
                color=major_grid_color,
                linewidth=theme["grid"]["major_linewidth"],
                linestyle=major_grid_linestyle,
            )
        else:
            axis.grid(False, which="major")
        try:
            axis.xaxis.set_minor_locator(AutoMinorLocator())
            axis.yaxis.set_minor_locator(AutoMinorLocator())
        except Exception:
            pass
        if show_minor_grid:
            axis.grid(
                True,
                which="minor",
                color=minor_grid_color,
                linewidth=theme["grid"]["minor_linewidth"],
                linestyle=minor_grid_linestyle,
            )
        else:
            axis.grid(False, which="minor")

    xlim = panel.get("xlim", {})
    ylim = panel.get("ylim", {})
    if xlim.get("min") is not None or xlim.get("max") is not None:
        axis.set_xlim(left=xlim.get("min"), right=xlim.get("max"))
    if ylim.get("min") is not None or ylim.get("max") is not None:
        axis.set_ylim(bottom=ylim.get("min"), top=ylim.get("max"))

    handles, labels = axis.get_legend_handles_labels()
    if panel.get("show_legend", True) and handles:
        axis.legend(
            handles,
            labels,
            facecolor=theme["legend"]["facecolor"],
            edgecolor=theme["legend"]["edgecolor"],
            framealpha=theme["legend"]["framealpha"],
            borderpad=theme["legend"]["borderpad"],
            fancybox=False,
            loc="best",
        )


def pretty_axis_label(label: str) -> str:
    if not label:
        return ""
    return label.replace("_", " ")
