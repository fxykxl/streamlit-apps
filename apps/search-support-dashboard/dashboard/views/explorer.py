"""Page 5 - query explorer (drill-through to the raw searches)."""
from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from .. import theme as T

OUTCOMES = ["All outcomes", "🚫 Zero results", "👀 No click", "↩ Clicked, not resolved", "✅ Resolved"]


def _with_outcome(df: pd.DataFrame) -> pd.DataFrame:
    out = np.select([df["zero_result"], df["resolved"], df["clicked"]],
                    ["🚫 Zero results", "✅ Resolved", "↩ Clicked, not resolved"], default="👀 No click")
    return df.assign(outcome=out)


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Query explorer",
                  "Drill through from a metric to the actual queries, results and sessions behind it.", ctx.chips)
    if ctx.s.empty:
        st.info("No searches match the current filters.")
        return

    names = ctx.agents.set_index("agent_id")["name"]
    titles = ctx.articles.set_index("article_id")["title"]
    s = _with_outcome(ctx.s)

    tab1, tab2, tab3 = st.tabs(["Top queries", "Search log", "Session replay"])

    with tab1:
        c1, c2 = st.columns([1, 3])
        min_n = c1.slider("Minimum searches", 1, 100, 10, key="ex_minq")
        g = s.groupby("query_norm").agg(searches=("search_id", "size"), ctr=("clicked", "mean"),
                                        zero=("zero_result", "mean"), resolved=("resolved", "mean"),
                                        results=("n_results", "mean"), area=("product_area", "first"))
        g = g[g["searches"] >= min_n].sort_values("searches", ascending=False).head(300).reset_index()
        g = g.assign(ctr=g["ctr"] * 100, zero=g["zero"] * 100, resolved=g["resolved"] * 100)
        c2.markdown(f"**{len(g):,}** queries with at least {min_n} searches (top 300 shown)")
        T.show_table(
            g[["query_norm", "area", "searches", "ctr", "zero", "resolved", "results"]].rename(columns={
                "query_norm": "Query", "area": "Area", "searches": "Searches", "ctr": "CTR", "zero": "Zero-result",
                "resolved": "Resolved", "results": "Avg results"}),
            column_config={
                "Searches": st.column_config.NumberColumn(format="%d"),
                "CTR": st.column_config.NumberColumn(format="%.0f%%"),
                "Zero-result": st.column_config.NumberColumn(format="%.0f%%"),
                "Resolved": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100),
                "Avg results": st.column_config.NumberColumn(format="%.0f"),
            })

    with tab2:
        c1, c2, c3 = st.columns([3, 2, 2])
        text = c1.text_input("Query contains", placeholder="e.g. saml, invoice, webhook", key="ex_text")
        outcome = c2.selectbox("Outcome", OUTCOMES, key="ex_outcome")
        zero_only = c3.checkbox("Only queries with few results (≤ 3)", key="ex_few")
        f = s
        if text.strip():
            f = f[f["query_norm"].str.contains(text.strip().lower(), regex=False)]
        if outcome != "All outcomes":
            f = f[f["outcome"] == outcome]
        if zero_only:
            f = f[f["n_results"] <= 3]
        f = f.sort_values("timestamp", ascending=False)
        st.markdown(f"**{len(f):,}** searches match")
        log = pd.DataFrame({
            "Time": f["timestamp"], "Query": f["query"], "Area": f["product_area"], "Who": f["user_type"],
            "Agent": f["agent_id"].map(names), "Results": f["n_results"],
            "Clicked article": f["clicked_article_id"].map(titles), "Rank": f["click_position"],
            "Seconds to click": f["time_to_first_click_s"], "Outcome": f["outcome"]}).head(5000)
        T.show_table(log, column_config={
            "Time": st.column_config.DatetimeColumn(format="MMM DD, HH:mm"),
            "Results": st.column_config.NumberColumn(format="%d"),
            "Rank": st.column_config.NumberColumn(format="%d"),
            "Seconds to click": st.column_config.NumberColumn(format="%.1f"),
        })
        st.download_button("Download this view as CSV", data=log.head(50000).to_csv(index=False).encode("utf-8"),
                           file_name="search_log.csv", mime="text/csv", key="ex_dl")

    with tab3:
        multi = ctx.ses[ctx.ses["n_searches"] >= 3]
        if multi.empty:
            st.info("No multi-search sessions in this selection.")
        else:
            sample = multi.sample(min(40, len(multi)), random_state=7).sort_values("start_time")
            labels = {r.session_id: f"{r.session_id} · {r.start_time:%b %d %H:%M} · {r.product_area} · {r.n_searches} searches"
                      for r in sample.itertuples()}
            pick = st.selectbox("Pick a session with several searches", list(labels), format_func=labels.get, key="ex_sess")
            row = sample[sample["session_id"] == pick].iloc[0]
            who = row["agent_name"] if isinstance(row["agent_name"], str) else "Customer"
            verdict = "resolved" if row["resolved"] else "ended without an answer"
            st.markdown(f"**{who}** · {row['channel']} · {row['product_area']} · {row['n_searches']} searches over "
                        f"{row['duration_s']}s · **{verdict}**"
                        + (f" · case `{row['case_id']}`" if isinstance(row["case_id"], str) else ""))
            steps = s[s["session_id"] == pick].sort_values("round")
            T.show_table(pd.DataFrame({
                "Step": steps["round"], "Query": steps["query"], "Results": steps["n_results"],
                "Clicked article": steps["clicked_article_id"].map(titles), "Seconds to click": steps["time_to_first_click_s"],
                "Outcome": steps["outcome"]}),
                column_config={"Seconds to click": st.column_config.NumberColumn(format="%.1f")})
