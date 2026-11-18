"""Design tokens, CSS and small HTML helpers shared by every page.

Palette: the categorical hues were checked with a colour-vision-deficiency validator
(dark surface #1a1a19): every adjacent pair clears the separation floors.
"""
from __future__ import annotations

import streamlit as st

FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif'

PAGE = "#0d0d0d"
SURFACE = "#1a1a19"
GRID = "#2c2c2a"
AXIS = "#383835"
INK = "#f0efec"
INK2 = "#c3c2b7"
MUTED = "#898781"

BLUE, ORANGE, AQUA, YELLOW = "#3987e5", "#d95926", "#199e70", "#c98500"
MAGENTA, GREEN, VIOLET, RED = "#d55181", "#0ca30c", "#9085e9", "#e66767"
SERIES = [BLUE, ORANGE, AQUA, YELLOW, MAGENTA, GREEN, VIOLET, RED]

GOOD, SERIOUS, CRITICAL = "#0ca30c", "#ec835a", "#d03b3b"
BLUE_RAMP = ["#104281", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4"]      # low -> high on dark
BLUE_ORDINAL = ["#6da7ec", "#3987e5", "#256abf", "#1c5cab"]
EVENT_COLORS = {"Incident": RED, "Release": VIOLET, "Content": AQUA}

CSS = f"""
<style>
html, body, [class*="css"] {{ font-family: {FONT}; }}
.block-container, [data-testid="stMainBlockContainer"] {{
    padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1480px; }}
header[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu, footer {{ visibility: hidden; }}
section[data-testid="stSidebar"] {{ border-right: 1px solid rgba(255,255,255,.06); }}

.page-title {{ font-size: 30px; font-weight: 700; color: {INK}; letter-spacing: -.01em; margin: 0; }}
.page-sub {{ font-size: 15px; color: {INK2}; margin: 4px 0 10px; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 0 0 18px; }}
.chip {{ font-size: 12px; color: {INK2}; border: 1px solid rgba(255,255,255,.10);
    border-radius: 999px; padding: 3px 11px; background: rgba(255,255,255,.03); }}

.kpi {{ background: {SURFACE}; border: 1px solid rgba(255,255,255,.08); border-radius: 14px;
    padding: 16px 18px 12px; min-height: 148px; position: relative; overflow: hidden; }}
.kpi .lbl {{ font-size: 11.5px; letter-spacing: .06em; text-transform: uppercase;
    color: {MUTED}; font-weight: 650; }}
.kpi .val {{ font-size: 36px; font-weight: 680; color: {INK}; line-height: 1.12; margin: 8px 0 4px; }}
.kpi .unit {{ font-size: 18px; font-weight: 600; color: {INK2}; margin-left: 2px; }}
.kpi .delta {{ font-size: 12.5px; font-weight: 650; }}
.kpi .delta.good {{ color: {GOOD}; }}
.kpi .delta.bad {{ color: {SERIOUS}; }}
.kpi .delta.flat {{ color: {MUTED}; }}
.kpi .foot {{ font-size: 11.5px; color: {MUTED}; margin-top: 2px; }}
.kpi svg {{ position: absolute; right: 14px; bottom: 12px; opacity: .95; }}

.ctitle {{ font-size: 15px; font-weight: 650; color: {INK}; margin: 2px 0 0; }}
.csub {{ font-size: 12.5px; color: {MUTED}; margin: 2px 0 8px; }}

.insight {{ background: {SURFACE}; border: 1px solid rgba(255,255,255,.08); border-left-width: 4px;
    border-radius: 12px; padding: 13px 15px; min-height: 142px; }}
.insight.bad {{ border-left-color: {SERIOUS}; }}
.insight.good {{ border-left-color: {GOOD}; }}
.insight.info {{ border-left-color: {BLUE}; }}
.insight .tag {{ font-size: 11px; font-weight: 700; letter-spacing: .07em; text-transform: uppercase; }}
.insight.bad .tag {{ color: {SERIOUS}; }} .insight.good .tag {{ color: {GOOD}; }}
.insight.info .tag {{ color: {BLUE}; }}
.insight .h {{ font-size: 14.5px; font-weight: 650; color: {INK}; margin: 5px 0 4px; line-height: 1.3; }}
.insight .d {{ font-size: 12.5px; color: {INK2}; line-height: 1.45; }}

.note {{ font-size: 12px; color: {MUTED}; margin-top: 26px; text-align: center; }}
</style>
"""


def apply_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


def page_header(title: str, subtitle: str, chips: list[str] | None = None) -> None:
    html = f'<p class="page-title">{title}</p><p class="page-sub">{subtitle}</p>'
    if chips:
        html += '<div class="chips">' + "".join(f'<span class="chip">{c}</span>' for c in chips) + "</div>"
    st.markdown(html, unsafe_allow_html=True)


def card_title(title: str, subtitle: str = "") -> None:
    html = f'<p class="ctitle">{title}</p>'
    if subtitle:
        html += f'<p class="csub">{subtitle}</p>'
    st.markdown(html, unsafe_allow_html=True)


def sparkline(values, color: str = BLUE, w: int = 104, h: int = 30) -> str:
    v = [float(x) for x in values if x == x]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    span = (hi - lo) or 1.0
    pts = [(3 + i * (w - 6) / (len(v) - 1), h - 4 - (x - lo) / span * (h - 8)) for i, x in enumerate(v)]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    ex, ey = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true">'
            f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="2.8" fill="{color}" stroke="{SURFACE}" stroke-width="2"/></svg>')


def kpi_card(label: str, value: str, unit: str = "", delta: str = "", tone: str = "flat",
             foot: str = "", spark: str = "") -> str:
    arrow = {"good": "▲", "bad": "▼", "flat": "●"}.get(tone, "●")
    d = f'<div class="delta {tone}">{arrow} {delta}</div>' if delta else ""
    u = f'<span class="unit">{unit}</span>' if unit else ""
    f = f'<div class="foot">{foot}</div>' if foot else ""
    return (f'<div class="kpi"><div class="lbl">{label}</div><div class="val">{value}{u}</div>'
            f'{d}{f}{spark}</div>')


def insight_card(tone: str, tag: str, headline: str, detail: str) -> str:
    icon = {"bad": "⚠", "good": "✔", "info": "ℹ"}.get(tone, "ℹ")
    return (f'<div class="insight {tone}"><div class="tag">{icon} {tag}</div>'
            f'<div class="h">{headline}</div><div class="d">{detail}</div></div>')


def show(fig, key: str | None = None) -> None:
    """Render a Plotly figure full-width; tolerant of Streamlit API changes."""
    cfg = {"displayModeBar": False, "responsive": True}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg, key=key)
    except Exception:  # older Streamlit: width= not accepted
        st.plotly_chart(fig, use_container_width=True, config=cfg, key=key)


def show_table(df, **kwargs) -> None:
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except Exception:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)
