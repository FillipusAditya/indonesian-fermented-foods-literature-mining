"""Visual Boolean builder, sequential progress, and combined CSV results."""

from datetime import datetime, timezone

import streamlit as st

import providers
from boolean_query import build_expression, compile_query
from credentials_ui import render_credentials
from multi_search import run_searches


def clear_multi_result() -> None:
    st.session_state.pop("multi_result", None)


def add_group() -> None:
    identifier = st.session_state.builder_next_group
    st.session_state.builder_next_group += 1
    st.session_state.builder_groups.append({"id": identifier, "terms": [0], "next_term": 1})


def remove_group(identifier: int) -> None:
    st.session_state.builder_groups = [group for group in st.session_state.builder_groups if group["id"] != identifier]


def add_term(identifier: int) -> None:
    group = next(group for group in st.session_state.builder_groups if group["id"] == identifier)
    group["terms"].append(group["next_term"])
    group["next_term"] += 1


def remove_term(group_id: int, term_id: int) -> None:
    group = next(group for group in st.session_state.builder_groups if group["id"] == group_id)
    group["terms"].remove(term_id)


def render_builder():
    if "builder_groups" not in st.session_state:
        st.session_state.builder_groups = [{"id": 0, "terms": [0], "next_term": 1}]
        st.session_state.builder_next_group = 1
    st.subheader("Build your query")
    instructions = (
        "- Combine included groups with AND or OR. Excluded groups are always removed from the combined result.\n"
        "- Enable Exact phrase for text containing spaces. Wildcards, proximity operators, and native field tags are available only in Single Database mode."
    )
    validation_notice = st.empty()
    with st.container(key="combine_groups_control"):
        combine = st.selectbox("Combine included groups", ["AND", "OR"], key="builder_combine")
    groups = []
    for number, group in enumerate(st.session_state.builder_groups, start=1):
        identifier = group["id"]
        with st.container(border=True):
            heading_column, _, remove_column = st.columns([5, 2, 1.5], vertical_alignment="center")
            with heading_column:
                st.markdown(f"**Group {number}**")
            with remove_column:
                st.button(
                    "Remove group", key=f"remove_group_{identifier}",
                    on_click=remove_group, args=(identifier,),
                    disabled=len(st.session_state.builder_groups) == 1,
                )
            operator_column, exclude_column, _ = st.columns([5, 2, 1.5], vertical_alignment="bottom")
            with operator_column:
                operator = st.selectbox("Terms in this group", ["OR", "AND"], key=f"builder_operator_{identifier}")
            with exclude_column:
                exclude = st.checkbox("Exclude group", key=f"builder_exclude_{identifier}")
            terms = []
            for term_number, term_id in enumerate(group["terms"], start=1):
                text_column, phrase_column, delete_column = st.columns([5, 2, 1.5], vertical_alignment="bottom")
                with text_column:
                    text = st.text_input(
                        f"Term {term_number}", key=f"builder_term_{identifier}_{term_id}",
                        placeholder="Enter one word, or a phrase", max_chars=200,
                    )
                with phrase_column:
                    phrase = st.checkbox("Exact phrase", key=f"builder_phrase_{identifier}_{term_id}")
                with delete_column:
                    st.button(
                        "Remove term", key=f"remove_term_{identifier}_{term_id}",
                        on_click=remove_term, args=(identifier, term_id), disabled=len(group["terms"]) == 1,
                    )
                terms.append({"text": text, "phrase": phrase})
            st.button("Add term", key=f"add_term_{identifier}", on_click=add_term, args=(identifier,))
            groups.append({"operator": operator, "exclude": exclude, "terms": terms})
    st.button("Add group", key="add_group", on_click=add_group)
    try:
        expression = build_expression(groups, combine)
    except ValueError as exc:
        validation_notice.caption(f"{instructions}\n- {exc}")
        return None, str(exc)
    validation_notice.caption(instructions)
    return expression, ""


def display_results() -> None:
    result = st.session_state.get("multi_result")
    if result is None:
        return
    frame = result["frame"]
    summaries = result["summaries"]
    succeeded = sum(row["status"] != "Failed" for row in summaries)
    failed = len(summaries) - succeeded
    st.divider()
    st.subheader("Combined search results")
    st.caption("Standard query used for this run:")
    st.code(result["standard_query"], language=None, wrap_lines=True)
    st.caption("Selected sources: " + ", ".join(row["database"] for row in summaries))
    st.caption("Limit per API: " + ("All results, subject to service limits" if result["limit"] is None else str(result["limit"])))
    source_column, article_column, failure_column = st.columns(3)
    source_column.metric("Successful sources", succeeded)
    article_column.metric("Articles in CSV", len(frame))
    failure_column.metric("Failed sources", failed)
    st.dataframe(
        [{"Database": row["database"], "Status": row["status"], "Articles": row["fetched"],
          "Reported matches": row["total"], "Details": row["message"]} for row in summaries],
        hide_index=True, width="stretch",
    )
    if not succeeded:
        st.error("Every selected source failed. No combined CSV was generated.")
        return
    if failed:
        st.warning("Some sources failed. The CSV includes only successful sources; review the status table before using it.")
    if any(row["status"] == "Limited" for row in summaries):
        st.warning("Some sources reached the requested article limit. This export contains subsets of their matches.")
    if frame.empty:
        st.info("The successful sources returned no articles. The CSV contains column headers only.")
    st.download_button(
        "Download combined CSV", data=result["csv"], file_name=result["filename"],
        mime="text/csv", width="stretch", key="download_multi",
    )
    st.caption("Source duplicates are retained. standard_query and executed_query record how each row was retrieved. Counts from Semantic Scholar are estimates.")
    if not frame.empty:
        st.dataframe(
            frame.head(100), hide_index=True, width="stretch",
            column_order=["source_database", "title", "authors", "publication_year", "doi", "url"],
            column_config={"url": st.column_config.LinkColumn("Article")},
        )


def render_multi() -> None:
    st.subheader("Select databases")
    selected = []
    with st.container(key="database_selection"):
        columns = st.columns(2)
        for index, database in enumerate(providers.MULTI_DATABASES):
            with columns[index % 2]:
                if st.checkbox(database, key=f"multi_select_{database}", on_change=clear_multi_result, width="stretch"):
                    selected.append(database)
    st.caption("Crossref and Springer Nature remain available in Single Database mode.")
    node, builder_error = render_builder()
    queries = {}
    standard_query = ""
    if node is not None:
        standard_query = compile_query(node)
        st.markdown("**Standard query preview**")
        st.code(standard_query, language=None, wrap_lines=True)
        queries = {database: compile_query(node, database) for database in selected}
        with st.expander("Translated queries and search coverage"):
            st.caption("Boolean structure is preserved; source coverage, phrase matching, stemming, and default search fields differ between APIs.")
            for database, query in queries.items():
                st.markdown(f"**{database}**")
                st.caption(providers.SEARCH_SCOPES[database])
                st.code(query, language=None, wrap_lines=True)
    credentials = {}
    credential_sources = [database for database in selected if database not in ("Europe PMC", "DOAJ", "arXiv")]
    if credential_sources:
        st.subheader("Credentials")
    for database in credential_sources:
        with st.expander(f"{database} credentials", expanded=True):
            credentials[database] = render_credentials(database, prefix="multi_")
    mode_column, limit_column = st.columns(2)
    with mode_column:
        scope = st.selectbox("Retrieval scope", ["Limit articles per API", "All results"], key="multi_scope")
    with limit_column:
        limit = st.number_input(
            "Article limit per API", min_value=1, value=100, step=100,
            disabled=scope == "All results", key="multi_limit",
        )
    with st.container(key="source_limits_note"):
        st.caption("Sources run one at a time. Each source keeps its service limits: DOAJ 1,000, PubMed 10,000, arXiv 30,000; OpenAlex needs a key after its first page. Scopus needs cursor access beyond 5,000. CORE may take longer due to rate limits.")
    submitted = st.button(
        "Search selected databases", type="primary", width="stretch", key="search_multi", disabled=not selected,
    )
    if submitted:
        clear_multi_result()
        errors = []
        if builder_error:
            errors.append(builder_error)
        for database in selected:
            try:
                providers.validate_credentials(database, credentials.get(database, {}))
            except ValueError as exc:
                errors.append(f"{database}: {exc}")
        if errors:
            for error in errors:
                st.warning(error)
        else:
            max_results = None if scope == "All results" else int(limit)
            overall = st.progress(0, text=f"0 of {len(selected)} APIs completed")
            current = st.progress(0, text="Preparing sequential search…")
            status_area = st.empty()
            statuses = {database: {"Database": database, "Status": "Waiting", "Articles": 0, "Reported matches": 0} for database in selected}
            status_area.dataframe(list(statuses.values()), hide_index=True, width="stretch")

            def update(event):
                database = event["database"]
                statuses[database] = {
                    "Database": database, "Status": event["status"], "Articles": event["fetched"],
                    "Reported matches": event["total"],
                }
                target = event["total"] if max_results is None else min(event["total"], max_results)
                fraction = min(event["fetched"] / target, 1.0) if target else 0.0
                running = event["status"] == "Running"
                overall.progress(
                    min((event["completed"] + (fraction if running else 0)) / len(selected), 1.0),
                    text=f'{event["completed"]} of {len(selected)} APIs completed · {database}: {event["status"]}',
                )
                current.progress(
                    fraction if running else 1.0,
                    text=f'{database} · {event["status"]} · {event["fetched"]:,} articles retrieved',
                )
                status_area.dataframe(list(statuses.values()), hide_index=True, width="stretch")

            with st.spinner("Running selected sources sequentially…"):
                frame, summaries = run_searches(queries, standard_query, credentials, max_results, update)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                st.session_state.multi_result = {
                    "frame": frame, "summaries": summaries, "standard_query": standard_query,
                    "limit": max_results, "csv": frame.to_csv(index=False).encode("utf-8-sig"),
                    "filename": f"literature_combined_{timestamp}.csv",
                }
            current.empty()
            status_area.empty()
    display_results()
    if "arXiv" in selected:
        st.caption("Thank you to arXiv for use of its open access interoperability.")
