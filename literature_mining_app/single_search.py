"""Single-source native query interface."""

from datetime import datetime, timezone

import requests
import streamlit as st

import providers
from credentials_ui import render_credentials
from i18n import language, tr
from query_guides import show_query_guide

DATABASES = providers.DATABASES


def clear_results() -> None:
    st.session_state.pop("search_result", None)


def render_single() -> None:
    database = st.selectbox(
        tr("Literature database", "Basis data literatur"), DATABASES,
        key="database", on_change=clear_results,
    )
    show_query_guide(database)

    with st.container(border=True):
        credentials = render_credentials(database)
        query = st.text_area(
            tr("Search query", "Kueri pencarian"), value="", height=130, key=f"query_{database}",
            help=tr(
                f"Write a query manually following the {database} syntax guide above.",
                f"Tulis kueri secara manual sesuai panduan sintaks {database} di atas.",
            ),
        )
        mode_column, limit_column = st.columns(2)
        with mode_column:
            mode_options = (
                ["Limit article count", "All results"]
                if language() == "English"
                else ["Batasi jumlah artikel", "Semua hasil"]
            )
            mode = st.selectbox(
                tr("Retrieval scope", "Cakupan pengambilan"),
                mode_options,
            )
        with limit_column:
            limit = st.number_input(
                tr("Article limit (limited mode)", "Batas artikel (mode terbatas)"), min_value=1,
                value=100 if database == "OpenAlex" else 500, step=100, key=f"limit_{database}",
                disabled=mode == mode_options[1],
            )
        st.caption(tr("Results are retrieved page by page. Broad queries take longer.", "Hasil diambil per halaman. Kueri yang luas memerlukan waktu lebih lama."))
        submitted = st.button(tr("Search literature", "Cari literatur"), type="primary", width="stretch")

    if submitted:
        clear_results()
        validation_error = ""
        try:
            providers.validate_credentials(database, credentials)
        except ValueError as exc:
            validation_error = str(exc)
        if not query.strip():
            st.warning(tr("Enter a query before starting the search.", "Masukkan kueri sebelum memulai pencarian."))
        elif validation_error:
            st.warning(validation_error)
        else:
            progress = st.progress(0, text=tr(f"Connecting to {database}…", f"Menghubungkan ke {database}…"))
            max_results = None if mode == mode_options[1] else int(limit)

            def update_progress(fetched: int, total: int) -> None:
                target = total if max_results is None else min(total, max_results)
                fraction = min(fetched / target, 1.0) if target else 1.0
                progress.progress(fraction, text=tr(
                    f"Retrieving {fetched:,} of {target:,} articles…",
                    f"Mengambil {fetched:,} dari {target:,} artikel…",
                ))

            try:
                with st.spinner(tr(f"Retrieving metadata and abstracts from {database}…", f"Mengambil metadata dan abstrak dari {database}…")):
                    frame, total = providers.search(database, query, credentials, max_results, update_progress)
                    csv_data = frame.to_csv(index=False).encode("utf-8-sig")
                    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                    prefix = database.lower().replace(" ", "_")
                    st.session_state.search_result = {
                        "frame": frame,
                        "total": total,
                        "query": query.strip(),
                        "database": database,
                        "csv": csv_data,
                        "filename": f"{prefix}_{timestamp}.csv",
                        "limit": max_results,
                    }
            except requests.Timeout:
                st.error(tr(f"{database} took too long to respond. Try again or narrow your query.", f"{database} terlalu lama merespons. Coba lagi atau persempit kueri."))
            except requests.HTTPError as exc:
                code = exc.response.status_code if exc.response is not None else None
                if code in (401, 403):
                    st.error(tr(f"{database} rejected the API key or access is restricted. Check your key and account access.", f"{database} menolak kunci API atau akses dibatasi. Periksa kunci dan akses akun Anda."))
                elif code in (400, 422):
                    st.error(tr(f"{database} rejected the request. Check your query syntax, query length, and credentials.", f"{database} menolak permintaan. Periksa sintaks dan panjang kueri serta kredensial."))
                elif code in (402, 429):
                    st.error(tr(f"{database} usage or rate limit reached. Check your API allowance and try again later.", f"Batas penggunaan {database} tercapai. Periksa kuota API dan coba lagi nanti."))
                else:
                    st.error(tr(f"{database} could not process the request. Please try again.", f"{database} tidak dapat memproses permintaan. Coba lagi."))
            except requests.exceptions.RetryError:
                st.error(tr(f"{database} remained unavailable or rate limited after retries. Please try again later.", f"{database} masih tidak tersedia atau dibatasi setelah percobaan ulang. Coba lagi nanti."))
            except requests.RequestException:
                st.error(tr(f"Could not connect to {database}. Check your connection and try again.", f"Tidak dapat terhubung ke {database}. Periksa koneksi dan coba lagi."))
            except ValueError as exc:
                st.error(str(exc))
            finally:
                progress.empty()

    result = st.session_state.get("search_result")
    if result is not None:
        frame = result["frame"]
        st.divider()
        st.subheader(tr("Search Results", "Hasil Pencarian"))
        st.caption(tr(
            f'Database: {result["database"]} · Query used for these results:',
            f'Basis data: {result["database"]} · Kueri yang digunakan:',
        ))
        st.code(result["query"], language=None, wrap_lines=True)
        total_column, fetched_column, abstract_column = st.columns(3)
        count_label = tr("Estimated matches", "Perkiraan hasil") if result["database"] == "Semantic Scholar" else tr(f'Found in {result["database"]}', f'Ditemukan di {result["database"]}')
        total_column.metric(count_label, f'{result["total"]:,}')
        fetched_column.metric(tr("Articles in CSV", "Artikel dalam CSV"), f"{len(frame):,}")
        abstract_column.metric(tr("With abstracts", "Dengan abstrak"), f'{frame["abstract"].notna().sum():,}')
        if frame.empty:
            st.info(tr("No matching articles. Try different terms or broaden your query.", "Tidak ada artikel yang cocok. Coba istilah lain atau perluas kueri."))
        elif result["limit"] is not None and len(frame) >= result["limit"] and len(frame) < result["total"]:
            st.warning(tr("Results were limited as requested. Select ‘All results’ to retrieve every match.", "Hasil dibatasi sesuai permintaan. Pilih ‘Semua hasil’ untuk mengambil seluruh kecocokan."))
        elif len(frame) < result["total"]:
            st.info(tr("Retrieval completed. The API's reported count may be estimated or may have changed during retrieval.", "Pengambilan selesai. Jumlah yang dilaporkan API mungkin berupa perkiraan atau berubah selama proses."))
        else:
            st.success(tr("All results retrieved. Your CSV is ready to download.", "Semua hasil berhasil diambil. CSV siap diunduh."))
        st.download_button(
            tr("Download CSV", "Unduh CSV"), data=result["csv"], file_name=result["filename"],
            mime="text/csv", width="stretch",
        )
        st.caption(tr("22 columns follow the notebook schema. Abstracts and PDF links are included when available.", "Sebanyak 22 kolom mengikuti skema notebook. Abstrak dan tautan PDF disertakan jika tersedia."))
        if not frame.empty:
            st.markdown(tr("**Preview · up to 100 articles**", "**Pratinjau · hingga 100 artikel**"))
            st.dataframe(
                frame.head(100),
                column_order=["title", "authors", "publication_year", "journal", "doi", "url", "abstract"],
                column_config={"url": st.column_config.LinkColumn(tr("Article", "Artikel"))},
                hide_index=True, width="stretch",
            )

    st.caption(" · ".join(DATABASES))
    if database == "arXiv":
        st.caption(tr("Thank you to arXiv for use of its open access interoperability.", "Terima kasih kepada arXiv atas interoperabilitas akses terbukanya."))

