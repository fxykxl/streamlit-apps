"""Short, data-driven highlight cards for the pages that don't have their own narrative.

Each function returns a list of dicts (tone, tag, headline, detail) rendered by theme.insight_row.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def search_page(s: pd.DataFrame, ses: pd.DataFrame, daily: pd.DataFrame, pos: pd.DataFrame,
                events: pd.DataFrame) -> list[dict]:
    out: list[dict] = []

    if len(pos):
        top1 = float(pos.loc[pos["position"] == 1, "share"].sum())
        top3 = float(pos.loc[pos["position"] <= 3, "share"].sum())
        out.append(dict(tone="info", tag="Ranking",
                        headline=f"{top1:.0%} of clicks go to the first result",
                        detail=f"{top3:.0%} land in the top three. Improving the first result helps more than "
                               f"anything further down the list."))

    if len(daily) >= 7 and daily["p95"].notna().any():
        typical = float(daily["p95"].median())
        worst = daily.loc[daily["p95"].idxmax()]
        if worst["p95"] > typical * 1.4:
            ev = events[(events["start"] <= worst["bucket"]) & (events["end"] >= worst["bucket"])]
            cause = f" It coincides with “{ev.iloc[0]['label']}”." if len(ev) else ""
            out.append(dict(tone="bad", tag="Latency spike",
                            headline=f"p95 latency peaked at {worst['p95']:,.0f} ms on {worst['bucket']:%b %d}",
                            detail=f"That is {worst['p95'] / typical:.1f}× the typical {typical:,.0f} ms.{cause}"))
        else:
            out.append(dict(tone="good", tag="Latency",
                            headline=f"Response time is steady at ~{typical:,.0f} ms (p95)",
                            detail="No day in this selection ran more than 40% above the typical p95."))

    if len(ses):
        many = ses[ses["n_searches"] >= 3]
        one = ses[ses["n_searches"] == 1]
        if len(many) and len(one):
            out.append(dict(tone="warn", tag="Effort",
                            headline=f"{len(many) / len(ses):.0%} of sessions need 3+ searches",
                            detail=f"Those resolve {many['resolved'].mean():.0%} of the time, against "
                                   f"{one['resolved'].mean():.0%} for single-search sessions."))
    return out[:3]


def agents_page(at: pd.DataFrame, cases: pd.DataFrame) -> list[dict]:
    out: list[dict] = []
    if at.empty:
        return out

    teams = at.groupby("team").apply(lambda d: np.average(d["success"], weights=d["sessions"]), include_groups=False)
    if len(teams) >= 2:
        best, worst = teams.idxmax(), teams.idxmin()
        out.append(dict(tone="info", tag="Teams",
                        headline=f"{best} leads at {teams[best]:.0%} search success",
                        detail=f"{worst} is lowest at {teams[worst]:.0%}. Teams handle different topics, so compare "
                               f"agents within a team."))
    elif len(teams) == 1:
        out.append(dict(tone="info", tag="Team",
                        headline=f"{teams.index[0]} resolves {teams.iloc[0]:.0%} of searches",
                        detail=f"{len(at)} active agents in this selection."))

    short = at[(at["vs_team"] <= -0.06) & (at["sessions"] >= 100)]
    if len(short):
        out.append(dict(tone="warn", tag="Coaching",
                        headline=f"{len(short)} agent{'s' if len(short) > 1 else ''} trail their team by 6+ pts",
                        detail=f"Biggest gap: {short.sort_values('vs_team').iloc[0]['name']} at "
                               f"{short['vs_team'].min() * 100:+.0f} pts. See the coaching shortlist below."))
    else:
        out.append(dict(tone="good", tag="Coaching",
                        headline="Nobody trails their team by 6+ pts",
                        detail="Every agent with meaningful volume is close to their team's median."))

    if len(cases) and cases["found"].nunique() == 2:
        f, n = cases[cases["found"]], cases[~cases["found"]]
        fh, nh = f["resolution_hours"].median(), n["resolution_hours"].median()
        if nh and nh == nh:
            out.append(dict(tone="good" if fh < nh else "bad", tag="Case outcomes",
                            headline=f"Answered cases close {1 - fh / nh:.0%} faster",
                            detail=f"Median {fh:.0f} h vs {nh:.0f} h when the agent found nothing; CSAT "
                                   f"{f['csat'].mean():.2f} vs {n['csat'].mean():.2f}."))
    return out[:3]


def explorer_kpis(s: pd.DataFrame, ses: pd.DataFrame) -> dict:
    q = s.groupby("query_norm")["zero_result"].agg(["mean", "size"])
    return dict(queries=int(len(q)), dead=int(((q["mean"] >= 0.5) & (q["size"] >= 5)).sum()),
                results=float(s["n_results"].median()) if len(s) else float("nan"),
                multi=float((ses["n_searches"] >= 3).mean()) if len(ses) else float("nan"))


def explorer_page(s: pd.DataFrame) -> list[dict]:
    out: list[dict] = []
    if s.empty:
        return out
    g = s.groupby("query_norm").agg(n=("search_id", "size"), zero=("zero_result", "mean"),
                                    resolved=("resolved", "mean"), reform=("reformulated", "mean"))
    top = g.sort_values("n", ascending=False).iloc[0]
    out.append(dict(tone="info", tag="Most searched",
                    headline=f"“{top.name}” is the top query",
                    detail=f"{int(top['n']):,} searches, {top['resolved']:.0%} resolved."))
    z = g[g["n"] >= 20].sort_values(["zero", "n"], ascending=False)
    if len(z) and z.iloc[0]["zero"] > 0:
        r = z.iloc[0]
        out.append(dict(tone="bad", tag="Dead end",
                        headline=f"“{r.name}” returns nothing {r['zero']:.0%} of the time",
                        detail=f"{int(r['n']):,} searches. A synonym or a new article would fix it."))
    rf = g[g["n"] >= 20].sort_values("reform", ascending=False)
    if len(rf):
        r = rf.iloc[0]
        out.append(dict(tone="warn", tag="Rephrased most",
                        headline=f"“{r.name}” is followed by another search {r['reform']:.0%} of the time",
                        detail="People try again after it: the results are close but not quite right."))
    return out[:3]
