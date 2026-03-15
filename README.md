# MPFC Paper-Style CSV Plotter

A local Streamlit app for building paper-ready plots from arbitrary CSV files with a default visual theme derived from the MPFC paper figures.

## Features

- Upload multiple CSV files in one session
- Map uploaded files to reusable logical data slots
- Build report-style multi-panel figures
- Support `line`, `scatter`, `bar`, and `heatmap` panels
- Save and reload JSON templates
- Export the same Matplotlib figure as `PNG`, `SVG`, and `PDF`
- Start from bundled theme presets:
  - `mpfc_paper_v1`: serif typography, boxed axes, and paper-sized figure presets
  - `mpfc_dark_v2`: dark background, bright grid, and a high-contrast palette inspired by the supplied screenshot

## Project Layout

- `streamlit_app.py`: Streamlit UI
- `app/template_store.py`: template schema, CSV loading, and dataset helpers
- `app/theme_engine.py`: theme presets, figure rendering, and export helpers
- `templates/`: saved demo templates
- `sample_data/`: demo CSV files
- `tests/`: unit and smoke tests

## Quick Start

1. Create a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Run the app:

   ```bash
   streamlit run streamlit_app.py
   ```

4. Open the local Streamlit URL in your browser.

## Suggested First Run

- Load the `general_demo` template from the sidebar
- Map the demo slots to the bundled CSV files in `sample_data/`
- Preview the figure and export it as `PNG`, `SVG`, or `PDF`

## Changing Plot Details

The app exposes the most common styling controls directly in the UI, so you can change plot appearance without editing Python code.

### Change the overall default look

- Open `Figure Settings`
- Change `Theme preset`
- Choose `MPFC Paper v1` for the original paper-style light theme
- Choose `MPFC Dark v2` for the black-background style with bright grid lines and high-contrast traces

### Font family

- Open `Figure Settings`
- Edit `Font family override`
- Enter one or more fonts separated by commas, for example `Times New Roman, Arial, DejaVu Serif`
- If the first font is not installed, Matplotlib falls back to the next one in the list

### Skip markers or reduce symbol density

- Open the target panel in `Panels`
- Set `Marker` to `Theme default` if you want the selected theme to decide the base marker style
- Change `Marker every N points`
- Use `1` to draw a symbol on every point
- Use `2`, `5`, `10`, and so on to keep the line but draw fewer symbols

### Change line and symbol colors

- Open the target panel in `Panels`
- Enter colors in `Line colors` and `Marker colors`
- Use comma-separated values such as `#000000, #e41a1c, royalblue`
- If a panel contains multiple series, colors are assigned in order
- Leave `Marker colors` empty to reuse the line colors for the symbols

### Change x-axis and y-axis ranges

- Open the target panel in `Panels`
- Edit `X min`, `X max`, `Y min`, and `Y max`
- Leave any field empty to keep automatic scaling

### Change grid visibility and style

- Open the target panel in `Panels`
- Toggle `Show major grid` and `Show minor grid`
- Set `Major grid color` and `Minor grid color` if you want custom colors
- Choose `Major grid style` and `Minor grid style` from `Theme default`, `-`, `--`, `:`, or `-.`
- Leave the grid color fields empty to keep the active theme colors

### Save your settings

- Click `Save template to templates/` to reuse the same configuration later
- Or click `Download template JSON` to export a portable template file

## Template Schema

Templates are stored as JSON with this top-level structure:

```json
{
  "version": "1.0",
  "theme": "mpfc_paper_v1",
  "figure": {},
  "data_slots": [],
  "panels": []
}
```

Each panel stores chart settings, bound slot id, filters, axis labels and limits, and style overrides. Style overrides include theme-aware line width, marker size, marker selection, marker skipping, custom line and marker colors, and grid controls. Heatmaps add `heatmap_y` and `value` so the app can map CSV columns to a 2D matrix.

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

## Notes

- The app prefers `pandas` for CSV ingestion when available and falls back to the standard library parser for testability.
- The bundled RF example template uses reduced sample CSV excerpts copied from the supplied measurement files.
