# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard in app mode (browser, no code visible)
marimo run dashboard.py

# Run in notebook/edit mode (code + output visible)
marimo edit dashboard.py
```

## Architecture

The entire project is a single marimo app: `dashboard.py`.

Marimo uses a **reactive cell model** — each `@app.cell` is a pure function. Arguments are names returned by earlier cells; returning a name makes it available downstream. When a UI element's `.value` changes, every cell that took it as an argument automatically reruns.

**Critical marimo display rule:** a cell's visible output is its **last bare expression** (no `return`). An explicit `return value` does not display — it only exports the name for other cells to consume. Cells that need to display AND export must use `return name,` (trailing comma makes a tuple; marimo exports the name and displays it).

### Cell dependency graph

```
imports → data_simulation → controls → filtering → display
```

| Cell | Inputs | Exports | Notes |
|---|---|---|---|
| **imports** | — | `mo, pd, np, px` | |
| **data_simulation** | `np, pd` | `df, CHANNELS, POPULATIONS, START_DATE, END_DATE` | Deterministic (`seed=42`); 16 500 rows |
| **controls** | `mo, CHANNELS, POPULATIONS, START_DATE, END_DATE` | `channel_filter, population_filter, date_range_picker, granularity_dd` | Creates `mo.ui` widgets; no display here |
| **filtering** | all 4 controls + `df, pd` | `filtered, agg_df` | Reruns on every control change |
| **display** | `CHANNELS, filtered, agg_df` + all 4 controls + `mo, pd, px` | *(none)* | Only cell with visible output — KPIs, 3 charts, full layout |

### Simulated data schema

| Column | Type | Details |
|---|---|---|
| `date` | datetime64 | Daily, 2024-05-01 → 2025-10-31 (18 months) |
| `channel` | str | 6 channels — order in `CHANNELS` list defines legend and color order |
| `population` | str | 5 age groups: 18-24, 25-34, 35-44, 45-54, 55+ |
| `volume` | int | Base × trend × weekday factor × monthly factor × noise |

To change the date window or channel mix, edit `CHANNEL_BASE` / `CHANNEL_POP_WEIGHTS` and `_end` in the data_simulation cell.

### Color consistency

Both the line chart and stacked bar share a `_color_map` built from `zip(CHANNELS, px.colors.qualitative.Plotly)` and `category_orders={"channel": CHANNELS}`. Any new chart should reuse `_color_map` and `_cat_order` to stay consistent.

### Marimo conventions used here

- Cell-local variables are prefixed with `_` to prevent them from leaking into the reactive namespace.
- UI widgets are created once in the **controls** cell and threaded through the dependency graph — never recreated inside computation or display cells.
- The **display** cell is the sole place that calls `mo.vstack`; it ends with `mo.vstack([...])` as a bare expression (no `return`) so marimo captures it as the cell output.
