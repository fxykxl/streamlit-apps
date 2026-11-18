"""Page 5 - query explorer (drill-through to the raw searches)."""
from __future__ import annotations

import html

import numpy as np
import pandas as pd
import streamlit as st

from .. import theme as T

ZERO, NOCLICK, CLICKED, RESOLVED = "Zero results", "No click", "Clicked, not resolved", "Resolved"
OUTCOME_STYLE = {ZERO: (T.ROSE, "search_x"), NOCLICK: (T.AMBER, "alert"),
                 CLICKED: (T.SKY, "pointer"), RESOLVED: (T.EMERALD, "check")}
OUTCOMES = ["All outcomes", ZERO, NOCLICK, CLICKED, RESOLVED]


def _with_outcome(df: pd.DataFrame) -> pd.DataFrame:
    out = np.select([df["zero_result"], df["resolved"], df["clicked"]], [ZERO, RESOLVED, CLICKED], default=NOCLICK)
    return df.assign(outcome=out)


def _badge(outcome: str) -> str:
    color, ico = OUTCOME_STYLE.get(outcome, (T.MUTED, "info"))
    return (f'<span class="badge" style="color:{color};background:{T.rgba(color, .14)}">'
            f'{T.icon(ico, 13, stroke=2.4)}{outcome}</span>')


@st.fragment
def _top_queries(s: pd.DataFrame) -> None:
    with T.card("ex_top"):
        T.card_title("Top queries", "Most frequent normalised queries and how they perform", "bar", T.INDIGO)
        c1, c2 = st.columns([1, 3], vertical_alignment="bottom")
        min_n = c1.slider("Minimum searches", 1, 100, 10, key="ex_minq")
        g = s.groupby("query_norm").agg(searches=("search_id", "size"), ctr=("clicked", "mean"),
                                        zero=("zero_result", "mean"), resolved=("resolved", "mean"),
                                        results=("n_results", "mean"), area=("product_area", "first"))
        g = g[g["searches"] >= min_n].sort_values("searches", ascending=False).head(300).reset_index()
        g = g.assign(ctr=g["ctr"] * 100, zero=g["zero"] * 100, resolved=g["resolved"] * 100)
        with c2:
            T.count(len(g), f"queries with at least {min_n} searches (top 300 shown)")
        T.show_table(
            g[["query_norm", "area", "searches", "ctr", "zero", "resolved", "results"]].rename(columns={
                "query_norm": "Query", "area": "Area", "searches": "Searches", "ctr": "CTR", "zero": "Zero-result",
                "resolved": "Resolved", "results": "Avg results"}),
            height=520,
            column_config={
                "Searches": st.column_config.NumberColumn(format="localized"),
                "CTR": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100, color="blue"),
                "Zero-result": st.column_config.NumberColumn(format="%.0f%%"),
                "Resolved": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100, color="green"),
                "Avg results": st.column_config.NumberColumn(format="%.0f"),
            })


@st.fragment
def _search_log(s: pd.DataFrame, names: pd.Series, titles: pd.Series) -> None:
    with T.card("ex_log"):
        T.card_title("Search log", "Every query in the current filters, newest first", "list", T.CYAN)
        c1, c2, c3 = st.columns([3, 2, 2], vertical_alignment="bottom")
        text = c1.text_input("Query contains", placeholder="e.g. saml, invoice, webhook", key="ex_text",
                             icon=":material/search:")
        outcome = c2.selectbox("Outcome", OUTCOMES, key="ex_outcome")
        few = c3.toggle("Only queries with few results (≤ 3)", key="ex_few")
        f = s
        if text.strip():
            f = f[f["query_norm"].str.contains(text.strip().lower(), regex=False)]
        if outcome != "All outcomes":
            f = f[f["outcome"] == outcome]
        if few:
            f = f[f["n_results"] <= 3]
        f = f.sort_values("timestamp", ascending=False)
        log = pd.DataFrame({
            "Time": f["timestamp"], "Query": f["query"], "Outcome": f["outcome"], "Area": f["product_area"],
            "Who": f["user_type"], "Agent": f["agent_id"].map(names), "Results": f["n_results"],
            "Clicked article": f["clicked_article_id"].map(titles), "Rank": f["click_position"],
            "Seconds to click": f["time_to_first_click_s"]}).head(5000)
        l, r = st.columns([3, 1], vertical_alignment="center")
        with l:
            T.count(len(f), "searches match" + (" (first 5,000 shown)" if len(f) > 5000 else ""))
        r.download_button("Download CSV", data=log.to_csv(index=False).encode("utf-8"), file_name="search_log.csv",
                          mime="text/csv", key="ex_dl", icon=":material/download:", width="stretch",
                          disabled=log.empty)
        if log.empty:
            st.info("No searches match. Try a shorter query or another outcome.", icon=":material/search_off:")
            return
        T.show_table(log, height=520, column_config={
            "Time": st.column_config.DatetimeColumn(format="MMM DD, HH:mm"),
            "Results": st.column_config.NumberColumn(format="%d"),
            "Rank": st.column_config.NumberColumn(format="%d"),
            "Seconds to click": st.column_config.NumberColumn(format="%.1f"),
        })


@st.fragment
def _replay(s: pd.DataFrame, titles: pd.Series) -> None:
    ctx = st.session_state["ctx"]
    with T.card("ex_replay"):
        T.card_title("Session replay", "Step through a real multi-search session to see where people get lost",
                     "repeat", T.PINK)
        multi = ctx.ses[ctx.ses["n_searches"] >= 3]
        if multi.empty:
            st.info("No multi-search sessions in this selection.")
            return
        sample = multi.sample(min(40, len(multi)), random_state=7).sort_values("start_time")
        labels = {r.session_id: f"{r.start_time:%b %d %H:%M} · {r.product_area} · {r.n_searches} searches · "
                                f"{'resolved' if r.resolved else 'no answer'}" for r in sample.itertuples()}
        pick = st.selectbox("Pick a session", list(labels), format_func=labels.get, key="ex_sess")
        row = sample[sample["session_id"] == pick].iloc[0]
        who = row["agent_name"] if isinstance(row["agent_name"], str) else "Customer"
        ok = bool(row["resolved"])
        verdict = _badge(RESOLVED) if ok else (f'<span class="badge" style="color:{T.ROSE};background:'
                                               f'{T.rgba(T.ROSE, .14)}">{T.icon("triangle", 13, stroke=2.4)}'
                                               f'Ended without an answer</span>')
        case = (f' · case <b>{html.escape(str(row["case_id"]))}</b>' if isinstance(row["case_id"], str) else "")
        st.markdown(f'<div class="replay">{T.icon("users", 15, T.CYAN)}<b>{html.escape(who)}</b> · '
                    f'{html.escape(str(row["channel"]))} · {html.escape(str(row["product_area"]))} · '
                    f'{row["n_searches"]} searches over {row["duration_s"]}s{case}<span style="flex:1"></span>'
                    f'{verdict}</div>', unsafe_allow_html=True)

        steps = s[s["session_id"] == pick].sort_values("round")
        items = []
        for i, r in enumerate(steps.itertuples()):
            color, _ = OUTCOME_STYLE.get(r.outcome, (T.MUTED, "info"))
            art = titles.get(r.clicked_article_id) if isinstance(r.clicked_article_id, str) else None
            secs = f" after {r.time_to_first_click_s:.1f}s" if r.time_to_first_click_s == r.time_to_first_click_s else ""
            click = (f'<div style="font-size:12.5px;color:{T.INK2};margin-top:4px">Clicked '
                     f'<b style="color:{T.INK}">{html.escape(str(art))}</b>{secs}</div>') if art else ""
            line = "" if i == len(steps) - 1 else (f'<div style="position:absolute;left:15px;top:34px;bottom:-14px;'
                                                   f'width:2px;background:{T.BORDER}"></div>')
            items.append(
                f'<div style="position:relative;display:flex;gap:14px;padding-bottom:14px">{line}'
                f'<div style="flex:none;width:32px;height:32px;border-radius:50%;display:grid;place-items:center;'
                f'font-weight:750;font-size:13px;color:{color};background:{T.rgba(color, .14)};'
                f'border:1px solid {T.rgba(color, .45)}">{r.round}</div>'
                f'<div style="flex:1;min-width:0;padding:8px 14px 10px;border-radius:12px;background:{T.SURFACE2};'
                f'border:1px solid {T.BORDER}"><div style="display:flex;flex-wrap:wrap;gap:8px;align-items:center;'
                f'justify-content:space-between"><span style="font-weight:650;color:{T.INK}">“{html.escape(str(r.query))}”'
                f'</span>{_badge(r.outcome)}</div><div style="font-size:12px;color:{T.MUTED};margin-top:2px">'
                f'{r.n_results} results</div>{click}</div></div>')
        st.markdown("".join(items), unsafe_allow_html=True)


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Query explorer",
                  "Drill through from a metric to the actual queries, results and sessions behind it.", ctx.chips)
    if ctx.s.empty:
        st.info("No searches match the current filters. Widen the period or clear the product-area filter.",
                icon=":material/filter_alt_off:")
        return

    names = ctx.agents.set_index("agent_id")["name"]
    titles = ctx.articles.set_index("article_id")["title"]
    s = _with_outcome(ctx.s)

    tab1, tab2, tab3 = st.tabs([":material/leaderboard: Top queries", ":material/list_alt: Search log",
                                ":material/replay: Session replay"])
    with tab1:
        _top_queries(s)
    with tab2:
        _search_log(s, names, titles)
    with tab3:
        _replay(s, titles)
