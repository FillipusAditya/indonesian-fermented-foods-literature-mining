"""Crossref journal-article search with cursor pagination."""

import time
from collections.abc import Callable

import pandas as pd

from common import create_session, validate_email, validate_query
from schema import COLUMNS

BASE_URL = "https://api.crossref.org/works"


def normalize_paper(paper: dict, query: str) -> dict:
    date_parts = ((paper.get("published") or {}).get("date-parts") or [[]])[0]
    titles = paper.get("title") or []
    journals = paper.get("container-title") or []
    authors = [
        " ".join(filter(None, [author.get("given"), author.get("family")]))
        or author.get("name") or ""
        for author in paper.get("author") or []
    ]
    return {
        "doi": paper.get("DOI"),
        "title": titles[0] if titles else None,
        "authors": "; ".join(authors) or None,
        "abstract": paper.get("abstract"),
        "publication_year": date_parts[0] if date_parts else None,
        "publication_date": "-".join(f"{part:02d}" for part in date_parts) or None,
        "journal": journals[0] if journals else None,
        "publication_type": paper.get("type"),
        "language": paper.get("language"),
        "citation_count": paper.get("is-referenced-by-count"),
        "url": paper.get("URL"),
        "pdf_url": next((
            link.get("URL") for link in paper.get("link") or []
            if link.get("content-type") == "application/pdf"
        ), None),
        "source_database": "Crossref",
        "query": query,
    }


def search_papers(
    query: str,
    email: str = "",
    api_key: str = "",
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Use optional polite email and optional Metadata Plus credentials."""
    query = validate_query(query, max_results)
    email = validate_email(email)
    headers = {"Crossref-Plus-API-Token": f"Bearer {api_key.strip()}"} if api_key.strip() else {}
    records = []
    cursor = "*"
    seen_cursors = set()
    with create_session(headers) as session:
        while True:
            rows = 100 if max_results is None else min(100, max_results - len(records))
            params = {
                "query.bibliographic": query, "filter": "type:journal-article",
                "rows": rows, "cursor": cursor,
            }
            if email:
                params["mailto"] = email
            response = session.get(BASE_URL, params=params, timeout=(10, 60))
            response.raise_for_status()
            data = response.json()
            message = data.get("message") if isinstance(data, dict) else None
            if not isinstance(message, dict) or not isinstance(message.get("items"), list):
                raise ValueError("Crossref returned an invalid response. Please try again.")
            if "total-results" not in message:
                raise ValueError("Crossref did not provide a result count. Please try again.")
            total = int(message["total-results"])
            batch = message["items"]
            records.extend(normalize_paper(paper, query) for paper in batch[:rows])
            if on_progress:
                on_progress(len(records), total)
            if max_results is not None and len(records) >= max_results:
                break
            if len(batch) < rows:
                break
            next_cursor = message.get("next-cursor")
            if not next_cursor or next_cursor == cursor or next_cursor in seen_cursors:
                raise ValueError("Crossref pagination stopped before completion. Please try again.")
            seen_cursors.add(cursor)
            cursor = next_cursor
            time.sleep(1.1)
    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
