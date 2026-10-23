"""Credential widgets used in both search modes."""

import streamlit as st


def render_credentials(database: str, prefix: str = "") -> dict:
    credentials = {"email": "", "api_key": "", "inst_token": "", "use_cursor": False}
    if database in ("Crossref", "PubMed"):
        required = "required" if database == "PubMed" else "optional, recommended"
        credentials["email"] = st.text_input(
            f"Contact email ({required})", key=f"{prefix}email_{database}",
        )
    if database not in ("Europe PMC", "DOAJ", "arXiv"):
        label = {"PubMed": "NCBI", "Crossref": "Crossref Metadata Plus"}.get(database, database)
        requirement = "required" if database in ("Springer Nature", "Scopus") else "optional"
        credentials["api_key"] = st.text_input(
            f"{label} API key ({requirement})", type="password", key=f"{prefix}api_key_{database}",
        )
        if database == "OpenAlex":
            st.caption("Optional for the first page (up to 100 articles); required for subsequent cursor pages.")
        elif database == "Crossref":
            st.caption("Public access works without credentials. Add email for polite access, or a Metadata Plus key if subscribed.")
        elif database == "PubMed":
            st.caption("Contact email identifies your NCBI requests. You can leave the API key empty.")
        elif database == "CORE":
            st.caption("Public metadata search works without a key, with a lower allowance. Add your CORE key if available.")
        elif database == "Springer Nature":
            st.caption("Use a Springer Nature key with access to the Meta v2 API. Available fields depend on your plan.")
        elif database == "Scopus":
            credentials["inst_token"] = st.text_input(
                "Scopus institutional token (optional)", type="password", key=f"{prefix}scopus_inst_token",
            )
            credentials["use_cursor"] = st.checkbox(
                "Use subscriber cursor pagination", value=False, key=f"{prefix}scopus_use_cursor",
                help="Required for more than 5,000 results. Your Scopus account must permit cursor access.",
            )
            st.caption("An API key alone does not grant Scopus access. Institutional entitlement or an approved access plan is needed.")
        else:
            st.caption("You can leave the API key empty. Anonymous requests may encounter stricter throttling.")
        st.caption("Credentials are used only for API requests and are not included in the CSV.")
    return credentials
