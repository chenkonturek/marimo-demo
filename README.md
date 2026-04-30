# Marketing Volume Dashboard

An interactive marketing channel monitoring dashboard built with [marimo](https://marimo.io/).

## Setup

```bash
pip install -r requirements.txt
```

## Running

```bash
# App mode — browser UI only, no code
marimo run dashboard.py

# Edit mode — live notebook with code and output
marimo edit dashboard.py
```

Open **http://localhost:2718** in your browser.

## Dashboard

The dashboard visualises simulated daily marketing volume across 6 channels and 5 audience segments over 18 months (May 2024 – Oct 2025).

**Filters**
- **Channels** — multiselect to show/hide individual channels
- **Populations** — multiselect to filter by age group (18-24, 25-34, 35-44, 45-54, 55+)
- **Date Range** — narrow the time window
- **Granularity** — aggregate by Day / Week / Month

**Charts**
| Chart | What it shows |
|---|---|
| KPI cards | Total volume, top channel, month-over-month growth vs the prior 30-day window |
| Line chart | Volume over time, one line per channel |
| Stacked bar | Volume composition by channel over time |
| Heatmap | Total volume broken down by channel × age group |

Colors are pinned consistently across the line and bar charts — the same channel always gets the same color.

## Simulated data

Volume is generated deterministically (`numpy.random.seed(42)`) with:
- per-channel base volumes and age-group weights
- 20 % long-term growth trend over the 18-month window
- weekday uplift (×1.1 Mon–Fri, ×0.65 Sat–Sun)
- summer dip (Jul–Aug ×0.82) and holiday peak (Nov–Dec ×1.08)
- Gaussian noise (σ = 12 %)

To swap in real data, replace the data_simulation cell with a DataFrame that has the same four columns: `date`, `channel`, `population`, `volume`.
