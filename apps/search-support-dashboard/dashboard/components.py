"""KPI-card helpers shared by several pages."""
from __future__ import annotations

import math

import streamlit as st

from . import theme as T


def _ok(v) -> bool:
    return v is not None and not (isinstance(v, float) and math.isnan(v))


def fmt_value(kind: str, v) -> tuple[str, str]:
    if not _ok(v):
        return "—", ""
    return {
        "pct": (f"{v * 100:.1f}", "%"),
        "sec": (f"{v:.1f}", "s"),
        "ms": (f"{v:,.0f}", " ms"),
        "int": (f"{v:,.0f}", ""),
        "hours": (f"{v:.1f}", " h"),
        "num": (f"{v:.1f}", ""),
    }[kind]


def delta(kind: str, v, pv, better: str) -> tuple[str, str]:
    """Return (text, tone). better is 'up', 'down' or 'neutral'."""
    if not (_ok(v) and _ok(pv)):
        return "", "flat"
    d = v - pv
    if kind == "pct":
        text, tiny = f"{d * 100:+.1f} pts", abs(d) < 0.0005
    elif kind == "int":
        text, tiny = f"{d:+,.0f}" + (f" ({d / pv:+.0%})" if pv else ""), d == 0
    elif kind == "ms":
        text, tiny = f"{d:+,.0f} ms", abs(d) < 1
    else:
        text, tiny = f"{d:+.1f}" + ("s" if kind == "sec" else ""), abs(d) < 0.05
    if tiny or better == "neutral":
        return text, "flat"
    good = (d > 0) == (better == "up")
    return text, "good" if good else "bad"


ACCENT_CYCLE = [T.INDIGO, T.CYAN, T.ROSE, T.AMBER, T.EMERALD]


def render_kpis(specs: list[dict], k: dict, pk: dict | None, prev_label: str, sparks: dict | None = None) -> None:
    """specs: dicts with key, label, kind, better, desc and optional accent / icon."""
    cols = st.columns(len(specs), gap="medium")
    for i, (col, sp) in enumerate(zip(cols, specs)):
        accent = sp.get("accent", ACCENT_CYCLE[i % len(ACCENT_CYCLE)])
        v = k.get(sp["key"])
        val, unit = fmt_value(sp["kind"], v)
        txt, tone = delta(sp["kind"], v, pk.get(sp["key"]) if pk else None, sp["better"])
        foot = f"vs {prev_label}" if txt else ""
        spark = ""
        if sparks and sp["key"] in sparks:
            spark = T.sparkline(sparks[sp["key"]], accent)
        col.markdown(T.kpi_card(sp["label"], val, unit, txt, tone, foot, spark, accent=accent,
                                ico=sp.get("icon", "activity"), delay=i * 0.05, info=sp["desc"]),
                    unsafe_allow_html=True)
