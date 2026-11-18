"""Plotly figure builders. Every function returns a styled go.Figure; pages just call show(fig)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import theme as T

USER_COLORS = {"Agent": T.BLUE, "Customer": T.ORANGE}
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
RAMP = [[0.0, T.BLUE_RAMP[0]], [0.25, T.BLUE_RAMP[1]], [0.5, T.BLUE_RAMP[2]],
        [0.75, T.BLUE_RAMP[3]], [1.0, T.BLUE_RAMP[4]]]
METRICS = {  # label -> (column, hover format, tick format, y-from-zero)
    "Success rate": ("success", "%{y:.1%}", ".0%", False),
    "Click-through": ("ctr", "%{y:.1%}", ".0%", False),
    "Zero-result rate": ("zero", "%{y:.1%}", ".0%", True),
    "Time to first click": ("ttfc", "%{y:.1f}s", ".0f", True),
    "Search volume": ("searches", "%{y:,.0f}", ",.0f", True),
}


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


def style(fig: go.Figure, height: int = 320, legend: bool = False, hover: str = "closest",
          top: int = 8, left: int = 4) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=left, r=8, t=top, b=4), showlegend=legend, hovermode=hover,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=T.SERIES, bargap=0.28,
        font=dict(family=T.FONT, color=T.INK2, size=12),
        hoverlabel=dict(bgcolor="#242422", bordercolor=T.AXIS, font=dict(family=T.FONT, color=T.INK, size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                    font=dict(color=T.INK2), bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=T.AXIS, ticks="", tickfont=dict(color=T.MUTED))
    fig.update_yaxes(gridcolor=T.GRID, zeroline=False, linecolor="rgba(0,0,0,0)", ticks="",
                     tickfont=dict(color=T.MUTED))
    return fig


def round_bars(fig: go.Figure, radius: int = 4) -> go.Figure:
    try:  # needs a recent Plotly; silently skipped otherwise
        fig.update_traces(marker_cornerradius=radius, selector=dict(type="bar"))
    except Exception:
        pass
    return fig


def add_events(fig: go.Figure, events: pd.DataFrame, x0, x1, labels: bool = True) -> None:
    n = 0
    for e in events.itertuples():
        if e.end < x0 or e.start > x1:
            continue
        color = T.EVENT_COLORS.get(e.kind, T.MUTED)
        s = max(e.start, x0)
        en = min(e.end + pd.Timedelta(days=1), x1 + pd.Timedelta(days=1))
        fig.add_shape(type="rect", xref="x", yref="paper", x0=s.strftime("%Y-%m-%d"), x1=en.strftime("%Y-%m-%d"),
                      y0=0, y1=1, fillcolor=color, opacity=0.16, line_width=0, layer="below")
        if labels:
            fig.add_annotation(x=s.strftime("%Y-%m-%d"), xref="x", y=1, yref="paper", text=e.label,
                               showarrow=False, xanchor="left", yanchor="bottom", yshift=14 * (n % 2),
                               font=dict(size=11, color=color))
        n += 1


# ------------------------------------------------------------------ executive
def trend_chart(tr: pd.DataFrame, metric: str, events: pd.DataFrame, freq: str, height: int = 360) -> go.Figure:
    col, hover, tick, zero = METRICS[metric]
    fig = go.Figure()
    many = len(tr) > 60
    when = "Week of %{x|%b %d}" if freq == "Weekly" else "%{x|%b %d}"
    fig.add_trace(go.Scatter(
        x=tr["bucket"], y=tr[col], mode="lines" if many else "lines+markers", name=metric,
        line=dict(color=T.BLUE, width=2.5), fill="tozeroy", fillcolor=rgba(T.BLUE, 0.10),
        marker=dict(size=7, color=T.BLUE, line=dict(color=T.SURFACE, width=2)),
        hovertemplate=f"{when}<br><b>{hover}</b><extra></extra>"))
    style(fig, height=height, hover="x", top=34)
    vals = tr[col].dropna()
    if zero or vals.empty:
        fig.update_yaxes(rangemode="tozero", tickformat=tick)
    else:
        fig.update_yaxes(range=[max(0, vals.min() - 0.08), min(1.0, vals.max() + 0.05)], tickformat=tick)
    if len(tr):
        add_events(fig, events, tr["bucket"].min(), tr["bucket"].max() + pd.Timedelta(days=6 if freq == "Weekly" else 0))
    return fig


def area_bars(df: pd.DataFrame, avg: float, height: int = 360) -> go.Figure:
    d = df.sort_values("success")  # worst first -> top once the axis is reversed
    fig = go.Figure(go.Bar(
        x=d["success"], y=d["product_area"], orientation="h", marker_color=T.BLUE,
        text=[f"{v:.0%}" for v in d["success"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=T.INK2, size=12), customdata=d["sessions"],
        hovertemplate="<b>%{y}</b><br>%{x:.1%} resolved · %{customdata:,} sessions<extra></extra>"))
    style(fig, height=height, left=0)
    fig.update_xaxes(range=[0, 1.1], tickformat=".0%", showgrid=True, gridcolor=T.GRID)
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=T.INK2, size=12))
    fig.add_vline(x=avg, line_width=1.5, line_dash="dot", line_color=T.MUTED)
    return round_bars(fig)


def impact_chart(imp: pd.DataFrame, height: int = 300) -> go.Figure:
    names = {True: "Answer found", False: "No answer found"}
    colors = {True: T.BLUE, False: T.ORANGE}
    specs = [("res_hours", "Median hours to resolve", "{:.0f} h"), ("escalation", "Escalation rate", "{:.0%}"),
             ("csat", "Average CSAT (1–5)", "{:.2f}")]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[s[1] for s in specs], horizontal_spacing=0.08)
    for ci, (col, _, fmt) in enumerate(specs, start=1):
        for found in (True, False):
            if found not in imp.index:
                continue
            v = float(imp.loc[found, col])
            fig.add_trace(go.Bar(x=[names[found]], y=[v], name=names[found], legendgroup=names[found],
                                 showlegend=(ci == 1), marker_color=colors[found], text=[fmt.format(v)],
                                 textposition="outside", cliponaxis=False, textfont=dict(color=T.INK, size=13),
                                 hovertemplate=f"{names[found]}<br><b>{fmt.format(v)}</b><extra></extra>"),
                          row=1, col=ci)
    style(fig, height=height, legend=True, top=52)
    fig.update_yaxes(showgrid=False, showticklabels=False, rangemode="tozero")
    fig.update_xaxes(showticklabels=False)
    fig.update_annotations(font=dict(size=12, color=T.INK2))
    # head-room for the value labels
    for ci, (col, _, _) in enumerate(specs, start=1):
        top = float(imp[col].max()) if col in imp else 1
        fig.update_yaxes(range=[0, top * 1.22], row=1, col=ci)
    return round_bars(fig)


# ------------------------------------------------------------------ search performance
def funnel_chart(f: dict, height: int = 330) -> go.Figure:
    stages = ["Searches", "Returned results", "Got a click", "Found an answer"]
    vals = [f["searches"], f["results"], f["clicked"], f["resolved"]]
    fig = go.Figure(go.Funnel(
        y=stages, x=vals, textinfo="value+percent initial", textposition="inside",
        textfont=dict(color="#ffffff", size=13), marker=dict(color=T.BLUE_ORDINAL, line=dict(width=0)),
        connector=dict(line=dict(color=T.GRID, width=1), fillcolor=rgba(T.BLUE, 0.08)),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} searches · %{percentInitial:.1%} of all<extra></extra>"))
    style(fig, height=height, left=0)
    fig.update_yaxes(tickfont=dict(color=T.INK2, size=12))
    return fig


def ttfc_distribution(s: pd.DataFrame, height: int = 330) -> go.Figure:
    fig = go.Figure()
    bins = np.arange(0, 62, 2)
    centers = (bins[:-1] + bins[1:]) / 2
    clicked = s[s["clicked"] & s["time_to_first_click_s"].notna()]
    users = [u for u in ("Agent", "Customer") if (clicked["user_type"] == u).any()]
    for u in users:
        x = clicked.loc[clicked["user_type"] == u, "time_to_first_click_s"].clip(upper=59.9)
        h, _ = np.histogram(x, bins=bins)
        pct = h / max(h.sum(), 1) * 100
        label = "Support agents" if u == "Agent" else "Customers"
        fig.add_trace(go.Scatter(x=centers, y=pct, mode="lines", name=label, line=dict(color=USER_COLORS[u], width=2.5,
                                 shape="spline", smoothing=0.7), fill="tozeroy", fillcolor=rgba(USER_COLORS[u], 0.14),
                                 hovertemplate=f"{label}<br>%{{x:.0f}}s · %{{y:.1f}}% of clicks<extra></extra>"))
        fig.add_vline(x=float(x.median()), line_dash="dot", line_color=USER_COLORS[u], line_width=1.5)
    style(fig, height=height, legend=len(users) > 1, hover="x", top=30)
    fig.update_xaxes(title=dict(text="Seconds from query to first click (dotted = median)",
                                font=dict(size=11, color=T.MUTED)), ticksuffix="s")
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    return fig


def position_bars(pos: pd.DataFrame, height: int = 330) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=pos["label"], y=pos["share"], marker_color=T.BLUE, text=[f"{v:.0%}" for v in pos["share"]],
        textposition="outside", cliponaxis=False, textfont=dict(color=T.INK2, size=12),
        hovertemplate="Position %{x}<br><b>%{y:.1%}</b> of clicks<extra></extra>"))
    style(fig, height=height, top=20)
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    fig.update_xaxes(title=dict(text="Rank of the clicked result", font=dict(size=11, color=T.MUTED)))
    return round_bars(fig)


def latency_chart(tr: pd.DataFrame, events: pd.DataFrame, height: int = 330) -> go.Figure:
    fig = go.Figure()
    for name, col, color in (("Median", "p50", T.BLUE), ("95th percentile", "p95", T.ORANGE)):
        fig.add_trace(go.Scatter(x=tr["bucket"], y=tr[col], mode="lines", name=name, line=dict(color=color, width=2.2),
                                 hovertemplate=f"{name}<br>%{{x|%b %d}} · <b>%{{y:,.0f}} ms</b><extra></extra>"))
    style(fig, height=height, legend=True, hover="x unified", top=40)
    fig.update_yaxes(rangemode="tozero", ticksuffix=" ms")
    if len(tr):
        add_events(fig, events, tr["bucket"].min(), tr["bucket"].max())
    return fig


def heatmap(pv: pd.DataFrame, height: int = 330) -> go.Figure:
    z = pv.values.astype(float)
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{h:02d}" for h in range(24)], y=DAYS, colorscale=RAMP, xgap=2, ygap=2, hoverongaps=False,
        zmin=float(np.nanmin(z)) if np.isfinite(z).any() else 0, zmax=float(np.nanmax(z)) if np.isfinite(z).any() else 1,
        colorbar=dict(tickformat=".0%", thickness=10, len=0.85, outlinewidth=0, tickfont=dict(color=T.MUTED, size=11)),
        hovertemplate="%{y} %{x}:00<br><b>%{z:.0%}</b> of sessions resolved<extra></extra>"))
    style(fig, height=height, left=0)
    fig.update_yaxes(autorange="reversed", showgrid=False)
    fig.update_xaxes(title=dict(text="Hour of day (ET)", font=dict(size=11, color=T.MUTED)), dtick=2)
    return fig


def searches_per_session(g: pd.DataFrame, height: int = 330) -> go.Figure:
    fig = go.Figure()
    for name, col, color in (("Found an answer", "found", T.BLUE), ("Gave up / no answer", "gave_up", T.ORANGE)):
        fig.add_trace(go.Bar(x=g["label"], y=g[col], name=name, marker=dict(color=color, line=dict(color=T.SURFACE, width=2)),
                             texttemplate="%{y:.0%}", textposition="auto", textfont=dict(color="#ffffff", size=12),
                             hovertemplate=f"{name}<br>%{{x}}: <b>%{{y:.1%}}</b> of sessions<extra></extra>"))
    style(fig, height=height, legend=True, top=34)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    return fig


# ------------------------------------------------------------------ content gaps
def gap_treemap(tt: pd.DataFrame, height: int = 420) -> go.Figure:
    d = tt[tt["failed"] > 0]
    fig = px.treemap(d, path=[px.Constant("All areas"), "product_area", "topic"], values="failed",
                     color="fail_rate", color_continuous_scale=T.BLUE_RAMP,
                     range_color=(float(d["fail_rate"].min()), float(d["fail_rate"].max())))
    fig.update_traces(root_color=T.SURFACE, marker=dict(line=dict(width=2, color=T.SURFACE)),
                      textfont=dict(family=T.FONT, size=13),
                      hovertemplate="<b>%{label}</b><br>%{value:,} failed sessions<br>failure rate %{color:.0%}<extra></extra>")
    fig.update_coloraxes(showscale=False)
    return style(fig, height=height, left=0, top=0)


def launch_chart(s: pd.DataFrame, ses: pd.DataFrame, area: str, events: pd.DataFrame, height: int = 400) -> go.Figure:
    sa, ea = s[s["product_area"] == area], ses[ses["product_area"] == area]
    vol = sa.groupby("week").agg(searches=("search_id", "size"), zero=("zero_result", "mean"))
    suc = ea.groupby("week")["resolved"].mean().rename("success")
    d = vol.join(suc).reset_index()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.45, 0.55], vertical_spacing=0.09)
    fig.add_trace(go.Bar(x=d["week"], y=d["searches"], name="Searches per week", marker_color=rgba(T.BLUE, 0.85),
                         hovertemplate="Week of %{x|%b %d}<br><b>%{y:,} searches</b><extra></extra>"), row=1, col=1)
    for name, col, color in (("Zero-result rate", "zero", T.ORANGE), ("Session success", "success", T.BLUE)):
        fig.add_trace(go.Scatter(x=d["week"], y=d[col], mode="lines+markers", name=name, line=dict(color=color, width=2.4),
                                 marker=dict(size=6, color=color, line=dict(color=T.SURFACE, width=2)),
                                 hovertemplate=f"{name}<br>Week of %{{x|%b %d}} · <b>%{{y:.0%}}</b><extra></extra>"),
                      row=2, col=1)
    style(fig, height=height, legend=True, hover="x", top=44)
    fig.update_yaxes(tickformat=".0%", rangemode="tozero", row=2, col=1)
    fig.update_yaxes(rangemode="tozero", row=1, col=1)
    if len(d):
        add_events(fig, events, d["week"].min(), d["week"].max() + pd.Timedelta(days=6))
    return round_bars(fig)


def hbar(labels, values, height: int = 360, fmt: str = "{:,.0f}", color: str = T.BLUE, hover_unit: str = "") -> go.Figure:
    fig = go.Figure(go.Bar(
        x=list(values), y=list(labels), orientation="h", marker_color=color, text=[fmt.format(v) for v in values],
        textposition="outside", cliponaxis=False, textfont=dict(color=T.INK2, size=12),
        hovertemplate=f"<b>%{{y}}</b><br>%{{x:,.0f}} {hover_unit}<extra></extra>"))
    style(fig, height=height, left=0)
    fig.update_xaxes(showgrid=False, showticklabels=False, rangemode="tozero")
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=T.INK2, size=12))
    return round_bars(fig)


# ------------------------------------------------------------------ agents
def agent_facets(at: pd.DataFrame, height: int = 520) -> go.Figure:
    teams = sorted(at["team"].unique())
    rows, cols = (1, 1) if len(teams) == 1 else (2, 2) if len(teams) > 2 else (1, 2)
    fig = make_subplots(rows=rows, cols=cols, subplot_titles=teams, shared_xaxes=True, shared_yaxes=True,
                        horizontal_spacing=0.05, vertical_spacing=0.12)
    big = max(float(at["sessions"].max()), 1.0)
    for i, team in enumerate(teams):
        d = at[at["team"] == team].dropna(subset=["ttfc"])
        if d.empty:
            continue
        lab = pd.Series("", index=d.index)
        lab[d["success"].idxmax()] = d.loc[d["success"].idxmax(), "name"]
        lab[d["success"].idxmin()] = d.loc[d["success"].idxmin(), "name"]
        cd = np.stack([d["name"], d["sessions"], d["tenure_months"], d["vs_team"] * 100], axis=-1)
        fig.add_trace(go.Scatter(
            x=d["ttfc"], y=d["success"], mode="markers+text", text=lab, textposition="top center",
            textfont=dict(size=11, color=T.INK2), showlegend=False, customdata=cd,
            marker=dict(size=9 + 17 * np.sqrt(d["sessions"] / big), color=T.BLUE, opacity=0.92,
                        line=dict(color=T.SURFACE, width=2)),
            hovertemplate="<b>%{customdata[0]}</b><br>Success %{y:.0%} (%{customdata[3]:+.1f} pts vs team)"
                          "<br>%{x:.1f}s to first click<br>%{customdata[1]:,} sessions · %{customdata[2]} mo tenure"
                          "<extra></extra>"), row=i // cols + 1, col=i % cols + 1)
    style(fig, height=height, top=30)
    fig.update_yaxes(tickformat=".0%", showgrid=True)
    fig.update_xaxes(ticksuffix="s", showgrid=True, gridcolor=T.GRID)
    fig.update_annotations(font=dict(size=12.5, color=T.INK))
    fig.add_hline(y=float(at["success"].median()), line_dash="dot", line_color=T.AXIS, row="all", col="all")
    return fig


def tenure_bars(tc: pd.DataFrame, height: int = 300) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=tc["tenure_band"].astype(str), y=tc["success"], marker_color=T.BLUE, customdata=np.stack([tc["agents"], tc["sessions"]], axis=-1),
        text=[f"{v:.0%}" for v in tc["success"]], textposition="outside", cliponaxis=False, textfont=dict(color=T.INK2, size=12),
        hovertemplate="%{x}<br><b>%{y:.1%}</b> resolved<br>%{customdata[0]} agents · %{customdata[1]:,} sessions<extra></extra>"))
    style(fig, height=height, top=20)
    fig.update_yaxes(tickformat=".0%", range=[0, max(0.9, float(tc["success"].max()) + 0.12)])
    return round_bars(fig)
