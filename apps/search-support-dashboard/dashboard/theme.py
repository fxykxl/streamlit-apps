"""Design tokens, CSS and small HTML helpers shared by every page.

Visual language: deep-navy surfaces, one accent colour per metric family, soft
gradient cards with an icon badge, and quiet motion (fade-up on mount, lift on hover).
Accents stay distinguishable on the #121829 surface; good/bad pairs are emerald vs rose,
which differ strongly in lightness as well as hue, so they also read for colour-blind users.
"""
from __future__ import annotations

import hashlib

import streamlit as st

FONT = 'Inter, system-ui, -apple-system, "Segoe UI", sans-serif'

# ---------------------------------------------------------------- surfaces & ink
PAGE = "#0a0e1a"
SURFACE = "#121829"
SURFACE2 = "#182036"
BORDER = "#232c48"
GRID = "#1e2640"
AXIS = "#2c3654"
INK = "#eef1fb"
INK2 = "#b6bdd6"
MUTED = "#7d86a6"
HOVER_BG = "#1a2238"

# ---------------------------------------------------------------- accents
INDIGO = "#7c6cff"
CYAN = "#22d3ee"
EMERALD = "#34d399"
AMBER = "#fbbf24"
ROSE = "#fb7185"
PINK = "#f472b6"
ORANGE = "#fb923c"
SKY = "#60a5fa"
VIOLET = "#a78bfa"
TEAL = "#2dd4bf"

SERIES = [INDIGO, CYAN, AMBER, PINK, EMERALD, ORANGE, SKY, ROSE]
GOOD, WARN, BAD = EMERALD, AMBER, ROSE

# backwards-compatible aliases
BLUE, AQUA, YELLOW, MAGENTA, GREEN, RED = INDIGO, CYAN, AMBER, PINK, EMERALD, ROSE
SERIOUS, CRITICAL = ORANGE, ROSE

# sequential ramps (low -> high on dark)
RAMP_COOL = ["#1c2148", "#33308a", "#5b4fd6", "#4f8ef0", "#38c9e8", "#7cf0dc"]
RAMP_HEAT = ["#232a4a", "#3d3480", "#6b3c9c", "#a8418f", "#e0577c", "#fb7185"]
DIVERGING = [ROSE, "#f0a49a", "#8f97b8", "#7fdcb9", EMERALD]           # bad -> neutral -> good

EVENT_COLORS = {"Incident": ROSE, "Release": VIOLET, "Content": EMERALD}
GAP_COLORS = {"No article": ROSE, "Vocabulary mismatch": ORANGE, "Weak content": AMBER,
              "Recovered": CYAN, "Healthy": EMERALD}
TONES = {"bad": ROSE, "warn": AMBER, "good": EMERALD, "info": INDIGO, "cyan": CYAN}

# ---------------------------------------------------------------- icons (24px stroke icons)
_ICONS = {
    "target": '<circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/>',
    "pointer": '<path d="m9 9 5 12 1.8-5.2L21 14Z"/><path d="M7.2 2.2 8 5.1"/><path d="m5.1 8-2.9-.8"/>'
               '<path d="M14 4.1 12 6"/><path d="m6 12-1.9 2"/>',
    "search_x": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/><path d="m13.5 8.5-5 5"/>'
                '<path d="m8.5 8.5 5 5"/>',
    "search": '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
    "timer": '<line x1="10" x2="14" y1="2" y2="2"/><line x1="12" x2="15" y1="14" y2="11"/>'
             '<circle cx="12" cy="14" r="8"/>',
    "user_check": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
                  '<polyline points="16 11 18 13 22 9"/>',
    "users": '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>'
             '<path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "zap": '<path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>',
    "repeat": '<path d="m17 2 4 4-4 4"/><path d="M3 11v-1a4 4 0 0 1 4-4h14"/><path d="m7 22-4-4 4-4"/>'
              '<path d="M21 13v1a4 4 0 0 1-4 4H3"/>',
    "alert": '<circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/>'
             '<line x1="12" x2="12.01" y1="16" y2="16"/>',
    "triangle": '<path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/>'
                '<line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/>',
    "file_x": '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
              '<polyline points="14 2 14 8 20 8"/><line x1="9.5" x2="14.5" y1="12.5" y2="17.5"/>'
              '<line x1="14.5" x2="9.5" y1="12.5" y2="17.5"/>',
    "file_edit": '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>'
                 '<polyline points="14 2 14 8 20 8"/><path d="M10 18l5.5-5.5 2 2L12 20h-2z"/>',
    "tag": '<path d="M12 2H2v10l9.29 9.29a1 1 0 0 0 1.41 0l8.59-8.59a1 1 0 0 0 0-1.41Z"/>'
           '<circle cx="7" cy="7" r="1.5"/>',
    "mail": '<rect width="20" height="16" x="2" y="4" rx="2"/><path d="m22 7-8.97 5.7a1.94 1.94 0 0 1-2.06 0L2 7"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    "check": '<path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/>',
    "trend_up": '<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>',
    "trend_down": '<polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/>',
    "bulb": '<path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A6 6 0 0 0 6 8c0 1 .2 2.2 1.5 3.5.7.7 1.3 1.5 1.5 2.5"/>'
            '<path d="M9 18h6"/><path d="M10 22h4"/>',
    "calendar": '<rect width="18" height="18" x="3" y="4" rx="2"/><line x1="16" x2="16" y1="2" y2="6"/>'
                '<line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
    "grid": '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/>'
            '<rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
    "activity": '<polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>',
    "bar": '<line x1="12" x2="12" y1="20" y2="10"/><line x1="18" x2="18" y1="20" y2="4"/>'
           '<line x1="6" x2="6" y1="20" y2="16"/>',
    "funnel": '<polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "list": '<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/>'
            '<line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/>'
            '<line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>',
    "map": '<polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" x2="9" y1="3" y2="18"/>'
           '<line x1="15" x2="15" y1="6" y2="21"/>',
    "rocket": '<path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>'
              '<path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>'
              '<path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>',
    "scatter": '<circle cx="7.5" cy="7.5" r="1.5"/><circle cx="18.5" cy="5.5" r="1.5"/><circle cx="11.5" cy="11.5" r="1.5"/>'
               '<circle cx="7.5" cy="16.5" r="1.5"/><circle cx="17.5" cy="14.5" r="1.5"/><path d="M3 3v18h18"/>',
    "award": '<circle cx="12" cy="8" r="6"/><path d="M15.477 12.89 17 22l-5-3-5 3 1.523-9.11"/>',
    "coach": '<path d="M2 21a8 8 0 0 1 13.29-6"/><circle cx="10" cy="8" r="5"/><path d="M19 16v6"/><path d="M22 19h-6"/>',
    "sparkles": '<path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 '
                '1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3Z"/>',
    "dollar": '<line x1="12" x2="12" y1="2" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>',
    "globe": '<circle cx="12" cy="12" r="10"/><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"/>'
             '<path d="M2 12h20"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "sliders": '<line x1="4" x2="4" y1="21" y2="14"/><line x1="4" x2="4" y1="10" y2="3"/><line x1="12" x2="12" y1="21" y2="12"/>'
               '<line x1="12" x2="12" y1="8" y2="3"/><line x1="20" x2="20" y1="21" y2="16"/><line x1="20" x2="20" y1="12" y2="3"/>'
               '<line x1="2" x2="6" y1="14" y2="14"/><line x1="10" x2="14" y1="8" y2="8"/><line x1="18" x2="22" y1="16" y2="16"/>',
}


def icon(name: str, size: int = 18, color: str = "currentColor", stroke: float = 2) -> str:
    body = _ICONS.get(name, _ICONS["info"])
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" '
            f'stroke="{color}" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{body}</svg>')


def rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{alpha})"


# ---------------------------------------------------------------- CSS
CSS = f"""
<style>
:root {{ --ease: cubic-bezier(.2,.7,.2,1); }}
html {{ scroll-behavior: smooth; }}
html, body, .stApp {{ font-family: {FONT}; }}
.stApp {{
  background:
    radial-gradient(1100px 520px at 12% -8%, {rgba(INDIGO, .16)}, transparent 62%),
    radial-gradient(900px 480px at 100% -6%, {rgba(CYAN, .09)}, transparent 60%),
    radial-gradient(800px 600px at 60% 110%, {rgba(PINK, .05)}, transparent 60%),
    {PAGE};
  background-attachment: fixed;
}}
.block-container, [data-testid="stMainBlockContainer"] {{
  padding-top: 2.6rem; padding-bottom: 3rem; max-width: 1480px; }}
header[data-testid="stHeader"] {{ background: {rgba(PAGE, .55)}; backdrop-filter: blur(10px); }}
[data-testid="stDecoration"] {{ background-image: linear-gradient(90deg, {INDIGO}, {CYAN}, {PINK}); }}
#MainMenu, footer {{ visibility: hidden; }}

/* keep the page steady while Streamlit reruns: no grey-out flash */
[data-stale="true"], .stale-element {{ opacity: 1 !important; }}

/* breathing room between rows of cards */
[data-testid="stMainBlockContainer"] [data-testid="stVerticalBlock"] {{ row-gap: 1.75rem; }}
/* ...but keep the inside of a card compact */
[data-testid="stMainBlockContainer"] [class*="st-key-card_"],
[data-testid="stMainBlockContainer"] [class*="st-key-card_"] [data-testid="stVerticalBlock"] {{ row-gap: .85rem; }}


/* ---------- motion ---------- */
@keyframes fadeUp {{ from {{ opacity: 0; transform: translateY(8px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes pulse {{ 0% {{ box-shadow: 0 0 0 0 {rgba(EMERALD, .55)}; }} 70% {{ box-shadow: 0 0 0 8px {rgba(EMERALD, 0)}; }}
  100% {{ box-shadow: 0 0 0 0 {rgba(EMERALD, 0)}; }} }}
@media (prefers-reduced-motion: reduce) {{
  *, *::before, *::after {{ animation: none !important; transition: none !important; scroll-behavior: auto !important; }}
}}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {{ background: linear-gradient(180deg, #10163a 0%, #0b1022 55%); border-right: 1px solid {BORDER}; }}
[data-testid="stSidebarNavLink"] {{ border-radius: 10px; margin: 1px 0;
  transition: background .2s var(--ease), box-shadow .2s var(--ease); }}
[data-testid="stSidebarNavLink"]:hover {{ background: {rgba(INDIGO, .12)}; }}
[data-testid="stSidebarNavLink"][aria-current="page"] {{
  background: linear-gradient(90deg, {rgba(INDIGO, .30)}, {rgba(INDIGO, .06)}); box-shadow: inset 3px 0 0 {INDIGO}; }}
[data-testid="stSidebarNavLink"][aria-current="page"] span {{ color: #fff; }}
[data-testid="stSidebarNavSeparator"] {{ border-color: {BORDER}; }}
.side-h {{ display: flex; align-items: center; gap: 8px; font-size: 11.5px; font-weight: 700; letter-spacing: .09em;
  text-transform: uppercase; color: {INK2}; margin: 2px 0 4px; }}
.side-h svg {{ color: {INDIGO}; }}
.side-note {{ font-size: 12px; color: {MUTED}; line-height: 1.5; padding: 10px 12px; border-radius: 10px;
  background: {rgba(INDIGO, .07)}; border: 1px solid {rgba(INDIGO, .18)}; }}

/* ---------- hero ---------- */
.hero {{ position: relative; overflow: hidden; border-radius: 20px; padding: 24px 28px 20px; margin: 0 0 12px;
  border: 1px solid {rgba(INDIGO, .28)};
  background: linear-gradient(120deg, {rgba(INDIGO, .22)} 0%, {rgba(CYAN, .07)} 55%, {rgba(PINK, .09)} 100%), {SURFACE};
  box-shadow: 0 16px 36px -30px {rgba(INDIGO, .55)}; animation: fadeUp .5s var(--ease) both; }}
.hero::before {{ content: ""; position: absolute; right: -90px; top: -130px; width: 360px; height: 360px;
  background: radial-gradient(circle, {rgba(CYAN, .22)}, transparent 68%); pointer-events: none; }}
.hero::after {{ content: ""; position: absolute; inset: 0; pointer-events: none; opacity: .4;
  background-image: radial-gradient({rgba("#ffffff", .08)} 1px, transparent 1px); background-size: 18px 18px;
  -webkit-mask-image: linear-gradient(90deg, transparent 45%, #000); mask-image: linear-gradient(90deg, transparent 45%, #000); }}
.hero .eyebrow {{ position: relative; z-index: 1; display: inline-flex; align-items: center; gap: 8px; font-size: 11.5px;
  font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: #c4bcff; }}
.hero .pulse {{ width: 7px; height: 7px; border-radius: 50%; background: {EMERALD}; animation: pulse 2.4s infinite; }}
.hero .title {{ position: relative; z-index: 1; font-size: 32px; font-weight: 800; letter-spacing: -.025em; line-height: 1.2;
  margin: 8px 0 4px; padding-bottom: 2px; background: linear-gradient(90deg, #ffffff 0%, #d6d1ff 55%, #7ee8f7 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent; }}
.hero .sub {{ position: relative; z-index: 1; font-size: 15px; color: {INK2}; margin: 0 0 14px; max-width: 760px; }}
.chips {{ position: relative; z-index: 1; display: flex; flex-wrap: wrap; gap: 8px; }}
.chip {{ display: inline-flex; align-items: center; gap: 7px; font-size: 12.5px; font-weight: 500; color: {INK};
  border: 1px solid {rgba("#ffffff", .09)}; border-radius: 999px; padding: 5px 12px 5px 10px;
  background: {rgba(PAGE, .55)}; }}

/* ---------- section heading ---------- */
.sec {{ display: flex; align-items: center; flex-wrap: wrap; gap: 10px; margin: 18px 0 -4px; }}
.sec .ico {{ width: 30px; height: 30px; border-radius: 9px; display: grid; place-items: center; }}
.sec .t {{ font-size: 18px; font-weight: 750; color: {INK}; letter-spacing: -.01em; }}
.sec .s {{ font-size: 13px; color: {MUTED}; }}

/* ---------- KPI cards ---------- */
.kpi {{ --accent: {INDIGO}; position: relative; overflow: hidden; border-radius: 18px; padding: 18px 18px 16px;
  min-height: 150px; display: flex; flex-direction: column;
  background: linear-gradient(155deg, color-mix(in srgb, var(--accent) 15%, {SURFACE}) 0%, {SURFACE} 62%);
  border: 1px solid color-mix(in srgb, var(--accent) 24%, {BORDER});
  box-shadow: inset 0 1px 0 {rgba("#ffffff", .04)};
  transition: transform .25s var(--ease), box-shadow .25s var(--ease), border-color .25s var(--ease);
  margin-bottom: 10px; animation: fadeUp .5s var(--ease) both; }}
.kpi::before {{ content: ""; position: absolute; left: 0; right: 0; top: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent), transparent 85%); }}
.kpi:hover {{ transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 55%, {BORDER});
  box-shadow: 0 18px 38px -20px var(--accent); }}
.kpi .top {{ display: flex; align-items: center; gap: 10px; }}
.kpi .ico {{ flex: none; width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center;
  color: var(--accent); background: color-mix(in srgb, var(--accent) 17%, transparent);
  border: 1px solid color-mix(in srgb, var(--accent) 28%, transparent); }}
.kpi .lbl {{ font-size: 11.5px; letter-spacing: .05em; text-transform: uppercase; color: {INK2}; font-weight: 650;
  line-height: 1.3; }}
.kpi .mid {{ display: flex; align-items: center; justify-content: space-between; gap: 6px; margin: 12px 0 8px; }}
.kpi .val {{ font-size: 32px; font-weight: 780; color: {INK}; letter-spacing: -.025em; line-height: 1.1;
  font-variant-numeric: tabular-nums; white-space: nowrap; }}
.kpi .unit {{ font-size: 17px; font-weight: 650; color: {INK2}; margin-left: 2px; letter-spacing: 0; }}
.kpi .spark {{ flex: 0 1 auto; min-width: 0; max-width: 46%; height: auto; }}
.kpi .bottom {{ margin-top: auto; }}
.kpi .foot {{ font-size: 11.5px; color: {MUTED}; margin-top: 6px; line-height: 1.35; }}
.pill {{ display: inline-flex; align-items: center; gap: 4px; font-size: 12px; font-weight: 700; padding: 3px 9px 3px 8px;
  border-radius: 999px; font-variant-numeric: tabular-nums; white-space: nowrap; }}
.pill.good {{ color: {EMERALD}; background: {rgba(EMERALD, .13)}; }}
.pill.bad {{ color: {ROSE}; background: {rgba(ROSE, .13)}; }}
.pill.flat {{ color: {INK2}; background: {rgba("#ffffff", .07)}; }}

/* ---------- content cards: st.container(key="card_*") ---------- */
[class*="st-key-card_"] {{
  background: linear-gradient(180deg, {rgba("#ffffff", .025)}, {rgba("#ffffff", 0)} 40%), {SURFACE};
  border: 1px solid {BORDER}; border-radius: 18px; padding: 22px 24px 20px;
  box-shadow: inset 0 1px 0 {rgba("#ffffff", .035)}, 0 14px 34px -22px rgba(0,0,0,.8);
  transition: border-color .25s var(--ease), box-shadow .25s var(--ease);
  animation: fadeUp .55s var(--ease) both; }}
[class*="st-key-card_"]:hover {{ border-color: {rgba(INDIGO, .38)};
  box-shadow: inset 0 1px 0 {rgba("#ffffff", .05)}, 0 20px 44px -24px {rgba(INDIGO, .55)}; }}
.chead {{ display: flex; align-items: flex-start; gap: 12px; }}
.chead .ico {{ flex: none; width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; }}
.chead .ctitle {{ font-size: 15.5px; font-weight: 700; color: {INK}; margin: 0; line-height: 1.3; letter-spacing: -.005em; }}
.chead .csub {{ font-size: 12.5px; color: {MUTED}; margin: 3px 0 0; line-height: 1.45; }}

/* ---------- insight cards ---------- */
.insight {{ --accent: {INDIGO}; position: relative; min-height: 172px; margin-bottom: 22px; border-radius: 18px; padding: 18px 18px 16px;
  background: linear-gradient(150deg, color-mix(in srgb, var(--accent) 16%, {SURFACE}) 0%, {SURFACE} 70%);
  border: 1px solid color-mix(in srgb, var(--accent) 26%, {BORDER});
  transition: transform .25s var(--ease), box-shadow .25s var(--ease), border-color .25s var(--ease);
  animation: fadeUp .55s var(--ease) both; }}
.insight:hover {{ transform: translateY(-3px); border-color: color-mix(in srgb, var(--accent) 55%, {BORDER});
  box-shadow: 0 18px 38px -22px var(--accent); }}
.insight .tag {{ display: inline-flex; align-items: center; gap: 6px; font-size: 10.5px; font-weight: 750; letter-spacing: .08em;
  text-transform: uppercase; color: var(--accent); padding: 4px 10px 4px 8px; border-radius: 999px;
  background: color-mix(in srgb, var(--accent) 14%, transparent); }}
.insight .h {{ font-size: 15px; font-weight: 700; color: {INK}; margin: 11px 0 6px; line-height: 1.35; letter-spacing: -.005em; }}
.insight .d {{ font-size: 12.8px; color: {INK2}; line-height: 1.5; }}

/* ---------- widgets ---------- */
[data-testid="stTabs"] [role="tablist"] {{ gap: 4px; background: {SURFACE}; padding: 5px; border-radius: 13px;
  border: 1px solid {BORDER}; width: fit-content; max-width: 100%; border-bottom: 1px solid {BORDER}; }}
[data-testid="stTab"] {{ height: 36px; padding: 0 16px; border-radius: 9px; background: transparent; display: flex;
  align-items: center; transition: background .2s var(--ease); }}
[data-testid="stTab"] p {{ color: {INK2}; font-weight: 550; }}
[data-testid="stTab"]:hover {{ background: {rgba(INDIGO, .12)}; }}
[data-testid="stTab"][aria-selected="true"] {{ background: linear-gradient(135deg, {INDIGO}, #5a7dff);
  box-shadow: 0 6px 18px -8px {INDIGO}; }}
[data-testid="stTab"][aria-selected="true"] p {{ color: #fff !important; font-weight: 650; }}
[data-testid="stTabs"] .react-aria-SelectionIndicator {{ display: none; }}
[data-testid="stTabPanel"] {{ padding-top: 6px; }}

[data-testid="stButtonGroup"] [role="radiogroup"], [data-testid="stButtonGroup"] [role="group"] {{
  display: inline-flex; flex-wrap: wrap; gap: 4px; padding: 4px; border-radius: 12px;
  background: {PAGE}; border: 1px solid {BORDER}; }}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"] {{
  border: 0 !important; border-radius: 9px !important; background: transparent; min-height: 32px; padding: 0 14px;
  color: {INK2}; box-shadow: none !important; transition: background .2s var(--ease), color .2s var(--ease); }}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"] p {{ color: inherit; font-weight: 550; font-size: 13px; }}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"]:hover {{ background: {rgba(INDIGO, .14)}; color: {INK}; }}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"][aria-checked="true"] {{
  background: linear-gradient(135deg, {INDIGO}, #5a7dff) !important; color: #fff !important;
  box-shadow: 0 6px 16px -8px {INDIGO} !important; }}
[data-testid="stButtonGroup"] button[data-variant="segmented_control"][aria-checked="true"] p {{ font-weight: 650; }}

/* slim toolbar card for page-level filters: st.container(key="toolbar_*") */
[class*="st-key-toolbar_"] {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 16px;
  padding: 12px 16px; margin-top: 8px; gap: 14px !important; animation: fadeUp .5s var(--ease) both; }}
.tb-label {{ display: inline-flex; align-items: center; gap: 8px; font-size: 12px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: {INK2}; white-space: nowrap; }}
.tb-label svg {{ color: {INDIGO}; }}

[data-testid="stDownloadButton"] button {{ background: linear-gradient(135deg, {INDIGO}, #5a7dff); border: 0; color: #fff;
  transition: filter .2s var(--ease), transform .2s var(--ease); }}
[data-testid="stDownloadButton"] button:hover {{ filter: brightness(1.12); transform: translateY(-1px); color: #fff; }}
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}
.count {{ font-size: 13px; color: {INK2}; padding-top: 6px; }}
.count b {{ color: {INK}; font-weight: 700; }}

.replay {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 12px 14px; border-radius: 12px;
  background: {SURFACE2}; border: 1px solid {BORDER}; margin: 4px 0 6px; font-size: 13px; color: {INK2}; }}
.replay b {{ color: {INK}; }}
.badge {{ display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px;
  font-size: 12px; font-weight: 650; }}

::-webkit-scrollbar {{ width: 10px; height: 10px; }}
::-webkit-scrollbar-thumb {{ background: {AXIS}; border-radius: 10px; border: 2px solid {PAGE}; }}
::-webkit-scrollbar-thumb:hover {{ background: #3b4770; }}
::-webkit-scrollbar-track {{ background: transparent; }}

.note {{ font-size: 12px; color: {MUTED}; margin-top: 28px; text-align: center; }}
</style>
"""


def apply_style() -> None:
    st.markdown(CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------- building blocks
CHIP_STYLE = [("calendar", INDIGO), ("users", CYAN), ("grid", AMBER), ("activity", EMERALD)]


def page_header(title: str, subtitle: str, chips: list[str] | None = None,
                eyebrow: str = "Quillstone · Search &amp; Support analytics") -> None:
    html = (f'<div class="hero"><div class="eyebrow"><span class="pulse"></span>{eyebrow}</div>'
            f'<div class="title">{title}</div><p class="sub">{subtitle}</p>')
    if chips:
        parts = [f'<span class="chip">{icon(CHIP_STYLE[i % 4][0], 14, CHIP_STYLE[i % 4][1])}{c}</span>'
                 for i, c in enumerate(chips)]
        html += '<div class="chips">' + "".join(parts) + "</div>"
    st.markdown(html + "</div>", unsafe_allow_html=True)


def section(title: str, subtitle: str = "", ico: str = "sparkles", color: str = INDIGO) -> None:
    sub = f'<span class="s">{subtitle}</span>' if subtitle else ""
    st.markdown(f'<div class="sec"><span class="ico" style="background:{rgba(color, .16)};color:{color}">'
                f'{icon(ico, 16)}</span><span class="t">{title}</span>{sub}</div>', unsafe_allow_html=True)


def card(key: str):
    """A styled content card; use as `with T.card("trend"): ...`."""
    return st.container(key=f"card_{key}")


def card_title(title: str, subtitle: str = "", ico: str = "bar", color: str = INDIGO) -> None:
    sub = f'<p class="csub">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<div class="chead"><span class="ico" style="background:{rgba(color, .15)};color:{color};'
                f'border:1px solid {rgba(color, .3)}">{icon(ico, 17)}</span>'
                f'<div><p class="ctitle">{title}</p>{sub}</div></div>', unsafe_allow_html=True)


def sparkline(values, color: str = INDIGO, w: int = 92, h: int = 36) -> str:
    v = [float(x) for x in values if x == x]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    span = (hi - lo) or 1.0
    pts = [(3 + i * (w - 6) / (len(v) - 1), h - 4 - (x - lo) / span * (h - 10)) for i, x in enumerate(v)]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    gid = "g" + hashlib.md5((color + path).encode()).hexdigest()[:10]
    ex, ey = pts[-1]
    return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-hidden="true">'
            f'<defs><linearGradient id="{gid}" x1="0" x2="0" y1="0" y2="1">'
            f'<stop offset="0" stop-color="{color}" stop-opacity=".32"/>'
            f'<stop offset="1" stop-color="{color}" stop-opacity="0"/></linearGradient></defs>'
            f'<polygon points="3,{h} {path} {w - 3},{h}" fill="url(#{gid})"/>'
            f'<polyline points="{path}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="3" fill="{color}" stroke="{SURFACE}" stroke-width="2"/></svg>')


def kpi_card(label: str, value: str, unit: str = "", delta: str = "", tone: str = "flat", foot: str = "",
             spark: str = "", accent: str = INDIGO, ico: str = "activity", delay: float = 0) -> str:
    d = ""
    if delta:
        arrow = "" if tone == "flat" else icon("trend_down" if delta.lstrip().startswith("-") else "trend_up", 13, stroke=2.4)
        d = f'<span class="pill {tone}">{arrow}{delta}</span>'
    u = f'<span class="unit">{unit}</span>' if unit else ""
    f = f'<div class="foot">{foot}</div>' if foot else ""
    return (f'<div class="kpi" style="--accent:{accent};animation-delay:{delay:.2f}s">'
            f'<div class="top"><span class="ico">{icon(ico, 17)}</span><span class="lbl">{label}</span></div>'
            f'<div class="mid"><div class="val">{value}{u}</div>{spark}</div>'
            f'<div class="bottom">{d}{f}</div></div>')


def insight_card(tone: str, tag: str, headline: str, detail: str, delay: float = 0) -> str:
    color = TONES.get(tone, INDIGO)
    ico = {"bad": "triangle", "warn": "alert", "good": "check", "info": "bulb"}.get(tone, "bulb")
    return (f'<div class="insight" style="--accent:{color};animation-delay:{delay:.2f}s">'
            f'<span class="tag">{icon(ico, 12, stroke=2.4)}{tag}</span>'
            f'<div class="h">{headline}</div><div class="d">{detail}</div></div>')


def insight_row(items: list[dict], title: str = "Highlights", subtitle: str = "Generated from the current filters",
                ico: str = "bulb", color: str = AMBER) -> None:
    """Section heading plus a row of insight cards (the Content gaps pattern, shared by every page)."""
    if not items:
        return
    section(title, subtitle, ico, color)
    for i, (col, it) in enumerate(zip(st.columns(len(items), gap="large"), items)):
        col.markdown(insight_card(it["tone"], it["tag"], it["headline"], it["detail"], delay=i * 0.06),
                     unsafe_allow_html=True)


def toolbar(key: str):
    """A slim horizontal card for page-level filters; use as `with T.toolbar("team"): ...`."""
    return st.container(key=f"toolbar_{key}", horizontal=True, vertical_alignment="center")


def toolbar_label(text: str, ico: str = "sliders") -> None:
    st.markdown(f'<span class="tb-label">{icon(ico, 15)}{text}</span>', unsafe_allow_html=True)


def count(n: int, what: str) -> None:
    st.markdown(f'<div class="count"><b>{n:,}</b> {what}</div>', unsafe_allow_html=True)


def show(fig, key: str | None = None) -> None:
    """Render a Plotly figure full-width with our own theme (not Streamlit's)."""
    cfg = {"displayModeBar": False, "responsive": True}
    try:
        st.plotly_chart(fig, width="stretch", config=cfg, key=key, theme=None)
    except TypeError:  # older Streamlit: width= not accepted
        st.plotly_chart(fig, use_container_width=True, config=cfg, key=key, theme=None)


def show_table(df, **kwargs) -> None:
    kwargs.setdefault("placeholder", "—")  # empty cells read as a dash, not "None"
    try:
        st.dataframe(df, width="stretch", hide_index=True, **kwargs)
    except TypeError:
        st.dataframe(df, use_container_width=True, hide_index=True, **kwargs)
