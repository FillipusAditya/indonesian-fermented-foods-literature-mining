"""CORE work metadata search using the public v3 API."""

import time
from collections.abc import Callable
from urllib.parse import urlsplit

import pandas as pd

from common import as_list, create_session, integer_or_none, validate_query
from schema import COLUMNS

BASE_URL = "https://api.core.ac.uk/v3/search/works/"


def normalize_paper(paper: dict, query: str) -> dict:
    authors = as_list(paper.get("authors"))
    journals = as_list(paper.get("journals"))
    language = paper.get("language")
    if isinstance(language, dict):
        language = language.get("code") or language.get("name")
    download = paper.get("downloadUrl") or paper.get("download_url")
    identifier = paper.get("id")
    return {
        "doi": paper.get("doi"),
        "title": paper.get("title"),
        "authors": "; ".join(
            (author.get("name") or "") if isinstance(author, dict) else str(author)
            for author in authors
        ) or None,
        "abstract": paper.get("abstract"),
        "publication_year": integer_or_none(paper.get("yearPublished") or paper.get("year_published")),
        "publication_date": paper.get("publishedDate") or paper.get("published_date"),
        "journal": next((journal.get("title") for journal in journals if isinstance(journal, dict) and journal.get("title")), None),
        "publication_type": paper.get("documentType") or paper.get("document_type"),
        "language": language,
        "citation_count": paper.get("citationCount", paper.get("citation_count")),
        "url": f"https://core.ac.uk/works/{identifier}" if identifier is not None else None,
        "pdf_url": download if isinstance(download, str) and urlsplit(download).path.lower().endswith(".pdf") else None,
        "source_database": "CORE",
        "query": query,
    }


def search_papers(
    query: str,
    api_key: str = "",
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    query = validate_query(query, max_results)
    headers = {"Authorization": f"Bearer {api_key.strip()}"} if api_key.strip() else {}
    records = []
    seen_ids = set()
    with create_session(headers) as session:
        while True:
            size = 100 if max_results is None else min(100, max_results - len(records))
            response = session.get(
                BASE_URL, params={"q": query, "limit": size, "offset": len(records)}, timeout=(10, 60),
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("results"), list):
                raise ValueError("CORE returned an invalid response. Please try again.")
            count = data.get("totalHits", data.get("total_hits"))
            if count is None:
                raise ValueError("CORE did not return a result count. Please try again.")
            total = int(count)
            target = total if max_results is None else min(total, max_results)
            batch = data["results"][:size]
            for paper in batch:
                identifier = paper.get("id")
                if identifier is not None:
                    if identifier in seen_ids:
                        raise ValueError("CORE repeated a result during pagination. Please try again.")
                    seen_ids.add(identifier)
            records.extend(normalize_paper(paper, query) for paper in batch)
            if on_progress:
                on_progress(len(records), total)
            if len(records) >= target:
                break
            if not batch:
                raise ValueError("CORE retrieval stopped before completion. Narrow your query or try again.")
            # Conservative pacing also accommodates the public metadata tier.
            time.sleep(6.2)
    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
