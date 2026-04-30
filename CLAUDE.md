# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project files

| File | Purpose |
|---|---|
| `dashboard.py` | Marimo app — single source of truth for the dashboard |
| `requirements.txt` | Local dev dependencies (`marimo pandas numpy altair`) |
| `.github/workflows/deploy.yml` | GitHub Actions workflow — exports WASM and deploys to GitHub Pages |
| `.gitignore` | Excludes `.idea/`, `dist/`, `__pycache__` |

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run dashboard in app mode (browser, no code visible)
marimo run dashboard.py

# Run in notebook/edit mode (code + output visible)
marimo edit dashboard.py

# Export as interactive WASM HTML (what GitHub Actions runs)
marimo export html-wasm dashboard.py -o dist/ --mode run --no-show-code
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
| **imports** | — | `mo, pd, np, alt` | |
| **data_simulation** | `np, pd` | `df, CHANNELS, POPULATIONS, START_DATE, END_DATE` | Deterministic (`seed=42`); 16 500 rows |
| **controls** | `mo, CHANNELS, POPULATIONS, START_DATE, END_DATE` | `channel_filter, population_filter, date_range_picker, granularity_dd` | Creates `mo.ui` widgets; no display here |
| **filtering** | all 4 controls + `df, pd` | `filtered, agg_df` | Reruns on every control change |
| **display** | `CHANNELS, POPULATIONS, filtered, agg_df` + all 4 controls + `mo, pd, alt` | *(none)* | Only cell with visible output — KPIs, 3 charts, full layout |

### Simulated data schema

| Column | Type | Details |
|---|---|---|
| `date` | datetime64 | Daily, 2024-05-01 → 2025-10-31 (18 months) |
| `channel` | str | 6 channels — order in `CHANNELS` list defines legend and color order |
| `population` | str | 5 age groups: 18-24, 25-34, 35-44, 45-54, 55+ |
| `volume` | int | Base × trend × weekday factor × monthly factor × noise |

To change the date window or channel mix, edit `CHANNEL_BASE` / `CHANNEL_POP_WEIGHTS` and `_end` in the data_simulation cell.

### Color consistency

All charts share `_color` built from `alt.Scale(domain=CHANNELS, range=_COLORS)` where `_COLORS` is a fixed 6-color list matching Plotly's qualitative palette. Any new channel-colored chart must reuse this scale. The `CHANNELS` list order controls legend order.

### Chart library: altair (not plotly)

Charts use **altair** (Vega-Lite). Do not switch to plotly — plotly is not in marimo's Pyodide lockfile and will fail with an internal error on GitHub Pages. Altair 5.4.1 is bundled and loads reliably in the WASM environment.

### Marimo conventions used here

- Cell-local variables are prefixed with `_` to prevent them from leaking into the reactive namespace.
- UI widgets are created once in the **controls** cell and threaded through the dependency graph — never recreated inside computation or display cells.
- The **display** cell is the sole place that calls `mo.vstack`; it ends with `mo.vstack([...])` as a bare expression (no `return`) so marimo captures it as the cell output.

## Deployment

The dashboard is deployed to GitHub Pages at `https://chenkonturek.github.io/marimo-demo/` via `.github/workflows/deploy.yml`. On every push to `main` the workflow:

1. Installs `marimo` (only marimo — other packages load via Pyodide in the browser)
2. Runs `marimo export html-wasm` to produce a self-contained `dist/index.html`
3. Deploys `dist/` to GitHub Pages using the official `actions/deploy-pages` action

The WASM export embeds the notebook code; Pyodide fetches `pandas`, `numpy`, and `altair` from marimo's lockfile at `wasm.marimo.app` when the page loads.

## Coding Standards

### Type annotations
- All public functions and methods must have full type annotations (parameters + return type), including `-> None`.
- Use native union syntax (`X | Y`, `list[X]`) — no need for `from __future__ import annotations` since floor is 3.12.
- Prefer concrete types over `Any`; use `Any` only when truly unavoidable and leave a comment explaining why.

### Docstrings
- Every public module, class, and function must have a one-line summary in imperative mood ("Return …", "Apply …", "Raise …").
- Use [Google Python Style](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) for multi-line docstrings: `Args:`, `Returns:`, `Raises:`, and `Attributes:` sections.
- **Class docstrings** describe the class's responsibility. Include an `Attributes:` section for non-obvious fields.
- **Functions/methods**: add `Args:` for non-obvious parameters and `Returns:` when the shape or conditions of the return value are non-trivial. Omit sections that would only restate the type annotation.
- Private helpers (`_name`) do not need docstrings unless the logic is subtle.

### Dataclasses & immutability
- Use `@dataclass(frozen=True)` for config/value objects that must not change after creation (see `GameConfig`).
- Use plain `@dataclass` for mutable game entities (see `Bird`).

### Constants & magic numbers
- Domain constants belong in `GameConfig`; avoid bare numeric literals in logic files.
- Module-level constants (non-config) go at the top of the module in `SCREAMING_SNAKE_CASE`.

### No bare `print`
- Use `rich.console.Console` for any terminal output; never use `print()` in library code.

### Error handling
- Raise `ValueError` / `TypeError` at public API boundaries with a descriptive message.
- Do not swallow exceptions silently; re-raise or log.
- Avoid returning `None` to signal failure — raise instead.
