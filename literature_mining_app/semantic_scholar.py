"""Semantic Scholar bulk search with an optional API key."""

import time
from collections.abc import Callable

import pandas as pd

from common import create_session, validate_query
from schema import COLUMNS

BASE_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
FIELDS = (
    "paperId,corpusId,title,abstract,authors,year,publicationDate,"
    "journal,venue,publicationTypes,externalIds,url,isOpenAccess,"
    "openAccessPdf,citationCount"
)


def normalize_paper(paper: dict, query: str) -> dict:
    ids = paper.get("externalIds") or {}
    return {
        "doi": ids.get("DOI"),
        "pmid": ids.get("PubMed"),
        "pmcid": ids.get("PubMedCentral"),
        "title": paper.get("title"),
        "authors": "; ".join(author.get("name") or "" for author in paper.get("authors") or []) or None,
        "abstract": paper.get("abstract"),
        "publication_year": paper.get("year"),
        "publication_date": paper.get("publicationDate"),
        "journal": (paper.get("journal") or {}).get("name") or paper.get("venue"),
        "is_open_access": paper.get("isOpenAccess"),
        "semantic_scholar_id": paper.get("paperId"),
        "semantic_scholar_corpus_id": paper.get("corpusId"),
        "publication_type": "; ".join(paper.get("publicationTypes") or []) or None,
        "citation_count": paper.get("citationCount"),
        "url": paper.get("url"),
        "pdf_url": (paper.get("openAccessPdf") or {}).get("url"),
        "source_database": "Semantic Scholar",
        "query": query,
    }


def search_papers(
    query: str,
    api_key: str = "",
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Follow continuation tokens, rather than the estimated total count."""
    query = validate_query(query, max_results)
    headers = {"x-api-key": api_key.strip()} if api_key.strip() else {}
    records = []
    token = None
    seen_tokens = set()
    with create_session(headers) as session:
        while True:
            params = {"query": query, "fields": FIELDS}
            if token:
                params["token"] = token
            response = session.get(BASE_URL, params=params, timeout=(10, 60))
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or "total" not in data or not isinstance(data.get("data"), list):
                raise ValueError("Semantic Scholar returned an invalid response. Please try again.")
            total = int(data["total"])
            batch = data["data"]
            remaining = len(batch) if max_results is None else max_results - len(records)
            records.extend(normalize_paper(paper, query) for paper in batch[:remaining])
            if on_progress:
                on_progress(len(records), total)
            if max_results is not None and len(records) >= max_results:
                break
            next_token = data.get("token")
            if not next_token:
                break
            if not batch or next_token == token or next_token in seen_tokens:
                raise ValueError("Semantic Scholar pagination stopped before completion. Please try again.")
            if len(records) >= 10_000_000:
                raise ValueError("Semantic Scholar bulk search is limited to 10 million papers. Narrow your query.")
            if token:
                seen_tokens.add(token)
            token = next_token
            time.sleep(1.1)
    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
