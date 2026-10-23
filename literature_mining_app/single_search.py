"""Single-source native query interface."""

from datetime import datetime, timezone

import requests
import streamlit as st

import providers
from credentials_ui import render_credentials
from query_guides import show_query_guide

DATABASES = providers.DATABASES


def clear_results() -> None:
    st.session_state.pop("search_result", None)


def render_single() -> None:
    database = st.selectbox(
        "Literature database", DATABASES,
        key="database", on_change=clear_results,
    )
    show_query_guide(database)

    with st.container(border=True):
        credentials = render_credentials(database)
        query = st.text_area(
            "Search query", value="", height=130, key=f"query_{database}",
            help=f"Write a query manually following the {database} syntax guide above.",
        )
        mode_column, limit_column = st.columns(2)
        with mode_column:
            mode = st.selectbox("Retrieval scope", ["Limit article count", "All results"])
        with limit_column:
            limit = st.number_input(
                "Article limit (limited mode)", min_value=1,
                value=100 if database == "OpenAlex" else 500, step=100, key=f"limit_{database}",
                disabled=mode == "All results",
            )
        st.caption("Results are retrieved page by page. Broad queries take longer.")
        submitted = st.button("Search literature", type="primary", width="stretch")

    if submitted:
        clear_results()
        validation_error = ""
        try:
            providers.validate_credentials(database, credentials)
        except ValueError as exc:
            validation_error = str(exc)
        if not query.strip():
            st.warning("Enter a query before starting the search.")
        elif validation_error:
            st.warning(validation_error)
        else:
            progress = st.progress(0, text=f"Connecting to {database}…")
            max_results = None if mode == "All results" else int(limit)

            def update_progress(fetched: int, total: int) -> None:
                target = total if max_results is None else min(total, max_results)
                fraction = min(fetched / target, 1.0) if target else 1.0
                progress.progress(fraction, text=f"Retrieving {fetched:,} of {target:,} articles…")

            try:
                with st.spinner(f"Retrieving metadata and abstracts from {database}…"):
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
                st.error(f"{database} took too long to respond. Try again or narrow your query.")
            except requests.HTTPError as exc:
                code = exc.response.status_code if exc.response is not None else None
                if code in (401, 403):
                    st.error(f"{database} rejected the API key or access is restricted. Check your key and account access.")
                elif code in (400, 422):
                    st.error(f"{database} rejected the request. Check your query syntax, query length, and credentials.")
                elif code in (402, 429):
                    st.error(f"{database} usage or rate limit reached. Check your API allowance and try again later.")
                else:
                    st.error(f"{database} could not process the request. Please try again.")
            except requests.exceptions.RetryError:
                st.error(f"{database} remained unavailable or rate limited after retries. Please try again later.")
            except requests.RequestException:
                st.error(f"Could not connect to {database}. Check your connection and try again.")
            except ValueError as exc:
                st.error(str(exc))
            finally:
                progress.empty()

    result = st.session_state.get("search_result")
    if result is not None:
        frame = result["frame"]
        st.divider()
        st.subheader("Search results")
        st.caption(f'Database: {result["database"]} · Query used for these results:')
        st.code(result["query"], language=None, wrap_lines=True)
        total_column, fetched_column, abstract_column = st.columns(3)
        count_label = "Estimated matches" if result["database"] == "Semantic Scholar" else f'Found in {result["database"]}'
        total_column.metric(count_label, f'{result["total"]:,}')
        fetched_column.metric("Articles in CSV", f"{len(frame):,}")
        abstract_column.metric("With abstracts", f'{frame["abstract"].notna().sum():,}')
        if frame.empty:
            st.info("No matching articles. Try different terms or broaden your query.")
        elif result["limit"] is not None and len(frame) >= result["limit"] and len(frame) < result["total"]:
            st.warning("Results were limited as requested. Select ‘All results’ to retrieve every match.")
        elif len(frame) < result["total"]:
            st.info("Retrieval completed. The API's reported count may be estimated or may have changed during retrieval.")
        else:
            st.success("All results retrieved. Your CSV is ready to download.")
        st.download_button(
            "Download CSV", data=result["csv"], file_name=result["filename"],
            mime="text/csv", width="stretch",
        )
        st.caption("22 columns follow the notebook schema. Abstracts and PDF links are included when available.")
        if not frame.empty:
            st.markdown("**Preview · up to 100 articles**")
            st.dataframe(
                frame.head(100),
                column_order=["title", "authors", "publication_year", "journal", "doi", "url", "abstract"],
                column_config={"url": st.column_config.LinkColumn("Article")},
                hide_index=True, width="stretch",
            )

    st.caption(" · ".join(DATABASES))
    if database == "arXiv":
        st.caption("Thank you to arXiv for use of its open access interoperability.")

