"""Page 1 - executive overview."""
from __future__ import annotations

import streamlit as st

from .. import charts, metrics
from .. import theme as T
from ..components import render_kpis

KPI_SPECS = [
    dict(key="success", label="Search success rate", kind="pct", better="up", desc="Sessions ending in a resolving click"),
    dict(key="ctr", label="Click-through rate", kind="pct", better="up", desc="Searches with at least one click"),
    dict(key="zero", label="Zero-result rate", kind="pct", better="down", desc="Searches that returned nothing"),
    dict(key="ttfc", label="Time to first click", kind="sec", better="down", desc="Median, searches with a click"),
    dict(key="self_service", label="Self-service resolution", kind="pct", better="up", desc="Customer sessions, no case opened"),
]


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Executive overview",
                  "Are people finding what they're looking for, and what does it cost us when they don't?", ctx.chips)
    if ctx.s.empty:
        st.info("No searches match the current filters.")
        return

    k = metrics.kpis(ctx.s, ctx.ses)
    pk = metrics.kpis(ctx.ps, ctx.pses) if ctx.has_prev else None
    tr_w = metrics.trend(ctx.s, ctx.ses, "Weekly", ctx.start, ctx.end)

    sparks = {c: tr_w[c].tolist() for c in ("success", "ctr", "zero", "ttfc") if c in tr_w}
    cust = ctx.ses[ctx.ses["user_type"] == "Customer"]
    if len(cust):
        sparks["self_service"] = (cust.assign(v=cust["resolved"] & ~cust["case_created"])
                                  .groupby("week")["v"].mean().tolist())
    render_kpis(KPI_SPECS, k, pk, ctx.prev_label, sparks)
    st.write("")

    left, right = st.columns([5, 3], gap="medium")
    with left, st.container(border=True):
        T.card_title("Search performance over time",
                     "Shaded bands mark incidents, releases and content launches.")
        c1, c2 = st.columns([4, 1.5])
        metric = c1.radio("Metric", list(charts.METRICS), horizontal=True, label_visibility="collapsed", key="exec_metric")
        freq = c2.radio("Granularity", ["Weekly", "Daily"], horizontal=True, label_visibility="collapsed", key="exec_freq")
        tr = tr_w if freq == "Weekly" else metrics.trend(ctx.s, ctx.ses, "Daily")
        T.show(charts.trend_chart(tr, metric, ctx.events, freq), key="exec_trend")
    with right, st.container(border=True):
        T.card_title("Where people succeed", "Share of search sessions resolved · dotted line = overall")
        T.show(charts.area_bars(metrics.by_area(ctx.ses), k["success"]), key="exec_area")

    tt = metrics.topic_table(ctx.s, ctx.ses, ctx.articles, ctx.end)
    impact = metrics.case_impact(ctx.cases)
    at = metrics.agent_table(ctx.ses_agents, ctx.s_agents, ctx.cases, ctx.agents)
    insights = metrics.build_insights(ctx, k, tt, tr_w, impact, at)
    if insights:
        st.markdown("#### What the data says")
        for col, ins in zip(st.columns(len(insights), gap="small"), insights):
            col.markdown(T.insight_card(ins["tone"], ins["tag"], ins["headline"], ins["detail"]), unsafe_allow_html=True)
        st.write("")

    a, b = st.columns([1, 1], gap="medium")
    with a, st.container(border=True):
        T.card_title("Where users get stuck", "Topics with the most unresolved search sessions. Full list under Content gaps.")
        if len(tt):
            d = tt.head(8).copy()
            d["success"] = d["success"] * 100
            T.show_table(
                d[["topic", "product_area", "failed", "success", "gap_type"]].rename(columns={
                    "topic": "Topic", "product_area": "Area", "failed": "Failed sessions",
                    "success": "Resolved", "gap_type": "Diagnosis"}),
                column_config={"Resolved": st.column_config.ProgressColumn(
                    "Resolved", format="%.0f%%", min_value=0, max_value=100)})
    with b, st.container(border=True):
        T.card_title("What a failed search costs", "Support cases, split by whether the agent found an answer.")
        if len(impact) == 2:
            T.show(charts.impact_chart(impact, height=300), key="exec_impact")
        else:
            st.info("Not enough cases in this selection.")
