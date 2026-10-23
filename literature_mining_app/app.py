"""Streamlit entry point for single and multi-API literature searches."""

import streamlit as st

from layout import render_header
from multi_ui import render_multi
from single_search import render_single


def clear_mode_results() -> None:
    st.session_state.pop("search_result", None)
    st.session_state.pop("multi_result", None)


def main() -> None:
    st.set_page_config(page_title="Literature Mining", page_icon="🔎", layout="wide")
    render_header()
    mode = st.radio(
        "Search mode", ["Single Database", "Multiple Databases"], horizontal=True,
        key="search_mode", on_change=clear_mode_results,
    )
    if mode == "Single Database":
        render_single()
    else:
        render_multi()


if __name__ == "__main__":
    main()
