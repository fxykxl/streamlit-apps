"""Page 2 - search performance (how well does the search engine itself behave?)."""
from __future__ import annotations

import streamlit as st

from .. import charts, highlights, metrics
from .. import theme as T
from ..components import render_kpis

KPI_SPECS = [
    dict(key="searches", label="Searches", kind="int", better="neutral", desc="Queries in the period",
         accent=T.INDIGO, icon="search"),
    dict(key="ctr", label="Click-through", kind="pct", better="up", desc="Searches with a click",
         accent=T.CYAN, icon="pointer"),
    dict(key="zero", label="Zero-result rate", kind="pct", better="down", desc="Searches that returned nothing",
         accent=T.ROSE, icon="search_x"),
    dict(key="p95_latency", label="p95 latency", kind="ms", better="down", desc="95th percentile response",
         accent=T.PINK, icon="zap"),
    dict(key="reform", label="Reformulation", kind="pct", better="down", desc="Searches followed by another",
         accent=T.AMBER, icon="repeat"),
]


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Search performance",
                  "How quickly and how reliably does search get people to a useful result?", ctx.chips)
    if ctx.s.empty:
        st.info("No searches match the current filters. Widen the period or clear the product-area filter.",
                icon=":material/filter_alt_off:")
        return

    k = metrics.kpis(ctx.s, ctx.ses)
    pk = metrics.kpis(ctx.ps, ctx.pses) if ctx.has_prev else None
    render_kpis(KPI_SPECS, k, pk, ctx.prev_label)

    daily = metrics.trend(ctx.s, ctx.ses, "Daily")
    pos = metrics.click_positions(ctx.s)
    T.insight_row(highlights.search_page(ctx.s, ctx.ses, daily, pos, ctx.events))

    a, b = st.columns(2, gap="medium")
    with a, T.card("sp_funnel"):
        T.card_title("Search funnel", "From query to a resolving click", "funnel", T.INDIGO)
        T.show(charts.funnel_chart(metrics.funnel(ctx.s)), key="sp_funnel")
    with b, T.card("sp_ttfc"):
        T.card_title("Time to first click", "How long people take to pick a result", "timer", T.AMBER)
        T.show(charts.ttfc_distribution(ctx.s), key="sp_ttfc")

    c, d = st.columns([2, 1], gap="medium")
    with c, T.card("sp_latency"):
        T.card_title("Response time", "Daily median and 95th percentile; spikes line up with index or release events",
                     "zap", T.PINK)
        T.show(charts.latency_chart(daily, ctx.events), key="sp_latency")
    with d, T.card("sp_pos"):
        T.card_title("Where people click", "Share of clicks by result rank", "pointer", T.CYAN)
        T.show(charts.position_bars(pos), key="sp_pos")

    e, f = st.columns([3, 2], gap="medium")
    with e, T.card("sp_heat"):
        T.card_title("When search works best", "Share of sessions resolved by weekday and hour (sparse cells hidden)",
                     "calendar", T.SKY)
        T.show(charts.heatmap(metrics.weekday_hour_success(ctx.ses)), key="sp_heat")
    with f, T.card("sp_effort"):
        T.card_title("Effort to find an answer", "Sessions by number of searches needed", "layers", T.EMERALD)
        T.show(charts.searches_per_session(metrics.searches_per_session(ctx.ses)), key="sp_effort")

    with T.card("sp_channel"):
        T.card_title("By channel", "Where the search box lives", "globe", T.VIOLET)
        ch = metrics.channel_table(ctx.s, ctx.ses)
        ch = ch.assign(ctr=ch["ctr"] * 100, zero=ch["zero"] * 100, success=ch["success"] * 100)
        T.show_table(
            ch[["channel", "searches", "sessions", "ctr", "zero", "success", "p95"]].rename(columns={
                "channel": "Channel", "searches": "Searches", "sessions": "Sessions", "ctr": "CTR",
                "zero": "Zero-result", "success": "Success", "p95": "p95 latency (ms)"}),
            column_config={
                "Searches": st.column_config.NumberColumn(format="localized"),
                "Sessions": st.column_config.NumberColumn(format="localized"),
                "CTR": st.column_config.NumberColumn(format="%.1f%%"),
                "Zero-result": st.column_config.NumberColumn(format="%.1f%%"),
                "Success": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100, color="green"),
                "p95 latency (ms)": st.column_config.NumberColumn(format="%d"),
            })
