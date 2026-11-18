"""Search & Support Effectiveness: a Streamlit dashboard on synthetic data.

Run locally:   streamlit run app.py
Regenerate:    python generate_data.py --seed 42
"""
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).parent / "assets"
st.set_page_config(page_title="Search & Support Effectiveness", page_icon=str(ASSETS / "icon.svg"), layout="wide",
                   initial_sidebar_state="auto")  # open on desktop, collapsed on phones

from dashboard import theme as T  # noqa: E402  (after set_page_config)
from dashboard.data import build_context, load_data  # noqa: E402
from dashboard.views import agents, content_gaps, executive, explorer, search_performance  # noqa: E402

T.apply_style()
st.logo(str(ASSETS / "logo.svg"), size="large", icon_image=str(ASSETS / "icon.svg"))
tables = load_data()
st.session_state["ctx"] = build_context(tables)

pages = [
    st.Page(executive.render, title="Executive overview", icon=":material/space_dashboard:",
            url_path="overview", default=True),
    st.Page(search_performance.render, title="Search performance", icon=":material/speed:", url_path="search"),
    st.Page(content_gaps.render, title="Content gaps", icon=":material/fact_check:", url_path="content-gaps"),
    st.Page(agents.render, title="Agent effectiveness", icon=":material/support_agent:", url_path="agents"),
    st.Page(explorer.render, title="Query explorer", icon=":material/manage_search:", url_path="explorer"),
]
st.navigation(pages).run()

st.markdown('<div class="note">All data is synthetic. “Quillstone Software” is a fictional company. '
            'Built with Streamlit, pandas and Plotly.</div>', unsafe_allow_html=True)
