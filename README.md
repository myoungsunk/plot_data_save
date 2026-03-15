# MPFC Paper-Style CSV Plotter

A local Streamlit app for building paper-ready plots from arbitrary CSV files with a default visual theme derived from the MPFC paper figures.

## Features

- Upload multiple CSV files in one session
- Map uploaded files to reusable logical data slots
- Build report-style multi-panel figures
- Support `line`, `scatter`, `bar`, and `heatmap` panels
- Save and reload JSON templates
- Export the same Matplotlib figure as `PNG`, `SVG`, and `PDF`
- Start from the bundled `mpfc_paper_v1` theme with serif typography, boxed axes, and paper-sized figure presets

## Project Layout

- `streamlit_app.py`: Streamlit UI
- `app/template_store.py`: template schema, CSV loading, and dataset helpers
- `app/theme_engine.py`: MPFC paper theme, figure rendering, and export helpers
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

Each panel stores chart settings, bound slot id, filters, axis labels and limits, and style overrides. Heatmaps add `heatmap_y` and `value` so the app can map CSV columns to a 2D matrix.

## Running Tests

```bash
python3 -m unittest discover -s tests -v
```

## Notes

- The app prefers `pandas` for CSV ingestion when available and falls back to the standard library parser for testability.
- The bundled RF example template uses reduced sample CSV excerpts copied from the supplied measurement files.

