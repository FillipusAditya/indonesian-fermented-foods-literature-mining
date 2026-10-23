"""Retrieve Europe PMC records using the notebook's CSV schema."""

import time
from collections.abc import Callable

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from schema import COLUMNS

BASE_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def normalize_paper(paper: dict, query: str) -> dict:
    """Preserve the Europe PMC mapping and column names in the notebook."""
    journal = (paper.get("journalInfo") or {}).get("journal") or {}
    full_text = (paper.get("fullTextUrlList") or {}).get("fullTextUrl") or []
    pdf_url = next(
        (item.get("url") for item in full_text if item.get("documentStyle") == "pdf"),
        None,
    )
    year = str(paper.get("pubYear") or "")
    source, identifier = paper.get("source"), paper.get("id")
    return {
        "doi": paper.get("doi"),
        "pmid": paper.get("pmid"),
        "pmcid": paper.get("pmcid"),
        "title": paper.get("title"),
        "authors": paper.get("authorString"),
        "abstract": paper.get("abstractText"),
        "publication_year": int(year) if year.isdigit() else None,
        "publication_date": paper.get("firstPublicationDate"),
        "journal": paper.get("journalTitle") or journal.get("title"),
        "is_open_access": {"Y": True, "N": False}.get(paper.get("isOpenAccess")),
        "openalex_id": None,
        "semantic_scholar_id": None,
        "semantic_scholar_corpus_id": None,
        "europe_pmc_id": identifier,
        "europe_pmc_source": source,
        "publication_type": "; ".join(
            (paper.get("pubTypeList") or {}).get("pubType") or []
        ) or None,
        "language": paper.get("language"),
        "citation_count": paper.get("citedByCount"),
        "url": f"https://europepmc.org/article/{source}/{identifier}"
        if source and identifier else None,
        "pdf_url": pdf_url,
        "source_database": "Europe PMC",
        "query": query,
    }


def search_papers(
    query: str,
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Fetch cursor pages; return records and the API's total match count.

    None means all results. Failures raise instead of exporting an incomplete
    dataset as a successful search. An explicit limit can return a subset.
    """
    query = query.strip()
    if not query:
        raise ValueError("Query cannot be empty.")
    if max_results is not None and max_results < 1:
        raise ValueError("The article limit must be at least 1.")

    records = []
    cursor = "*"
    visited_cursors = set()
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    with requests.Session() as session:
        session.mount("https://", HTTPAdapter(max_retries=retry))
        session.headers["User-Agent"] = "IndonesiaFermentedFoodsMining/1.0"
        while True:
            page_size = 100 if max_results is None else min(100, max_results - len(records))
            response = session.get(
                BASE_URL,
                params={
                    "query": query,
                    "format": "json",
                    "resultType": "core",
                    "pageSize": page_size,
                    "cursorMark": cursor,
                },
                timeout=(10, 60),
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "hitCount" not in data:
                raise ValueError("Europe PMC returned an invalid response. Check your query syntax.")
            if data.get("errMsg") or data.get("error"):
                raise ValueError("Europe PMC rejected the query. Check your query syntax.")
            total = int(data["hitCount"])
            batch = (data.get("resultList") or {}).get("result")
            if not isinstance(batch, list):
                raise ValueError("Europe PMC returned an invalid result format. Please try again.")
            records.extend(normalize_paper(paper, query) for paper in batch[:page_size])
            if on_progress:
                on_progress(len(records), total)
            target = total if max_results is None else min(total, max_results)
            if len(records) >= target:
                break
            next_cursor = data.get("nextCursorMark")
            if not batch or not next_cursor or next_cursor == cursor or next_cursor in visited_cursors:
                raise ValueError("Retrieval stopped before completion. Please run the query again.")
            visited_cursors.add(cursor)
            cursor = next_cursor
            time.sleep(1.1)

    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
