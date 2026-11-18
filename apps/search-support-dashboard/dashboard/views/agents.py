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
    dict(key="agents", label="Active agents", kind="int", better="neutral", desc="With searches in the period",
         accent=T.VIOLET, icon="users"),
    dict(key="success", label="Search success", kind="pct", better="up", desc="Sessions resolved by agents",
         accent=T.INDIGO, icon="target"),
    dict(key="ttfc", label="Time to first click", kind="sec", better="down", desc="Median, session-weighted",
         accent=T.AMBER, icon="timer"),
    dict(key="spc", label="Searches per case", kind="num", better="down", desc="Effort to find an answer",
         accent=T.CYAN, icon="layers"),
    dict(key="found", label="Cases answered", kind="pct", better="up", desc="Cases where search found an answer",
         accent=T.EMERALD, icon="check"),
]


@st.fragment
def _body() -> None:
    """Everything below the header; switching team re-runs only this part."""
    ctx = st.session_state["ctx"]
    teams = ["All teams"] + sorted(ctx.agents["team"].unique())
    team = st.segmented_control("Team", teams, default="All teams", required=True, key="ag_team",
                                label_visibility="collapsed")
    cases, ses, s = ctx.cases, ctx.ses_agents, ctx.s_agents
    if team != "All teams":
        ids = ctx.agents.loc[ctx.agents["team"] == team, "agent_id"]
        ses, s, cases = ses[ses["agent_id"].isin(ids)], s[s["agent_id"].isin(ids)], cases[cases["agent_id"].isin(ids)]
    at = metrics.agent_table(ses, s, cases, ctx.agents)
    if at.empty:
        st.info("No agent activity for this team in the selected period.", icon=":material/person_off:")
        return

    render_kpis(KPI_SPECS, _summary(at), None, "", None)

    a, b = st.columns([5, 3], gap="medium")
    with a, T.card("ag_impact"):
        T.card_title("What a good search is worth",
                     "Cases split by whether the agent found an answer in the knowledge base.", "dollar", T.EMERALD)
        imp = metrics.case_impact(cases)
        if len(imp) == 2:
            T.show(charts.impact_chart(imp, height=320), key="ag_impact")
        else:
            st.info("Not enough cases.")
    with b, T.card("ag_tenure"):
        T.card_title("Ramp-up curve", "Search success by agent tenure", "trend_up", T.VIOLET)
        tc = metrics.tenure_curve(at)
        if len(tc):
            T.show(charts.tenure_bars(tc, height=320), key="ag_tenure")

    c, d = st.columns([5, 3], gap="medium")
    with c, T.card("ag_scatter"):
        T.card_title("Speed vs. success, by team",
                     "Each dot is an agent (size = sessions, colour = vs team median). Best and weakest per team "
                     "are labelled.", "scatter", T.CYAN)
        T.show(charts.agent_facets(at), key="ag_scatter")
    with d, T.card("ag_coach"):
        T.card_title("Coaching shortlist", "Agents well below their team's median, with enough volume to be meaningful",
                     "coach", T.ROSE)
        short = at[(at["vs_team"] <= -0.06) & (at["sessions"] >= 100)].sort_values("vs_team").head(8)
        if short.empty:
            st.success("Nobody is far behind their team. Nothing to flag.", icon=":material/celebration:")
        else:
            short = short.assign(vs=short["vs_team"] * 100, success=short["success"] * 100)
            T.show_table(
                short[["name", "success", "vs", "team"]].rename(columns={
                    "name": "Agent", "team": "Team", "success": "Success", "vs": "vs team"}),
                column_config={"Success": st.column_config.NumberColumn(format="%.0f%%"),
                               "vs team": st.column_config.NumberColumn(format="%+.1f pts")})

    with T.card("ag_board"):
        T.card_title("Agent leaderboard", "Sorted by search success. Compare agents within a team; teams handle "
                     "different topics.", "award", T.AMBER)
        t = at.assign(success=at["success"] * 100, vs_team=at["vs_team"] * 100, escalation=at["escalation"] * 100)
        T.show_table(
            t[["name", "team", "tenure_months", "sessions", "success", "vs_team", "ttfc", "searches_per_case",
               "escalation", "res_hours", "csat"]].rename(columns={
                "name": "Agent", "team": "Team", "tenure_months": "Tenure (mo)", "sessions": "Sessions",
                "success": "Success", "vs_team": "vs team", "ttfc": "Time to click (s)",
                "searches_per_case": "Searches / case", "escalation": "Escalated",
                "res_hours": "Median hrs to resolve", "csat": "CSAT"}),
            column_config={
                "Success": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=100, color="green"),
                "vs team": st.column_config.NumberColumn(format="%+.1f pts"),
                "Time to click (s)": st.column_config.NumberColumn(format="%.1f"),
                "Searches / case": st.column_config.NumberColumn(format="%.2f"),
                "Escalated": st.column_config.NumberColumn(format="%.0f%%"),
                "Median hrs to resolve": st.column_config.NumberColumn(format="%.1f"),
                "CSAT": st.column_config.NumberColumn(format="%.2f"),
                "Sessions": st.column_config.NumberColumn(format="localized"),
            })


def render() -> None:
    ctx = st.session_state["ctx"]
    T.page_header("Agent effectiveness",
                  "Are support agents finding what they need, fast enough, and does it change case outcomes?",
                  [ctx.chips[0], "Support agents only (ignores the “who” filter)", ctx.chips[2],
                   f"{len(ctx.s_agents):,} searches · {len(ctx.ses_agents):,} sessions"])
    if ctx.ses_agents.empty:
        st.info("No agent activity in this selection.", icon=":material/person_off:")
        return
    _body()
