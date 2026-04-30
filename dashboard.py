import marimo

__generated_with = "0.23.4"
app = marimo.App()


@app.cell
def __():
    import marimo as mo
    import pandas as pd
    import numpy as np
    import altair as alt
    return alt, mo, np, pd


@app.cell
def __(np, pd):
    CHANNELS = [
        "Email",
        "Paid Search",
        "Social Media",
        "Display Ads",
        "Affiliate",
        "Push Notification",
    ]
    POPULATIONS = ["18-24", "25-34", "35-44", "45-54", "55+"]

    CHANNEL_BASE = {
        "Email": 3000,
        "Paid Search": 5000,
        "Social Media": 4500,
        "Display Ads": 2500,
        "Affiliate": 1500,
        "Push Notification": 1000,
    }

    # Fraction of volume per age group per channel
    CHANNEL_POP_WEIGHTS = {
        "Email":             [0.10, 0.25, 0.30, 0.25, 0.10],
        "Paid Search":       [0.15, 0.30, 0.28, 0.18, 0.09],
        "Social Media":      [0.35, 0.32, 0.18, 0.10, 0.05],
        "Display Ads":       [0.20, 0.25, 0.25, 0.20, 0.10],
        "Affiliate":         [0.18, 0.28, 0.25, 0.20, 0.09],
        "Push Notification": [0.30, 0.35, 0.20, 0.10, 0.05],
    }

    np.random.seed(42)
    _end = pd.Timestamp("2025-10-31")
    _start = _end - pd.DateOffset(months=18)
    _dates = pd.date_range(start=_start, end=_end, freq="D")
    _n = len(_dates)

    _trend = np.linspace(1.0, 1.2, _n)
    _weekday = np.array([1.1 if d.weekday() < 5 else 0.65 for d in _dates])
    _monthly = np.array([
        0.82 if d.month in (7, 8) else (1.08 if d.month in (11, 12) else 1.0)
        for d in _dates
    ])

    _rows = []
    for _ch in CHANNELS:
        _base = CHANNEL_BASE[_ch]
        for _i, _pop in enumerate(POPULATIONS):
            _w = CHANNEL_POP_WEIGHTS[_ch][_i]
            _noise = np.clip(np.random.normal(1.0, 0.12, _n), 0.5, 1.8)
            _vol = (_base * _w * _trend * _weekday * _monthly * _noise).astype(int)
            for _j, _dt in enumerate(_dates):
                _rows.append({
                    "date": _dt,
                    "channel": _ch,
                    "population": _pop,
                    "volume": int(_vol[_j]),
                })

    df = pd.DataFrame(_rows)
    START_DATE = _dates[0].date()
    END_DATE = _dates[-1].date()
    return CHANNELS, END_DATE, POPULATIONS, START_DATE, df


@app.cell
def __(CHANNELS, END_DATE, POPULATIONS, START_DATE, mo):
    channel_filter = mo.ui.multiselect(
        options=CHANNELS, value=CHANNELS, label="Channels"
    )
    population_filter = mo.ui.multiselect(
        options=POPULATIONS, value=POPULATIONS, label="Populations"
    )
    date_range_picker = mo.ui.date_range(
        start=START_DATE, stop=END_DATE, value=(START_DATE, END_DATE)
    )
    granularity_dd = mo.ui.dropdown(
        options=["Daily", "Weekly", "Monthly"], value="Weekly", label="Granularity"
    )
    return channel_filter, date_range_picker, granularity_dd, population_filter


@app.cell
def __(channel_filter, date_range_picker, df, granularity_dd, pd, population_filter):
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
def __(CHANNELS, POPULATIONS, agg_df, alt, channel_filter, date_range_picker, filtered, granularity_dd, mo, pd, population_filter):
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

    # ── Shared color scale (same order & colors across charts) ────
    _COLORS = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]
    _color = alt.Color(
        "channel:N",
        scale=alt.Scale(domain=CHANNELS, range=_COLORS),
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
            order=alt.Order("channel:N", sort=CHANNELS),
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
            x=alt.X("population:N", title="Population", sort=POPULATIONS),
            y=alt.Y("channel:N", title="Channel", sort=CHANNELS),
            color=alt.Color("volume:Q", title="Volume", scale=alt.Scale(scheme="blues")),
            tooltip=["channel:N", "population:N", "volume:Q"],
        )
        .properties(title="Total Volume: Channel × Population", width="container", height=240)
    )

    # ── Layout ───────────────────────────────────────────────────
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
