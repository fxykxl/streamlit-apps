"""Page 3 - content gaps (what are people looking for that we can't answer?)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from .. import charts, metrics
from .. import theme as T
from ..components import render_kpis

KPI_SPECS = [
    dict(key="zero", label="Zero-result rate", kind="pct", better="down", desc="Searches that returned nothing",
         accent=T.ROSE, icon="search_x"),
    dict(key="failed", label="Unresolved sessions", kind="int", better="down", desc="Sessions with no answer found",
         accent=T.ORANGE, icon="alert"),
    dict(key="gap_topics", label="Topics with no article", kind="int", better="down", desc="Demand with no content",
         accent=T.AMBER, icon="file_x"),
    dict(key="cases", label="Cases after failed search", kind="int", better="down",
         desc="Customers who gave up and wrote in", accent=T.PINK, icon="mail"),
]
ACTIONS = {
    "No article": ("bad", "Write new content", "topics have searches but no article at all."),
    "Vocabulary mismatch": ("warn", "Add synonyms / retitle", "topics have an article, yet queries return nothing."),
    "Weak content": ("info", "Rewrite weak articles", "topics get clicks but rarely resolve."),
}
DIAGNOSES = ["No article", "Vocabulary mismatch", "Weak content", "Recovered", "Healthy"]


def _kpis(s: pd.DataFrame, ses: pd.DataFrame, tt: pd.DataFrame) -> dict:
    return dict(zero=metrics._mean(s["zero_result"]), failed=int((~ses["resolved"]).sum()),
                gap_topics=int(((tt["gap_type"] == "No article")).sum()) if len(tt) else 0,
                cases=int(ses["case_created"].sum()))


@st.fragment
def _fix_first(tt: pd.DataFrame) -> None:
    """Filters here re-run only this card."""
    ctx = st.session_state["ctx"]
    with T.card("cg_fix"):
        T.card_title("Fix-first list", "Topics ranked by failed sessions. The trend shows weekly failed searches.",
                     "list", T.ROSE)
        f1, f2 = st.columns([3, 2], gap="medium")
        kinds = f1.multiselect("Diagnosis", DIAGNOSES, default=DIAGNOSES[:3], key="cg_kinds")
        min_s = f2.slider("Minimum sessions", 0, 300, 40, step=10, key="cg_min")
        d = tt[tt["gap_type"].isin(kinds) & (tt["sessions"] >= min_s)].head(20).copy()
        if d.empty:
            st.info("No topics match these filters. Lower the minimum or add a diagnosis.", icon=":material/search_off:")
            return
        weeks = sorted(ctx.s["week"].unique())
        spark = metrics.topic_weekly(ctx.s, d["topic"].tolist(), weeks)
        d["trend"] = d["topic"].map(spark)
        d["success"], d["zero"] = d["success"] * 100, d["zero"] * 100
        T.show_table(
            d[["topic", "product_area", "failed", "success", "zero", "articles", "gap_type", "trend"]].rename(columns={
                "topic": "Topic", "product_area": "Area", "failed": "Failed sessions", "success": "Resolved",
                "zero": "Zero-result", "articles": "Articles", "gap_type": "Diagnosis", "trend": "Weekly trend"}),
            column_config={
                "Failed sessions": st.column_config.NumberColumn(format="localized"),
                "Resolved": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100, color="green"),
                "Zero-result": st.column_config.NumberColumn(format="%.0f%%"),
                "Weekly trend": st.column_config.AreaChartColumn(y_min=0, color="red"),
            })


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Content gaps",
                  "What are people searching for that we can't answer, and what should we fix first?", ctx.chips)
    if ctx.s.empty:
        st.info("No searches match the current filters. Widen the period or clear the product-area filter.",
                icon=":material/filter_alt_off:")
        return

    tt = metrics.topic_table(ctx.s, ctx.ses, ctx.articles, ctx.end)
    k = _kpis(ctx.s, ctx.ses, tt)
    pk = None
    if ctx.has_prev and len(ctx.ps):
        ptt = metrics.topic_table(ctx.ps, ctx.pses, ctx.articles, ctx.start - pd.Timedelta(days=1))
        pk = _kpis(ctx.ps, ctx.pses, ptt)
    render_kpis(KPI_SPECS, k, pk, ctx.prev_label)

    # --- recommended actions
    T.section("Recommended actions", "Grouped by why searches fail", "bulb", T.AMBER)
    cols = st.columns(3, gap="small")
    for i, (col, (gtype, (tone, head, tail))) in enumerate(zip(cols, ACTIONS.items())):
        sub = tt[tt["gap_type"] == gtype]
        failed = int(sub["failed"].sum())
        col.markdown(T.insight_card(
            tone, gtype, f"{head}: {len(sub)} topics, {failed:,} failed sessions",
            f"{len(sub)} {tail}" if len(sub) else "Nothing to fix in this selection.", delay=i * 0.06),
            unsafe_allow_html=True)

    a, b = st.columns([3, 2], gap="medium")
    with a, T.card("cg_tree"):
        T.card_title("Unresolved demand map", "Tile size = failed sessions · warmer = higher failure rate",
                     "map", T.PINK)
        if len(tt):
            T.show(charts.gap_treemap(tt), key="cg_tree")
    with b, T.card("cg_type"):
        T.card_title("Failed sessions by diagnosis", "Why searches don't resolve", "bar", T.ORANGE)
        by = tt.groupby("gap_type")["failed"].sum().reindex(DIAGNOSES).fillna(0)
        T.show(charts.hbar(by.index, by.values, height=430, hover_unit="failed sessions",
                           color=[T.GAP_COLORS[g] for g in by.index]), key="cg_type")

    _fix_first(tt)

    # --- launch story + literal queries
    c, d2 = st.columns([3, 2], gap="medium")
    area = "Workflow & Automation"
    with c, T.card("cg_launch"):
        T.card_title(f"Demand vs. documentation: {area}",
                     "New feature launched before its docs: demand arrives immediately, resolution only after publishing.",
                     "rocket", T.VIOLET)
        if (ctx.s["product_area"] == area).sum() > 50:
            T.show(charts.launch_chart(ctx.s, ctx.ses, area, ctx.events), key="cg_launch")
        else:
            st.info(f"No {area} activity in this selection. Widen the period or the product-area filter.")
    with d2, T.card("cg_zero"):
        T.card_title("What people typed and got nothing", "Most frequent zero-result queries", "search_x", T.ROSE)
        zq = metrics.top_zero_queries(ctx.s, 12)
        if len(zq):
            T.show(charts.hbar(zq["query_norm"], zq["searches"], height=410, hover_unit="searches",
                               color=charts.gradient(len(zq), T.ROSE, T.AMBER)), key="cg_zero")

    # --- weak content
    with T.card("cg_weak"):
        T.card_title("Articles that get clicked but don't resolve",
                     "Only clicks where the article matches the topic searched. Low helpful-vote rate and old updates "
                     "are the usual suspects.", "file_edit", T.AMBER)
        at = metrics.article_table(ctx.s, ctx.articles, ctx.end)
        overall = float(ctx.ses["resolved"].mean())
        w = at[(at["clicks"] >= 40) & (at["resolve_rate"] < overall - 0.10)].sort_values("clicks", ascending=False).head(12)
        if w.empty:
            st.success("No weak articles in this selection.", icon=":material/check_circle:")
        else:
            w = w.assign(resolve_rate=w["resolve_rate"] * 100, helpful_rate=w["helpful_rate"] * 100)
            T.show_table(
                w[["title", "product_area", "clicks", "resolve_rate", "helpful_rate", "age_days"]].rename(columns={
                    "title": "Article", "product_area": "Area", "clicks": "Clicks", "resolve_rate": "Resolved after click",
                    "helpful_rate": "Helpful votes", "age_days": "Days since update"}),
                column_config={
                    "Clicks": st.column_config.NumberColumn(format="localized"),
                    "Resolved after click": st.column_config.ProgressColumn(format="%.0f%%", min_value=0,
                                                                            max_value=100, color="orange"),
                    "Helpful votes": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100,
                                                                     color="violet"),
                    "Days since update": st.column_config.NumberColumn(format="%d"),
                })
