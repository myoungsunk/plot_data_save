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
  - `mpfc_dark_v2`: white figure and plot background with a black-leading high-contrast line palette inspired by the supplied screenshot

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
- Choose `MPFC Dark v2` for the white-background style with a black-leading trace palette and stronger scientific contrast

### Font family

- Open `Figure Settings`
- Use `Font family` to choose `Theme default`, a preset font stack, or `Custom`
- Preset options include `Times New Roman`, `Arial`, `Helvetica`, `Calibri`, `DejaVu Serif`, and `DejaVu Sans`
- If you choose `Custom`, enter one or more fonts separated by commas such as `Times New Roman, Arial, DejaVu Serif`
- The app also shows an adaptive font suggestion when mapped CSV labels look dense or long

### Skip markers or reduce symbol density

- Open the target panel in `Panels`
- Set `Marker` to `Theme default` if you want the selected theme to decide the base marker style
- Change `Marker every N points`
- Use `1` to draw a symbol on every point
- Use `2`, `5`, `10`, and so on to keep the line but draw fewer symbols

### Change line and symbol colors

- Open the target panel in `Panels`
- Set `Line color mode` to `Choose colors` if you want to override the theme
- Pick each line color from preset options such as `Black`, `Red`, `Green`, and `Blue`
- Choose `Custom` for any slot if you want to type another color such as `yellow`, `royalblue`, or `#ffd400`
- Set `Marker color mode` to `Reuse line colors` to keep markers matched to the lines
- Or change `Marker color mode` to `Choose colors` and configure marker colors the same way

### Change x-axis and y-axis ranges

- Open the target panel in `Panels`
- Edit `X min`, `X max`, `Y min`, and `Y max`
- Leave any field empty to keep automatic scaling

### Change grid visibility and style

- Open the target panel in `Panels`
- Toggle `Show major grid` and `Show minor grid`
- If the selected CSV uses numeric axes, the app shows adaptive grid spacing controls based on the current data range
- Use `X major step` and `Y major step` to choose `Auto`, a recommended interval, or `Custom`
- Use `X minor per major` and `Y minor per major` to control the number of minor grid intervals between major lines
- Pick `Major grid color` and `Minor grid color` from preset options, or choose `Custom` to type your own color
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

Each panel stores chart settings, bound slot id, filters, axis labels and limits, and style overrides. Style overrides include theme-aware line width, marker size, marker selection, marker skipping, custom line and marker colors, adaptive major/minor grid spacing, and grid style controls. Heatmaps add `heatmap_y` and `value` so the app can map CSV columns to a 2D matrix.

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

## Notes

- The app prefers `pandas` for CSV ingestion when available and falls back to the standard library parser for testability.
- The bundled RF example template uses reduced sample CSV excerpts copied from the supplied measurement files.
