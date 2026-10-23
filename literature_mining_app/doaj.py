"""Public DOAJ article search, with the documented 1,000-record ceiling."""

import time
from collections.abc import Callable
from urllib.parse import quote

import pandas as pd

from common import as_list, create_session, integer_or_none, validate_query
from schema import COLUMNS

BASE_URL = "https://doaj.org/api/v4/search/articles"


def normalize_paper(paper: dict, query: str) -> dict:
    bib = paper.get("bibjson") or {}
    journal = bib.get("journal") or {}
    links = as_list(bib.get("link"))
    year = integer_or_none(bib.get("year"))
    month = integer_or_none(bib.get("month"))
    date = f"{year:04d}" if year else None
    if date and month and 1 <= month <= 12:
        date += f"-{month:02d}"
    return {
        "doi": next((item.get("id") for item in as_list(bib.get("identifier")) if item.get("type") == "doi"), None),
        "title": bib.get("title"),
        "authors": "; ".join(item.get("name") or "" for item in as_list(bib.get("author"))) or None,
        "abstract": bib.get("abstract"),
        "publication_year": year,
        "publication_date": date,
        "journal": journal.get("title"),
        "is_open_access": True,
        "publication_type": "journal-article",
        "language": "; ".join(as_list(journal.get("language"))) or None,
        "url": next((item.get("url") for item in links if item.get("type") == "fulltext"), None)
        or (f"https://doaj.org/article/{paper['id']}" if paper.get("id") else None),
        "pdf_url": next((item.get("url") for item in links if item.get("content_type") == "application/pdf"), None),
        "source_database": "DOAJ",
        "query": query,
    }


def search_papers(
    query: str,
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    query = validate_query(query, max_results)
    records = []
    page = 1
    # Keep pageSize fixed: reducing it on the last page would change its offset.
    page_size = 100 if max_results is None else min(100, max_results)
    with create_session() as session:
        while True:
            response = session.get(
                f"{BASE_URL}/{quote(query, safe='')}",
                params={"page": page, "pageSize": page_size}, timeout=(10, 60),
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "total" not in data or not isinstance(data.get("results"), list):
                raise ValueError("DOAJ returned an invalid response. Please try again.")
            total = int(data["total"])
            target = total if max_results is None else min(total, max_results)
            if target > 1000:
                raise ValueError("DOAJ search can retrieve at most 1,000 articles. Narrow your query or choose an article limit of 1,000 or fewer.")
            if data.get("page", page) != page:
                raise ValueError("DOAJ returned an unexpected page. Please try again.")
            batch = data["results"]
            records.extend(normalize_paper(paper, query) for paper in batch[:target - len(records)])
            if on_progress:
                on_progress(len(records), total)
            if len(records) >= target:
                break
            if not batch:
                raise ValueError("DOAJ retrieval stopped before completion. Please try again.")
            page += 1
            time.sleep(1.1)
    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
