"""NCBI PubMed search history and MEDLINE retrieval without global credentials."""

import time
from collections.abc import Callable
from io import StringIO

import pandas as pd
from Bio import Medline

from common import create_session, validate_email, validate_query
from schema import COLUMNS

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def normalize_paper(paper: dict, query: str) -> dict:
    publication_date = paper.get("DP")
    pmid = paper.get("PMID")
    identifiers = []
    # MEDLINE can represent AID/LID as either a single string or a list.
    for field in ("AID", "LID"):
        values = paper.get(field) or []
        identifiers.extend([values] if isinstance(values, str) else values)
    return {
        "doi": next((
            identifier.removesuffix(" [doi]")
            for identifier in identifiers
            if identifier.endswith(" [doi]")
        ), None),
        "pmid": pmid,
        "pmcid": paper.get("PMC"),
        "title": paper.get("TI"),
        "authors": "; ".join(paper.get("FAU") or paper.get("AU") or []) or None,
        "abstract": paper.get("AB"),
        "publication_year": int(publication_date[:4])
        if publication_date and publication_date[:4].isdigit() else None,
        "publication_date": publication_date,
        "journal": paper.get("JT"),
        "publication_type": "; ".join(paper.get("PT") or []) or None,
        "language": "; ".join(paper.get("LA") or []) or None,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
        "source_database": "PubMed",
        "query": query,
    }


def search_papers(
    query: str,
    email: str,
    api_key: str = "",
    max_results: int | None = 500,
    on_progress: Callable[[int, int], None] | None = None,
) -> tuple[pd.DataFrame, int]:
    """Require contact email; API key is optional. Fetch at most 10,000 IDs."""
    query = validate_query(query, max_results)
    email = validate_email(email, required=True)
    common_params = {"db": "pubmed", "email": email, "tool": "IndonesiaFermentedFoodsMining"}
    if api_key.strip():
        common_params["api_key"] = api_key.strip()
    records = []
    with create_session() as session:
        response = session.get(
            f"{BASE_URL}/esearch.fcgi",
            params={**common_params, "term": query, "usehistory": "y", "retmax": 0, "retmode": "json"},
            timeout=(10, 60),
        )
        response.raise_for_status()
        data = response.json()
        search = data.get("esearchresult") if isinstance(data, dict) else None
        if not isinstance(search, dict) or "count" not in search:
            raise ValueError("PubMed returned an invalid search response. Check your query and credentials.")
        if search.get("errorlist") or search.get("ERROR"):
            raise ValueError("PubMed could not interpret part of the query. Check field tags and phrases.")
        total = int(search["count"])
        target = total if max_results is None else min(total, max_results)
        if target > 10_000:
            raise ValueError("PubMed retrieval is limited to 10,000 articles per query. Narrow the query or set a smaller limit.")
        if on_progress:
            on_progress(0, total)
        if target and (not search.get("querykey") or not search.get("webenv")):
            raise ValueError("PubMed did not return a search history. Please try again.")
        for start in range(0, target, 100):
            # Keep every request, including the first EFetch, below 3 per second.
            time.sleep(0.4)
            size = min(100, target - start)
            response = session.get(
                f"{BASE_URL}/efetch.fcgi",
                params={
                    **common_params, "query_key": search["querykey"], "WebEnv": search["webenv"],
                    "retstart": start, "retmax": size, "rettype": "medline", "retmode": "text",
                },
                timeout=(10, 60),
            )
            response.raise_for_status()
            # NCBI text is UTF-8 even when a proxy omits the charset header.
            response.encoding = "utf-8"
            batch = list(Medline.parse(StringIO(response.text)))
            if len(batch) != size or any(not paper.get("PMID") for paper in batch):
                raise ValueError("PubMed retrieval stopped before completion. Please run the query again.")
            records.extend(normalize_paper(paper, query) for paper in batch)
            if on_progress:
                on_progress(len(records), total)
    return pd.DataFrame(records, columns=COLUMNS, dtype=object), total
