"""Retrieve OpenAlex works using the notebook's metadata mapping."""

import time
from collections.abc import Callable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from schema import COLUMNS

BASE_URL = "https://api.openalex.org/works"


def normalize_paper(paper: dict, query: str) -> dict:
    """Reconstruct the abstract and preserve the shared CSV schema."""
    ids = paper.get("ids") or {}
    location = paper.get("primary_location") or {}
    source = location.get("source") or {}
    words = {
        position: word
        for word, positions in (paper.get("abstract_inverted_index") or {}).items()
        for position in positions
    }
    return {
        "doi": paper.get("doi"),
        "pmid": ids.get("pmid"),
        "pmcid": ids.get("pmcid"),
        "title": paper.get("title"),
        "authors": "; ".join(
            (author.get("author") or {}).get("display_name") or ""
            for author in paper.get("authorships") or []
        ) or None,
        "abstract": " ".join(words[position] for position in sorted(words)) or None,
        "publication_year": paper.get("publication_year"),
        "publication_date": paper.get("publication_date"),
        "journal": source.get("display_name"),
        "is_open_access": (paper.get("open_access") or {}).get("is_oa"),
        "openalex_id": paper.get("id"),
        "semantic_scholar_id": None,
        "semantic_scholar_corpus_id": None,
        "europe_pmc_id": None,
        "europe_pmc_source": None,
        "publication_type": paper.get("type"),
        "language": paper.get("language"),
        "citation_count": paper.get("cited_by_count"),
        "url": location.get("landing_page_url"),
        "pdf_url": location.get("pdf_url"),
        "source_database": "OpenAlex",
        "query": query,
    }


def search_papers(
    query: str,
    api_key: str = "",
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Send a manual search expression and follow cursor pages.

    The key is sent in an Authorization header, never in CSV metadata.
    Failures raise instead of returning a partial dataset as a success.
    """
    query, api_key = query.strip(), api_key.strip()
    if not query:
        raise ValueError("Query cannot be empty.")
    if max_results is not None and max_results < 1:
        raise ValueError("The article limit must be at least 1.")

    records = []
    cursor = "*"
    visited_cursors = set()
    retry = Retry(
        total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"], respect_retry_after_header=True,
    )
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retry))
        headers = {"User-Agent": "IndonesiaFermentedFoodsMining/1.0"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        session.headers.update(headers)
        while True:
            page_size = 100 if max_results is None else min(100, max_results - len(records))
            response = session.get(
                BASE_URL,
                params={"search": query, "per_page": page_size, "cursor": cursor},
                timeout=(10, 60),
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get("meta"), dict):
                raise ValueError("OpenAlex returned an invalid response. Check your query syntax.")
            meta = data["meta"]
            if "count" not in meta or not isinstance(data.get("results"), list):
                raise ValueError("OpenAlex returned an invalid result format. Please try again.")
            total = int(meta["count"])
            batch = data["results"]
            records.extend(normalize_paper(paper, query) for paper in batch[:page_size])
            if on_progress:
                on_progress(len(records), total)
            target = total if max_results is None else min(total, max_results)
            if len(records) >= target:
                break
            if not api_key:
                raise ValueError("OpenAlex requires an API key beyond the first page. Add a key or set the article limit to 100 or fewer.")
            next_cursor = meta.get("next_cursor")
            if not batch or not next_cursor or next_cursor == cursor or next_cursor in visited_cursors:
                raise ValueError("Retrieval stopped before completion. Please run the query again.")
            visited_cursors.add(cursor)
            cursor = next_cursor
            time.sleep(1.1)

    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
