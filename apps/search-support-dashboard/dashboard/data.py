"""Data loading, filters and the shared context every page reads."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
NAMES = ["agents", "articles", "cases", "sessions", "searches", "events"]
USER_OPTIONS = {
    "Everyone": None,
    "Support agents (console)": "Agent",
    "Customers (self-service)": "Customer",
}


def _prepare(t: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    s, ses, c = t["searches"].copy(), t["sessions"].copy(), t["cases"].copy()
    a, ag, ev = t["articles"].copy(), t["agents"].copy(), t["events"].copy()

    s["timestamp"] = pd.to_datetime(s["timestamp"])
    s["date"] = s["timestamp"].dt.normalize()
    s["week"] = s["date"] - pd.to_timedelta(s["date"].dt.dayofweek, unit="D")
    s["query_norm"] = s["query"].str.lower().str.strip()

    ses["start_time"] = pd.to_datetime(ses["start_time"])
    ses["date"] = ses["start_time"].dt.normalize()
    ses["week"] = ses["date"] - pd.to_timedelta(ses["date"].dt.dayofweek, unit="D")
    ses["hour"] = ses["start_time"].dt.hour
    ses["dow"] = ses["start_time"].dt.dayofweek
    ses = ses.merge(ag[["agent_id", "name", "team", "tenure_months"]].rename(columns={"name": "agent_name"}),
                    on="agent_id", how="left")

    c["created_at"] = pd.to_datetime(c["created_at"])
    c["resolved_at"] = pd.to_datetime(c["resolved_at"])
    c["date"] = c["created_at"].dt.normalize()
    found = ses[ses["case_id"].notna()].groupby("case_id")["resolved"].max()
    c["found"] = c["case_id"].map(found).fillna(False).astype(bool)

    for col in ("published_date", "last_updated"):
        a[col] = pd.to_datetime(a[col])
    tot = (a["helpful_votes"] + a["unhelpful_votes"]).replace(0, float("nan"))
    a["helpful_rate"] = a["helpful_votes"] / tot

    ev["start"] = pd.to_datetime(ev["start"])
    ev["end"] = pd.to_datetime(ev["end"])
    return dict(searches=s, sessions=ses, cases=c, articles=a, agents=ag, events=ev)


@st.cache_data(show_spinner="Loading data…")
def load_data() -> dict[str, pd.DataFrame]:
    if all((DATA_DIR / f"{n}.csv.gz").exists() for n in NAMES):
        raw = {n: pd.read_csv(DATA_DIR / f"{n}.csv.gz") for n in NAMES}
    else:  # fall back to generating in memory (e.g. fresh clone without the data folder)
        sys.path.insert(0, str(ROOT))
        from generate_data import generate
        raw = generate()
    return _prepare(raw)


@dataclass
class Ctx:
    start: pd.Timestamp
    end: pd.Timestamp
    user: str | None
    areas: list[str]
    all_areas: list[str]
    s: pd.DataFrame            # searches, all filters
    ses: pd.DataFrame          # sessions, all filters
    cases: pd.DataFrame        # cases (date + area filters)
    ps: pd.DataFrame           # previous period (same filters), may be empty
    pses: pd.DataFrame
    s_agents: pd.DataFrame     # agent searches (date + area filters, user filter ignored)
    ses_agents: pd.DataFrame
    articles: pd.DataFrame
    agents: pd.DataFrame
    events: pd.DataFrame
    has_prev: bool
    prev_label: str

    @property
    def user_label(self) -> str:
        return {None: "All users", "Agent": "Support agents", "Customer": "Customers"}[self.user]

    @property
    def chips(self) -> list[str]:
        area = "All product areas" if len(self.areas) == len(self.all_areas) else f"{len(self.areas)} product areas"
        return [f"{self.start:%b %d, %Y} – {self.end:%b %d, %Y}", self.user_label, area,
                f"{len(self.s):,} searches · {len(self.ses):,} sessions"]


def _flt(df: pd.DataFrame, start, end, areas, user=None) -> pd.DataFrame:
    m = (df["date"] >= start) & (df["date"] <= end) & df["product_area"].isin(areas)
    if user is not None and "user_type" in df.columns:
        m &= df["user_type"] == user
    return df[m]


def build_context(t: dict[str, pd.DataFrame]) -> Ctx:
    s, ses, cases = t["searches"], t["sessions"], t["cases"]
    lo, hi = s["date"].min(), s["date"].max()
    all_areas = sorted(s["product_area"].unique())

    from . import theme as T  # local import: theme has no dependency on data

    def _reset() -> None:
        st.session_state.update(f_period="Full period", f_user=next(iter(USER_OPTIONS)), f_areas=[])
        st.session_state.pop("f_dates", None)

    with st.sidebar:
        st.markdown(f'<div class="side-h">{T.icon("sliders", 14)}Filters</div>', unsafe_allow_html=True)
        preset = st.selectbox("Period", ["Full period", "Last 90 days", "Last 30 days", "Custom range"],
                              key="f_period")
        start, end = lo, hi
        if preset == "Last 90 days":
            start = max(lo, hi - pd.Timedelta(days=89))
        elif preset == "Last 30 days":
            start = max(lo, hi - pd.Timedelta(days=29))
        elif preset == "Custom range":
            picked = st.date_input("Dates", value=(lo.date(), hi.date()), min_value=lo.date(),
                                   max_value=hi.date(), key="f_dates")
            if isinstance(picked, (tuple, list)) and len(picked) == 2:
                start, end = pd.Timestamp(picked[0]), pd.Timestamp(picked[1])
            elif isinstance(picked, (tuple, list)) and len(picked) == 1:
                start = end = pd.Timestamp(picked[0])
        who = st.radio("Who is searching", list(USER_OPTIONS), key="f_user")
        picked_areas = st.multiselect("Product area", all_areas, default=[], placeholder="All product areas",
                                      key="f_areas")
        active = preset != "Full period" or bool(picked_areas) or USER_OPTIONS[who] is not None
        st.button("Reset filters", icon=":material/restart_alt:", on_click=_reset, disabled=not active,
                  width="stretch", key="f_reset")
        st.markdown('<div class="side-note">Synthetic data for a fictional company. The agent page always shows '
                    'support agents, whatever “Who is searching” says.</div>', unsafe_allow_html=True)

    areas = picked_areas or all_areas
    user = USER_OPTIONS[who]

    n_days = (end - start).days + 1
    pend, pstart = start - pd.Timedelta(days=1), start - pd.Timedelta(days=n_days)
    has_prev = pstart >= lo
    empty_s, empty_ses = s.iloc[0:0], ses.iloc[0:0]

    return Ctx(
        start=start, end=end, user=user, areas=areas, all_areas=all_areas,
        s=_flt(s, start, end, areas, user), ses=_flt(ses, start, end, areas, user),
        cases=_flt(cases, start, end, areas),
        ps=_flt(s, pstart, pend, areas, user) if has_prev else empty_s,
        pses=_flt(ses, pstart, pend, areas, user) if has_prev else empty_ses,
        s_agents=_flt(s, start, end, areas, "Agent"), ses_agents=_flt(ses, start, end, areas, "Agent"),
        articles=t["articles"], agents=t["agents"], events=t["events"],
        has_prev=has_prev, prev_label=f"previous {n_days} days",
    )
