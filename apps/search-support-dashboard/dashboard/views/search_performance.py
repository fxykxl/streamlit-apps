"""Page 2 - search performance (how well does the search engine itself behave?)."""
from __future__ import annotations

import streamlit as st

from .. import charts, metrics
from .. import theme as T
from ..components import render_kpis

KPI_SPECS = [
    dict(key="searches", label="Searches", kind="int", better="neutral", desc="Queries in the period"),
    dict(key="ctr", label="Click-through rate", kind="pct", better="up", desc="Searches with a click"),
    dict(key="zero", label="Zero-result rate", kind="pct", better="down", desc="Searches that returned nothing"),
    dict(key="p95_latency", label="p95 latency", kind="ms", better="down", desc="95th percentile response"),
    dict(key="reform", label="Reformulation rate", kind="pct", better="down", desc="Searches followed by another"),
]


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Search performance",
                  "How quickly and how reliably does search get people to a useful result?", ctx.chips)
    if ctx.s.empty:
        st.info("No searches match the current filters.")
        return

    k = metrics.kpis(ctx.s, ctx.ses)
    pk = metrics.kpis(ctx.ps, ctx.pses) if ctx.has_prev else None
    render_kpis(KPI_SPECS, k, pk, ctx.prev_label)
    st.write("")

    a, b = st.columns(2, gap="medium")
    with a, st.container(border=True):
        T.card_title("Search funnel", "From query to a resolving click")
        T.show(charts.funnel_chart(metrics.funnel(ctx.s)), key="sp_funnel")
    with b, st.container(border=True):
        T.card_title("Time to first click", "How long people take to pick a result")
        T.show(charts.ttfc_distribution(ctx.s), key="sp_ttfc")

    c, d = st.columns([2, 1], gap="medium")
    with c, st.container(border=True):
        T.card_title("Response time", "Daily median and 95th percentile; spikes line up with index or release events")
        T.show(charts.latency_chart(metrics.trend(ctx.s, ctx.ses, "Daily"), ctx.events), key="sp_latency")
    with d, st.container(border=True):
        T.card_title("Where people click", "Share of clicks by result rank")
        T.show(charts.position_bars(metrics.click_positions(ctx.s)), key="sp_pos")

    e, f = st.columns([3, 2], gap="medium")
    with e, st.container(border=True):
        T.card_title("When search works best", "Share of sessions resolved, by weekday and hour (cells with few sessions hidden)")
        T.show(charts.heatmap(metrics.weekday_hour_success(ctx.ses)), key="sp_heat")
    with f, st.container(border=True):
        T.card_title("Effort to find an answer", "Sessions by number of searches needed")
        T.show(charts.searches_per_session(metrics.searches_per_session(ctx.ses)), key="sp_effort")

    with st.container(border=True):
        T.card_title("By channel", "Where the search box lives")
        ch = metrics.channel_table(ctx.s, ctx.ses)
        ch = ch.assign(ctr=ch["ctr"] * 100, zero=ch["zero"] * 100, success=ch["success"] * 100)
        T.show_table(
            ch[["channel", "searches", "sessions", "ctr", "zero", "success", "p95"]].rename(columns={
                "channel": "Channel", "searches": "Searches", "sessions": "Sessions", "ctr": "CTR",
                "zero": "Zero-result", "success": "Success", "p95": "p95 latency (ms)"}),
            column_config={
                "Searches": st.column_config.NumberColumn(format="%d"),
                "Sessions": st.column_config.NumberColumn(format="%d"),
                "CTR": st.column_config.NumberColumn(format="%.1f%%"),
                "Zero-result": st.column_config.NumberColumn(format="%.1f%%"),
                "Success": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100),
                "p95 latency (ms)": st.column_config.NumberColumn(format="%d"),
            })
