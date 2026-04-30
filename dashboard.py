import marimo
import types
from dataclasses import dataclass
from typing import Any

__generated_with = "0.23.4"
app = marimo.App()


@dataclass(frozen=True)
class ChannelConfig:
    """Immutable simulation parameters for a single marketing channel.

    Attributes:
        base_volume: Expected daily impressions summed across all populations.
        pop_weights: Volume fraction per population group; values should sum to ~1.
    """

    base_volume: int
    pop_weights: list[float]


@dataclass(frozen=True)
class SimulationConfig:
    """Immutable parameters that define the full marketing data simulation.

    Attributes:
        channels: Ordered channel names; order controls chart legend and colours.
        populations: Ordered age-group labels.
        channel_configs: Per-channel parameters keyed by channel name.
        end_date: Last date in the time series (ISO-8601).
        months: Number of months of history to generate.
        random_seed: Seed for reproducible noise generation.
    """

    channels: list[str]
    populations: list[str]
    channel_configs: dict[str, ChannelConfig]
    end_date: str
    months: int = 18
    random_seed: int = 42


CONFIG = SimulationConfig(
    channels=[
        "Email",
        "Paid Search",
        "Social Media",
        "Display Ads",
        "Affiliate",
        "Push Notification",
    ],
    populations=["18-24", "25-34", "35-44", "45-54", "55+"],
    channel_configs={
        "Email":             ChannelConfig(3000, [0.10, 0.25, 0.30, 0.25, 0.10]),
        "Paid Search":       ChannelConfig(5000, [0.15, 0.30, 0.28, 0.18, 0.09]),
        "Social Media":      ChannelConfig(4500, [0.35, 0.32, 0.18, 0.10, 0.05]),
        "Display Ads":       ChannelConfig(2500, [0.20, 0.25, 0.25, 0.20, 0.10]),
        "Affiliate":         ChannelConfig(1500, [0.18, 0.28, 0.25, 0.20, 0.09]),
        "Push Notification": ChannelConfig(1000, [0.30, 0.35, 0.20, 0.10, 0.05]),
    },
    end_date="2025-10-31",
)

CHANNEL_COLORS: list[str] = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]


def _build_volume_dataframe(
    config: SimulationConfig,
    np: types.ModuleType,
    pd: types.ModuleType,
) -> tuple[Any, Any, Any]:
    """Build the simulated marketing volume DataFrame from config.

    Args:
        config: Simulation parameters including channels, populations, and date range.
        np: numpy module.
        pd: pandas module.

    Returns:
        Tuple of (df, start_date, end_date) where df has columns:
        date (datetime64), channel (str), population (str), volume (int).
    """
    np.random.seed(config.random_seed)
    _end = pd.Timestamp(config.end_date)
    _start = _end - pd.DateOffset(months=config.months)
    _dates = pd.date_range(start=_start, end=_end, freq="D")
    _n = len(_dates)

    _trend = np.linspace(1.0, 1.2, _n)
    _weekday = np.array([1.1 if d.weekday() < 5 else 0.65 for d in _dates])
    _monthly = np.array([
        0.82 if d.month in (7, 8) else (1.08 if d.month in (11, 12) else 1.0)
        for d in _dates
    ])

    _rows: list[dict[str, Any]] = []
    for _ch in config.channels:
        _cfg = config.channel_configs[_ch]
        for _i, _pop in enumerate(config.populations):
            _w = _cfg.pop_weights[_i]
            _noise = np.clip(np.random.normal(1.0, 0.12, _n), 0.5, 1.8)
            _vol = (_cfg.base_volume * _w * _trend * _weekday * _monthly * _noise).astype(int)
            for _j, _dt in enumerate(_dates):
                _rows.append({
                    "date": _dt,
                    "channel": _ch,
                    "population": _pop,
                    "volume": int(_vol[_j]),
                })

    return pd.DataFrame(_rows), _dates[0].date(), _dates[-1].date()


@app.cell
def imports() -> tuple[Any, Any, Any, Any]:
    """Load third-party libraries used across all cells."""
    import marimo as mo
    import pandas as pd
    import numpy as np
    import altair as alt
    return alt, mo, np, pd


@app.cell
def simulate_data(
    np: types.ModuleType,
    pd: types.ModuleType,
) -> tuple[Any, Any, Any]:
    """Generate simulated daily marketing volume using CONFIG."""
    df, START_DATE, END_DATE = _build_volume_dataframe(CONFIG, np, pd)
    return df, START_DATE, END_DATE


@app.cell
def controls(
    END_DATE: Any,
    START_DATE: Any,
    mo: types.ModuleType,
) -> tuple[Any, Any, Any, Any]:
    """Create UI filter widgets. Widgets are displayed via the layout cell."""
    channel_filter = mo.ui.multiselect(
        options=CONFIG.channels, value=CONFIG.channels, label="Channels"
    )
    population_filter = mo.ui.multiselect(
        options=CONFIG.populations, value=CONFIG.populations, label="Populations"
    )
    date_range_picker = mo.ui.date_range(
        start=START_DATE, stop=END_DATE, value=(START_DATE, END_DATE)
    )
    granularity_dd = mo.ui.dropdown(
        options=["Daily", "Weekly", "Monthly"], value="Weekly", label="Granularity"
    )
    return channel_filter, date_range_picker, granularity_dd, population_filter


@app.cell
def filter_data(
    channel_filter: Any,
    date_range_picker: Any,
    df: Any,
    granularity_dd: Any,
    pd: types.ModuleType,
    population_filter: Any,
) -> tuple[Any, Any]:
    """Apply UI filter selections to the raw DataFrame.

    Returns:
        filtered: Row-level DataFrame matching all active filters.
        agg_df: Filtered data aggregated by channel at the chosen granularity.
    """
    _sel_ch = channel_filter.value or df["channel"].unique().tolist()
    _sel_pop = population_filter.value or df["population"].unique().tolist()
    _d0, _d1 = date_range_picker.value

    filtered = df[
        df["channel"].isin(_sel_ch)
        & df["population"].isin(_sel_pop)
        & (df["date"] >= pd.Timestamp(_d0))
        & (df["date"] <= pd.Timestamp(_d1))
    ].copy()

    _freq = {"Daily": "D", "Weekly": "W-MON", "Monthly": "MS"}[granularity_dd.value]

    agg_df = (
        filtered
        .groupby([pd.Grouper(key="date", freq=_freq), "channel"])["volume"]
        .sum()
        .reset_index()
    )
    return agg_df, filtered


@app.cell
def layout(
    agg_df: Any,
    alt: types.ModuleType,
    channel_filter: Any,
    date_range_picker: Any,
    filtered: Any,
    granularity_dd: Any,
    mo: types.ModuleType,
    pd: types.ModuleType,
    population_filter: Any,
) -> None:
    """Compute KPIs, build Altair charts, and assemble the full dashboard layout."""
    # ── KPI metrics ──────────────────────────────────────────────
    _total = int(filtered["volume"].sum())
    if not filtered.empty:
        _top_ch = filtered.groupby("channel")["volume"].sum().idxmax()
        _cutoff = filtered["date"].max()
        _recent = filtered[filtered["date"] > _cutoff - pd.Timedelta(days=30)]["volume"].sum()
        _prev = filtered[
            (filtered["date"] > _cutoff - pd.Timedelta(days=60))
            & (filtered["date"] <= _cutoff - pd.Timedelta(days=30))
        ]["volume"].sum()
        _mom = f"{(_recent - _prev) / _prev * 100:+.1f}%" if _prev > 0 else "N/A"
    else:
        _top_ch = "N/A"
        _mom = "N/A"

    # ── Shared colour scale ───────────────────────────────────────
    _color = alt.Color(
        "channel:N",
        scale=alt.Scale(domain=CONFIG.channels, range=CHANNEL_COLORS),
        legend=alt.Legend(title="Channel"),
    )

    # ── Time series line chart ────────────────────────────────────
    _ts = (
        alt.Chart(agg_df)
        .mark_line()
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("volume:Q", title="Volume"),
            color=_color,
            tooltip=["date:T", "channel:N", "volume:Q"],
        )
        .properties(title="Volume Over Time by Channel", width="container", height=320)
    )

    # ── Stacked bar chart ─────────────────────────────────────────
    _bar = (
        alt.Chart(agg_df)
        .mark_bar()
        .encode(
            x=alt.X("date:T", title="Date"),
            y=alt.Y("volume:Q", title="Volume", stack=True),
            color=_color,
            order=alt.Order("channel:N", sort=CONFIG.channels),
            tooltip=["date:T", "channel:N", "volume:Q"],
        )
        .properties(title="Stacked Volume by Channel", width="container", height=320)
    )

    # ── Channel × Population heatmap ──────────────────────────────
    _hm_df = (
        filtered.groupby(["channel", "population"])["volume"]
        .sum()
        .reset_index()
    )
    _hm = (
        alt.Chart(_hm_df)
        .mark_rect()
        .encode(
            x=alt.X("population:N", title="Population", sort=CONFIG.populations),
            y=alt.Y("channel:N", title="Channel", sort=CONFIG.channels),
            color=alt.Color("volume:Q", title="Volume", scale=alt.Scale(scheme="blues")),
            tooltip=["channel:N", "population:N", "volume:Q"],
        )
        .properties(title="Total Volume: Channel × Population", width="container", height=240)
    )

    mo.vstack([
        mo.md("# Marketing Volume Dashboard"),
        mo.md("Monitor marketing channel performance across audience segments."),
        mo.hstack(
            [channel_filter, population_filter, date_range_picker, granularity_dd],
            wrap=True,
        ),
        mo.hstack([
            mo.stat(value=f"{_total:,}", label="Total Volume"),
            mo.stat(value=_top_ch, label="Top Channel"),
            mo.stat(value=_mom, label="MoM Growth"),
        ]),
        _ts,
        _bar,
        _hm,
    ])
