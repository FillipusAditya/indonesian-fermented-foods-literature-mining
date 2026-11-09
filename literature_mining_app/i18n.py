"""Small shared language helper for visible interface text."""

import streamlit as st


def language() -> str:
    return st.session_state.get("app_language", "English")


def tr(english: str, indonesian: str) -> str:
    return indonesian if language() == "Indonesia" else english
