"""Streamlit entry point for the food atlas and literature search tools."""

import streamlit as st

from food_inventory_ui import render_food_inventory
from i18n import language, tr
from layout import render_header, render_navigation, render_styles
from multi_ui import render_multi
from single_search import render_single


def clear_mode_results() -> None:
    st.session_state.pop("search_result", None)
    st.session_state.pop("multi_result", None)


def main() -> None:
    st.set_page_config(page_title="Indonesia Fermented Food", page_icon="✦", layout="wide")
    render_styles()
    page = render_navigation()
    if page == "Indonesia Fermented Food":
        render_food_inventory()
        return

    render_header()
    mode_options = (
        ["Single Database", "Multiple Databases"]
        if language() == "English"
        else ["Basis Data Tunggal", "Beberapa Basis Data"]
    )
    mode_key = "search_mode" if language() == "English" else "search_mode_idn"
    current_mode = st.session_state.get("search_mode_choice", "Single Database")
    mode = st.radio(
        tr("Search mode", "Mode pencarian"), mode_options, horizontal=True,
        index=0 if current_mode == "Single Database" else 1,
        key=mode_key, on_change=clear_mode_results,
    )
    st.session_state["search_mode_choice"] = (
        "Single Database" if mode == mode_options[0] else "Multiple Databases"
    )
    if mode == mode_options[0]:
        render_single()
    else:
        render_multi()


if __name__ == "__main__":
    main()
