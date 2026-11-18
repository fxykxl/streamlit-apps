"""Page 4 - support agent effectiveness."""
from __future__ import annotations

import numpy as np
import streamlit as st

from .. import charts, metrics
from .. import theme as T
from ..components import render_kpis


def _wavg(at, col, w="sessions"):
    d = at.dropna(subset=[col])
    return float(np.average(d[col], weights=d[w])) if len(d) and d[w].sum() else float("nan")


def _summary(at) -> dict:
    return dict(agents=len(at), success=_wavg(at, "success"), ttfc=_wavg(at, "ttfc"),
                spc=_wavg(at, "searches_per_case", "cases"), found=_wavg(at, "found", "cases"))


KPI_SPECS = [
    dict(key="agents", label="Active agents", kind="int", better="neutral", desc="With searches in the period"),
    dict(key="success", label="Search success", kind="pct", better="up", desc="Sessions resolved by agents"),
    dict(key="ttfc", label="Time to first click", kind="sec", better="down", desc="Median, session-weighted"),
    dict(key="spc", label="Searches per case", kind="num", better="down", desc="Effort to find an answer"),
    dict(key="found", label="Cases with an answer found", kind="pct", better="up", desc="Cases where search resolved"),
]


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Agent effectiveness",
                  "Are support agents finding what they need, fast enough, and does it change case outcomes?", ctx.chips)
    st.caption("This page always analyses support-agent searches; the sidebar “Who is searching” filter does not apply.")
    if ctx.ses_agents.empty:
        st.info("No agent activity in this selection.")
        return

    teams = ["All teams"] + sorted(ctx.agents["team"].unique())
    team = st.selectbox("Team", teams, key="ag_team")
    cases, ses, s = ctx.cases, ctx.ses_agents, ctx.s_agents
    if team != "All teams":
        ids = ctx.agents.loc[ctx.agents["team"] == team, "agent_id"]
        ses, s, cases = ses[ses["agent_id"].isin(ids)], s[s["agent_id"].isin(ids)], cases[cases["agent_id"].isin(ids)]
    at = metrics.agent_table(ses, s, cases, ctx.agents)
    if at.empty:
        st.info("No agent activity for this team in the selected period.")
        return

    render_kpis(KPI_SPECS, _summary(at), None, "", None)
    st.write("")

    a, b = st.columns([5, 3], gap="medium")
    with a, st.container(border=True):
        T.card_title("What a good search is worth",
                     "Cases split by whether the agent found an answer in the knowledge base.")
        imp = metrics.case_impact(cases)
        if len(imp) == 2:
            T.show(charts.impact_chart(imp, height=300), key="ag_impact")
        else:
            st.info("Not enough cases.")
    with b, st.container(border=True):
        T.card_title("Ramp-up curve", "Search success by agent tenure")
        tc = metrics.tenure_curve(at)
        if len(tc):
            T.show(charts.tenure_bars(tc), key="ag_tenure")

    c, d = st.columns([5, 3], gap="medium")
    with c, st.container(border=True):
        T.card_title("Speed vs. success, by team",
                     "Each dot is an agent (size = sessions). Best and weakest per team are labelled; dotted line = overall median.")
        T.show(charts.agent_facets(at), key="ag_scatter")
    with d, st.container(border=True):
        T.card_title("Coaching shortlist", "Agents well below their team's median, with enough volume to be meaningful")
        short = at[(at["vs_team"] <= -0.06) & (at["sessions"] >= 100)].sort_values("vs_team").head(8)
        if short.empty:
            st.success("Nobody is far behind their team. Nothing to flag.")
        else:
            short = short.assign(vs=short["vs_team"] * 100, success=short["success"] * 100)
            T.show_table(
                short[["name", "team", "tenure_months", "success", "vs"]].rename(columns={
                    "name": "Agent", "team": "Team", "tenure_months": "Tenure (mo)", "success": "Success", "vs": "vs team"}),
                column_config={"Success": st.column_config.NumberColumn(format="%.0f%%"),
                               "vs team": st.column_config.NumberColumn(format="%+.1f pts")})

    with st.container(border=True):
        T.card_title("Agent leaderboard", "Sorted by search success. Compare agents within a team; teams handle different topics.")
        t = at.assign(success=at["success"] * 100, vs_team=at["vs_team"] * 100, escalation=at["escalation"] * 100)
        T.show_table(
            t[["name", "team", "tenure_months", "sessions", "success", "vs_team", "ttfc", "searches_per_case",
               "escalation", "res_hours", "csat"]].rename(columns={
                "name": "Agent", "team": "Team", "tenure_months": "Tenure (mo)", "sessions": "Sessions",
                "success": "Success", "vs_team": "vs team", "ttfc": "Time to click (s)",
                "searches_per_case": "Searches / case", "escalation": "Escalated",
                "res_hours": "Median hrs to resolve", "csat": "CSAT"}),
            column_config={
                "Success": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100),
                "vs team": st.column_config.NumberColumn(format="%+.1f pts"),
                "Time to click (s)": st.column_config.NumberColumn(format="%.1f"),
                "Searches / case": st.column_config.NumberColumn(format="%.2f"),
                "Escalated": st.column_config.NumberColumn(format="%.0f%%"),
                "Median hrs to resolve": st.column_config.NumberColumn(format="%.1f"),
                "CSAT": st.column_config.NumberColumn(format="%.2f"),
                "Sessions": st.column_config.NumberColumn(format="%d"),
            })
