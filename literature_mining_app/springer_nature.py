"""Springer Nature Meta v2 metadata search."""

import time
from collections.abc import Callable

import pandas as pd

from common import as_list, boolean_or_none, create_session, integer_or_none, validate_query
from schema import COLUMNS

BASE_URL = "https://api.springernature.com/meta/v2/json"


def normalize_paper(paper: dict, query: str) -> dict:
    urls = as_list(paper.get("url"))
    date = paper.get("publicationDate")
    abstract = paper.get("abstract")
    if isinstance(abstract, dict):
        abstract = abstract.get("p") or abstract.get("value")
    return {
        "doi": paper.get("doi"),
        "title": paper.get("title"),
        "authors": "; ".join(
            (item.get("creator") or item.get("name") or "") if isinstance(item, dict) else str(item)
            for item in as_list(paper.get("creators"))
        ) or None,
        "abstract": abstract,
        "publication_year": integer_or_none(date[:4]) if date else None,
        "publication_date": date,
        "journal": paper.get("publicationName") or paper.get("journalTitle"),
        "is_open_access": boolean_or_none(paper.get("openaccess", paper.get("openAccess"))),
        "publication_type": paper.get("genre") or paper.get("publicationType"),
        "language": paper.get("language"),
        "url": next((item.get("value") for item in urls if isinstance(item, dict) and item.get("format") == "html"), None)
        or (f"https://doi.org/{paper['doi']}" if paper.get("doi") else None),
        "pdf_url": next((item.get("value") for item in urls if isinstance(item, dict) and item.get("format") == "pdf"), None),
        "source_database": "Springer Nature",
        "query": query,
    }


def search_papers(
    query: str,
    api_key: str,
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    query = validate_query(query, max_results)
    if not api_key.strip():
        raise ValueError("Enter your Springer Nature API key.")
    records = []
    with create_session() as session:
        while True:
            size = 20 if max_results is None else min(20, max_results - len(records))
            response = session.get(
                BASE_URL,
                params={"api_key": api_key.strip(), "q": query, "s": len(records) + 1, "p": size},
                timeout=(10, 60),
            )
            response.raise_for_status()
            data = response.json()
            summaries = data.get("result") if isinstance(data, dict) else None
            if not isinstance(summaries, list) or not summaries or not isinstance(data.get("records"), list):
                raise ValueError("Springer Nature returned an invalid response. Check your query and API access.")
            if "total" not in summaries[0]:
                raise ValueError("Springer Nature did not return a result count. Please try again.")
            total = int(summaries[0]["total"])
            target = total if max_results is None else min(total, max_results)
            batch = data["records"][:size]
            records.extend(normalize_paper(paper, query) for paper in batch)
            if on_progress:
                on_progress(len(records), total)
            if len(records) >= target:
                break
            if not batch:
                raise ValueError("Springer Nature retrieval stopped before completion. Check your plan limits or narrow the query.")
            time.sleep(1.1)
    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
