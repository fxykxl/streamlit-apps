"""Plotly figure builders. Every function returns a styled go.Figure; pages just call show(fig).

Colour carries meaning throughout: emerald = good / resolved, rose = bad / failed,
amber = warning, indigo -> cyan gradients for ordered categories, and one accent per metric.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.colors import sample_colorscale
from plotly.subplots import make_subplots

from . import theme as T
from .theme import rgba

USER_COLORS = {"Agent": T.INDIGO, "Customer": T.CYAN}
INDIGO_DEEP = "#3f3699"
INDIGO_SOFT = "#a59bff"
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _scale(colors: list[str]) -> list[list]:
    n = len(colors) - 1
    return [[i / n, c] for i, c in enumerate(colors)]


COOL = _scale(["#1a1f45", "#2c2a6e", "#4a40b0", "#7c6cff", "#b9b0ff"])
HEAT = _scale(T.RAMP_HEAT)
RYG = _scale([T.ROSE, T.ORANGE, T.AMBER, "#a3d977", T.EMERALD])
DIV = _scale(T.DIVERGING)

METRICS = {  # label -> (column, hover format, tick format, y-from-zero, colour)
    "Success rate": ("success", "%{y:.1%}", ".0%", False, T.INDIGO),
    "Click-through": ("ctr", "%{y:.1%}", ".0%", False, T.CYAN),
    "Zero-result rate": ("zero", "%{y:.1%}", ".0%", True, T.ROSE),
    "Time to first click": ("ttfc", "%{y:.1f}s", ".0f", True, T.AMBER),
    "Search volume": ("searches", "%{y:,.0f}", ",.0f", True, T.EMERALD),
}


def gradient(n: int, a: str = T.INDIGO, b: str = T.CYAN) -> list[str]:
    if n <= 1:
        return [a] * max(n, 0)
    return sample_colorscale([[0, a], [1, b]], [i / (n - 1) for i in range(n)], colortype="rgb")


def style(fig: go.Figure, height: int = 320, legend: bool = False, hover: str = "closest",
          top: int = 8, left: int = 4) -> go.Figure:
    fig.update_layout(
        height=height, margin=dict(l=left, r=10, t=top, b=4), showlegend=legend, hovermode=hover,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", colorway=T.SERIES, bargap=0.32,
        font=dict(family=T.FONT, color=T.INK2, size=12),
        hoverlabel=dict(bgcolor=T.HOVER_BG, bordercolor=T.AXIS, font=dict(family=T.FONT, color=T.INK, size=12.5),
                        align="left"),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0, itemsizing="constant",
                    font=dict(color=T.INK2, size=12), bgcolor="rgba(0,0,0,0)"),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=T.AXIS, ticks="", tickfont=dict(color=T.MUTED),
                     showspikes=False, automargin=True)
    fig.update_yaxes(gridcolor=T.GRID, griddash="dot", zeroline=False, linecolor="rgba(0,0,0,0)", ticks="",
                     tickfont=dict(color=T.MUTED), automargin=True, ticklabelstandoff=6)
    return fig


def round_bars(fig: go.Figure, radius: int = 6) -> go.Figure:
    try:  # needs a recent Plotly; silently skipped otherwise
        fig.update_traces(marker_cornerradius=radius, selector=dict(type="bar"))
    except Exception:
        pass
    return fig


def _area_fill(trace_kwargs: dict, color: str, alpha: float = 0.30) -> dict:
    """Vertical gradient fill under a line (falls back to a flat tint on old Plotly)."""
    try:
        go.Scatter(fillgradient=dict(type="vertical", colorscale=[[0, rgba(color, 0)], [1, rgba(color, alpha)]]))
        trace_kwargs["fillgradient"] = dict(type="vertical", colorscale=[[0, rgba(color, 0)], [1, rgba(color, alpha)]])
    except Exception:
        trace_kwargs["fillcolor"] = rgba(color, alpha / 3)
    return trace_kwargs


def add_events(fig: go.Figure, events: pd.DataFrame, x0, x1, labels: bool = True) -> None:
    n = 0
    for e in events.itertuples():
        if e.end < x0 or e.start > x1:
            continue
        color = T.EVENT_COLORS.get(e.kind, T.MUTED)
        s = max(e.start, x0)
        en = min(e.end + pd.Timedelta(days=1), x1 + pd.Timedelta(days=1))
        fig.add_shape(type="rect", xref="x", yref="paper", x0=s.strftime("%Y-%m-%d"), x1=en.strftime("%Y-%m-%d"),
                      y0=0, y1=1, fillcolor=color, opacity=0.13, line_width=0, layer="below")
        fig.add_shape(type="line", xref="x", yref="paper", x0=s.strftime("%Y-%m-%d"), x1=s.strftime("%Y-%m-%d"),
                      y0=0, y1=1, line=dict(color=rgba(color, .55), width=1, dash="dot"), layer="below")
        if labels:
            fig.add_annotation(x=s.strftime("%Y-%m-%d"), xref="x", y=1, yref="paper", text=f"● {e.label}",
                               showarrow=False, xanchor="left", yanchor="bottom", yshift=4 + 16 * (n % 2),
                               font=dict(size=11, color=color))
        n += 1


# ------------------------------------------------------------------ executive
def trend_chart(tr: pd.DataFrame, metric: str, events: pd.DataFrame, freq: str, height: int = 370) -> go.Figure:
    col, hover, tick, zero, _ = METRICS[metric]
    color = T.INDIGO
    fig = go.Figure()
    many = len(tr) > 60
    when = "Week of %{x|%b %d}" if freq == "Weekly" else "%{x|%a, %b %d}"
    kw = dict(x=tr["bucket"], y=tr[col], mode="lines" if many else "lines+markers", name=metric, fill="tozeroy",
              line=dict(color=color, width=2.6, shape="spline", smoothing=0.5),
              marker=dict(size=7, color=color, line=dict(color=T.SURFACE, width=2)),
              hovertemplate=f"{when}<br><b>{hover}</b><extra></extra>")
    fig.add_trace(go.Scatter(**_area_fill(kw, color)))
    style(fig, height=height, hover="x", top=62)
    vals = tr[col].dropna()
    if zero or vals.empty:
        fig.update_yaxes(rangemode="tozero", tickformat=tick)
    else:
        fig.update_yaxes(range=[max(0, vals.min() - 0.08), min(1.0, vals.max() + 0.05)], tickformat=tick)
    if len(tr):
        add_events(fig, events, tr["bucket"].min(), tr["bucket"].max() + pd.Timedelta(days=6 if freq == "Weekly" else 0))
    return fig


def area_bars(df: pd.DataFrame, avg: float, height: int = 370) -> go.Figure:
    d = df.sort_values("success")  # worst first -> top once the axis is reversed
    fig = go.Figure(go.Bar(
        x=d["success"], y=d["product_area"], orientation="h",
        marker=dict(color=[T.ROSE if v < avg - 0.03 else T.INDIGO for v in d["success"]], line=dict(width=0)),
        text=[f"{v:.0%}" for v in d["success"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=T.INK, size=12), customdata=np.stack([d["sessions"], (d["success"] - avg) * 100], axis=-1),
        hovertemplate="<b>%{y}</b><br>%{x:.1%} resolved (%{customdata[1]:+.1f} pts vs overall)"
                      "<br>%{customdata[0]:,} sessions<extra></extra>"))
    style(fig, height=height, left=0, top=26)
    fig.update_xaxes(range=[0, 1.1], tickformat=".0%", showgrid=True, gridcolor=T.GRID, griddash="dot")
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=T.INK2, size=12))
    fig.add_vline(x=avg, line_width=1.5, line_dash="dot", line_color=T.INK2)
    fig.add_annotation(x=avg, y=1, yref="paper", text=f"overall {avg:.0%}", showarrow=False, yanchor="bottom",
                       font=dict(size=11, color=T.INK2), bgcolor=T.SURFACE)
    return round_bars(fig)


def impact_chart(imp: pd.DataFrame, height: int = 300) -> go.Figure:
    names = {True: "Answer found", False: "No answer found"}
    colors = {True: T.INDIGO, False: T.ROSE}
    specs = [("res_hours", "Median hours to resolve", "{:.0f} h"), ("escalation", "Escalation rate", "{:.0%}"),
             ("csat", "Average CSAT (1–5)", "{:.2f}")]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[s[1] for s in specs], horizontal_spacing=0.08)
    for ci, (col, _, fmt) in enumerate(specs, start=1):
        for found in (True, False):
            if found not in imp.index:
                continue
            v = float(imp.loc[found, col])
            fig.add_trace(go.Bar(x=[names[found]], y=[v], name=names[found], legendgroup=names[found],
                                 showlegend=(ci == 1), marker=dict(color=colors[found], line=dict(width=0)),
                                 text=[fmt.format(v)], textposition="outside", cliponaxis=False,
                                 textfont=dict(color=T.INK, size=13),
                                 hovertemplate=f"{names[found]}<br><b>{fmt.format(v)}</b><extra></extra>"),
                          row=1, col=ci)
    style(fig, height=height, legend=True, top=78)
    fig.update_layout(bargap=0.22, legend=dict(y=1.2))
    fig.update_yaxes(showgrid=False, showticklabels=False, rangemode="tozero")
    fig.update_xaxes(showticklabels=False)
    fig.update_annotations(font=dict(size=12, color=T.INK2))
    for ci, (col, _, _) in enumerate(specs, start=1):
        top = float(imp[col].max()) if col in imp else 1
        fig.update_yaxes(range=[0, top * 1.24], row=1, col=ci)
    return round_bars(fig, 8)


# ------------------------------------------------------------------ search performance
def funnel_chart(f: dict, height: int = 340) -> go.Figure:
    stages = ["Searches", "Returned results", "Got a click", "Found an answer"]
    vals = [f["searches"], f["results"], f["clicked"], f["resolved"]]
    fig = go.Figure(go.Funnel(
        y=stages, x=vals, texttemplate="<b>%{value:,.0f}</b><br>%{percentInitial:.0%}", textposition="inside",
        textfont=dict(color="#ffffff", size=13, family=T.FONT),
        marker=dict(color=gradient(4, T.INDIGO, INDIGO_DEEP), line=dict(width=0)),
        connector=dict(line=dict(color=T.GRID, width=1), fillcolor=rgba(T.INDIGO, 0.10)),
        hovertemplate="<b>%{y}</b><br>%{x:,.0f} searches · %{percentInitial:.1%} of all<extra></extra>"))
    style(fig, height=height, left=0)
    fig.update_yaxes(tickfont=dict(color=T.INK2, size=12))
    return fig


def ttfc_distribution(s: pd.DataFrame, height: int = 340) -> go.Figure:
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
        c = USER_COLORS[u]
        kw = dict(x=centers, y=pct, mode="lines", name=label, fill="tozeroy",
                  line=dict(color=c, width=2.6, shape="spline", smoothing=0.7),
                  hovertemplate=f"{label}<br>%{{x:.0f}}s · <b>%{{y:.1f}}%</b> of clicks<extra></extra>")
        fig.add_trace(go.Scatter(**_area_fill(kw, c, 0.35)))
        med = float(x.median())
        fig.add_vline(x=med, line_dash="dot", line_color=c, line_width=1.5)
        fig.add_annotation(x=med, y=1, yref="paper", text=f"median {med:.0f}s", showarrow=False, xanchor="left",
                           xshift=4, yanchor="top", yshift=-4 - 18 * users.index(u), font=dict(size=11, color=c))
    style(fig, height=height, legend=len(users) > 1, hover="x", top=30)
    fig.update_xaxes(title=dict(text="Seconds from query to first click", font=dict(size=11, color=T.MUTED)),
                     ticksuffix="s")
    fig.update_yaxes(ticksuffix="%", rangemode="tozero")
    return fig


def position_bars(pos: pd.DataFrame, height: int = 340) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=pos["label"], y=pos["share"], marker=dict(color=gradient(len(pos), T.INDIGO, INDIGO_DEEP), line=dict(width=0)),
        text=[f"{v:.0%}" if v >= 0.005 else "" for v in pos["share"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=T.INK, size=12),
        hovertemplate="Position %{x}<br><b>%{y:.1%}</b> of clicks<extra></extra>"))
    style(fig, height=height, top=20)
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    fig.update_xaxes(title=dict(text="Rank of the clicked result", font=dict(size=11, color=T.MUTED)))
    return round_bars(fig)


def latency_chart(tr: pd.DataFrame, events: pd.DataFrame, height: int = 340) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=tr["bucket"], y=tr["p50"], mode="lines", name="Median",
                             line=dict(color=T.INDIGO, width=2.4),
                             hovertemplate="Median · <b>%{y:,.0f} ms</b><extra></extra>"))
    fig.add_trace(go.Scatter(x=tr["bucket"], y=tr["p95"], mode="lines", name="95th percentile",
                             line=dict(color=T.ROSE, width=2.2), fill="tonexty", fillcolor=rgba(T.ROSE, 0.07),
                             hovertemplate="p95 · <b>%{y:,.0f} ms</b><extra></extra>"))
    style(fig, height=height, legend=True, hover="x unified", top=44)
    fig.update_layout(legend=dict(y=-0.1, yanchor="top", x=0.5, xanchor="center"), margin=dict(b=10))
    fig.update_xaxes(hoverformat="%a, %b %d")
    fig.update_yaxes(rangemode="tozero", ticksuffix=" ms")
    if len(tr):
        add_events(fig, events, tr["bucket"].min(), tr["bucket"].max())
    return fig


def heatmap(pv: pd.DataFrame, height: int = 340) -> go.Figure:
    z = pv.values.astype(float)
    ok = np.isfinite(z).any()
    fig = go.Figure(go.Heatmap(
        z=z, x=[f"{h:02d}" for h in range(24)], y=DAYS, colorscale=COOL, xgap=3, ygap=3, hoverongaps=False,
        zmin=float(np.nanmin(z)) if ok else 0, zmax=float(np.nanmax(z)) if ok else 1,
        colorbar=dict(tickformat=".0%", thickness=10, len=0.9, outlinewidth=0, tickfont=dict(color=T.MUTED, size=11)),
        hovertemplate="%{y} %{x}:00<br><b>%{z:.0%}</b> of sessions resolved<extra></extra>"))
    style(fig, height=height, left=0)
    fig.update_yaxes(autorange="reversed", showgrid=False, tickfont=dict(color=T.INK2))
    fig.update_xaxes(title=dict(text="Hour of day (ET)", font=dict(size=11, color=T.MUTED)), dtick=2, linecolor="rgba(0,0,0,0)")
    return fig


def searches_per_session(g: pd.DataFrame, height: int = 340) -> go.Figure:
    fig = go.Figure()
    for name, col, color in (("Found an answer", "found", T.INDIGO), ("Gave up / no answer", "gave_up", T.ROSE)):
        fig.add_trace(go.Bar(x=g["label"], y=g[col], name=name, marker=dict(color=color, line=dict(color=T.SURFACE, width=2)),
                             texttemplate="%{y:.0%}", textposition="inside", insidetextanchor="middle",
                             textfont=dict(color="#ffffff", size=12),
                             hovertemplate=f"{name}<br>%{{x}}: <b>%{{y:.1%}}</b> of sessions<extra></extra>"))
    style(fig, height=height, legend=True, top=34)
    fig.update_layout(barmode="stack", legend=dict(traceorder="normal"))
    fig.update_xaxes(tickangle=0, tickfont=dict(size=11))
    fig.update_yaxes(tickformat=".0%", rangemode="tozero")
    return round_bars(fig, 4)


# ------------------------------------------------------------------ content gaps
def gap_treemap(tt: pd.DataFrame, height: int = 430) -> go.Figure:
    d = tt[tt["failed"] > 0]
    fig = px.treemap(d, path=[px.Constant("All areas"), "product_area", "topic"], values="failed",
                     color="fail_rate", color_continuous_scale=HEAT,
                     range_color=(float(d["fail_rate"].min()), float(d["fail_rate"].max())))
    fig.update_traces(root_color=T.SURFACE, marker=dict(line=dict(width=2, color=T.SURFACE), cornerradius=6),
                      textfont=dict(family=T.FONT, size=13, color="#ffffff"),
                      texttemplate="<b>%{label}</b><br>%{value:,}",
                      hovertemplate="<b>%{label}</b><br>%{value:,} failed sessions<br>failure rate %{color:.0%}<extra></extra>")
    fig.update_coloraxes(showscale=False)
    fig.update_layout(uniformtext=dict(minsize=10, mode="hide"))
    return style(fig, height=height, left=0, top=0)


def launch_chart(s: pd.DataFrame, ses: pd.DataFrame, area: str, events: pd.DataFrame, height: int = 410) -> go.Figure:
    sa, ea = s[s["product_area"] == area], ses[ses["product_area"] == area]
    vol = sa.groupby("week").agg(searches=("search_id", "size"), zero=("zero_result", "mean"))
    suc = ea.groupby("week")["resolved"].mean().rename("success")
    d = vol.join(suc).reset_index()
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.45, 0.55], vertical_spacing=0.09)
    fig.add_trace(go.Bar(x=d["week"], y=d["searches"], name="Searches per week",
                         marker=dict(color=gradient(len(d), "#4b3fb8", T.INDIGO), line=dict(width=0)),
                         hovertemplate="Week of %{x|%b %d}<br><b>%{y:,} searches</b><extra></extra>"), row=1, col=1)
    for name, col, color in (("Zero-result rate", "zero", T.ROSE), ("Session success", "success", T.EMERALD)):
        fig.add_trace(go.Scatter(x=d["week"], y=d[col], mode="lines+markers", name=name,
                                 line=dict(color=color, width=2.4, shape="spline", smoothing=0.4),
                                 marker=dict(size=6, color=color, line=dict(color=T.SURFACE, width=2)),
                                 hovertemplate=f"{name}<br>Week of %{{x|%b %d}} · <b>%{{y:.0%}}</b><extra></extra>"),
                      row=2, col=1)
    style(fig, height=height, legend=True, hover="x", top=44)
    fig.update_layout(legend=dict(y=-0.08, yanchor="top", x=0.5, xanchor="center"), margin=dict(b=10))
    fig.update_yaxes(tickformat=".0%", rangemode="tozero", row=2, col=1)
    fig.update_yaxes(rangemode="tozero", row=1, col=1)
    if len(d):
        add_events(fig, events, d["week"].min(), d["week"].max() + pd.Timedelta(days=6))
    return round_bars(fig, 4)


def hbar(labels, values, height: int = 360, fmt: str = "{:,.0f}", color=T.INDIGO, hover_unit: str = "") -> go.Figure:
    values = list(values)
    fig = go.Figure(go.Bar(
        x=values, y=list(labels), orientation="h", marker=dict(color=color, line=dict(width=0)),
        text=[fmt.format(v) for v in values], textposition="outside", cliponaxis=False,
        textfont=dict(color=T.INK, size=12),
        hovertemplate=f"<b>%{{y}}</b><br>%{{x:,.0f}} {hover_unit}<extra></extra>"))
    style(fig, height=height, left=0)
    fig.update_xaxes(showgrid=False, showticklabels=False, rangemode="tozero",
                     range=[0, (max(values) if values else 1) * 1.15])
    fig.update_yaxes(autorange="reversed", tickfont=dict(color=T.INK2, size=12))
    return round_bars(fig)


# ------------------------------------------------------------------ agents
TEAM_COLORS = [T.INDIGO, T.CYAN, T.AMBER, T.PINK]


def agent_facets(at: pd.DataFrame, height: int = 540) -> go.Figure:
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
            x=d["ttfc"], y=d["success"], mode="markers+text", text=lab,
            textposition=np.where(d["ttfc"] < float(at["ttfc"].median()), "top right", "top left"),
            textfont=dict(size=11, color=T.INK), showlegend=False, customdata=cd,
            marker=dict(size=10 + 18 * np.sqrt(d["sessions"] / big), color=d["vs_team"], colorscale=DIV,
                        cmin=-0.12, cmax=0.12, opacity=0.95, line=dict(color=T.SURFACE, width=2),
                        showscale=(i == 0),
                        colorbar=dict(title=dict(text="vs team", font=dict(size=11, color=T.MUTED)), tickformat="+.0%",
                                      thickness=10, len=0.6, x=1.02, outlinewidth=0, tickfont=dict(color=T.MUTED, size=11))),
            hovertemplate="<b>%{customdata[0]}</b><br>Success %{y:.0%} (%{customdata[3]:+.1f} pts vs team)"
                          "<br>%{x:.1f}s to first click<br>%{customdata[1]:,} sessions · %{customdata[2]} mo tenure"
                          "<extra></extra>"), row=i // cols + 1, col=i % cols + 1)
    style(fig, height=height, top=30)
    # pad both axes so labels on the extreme dots are never clipped
    dd = at.dropna(subset=["ttfc"])
    if len(dd):
        x0, x1 = float(dd["ttfc"].min()), float(dd["ttfc"].max())
        y0, y1 = float(dd["success"].min()), float(dd["success"].max())
        px_, py_ = max((x1 - x0) * 0.14, 0.4), max((y1 - y0) * 0.16, 0.03)
        fig.update_xaxes(range=[x0 - px_, x1 + px_])
        fig.update_yaxes(range=[y0 - py_, y1 + py_ * 1.4])
    fig.update_yaxes(tickformat=".0%", showgrid=True)
    fig.update_xaxes(ticksuffix="s", showgrid=True, gridcolor=T.GRID, griddash="dot")
    for k, a in enumerate(fig.layout.annotations):
        a.font = dict(size=12.5, color=T.INK)
    fig.add_hline(y=float(at["success"].median()), line_dash="dot", line_color=T.AXIS, row="all", col="all")
    return fig


def tenure_bars(tc: pd.DataFrame, height: int = 300) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=tc["tenure_band"].astype(str), y=tc["success"],
        marker=dict(color=gradient(len(tc), INDIGO_DEEP, INDIGO_SOFT), line=dict(width=0)),
        customdata=np.stack([tc["agents"], tc["sessions"]], axis=-1),
        text=[f"{v:.0%}" for v in tc["success"]], textposition="outside", cliponaxis=False,
        textfont=dict(color=T.INK, size=12),
        hovertemplate="%{x}<br><b>%{y:.1%}</b> resolved<br>%{customdata[0]} agents · %{customdata[1]:,} sessions<extra></extra>"))
    style(fig, height=height, top=20)
    fig.update_yaxes(tickformat=".0%", range=[0, max(0.9, float(tc["success"].max()) + 0.12)])
    return round_bars(fig)
