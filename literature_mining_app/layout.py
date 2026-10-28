"""Shared application heading and responsive styles."""

import streamlit as st


def render_header() -> None:
    st.markdown(
        """<style>
        .stApp {--workspace-accent: #14998b;
                --workspace-line: color-mix(in srgb, currentColor 15%, transparent);}
        .stMainBlockContainer {max-width: 1080px; padding: 3.5rem 2rem 3rem;}
        .stMainBlockContainer > div {gap: .85rem;}
        h1 {letter-spacing: -.045em; font-weight: 750 !important;}
        h3 {font-size: 1.3rem !important; letter-spacing: -.025em; padding-top: .5rem !important;}
        .st-key-workspace_header {
            border: 1px solid var(--workspace-line); border-top: 3px solid var(--workspace-accent);
            border-radius: 20px; padding: 1.7rem 2rem; margin-bottom: .4rem;
            background: linear-gradient(115deg, rgba(20, 153, 139, .1), transparent);
        }
        .st-key-workspace_header h1 {font-size: 2.65rem; padding: .1rem 0 .5rem;}
        .st-key-workspace_header p {margin-bottom: 0; opacity: .78; max-width: 680px; line-height: 1.6;}
        .eyebrow {color: var(--workspace-accent); font-size: .72rem; font-weight: 750;
                  letter-spacing: .16em; margin-bottom: .3rem;}
        [data-testid="stWidgetLabel"] p {font-size: .85rem; font-weight: 550;}
        [data-testid="stCaptionContainer"] p {line-height: 1.4; margin-bottom: 0;}
        [data-testid="stCaptionContainer"] ul {margin-bottom: 0; padding-left: 1.25rem;}
        [data-testid="stCaptionContainer"] li {margin-bottom: .2rem; line-height: 1.4;}
        .st-key-combine_groups_control {margin-top: .8rem;}
        .st-key-source_limits_note {margin-bottom: .8rem;}
        [data-testid="stRadio"] [role="radiogroup"] {gap: .65rem;}
        [data-testid="stRadioOption"] {
            border: 1px solid var(--workspace-line); border-radius: 12px;
            padding: .65rem 1rem; margin: 0;
        }
        [data-testid="stRadioOption"]:has(input:checked) {
            border-color: var(--workspace-accent);
            background: rgba(20, 153, 139, .1);
        }
        [data-testid="stVerticalBlockBorderWrapper"] > div {
            border-color: var(--workspace-line) !important; border-radius: 16px !important;
        }
        [data-testid="stExpander"] details {border-color: var(--workspace-line); border-radius: 12px;}
        [data-testid="stTextInputRootElement"], [data-baseweb="select"] > div,
        [data-testid="stNumberInputContainer"], [data-testid="stTextArea"] textarea {border-radius: 10px !important;}
        [data-testid="stButton"] button, [data-testid="stDownloadButton"] button {
            border-radius: 10px; min-height: 2.6rem; font-weight: 550;
        }
        button[kind="primary"], .stDownloadButton button {
            background: #117e73 !important; border-color: #117e73 !important; color: #fff !important;
        }
        button[kind="primary"]:hover, .stDownloadButton button:hover {
            background: #09685f !important; border-color: #09685f !important;
        }
        button[kind="primary"]:disabled {opacity: .45;}
        .st-key-database_selection [data-testid="stCheckbox"] {width: 100%;}
        .st-key-database_selection [data-testid="stCheckbox"] label {
            border: 1px solid var(--workspace-line); border-radius: 10px;
            padding: .45rem .75rem; width: 100%; max-width: none;
            min-height: 42px; box-sizing: border-box;
        }
        .st-key-database_selection [data-testid="stCheckbox"] p {line-height: 1.3; margin: 0;}
        .st-key-database_selection [data-testid="stHorizontalBlock"] {gap: .65rem;}
        .st-key-database_selection [data-testid="stCheckbox"] label:has(input:checked) {
            border-color: var(--workspace-accent);
            background: rgba(20, 153, 139, .08);
        }
        .st-key-database_selection [data-testid="stVerticalBlock"] {gap: .35rem;}
        [data-testid="stMetric"] {
            border: 1px solid var(--workspace-line); border-radius: 14px; padding: 1rem 1.2rem;
        }
        [data-testid="stCode"] {border-radius: 12px;}
        @media (max-width: 640px) {
            .stMainBlockContainer {padding: 3rem 1rem 1.5rem;}
            .st-key-workspace_header {padding: 1.2rem; border-radius: 14px;}
            .st-key-workspace_header h1 {font-size: 2rem !important;}
            [data-testid="stHorizontalBlock"] {flex-direction: column;}
            [data-testid="stColumn"] {width: 100% !important; flex: 1 1 100% !important;}
            [data-testid="stMarkdownContainer"] code {overflow-wrap: anywhere; white-space: pre-wrap;}
        }
        </style>""",
        unsafe_allow_html=True,
    )
    with st.container(key="workspace_header"):
        st.markdown('<div class="eyebrow">RESEARCH WORKSPACE</div>', unsafe_allow_html=True)
        st.title("Literature mining")
        st.write("Explore research across databases. Build your search, collect articles, and export the results.")
