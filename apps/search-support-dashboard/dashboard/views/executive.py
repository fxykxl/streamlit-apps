"""Page 1 - executive overview."""
from __future__ import annotations

import streamlit as st

from .. import charts, metrics
from .. import theme as T
from ..components import render_kpis

KPI_SPECS = [
    dict(key="success", label="Search success", kind="pct", better="up", desc="Sessions ending in a resolving click",
         accent=T.INDIGO, icon="target"),
    dict(key="ctr", label="Click-through", kind="pct", better="up", desc="Searches with at least one click",
         accent=T.CYAN, icon="pointer"),
    dict(key="zero", label="Zero-result rate", kind="pct", better="down", desc="Searches that returned nothing",
         accent=T.ROSE, icon="search_x"),
    dict(key="ttfc", label="Time to first click", kind="sec", better="down", desc="Median, searches with a click",
         accent=T.AMBER, icon="timer"),
    dict(key="self_service", label="Self-service", kind="pct", better="up", desc="Customer sessions, no case opened",
         accent=T.EMERALD, icon="user_check"),
]


@st.fragment
def _trend_card() -> None:
    """Re-runs on its own when the metric / granularity changes: the rest of the page stays put."""
    ctx = st.session_state["ctx"]
    with T.card("exec_trend"):
        T.card_title("Search performance over time",
                     "Shaded bands mark incidents, releases and content launches.", "activity", T.INDIGO)
        c1, c2 = st.columns([4, 1.4], vertical_alignment="center")
        with c1:
            metric = st.segmented_control("Metric", list(charts.METRICS), default="Success rate", required=True,
                                          label_visibility="collapsed", key="exec_metric")
        with c2:
            freq = st.segmented_control("Granularity", ["Weekly", "Daily"], default="Weekly", required=True,
                                        label_visibility="collapsed", key="exec_freq")
        tr = metrics.trend(ctx.s, ctx.ses, freq, ctx.start, ctx.end) if freq == "Weekly" \
            else metrics.trend(ctx.s, ctx.ses, "Daily")
        T.show(charts.trend_chart(tr, metric, ctx.events, freq), key="exec_trend_chart")


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Executive overview",
                  "Are people finding what they're looking for, and what does it cost us when they don't?", ctx.chips)
    if ctx.s.empty:
        st.info("No searches match the current filters. Widen the period or clear the product-area filter.",
                icon=":material/filter_alt_off:")
        return

    k = metrics.kpis(ctx.s, ctx.ses)
    pk = metrics.kpis(ctx.ps, ctx.pses) if ctx.has_prev else None
    tr_w = metrics.trend(ctx.s, ctx.ses, "Weekly", ctx.start, ctx.end)
    render_kpis(KPI_SPECS, k, pk, ctx.prev_label)

    tt = metrics.topic_table(ctx.s, ctx.ses, ctx.articles, ctx.end)
    impact = metrics.case_impact(ctx.cases)
    at = metrics.agent_table(ctx.ses_agents, ctx.s_agents, ctx.cases, ctx.agents)
    T.insight_row(metrics.build_insights(ctx, k, tt, tr_w, impact, at), "What the data says")

    left, right = st.columns([5, 3], gap="medium")
    with left:
        _trend_card()
    with right, T.card("exec_area"):
        T.card_title("Where people succeed", "Share of search sessions resolved, by product area", "grid", T.EMERALD)
        T.show(charts.area_bars(metrics.by_area(ctx.ses), k["success"], height=420), key="exec_area")

    a, b = st.columns(2, gap="medium")
    with a, T.card("exec_stuck"):
        T.card_title("Where users get stuck", "Topics with the most unresolved sessions. Full list under Content gaps.",
                     "triangle", T.ROSE)
        if len(tt):
            d = tt.head(8).copy()
            d["success"] = d["success"] * 100
            T.show_table(
                d[["topic", "product_area", "failed", "success", "gap_type"]].rename(columns={
                    "topic": "Topic", "product_area": "Area", "failed": "Failed sessions",
                    "success": "Resolved", "gap_type": "Diagnosis"}),
                column_config={
                    "Failed sessions": st.column_config.NumberColumn(format="localized"),
                    "Resolved": st.column_config.ProgressColumn(
                        "Resolved", format="%.0f%%", min_value=0, max_value=100, color="green")})
    with b, T.card("exec_cost"):
        T.card_title("What a failed search costs", "Support cases, split by whether the agent found an answer.",
                     "dollar", T.AMBER)
        if len(impact) == 2:
            T.show(charts.impact_chart(impact, height=330), key="exec_impact")
        else:
            st.info("Not enough cases in this selection.")
