"""Scopus Search API using standard or subscriber cursor pagination."""

import time
from collections.abc import Callable

import pandas as pd

from common import as_list, boolean_or_none, create_session, integer_or_none, validate_query
from schema import COLUMNS

BASE_URL = "https://api.elsevier.com/content/search/scopus"


def normalize_paper(paper: dict, query: str) -> dict:
    date = paper.get("prism:coverDate")
    authors = as_list(paper.get("author"))
    return {
        "doi": paper.get("prism:doi"),
        "pmid": paper.get("pubmed-id"),
        "title": paper.get("dc:title"),
        "authors": "; ".join(item.get("authname") or item.get("ce:indexed-name") or "" for item in authors)
        or paper.get("dc:creator"),
        "abstract": paper.get("dc:description"),
        "publication_year": integer_or_none(date[:4]) if date else None,
        "publication_date": date,
        "journal": paper.get("prism:publicationName"),
        "is_open_access": boolean_or_none(paper.get("openaccess")),
        "publication_type": paper.get("subtypeDescription") or paper.get("prism:aggregationType"),
        "citation_count": integer_or_none(paper.get("citedby-count")),
        "url": next((item.get("@href") for item in as_list(paper.get("link")) if item.get("@ref") == "scopus"), None),
        "source_database": "Scopus",
        "query": query,
    }


def search_papers(
    query: str,
    api_key: str,
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
    inst_token: str = "",
    use_cursor: bool = False,
) -> tuple[pd.DataFrame, int]:
    query = validate_query(query, max_results)
    if not api_key.strip():
        raise ValueError("Enter your Scopus API key.")
    headers = {"X-ELS-APIKey": api_key.strip(), "Accept": "application/json"}
    if inst_token.strip():
        headers["X-ELS-Insttoken"] = inst_token.strip()
    records = []
    cursor = "*"
    seen_cursors = set()
    with create_session(headers) as session:
        while True:
            size = 100 if max_results is None else min(100, max_results - len(records))
            params = {"query": query, "view": "STANDARD", "count": size}
            params["cursor" if use_cursor else "start"] = cursor if use_cursor else len(records)
            response = session.get(BASE_URL, params=params, timeout=(10, 60))
            response.raise_for_status()
            data = response.json()
            result = data.get("search-results") if isinstance(data, dict) else None
            if not isinstance(result, dict) or "opensearch:totalResults" not in result:
                raise ValueError("Scopus returned an invalid response. Check your query and account access.")
            total = int(result["opensearch:totalResults"])
            target = total if max_results is None else min(total, max_results)
            if not use_cursor and target > 5000:
                raise ValueError("Scopus standard paging is limited to 5,000 results. Enable subscriber cursor pagination, narrow the query, or set a smaller limit.")
            batch = as_list(result.get("entry"))
            if total == 0:
                batch = []
            elif not batch or any(item.get("error") for item in batch):
                raise ValueError("Scopus retrieval stopped before completion. Check your API access or try again.")
            records.extend(normalize_paper(paper, query) for paper in batch[:size])
            if on_progress:
                on_progress(len(records), total)
            if len(records) >= target:
                break
            if use_cursor:
                next_cursor = (result.get("cursor") or {}).get("@next")
                if not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
                    raise ValueError("Scopus cursor pagination stopped before completion. Please try again.")
                seen_cursors.add(cursor)
                cursor = next_cursor
            time.sleep(1.1)
    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
