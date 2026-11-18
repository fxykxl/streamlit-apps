"""Pure-pandas metric definitions (no Streamlit / Plotly imports - easy to test).

Definitions used across the dashboard
    Search success rate   share of search SESSIONS that ended with a resolving click
    Click-through rate    share of SEARCHES with at least one click
    Zero-result rate      share of SEARCHES that returned nothing
    Time to first click   median seconds from query to first click (clicked searches)
    Self-service rate     share of CUSTOMER sessions resolved without opening a case
"""
from __future__ import annotations

import numpy as np
import pandas as pd

NAN = float("nan")


def _mean(x) -> float:
    return float(x.mean()) if len(x) else NAN


def kpis(s: pd.DataFrame, ses: pd.DataFrame) -> dict:
    cust = ses[ses["user_type"] == "Customer"]
    clicked = s[s["clicked"]]
    return dict(
        searches=len(s), sessions=len(ses),
        success=_mean(ses["resolved"]),
        ctr=_mean(s["clicked"]),
        zero=_mean(s["zero_result"]),
        ttfc=float(clicked["time_to_first_click_s"].median()) if len(clicked) else NAN,
        self_service=_mean(cust["resolved"] & ~cust["case_created"]) if len(cust) else NAN,
        p95_latency=float(s["latency_ms"].quantile(0.95)) if len(s) else NAN,
        reform=_mean(s["reformulated"]),
    )


def trend(s: pd.DataFrame, ses: pd.DataFrame, freq: str, start=None, end=None) -> pd.DataFrame:
    key = "week" if freq == "Weekly" else "date"
    if s.empty:
        return pd.DataFrame()
    a = s.groupby(key).agg(searches=("search_id", "size"), ctr=("clicked", "mean"), zero=("zero_result", "mean"),
                           p50=("latency_ms", "median"), p95=("latency_ms", lambda x: x.quantile(0.95)))
    t = s[s["clicked"]].groupby(key)["time_to_first_click_s"].median().rename("ttfc")
    u = ses.groupby(key)["resolved"].mean().rename("success")
    out = a.join(t).join(u).reset_index().rename(columns={key: "bucket"})
    if freq == "Weekly" and start is not None:
        full = out[(out["bucket"] >= start) & (out["bucket"] + pd.Timedelta(days=6) <= end)]
        if len(full) >= 3:
            out = full
    return out.reset_index(drop=True)


def by_area(ses: pd.DataFrame) -> pd.DataFrame:
    g = ses.groupby("product_area").agg(sessions=("session_id", "size"), success=("resolved", "mean"))
    return g.reset_index().sort_values("success")


def funnel(s: pd.DataFrame) -> dict:
    return dict(searches=len(s), results=int((~s["zero_result"]).sum()), clicked=int(s["clicked"].sum()),
                resolved=int(s["resolved"].sum()))


def click_positions(s: pd.DataFrame, cap: int = 10) -> pd.DataFrame:
    p = s.loc[s["clicked"], "click_position"].dropna().astype(int).clip(upper=cap + 1)
    c = p.value_counts(normalize=True).sort_index()
    out = pd.DataFrame({"position": c.index, "share": c.values})
    out["label"] = out["position"].map(lambda x: f"{cap}+" if x > cap else str(x))
    return out


def weekday_hour_success(ses: pd.DataFrame, min_n: int = 15) -> pd.DataFrame:
    g = ses.groupby(["dow", "hour"]).agg(n=("session_id", "size"), success=("resolved", "mean")).reset_index()
    g.loc[g["n"] < min_n, "success"] = np.nan
    return g.pivot(index="dow", columns="hour", values="success").reindex(index=range(7), columns=range(24))


def searches_per_session(ses: pd.DataFrame) -> pd.DataFrame:
    n = ses["n_searches"].clip(upper=5)
    g = ses.assign(n=n).groupby(["n", "resolved"]).size().unstack(fill_value=0)
    for col in (True, False):
        if col not in g.columns:
            g[col] = 0
    g = g.reindex(range(1, 6), fill_value=0)
    g["total"] = g[True] + g[False]
    g["share"] = g["total"] / max(g["total"].sum(), 1)
    g["found"] = g[True] / max(g["total"].sum(), 1)
    g["gave_up"] = g[False] / max(g["total"].sum(), 1)
    g["label"] = ["1 search", "2 searches", "3 searches", "4 searches", "5+ searches"]
    return g.reset_index(drop=True)


def channel_table(s: pd.DataFrame, ses: pd.DataFrame) -> pd.DataFrame:
    a = s.groupby("channel").agg(searches=("search_id", "size"), ctr=("clicked", "mean"),
                                 zero=("zero_result", "mean"), p95=("latency_ms", lambda x: x.quantile(.95)))
    b = ses.groupby("channel").agg(sessions=("session_id", "size"), success=("resolved", "mean"))
    return a.join(b).reset_index().sort_values("searches", ascending=False)


# ------------------------------------------------------------------ content gaps
def gap_type(r) -> str:
    """Diagnosis from the most recent window (so fixed problems stop showing as open)."""
    if r["articles"] == 0:
        return "No article"
    if r["zero_r"] >= 0.15:
        return "Vocabulary mismatch"
    if r["success_r"] < r["overall"] - 0.10 and r["ctr_r"] >= 0.5:
        return "Weak content"
    if r["success"] < r["overall"] - 0.10 or r["zero"] >= 0.15:
        return "Recovered"  # was failing earlier in the period, healthy now
    return "Healthy"


def topic_table(s: pd.DataFrame, ses: pd.DataFrame, articles: pd.DataFrame, end, recent_days: int = 28) -> pd.DataFrame:
    if ses.empty:
        return pd.DataFrame()
    keys = ["product_area", "topic"]

    def agg(s_, ses_):
        a = ses_.groupby(keys).agg(sessions=("session_id", "size"), success=("resolved", "mean"))
        b = s_.groupby(keys).agg(searches=("search_id", "size"), zero=("zero_result", "mean"), ctr=("clicked", "mean"))
        return a.join(b)

    t = agg(s, ses)
    cut = ses["date"].max() - pd.Timedelta(days=recent_days - 1)
    rec = agg(s[s["date"] >= cut], ses[ses["date"] >= cut])
    rec = rec[rec["sessions"] >= 20][["success", "zero", "ctr"]].add_suffix("_r")
    t = t.join(rec).reset_index()
    for c in ("success", "zero", "ctr"):  # topics too quiet recently fall back to the full period
        t[c + "_r"] = t[c + "_r"].fillna(t[c])
    t["failed"] = (t["sessions"] * (1 - t["success"])).round().astype(int)
    art = articles[articles["published_date"] <= end].groupby("topic").size().rename("articles")
    t = t.merge(art, on="topic", how="left")
    t["articles"] = t["articles"].fillna(0).astype(int)
    t["overall"] = float(ses["resolved"].mean())
    t["gap_type"] = t.apply(gap_type, axis=1)
    t["fail_rate"] = 1 - t["success"]
    return t.sort_values("failed", ascending=False).reset_index(drop=True)


def topic_weekly(s: pd.DataFrame, topics: list[str], weeks: list) -> dict[str, list[float]]:
    """Weekly failed-search counts per topic (for sparkline columns)."""
    f = s[s["topic"].isin(topics) & ~s["resolved"]]
    p = f.groupby(["topic", "week"]).size().unstack(fill_value=0).reindex(columns=weeks, fill_value=0)
    return {t: p.loc[t].tolist() if t in p.index else [0] * len(weeks) for t in topics}


def top_zero_queries(s: pd.DataFrame, n: int = 15) -> pd.DataFrame:
    z = s[s["zero_result"]]
    g = z.groupby("query_norm").agg(searches=("search_id", "size"), area=("product_area", "first"))
    g = g.sort_values("searches", ascending=False).head(n).reset_index()
    g["share"] = g["searches"] / max(len(z), 1)
    return g


def article_table(s: pd.DataFrame, articles: pd.DataFrame, end) -> pd.DataFrame:
    """Per-article clicks and resolve rate, counting only clicks where the article matches the topic searched."""
    topic_of = articles.set_index("article_id")["topic"]
    c = s[s["clicked_article_id"].notna()].copy()
    c["match"] = c["clicked_article_id"].map(topic_of) == c["topic"]
    c = c[c["match"]]
    g = c.groupby("clicked_article_id").agg(clicks=("search_id", "size"), resolve_rate=("resolved", "mean"))
    t = articles.merge(g, left_on="article_id", right_index=True, how="left")
    t["clicks"] = t["clicks"].fillna(0).astype(int)
    t["age_days"] = (end - t["last_updated"]).dt.days.clip(lower=0)
    return t


# ------------------------------------------------------------------ agents
def agent_table(ses: pd.DataFrame, s: pd.DataFrame, cases: pd.DataFrame, agents: pd.DataFrame) -> pd.DataFrame:
    if ses.empty:
        return pd.DataFrame()
    a = ses.groupby("agent_id").agg(sessions=("session_id", "size"), success=("resolved", "mean"),
                                    searches=("n_searches", "sum"))
    t = s[s["clicked"]].groupby("agent_id")["time_to_first_click_s"].median().rename("ttfc")
    c = cases.groupby("agent_id").agg(cases=("case_id", "size"), escalation=("escalated", "mean"),
                                      res_hours=("resolution_hours", "median"), csat=("csat", "mean"),
                                      found=("found", "mean"))
    out = a.join(t).join(c).reset_index().merge(agents, on="agent_id", how="left")
    out["searches_per_case"] = out["searches"] / out["cases"].replace(0, np.nan)
    out["vs_team"] = out["success"] - out.groupby("team")["success"].transform("median")
    out["tenure_band"] = pd.cut(out["tenure_months"], [0, 3, 6, 12, 24, 1000],
                                labels=["≤3 mo", "4–6 mo", "7–12 mo", "13–24 mo", "25+ mo"])
    return out.sort_values("success", ascending=False).reset_index(drop=True)


def case_impact(cases: pd.DataFrame) -> pd.DataFrame:
    if cases.empty:
        return pd.DataFrame()
    g = cases.groupby("found").agg(cases=("case_id", "size"), res_hours=("resolution_hours", "median"),
                                   escalation=("escalated", "mean"), csat=("csat", "mean"))
    return g.reindex([True, False]).dropna(how="all")


def tenure_curve(at: pd.DataFrame) -> pd.DataFrame:
    g = at.groupby("tenure_band", observed=True).apply(
        lambda d: pd.Series(dict(agents=len(d), success=np.average(d["success"], weights=d["sessions"]),
                                 sessions=d["sessions"].sum())), include_groups=False)
    return g.reset_index()


# ------------------------------------------------------------------ narrative
def build_insights(ctx, k: dict, tt: pd.DataFrame, tr: pd.DataFrame, impact: pd.DataFrame, at: pd.DataFrame) -> list[dict]:
    out: list[dict] = []

    # 1. biggest incident in the trend
    if len(tr) >= 4 and tr["success"].notna().sum() >= 4:
        med = tr["success"].median()
        w = tr.loc[tr["success"].idxmin()]
        drop = med - w["success"]
        if drop >= 0.05:
            end = w["bucket"] + pd.Timedelta(days=6)
            ev = ctx.events[(ctx.events["start"] <= end) & (ctx.events["end"] >= w["bucket"])]
            cause = f" Coincides with “{ev.iloc[0]['label']}”." if len(ev) else ""
            out.append(dict(tone="bad", tag="Dip detected",
                            headline=f"Success fell to {w['success']:.0%} in the week of {w['bucket']:%b %d}",
                            detail=f"{drop * 100:.0f} pts below the typical week; zero-result rate hit "
                                   f"{w['zero']:.0%} and p95 latency {w['p95']:.0f} ms.{cause}"))

    # 2. biggest content gap
    open_gaps = tt[tt["gap_type"].isin(["No article", "Vocabulary mismatch", "Weak content"])] if len(tt) else tt
    if len(open_gaps):
        g = open_gaps.iloc[0]
        total_failed = max(tt["failed"].sum(), 1)
        what = {"No article": "has no article", "Vocabulary mismatch": "has an article users can't find with their words",
                "Weak content": "has an article that doesn't resolve the question"}.get(g["gap_type"], "underperforms")
        out.append(dict(tone="bad", tag="Biggest content gap",
                        headline=f"“{g['topic']}” {what}",
                        detail=f"{g['failed']:,} failed sessions ({g['failed'] / total_failed:.0%} of all failures) in "
                               f"{g['product_area']}; only {g['success']:.0%} are resolved."))

    # 3. why it matters: case impact
    if len(impact) == 2 and impact.loc[True, "res_hours"] and impact.loc[False, "res_hours"]:
        f, n = impact.loc[True], impact.loc[False]
        out.append(dict(tone="info", tag="Why it matters",
                        headline=f"Finding an answer makes cases {1 - f['res_hours'] / n['res_hours']:.0%} faster to resolve",
                        detail=f"Median {f['res_hours']:.0f} h vs {n['res_hours']:.0f} h, and escalation falls from "
                               f"{n['escalation']:.0%} to {f['escalation']:.0%}. "
                               f"{n['cases'] / (f['cases'] + n['cases']):.0%} of cases never found an answer."))

    # 4. agents: tenure / spread
    if len(at) >= 8:
        new = at[at["tenure_months"] <= 3]
        old = at[at["tenure_months"] > 3]
        if len(new) >= 2 and len(old):
            ns = np.average(new["success"], weights=new["sessions"])
            os_ = np.average(old["success"], weights=old["sessions"])
            tone = "bad" if os_ - ns > 0.03 else "good"
            out.append(dict(tone=tone, tag="Agent ramp-up",
                            headline=f"New agents resolve {ns:.0%} of searches vs {os_:.0%} for the rest",
                            detail=f"{len(new)} agents with ≤3 months tenure. A shared “first 90 days” search playbook "
                                   f"is the cheapest lever."))
    if len(out) < 4 and k["zero"] == k["zero"]:
        out.append(dict(tone="info", tag="Zero results",
                        headline=f"{k['zero']:.0%} of searches return nothing",
                        detail=f"Median time to first click is {k['ttfc']:.1f}s; {k['reform']:.0%} of searches are "
                               f"followed by a reformulation."))
    return out[:4]
