# spanish_state.py (v5)
# Minimal state for grid -> detail UX

from __future__ import annotations
import streamlit as st

PAGE_CONFIG = {"layout": "wide", "page_title": "Spanish Verb Lab", "page_icon": "🇪🇸"}


def ensure_state() -> None:
    st.session_state.setdefault("mode", "grid")   # grid | detail
    st.session_state.setdefault("preview", None) # currently previewed infinitive
    st.session_state.setdefault("selected", None) # currently opened infinitive (detail)


def click_tile(infinitive: str) -> None:
    """
    Grid behavior:
    - click once -> preview in sidebar
    - click same again -> open detail
    """
    prev = st.session_state.get("preview")
    if prev == infinitive and st.session_state.get("mode") == "grid":
        st.session_state["selected"] = infinitive
        st.session_state["mode"] = "detail"
    else:
        st.session_state["preview"] = infinitive
        st.session_state["selected"] = None
        st.session_state["mode"] = "grid"


def back_to_grid() -> None:
    st.session_state["mode"] = "grid"
    st.session_state["selected"] = None
