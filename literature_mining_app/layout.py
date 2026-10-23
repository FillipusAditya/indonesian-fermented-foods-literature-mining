"""Shared application heading and responsive styles."""

import streamlit as st


def render_header() -> None:
    st.markdown(
        """<style>
        .stMainBlockContainer {max-width: 1120px; padding-top: 4.5rem;}
        h1 {letter-spacing: -0.04em;}
        .eyebrow {color: #0f9488; font-size: .8rem; font-weight: 700;
                  letter-spacing: .14em; margin-bottom: .5rem;}
        [data-testid="stForm"] {border-radius: 16px;}
        button[kind="primary"], .stDownloadButton button {border-radius: 10px;}
        @media (max-width: 640px) {
            .stMainBlockContainer {padding: 4rem 1rem 1.5rem;}
            h1 {font-size: 2rem !important;}
            [data-testid="stHorizontalBlock"] {flex-direction: column;}
            [data-testid="stColumn"] {width: 100% !important; flex: 1 1 100% !important;}
            [data-testid="stMarkdownContainer"] code {overflow-wrap: anywhere; white-space: pre-wrap;}
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown('<div class="eyebrow">RESEARCH WORKSPACE</div>', unsafe_allow_html=True)
    st.title("Literature mining")
    st.write("Search the literature, collect metadata and abstracts, and download your results as CSV.")
