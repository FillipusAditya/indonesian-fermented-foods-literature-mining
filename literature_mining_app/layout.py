"""Shared navigation, heading, and responsive styles."""

from pathlib import Path

import streamlit as st

from i18n import tr


STYLE_PATH = Path(__file__).with_name("food_inventory.css")


def reset_language_widgets() -> None:
    st.session_state["food_page"] = 1

def render_styles() -> None:
    st.markdown(
        """<style>
        .stApp {--workspace-accent: #14998b;
                --workspace-line: color-mix(in srgb, currentColor 15%, transparent);}
        .stMainBlockContainer {max-width: 1080px; padding: 3.5rem 2rem 3rem;}
        .stMainBlockContainer > div {gap: .85rem;}
        h1 {letter-spacing: -.045em; font-weight: 750 !important;}
        h3 {font-size: 1.3rem !important; letter-spacing: -.025em; padding-top: .5rem !important;}
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
        [data-testid="stRadioOption"]:has(input:checked) > div > div:first-child {
            border-color: var(--workspace-accent) !important;
        }
        [data-testid="stRadioOption"]:has(input:checked) > div > div:first-child > div {
            background: var(--workspace-accent) !important;
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
        .st-key-search_mode, .st-key-search_mode_idn {margin-top: 1.1rem;}
        .st-key-top_nav {
            border-bottom: 1px solid var(--workspace-line);
            padding: .15rem 0 .85rem;
            margin-bottom: .8rem;
        }
        .st-key-top_nav > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
            align-items: center; justify-content: space-between; gap: 1rem;
        }
        .st-key-top_nav [data-testid="stColumn"]:last-child {
            display: flex; justify-content: flex-end;
        }
        .st-key-main_navigation [role="radiogroup"] {
            display: flex; gap: .6rem; background: transparent; border: 0;
        }
        .st-key-main_navigation button[data-variant="segmented_control"] {
            border: 1px solid var(--workspace-line); border-radius: 10px !important;
            padding: .45rem .85rem; min-height: 2.65rem;
        }
        .st-key-main_navigation button[data-selected="true"] {
            border-color: var(--workspace-accent) !important;
            background: color-mix(in srgb, currentColor 12%, transparent) !important;
            color: inherit !important;
        }
        .st-key-app_language button[data-selected="true"] {
            border-color: var(--workspace-accent) !important;
            background: color-mix(in srgb, currentColor 12%, transparent) !important;
            color: inherit !important;
        }
        .st-key-app_language [role="radiogroup"] {gap: .35rem; background: transparent; border: 0;}
        .st-key-app_language button[data-variant="segmented_control"] {
            border: 1px solid var(--workspace-line); border-radius: 10px !important;
            min-height: 2.65rem; padding: .45rem .7rem;
        }
        @media (max-width: 640px) {
            .stMainBlockContainer {padding: 3rem 1rem 1.5rem;}
            [data-testid="stHorizontalBlock"] {flex-direction: column;}
            [data-testid="stColumn"] {width: 100% !important; flex: 1 1 100% !important;}
            .st-key-top_nav > [data-testid="stLayoutWrapper"] > [data-testid="stHorizontalBlock"] {
                flex-direction: row !important; flex-wrap: wrap; gap: .5rem;
            }
            .st-key-top_nav [data-testid="stColumn"] {width: auto !important; flex: 0 1 auto !important; min-width: 0;}
            .st-key-top_nav [data-testid="stColumn"]:last-child {margin-left: auto;}
            .st-key-main_navigation [role="radiogroup"] {width: auto;}
            .st-key-main_navigation button[data-variant="segmented_control"] {
                justify-content: center; text-align: center; font-size: .78rem;
                padding: .4rem .5rem; white-space: normal;
            }
            .st-key-app_language button[data-variant="segmented_control"] {
                font-size: .78rem; padding: .4rem .45rem;
            }
            [data-testid="stMarkdownContainer"] code {overflow-wrap: anywhere; white-space: pre-wrap;}
        }
        </style>""",
        unsafe_allow_html=True,
    )
    st.markdown(f"<style>{STYLE_PATH.read_text()}</style>", unsafe_allow_html=True)


def render_navigation() -> str:
    with st.container(key="top_nav"):
        menu, language_choice = st.columns([3, 1], vertical_alignment="center")
        with menu:
            selected = st.segmented_control(
                "Page",
                ["Indonesia Fermented Food", "Tools"],
                default="Tools",
                key="main_navigation",
                label_visibility="collapsed",
            )
        with language_choice:
            st.segmented_control(
                "Language / Bahasa", ["English", "Indonesia"],
                default="English", key="app_language", label_visibility="collapsed",
                on_change=reset_language_widgets,
            )
    return selected or "Tools"


def render_header() -> None:
    st.markdown(
        '<div class="atlas-hero">'
        f'<div class="atlas-eyebrow">{tr("RESEARCH WORKSPACE", "RUANG KERJA RISET")}</div>'
        f'<div class="atlas-title">{tr("Literature Mining", "Penelusuran Literatur")}</div>'
        f'<p class="atlas-intro">{tr("Explore research across databases. Build your search, collect articles, and export the results.", "Telusuri penelitian dari berbagai basis data. Susun pencarian, kumpulkan artikel, dan ekspor hasilnya.")}</p>'
        '</div>',
        unsafe_allow_html=True,
    )
