"""Credential widgets used in both search modes."""

import streamlit as st

from i18n import tr


def render_credentials(database: str, prefix: str = "") -> dict:
    credentials = {"email": "", "api_key": "", "inst_token": "", "use_cursor": False}
    if database in ("Crossref", "PubMed"):
        required = tr("required", "wajib") if database == "PubMed" else tr("optional, recommended", "opsional, disarankan")
        credentials["email"] = st.text_input(
            tr(f"Contact email ({required})", f"Email kontak ({required})"), key=f"{prefix}email_{database}",
        )
    if database not in ("Europe PMC", "DOAJ", "arXiv"):
        label = {"PubMed": "NCBI", "Crossref": "Crossref Metadata Plus"}.get(database, database)
        requirement = tr("required", "wajib") if database in ("Springer Nature", "Scopus") else tr("optional", "opsional")
        credentials["api_key"] = st.text_input(
            tr(f"{label} API key ({requirement})", f"Kunci API {label} ({requirement})"), type="password", key=f"{prefix}api_key_{database}",
        )
        if database == "OpenAlex":
            st.caption(tr("Optional for the first page (up to 100 articles); required for subsequent cursor pages.", "Opsional untuk halaman pertama (hingga 100 artikel); wajib untuk halaman cursor berikutnya."))
        elif database == "Crossref":
            st.caption(tr("Public access works without credentials. Add email for polite access, or a Metadata Plus key if subscribed.", "Akses publik dapat digunakan tanpa kredensial. Tambahkan email untuk akses yang lebih tertib, atau kunci Metadata Plus jika berlangganan."))
        elif database == "PubMed":
            st.caption(tr("Contact email identifies your NCBI requests. You can leave the API key empty.", "Email kontak mengidentifikasi permintaan NCBI Anda. Kunci API boleh dikosongkan."))
        elif database == "CORE":
            st.caption(tr("Public metadata search works without a key, with a lower allowance. Add your CORE key if available.", "Pencarian metadata publik dapat dilakukan tanpa kunci, dengan kuota lebih rendah. Tambahkan kunci CORE jika tersedia."))
        elif database == "Springer Nature":
            st.caption(tr("Use a Springer Nature key with access to the Meta v2 API. Available fields depend on your plan.", "Gunakan kunci Springer Nature yang memiliki akses ke API Meta v2. Bidang yang tersedia bergantung pada paket Anda."))
        elif database == "Scopus":
            credentials["inst_token"] = st.text_input(
                tr("Scopus institutional token (optional)", "Token institusi Scopus (opsional)"), type="password", key=f"{prefix}scopus_inst_token",
            )
            credentials["use_cursor"] = st.checkbox(
                tr("Use subscriber cursor pagination", "Gunakan pagination cursor pelanggan"), value=False, key=f"{prefix}scopus_use_cursor",
                help=tr("Required for more than 5,000 results. Your Scopus account must permit cursor access.", "Diperlukan untuk lebih dari 5.000 hasil. Akun Scopus Anda harus mengizinkan akses cursor."),
            )
            st.caption(tr("An API key alone does not grant Scopus access. Institutional entitlement or an approved access plan is needed.", "Kunci API saja tidak memberikan akses Scopus. Diperlukan hak akses institusi atau paket akses yang disetujui."))
        else:
            st.caption(tr("You can leave the API key empty. Anonymous requests may encounter stricter throttling.", "Kunci API boleh dikosongkan. Permintaan anonim mungkin memiliki batas laju yang lebih ketat."))
        st.caption(tr("Credentials are used only for API requests and are not included in the CSV.", "Kredensial hanya digunakan untuk permintaan API dan tidak dimasukkan ke CSV."))
    return credentials
